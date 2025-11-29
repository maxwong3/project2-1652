"""
Shared game state module for multiplayer arena shooter.
Contains game entities, constants, and state management logic.
"""

import time
import math
from typing import Dict, List, Tuple, Optional

# Game Constants
ARENA_WIDTH = 800
ARENA_HEIGHT = 600
PLAYER_SIZE = 20
PLAYER_SPEED = 200  # pixels per second
BULLET_SIZE = 5
BULLET_SPEED = 400  # pixels per second
BULLET_LIFETIME = 3.0  # seconds
TICK_RATE = 30  # server ticks per second
RESPAWN_TIME = 3.0  # seconds


class Player:
    """Represents a player in the game."""

    def __init__(self, player_id: str, x: float, y: float):
        self.id = player_id
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.score = 0
        self.alive = True
        self.respawn_time = 0.0
        self.color = self._generate_color(player_id)

    def _generate_color(self, player_id: str) -> Tuple[int, int, int]:
        """Generate a unique color based on player ID."""
        hash_val = hash(player_id)
        r = (hash_val & 0xFF0000) >> 16
        g = (hash_val & 0x00FF00) >> 8
        b = (hash_val & 0x0000FF)
        # Ensure colors are bright enough
        r = max(100, r)
        g = max(100, g)
        b = max(100, b)
        return (r, g, b)

    def update(self, dt: float):
        """Update player position based on velocity."""
        if self.alive:
            self.x += self.vx * dt
            self.y += self.vy * dt

            # Keep player in bounds
            self.x = max(PLAYER_SIZE, min(ARENA_WIDTH - PLAYER_SIZE, self.x))
            self.y = max(PLAYER_SIZE, min(ARENA_HEIGHT - PLAYER_SIZE, self.y))

    def set_velocity(self, vx: float, vy: float):
        """Set player velocity based on input."""
        self.vx = vx
        self.vy = vy

    def kill(self):
        """Kill the player."""
        self.alive = False
        self.respawn_time = time.time() + RESPAWN_TIME

    def try_respawn(self) -> bool:
        """Try to respawn the player if respawn time has elapsed."""
        if not self.alive and time.time() >= self.respawn_time:
            self.alive = True
            # Respawn at random position
            import random
            self.x = random.randint(PLAYER_SIZE, ARENA_WIDTH - PLAYER_SIZE)
            self.y = random.randint(PLAYER_SIZE, ARENA_HEIGHT - PLAYER_SIZE)
            return True
        return False

    def to_dict(self) -> dict:
        """Convert player to dictionary for network transmission."""
        return {
            'id': self.id,
            'x': self.x,
            'y': self.y,
            'vx': self.vx,
            'vy': self.vy,
            'score': self.score,
            'alive': self.alive,
            'color': self.color
        }


class Bullet:
    """Represents a bullet in the game."""

    def __init__(self, bullet_id: str, owner_id: str, x: float, y: float,
                 vx: float, vy: float):
        self.id = bullet_id
        self.owner_id = owner_id
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.spawn_time = time.time()

    def update(self, dt: float):
        """Update bullet position."""
        self.x += self.vx * dt
        self.y += self.vy * dt

    def is_expired(self) -> bool:
        """Check if bullet has expired."""
        return (time.time() - self.spawn_time > BULLET_LIFETIME or
                self.x < 0 or self.x > ARENA_WIDTH or
                self.y < 0 or self.y > ARENA_HEIGHT)

    def to_dict(self) -> dict:
        """Convert bullet to dictionary for network transmission."""
        return {
            'id': self.id,
            'owner_id': self.owner_id,
            'x': self.x,
            'y': self.y,
            'vx': self.vx,
            'vy': self.vy
        }


class GameState:
    """Manages the complete game state."""

    def __init__(self):
        self.players: Dict[str, Player] = {}
        self.bullets: Dict[str, Bullet] = {}
        self.last_update = time.time()
        self.bullet_counter = 0

    def add_player(self, player_id: str) -> Player:
        """Add a new player to the game."""
        import random
        x = random.randint(PLAYER_SIZE, ARENA_WIDTH - PLAYER_SIZE)
        y = random.randint(PLAYER_SIZE, ARENA_HEIGHT - PLAYER_SIZE)
        player = Player(player_id, x, y)
        self.players[player_id] = player
        return player

    def remove_player(self, player_id: str):
        """Remove a player from the game."""
        if player_id in self.players:
            del self.players[player_id]

    def create_bullet(self, owner_id: str, direction: Tuple[float, float]) -> Optional[Bullet]:
        """Create a new bullet."""
        if owner_id not in self.players:
            return None

        player = self.players[owner_id]
        if not player.alive:
            return None

        # Normalize direction
        dx, dy = direction
        length = math.sqrt(dx * dx + dy * dy)
        if length == 0:
            return None

        dx /= length
        dy /= length

        # Create bullet
        bullet_id = f"{owner_id}_{self.bullet_counter}"
        self.bullet_counter += 1

        # Spawn bullet slightly in front of player
        offset = PLAYER_SIZE + BULLET_SIZE
        bullet = Bullet(
            bullet_id, owner_id,
            player.x + dx * offset,
            player.y + dy * offset,
            dx * BULLET_SPEED,
            dy * BULLET_SPEED
        )
        self.bullets[bullet_id] = bullet
        return bullet

    def update(self, dt: float):
        """Update all game entities."""
        # Update players
        for player in self.players.values():
            player.update(dt)
            player.try_respawn()

        # Update bullets
        expired_bullets = []
        for bullet_id, bullet in self.bullets.items():
            bullet.update(dt)
            if bullet.is_expired():
                expired_bullets.append(bullet_id)

        # Remove expired bullets
        for bullet_id in expired_bullets:
            del self.bullets[bullet_id]

        # Check collisions
        self._check_collisions()

    def _check_collisions(self):
        """Check for bullet-player collisions."""
        bullets_to_remove = []

        for bullet_id, bullet in self.bullets.items():
            for player_id, player in self.players.items():
                # Don't hit the shooter
                if player_id == bullet.owner_id or not player.alive:
                    continue

                # Check collision (simple circle collision)
                dx = bullet.x - player.x
                dy = bullet.y - player.y
                distance = math.sqrt(dx * dx + dy * dy)

                if distance < (PLAYER_SIZE + BULLET_SIZE):
                    # Hit!
                    player.kill()
                    bullets_to_remove.append(bullet_id)

                    # Award point to shooter
                    if bullet.owner_id in self.players:
                        self.players[bullet.owner_id].score += 1
                    break

        # Remove bullets that hit
        for bullet_id in bullets_to_remove:
            if bullet_id in self.bullets:
                del self.bullets[bullet_id]

    def to_dict(self) -> dict:
        """Convert game state to dictionary for network transmission."""
        return {
            'players': {pid: p.to_dict() for pid, p in self.players.items()},
            'bullets': {bid: b.to_dict() for bid, b in self.bullets.items()},
            'timestamp': time.time()
        }
