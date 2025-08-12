import uuid
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

class StreamIDService:
    """Service for managing stream IDs"""
    
    def __init__(self):
        self._group_streams = {}  # In-memory storage for now
    
    def get_group_streams(self, group_id: str, group_name: str, screen_count: int) -> Dict[str, str]:
        """Get or create persistent stream IDs for a group"""
        logger.info(f"Getting persistent streams for group {group_name} ({screen_count} screens)")
        
        # Check if we already have streams for this group
        if group_id in self._group_streams:
            existing_streams = self._group_streams[group_id]
            logger.info(f"Found existing streams: {existing_streams}")
            return existing_streams
        
        # Generate new stream IDs
        streams = self._generate_stream_ids(group_id, group_name, screen_count)
        
        # Store them for this group
        self._group_streams[group_id] = streams
        
        logger.info(f"Generated new streams: {streams}")
        return streams
    
    def _generate_stream_ids(self, group_id: str, group_name: str, screen_count: int) -> Dict[str, str]:
        """Generate stream IDs for a group"""
        # Generate a unique session ID based on current time and group
        session_id = str(uuid.uuid4())[:8]
        
        streams = {}
        
        # Main/combined stream
        streams["combined"] = f"split_{session_id}"
        
        # Individual screen streams
        for i in range(screen_count):
            streams[f"screen{i}"] = f"{session_id}_{i}"
        
        return streams
    
    def clear_group_streams(self, group_id: str):
        """Clear stream IDs for a group"""
        if group_id in self._group_streams:
            del self._group_streams[group_id]
            logger.info(f"Cleared streams for group {group_id}")
    
    def get_all_group_streams(self) -> Dict[str, Dict[str, str]]:
        """Get all group streams (for debugging)"""
        return self._group_streams.copy()
