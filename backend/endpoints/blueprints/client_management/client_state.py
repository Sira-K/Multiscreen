"""
Client State Management - FIXED VERSION
Centralized state management for registered clients
"""

import time
import threading
import logging
from typing import Dict, List, Any, Optional

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

# Global client state instance
client_state = ClientState()

def get_state():
    """Get application state"""
    if not client_state.initialized:
        client_state.initialize()
    return client_state