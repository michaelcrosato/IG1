"""Tactical Squad Game - Single File Architecture
All game logic intentionally in one file for LLM optimization.
See framework documentation for design rationale.

Navigation: Use Ctrl+F with section markers like [03] to jump between sections.
"""

# ======================================================================
# === [00] IMPORTS
# ======================================================================
import pygame
import json
import math
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Any
from copy import deepcopy
import random
import os

# ======================================================================
# === [01] CONFIGURATION NAMESPACE
# ======================================================================
class Cfg:
    """All game constants in one place"""
    # Display
    SCREEN_WIDTH = 1280
    SCREEN_HEIGHT = 720
    TILE_SIZE = 32
    FPS = 60
    DEBUG_OVERLAY = False  # Toggle with F3
    
    # Combat
    BASE_HIT_CHANCE = 75
    CRIT_MULTIPLIER = 2.0
    
    # Action Point Costs
    AP_COST_MOVE = 1
    AP_COST_SHOOT = 4
    AP_COST_OVERWATCH = 3
    AP_COST_RELOAD = 2
    AP_COST_CROUCH = 1
    
    # File paths
    SAVE_FILE = "saves/current_game.json"
    SNAPSHOT_DIR = "saves/snapshots/"

# ======================================================================
# === [02] KEY CONSTANTS (Prevent typos in dict access)
# ======================================================================
# Character keys
K_ID = 'id'
K_NAME = 'name'
K_HP = 'health'
K_MAX_HP = 'max_health'
K_AP = 'ap'
K_MAX_AP = 'max_ap'
K_X = 'x'
K_Y = 'y'
K_FACTION = 'faction'
K_STATUS = 'status_effects'
K_INVENTORY = 'inventory'
K_EQUIPMENT = 'equipment'

# Ammo tracking keys
K_CURRENT_AMMO = 'current_ammo'
K_MAX_AMMO = 'max_ammo'
K_WEAPON_TYPE = 'weapon_type'

# Character attributes
K_MARKSMANSHIP = 'marksmanship'
K_AGILITY = 'agility'
K_DEXTERITY = 'dexterity'
K_STRENGTH = 'strength'
K_WISDOM = 'wisdom'

# Map tile keys
K_TYPE = 'type'
K_COVER = 'cover'
K_BLOCKS_SIGHT = 'blocks_sight'
K_BLOCKS_MOVE = 'blocks_movement'
K_MOVE_COST = 'movement_cost'

# ======================================================================
# === [03] GLOBAL STATE VARIABLES
# ======================================================================
# Game State - ALL mutable state goes here
g_game_state = {
    'current_state': 'main_menu',  # GameState value
    'score': 0,
    'turn_count': 0,
    'active_unit_id': None,
    'selected_tile': None,
    'camera_offset': (0, 0),
    'combat_log': [],
    'ui_state': {
        'show_inventory': False,
        'selected_menu_item': 0,
        'tooltip_text': "",
        'debug_overlay': False,
    },
    'menu_state': {
        'selected_mission': None,
        'selected_mission_id': None,
        'squad_slots': [None, None, None],  # Will expand based on mission
        'squad_loadouts': [{}, {}, {}],     # Weapons/equipment per slot
        'max_squad_size': 3,
        'current_slot': 0,
        'current_loadout_slot': 0,
        'available_classes': ['soldier', 'sniper', 'scout', 'heavy', 'medic'],
    }
}

# Entities
g_player_squad: List[dict] = []  # Player's units
g_enemy_units: List[dict] = []   # Current mission enemies
g_current_map: List[List[dict]] = []  # Current map tiles
g_projectiles: List[dict] = []   # Active projectiles
g_effect_queue: List[dict] = []  # Queued visual effects
g_floating_texts: List[dict] = []  # Damage numbers, etc.

# Systems
g_screen: pygame.Surface = None
g_clock: pygame.time.Clock = None
g_font: pygame.font.Font = None
g_sounds: Dict[str, pygame.mixer.Sound] = {}

# Cached Data
g_unit_templates: Dict[str, dict] = {}  # Loaded from characters.json
g_weapon_data: Dict[str, dict] = {}     # Loaded from weapons.json
g_mission_data: Dict[str, dict] = {}    # Loaded from missions.json

# Debug & Development
g_error_log: List[str] = []  # Error tracking
g_debug_lines: List[dict] = []  # Visual debug lines (LoS, paths, etc.)

# ======================================================================
# === [04] UTILITY FUNCTIONS
# ======================================================================
def log_error(message: str):
    """Log error to console and error list.
    
    Side effects:
        Appends to g_error_log
        Prints to console
    """
    error_msg = f"[ERROR] {message}"
    g_error_log.append(error_msg)
    print(error_msg)

def safe_load_json(path: str, fallback: Any = None) -> Any:
    """Load JSON file with error handling.
    
    Returns:
        Loaded data or fallback value if error
    """
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        log_error(f"Failed to load {path}: {e}")
        return fallback if fallback is not None else {}

def save_state_snapshot(tag: str = ""):
    """Save complete game state for debugging.
    
    Side effects:
        Creates snapshot file in saves/snapshots/
        
    Globals:
        Reads: All game state
    """
    os.makedirs(Cfg.SNAPSHOT_DIR, exist_ok=True)
    timestamp = pygame.time.get_ticks()
    filename = f"{Cfg.SNAPSHOT_DIR}snapshot_{timestamp}_{tag}.json"
    
    snapshot = {
        'game_state': g_game_state,
        'player_squad': g_player_squad,
        'enemy_units': g_enemy_units,
        'timestamp': timestamp,
        'tag': tag
    }
    
    try:
        with open(filename, 'w') as f:
            json.dump(snapshot, f, indent=2)
        print(f"[DEBUG] Saved snapshot: {filename}")
    except Exception as e:
        log_error(f"Failed to save snapshot: {e}")

def validate_game_state():
    """Check game state consistency.
    
    Side effects:
        Logs errors for any inconsistencies
        
    Globals:
        Reads: All entity lists and game state
    """
    # Check for duplicate unit IDs
    all_units = g_player_squad + g_enemy_units
    unit_ids = [unit[K_ID] for unit in all_units]
    if len(unit_ids) != len(set(unit_ids)):
        log_error("Duplicate unit IDs detected")
    
    # Check units are within map bounds
    if g_current_map:
        map_height = len(g_current_map)
        map_width = len(g_current_map[0]) if map_height > 0 else 0
        
        for unit in all_units:
            if not (0 <= unit[K_X] < map_width and 0 <= unit[K_Y] < map_height):
                log_error(f"Unit {unit[K_ID]} out of bounds at ({unit[K_X]}, {unit[K_Y]})")
    
    # Check active unit exists
    if g_game_state['active_unit_id']:
        if not find_unit_by_id(g_game_state['active_unit_id']):
            log_error(f"Active unit {g_game_state['active_unit_id']} not found")

# ======================================================================
# === [05] GAME STATE MANAGEMENT
# ======================================================================
class GameState(Enum):
    MAIN_MENU = "main_menu"
    MISSION_SELECTION = "mission_selection"
    SQUAD_SELECTION = "squad_selection"
    LOADOUT_SCREEN = "loadout_screen"
    MISSION_BRIEFING = "mission_briefing"
    TACTICAL_COMBAT = "tactical_combat"
    ENEMY_TURN = "enemy_turn"
    SETTINGS = "settings"
    GAME_OVER = "game_over"

# ======================================================================
# === [06] DATA STRUCTURES
# ======================================================================
# Type aliases for clarity
Character = Dict[str, Any]
Tile = Dict[str, Any]
Effect = Dict[str, Any]

def create_character(template_id: str, x: int, y: int) -> Character:
    """Create character from template.
    
    Args:
        template_id: Key from characters.json 'templates' (e.g., 'soldier')
        x, y: Initial tile coordinates
        
    Returns:
        Character dict with all properties
    
    Side effects:
        None - returns new dict
        
    Globals:
        Reads: g_unit_templates (cached from characters.json)
    """
    # Deep copy template to avoid mutations
    template = deepcopy(g_unit_templates.get(template_id, {}))
    
    return {
        K_ID: f"unit_{random.randint(1000, 9999)}",
        'template_id': template_id,
        K_NAME: template.get('name', 'Unknown'),
        K_X: x,
        K_Y: y,
        K_HP: template.get('base_stats', {}).get('health', 100),
        K_MAX_HP: template.get('base_stats', {}).get('health', 100),
        K_AP: template.get('base_stats', {}).get('action_points', 10),
        K_MAX_AP: template.get('base_stats', {}).get('action_points', 10),
        K_FACTION: 'player',
        K_STATUS: [],  # ['overwatch', 'suppressed', etc.]
        K_EQUIPMENT: {
            'primary_weapon': None,
            'armor': None
        },
        K_INVENTORY: [],
        # Initialize ammo tracking
        K_CURRENT_AMMO: 0,
        K_MAX_AMMO: 0,
        K_WEAPON_TYPE: None,
        'attributes': template.get('attributes', {
            K_MARKSMANSHIP: 70,
            K_AGILITY: 60,
            K_DEXTERITY: 60,
            K_STRENGTH: 60,
            K_WISDOM: 50
        }),
        'sprite': template.get('sprite', 'default.png')
    }

def create_effect(effect_type: str, x: int, y: int, **kwargs) -> Effect:
    """Create a visual effect for the effect queue.
    
    Side effects:
        None - returns new dict
    """
    return {
        'type': effect_type,
        'x': x,
        'y': y,
        'frame': 0,
        'max_frames': kwargs.get('duration', 30),
        'data': kwargs
    }

# ======================================================================
# === [07] CORE GAME LOOP
# ======================================================================
def main():
    """Entry point and main game loop.
    
    Side effects:
        Initializes pygame
        Modifies all global state
    """
    global g_screen, g_clock, g_font
    
    pygame.init()
    g_screen = pygame.display.set_mode((Cfg.SCREEN_WIDTH, Cfg.SCREEN_HEIGHT))
    g_clock = pygame.time.Clock()
    g_font = pygame.font.Font(None, 24)
    pygame.display.set_caption("Tactical Squad Game")
    
    # Start in main menu (test game available as "Quick Battle" option)
    g_game_state['current_state'] = GameState.MAIN_MENU.value
    
    running = True
    while running:
        # Handle input
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            else:
                handle_input(event)
        
        # Update
        update_game_state()
        
        # Render
        render_frame()
        
        g_clock.tick(Cfg.FPS)
    
    pygame.quit()

