# app_config.py - Save this file in your /home/sirakong/Mulitiscreen/backend/endpoints/ directory

import os
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class UnifiedConfig:
    """
    Unified configuration system that handles both Flask app settings 
    and screen layout configuration in a single JSON file
    """
    
    def __init__(self, config_file=None):
        # Default config file location
        if config_file is None:
            self.config_file = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), 
                'app_config.json'
            )
        else:
            self.config_file = config_file
        
        # Default configuration
        self.defaults = {
            # Flask/Server settings
            "server": {
                "host": "0.0.0.0",
                "port": 5001,
                "debug": True,
                "secret_key": "your-secret-key-change-in-production"
            },
            
            # File/Video settings  
            "files": {
                "upload_folder": "uploads",
                "download_folder": "resized_video",
                "max_file_size_mb": 2048,
                "allowed_extensions": ["mp4", "avi", "mov", "mkv", "wmv", "flv", "webm", "m4v"]
            },
            
            # Screen/Display settings
            "display": {
                "screen_count": 2,
                "orientation": "horizontal",  # horizontal, vertical, grid
                "grid_rows": 2,
                "grid_cols": 2,
                "screen_ips": {},
                "srt_ip": "127.0.0.1"
            },
            
            # System settings
            "system": {
                "architecture": "hybrid_docker_discovery",
                "version": "3.1.0",
                "log_level": "INFO"
            }
        }
        
        self.config = {}
        self.load()
    
    def load(self):
        """Load configuration from JSON file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                
                # Merge with defaults (keeps structure, updates values)
                self.config = self._deep_merge(self.defaults.copy(), loaded_config)
                
                # Validate and fix any issues
                self._validate_config()
                
                logger.info(f"Configuration loaded from {self.config_file}")
                self._log_config_summary()
                
            else:
                logger.info(f"Config file not found, using defaults: {self.config_file}")
                self.config = self.defaults.copy()
                self.save()  # Create the file with defaults
                
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            logger.info("Using default configuration")
            self.config = self.defaults.copy()
    
    def save(self):
        """Save current configuration to JSON file"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            # Write config to file
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            
            logger.info(f"Configuration saved to {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            return False
    
    def get(self, section, key=None, default=None):
        """Get configuration value"""
        try:
            if key is None:
                return self.config.get(section, default)
            else:
                return self.config.get(section, {}).get(key, default)
        except:
            return default
    
    def set(self, section, key=None, value=None):
        """Set configuration value"""
        try:
            if key is None:
                # Setting entire section
                self.config[section] = value
            else:
                # Setting specific key in section
                if section not in self.config:
                    self.config[section] = {}
                self.config[section][key] = value
            
            # Validate after setting
            self._validate_config()
            return True
            
        except Exception as e:
            logger.error(f"Error setting config: {e}")
            return False
    
    def update_display_layout(self, orientation=None, screen_count=None, grid_rows=None, grid_cols=None):
        """Update display layout settings"""
        display = self.config.setdefault("display", {})
        
        if orientation:
            display["orientation"] = orientation
        if screen_count:
            display["screen_count"] = screen_count
        if grid_rows:
            display["grid_rows"] = grid_rows
        if grid_cols:
            display["grid_cols"] = grid_cols
        
        self._validate_config()
        
    def get_flask_config(self):
        """Get configuration formatted for Flask app.config"""
        base_dir = os.path.dirname(os.path.abspath(self.config_file))
        
        return {
            'SECRET_KEY': self.get('server', 'secret_key'),
            'DEBUG': self.get('server', 'debug'),
            'UPLOAD_FOLDER': os.path.join(base_dir, self.get('files', 'upload_folder')),
            'DOWNLOAD_FOLDER': os.path.join(base_dir, self.get('files', 'download_folder')),
            'MAX_CONTENT_LENGTH': self.get('files', 'max_file_size_mb') * 1024 * 1024,
            'ALLOWED_EXTENSIONS': set(self.get('files', 'allowed_extensions', []))
        }
    
    def get_layout_presets(self):
        """Get layout presets for quick configuration"""
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
            {"name": "3×3 Grid", "orientation": "grid", "grid_rows": 3, "grid_cols": 3, "screen_count": 9},
        ]
    
    def apply_preset(self, preset_name):
        """Apply a layout preset"""
        presets = self.get_layout_presets()
        
        for preset in presets:
            if preset["name"] == preset_name:
                self.update_display_layout(
                    orientation=preset["orientation"],
                    screen_count=preset["screen_count"],
                    grid_rows=preset.get("grid_rows"),
                    grid_cols=preset.get("grid_cols")
                )
                logger.info(f"Applied preset: {preset_name}")
                return True
        
        logger.warning(f"Preset not found: {preset_name}")
        return False
    
    def _validate_config(self):
        """Validate and fix configuration"""
        display = self.config.get("display", {})
        
        # Fix grid settings
        if display.get("orientation") == "grid":
            rows = display.get("grid_rows", 2)
            cols = display.get("grid_cols", 2)
            
            if rows <= 0:
                display["grid_rows"] = 2
                rows = 2
            if cols <= 0:
                display["grid_cols"] = 2  
                cols = 2
            
            # Ensure screen count matches grid
            expected_count = rows * cols
            if display.get("screen_count") != expected_count:
                display["screen_count"] = expected_count
                logger.info(f"Adjusted screen count to {expected_count} for {rows}×{cols} grid")
    
    def _deep_merge(self, dict1, dict2):
        """Deep merge two dictionaries"""
        result = dict1.copy()
        
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _log_config_summary(self):
        """Log a summary of current configuration"""
        display = self.config.get("display", {})
        files = self.config.get("files", {})
        server = self.config.get("server", {})
        
        if display.get("orientation") == "grid":
            layout = f"{display.get('grid_rows')}×{display.get('grid_cols')} grid ({display.get('screen_count')} screens)"
        else:
            layout = f"{display.get('orientation')} ({display.get('screen_count')} screens)"
        
        logger.info(f"Config summary:")
        logger.info(f"  Server: {server.get('host')}:{server.get('port')}")
        logger.info(f"  Layout: {layout}")
        logger.info(f"  Upload folder: {files.get('upload_folder')}")
        logger.info(f"  Download folder: {files.get('download_folder')}")

# Global config instance
config = UnifiedConfig()

# Legacy compatibility functions for existing code
def load_config(state):
    """Legacy function - loads display config into state object"""
    display = config.get('display')
    if display:
        state.screen_count = display.get('screen_count', 2)
        state.orientation = display.get('orientation', 'horizontal')
        state.grid_rows = display.get('grid_rows', 2)
        state.grid_cols = display.get('grid_cols', 2)
        state.screen_ips = display.get('screen_ips', {})
        state.srt_ip = display.get('srt_ip', '127.0.0.1')

def save_config(state):
    """Legacy function - saves display config from state object"""
    config.config['display'] = {
        'screen_count': getattr(state, 'screen_count', 2),
        'orientation': getattr(state, 'orientation', 'horizontal'),
        'grid_rows': getattr(state, 'grid_rows', 2),
        'grid_cols': getattr(state, 'grid_cols', 2),
        'screen_ips': getattr(state, 'screen_ips', {}),
        'srt_ip': getattr(state, 'srt_ip', '127.0.0.1')
    }
    return config.save()