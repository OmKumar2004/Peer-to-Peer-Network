import random
import socket
import threading
import time

class Peers:
    def __init__(self,ip,port):
        self.ip = ip
        self.port = int(port)
        self.seed_list = []
        self.connections = []
        self.server_socket = None

    def connect(self, seeds):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.ip, int(self.port)))
        self.server_socket.listen(5)
        thread = threading.Thread(target=self.accept_connections, daemon=True)
        thread.start()
        print(f"Peer listening on {self.ip}:{self.port}")

        #choose (n/2)+1 seeds randomly
        chosen_seeds = random.sample(seeds, (len(seeds) // 2) + 1)
        self.seed_list = chosen_seeds
        
        time.sleep(1)
        
        for seed in chosen_seeds:
            self.connect_to_seed(seed)
        # for seed in self.seed_list:
        #     print(seed.ip, "   " ,seed.port)
        # print("----")


    def accept_connections(self):
        while True:
            try:
                client_socket, address = self.server_socket.accept()
                print(f"New connection from {address[0]}:{address[1]}")
                # You might want to start a new thread to handle communication with this peer
            except Exception as e:
                print(f"Error accepting connection: {e}")
                break
            
            
    def connect_to_seed(self, seed):
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # client_socket.bind((self.ip, self.port))
            client_socket.connect((str(seed.ip) , int(seed.port)))
            print("connection: ", type(client_socket))
            self.connections.append(client_socket)
            print(f"Connected to {seed.ip}:{seed.port}")
        except socket.error as e:
            print(f"Failed to connect to {seed.ip}:{seed.port}. Error:{e}")

    def close(self):
        if self.server_socket:
            self.server_socket.close()
            print(f"Peer on {self.ip}:{self.port} closed.")
        for conn in self.connections:
            try:
                conn.close()
            except Exception as e:
                print(f"Error closing a connection: {e}")


