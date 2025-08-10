"""
Main Client Management Blueprint
Routes all client management endpoints and organizes them by functionality
"""

import logging
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