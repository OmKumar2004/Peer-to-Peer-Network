import random
import socket
import threading
from typing import List
import time
import select
from log_util import log_message

PING_INTERVAL = 2
PING_MAX_WAIT = 5
GOSSIP_SEND_INTERVAL = 15
NUM_MESSAGES = 10

class Peers:
    def __init__(self, ip, port):
        # While playing role of server
        self.ip = ip
        self.port = int(port)
        self.server_socket = None
        
        self.seed_list = []
        self.peer_list = []
        self.seed_connections: List[socket.socket] = []  # When acting as client (to seeds)
        self.peer_connections: List[socket.socket] = []  # Connections to other peers
        
        self.message_hashes = set()
        self.running_status = True
        self.isDead = False
        self.ping_tracker = {}  # Keeps count of consecutive missed PONGs per peer
        self.last_pong = {}     # Records the time when the last PONG was received for each peer
    
    def creation(self):
        # Activate as a server
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.ip, self.port))
        self.server_socket.listen()
        print(f"Peer listening on {self.ip}:{self.port}")
        thread = threading.Thread(target=self.accept_connections, daemon=True)
        thread.start()
    
    def connect(self, seeds):
        # Choose (n/2)+1 seeds randomly
        self.seed_list = random.sample(seeds, (len(seeds) // 2) + 1)
        for seed in self.seed_list:
            self.connect_to_seed(seed)
        
        # Request the peer list from all connected seeds 
        self.request_peer_lists()
        self.connect_to_peers()
        
        # Start the thread that sends periodic PINGs
        thread_ping_sender = threading.Thread(target=self.ping_sender, daemon=True)
        thread_ping_sender.start()
        
        # Start a monitor thread that checks for missed PONG replies
        thread_ping_monitor = threading.Thread(target=self.ping_monitor, daemon=True)
        thread_ping_monitor.start()
        
        # Start a single receiver thread that processes all incoming messages from peers
        thread_receiver = threading.Thread(target=self.gossip_receiver, daemon=True)
        thread_receiver.start()
        
        # Start the gossip sender thread
        thread_sender = threading.Thread(target=self.gossip_sender_all, daemon=True)
        thread_sender.start()
    
    def ping_sender(self):
        """Sends a PING message to every connected peer periodically."""
        while self.running_status and not self.isDead:
            for peer_socket in list(self.peer_connections):
                try:
                    peer_socket.sendall("PING\n".encode('utf-8'))
                    print(f"Peer(client)({self.ip}:{self.port}) -> Sent: PING to {peer_socket.getpeername()}")
                    log_message(f"Peer(client)({self.ip}:{self.port}) -> Sent: PING to {peer_socket.getpeername()}")
                except Exception as e:
                    try:
                        peer_name = peer_socket.getpeername()
                    except Exception:
                        peer_name = "Unknown"
                    print(f"Peer(client)({self.ip}:{self.port}) -> Error sending PING to {peer_name}: {e}")
            time.sleep(PING_INTERVAL)
    
    def ping_monitor(self):
        """
        Checks each peer’s last PONG timestamp.
        If no PONG is received within PING_MAX_WAIT seconds, increments a counter.
        After 3 missed PONGs, the peer is marked as dead.
        """
        while self.running_status and not self.isDead:
            current_time = time.time()
            for peer in list(self.peer_connections):
                last = self.last_pong.get(peer, current_time)
                if current_time - last > PING_MAX_WAIT:
                    self.ping_tracker[peer] = self.ping_tracker.get(peer, 0) + 1
                    print(f"Peer(client)({self.ip}:{self.port}) -> No PONG from {peer.getpeername()} in {PING_MAX_WAIT} sec, count={self.ping_tracker[peer]}")
                    if self.ping_tracker[peer] >= 3:
                        print(f"Peer(client)({self.ip}:{self.port}) -> Peer {peer.getpeername()} is marked as dead")
                        log_message(f"Peer(client)({self.ip}:{self.port}) -> Peer {peer.getpeername()} is marked as dead")
                        self.peer_connections.remove(peer)
                        if peer.getpeername() in self.peer_list:
                            self.peer_list.remove(peer.getpeername())
                        for seed_socket in self.seed_connections:
                            dead_msg = f"DEAD_NODE:{peer.getpeername()[0]}:{peer.getpeername()[1]}:{time.strftime('%H:%M:%S')}:{self.ip}:{self.port}\n"
                            try:
                                seed_socket.sendall(dead_msg.encode('utf-8'))
                                log_message(f"Peer(client)({self.ip}:{self.port}) -> Sent dead message to seed")
                            except Exception as e:
                                print(f"Error sending dead message to seed: {e}")
                else:
                    # Reset the counter if a recent PONG was received
                    self.ping_tracker[peer] = 0
            time.sleep(1)
    
    def gossip_sender_all(self):
        """Periodically sends a gossip message to all peers."""
        for i in range(NUM_MESSAGES):
            if not self.running_status or self.isDead:
                break
            message = f"{time.strftime('%H:%M:%S')}:{self.ip}:{self.port}:m"
            message_hash = hash(message)
            self.message_hashes.add(message_hash)
            for peer in list(self.peer_connections):
                threading.Thread(target=self.gossip_sender_peer, args=(peer, message_hash), daemon=True).start()
            time.sleep(GOSSIP_SEND_INTERVAL)
    
    def gossip_receiver(self):
        """
        Uses select() to wait for data on any peer socket.
        Processes incoming messages:
          - Replies to PINGs with a PONG.
          - When a PONG is received, updates the last_pong timestamp.
          - For GOSSIP messages, forwards them if not already seen.
        """
        while self.running_status and not self.isDead:
            if not self.peer_connections:
                time.sleep(0.5)
                continue
            try:
                readable, _, _ = select.select(self.peer_connections, [], [], 1)
                for peer in readable:
                    try:
                        data = peer.recv(1024)
                        if not data:
                            continue
                        buffer = data.decode('utf-8')
                        for line in buffer.split("\n"):
                            line = line.strip()
                            if not line:
                                continue
                            if line == "PING":
                                peer.sendall("PONG\n".encode('utf-8'))
                                print(f"Peer(server)({self.ip}:{self.port}) -> Received: PING from {peer.getpeername()}, sent: PONG")
                                log_message
                            elif line == "PONG":
                                print(f"Peer(server)({self.ip}:{self.port}) -> Received: PONG from {peer.getpeername()}")
                                self.ping_tracker[peer] = 0
                                self.last_pong[peer] = time.time()
                            elif line.startswith("GOSSIP:"):
                                try:
                                    message_hash = int(line.split("GOSSIP:")[1])
                                except ValueError:
                                    print(f"Failed to parse message hash from: {line}")
                                    continue
                                if message_hash not in self.message_hashes:
                                    self.message_hashes.add(message_hash)
                                    for peer_socket in self.peer_connections:
                                        if peer_socket != peer:
                                            threading.Thread(target=self.gossip_sender_peer, args=(peer_socket, message_hash), daemon=True).start()
                            # Handle other message types here if needed
                    except Exception as e:
                        print(f"Peer(server)({self.ip}:{self.port}) -> Error receiving from {peer}: {e}")
            except Exception as e:
                if self.running_status:
                    print(f"Peer(server)({self.ip}:{self.port}) -> Error in select: {e}")
    
    def gossip_sender_peer(self, peer: socket.socket, message_hash: int):
        try:
            peer.sendall(f"GOSSIP:{message_hash}\n".encode('utf-8'))
            print(f"Peer(server)({self.ip}:{self.port}) -> Sent: GOSSIP:{message_hash} to {peer.getpeername()}")
            log_message(f"Peer(server)({self.ip}:{self.port}) -> Sent: GOSSIP:{message_hash} to {peer.getpeername()}")
        except Exception as e:
            if self.running_status:
                print(f"Peer(server)({self.ip}:{self.port}) -> Error sending gossip to peer: {e}")
            
    def accept_connections(self):
        while self.running_status and not self.isDead:
            try:
                connection, address = self.server_socket.accept()
                print(f"Peer(server)({self.ip}:{self.port}) -> New connection from {address[0]}:{address[1]}")
                self.peer_connections.append(connection)
                # Initialize tracking for the new connection
                self.ping_tracker[connection] = 0
                self.last_pong[connection] = time.time()
            except Exception as e:
                if self.running_status:
                    print(f"Peer(server)({self.ip}:{self.port}) -> Error accepting connection: {e}")
                break
            
    def connect_to_seed(self, seed):
        try:
            seed_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            seed_socket.connect((seed[0], seed[1]))
            print(f"Peer(client)({self.ip}:{self.port}) -> Connected to {seed[0]}:{seed[1]}")
            seed_socket.sendall(f"PEER_SERVER:{self.port}\n".encode('utf-8'))
            log_message(f"Peer(client)({self.ip}:{self.port}) -> Sent PEER_SERVER message to seed")
            self.seed_connections.append(seed_socket)
        except socket.error as e:
            print(f"Peer(client)({self.ip}:{self.port}) -> Failed to connect to seed {seed[0]}:{seed[1]}. Error: {e}")
    
    def request_peer_lists(self):
        for seed_socket in self.seed_connections:
            try:
                seed_socket.sendall(f"REQUEST_PEER_LIST:{self.port}\n".encode('utf-8'))
                log_message(f"Peer(client)({self.ip}:{self.port}) -> Sent REQUEST_PEER_LIST message to seed")
                peer_list_str = seed_socket.recv(1024).decode('utf-8')
                if peer_list_str:
                    peers = peer_list_str.split('\n')
                    for peer in peers:
                        if peer:
                            ip, port = peer.split(':')
                            self.peer_list.append((ip, int(port)))
            except Exception as e:
                print(f"Peer(client)({self.ip}:{self.port}) -> Error requesting peer list from {seed_socket.getpeername()}: {e}")
        
    def connect_to_peers(self):
        for peer in set(self.peer_list):
            try:
                if peer[0] == self.ip and peer[1] == self.port:
                    continue
                peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                peer_socket.connect((peer[0], peer[1]))
                self.peer_connections.append(peer_socket)
                self.ping_tracker[peer_socket] = 0
                self.last_pong[peer_socket] = time.time()
                print(f"Peer(client)({self.ip}:{self.port}) -> Connected to peer {peer[0]}:{peer[1]}")
            except socket.error as e:
                print(f"Peer(client)({self.ip}:{self.port}) -> Failed to connect to peer {peer[0]}:{peer[1]}. Error: {e}")
    
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
                print(f"Error closing a seed connection: {e}")
    
        for conn in self.peer_connections:
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                conn.close()
            except Exception as e:
                print(f"Error closing a peer-to-peer connection: {e}")
