# backend/endpoints/blueprints/client_management/info_endpoints.py
"""
Client Information Endpoints
Endpoints for retrieving client information and status
"""

import time
import logging
import traceback
from flask import jsonify


from .client_state import get_state
from .client_utils import get_group_from_docker, format_time_ago

logger = logging.getLogger(__name__)

def list_clients():
    """Get all registered clients with enhanced information"""
    try:
        state = get_state()
        
        # Get groups info for enrichment
        groups_info = {}
        try:
            from blueprints.docker_management import discover_groups
            discovery_result = discover_groups()
            if discovery_result.get("success", False):
                for group in discovery_result.get("groups", []):
                    groups_info[group.get("id")] = group
        except Exception as e:
            logger.warning(f"Could not get group info: {e}")
        
        current_time = time.time()
        clients_list = []
        
        all_clients = state.get_all_clients()
        
        for client_id, client_data in all_clients.items():
            # Calculate activity status
            last_seen = client_data.get("last_seen", 0)
            seconds_ago = int(current_time - last_seen)
            is_active = seconds_ago <= 60
            
            # Get group information
            group_id = client_data.get("group_id")
            group_info = groups_info.get(group_id) if group_id else None
            
            # Build client info
            client_info = {
                "client_id": client_id,
                "hostname": client_data.get("hostname", client_id),
                "ip_address": client_data.get("ip_address", "unknown"),
                "display_name": client_data.get("display_name", client_id),
                "platform": client_data.get("platform", "unknown"),
                
                # Status information
                "registered_at": client_data.get("registered_at", 0),
                "last_seen": last_seen,
                "last_seen_formatted": format_time_ago(seconds_ago),
                "seconds_ago": seconds_ago,
                "is_active": is_active,
                "status": "active" if is_active else "inactive",
                "assignment_status": client_data.get("assignment_status", "unknown"),
                
                # Assignment information
                "group_id": group_id,
                "group_name": group_info.get("name") if group_info else None,
                "group_docker_running": group_info.get("docker_running") if group_info else None,
                "stream_assignment": client_data.get("stream_assignment"),
                "stream_url": client_data.get("stream_url"),
                "screen_number": client_data.get("screen_number"),
                "assigned_at": client_data.get("assigned_at")
            }
            
            clients_list.append(client_info)
        
        # Sort by last seen (most recent first)
        clients_list.sort(key=lambda x: x["last_seen"], reverse=True)
        
        # Calculate statistics
        active_clients = len([c for c in clients_list if c["is_active"]])
        assigned_clients = len([c for c in clients_list if c["group_id"]])
        screen_assigned = len([c for c in clients_list if c["screen_number"] is not None])
        
        return jsonify({
            "success": True,
            "clients": clients_list,
            "statistics": {
                "total_clients": len(clients_list),
                "active_clients": active_clients,
                "assigned_clients": assigned_clients,
                "screen_assigned_clients": screen_assigned,
                "groups_available": len(groups_info)
            },
            "timestamp": current_time
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing clients: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

def get_client_details(client_id: str):
    """Get detailed information about a specific client"""
    try:
        state = get_state()
        client = state.get_client(client_id)
        
        if not client:
            return jsonify({
                "success": False,
                "error": f"Client {client_id} not found"
            }), 404
        
        # Get group information
        group_id = client.get("group_id")
        group_info = None
        if group_id:
            group_info = get_group_from_docker(group_id)
        
        current_time = time.time()
        last_seen = client.get("last_seen", 0)
        
        client_details = {
            "client_id": client_id,
            "hostname": client.get("hostname"),
            "ip_address": client.get("ip_address"),
            "display_name": client.get("display_name"),
            "platform": client.get("platform"),
            
            # Status
            "registered_at": client.get("registered_at"),
            "last_seen": last_seen,
            "is_active": (current_time - last_seen) <= 60,
            "assignment_status": client.get("assignment_status"),
            
            # Assignments
            "group_id": group_id,
            "group_info": group_info,
            "stream_assignment": client.get("stream_assignment"),
            "stream_url": client.get("stream_url"),
            "screen_number": client.get("screen_number"),
            "assigned_at": client.get("assigned_at")
        }
        
        return jsonify({
            "success": True,
            "client": client_details
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting client details: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

def health_check():
    """Health check endpoint"""
    try:
        state = get_state()
        all_clients = state.get_all_clients()
        
        current_time = time.time()
        active_clients = [
            c for c in all_clients.values()
            if (current_time - c.get("last_seen", 0)) <= 60
        ]
        
        return jsonify({
            "success": True,
            "status": "healthy",
            "timestamp": current_time,
            "client_management": {
                "initialized": state.initialized,
                "total_clients": len(all_clients),
                "active_clients": len(active_clients)
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }), 500

# Legacy endpoint for backwards compatibility
def get_clients_legacy():
    """Legacy endpoint - redirects to new list endpoint"""
    return list_clients()