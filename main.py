from peers import Peers
from seeds import Seeds
import time
import random
import signal
import sys
import os

peer_dict = {}          # Maps assigned peer port to its process ID (PID)
seeds = []              # List of seed objects
seeds_connection = []   # List of (IP, port) for seeds
peer_port = 8300        # Starting port for peers

def signal_handler(sig, frame):
    print("\nSignal received. Closing peers and seeds ...")
    # For each peer, send SIGUSR1 so that its child handler calls .close() before exiting
    for port, pid in peer_dict.items():
        try:
            os.kill(pid, signal.SIGUSR1)
            print(f"Sent termination signal to peer on port {port} (PID: {pid})")
        except OSError:
            pass
        
    # Close all seed nodes
    for seed in seeds:
        seed.close()
    sys.exit(0)

if __name__ == "__main__":
    # Handle keyboard interrupt (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Reading the config file for seeds
    with open("config.txt", "r") as config_file:
        config = config_file.readlines()
        
    for line in config:
        if line.count(':') != 1 or line.count('.') != 3:
            continue
        if line.strip() == "":
            continue
        line = line.strip()
        ip, port = line.split(':')
        seed = Seeds(ip, port)
        seed.creation()
        seeds_connection.append((seed.ip, int(seed.port)))
        seeds.append(seed)
    
    try:
        num_peers = int(input("How many peers to create :  "))
    except ValueError:
        print("Invalid input. Exiting.")
        sys.exit(1)
    
    # Create initial peers in separate processes using fork
    for i in range(num_peers):
        assigned_port = peer_port  
        pid = os.fork()
        if pid == 0:
            # Child process: create and run the peer instance
            peer = Peers('127.0.0.1', assigned_port)
            peer.creation()
            peer.connect(seeds_connection)
            # Register a signal handler so that when SIGUSR1 is received,
            # the peer calls its .close() method and exits .
            def child_handler(sig, frame):
                print(f"Peer on port {assigned_port} received termination signal, closing .")
                peer.close()
                sys.exit(0)
            signal.signal(signal.SIGUSR1, child_handler)
            while True:
                time.sleep(1)
            sys.exit(0)
        else:
            peer_dict[assigned_port] = pid
            print(f"Created peer on port {assigned_port} (PID: {pid})")
            peer_port += 1

    # Parent process interactive command loop.
    # Commands:
    #   kill <port>  - kill a peer on a given port (via close())
    #   new          - create a new peer on the next available port
    #   list         - list currently active peers (port and PID)
    #   exit         - exit and close all peers and seeds
    while True:
        cmd = input("\nEnter command (kill <port> | new | list | exit): ").strip()
        if cmd.startswith("kill"):
            tokens = cmd.split()
            if len(tokens) != 2:
                print("Usage: kill <port>")
                continue
            try:
                port_to_kill = int(tokens[1])
            except ValueError:
                print("Port must be an integer.")
                continue
            if port_to_kill in peer_dict:
                pid = peer_dict[port_to_kill]
                try:
                    os.kill(pid, signal.SIGUSR1)
                    print(f"Sent termination signal to peer on port {port_to_kill} (PID: {pid})")
                    del peer_dict[port_to_kill]
                except Exception as e:
                    print("Error killing peer:", e)
            else:
                print(f"No peer running on port {port_to_kill}.")
        elif cmd == "new":
            # Create a new peer in a separate process.
            assigned_port = peer_port
            pid = os.fork()
            if pid == 0:
                peer = Peers('127.0.0.1', assigned_port)
                peer.creation()
                peer.connect(seeds_connection)
                def child_handler(sig, frame):
                    print(f"Peer on port {assigned_port} received termination signal, closing .")
                    peer.close()
                    sys.exit(0)
                signal.signal(signal.SIGUSR1, child_handler)
                while True:
                    time.sleep(1)
                sys.exit(0)
            else:
                peer_dict[assigned_port] = pid
                peer_port += 1
                print(f"Created new peer on port {assigned_port} (PID: {pid})")
        elif cmd == "list":
            if peer_dict:
                print("Active peers:")
                for port, pid in peer_dict.items():
                    print(f"Port: {port}, PID: {pid}")
            else:
                print("No active peers.")
        elif cmd == "exit":
            signal_handler(None, None)
        else:
            print("Unknown command. Available commands: kill <port>, new, list, exit.")
