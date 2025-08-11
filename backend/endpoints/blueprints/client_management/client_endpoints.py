# backend/endpoints/blueprints/client_management/client_endpoints.py
"""
Client Registration and Polling Endpoints
Core client-facing endpoints for registration and status polling
Complete file with all functions and fixes for stream URL assignment
"""

import time
import uuid
import logging
import traceback
from typing import Dict, Any, List, Optional
from flask import request, jsonify, current_app

logger = logging.getLogger(__name__)

# =====================================
# HELPER FUNCTIONS
# =====================================

def get_state():
    """Get the application state"""
    return current_app.config.get('APP_STATE')

def get_group_from_docker(group_id: str) -> Optional[Dict[str, Any]]:
    """
    Get group information from Docker discovery
    Clean import strategy - imports only when needed
    """
    try:
        from ..docker_management import get_all_groups
        groups = get_all_groups()
        return groups.get(group_id, {})
    except ImportError:
        logger.warning("Docker management not available")
        return {}
    except Exception as e:
        logger.error(f"Error getting group from Docker: {e}")
        return {}

def check_streaming_status_for_group(group_id: str, group_name: str, container_id: str = None) -> bool:
    """
    Check if streaming is active for a group
    Clean import strategy with fallback
    """
    try:
        from ..stream_management import check_streaming_status
        return check_streaming_status(container_id) if container_id else False
    except ImportError:
        logger.warning("Stream management not available, assuming streaming is inactive")
        return False
    except Exception as e:
        logger.error(f"Error checking streaming status for group {group_name}: {e}")
        return False

def generate_stream_ids(group_id: str, group_name: str, screen_count: int) -> Dict[str, str]:
    """Generate dynamic stream IDs for a session"""
    streams = {}
    
    # Generate a unique session ID based on current time and group
    session_id = str(uuid.uuid4())[:8]
    
    # Main/combined stream
    streams["test"] = f"{session_id}"
    
    # Individual screen streams
    for i in range(screen_count):
        streams[f"test{i}"] = f"{session_id}_{i}"
    
    return streams

def get_active_stream_ids_for_group(group_id: str, group_name: str, screen_count: int) -> Dict[str, str]:
    """
    Get current active stream IDs for a group
    Clean import strategy with graceful fallback
    """
    try:
        logger.info(f"Getting active stream IDs for group {group_name}")
        
        # Get group info
        group = get_group_from_docker(group_id)
        if not group:
            logger.error(f"Group {group_id} not found")
            return {}
        
        # Check if streaming is active
        container_id = group.get("container_id")
        is_streaming = check_streaming_status_for_group(group_id, group_name, container_id)
        
        if not is_streaming:
            logger.info(f"Group {group_name} is not currently streaming - no stream IDs available")
            return {}
        
        # Generate the SAME stream IDs that are actually being used
        stream_ids = generate_stream_ids(group_id, group_name, screen_count)
        
        logger.info(f"Active stream IDs for group {group_name}: {stream_ids}")
        return stream_ids
        
    except Exception as e:
        logger.error(f"Error getting active stream IDs: {e}")
        return {}

def build_stream_url_for_client(group: Dict[str, Any], stream_id: str, group_name: str, srt_ip: str = "127.0.0.1") -> str:
    """
    Build SRT stream URL for a client
    FIXED: Complete URL format with proper error handling
    """
    try:
        ports = group.get("ports", {})
        srt_port = ports.get("srt_port")
        
        if not srt_port:
            logger.error(f"No SRT port found for group {group_name}. Group ports: {ports}")
            srt_port = 10080
            logger.warning(f"Using fallback SRT port {srt_port} for group {group_name}")
        
        stream_path = f"live/{group_name}/{stream_id}"
        
        # FIXED: Complete SRT URL format with all required parameters
        stream_url = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={stream_path},m=request,latency=5000000"
        
        logger.info(f"Built stream URL - Group: {group_name}, Stream ID: {stream_id}, Port: {srt_port}, URL: {stream_url}")
        
        return stream_url
        
    except Exception as e:
        logger.error(f"Error building stream URL: {e}")
        fallback_url = f"srt://{srt_ip}:10080?streamid=#!::r=live/{group_name}/{stream_id},m=request,latency=5000000"
        logger.warning(f"Using fallback URL: {fallback_url}")
        return fallback_url

# =====================================
# CLIENT ENDPOINTS
# =====================================

