import random
import socket
import threading
from typing import List
import time
import select

PING_INTERVAL = 2
PING_MAX_WAIT = 5
GOSSIP_SEND_INTERVAL = 15
NUM_MESSAGES = 10

class Peers:
    def __init__(self,ip,port):
        # While playing role of server
        self.ip = ip
        self.port = int(port)
        self.server_socket = None
        
        self.seed_list = []
        self.peer_list = []
        self.seed_connections: List[socket.socket] = []       # List of sockets of connections when it is behaving as client
        self.peer_connections: List[socket.socket] = []
        
        self.message_hashes = set()
        self.running_status = True
        self.isDead = False
        self.ping_tracker = {}                              #Keeping track of number of consequtive failed pings
        
    def creation(self):  # activate (fulfiling it as server)
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.ip, self.port))
        self.server_socket.listen(100)
        thread = threading.Thread(target=self.accept_connections, daemon=True)
        thread.start()
        print(f"Peer listening on {self.ip}:{self.port}")
    
    
    def connect(self, seeds):   # Now Peer behaving as client
        #choose (n/2)+1 seeds randomly
        self.seed_list = random.sample(seeds, (len(seeds) // 2) + 1)
        # time.sleep(2)
        for seed in self.seed_list:
            self.connect_to_seed(seed)
        
        # Requesting the peer list from all connected seeds 
        self.request_peer_lists()
        # for peer in self.peer_list:
        #     print(peer)
        self.connect_to_peers()
        
        thread_ping_sender = threading.Thread(target=self.ping_sender, daemon=True)
        thread_ping_sender.start()
        
        thread_ping_receiver = threading.Thread(target=self.ping_receiver, daemon=True)
        thread_ping_receiver.start()
        
        thread_sender = threading.Thread(target=self.gossip_sender_all, daemon=True)
        thread_sender.start()
        
        thread_receiver = threading.Thread(target=self.gossip_receiver,daemon=True)
        thread_receiver.start()   
    
    
    def ping_sender(self):
        while self.running_status and not self.isDead:
            for peer_socket in self.peer_connections:
                thread = threading.Thread(target=self.ping_sender_peer, args=(peer_socket,), daemon=True)
                thread.start()
            time.sleep(PING_INTERVAL)

    
    def ping_sender_peer(self, peer_socket: socket.socket):
        if self.isDead or not self.running_status:
            return
        
        # Remove the explicit timeout setting
        if peer_socket not in self.ping_tracker:
            self.ping_tracker[peer_socket] = 0
        try:
            peer_socket.sendall("PING\n".encode('utf-8'))
            print(f"Peer(client)({self.ip}:{self.port}) -> Sent: PING to {peer_socket.getpeername()}")
            # Use select to wait for a response with a timeout
            # print("-------------------------hihihihihi--------------------")
            readable, _, _ = select.select([peer_socket], [], [], PING_MAX_WAIT)
            if readable:
                # print("-------------------------qqqqqqqqqqqqqq--------------------")
                response = peer_socket.recv(1024).decode('utf-8').strip()
                # print("-------------------------wwwwwwwwwwwwwwwwwwww--------------------")
                if response == "PONG":
                    print(f"Peer(client)({self.ip}:{self.port}) -> Received: Ping_back from {peer_socket.getpeername()}")
                    self.ping_tracker[peer_socket] = 0 
            else:
                print(f"Peer(client)({self.ip}:{self.port}) -> Ping timed out for {peer_socket.getpeername()}")
                self.ping_tracker[peer_socket] += 1
                if self.ping_tracker[peer_socket] >= 3:
                    print(f"Peer(client)({self.ip}:{self.port}) -> Peer {peer_socket.getpeername()} is dead")
                    
                    if peer_socket in self.peer_connections:
                        self.peer_connections.remove(peer_socket)
                    if peer_socket.getpeername() in self.peer_list:
                        self.peer_list.remove(peer_socket.getpeername())
                    for seed_socket in self.seed_connections:
                        dead_msg = f"DEAD_NODE:{peer_socket.getpeername()[0]}:{peer_socket.getpeername()[1]}:{time.strftime('%H:%M:%S')}:{self.ip}:{self.port}\n"
                        seed_socket.sendall(dead_msg.encode('utf-8'))
                    #peer_socket.close()  #commenting this to prevent the peer from closing the connection
        except Exception as e:
            if not self.running_status:
                return
            try:
                peer_name = peer_socket.getpeername()
            except Exception:
                peer_name = "Unknown"
            print(f"Peer(client)({self.ip}:{self.port}) -> Error sending pong to {peer_name}: {e}")
            
    def ping_receiver(self):
        while self.running_status and not self.isDead:
            for seed_socket in self.seed_connections:
                try:
                    data = seed_socket.recv(1024).decode('utf-8')
                    if not data:
                        continue
                    
                    messages = data.split("\n")
                    for msg in messages:
                        if msg.strip()=="":
                            continue
                        if msg.startswith("PING"):
                            seed_socket.sendall("PONG\n".encode('utf-8'))
                            print(f"Peer(client)({self.ip}:{self.port}) -> Received: PING from {seed_socket.getpeername()}")
                    # if data.startswith("PING"):
                    #     seed_socket.sendall("PONG".encode('utf-8'))
                    #     print(f"Peer(client)({self.ip}:{self.port}) -> Received: PING from {seed_socket.getpeername()}")
                    # else:
                    #     continue
                except Exception as e:
                    if not self.running_status:
                        return
                    try:
                        seed_name = seed_socket.getpeername()
                    except Exception:
                        seed_name = "Unknown"
                    
                        print(f"Peer(client)({self.ip}:{self.port}) -> Error receiving data from {seed_name}: {e}")
                    
    
    def gossip_sender_all(self):
        for i in range(NUM_MESSAGES):
            if not self.running_status or self.isDead:
                break
            message = f"{time.strftime('%H:%M:%S')}:{self.ip}:{self.port}:m"
            message_hash = hash(message)
            self.message_hashes.add(message_hash)
            for peer in self.peer_connections:
                thread = threading.Thread(target=self.gossip_sender_peer, args=(peer,message_hash), daemon=True)
                thread.start()
            time.sleep(GOSSIP_SEND_INTERVAL)
        
    # Modify gossip_receiver to handle multiple or concatenated messages
    def gossip_receiver(self):
        buffer = ""
        while self.running_status and not self.isDead:
            try:
                for peer in self.peer_connections:
                    data = peer.recv(1024)
                    if not data:
                        continue
                    buffer += data.decode('utf-8')
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        if line:
                            print(f"Peer(server)({self.ip}:{self.port}) -> Received: {line}")
                            if line.startswith("GOSSIP:"):
                                try:
                                    message_hash = int(line.split("GOSSIP:")[1])
                                except ValueError:
                                    print(f"Failed to parse message hash from: {line}")
                                    break
                                if message_hash not in self.message_hashes:
                                    self.message_hashes.add(message_hash)
                                    for peer_socket in self.peer_connections:
                                        if peer_socket != peer:
                                            thread = threading.Thread(target=self.gossip_sender_peer, args=(peer_socket, message_hash), daemon=True)
                                            thread.start()
            except Exception as e:
                if self.running_status:
                    print(f"Peer(server)({self.ip}:{self.port}) -> Error handling peer connection: {e}")
                break  

    
    
    def gossip_sender_peer(self, peer: socket.socket, message_hash: int):
        try:
            peer.sendall(f"GOSSIP:{message_hash}\n".encode('utf-8'))                      # Adding GOSSIP to the hash message
            print(f"Peer(server)({self.ip}:{self.port}) -> Sent: GOSSIP:{message_hash}")
        except Exception as e:
            if self.running_status:
                print(f"Peer(server)({self.ip}:{self.port}) -> Error sending gossip to peer: {e}")
            
    def accept_connections(self):
        while self.running_status and not self.isDead:
            try:
                connection, address = self.server_socket.accept()
                print(f"Peer(server)({self.ip}:{self.port}) -> New connection from {address[0]}:{address[1]}")
                self.peer_connections.append(connection)
                
                # thread = threading.Thread(target=self.handle_peer_connection, args=(connection, address), daemon=True)
                # thread.start()
                
            except Exception as e:
                if self.running_status:
                    print(f"Peer(server)({self.ip}:{self.port}) -> Error accepting connection: {e}")
                break
            
            
    
        
            
    def connect_to_seed(self, seed):    # Now Peer behaving as client
        try:
            seed_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)     # No need to bind to any port or ip it is in built handled by os
            seed_socket.connect((seed[0] , seed[1]))
            
            #sending the server port of peer to seed
            seed_socket.sendall(f"PEER_SERVER:{self.port}\n".encode('utf-8'))
            self.seed_connections.append(seed_socket)
            print(f"Peer(client)({self.ip}:{self.port}) -> Connected to {seed[0]}:{seed[1]}")
        except socket.error as e:
            print(f"Peer(client)({self.ip}:{self.port}) -> Failed to connect to seed {seed[0]}:{seed[1]}. Error:{e}")


    def request_peer_lists(self):
                
        for seed_socket in self.seed_connections:
            try:
                # print("hi 5")
                # seed_socket.sendall(b"REQUEST_PEER_LIST")
                seed_socket.sendall(f"REQUEST_PEER_LIST:{self.port}\n".encode('utf-8'))
                # print("hi 6")
                peer_list_str = seed_socket.recv(1024).decode('utf-8')
                # peer_list_str = peer_list_str.decode('utf-8')
                # print("hi 7")
                
                # Split the received string into individual peer entries
                if peer_list_str:
                    peers = peer_list_str.split('\n')
                    for peer in peers:
                        if peer:
                            ip, port = peer.split(':')
                            self.peer_list.append((ip, int(port)))
                          
            except Exception as e:
                print(f"Peer(client)({self.ip}:{self.port}) -> Error requesting peer list from {seed_socket.getpeername()}: {e}")
        

    def connect_to_peers(self):     # Acting as client
        
        for peer in set(self.peer_list):
            try:
                if peer[0] == self.ip and peer[1] == self.port:
                    continue
                peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                print(peer[0],"  ", peer[1])
                peer_socket.connect((peer[0], peer[1]))
                print("p1")
                self.peer_connections.append(peer_socket)
                
                self.ping_tracker[peer_socket]=0
                print(f"Peer(client)({self.ip}:{self.port}) -> Connected to peer {peer[0]}:{peer[1]}")
                # peer_socket.sendall("Hello from Peer(client)".encode('utf-8'))
                
            except socket.error as e:
                print(f"Peer(client)({self.ip}:{self.port}) -> Failed to connect to peer {peer[0]}:{peer[1]}. Error:{e}")

    def close(self):
        self.running_status = False
        if self.server_socket:
            try:
                self.server_socket.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            self.server_socket.close()
            print(f"Peer on {self.ip}:{self.port} closed.")

        for conn in self.seed_connections:
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                conn.close()
            except Exception as e:
                print(f"Error closing a peer to seed connection: {e}")

        for conn in self.peer_connections:
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                conn.close()
            except Exception as e:
                print(f"Error closing a peer to peer connection: {e}")

