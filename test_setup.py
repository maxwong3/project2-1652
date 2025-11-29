"""
Simple test script to verify the setup is correct.
Run this before starting the game to check dependencies.
"""

import sys

print("=" * 50)
print("Testing Multiplayer Arena Shooter Setup")
print("=" * 50)

# Check Python version
print(f"\n1. Python Version: {sys.version}")
major, minor = sys.version_info[:2]
if major >= 3 and minor >= 7:
    print("   ✓ Python version is compatible")
else:
    print("   ✗ Python 3.7 or higher required")
    sys.exit(1)

# Check pygame
try:
    import pygame
    print(f"\n2. Pygame: {pygame.__version__}")
    print("   ✓ Pygame is installed")
except ImportError:
    print("\n2. Pygame: Not installed")
    print("   ✗ Please install pygame: pip install pygame")
    sys.exit(1)

# Check game modules
try:
    import game_state
    print("\n3. Game State Module:")
    print(f"   Arena: {game_state.ARENA_WIDTH}x{game_state.ARENA_HEIGHT}")
    print(f"   Tick Rate: {game_state.TICK_RATE} TPS")
    print("   ✓ Game state module loaded")
except ImportError as e:
    print(f"\n3. Game State Module: Error - {e}")
    sys.exit(1)

# Check server module
try:
    import server
    print("\n4. Server Module:")
    print(f"   Default Port: {server.PORT}")
    print("   ✓ Server module loaded")
except ImportError as e:
    print(f"\n4. Server Module: Error - {e}")
    sys.exit(1)

# Check client module
try:
    import client
    print("\n5. Client Module:")
    print(f"   Default Host: {client.DEFAULT_HOST}")
    print(f"   Default Port: {client.DEFAULT_PORT}")
    print(f"   Target FPS: {client.FPS}")
    print("   ✓ Client module loaded")
except ImportError as e:
    print(f"\n5. Client Module: Error - {e}")
    sys.exit(1)

print("\n" + "=" * 50)
print("All checks passed! You're ready to play.")
print("=" * 50)
print("\nQuick Start:")
print("1. In one terminal: python server.py")
print("2. In another terminal: python client.py")
print("3. Open more terminals for more players!")
print("\nHave fun!")
