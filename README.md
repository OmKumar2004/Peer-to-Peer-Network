# Peer-to-Peer Network Simulation in Python

## Overview

This Python project simulates a simplified peer-to-peer (P2P) network, designed to illustrate core P2P networking concepts. It showcases peer discovery, message propagation through a gossip protocol, and basic mechanisms for detecting node liveness. The network is composed of two distinct node types: **seed nodes** and **peer nodes**. Seed nodes serve as the initial entry points, enabling peers to discover each other . Peer nodes, after connecting to seeds, form a decentralized network, communicating directly and send information using a gossip-based approach.

**This code is machine independent means We can seeds and peers(each peer also) on different machines**


## Architecture

*   **Seed Nodes:**
    *   **Purpose:** Seed nodes are pre-configured and well-known addresses that peers initially contact to learn about other participants in the network.
    *   **Configuration:** Seed nodes are defined in the `config.txt` file. Each line specifies the IP address and port for a seed node and we have to ensure that the ip of seeds written in the config file matches with the ip of the machine in which main.py is executed.
    *   **Startup:** Seed nodes are launched using the `main.py` script.
    *   **Functionality:**
        *   **initiating the network as an helper for connecting peers**
        *   **contains peer list for coordinating among peers**
        *   **Degree Tracking**
        *   **Dead Node Notification**

*   **Peer Nodes:**
    *   **Purpose:** Peer nodes connect to seed nodes initially for discovery and then communicate and interact directly with each other.
    *   **Startup:** Peer nodes are started using the `new_peer.py <port>` script, requiring a unique port number as a command-line argument for each peer instance.
    *   **Functionality:**
        *   **Seed Connection:** Upon startup, peers read the seed node list from `config.txt` and connect to floor(n/2) + 1 seeds, where n is the total number of seeds.
        *   **Peer-to-Peer Connection Establishment:** Peers utilize a power-law based preferential attachment mechanism to decide which peers from the discovered list to connect with.
        *   **Gossip Protocol:** Peers implement a gossip protocol to send and receive messages (simulated as message hashes) across the network. When a peer originates or receives a new message, it gossips (forwards) this message to its connected peers if came for first time.
        *   **Liveness Detection (Ping/Pong):** Peers actively monitor the liveness of their connected peers using a ping/pong mechanism. They periodically send "PING" messages and expect "PONG" responses. Failure to receive responses within a timeout period for 3 consecutive attempts leads to the peer being considered dead.
        *   **Simulated Death:** To simulate network, peers have a probability of "dying" after a random period. This simulates node failures and departures in a real network environment.
        *   **Connection Updates & Dead Node Notifications:** Peers inform the seed nodes about their new connections and when they detect a peer as dead. This ensures that seed nodes maintain an up-to-date view of the network topology.

**Network Flow Explanation:**

1.  **Seed Node Initialization:**
    *   The simulation begins by launching seed nodes using `main.py`.
    *   Each seed node reads its configuration (IP and port) and starts listening for incoming connections from peers.

2.  **Peer Node Initiation and Discovery:**
    *   When a peer node is started using `new_peer.py <port>`, it initiates the bootstrapping process.
    *   **Seed Selection:** The peer reads the list of seed nodes from `config.txt`. It then randomly selects `(n/2) + 1` seed nodes to connect to, where `n` is the total number of seed nodes listed.
    *   **Seed Connection and Registration:** The peer attempts to establish TCP connections with the selected seed nodes. Upon successful connection, it registers itself with each seed by sending a `PEER_SERVER:<port>` message, informing the seed of its listening port for incoming peer connections.
    *   **Peer List Request:** After registration, the peer sends a `REQUEST_PEER_LIST:<port>` message to each connected seed node.
    *   **Peer List Retrieval and Merging:** Seed nodes respond to the request by sending back a list of peers they are aware of, including each peer's IP address, port, and connection degree. The requesting peer collects these lists from all connected seeds. If there are duplicate peer entries (reported by multiple seeds), the peer merges them, taking the maximum reported degree for each unique peer. This merged list becomes the peer's initial view of the network.

3.  **Peer-to-Peer Connection Establishment (Power Law):**
    *   Once a peer has obtained the initial peer list from the seeds, it begins establishing direct connections with other peers based on a power-law.
    *   **Power Law Logic:** For each peer in the discovered peer list (excluding itself), the connecting peer calculates a connection threshold based on the discovered peer's degree. The threshold is inversely proportional to the peer's degree, specifically `threshold = 1 / (peer_degree + 1)`.
    *   **Connection Decision:** A random value between 0 and 1 is generated. If this random value is greater than the calculated threshold, the connecting peer attempts to establish a TCP connection with the discovered peer.
    *   **Handshake:** Upon successfully connecting to a peer, a handshake message (`NEW_PEER_SERVER:<port>`) is sent to inform the newly connected peer of the connecting peer's server port. This is crucial for bi-directional communication so that the server port of that connected peer is with the current peer.

4.  **Gossip-based Message:**
    *   The simulation implements a simplified gossip protocol for message propagation.
    *   **Message Generation:** Peers periodically generate new messages. In this simulation, messages are represented by hashes of timestamped strings containing the peer's IP and port.
    *   **Gossip Initiation:** When a peer generates a new message, it checks if it has already seen this message (by checking its set of `message_hashes`). If it's a new message, the peer adds its hash to its `message_hashes` set and initiates the gossip process.
    *   **Message Propagation:** The originating peer sends `GOSSIP:<message_hash>` messages to all of its currently connected peers.
    *   **Message Forwarding:** When a peer receives a `GOSSIP:<message_hash>` message, it checks if it has already processed this message hash. If it's a new message, it adds the hash to its `message_hashes` set and forwards the same `GOSSIP:<message_hash>` message to *all* of its other connected peers (excluding the peer it received the message from). This process continues, propagating the message throughout the connected network.

