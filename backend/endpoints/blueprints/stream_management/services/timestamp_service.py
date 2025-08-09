# backend/endpoints/blueprints/stream_management/services/timestamp_service.py
"""
Dynamic Timestamp Service for OpenVideoWalls Implementation
Based on the OpenVideoWalls paper: embeds dynamic Unix timestamps in SEI metadata
"""

import time
import threading
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class TimestampService:
    """
    Service for generating dynamic timestamps for video synchronization
    Implements the OpenVideoWalls paper's timestamp embedding approach
    """
    
    def __init__(self, offset_seconds: float = 2.0):
        """
        Initialize timestamp service
        
        Args:
            offset_seconds: Buffer time ahead of current time (1-3x RTT recommended)
        """
        self.offset_seconds = offset_seconds
        self._lock = threading.Lock()
        
    def generate_timestamp_hex(self, additional_offset: float = 0.0) -> str:
        """
        Generate a dynamic Unix timestamp in hex format for SEI embedding
        
        Args:
            additional_offset: Additional offset for this specific frame
            
        Returns:
            Hex-encoded timestamp string for SEI metadata
        """
        with self._lock:
            # Get current time + offset (as per OpenVideoWalls paper)
            current_time = time.time()
            timestamp = current_time + self.offset_seconds + additional_offset
            
            # Convert to milliseconds (paper uses millisecond precision)
            timestamp_ms = int(timestamp * 1000)
            
            # Convert to hex string (8 bytes = 16 hex chars)
            timestamp_hex = f"{timestamp_ms:016x}"
            
            logger.debug(f"Generated timestamp: {timestamp_ms}ms -> {timestamp_hex}")
            return timestamp_hex
    
    def get_display_timestamp(self, frame_number: int, framerate: float = 30.0) -> str:
        """
        Generate timestamp for a specific frame number
        
        Args:
            frame_number: Frame sequence number
            framerate: Video framerate
            
        Returns:
            Hex-encoded timestamp for this frame
        """
        # Calculate frame-specific offset
        frame_offset = frame_number / framerate
        return self.generate_timestamp_hex(frame_offset)
    
    def create_sei_metadata(self, uuid: str = "681d5c8f-80cd-4847-930a-99b9484b4a32") -> str:
        """
        Create SEI metadata string with dynamic timestamp
        
        Args:
            uuid: UUID for identifying our custom SEI data
            
        Returns:
            Complete SEI metadata string for FFmpeg
        """
        timestamp_hex = self.generate_timestamp_hex()
        
        # Format: UUID + timestamp (as per OpenVideoWalls implementation)
        sei_data = f"{uuid}+{timestamp_hex}"
        
        logger.debug(f"Created SEI metadata: {sei_data}")
        return sei_data