# blueprints/group_management.py
from flask import Blueprint, request, jsonify, current_app
import traceback
import time
import threading
import logging
import os
import uuid
from typing import Dict, List, Any, Optional, Tuple

# Create blueprint
group_bp = Blueprint('group_management', __name__)

# Configure logging
logger = logging.getLogger(__name__)

def get_state():
    """Get application state from current app context"""
    return current_app.config['APP_STATE']

def validate_group_data(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate group creation/update data
    
    Args:
        data: The group data to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not data:
        return False, "No JSON data provided"
        
    if not data.get("name"):
        return False, "Missing group name"
        
    if not data.get("name").strip():
        return False, "Group name cannot be empty"
        
    return True, None

@group_bp.route("/create_group", methods=["POST"])
def create_group():
    """Create a new group for managing screens and clients"""
    try:
        logger.info("==== CREATE GROUP REQUEST RECEIVED ====")
        
        # Get app state
        state = get_state()
        
        # Initialize groups if needed
        if not hasattr(state, 'groups_lock'):
            state.groups_lock = threading.RLock()
        
        if not hasattr(state, 'groups'):
            state.groups = {}
        
        # Parse and validate request data
        data = request.get_json()
        is_valid, error_message = validate_group_data(data)
        
        if not is_valid:
            return jsonify({"error": error_message}), 400
            
        group_name = data.get("name").strip()
        description = data.get("description", "").strip()
        screen_count = int(data.get("screen_count", 2))
        orientation = data.get("orientation", "horizontal")
        
        # Generate unique group ID
        group_id = str(uuid.uuid4())
        
        # Calculate port range for this group (each group gets 10 ports)
        base_port = 10000 + (len(state.groups) * 10)
        srt_port = base_port + 80  # SRT port (10080, 10090, 10100, etc.)
        
        with state.groups_lock:
            # Check if group name already exists
            for existing_group in state.groups.values():
                if existing_group.get("name", "").lower() == group_name.lower():
                    return jsonify({"error": f"Group name '{group_name}' already exists"}), 400
            
            # Create new group
            state.groups[group_id] = {
                "id": group_id,
                "name": group_name,
                "description": description,
                "screen_count": screen_count,
                "orientation": orientation,
                "created_at": time.time(),
                "status": "inactive",  # inactive, starting, active, stopping
                "clients": {},  # Client IDs belonging to this group
                "docker_container_id": None,
                "ffmpeg_process_id": None,
                "current_video": None,
                "available_streams": [],
                # Network configuration
                "srt_port": srt_port,
                "base_port": base_port,
                "screen_ips": {},
                # Statistics
                "total_clients": 0,
                "active_clients": 0,
                "last_activity": time.time()
            }
            
            logger.info(f"Created group: {group_name} (ID: {group_id})")
            logger.info(f"Group assigned ports: SRT={srt_port}, Base={base_port}")
            
        return jsonify({
            "message": f"Group '{group_name}' created successfully",
            "group": state.groups[group_id]
        }), 200
        
    except Exception as e:
        logger.error(f"Error creating group: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@group_bp.route("/get_groups", methods=["GET"])
def get_groups():
    """Get a list of all groups with their status and statistics"""
    logger.info("==== GET_GROUPS REQUEST RECEIVED ====")
    state = get_state()

    try:
        if not hasattr(state, 'groups'):
            state.groups = {}
            
        with state.groups_lock if hasattr(state, 'groups_lock') else threading.RLock():
            current_time = time.time()
            groups_list = []
            
            for group_id, group_data in state.groups.items():
                # Create a copy for modification
                group = dict(group_data)
                
                # Update client statistics
                active_clients = 0
                total_clients = len(group.get("clients", {}))
                
                for client_data in group.get("clients", {}).values():
                    if current_time - client_data.get("last_seen", 0) <= 60:  # 1 minute threshold
                        active_clients += 1
                
                group["active_clients"] = active_clients
                group["total_clients"] = total_clients
                
                # Update available streams based on active clients
                if active_clients > 1:
                    streams = [f"live/{group_id}/test"]  # Full stream
                    for i in range(min(active_clients, group.get("screen_count", 2))):
                        streams.append(f"live/{group_id}/test{i}")
                    group["available_streams"] = streams
                else:
                    group["available_streams"] = [f"live/{group_id}/test"]
                
                # Format creation time
                group["created_at_formatted"] = time.strftime(
                    "%Y-%m-%d %H:%M:%S", 
                    time.localtime(group.get("created_at", current_time))
                )
                
                groups_list.append(group)
            
            logger.info(f"Returning {len(groups_list)} groups")
            
            return jsonify({
                "groups": groups_list,
                "total": len(state.groups)
            }), 200
            
    except Exception as e:
        logger.error(f"Error getting groups: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@group_bp.route("/update_group/<group_id>", methods=["PUT"])
def update_group(group_id: str):
    """Update group settings"""
    try:
        state = get_state()
        
        if not hasattr(state, 'groups') or group_id not in state.groups:
            return jsonify({"error": "Group not found"}), 404
            
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        with state.groups_lock:
            group = state.groups[group_id]
            
            # Update allowed fields
            if "name" in data and data["name"].strip():
                # Check for name conflicts
                new_name = data["name"].strip()
                for gid, existing_group in state.groups.items():
                    if gid != group_id and existing_group.get("name", "").lower() == new_name.lower():
                        return jsonify({"error": f"Group name '{new_name}' already exists"}), 400
                group["name"] = new_name
                
            if "description" in data:
                group["description"] = data["description"].strip()
                
            if "screen_count" in data:
                group["screen_count"] = int(data["screen_count"])
                
            if "orientation" in data:
                group["orientation"] = data["orientation"]
                
            if "screen_ips" in data:
                group["screen_ips"] = data["screen_ips"]
            
            group["last_activity"] = time.time()
        
        return jsonify({
            "message": f"Group updated successfully",
            "group": state.groups[group_id]
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating group: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@group_bp.route("/delete_group/<group_id>", methods=["DELETE"])
def delete_group(group_id: str):
    """Delete a group (only if inactive)"""
    try:
        state = get_state()
        
        if not hasattr(state, 'groups') or group_id not in state.groups:
            return jsonify({"error": "Group not found"}), 404
            
        with state.groups_lock:
            group = state.groups[group_id]
            
            # Check if group is active
            if group.get("status") == "active":
                return jsonify({"error": "Cannot delete active group. Stop it first."}), 400
            
            # Move clients back to default group or unassign them
            if group.get("clients"):
                # For now, just remove group assignment from clients
                if hasattr(state, 'clients'):
                    for client_id in group["clients"].keys():
                        if client_id in state.clients:
                            state.clients[client_id]["group_id"] = None
            
            group_name = group.get("name", group_id)
            del state.groups[group_id]
            
        return jsonify({
            "message": f"Group '{group_name}' deleted successfully"
        }), 200
        
    except Exception as e:
        logger.error(f"Error deleting group: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@group_bp.route("/assign_client_to_group", methods=["POST"])
def assign_client_to_group():
    """Assign a client to a specific group"""
    try:
        state = get_state()
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        client_id = data.get("client_id")
        group_id = data.get("group_id")
        
        if not client_id:
            return jsonify({"error": "Missing client_id"}), 400
            
        # Initialize groups and clients if needed
        if not hasattr(state, 'groups'):
            state.groups = {}
        if not hasattr(state, 'clients'):
            state.clients = {}
            
        # Validate group exists (if group_id is provided)
        if group_id and group_id not in state.groups:
            return jsonify({"error": "Group not found"}), 404
            
        # Validate client exists
        if client_id not in state.clients:
            return jsonify({"error": "Client not found"}), 404
        
        with state.clients_lock if hasattr(state, 'clients_lock') else threading.RLock():
            with state.groups_lock if hasattr(state, 'groups_lock') else threading.RLock():
                client = state.clients[client_id]
                old_group_id = client.get("group_id")
                
                # Remove from old group
                if old_group_id and old_group_id in state.groups:
                    if client_id in state.groups[old_group_id].get("clients", {}):
                        del state.groups[old_group_id]["clients"][client_id]
                
                # Add to new group
                if group_id:
                    if "clients" not in state.groups[group_id]:
                        state.groups[group_id]["clients"] = {}
                    state.groups[group_id]["clients"][client_id] = {
                        "assigned_at": time.time(),
                        "stream_id": None
                    }
                    client["group_id"] = group_id
                    
                    # Auto-assign a stream within the group
                    group = state.groups[group_id]
                    if group.get("available_streams"):
                        # Assign the first available stream
                        client["stream_id"] = group["available_streams"][0]
                else:
                    client["group_id"] = None
                    client["stream_id"] = None
        
        message = f"Client {client_id} assigned to group {group_id}" if group_id else f"Client {client_id} removed from all groups"
        
        return jsonify({
            "message": message,
            "client": state.clients[client_id]
        }), 200
        
    except Exception as e:
        logger.error(f"Error assigning client to group: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@group_bp.route("/group_clients/<group_id>", methods=["GET"])
def get_group_clients(group_id: str):
    """Get all clients belonging to a specific group"""
    try:
        state = get_state()
        
        if not hasattr(state, 'groups') or group_id not in state.groups:
            return jsonify({"error": "Group not found"}), 404
            
        if not hasattr(state, 'clients'):
            state.clients = {}
            
        current_time = time.time()
        group_clients = []
        
        with state.clients_lock if hasattr(state, 'clients_lock') else threading.RLock():
            for client_id, client_data in state.clients.items():
                if client_data.get("group_id") == group_id:
                    # Create a copy for modification
                    client = dict(client_data)
                    
                    # Update status
                    if current_time - client_data.get("last_seen", 0) <= 60:
                        client["status"] = "active"
                    else:
                        client["status"] = "inactive"
                    
                    # Add formatted last seen
                    seconds_ago = int(current_time - client_data.get("last_seen", 0))
                    client["last_seen_formatted"] = format_time_ago(seconds_ago)
                    
                    group_clients.append(client)
        
        return jsonify({
            "group_id": group_id,
            "clients": group_clients,
            "total": len(group_clients),
            "active": len([c for c in group_clients if c["status"] == "active"])
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting group clients: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

def format_time_ago(seconds_ago: int) -> str:
    """Format a time difference in seconds into a human-readable string"""
    if seconds_ago < 60:
        return f"{seconds_ago} seconds ago"
    elif seconds_ago < 3600:
        minutes = seconds_ago // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    else:
        hours = seconds_ago // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"

# Helper function to get group-specific available streams
def get_group_available_streams(group_id: str) -> Dict[str, Any]:
    """
    Get available streams for a specific group
    """
    state = get_state()
    
    if not hasattr(state, 'groups') or group_id not in state.groups:
        return {
            "available_streams": [],
            "active_clients": 0,
            "max_screens": 1
        }
    
    group = state.groups[group_id]
    screen_count = group.get("screen_count", 2)
    
    # Count active clients in this group
    current_time = time.time()
    active_clients = 0
    
    if hasattr(state, 'clients'):
        for client_data in state.clients.values():
            if (client_data.get("group_id") == group_id and 
                current_time - client_data.get("last_seen", 0) <= 60):
                active_clients += 1
    
    # Build available streams for this group
    available_streams = [f"live/{group_id}/test"]  # Full stream
    
    if active_clients >= 2:
        for i in range(min(active_clients, screen_count)):
            available_streams.append(f"live/{group_id}/test{i}")
    
    return {
        "available_streams": available_streams,
        "active_clients": active_clients,
        "max_screens": screen_count,
        "group_name": group.get("name", group_id)
    }