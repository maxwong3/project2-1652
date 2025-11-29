"""
Authoritative game server for multiplayer arena shooter.
Manages game state, processes client inputs, and broadcasts updates.
"""

import socket
import threading
import json
import time
import select
from typing import Dict, Set
from game_state import GameState, TICK_RATE, PLAYER_SPEED

# Server Configuration
HOST = '0.0.0.0'
PORT = 5555
TICK_INTERVAL = 1.0 / TICK_RATE


class GameServer:
    """Authoritative game server."""

    def __init__(self, host: str = HOST, port: int = PORT):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False

        # Game state
        self.game_state = GameState()

        # Client management
        self.clients: Dict[socket.socket, str] = {}  # socket -> player_id
        self.client_sockets: Set[socket.socket] = set()
        self.client_lock = threading.Lock()

        # Input buffer
        self.input_buffer: Dict[str, dict] = {}  # player_id -> latest input
        self.input_lock = threading.Lock()

    def start(self):
        """Start the game server."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.server_socket.setblocking(False)

        self.running = True

        print(f"[SERVER] Starting on {self.host}:{self.port}")

        # Start game loop thread
        game_thread = threading.Thread(target=self._game_loop, daemon=True)
        game_thread.start()

        # Start accepting connections
        self._accept_connections()

    def _accept_connections(self):
        """Accept incoming client connections."""
        print("[SERVER] Waiting for connections...")

        while self.running:
            try:
                # Use select to avoid blocking
                readable, _, _ = select.select([self.server_socket], [], [], 0.1)

                if readable:
                    client_socket, address = self.server_socket.accept()
                    print(f"[SERVER] New connection from {address}")

                    # Start client handler thread
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, address),
                        daemon=True
                    )
                    client_thread.start()

            except Exception as e:
                if self.running:
                    print(f"[SERVER] Error accepting connection: {e}")

    def _handle_client(self, client_socket: socket.socket, address):
        """Handle a single client connection."""
        player_id = None

        try:
            # Receive JOIN message
            data = self._recv_json(client_socket)
            if not data or data.get('type') != 'JOIN':
                print(f"[SERVER] Invalid JOIN from {address}")
                client_socket.close()
                return

            # Create player
            player_id = f"player_{address[1]}"  # Use port as unique ID
            player = self.game_state.add_player(player_id)

            with self.client_lock:
                self.clients[client_socket] = player_id
                self.client_sockets.add(client_socket)

            # Send JOIN response
            response = {
                'type': 'JOIN_ACK',
                'player_id': player_id,
                'color': player.color
            }
            self._send_json(client_socket, response)

            print(f"[SERVER] Player {player_id} joined from {address}")

            # Handle client messages
            while self.running:
                data = self._recv_json(client_socket)
                if not data:
                    break

                if data['type'] == 'INPUT':
                    with self.input_lock:
                        self.input_buffer[player_id] = data
                elif data['type'] == 'LEAVE':
                    break

        except Exception as e:
            print(f"[SERVER] Client {address} error: {e}")

        finally:
            # Clean up client
            if player_id:
                self.game_state.remove_player(player_id)
                with self.input_lock:
                    if player_id in self.input_buffer:
                        del self.input_buffer[player_id]

            with self.client_lock:
                if client_socket in self.clients:
                    del self.clients[client_socket]
                if client_socket in self.client_sockets:
                    self.client_sockets.remove(client_socket)

            client_socket.close()
            print(f"[SERVER] Player {player_id} disconnected")

    def _game_loop(self):
        """Main game loop running at fixed tick rate."""
        print(f"[SERVER] Game loop started at {TICK_RATE} TPS")

        last_time = time.time()
        accumulator = 0.0

        while self.running:
            current_time = time.time()
            frame_time = current_time - last_time
            last_time = current_time

            accumulator += frame_time

            # Fixed time step updates
            while accumulator >= TICK_INTERVAL:
                self._process_inputs()
                self.game_state.update(TICK_INTERVAL)
                self._broadcast_state()
                accumulator -= TICK_INTERVAL

            # Sleep to avoid busy waiting
            time.sleep(0.001)

    def _process_inputs(self):
        """Process all client inputs."""
        with self.input_lock:
            for player_id, input_data in self.input_buffer.items():
                if player_id not in self.game_state.players:
                    continue

                player = self.game_state.players[player_id]

                # Process movement
                keys = input_data.get('keys', {})
                vx = 0.0
                vy = 0.0

                if keys.get('left'):
                    vx -= PLAYER_SPEED
                if keys.get('right'):
                    vx += PLAYER_SPEED
                if keys.get('up'):
                    vy -= PLAYER_SPEED
                if keys.get('down'):
                    vy += PLAYER_SPEED

                player.set_velocity(vx, vy)

                # Process shooting
                if input_data.get('shoot'):
                    shoot_dir = input_data.get('shoot_dir', (0, 0))
                    self.game_state.create_bullet(player_id, shoot_dir)

            # Clear input buffer after processing
            self.input_buffer.clear()

    def _broadcast_state(self):
        """Broadcast game state to all connected clients."""
        state_msg = {
            'type': 'STATE',
            'state': self.game_state.to_dict()
        }

        # Get list of clients to send to
        with self.client_lock:
            clients_to_send = list(self.client_sockets)

        # Send to all clients (outside lock to avoid blocking)
        dead_clients = []
        for client_socket in clients_to_send:
            try:
                self._send_json(client_socket, state_msg)
            except Exception as e:
                dead_clients.append(client_socket)

        # Remove dead clients
        if dead_clients:
            with self.client_lock:
                for client_socket in dead_clients:
                    if client_socket in self.clients:
                        del self.clients[client_socket]
                    if client_socket in self.client_sockets:
                        self.client_sockets.remove(client_socket)

    def _send_json(self, sock: socket.socket, data: dict):
        """Send JSON data over socket."""
        message = json.dumps(data).encode('utf-8')
        length = len(message)
        # Send length prefix (4 bytes) then message
        sock.sendall(length.to_bytes(4, byteorder='big'))
        sock.sendall(message)

    def _recv_json(self, sock: socket.socket) -> dict:
        """Receive JSON data from socket."""
        # Receive length prefix
        length_bytes = self._recv_all(sock, 4)
        if not length_bytes:
            return None

        length = int.from_bytes(length_bytes, byteorder='big')

        # Receive message
        message_bytes = self._recv_all(sock, length)
        if not message_bytes:
            return None

        return json.loads(message_bytes.decode('utf-8'))

    def _recv_all(self, sock: socket.socket, n: int) -> bytes:
        """Receive exactly n bytes from socket."""
        data = bytearray()
        while len(data) < n:
            packet = sock.recv(n - len(data))
            if not packet:
                return None
            data.extend(packet)
        return bytes(data)

    def stop(self):
        """Stop the game server."""
        print("[SERVER] Shutting down...")
        self.running = False

        with self.client_lock:
            for client_socket in list(self.client_sockets):
                client_socket.close()

        if self.server_socket:
            self.server_socket.close()


def main():
    """Main entry point for server."""
    server = GameServer()

    try:
        server.start()
    except KeyboardInterrupt:
        print("\n[SERVER] Interrupted by user")
    finally:
        server.stop()


if __name__ == '__main__':
    main()
