# Tactical Squad Game

A turn-based tactical squad game built with Python and Pygame, featuring strategic combat, squad management, and mission-based gameplay. Inspired by Jagged Alliance and XCOM.

## Features

- **LLM-Optimized Architecture**: Single-file design for maximum AI assistant effectiveness
- **Tactical Combat**: Turn-based combat with action points, cover system, and line of sight
- **Squad Management**: Multiple character classes with unique abilities
- **Mission System**: Various objectives and dynamic scenarios
- **Modular Data**: JSON-based configuration for easy content modification

## Installation

1. Ensure you have Python 3.8+ installed
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Game

```bash
python main.py
```

## Controls

### During Combat:
- **Left Click**: Select unit or move to tile
- **Right Click**: Show tile information
- **SPACE**: End player turn
- **TAB**: Cycle through units
- **O**: Put active unit on overwatch

### Debug Controls (Available in any mode):
- **F1**: Quick save
- **F2**: Quick load
- **F3**: Toggle debug overlay (shows coordinates, line of sight)
- **F4**: Save debug snapshot
- **F5**: Validate game state
- **F12**: Dump error log

## Game Mechanics

### Action Points (AP)
Each unit has Action Points that determine what they can do per turn:
- **Move**: 1 AP per tile
- **Shoot**: 4 AP
- **Overwatch**: 3 AP
- **Reload**: 2 AP
- **Use Item**: 2 AP

### Combat System
- **Hit Chance**: Based on marksmanship, distance, cover, and target agility
- **Cover**: Tiles provide defensive bonuses (0-100%)
- **Line of Sight**: Units must have clear sight lines to attack
- **Overwatch**: Units can interrupt enemy movement

### Character Classes

#### Soldier (Balanced Fighter)
- Health: 100 | AP: 10
- High marksmanship and decent all-around stats
- Skills: Overwatch, Suppressing Fire

#### Sniper (Long-range Specialist)
- Health: 80 | AP: 8
- Exceptional marksmanship and accuracy
- Skills: Overwatch, Aimed Shot, Camouflage

#### Scout (Mobile Reconnaissance)
- Health: 90 | AP: 12
- High agility and movement speed
- Skills: Sprint, Spot, Smoke Grenade

#### Heavy Gunner (Defensive Support)
- Health: 120 | AP: 8
- High strength and heavy weapons
- Skills: Suppressing Fire, Heavy Weapons

#### Combat Medic (Support)
- Health: 85 | AP: 10
- High wisdom and medical abilities
- Skills: Medical Training, Stabilize, Field Surgery

## Project Structure

```
tactical_game/
├── main.py                 # ALL game logic (single file by design)
├── data/
│   ├── characters.json     # Character templates and stats
│   ├── weapons.json        # Weapon definitions
│   ├── items.json          # Equipment and consumables
│   ├── config.json         # Game configuration
│   ├── missions.json       # Mission definitions
│   └── maps/               # Map data files
│       └── map_01.json
├── assets/                 # Graphics and audio (to be added)
│   ├── sprites/
│   ├── tiles/
│   ├── ui/
│   └── sounds/
├── saves/                  # Save game files
└── requirements.txt        # Python dependencies
```

## Development Philosophy

This project follows an **LLM-Optimized Architecture**:

- **Single File Logic**: All game logic in `main.py` for complete context visibility
- **Data Separation**: Content and balance in JSON files, separate from logic
- **Explicit State**: Global variables and clear state mutations
- **Copy Don't Abstract**: Favor clarity over DRY principles
- **Document Side Effects**: Every function documents what it modifies

## Extending the Game

### Adding New Character Types
1. Add template to `data/characters.json`
2. New characters automatically available via `create_character()`

### Adding New Weapons
1. Add weapon to `data/weapons.json`
2. Implement any special mechanics in combat functions

### Creating New Missions
1. Add mission to `data/missions.json`
2. Create corresponding map file in `data/maps/`

### Adding New Mechanics
1. Add state to global variables section
2. Create handler function with full documentation
3. Hook into appropriate update/render functions

## Debug Features

The game includes extensive debugging capabilities:

- **State Snapshots**: Capture complete game state at any time
- **State Validation**: Check for inconsistencies and errors
- **Visual Debug Overlay**: Show coordinates, line of sight, paths
- **Error Logging**: Track and display all errors
- **Hot Reload**: Save/load during development

## Technical Details

- **Engine**: Pygame 2.1.0+
- **Line of Sight**: Bresenham's line algorithm
- **Pathfinding**: Simple grid-based movement (A* can be added later)
- **Save System**: JSON-based complete state serialization
- **Architecture**: Single-file with global state management

## Current Status

✅ **Implemented:**
- Basic tactical combat
- Unit movement and selection
- Action point system
- Line of sight calculations
- Save/load system
- Debug tools
- Data-driven content

🔄 **In Progress:**
- Complete AI system
- Combat effects and animations
- Item/equipment system
- Mission objectives

📋 **Planned:**
- Sound system
- Particle effects
- Multiple maps
- Campaign progression
- Advanced AI behaviors

## Contributing

This project is optimized for AI-assisted development. When making changes:

1. Keep all logic in `main.py`
2. Document side effects clearly
3. Use explicit state management
4. Test with debug tools (F1-F12)
5. Add JSON data rather than hardcoding values

The single-file architecture might seem unusual, but it enables rapid iteration and complete context awareness for AI assistants.

## License

This project is open source. Feel free to modify and extend it according to your needs. 