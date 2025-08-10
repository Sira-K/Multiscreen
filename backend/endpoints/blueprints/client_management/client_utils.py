# backend/endpoints/blueprints/client_management/client_utils.py
"""
Client Management Utility Functions
Helper functions for client operations
"""

import uuid
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

def get_group_from_docker(group_id: str) -> Optional[Dict[str, Any]]:
    """Get group information from Docker discovery"""
    try:
        # Import here to avoid circular imports
        from blueprints.docker_management import discover_groups
        
        discovery_result = discover_groups()
        if not discovery_result.get("success", False):
            logger.error(f"Failed to discover groups: {discovery_result.get('error')}")
            return None
        
        for group in discovery_result.get("groups", []):
            if group.get("id") == group_id:
                return group
        
        logger.warning(f"Group {group_id} not found in Docker containers")
        return None
        
    except Exception as e:
        logger.error(f"Error getting group from Docker: {e}")
        return None

def get_persistent_streams_for_group(group_id: str, group_name: str, split_count: int = 4) -> Dict[str, str]:
    """Generate dynamic stream IDs (not persistent anymore)"""
    logger.info(f"Generating dynamic stream IDs for group {group_name} (not persistent)")
    
    # Generate dynamic stream IDs based on group
    streams = {}
    base_id = group_id[:8] if len(group_id) >= 8 else group_id
    
    # Main/combined stream
    streams["test"] = base_id
    
    # Individual screen streams  
    for i in range(split_count):
        streams[f"test{i}"] = f"{base_id}_{i}"
    
    return streams

def check_group_streaming_status(group_id: str, group_name: str) -> bool:
    """Check if streaming is active for a group"""
    try:
        # Import here to avoid circular imports
        from blueprints.stream_management import find_running_ffmpeg_for_group_strict
        from blueprints.stream_management import discover_group_from_docker
        
        # Get group info
        group = discover_group_from_docker(group_id)
        if not group:
            logger.warning(f"Group {group_id} not found")
            return False
        
        container_id = group.get("container_id")
        processes = find_running_ffmpeg_for_group_strict(group_id, group_name, container_id)
        is_streaming = len(processes) > 0
        
        logger.debug(f"Group {group_name} streaming status: {is_streaming} ({len(processes)} processes)")
        return is_streaming
        
    except ImportError as e:
        logger.warning(f"Stream management functions not available: {e}")
        return False  # Conservative: assume not streaming if we can't check
    except Exception as e:
        logger.error(f"Error checking streaming status for group {group_name}: {e}")
        return False

def format_time_ago(seconds_ago: int) -> str:
    """Format time difference as human-readable string"""
    if seconds_ago < 60:
        return f"{seconds_ago} seconds ago"
    elif seconds_ago < 3600:
        minutes = seconds_ago // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    else:
        hours = seconds_ago // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"

def get_next_steps(client_data: Dict[str, Any]) -> List[str]:
    """Get next steps for client based on current state"""
    assignment_status = client_data.get("assignment_status", "waiting_for_assignment")
    
    if assignment_status == "waiting_for_assignment":
        return [
            "Wait for admin to assign you to a group",
            "Use /wait_for_assignment endpoint to poll for updates"
        ]
    elif assignment_status == "group_assigned":
        return [
            "Wait for admin to assign you to a specific stream or screen",
            "Use /wait_for_assignment endpoint to poll for updates"
        ]
    elif assignment_status == "stream_assigned":
        return [
            "Wait for streaming to start",
            "Use /wait_for_assignment endpoint to get stream URL when ready"
        ]
    elif assignment_status == "screen_assigned":
        return [
            "Wait for multi-video streaming to start",
            "Use /wait_for_assignment endpoint to get stream URL when ready"
        ]
    else:
        return ["Contact administrator for assistance"]

def build_stream_url(group: Dict[str, Any], stream_id: str, group_name: str, srt_ip: str = "127.0.0.1") -> str:
    """Build SRT stream URL for a client"""
    ports = group.get("ports", {})
    srt_port = ports.get("srt_port", 10080)
    stream_path = f"live/{group_name}/{stream_id}"
    return f"srt://{srt_ip}:{srt_port}?streamid=#!::r={stream_path},m=request,latency=5000000"

def validate_screen_assignment(screen_number: int, group: Dict[str, Any]) -> tuple:
    """Validate screen assignment parameters"""
    screen_count = group.get("screen_count", 4)
    
    if screen_number >= screen_count:
        return False, f"Screen number {screen_number} exceeds group screen count {screen_count}"
    
    return True, None

def check_screen_availability(client_id: str, group_id: str, screen_number: int, all_clients: Dict[str, Any]) -> tuple:
    """Check if a screen is available for assignment"""
    for other_client_id, other_client in all_clients.items():
        if (other_client_id != client_id and 
            other_client.get("group_id") == group_id and 
            other_client.get("screen_number") == screen_number):
            return False, {
                "client_id": other_client_id,
                "hostname": other_client.get("hostname", "unknown")
            }
    return True, None