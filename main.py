from peers import Peers
from seeds import Seeds
import time 

if __name__ == "__main__":
    config_file = open("config.txt", "r")
    config = config_file.readlines()
    config_file.close()
    seeds = []
    peers = []
    
    # Creating instances of seeds and storing them in a list
    for i in range(len(config)):
        # If there is wrong formatting in the config file, ignore it       
        if( config[i].count(':')!=1 and config[i].count('.')!=3):   continue
        if(config[i] == '\n'):  continue
        config[i] = config[i].strip()
        seed = Seeds(config[i].split(':')[0], config[i].split(':')[1])
        seed.creation()
        seeds.append(seed)
        # print(seed.ip,"   ", seed.port)


    
    num_peers = int(input("How many peers:  "))

    # Creating instances of peers and storing them in a list
    peer_port = 8300
    for i in range(num_peers):
        peer = Peers('127.0.0.1', peer_port)
        peer_port+=1
        peer.creation()
        peer.connect(seeds) #randomly selects the seed to connect (n/2)+1
        peers.append(peer)

    time.sleep(15)
    for peer in peers:
        peer.close()
    time.sleep(5)
    for seed in seeds:
        seed.close()
    
    
