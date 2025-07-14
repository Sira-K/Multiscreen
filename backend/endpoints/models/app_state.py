# models/app_state.py - HYBRID VERSION
"""
Hybrid application state: 
- Clients managed in memory (for real-time connections)
- Groups managed through Docker discovery (pure Docker)
"""

import threading
import json
import os
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class AppState:
    """
    Hybrid application state:
    - Client connections managed in memory (real-time)
    - Group management delegated to Docker containers
    """
    
    def __init__(self):
        """Initialize application state"""
        # Client management (kept in memory for real-time tracking)
        self.clients = {}
        self.clients_lock = threading.RLock()
        
        # Configuration settings
        self.screen_count = 2
        self.orientation = "horizontal"  # "horizontal", "vertical", or "grid"
        self.grid_rows = 2
        self.grid_cols = 2
        self.srt_ip = "127.0.0.1"
        
        # State management
        self.config_lock = threading.RLock()
        self.last_updated = 0
        
        # NO GROUP STATE - groups come from Docker discovery
        # Remove: self.groups, self.groups_lock, etc.
        
    def update(self, **kwargs) -> None:
        """Update configuration properties"""
        with self.config_lock:
            for key, value in kwargs.items():
                if hasattr(self, key) and key not in ['clients', 'clients_lock']:
                    setattr(self, key, value)
                else:
                    logger.warning(f"Attempted to set unknown/protected property: {key}")
            
            import time
            self.last_updated = time.time()
    
    # Client Management Methods (keep these)
    def get_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get a client by ID with thread safety"""
        with self.clients_lock:
            return self.clients.get(client_id)
    
    def update_client(self, client_id: str, **kwargs) -> None:
        """Update a client's properties"""
        with self.clients_lock:
            if client_id not in self.clients:
                logger.warning(f"Attempted to update non-existent client: {client_id}")
                return
            for key, value in kwargs.items():
                self.clients[client_id][key] = value
    
    def add_client(self, client_id: str, client_data: Dict[str, Any]) -> None:
        """Add a new client"""
        with self.clients_lock:
            self.clients[client_id] = client_data
            logger.info(f"Added client: {client_id}")
    
    def remove_client(self, client_id: str) -> bool:
        """Remove a client"""
        with self.clients_lock:
            if client_id in self.clients:
                del self.clients[client_id]
                logger.info(f"Removed client: {client_id}")
                return True
            return False
    
    def get_active_clients_count(self, group_id: str = None) -> int:
        """Get count of active clients, optionally filtered by group"""
        import time
        current_time = time.time()
        inactive_threshold = 60
        
        with self.clients_lock:
            active_count = 0
            for client in self.clients.values():
                if current_time - client.get('last_seen', 0) <= inactive_threshold:
                    if group_id is None or client.get('group_id') == group_id:
                        active_count += 1
            return active_count
    
    def get_clients_by_group(self, group_id: str) -> List[Dict[str, Any]]:
        """Get all clients assigned to a specific group"""
        with self.clients_lock:
            group_clients = []
            for client_id, client_data in self.clients.items():
                if client_data.get('group_id') == group_id:
                    client_copy = client_data.copy()
                    client_copy['client_id'] = client_id
                    group_clients.append(client_copy)
            return group_clients
    
    # Layout/Configuration Methods (keep these)
    def get_effective_screen_count(self) -> int:
        """Get effective screen count based on orientation"""
        if self.orientation == "grid":
            return self.grid_rows * self.grid_cols
        return self.screen_count
    
    def get_layout_description(self) -> str:
        """Get human-readable layout description"""
        if self.orientation == "grid":
            return f"{self.grid_rows}×{self.grid_cols} grid ({self.grid_rows * self.grid_cols} screens)"
        return f"{self.orientation} ({self.screen_count} screens)"
    
    def set_grid_layout(self, rows: int, cols: int) -> None:
        """Set grid layout"""
        with self.config_lock:
            self.orientation = "grid"
            self.grid_rows = rows
            self.grid_cols = cols
            self.screen_count = rows * cols
            import time
            self.last_updated = time.time()
    
    def set_linear_layout(self, orientation: str, count: int) -> None:
        """Set horizontal or vertical layout"""
        with self.config_lock:
            if orientation in ["horizontal", "vertical"]:
                self.orientation = orientation
                self.screen_count = count
                import time
                self.last_updated = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for serialization (config only)"""
        with self.config_lock:
            return {
                'screen_count': self.screen_count,
                'orientation': self.orientation,
                'grid_rows': self.grid_rows,
                'grid_cols': self.grid_cols,
                'srt_ip': self.srt_ip,
                'last_updated': self.last_updated
            }
    
    def load_from_dict(self, data: Dict[str, Any]) -> None:
        """Load configuration from dict"""
        with self.config_lock:
            for key, value in data.items():
                if hasattr(self, key) and key not in ['clients', 'clients_lock', 'config_lock']:
                    setattr(self, key, value)

# Create singleton instance
state = AppState()