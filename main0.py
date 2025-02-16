import signal
import sys
import time
import random
from peers import Peers
from seeds import Seeds

# Global lists to hold our nodes so the signal handler can access them
# peers = []
seeds = []

def signal_handler(sig, frame):
    print("\nSignal received. Closing seeds gracefully...")
    # for peer in peers:
    #     peer.close()
    for seed in seeds:
        seed.close()
    sys.exit(0)

if __name__ == "__main__":
    # Register the signal handler for graceful shutdown (SIGINT for Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)

    # Read seed configuration from config.txt
    with open("config.txt", "r") as config_file:
        config = config_file.readlines()
        
    # seeds_connection = []
    
    # Create seed nodes from the config file
    for line in config:
        # Skip improperly formatted lines
        if line.count(':') != 1 or line.count('.') != 3:
            continue
        if line.strip() == "":
            continue
        line = line.strip()
        ip, port = line.split(':')
        seed = Seeds(ip, port)
        seed.creation()
        # seeds_connection.append((seed.ip, int(seed.port)))
        seeds.append(seed)

    # num_peers = int(input("How many peers:  "))

    # # Create peer nodes
    # peer_port = 8300
    # for i in range(num_peers):
    #     peer = Peers('127.0.0.1', peer_port)
    #     peer_port += 1
    #     peer.creation()
    #     peer.connect(seeds_connection)  # Connects to (⌊n/2⌋ + 1) seeds and then to peers
    #     # Optionally simulate a peer dying randomly
    #     if random.randint(1, 100) <= 60 and len(peers) > 0:
    #         chosen_peer = random.choice(peers)
    #         if not chosen_peer.isDead:
    #             chosen_peer.isDead = True
    #             print(f"Simulating death for peer {chosen_peer.ip}:{chosen_peer.port}")
    #     peers.append(peer)
        
    # Keep the main thread alive until an external signal (Ctrl+C) is received
    # try:
    #     while True:
    #         time.sleep(1)
    # except KeyboardInterrupt:
    #     # Fallback in case signal_handler isn't triggered
    #     signal_handler(None, None)
    print("Seed nodes created.")
    while True:
        time.sleep(1)
