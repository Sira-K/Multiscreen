"""
Admin Assignment Endpoints
Administrative functions for assigning clients to groups and streams
"""

import time
import logging
import traceback
from flask import request, jsonify

from .client_state import get_state
from .client_validators import (
    validate_group_assignment,
    validate_stream_assignment,
    validate_screen_assignment,
    validate_auto_assignment,
    validate_unassignment
)
from .client_utils import (
    get_group_from_docker,
    get_persistent_streams_for_group,
    build_stream_url,
    validate_screen_assignment as util_validate_screen,
    check_screen_availability
)

logger = logging.getLogger(__name__)

def assign_client_to_group():
    """
    Admin function: Assign a client to a specific group
    
    Expected payload:
    {
        "client_id": "display-001",
        "group_id": "group-123"  # or null to unassign
    }
    """
    try:
        logger.info("==== ASSIGN CLIENT TO GROUP REQUEST ====")
        
        state = get_state()
        data = request.get_json()
        
        # Validate input
        is_valid, error_msg, cleaned_data = validate_group_assignment(data)
        if not is_valid:
            return jsonify({
                "success": False,
                "error": error_msg
            }), 400
        
        client_id = cleaned_data["client_id"]
        group_id = cleaned_data["group_id"]
        
        # Validate client exists
        client = state.get_client(client_id)
        if not client:
            return jsonify({
                "success": False,
                "error": f"Client '{client_id}' not found"
            }), 404
        
        # Validate group exists (if group_id is provided)
        if group_id:
            group = get_group_from_docker(group_id)
            if not group:
                return jsonify({
                    "success": False,
                    "error": f"Group '{group_id}' not found"
                }), 404
        
        old_group_id = client.get("group_id")
        
        # Update client's group assignment
        if group_id:
            client.update({
                "group_id": group_id,
                "assigned_at": time.time(),
                "assignment_status": "group_assigned",
                # Clear stream/screen assignments when changing groups
                "stream_assignment": None,
                "stream_url": None,
                "screen_number": None
            })
            logger.info(f"Assigned client {client_id} to group {group_id}")
        else:
            # Unassign from group
            client.update({
                "group_id": None,
                "assigned_at": None,
                "assignment_status": "waiting_for_assignment",
                "stream_assignment": None,
                "stream_url": None,
                "screen_number": None
            })
            logger.info(f"Unassigned client {client_id} from group")
        
        state.add_client(client_id, client)
        
        return jsonify({
            "success": True,
            "message": "Client assignment updated successfully",
            "client_id": client_id,
            "old_group_id": old_group_id,
            "new_group_id": group_id,
            "assignment_status": client["assignment_status"]
        }), 200
        
    except Exception as e:
        logger.error(f"Error assigning client to group: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

def assign_client_to_stream():
    """
    Admin function: Assign a client to a specific stream
    
    Expected payload:
    {
        "client_id": "display-001",
        "group_id": "group-123",  # Optional if client already in group
        "stream_name": "test0",   # Optional, will auto-assign if not provided
        "srt_ip": "192.168.1.100" # Optional, defaults to 127.0.0.1
    }
    """
    try:
        logger.info("==== ASSIGN CLIENT TO STREAM REQUEST ====")
        
        state = get_state()
        data = request.get_json() or {}
        
        # Validate input
        is_valid, error_msg, cleaned_data = validate_stream_assignment(data)
        if not is_valid:
            return jsonify({
                "success": False,
                "error": error_msg
            }), 400
        
        client_id = cleaned_data["client_id"]
        group_id = cleaned_data["group_id"]
        stream_name = cleaned_data["stream_name"]
        srt_ip = cleaned_data["srt_ip"]
        
        # Get client
        client = state.get_client(client_id)
        if not client:
            return jsonify({
                "success": False,
                "error": f"Client {client_id} not registered"
            }), 404
        
        # Get group_id from client if not provided
        if not group_id:
            group_id = client.get("group_id")
        
        if not group_id:
            return jsonify({
                "success": False,
                "error": "Client not assigned to any group and no group_id provided"
            }), 400
        
        # Verify group exists
        group = get_group_from_docker(group_id)
        if not group:
            return jsonify({
                "success": False,
                "error": f"Group {group_id} not found"
            }), 404
        
        group_name = group.get("name", group_id)
        
        # Auto-assign stream if not specified
        if not stream_name:
            persistent_streams = get_persistent_streams_for_group(group_id, group_name, 4)
            
            # Find unassigned streams
            all_clients = state.get_all_clients()
            assigned_streams = set()
            for other_client in all_clients.values():
                if (other_client.get("group_id") == group_id and 
                    other_client.get("stream_assignment") and
                    other_client["client_id"] != client_id):
                    assigned_streams.add(other_client["stream_assignment"])
            
            # Prefer split streams over full stream
            available_streams = [name for name in persistent_streams.keys() 
                               if name.startswith("test") and len(name) > 4]
            if not available_streams:
                available_streams = ["test"]
            
            # Find first unassigned stream
            for stream in available_streams:
                if stream not in assigned_streams:
                    stream_name = stream
                    break
            
            if not stream_name:
                # All streams assigned, use round-robin
                stream_name = available_streams[len(assigned_streams) % len(available_streams)]
        
        # Build stream URL
        persistent_streams = get_persistent_streams_for_group(group_id, group_name, 4)
        if stream_name not in persistent_streams:
            return jsonify({
                "success": False,
                "error": f"Stream {stream_name} not available in group",
                "available_streams": list(persistent_streams.keys())
            }), 400
        
        stream_id = persistent_streams[stream_name]
        stream_url = build_stream_url(group, stream_id, group_name, srt_ip)
        
        # Update client assignment
        client.update({
            "group_id": group_id,
            "stream_assignment": stream_name,
            "stream_url": stream_url,
            "assigned_at": time.time(),
            "assignment_status": "stream_assigned",
            "screen_number": None  # Clear screen assignment if using streams
        })
        state.add_client(client_id, client)
        
        logger.info(f"Assigned client {client_id} to stream {stream_name} in group {group_id}")
        
        return jsonify({
            "success": True,
            "message": "Stream assigned successfully",
            "client_id": client_id,
            "group_id": group_id,
            "group_name": group_name,
            "stream_name": stream_name,
            "stream_url": stream_url,
            "assignment_status": "stream_assigned"
        }), 200
        
    except Exception as e:
        logger.error(f"Error assigning client to stream: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

def assign_client_to_screen():
    """
    Admin function: Assign a client to a specific screen (1 client per screen)
    
    Expected payload:
    {
        "client_id": "display-001",
        "group_id": "group-123",
        "screen_number": 0,
        "srt_ip": "192.168.1.100"
    }
    """
    try:
        logger.info("==== ASSIGN CLIENT TO SCREEN REQUEST ====")
        
        state = get_state()
        data = request.get_json() or {}
        
        # Validate input
        is_valid, error_msg, cleaned_data = validate_screen_assignment(data)
        if not is_valid:
            return jsonify({
                "success": False,
                "error": error_msg
            }), 400
        
        client_id = cleaned_data["client_id"]
        group_id = cleaned_data["group_id"]
        screen_number = cleaned_data["screen_number"]
        srt_ip = cleaned_data["srt_ip"]
        
        # Validate client exists
        client = state.get_client(client_id)
        if not client:
            return jsonify({
                "success": False,
                "error": f"Client {client_id} not registered"
            }), 404
        
        # Verify group exists
        group = get_group_from_docker(group_id)
        if not group:
            return jsonify({
                "success": False,
                "error": f"Group {group_id} not found"
            }), 404
        
        group_name = group.get("name", group_id)
        
        # Validate screen number against group
        is_valid_screen, screen_error = util_validate_screen(screen_number, group)
        if not is_valid_screen:
            return jsonify({
                "success": False,
                "error": screen_error
            }), 400
        
        # Check if another client is already assigned to this screen
        all_clients = state.get_all_clients()
        screen_available, conflict_info = check_screen_availability(client_id, group_id, screen_number, all_clients)
        
        if not screen_available:
            return jsonify({
                "success": False,
                "error": f"Screen {screen_number} is already assigned to client {conflict_info['client_id']}",
                "current_assignment": conflict_info
            }), 409
        
        # Build stream URL for the specific screen
        screen_count = group.get("screen_count", 4)
        persistent_streams = get_persistent_streams_for_group(group_id, group_name, screen_count)

        # Use the main combined stream for all screen assignments
        main_stream_key = "test"  # ✅ CORRECT

        if main_stream_key not in persistent_streams:
            return jsonify({
                "success": False,
                "error": f"Main stream not available. Start streaming first.",
                "available_streams": list(persistent_streams.keys())
            }), 400

        stream_id = persistent_streams[main_stream_key]
        stream_url = build_stream_url(group, stream_id, group_name, srt_ip)
        
        # Update client assignment
        client.update({
            "group_id": group_id,
            "screen_number": screen_number,
            "stream_assignment": f"screen{screen_number}",
            "stream_url": stream_url,
            "assigned_at": time.time(),
            "assignment_status": "screen_assigned"
        })
        state.add_client(client_id, client)
        
        logger.info(f"Assigned client {client_id} to screen {screen_number} in group {group_name}")
        
        return jsonify({
            "success": True,
            "message": f"Client assigned to screen {screen_number}",
            "client_id": client_id,
            "group_id": group_id,
            "group_name": group_name,
            "screen_number": screen_number,
            "stream_assignment": f"screen{screen_number}",
            "stream_url": stream_url,
            "assignment_status": "screen_assigned"
        }), 200
        
    except Exception as e:
        logger.error(f"Error assigning client to screen: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

def auto_assign_group_clients():
    """
    Admin function: Auto-assign all clients in a group to different streams
    
    Expected payload:
    {
        "group_id": "group-123",
        "assignment_type": "streams",  # or "screens"
        "srt_ip": "192.168.1.100"
    }
    """
    try:
        logger.info("==== AUTO ASSIGN GROUP CLIENTS REQUEST ====")
        
        state = get_state()
        data = request.get_json() or {}
        
        # Validate input
        is_valid, error_msg, cleaned_data = validate_auto_assignment(data)
        if not is_valid:
            return jsonify({
                "success": False,
                "error": error_msg
            }), 400
        
        group_id = cleaned_data["group_id"]
        assignment_type = cleaned_data["assignment_type"]
        srt_ip = cleaned_data["srt_ip"]
        
        # Verify group exists
        group = get_group_from_docker(group_id)
        if not group:
            return jsonify({
                "success": False,
                "error": f"Group {group_id} not found"
            }), 404
        
        group_name = group.get("name", group_id)
        screen_count = group.get("screen_count", 4)
        
        # Get clients in this group
        group_clients = state.get_active_clients(group_id)
        
        if not group_clients:
            return jsonify({
                "success": True,
                "message": f"No active clients assigned to group {group_id}",
                "assignments": []
            }), 200
        
        assignments = []
        
        if assignment_type == "screens":
            # Assign 1 client per screen
            available_screens = list(range(screen_count))
            
            for i, client in enumerate(group_clients[:screen_count]):  # Limit to screen count
                screen_number = available_screens[i]
                
                # Build screen stream URL
                persistent_streams = get_persistent_streams_for_group(group_id, group_name, screen_count)
                screen_stream_key = f"test{screen_number}"
                
                if screen_stream_key in persistent_streams:
                    stream_id = persistent_streams[screen_stream_key]
                    stream_url = build_stream_url(group, stream_id, group_name, srt_ip)
                    
                    # Update client
                    client.update({
                        "screen_number": screen_number,
                        "stream_assignment": f"screen{screen_number}",
                        "stream_url": stream_url,
                        "assigned_at": time.time(),
                        "assignment_status": "screen_assigned"
                    })
                    state.add_client(client["client_id"], client)
                    
                    assignments.append({
                        "client_id": client["client_id"],
                        "hostname": client.get("hostname", "unknown"),
                        "display_name": client.get("display_name", "unknown"),
                        "assignment_type": "screen",
                        "screen_number": screen_number,
                        "stream_assignment": f"screen{screen_number}",
                        "stream_url": stream_url
                    })
        else:
            # Assign to regular streams (multiple clients can share)
            persistent_streams = get_persistent_streams_for_group(group_id, group_name, len(group_clients))
            
            stream_names = [name for name in persistent_streams.keys() 
                           if name.startswith("test") and len(name) > 4]
            if not stream_names:
                stream_names = ["test"]
            
            for i, client in enumerate(group_clients):
                stream_name = stream_names[i % len(stream_names)]  # Round-robin
                stream_id = persistent_streams[stream_name]
                stream_url = build_stream_url(group, stream_id, group_name, srt_ip)
                
                # Update client
                client.update({
                    "stream_assignment": stream_name,
                    "stream_url": stream_url,
                    "assigned_at": time.time(),
                    "assignment_status": "stream_assigned",
                    "screen_number": None  # Clear screen assignment
                })
                state.add_client(client["client_id"], client)
                
                assignments.append({
                    "client_id": client["client_id"],
                    "hostname": client.get("hostname", "unknown"),
                    "display_name": client.get("display_name", "unknown"),
                    "assignment_type": "stream",
                    "stream_name": stream_name,
                    "stream_url": stream_url
                })
        
        logger.info(f"Auto-assigned {len(assignments)} clients in group {group_id} using {assignment_type}")
        
        return jsonify({
            "success": True,
            "message": f"Auto-assigned {len(assignments)} clients in group {group_id}",
            "group_id": group_id,
            "group_name": group_name,
            "assignment_type": assignment_type,
            "assignments": assignments
        }), 200
        
    except Exception as e:
        logger.error(f"Error in auto-assign group clients: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

def unassign_client():
    """
    Admin function: Unassign a client from its group/stream/screen
    
    Expected payload:
    {
        "client_id": "display-001",
        "unassign_type": "all"  # "all", "stream", or "screen"
    }
    """
    try:
        logger.info("==== UNASSIGN CLIENT REQUEST ====")
        
        state = get_state()
        data = request.get_json() or {}
        
        # Validate input
        is_valid, error_msg, cleaned_data = validate_unassignment(data)
        if not is_valid:
            return jsonify({
                "success": False,
                "error": error_msg
            }), 400
        
        client_id = cleaned_data["client_id"]
        unassign_type = cleaned_data["unassign_type"]
        
        client = state.get_client(client_id)
        if not client:
            return jsonify({
                "success": False,
                "error": "Client not found"
            }), 404
        
        old_assignments = {
            "group_id": client.get("group_id"),
            "stream_assignment": client.get("stream_assignment"),
            "screen_number": client.get("screen_number"),
            "assignment_status": client.get("assignment_status")
        }
        
        if unassign_type == "all":
            # Clear all assignments
            client.update({
                "group_id": None,
                "stream_assignment": None,
                "stream_url": None,
                "screen_number": None,
                "assignment_status": "waiting_for_assignment",
                "assigned_at": None,
                "unassigned_at": time.time()
            })
        elif unassign_type == "stream":
            # Clear stream assignment but keep group
            client.update({
                "stream_assignment": None,
                "stream_url": None,
                "assignment_status": "group_assigned" if client.get("group_id") else "waiting_for_assignment",
                "unassigned_at": time.time()
            })
        elif unassign_type == "screen":
            # Clear screen assignment but keep group
            client.update({
                "screen_number": None,
                "stream_assignment": None,
                "stream_url": None,
                "assignment_status": "group_assigned" if client.get("group_id") else "waiting_for_assignment",
                "unassigned_at": time.time()
            })
        
        state.add_client(client_id, client)
        
        logger.info(f"Unassigned client {client_id} ({unassign_type})")
        
        return jsonify({
            "success": True,
            "message": f"Client {client_id} unassigned successfully ({unassign_type})",
            "client_id": client_id,
            "unassign_type": unassign_type,
            "old_assignments": old_assignments,
            "new_assignment_status": client["assignment_status"]
        }), 200
        
    except Exception as e:
        logger.error(f"Error unassigning client: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

def remove_client():
    """
    Admin function: Remove a client from the system completely
    
    Expected payload:
    {
        "client_id": "display-001"
    }
    """
    try:
        logger.info("==== REMOVE CLIENT REQUEST ====")
        
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No JSON data provided"
            }), 400
            
        client_id = data.get("client_id")
        if not client_id:
            return jsonify({
                "success": False,
                "error": "client_id is required"
            }), 400
        
        state = get_state()
        client = state.get_client(client_id)
        
        if not client:
            return jsonify({
                "success": False,
                "error": f"Client '{client_id}' not found"
            }), 404
        
        client_name = client.get('display_name') or client.get('hostname') or client_id
        
        # Remove client
        if state.remove_client(client_id):
            logger.info(f"Successfully removed client: {client_name} ({client_id})")
            
            return jsonify({
                "success": True,
                "message": f"Client '{client_name}' removed successfully",
                "removed_client_id": client_id,
                "removed_client_name": client_name
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": f"Failed to remove client {client_id}"
            }), 404
        
    except Exception as e:
        logger.error(f"Error removing client: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500