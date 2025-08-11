"""
Client Registration and Polling Endpoints
Core client-facing endpoints for registration and status polling
"""

import time
import logging
import traceback
from typing import Dict, List, Any, Optional  # ADD THIS LINE
from flask import request, jsonify


from .client_state import get_state
from .client_validators import validate_client_registration
from .client_utils import (
    get_group_from_docker, 
    check_group_streaming_status, 
    get_next_steps,
    build_stream_url
)
from blueprints.stream_management import (
    find_running_ffmpeg_for_group_strict, 
    generate_stream_ids
)


logger = logging.getLogger(__name__)


def get_group_from_docker(group_id: str) -> Optional[Dict[str, Any]]:
    """
    Get group information from Docker discovery
    Clean import strategy - imports only when needed
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

def check_streaming_status_for_group(group_id: str, group_name: str, container_id: str = None) -> bool:
    """
    Check if streaming is active for a group
    Clean import strategy with fallback
    """
    try:
        from blueprints.stream_management import find_running_ffmpeg_for_group_strict
        
        running_processes = find_running_ffmpeg_for_group_strict(group_id, group_name, container_id)
        is_streaming = len(running_processes) > 0
        
        logger.debug(f"Group {group_name} streaming status: {is_streaming} ({len(running_processes)} processes)")
        return is_streaming
        
    except ImportError:
        logger.warning("Stream management not available, assuming streaming is inactive")
        return False  # Conservative fallback
    except Exception as e:
        logger.error(f"Error checking streaming status for group {group_name}: {e}")
        return False

def get_active_stream_ids_for_group(group_id: str, group_name: str, screen_count: int) -> Dict[str, str]:
    """
    Get current active stream IDs for a group
    Clean import strategy with graceful fallback
    """
    try:
        from blueprints.stream_management import generate_stream_ids
        
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
        
    except ImportError:
        logger.warning("Stream management not available, cannot get active stream IDs")
        return {}
    except Exception as e:
        logger.error(f"Error getting active stream IDs: {e}")
        return {}

def build_stream_url_for_client(group: Dict[str, Any], stream_id: str, group_name: str, srt_ip: str = "127.0.0.1") -> str:
    """
    Build SRT stream URL for a client
    Self-contained function with no external imports needed
    """
    try:
        ports = group.get("ports", {})
        srt_port = ports.get("srt_port")
        
        if not srt_port:
            logger.error(f"No SRT port found for group {group_name}. Group ports: {ports}")
            # Use fallback port but log the issue
            srt_port = 10080
            logger.warning(f"Using fallback SRT port {srt_port} for group {group_name}")
        
        stream_path = f"live/{group_name}/{stream_id}"
        return f"srt://{srt_ip}:{srt_port}?streamid=#!::r={stream_path},m=request,latency=5000000"
        
    except Exception as e:
        logger.error(f"Error building stream URL: {e}")
        return ""

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
        existing_client = state.get_client(client_id)
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
            "stream_assignment": existing_client.get("stream_assignment") if existing_client else None,
            "stream_url": existing_client.get("stream_url") if existing_client else None,
            "screen_number": existing_client.get("screen_number") if existing_client else None,
            "assigned_at": existing_client.get("assigned_at") if existing_client else None
        }
        
        # Update assignment status based on current assignments
        if client_data["group_id"]:
            if client_data["screen_number"] is not None:
                client_data["assignment_status"] = "screen_assigned"
            elif client_data["stream_assignment"]:
                client_data["assignment_status"] = "stream_assigned"
            else:
                client_data["assignment_status"] = "group_assigned"
        
        # Save client - FIXED: Use the correct method name
        state.add_or_update_client(client_id, client_data)
        
        logger.info(f"Client {action}: {client_id} (status: {client_data['assignment_status']})")
        
        # Prepare response
        response_data = {
            "success": True,
            "message": f"Client {action} successfully",
            "client_id": client_id,
            "action": action,
            "status": client_data["assignment_status"],
            "server_time": current_time,
            # FIXED: Only pass client_data (one argument)
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
        
        if not state.remove_client(client_id):
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
    Client endpoint: Wait for assignment and get stream URL when streaming is active
    Enhanced version with dynamic stream URL resolution
    """
    try:
        data = request.get_json() or {}
        client_id = data.get("client_id")
        
        if not client_id:
            return jsonify({
                "success": False,
                "error": "client_id is required"
            }), 400
        
        state = get_state()
        client = state.get_client(client_id) if hasattr(state, 'get_client') else state.clients.get(client_id)
        
        if not client:
            return jsonify({
                "success": False,
                "status": "not_registered",
                "message": "Client not registered"
            }), 404
        
        assignment_status = client.get("assignment_status", "waiting_for_assignment")
        group_id = client.get("group_id")
        
        # Handle different assignment statuses
        if assignment_status == "waiting_for_assignment":
            return jsonify({
                "success": True,
                "status": "waiting_for_group_assignment",
                "message": "Waiting for admin to assign client to a group"
            }), 200
        
        elif assignment_status in ["group_assigned", "stream_assigned", "screen_assigned"]:
            if not group_id:
                return jsonify({
                    "success": False,
                    "status": "error",
                    "message": "Client has assignment status but no group_id"
                }), 500
            
            # Get group info using our wrapper function
            group = get_group_from_docker(group_id)
            if not group:
                return jsonify({
                    "success": False,
                    "status": "group_not_found",
                    "message": f"Assigned group {group_id} not found"
                }), 404
            
            group_name = group.get("name", group_id)
            
            # Check if streaming is active using our wrapper function
            container_id = group.get("container_id")
            is_streaming = check_streaming_status_for_group(group_id, group_name, container_id)
            
            if not is_streaming:
                return jsonify({
                    "success": True,
                    "status": "waiting_for_streaming",
                    "message": f"Assigned to {group_name}. Waiting for streaming to start.",
                    "group_name": group_name,
                    "stream_assignment": client.get("stream_assignment"),
                    "screen_number": client.get("screen_number")
                }), 200
            
            # STREAMING IS ACTIVE - RESOLVE STREAM URL DYNAMICALLY
            screen_number = client.get("screen_number")
            srt_ip = client.get("srt_ip", "127.0.0.1")
            
            if screen_number is not None:
                # Client is assigned to a specific screen - get individual stream URL
                screen_count = group.get("screen_count", 2)
                
                # Get CURRENT active stream IDs using our wrapper function
                active_stream_ids = get_active_stream_ids_for_group(group_id, group_name, screen_count)
                
                if not active_stream_ids:
                    return jsonify({
                        "success": False,
                        "status": "stream_not_ready",
                        "message": "Streaming is starting but stream IDs not ready yet. Please try again in a moment."
                    }), 503
                
                # Get the stream ID for this specific screen
                screen_stream_key = f"test{screen_number}"
                if screen_stream_key in active_stream_ids:
                    stream_id = active_stream_ids[screen_stream_key]
                    stream_url = build_stream_url_for_client(group, stream_id, group_name, srt_ip)
                    
                    if not stream_url:
                        return jsonify({
                            "success": False,
                            "status": "url_generation_failed",
                            "message": "Failed to generate stream URL"
                        }), 500
                    
                    # Update client with resolved stream URL
                    if hasattr(state, 'clients_lock'):
                        with state.clients_lock:
                            client["stream_url"] = stream_url
                            client["stream_version"] = int(time.time())
                            if hasattr(state, 'add_client'):
                                state.add_client(client_id, client)
                            else:
                                state.clients[client_id] = client
                    else:
                        client["stream_url"] = stream_url
                        client["stream_version"] = int(time.time())
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
                        "stream_version": client["stream_version"],
                        "assignment_status": "screen_assigned"
                    }), 200
                else:
                    return jsonify({
                        "success": False,
                        "status": "stream_not_available",
                        "message": f"Stream for screen {screen_number} not available in current streaming session",
                        "available_streams": list(active_stream_ids.keys())
                    }), 404
            else:
                # Handle regular stream assignment (not screen-specific)
                # This would be for your existing stream assignment logic
                stream_assignment = client.get("stream_assignment")
                if stream_assignment:
                    # Use existing stream URL if available
                    stream_url = client.get("stream_url")
                    if stream_url:
                        return jsonify({
                            "success": True,
                            "status": "ready_to_play",
                            "message": f"Stream ready",
                            "group_name": group_name,
                            "stream_assignment": stream_assignment,
                            "stream_url": stream_url,
                            "assignment_status": "stream_assigned"
                        }), 200
                
                return jsonify({
                    "success": True,
                    "status": "waiting_for_stream_assignment",
                    "message": f"Assigned to group {group_name} but no specific stream assigned",
                    "group_name": group_name
                }), 200
        
        return jsonify({
            "success": False,
            "status": "unknown_status",
            "message": f"Unknown assignment status: {assignment_status}"
        }), 500
        
    except Exception as e:
        logger.error(f"Error in wait_for_assignment: {e}")
        return jsonify({
            "success": False,
            "status": "error",
            "message": str(e)
        }), 500
    
