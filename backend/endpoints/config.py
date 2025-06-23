import os
import json
import logging

logger = logging.getLogger(__name__)

# Configuration file path
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')

def save_config(state):
    """
    Save the application state to a configuration file
    Now includes grid layout support
    
    Args:
        state: The application state object
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create a serializable dictionary from the state
        config = {
            'screen_count': getattr(state, 'screen_count', 2),
            'orientation': getattr(state, 'orientation', 'horizontal'),
            'grid_rows': getattr(state, 'grid_rows', 2),
            'grid_cols': getattr(state, 'grid_cols', 2),
            'screen_ips': getattr(state, 'screen_ips', {}),
            'srt_ip': getattr(state, 'srt_ip', '127.0.0.1')
        }
        
        # Validate grid settings
        if config['orientation'] == 'grid':
            if config['grid_rows'] <= 0:
                config['grid_rows'] = 2
            if config['grid_cols'] <= 0:
                config['grid_cols'] = 2
            # Ensure screen count matches grid
            expected_count = config['grid_rows'] * config['grid_cols']
            if config['screen_count'] != expected_count:
                logger.info(f"Adjusting screen count from {config['screen_count']} to {expected_count} for grid layout")
                config['screen_count'] = expected_count
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        
        # Write the configuration to file
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
            
        logger.info(f"Configuration saved to {CONFIG_FILE}")
        
        # Log the saved configuration
        if config['orientation'] == 'grid':
            layout_desc = f"{config['grid_rows']}×{config['grid_cols']} grid ({config['screen_count']} screens)"
        else:
            layout_desc = f"{config['orientation']} ({config['screen_count']} screens)"
        
        logger.info(f"Saved layout: {layout_desc}")
        
        return True
    except Exception as e:
        logger.error(f"Error saving configuration: {e}")
        return False

def load_config(state):
    """
    Load the configuration from file into the application state
    Now includes grid layout support
    
    Args:
        state: The application state object
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                
            # Update state with loaded configuration
            if 'screen_count' in config:
                state.screen_count = config['screen_count']
            if 'orientation' in config:
                state.orientation = config['orientation']
            if 'grid_rows' in config:
                state.grid_rows = config['grid_rows']
            if 'grid_cols' in config:
                state.grid_cols = config['grid_cols']
            if 'screen_ips' in config:
                state.screen_ips = config['screen_ips']
            if 'srt_ip' in config:
                state.srt_ip = config['srt_ip']
            
            # Validate and fix grid settings if needed
            if state.orientation == 'grid':
                if state.grid_rows <= 0:
                    logger.warning("Invalid grid_rows in config, setting to 2")
                    state.grid_rows = 2
                if state.grid_cols <= 0:
                    logger.warning("Invalid grid_cols in config, setting to 2")
                    state.grid_cols = 2
                
                # Ensure screen count matches grid
                expected_count = state.grid_rows * state.grid_cols
                if state.screen_count != expected_count:
                    logger.info(f"Adjusting screen count from {state.screen_count} to {expected_count} for grid layout")
                    state.screen_count = expected_count
            
            # Log the loaded configuration
            if state.orientation == 'grid':
                layout_desc = f"{state.grid_rows}×{state.grid_cols} grid ({state.screen_count} screens)"
            else:
                layout_desc = f"{state.orientation} ({state.screen_count} screens)"
            
            logger.info(f"Configuration loaded from {CONFIG_FILE}")
            logger.info(f"Loaded layout: {layout_desc}")
            return True
        else:
            logger.warning(f"Configuration file not found: {CONFIG_FILE}")
            # Set default grid values for new installations
            state.grid_rows = 2
            state.grid_cols = 2
            logger.info("Set default grid configuration: 2×2")
            return False
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        # Set safe defaults on error
        state.grid_rows = 2
        state.grid_cols = 2
        state.orientation = 'horizontal'
        state.screen_count = 2
        return False

def get_layout_presets():
    """
    Get common layout presets for quick configuration
    
    Returns:
        List of layout preset dictionaries
    """
    return [
        # Horizontal layouts
        {"name": "2 Horizontal", "orientation": "horizontal", "screen_count": 2},
        {"name": "3 Horizontal", "orientation": "horizontal", "screen_count": 3},
        {"name": "4 Horizontal", "orientation": "horizontal", "screen_count": 4},
        
        # Vertical layouts
        {"name": "2 Vertical", "orientation": "vertical", "screen_count": 2},
        {"name": "3 Vertical", "orientation": "vertical", "screen_count": 3},
        {"name": "4 Vertical", "orientation": "vertical", "screen_count": 4},
        
        # Grid layouts
        {"name": "2×2 Grid", "orientation": "grid", "grid_rows": 2, "grid_cols": 2, "screen_count": 4},
        {"name": "2×3 Grid", "orientation": "grid", "grid_rows": 2, "grid_cols": 3, "screen_count": 6},
        {"name": "3×2 Grid", "orientation": "grid", "grid_rows": 3, "grid_cols": 2, "screen_count": 6},
        {"name": "3×3 Grid", "orientation": "grid", "grid_rows": 3, "grid_cols": 3, "screen_count": 9},
        {"name": "2×4 Grid", "orientation": "grid", "grid_rows": 2, "grid_cols": 4, "screen_count": 8},
        {"name": "4×2 Grid", "orientation": "grid", "grid_rows": 4, "grid_cols": 2, "screen_count": 8},
    ]

def apply_layout_preset(state, preset_name):
    """
    Apply a layout preset to the application state
    
    Args:
        state: The application state object
        preset_name: Name of the preset to apply
        
    Returns:
        True if successful, False if preset not found
    """
    presets = get_layout_presets()
    
    for preset in presets:
        if preset["name"] == preset_name:
            state.orientation = preset["orientation"]
            state.screen_count = preset["screen_count"]
            
            if preset["orientation"] == "grid":
                state.grid_rows = preset["grid_rows"]
                state.grid_cols = preset["grid_cols"]
            
            logger.info(f"Applied layout preset: {preset_name}")
            return True
    
    logger.warning(f"Layout preset not found: {preset_name}")
    return False