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
    SQUAD_MANAGEMENT = "squad_management"
    MISSION_BRIEFING = "mission_briefing"
    TACTICAL_COMBAT = "tactical_combat"
    ENEMY_TURN = "enemy_turn"
    INVENTORY = "inventory"
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
    
    # Initialize with test squad for development
    init_test_game()
    
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
    
    # Create enemy units
    g_enemy_units = []
    enemy1 = create_character('soldier', 17, 12)
    enemy1[K_FACTION] = 'enemy'
    g_enemy_units.append(enemy1)
    
    enemy2 = create_character('soldier', 18, 11)
    enemy2[K_FACTION] = 'enemy'
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
        handle_menu_input(event)
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
            if active_unit and is_valid_position(x, y):
                if can_reach_position(active_unit, x, y):
                    old_x, old_y = active_unit[K_X], active_unit[K_Y]
                    move_unit(active_unit[K_ID], x, y)
                    print(f"[INPUT] Moved {active_unit[K_NAME]} to ({x}, {y})")
                else:
                    print(f"[INPUT] Cannot reach ({x}, {y}) - not enough AP")

def handle_tile_right_click(x: int, y: int):
    """Handle right click on tile."""
    # For now, just show tile info
    if is_valid_position(x, y):
        tile = g_current_map[y][x]
        print(f"[INPUT] Tile ({x}, {y}): {tile[K_TYPE]}, Cover: {tile.get(K_COVER, 0)}")

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
    # Simple AI: just end turn for now
    # TODO: Implement actual AI behaviors
    g_game_state['current_state'] = GameState.TACTICAL_COMBAT.value
    
    # Reset all player unit AP for new turn
    for unit in g_player_squad:
        unit[K_AP] = unit[K_MAX_AP]
    
    g_game_state['turn_count'] += 1
    print(f"[AI] Turn {g_game_state['turn_count']} - Player turn begins")

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
    """Render main menu."""
    title_text = g_font.render("Tactical Squad Game", True, (255, 255, 255))
    g_screen.blit(title_text, (Cfg.SCREEN_WIDTH // 2 - 100, Cfg.SCREEN_HEIGHT // 2))

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
        unit[K_X] = new_x
        unit[K_Y] = new_y
        unit[K_AP] -= ap_cost

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

def handle_menu_input(event: pygame.event.Event):
    """Handle main menu input."""
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_SPACE:
            # Start test game
            init_test_game()

# ======================================================================
# === [15] MAIN EXECUTION
# ======================================================================
if __name__ == "__main__":
    load_game_data()
    main() 