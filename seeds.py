import socket
import threading
from typing import List
from log import log


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Connecting to an external host to get the ip address
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


class Seeds:
    def __init__(self, ip=None, port=0):
        # If no IP is provided, determine the machine's local IP dynamically.
        if ip is None:
            self.ip = get_local_ip()
        else:
            self.ip = ip
        self.port = int(port)
        self.server_socket = None
        self.seed_sockets: List[socket.socket] = []
        self.peer_list = []  # List of tuples: (ip, port, degree)
        self.running_status = True

    def creation(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Enable immediate reuse of the address
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server_socket.bind((self.ip, self.port))
            # If port was set to 0, update self.port with the assigned port.
            if self.port == 0:
                self.port = self.server_socket.getsockname()[1]
            self.server_socket.listen(100)
            msg = f"Seed activated: Listening on {self.ip}:{self.port}"
            print(msg)
            log(msg)
            thread = threading.Thread(target=self.accept_connections, daemon=True)
            thread.start()
            return 1
        except socket.error as e:
            err_msg = f"Failed to activate seed on {self.ip}:{self.port}. Error: {e}"
            print(err_msg)
            # log(err_msg)
            return 0

    def accept_connections(self):
        while self.running_status:
            try:
                connection, address = self.server_socket.accept()
                msg = f"Seed({self.ip}:{self.port}) -> New connection from {address[0]}:{address[1]}"
                print(msg)
                log(msg)
                thread = threading.Thread(target=self.handle_peer_connection, args=(connection, address), daemon=True)
                thread.start()
            except Exception as e:
                if self.running_status:
                    err_msg = f"Seed({self.ip}:{self.port}) -> Error accepting connection: {e}"
                    print(err_msg)
                    # log(err_msg)
                break

    def handle_peer_connection(self, connection: socket.socket, address):
        buffer = ""
        while self.running_status:
            try:
                data = connection.recv(1024)
                if not data:
                    buffer = ""
                    continue
                buffer += data.decode('utf-8')
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if not line:
                        continue
                    # Handle different message types
                    if line.startswith("PEER_SERVER:"):
                        try:
                            server_port = int(line.split(":")[1])
                        except ValueError:
                            continue
                        # Add the new peer with an initial degree of 1 
                        peer_entry = (address[0], server_port, 1)
                        if not any(p[0] == address[0] and p[1] == server_port for p in self.peer_list):
                            self.peer_list.append(peer_entry)
                        msg = f"Seed({self.ip}:{self.port}) -> Peer {address[0]}:{server_port} appended to peer list with degree 1"
                        print(msg)
                        log(msg)
                        if connection not in self.seed_sockets:
                            self.seed_sockets.append(connection)
                    if line.startswith("REQUEST_PEER_LIST:"):
                        # Send the peer list with updated degree info
                        peer_list_str = '\n'.join([f"{ip}:{port}:{degree}" for ip, port, degree in self.peer_list]) + "\n"
                        connection.sendall(peer_list_str.encode('utf-8'))
                    if line.startswith("DEAD_NODE:"):
                        parts = line.split(":")
                        if len(parts) >= 3:
                            dead_ip = parts[1]
                            try:
                                dead_port = int(parts[2])
                            except ValueError:
                                err_msg = f"Invalid dead port in message: {line}"
                                print(err_msg)
                                log(err_msg)
                                continue
                            # Remove the peer from the list
                            before_count = len(self.peer_list)
                            self.peer_list = [p for p in self.peer_list if not (p[0] == dead_ip and p[1] == dead_port)]
                            after_count = len(self.peer_list)
                            if before_count != after_count:
                                msg = f"Seed({self.ip}:{self.port}) -> Peer {dead_ip}:{dead_port} marked as dead and removed from peer list."
                                print(msg)
                                log(msg)
                            else:
                                msg = f"Seed({self.ip}:{self.port}) -> Peer {dead_ip}:{dead_port} not found in peer list."
                                print(msg)
                                log(msg)
                    if line.startswith("CONNECTION_UPDATE:"):
                        parts = line.split(":", 4)
                        if len(parts) < 4:
                            continue
                        new_ip = parts[1]
                        try:
                            new_port = int(parts[2])
                            new_degree = int(parts[3])
                        except ValueError:
                            continue
                        connected_peers_str = parts[4] if len(parts) == 5 else ""
                        # Update new peer's own entry in the peer list
                        existing = next((p for p in self.peer_list if p[0] == new_ip and p[1] == new_port), None)
                        if existing:
                            # Update degree to maximum of existing and new_degree
                            updated_degree = max(existing[2], new_degree)
                            self.peer_list = [ (p[0], p[1], updated_degree) if (p[0]==new_ip and p[1]==new_port) else p for p in self.peer_list]
                        else:
                            self.peer_list.append((new_ip, new_port, new_degree))
                        # Process the list of peers that the new peer is connected to
                        if connected_peers_str:
                            connected_peers = connected_peers_str.split(",")
                            for cp in connected_peers:
                                if cp.strip() == "":
                                    continue
                                try:
                                    cp_ip, cp_port_str = cp.split(":")
                                    cp_port = int(cp_port_str)
                                except ValueError:
                                    continue
                                # Find if this connected peer exists; if yes, increment its degree by 1, else add it with degree 1
                                found = False
                                for p in self.peer_list:
                                    if p[0] == cp_ip and p[1] == cp_port:
                                        new_deg = p[2] + 1
                                        self.peer_list = [ (p[0], p[1], new_deg) if (p[0]==cp_ip and p[1]==cp_port) else p for p in self.peer_list]
                                        found = True
                                        break
                                if not found:
                                    self.peer_list.append((cp_ip, cp_port, 1))
                        msg = f"Seed({self.ip}:{self.port}) -> Processed CONNECTION_UPDATE from {new_ip}:{new_port}. Updated peer list: {self.peer_list}"
                        print(msg)
                        log(msg)
                    else:
                        continue
            except Exception as e:
                if self.running_status:
                    err_msg = f"Seed({self.ip}:{self.port}) -> Error handling peer connection: {e}"
                    print(err_msg)
                    log(err_msg)
                break
        if connection:
            connection.close()

    def close(self):
        self.running_status = False
        if self.server_socket:
            try:
                self.server_socket.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            self.server_socket.close()
            msg = f"Seed server on {self.ip}:{self.port} closed."
            print(msg)
            log(msg)
        for conn in self.seed_sockets:
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                conn.close()
            except Exception as e:
                err_msg = "This connection of this seed with peer is already closed"
                print(err_msg)
                log(err_msg)
