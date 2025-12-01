"""
Game client for multiplayer arena shooter.
Handles user input, network communication, and rendering.
"""

import socket
import threading
import json
import pygame
import sys
import time
import math
from typing import Optional, Tuple
from game_state import (ARENA_WIDTH, ARENA_HEIGHT, PLAYER_SIZE, BULLET_SIZE, AMMO_BOX_SIZE,
                        PLAYER_SPEED)

# Client Configuration
DEFAULT_HOST = 'localhost'
DEFAULT_PORT = 5555
FPS = 60


class GameClient:
    """Game client with networking and rendering."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        self.connected = False

        # Player info
        self.player_id = None
        self.player_color = (255, 255, 255)

        # Game state (from server)
        self.game_state = None
        self.state_lock = threading.Lock()

        # Input state
        self.keys = {
            'left': False,
            'right': False,
            'up': False,
            'down': False
        }
        self.mouse_pos = (0, 0)
        self.shooting = False

        # Pygame
        pygame.init()
        self.screen = pygame.display.set_mode((ARENA_WIDTH, ARENA_HEIGHT))
        pygame.display.set_caption("Multiplayer Arena Shooter")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)

        # Network stats
        self.last_state_time = 0
        self.network_fps = 0

    def connect(self) -> bool:
        """Connect to game server."""
        try:
            print(f"[CLIENT] Connecting to {self.host}:{self.port}...")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))

            # Send JOIN message
            join_msg = {'type': 'JOIN'}
            self._send_json(join_msg)

            # Receive JOIN_ACK
            response = self._recv_json()
            if response and response['type'] == 'JOIN_ACK':
                self.player_id = response['player_id']
                self.player_color = tuple(response['color'])
                self.connected = True
                print(f"[CLIENT] Connected as {self.player_id}")

                # Start network thread
                network_thread = threading.Thread(target=self._network_loop, daemon=True)
                network_thread.start()

                return True

        except Exception as e:
            print(f"[CLIENT] Connection failed: {e}")
            return False

        return False

    def _network_loop(self):
        """Network thread that receives game state updates."""
        last_fps_time = time.time()
        frame_count = 0

        while self.connected:
            try:
                data = self._recv_json()
                if not data:
                    break

                if data['type'] == 'STATE':
                    with self.state_lock:
                        self.game_state = data['state']
                        self.last_state_time = time.time()

                    # Update network FPS
                    frame_count += 1
                    current_time = time.time()
                    if current_time - last_fps_time >= 1.0:
                        self.network_fps = frame_count
                        frame_count = 0
                        last_fps_time = current_time

            except Exception as e:
                print(f"[CLIENT] Network error: {e}")
                break

        self.connected = False
        print("[CLIENT] Disconnected from server")

    def _send_input(self):
        """Send current input state to server."""
        if not self.connected:
            return

        # Calculate shoot direction from mouse position
        shoot_dir = (0, 0)
        if self.shooting and self.player_id and self.game_state:
            with self.state_lock:
                players = self.game_state.get('players', {})
                if self.player_id in players:
                    player = players[self.player_id]
                    px, py = player['x'], player['y']
                    mx, my = self.mouse_pos

                    dx = mx - px
                    dy = my - py
                    length = math.sqrt(dx * dx + dy * dy)
                    if length > 0:
                        shoot_dir = (dx / length, dy / length)

        input_msg = {
            'type': 'INPUT',
            'keys': self.keys.copy(),
            'shoot': self.shooting,
            'shoot_dir': shoot_dir
        }

        try:
            self._send_json(input_msg)
        except Exception as e:
            print(f"[CLIENT] Failed to send input: {e}")
            self.connected = False

    def run(self):
        """Main game loop."""
        self.running = True

        while self.running:
            # Handle events
            self._handle_events()

            # Send input to server
            self._send_input()

            # Render
            self._render()

            # Cap framerate
            self.clock.tick(FPS)

        self._cleanup()

    def _handle_events(self):
        """Handle pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT or event.key == pygame.K_a:
                    self.keys['left'] = True
                elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                    self.keys['right'] = True
                elif event.key == pygame.K_UP or event.key == pygame.K_w:
                    self.keys['up'] = True
                elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                    self.keys['down'] = True
                elif event.key == pygame.K_ESCAPE:
                    self.running = False

            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_LEFT or event.key == pygame.K_a:
                    self.keys['left'] = False
                elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                    self.keys['right'] = False
                elif event.key == pygame.K_UP or event.key == pygame.K_w:
                    self.keys['up'] = False
                elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                    self.keys['down'] = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    self.shooting = True

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    self.shooting = False

            elif event.type == pygame.MOUSEMOTION:
                self.mouse_pos = event.pos

    def _render(self):
        """Render the game."""
        # Clear screen
        self.screen.fill((20, 20, 30))

        if not self.connected:
            # Show disconnected message
            text = self.font.render("Disconnected", True, (255, 0, 0))
            rect = text.get_rect(center=(ARENA_WIDTH // 2, ARENA_HEIGHT // 2))
            self.screen.blit(text, rect)
            pygame.display.flip()
            return

        # Get game state
        with self.state_lock:
            if not self.game_state:
                # Show waiting message
                text = self.font.render("Waiting for game state...", True, (255, 255, 255))
                rect = text.get_rect(center=(ARENA_WIDTH // 2, ARENA_HEIGHT // 2))
                self.screen.blit(text, rect)
                pygame.display.flip()
                return

            players = self.game_state.get('players', {})
            bullets = self.game_state.get('bullets', {})
            ammo_boxes = self.game_state.get('ammo_boxes', {})

        # Draw arena border
        pygame.draw.rect(self.screen, (100, 100, 100),
                        (0, 0, ARENA_WIDTH, ARENA_HEIGHT), 2)

        # Draw bullets
        for bullet in bullets.values():
            x, y = int(bullet['x']), int(bullet['y'])
            pygame.draw.circle(self.screen, (255, 255, 0), (x, y), BULLET_SIZE)

        # Draw players
        for player in players.values():
            if not player['alive']:
                continue

            x, y = int(player['x']), int(player['y'])
            color = tuple(player['color'])

            # Highlight own player
            if player['id'] == self.player_id:
                pygame.draw.circle(self.screen, (255, 255, 255), (x, y), PLAYER_SIZE + 3, 2)

            # Draw player
            pygame.draw.circle(self.screen, color, (x, y), PLAYER_SIZE)

            # Draw player ID and score
            text = self.small_font.render(
                f"{player['id']} ({player['score']})",
                True, (255, 255, 255)
            )
            text_rect = text.get_rect(center=(x, y - PLAYER_SIZE - 15))
            self.screen.blit(text, text_rect)

        # Draw ammo boxes
        for box in ammo_boxes.values():
            x, y = int(box['x']), int(box['y'])
            pygame.draw.rect(self.screen, (255, 0, 0), (x, y, AMMO_BOX_SIZE, AMMO_BOX_SIZE))

        # Draw crosshair at mouse position
        mx, my = self.mouse_pos
        pygame.draw.circle(self.screen, (255, 0, 0), (mx, my), 3, 1)
        pygame.draw.line(self.screen, (255, 0, 0), (mx - 10, my), (mx + 10, my), 1)
        pygame.draw.line(self.screen, (255, 0, 0), (mx, my - 10), (mx, my + 10), 1)

        # Draw UI
        self._draw_ui(players)

        pygame.display.flip()

    def _draw_ui(self, players):
        """Draw UI elements."""
        # Draw FPS
        fps_text = self.small_font.render(
            f"FPS: {int(self.clock.get_fps())} | Network: {self.network_fps} TPS",
            True, (200, 200, 200)
        )
        self.screen.blit(fps_text, (10, 10))

        # Draw player count
        player_count = len([p for p in players.values() if p['alive']])
        count_text = self.small_font.render(
            f"Players: {player_count}",
            True, (200, 200, 200)
        )
        self.screen.blit(count_text, (10, 35))

        # Draw controls
        controls = [
            "Controls:",
            "WASD/Arrows: Move",
            "Mouse: Aim",
            "Left Click: Shoot",
            "ESC: Quit"
        ]

        y_offset = ARENA_HEIGHT - 130
        for i, line in enumerate(controls):
            text = self.small_font.render(line, True, (150, 150, 150))
            self.screen.blit(text, (10, y_offset + i * 22))

        # Draw ammo count
        ammo_count = self.small_font.render(f"Ammo: {players[self.player_id]["ammo"]}", True, (200, 200, 200))
        self.screen.blit(ammo_count, (700, 550))

        # Draw scoreboard
        scoreboard = sorted(players.values(), key=lambda p: p['score'], reverse=True)[:5]
        if scoreboard:
            y_offset = 70
            title = self.small_font.render("Scoreboard:", True, (200, 200, 200))
            self.screen.blit(title, (10, y_offset))
            y_offset += 25

            for i, player in enumerate(scoreboard):
                score_text = self.small_font.render(
                    f"{i + 1}. {player['id']}: {player['score']}",
                    True, tuple(player['color'])
                )
                self.screen.blit(score_text, (10, y_offset + i * 22))

    def _send_json(self, data: dict):
        """Send JSON data over socket."""
        message = json.dumps(data).encode('utf-8')
        length = len(message)
        self.socket.sendall(length.to_bytes(4, byteorder='big'))
        self.socket.sendall(message)

    def _recv_json(self) -> dict:
        """Receive JSON data from socket."""
        length_bytes = self._recv_all(4)
        if not length_bytes:
            return None

        length = int.from_bytes(length_bytes, byteorder='big')
        message_bytes = self._recv_all(length)
        if not message_bytes:
            return None

        return json.loads(message_bytes.decode('utf-8'))

    def _recv_all(self, n: int) -> bytes:
        """Receive exactly n bytes from socket."""
        data = bytearray()
        while len(data) < n:
            packet = self.socket.recv(n - len(data))
            if not packet:
                return None
            data.extend(packet)
        return bytes(data)

    def _cleanup(self):
        """Clean up resources."""
        if self.connected and self.socket:
            try:
                leave_msg = {'type': 'LEAVE'}
                self._send_json(leave_msg)
            except:
                pass

        if self.socket:
            self.socket.close()

        pygame.quit()


def main():
    """Main entry point for client."""
    # Parse command line arguments
    host = DEFAULT_HOST
    port = DEFAULT_PORT

    if len(sys.argv) > 1:
        host = sys.argv[1]
    if len(sys.argv) > 2:
        port = int(sys.argv[2])

    # Create and run client
    client = GameClient(host, port)

    if client.connect():
        try:
            client.run()
        except KeyboardInterrupt:
            print("\n[CLIENT] Interrupted by user")
    else:
        print("[CLIENT] Failed to connect to server")
        pygame.quit()


if __name__ == '__main__':
    main()
