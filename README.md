# Peer-to-Peer-Network
---

## How to Run Code
To run the peer-to-peer network, execute the following command:
```
python3 main0.py
python3 new_peer.py (new terminal)
```
Ensure that you have Python 3 installed and the necessary dependencies available.


## Code Files Overview
- **peers.py**: Implements the core peer-to-peer network logic including server setup, connection management, message passing, ping monitoring, and gossip protocol.
- **log_util.py**: Used for logging messages to the network log file.
- **seeds.py**: Implements the seed node logic which handles incoming connections from peers and provides them with the peer list.
- **main.py**: Creates peers in separate processes, manages them via an interactive command loop, and handles signals for graceful shutdown.
- **main0.py**: Sets up seed nodes from the configuration file and keeps the seed processes alive.
- **new_peer.py**: Creates a new peer instance and connects it to seeds, handling signals to perform a graceful shutdown.
- **config.txt**: Contains the configuration of seed nodes.

