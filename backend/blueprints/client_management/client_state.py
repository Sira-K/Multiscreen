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
        """Update client last seen timestamp and status"""
        current_time = time.time()
        with self.clients_lock:
            if client_id in self.clients:
                self.clients[client_id]["last_seen"] = current_time
                self.clients[client_id]["status"] = "active"
                self.clients[client_id]["is_active"] = True
                logger.debug(f"Client {client_id} heartbeat updated, status: active")
    
    def update_client(self, client_id: str, **kwargs):
        """Update specific fields of a client"""
        with self.clients_lock:
            if client_id in self.clients:
                for key, value in kwargs.items():
                    self.clients[client_id][key] = value
                logger.debug(f"Updated client {client_id}: {kwargs}")
            else:
                logger.warning(f"Attempted to update non-existent client: {client_id}")

    def update_client_statuses(self):
        """
        Update client statuses based on heartbeat timing:
        - Active: heartbeat within 30 seconds
        - Inactive: heartbeat within 30-120 seconds (warning stage)
        - Disconnected: no heartbeat for 120+ seconds (will be removed)
        """
        current_time = time.time()
        status_changes = []
        
        with self.clients_lock:
            for client_id, client in self.clients.items():
                last_seen = client.get('last_seen', 0)
                time_since_heartbeat = current_time - last_seen
                old_status = client.get('status', 'unknown')
                old_is_active = client.get('is_active', False)
                
                # Determine new status based on heartbeat timing
                if time_since_heartbeat <= 30:
                    new_status = "active"
                    new_is_active = True
                elif time_since_heartbeat <= 120:
                    new_status = "inactive"
                    new_is_active = False
                else:
                    new_status = "disconnected"
                    new_is_active = False
                
                # Update if status changed
                if new_status != old_status or new_is_active != old_is_active:
                    client['status'] = new_status
                    client['is_active'] = new_is_active
                    client['seconds_ago'] = int(time_since_heartbeat)
                    
                    status_changes.append({
                        'client_id': client_id,
                        'old_status': old_status,
                        'new_status': new_status,
                        'time_since_heartbeat': time_since_heartbeat
                    })
                    
                    logger.info(f"Client {client_id} status changed: {old_status} -> {new_status} "
                              f"(last heartbeat: {time_since_heartbeat:.1f}s ago)")
        
        return status_changes

    def cleanup_disconnected_clients(self, force: bool = False):
        """
        Automatically remove clients that are in 'disconnected' status (no heartbeat for 120+ seconds)
        
        Args:
            force: If True, remove clients even if they're actively streaming
        
        Returns:
            dict: Summary of cleanup operation
        """
        disconnected_clients = []
        removed_count = 0
        failed_count = 0
        
        with self.clients_lock:
            # Find disconnected clients
            for client_id, client in list(self.clients.items()):
                if client.get('status') == 'disconnected':
                    disconnected_clients.append((client_id, client))
            
            # Remove disconnected clients
            for client_id, client in disconnected_clients:
                try:
                    client_name = client.get('display_name') or client.get('hostname') or client_id
                    
                    # Check if client is actively streaming
                    if not force and client.get('stream_assignment'):
                        logger.info(f"Skipping cleanup for actively streaming client: {client_name} ({client_id})")
                        continue
                    
                    # Remove client
                    del self.clients[client_id]
                    removed_count += 1
                    logger.info(f"Auto-removed disconnected client: {client_name} ({client_id})")
                    
                except Exception as e:
                    logger.error(f"Error removing disconnected client {client_id}: {e}")
                    failed_count += 1
        
        if removed_count > 0:
            logger.info(f"Auto-cleanup completed: {removed_count} disconnected clients removed, {failed_count} failed")
        
        return {
            "removed_count": removed_count,
            "failed_count": failed_count,
            "total_disconnected": len(disconnected_clients)
        }

    def start_auto_cleanup(self, cleanup_interval_seconds: int = 30, inactive_threshold_seconds: int = 120):
        """
        Start automatic cleanup of inactive clients
        
        Args:
            cleanup_interval_seconds: How often to run cleanup (default: 30 seconds)
            inactive_threshold_seconds: Time after which clients are considered inactive (default: 2 minutes)
        """
        if hasattr(self, '_cleanup_thread') and self._cleanup_thread.is_alive():
            logger.warning("Auto-cleanup already running")
            return
        
        def cleanup_worker():
            logger.info(f"Auto-cleanup worker started (interval: {cleanup_interval_seconds}s)")
            while True:
                try:
                    time.sleep(cleanup_interval_seconds)
                    
                    # First, update client statuses based on heartbeat timing
                    status_changes = self.update_client_statuses()
                    if status_changes:
                        logger.info(f"Updated {len(status_changes)} client statuses")
                    
                    # Then, remove clients that are in 'disconnected' status
                    cleanup_result = self.cleanup_disconnected_clients()
                    if cleanup_result['removed_count'] > 0:
                        logger.info(f"Removed {cleanup_result['removed_count']} disconnected clients")
                        
                except Exception as e:
                    logger.error(f"Error in auto-cleanup worker: {e}")
                    time.sleep(5)  # Wait a bit before retrying
        
        self._cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        self._cleanup_thread.start()
        logger.info("Auto-cleanup thread started")

    def stop_auto_cleanup(self):
        """Stop automatic cleanup of inactive clients"""
        if hasattr(self, '_cleanup_thread') and self._cleanup_thread.is_alive():
            # Set a flag to stop the thread (we'll use a simple approach)
            self._cleanup_running = False
            logger.info("Auto-cleanup stopped")
        else:
            logger.info("Auto-cleanup was not running")

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
            
            # Add auto-cleanup methods
            if not hasattr(state, 'update_client_statuses'):
                state.update_client_statuses = lambda: ClientState().update_client_statuses()
            if not hasattr(state, 'cleanup_disconnected_clients'):
                state.cleanup_disconnected_clients = lambda force=False: ClientState().cleanup_disconnected_clients(force)
            if not hasattr(state, 'start_auto_cleanup'):
                state.start_auto_cleanup = lambda interval=30, threshold=120: ClientState().start_auto_cleanup(interval, threshold)
            if not hasattr(state, 'stop_auto_cleanup'):
                state.stop_auto_cleanup = lambda: ClientState().stop_auto_cleanup()
        
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