def register_client():
    """
    Register a client device
    
    Expected payload:
    {
        "hostname": "display-001",
        "ip_address": "192.168.1.100",  # Optional, will use request IP
        "display_name": "Left Display",  # Optional
        "platform": "linux"  # Optional
    }
    """
    try:
        logger.info("==== CLIENT REGISTRATION REQUEST ====")
        
        # Import validators
        from .client_validators import validate_client_registration
        from .client_utils import get_next_steps
        
        # Get state
        state = get_state()
        
        # Parse and validate request data
        data = request.get_json()
        is_valid, error_msg, cleaned_data = validate_client_registration(data)
        
        if not is_valid:
            return jsonify({
                "success": False,
                "error": error_msg
            }), 400
        
        # Extract validated data
        hostname = cleaned_data["hostname"]
        ip_address = cleaned_data["ip_address"] or request.remote_addr
        display_name = cleaned_data["display_name"]
        platform = cleaned_data["platform"]
        
        client_id = hostname  # Use hostname as client ID
        current_time = time.time()
        
        logger.info(f"Registering client: {client_id} ({ip_address})")
        
        # Check for existing client
        existing_client = state.get_client(client_id) if hasattr(state, 'get_client') else state.clients.get(client_id)
        action = "updated" if existing_client else "registered"
        
        # Create or update client record
        client_data = {
            "client_id": client_id,
            "hostname": hostname,
            "ip_address": ip_address,
            "display_name": display_name,
            "platform": platform,
            "registered_at": existing_client.get("registered_at", current_time) if existing_client else current_time,
            "last_seen": current_time,
            "status": "active",
            "assignment_status": "waiting_for_assignment",
            
            # Group and stream assignment
            "group_id": existing_client.get("group_id") if existing_client else None,
            "group_name": existing_client.get("group_name") if existing_client else None,
            "stream_assignment": existing_client.get("stream_assignment") if existing_client else None,
            "stream_url": existing_client.get("stream_url") if existing_client else None,
            "screen_number": existing_client.get("screen_number") if existing_client else None,
            "assigned_at": existing_client.get("assigned_at") if existing_client else None,
            "srt_ip": existing_client.get("srt_ip", "127.0.0.1") if existing_client else "127.0.0.1"
        }
        
        # Update assignment status based on current assignments
        if client_data["group_id"]:
            if client_data["screen_number"] is not None:
                client_data["assignment_status"] = "screen_assigned"
            elif client_data["stream_assignment"]:
                client_data["assignment_status"] = "stream_assigned"
            else:
                client_data["assignment_status"] = "group_assigned"
        
        # Save client
        if hasattr(state, 'add_client'):
            state.add_client(client_id, client_data)
        elif hasattr(state, 'add_or_update_client'):
            state.add_or_update_client(client_id, client_data)
        else:
            state.clients[client_id] = client_data
        
        logger.info(f"Client {action}: {client_id} (status: {client_data['assignment_status']})")
        
        # Prepare response
        response_data = {
            "success": True,
            "message": f"Client {action} successfully",
            "client_id": client_id,
            "action": action,
            "status": client_data["assignment_status"],
            "server_time": current_time,
            "next_steps": get_next_steps(client_data)
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Client registration failed: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"Registration failed: {str(e)}"
        }), 500

def unregister_client():
    """Unregister a client"""
    try:
        data = request.get_json()
        client_id = data.get("client_id") if data else None
        
        if not client_id:
            return jsonify({
                "success": False,
                "error": "client_id is required"
            }), 400
        
        state = get_state()
        
        # Try different methods to remove client
        removed = False
        if hasattr(state, 'remove_client'):
            removed = state.remove_client(client_id)
        elif hasattr(state, 'clients'):
            if client_id in state.clients:
                del state.clients[client_id]
                removed = True
        
        if not removed:
            return jsonify({
                "success": False,
                "error": f"Client {client_id} not found"
            }), 404
        
        logger.info(f"Unregistered client: {client_id}")
        
        return jsonify({
            "success": True,
            "message": f"Client {client_id} unregistered successfully"
        }), 200
        
    except Exception as e:
        logger.error(f"Client unregistration failed: {e}")
        return jsonify({
            "success": False,
            "error": f"Unregistration failed: {str(e)}"
        }), 500

