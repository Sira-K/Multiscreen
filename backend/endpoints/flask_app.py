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
    from .blueprints.stream_management import stream_bp
    from .blueprints.docker_management import docker_bp
    from .blueprints.split_screen_bp import split_screen_bp
except ImportError:
    # Fallback for direct execution
    from app_config import AppConfig
    from blueprints.group_management import group_bp
    from blueprints.video_management import video_bp
    from blueprints.client_management import client_bp
    from blueprints.stream_management import stream_bp
    from blueprints.docker_management import docker_bp
    from blueprints.split_screen_bp import split_screen_bp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    
    # Create uploads directory
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Register blueprints
    app.register_blueprint(group_bp)
    app.register_blueprint(video_bp)
    app.register_blueprint(client_bp, url_prefix='/api/clients')
    app.register_blueprint(stream_bp)
    app.register_blueprint(docker_bp)
    app.register_blueprint(split_screen_bp, url_prefix='/api/split_screen')
    
    # Root endpoint
    @app.route('/')
    def index():
        return jsonify({
            "api_endpoints": {
                "clients": "/api/clients",
                "docker": "/api/docker",
                "groups": "/api/groups",
                "streams": "/api/streams",
                "videos": "/api/videos",
                "split_screen": "/api/split_screen"
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