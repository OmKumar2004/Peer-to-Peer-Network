import signal
import sys
import time
import threading
from seeds import Seeds
from log import log

# Global list of seed nodes
seeds = []

def signal_handler(sig, frame):
    print("\nSignal received. Closing seeds gracefully...")
    log("Signal received. Closing seeds gracefully...")
    for seed in seeds:
        seed.close()
    sys.exit(0)


def command_listener():
    
    while True:
        cmd = input("Enter command (list/exit): ").strip().lower()
        if cmd == "list":
            print("=== Peer Lists from All Seeds ===")
            for seed in seeds:
                print(f"Seed {seed.ip}:{seed.port} peer list:")
                for peer in seed.peer_list:
                    print(f"  {peer[0]}:{peer[1]} degree: {peer[2]}")
            print("=== End of Peer Lists ===")
        elif cmd == "exit":
            print("Exiting and closing seeds...")
            for seed in seeds:
                seed.close()
            sys.exit(0)
        else:
            print("Unknown command. Try 'list' or 'exit'.")

if __name__ == "__main__":
    # Register the signal handler for shutdown 
    signal.signal(signal.SIGINT, signal_handler)

    with open("config.txt", "r") as config_file:
        config = config_file.readlines()
        
    # Create seed nodes from the config file
    for line in config:
        # improperly formatted or empty lines so skiiping them 
        if line.count(':') != 1 or line.count('.') != 3:
            continue
        if line.strip() == "":
            continue
        line = line.strip()
        ip, port = line.split(':')
        seed = Seeds(ip, port)
        seed.creation()
        seeds.append(seed)
    
    print("Seed nodes created.")
    log("Seed nodes created.")
    
    command_thread = threading.Thread(target=command_listener, daemon=True)
    command_thread.start()

    while True:
        time.sleep(1)
