# Multiplayer Arena Shooter - CS1652 Project 2

A real-time multiplayer 2D arena shooter game built with Python, demonstrating key computer networking concepts including client-server architecture, state synchronization, and latency handling.

## Project Overview

This project implements a multiplayer game where players can move around a 2D arena, shoot projectiles at each other, and compete for the highest score. The game uses an **authoritative server architecture** to ensure fairness and consistency across all players.

### Key Features

- **Real-time Multiplayer**: Support for multiple simultaneous players
- **Authoritative Server**: Server-side game logic prevents cheating and ensures consistency
- **TCP Networking**: Reliable message delivery using JSON over TCP sockets
- **Client-Side Rendering**: Smooth 60 FPS visualization using Pygame
- **Hit Detection & Scoring**: Server-side collision detection with real-time score tracking
- **Player Respawning**: Automatic respawn after being hit
- **Network Statistics**: Display of FPS and network tick rate

## System Architecture

### Modules

1. **game_state.py** - Shared game state module
   - Defines game entities (Player, Bullet)
   - Game constants (arena size, speeds, tick rate)
   - Game state management and physics
   - Collision detection logic

2. **server.py** - Authoritative game server
   - Accepts client connections (TCP)
   - Manages game state at fixed tick rate (30 TPS)
   - Processes player inputs
   - Broadcasts state updates to all clients
   - Handles player joins/leaves

3. **client.py** - Game client with visualization
   - Connects to game server
   - Captures user input (keyboard/mouse)
   - Sends input to server
   - Receives and renders game state
   - Displays UI and scoreboard

### Network Protocol

The game uses TCP sockets with JSON messages. Each message has a 4-byte length prefix followed by JSON data.

**Message Types:**

- `JOIN`: Client requests to join game
- `JOIN_ACK`: Server confirms join and assigns player ID
- `INPUT`: Client sends input state (keys, mouse, shooting)
- `STATE`: Server broadcasts complete game state
- `LEAVE`: Client disconnects gracefully

### Networking Concepts Demonstrated

1. **Client-Server Architecture**: Centralized authoritative server model
2. **Fixed Tick Rate**: Server runs at consistent 30 ticks per second
3. **State Synchronization**: Full state broadcast to all clients
4. **Concurrent Connections**: Multi-threaded server handling multiple clients
5. **Message Framing**: Length-prefixed messages for reliable parsing
6. **Latency Handling**: Server processes inputs and broadcasts results
7. **Graceful Disconnection**: Proper cleanup of client resources

## Requirements

- Python 3.7 or higher
- pygame library

## Installation

1. Install Python dependencies:
```bash
pip install pygame
```

2. Verify installation:
```bash
python --version  # Should be 3.7+
python -c "import pygame; print(pygame.__version__)"
```

## Running the Game

### Step 1: Start the Server

In a terminal, navigate to the project directory and run:

```bash
python server.py
```

You should see:
```
[SERVER] Starting on 0.0.0.0:5555
[SERVER] Waiting for connections...
[SERVER] Game loop started at 30 TPS
```

The server will listen on port 5555 for incoming connections.

### Step 2: Start Client(s)

In separate terminals (one for each player), run:

```bash
python client.py
```

To connect to a remote server:
```bash
python client.py <hostname> <port>
```

Example:
```bash
python client.py localhost 5555
python client.py 192.168.1.100 5555
```

### Step 3: Play the Game

**Controls:**
- **WASD** or **Arrow Keys**: Move your player
- **Mouse**: Aim
- **Left Click**: Shoot
- **ESC**: Quit

**Objective:**
- Shoot other players to score points
- Avoid getting hit
- Compete for the highest score!

## Testing the Multiplayer Functionality

### Local Testing (Single Machine)

1. Open 3 terminal windows
2. Terminal 1: Run `python server.py`
3. Terminal 2: Run `python client.py`
4. Terminal 3: Run `python client.py`
5. You should see two players in each client window
6. Move and shoot to test synchronization

### Network Testing (Multiple Machines)

1. On the server machine:
   - Note the IP address: `ipconfig` (Windows) or `ifconfig` (Mac/Linux)
   - Run `python server.py`
   - Ensure firewall allows port 5555

2. On each client machine:
   - Run `python client.py <server_ip> 5555`
   - Example: `python client.py 192.168.1.100 5555`

3. Test different scenarios:
   - Multiple players joining simultaneously
   - Players shooting each other
   - Players disconnecting and rejoining
   - Network latency effects

## Game Configuration

You can modify these constants in `game_state.py`:

```python
ARENA_WIDTH = 800        # Arena width in pixels
ARENA_HEIGHT = 600       # Arena height in pixels
PLAYER_SIZE = 20         # Player radius
PLAYER_SPEED = 200       # Player movement speed
BULLET_SPEED = 400       # Bullet speed
TICK_RATE = 30           # Server update rate (ticks per second)
RESPAWN_TIME = 3.0       # Respawn delay in seconds
MAX_AMMO = 20            # Default ammo limit
```

## Project Goals

This project demonstrates:

1. **Relevance to Networking**: Implements real-time client-server communication, addressing challenges like state synchronization, concurrent connections, and latency.

2. **Technical Depth**:
   - Authoritative server architecture
   - Multi-threaded server handling
   - Fixed tick rate game loop
   - Message framing protocol
   - Real-time state broadcasting

3. **Completeness**: Fully functional multiplayer game with:
   - Player movement and shooting
   - Collision detection
   - Scoring system
   - Visual feedback
   - Network statistics

4. **Reproducibility**: Clear setup instructions, well-documented code, and testable on any platform with Python and pygame.


## Authors

Ilay Dvir and Max Wong

## License

This project is created for educational purposes as part of CS1652.
