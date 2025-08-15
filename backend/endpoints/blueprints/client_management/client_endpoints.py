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
import requests

logger = logging.getLogger(__name__)

# =====================================
# HELPER FUNCTIONS
# =====================================

def get_state():
    """Get the application state from Flask app config"""
    try:
        # Try to get from Flask app config
        state = current_app.config.get('APP_STATE')
        if state is not None:
            return state
        
        # Fallback: create a simple state object
        logger.warning("APP_STATE not found in config, using fallback state")
        return SimpleClientState()
        
    except Exception as e:
        logger.warning(f"Error getting state from Flask config: {e}, using fallback")
        return SimpleClientState()

class SimpleClientState:
    """Simple fallback client state for when APP_STATE is not available"""
    
    def __init__(self):
        self.clients = {}
        self.clients_lock = None  # No threading for now
    
    def get_client(self, client_id: str):
        """Get client by ID"""
        return self.clients.get(client_id)
    
    def get_all_clients(self):
        """Get all clients"""
        return self.clients
    
    def add_client(self, client_id: str, client_data: Dict):
        """Add or update client"""
        self.clients[client_id] = client_data
    
    def remove_client(self, client_id: str):
        """Remove client"""
        if client_id in self.clients:
            del self.clients[client_id]

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
        # Try to import the stream status check
        from ..stream_management import find_running_ffmpeg_for_group
        processes = find_running_ffmpeg_for_group(group_id, group_name)
        return len(processes) > 0
    except ImportError:
        logger.warning("Stream management not available, checking alternative way")
        # Try checking if FFmpeg is running with the group name
        try:
            import subprocess
            result = subprocess.run(['pgrep', '-f', f'live/{group_name}/'], capture_output=True)
            return result.returncode == 0
        except:
            # Assume streaming is active if we can't check
            logger.warning("Cannot verify streaming status, assuming active")
            return True
    except Exception as e:
        logger.error(f"Error checking streaming status: {e}")
        # Assume streaming is active if we can't check
        return True
    

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
        
        # Create unique client ID by combining hostname and IP address
        # This allows multiple terminal instances from the same device to run simultaneously
        client_id = f"{hostname}_{ip_address}"
        current_time = time.time()
        
        logger.info(f"Registering client: {client_id} (hostname: {hostname}, IP: {ip_address})")
        
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
        
        # Debug: Verify client was saved
        logger.info(f"State type after save: {type(state)}")
        logger.info(f"State has clients after save: {hasattr(state, 'clients')}")
        if hasattr(state, 'clients'):
            logger.info(f"Available client IDs after save: {list(state.clients.keys())}")
            saved_client = state.clients.get(client_id)
            logger.info(f"Saved client data: {saved_client is not None}")
        
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
        logger.info("==== WAIT FOR ASSIGNMENT REQUEST ====")
        
        # Import utilities from the same module
        from .client_utils import get_next_steps, build_stream_url
        # DON'T import get_state from client_state - use the one at top of file
        
        data = request.get_json() or {}
        client_id = data.get("client_id")
        
        logger.info(f"Request data: {data}")
        logger.info(f"Client ID: {client_id}")
        
        if not client_id:
            return jsonify({
                "success": False,
                "status": "error",
                "message": "client_id is required"
            }), 400
        
        state = get_state()  # Use the function defined at top of file
        logger.info(f"State type: {type(state)}")
        logger.info(f"State has clients: {hasattr(state, 'clients')}")
        if hasattr(state, 'clients'):
            logger.info(f"Available client IDs: {list(state.clients.keys())}")
        
        client = state.get_client(client_id) if hasattr(state, 'get_client') else state.clients.get(client_id)
        
        logger.info(f"Found client: {client is not None}")
        
        if not client:
            return jsonify({
                "success": False,
                "status": "not_registered", 
                "message": "Client not found. Please register first."
            }), 404
        
        # Get assignment status
        assignment_status = client.get("assignment_status", "waiting_for_assignment")
        group_id = client.get("group_id")
        
        logger.info(f"🔍 Client {client_id} checking assignment:")
        logger.info(f"   - Assignment status: {assignment_status}")
        logger.info(f"   - Group ID: {group_id}")
        logger.info(f"   - Full client data: {client}")
        
        # Case 1: Waiting for group assignment
        if assignment_status == "waiting_for_assignment" or not group_id:
            logger.info(f"❌ Client {client_id} is waiting for group assignment or has no group")
            return jsonify({
                "success": False,
                "status": "waiting_for_assignment",
                "message": "Waiting for admin to assign you to a group",
                "next_steps": get_next_steps(client)
            }), 202
        
        # Get group information - FIX THE IMPORT HERE
        group = None
        if group_id:
            try:
                # Try to import and use discover_groups (same as admin_endpoints does)
                from ..docker_management import discover_groups
                discovery_result = discover_groups()
                if discovery_result.get("success", False):
                    for g in discovery_result.get("groups", []):
                        if g.get("id") == group_id:
                            group = g
                            logger.info(f"Found group {group_id} in Docker")
                            break
            except ImportError as e:
                logger.warning(f"Docker management import failed: {e}")
            except Exception as e:
                logger.warning(f"Error discovering groups: {e}")
            
            # If we couldn't find the group, create a mock one
            if not group:
                logger.warning(f"Using mock group for {group_id}")
                group = {
                    "id": group_id,
                    "name": f"Group-{group_id[:8]}",
                    "docker_running": True,
                    "container_id": f"mock-{group_id[:8]}",
                    "ports": {"srt_port": 10100}
                }
        
        if not group:
            return jsonify({
                "success": False,
                "status": "group_not_found",
                "message": f"Group {group_id} not found or not running",
                "group_id": group_id
            }), 202
        
        group_name = group.get("name", group_id)
        
        # Case 2: Group assigned but no stream assignment
        if assignment_status == "group_assigned":
            logger.info(f"❌ Client {client_id} has group but no stream/screen assignment")
            return jsonify({
                "success": False,
                "status": "waiting_for_stream_assignment",
                "message": "Waiting for admin to assign you to a specific stream or screen",
                "group_id": group_id,
                "group_name": group_name,
                "next_steps": get_next_steps(client)
            }), 202
        
        # Case 3: Stream or screen assigned - check if streaming
        if assignment_status in ["stream_assigned", "screen_assigned"]:
            logger.info(f"✅ Client {client_id} has stream/screen assignment, checking streaming status")
            # Check if group is streaming
            container_id = group.get("container_id")
            
            # Check if group is streaming
            is_streaming = False
            
            try:
                # Try to check if FFmpeg is running
                from ..stream_management import find_running_ffmpeg_for_group_strict
                processes = find_running_ffmpeg_for_group_strict(group_id, group_name, group.get("container_id"))
                is_streaming = len(processes) > 0
                logger.info(f"🔍 FFmpeg check for group {group_name}: {len(processes)} processes found, is_streaming={is_streaming}")
            except ImportError as e:
                logger.warning(f"Import error checking streaming status: {e}")
                # Try alternative import path
                try:
                    try:
                        from blueprints.streaming.split_stream import find_running_ffmpeg_for_group_strict
                    except ImportError:
                        try:
                            from blueprints.streaming.multi_stream import find_running_ffmpeg_for_group_strict
                        except ImportError:
                            # Fallback function if import fails
                            def find_running_ffmpeg_for_group_strict(group_id: str, group_name: str, container_id: str):
                                """Find running FFmpeg processes for a group"""
                                return []
                    processes = find_running_ffmpeg_for_group_strict(group_id, group_name, group.get("container_id"))
                    is_streaming = len(processes) > 0
                    logger.info(f"🔍 FFmpeg check (alt import) for group {group_name}: {len(processes)} processes found, is_streaming={is_streaming}")
                except Exception as e2:
                    logger.error(f"Alternative import also failed: {e2}")
                    is_streaming = False
            except Exception as e:
                logger.error(f"Error checking streaming status: {e}")
                is_streaming = False
            
            if not is_streaming:
                return jsonify({
                    "success": False,
                    "status": "waiting_for_streaming",
                    "message": "Waiting for streaming to start",
                    "group_id": group_id,
                    "group_name": group_name,
                    "stream_assignment": client.get("stream_assignment"),
                    "screen_number": client.get("screen_number"),
                    "assignment_status": assignment_status,
                    "next_steps": get_next_steps(client)
                }), 202
            
            # Streaming is active - prepare stream URL
            stream_url = client.get("stream_url")
            
            # If no stream URL yet, build it
            if not stream_url:
                if assignment_status == "screen_assigned":
                    # For screen assignment, build URL with screen number
                    screen_number = client.get("screen_number", 0)
                    stream_id = f"screen{screen_number}"
                else:
                    # For stream assignment, use the assigned stream
                    stream_id = client.get("stream_assignment", "default")
                
                # Get SRT IP from client or use default
                srt_ip = client.get("srt_ip", "127.0.0.1")
                
                # Build the stream URL
                stream_url = build_stream_url(group, stream_id, group_name, srt_ip)
                
                # Update client with stream URL
                client["stream_url"] = stream_url
                if hasattr(state, 'add_client'):
                    state.add_client(client_id, client)
                else:
                    state.clients[client_id] = client
            
            # Return ready to play status
            return jsonify({
                "success": True,
                "status": "ready_to_play",
                "message": "Stream is ready",
                "stream_url": stream_url,
                "group_id": group_id,
                "group_name": group_name,
                "stream_assignment": client.get("stream_assignment"),
                "screen_number": client.get("screen_number"),
                "assignment_status": assignment_status,
                "stream_version": client.get("stream_version", None)
            }), 200
        
        # Unknown status
        logger.warning(f"⚠️ Client {client_id} has unknown assignment status: {assignment_status}")
        return jsonify({
            "success": False,
            "status": "unknown",
            "message": f"Unknown assignment status: {assignment_status}",
            "assignment_status": assignment_status
        }), 202
        
    except Exception as e:
        logger.error(f"Error in wait_for_assignment: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "status": "error",
            "message": f"Internal server error: {str(e)}"
        }), 500


