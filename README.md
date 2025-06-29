# Tactical Squad Game

A turn-based tactical combat game built with Python and Pygame, featuring comprehensive mission planning, squad customization, and strategic combat.

## 🎮 **Complete Mission System - NOW WORKING!**

The game features a fully functional mission planning system that launches on startup:

### **Mission Selection**
- Choose from multiple available missions
- View detailed mission briefings and objectives  
- See rewards and difficulty ratings
- Access to 3 complete missions with unique challenges

### **Squad Composition**
- **5 Character Classes** to choose from:
  - **Soldier** (Balanced Fighter): HP 100, AP 10 - High marksmanship, overwatch specialist
  - **Sniper** (Long-range Specialist): HP 80, AP 8 - Exceptional accuracy, aimed shot, camouflage
  - **Scout** (Mobile Reconnaissance): HP 90, AP 12 - High agility, sprint, smoke grenades
  - **Heavy Gunner** (Defensive Support): HP 120, AP 8 - High strength, heavy weapons
  - **Combat Medic** (Support): HP 85, AP 10 - Medical training, field surgery
- **Flexible Squad Size**: Deploy 1-4 team members based on mission requirements
- **Strategic Team Building**: Mix and match classes for different tactical approaches

### **Weapon Loadout System**
- **6 Weapon Types**: Assault Rifle, Sniper Rifle, SMG, Shotgun, LMG, Pistol
- **Individual Configuration**: Assign specific weapons to each squad member
- **Stat Comparison**: View damage, range, accuracy, and AP costs
- **Tactical Planning**: Match weapons to roles and mission requirements

### **Mission Briefing**
- Final review of squad composition and loadouts
- Mission objectives and tactical overview
- One-click deployment to tactical combat

## 🎯 **Controls**

### **Main Menu Navigation**
- **UP/DOWN**: Navigate menu options
- **ENTER**: Select option
- **ESC**: Go back/Exit

### **Mission Planning**
- **UP/DOWN**: Browse missions/options
- **LEFT/RIGHT**: Switch squad members (loadout screen)
- **ENTER**: Select/Confirm
- **ESC**: Previous screen

### **Tactical Combat**
- **Left Click**: Select unit or move to tile
- **Right Click**: Attack enemy unit
- **TAB**: Cycle through player units
- **SPACE**: End turn
- **R**: Reload weapon
- **O**: Activate overwatch
- **ESC**: Return to main menu

### **Debug Controls**
- **F1-F12**: Various debug functions and state snapshots

## 🛡️ **Combat System**

### **Core Mechanics**
- **Action Points (AP)**: Each unit has limited actions per turn
  - Move: 1 AP per tile
  - Attack: 4 AP
  - Overwatch: 3 AP
  - **Reload: 2 AP** *(NEW)*
- **Line of Sight**: Realistic visibility and shooting mechanics
- **Cover System**: Use terrain for defensive bonuses
- **Turn-Based**: Alternating player and AI turns

### **Weapon Ammunition System** *(NEW)*
- **Ammo Tracking**: Each weapon has limited ammunition capacity
- **Ammo Consumption**: Each shot consumes 1 round
- **Reload Action**: Press **R** to reload weapon (2 AP cost)
- **Visual Feedback**: Ammo counters show current/max ammo
- **Low Ammo Warnings**: Yellow/red indicators when running low
- **Out-of-Ammo**: Units cannot attack when ammo is depleted

### **Advanced Tactics**
- **Overwatch**: Set units to automatically fire on moving enemies
- **Flanking**: Attack from sides/behind for damage bonuses
- **Suppression**: Pin down enemies with heavy fire
- **Environmental Cover**: Walls provide 100% cover, crates 50%
- **Ammo Management**: Strategic reload timing and conservation

## 🤖 **Intelligent AI**

### **Layered AI Behaviors**
1. **Attack Priority**: Engage visible enemies, prioritize wounded targets
2. **Cover Seeking**: Move to positions with 20%+ cover when exposed
3. **Tactical Advance**: Move toward enemies when not in range
4. **Overwatch Positioning**: Set up defensive positions as fallback

### **AI Features**
- **Smart Target Selection**: Focus fire on weakened enemies
- **Terrain Awareness**: Uses cover effectively
- **Coordinated Movement**: Multiple AI units work together
- **Adaptive Difficulty**: Responds to player tactics

## 📊 **Data-Driven Design**

