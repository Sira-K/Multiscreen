# flask_app.py - Updated for Hybrid Architecture
import os
import time
import threading
import logging
import traceback
from flask import Flask, request, jsonify
from flask_cors import CORS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import blueprints
from blueprints.group_management import group_bp
from blueprints.video_management import video_bp
from blueprints.client_management import client_bp
from blueprints.stream_management import stream_bp
from blueprints.docker_management import docker_bp

# Import application state and config functions  
from models.app_state import state
from config import load_config, save_config

app = Flask(__name__)
CORS(app)

# Configuration
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['DOWNLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'resized_video')
app.config['APP_STATE'] = state

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

# Register blueprints
app.register_blueprint(group_bp)
app.register_blueprint(video_bp)
app.register_blueprint(client_bp)
app.register_blueprint(stream_bp)
app.register_blueprint(docker_bp)

# Initialize application state
load_config(state)

def initialize_app_state():
    """Initialize app state - hybrid architecture (clients only)"""
    try:
        logger.info("Initializing application state...")
        
        # Initialize client state only - groups come from Docker discovery
        if not hasattr(state, 'clients'):
            state.clients = {}
        if not hasattr(state, 'clients_lock'):
            state.clients_lock = threading.RLock()
        
        # Initialize configuration locks
        if not hasattr(state, 'config_lock'):
            state.config_lock = threading.RLock()
        
        # NO GROUP INITIALIZATION - groups are managed by Docker containers
        
        # Log current state
        total_clients = len(getattr(state, 'clients', {}))
        
        logger.info(f"Application state initialized:")
        logger.info(f"  - Total clients: {total_clients}")
        logger.info(f"  - Groups: Managed by Docker discovery")
        
        return True
        
    except Exception as e:
        logger.error(f"Error initializing app state: {e}")
        traceback.print_exc()
        return False

def get_system_status():
    """Get overall system status - hybrid architecture"""
    try:
        current_time = time.time()
        
        # Get groups from Docker discovery
        groups_info = {"total": 0, "active": 0, "docker_containers": 0}
        
        try:
            from blueprints.docker_management import discover_groups
            discovery_result = discover_groups()
            
            if discovery_result.get("success", False):
                groups = discovery_result.get("groups", [])
                groups_info["total"] = len(groups)
                groups_info["docker_containers"] = len([g for g in groups if g.get("docker_running", False)])
                groups_info["active"] = len([g for g in groups if g.get("docker_running", False)])
            
        except Exception as e:
            logger.warning(f"Could not get group info from Docker: {e}")
        
        # Count clients from app state
        total_clients = len(getattr(state, 'clients', {}))
        active_clients = 0
        
        if hasattr(state, 'clients'):
            for client in state.clients.values():
                if current_time - client.get('last_seen', 0) <= 60:
                    active_clients += 1
        
        return {
            'timestamp': current_time,
            'groups': groups_info,
            'clients': {
                'total': total_clients,
                'active': active_clients
            },
            'architecture': 'hybrid_docker_discovery'
        }
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return {'error': str(e), 'timestamp': time.time()}

# Main routes
@app.route('/')
def home():
    """Home endpoint with system information"""
    # Get groups count from Docker discovery
    groups_count = 0
    active_groups_count = 0
    
    try:
        from blueprints.docker_management import discover_groups
        discovery_result = discover_groups()
        if discovery_result.get("success", False):
            groups = discovery_result.get("groups", [])
            groups_count = len(groups)
            active_groups_count = len([g for g in groups if g.get("docker_running", False)])
    except Exception as e:
        logger.warning(f"Could not get groups for home endpoint: {e}")
    
    return jsonify({
        "status": "running", 
        "message": "Multi-Screen SRT Control Server - Hybrid Architecture",
        "server_info": {
            "upload_folder": app.config['UPLOAD_FOLDER'],
            "download_folder": app.config['DOWNLOAD_FOLDER'],
            "version": "3.1.0",
            "architecture": "hybrid_docker_discovery",
            "features": [
                "Pure Docker Group Discovery",
                "In-Memory Client Management", 
                "Multi-Container Docker Support", 
                "Per-Group SRT Streaming",
                "Dynamic Port Assignment",
                "Client Group Assignment",
                "REST API Only"
            ]
        },
        "stats": {
            "total_groups": groups_count,
            "active_groups": active_groups_count,
            "total_clients": len(getattr(state, 'clients', {}))
        }
    })

@app.route('/ping')
def ping():
    """Simple ping endpoint to test server availability"""
    return jsonify({
        "message": "pong",
        "server_ip": request.host,
        "timestamp": time.time(),
        "architecture": "hybrid_docker_discovery",
        "clients_available": hasattr(state, 'clients')
    })

@app.route('/system_status')
def system_status():
    """Get overall system status including groups and clients"""
    try:
        return jsonify(get_system_status()), 200
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return jsonify({
            "error": str(e),
            "server_running": True,
            "architecture": "hybrid_docker_discovery"
        }), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Check Docker availability
        docker_available = False
        groups_count = 0
        
        try:
            from blueprints.docker_management import discover_groups
            discovery_result = discover_groups()
            docker_available = discovery_result.get("success", False)
            if docker_available:
                groups_count = len(discovery_result.get("groups", []))
        except:
            docker_available = False
        
        health_status = {
            "status": "healthy",
            "timestamp": time.time(),
            "architecture": "hybrid_docker_discovery",
            "checks": {
                "app_state": hasattr(state, 'clients') and hasattr(state, 'clients_lock'),
                "upload_folder": os.path.exists(app.config['UPLOAD_FOLDER']),
                "download_folder": os.path.exists(app.config['DOWNLOAD_FOLDER']),
                "docker_discovery": docker_available,
                "client_management": hasattr(state, 'clients')
            },
            "stats": {
                "groups_discovered": groups_count,
                "clients_connected": len(getattr(state, 'clients', {}))
            }
        }
        
        all_healthy = all(health_status["checks"].values())
        
        if not all_healthy:
            health_status["status"] = "degraded"
            
        return jsonify(health_status), 200 if all_healthy else 503
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time(),
            "architecture": "hybrid_docker_discovery"
        }), 503

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Endpoint not found",
        "message": "The requested endpoint does not exist",
        "architecture": "hybrid_docker_discovery",
        "available_endpoints": [
            "/", "/ping", "/system_status", "/api/health",
            "/get_groups", "/create_group", "/delete_group",
            "/get_clients", "/register_client", "/assign_client_to_group",
            "/start_group_srt", "/stop_group_srt",
            "/start_group_docker", "/stop_group_docker"
        ]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "error": "Internal server error",
        "message": "An unexpected error occurred",
        "timestamp": time.time(),
        "architecture": "hybrid_docker_discovery"
    }), 500

# Cleanup function for graceful shutdown
def cleanup_on_shutdown():
    """Clean up resources on application shutdown"""
    try:
        logger.info("Performing cleanup on shutdown...")
        # Save configuration (not clients, they're runtime data)
        save_config(state)
        logger.info("Saved configuration")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

# Register cleanup function
import atexit
atexit.register(cleanup_on_shutdown)

if __name__ == "__main__":
    import logging
    import traceback
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Initialize application state
    logger.info("Starting Multi-Screen Display Server (Hybrid Architecture)...")
    
    if initialize_app_state():
        logger.info("Application state initialized successfully")
    else:
        logger.warning("Application state initialization had issues, but continuing...")
    
    # Start the Flask app
    app.run(host="0.0.0.0", port=5001, debug=True)  # Using port 5001 to avoid conflicts