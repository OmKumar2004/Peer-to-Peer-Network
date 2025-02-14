import socket
import threading
import os

class Seeds:
    def __init__(self, ip, port):
        # While playing role of server
        self.ip = ip
        self.port = int(port)
        self.server_socket = None
        
        self.peer_list = []
        


    def creation(self):  # activate (fulfiling it as server)
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #creating a TCP/IP socket
        try:
            self.server_socket.bind((self.ip, self.port))
            self.server_socket.listen(100)
            thread = threading.Thread(target=self.accept_connections, daemon=True)
            thread.start()
            print(f"Process ID (PID): {os.getpid()}, Thread ID: {thread.ident}")
            print(f"Seed activated: Listening on {self.ip}:{self.port}")
        except socket.error as e:
            print(f"Failed to activate seed on {self.ip}:{self.port}. Error: {e}")

    #runs in background to acceps incoming connections
    def accept_connections(self):
        while True:
            try:
                connection, address = self.server_socket.accept()           # Accepting all incoming connections
                print(f"Seed({self.ip}:{self.port}) -> New connection from {address[0]}:{address[1]}")
                # self.peer_list.append((address[0],address[1]))
                #handling the connection in a different thread
                thread = threading.Thread(target=self.handle_peer_connection,args=(connection,address),daemon=True)
                thread.start()

            except Exception as e:
                print(f"Seed({self.ip}:{self.port}) -> Error accepting connection: {e}")
                break
    
    #handles the new peer connection
    def handle_peer_connection(self,connection: socket.socket,address):
        while True:
            try:
                data = connection.recv(1024)
                if not data:
                    break
                
                message = data.decode('utf-8')
                  
                if message.startswith("PEER_SERVER:"):
                    server_port = int(message.split(":")[1])
                    self.peer_list.append((address[0], server_port))
                elif data == b"REQUEST_PEER_LIST":
                    peer_list_str = '\n'.join([f"{ip}:{port}" for ip, port in self.peer_list])
                    connection.sendall(peer_list_str.encode('utf-8'))

            except Exception as e:
                print(f"Seed({self.ip}:{self.port}) -> Error handling peer connection: {e}")
                break
        connection.close()
            
    
    # def new_peer_registration(self, ip, port):  # registering new peers
    #     return ip, port

    # def remove_dead_peer(self, msg_dead):  # removing dead peers
    #     pass

    def close(self):
        if self.server_socket:
            self.server_socket.close()
            print(f"Seed server on {self.ip}:{self.port} closed.")


    