"""
Client Validation Functions
Validation logic for client registration and operations
"""

import logging
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

def validate_client_registration(data):
    """Validate client registration data - SIMPLIFIED"""
    if not data:
        return False, "No data provided", None
    
    # Required fields
    hostname = data.get("hostname", "").strip()
    if not hostname:
        return False, "hostname is required", None
    
    # Optional fields
    ip_address = data.get("ip_address", "").strip() or None
    display_name = data.get("display_name", "").strip() or hostname
    platform = data.get("platform", "").strip() or "unknown"
    
    
    cleaned_data = {
        "hostname": hostname,
        "ip_address": ip_address,
        "display_name": display_name,
        "platform": platform

    }
    
    return True, None, cleaned_data
    

def validate_group_assignment(data: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Validate group assignment data
    
    Args:
        data: Assignment data from request
        
    Returns:
        Tuple of (is_valid, error_message, cleaned_data)
    """
    if not data:
        return False, "No data provided", None
    
    client_id = data.get("client_id")
    if not client_id:
        return False, "client_id is required", None
    
    group_id = data.get("group_id")
    # group_id can be None (for unassignment)
    
    cleaned_data = {
        "client_id": client_id.strip() if isinstance(client_id, str) else client_id,
        "group_id": group_id.strip() if isinstance(group_id, str) and group_id else group_id
    }
    
    return True, None, cleaned_data

def validate_stream_assignment(data: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Validate stream assignment data
    
    Args:
        data: Assignment data from request
        
    Returns:
        Tuple of (is_valid, error_message, cleaned_data)
    """
    if not data:
        return False, "No data provided", None
    
    client_id = data.get("client_id")
    if not client_id:
        return False, "client_id is required", None
    
    # Validate SRT IP if provided
    srt_ip = data.get("srt_ip", "127.0.0.1")
    if srt_ip and not _is_valid_ip(srt_ip):
        return False, "invalid srt_ip format", None
    
    cleaned_data = {
        "client_id": client_id.strip() if isinstance(client_id, str) else client_id,
        "group_id": data.get("group_id"),
        "stream_name": data.get("stream_name"),
        "srt_ip": srt_ip
    }
    
    return True, None, cleaned_data

def validate_screen_assignment(data: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Validate screen assignment data
    
    Args:
        data: Assignment data from request
        
    Returns:
        Tuple of (is_valid, error_message, cleaned_data)
    """
    if not data:
        return False, "No data provided", None
    
    client_id = data.get("client_id")
    group_id = data.get("group_id")
    screen_number = data.get("screen_number")
    
    if not all([client_id, group_id, screen_number is not None]):
        return False, "client_id, group_id, and screen_number are required", None
    
    # Validate screen number
    try:
        screen_number = int(screen_number)
        if screen_number < 0:
            return False, "screen_number must be non-negative", None
    except (ValueError, TypeError):
        return False, "screen_number must be a valid integer", None
    
    # Validate SRT IP if provided
    srt_ip = data.get("srt_ip", "127.0.0.1")
    if srt_ip and not _is_valid_ip(srt_ip):
        return False, "invalid srt_ip format", None
    
    cleaned_data = {
        "client_id": client_id.strip() if isinstance(client_id, str) else client_id,
        "group_id": group_id.strip() if isinstance(group_id, str) else group_id,
        "screen_number": screen_number,
        "srt_ip": srt_ip
    }
    
    return True, None, cleaned_data

def validate_auto_assignment(data: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Validate auto assignment data
    
    Args:
        data: Assignment data from request
        
    Returns:
        Tuple of (is_valid, error_message, cleaned_data)
    """
    if not data:
        return False, "No data provided", None
    
    group_id = data.get("group_id")
    if not group_id:
        return False, "group_id is required", None
    
    assignment_type = data.get("assignment_type", "streams")
    if assignment_type not in ["streams", "screens"]:
        return False, "assignment_type must be 'streams' or 'screens'", None
    
    # Validate SRT IP if provided
    srt_ip = data.get("srt_ip", "127.0.0.1")
    if srt_ip and not _is_valid_ip(srt_ip):
        return False, "invalid srt_ip format", None
    
    cleaned_data = {
        "group_id": group_id.strip() if isinstance(group_id, str) else group_id,
        "assignment_type": assignment_type,
        "srt_ip": srt_ip
    }
    
    return True, None, cleaned_data

def validate_unassignment(data: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Validate unassignment data
    
    Args:
        data: Unassignment data from request
        
    Returns:
        Tuple of (is_valid, error_message, cleaned_data)
    """
    if not data:
        return False, "No data provided", None
    
    client_id = data.get("client_id")
    if not client_id:
        return False, "client_id is required", None
    
    unassign_type = data.get("unassign_type", "all")
    if unassign_type not in ["all", "stream", "screen"]:
        return False, "unassign_type must be 'all', 'stream', or 'screen'", None
    
    cleaned_data = {
        "client_id": client_id.strip() if isinstance(client_id, str) else client_id,
        "unassign_type": unassign_type
    }
    
    return True, None, cleaned_data

def _is_valid_ip(ip: str) -> bool:
    """Validate IP address format"""
    try:
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        
        for part in parts:
            num = int(part)
            if not 0 <= num <= 255:
                return False
        
        return True
    except (ValueError, AttributeError):
        return False