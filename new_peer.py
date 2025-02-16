import sys
import time
import signal
import os
from peers import Peers

def signal_handler(sig, frame):
    global peer_instance
    print("Termination signal received, closing peer.")
    peer_instance.close()
    sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python new_peer.py <port>")
        sys.exit(1)
    try:
        assigned_port = int(sys.argv[1])
    except ValueError:
        print("Invalid port number.")
        sys.exit(1)
        
    # Read seeds from the config file
    seeds_connection = []
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
    
    # Create the peer instance
    peer_instance = Peers('127.0.0.1', assigned_port)
    peer_instance.creation()
    time.sleep(1)  # Give time for the server socket to start
    peer_instance.connect(seeds_connection)
    
    # Register signal handlers so that if this terminal is closed the peer cleans up
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print(f"Peer running on 127.0.0.1:{assigned_port}.")
    while True:
        time.sleep(1)