def start_selected_mission():
    """Start the mission with player's selected squad and loadouts.
    
    Side effects:
        Creates squad from menu selections
        Loads selected map and enemies
        Transitions to tactical combat
        
    Globals:
        Reads: g_game_state menu selections
        Writes: g_player_squad, g_enemy_units, g_current_map, g_game_state
    """
    global g_player_squad, g_enemy_units, g_current_map, g_game_state
    
    menu_state = g_game_state['menu_state']
    mission = menu_state['selected_mission']
    
    # Clear existing units
    g_player_squad = []
    g_enemy_units = []
    
    # Create player squad from selections
    spawn_positions = [(2, 2), (3, 2), (4, 2), (2, 3), (3, 3), (4, 3)]  # Default spawn area
    
    for i, class_name in enumerate(menu_state['squad_slots']):
        if class_name is not None and i < len(spawn_positions):
            # Create character
            x, y = spawn_positions[i]
            unit = create_character(class_name, x, y)
            
            # Apply weapon loadout
            loadout = menu_state['squad_loadouts'][i]
            if loadout.get('primary_weapon'):
                weapon_id = loadout['primary_weapon']
                unit[K_EQUIPMENT]['primary_weapon'] = weapon_id
                # Initialize ammo for the weapon
                initialize_unit_ammo(unit, weapon_id)
            
            g_player_squad.append(unit)
    
    # Load map (use first available map for now, could be mission-specific)
    map_file = mission.get('map_file', 'map_01')
    load_map(map_file)
    
    # Set first unit as active
    if g_player_squad:
        g_game_state['active_unit_id'] = g_player_squad[0][K_ID]
    
    # Clear combat log and reset turn counter
    g_game_state['combat_log'] = []
    g_game_state['turn_count'] = 1
    
    # Transition to combat
    g_game_state['current_state'] = GameState.TACTICAL_COMBAT.value
    
    print(f"[MISSION] Started '{mission['name']}' with {len(g_player_squad)} squad members")
    g_game_state['combat_log'].append(f"Mission '{mission['name']}' begins!")

def load_map(map_name: str):
    """Load a map from JSON file.
    
    Side effects:
        Replaces g_current_map
        Spawns units based on map data
        
    Globals:
        Writes: g_current_map, g_enemy_units
    """
    global g_current_map, g_enemy_units
    
    map_data = safe_load_json(f'data/maps/{map_name}.json', {})
    if not map_data:
        log_error(f"Failed to load map: {map_name}")
        # Create default map if load fails
        init_default_map()
        return
    
    # Create map from data or use simple generation for now
    map_width = map_data.get('width', 20)
    map_height = map_data.get('height', 15)
    
    g_current_map = []
    for y in range(map_height):
        row = []
        for x in range(map_width):
            # Create tiles based on pattern (simplified for now)
            if x == 10 and 5 <= y <= 10:  # Vertical wall
                tile = {K_TYPE: 'wall', K_COVER: 100, K_BLOCKS_SIGHT: True, K_BLOCKS_MOVE: True}
            elif (x == 5 or x == 15) and (y == 3 or y == 12):  # Some crates
                tile = {K_TYPE: 'crate', K_COVER: 50, K_BLOCKS_SIGHT: False, K_BLOCKS_MOVE: True}
            else:
                tile = {K_TYPE: 'floor', K_COVER: 0, K_BLOCKS_SIGHT: False, K_BLOCKS_MOVE: False}
            row.append(tile)
        g_current_map.append(row)
    
    # Spawn enemies from map data
    for spawn in map_data.get('enemy_spawns', []):
        enemy = create_character(spawn['template'], spawn['x'], spawn['y'])
        enemy[K_FACTION] = 'enemy'
        
        # Give enemies default weapons and ammo
        default_weapon = 'assault_rifle'  # Default enemy weapon
        enemy[K_EQUIPMENT]['primary_weapon'] = default_weapon
        initialize_unit_ammo(enemy, default_weapon)
        
        g_enemy_units.append(enemy)
    
    print(f"[MAP] Loaded {map_name} ({map_width}x{map_height}) with {len(g_enemy_units)} enemies")

def init_default_map():
    """Create a default map if map loading fails."""
    global g_current_map
    
    g_current_map = []
    for y in range(15):
        row = []
        for x in range(20):
            if x == 10 and 5 <= y <= 10:  # Vertical wall
                tile = {K_TYPE: 'wall', K_COVER: 100, K_BLOCKS_SIGHT: True, K_BLOCKS_MOVE: True}
            elif (x == 5 or x == 15) and (y == 3 or y == 12):  # Some crates
                tile = {K_TYPE: 'crate', K_COVER: 50, K_BLOCKS_SIGHT: False, K_BLOCKS_MOVE: True}
            else:
                tile = {K_TYPE: 'floor', K_COVER: 0, K_BLOCKS_SIGHT: False, K_BLOCKS_MOVE: False}
            row.append(tile)
        g_current_map.append(row)

def init_test_game():
    """Initialize a test game for development.
    
    Side effects:
        Creates test squad and map
        Sets game state to combat
        
    Globals:
        Writes: g_player_squad, g_enemy_units, g_current_map, g_game_state
    """
    global g_player_squad, g_enemy_units, g_current_map, g_game_state
    
    # Create test map (20x15 grid)
    g_current_map = []
    for y in range(15):
        row = []
        for x in range(20):
            # Create some cover and walls for testing
            if x == 10 and 5 <= y <= 10:  # Vertical wall
                tile = {K_TYPE: 'wall', K_COVER: 100, K_BLOCKS_SIGHT: True, K_BLOCKS_MOVE: True}
            elif (x == 5 or x == 15) and (y == 3 or y == 12):  # Some crates
                tile = {K_TYPE: 'crate', K_COVER: 50, K_BLOCKS_SIGHT: False, K_BLOCKS_MOVE: True}
            else:
                tile = {K_TYPE: 'floor', K_COVER: 0, K_BLOCKS_SIGHT: False, K_BLOCKS_MOVE: False}
            row.append(tile)
        g_current_map.append(row)
    
    # Create test squad
    g_player_squad = [
        create_character('soldier', 2, 2),
        create_character('soldier', 3, 2),
        create_character('soldier', 4, 2)
    ]
    
    # Give test squad weapons and ammo
    for unit in g_player_squad:
        unit[K_EQUIPMENT]['primary_weapon'] = 'assault_rifle'
        initialize_unit_ammo(unit, 'assault_rifle')
    
    # Create enemy units
    g_enemy_units = []
    enemy1 = create_character('soldier', 17, 12)
    enemy1[K_FACTION] = 'enemy'
    enemy1[K_EQUIPMENT]['primary_weapon'] = 'assault_rifle'
    initialize_unit_ammo(enemy1, 'assault_rifle')
    g_enemy_units.append(enemy1)
    
    enemy2 = create_character('soldier', 18, 11)
    enemy2[K_FACTION] = 'enemy'
    enemy2[K_EQUIPMENT]['primary_weapon'] = 'assault_rifle'
    initialize_unit_ammo(enemy2, 'assault_rifle')
    g_enemy_units.append(enemy2)
    
    # Set first unit as active
    if g_player_squad:
        g_game_state['active_unit_id'] = g_player_squad[0][K_ID]
    
    # Start in combat mode for testing
    g_game_state['current_state'] = GameState.TACTICAL_COMBAT.value
    
    print("[INIT] Test game initialized with 3 soldiers vs 2 enemies")

# ======================================================================
# === [08] INPUT HANDLING
# ======================================================================
def handle_input(event: pygame.event.Event):
    """Process input based on current game state.
    
    Side effects:
        Modifies g_game_state based on input
        
    Globals:
        Reads: g_game_state
        Writes: g_game_state
    """
    current_state = GameState(g_game_state['current_state'])
    
    # Global debug keys (work in any state)
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_F1:
            # Quick save
            save_game()
        elif event.key == pygame.K_F2:
            # Quick load
            load_game()
        elif event.key == pygame.K_F3:
            # Toggle debug overlay
            g_game_state['ui_state']['debug_overlay'] = not g_game_state['ui_state']['debug_overlay']
            print(f"[DEBUG] Overlay: {g_game_state['ui_state']['debug_overlay']}")
        elif event.key == pygame.K_F4:
            # Save debug snapshot
            save_state_snapshot("manual")
        elif event.key == pygame.K_F5:
            # Validate state
            validate_game_state()
        elif event.key == pygame.K_F12:
            # Dump error log
            print("\n=== ERROR LOG ===")
            for error in g_error_log[-20:]:  # Last 20 errors
                print(error)
            print("=================\n")
    
    # State-specific input handling
    if current_state == GameState.MAIN_MENU:
        handle_main_menu_input(event)
    elif current_state == GameState.MISSION_SELECTION:
        handle_mission_selection_input(event)
    elif current_state == GameState.SQUAD_SELECTION:
        handle_squad_selection_input(event)
    elif current_state == GameState.LOADOUT_SCREEN:
        handle_loadout_input(event)
    elif current_state == GameState.MISSION_BRIEFING:
        handle_briefing_input(event)
    elif current_state == GameState.SETTINGS:
        handle_settings_input(event)
    elif current_state == GameState.TACTICAL_COMBAT:
        handle_combat_input(event)

def handle_combat_input(event: pygame.event.Event):
    """Handle input during combat.
    
    Side effects:
        Modifies unit positions, triggers actions
        
    Globals:
        Reads: g_game_state, g_player_squad
        Writes: Various based on action
    """
    if event.type == pygame.MOUSEBUTTONDOWN:
        # Convert mouse to tile coordinates
        tile_x = event.pos[0] // Cfg.TILE_SIZE
        tile_y = event.pos[1] // Cfg.TILE_SIZE
        
        if event.button == 1:  # Left click
            handle_tile_click(tile_x, tile_y)
        elif event.button == 3:  # Right click
            handle_tile_right_click(tile_x, tile_y)
    
    elif event.type == pygame.KEYDOWN:
        if event.key == pygame.K_SPACE:
            # End turn
            end_player_turn()
        elif event.key == pygame.K_o:
            # Overwatch mode
            if g_game_state['active_unit_id']:
                activate_overwatch(g_game_state['active_unit_id'])
        elif event.key == pygame.K_r:
            # Reload weapon
            if g_game_state['active_unit_id']:
                reload_weapon(g_game_state['active_unit_id'])
        elif event.key == pygame.K_TAB:
            # Cycle through units
            cycle_active_unit()

def handle_tile_click(x: int, y: int):
    """Handle left click on tile.
    
    Side effects:
        May move active unit or select new unit
        
    Globals:
        Reads: g_game_state, g_player_squad
        Writes: g_game_state, unit positions
    """
    # Check if clicking on a unit
    clicked_unit = None
    for unit in g_player_squad:
        if unit[K_X] == x and unit[K_Y] == y:
            clicked_unit = unit
            break
    
    if clicked_unit:
        # Select this unit
        g_game_state['active_unit_id'] = clicked_unit[K_ID]
        print(f"[INPUT] Selected {clicked_unit[K_NAME]}")
    else:
        # Try to move active unit
        if g_game_state['active_unit_id']:
            active_unit = find_unit_by_id(g_game_state['active_unit_id'])
            if active_unit and is_valid_position(x, y) and not is_position_occupied(x, y):
                if can_reach_position(active_unit, x, y):
                    move_unit(active_unit[K_ID], x, y)
                    print(f"[INPUT] Moved {active_unit[K_NAME]} to ({x}, {y})")
                else:
                    print(f"[INPUT] Cannot reach ({x}, {y}) - not enough AP")
            elif is_position_occupied(x, y):
                print(f"[INPUT] Position ({x}, {y}) is occupied")

