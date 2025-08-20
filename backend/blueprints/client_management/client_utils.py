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
    
    logger.info(f" Building stream URL for stream_id: {stream_id}, group: {group_name}")
    logger.info(f" Group ports: {ports}")
    
    # Try to get active stream IDs first
    try:
        try:
            from blueprints.streaming.split_stream import get_active_stream_ids
        except ImportError:
            try:
                from blueprints.streaming.multi_stream import get_active_stream_ids
            except ImportError:
                # Fallback function if import fails
                def get_active_stream_ids(group_id: str):
                    """Get active stream IDs for a group"""
                    return {}
        active_stream_ids = get_active_stream_ids(group.get("id", "unknown"))
        if active_stream_ids:
            logger.info(f" Found active stream IDs: {active_stream_ids}")
            actual_stream_ids = active_stream_ids
        else:
            logger.info(f" No active stream IDs found, trying group metadata")
            actual_stream_ids = group.get("stream_ids", {})
    except Exception as e:
        logger.warning(f"Could not get active stream IDs: {e}")
        actual_stream_ids = group.get("stream_ids", {})
    
    logger.info(f" Available stream IDs: {actual_stream_ids}")
    
    # For screen assignments, map to the correct stream ID
    if stream_id.startswith("screen"):
        screen_num = stream_id.replace("screen", "")
        screen_key = f"test{screen_num}"
        
        if screen_key in actual_stream_ids:
            # Use the actual stream ID from active streaming or group metadata
            actual_stream_id = actual_stream_ids[screen_key]
            logger.info(f" Using actual stream ID for screen {screen_num}: {actual_stream_id}")
        else:
            # Fallback: try to generate stream IDs if not available
            try:
                try:
                    from blueprints.streaming.split_stream import generate_stream_ids
                except ImportError:
                    try:
                        from blueprints.streaming.multi_stream import generate_stream_ids
                    except ImportError:
                        # Fallback function if import fails
                        def generate_stream_ids(base_stream_id: str, group_name: str, screen_count: int):
                            """Generate stream IDs for a group"""
                            stream_ids = {}
                            
                            # Combined stream ID
                            stream_ids["test"] = f"{base_stream_id[:8]}"
                            
                            # Individual screen stream IDs
                            for i in range(screen_count):
                                stream_ids[f"test{i}"] = f"{base_stream_id[:8]}_{i}"
                            
                            return stream_ids
                screen_count = group.get("screen_count", 2)
                fallback_ids = generate_stream_ids(group.get("id", "unknown"), group_name, screen_count)
                if screen_key in fallback_ids:
                    actual_stream_id = fallback_ids[screen_key]
                    logger.info(f" Using generated stream ID for screen {screen_num}: {actual_stream_id}")
                else:
                    # Last resort: use a predictable fallback
                    actual_stream_id = f"screen{screen_num}_{group_name}"
                    logger.warning(f" Using fallback stream ID for screen {screen_num}: {actual_stream_id}")
            except Exception as e:
                logger.error(f"Error generating fallback stream IDs: {e}")
                actual_stream_id = f"screen{screen_num}_{group_name}"
                logger.warning(f" Using emergency fallback stream ID: {actual_stream_id}")
    else:
        # For direct stream assignments, use the stream_id as is
        actual_stream_id = stream_id
    
    stream_path = f"live/{group_name}/{actual_stream_id}"
    stream_url = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={stream_path},m=request,latency=5000000"
    
    logger.info(f" Built stream URL: {stream_url}")
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
            logger.info(f" Using pre-generated stream IDs from group creation: {stream_ids}")
            return stream_ids
        else:
            logger.warning(f"No pre-generated stream IDs found for group {group_name}")
            logger.warning(f"Group may have been created with older version")
            
            # Fallback: generate them now (for backwards compatibility)
            try:
                from blueprints.streaming.split_stream import generate_stream_ids
            except ImportError:
                try:
                    from blueprints.streaming.multi_stream import generate_stream_ids
                except ImportError:
                    # Fallback function if import fails
                    def generate_stream_ids(base_stream_id: str, group_name: str, screen_count: int):
                        """Generate stream IDs for a group"""
                        stream_ids = {}
                        
                        # Combined stream ID
                        stream_ids["test"] = f"{base_stream_id[:8]}"
                        
                        # Individual screen stream IDs
                        for i in range(screen_count):
                            stream_ids[f"test{i}"] = f"{base_stream_id[:8]}_{i}"
                        
                        return stream_ids
            screen_count = group.get("screen_count", 2)
            fallback_ids = generate_stream_ids(group_id, group_name, screen_count)
            logger.info(f"Generated fallback stream IDs: {fallback_ids}")
            return fallback_ids
        
    except Exception as e:
        logger.error(f"Error getting stream IDs: {e}")
        return {}

# Client Utility Functions
# Helper functions for client management operations

import logging
from typing import Dict, Any, Optional, Tuple, List

logger = logging.getLogger(__name__)

def extract_hostname_from_client_id(client_id: str) -> str:
    """
    Extract hostname from client ID
    Client ID format: hostname_ipaddress
    """
    if '_' in client_id:
        return client_id.split('_')[0]
    return client_id

def extract_ip_from_client_id(client_id: str) -> str:
    """
    Extract IP address from client ID
    Client ID format: hostname_ipaddress
    """
    if '_' in client_id:
        parts = client_id.split('_')
        if len(parts) >= 2:
            # Reconstruct IP address (may have multiple underscores)
            return '_'.join(parts[1:])
    return "unknown"

def get_clients_by_hostname(state, hostname: str) -> List[Dict[str, Any]]:
    """
    Get all clients with the same hostname (different IP addresses)
    Useful for managing multiple terminal instances from the same device
    """
    clients = []
    if hasattr(state, 'clients') and state.clients:
        for client_id, client_data in state.clients.items():
            if extract_hostname_from_client_id(client_id) == hostname:
                clients.append({
                    "client_id": client_id,
                    "hostname": extract_hostname_from_client_id(client_id),
                    "ip_address": extract_ip_from_client_id(client_id),
                    **client_data
                })
    return clients

def format_client_display_name(client_id: str, client_data: Dict[str, Any]) -> str:
    """
    Format a user-friendly display name for the client
    Shows hostname and IP address clearly
    """
    hostname = extract_hostname_from_client_id(client_id)
    ip_address = extract_ip_from_client_id(client_id)
    
    if ip_address != "unknown":
        return f"{hostname} ({ip_address})"
    return hostname