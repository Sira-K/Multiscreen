# flask_app.py - Updated with Comprehensive Error System Integration
import os
import time
import threading
import logging
import traceback
from flask import Flask, request, jsonify
from flask_cors import CORS
from app_config import config, load_config, save_config
from models.app_state import state

# Import error handling system
from errors import (
    StreamError, DockerError, VideoError, ClientError, SystemError,
    StreamManagementException, DockerManagementException, 
    VideoManagementException, ClientManagementException, SystemException,
    format_error_response, format_docker_error_response, 
    format_video_error_response, format_client_error_response,
    format_system_error_response
)

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
        
        # Log current state
        total_clients = len(getattr(state, 'clients', {}))
        
        logger.info(f"Application state initialized:")
        logger.info(f"  - Total clients: {total_clients}")
        logger.info(f"  - Groups: Managed by Docker discovery")
        
        return True
        
    except SystemException as e:
        logger.error(f"System error initializing app state: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error initializing app state: {e}")
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
            
        except DockerManagementException as e:
            logger.warning(f"Docker management error getting group info: {e}")
            groups_info["error"] = f"Docker error: {e.error_code}"
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
        
    except SystemException as e:
        logger.error(f"System error getting status: {e}")
        return format_system_error_response(e.error_code, {'timestamp': time.time()})
    except Exception as e:
        logger.error(f"Unexpected error getting system status: {e}")
        return format_system_error_response(506, {'error': str(e), 'timestamp': time.time()})

# Enhanced error handlers with proper error system integration
@app.errorhandler(StreamManagementException)
def handle_stream_error(error):
    """Handle stream management errors"""
    logger.error(f"Stream management error {error.error_code}: {error}")
    response = format_error_response(error.error_code, error.context)
    response['timestamp'] = time.time()
    return jsonify(response), 500

@app.errorhandler(DockerManagementException)
def handle_docker_error(error):
    """Handle Docker management errors"""
    logger.error(f"Docker management error {error.error_code}: {error}")
    response = format_docker_error_response(error.error_code, error.context)
    response['timestamp'] = time.time()
    return jsonify(response), 500

@app.errorhandler(VideoManagementException)
def handle_video_error(error):
    """Handle video management errors"""
    logger.error(f"Video management error {error.error_code}: {error}")
    response = format_video_error_response(error.error_code, error.context)
    response['timestamp'] = time.time()
    return jsonify(response), 500

@app.errorhandler(ClientManagementException)
def handle_client_error(error):
    """Handle client management errors"""
    logger.error(f"Client management error {error.error_code}: {error}")
    response = format_client_error_response(error.error_code, error.context)
    response['timestamp'] = time.time()
    return jsonify(response), 500

@app.errorhandler(SystemException)
def handle_system_error(error):
    """Handle system errors"""
    logger.error(f"System error {error.error_code}: {error}")
    response = format_system_error_response(error.error_code, error.context)
    response['timestamp'] = time.time()
    return jsonify(response), 500

@app.errorhandler(400)
def bad_request(error):
    """Handle bad request errors"""
    logger.warning(f"Bad request: {error}")
    return jsonify({
        "success": False,
        "error_code": 400,
        "error_message": "Bad Request",
        "description": "The request was malformed or invalid",
        "category": "http",
        "timestamp": time.time()
    }), 400