def handle_tile_right_click(x: int, y: int):
    """Handle right click on tile - Attack if enemy present.
    
    Side effects:
        May execute attack if valid target
        
    Globals:
        Reads: g_game_state, g_enemy_units
        Writes: Various if attack occurs
    """
    # Check if there's an enemy at this position
    target_enemy = None
    for enemy in g_enemy_units:
        if enemy[K_X] == x and enemy[K_Y] == y and enemy[K_HP] > 0:
            target_enemy = enemy
            break
    
    if target_enemy and g_game_state['active_unit_id']:
        active_unit = find_unit_by_id(g_game_state['active_unit_id'])
        if active_unit and active_unit[K_AP] >= Cfg.AP_COST_SHOOT:
            # Check line of sight
            if has_line_of_sight(active_unit[K_X], active_unit[K_Y], x, y):
                execute_attack(active_unit[K_ID], target_enemy[K_ID])
                active_unit[K_AP] -= Cfg.AP_COST_SHOOT
                print(f"[COMBAT] {active_unit[K_NAME]} attacks {target_enemy[K_NAME]}!")
            else:
                print(f"[COMBAT] No line of sight to target!")
                g_game_state['combat_log'].append("No line of sight to target")
        else:
            print(f"[COMBAT] Not enough AP to shoot (need {Cfg.AP_COST_SHOOT})")
            g_game_state['combat_log'].append("Not enough AP to shoot")
    else:
        # Show tile info if no enemy
        if is_valid_position(x, y):
            tile = g_current_map[y][x]
            print(f"[INPUT] Tile ({x}, {y}): {tile[K_TYPE]}, Cover: {tile.get(K_COVER, 0)}")
            g_game_state['combat_log'].append(f"Tile ({x}, {y}): {tile[K_TYPE]}, Cover: {tile.get(K_COVER, 0)}")

def cycle_active_unit():
    """Cycle to next available unit.
    
    Side effects:
        Changes active unit
        
    Globals:
        Reads: g_player_squad, g_game_state
        Writes: g_game_state
    """
    if not g_player_squad:
        return
    
    current_id = g_game_state['active_unit_id']
    current_index = -1
    
    # Find current unit index
    for i, unit in enumerate(g_player_squad):
        if unit[K_ID] == current_id:
            current_index = i
            break
    
    # Move to next unit (wrap around)
    next_index = (current_index + 1) % len(g_player_squad)
    g_game_state['active_unit_id'] = g_player_squad[next_index][K_ID]
    print(f"[INPUT] Switched to {g_player_squad[next_index][K_NAME]}")

# ======================================================================
# === [09] UPDATE FUNCTIONS
# ======================================================================
def update_game_state():
    """Update all game systems.
    
    Side effects:
        Modifies all entity lists and game state
        
    Globals:
        Reads: All globals
        Writes: All globals
    """
    current_state = GameState(g_game_state['current_state'])
    
    if current_state == GameState.TACTICAL_COMBAT:
        update_combat()
        update_projectiles()
        update_effects()
    elif current_state == GameState.ENEMY_TURN:
        update_enemy_ai()

def update_combat():
    """Update combat state.
    
    Side effects:
        May change game state or unit states
        
    Globals:
        Reads: g_player_squad, g_enemy_units
        Writes: g_game_state
    """
    # Check win/lose conditions
    alive_players = [u for u in g_player_squad if u[K_HP] > 0]
    alive_enemies = [u for u in g_enemy_units if u[K_HP] > 0]
    
    if not alive_players:
        g_game_state['current_state'] = GameState.GAME_OVER.value
        print("[COMBAT] Game Over - All squad members eliminated")
    elif not alive_enemies:
        print("[COMBAT] Victory - All enemies eliminated")
        # Could transition to mission complete screen

def update_projectiles():
    """Update projectile positions.
    
    Side effects:
        Modifies g_projectiles
        
    Globals:
        Reads: g_projectiles
        Writes: g_projectiles
    """
    for projectile in g_projectiles[:]:  # Copy list to avoid modification during iteration
        projectile['frame'] += 1
        if projectile['frame'] >= projectile['max_frames']:
            g_projectiles.remove(projectile)

def update_effects():
    """Update visual effects.
    
    Side effects:
        Modifies g_effect_queue
        
    Globals:
        Reads: g_effect_queue
        Writes: g_effect_queue
    """
    for effect in g_effect_queue[:]:  # Copy list to avoid modification during iteration
        effect['frame'] += 1
        if effect['frame'] >= effect['max_frames']:
            g_effect_queue.remove(effect)

def update_enemy_ai():
    """Process AI turns using layered behaviors.
    
    Side effects:
        Modifies enemy positions and states
        May trigger attacks
        
    Globals:
        Reads: g_enemy_units, g_player_squad
        Writes: g_enemy_units, g_game_state
    """
    # Process each enemy unit's turn
    enemies_with_ap = [e for e in g_enemy_units if e[K_HP] > 0 and e[K_AP] > 0]
    
    if enemies_with_ap:
        # Process one enemy at a time
        for enemy in enemies_with_ap:
            if enemy[K_AP] > 0:
                ai_take_turn(enemy)
                break  # Only process one enemy per frame to avoid long delays
    else:
        # All enemies done, end AI turn
        end_enemy_turn()

def end_enemy_turn():
    """End enemy turn and start player turn.
    
    Side effects:
        Resets AP for all units
        Changes game state
        
    Globals:
        Writes: g_player_squad, g_enemy_units, g_game_state
    """
    # Reset AP for all units
    for unit in g_player_squad:
        unit[K_AP] = unit[K_MAX_AP]
    
    for unit in g_enemy_units:
        unit[K_AP] = unit[K_MAX_AP]
        # Clear overwatch status at turn end
        if 'overwatch' in unit[K_STATUS]:
            unit[K_STATUS].remove('overwatch')
    
    # Clear player overwatch too
    for unit in g_player_squad:
        if 'overwatch' in unit[K_STATUS]:
            unit[K_STATUS].remove('overwatch')
    
    g_game_state['current_state'] = GameState.TACTICAL_COMBAT.value
    g_game_state['turn_count'] += 1
    g_game_state['combat_log'].append(f"Turn {g_game_state['turn_count']} begins")
    print(f"[AI] Turn {g_game_state['turn_count']} - Player turn begins")

def ai_take_turn(unit: Character):
    """Execute AI behavior for one unit using priority layers.
    
    Side effects:
        Modifies unit state
        May trigger combat or movement
        
    Globals:
        Various based on actions taken
    """
    print(f"[AI] {unit[K_NAME]} taking turn (AP: {unit[K_AP]})")
    
    # Layer 1: Try to attack if possible
    if ai_try_attack_visible_enemy(unit):
        return
    
    # Layer 2: Try to take cover if under fire or exposed
    if ai_try_take_cover(unit):
        return
    
    # Layer 3: Move toward nearest enemy
    if ai_try_move_to_enemy(unit):
        return
    
    # Layer 4: Set up overwatch as fallback
    if unit[K_AP] >= Cfg.AP_COST_OVERWATCH:
        activate_overwatch(unit[K_ID])
        unit[K_AP] = 0  # End turn after overwatch
    else:
        # End turn if nothing else to do
        unit[K_AP] = 0

def ai_try_attack_visible_enemy(unit: Character) -> bool:
    """Try to attack any visible enemy.
    
    Returns:
        True if attacked, False otherwise
    """
    if unit[K_AP] < Cfg.AP_COST_SHOOT:
        return False
    
    best_target = None
    best_score = 0
    
    for player_unit in g_player_squad:
        if player_unit[K_HP] <= 0:
            continue
        
        # Check line of sight
        if has_line_of_sight(unit[K_X], unit[K_Y], player_unit[K_X], player_unit[K_Y]):
            hit_chance = calculate_hit_chance(unit, player_unit)
            
            # Score targets: prefer wounded enemies and high hit chance
            health_factor = (player_unit[K_MAX_HP] - player_unit[K_HP]) / player_unit[K_MAX_HP]
            score = hit_chance + (health_factor * 30)  # Bonus for wounded targets
            
            if score > best_score:
                best_score = score
                best_target = player_unit
    
    if best_target and best_score > 40:  # Only attack if decent chance
        execute_attack(unit[K_ID], best_target[K_ID])
        unit[K_AP] -= Cfg.AP_COST_SHOOT
        return True
    
    return False

def ai_try_take_cover(unit: Character) -> bool:
    """Try to move to better cover if exposed.
    
    Returns:
        True if moved to cover, False otherwise
    """
    current_tile = g_current_map[unit[K_Y]][unit[K_X]]
    current_cover = current_tile.get(K_COVER, 0)
    
    # Only seek cover if currently exposed and have enough AP
    if current_cover >= 50 or unit[K_AP] < Cfg.AP_COST_MOVE * 2:
        return False
    
    # Find nearby cover positions
    best_cover_pos = None
    best_cover_value = current_cover
    best_distance = float('inf')
    
    for dy in range(-4, 5):
        for dx in range(-4, 5):
            new_x = unit[K_X] + dx
            new_y = unit[K_Y] + dy
            
            if not is_valid_position(new_x, new_y):
                continue
            
            # Skip if occupied
            if is_position_occupied(new_x, new_y):
                continue
            
            tile = g_current_map[new_y][new_x]
            cover_value = tile.get(K_COVER, 0)
            distance = abs(dx) + abs(dy)
            
            # Prefer better cover, closer positions
            if cover_value > best_cover_value or (cover_value == best_cover_value and distance < best_distance):
                if can_reach_position(unit, new_x, new_y):
                    best_cover_value = cover_value
                    best_cover_pos = (new_x, new_y)
                    best_distance = distance
    
    if best_cover_pos and best_cover_value > current_cover + 20:  # Significant improvement
        old_x, old_y = unit[K_X], unit[K_Y]
        move_unit(unit[K_ID], best_cover_pos[0], best_cover_pos[1])
        print(f"[AI] {unit[K_NAME]} moved to cover at ({best_cover_pos[0]}, {best_cover_pos[1]})")
        
        # Check for overwatch triggers
        check_overwatch_triggers(unit, old_x, old_y)
        return True
    
    return False

def ai_try_move_to_enemy(unit: Character) -> bool:
    """Try to move toward nearest enemy.
    
    Returns:
        True if moved, False otherwise
    """
    if unit[K_AP] < Cfg.AP_COST_MOVE:
        return False
    
    nearest = find_nearest_player(unit)
    if not nearest:
        return False
    
    # Don't move if already in good attack range
    distance = calculate_distance(unit, nearest)
    if distance <= 8:  # Within good range
        return False
    
    # Find best move toward target
    target_x, target_y = nearest[K_X], nearest[K_Y]
    best_move = None
    best_distance = distance
    
    # Try all adjacent positions
    for dy in [-1, 0, 1]:
        for dx in [-1, 0, 1]:
            if dx == 0 and dy == 0:
                continue
                
            new_x = unit[K_X] + dx
            new_y = unit[K_Y] + dy
            
            if not is_valid_position(new_x, new_y):
                continue
            
            if is_position_occupied(new_x, new_y):
                continue
            
            # Calculate distance to target
            new_distance = math.sqrt((new_x - target_x)**2 + (new_y - target_y)**2)
            
            if new_distance < best_distance:
                best_distance = new_distance
                best_move = (new_x, new_y)
    
    if best_move and unit[K_AP] >= Cfg.AP_COST_MOVE:
        old_x, old_y = unit[K_X], unit[K_Y]
        move_unit(unit[K_ID], best_move[0], best_move[1])
        print(f"[AI] {unit[K_NAME]} advanced toward enemy to ({best_move[0]}, {best_move[1]})")
        
        # Check for overwatch triggers
        check_overwatch_triggers(unit, old_x, old_y)
        return True
    
    return False

