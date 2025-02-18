import random
import socket
import threading
from typing import List
import time
from log import log

PING_INTERVAL = 3
PING_MAX_WAIT = 5
GOSSIP_SEND_INTERVAL = 5
NUM_MESSAGES = 10

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Connecting to an external host forces the OS to pick the right outbound interface.
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


class Peers:
    def __init__(self, ip=None, port=0):
        # If no IP is provided, determine the machine's local IP dynamically.
        if ip is None:
            self.ip = get_local_ip()
        else:
            self.ip = ip
        self.port = int(port)
        self.server_socket = None
        
        self.seed_list = []
        self.peer_list = []  # list of tuples: (ip, port, degree)
        self.seed_connections: List[socket.socket] = []  # List of seed connection sockets
        self.peer_connections: List[socket.socket] = []  # List of peer connection sockets
        
        self.message_hashes = set()
        self.running_status = True
        self.isDead = False
        self.ping_tracker = {}  # Keeping track of consecutive failed pings for each peer
        self.peer_info = {}
        
    def creation(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Enable immediate reuse of the address
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server_socket.bind((self.ip, self.port))
            # If port was set to 0, update self.port with the assigned port.
            if self.port == 0:
                self.port = self.server_socket.getsockname()[1]
            self.server_socket.listen()
            msg = f"Peer listening on {self.ip}:{self.port}"
            print(msg)
            log(msg)
            thread = threading.Thread(target=self.accept_connections, daemon=True)
            thread.start()
        except Exception as e:
            err_msg = f"Error creating peer server on {self.ip}:{self.port}: {e}"
            print(err_msg)
            # log(err_msg)
    
    def connect(self, seeds):
        # Choosing (n/2)+1 seeds randomly from the provided list
        if len(seeds) > 0:
            self.seed_list = random.sample(seeds, (len(seeds) // 2) + 1)
        for seed in self.seed_list:
            self.connect_to_seed(seed)
        
        self.request_peer_lists()
        self.connect_to_peers()
        
        # We send connection update to all connected seeds
        self.send_connection_update()
        
        # Starting background threads for pings and gossip only if not dead
        if not self.isDead:
            thread_ping_sender = threading.Thread(target=self.ping_sender, daemon=True)
            thread_ping_sender.start()
        
            thread_sender = threading.Thread(target=self.gossip_sender_all, daemon=True)
            thread_sender.start()
        
        # To simulate peer death
        thread_death = threading.Thread(target=self.simulate_death, daemon=True)
        thread_death.start()
    
    # Method to simulate peer death; only a few peers (30% chance) will be marked as dead
    def simulate_death(self):
        chance_to_die = 0.3  
        if random.random() < chance_to_die:
            death_time = random.uniform(30, 60)  # Peer dies between 30 and 90 seconds
            time.sleep(death_time)
            self.isDead = True
            msg = f"Peer {self.ip}:{self.port} has died (simulated)."
            print(msg)
            log(msg)
            # Notifying all connected seeds that this peer is dead
            # for seed_socket in self.seed_connections:
            #     try:
            #         dead_msg = f"DEAD_NODE:{self.ip}:{self.port}:{time.strftime('%H:%M:%S')}:{self.ip}:{self.port}\n"
            #         seed_socket.sendall(dead_msg.encode('utf-8'))
            #         log(f"Notified seed {seed_socket.getpeername()} about dead peer {self.ip}:{self.port}")
            #     except Exception as e:
            #         err_msg = f"Error notifying seed of dead peer: {e}"
            #         print(err_msg)
            #         # log(err_msg)
        else:
            msg = f"Peer {self.ip}:{self.port} remains alive (simulation)."
            print(msg)
            # log(msg)
    
    # Sending peer ping to all connected peers
    def ping_sender(self):
        while self.running_status and not self.isDead:
            for peer_socket in list(self.peer_connections):
                self.ping_sender_peer(peer_socket)
            time.sleep(PING_INTERVAL)
    
    # Method to send ping to a peer
    def ping_sender_peer(self, peer_socket: socket.socket):
        if self.isDead or not self.running_status:
            return
        try:
            if peer_socket not in self.ping_tracker:
                self.ping_tracker[peer_socket] = [time.time(), 0]
            peer_addr = self.peer_info[peer_socket]
            if time.time() - self.ping_tracker[peer_socket][0] >= PING_MAX_WAIT:
                # Increase counter if ping not received
                counter = self.ping_tracker[peer_socket][1]
                self.ping_tracker[peer_socket] = [time.time(), counter + 1]
                if self.ping_tracker[peer_socket][1] >= 3:
                    msg = f"Peer(client)({self.ip}:{self.port}) -> Peer {peer_addr} is dead"
                    print(msg)
                    log(msg)
                    if peer_socket in self.peer_connections:
                        self.peer_connections.remove(peer_socket)
                    if peer_addr in self.peer_list:
                        self.peer_list = [p for p in self.peer_list if p[0:2] != peer_addr]
                    for seed_socket in self.seed_connections:
                        dead_msg = f"DEAD_NODE:{peer_addr[0]}:{peer_addr[1]}:{time.strftime('%H:%M:%S')}:{self.ip}:{self.port}\n"
                        seed_socket.sendall(dead_msg.encode('utf-8'))
                    peer_socket.close()
                    return
            peer_socket.sendall("PING\n".encode('utf-8'))
            msg = f"Peer(client)({self.ip}:{self.port}) -> Sent: PING to {peer_addr}"
            print(msg)
            log(msg)
        except Exception as e:
            if not self.running_status:
                return
            peer_addr = self.peer_info.get(peer_socket, ("Unknown", "Unknown"))
            err_msg = f"Peer(client)({self.ip}:{self.port}) -> Error {e} when sending PING to {peer_addr}"
            print(err_msg)
            # Increment ping counter on exception as well
            if peer_socket not in self.ping_tracker:
                self.ping_tracker[peer_socket] = [time.time(), 1]
            else:
                self.ping_tracker[peer_socket][1] += 1
            if self.ping_tracker[peer_socket][1] >= 3:
                msg = f"Peer(client)({self.ip}:{self.port}) -> Peer {peer_addr} is dead due to repeated ping failures"
                print(msg)
                log(msg)
                if peer_socket in self.peer_connections:
                    self.peer_connections.remove(peer_socket)
                # Notify all connected seeds about the dead peer
                for seed_socket in self.seed_connections:
                    try:
                        dead_msg = f"DEAD_NODE:{peer_addr[0]}:{peer_addr[1]}:{time.strftime('%H:%M:%S')}:{self.ip}:{self.port}\n"
                        seed_socket.sendall(dead_msg.encode('utf-8'))
                    except Exception as ex:
                        print(f"Error notifying seed: {ex}")
                try:
                    peer_socket.close()
                except Exception:
                    pass
            return

    # def ping_sender_peer(self, peer_socket: socket.socket):
    #     if self.isDead or not self.running_status:
    #         return
    #     try:
    #         if peer_socket not in self.ping_tracker:
    #             self.ping_tracker[peer_socket] = [time.time(), 0]
    #         if time.time() - self.ping_tracker[peer_socket][0] >= PING_MAX_WAIT:  # Increase counter if ping not received
    #             counter = self.ping_tracker[peer_socket][1]
    #             self.ping_tracker[peer_socket] = [time.time(), counter + 1]
    #             if self.ping_tracker[peer_socket][1] >= 3:  # If counter is >= 3 then peer is dead
    #                 msg = f"Peer(client)({self.ip}:{self.port}) -> Peer {peer_socket.getpeername()} is dead"
    #                 print(msg)
    #                 log(msg)
    #                 if peer_socket in self.peer_connections:
    #                     self.peer_connections.remove(peer_socket)
    #                 if peer_socket.getpeername() in self.peer_list:
    #                     self.peer_list = [p for p in self.peer_list if p[0:2] != peer_socket.getpeername()]
    #                 for seed_socket in self.seed_connections:  # Notifying all connected seeds that this peer is dead
    #                     dead_msg = f"DEAD_NODE:{peer_socket.getpeername()[0]}:{peer_socket.getpeername()[1]}:{time.strftime('%H:%M:%S')}:{self.ip}:{self.port}\n"
    #                     seed_socket.sendall(dead_msg.encode('utf-8'))
    #                 peer_socket.close()
    #                 return
    #         peer_socket.sendall("PING\n".encode('utf-8'))
    #         msg = f"Peer(client)({self.ip}:{self.port}) -> Sent: PING to {peer_socket.getpeername()}"
    #         print(msg)
    #         log(msg)
    #     except Exception as e:
    #         if not self.running_status:
    #             return
    #         try:
    #             peer_name = peer_socket.getpeername()
    #         except Exception:
    #             peer_name = "Unknown"
    #         err_msg = f"Peer(client)({self.ip}:{self.port}) -> Error {e} when sending PING to {peer_name}"
    #         print(err_msg)
    #         # log(err_msg)
    
    # Sending gossip to all connected peers 
    def gossip_sender_all(self):
        for i in range(NUM_MESSAGES):
            if not self.running_status or self.isDead:
                break
            message = f"{time.strftime('%H:%M:%S')}:{self.ip}:{self.port}:m"
            message_hash = hash(message)
           
            if message_hash not in self.message_hashes:  # If message hash is not seen before, send to all peers
                log(f"Peer {self.ip}:{self.port} -> Sending hash message for first time: {message}")
                self.message_hashes.add(message_hash)
                for peer in list(self.peer_connections):
                    thread = threading.Thread(target=self.gossip_sender_peer, args=(peer, message_hash), daemon=True)
                    thread.start()
            time.sleep(GOSSIP_SEND_INTERVAL)
    
    # Helper function to send gossip to a peer
    def gossip_sender_peer(self, peer: socket.socket, message_hash: int):
        try:
            peer.sendall(f"GOSSIP:{message_hash}\n".encode('utf-8'))
            msg = f"Peer(server)({self.ip}:{self.port}) -> Sent: GOSSIP:{message_hash}"
            print(msg)
            # log(msg)
        except Exception as e:
            if self.running_status:
                err_msg = f"Peer(server)({self.ip}:{self.port}) -> Error sending gossip to peer: {e}"
                print(err_msg)
                # log(err_msg)
           
    
    # def peer_listener(self, peer: socket.socket, buffer: str):
    #     while self.running_status and not self.isDead:
    #         try:
    #             data = peer.recv(1024)
    #         except Exception as e:
    #             err_msg = f"Peer(server)({self.ip}:{self.port}) -> Error receiving data: {e}"
    #             print(err_msg)
    #             # log(err_msg)
    #             break
    #         decoded_data = data.decode('utf-8')
    #         if not data:
    #             break
    #         buffer += decoded_data
    #         while "\n" in buffer:
    #             line, buffer = buffer.split("\n", 1)
    #             if line:
    #                 msg = f"Peer(server)({self.ip}:{self.port}) -> Received: {line}"
    #                 print(msg)
    #                 log(msg)
    #                 if line.startswith("PING"):  # If received ping then send pong
    #                     peer.sendall("PONG\n".encode('utf-8'))
    #                     msg = f"Peer(server)({self.ip}:{self.port}) -> Received: PING from {peer.getpeername()} and sent: PONG"
    #                     print(msg)
    #                     log(msg)
    #                 if line.startswith("PONG"):  # If received pong then update the ping tracker
    #                     self.ping_tracker[peer] = [time.time(), 0]
    #                     msg = f"Peer(server)({self.ip}:{self.port}) -> Received: PONG from {peer.getpeername()} and updated the ping tracker"
    #                     print(msg)
    #                     log(msg)
    #                 if line.startswith("GOSSIP:"):  # If received gossip then propagate to other peers
    #                     try:
    #                         message_hash = int(line.split("GOSSIP:")[1])
    #                     except ValueError:
    #                         err_msg = f"Failed to parse message hash from: {line}"
    #                         print(err_msg)
    #                         # log(err_msg)
    #                         continue
    #                     if message_hash not in self.message_hashes:
    #                         self.message_hashes.add(message_hash)
    #                         for peer_socket in list(self.peer_connections):
    #                             if peer_socket != peer:
    #                                 thread = threading.Thread(target=self.gossip_sender_peer, args=(peer_socket, message_hash), daemon=True)
    #                                 thread.start()
    
    
    def peer_listener(self, peer: socket.socket, buffer: str, handshake_required: bool = True):
        handshake_done = not handshake_required
        while self.running_status and not self.isDead:
            try:
                data = peer.recv(1024)
            except Exception as e:
                err_msg = f"Error receiving data: {e}"
                print(err_msg)
                log(err_msg)
                break
            if not data:
                break
            buffer += data.decode('utf-8')
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if line:
                    if not handshake_done:
                        # Expect handshake message only for inbound connections.
                        if line.startswith("PEER_SERVER:") or line.startswith("NEW_PEER_SERVER:"):
                            try:
                                remote_port = int(line.split(":")[1])
                                remote_ip = peer.getpeername()[0]
                                self.peer_info[peer] = (remote_ip, remote_port)
                                handshake_done = True
                                msg = f"Handshake complete with peer {remote_ip}:{remote_port}"
                                print(msg)
                                log(msg)
                            except ValueError:
                                err_msg = f"Invalid handshake message: {line}"
                                print(err_msg)
                                log(err_msg)
                        else:
                            err_msg = f"Expected handshake but received: {line}"
                            print(err_msg)
                            log(err_msg)
                    else:
                        # Process subsequent messages.
                        msg = f"Received: {line}"
                        print(msg)
                        log(msg)
                        if line.startswith("PING"):
                            peer.sendall("PONG\n".encode('utf-8'))
                            msg = f"Received PING and sent PONG to {self.peer_info.get(peer, peer.getpeername())}"
                            print(msg)
                            log(msg)
                        elif line.startswith("PONG"):
                            self.ping_tracker[peer] = [time.time(), 0]
                            msg = f"Received PONG from {self.peer_info.get(peer, peer.getpeername())}"
                            print(msg)
                            log(msg)
                        elif line.startswith("GOSSIP:"):
                            try:
                                message_hash = int(line.split("GOSSIP:")[1])
                            except ValueError:
                                err_msg = f"Failed to parse message hash: {line}"
                                print(err_msg)
                                log(err_msg)
                                continue
                            if message_hash not in self.message_hashes:
                                self.message_hashes.add(message_hash)
                                for peer_socket in list(self.peer_connections):
                                    if peer_socket != peer:
                                        thread = threading.Thread(
                                            target=self.gossip_sender_peer, 
                                            args=(peer_socket, message_hash), 
                                            daemon=True
                                        )
                                        thread.start()


    def accept_connections(self):
        while self.running_status and not self.isDead:
            try:
                connection, address = self.server_socket.accept()
                msg = f"Peer(server)({self.ip}:{self.port}) -> New connection from {address[0]}:{address[1]}"
                print(msg)
                log(msg)
                self.peer_connections.append(connection)
                # self.peer_info[connection] = (address[0], address[1])
                buffer = ""
                thread = threading.Thread(target=self.peer_listener, args=(connection, buffer, True), daemon=True)
                thread.start()
            except Exception as e:
                if self.running_status:
                    err_msg = f"Peer(server)({self.ip}:{self.port}) -> Error accepting connection: {e}"
                    print(err_msg)
                    # log(err_msg)
                break
    
    
    
    def connect_to_seed(self, seed):
        try:
            seed_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            seed_socket.connect((seed[0], seed[1]))
            msg = f"Peer(client)({self.ip}:{self.port}) -> Connected to seed {seed[0]}:{seed[1]}"
            print(msg)
            log(msg)
            # Send this peer's server port to the seed
            seed_socket.sendall(f"PEER_SERVER:{self.port}\n".encode('utf-8'))
            self.seed_connections.append(seed_socket)
        except socket.error as e:
            err_msg = f"Peer(client)({self.ip}:{self.port}) -> Failed to connect to seed {seed[0]}:{seed[1]}. Error:{e}"
            print(err_msg)
            # log(err_msg)
    
    def request_peer_lists(self):
        # Merge peer lists from all connected seeds, taking the maximum degree for duplicates
        merged_peers = {}
        for seed_socket in self.seed_connections:
            try:
                seed_socket.sendall(f"REQUEST_PEER_LIST:{self.port}\n".encode('utf-8'))
                peer_list_str = seed_socket.recv(1024).decode('utf-8')
                if peer_list_str:
                    peers = peer_list_str.split('\n')
                    for peer in peers:
                        if peer:
                            parts = peer.split(':')
                            if len(parts) != 3:
                                continue
                            ip, port_str, degree_str = parts
                            try:
                                port = int(port_str)
                                degree = int(degree_str)
                            except ValueError:
                                continue
                            key = (ip, port)
                            if key in merged_peers:
                                merged_peers[key] = max(merged_peers[key], degree)
                            else:
                                merged_peers[key] = degree
            except Exception as e:
                err_msg = f"Peer(client)({self.ip}:{self.port}) -> Error requesting peer list from {seed_socket.getpeername()}: {e}"
                print(err_msg)
                # log(err_msg)
        # Update self.peer_list from merged_peers
        self.peer_list = [(ip, port, merged_peers[(ip, port)]) for (ip, port) in merged_peers]
        msg = f"Peer(client)({self.ip}:{self.port}) -> Merged peer list: {self.peer_list}"
        print(msg)
        log(msg)
    
    def connect_to_peers(self):
        # Use an offset-based preferential attachment:
        # threshold = 1/(peer_degree + 1). Connect if random() > threshold.
        for peer in set(self.peer_list):
            peer_ip, peer_port, peer_degree = peer
            if peer_ip == self.ip and peer_port == self.port:
                continue  # Skip self
            threshold = 1 / (peer_degree + 1)
            rand_val = random.random()
            msg = f"Evaluating connection to {peer_ip}:{peer_port} with degree {peer_degree} -> threshold {threshold:.4f}, random value {rand_val:.4f}"
            print(msg)
            log(msg)
            if rand_val > threshold:
                try:
                    peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    peer_socket.connect((peer_ip, peer_port))
                    self.peer_connections.append(peer_socket)
                    peer_socket.sendall(f"NEW_PEER_SERVER:{self.port}\n".encode('utf-8'))
                    self.peer_info[peer_socket] = (peer_ip, peer_port)
                    msg = f"Peer(client)({self.ip}:{self.port}) -> Connected to peer {peer_ip}:{peer_port}"
                    print(msg)
                    log(msg)
                    thread = threading.Thread(target=self.peer_listener, args=(peer_socket, "", False), daemon=True)
                    thread.start()
                except socket.error as e:
                    err_msg = f"Peer(client)({self.ip}:{self.port}) -> Failed to connect to peer {peer_ip}:{peer_port}. Error:{e}"
                    print(err_msg)
                    # log(err_msg)
    
    # This method sends connection updates to all connected seeds.
    def send_connection_update(self):
        # Send connection update to all connected seeds with the list of connected peers.
        connected_peers = []
        for peer_socket in self.peer_connections:
            try:
                peer_addr = peer_socket.getpeername()
                connected_peers.append(f"{peer_addr[0]}:{peer_addr[1]}")
            except Exception:
                continue
        new_degree = len(self.peer_connections)
        update_msg = f"CONNECTION_UPDATE:{self.ip}:{self.port}:{new_degree}:"
        if connected_peers:
            update_msg += ",".join(connected_peers)
        update_msg += "\n"
        for seed_socket in self.seed_connections:
            try:
                seed_socket.sendall(update_msg.encode('utf-8'))
                msg = f"Peer(client)({self.ip}:{self.port}) -> Sent connection update to seed {seed_socket.getpeername()}"
                print(msg)
                log(msg)
            except Exception as e:
                err_msg = f"Peer(client)({self.ip}:{self.port}) -> Failed to send connection update to seed. Error: {e}"
                print(err_msg)
                # log(err_msg)
    
    # Close the peer
    def close(self):
        # for seed_socket in self.seed_connections:
        #     try:
        #         goodbye_msg = f"GOODBYE:{self.ip}:{self.port}\n"
        #         seed_socket.sendall(goodbye_msg.encode('utf-8'))
        #         msg = f"Sent GOODBYE to seed {seed_socket.getpeername()}"
        #         print(msg)
        #         log(msg)
        #     except Exception as e:
        #         err_msg = f"Error sending GOODBYE to seed: {e}"
        #         print(err_msg)
        #         log(err_msg)
        self.running_status = False
        if self.server_socket:
            try:
                self.server_socket.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            self.server_socket.close()
            msg = f"Peer on {self.ip}:{self.port} closed."
            print(msg)
            log(msg)
        # for conn in self.seed_connections:
        #     try:
        #         conn.shutdown(socket.SHUT_RDWR)
        #     except Exception:
        #         pass
        #     try:
        #         conn.close()
        #     except Exception as e:
        #         err_msg = f"Error closing a peer-to-seed connection: {e}"
        #         print(err_msg)
        #         log(err_msg)
        # for conn in self.peer_connections:
        #     try:
        #         conn.shutdown(socket.SHUT_RDWR)
        #     except Exception:
        #         pass
        #     try:
        #         conn.close()
        #     except Exception as e:
        #         err_msg = f"Error closing a peer-to-peer connection: {e}"
        #         print(err_msg)
        #         log(err_msg)
