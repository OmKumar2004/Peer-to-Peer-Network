# Peer-to-Peer Network Simulation in Python

## Overview

This Python project simulates a basic peer-to-peer (P2P) network. It demonstrates fundamental P2P concepts like peer discovery, message gossip, and basic node liveness detection using ping/pong. The network consists of two types of nodes: **seed nodes** and **peer nodes**. Seed nodes act as initial points of contact for peers to discover other peers in the network. Peer nodes connect to seeds to get the initial list of peers and then communicate directly with each other using a gossip protocol to disseminate messages.

## Architecture

The simulation implements a simplified P2P network with:

*   **Seed Nodes:**
    *   Act as servers for peer discovery.
    *   Configured in `config.txt`.
    *   Started by running `main.py`.
    *   Maintain a list of active peers with their degrees (number of connections).
    *   Peers connect to seeds initially to get the list of other peers and their degrees.

*   **Peer Nodes:**
    *   Connect to seed nodes to discover other peers.
    *   Started by running `new_peer.py <port>`.
    *   Communicate directly with other peers using TCP sockets.
    *   Use a gossip protocol to send messages (simulated by message hashes).
    *   Implement a ping/pong mechanism to detect peer liveness.
    *   Simulate random death to demonstrate network dynamics.
    *   Use power law distribution for establishing connections.

**Network Flow:**

1.  **Seed Node Startup:** Seed nodes are started first using `main.py`. They listen on ports specified in `config.txt`.
2.  **Peer Node Startup:** Peer nodes are started using `new_peer.py <port>`. Each peer needs a unique port number.
3.  **Peer Discovery:**
    *   When a peer starts, it reads the seed list from `config.txt`.
    *   It randomly selects `(n/2) + 1` seeds from the list and connects to them.
    *   Peers send "PEER_SERVER:<port>" to seeds to register their server port.
    *   Peers request a peer list from the connected seeds using "REQUEST_PEER_LIST".
    *   Seeds respond with a list of currently known peers along with their degrees.
    *   Peers use power law distribution to decide connections.

4.  **Power Law Implementation:**
    *   Each peer in the network has a degree (number of connections).
    *   For a new peer, connection probability is calculated as: P(k) ∝ k^(-α)
        * k is the degree of the existing peer
        * α is the power law exponent
    *   For each potential peer connection:
        * Calculate probability based on peer's degree
        * Generate random number between 0 and 1
        * Connect if random number > calculated probability
    *   After establishing connections:
        * Notify connected seeds about new connections
        * Seeds update degree counts in their peer tables
        * If multiple seeds have different degrees for same peer, maximum is used

5.  **Gossip Communication:**
    *   Peers periodically generate new messages (represented by message hashes).
    *   When a peer generates a new message, it sends "GOSSIP:<message_hash>" to all its connected peers.
    *   Upon receiving a "GOSSIP" message with a new hash, a peer stores the hash and forwards the "GOSSIP" message to all its *other* connected peers. 

6.  **Liveness Detection (Ping/Pong):**
    *   Peers periodically send "PING" messages to their connected peers.
    *   Upon receiving a "PING", a peer responds with a "PONG".
    *   If a peer doesn't receive a "PONG" within a timeout period for multiple consecutive "PING" messages, it considers the peer dead, removes it from its peer list, and notifies the seed nodes about the dead peer using "DEAD_NODE:<ip>:<port>:<timestamp>:<reporter_ip>:<reporter_port>".
    *   Seeds, upon receiving "DEAD_NODE", remove the reported peer from their peer list.

7.  **Simulated Peer Death:**
    *   Each peer has a chance to "die" after a random time interval.
    *   If a peer is simulated to die, it stops participating in the network and notifies its connected seeds.

## How to Run

**Prerequisites:**

*   **Python 3.x** must be installed on your system.

**Steps:**
1.  **Start the Seed Nodes:**
    *   Open a terminal and Run the `main.py` script to start the seed nodes:
        ```bash
        python main.py
        ```
2.  **Start Peer Nodes:**
    *   Open **new** terminals for each peer node you want to start. In each new terminal, navigate to the project directory and run `new_peer.py` with a unique port number as a command-line argument. For example:

        ```bash
        python new_peer.py <port_num>
        ```

3.  **Observe the Network:**
    *   Monitor the output in each terminal (seed and peer terminals). You will see log messages indicating:
        *   Seed node activations.
        *   Peer connections to seeds and other peers.
        *   PING and PONG messages for liveness detection.
        *   GOSSIP messages being sent and received.
        *   Connection decisions based on power law distribution.
        *   Degree updates in seed tables.
        *   Simulated peer deaths (if they occur).
    *   Check the `OUTPUT.txt` file in the project directory. It will contain a timestamped log of all significant events in the network.

4.  **Stop the Network:**
    *   To stop the seed nodes, press **Ctrl+C** in the terminal where [main.py](http://_vscodecontentref_/1) is running.
    *   To stop each peer node, press **Ctrl+C** in each of the peer terminals.

## Configuration ([config.txt](http://_vscodecontentref_/2))

The [config.txt](http://_vscodecontentref_/3) file is crucial for setting up the seed nodes. Each line in this file represents a seed node.

*   **Format:** `IP_ADDRESS:PORT`
*   **Example:**
    ```
    127.0.0.1:8000
    127.0.0.1:8001
    127.0.0.1:8002
    127.0.0.1:8003
    ```