# backend/endpoints/blueprints/client_management/client_utils.py

import time
from typing import Dict, Any, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

def format_time_ago(timestamp: float) -> str:
    """Format timestamp as human-readable time ago"""
    if not timestamp:
        return "Never"
    
    seconds_ago = time.time() - timestamp
    
    if seconds_ago < 60:
        return f"{int(seconds_ago)} seconds ago"
    elif seconds_ago < 3600:
        return f"{int(seconds_ago / 60)} minutes ago"
    elif seconds_ago < 86400:
        return f"{int(seconds_ago / 3600)} hours ago"
    else:
        return f"{int(seconds_ago / 86400)} days ago"

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

def build_stream_url(group: Dict[str, Any], stream_id: str, group_name: str, srt_ip: str) -> str:
    """Build SRT stream URL for a client"""
    ports = group.get("ports", {})
    srt_port = ports.get("srt_port", 10100)  # Default to 10100 from your logs
    
    # For screen assignments, map to the correct stream
    if stream_id.startswith("screen"):
        screen_num = stream_id.replace("screen", "")
        if screen_num == "0":
            stream_id = "e61d16f4_0"  # From your FFmpeg output
        elif screen_num == "1":
            stream_id = "e61d16f4_1"  # From your FFmpeg output
        else:
            stream_id = "7164fd0a"  # Main stream
    
    stream_path = f"live/{group_name}/{stream_id}"
    stream_url = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={stream_path},m=request,latency=5000000"
    
    logger.info(f"Built stream URL: {stream_url}")
    return stream_url

def check_screen_availability(
    requesting_client_id: str,
    group_id: str,
    screen_number: int,
    all_clients: Dict[str, Dict[str, Any]]
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Check if a screen number is available for assignment
    Returns (is_available, conflicting_client_info)
    """
    for client_id, client in all_clients.items():
        # Skip the requesting client
        if client_id == requesting_client_id:
            continue
            
        # Check if another client has this screen in the same group
        if (client.get("group_id") == group_id and 
            client.get("screen_number") == screen_number):
            
            conflict_info = {
                "client_id": client_id,
                "hostname": client.get("hostname", "unknown"),
                "display_name": client.get("display_name", "unknown"),
                "assigned_at": client.get("assigned_at")
            }
            return False, conflict_info
    
    return True, None

def validate_assignment(data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Validate client assignment request data
    Returns (is_valid, error_message, cleaned_data)
    """
    cleaned = {}
    
    # Validate client_id
    client_id = data.get("client_id", "").strip()
    if not client_id:
        return False, "client_id is required", {}
    cleaned["client_id"] = client_id
    
    # Validate group_id
    group_id = data.get("group_id", "").strip()
    if not group_id:
        return False, "group_id is required", {}
    cleaned["group_id"] = group_id
    
    # Optional fields
    cleaned["stream_name"] = data.get("stream_name", "").strip() or None
    cleaned["screen_number"] = data.get("screen_number")
    cleaned["srt_ip"] = data.get("srt_ip", "127.0.0.1").strip()
    
    # Validate screen_number if provided
    if cleaned["screen_number"] is not None:
        try:
            screen_num = int(cleaned["screen_number"])
            if screen_num < 0:
                return False, "screen_number must be non-negative", {}
            cleaned["screen_number"] = screen_num
        except (ValueError, TypeError):
            return False, "screen_number must be a valid integer", {}
    
    return True, "", cleaned

def validate_unassignment(data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Validate client unassignment request data
    Returns (is_valid, error_message, cleaned_data)
    """
    cleaned = {}
    
    # Validate client_id
    client_id = data.get("client_id", "").strip()
    if not client_id:
        return False, "client_id is required", {}
    cleaned["client_id"] = client_id
    
    # Validate unassign_type
    unassign_type = data.get("unassign_type", "all").strip().lower()
    if unassign_type not in ["all", "stream", "screen"]:
        return False, "unassign_type must be 'all', 'stream', or 'screen'", {}
    cleaned["unassign_type"] = unassign_type
    
    return True, "", cleaned

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
    """Get pre-generated stream IDs from group metadata (always available)"""
    try:
        logger.info(f"Getting stream IDs for group {group_name}")
        
        # Get group info with pre-generated stream IDs
        group = get_group_from_docker(group_id)
        if not group:
            logger.error(f"Group {group_id} not found")
            return {}
        
        # Get pre-generated stream IDs from group metadata
        stream_ids = group.get("stream_ids", {})
        
        if stream_ids:
            logger.info(f"✅ Using pre-generated stream IDs from group creation: {stream_ids}")
            return stream_ids
        else:
            logger.warning(f"No pre-generated stream IDs found for group {group_name}")
            logger.warning(f"Group may have been created with older version")
            
            # Fallback: generate them now (for backwards compatibility)
            from blueprints.stream_management import generate_stream_ids
            screen_count = group.get("screen_count", 2)
            fallback_ids = generate_stream_ids(group_id, group_name, screen_count)
            logger.info(f"Generated fallback stream IDs: {fallback_ids}")
            return fallback_ids
        
    except Exception as e:
        logger.error(f"Error getting stream IDs: {e}")
        return {}