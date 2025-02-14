import socket
import threading
import os

class Seeds:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = int(port)
        self.peer_list = []
        self.server_socket = None
        


    def creation(self):  # activate it
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #creating a TCP/IP socket
        try:
            s.bind((self.ip, self.port))
            s.listen(5)  # 5 is the maximum number of queued connections
            self.server_socket = s
            thread = threading.Thread(target=self.accept_connections, daemon=True)
            thread.start()
            print(f"Process ID (PID): {os.getpid()}, Thread ID: {thread.ident}")
            print(f"Seed activated: Listening on {self.ip}:{self.port}")
        except socket.error as e:
            print(f"Failed to activate seed on {self.ip}:{self.port}. Error: {e}")

    #runs in background to acceps incomiing connections
    def accept_connections(self):
        while True:
            try:
                client_socket, address = self.server_socket.accept() #waiting for new connections
                print(f"New connection from {address[0]}:{address[1]}")
                #handling the connection in a different thread
                thread = threading.Thread(target=self.handle_peer_connection,args=(client_socket,address),daemon=True)
                # self.peer_list.append((address[0], address[1]))
            except Exception as e:
                print(f"Error accepting connection: {e}")
                break
    
    #handles the new peer connection
    def handle_peer_connection(self,client_socket,address):
        pass
            
    
    # def new_peer_registration(self, ip, port):  # registering new peers
    #     return ip, port

    # def remove_dead_peer(self, msg_dead):  # removing dead peers
    #     pass

    def close(self):
        if self.server_socket:
            self.server_socket.close()
            print(f"Seed server on {self.ip}:{self.port} closed.")

if __name__ == "__main__":
    #to test the code 
    seed = Seeds("127.0.0.1",8000)
    seed.creation();
    seed.close()
    