import random
import socket
import threading
import time

class Peers:
    def __init__(self,ip,port):
        self.ip = ip
        self.port = port
        self.seed_list = []
        self.connections = []
        self.server_socket = None

    def connect(self, seeds):
        #choose (n/2)+1 seeds randomly
        chosen_seeds = random.sample(seeds, (len(seeds) // 2) + 1)
        self.seed_list = chosen_seeds

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.ip, int(self.port)))
        self.server_socket.listen(5)
        print(f"Peer listening on {self.ip}:{self.port}")

        for seed in chosen_seeds:
            self.connect_to_seed(seed)
        # for seed in self.seed_list:
        #     print(seed.ip, "   " ,seed.port)
        # print("----")

    def connect_to_seed(self, seed):
        try:
            connection = self.server_socket.connect((seed.ip , int(seed.port)))
            print("connection: ", type(connection))
            self.connections.append(connection)
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


