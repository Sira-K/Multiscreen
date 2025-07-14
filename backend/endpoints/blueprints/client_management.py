# blueprints/client_management.py - Updated for Hybrid Architecture
"""
Client management with hybrid architecture:
- Clients stored in app state (real-time connections)
- Groups discovered from Docker containers
"""

from flask import Blueprint, request, jsonify, current_app
import time
import threading
import logging
import traceback
from typing import Dict, List, Any, Optional

# Create blueprint
client_bp = Blueprint('client_management', __name__)

# Configure logging
logger = logging.getLogger(__name__)

def get_state():
    """Get application state from current app context"""
    return current_app.config['APP_STATE']

def get_group_from_docker(group_id: str) -> Optional[Dict[str, Any]]:
    """
    Get group information from Docker discovery
    
    Args:
        group_id: The group ID to find
        
    Returns:
        Group data dict or None if not found
    """
    try:
        from blueprints.docker_management import discover_groups
        
        discovery_result = discover_groups()
        if not discovery_result.get("success", False):
            logger.error(f"Failed to discover groups: {discovery_result.get('error')}")
            return None
        
        # Find the specific group
        for group in discovery_result.get("groups", []):
            if group.get("id") == group_id:
                return group
        
        logger.warning(f"Group {group_id} not found in Docker containers")
        return None
        
    except Exception as e:
        logger.error(f"Error getting group from Docker: {e}")
        return None

def get_available_streams_for_group(group_id: str) -> Dict[str, Any]:
    """
    Get available streams for a specific group from Docker discovery
    
    Args:
        group_id: Group ID to get streams for
        
    Returns:
        Dict with available streams info
    """
    try:
        # Get group info from Docker
        group = get_group_from_docker(group_id)
        
        if not group:
            return {
                "available_streams": [],
                "active_clients": 0,
                "max_screens": 1,
                "group_name": "Unknown"
            }
        
        screen_count = group.get("screen_count", 2)
        group_name = group.get("name", group_id)
        
        # Get app state for client counting
        state = get_state()
        
        # Count active clients in this group
        active_clients = state.get_active_clients_count(group_id)
        
        # Always include the full stream for this group
        available_streams = [f"live/{group_name}/test"]
        
        # Add split streams based on client count and screen_count
        if active_clients >= 2:
            # If we have at least 2 active clients, make split streams available
            # But limit to our configured screen_count
            for i in range(min(active_clients, screen_count)):
                available_streams.append(f"live/{group_name}/test{i}")
        
        return {
            "available_streams": available_streams,
            "active_clients": active_clients,
            "max_screens": screen_count,
            "group_name": group_name,
            "full_stream": f"live/{group_name}/test"
        }
        
    except Exception as e:
        logger.error(f"Error getting streams for group {group_id}: {e}")
        return {
            "available_streams": [],
            "active_clients": 0,
            "max_screens": 1,
            "group_name": "Error"
        }

