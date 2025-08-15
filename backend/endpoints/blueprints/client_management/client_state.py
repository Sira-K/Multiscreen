"""
Client State Management - FIXED VERSION
Centralized state management for registered clients
"""

import time
import threading
import logging
from typing import Dict, List, Any, Optional
from flask import current_app

logger = logging.getLogger(__name__)

class ClientState:
    """Centralized client state management"""
    
    def __init__(self):
        self.clients = {}
        self.clients_lock = threading.RLock()
        self.initialized = False
    
    def initialize(self):
        """Initialize client management system"""
        if self.initialized:
            return
        
        try:
            self.initialized = True
            logger.info("Client management system initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize client management: {e}")
            raise
    
    def get_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get client by ID"""
        with self.clients_lock:
            return self.clients.get(client_id)
    
    def add_client(self, client_id: str, client_data: Dict[str, Any]):
        """Add or update client"""
        with self.clients_lock:
            self.clients[client_id] = client_data
            logger.debug(f"Added/updated client: {client_id}")
    
    def add_or_update_client(self, client_id: str, client_data: Dict[str, Any]):
        """Add or update client (alias for add_client for compatibility)"""
        return self.add_client(client_id, client_data)
    
    def remove_client(self, client_id: str) -> bool:
        """Remove client"""
        with self.clients_lock:
            if client_id in self.clients:
                del self.clients[client_id]
                logger.debug(f"Removed client: {client_id}")
                return True
            return False
    
    def get_all_clients(self) -> Dict[str, Any]:
        """Get all clients"""
        with self.clients_lock:
            return dict(self.clients)
    
    def get_group_clients(self, group_id: str) -> List[Dict[str, Any]]:
        """Get all clients in a specific group"""
        with self.clients_lock:
            return [
                client for client in self.clients.values()
                if client.get("group_id") == group_id
            ]
    
    def get_active_clients(self, group_id: str = None) -> List[Dict[str, Any]]:
        """Get active clients (seen within 60 seconds)"""
        current_time = time.time()
        with self.clients_lock:
            active_clients = []
            for client in self.clients.values():
                if current_time - client.get("last_seen", 0) <= 60:
                    if group_id is None or client.get("group_id") == group_id:
                        active_clients.append(client)
            return active_clients
    
    def update_client_heartbeat(self, client_id: str):
        """Update client last seen timestamp"""
        current_time = time.time()
        with self.clients_lock:
            if client_id in self.clients:
                self.clients[client_id]["last_seen"] = current_time
                self.clients[client_id]["status"] = "active"
    
    def update_client(self, client_id: str, **kwargs):
        """Update specific fields of a client"""
        with self.clients_lock:
            if client_id in self.clients:
                for key, value in kwargs.items():
                    self.clients[client_id][key] = value
                logger.debug(f"Updated client {client_id}: {kwargs}")
            else:
                logger.warning(f"Attempted to update non-existent client: {client_id}")

# DON'T create a separate instance - use Flask's app state
# Global client state instance
# client_state = ClientState()  # REMOVE THIS

def get_state():
    """Get application state from Flask app config"""
    try:
        # Get the state from Flask's app config (same as register_client uses)
        state = current_app.config.get('APP_STATE')
        
        # Ensure it has the ClientState methods if it doesn't already
        # This makes the AppState compatible with ClientState interface
        if state and not hasattr(state, 'initialized'):
            # Add the missing methods/attributes if needed
            if not hasattr(state, 'initialized'):
                state.initialized = True
            if not hasattr(state, 'get_client'):
                state.get_client = lambda client_id: state.clients.get(client_id) if hasattr(state, 'clients') else None
            if not hasattr(state, 'add_client'):
                def add_client_method(client_id, client_data):
                    if hasattr(state, 'clients'):
                        state.clients[client_id] = client_data
                state.add_client = add_client_method
            if not hasattr(state, 'get_all_clients'):
                state.get_all_clients = lambda: dict(state.clients) if hasattr(state, 'clients') else {}
            if not hasattr(state, 'remove_client'):
                def remove_client_method(client_id):
                    if hasattr(state, 'clients') and client_id in state.clients:
                        del state.clients[client_id]
                        return True
                    return False
                state.remove_client = remove_client_method
        
        return state
        
    except RuntimeError:
        # Outside of Flask request context (e.g., during testing)
        # Fall back to a local instance for testing only
        logger.warning("Outside Flask context, using local ClientState instance")
        if not hasattr(get_state, '_fallback_state'):
            get_state._fallback_state = ClientState()
            get_state._fallback_state.initialize()
        return get_state._fallback_state

def get_persistent_state():
    """Create and return a persistent client state instance for Flask app config"""
    state = ClientState()
    state.initialize()
    return state