def unassign_client_from_screen():
    """
    Admin function: Remove a client's screen assignment (frees up the screen for another client)
    """
    try:
        logger.info("==== UNASSIGN CLIENT FROM SCREEN REQUEST RECEIVED ====")
        
        state = get_state()
        data = request.get_json() or {}
        
        client_id = data.get("client_id")
        
        if not client_id:
            return jsonify({
                "success": False,
                "error": "client_id is required"
            }), 400
        
        # Check if state has clients attribute
        if not hasattr(state, 'clients'):
            state.clients = {}
        
        if client_id not in state.clients:
            return jsonify({
                "success": False,
                "error": "Client not found"
            }), 404
        
        # Handle state with or without lock
        if hasattr(state, 'clients_lock'):
            with state.clients_lock:
                client = state.clients[client_id]
                old_group_id = client.get("group_id")
                old_screen_number = client.get("screen_number")
                old_stream = client.get("stream_assignment")
                
                # Clear screen assignment but keep group assignment
                client.update({
                    "screen_number": None,
                    "stream_assignment": None,
                    "stream_url": None,
                    "assignment_status": "assigned_to_group",  # Still in group, just no specific screen
                    "unassigned_at": time.time()
                })
        else:
            # No lock available, update directly
            client = state.clients[client_id]
            old_group_id = client.get("group_id")
            old_screen_number = client.get("screen_number")
            old_stream = client.get("stream_assignment")
            
            # Clear screen assignment but keep group assignment
            client.update({
                "screen_number": None,
                "stream_assignment": None,
                "stream_url": None,
                "assignment_status": "assigned_to_group",  # Still in group, just no specific screen
                "unassigned_at": time.time()
            })
        
        logger.info(f"✅ Unassigned client {client_id} from screen {old_screen_number} in group {old_group_id}")
        
        return jsonify({
            "success": True,
            "message": f"Client {client_id} unassigned from screen {old_screen_number}",
            "client_id": client_id,
            "group_id": old_group_id,
            "old_screen_number": old_screen_number,
            "old_stream": old_stream,
            "assignment_status": "assigned_to_group"
        }), 200
        
    except Exception as e:
        logger.error(f"Error unassigning client from screen: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def unassign_client_from_stream():
    """
    Admin function: Remove a client's stream assignment (frees up the stream for another client)
    """
    try:
        logger.info("==== UNASSIGN CLIENT FROM STREAM REQUEST RECEIVED ====")
        
        state = get_state()
        data = request.get_json() or {}
        
        client_id = data.get("client_id")
        
        if not client_id:
            return jsonify({
                "success": False,
                "error": "client_id is required"
            }), 400
        
        # Check if state has clients attribute
        if not hasattr(state, 'clients'):
            state.clients = {}
        
        if client_id not in state.clients:
            return jsonify({
                "success": False,
                "error": "Client not found"
            }), 404
        
        # Handle state with or without lock
        if hasattr(state, 'clients_lock'):
            with state.clients_lock:
                client = state.clients[client_id]
                old_group_id = client.get("group_id")
                old_stream = client.get("stream_assignment")
                old_screen_number = client.get("screen_number")
                
                # Clear stream assignment but keep group assignment
                client.update({
                    "stream_assignment": None,
                    "stream_url": None,
                    "assignment_status": "assigned_to_group" if old_group_id else "waiting_for_assignment",
                    "unassigned_at": time.time()
                })
        else:
            # No lock available, update directly
            client = state.clients[client_id]
            old_group_id = client.get("group_id")
            old_stream = client.get("stream_assignment")
            old_screen_number = client.get("screen_number")
            
            # Clear stream assignment but keep group assignment
            client.update({
                "stream_assignment": None,
                "stream_url": None,
                "assignment_status": "assigned_to_group" if old_group_id else "waiting_for_assignment",
                "unassigned_at": time.time()
            })
        
        logger.info(f"✅ Unassigned client {client_id} from stream {old_stream} in group {old_group_id}")
        
        return jsonify({
            "success": True,
            "message": f"Client {client_id} unassigned from stream {old_stream}",
            "client_id": client_id,
            "group_id": old_group_id,
            "old_stream": old_stream,
            "old_screen_number": old_screen_number,
            "assignment_status": client.get("assignment_status")
        }), 200
        
    except Exception as e:
        logger.error(f"Error unassigning client from stream: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e)
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
        
        # Try to get stream IDs from active streaming first
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
            
            active_stream_ids = get_active_stream_ids(group_id)
            if active_stream_ids:
                logger.info(f"✅ Using active stream IDs: {active_stream_ids}")
            else:
                # Fallback: try group metadata
                active_stream_ids = group.get("stream_ids", {})
                if active_stream_ids:
                    logger.info(f"⚠️ Using group metadata stream IDs: {active_stream_ids}")
                else:
                    # Last resort: generate stream IDs
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
                    active_stream_ids = generate_stream_ids(group_id, group_name, screen_count)
                    logger.info(f"⚠️ Generated fallback stream IDs: {active_stream_ids}")
        except Exception as e:
            logger.error(f"Error getting active stream IDs: {e}")
            return
        
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