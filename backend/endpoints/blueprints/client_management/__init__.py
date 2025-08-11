"""
Client Management Module
Split into multiple files for better organization
"""

from .client_blueprint import client_bp
from .client_state import ClientState, get_state  # Import get_state instead of client_state
from .client_validators import validate_client_registration
from .client_utils import get_group_from_docker, get_persistent_streams_for_group, format_time_ago

__all__ = [
    'client_bp',
    'ClientState', 
    'get_state',  # Export get_state function instead of client_state instance
    'validate_client_registration',
    'get_group_from_docker',
    'get_persistent_streams_for_group',
    'format_time_ago'
]