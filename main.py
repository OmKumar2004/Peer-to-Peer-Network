from peers import Peers
from seeds import Seeds
import time 
import random

if __name__ == "__main__":
    config_file = open("config.txt", "r")
    config = config_file.readlines()
    config_file.close()
    seeds_connection = []
    peers = []
    seeds = []
    
    # Creating instances of seeds and storing them in a list
    for i in range(len(config)):
        # If there is wrong formatting in the config file, ignore it       
        if( config[i].count(':')!=1 and config[i].count('.')!=3):   continue
        if(config[i] == '\n'):  continue
        config[i] = config[i].strip()
        seed = Seeds(config[i].split(':')[0], config[i].split(':')[1])
        seed.creation()
        seeds_connection.append((seed.ip, int(seed.port)))
        seeds.append(seed)
        # print(seed.ip,"   ", seed.port)


    
    num_peers = int(input("How many peers:  "))

    # Creating instances of peers and storing them in a list
    peer_port = 8300
    for i in range(num_peers):
        peer = Peers('127.0.0.1', peer_port)
        peer_port+=1
        peer.creation()
        peer.connect(seeds_connection) #randomly selects the seed to connect (n/2)+1
        #randomly select the peer from the peer list and check if it is alive and make it as dead
        if random.randint(1, 100) <= 60 and len(peers) > 0:
            chosen_peer = random.choice(peers)
            if not chosen_peer.isDead:
                chosen_peer.isDead = True
                print(f"Simulating death for peer {chosen_peer.ip}:{chosen_peer.port}")
            # peer.isDead = True
            # print(f"Simulating death for peer {peer.ip}:{peer.port}")
        peers.append(peer)
           
        
        
    try:
        while True:
            time.sleep(1)  # Run indefinitely until a keyboard interrupt is received
    except KeyboardInterrupt:
        print("KeyboardInterrupt received. Closing peers and seeds...")
        for peer in peers:
            peer.close()
        for seed in seeds:
            seed.close()    
   
    
