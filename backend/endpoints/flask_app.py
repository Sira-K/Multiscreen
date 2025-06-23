# flask_app.py - Updated with Group Management Support
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import logging
import time
import threading

# Import application state
from models.app_state import state

# Import blueprints - now including group management
from blueprints.client_management import client_bp
from blueprints.video_management import video_bp
from blueprints.stream_management import stream_bp
from blueprints.docker_management import docker_bp
from blueprints.screen_management import screen_bp
from blueprints.group_management import group_bp  # New group management blueprint

# Import configuration functions
from config import load_config, save_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask application
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'raw_video_file')
app.config['DOWNLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resized_video')
app.config['APP_STATE'] = state
app.config['SRT_SERVER_IP'] = '128.205.39.64'

# Ensure both directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

logger.info(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
logger.info(f"Download folder: {app.config['DOWNLOAD_FOLDER']}")

# Initialize application state with group support
def initialize_app_state():
    """Initialize the application state with group support and load saved configuration"""
    
    # Initialize group-related attributes if they don't exist
    if not hasattr(state, 'groups'):
        state.groups = {}
        logger.info("Initialized groups dictionary")
    
    if not hasattr(state, 'groups_lock'):
        state.groups_lock = threading.RLock()
        logger.info("Initialized groups lock")
    
    # Load saved configuration
    try:
        success = load_config(state)
        if success:
            logger.info("Loaded application configuration from file")
        else:
            logger.info("Using default configuration (no saved config found)")
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
    
    # Set default SRT IP if not configured
    if not hasattr(state, 'srt_ip') or not state.srt_ip:
        state.srt_ip = app.config['SRT_SERVER_IP']
        logger.info(f"Set default SRT IP: {state.srt_ip}")

# Initialize state
initialize_app_state()

# Register blueprints
app.register_blueprint(client_bp)
app.register_blueprint(video_bp)
app.register_blueprint(stream_bp)
app.register_blueprint(docker_bp)
app.register_blueprint(screen_bp)
app.register_blueprint(group_bp)  # Register the new group management blueprint

logger.info("Registered all blueprints including group management")

@app.route('/')
def home():
    """Home endpoint with group information"""
    return jsonify({
        "status": "running", 
        "message": "Multi-Screen SRT Control Server with Group Management",
        "server_info": {
            "upload_folder": app.config['UPLOAD_FOLDER'],
            "download_folder": app.config['DOWNLOAD_FOLDER'],
            "version": "2.0.0",
            "features": [
                "Group Management",
                "Multi-Container Docker Support", 
                "Per-Group SRT Streaming",
                "Dynamic Port Assignment",
                "Client Group Assignment"
            ]
        },
        "group_stats": {
            "total_groups": len(getattr(state, 'groups', {})),
            "active_groups": len([g for g in getattr(state, 'groups', {}).values() if g.get('status') == 'active']),
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
        "groups_available": hasattr(state, 'groups')
    })

@app.route('/system_status')
def system_status():
    """Get overall system status including groups"""
    try:
        system_status = {
            "server_running": True,
            "total_groups": len(getattr(state, 'groups', {})),
            "active_groups": 0,
            "total_clients": len(getattr(state, 'clients', {})),
            "active_clients": 0,
            "docker_containers": 0,
            "active_streams": 0
        }
        
        current_time = time.time()
        
        # Count active clients (seen in last minute)
        if hasattr(state, 'clients'):
            for client in state.clients.values():
                if current_time - client.get('last_seen', 0) <= 60:
                    system_status["active_clients"] += 1
        
        # Count group statistics
        if hasattr(state, 'groups'):
            for group in state.groups.values():
                if group.get('status') == 'active':
                    system_status["active_groups"] += 1
                if group.get('docker_container_id'):
                    system_status["docker_containers"] += 1
                if group.get('ffmpeg_process_id'):
                    system_status["active_streams"] += 1
        
        return jsonify(system_status), 200
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return jsonify({
            "error": str(e),
            "server_running": True
        }), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Basic health checks
        health_status = {
            "status": "healthy",
            "timestamp": time.time(),
            "checks": {
                "app_state": hasattr(state, 'groups') and hasattr(state, 'clients'),
                "upload_folder": os.path.exists(app.config['UPLOAD_FOLDER']),
                "download_folder": os.path.exists(app.config['DOWNLOAD_FOLDER']),
                "groups_initialized": hasattr(state, 'groups_lock')
            }
        }
        
        # Check if all components are working
        all_healthy = all(health_status["checks"].values())
        
        if not all_healthy:
            health_status["status"] = "degraded"
            
        return jsonify(health_status), 200 if all_healthy else 503
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }), 503

@app.route('/api/config', methods=['GET', 'POST'])
def manage_config():
    """Get or update application configuration"""
    if request.method == 'GET':
        # Return current configuration
        config = {
            "srt_ip": getattr(state, 'srt_ip', '127.0.0.1'),
            "screen_count": getattr(state, 'screen_count', 2),
            "orientation": getattr(state, 'orientation', 'horizontal'),
            "screen_ips": getattr(state, 'screen_ips', {}),
            "total_groups": len(getattr(state, 'groups', {}))
        }
        return jsonify(config), 200
    
    elif request.method == 'POST':
        # Update configuration
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "No configuration data provided"}), 400
            
            # Update state with new configuration
            if 'srt_ip' in data:
                state.srt_ip = data['srt_ip']
            if 'screen_count' in data:
                state.screen_count = int(data['screen_count'])
            if 'orientation' in data:
                state.orientation = data['orientation']
            if 'screen_ips' in data:
                state.screen_ips = data['screen_ips']
            
            # Save configuration to file
            success = save_config(state)
            
            if success:
                return jsonify({
                    "message": "Configuration updated successfully",
                    "saved": True
                }), 200
            else:
                return jsonify({
                    "message": "Configuration updated but not saved to file",
                    "saved": False
                }), 200
                
        except Exception as e:
            logger.error(f"Error updating configuration: {e}")
            return jsonify({"error": str(e)}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Endpoint not found",
        "message": "The requested endpoint does not exist",
        "available_endpoints": [
            "/", "/ping", "/system_status", "/api/health", "/api/config",
            "/get_groups", "/create_group", "/get_clients", "/assign_stream",
            "/start_group_docker", "/stop_group_docker", 
            "/start_group_srt", "/stop_group_srt"
        ]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({
        "error": "Internal server error",
        "message": "An unexpected error occurred"
    }), 500

@app.errorhandler(400)
def bad_request(error):
    return jsonify({
        "error": "Bad request",
        "message": "The request was malformed or missing required parameters"
    }), 400

# Cleanup function for graceful shutdown
def cleanup_on_shutdown():
    """Clean up resources on application shutdown"""
    try:
        logger.info("Performing cleanup on shutdown...")
        
        # Save current configuration
        save_config(state)
        logger.info("Saved configuration")
        
        # Could add more cleanup here (stop processes, close connections, etc.)
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

# Register cleanup function
import atexit
atexit.register(cleanup_on_shutdown)

if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("Starting Multi-Screen SRT Control Server with Group Management")
    logger.info("=" * 60)
    logger.info(f"Groups initialized: {hasattr(state, 'groups')}")
    logger.info(f"Total groups: {len(getattr(state, 'groups', {}))}")
    logger.info(f"SRT IP: {getattr(state, 'srt_ip', 'Not set')}")
    logger.info("=" * 60)
    
    # Run the Flask application
    app.run(host='0.0.0.0', port=5000, debug=True)