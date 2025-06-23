# models/app_state.py
import threading
import json
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class AppState:
    """
    Application state singleton class that manages global application state
    with thread-safe operations. Now includes grid layout support.
    """
    
    def __init__(self):
        """Initialize application state with default values"""
        self.screen_count = 2
        self.orientation = "horizontal"  # "horizontal", "vertical", or "grid"
        self.grid_rows = 2  # Number of rows for grid layout
        self.grid_cols = 2  # Number of columns for grid layout
        self.screen_ips = {}
        self.srt_ip = "127.0.0.1"  # Default to localhost
        self.ffmpeg_process_id = None
        self.docker_container_id = None
        self.clients = {}
        self.stream_assignments = {}
        self.clients_lock = threading.RLock()
        self.config_lock = threading.RLock()
        self.last_updated = 0  # Timestamp of last update
        
    def update(self, **kwargs) -> None:
        """
        Update multiple state properties atomically
        
        Args:
            **kwargs: Properties to update
        """
        with self.config_lock:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
                else:
                    logger.warning(f"Attempted to set unknown property: {key}")
            
            # Update last_updated timestamp
            import time
            self.last_updated = time.time()
    
    def get_effective_screen_count(self) -> int:
        """
        Get the effective screen count based on orientation
        
        Returns:
            Effective number of screens
        """
        if self.orientation == "grid":
            return self.grid_rows * self.grid_cols
        return self.screen_count
    
    def get_layout_description(self) -> str:
        """
        Get a human-readable description of the current layout
        
        Returns:
            Layout description string
        """
        if self.orientation == "grid":
            return f"{self.grid_rows}×{self.grid_cols} grid ({self.grid_rows * self.grid_cols} screens)"
        return f"{self.orientation} ({self.screen_count} screens)"
    
    def set_grid_layout(self, rows: int, cols: int) -> None:
        """
        Set grid layout and update related properties
        
        Args:
            rows: Number of grid rows
            cols: Number of grid columns
        """
        with self.config_lock:
            self.orientation = "grid"
            self.grid_rows = rows
            self.grid_cols = cols
            self.screen_count = rows * cols
            
            # Update timestamp
            import time
            self.last_updated = time.time()
    
    def set_linear_layout(self, orientation: str, count: int) -> None:
        """
        Set horizontal or vertical layout
        
        Args:
            orientation: "horizontal" or "vertical"
            count: Number of screens
        """
        with self.config_lock:
            if orientation in ["horizontal", "vertical"]:
                self.orientation = orientation
                self.screen_count = count
                
                # Update timestamp
                import time
                self.last_updated = time.time()
            else:
                logger.warning(f"Invalid orientation: {orientation}")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert state to a dictionary for serialization
        
        Returns:
            Dictionary representation of serializable state
        """
        with self.config_lock:
            # Only include serializable properties
            serializable = {
                'screen_count': self.screen_count,
                'orientation': self.orientation,
                'grid_rows': self.grid_rows,
                'grid_cols': self.grid_cols,
                'screen_ips': self.screen_ips,
                'srt_ip': self.srt_ip,
                'last_updated': self.last_updated
            }
            return serializable
    
    def load_from_dict(self, data: Dict[str, Any]) -> None:
        """
        Load state from a dictionary
        
        Args:
            data: Dictionary containing state data
        """
        with self.config_lock:
            for key, value in data.items():
                if hasattr(self, key):
                    setattr(self, key, value)
                else:
                    logger.warning(f"Unknown property in config: {key}")
            
            # Validate grid settings
            if self.orientation == "grid":
                if self.grid_rows <= 0:
                    self.grid_rows = 2
                if self.grid_cols <= 0:
                    self.grid_cols = 2
                # Ensure screen count matches grid
                expected_count = self.grid_rows * self.grid_cols
                if self.screen_count != expected_count:
                    logger.info(f"Adjusting screen count from {self.screen_count} to {expected_count} for grid layout")
                    self.screen_count = expected_count
    
    def save_to_file(self, filepath: str) -> bool:
        """
        Save state to a JSON file
        
        Args:
            filepath: Path to save the state
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.config_lock:
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                
                # Serialize state
                state_dict = self.to_dict()
                
                # Write to file
                with open(filepath, 'w') as f:
                    json.dump(state_dict, f, indent=2)
                    
                logger.info(f"State saved to {filepath}")
                return True
        except Exception as e:
            logger.error(f"Error saving state: {e}")
            return False
    
    def load_from_file(self, filepath: str) -> bool:
        """
        Load state from a JSON file
        
        Args:
            filepath: Path to load the state from
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    
                self.load_from_dict(data)
                logger.info(f"State loaded from {filepath}")
                return True
            else:
                logger.warning(f"State file not found: {filepath}")
                return False
        except Exception as e:
            logger.error(f"Error loading state: {e}")
            return False
    
    def get_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a client by ID with thread safety
        
        Args:
            client_id: The client ID to look up
            
        Returns:
            Client data or None if not found
        """
        with self.clients_lock:
            return self.clients.get(client_id)
    
    def update_client(self, client_id: str, **kwargs) -> None:
        """
        Update a client's properties
        
        Args:
            client_id: The client ID to update
            **kwargs: Properties to update
        """
        with self.clients_lock:
            if client_id not in self.clients:
                logger.warning(f"Attempted to update non-existent client: {client_id}")
                return
                
            for key, value in kwargs.items():
                self.clients[client_id][key] = value
    
    def get_grid_position(self, index: int) -> Dict[str, int]:
        """
        Get grid position (row, col) for a given index
        
        Args:
            index: 0-based index
            
        Returns:
            Dictionary with 'row' and 'col' keys (1-based)
        """
        if self.orientation != "grid":
            return {"row": 1, "col": index + 1}
        
        row = (index // self.grid_cols) + 1
        col = (index % self.grid_cols) + 1
        return {"row": row, "col": col}
    
    def get_index_from_grid_position(self, row: int, col: int) -> int:
        """
        Get index from grid position
        
        Args:
            row: 1-based row number
            col: 1-based column number
            
        Returns:
            0-based index
        """
        return (row - 1) * self.grid_cols + (col - 1)

# Create a singleton instance
state = AppState()