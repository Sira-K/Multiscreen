# blueprints/client_management.py - Updated with Group Support
from flask import Blueprint, request, jsonify, current_app
import traceback
import time
import threading
import logging
import os
from typing import Dict, List, Any, Optional, Tuple

# Create blueprint
client_bp = Blueprint('client', __name__)

# Configure logging
logger = logging.getLogger(__name__)

# Type alias for client info
ClientInfo = Dict[str, Any]

def get_state():
    """Get application state from current app context"""
    return current_app.config['APP_STATE']

def get_available_videos():
    """Get list of available videos for client assignment"""
    try:
        # Check both resized and raw video folders
        download_folder = current_app.config.get('DOWNLOAD_FOLDER', 'resized_video')
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'raw_video_file')
        
        available_videos = []
        
        # Priority 1: Check resized videos folder
        if os.path.exists(download_folder):
            video_extensions = ('.mp4', '.mkv', '.avi', '.mov', '.webm')
            try:
                for filename in os.listdir(download_folder):
                    if filename.lower().endswith(video_extensions):
                        # Remove 2k_ prefix for client compatibility
                        client_filename = filename
                        if filename.startswith('2k_'):
                            client_filename = filename[3:]  # Remove '2k_' prefix
                        
                        available_videos.append({
                            'client_name': client_filename,  # Name client expects
                            'server_path': f"resized_videos/{filename}",  # Actual server path
                            'source': 'resized'
                        })
            except Exception as e:
                logger.warning(f"Error scanning resized videos: {e}")
        
        # Priority 2: Check raw videos folder (fallback)
        if not available_videos and os.path.exists(upload_folder):
            video_extensions = ('.mp4', '.mkv', '.avi', '.mov', '.webm')
            try:
                for filename in os.listdir(upload_folder):
                    if filename.lower().endswith(video_extensions):
                        available_videos.append({
                            'client_name': filename,  # Original name
                            'server_path': f"uploads/{filename}",  # Old path for compatibility
                            'source': 'raw'
                        })
            except Exception as e:
                logger.warning(f"Error scanning raw videos: {e}")
        
        logger.info(f"Found {len(available_videos)} videos for client assignment")
        return available_videos
        
    except Exception as e:
        logger.error(f"Error getting available videos: {e}")
        return []

