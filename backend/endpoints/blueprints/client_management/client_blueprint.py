"""
Main Client Management Blueprint
Routes all client management endpoints and organizes them by functionality
"""

import logging
import traceback
from flask import Blueprint

# Import endpoint functions
from .client_endpoints import (
    register_client,
    unregister_client,
    wait_for_assignment,
    register_client_legacy,
    wait_for_stream_legacy
)
from .admin_endpoints import (
    assign_client_to_group,
    assign_client_to_stream,
    assign_client_to_screen,
    auto_assign_group_clients,
    unassign_client,
    remove_client
)
# unassign_client_from_screen is now imported from the main module
from .info_endpoints import (
    list_clients,
    get_client_details,
    health_check,
    get_clients_legacy
)

logger = logging.getLogger(__name__)

# Create blueprint
client_bp = Blueprint('client_management', __name__)

# =====================================
# CLIENT REGISTRATION ENDPOINTS
# =====================================

@client_bp.route("/register", methods=["POST"])
def register_route():
    """Register a client device"""
    return register_client()

@client_bp.route("/unregister", methods=["POST"])
def unregister_route():
    """Unregister a client"""
    return unregister_client()

@client_bp.route("/wait_for_assignment", methods=["POST"])
def wait_for_assignment_route():
    """Client polls this endpoint to wait for assignments and streaming"""
    return wait_for_assignment()

# =====================================
# CLIENT INFORMATION ENDPOINTS
# =====================================

@client_bp.route("/list", methods=["GET"])
def list_clients_route():
    """Get all registered clients with enhanced information"""
    return list_clients()

@client_bp.route("/get_client/<client_id>", methods=["GET"])
def get_client_details_route(client_id: str):
    """Get detailed information about a specific client"""
    return get_client_details(client_id)

@client_bp.route("/health", methods=["GET"])
def health_check_route():
    """Health check endpoint"""
    return health_check()

@client_bp.route("/debug/state", methods=["GET"])
def debug_state_route():
    """Debug endpoint to show current state"""
    try:
        from .admin_endpoints import get_state
        state = get_state()
        
        if not state:
            return jsonify({
                "error": "No state available",
                "state_type": "None"
            }), 500
        
        debug_info = {
            "state_type": type(state).__name__,
            "state_attributes": [attr for attr in dir(state) if not attr.startswith('_')],
            "has_clients": hasattr(state, 'clients'),
            "has_get_client": hasattr(state, 'get_client'),
            "has_add_client": hasattr(state, 'add_client'),
        }
        
        if hasattr(state, 'clients'):
            debug_info["clients_count"] = len(state.clients) if state.clients else 0
            debug_info["clients_keys"] = list(state.clients.keys()) if state.clients else []
        
        return jsonify(debug_info), 200
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@client_bp.route("/test/unassign", methods=["POST"])
def test_unassign_route():
    """Test endpoint to test unassignment functionality"""
    try:
        from .admin_endpoints import get_state
        state = get_state()
        
        if not state:
            return jsonify({
                "error": "No state available"
            }), 500
        
        # Test data
        test_data = {
            "client_id": "test-client",
            "unassign_type": "all"
        }
        
        # Test validation
        from .client_utils import validate_unassignment
        is_valid, error_msg, cleaned_data = validate_unassignment(test_data)
        
        return jsonify({
            "test_data": test_data,
            "validation_result": {
                "is_valid": is_valid,
                "error_msg": error_msg,
                "cleaned_data": cleaned_data
            },
            "state_info": {
                "type": type(state).__name__,
                "has_clients": hasattr(state, 'clients'),
                "has_get_client": hasattr(state, 'get_client'),
                "has_add_client": hasattr(state, 'add_client'),
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@client_bp.route("/test/stream_unassign", methods=["POST"])
def test_stream_unassign_route():
    """Test endpoint specifically for stream unassignment"""
    try:
        from .admin_endpoints import get_state
        state = get_state()
        
        if not state:
            return jsonify({
                "error": "No state available"
            }), 500
        
        data = request.get_json() or {}
        client_id = data.get("client_id", "test-client")
        
        # Check if client exists and show current state
        if hasattr(state, 'clients') and client_id in state.clients:
            client = state.clients[client_id]
            current_state = {
                "client_id": client_id,
                "group_id": client.get("group_id"),
                "stream_assignment": client.get("stream_assignment"),
                "screen_number": client.get("screen_number"),
                "assignment_status": client.get("assignment_status"),
                "stream_url": client.get("stream_url")
            }
        else:
            current_state = {"error": "Client not found"}
        
        return jsonify({
            "test_type": "stream_unassign",
            "client_id": client_id,
            "current_client_state": current_state,
            "state_info": {
                "type": type(state).__name__,
                "has_clients": hasattr(state, 'clients'),
                "clients_count": len(state.clients) if hasattr(state, 'clients') else 0,
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

# =====================================
# ADMIN ASSIGNMENT ENDPOINTS
# =====================================

@client_bp.route("/assign_to_group", methods=["POST"])
def assign_to_group_route():
    """Admin function: Assign a client to a specific group"""
    return assign_client_to_group()

@client_bp.route("/assign_to_stream", methods=["POST"])
def assign_to_stream_route():
    """Admin function: Assign a client to a specific stream"""
    return assign_client_to_stream()

@client_bp.route("/assign_to_screen", methods=["POST"])
def assign_to_screen_route():
    """Admin function: Assign a client to a specific screen"""
    return assign_client_to_screen()

@client_bp.route("/auto_assign_group", methods=["POST"])
def auto_assign_group_route():
    """Admin function: Auto-assign all clients in a group to different streams"""
    return auto_assign_group_clients()

@client_bp.route("/unassign_client", methods=["POST"])
def unassign_client_route():
    """Admin function: Unassign a client from its group/stream/screen"""
    return unassign_client()

@client_bp.route("/unassign_from_screen", methods=["POST"])
def unassign_from_screen_route():
    """Admin function: Unassign a client from its screen but keep group assignment"""
    return unassign_client_from_screen()

@client_bp.route("/unassign_from_stream", methods=["POST"])
def unassign_from_stream_route():
    """Admin function: Unassign a client from its stream but keep group assignment"""
    return unassign_client_from_stream()

@client_bp.route("/remove_client", methods=["POST"])
def remove_client_route():
    """Admin function: Remove a client from the system completely"""
    return remove_client()

# =====================================
# LEGACY ENDPOINTS (for backwards compatibility)
# =====================================

@client_bp.route("/register_client", methods=["POST"])
def register_client_legacy_route():
    """Legacy endpoint - redirects to new register endpoint"""
    return register_client_legacy()

@client_bp.route("/wait_for_stream", methods=["POST"])
def wait_for_stream_legacy_route():
    """Legacy endpoint - redirects to new wait_for_assignment endpoint"""
    return wait_for_stream_legacy()

@client_bp.route("/get_clients", methods=["GET"])
def get_clients_legacy_route():
    """Legacy endpoint - redirects to new list endpoint"""
    return get_clients_legacy()

# =====================================
# INITIALIZATION
# =====================================

def init_client_management():
    """Initialize client management system when module is loaded"""
    try:
        # Initialize the state (this will start any required services)
        from .client_state import get_state
        get_state()
        logger.info("Client management system initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize client management system: {e}")

# Initialize when module is imported
init_client_management()