### **JSON Configuration**
- **Characters**: All classes defined in `data/characters.json`
- **Weapons**: Complete weapon stats in `data/weapons.json`
- **Missions**: Mission data and objectives in `data/missions.json`
- **Maps**: Level layouts and spawn points in `data/maps/`
- **Items**: Equipment and consumables in `data/items.json`

### **Save System**
- **Auto-saves**: Game state preserved between sessions
- **Debug Snapshots**: F1-F12 create development saves
- **State Validation**: Robust error checking and recovery

## 🎨 **Visual Features**

- **Clean UI**: Modern, responsive interface design
- **Visual Effects**: Damage numbers, hit/miss indicators
- **Color-Coded Information**: Health, AP, faction identification
- **Debug Overlay**: Development information (F3 to toggle)
- **Smooth Navigation**: Intuitive menu flow

## 🔧 **Technical Features**

### **LLM-Optimized Architecture**
- **Single File Logic**: Complete game in `main.py` for AI comprehension
- **Explicit State Management**: All global state documented
- **Data Separation**: Logic and data cleanly separated
- **Copy-Don't-Abstract**: Clear, maintainable code patterns

### **Robust Systems**
- **Error Handling**: Graceful degradation on data issues
- **State Validation**: Comprehensive game state checking
- **Debug Tools**: Extensive logging and development features
- **Modular Design**: Easy to extend with new content

## 🚀 **Getting Started**

### **Installation**
```bash
pip install -r requirements.txt
```

### **Run Game**
```bash
python main.py
```

### **Quick Start**
1. **Launch Game**: Start with `python main.py`
2. **Main Menu**: Choose "Start Mission" or "Quick Battle (Test)"
3. **Choose Mission**: Pick your tactical challenge
4. **Build Squad**: Select 1-4 operatives from 5 classes
5. **Equip Team**: Assign weapons and gear
6. **Deploy**: Review briefing and start combat!

### **Development Mode**
- Use **"Quick Battle (Test)"** from main menu for immediate combat testing
- F1-F12 keys create debug snapshots
- F3 toggles debug overlay

## 📁 **Project Structure**

```
IG1/
├── main.py              # Complete game logic
├── data/                # JSON configuration files
│   ├── characters.json  # Character classes and stats
│   ├── weapons.json     # Weapon specifications
│   ├── missions.json    # Mission definitions
│   ├── items.json       # Equipment and consumables
│   └── maps/            # Level data and layouts
├── saves/               # Save files and snapshots
├── assets/              # Graphics and audio (future)
└── requirements.txt     # Python dependencies
```

## 🎯 **Mission Types**

### **Available Missions**
1. **Search and Destroy**: Eliminate all enemy forces
2. **Rescue Operation**: Extract civilians from hostile territory  
3. **Data Recovery**: Secure intelligence from enemy compound

Each mission features:
- **Unique Objectives**: Varied tactical challenges
- **Custom Maps**: Specialized terrain and layouts
- **Dynamic Enemies**: Different AI compositions
- **Reward Systems**: Cash and equipment incentives

## 🏆 **Features Completed**

✅ **Complete Menu System**: Mission selection through deployment - **NOW WORKING!**  
✅ **Squad Customization**: 5 classes, flexible team building  
✅ **Weapon Loadouts**: Individual equipment assignment  
✅ **Tactical Combat**: Turn-based combat with AP system  
✅ **Intelligent AI**: Multi-layered enemy behavior  
✅ **Line of Sight**: Realistic visibility mechanics  
✅ **Cover System**: Environmental tactical advantages  
✅ **Save/Load**: Persistent game state  
✅ **Debug Tools**: Development and testing features  
✅ **Right-Click Combat**: Direct attack system with AP costs  
✅ **Visual Combat Effects**: Damage numbers and hit indicators  
✅ **Weapon Ammunition System**: Ammo tracking, reload mechanics, visual feedback *(NEW)*

## 🔮 **Future Enhancements**

- **Campaign Mode**: Persistent squad progression
- **Equipment Upgrades**: Weapon modifications and armor
- **Skill Trees**: Character advancement systems
- **Multiplayer**: Online tactical combat
- **Map Editor**: Custom scenario creation
- **Sound Effects**: Audio feedback and music
- **Animations**: Smooth movement and combat visuals

---

**Built with the LLM-Optimized Architecture for maximum AI comprehension and maintainability.** 