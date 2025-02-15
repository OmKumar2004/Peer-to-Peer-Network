import random
import socket
import threading
from typing import List
import time

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
        
        print("hi there")
        # Requesting the peer list from all connected seeds 
        self.request_peer_lists()
        print("hi 2")
        for peer in self.peer_list:
            print(peer)
        print("hi 3")
        self.connect_to_peers()
        print("hi 4")
        thread_sender = threading.Thread(target=self.gossip_sender_all, daemon=True)
        thread_sender.start()
        
        thread_receiver = threading.Thread(target=self.gossip_receiver,daemon=True)
        thread_receiver.start()   
        
    # Modify gossip_receiver to handle multiple or concatenated messages
    def gossip_receiver(self):
        buffer = ""
        while self.running_status:
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
                                    continue
                                if message_hash not in self.message_hashes:
                                    self.message_hashes.add(message_hash)
                                    for peer_socket in self.peer_connections:
                                        if peer_socket != peer:
                                            thread = threading.Thread(target=self.gossip_sender_peer, args=(peer_socket, message_hash), daemon=True)
                                            thread.start()
            except Exception as e:
                print(f"Peer(server)({self.ip}:{self.port}) -> Error handling peer connection: {e}")
                break  

    def gossip_sender_all(self):
        for i in range(10):
            if not self.running_status:
                break
            message = f"{time.strftime("%H:%M:%S")}:{self.ip}:{self.port}:m"
            message_hash = hash(message)
            self.message_hashes.add(message_hash)
            for peer in self.peer_connections:
                thread = threading.Thread(target=self.gossip_sender_peer, args=(peer,message_hash), daemon=True)
                thread.start()
            time.sleep(30)
    
    def gossip_sender_peer(self, peer: socket.socket, message_hash: int):
        try:
            peer.sendall(f"GOSSIP:{message_hash}\n".encode('utf-8'))                      # Adding GOSSIP to the hash message
            print(f"Peer(server)({self.ip}:{self.port}) -> Sent: GOSSIP:{message_hash}")
        except Exception as e:
            print(f"Peer(server)({self.ip}:{self.port}) -> Error sending gossip to peer: {e}")
            
    def accept_connections(self):
        while self.running_status:
            try:
                connection, address = self.server_socket.accept()
                print(f"Peer(server)({self.ip}:{self.port}) -> New connection from {address[0]}:{address[1]}")
                self.peer_connections.append(connection)
                
                # thread = threading.Thread(target=self.handle_peer_connection, args=(connection, address), daemon=True)
                # thread.start()
                
            except Exception as e:
                print(f"Peer(server)({self.ip}:{self.port}) -> Error accepting connection: {e}")
                break
            
            
    
        
            
    def connect_to_seed(self, seed):    # Now Peer behaving as client
        try:
            seed_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)     # No need to bind to any port or ip it is in built handled by os
            seed_socket.connect((str(seed.ip) , int(seed.port)))
            
            #sending the server port of peer to seed
            seed_socket.sendall(f"PEER_SERVER:{self.port}".encode('utf-8'))
            self.seed_connections.append(seed_socket)
            print(f"Peer(client)({self.ip}:{self.port}) -> Connected to {seed.ip}:{seed.port}")
        except socket.error as e:
            print(f"Peer(client)({self.ip}:{self.port}) -> Failed to connect to {seed.ip}:{seed.port}. Error:{e}")


    def request_peer_lists(self):
                
        for seed_socket in self.seed_connections:
            try:
                # print("hi 5")
                # seed_socket.sendall(b"REQUEST_PEER_LIST")
                seed_socket.sendall(f"REQUEST_PEER_LIST:{self.port}".encode('utf-8'))
                # print("hi 6")
                peer_list_str = seed_socket.recv(1024)
                peer_list_str = peer_list_str.decode('utf-8')
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
                peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                print(peer[0],"  ", peer[1])
                peer_socket.connect((peer[0], peer[1]))
                print("p1")
                self.peer_connections.append(peer_socket)
                print(f"Peer(client)({self.ip}:{self.port}) -> Connected to peer {peer[0]}:{peer[1]}")
                # peer_socket.sendall("Hello from Peer(client)".encode('utf-8'))
                
            except socket.error as e:
                print(f"Peer(client)({self.ip}:{self.port}) -> Failed to connect to peer {peer[0]}:{peer[1]}. Error:{e}")

    def close(self):
        self.running_status = False
        if self.server_socket:
            self.server_socket.close()
            print(f"Peer on {self.ip}:{self.port} closed.")
            
        for conn in self.seed_connections:
            try:
                conn.close()
            except Exception as e:
                print(f"Error closing a peer to seed connection: {e}")
        for conn in self.peer_connections:
            try:
                conn.close()
            except Exception as e:
                print(f"Error closing a peer to peer connection: {e}")


