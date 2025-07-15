# blueprints/client_management.py
"""
Enhanced Client Management with Registration-Based Stream Assignment
Integrates with Docker discovery and stateless stream management
"""

from flask import Blueprint, request, jsonify, current_app
import time
import threading
import logging
import traceback
import uuid
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

def get_persistent_streams_for_group(group_id: str, group_name: str, split_count: int = 4):
    """Get persistent stream IDs for a group - integrate with stream management"""
    try:
        # Import from stateless stream management
        from blueprints.stream_management import get_persistent_streams_for_group as get_streams
        return get_streams(group_id, group_name, split_count)
    except ImportError:
        # Fallback if stream management not available
        logger.warning("Stream management not available, using fallback streams")
        streams = {"test": str(uuid.uuid4())[:8]}
        for i in range(split_count):
            streams[f"test{i}"] = str(uuid.uuid4())[:8]
        return streams

def check_group_streaming_status(group_id: str, group_name: str) -> bool:
    """Check if streaming is active for a group"""
    try:
        from blueprints.stream_management import find_running_ffmpeg_for_group
        ffmpeg_processes = find_running_ffmpeg_for_group(group_id, group_name)
        return len(ffmpeg_processes) > 0
    except ImportError:
        logger.warning("Stream management not available, assuming streaming is active")
        return True

