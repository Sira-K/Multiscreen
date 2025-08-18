"""
Multi-Screen Display Server

A Flask-based server for managing multi-screen video streaming.
"""

import os
import time
import threading
import logging
from flask import Flask, jsonify
from flask_cors import CORS

# Handle imports for both direct execution and module import
try:
    from .app_config import AppConfig
    from .blueprints.group_management import group_bp
    from .blueprints.video_management import video_bp
    from .blueprints.client_management import client_bp
    from .blueprints.streaming import multi_stream_bp, split_stream_bp
    from .blueprints.docker_management import docker_bp
except ImportError:
    # Fallback for direct execution
    from app_config import AppConfig
    from blueprints.group_management import group_bp
    from blueprints.video_management import video_bp
    from blueprints.client_management import client_bp
    from blueprints.streaming import multi_stream_bp, split_stream_bp
    from blueprints.docker_management import docker_bp


def clear_all_logs():
    """Clear all log files when server starts"""
    try:
        logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
        if os.path.exists(logs_dir):
            log_files = [
                'all.log',
                'errors.log', 
                'ffmpeg.log',
                'clients.log',
                'streaming.log',
                'system.log'
            ]
            
            for log_file in log_files:
                log_path = os.path.join(logs_dir, log_file)
                if os.path.exists(log_path):
                    # Clear the file content
                    with open(log_path, 'w') as f:
                        f.write(f"# Log file cleared at server startup: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"# Server session started\n")
                        f.write("=" * 80 + "\n\n")
                    print(f"Cleared log file: {log_file}")
    except Exception as e:
        print(f"Warning: Could not clear log files: {e}")

# Configure comprehensive logging
try:
    from logging_config import setup_comprehensive_logging
    logger = setup_comprehensive_logging()
    
    # Clear all logs at startup
    clear_all_logs()
    
    logger.info("Enhanced logging system initialized")
    logger.info("All previous log files cleared for new server session")
except ImportError:
    # Fallback to basic logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.warning("Enhanced logging not available, using basic logging")

def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    
    # Enable CORS for all routes
    CORS(app, resources={
        r"/*": {
            "origins": [
                "http://localhost:3000",           # React dev server
                "http://127.0.0.1:3000",          # React dev server alternative
                "http://localhost:5173",           # Vite dev server
                "http://127.0.0.1:5173",          # Vite dev server alternative
                "http://128.205.39.64:3000",      # Your server's frontend
                "http://128.205.39.64:5173",      # Your server's frontend alternative
                "*"                               # Allow all origins (for development)
            ],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
            "supports_credentials": True
        }
    })
    
    # Load configuration
    config = AppConfig()
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
    app.config['UNIFIED_CONFIG'] = config
    
    # Initialize persistent client state
    from blueprints.client_management.client_state import get_persistent_state
    app.config['APP_STATE'] = get_persistent_state()
    
    # Create uploads directory
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Register blueprints
    app.register_blueprint(group_bp)
    app.register_blueprint(video_bp)
    app.register_blueprint(client_bp, url_prefix='/api/clients')
    app.register_blueprint(multi_stream_bp, url_prefix='/api/streaming')
    app.register_blueprint(split_stream_bp, url_prefix='/api/streaming')
    
    # Add backward compatibility routes (without prefix) with unique names
    app.register_blueprint(multi_stream_bp, url_prefix='', name='multi_stream_legacy')
    app.register_blueprint(split_stream_bp, url_prefix='', name='split_stream_legacy')
    app.register_blueprint(docker_bp)

    
    # Root endpoint
    @app.route('/')
    def index():
        return jsonify({
            "api_endpoints": {
                "clients": "/api/clients",
                "docker": "/api/docker",
                "groups": "/api/groups",
                "multi_stream": "/api/streaming/start_multi_video_srt",
                "split_stream": "/api/streaming/start_split_screen_srt",
                "streaming_status": "/api/streaming/all_streaming_statuses",
                "stop_stream": "/api/streaming/stop_group_stream",
                "videos": "/api/videos",

            },
            "status": "running",
            "version": "2.0.0"
        })
    
    # Health check endpoint
    @app.route('/health')
    def health():
        return jsonify({
            "status": "healthy",
            "timestamp": time.time(),
            "service": "multi_screen_server"
        })
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Endpoint not found"}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({"error": "Internal server error"}), 500
    
    return app

# Create app instance
app = create_app()

if __name__ == '__main__':
    logger.info("Starting Multi-Screen Display Server...")
    logger.info(f"Server config: 0.0.0.0:5000, debug=True")
    
    # Run the app
    app.run(host='0.0.0.0', port=5000, debug=True)