def validate_client_data(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate client registration data
    
    Args:
        data: The client data to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not data:
        return False, "No JSON data provided"
        
    if not data.get("client_id"):
        return False, "Missing client_id parameter"
        
    return True, None

@client_bp.route("/register_client", methods=["POST"])
def register_client():
    """Register a client device with the server - Updated with group support"""
    try:
        logger.info("==== REGISTER CLIENT REQUEST RECEIVED ====")
        logger.info(f"Request JSON: {request.get_json()}")
        logger.info(f"Remote Address: {request.remote_addr}")
        
        # Get app state
        state = get_state()
        
        # Initialize state objects if needed
        if not hasattr(state, 'clients_lock'):
            state.clients_lock = threading.RLock()
        
        if not hasattr(state, 'clients'):
            state.clients = {}
            
        if not hasattr(state, 'groups'):
            state.groups = {}
        
        # Parse and validate request data
        data = request.get_json()
        is_valid, error_message = validate_client_data(data)
        
        if not is_valid:
            return jsonify({"error": error_message}), 400
            
        client_id = data.get("client_id")
        client_info = data.get("client_info", {})
        preferred_group = data.get("group_id")  # Optional group preference
        
        logger.info(f"Registering client with ID: {client_id}")
        
        # Get available videos for assignment
        available_videos = get_available_videos()
        
        with state.clients_lock:
            # Check if client already exists
            existing_client = state.clients.get(client_id, {})
            existing_group_id = existing_client.get("group_id")
            
            # Determine group assignment
            assigned_group_id = existing_group_id or preferred_group
            
            # If no group specified and no existing assignment, try to find a suitable group
            if not assigned_group_id and state.groups:
                # Find a group that's active and has space
                for group_id, group_data in state.groups.items():
                    if (group_data.get("status") == "active" and 
                        len(group_data.get("clients", {})) < group_data.get("screen_count", 2)):
                        assigned_group_id = group_id
                        logger.info(f"Auto-assigning client to available group: {group_id}")
                        break
            
            # Determine video assignment
            assigned_video = existing_client.get("video_file")
            
            # If no existing assignment and videos are available, assign the first one
            if not assigned_video and available_videos:
                assigned_video = available_videos[0]['client_name']
                logger.info(f"Auto-assigning video to new client: {assigned_video}")
            
            # Create or update client record
            state.clients[client_id] = {
                "id": client_id,
                "ip": client_info.get("ip_address") or request.remote_addr,
                "hostname": client_info.get("hostname", "Unknown"),
                "platform": client_info.get("platform", "Unknown"),
                "mac_address": client_info.get("mac_address", "Unknown"),
                "last_seen": time.time(),
                "status": "active",
                "client_type": client_info.get("client_type", "srt_stream"),  # Default to SRT streaming
                # Group assignment
                "group_id": assigned_group_id,
                # Video file assignment (for file-based clients)
                "video_file": assigned_video,
                # Stream assignment (for SRT streaming clients) 
                "stream_id": existing_client.get("stream_id", None),
                # Display name
                "display_name": existing_client.get("display_name", None)
            }
            
            # Update group membership
            if assigned_group_id and assigned_group_id in state.groups:
                if not hasattr(state, 'groups_lock'):
                    state.groups_lock = threading.RLock()
                    
                with state.groups_lock:
                    if "clients" not in state.groups[assigned_group_id]:
                        state.groups[assigned_group_id]["clients"] = {}
                    
                    state.groups[assigned_group_id]["clients"][client_id] = {
                        "assigned_at": time.time(),
                        "stream_id": existing_client.get("stream_id", None)
                    }
                    
                    # Auto-assign stream within group if available
                    group_streams = get_group_available_streams(assigned_group_id)
                    if group_streams["available_streams"] and not state.clients[client_id].get("stream_id"):
                        stream_id = group_streams["available_streams"][0]  # Assign first available
                        state.clients[client_id]["stream_id"] = stream_id
                        state.groups[assigned_group_id]["clients"][client_id]["stream_id"] = stream_id
                        logger.info(f"Auto-assigned stream {stream_id} to client in group {assigned_group_id}")
            
            logger.info(f"Client state after registration: {state.clients[client_id]}")
            logger.info(f"Total clients now: {len(state.clients)}")
            
        # Prepare response based on client type and group assignment
        response_data = {
            "message": f"Client {client_id} registered successfully"
        }
        
        # Add group information
        if assigned_group_id:
            response_data["group_id"] = assigned_group_id
            if assigned_group_id in state.groups:
                group = state.groups[assigned_group_id]
                response_data["group_name"] = group.get("name", assigned_group_id)
                response_data["srt_port"] = group.get("srt_port", 10080)
        
        # Add video file info for video clients
        if assigned_video:
            response_data["video_file"] = assigned_video
            
        # Add stream info for SRT clients  
        if state.clients[client_id].get("stream_id"):
            response_data["stream_id"] = state.clients[client_id]["stream_id"]
            
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error registering client: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@client_bp.route("/get_clients", methods=["GET"])
def get_clients():
    """Get a list of all registered clients with group and stream info"""
    logger.info("==== GET_CLIENTS REQUEST RECEIVED ====")
    state = get_state()

    try:
        # Get optional group filter
        group_id = request.args.get('group_id')
        
        with state.clients_lock if hasattr(state, 'clients_lock') else threading.RLock():
            # Consider a client inactive if not seen in the last minute
            current_time = time.time()
            client_list = []
            
            logger.info(f"Total clients in state: {len(state.clients) if hasattr(state, 'clients') else 0}")
            
            if not hasattr(state, 'clients'):
                state.clients = {}
            
            for client_id, client_data in state.clients.items():
                # Filter by group if specified
                if group_id and client_data.get("group_id") != group_id:
                    continue
                    
                # Create a copy of the client data for modification
                client = dict(client_data)
                
                # Update status based on last seen time
                inactive_threshold = 60  # seconds
                if current_time - client_data.get("last_seen", 0) > inactive_threshold:
                    client["status"] = "inactive"
                else:
                    client["status"] = "active"
                    
                # Add formatted last seen time
                seconds_ago = int(current_time - client_data.get("last_seen", 0))
                client["last_seen_formatted"] = format_time_ago(seconds_ago)
                
                # Add group information
                client_group_id = client.get("group_id")
                if client_group_id and hasattr(state, 'groups') and client_group_id in state.groups:
                    group = state.groups[client_group_id]
                    client["group_name"] = group.get("name", client_group_id)
                    client["group_status"] = group.get("status", "unknown")
                    client["srt_port"] = group.get("srt_port", 10080)
                else:
                    client["group_name"] = None
                    client["group_status"] = None
                    client["srt_port"] = 10080  # Default port
                    
                client_list.append(client)
            
            # Get available streams based on group or global
            if group_id:
                streams_info = get_group_available_streams(group_id)
            else:
                # Return all streams from all groups
                all_streams = set()
                total_active = 0
                
                if hasattr(state, 'groups'):
                    for gid in state.groups.keys():
                        group_streams = get_group_available_streams(gid)
                        all_streams.update(group_streams["available_streams"])
                        total_active += group_streams["active_clients"]
                
                streams_info = {
                    "available_streams": list(all_streams),
                    "active_clients": total_active,
                    "max_screens": 4  # Default
                }
            
            logger.info(f"Returning {len(client_list)} clients")
                
            return jsonify({
                "clients": client_list,
                "total": len(client_list),
                "active": len([c for c in client_list if c["status"] == "active"]),
                "available_streams": streams_info["available_streams"],
                "max_screens": streams_info["max_screens"],
                "group_filter": group_id
            }), 200
    except Exception as e:
        logger.error(f"Error getting clients: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@client_bp.route("/assign_stream", methods=["POST"])
def assign_stream():
    """Assign a specific stream to a client - Updated with group support"""
    state = get_state()

    try:
        # Get and validate request data
        data = request.get_json()
        
        logger.info(f"Received assign_stream request: {data}")
        
        if not data:
            return jsonify({"error": "Missing request data"}), 400
            
        client_id = data.get("client_id")
        stream_id = data.get("stream_id") or data.get("stream_name")
        
        if not client_id:
            return jsonify({"error": "Missing required parameter: client_id"}), 400
            
        with state.clients_lock if hasattr(state, 'clients_lock') else threading.RLock():
            if client_id not in state.clients:
                return jsonify({"error": f"Client not registered: {client_id}"}), 404
                
            client = state.clients[client_id]
            client_group_id = client.get("group_id")
            
            # Get available streams for the client's group
            if client_group_id:
                streams_info = get_group_available_streams(client_group_id)
            else:
                # If no group, return error
                return jsonify({"error": "Client must be assigned to a group before stream assignment"}), 400
            
            # Check if the requested stream is available for this group
            if stream_id and stream_id not in streams_info["available_streams"]:
                return jsonify({
                    "error": f"Stream {stream_id} is not available for group {client_group_id}. Available streams: {streams_info['available_streams']}"
                }), 400
                
            # Debug - print before state
            logger.info(f"Client before update: {client}")
            
            # Set the stream_id and mark as SRT client
            state.clients[client_id]["stream_id"] = stream_id
            state.clients[client_id]["client_type"] = "srt_stream"
            
            # Update group assignment
            if client_group_id and hasattr(state, 'groups') and client_group_id in state.groups:
                with state.groups_lock if hasattr(state, 'groups_lock') else threading.RLock():
                    if "clients" not in state.groups[client_group_id]:
                        state.groups[client_group_id]["clients"] = {}
                    state.groups[client_group_id]["clients"][client_id] = {
                        "assigned_at": time.time(),
                        "stream_id": stream_id
                    }
                
            # Debug - print after state
            logger.info(f"Client after update: {state.clients[client_id]}")
            
        return jsonify({
            "message": f"Client {client_id} assigned to stream {stream_id} in group {client_group_id}",
            "client": state.clients[client_id],
            "available_streams": streams_info["available_streams"]
        }), 200
    except Exception as e:
        logger.error(f"Error assigning stream: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@client_bp.route("/available_streams", methods=["GET"])
def available_streams_endpoint():
    """Endpoint to get available streams based on group or global"""
    try:
        group_id = request.args.get('group_id')
        
        if group_id:
            streams_info = get_group_available_streams(group_id)
        else:
            # Return streams from all groups
            state = get_state()
            all_streams = set()
            total_active = 0
            
            if hasattr(state, 'groups'):
                for gid in state.groups.keys():
                    group_streams = get_group_available_streams(gid)
                    all_streams.update(group_streams["available_streams"])
                    total_active += group_streams["active_clients"]
            
            streams_info = {
                "available_streams": list(all_streams),
                "active_clients": total_active,
                "max_screens": 4,
                "group_name": "All Groups"
            }
        
        return jsonify(streams_info), 200
    except Exception as e:
        logger.error(f"Error getting available streams: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

def get_group_available_streams(group_id: str) -> Dict[str, Any]:
    """
    Get the list of available streams for a specific group based on connected clients.
    """
    # Get app state
    state = get_state()
    
    # Check if group exists
    if not hasattr(state, 'groups') or group_id not in state.groups:
        return {
            "available_streams": [],
            "active_clients": 0,
            "max_screens": 1,
            "group_name": "Unknown"
        }
    
    group = state.groups[group_id]
    screen_count = group.get("screen_count", 2)
    
    # Ensure clients_lock exists
    if not hasattr(state, 'clients_lock'):
        state.clients_lock = threading.RLock()
    
    # Ensure clients dict exists
    if not hasattr(state, 'clients'):
        state.clients = {}
    
    with state.clients_lock:
        # Count active clients in this group
        current_time = time.time()
        inactive_threshold = 60  # seconds
        
        active_clients = 0
        for client_data in state.clients.values():
            if (client_data.get("group_id") == group_id and 
                current_time - client_data.get("last_seen", 0) <= inactive_threshold):
                active_clients += 1
        
        # Always include the full stream for this group
        available_streams = [f"live/{group_id}/test"]
        
        # Add split streams based on client count and screen_count
        if active_clients >= 2:
            # If we have at least 2 active clients, make split streams available
            # But limit to our configured screen_count
            for i in range(min(active_clients, screen_count)):
                available_streams.append(f"live/{group_id}/test{i}")
        
        return {
            "available_streams": available_streams,
            "active_clients": active_clients,
            "max_screens": screen_count,
            "group_name": group.get("name", group_id),
            "full_stream": f"live/{group_id}/test"  # Always available
        }

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

# Keep existing endpoints for backward compatibility
@client_bp.route("/assign_video", methods=["POST"])
def assign_video():
    """Assign a specific video to a client - Legacy endpoint"""
    # This endpoint is kept for backward compatibility
    # but groups should use the streaming approach instead
    state = get_state()

    try:
        data = request.get_json()
        logger.info(f"Received assign_video request: {data}")
        
        if not data:
            return jsonify({"error": "Missing request data"}), 400
            
        client_id = data.get("client_id")
        video_name = data.get("video_name") or data.get("video_file")
        
        if not client_id:
            return jsonify({"error": "Missing required parameter: client_id"}), 400
            
        available_videos = get_available_videos()
        video_names = [v['client_name'] for v in available_videos]
        
        if video_name and video_name not in video_names:
            return jsonify({
                "error": f"Video {video_name} is not available. Available videos: {video_names}"
            }), 400
            
        with state.clients_lock if hasattr(state, 'clients_lock') else threading.RLock():
            if client_id not in state.clients:
                return jsonify({"error": f"Client not registered: {client_id}"}), 404
                
            logger.info(f"Client before update: {state.clients[client_id]}")
            state.clients[client_id]["video_file"] = video_name
            logger.info(f"Client after update: {state.clients[client_id]}")
            
        return jsonify({
            "message": f"Client {client_id} assigned to video {video_name}",
            "client": state.clients[client_id],
            "available_videos": video_names
        }), 200
    except Exception as e:
        logger.error(f"Error assigning video: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@client_bp.route("/rename_client", methods=["POST"])
def rename_client():
    """Rename a client for easier identification"""
    state = get_state()
    try:
        data = request.get_json()
        client_id = data.get("client_id")
        display_name = data.get("display_name")
        
        if not client_id:
            return jsonify({"error": "Missing client_id parameter"}), 400
            
        if not display_name:
            return jsonify({"error": "Missing display_name parameter"}), 400
            
        with state.clients_lock if hasattr(state, 'clients_lock') else threading.RLock():
            if client_id not in state.clients:
                return jsonify({"error": "Client not registered"}), 404
                
            state.clients[client_id]["display_name"] = display_name
            
        return jsonify({
            "message": f"Client {client_id} renamed to '{display_name}'",
            "client": state.clients[client_id]
        }), 200
    except Exception as e:
        logger.error(f"Error renaming client: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@client_bp.route("/client_status", methods=["POST"])
def client_status():
    """Check what stream/video a client should be displaying - Updated with group support"""
    state = get_state()
    
    try:
        data = request.get_json()
        
        if not data or not data.get("client_id"):
            return jsonify({"error": "Missing client_id parameter"}), 400
        
        client_id = data.get("client_id")
        
        # Get available videos for potential assignment
        available_videos = get_available_videos()
                
        with state.clients_lock if hasattr(state, 'clients_lock') else threading.RLock():
            if client_id not in state.clients:
                # Auto-register unknown clients without group assignment
                assigned_video = available_videos[0]['client_name'] if available_videos else None
                
                state.clients[client_id] = {
                    "id": client_id,
                    "ip": request.remote_addr,
                    "hostname": "Unknown",
                    "last_seen": time.time(),
                    "status": "active",
                    "client_type": "srt_stream",  # Default to SRT streaming
                    "group_id": None,  # No group assignment for auto-registered clients
                    "video_file": assigned_video,
                    "stream_id": None
                }
                
                logger.info(f"Auto-registered new client {client_id} (no group assignment)")
            else:
                # Update last seen timestamp
                state.clients[client_id]["last_seen"] = time.time()
                state.clients[client_id]["status"] = "active"
                
                # Ensure client has a video assignment if videos are available
                if not state.clients[client_id].get("video_file") and available_videos:
                    state.clients[client_id]["video_file"] = available_videos[0]['client_name']
                    logger.info(f"Assigned video to existing client {client_id}: {available_videos[0]['client_name']}")
            
            client_data = state.clients[client_id]
            
        # Determine response based on client type and group assignment
        client_type = client_data.get("client_type", "srt_stream")
        client_group_id = client_data.get("group_id")
        
        if client_type == "srt_stream" and client_group_id:
            # SRT streaming client with group assignment
            group = state.groups.get(client_group_id, {}) if hasattr(state, 'groups') else {}
            
            response_data = {
                "client_id": client_id,
                "stream_id": client_data.get("stream_id"),
                "group_id": client_group_id,
                "group_name": group.get("name", client_group_id),
                "srt_ip": getattr(state, 'srt_ip', '127.0.0.1'),
                "srt_port": group.get("srt_port", 10080),
                "orientation": group.get("orientation", "horizontal"),
                "status": "active"
            }
        elif client_type == "srt_stream":
            # SRT streaming client without group (legacy mode)
            response_data = {
                "client_id": client_id,
                "stream_id": client_data.get("stream_id"),
                "group_id": None,
                "srt_ip": getattr(state, 'srt_ip', '127.0.0.1'),
                "srt_port": 10080,
                "orientation": getattr(state, 'orientation', "horizontal"),
                "status": "active",
                "message": "Client not assigned to any group"
            }
        else:
            # Video file client - return video assignment
            video_file = client_data.get("video_file")
            
            response_data = {
                "client_id": client_id,
                "video_file": video_file,
                "status": "active",
                "available_videos": [v['client_name'] for v in available_videos]
            }
            
            # Add download URL mapping for the assigned video
            if video_file and available_videos:
                # Find the server path for this video
                for video in available_videos:
                    if video['client_name'] == video_file:
                        response_data["download_url"] = f"/{video['server_path']}"
                        response_data["video_source"] = video['source']
                        break
            
        logger.info(f"Client status response for {client_id}: {response_data}")
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error checking client status: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500