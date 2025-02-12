import socket

class Seeds:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.peer_list = []
        self.server_socket = None

    def creation(self):  # activate it
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind((self.ip, int(self.port)))
            s.listen(5)  # 5 is the maximum number of queued connections
            self.server_socket = s
            print(f"Seed activated: Listening on {self.ip}:{self.port}")
        except socket.error as e:
            print(f"Failed to activate seed on {self.ip}:{self.port}. Error: {e}")

    def new_peer_registration(self, ip, port):  # registering new peers
        return ip, port

    def remove_dead_peer(self, msg_dead):  # removing dead peers
        pass

    def close(self):
        if self.server_socket:
            self.server_socket.close()
            print(f"Seed server on {self.ip}:{self.port} closed.")

if __name__ == "__main__":
    pass