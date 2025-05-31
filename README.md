# FOGMOE

A simple Monopoly-style game supporting both single-player and LAN multiplayer modes, developed in Python using Pygame.

## Features

- **Single-Player Mode**: 1 human player versus 3 AI opponents  
- **Multiplayer Mode**: Up to 4 players over a local area network (LAN)  
- **Game Rules**  
  - Collect coins and return to your Home cell to win  
  - Victory condition: have 100 coins and land on your Home cell  
  - **Reward Cell** (Yellow): roll the dice to gain coins  
  - **Penalty Cell** (Dark Blue): roll the dice to lose coins  

## Quick Start

### Install Dependencies

```bash
pip install pygame
```

### Single-Player Game

```bash
python main.py
```

Click “Single Player” to begin.

### Multiplayer Game

1. **Start the Server** (on the host machine):
   ```bash
   python start_server.py
   ```
2. **Create or Join a Room**:
   - Run `python main.py`
   - Click “Multiplayer”
   - The host clicks “Create Room”
   - Other players click “Join Room” and enter the server’s IP address
3. **Begin the Game**:
   - The host clicks the “Start Game” button

## Project Structure

```
miniGame/
├── main.py                  # Main game program
├── start_server.py          # Game server launcher
├── test_multiplayer.py      # Multiplayer test script
├── game/                    # Game logic
│   ├── board.py             # Board definition
│   ├── game_logic.py        # Core game rules
│   └── network_game_logic.py # Networked game logic
├── models/                  # Data models
│   ├── player.py            # Player class
│   ├── cell.py              # Cell class
│   └── constants.py         # Game constants
├── network/                 # Networking components
│   ├── client.py            # Game client
│   ├── server.py            # Game server
│   └── protocol.py          # Network protocol definitions
└── ui/                      # User interface
    ├── renderer.py          # Rendering engine
    └── animations.py        # Animation manager
```

## Multiplayer Details

- Players are assigned as Player 1, 2, 3, and 4 in join order  
- Only the active player may roll the dice on their turn  
- AI actions are calculated by the host and synchronized to all clients  
- Game state is kept in sync across all clients in real time  

## System Requirements

- Python 3.7 or higher  
- Pygame 2.0 or higher  

## Notes

- All players must be on the same LAN  
- Ensure your firewall allows traffic on port 29188  
- The server must remain running while the game is in progress  

## License

This project is licensed under the GPL License.  