def check_overwatch_triggers(moved_unit: Character, old_x: int, old_y: int):
    """Check if movement triggers any overwatch shots.
    
    Side effects:
        May execute attacks
        Removes overwatch status after firing
        
    Globals:
        Reads: All units
        Writes: Unit status, may trigger combat
    """
    # Check all enemy units if player moved, and vice versa
    if moved_unit[K_FACTION] == 'player':
        watching_units = g_enemy_units
    else:
        watching_units = g_player_squad
    
    for watcher in watching_units:
        if 'overwatch' in watcher[K_STATUS] and watcher[K_HP] > 0:
            # Check if watcher can see the new position
            if has_line_of_sight(watcher[K_X], watcher[K_Y], moved_unit[K_X], moved_unit[K_Y]):
                # Check if they couldn't see the old position (unit emerged into view)
                could_see_before = has_line_of_sight(watcher[K_X], watcher[K_Y], old_x, old_y)
                
                if not could_see_before:  # Unit moved into view
                    # Execute overwatch shot
                    g_game_state['combat_log'].append(f"{watcher[K_NAME]} fires overwatch at {moved_unit[K_NAME]}!")
                    execute_attack(watcher[K_ID], moved_unit[K_ID])
                    watcher[K_STATUS].remove('overwatch')
                    break  # Only one overwatch shot per movement

def is_position_occupied(x: int, y: int) -> bool:
    """Check if position is occupied by any unit.
    
    Returns:
        True if occupied, False otherwise
    """
    for unit in g_player_squad + g_enemy_units:
        if unit[K_HP] > 0 and unit[K_X] == x and unit[K_Y] == y:
            return True
    return False

# ======================================================================
# === [10] RENDERING
# ======================================================================
def render_frame():
    """Render current game state.
    
    Side effects:
        Draws to g_screen
        
    Globals:
        Reads: All globals
        Writes: g_screen
    """
    g_screen.fill((40, 40, 40))  # Dark gray background
    
    current_state = GameState(g_game_state['current_state'])
    
    if current_state == GameState.MAIN_MENU:
        render_main_menu()
    elif current_state == GameState.MISSION_SELECTION:
        render_mission_selection()
    elif current_state == GameState.SQUAD_SELECTION:
        render_squad_selection()
    elif current_state == GameState.LOADOUT_SCREEN:
        render_loadout_screen()
    elif current_state == GameState.MISSION_BRIEFING:
        render_mission_briefing()
    elif current_state == GameState.SETTINGS:
        render_settings()
    elif current_state == GameState.TACTICAL_COMBAT:
        render_map()
        render_units()
        render_effects()
        render_ui()
    
    pygame.display.flip()

