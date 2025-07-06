# flask_app.py
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

# Import application state and config functions  
from models.app_state import state
from config import load_config, save_config

app = Flask(__name__)
CORS(app)

# Configuration
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['DOWNLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'resized_video')
app.config['APP_STATE'] = state  # Add this line to fix the KeyError

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

# Register blueprints
app.register_blueprint(group_bp)
app.register_blueprint(video_bp)
app.register_blueprint(client_bp)
app.register_blueprint(stream_bp)

# Initialize application state
load_config(state)

def get_system_status():
    """Get overall system status including groups and clients"""
    try:
        current_time = time.time()
        
        # Count groups and their statuses
        total_groups = len(getattr(state, 'groups', {}))
        active_groups = 0
        docker_containers = 0
        active_streams = 0
        
        if hasattr(state, 'groups'):
            for group in state.groups.values():
                if group.get('status') == 'active':
                    active_groups += 1
                if group.get('docker_container_id'):
                    docker_containers += 1
                if group.get('ffmpeg_process_id'):
                    active_streams += 1
        
        # Count clients
        total_clients = len(getattr(state, 'clients', {}))
        active_clients = 0
        
        if hasattr(state, 'clients'):
            for client in state.clients.values():
                if current_time - client.get('last_seen', 0) <= 60:
                    active_clients += 1
        
        return {
            'timestamp': current_time,
            'groups': {
                'total': total_groups,
                'active': active_groups,
                'docker_containers': docker_containers,
                'active_streams': active_streams
            },
            'clients': {
                'total': total_clients,
                'active': active_clients
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return {'error': str(e), 'timestamp': time.time()}

# Main routes
@app.route('/')
def home():
    """Home endpoint with system information"""
    return jsonify({
        "status": "running", 
        "message": "Multi-Screen SRT Control Server - REST API",
        "server_info": {
            "upload_folder": app.config['UPLOAD_FOLDER'],
            "download_folder": app.config['DOWNLOAD_FOLDER'],
            "version": "3.0.0",
            "features": [
                "Group Management",
                "Multi-Container Docker Support", 
                "Per-Group SRT Streaming",
                "Dynamic Port Assignment",
                "Client Group Assignment",
                "REST API Only"
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
        return jsonify(get_system_status()), 200
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

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Endpoint not found",
        "message": "The requested endpoint does not exist",
        "available_endpoints": [
            "/", "/ping", "/system_status", "/api/health",
            "/get_groups", "/create_group", "/get_clients", "/assign_stream",
            "/start_group_docker", "/stop_group_docker", 
            "/start_group_complete", "/stop_group_complete",
            "/get_videos", "/delete_group"
        ]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "error": "Internal server error",
        "message": "An unexpected error occurred",
        "timestamp": time.time()
    }), 500

# Cleanup function for graceful shutdown
def cleanup_on_shutdown():
    """Clean up resources on application shutdown"""
    try:
        logger.info("Performing cleanup on shutdown...")
        save_config(state)
        logger.info("Saved configuration")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

# Register cleanup function
import atexit
atexit.register(cleanup_on_shutdown)

if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("Starting Multi-Screen SRT Control Server - REST API Only")
    logger.info("=" * 60)
    logger.info(f"Groups initialized: {hasattr(state, 'groups')}")
    logger.info(f"Total groups: {len(getattr(state, 'groups', {}))}")
    logger.info(f"SRT IP: {getattr(state, 'srt_ip', 'Not set')}")
    logger.info(f"API Type: REST Only")
    logger.info("=" * 60)
    
    # Run with regular Flask (no SocketIO)
    app.run(host='0.0.0.0', port=5000, debug=True)