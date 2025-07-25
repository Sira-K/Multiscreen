# flask_app.py - Updated for Hybrid Architecture
import os
import time
import threading
import logging
import traceback
from flask import Flask, request, jsonify
from flask_cors import CORS
from app_config import config, load_config, save_config
from models.app_state import state


# Import blueprints
from blueprints.group_management import group_bp
from blueprints.video_management import video_bp
from blueprints.client_management import client_bp
from blueprints.stream_management import stream_bp
from blueprints.docker_management import docker_bp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

flask_config = config.get_flask_config()
app.config.update(flask_config)


app.config['UNIFIED_CONFIG'] = config
app.config['APP_STATE'] = state

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
        "message": "Multi-Screen SRT Control Server - Unified Config",
        "server_info": {
            "upload_folder": app.config['UPLOAD_FOLDER'],
            "download_folder": app.config['DOWNLOAD_FOLDER'],
            "version": config.get('system', 'version'),
            "architecture": config.get('system', 'architecture'),
            "config_file": config.config_file,
            "features": [
                "Unified Configuration System",
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

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    return jsonify({
        "success": True,
        "config": config.config,
        "config_file": config.config_file
    })

@app.route('/test_config')
def test_config():
    return jsonify({
        'MAX_CONTENT_LENGTH': app.config.get('MAX_CONTENT_LENGTH'),
        'MAX_CONTENT_LENGTH_MB': app.config.get('MAX_CONTENT_LENGTH', 0) / (1024*1024),
        'config_file': config.config_file,
        'files_config': config.get('files')
    })

@app.route('/api/config', methods=['POST'])
def update_config():
    """Update configuration"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "No data provided"}), 400
        
        # Update config
        for section, values in data.items():
            if isinstance(values, dict):
                for key, value in values.items():
                    config.set(section, key, value)
            else:
                config.set(section, None, values)
        
        # Save to file
        if config.save():
            # Update Flask config if needed
            if 'files' in data or 'server' in data:
                flask_config = config.get_flask_config()
                app.config.update(flask_config)
            
            # Update state if display settings changed
            if 'display' in data:
                load_config(state)
            
            return jsonify({
                "success": True,
                "message": "Configuration updated successfully"
            })
        else:
            return jsonify({
                "success": False,
                "message": "Failed to save configuration"
            }), 500
            
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

@app.route('/api/config/presets', methods=['GET'])
def get_presets():
    """Get available layout presets"""
    return jsonify({
        "success": True,
        "presets": config.get_layout_presets()
    })

@app.route('/api/config/preset/<preset_name>', methods=['POST'])
def apply_preset(preset_name):
    """Apply a layout preset"""
    try:
        if config.apply_preset(preset_name):
            config.save()
            load_config(state)  # Update state
            
            return jsonify({
                "success": True,
                "message": f"Applied preset: {preset_name}",
                "display_config": config.get('display')
            })
        else:
            return jsonify({
                "success": False,
                "message": f"Preset not found: {preset_name}"
            }), 404
            
    except Exception as e:
        logger.error(f"Error applying preset: {e}")
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


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
    # Initialize application state
    logger.info("Starting Multi-Screen Display Server (Unified Config)...")
    
    # Server settings from config
    server_config = config.get('server')
    host = server_config.get('host', '0.0.0.0')
    port = server_config.get('port', 5001)
    debug = server_config.get('debug', True)
    
    logger.info(f"Server config: {host}:{port}, debug={debug}")
    
    if initialize_app_state():
        logger.info("Application state initialized successfully")
    else:
        logger.warning("Application state initialization had issues, but continuing...")
    
    # Start the Flask app
    app.run(host=host, port=port, debug=debug)