# Legacy endpoints for backwards compatibility
def register_client_legacy():
    """Legacy endpoint - redirects to new register endpoint"""
    return register_client()

def resolve_stream_urls_for_group(group_id: str, group_name: str):
    """
    Called when streaming starts - resolves stream URLs for all assigned clients
    """
    try:
        logger.info(f"🔄 Resolving stream URLs for all clients assigned to group {group_name}")
        
        state = get_state()
        all_clients = state.get_all_clients()
        
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
        for client_id, client in group_clients:
            screen_number = client.get("screen_number")
            if screen_number is not None:
                screen_stream_key = f"test{screen_number}"
                if screen_stream_key in active_stream_ids:
                    stream_id = active_stream_ids[screen_stream_key]
                    srt_ip = client.get("srt_ip", "127.0.0.1")
                    stream_url = build_stream_url(group, stream_id, group_name, srt_ip)
                    
                    # Update client
                    client["stream_url"] = stream_url
                    client["stream_version"] = int(time.time())
                    state.add_client(client_id, client)
                    
                    logger.info(f"✅ Resolved URL for client {client_id} → screen {screen_number} → {stream_id}")
        
        logger.info(f"🎯 Resolved stream URLs for {len(group_clients)} clients in group {group_name}")
        
    except Exception as e:
        logger.error(f"Error resolving stream URLs for group {group_name}: {e}")

def wait_for_stream_legacy():
    """Legacy endpoint - redirects to new wait_for_assignment endpoint"""
    return wait_for_assignment()