import socket
import threading
import os
from typing import List

class Seeds:
    def __init__(self, ip, port):
        # While playing role of server
        self.ip = ip
        self.port = int(port)
        self.server_socket = None
        self.seed_sockets: List[socket.socket] = []
        self.peer_list = []
        self.running_status = True


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
        while self.running_status:
            try:
                connection, address = self.server_socket.accept()           # Accepting all incoming connections
                print(f"Seed({self.ip}:{self.port}) -> New connection from {address[0]}:{address[1]}")
                # self.peer_list.append((address[0],address[1]))
                #handling the connection in a different thread
                thread = threading.Thread(target=self.handle_peer_connection,args=(connection,address),daemon=True)
                thread.start()

            except Exception as e:
                if self.running_status:
                    print(f"Seed({self.ip}:{self.port}) -> Error accepting connection: {e}")
                break
    
    #handles the new peer connection
    def handle_peer_connection(self, connection: socket.socket, address):
        buffer = ""
        while self.running_status:
            try:
                data = connection.recv(1024)
                if not data:
                    break
                buffer += data.decode('utf-8')
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if not line:
                        continue
                    if line.startswith("PEER_SERVER:"):
                        try:
                            server_port = int(line.split(":")[1])
                        except ValueError:
                            continue
                        self.peer_list.append((address[0], server_port))
                        self.seed_sockets.append(connection)
                    elif line.startswith("REQUEST_PEER_LIST"):
                        peer_list_str = '\n'.join([f"{ip}:{port}" for ip, port in self.peer_list]) + "\n"
                        connection.sendall(peer_list_str.encode('utf-8'))
                    elif line.startswith("DEAD_NODE:"):
                        parts = line.split(":")
                        if len(parts) >= 3:
                            dead_ip = parts[1]
                            try:
                                dead_port = int(parts[2])
                            except ValueError:
                                print(f"Invalid dead port in message: {line}")
                                continue
                            try:
                                self.peer_list.remove((dead_ip, dead_port))
                                self.seed_sockets.remove(connection)
                                connection.close()
                            except ValueError:
                                pass
                                print(f"Peer {dead_ip}:{dead_port} not found in peer list.")
                            print(f"Seed({self.ip}:{self.port}) -> Peer {dead_ip}:{dead_port} marked as dead.")
                    else:
                        continue
            except Exception as e:
                if self.running_status:
                    print(f"Seed({self.ip}:{self.port}) -> Error handling peer connection: {e}")
                break
        connection.close()
    
                    
    def close(self):
        self.running_status = False
        if self.server_socket:
            try:
                self.server_socket.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            self.server_socket.close()
            print(f"Seed server on {self.ip}:{self.port} closed.")

        for conn in self.seed_sockets:
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                conn.close()
            except Exception as e:
                print(f"Error closing a seed connection: {e}")


    