def wait_for_assignment():
    """
    FIXED: Enhanced client endpoint to check assignment status and get stream URL when ready
    Handles both screen assignments and direct stream assignments
    """
    try:
        from .client_utils import get_next_steps
        
        data = request.get_json() or {}
        client_id = data.get("client_id")
        
        if not client_id:
            return jsonify({
                "success": False,
                "status": "error",
                "message": "client_id is required"
            }), 400
        
        state = get_state()
        client = state.get_client(client_id) if hasattr(state, 'get_client') else state.clients.get(client_id)
        
        if not client:
            return jsonify({
                "success": False,
                "status": "not_registered",
                "message": "Client not found. Please register first."
            }), 404
        
        # Update last_seen
        client["last_seen"] = time.time()
        if hasattr(state, 'add_client'):
            state.add_client(client_id, client)
        else:
            state.clients[client_id] = client
        
        # Check assignment status
        assignment_status = client.get("assignment_status", "waiting_for_assignment")
        group_id = client.get("group_id")
        group_name = client.get("group_name")
        
        logger.info(f"Client {client_id} checking assignment - Status: {assignment_status}, Group: {group_name}")
        
        # Waiting for any assignment
        if assignment_status == "waiting_for_assignment":
            return jsonify({
                "success": False,
                "status": "waiting_for_assignment",
                "message": "Waiting for admin to assign you to a group",
                "next_steps": get_next_steps(client)
            }), 202
        
        # Assigned to group but not to stream/screen
        elif assignment_status == "group_assigned":
            return jsonify({
                "success": False,
                "status": "waiting_for_stream_assignment",
                "message": f"Assigned to group {group_name}, waiting for stream/screen assignment",
                "group_name": group_name,
                "next_steps": get_next_steps(client)
            }), 202
        
        # Handle screen assignment (multi-video mode)
        elif assignment_status == "screen_assigned":
            screen_number = client.get("screen_number")
            srt_ip = client.get("srt_ip", "127.0.0.1")
            
            # Check if streaming is active and resolve URL
            if group_id and group_name:
                group = get_group_from_docker(group_id)
                if not group:
                    logger.warning(f"Group {group_id} not found in Docker")
                    return jsonify({
                        "success": False,
                        "status": "group_not_found",
                        "message": f"Group {group_name} configuration not found"
                    }), 404
                
                # Check if streaming is active
                container_id = group.get("container_id")
                is_streaming = check_streaming_status_for_group(group_id, group_name, container_id)
                
                if not is_streaming:
                    return jsonify({
                        "success": False,
                        "status": "waiting_for_stream",
                        "message": f"Assigned to screen {screen_number}, waiting for streaming to start",
                        "group_name": group_name,
                        "screen_number": screen_number,
                        "assignment_status": "screen_assigned"
                    }), 202
                
                # Get active stream IDs
                screen_count = group.get("screen_count", 2)
                active_stream_ids = get_active_stream_ids_for_group(group_id, group_name, screen_count)
                
                if not active_stream_ids:
                    # Try generating them directly
                    active_stream_ids = generate_stream_ids(group_id, group_name, screen_count)
                
                # Get the stream ID for this specific screen
                screen_stream_key = f"test{screen_number}"
                if screen_stream_key in active_stream_ids:
                    stream_id = active_stream_ids[screen_stream_key]
                    
                    # FIXED: Build complete stream URL with proper format
                    stream_url = build_stream_url_for_client(group, stream_id, group_name, srt_ip)
                    
                    # Update client with resolved stream URL
                    client["stream_url"] = stream_url
                    client["stream_version"] = int(time.time())
                    if hasattr(state, 'add_client'):
                        state.add_client(client_id, client)
                    else:
                        state.clients[client_id] = client
                    
                    logger.info(f"✅ Resolved stream URL for client {client_id}:")
                    logger.info(f"   Screen: {screen_number}")
                    logger.info(f"   Stream ID: {stream_id}")
                    logger.info(f"   URL: {stream_url}")
                    
                    return jsonify({
                        "success": True,
                        "status": "ready_to_play",
                        "message": f"Stream ready for screen {screen_number}",
                        "group_name": group_name,
                        "stream_assignment": f"screen{screen_number}",
                        "screen_number": screen_number,
                        "stream_url": stream_url,
                        "stream_version": client.get("stream_version", 0),
                        "assignment_status": "screen_assigned"
                    }), 200
                else:
                    return jsonify({
                        "success": False,
                        "status": "stream_not_available",
                        "message": f"Stream for screen {screen_number} not available",
                        "available_streams": list(active_stream_ids.keys())
                    }), 404
        
        # Handle direct stream assignment
        elif assignment_status == "stream_assigned":
            stream_assignment = client.get("stream_assignment")
            stream_url = client.get("stream_url")
            
            # If we don't have a stream URL yet, try to build it
            if not stream_url and group_id and group_name:
                group = get_group_from_docker(group_id)
                if group:
                    # Get stream ID from persistent streams or generate one
                    from .admin_endpoints import get_persistent_streams_for_group
                    persistent_streams = get_persistent_streams_for_group(group_id, group_name, 4)
                    
                    if stream_assignment in persistent_streams:
                        stream_id = persistent_streams[stream_assignment]
                        srt_ip = client.get("srt_ip", "127.0.0.1")
                        
                        # FIXED: Build complete stream URL
                        stream_url = build_stream_url_for_client(group, stream_id, group_name, srt_ip)
                        
                        # Update client with the URL
                        client["stream_url"] = stream_url
                        client["stream_version"] = int(time.time())
                        if hasattr(state, 'add_client'):
                            state.add_client(client_id, client)
                        else:
                            state.clients[client_id] = client
                        
                        logger.info(f"✅ Built stream URL for client {client_id}: {stream_url}")
            
            if stream_url:
                return jsonify({
                    "success": True,
                    "status": "ready_to_play",
                    "message": "Stream ready",
                    "group_name": group_name,
                    "stream_assignment": stream_assignment,
                    "stream_url": stream_url,
                    "assignment_status": "stream_assigned"
                }), 200
            else:
                return jsonify({
                    "success": False,
                    "status": "waiting_for_stream",
                    "message": "Assigned to stream, waiting for URL resolution",
                    "group_name": group_name,
                    "stream_assignment": stream_assignment
                }), 202
        
        # Unknown status
        return jsonify({
            "success": False,
            "status": "unknown_status",
            "message": f"Unknown assignment status: {assignment_status}"
        }), 500
        
    except Exception as e:
        logger.error(f"Error in wait_for_assignment: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "status": "error",
            "message": str(e)
        }), 500