def render_map():
    """Render the game map.
    
    Side effects:
        Draws tiles to g_screen
        
    Globals:
        Reads: g_current_map, g_screen
        Writes: g_screen
    """
    for y, row in enumerate(g_current_map):
        for x, tile in enumerate(row):
            screen_x = x * Cfg.TILE_SIZE
            screen_y = y * Cfg.TILE_SIZE
            
            # Choose color based on tile type
            if tile[K_TYPE] == 'wall':
                color = (80, 80, 80)  # Gray
            elif tile[K_TYPE] == 'crate':
                color = (139, 69, 19)  # Brown
            else:  # floor
                color = (60, 60, 60)  # Dark gray
            
            # Add cover indication
            cover = tile.get(K_COVER, 0)
            if cover > 0:
                # Lighter color for more cover
                color = tuple(min(255, c + cover // 2) for c in color)
            
            pygame.draw.rect(g_screen, color, 
                           (screen_x, screen_y, Cfg.TILE_SIZE, Cfg.TILE_SIZE))
            
            # Draw tile border
            pygame.draw.rect(g_screen, (100, 100, 100), 
                           (screen_x, screen_y, Cfg.TILE_SIZE, Cfg.TILE_SIZE), 1)

def render_units():
    """Render all units.
    
    Side effects:
        Draws units to g_screen
        
    Globals:
        Reads: g_player_squad, g_enemy_units, g_screen
        Writes: g_screen
    """
    # Render player units
    for unit in g_player_squad:
        if unit[K_HP] > 0:
            screen_x = unit[K_X] * Cfg.TILE_SIZE
            screen_y = unit[K_Y] * Cfg.TILE_SIZE
            
            # Unit color (blue for player)
            color = (0, 100, 255)
            
            # Highlight active unit
            if unit[K_ID] == g_game_state['active_unit_id']:
                color = (0, 200, 255)  # Brighter blue
            
            # Draw unit circle
            center_x = screen_x + Cfg.TILE_SIZE // 2
            center_y = screen_y + Cfg.TILE_SIZE // 2
            pygame.draw.circle(g_screen, color, (center_x, center_y), Cfg.TILE_SIZE // 3)
            
            # Draw health bar
            bar_width = Cfg.TILE_SIZE - 4
            bar_height = 4
            bar_x = screen_x + 2
            bar_y = screen_y + 2
            
            # Background (red)
            pygame.draw.rect(g_screen, (255, 0, 0), 
                           (bar_x, bar_y, bar_width, bar_height))
            
            # Health (green)
            health_percent = unit[K_HP] / unit[K_MAX_HP]
            health_width = int(bar_width * health_percent)
            pygame.draw.rect(g_screen, (0, 255, 0), 
                           (bar_x, bar_y, health_width, bar_height))
            
            # Show AP as small text
            ap_text = g_font.render(f"AP:{unit[K_AP]}", True, (255, 255, 255))
            g_screen.blit(ap_text, (screen_x, screen_y + Cfg.TILE_SIZE - 15))
            
            # Show ammo if unit has a weapon
            if unit[K_WEAPON_TYPE]:
                ammo_color = (255, 255, 255)  # White for normal
                if unit[K_CURRENT_AMMO] <= unit[K_MAX_AMMO] // 4:  # Low ammo warning
                    ammo_color = (255, 255, 100)  # Yellow
                if unit[K_CURRENT_AMMO] <= 0:  # Out of ammo
                    ammo_color = (255, 100, 100)  # Red
                
                ammo_text = g_font.render(f"AMMO:{unit[K_CURRENT_AMMO]}/{unit[K_MAX_AMMO]}", True, ammo_color)
                g_screen.blit(ammo_text, (screen_x, screen_y + Cfg.TILE_SIZE - 30))

    # Render enemy units
    for unit in g_enemy_units:
        if unit[K_HP] > 0:
            screen_x = unit[K_X] * Cfg.TILE_SIZE
            screen_y = unit[K_Y] * Cfg.TILE_SIZE
            
            # Unit color (red for enemy)
            color = (255, 50, 50)
            
            # Draw unit circle
            center_x = screen_x + Cfg.TILE_SIZE // 2
            center_y = screen_y + Cfg.TILE_SIZE // 2
            pygame.draw.circle(g_screen, color, (center_x, center_y), Cfg.TILE_SIZE // 3)

def render_effects():
    """Render visual effects.
    
    Side effects:
        Draws effects to g_screen
        
    Globals:
        Reads: g_effect_queue, g_screen
        Writes: g_screen
    """
    for effect in g_effect_queue:
        screen_x = effect['x'] * Cfg.TILE_SIZE + Cfg.TILE_SIZE // 2
        screen_y = effect['y'] * Cfg.TILE_SIZE + Cfg.TILE_SIZE // 2
        
        if effect['type'] == 'damage_text':
            # Floating damage text
            text = effect['data'].get('text', '0')
            color = effect['data'].get('color', (255, 255, 255))
            
            # Make text float upward
            offset_y = -(effect['frame'] * 2)
            
            damage_surface = g_font.render(text, True, color)
            g_screen.blit(damage_surface, (screen_x - 10, screen_y + offset_y))

def render_ui():
    """Render UI elements.
    
    Side effects:
        Draws UI to g_screen
        
    Globals:
        Reads: g_game_state, g_screen
        Writes: g_screen
    """
    # Combat log (bottom of screen)
    log_y = Cfg.SCREEN_HEIGHT - 150
    pygame.draw.rect(g_screen, (20, 20, 20), (0, log_y, Cfg.SCREEN_WIDTH, 150))
    
    # Show last few log entries
    log_entries = g_game_state['combat_log'][-8:]  # Show last 8 entries
    for i, entry in enumerate(log_entries):
        text_surface = g_font.render(entry, True, (200, 200, 200))
        g_screen.blit(text_surface, (10, log_y + 10 + i * 18))
    
    # Combat controls (bottom right)
    controls_x = Cfg.SCREEN_WIDTH - 200
    controls_y = log_y + 10
    
    controls_text = [
        "Controls:",
        "LEFT CLICK: Move/Select",
        "RIGHT CLICK: Attack",
        "R: Reload Weapon",
        "O: Overwatch",
        "TAB: Cycle Units",
        "SPACE: End Turn"
    ]
    
    for i, control in enumerate(controls_text):
        color = (255, 255, 100) if i == 0 else (150, 150, 150)
        control_surface = g_font.render(control, True, color)
        g_screen.blit(control_surface, (controls_x, controls_y + i * 16))
    
    # Active unit info (top right)
    if g_game_state['active_unit_id']:
        active_unit = find_unit_by_id(g_game_state['active_unit_id'])
        if active_unit:
            info_x = Cfg.SCREEN_WIDTH - 200
            info_y = 10
            
            pygame.draw.rect(g_screen, (20, 20, 20), (info_x, info_y, 190, 100))
            
            name_text = g_font.render(f"Active: {active_unit[K_NAME]}", True, (255, 255, 255))
            hp_text = g_font.render(f"HP: {active_unit[K_HP]}/{active_unit[K_MAX_HP]}", True, (255, 255, 255))
            ap_text = g_font.render(f"AP: {active_unit[K_AP]}/{active_unit[K_MAX_AP]}", True, (255, 255, 255))
            
            g_screen.blit(name_text, (info_x + 5, info_y + 5))
            g_screen.blit(hp_text, (info_x + 5, info_y + 25))
            g_screen.blit(ap_text, (info_x + 5, info_y + 45))
            
            # Show ammo if unit has a weapon
            if active_unit[K_WEAPON_TYPE]:
                ammo_color = (255, 255, 255)  # White for normal
                if active_unit[K_CURRENT_AMMO] <= active_unit[K_MAX_AMMO] // 4:  # Low ammo warning
                    ammo_color = (255, 255, 100)  # Yellow
                if active_unit[K_CURRENT_AMMO] <= 0:  # Out of ammo
                    ammo_color = (255, 100, 100)  # Red
                
                ammo_text = g_font.render(f"Ammo: {active_unit[K_CURRENT_AMMO]}/{active_unit[K_MAX_AMMO]}", True, ammo_color)
                g_screen.blit(ammo_text, (info_x + 5, info_y + 65))
    
    # Debug overlay
    if g_game_state['ui_state']['debug_overlay']:
        render_debug_overlay()

def render_debug_overlay():
    """Render debug information overlay.
    
    Side effects:
        Draws debug info to g_screen
        
    Globals:
        Reads: Various debug info
        Writes: g_screen
    """
    # Grid coordinates
    for y in range(len(g_current_map)):
        for x in range(len(g_current_map[0])):
            screen_x = x * Cfg.TILE_SIZE
            screen_y = y * Cfg.TILE_SIZE
            
            coord_text = g_font.render(f"{x},{y}", True, (100, 255, 100))
            g_screen.blit(coord_text, (screen_x + 2, screen_y + 2))

def render_main_menu():
    """Render main menu with navigation options.
    
    Side effects:
        Draws main menu to g_screen
        
    Globals:
        Reads: g_game_state, g_font, g_screen
        Writes: g_screen
    """
    # Background
    g_screen.fill((20, 30, 40))
    
    # Title
    title_font = pygame.font.Font(None, 72)
    title_text = title_font.render("TACTICAL SQUAD", True, (255, 255, 100))
    title_rect = title_text.get_rect(center=(Cfg.SCREEN_WIDTH // 2, 150))
    g_screen.blit(title_text, title_rect)
    
    subtitle_text = g_font.render("Turn-Based Tactical Combat", True, (200, 200, 200))
    subtitle_rect = subtitle_text.get_rect(center=(Cfg.SCREEN_WIDTH // 2, 200))
    g_screen.blit(subtitle_text, subtitle_rect)
    
    # Menu options
    menu_items = [
        "Start Mission",
        "Quick Battle (Test)",
        "Settings", 
        "Exit"
    ]
    
    selected_item = g_game_state['ui_state']['selected_menu_item']
    
    for i, item in enumerate(menu_items):
        y_pos = 300 + i * 60
        color = (255, 255, 100) if i == selected_item else (200, 200, 200)
        
        # Highlight selected item
        if i == selected_item:
            highlight_rect = pygame.Rect(Cfg.SCREEN_WIDTH // 2 - 150, y_pos - 10, 300, 40)
            pygame.draw.rect(g_screen, (60, 80, 100), highlight_rect)
            pygame.draw.rect(g_screen, (100, 120, 140), highlight_rect, 2)
        
        text = g_font.render(item, True, color)
        text_rect = text.get_rect(center=(Cfg.SCREEN_WIDTH // 2, y_pos))
        g_screen.blit(text, text_rect)
    
    # Instructions
    instruction_text = g_font.render("Use UP/DOWN arrows and ENTER to select", True, (150, 150, 150))
    instruction_rect = instruction_text.get_rect(center=(Cfg.SCREEN_WIDTH // 2, Cfg.SCREEN_HEIGHT - 50))
    g_screen.blit(instruction_text, instruction_rect)

def render_mission_selection():
    """Render mission selection screen.
    
    Side effects:
        Draws mission selection UI to g_screen
        
    Globals:
        Reads: g_game_state, g_mission_data, g_font, g_screen
        Writes: g_screen
    """
    g_screen.fill((25, 35, 45))
    
    # Title
    title_text = g_font.render("SELECT MISSION", True, (255, 255, 100))
    title_rect = title_text.get_rect(center=(Cfg.SCREEN_WIDTH // 2, 50))
    g_screen.blit(title_text, title_rect)
    
    # Mission list
    mission_keys = list(g_mission_data.keys())
    selected = g_game_state['ui_state']['selected_menu_item']
    
    y_start = 120
    for i, mission_id in enumerate(mission_keys):
        mission = g_mission_data[mission_id]
        y_pos = y_start + i * 160
        
        # Mission panel
        panel_rect = pygame.Rect(50, y_pos - 10, Cfg.SCREEN_WIDTH - 100, 140)
        panel_color = (80, 100, 120) if i == selected else (50, 60, 70)
        border_color = (120, 140, 160) if i == selected else (70, 80, 90)
        
        pygame.draw.rect(g_screen, panel_color, panel_rect)
        pygame.draw.rect(g_screen, border_color, panel_rect, 2)
        
        # Mission name
        name_color = (255, 255, 100) if i == selected else (200, 200, 200)
        name_text = g_font.render(mission['name'], True, name_color)
        g_screen.blit(name_text, (70, y_pos))
        
        # Mission briefing (first line)
        if mission.get('briefing_text'):
            brief_text = mission['briefing_text'][0]
            brief_color = (180, 180, 180) if i == selected else (150, 150, 150)
            brief_render = g_font.render(brief_text[:80] + "..." if len(brief_text) > 80 else brief_text, 
                                       True, brief_color)
            g_screen.blit(brief_render, (70, y_pos + 25))
        
        # Objectives count
        obj_count = len(mission.get('objectives', []))
        obj_text = g_font.render(f"Objectives: {obj_count}", True, (160, 160, 160))
        g_screen.blit(obj_text, (70, y_pos + 50))
        
        # Rewards
        if mission.get('rewards', {}).get('cash'):
            reward_text = g_font.render(f"Reward: ${mission['rewards']['cash']}", True, (100, 255, 100))
            g_screen.blit(reward_text, (70, y_pos + 75))
    
    # Instructions
    instruction_text = g_font.render("UP/DOWN: Select | ENTER: Choose Mission | ESC: Back", True, (150, 150, 150))
    instruction_rect = instruction_text.get_rect(center=(Cfg.SCREEN_WIDTH // 2, Cfg.SCREEN_HEIGHT - 30))
    g_screen.blit(instruction_text, instruction_rect)

def render_squad_selection():
    """Render squad selection screen.
    
    Side effects:
        Draws squad selection UI to g_screen
        
    Globals:
        Reads: g_game_state, g_unit_templates, g_font, g_screen
        Writes: g_screen
    """
    g_screen.fill((30, 40, 50))
    
    # Title
    title_text = g_font.render("SQUAD SELECTION", True, (255, 255, 100))
    title_rect = title_text.get_rect(center=(Cfg.SCREEN_WIDTH // 2, 30))
    g_screen.blit(title_text, title_rect)
    
    menu_state = g_game_state['menu_state']
    selected = g_game_state['ui_state']['selected_menu_item']
    
    # Available classes (left side)
    class_panel = pygame.Rect(50, 80, 400, 500)
    pygame.draw.rect(g_screen, (40, 50, 60), class_panel)
    pygame.draw.rect(g_screen, (80, 100, 120), class_panel, 2)
    
    class_title = g_font.render("Available Classes:", True, (200, 200, 200))
    g_screen.blit(class_title, (70, 90))
    
    for i, class_name in enumerate(menu_state['available_classes']):
        y_pos = 120 + i * 80
        template = g_unit_templates.get(class_name, {})
        
        # Highlight if selected
        if i == selected:
            highlight_rect = pygame.Rect(60, y_pos - 5, 380, 70)
            pygame.draw.rect(g_screen, (60, 80, 100), highlight_rect)
            pygame.draw.rect(g_screen, (100, 120, 140), highlight_rect, 2)
        
        # Class name
        name_color = (255, 255, 100) if i == selected else (200, 200, 200)
        name_text = g_font.render(template.get('name', class_name.title()), True, name_color)
        g_screen.blit(name_text, (70, y_pos))
        
        # Stats
        base_stats = template.get('base_stats', {})
        stats_text = f"HP: {base_stats.get('health', 100)} | AP: {base_stats.get('action_points', 10)}"
        stats_render = g_font.render(stats_text, True, (160, 160, 160))
        g_screen.blit(stats_render, (70, y_pos + 20))
        
        # Attributes
        attrs = template.get('attributes', {})
        attr_text = f"Marks: {attrs.get('marksmanship', 70)} | Agil: {attrs.get('agility', 60)}"
        attr_render = g_font.render(attr_text, True, (140, 140, 140))
        g_screen.blit(attr_render, (70, y_pos + 40))
    
    # Squad slots (right side)
    squad_panel = pygame.Rect(500, 80, 350, 500)
    pygame.draw.rect(g_screen, (40, 50, 60), squad_panel)
    pygame.draw.rect(g_screen, (80, 100, 120), squad_panel, 2)
    
    squad_title = g_font.render("Squad Composition:", True, (200, 200, 200))
    g_screen.blit(squad_title, (520, 90))
    
    for i in range(menu_state['max_squad_size']):
        y_pos = 120 + i * 60
        slot_selection = len(menu_state['available_classes']) + i
        
        # Highlight if selected
        if slot_selection == selected:
            highlight_rect = pygame.Rect(510, y_pos - 5, 330, 50)
            pygame.draw.rect(g_screen, (60, 80, 100), highlight_rect)
            pygame.draw.rect(g_screen, (100, 120, 140), highlight_rect, 2)
        
        slot_text = f"Slot {i + 1}: "
        if menu_state['squad_slots'][i]:
            template = g_unit_templates.get(menu_state['squad_slots'][i], {})
            slot_text += template.get('name', menu_state['squad_slots'][i].title())
            color = (100, 255, 100)
        else:
            slot_text += "Empty"
            color = (160, 160, 160)
        
        slot_render = g_font.render(slot_text, True, color)
        g_screen.blit(slot_render, (520, y_pos))
    
    # Continue option
    continue_selection = len(menu_state['available_classes']) + menu_state['max_squad_size']
    if continue_selection == selected:
        highlight_rect = pygame.Rect(500, 400, 350, 40)
        pygame.draw.rect(g_screen, (60, 80, 100), highlight_rect)
        pygame.draw.rect(g_screen, (100, 120, 140), highlight_rect, 2)
    
    squad_filled = any(slot is not None for slot in menu_state['squad_slots'])
    continue_color = (100, 255, 100) if squad_filled else (100, 100, 100)
    continue_text = g_font.render("Continue to Loadout", True, continue_color)
    g_screen.blit(continue_text, (520, 410))
    
    # Instructions
    instruction_lines = [
        "UP/DOWN: Navigate | ENTER: Select/Clear | ESC: Back",
        "Select classes to add to squad, select slots to clear them"
    ]
    for i, line in enumerate(instruction_lines):
        instruction_text = g_font.render(line, True, (150, 150, 150))
        instruction_rect = instruction_text.get_rect(center=(Cfg.SCREEN_WIDTH // 2, Cfg.SCREEN_HEIGHT - 40 + i * 20))
        g_screen.blit(instruction_text, instruction_rect)

def render_loadout_screen():
    """Render loadout screen.
    
    Side effects:
        Draws loadout UI to g_screen
        
    Globals:
        Reads: g_game_state, g_weapon_data, g_unit_templates, g_font, g_screen
        Writes: g_screen
    """
    g_screen.fill((35, 45, 55))
    
    # Title
    title_text = g_font.render("WEAPON LOADOUT", True, (255, 255, 100))
    title_rect = title_text.get_rect(center=(Cfg.SCREEN_WIDTH // 2, 30))
    g_screen.blit(title_text, title_rect)
    
    menu_state = g_game_state['menu_state']
    selected = g_game_state['ui_state']['selected_menu_item']
    current_slot = menu_state['current_loadout_slot']
    
    # Ensure current_slot points to a valid squad member
    if current_slot >= len(menu_state['squad_slots']) or menu_state['squad_slots'][current_slot] is None:
        # Find first valid slot
        for i, slot in enumerate(menu_state['squad_slots']):
            if slot is not None:
                menu_state['current_loadout_slot'] = i
                current_slot = i
                break
    
    # Current squad member info (top)
    if current_slot < len(menu_state['squad_slots']) and menu_state['squad_slots'][current_slot]:
        class_name = menu_state['squad_slots'][current_slot]
        template = g_unit_templates.get(class_name, {})
        
        member_panel = pygame.Rect(50, 70, Cfg.SCREEN_WIDTH - 100, 80)
        pygame.draw.rect(g_screen, (50, 70, 90), member_panel)
        pygame.draw.rect(g_screen, (100, 120, 140), member_panel, 2)
        
        member_text = f"Configuring: Slot {current_slot + 1} - {template.get('name', class_name.title())}"
        member_render = g_font.render(member_text, True, (255, 255, 255))
        g_screen.blit(member_render, (70, 85))
        
        # Current weapon
        current_weapon = menu_state['squad_loadouts'][current_slot].get('primary_weapon')
        weapon_text = "Current Weapon: "
        if current_weapon:
            weapon_info = g_weapon_data.get(current_weapon, {})
            weapon_text += weapon_info.get('name', current_weapon)
        else:
            weapon_text += "None"
        weapon_render = g_font.render(weapon_text, True, (200, 200, 200))
        g_screen.blit(weapon_render, (70, 110))
    
    # Available weapons (left side)
    weapon_panel = pygame.Rect(50, 170, 500, 400)
    pygame.draw.rect(g_screen, (40, 50, 60), weapon_panel)
    pygame.draw.rect(g_screen, (80, 100, 120), weapon_panel, 2)
    
    weapon_title = g_font.render("Available Weapons:", True, (200, 200, 200))
    g_screen.blit(weapon_title, (70, 180))
    
    weapon_keys = list(g_weapon_data.keys())
    for i, weapon_id in enumerate(weapon_keys):
        y_pos = 210 + i * 50
        weapon = g_weapon_data[weapon_id]
        
        # Highlight if selected
        if i == selected:
            highlight_rect = pygame.Rect(60, y_pos - 5, 480, 40)
            pygame.draw.rect(g_screen, (60, 80, 100), highlight_rect)
            pygame.draw.rect(g_screen, (100, 120, 140), highlight_rect, 2)
        
        # Weapon name
        name_color = (255, 255, 100) if i == selected else (200, 200, 200)
        name_text = g_font.render(weapon['name'], True, name_color)
        g_screen.blit(name_text, (70, y_pos))
        
        # Weapon stats
        stats_text = f"Dmg: {weapon['damage']} | Range: {weapon['range']} | AP: {weapon['ap_cost']}"
        stats_render = g_font.render(stats_text, True, (160, 160, 160))
        g_screen.blit(stats_render, (70, y_pos + 20))
    
    # Squad overview (right side)
    squad_panel = pygame.Rect(580, 170, 300, 400)
    pygame.draw.rect(g_screen, (40, 50, 60), squad_panel)
    pygame.draw.rect(g_screen, (80, 100, 120), squad_panel, 2)
    
    squad_title = g_font.render("Squad Overview:", True, (200, 200, 200))
    g_screen.blit(squad_title, (600, 180))
    
    for i, class_name in enumerate(menu_state['squad_slots']):
        if class_name is not None:
            y_pos = 210 + i * 60
            
            # Highlight current slot
            if i == current_slot:
                highlight_rect = pygame.Rect(590, y_pos - 5, 280, 50)
                pygame.draw.rect(g_screen, (60, 80, 100), highlight_rect)
                pygame.draw.rect(g_screen, (100, 120, 140), highlight_rect, 2)
            
            template = g_unit_templates.get(class_name, {})
            slot_text = f"{i + 1}. {template.get('name', class_name.title())}"
            slot_color = (255, 255, 100) if i == current_slot else (200, 200, 200)
            slot_render = g_font.render(slot_text, True, slot_color)
            g_screen.blit(slot_render, (600, y_pos))
            
            # Assigned weapon
            assigned_weapon = menu_state['squad_loadouts'][i].get('primary_weapon')
            if assigned_weapon:
                weapon_info = g_weapon_data.get(assigned_weapon, {})
                weapon_text = weapon_info.get('name', assigned_weapon)[:20]
            else:
                weapon_text = "No weapon"
            weapon_render = g_font.render(weapon_text, True, (140, 140, 140))
            g_screen.blit(weapon_render, (600, y_pos + 20))
    
    # Control buttons
    continue_selection = len(weapon_keys)
    back_selection = len(weapon_keys) + 1
    
    # Continue button
    if continue_selection == selected:
        highlight_rect = pygame.Rect(50, 590, 200, 40)
        pygame.draw.rect(g_screen, (60, 80, 100), highlight_rect)
        pygame.draw.rect(g_screen, (100, 120, 140), highlight_rect, 2)
    
    continue_text = g_font.render("Continue to Briefing", True, (100, 255, 100))
    g_screen.blit(continue_text, (60, 600))
    
    # Back button
    if back_selection == selected:
        highlight_rect = pygame.Rect(280, 590, 150, 40)
        pygame.draw.rect(g_screen, (60, 80, 100), highlight_rect)
        pygame.draw.rect(g_screen, (100, 120, 140), highlight_rect, 2)
    
    back_text = g_font.render("Back to Squad", True, (255, 100, 100))
    g_screen.blit(back_text, (290, 600))
    
    # Instructions
    instruction_lines = [
        "LEFT/RIGHT: Switch Squad Member | UP/DOWN: Select Weapon | ENTER: Assign",
        "ESC: Back to Squad Selection"
    ]
    for i, line in enumerate(instruction_lines):
        instruction_text = g_font.render(line, True, (150, 150, 150))
        instruction_rect = instruction_text.get_rect(center=(Cfg.SCREEN_WIDTH // 2, Cfg.SCREEN_HEIGHT - 30 + i * 15))
        g_screen.blit(instruction_text, instruction_rect)

def render_mission_briefing():
    """Render final mission briefing screen.
    
    Side effects:
        Draws mission briefing UI to g_screen
        
    Globals:
        Reads: g_game_state, g_unit_templates, g_weapon_data, g_font, g_screen
        Writes: g_screen
    """
    g_screen.fill((40, 50, 60))
    
    # Title
    title_text = g_font.render("MISSION BRIEFING", True, (255, 255, 100))
    title_rect = title_text.get_rect(center=(Cfg.SCREEN_WIDTH // 2, 30))
    g_screen.blit(title_text, title_rect)
    
    menu_state = g_game_state['menu_state']
    mission = menu_state['selected_mission']
    
    if mission:
        # Mission name
        mission_name = g_font.render(mission['name'], True, (255, 255, 255))
        mission_rect = mission_name.get_rect(center=(Cfg.SCREEN_WIDTH // 2, 70))
        g_screen.blit(mission_name, mission_rect)
        
        # Briefing text
        y_pos = 110
        for line in mission.get('briefing_text', []):
            line_text = g_font.render(line, True, (200, 200, 200))
            line_rect = line_text.get_rect(center=(Cfg.SCREEN_WIDTH // 2, y_pos))
            g_screen.blit(line_text, line_rect)
            y_pos += 30
        
        # Objectives
        obj_title = g_font.render("OBJECTIVES:", True, (255, 255, 100))
        g_screen.blit(obj_title, (100, y_pos + 20))
        y_pos += 50
        
        for i, obj in enumerate(mission.get('objectives', [])):
            obj_text = f"• {obj['description']}"
            obj_render = g_font.render(obj_text, True, (180, 180, 180))
            g_screen.blit(obj_render, (120, y_pos))
            y_pos += 25
        
        # Squad summary
        squad_title = g_font.render("SQUAD DEPLOYMENT:", True, (255, 255, 100))
        g_screen.blit(squad_title, (100, y_pos + 20))
        y_pos += 50
        
        for i, class_name in enumerate(menu_state['squad_slots']):
            if class_name is not None:
                template = g_unit_templates.get(class_name, {})
                weapon = menu_state['squad_loadouts'][i].get('primary_weapon')
                weapon_name = g_weapon_data.get(weapon, {}).get('name', 'Unarmed') if weapon else 'Unarmed'
                
                squad_text = f"• {template.get('name', class_name.title())} - {weapon_name}"
                squad_render = g_font.render(squad_text, True, (180, 180, 180))
                g_screen.blit(squad_render, (120, y_pos))
                y_pos += 25
    
    # Deploy button
    deploy_rect = pygame.Rect(Cfg.SCREEN_WIDTH // 2 - 100, Cfg.SCREEN_HEIGHT - 100, 200, 50)
    pygame.draw.rect(g_screen, (100, 150, 100), deploy_rect)
    pygame.draw.rect(g_screen, (150, 200, 150), deploy_rect, 3)
    
    deploy_text = g_font.render("DEPLOY SQUAD", True, (255, 255, 255))
    deploy_text_rect = deploy_text.get_rect(center=deploy_rect.center)
    g_screen.blit(deploy_text, deploy_text_rect)
    
    # Instructions
    instruction_text = g_font.render("ENTER: Deploy to Mission | ESC: Back to Loadout", True, (150, 150, 150))
    instruction_rect = instruction_text.get_rect(center=(Cfg.SCREEN_WIDTH // 2, Cfg.SCREEN_HEIGHT - 30))
    g_screen.blit(instruction_text, instruction_rect)

# ======================================================================
# === [11] COMBAT SYSTEM
# ======================================================================
def calculate_hit_chance(attacker: Character, target: Character) -> int:
    """Calculate chance to hit including all modifiers.
    
    Side effects:
        None - pure function
        
    Returns:
        Hit chance as percentage (0-100)
    """
    # Base chance from attacker's marksmanship
    base_chance = Cfg.BASE_HIT_CHANCE + (attacker['attributes'][K_MARKSMANSHIP] - 70) // 2
    
    # Distance penalty
    distance = calculate_distance(attacker, target)
    distance_penalty = int(distance * 3)
    
    # Cover bonus for target
    target_tile = g_current_map[target[K_Y]][target[K_X]]
    cover_bonus = target_tile.get(K_COVER, 0)
    
    # Calculate final chance
    final_chance = base_chance - distance_penalty - cover_bonus
    
    # Agility gives a dodge chance
    dodge_bonus = (target['attributes'][K_AGILITY] - 60) // 4
    final_chance -= dodge_bonus
    
    return max(5, min(95, final_chance))

def has_line_of_sight(x0: int, y0: int, x1: int, y1: int) -> bool:
    """Check if line between points is blocked.
    
    Side effects:
        Adds debug lines if debug overlay is on
        
    Globals:
        Reads: g_current_map, g_game_state
    """
    # Bresenham's line algorithm
    points = []
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    
    x, y = x0, y0
    
    while True:
        points.append((x, y))
        
        # Check if current tile blocks sight
        if 0 <= y < len(g_current_map) and 0 <= x < len(g_current_map[0]):
            if g_current_map[y][x].get(K_BLOCKS_SIGHT, False):
                # Don't block if it's the start or end tile
                if (x, y) != (x0, y0) and (x, y) != (x1, y1):
                    if g_game_state['ui_state']['debug_overlay']:
                        g_debug_lines.append({
                            'points': points,
                            'color': (255, 0, 0),
                            'lifetime': 60
                        })
                    return False
        
        if x == x1 and y == y1:
            break
            
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy
    
    if g_game_state['ui_state']['debug_overlay']:
        g_debug_lines.append({
            'points': points,
            'color': (0, 255, 0),
            'lifetime': 60
        })
    
    return True

def execute_attack(attacker_id: str, target_id: str):
    """Execute attack between units.
    
    Side effects:
        Modifies target health
        Creates visual effects
        Updates combat log
        May trigger unit death
        Consumes ammo
        
    Globals:
        Reads: g_player_squad, g_enemy_units
        Writes: g_player_squad, g_enemy_units, g_effect_queue, g_game_state
    """
    # Find units
    attacker = find_unit_by_id(attacker_id)
    target = find_unit_by_id(target_id)
    
    if not attacker or not target:
        log_error(f"Could not find attacker {attacker_id} or target {target_id}")
        return
    
    # Check if attacker has ammo
    if attacker[K_CURRENT_AMMO] <= 0:
        g_game_state['combat_log'].append(f"{attacker[K_NAME]} is out of ammo!")
        g_effect_queue.append(create_effect(
            'text',
            attacker[K_X], attacker[K_Y],
            text="OUT OF AMMO",
            color=(255, 100, 100),
            duration=45
        ))
        return
    
    # Check line of sight
    if not has_line_of_sight(attacker[K_X], attacker[K_Y], target[K_X], target[K_Y]):
        g_game_state['combat_log'].append("No line of sight to target")
        return
    
    # Consume ammo
    attacker[K_CURRENT_AMMO] -= 1
    
    # Calculate hit
    hit_chance = calculate_hit_chance(attacker, target)
    roll = random.randint(1, 100)
    
    if roll <= hit_chance:
        # Calculate damage (base 25 + marksmanship bonus)
        base_damage = 25
        skill_bonus = (attacker['attributes'][K_MARKSMANSHIP] - 70) // 5
        damage = max(15, base_damage + skill_bonus + random.randint(-5, 5))
        
        # Apply damage
        old_hp = target[K_HP]
        target[K_HP] = max(0, target[K_HP] - damage)
        actual_damage = old_hp - target[K_HP]
        
        # Add to combat log
        g_game_state['combat_log'].append(
            f"{attacker[K_NAME]} hit {target[K_NAME]} for {actual_damage} damage ({hit_chance}% chance, rolled {roll})"
        )
        
        # Create visual effects
        g_effect_queue.append(create_effect(
            'damage_text',
            target[K_X], target[K_Y],
            text=str(actual_damage),
            color=(255, 100, 100),
            duration=45
        ))
        
        # Check for death
        if target[K_HP] <= 0:
            handle_unit_death(target)
    else:
        g_game_state['combat_log'].append(
            f"{attacker[K_NAME]} missed {target[K_NAME]} ({hit_chance}% chance, rolled {roll})"
        )
        
        g_effect_queue.append(create_effect(
            'text',
            target[K_X], target[K_Y],
            text="MISS",
            color=(200, 200, 200),
            duration=30
        ))
    
    # Show ammo status after attack
    ammo_status = f"({attacker[K_CURRENT_AMMO]}/{attacker[K_MAX_AMMO]})"
    g_game_state['combat_log'].append(f"{attacker[K_NAME]} ammo: {ammo_status}")

def handle_unit_death(unit: Character):
    """Handle unit death.
    
    Side effects:
        Removes unit from appropriate list
        Creates death effect
        Updates combat log
        
    Globals:
        Writes: g_player_squad or g_enemy_units, g_effect_queue, g_game_state
    """
    # Add death message
    g_game_state['combat_log'].append(f"{unit[K_NAME]} has been killed!")
    
    # Create death effect
    g_effect_queue.append(create_effect(
        'death',
        unit[K_X], unit[K_Y],
        duration=60
    ))
    
    # Remove from appropriate list
    if unit[K_FACTION] == 'player':
        if unit in g_player_squad:
            g_player_squad.remove(unit)
            print(f"[COMBAT] Player unit {unit[K_NAME]} eliminated!")
    else:
        if unit in g_enemy_units:
            g_enemy_units.remove(unit)
            print(f"[COMBAT] Enemy unit {unit[K_NAME]} eliminated!")
    
    # Clear active unit if it was the one that died
    if g_game_state['active_unit_id'] == unit[K_ID]:
        # Select next available unit
        if g_player_squad:
            g_game_state['active_unit_id'] = g_player_squad[0][K_ID]
        else:
            g_game_state['active_unit_id'] = None

def activate_overwatch(unit_id: str):
    """Put unit into overwatch mode.
    
    Side effects:
        Adds 'overwatch' to unit status
        Deducts AP
        
    Globals:
        Reads: Unit from g_player_squad or g_enemy_units
        Writes: Unit status
    """
    unit = find_unit_by_id(unit_id)
    if not unit:
        return
    
    if unit[K_AP] >= Cfg.AP_COST_OVERWATCH:
        unit[K_AP] -= Cfg.AP_COST_OVERWATCH
        if 'overwatch' not in unit[K_STATUS]:
            unit[K_STATUS].append('overwatch')
        g_game_state['combat_log'].append(f"{unit[K_NAME]} is on overwatch")

def end_player_turn():
    """End the player's turn.
    
    Side effects:
        Changes game state to enemy turn
        
    Globals:
        Writes: g_game_state
    """
    g_game_state['current_state'] = GameState.ENEMY_TURN.value
    g_game_state['combat_log'].append("Player turn ended")

# ======================================================================
# === [12] UTILITY FUNCTIONS
# ======================================================================
def calculate_distance(unit1: Character, unit2: Character) -> float:
    """Calculate tile distance between units."""
    return math.sqrt((unit1[K_X] - unit2[K_X])**2 + 
                    (unit1[K_Y] - unit2[K_Y])**2)

def find_unit_by_id(unit_id: str) -> Optional[Character]:
    """Find unit in any list by ID.
    
    Globals:
        Reads: g_player_squad, g_enemy_units
    """
    for unit in g_player_squad + g_enemy_units:
        if unit[K_ID] == unit_id:
            return unit
    return None

def find_nearest_player(unit: Character) -> Optional[Character]:
    """Find nearest player unit to given unit.
    
    Returns:
        Nearest player unit or None if no valid targets
    """
    nearest = None
    min_distance = float('inf')
    
    for player_unit in g_player_squad:
        if player_unit[K_HP] <= 0:
            continue
        dist = calculate_distance(unit, player_unit)
        if dist < min_distance:
            min_distance = dist
            nearest = player_unit
    
    return nearest

def is_valid_position(x: int, y: int) -> bool:
    """Check if position is valid and walkable."""
    if not (0 <= y < len(g_current_map) and 0 <= x < len(g_current_map[0])):
        return False
    
    tile = g_current_map[y][x]
    return not tile.get(K_BLOCKS_MOVE, False)

def can_reach_position(unit: Character, x: int, y: int) -> bool:
    """Check if unit has enough AP to reach position."""
    distance = abs(unit[K_X] - x) + abs(unit[K_Y] - y)
    return unit[K_AP] >= distance * Cfg.AP_COST_MOVE

def move_unit(unit_id: str, new_x: int, new_y: int):
    """Move unit to new position.
    
    Side effects:
        Updates unit position
        Deducts AP
        May trigger overwatch
        
    Globals:
        Modifies unit in g_player_squad or g_enemy_units
    """
    unit = find_unit_by_id(unit_id)
    if not unit:
        return
    
    # Calculate AP cost
    distance = abs(unit[K_X] - new_x) + abs(unit[K_Y] - new_y)
    ap_cost = distance * Cfg.AP_COST_MOVE
    
    if unit[K_AP] >= ap_cost:
        old_x, old_y = unit[K_X], unit[K_Y]
        unit[K_X] = new_x
        unit[K_Y] = new_y
        unit[K_AP] -= ap_cost
        
        # Check for overwatch triggers
        check_overwatch_triggers(unit, old_x, old_y)

# ======================================================================
# === [13] SAVE/LOAD SYSTEM
# ======================================================================
def save_game():
    """Save current game state to JSON.
    
    Side effects:
        Creates save file
        
    Globals:
        Reads: All game state
    """
    state_to_save = {
        'game_state': g_game_state,
        'player_squad': g_player_squad,
        'enemy_units': g_enemy_units,
        'current_map_name': 'test_map',
        'version': '1.0.0'
    }
    
    try:
        os.makedirs(os.path.dirname(Cfg.SAVE_FILE), exist_ok=True)
        with open(Cfg.SAVE_FILE, 'w') as f:
            json.dump(state_to_save, f, indent=2)
        g_game_state['combat_log'].append("Game saved successfully")
        print("[SAVE] Game saved to", Cfg.SAVE_FILE)
    except Exception as e:
        log_error(f"Save failed: {e}")

def load_game():
    """Load game state from JSON.
    
    Side effects:
        Replaces all game state
        
    Globals:
        Writes: All game state
    """
    global g_game_state, g_player_squad, g_enemy_units
    
    try:
        with open(Cfg.SAVE_FILE, 'r') as f:
            data = json.load(f)
            
        g_game_state = data['game_state']
        g_player_squad = data['player_squad']
        g_enemy_units = data['enemy_units']
        
        validate_game_state()
        g_game_state['combat_log'].append("Game loaded successfully")
        print("[LOAD] Game loaded from", Cfg.SAVE_FILE)
        
    except FileNotFoundError:
        log_error("No save file found")
    except Exception as e:
        log_error(f"Load failed: {e}")

# ======================================================================
# === [14] DATA LOADING
# ======================================================================
def load_game_data():
    """Load all JSON game data files.
    
    Side effects:
        Populates global caches
        Updates Cfg from config.json
        
    Globals:
        Writes: g_unit_templates, g_weapon_data, g_mission_data, Cfg
    """
    global g_unit_templates, g_weapon_data, g_mission_data
    
    # Load config
    config = safe_load_json('data/config.json', {})
    for key, value in config.items():
        if hasattr(Cfg, key.upper()):
            setattr(Cfg, key.upper(), value)
    
    # Load templates
    char_data = safe_load_json('data/characters.json', {})
    g_unit_templates = char_data.get('templates', {})
    
    # Load weapons
    g_weapon_data = safe_load_json('data/weapons.json', {})
    
    # Load missions
    g_mission_data = safe_load_json('data/missions.json', {})
    
    print(f"[INIT] Loaded {len(g_unit_templates)} unit templates")
    print(f"[INIT] Loaded {len(g_weapon_data)} weapons")
    print(f"[INIT] Loaded {len(g_mission_data)} missions")

def handle_main_menu_input(event: pygame.event.Event):
    """Handle main menu input.
    
    Side effects:
        Changes menu selection or game state
        
    Globals:
        Reads: g_game_state
        Writes: g_game_state
    """
    if event.type == pygame.KEYDOWN:
        selected = g_game_state['ui_state']['selected_menu_item']
        
        if event.key == pygame.K_UP:
            g_game_state['ui_state']['selected_menu_item'] = max(0, selected - 1)
        elif event.key == pygame.K_DOWN:
            g_game_state['ui_state']['selected_menu_item'] = min(3, selected + 1)
        elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
            if selected == 0:  # Start Mission
                g_game_state['current_state'] = GameState.MISSION_SELECTION.value
                g_game_state['ui_state']['selected_menu_item'] = 0  # Reset for mission selection
            elif selected == 1:  # Quick Battle (Test)
                init_test_game()
            elif selected == 2:  # Settings
                g_game_state['current_state'] = GameState.SETTINGS.value
            elif selected == 3:  # Exit
                pygame.quit()
                exit()

def handle_mission_selection_input(event: pygame.event.Event):
    """Handle mission selection input.
    
    Side effects:
        Changes mission selection or advances to squad selection
        
    Globals:
        Reads: g_game_state, g_mission_data
        Writes: g_game_state
    """
    if event.type == pygame.KEYDOWN:
        selected = g_game_state['ui_state']['selected_menu_item']
        mission_keys = list(g_mission_data.keys())
        
        if event.key == pygame.K_UP:
            g_game_state['ui_state']['selected_menu_item'] = max(0, selected - 1)
        elif event.key == pygame.K_DOWN:
            g_game_state['ui_state']['selected_menu_item'] = min(len(mission_keys) - 1, selected + 1)
        elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
            # Select mission and advance to squad selection
            mission_id = mission_keys[selected]
            g_game_state['menu_state']['selected_mission_id'] = mission_id
            g_game_state['menu_state']['selected_mission'] = g_mission_data[mission_id]
            
            # Set squad size based on mission (default to 4 for now)
            g_game_state['menu_state']['max_squad_size'] = 4
            g_game_state['menu_state']['squad_slots'] = [None] * 4
            g_game_state['menu_state']['squad_loadouts'] = [{} for _ in range(4)]
            
            g_game_state['current_state'] = GameState.SQUAD_SELECTION.value
            g_game_state['ui_state']['selected_menu_item'] = 0
        elif event.key == pygame.K_ESCAPE:
            g_game_state['current_state'] = GameState.MAIN_MENU.value

def handle_squad_selection_input(event: pygame.event.Event):
    """Handle squad selection input.
    
    Side effects:
        Changes squad composition or advances to loadout screen
        
    Globals:
        Reads: g_game_state, g_unit_templates
        Writes: g_game_state
    """
    if event.type == pygame.KEYDOWN:
        menu_state = g_game_state['menu_state']
        selected = g_game_state['ui_state']['selected_menu_item']
        
        if event.key == pygame.K_UP:
            g_game_state['ui_state']['selected_menu_item'] = max(0, selected - 1)
        elif event.key == pygame.K_DOWN:
            max_selection = len(menu_state['available_classes']) + menu_state['max_squad_size'] + 1  # Classes + slots + continue
            g_game_state['ui_state']['selected_menu_item'] = min(max_selection - 1, selected + 1)
        elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
            available_classes = menu_state['available_classes']
            
            if selected < len(available_classes):
                # Select a class to assign
                selected_class = available_classes[selected]
                # Find first empty slot
                for i, slot in enumerate(menu_state['squad_slots']):
                    if slot is None:
                        menu_state['squad_slots'][i] = selected_class
                        print(f"[MENU] Added {selected_class} to slot {i + 1}")
                        break
            elif selected < len(available_classes) + menu_state['max_squad_size']:
                # Clear a squad slot
                slot_index = selected - len(available_classes)
                if menu_state['squad_slots'][slot_index] is not None:
                    menu_state['squad_slots'][slot_index] = None
                    print(f"[MENU] Cleared slot {slot_index + 1}")
            else:
                # Continue to loadout (if squad has at least one member)
                if any(slot is not None for slot in menu_state['squad_slots']):
                    # Set current loadout slot to first occupied slot
                    for i, slot in enumerate(menu_state['squad_slots']):
                        if slot is not None:
                            menu_state['current_loadout_slot'] = i
                            break
                    g_game_state['current_state'] = GameState.LOADOUT_SCREEN.value
                    g_game_state['ui_state']['selected_menu_item'] = 0
                else:
                    print("[MENU] Need at least one squad member!")
        elif event.key == pygame.K_ESCAPE:
            g_game_state['current_state'] = GameState.MISSION_SELECTION.value

def handle_loadout_input(event: pygame.event.Event):
    """Handle loadout screen input.
    
    Side effects:
        Changes weapon/equipment assignments or advances to briefing
        
    Globals:
        Reads: g_game_state, g_weapon_data
        Writes: g_game_state
    """
    if event.type == pygame.KEYDOWN:
        menu_state = g_game_state['menu_state']
        selected = g_game_state['ui_state']['selected_menu_item']
        weapon_keys = list(g_weapon_data.keys())
        
        if event.key == pygame.K_UP:
            g_game_state['ui_state']['selected_menu_item'] = max(0, selected - 1)
        elif event.key == pygame.K_DOWN:
            max_items = len(weapon_keys) + 2  # Weapons + next/back buttons
            g_game_state['ui_state']['selected_menu_item'] = min(max_items - 1, selected + 1)
        elif event.key == pygame.K_LEFT:
            # Previous squad member
            current_slot = menu_state['current_loadout_slot']
            while True:
                current_slot = (current_slot - 1) % menu_state['max_squad_size']
                if menu_state['squad_slots'][current_slot] is not None:
                    menu_state['current_loadout_slot'] = current_slot
                    break
                if current_slot == menu_state['current_loadout_slot']:  # Avoid infinite loop
                    break
        elif event.key == pygame.K_RIGHT:
            # Next squad member
            current_slot = menu_state['current_loadout_slot']
            while True:
                current_slot = (current_slot + 1) % menu_state['max_squad_size']
                if menu_state['squad_slots'][current_slot] is not None:
                    menu_state['current_loadout_slot'] = current_slot
                    break
                if current_slot == menu_state['current_loadout_slot']:  # Avoid infinite loop
                    break
        elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
            if selected < len(weapon_keys):
                # Assign weapon to current squad member
                weapon_id = weapon_keys[selected]
                current_slot = menu_state['current_loadout_slot']
                if menu_state['squad_slots'][current_slot] is not None:
                    menu_state['squad_loadouts'][current_slot]['primary_weapon'] = weapon_id
                    print(f"[MENU] Assigned {weapon_id} to slot {current_slot + 1}")
            elif selected == len(weapon_keys):
                # Continue to briefing
                g_game_state['current_state'] = GameState.MISSION_BRIEFING.value
                g_game_state['ui_state']['selected_menu_item'] = 0
            elif selected == len(weapon_keys) + 1:
                # Back to squad selection
                g_game_state['current_state'] = GameState.SQUAD_SELECTION.value
        elif event.key == pygame.K_ESCAPE:
            g_game_state['current_state'] = GameState.SQUAD_SELECTION.value

def handle_briefing_input(event: pygame.event.Event):
    """Handle mission briefing input.
    
    Side effects:
        Starts mission or returns to loadout
        
    Globals:
        Reads: g_game_state
        Writes: g_game_state
    """
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
            # Deploy to mission!
            start_selected_mission()
        elif event.key == pygame.K_ESCAPE:
            g_game_state['current_state'] = GameState.LOADOUT_SCREEN.value

def handle_settings_input(event: pygame.event.Event):
    """Handle settings screen input.
    
    Side effects:
        Returns to main menu
        
    Globals:
        Reads: g_game_state
        Writes: g_game_state
    """
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE or event.key == pygame.K_RETURN:
            g_game_state['current_state'] = GameState.MAIN_MENU.value

def render_settings():
    """Render settings screen.
    
    Side effects:
        Draws settings UI to g_screen
        
    Globals:
        Reads: g_font, g_screen
        Writes: g_screen
    """
    g_screen.fill((30, 30, 30))
    
    # Title
    title_text = g_font.render("SETTINGS", True, (255, 255, 100))
    title_rect = title_text.get_rect(center=(Cfg.SCREEN_WIDTH // 2, 100))
    g_screen.blit(title_text, title_rect)
    
    # Placeholder settings info
    settings_lines = [
        "Settings screen - Coming Soon!",
        "",
        "Future features:",
        "• Audio volume controls",
        "• Display options",
        "• Control remapping",
        "• Difficulty settings",
        "",
        "Press ESC or ENTER to return to main menu"
    ]
    
    for i, line in enumerate(settings_lines):
        y_pos = 200 + i * 30
        color = (200, 200, 200) if line else (100, 100, 100)
        if line:
            line_text = g_font.render(line, True, color)
            line_rect = line_text.get_rect(center=(Cfg.SCREEN_WIDTH // 2, y_pos))
            g_screen.blit(line_text, line_rect)

def initialize_unit_ammo(unit: Character, weapon_id: str):
    """Initialize ammo for a unit based on their weapon.
    
    Side effects:
        Updates unit's ammo tracking
        
    Globals:
        Reads: g_weapon_data
    """
    weapon_data = g_weapon_data.get(weapon_id, {})
    ammo_capacity = weapon_data.get('ammo_capacity', 30)
    
    unit[K_WEAPON_TYPE] = weapon_id
    unit[K_MAX_AMMO] = ammo_capacity
    unit[K_CURRENT_AMMO] = ammo_capacity  # Start with full ammo
    
    print(f"[AMMO] {unit[K_NAME]} equipped {weapon_data.get('name', weapon_id)} with {ammo_capacity} ammo")

def reload_weapon(unit_id: str) -> bool:
    """Reload unit's weapon.
    
    Returns:
        True if reload was successful, False otherwise
        
    Side effects:
        Updates unit's ammo and deducts AP
        
    Globals:
        Reads: g_player_squad, g_enemy_units
        Writes: Unit ammo and AP
    """
    unit = find_unit_by_id(unit_id)
    if not unit:
        return False
    
    # Check if unit has AP and needs reload
    if unit[K_AP] < Cfg.AP_COST_RELOAD:
        g_game_state['combat_log'].append(f"{unit[K_NAME]} doesn't have enough AP to reload")
        return False
    
    if unit[K_CURRENT_AMMO] >= unit[K_MAX_AMMO]:
        g_game_state['combat_log'].append(f"{unit[K_NAME]}'s weapon is already full")
        return False
    
    # Perform reload
    unit[K_AP] -= Cfg.AP_COST_RELOAD
    unit[K_CURRENT_AMMO] = unit[K_MAX_AMMO]
    
    g_game_state['combat_log'].append(f"{unit[K_NAME]} reloaded weapon ({unit[K_CURRENT_AMMO]}/{unit[K_MAX_AMMO]})")
    
    # Create reload effect
    g_effect_queue.append(create_effect(
        'text',
        unit[K_X], unit[K_Y],
        text="RELOAD",
        color=(100, 255, 100),
        duration=30
    ))
    
    return True

# ======================================================================
# === [15] MAIN EXECUTION
# ======================================================================
if __name__ == "__main__":
    load_game_data()
    main() 