# =====================================
# CLIENT REGISTRATION ENDPOINTS
# =====================================

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
        ip_address = data.get("ip_address") or request.remote_addr
        display_name = data.get("display_name")
        platform = data.get("platform", "unknown")
        
        if not hostname:
            return jsonify({"error": "Missing hostname"}), 400
        
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
                    "platform": platform,
                    "last_seen": current_time,
                    "status": "active"
                })
                
                logger.info(f"Updated existing client: {client_id}")
                action = "updated"
            else:
                # Create new client
                state.clients[client_id] = {
                    "client_id": client_id,
                    "hostname": hostname,
                    "ip_address": ip_address,
                    "display_name": display_name or hostname,
                    "platform": platform,
                    "registered_at": current_time,
                    "last_seen": current_time,
                    "status": "waiting_for_assignment",
                    "group_id": None,
                    "stream_assignment": None,
                    "stream_url": None,
                    "assigned_at": None
                }
                
                logger.info(f"Registered new client: {client_id}")
                action = "registered"
        
        return jsonify({
            "message": f"Client {action} successfully",
            "client_id": client_id,
            "status": "waiting_for_assignment",
            "next_action": "wait_for_assignment"
        }), 200
        
    except Exception as e:
        logger.error(f"Error registering client: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@client_bp.route("/wait_for_stream", methods=["POST"])
def wait_for_stream():
    """Client polls this endpoint to wait for stream assignment and streaming to start"""
    try:
        state = get_state()
        data = request.get_json() or {}
        
        client_id = data.get("client_id") or data.get("hostname")
        
        if not client_id:
            return jsonify({"error": "client_id or hostname is required"}), 400
        
        # Initialize clients if needed
        if not hasattr(state, 'clients'):
            state.clients = {}
        
        # Update client heartbeat
        current_time = time.time()
        
        with state.clients_lock:
            if client_id not in state.clients:
                return jsonify({
                    "status": "not_registered",
                    "action": "register_first",
                    "message": "Client not registered, please register first"
                }), 404
            
            client = state.clients[client_id]
            client["last_seen"] = current_time
            client["status"] = "active"
            
            # Check if client is assigned to a group
            group_id = client.get("group_id")
            if not group_id:
                return jsonify({
                    "status": "waiting_for_group_assignment",
                    "message": "Client not assigned to any group yet. Admin needs to assign client to a group."
                }), 200
            
            # Check if client has stream assignment
            stream_assignment = client.get("stream_assignment")
            stream_url = client.get("stream_url")
            
            if not stream_assignment or not stream_url:
                return jsonify({
                    "status": "waiting_for_stream_assignment", 
                    "group_id": group_id,
                    "message": "Client assigned to group but no stream assigned yet. Admin needs to assign stream."
                }), 200
        
        # Verify group still exists and is running
        group = get_group_from_docker(group_id)
        if not group:
            # Clear invalid group assignment
            with state.clients_lock:
                client = state.clients[client_id]
                client.update({
                    "group_id": None,
                    "stream_assignment": None,
                    "stream_url": None,
                    "status": "waiting_for_assignment"
                })
            
            return jsonify({
                "status": "group_not_found",
                "group_id": group_id,
                "message": "Assigned group no longer exists. Client unassigned."
            }), 404
        
        if not group.get("docker_running", False):
            return jsonify({
                "status": "group_not_running",
                "group_id": group_id,
                "group_name": group.get("name"),
                "message": "Group's Docker container is not running. Start the Docker container first."
            }), 503
        
        # Check if streaming is active for this group
        group_name = group.get("name", group_id)
        streaming_active = check_group_streaming_status(group_id, group_name)
        
        if not streaming_active:
            return jsonify({
                "status": "waiting_for_streaming",
                "group_id": group_id,
                "group_name": group_name,
                "stream_assignment": stream_assignment,
                "message": "Waiting for streaming to start. Use /start_group_srt to begin streaming."
            }), 200
        
        # Everything ready - return stream URL
        return jsonify({
            "status": "ready_to_play",
            "group_id": group_id,
            "group_name": group_name,
            "stream_assignment": stream_assignment,
            "stream_url": stream_url,
            "message": "Stream ready to play!"
        }), 200
        
    except Exception as e:
        logger.error(f"Error in wait_for_stream: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@client_bp.route("/move_client", methods=["POST"])
def move_client():
    """Move client up/down in order - Frontend compatibility"""
    try:
        data = request.get_json() or {}
        
        client_id = data.get("client_id")
        direction = data.get("direction")  # "up" or "down"
        
        if not all([client_id, direction]):
            return jsonify({"error": "client_id and direction are required"}), 400
        
        state = get_state()
        
        if not hasattr(state, 'clients') or client_id not in state.clients:
            return jsonify({"error": f"Client {client_id} not found"}), 404
        
        # For now, just return success - ordering can be implemented later
        # This is mainly for frontend compatibility
        
        return jsonify({
            "message": f"Client moved {direction}",
            "client_id": client_id,
            "direction": direction
        }), 200
        
    except Exception as e:
        logger.error(f"Error moving client: {e}")
        return jsonify({"error": str(e)}), 500

@client_bp.route("/rename_client", methods=["POST"])
def rename_client():
    """Rename client - Frontend compatibility"""
    try:
        data = request.get_json() or {}
        
        client_id = data.get("client_id")
        display_name = data.get("display_name")
        
        if not all([client_id, display_name]):
            return jsonify({"error": "client_id and display_name are required"}), 400
        
        state = get_state()
        
        if not hasattr(state, 'clients') or client_id not in state.clients:
            return jsonify({"error": f"Client {client_id} not found"}), 404
        
        with state.clients_lock:
            state.clients[client_id]["display_name"] = display_name
        
        return jsonify({
            "message": f"Client renamed to '{display_name}'",
            "client_id": client_id,
            "display_name": display_name
        }), 200
        
    except Exception as e:
        logger.error(f"Error renaming client: {e}")
        return jsonify({"error": str(e)}), 500
    
    
@client_bp.route("/assign_stream", methods=["POST"])
def assign_stream():
    """Assign stream to client - Frontend compatible endpoint"""
    try:
        logger.info("==== ASSIGN STREAM REQUEST (Frontend Compatible) ====")
        
        data = request.get_json() or {}
        
        client_id = data.get("client_id")
        stream_id = data.get("stream_id")
        group_id = data.get("group_id")
        
        if not all([client_id, stream_id]):
            return jsonify({"error": "client_id and stream_id are required"}), 400
        
        # Convert frontend stream_id format to backend format
        # Frontend might send: "test0", "test1", etc.
        # Backend expects: "test0", "test1", etc. (same format)
        stream_name = stream_id
        
        # Use the existing assign_client_stream logic
        state = get_state()
        
        if not hasattr(state, 'clients') or client_id not in state.clients:
            return jsonify({"error": f"Client {client_id} not found"}), 404
        
        # Call the existing assignment function
        assignment_data = {
            "client_id": client_id,
            "stream_name": stream_name,
            "group_id": group_id,
            "srt_ip": "128.205.39.64"  # Use your server IP
        }
        
        # Import and call the existing function
        from flask import current_app
        with current_app.test_request_context(json=assignment_data, method='POST'):
            response = assign_client_stream()
            response_data = response.get_json() if hasattr(response, 'get_json') else {}
            
            if response.status_code == 200:
                return jsonify({
                    "message": "Stream assigned successfully",
                    "client_id": client_id,
                    "stream_id": stream_id,  # Return in frontend format
                    "group_id": group_id
                }), 200
            else:
                return response
        
    except Exception as e:
        logger.error(f"Error in assign_stream (frontend): {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    
    
@client_bp.route("/assign_client_to_group", methods=["POST"])
def assign_client_to_group():
    """Assign a client to a specific group (Admin function)"""
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
            return jsonify({"error": f"Client '{client_id}' not found"}), 404
        
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
                client.update({
                    "group_id": group_id,
                    "assigned_at": time.time(),
                    "stream_assignment": None,  # Reset stream assignment
                    "stream_url": None,
                    "status": "assigned_to_group"
                })
                logger.info(f"Assigned client {client_id} to group {group_id}")
            else:
                # Unassign from group
                client.update({
                    "group_id": None,
                    "assigned_at": None,
                    "stream_assignment": None,
                    "stream_url": None,
                    "status": "waiting_for_assignment"
                })
                logger.info(f"Unassigned client {client_id} from group")
        
        return jsonify({
            "message": f"Client assigned successfully",
            "client_id": client_id,
            "old_group_id": old_group_id,
            "new_group_id": group_id,
            "status": "assigned_to_group" if group_id else "unassigned"
        }), 200
        
    except Exception as e:
        logger.error(f"Error assigning client to group: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@client_bp.route("/assign_client_stream", methods=["POST"])
def assign_client_stream():
    """Assign a specific stream to a client (Admin function)"""
    try:
        logger.info("==== ASSIGN CLIENT STREAM REQUEST RECEIVED ====")
        
        state = get_state()
        data = request.get_json() or {}
        
        client_id = data.get("client_id")
        group_id = data.get("group_id")
        stream_name = data.get("stream_name")  # e.g., "test0", "test1", "test"
        srt_ip = data.get("srt_ip", "127.0.0.1")  # Should be actual server IP
        
        if not client_id:
            return jsonify({"error": "client_id is required"}), 400
        
        # Initialize clients if needed
        if not hasattr(state, 'clients'):
            state.clients = {}
        
        # Verify client exists
        if client_id not in state.clients:
            return jsonify({"error": f"Client {client_id} not registered"}), 404
        
        # Get group_id from client if not provided
        with state.clients_lock:
            client = state.clients[client_id]
            if not group_id:
                group_id = client.get("group_id")
            
            if not group_id:
                return jsonify({"error": "Client not assigned to any group"}), 400
        
        # Verify group exists in Docker
        group = get_group_from_docker(group_id)
        if not group:
            return jsonify({"error": f"Group {group_id} not found in Docker"}), 404
        
        group_name = group.get("name", group_id)
        
        # Auto-assign stream if not specified
        if not stream_name:
            # Get persistent streams for this group
            persistent_streams = get_persistent_streams_for_group(group_id, group_name, 4)
            
            # Find unassigned streams
            with state.clients_lock:
                assigned_streams = set()
                for other_client in state.clients.values():
                    if (other_client.get("group_id") == group_id and 
                        other_client.get("stream_assignment") and
                        other_client["client_id"] != client_id):  # Exclude current client
                        assigned_streams.add(other_client["stream_assignment"])
                
                # Prefer split streams (test0, test1, etc.) over full stream (test)
                available_streams = [name for name in persistent_streams.keys() 
                                   if name.startswith("test") and len(name) > 4]
                if not available_streams:
                    available_streams = ["test"]  # Fallback to full stream
                
                # Find first unassigned stream
                for stream in available_streams:
                    if stream not in assigned_streams:
                        stream_name = stream
                        break
                
                if not stream_name:
                    # All streams assigned, use round-robin
                    stream_name = available_streams[len(assigned_streams) % len(available_streams)]
        
        # Build stream URL
        ports = group.get("ports", {})
        srt_port = ports.get("srt_port", 10080)
        
        persistent_streams = get_persistent_streams_for_group(group_id, group_name, 4)
        if stream_name not in persistent_streams:
            return jsonify({"error": f"Stream {stream_name} not available in group"}), 400
        
        stream_id = persistent_streams[stream_name]
        stream_path = f"live/{group_name}/{stream_id}"
        stream_url = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={stream_path},m=request"
        
        # Update client assignment
        with state.clients_lock:
            client = state.clients[client_id]
            client.update({
                "group_id": group_id,  # Ensure group_id is set
                "stream_assignment": stream_name,
                "stream_url": stream_url,
                "assigned_at": time.time(),
                "status": "stream_assigned"
            })
        
        logger.info(f"✅ Assigned client {client_id} to group {group_id}, stream {stream_name}")
        
        return jsonify({
            "message": f"Stream assigned successfully",
            "client_id": client_id,
            "group_id": group_id,
            "group_name": group_name,
            "stream_name": stream_name,
            "stream_url": stream_url,
            "status": "stream_assigned"
        }), 200
        
    except Exception as e:
        logger.error(f"Error assigning client stream: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@client_bp.route("/auto_assign_group_clients", methods=["POST"])
def auto_assign_group_clients():
    """Auto-assign all clients in a group to different streams (Admin function)"""
    try:
        logger.info("==== AUTO ASSIGN GROUP CLIENTS REQUEST RECEIVED ====")
        
        state = get_state()
        data = request.get_json() or {}
        
        group_id = data.get("group_id")
        srt_ip = data.get("srt_ip", "127.0.0.1")
        
        if not group_id:
            return jsonify({"error": "group_id is required"}), 400
        
        # Verify group exists
        group = get_group_from_docker(group_id)
        if not group:
            return jsonify({"error": f"Group {group_id} not found"}), 404
        
        group_name = group.get("name", group_id)
        
        # Initialize clients if needed
        if not hasattr(state, 'clients'):
            state.clients = {}
        
        assignments = []
        
        with state.clients_lock:
            # Get clients assigned to this group
            group_clients = [
                client for client_id, client in state.clients.items()
                if client.get("group_id") == group_id
            ]
            
            if not group_clients:
                return jsonify({
                    "message": f"No clients assigned to group {group_id}",
                    "assignments": []
                }), 200
            
            # Get available streams
            persistent_streams = get_persistent_streams_for_group(group_id, group_name, len(group_clients))
            
            # Prefer split streams over full stream
            stream_names = [name for name in persistent_streams.keys() 
                           if name.startswith("test") and len(name) > 4]
            if not stream_names:
                stream_names = ["test"]  # Fallback to full stream
            
            # Build stream URLs
            ports = group.get("ports", {})
            srt_port = ports.get("srt_port", 10080)
            
            # Assign streams to clients
            for i, client in enumerate(group_clients):
                stream_name = stream_names[i % len(stream_names)]  # Round-robin
                stream_id = persistent_streams[stream_name]
                stream_path = f"live/{group_name}/{stream_id}"
                stream_url = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={stream_path},m=request"
                
                # Update client
                client.update({
                    "stream_assignment": stream_name,
                    "stream_url": stream_url,
                    "assigned_at": time.time(),
                    "status": "stream_assigned"
                })
                
                assignments.append({
                    "client_id": client.get("client_id", "unknown"),
                    "hostname": client.get("hostname", "unknown"),
                    "display_name": client.get("display_name", "unknown"),
                    "stream_name": stream_name,
                    "stream_url": stream_url
                })
        
        logger.info(f"✅ Auto-assigned {len(assignments)} clients in group {group_id}")
        
        return jsonify({
            "message": f"Auto-assigned {len(assignments)} clients in group {group_id}",
            "group_id": group_id,
            "group_name": group_name,
            "assignments": assignments
        }), 200
        
    except Exception as e:
        logger.error(f"Error in auto-assign group clients: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@client_bp.route("/unassign_client", methods=["POST"])
def unassign_client():
    """Unassign a client from its group and stream (Admin function)"""
    try:
        logger.info("==== UNASSIGN CLIENT REQUEST RECEIVED ====")
        
        state = get_state()
        data = request.get_json() or {}
        
        client_id = data.get("client_id")
        
        if not client_id:
            return jsonify({"error": "client_id is required"}), 400
        
        if not hasattr(state, 'clients'):
            state.clients = {}
        
        if client_id not in state.clients:
            return jsonify({"error": "Client not found"}), 404
        
        with state.clients_lock:
            client = state.clients[client_id]
            old_group_id = client.get("group_id")
            old_stream = client.get("stream_assignment")
            
            # Clear assignments
            client.update({
                "group_id": None,
                "stream_assignment": None,
                "stream_url": None,
                "status": "waiting_for_assignment",
                "unassigned_at": time.time()
            })
        
        logger.info(f"✅ Unassigned client {client_id} from group {old_group_id}")
        
        return jsonify({
            "message": f"Client {client_id} unassigned successfully",
            "client_id": client_id,
            "old_group_id": old_group_id,
            "old_stream": old_stream,
            "status": "waiting_for_assignment"
        }), 200
        
    except Exception as e:
        logger.error(f"Error unassigning client: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# =====================================
# CLIENT INFORMATION ENDPOINTS
# =====================================

@client_bp.route("/get_clients", methods=["GET"])
def get_clients():
    """Get all registered clients with their assignments - Frontend Compatible Format"""
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
                        "docker_running": group.get("docker_running", False),
                        "docker_status": group.get("docker_status", "unknown")
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
                
                # Determine client status
                status = client_data.get("status", "unknown")
                if not is_active:
                    status = "inactive"
                
                # FORMAT FOR FRONTEND COMPATIBILITY
                client_info = {
                    "client_id": client_id,
                    "hostname": client_data.get("hostname", client_id),
                    "ip": client_data.get("ip_address", "unknown"),  # Frontend expects 'ip', not 'ip_address'
                    "display_name": client_data.get("display_name", client_id),
                    "platform": client_data.get("platform", "unknown"),
                    "registered_at": client_data.get("registered_at", 0),
                    "last_seen": last_seen,
                    "last_seen_formatted": format_time_ago(seconds_ago),  # Frontend might expect this
                    "seconds_ago": seconds_ago,
                    "is_active": is_active,
                    "status": "active" if is_active else "inactive",  # Frontend expects 'active'/'inactive'
                    "group_id": group_id,
                    "group_name": group_info.get("name") if group_info else None,
                    "group_docker_running": group_info.get("docker_running") if group_info else None,
                    "group_docker_status": group_info.get("docker_status") if group_info else None,
                    "stream_id": client_data.get("stream_assignment"),  # Frontend expects 'stream_id', not 'stream_assignment'
                    "stream_url": client_data.get("stream_url"),
                    "assigned_at": client_data.get("assigned_at"),
                    
                    # Additional fields that might be needed
                    "stream_assignment": client_data.get("stream_assignment"),  # Keep both for compatibility
                    "order": len(clients_list)  # Frontend might use this for ordering
                }
                
                clients_list.append(client_info)
        
        # Sort by last seen (most recent first)
        clients_list.sort(key=lambda x: x["last_seen"], reverse=True)
        
        # Count various client states
        active_clients = len([c for c in clients_list if c["is_active"]])
        assigned_clients = len([c for c in clients_list if c["group_id"]])
        waiting_clients = len([c for c in clients_list if "waiting" in c["status"]])
        
        logger.info(f"Returning {len(clients_list)} clients ({active_clients} active, {assigned_clients} assigned)")
        
        return jsonify({
            "clients": clients_list,
            "total_clients": len(clients_list),
            "active_clients": active_clients,
            "assigned_clients": assigned_clients,
            "waiting_clients": waiting_clients,
            "groups_available": len(groups_info),
            "timestamp": current_time
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting clients: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    

@client_bp.route("/remove_client", methods=["POST"])
def remove_client():
    """Remove a client from the system (Admin function)"""
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

# =====================================
# UTILITY FUNCTIONS
# =====================================

def get_active_clients_count(group_id: str = None) -> int:
    """Get count of active clients, optionally filtered by group"""
    try:
        state = get_state()
        
        if not hasattr(state, 'clients'):
            return 0
        
        current_time = time.time()
        active_count = 0
        
        with state.clients_lock:
            for client in state.clients.values():
                # Check if client is active (seen within 60 seconds)
                if current_time - client.get("last_seen", 0) <= 60:
                    # Filter by group if specified
                    if group_id is None or client.get("group_id") == group_id:
                        active_count += 1
        
        return active_count
        
    except Exception as e:
        logger.error(f"Error counting active clients: {e}")
        return 0

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

# Add this method to the state class if needed
def get_state():
    """Get application state - ensures state has active client count method"""
    state = current_app.config['APP_STATE']
    
    # Add method to state if it doesn't exist
    if not hasattr(state, 'get_active_clients_count'):
        state.get_active_clients_count = lambda group_id=None: get_active_clients_count(group_id)
    
    return state