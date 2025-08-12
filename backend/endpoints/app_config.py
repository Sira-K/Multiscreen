"""
Application Configuration

Simple configuration management for the multi-screen server.
"""

import os
import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class AppConfig:
    """Simple application configuration manager"""
    
    def __init__(self, config_file: str = None):
        self.config_file = config_file or os.path.join(
            os.path.dirname(__file__), 'app_config.json'
        )
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            else:
                # Create default config
                default_config = self._get_default_config()
                self._save_config(default_config)
                return default_config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "server": {
                "host": "0.0.0.0",
                "port": 5000,
                "debug": True
            },
            "files": {
                "upload_folder": "uploads",
                "download_folder": "uploads",
                "max_file_size_mb": 2048,
                "allowed_extensions": ["mp4", "avi", "mov", "mkv", "wmv", "flv", "webm", "m4v"]
            },
            "streaming": {
                "default_framerate": 30,
                "default_bitrate": "3000k",
                "srt_latency": 5000000,
                "srt_timeout": 5000
            }
        }
    
    def _save_config(self, config: Dict[str, Any]) -> bool:
        """Save configuration to file"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False
    
    def get(self, section: str, key: str = None, default: Any = None) -> Any:
        """Get configuration value"""
        try:
            if key is None:
                return self.config.get(section, default)
            return self.config.get(section, {}).get(key, default)
        except Exception as e:
            logger.error(f"Failed to get config {section}.{key}: {e}")
            return default
    
    def set(self, section: str, key: str, value: Any) -> bool:
        """Set configuration value"""
        try:
            if section not in self.config:
                self.config[section] = {}
            
            if key is None:
                self.config[section] = value
            else:
                self.config[section][key] = value
            
            return self._save_config(self.config)
        except Exception as e:
            logger.error(f"Failed to set config {section}.{key}: {e}")
            return False
    
    def save(self) -> bool:
        """Save current configuration"""
        return self._save_config(self.config)
    
    def reload(self) -> bool:
        """Reload configuration from file"""
        try:
            self.config = self._load_config()
            return True
        except Exception as e:
            logger.error(f"Failed to reload config: {e}")
            return False