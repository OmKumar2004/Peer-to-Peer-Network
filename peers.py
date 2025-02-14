import random
import socket
import threading
import time

class Peers:
    def __init__(self,ip,port):
        # While playing role of server
        self.ip = ip
        self.port = int(port)
        self.server_socket = None
        
        self.seed_list = []
        self.peer_list = []
        self.seed_connections = []       # List of sockets of connections when it is behaving as client
        self.peer_connections = []
        
    def creation(self):  # activate (fulfiling it as server)
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.ip, self.port))
        self.server_socket.listen() 
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
        self.connect_to_peers()
        

    
    def accept_connections(self):
        while True:
            try:
                connection, address = self.server_socket.accept()
                print(f"Peer(server)({self.ip}:{self.port}) -> New connection from {address[0]}:{address[1]}")
                thread = threading.Thread(target=self.handle_peer_connection, args=(connection, address), daemon=True)
                thread.start()
                
            except Exception as e:
                print(f"Peer(server)({self.ip}:{self.port}) -> Error accepting connection: {e}")
                break
            
            
    def handle_peer_connection(self, connection, address):
        while True:
            try:
                data = connection.recv(1024)
                if not data:
                    break
                print(f"Peer(server)({self.ip}:{self.port}) -> Received data from {address[0]}:{address[1]}: {data}")        #L Will now handle the data  
                # self.peer_list.append((address[0], address[1]))
                # print(self.peer_list)
                # self.send_peer_list(connection)
                # self.send_peer_list(connection)
            except Exception as e:
                print(f"Peer(server)({self.ip}:{self.port}) -> Error handling peer connection: {e}")
                break
        connection.close()
        
            
    def connect_to_seed(self, seed):    # Now Peer behaving as client
        try:
            seed_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)     # No need to bind to any port or ip it is in built handled by os
            seed_socket.connect((str(seed.ip) , int(seed.port)))
            self.seed_connections.append(seed_socket)
            print(f"Peer(client)({self.ip}:{self.port}) -> Connected to {seed.ip}:{seed.port}")
        except socket.error as e:
            print(f"Peer(client)({self.ip}:{self.port}) -> Failed to connect to {seed.ip}:{seed.port}. Error:{e}")


    def request_peer_lists(self):
        self.peer_list = []
        for seed_socket in self.seed_connections:
            try:
                seed_socket.send(b"REQUEST_PEER_LIST")
                peer_list_str = seed_socket.recv(1024)
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
        for peer in self.peer_list:
            try:
                peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                peer_socket.connect((peer[0], peer[1]))
                self.peer_connections.append(peer_socket)
                print(f"Peer(client)({self.ip}:{self.port}) -> Connected to {peer[0]}:{peer[1]}")
                peer_socket.sendall(b"Hello from Peer(client)")
                
            except socket.error as e:
                print(f"Peer(client)({self.ip}:{self.port}) -> Failed to connect to {peer[0]}:{peer[1]}. Error:{e}")

    def close(self):
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