5.  **Liveness Detection and Dead Node Handling (Ping/Pong Mechanism):**
    *   To maintain network health and responsiveness, peers continuously monitor the liveness of their direct peer connections using a ping/pong mechanism.
    *   **Ping Sending:** Peers periodically send `PING` messages to each of their connected peers at intervals defined by `PING_INTERVAL`.
    *   **Pong Response:** Upon receiving a `PING` message, a peer immediately responds with a `PONG` message.
    *   **Timeout and Failure Counting:** The pinging peer tracks the time elapsed since sending a `PING`. If a `PONG` is not received within a defined `PING_MAX_WAIT` time, it is considered a ping failure. Peers maintain a failure counter for each connected peer.
    *   **Dead Node Declaration:** If a peer fails to respond to a `PING` multiple times consecutively (currently set to 3 failures), the pinging peer declares the non-responsive peer as "dead."
    *   **Dead Node Actions:**
        *   **Local Peer List Update:** The declaring peer removes the dead peer from its list of connected peers (`peer_connections`) and its general `peer_list`.
        *   **Seed Notification:** The declaring peer sends a `DEAD_NODE:<ip>:<port>:<timestamp>:<reporter_ip>:<reporter_port>` message to all of its connected seed nodes, informing them about the dead peer. This allows seeds to update their global peer lists and degree counts, ensuring network-wide consistency.
        *   **Socket Closure:** The declaring peer closes the socket connection to the dead peer.


6.  **Connection Update to Seeds:**
    *   After establishing initial peer connections, and whenever a peer's connection status changes (new connection, disconnection due to dead peer detection, etc.), the peer sends a `CONNECTION_UPDATE:<self_ip>:<self_port>:<new_degree>:<connected_peer1>,<connected_peer2>,...` message to its connected seed nodes.
    *   **Update Information:** This message includes:
        *   The peer's own IP and port.
        *   Its current connection degree (`new_degree`), which is the number of peers it is directly connected to.
        *   A comma-separated list of the IP:port of all peers it is currently connected to.
    *   **Seed Processing:** Seed nodes receive these `CONNECTION_UPDATE` messages and use the information to:
        *   Update the connection degree of the reporting peer in their peer list.
        *   Increment the degree count of each peer in the `connected_peers` list (as reported by the updating peer), reflecting the newly established or maintained connections.
        *   Add any newly reported peers to their peer list if they weren't already known.



## How to Run

**Prerequisites:**

*   **Python 3.x** must be installed on your system.

**Steps:**

1.  **Configure Seed Nodes:**
    *   Open the `config.txt` file in a text editor.
    *   Enter the IP address and port for each seed node, one per line, in the format `IP_ADDRESS:PORT`. For local testing, you can use `127.0.0.1` or your device's IP as the IP address for all seed nodes, using different ports (e.g., 8000, 8001, 8002).
    *   Example `config.txt`:
        ```
        192.12.31.22:8000
        192.12.31.22:8001
        192.12.31.22:8002
        ```

2.  **Start the Seed Nodes:**
    *   Open a terminal, navigate to the project directory, and run the `main.py` script:
        ```bash
        python main.py
        ```
    *   This will start the seed nodes defined in `config.txt`. You should see output in the terminal indicating that each seed node has been activated and is listening on its specified port.
    *   You can use the command listener in the seed node terminal to interact with the seed network:
        *   Type `list` and press Enter to view the current peer list maintained by the seeds.
        *   Type `exit` and press Enter to gracefully shut down the seed nodes.

3.  **Start Peer Nodes:**
    *   Open **new** terminal windows for each peer node **can do in different devices also** you want to start. Each peer needs to run in its own terminal.
    *   In each new terminal, navigate to the project directory and run `new_peer.py` followed by a unique port number as a command-line argument. For example, to start three peer nodes:

        **Terminal 1:**
        ```bash
        python new_peer.py 9000
        ```

        **Terminal 2:**
        ```bash
        python new_peer.py 9001
        ```

        **Terminal 3:**
        ```bash
        python new_peer.py 9002
        ```

4.  **Observe the Network in Action:**
    *   Monitor the output in all terminals (seed and peer terminals). Observe the log messages to understand the network's behavior:
        *   Seed node initializations and peer connection acceptances.
        *   Peer node connections to seeds and other peers.
        *   PING and PONG exchanges between peers.
        *   GOSSIP message propagation.
        *   Connection decisions based on the power-law mechanism.
        *   Degree updates in seed node peer lists.
        *   Dead node detections and removals.
        *   Simulated peer death events.
    *   For more detailed logging, check the `OUTPUT.txt` file in the project directory. It contains timestamped logs of all significant events from both seed and peer nodes.

5.  **Stop the Network:**
    *   To stop the seed nodes, press **Ctrl+C** in the terminal where `main.py` is running. This will trigger the signal handler and gracefully close the seed node servers.
    *   To stop each peer node, press **Ctrl+C** in each of the peer terminals. This will also trigger signal handlers in the peer nodes, causing them to close their connections and exit gracefully.