def resolve_stream_urls_for_group(group_id: str, group_name: str):
    """
    FIXED: Called when streaming starts - resolves stream URLs for all assigned clients
    Ensures all clients get properly formatted stream URLs
    """
    try:
        logger.info(f"🔄 Resolving stream URLs for all clients assigned to group {group_name}")
        
        state = get_state()
        all_clients = state.get_all_clients() if hasattr(state, 'get_all_clients') else state.clients
        
        # Find clients assigned to this group
        group_clients = []
        for client_id, client in all_clients.items():
            if client.get("group_id") == group_id and client.get("assignment_status") == "screen_assigned":
                group_clients.append((client_id, client))
        
        if not group_clients:
            logger.info(f"No clients assigned to group {group_name}")
            return
        
        # Get current active stream IDs
        group = get_group_from_docker(group_id)
        if not group:
            logger.error(f"Group {group_id} not found")
            return
        
        screen_count = group.get("screen_count", 2)
        active_stream_ids = generate_stream_ids(group_id, group_name, screen_count)
        
        # Update each client with resolved stream URL
        updated_count = 0
        for client_id, client in group_clients:
            screen_number = client.get("screen_number")
            if screen_number is not None:
                screen_stream_key = f"test{screen_number}"
                if screen_stream_key in active_stream_ids:
                    stream_id = active_stream_ids[screen_stream_key]
                    srt_ip = client.get("srt_ip", "127.0.0.1")
                    
                    # FIXED: Use the corrected build function
                    stream_url = build_stream_url_for_client(group, stream_id, group_name, srt_ip)
                    
                    # Update client
                    client["stream_url"] = stream_url
                    client["stream_version"] = int(time.time())
                    if hasattr(state, 'add_client'):
                        state.add_client(client_id, client)
                    else:
                        state.clients[client_id] = client
                    
                    logger.info(f"✅ Resolved URL for client {client_id} → screen {screen_number} → {stream_id}")
                    logger.info(f"   Full URL: {stream_url}")
                    updated_count += 1
        
        logger.info(f"🎯 Resolved stream URLs for {updated_count}/{len(group_clients)} clients in group {group_name}")
        
    except Exception as e:
        logger.error(f"Error resolving stream URLs for group {group_name}: {e}")
        import traceback
        traceback.print_exc()

# Legacy endpoints for backwards compatibility
def register_client_legacy():
    """Legacy endpoint - redirects to new register endpoint"""
    return register_client()

def wait_for_stream_legacy():
    """Legacy endpoint - redirects to new wait_for_assignment endpoint"""
    return wait_for_assignment()