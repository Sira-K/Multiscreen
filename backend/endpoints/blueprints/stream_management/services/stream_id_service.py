import os
import json
import threading
import uuid
import logging
from typing import Dict

logger = logging.getLogger(__name__)

class StreamIDService:
    """Manages persistent stream IDs across application restarts"""
    
    def __init__(self, storage_file: str = "persistent_stream_ids.json"):
        self.storage_file = storage_file
        self.ids_data = {"streams": {}}
        self._lock = threading.RLock()
        self._load_ids()
    
    def _load_ids(self):
        """Load persistent stream IDs from file"""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r') as f:
                    self.ids_data = json.load(f)
                logger.debug(f"Loaded persistent stream IDs from {self.storage_file}")
        except Exception as e:
            logger.error(f"Error loading persistent stream IDs: {e}")
            self.ids_data = {"streams": {}}
    
    def _save_ids(self):
        """Save persistent stream IDs to file"""
        try:
            with open(self.storage_file, 'w') as f:
                json.dump(self.ids_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving persistent stream IDs: {e}")
    
    def get_stream_id(self, group_key: str, stream_name: str) -> str:
        """Get or create persistent stream ID"""
        with self._lock:
            if group_key not in self.ids_data["streams"]:
                self.ids_data["streams"][group_key] = {}
            
            if stream_name not in self.ids_data["streams"][group_key]:
                stream_id = str(uuid.uuid4())[:8]
                self.ids_data["streams"][group_key][stream_name] = stream_id
                self._save_ids()
                logger.debug(f"Created new stream ID: {stream_name} -> {stream_id}")
            
            return self.ids_data["streams"][group_key][stream_name]
    
    def get_group_streams(self, group_id: str, group_name: str, screen_count: int) -> Dict[str, str]:
        """Get all persistent stream IDs for a group"""
        group_key = f"group_{group_id}"
        
        streams = {}
        streams["test"] = self.get_stream_id(group_key, "test")
        
        for i in range(screen_count):
            streams[f"test{i}"] = self.get_stream_id(group_key, f"test{i}")
        
        return streams