@app.errorhandler(404)
def not_found(error):
    """Handle not found errors"""
    logger.warning(f"Not found: {request.url}")
    return jsonify({
        "success": False,
        "error_code": 404,
        "error_message": "Not Found",
        "description": "The requested resource was not found",
        "category": "http",
        "timestamp": time.time(),
        "suggestions": [
            "Check the API documentation for correct endpoints",
            "Verify the URL path is correct",
            "Ensure the resource exists"
        ]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle internal server errors"""
    logger.error(f"Internal server error: {error}")
    return jsonify(format_system_error_response(506, {
        "original_error": str(error),
        "timestamp": time.time(),
        "architecture": "hybrid_docker_discovery"
    })), 500

# Main routes with enhanced error handling
@app.route('/')
def home():
    """Home endpoint with system information"""
    try:
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
        except DockerManagementException as e:
            logger.warning(f"Docker error in home route: {e}")
            # Continue with default values
        except Exception as e:
            logger.warning(f"Error getting groups in home route: {e}")
        
        # Get client count
        total_clients = len(getattr(state, 'clients', {}))
        
        return jsonify({
            "message": "Multi-Screen Display Server (Hybrid Architecture)",
            "status": "running",
            "timestamp": time.time(),
            "groups": {
                "total": groups_count,
                "active": active_groups_count
            },
            "clients": {
                "total": total_clients
            },
            "architecture": "hybrid_docker_discovery",
            "api_endpoints": {
                "groups": "/api/groups",
                "clients": "/api/clients",
                "streams": "/api/streams",
                "videos": "/api/videos",
                "docker": "/api/docker",
                "status": "/api/status"
            }
        })
        
    except SystemException as e:
        logger.error(f"System error in home route: {e}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in home route: {e}")
        raise SystemException(506, context={"route": "home", "error": str(e)})

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get system status with error handling"""
    try:
        status = get_system_status()
        if 'error' in status:
            return jsonify(status), 500
        return jsonify({
            "success": True,
            "status": status
        })
    except SystemException as e:
        raise e
    except Exception as e:
        raise SystemException(506, context={"route": "status", "error": str(e)})

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration with error handling"""
    try:
        return jsonify({
            "success": True,
            "config": config.config,
            "config_file": config.config_file
        })
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        raise SystemException(506, context={"route": "get_config", "error": str(e)})

@app.route('/api/config', methods=['POST'])
def update_config():
    """Update configuration with enhanced error handling"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error_code": 400,
                "error_message": "No data provided",
                "category": "validation"
            }), 400
        
        # Update config
        for section, values in data.items():
            try:
                if isinstance(values, dict):
                    for key, value in values.items():
                        config.set(section, key, value)
                else:
                    config.set(section, None, values)
            except Exception as e:
                logger.error(f"Error updating config section {section}: {e}")
                raise SystemException(503, context={
                    "section": section, 
                    "error": str(e),
                    "route": "update_config"
                })
        
        # Save to file
        try:
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
                raise SystemException(503, context={
                    "operation": "save_config",
                    "route": "update_config"
                })
        except SystemException:
            raise
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            raise SystemException(503, context={
                "operation": "save_config",
                "error": str(e),
                "route": "update_config"
            })
            
    except SystemException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error updating config: {e}")
        raise SystemException(506, context={"route": "update_config", "error": str(e)})

@app.route('/api/config/presets', methods=['GET'])
def get_presets():
    """Get available layout presets with error handling"""
    try:
        return jsonify({
            "success": True,
            "presets": config.get_layout_presets()
        })
    except Exception as e:
        logger.error(f"Error getting presets: {e}")
        raise SystemException(506, context={"route": "get_presets", "error": str(e)})

@app.route('/api/config/preset/<preset_name>', methods=['POST'])
def apply_preset(preset_name):
    """Apply a layout preset with error handling"""
    try:
        if config.apply_preset(preset_name):
            if config.save():
                load_config(state)  # Update state
                
                return jsonify({
                    "success": True,
                    "message": f"Applied preset: {preset_name}",
                    "display_config": config.get('display')
                })
            else:
                raise SystemException(503, context={
                    "operation": "save_preset",
                    "preset": preset_name
                })
        else:
            return jsonify({
                "success": False,
                "error_code": 404,
                "error_message": f"Preset not found: {preset_name}",
                "category": "validation"
            }), 404
            
    except SystemException as e:
        raise e
    except Exception as e:
        logger.error(f"Error applying preset {preset_name}: {e}")
        raise SystemException(506, context={
            "preset": preset_name,
            "error": str(e),
            "route": "apply_preset"
        })

# Cleanup function for graceful shutdown
def cleanup_on_shutdown():
    """Clean up resources on application shutdown"""
    try:
        logger.info("Performing cleanup on shutdown...")
        # Save configuration (not clients, they're runtime data)
        save_config(state)
        logger.info("Saved configuration")
    except SystemException as e:
        logger.error(f"System error during cleanup: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during cleanup: {e}")

# Register cleanup function
import atexit
atexit.register(cleanup_on_shutdown)

if __name__ == "__main__":
    try:
        # Initialize application state
        logger.info("Starting Multi-Screen Display Server (Unified Config)...")
        
        # Server settings from config
        server_config = config.get('server')
        host = server_config.get('host', '0.0.0.0')
        port = server_config.get('port', 5000)
        debug = server_config.get('debug', True)
        
        logger.info(f"Server config: {host}:{port}, debug={debug}")
        
        if initialize_app_state():
            logger.info("Application state initialized successfully")
        else:
            logger.warning("Application state initialization had issues, but continuing...")
        
        # Start the Flask app
        app.run(host=host, port=port, debug=debug)
        
    except SystemException as e:
        logger.error(f"System error starting application: {e}")
        exit(1)
    except Exception as e:
        logger.error(f"Unexpected error starting application: {e}")
        traceback.print_exc()
        exit(1)