@client_bp.route("/register_client", methods=["POST"])
def register_client():
    """Register a client device with the server"""
    try:
        logger.info("==== REGISTER CLIENT REQUEST RECEIVED ====")
        
        # Get app state
        state = get_state()
        
        # Initialize state objects if needed
        if not hasattr(state, 'clients_lock'):
            state.clients_lock = threading.RLock()
        
        if not hasattr(state, 'clients'):
            state.clients = {}
        
        # Parse and validate request data
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        hostname = data.get("hostname")
        ip_address = data.get("ip_address")
        display_name = data.get("display_name")
        
        if not hostname:
            return jsonify({"error": "Missing hostname"}), 400
            
        if not ip_address:
            return jsonify({"error": "Missing ip_address"}), 400
        
        # Use hostname as client_id for consistency
        client_id = hostname
        current_time = time.time()
        
        logger.info(f"Registering client: {client_id} ({ip_address})")
        
        with state.clients_lock:
            # Check if client already exists
            existing_client = state.clients.get(client_id)
            
            if existing_client:
                # Update existing client
                existing_client.update({
                    "ip_address": ip_address,
                    "display_name": display_name or existing_client.get("display_name", hostname),
                    "last_seen": current_time,
                    "status": "active"
                })
                
                logger.info(f"Updated existing client: {client_id}")
                action = "updated"
            else:
                # Create new client
                state.clients[client_id] = {
                    "hostname": hostname,
                    "ip_address": ip_address,
                    "display_name": display_name or hostname,
                    "registered_at": current_time,
                    "last_seen": current_time,
                    "status": "active",
                    "group_id": None,  # Not assigned to any group initially
                    "stream_assignment": None
                }
                
                logger.info(f"Registered new client: {client_id}")
                action = "registered"
        
        return jsonify({
            "message": f"Client {action} successfully",
            "client_id": client_id,
            "client_info": state.clients[client_id]
        }), 200
        
    except Exception as e:
        logger.error(f"Error registering client: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@client_bp.route("/assign_client_to_group", methods=["POST"])
def assign_client_to_group():
    """Assign a client to a specific group"""
    try:
        logger.info("==== ASSIGN CLIENT TO GROUP REQUEST RECEIVED ====")
        
        state = get_state()
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        client_id = data.get("client_id")
        group_id = data.get("group_id")
        
        logger.info(f"Assigning client {client_id} to group {group_id}")
        
        if not client_id:
            return jsonify({"error": "Missing client_id"}), 400
        
        # Initialize clients if needed
        if not hasattr(state, 'clients'):
            state.clients = {}
            
        # Validate client exists
        if client_id not in state.clients:
            return jsonify({"error": "Client not found"}), 404
        
        # Validate group exists (if group_id is provided) - check Docker
        if group_id:
            group = get_group_from_docker(group_id)
            if not group:
                return jsonify({"error": f"Group '{group_id}' not found in Docker containers"}), 404
        
        with state.clients_lock:
            client = state.clients[client_id]
            old_group_id = client.get("group_id")
            
            # Update client's group assignment
            if group_id:
                client["group_id"] = group_id
                client["assigned_at"] = time.time()
                client["stream_assignment"] = None  # Reset stream assignment
                logger.info(f"Assigned client {client_id} to group {group_id}")
            else:
                # Unassign from group
                client["group_id"] = None
                client["assigned_at"] = None
                client["stream_assignment"] = None
                logger.info(f"Unassigned client {client_id} from group")
        
        return jsonify({
            "message": f"Client assigned successfully",
            "client_id": client_id,
            "old_group_id": old_group_id,
            "new_group_id": group_id,
            "client_info": state.clients[client_id]
        }), 200
        
    except Exception as e:
        logger.error(f"Error assigning client to group: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@client_bp.route("/get_clients", methods=["GET"])
def get_clients():
    """Get all registered clients with their group assignments"""
    try:
        logger.info("==== GET CLIENTS REQUEST RECEIVED ====")
        
        # Get app state
        state = get_state()
        
        # Initialize clients if needed
        if not hasattr(state, 'clients'):
            state.clients = {}
        
        # Get groups from Docker for additional info
        groups_info = {}
        try:
            from blueprints.docker_management import discover_groups
            discovery_result = discover_groups()
            if discovery_result.get("success", False):
                for group in discovery_result.get("groups", []):
                    groups_info[group.get("id")] = {
                        "name": group.get("name"),
                        "docker_running": group.get("docker_running", False)
                    }
        except Exception as e:
            logger.warning(f"Could not get group info: {e}")
        
        current_time = time.time()
        clients_list = []
        
        with state.clients_lock:
            for client_id, client_data in state.clients.items():
                # Calculate time since last seen
                last_seen = client_data.get("last_seen", 0)
                seconds_ago = int(current_time - last_seen)
                is_active = seconds_ago <= 60  # Active if seen within 60 seconds
                
                # Get group info
                group_id = client_data.get("group_id")
                group_info = None
                if group_id and group_id in groups_info:
                    group_info = groups_info[group_id]
                
                client_info = {
                    "client_id": client_id,
                    "hostname": client_data.get("hostname", client_id),
                    "ip_address": client_data.get("ip_address", "unknown"),
                    "display_name": client_data.get("display_name", client_id),
                    "registered_at": client_data.get("registered_at", 0),
                    "last_seen": last_seen,
                    "seconds_ago": seconds_ago,
                    "is_active": is_active,
                    "status": "active" if is_active else "inactive",
                    "group_id": group_id,
                    "group_name": group_info.get("name") if group_info else None,
                    "group_docker_running": group_info.get("docker_running") if group_info else None,
                    "stream_assignment": client_data.get("stream_assignment")
                }
                
                clients_list.append(client_info)
        
        # Sort by last seen (most recent first)
        clients_list.sort(key=lambda x: x["last_seen"], reverse=True)
        
        # Count active clients
        active_clients = len([c for c in clients_list if c["is_active"]])
        
        logger.info(f"Returning {len(clients_list)} clients ({active_clients} active)")
        
        return jsonify({
            "clients": clients_list,
            "total_clients": len(clients_list),
            "active_clients": active_clients,
            "groups_available": len(groups_info),
            "timestamp": current_time
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting clients: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@client_bp.route("/client_status", methods=["POST"])
def client_status():
    """Check what stream a client should be displaying"""
    try:
        # Get app state
        state = get_state()
        
        # Parse request data
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        client_id = data.get("client_id") or data.get("hostname")
        
        if not client_id:
            return jsonify({"error": "Missing client_id or hostname"}), 400
        
        # Initialize clients if needed
        if not hasattr(state, 'clients'):
            state.clients = {}
        
        # Update client last seen time
        current_time = time.time()
        
        with state.clients_lock:
            if client_id in state.clients:
                state.clients[client_id]["last_seen"] = current_time
                state.clients[client_id]["status"] = "active"
                client = state.clients[client_id]
            else:
                # Auto-register client if not found
                ip_address = request.remote_addr
                state.clients[client_id] = {
                    "hostname": client_id,
                    "ip_address": ip_address,
                    "display_name": client_id,
                    "registered_at": current_time,
                    "last_seen": current_time,
                    "status": "active",
                    "group_id": None,
                    "stream_assignment": None
                }
                client = state.clients[client_id]
                logger.info(f"Auto-registered client: {client_id}")
        
        # Get client's group assignment
        group_id = client.get("group_id")
        
        if not group_id:
            return jsonify({
                "client_id": client_id,
                "assigned": False,
                "message": "Client not assigned to any group",
                "group_id": None,
                "stream_url": None
            }), 200
        
        # Verify group exists in Docker
        group = get_group_from_docker(group_id)
        if not group:
            return jsonify({
                "client_id": client_id,
                "assigned": True,
                "group_id": group_id,
                "error": "Assigned group not found in Docker containers",
                "stream_url": None
            }), 404
        
        # Check if group's Docker container is running
        if not group.get("docker_running", False):
            return jsonify({
                "client_id": client_id,
                "assigned": True,
                "group_id": group_id,
                "group_name": group.get("name"),
                "error": "Group's Docker container is not running",
                "docker_status": group.get("docker_status", "unknown"),
                "stream_url": None
            }), 503
        
        # Get available streams for this group
        streams_info = get_available_streams_for_group(group_id)
        
        # For now, assign the full stream (could be enhanced with automatic assignment logic)
        stream_url = None
        if streams_info.get("available_streams"):
            # Use the full stream by default
            full_stream = streams_info.get("full_stream")
            if full_stream:
                ports = group.get("ports", {})
                srt_port = ports.get("srt_port", 10080)
                stream_url = f"srt://127.0.0.1:{srt_port}?streamid=#!::r={full_stream},m=request"
        
        return jsonify({
            "client_id": client_id,
            "assigned": True,
            "group_id": group_id,
            "group_name": group.get("name"),
            "docker_status": group.get("docker_status"),
            "docker_running": group.get("docker_running"),
            "stream_url": stream_url,
            "available_streams": streams_info.get("available_streams", []),
            "active_clients_in_group": streams_info.get("active_clients", 0)
        }), 200
        
    except Exception as e:
        logger.error(f"Error checking client status: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@client_bp.route("/remove_client", methods=["POST"])
def remove_client():
    """Remove a client from the system"""
    try:
        logger.info("==== REMOVE CLIENT REQUEST RECEIVED ====")
        
        # Get app state
        state = get_state()
        
        # Initialize state objects if needed
        if not hasattr(state, 'clients_lock'):
            state.clients_lock = threading.RLock()
        
        if not hasattr(state, 'clients'):
            state.clients = {}
        
        # Parse and validate request data
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        client_id = data.get("client_id")
        
        if not client_id:
            return jsonify({"error": "Missing client_id parameter"}), 400
        
        logger.info(f"Removing client: {client_id}")
        
        with state.clients_lock:
            if client_id not in state.clients:
                return jsonify({"error": f"Client '{client_id}' not found"}), 404
            
            client = state.clients[client_id]
            client_name = client.get('display_name') or client.get('hostname') or client_id
            
            # Remove client from the main clients dictionary
            del state.clients[client_id]
            
            logger.info(f"Successfully removed client: {client_name} ({client_id})")
        
        return jsonify({
            "message": f"Client '{client_name}' removed successfully",
            "removed_client_id": client_id,
            "removed_client_name": client_name
        }), 200
        
    except Exception as e:
        logger.error(f"Error removing client: {e}")
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