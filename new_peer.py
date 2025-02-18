import sys
import time
import signal
from peers import Peers
from log import log
import socket

seeds_connection = []

def signal_handler(sig, frame):
    global peer_instance
    msg = "Termination signal received, peer is dead."
    print(msg)
    log(msg)
    peer_instance.close()
    sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        msg = "Usage: python new_peer.py <port>"
        print(msg)
        log(msg)
        sys.exit(1)
    try:
        assigned_port = int(sys.argv[1])
    except ValueError:
        msg = "Invalid port number."
        print(msg)
        log(msg)
        sys.exit(1)
        
    # Read seeds from the config file to connect to
    with open("config.txt", "r") as config_file:
        config = config_file.readlines()
    for line in config:
        if line.count(':') != 1 or line.count('.') != 3:
            continue
        if line.strip() == "":
            continue
        line = line.strip()
        ip, port = line.split(':')
        seeds_connection.append((ip, int(port)))
    
    # Creating peer instance using dynamic IP assignment by passing None.
    peer_instance = Peers(None, assigned_port)
    peer_instance.creation()
    time.sleep(1)  # Waiting for the server socket to start
    peer_instance.connect(seeds_connection)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    msg = f"Peer running on {peer_instance.ip}:{peer_instance.port}."
    print(msg)
    log(msg)
    
    while True:
        time.sleep(1)
