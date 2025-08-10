"""
Client Registration and Polling Endpoints
Core client-facing endpoints for registration and status polling
"""

import time
import logging
import traceback
from flask import request, jsonify

from .client_state import get_state
from .client_validators import validate_client_registration
from .client_utils import (
    get_group_from_docker, 
    check_group_streaming_status, 
    get_next_steps
)

logger = logging.getLogger(__name__)

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
        
        # Save client
        state.add_client(client_id, client_data)
        
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
    Client polls this endpoint to wait for assignments and streaming
    
    Expected payload:
    {
        "client_id": "display-001"  # or "hostname"
    }
    """
    try:
        state = get_state()
        data = request.get_json() or {}
        
        client_id = data.get("client_id") or data.get("hostname")
        if not client_id:
            return jsonify({
                "status": "error",
                "error": "client_id or hostname is required"
            }), 400
        
        # Update client heartbeat
        current_time = time.time()
        client = state.get_client(client_id)
        
        if not client:
            return jsonify({
                "status": "not_registered",
                "action": "register_first",
                "message": "Client not registered, please register first",
                "registration_endpoint": "/api/clients/register"
            }), 404
        
        # Update last seen
        client["last_seen"] = current_time
        client["status"] = "active"
        state.add_client(client_id, client)
        
        # Check assignment status
        assignment_status = client.get("assignment_status", "waiting_for_assignment")
        
        if assignment_status == "waiting_for_assignment":
            return jsonify({
                "status": "waiting_for_group_assignment",
                "message": "Waiting for admin to assign client to a group",
                "instructions": "Admin needs to assign client to a group using the web interface"
            }), 200
        
        group_id = client.get("group_id")
        if not group_id:
            return jsonify({
                "status": "assignment_error",
                "message": "Client has assignment status but no group_id"
            }), 500
        
        # Verify group still exists
        group = get_group_from_docker(group_id)
        if not group:
            # Clear invalid group assignment
            client.update({
                "group_id": None,
                "stream_assignment": None,
                "stream_url": None,
                "screen_number": None,
                "assignment_status": "waiting_for_assignment"
            })
            state.add_client(client_id, client)
            
            return jsonify({
                "status": "group_not_found",
                "group_id": group_id,
                "message": "Assigned group no longer exists. Client unassigned.",
                "action": "wait_for_reassignment"
            }), 404
        
        if not group.get("docker_running", False):
            return jsonify({
                "status": "group_not_running",
                "group_id": group_id,
                "group_name": group.get("name"),
                "message": "Group's Docker container is not running. Contact admin to start container."
            }), 503
        
        # Check specific assignment types
        if assignment_status == "group_assigned":
            return jsonify({
                "status": "waiting_for_stream_assignment",
                "group_id": group_id,
                "group_name": group.get("name"),
                "message": "Assigned to group but waiting for specific stream/screen assignment"
            }), 200
        
        # Check if streaming is active
        group_name = group.get("name", group_id)
        streaming_active = check_group_streaming_status(group_id, group_name)
        
        if not streaming_active:
            return jsonify({
                "status": "waiting_for_streaming",
                "group_id": group_id,
                "group_name": group_name,
                "assignment_status": assignment_status,
                "message": "Waiting for streaming to start. Admin needs to start streaming."
            }), 200
        
        # Stream is ready!
        stream_url = client.get("stream_url")
        if stream_url:
            return jsonify({
                "status": "ready_to_play",
                "group_id": group_id,
                "group_name": group_name,
                "assignment_status": assignment_status,
                "stream_assignment": client.get("stream_assignment"),
                "screen_number": client.get("screen_number"),
                "stream_url": stream_url,
                "message": "Stream ready to play!"
            }), 200
        else:
            return jsonify({
                "status": "stream_url_missing",
                "message": "Assignment exists but stream URL not generated. Contact admin."
            }), 500
        
    except Exception as e:
        logger.error(f"Error in wait_for_assignment: {e}")
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

# Legacy endpoints for backwards compatibility
def register_client_legacy():
    """Legacy endpoint - redirects to new register endpoint"""
    return register_client()

def wait_for_stream_legacy():
    """Legacy endpoint - redirects to new wait_for_assignment endpoint"""
    return wait_for_assignment()