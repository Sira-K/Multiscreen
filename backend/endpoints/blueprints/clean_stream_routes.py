"""
Clean Stream Routes

Simple, clean Flask routes for stream management using the new service architecture.
"""

from flask import Blueprint, request, jsonify
import logging
from ..services.stream_controller import StreamController

logger = logging.getLogger(__name__)

# Create blueprint
stream_routes = Blueprint('stream_routes', __name__)

# Initialize controller
stream_controller = StreamController()


@stream_routes.route("/start_split_screen", methods=["POST"])
def start_split_screen():
    """Start split-screen streaming"""
    try:
        data = request.get_json() or {}
        
        # Extract parameters
        group_id = data.get("group_id")
        video_file = data.get("video_file")
        
        # Optional parameters
        orientation = data.get("orientation", "horizontal")
        grid_rows = data.get("grid_rows", 2)
        grid_cols = data.get("grid_cols", 2)
        framerate = data.get("framerate", 30)
        bitrate = data.get("bitrate", "3000k")
        sei = data.get("sei")
        
        # Start stream
        result = stream_controller.start_split_screen_stream(
            group_id=group_id,
            video_file=video_file,
            orientation=orientation,
            grid_rows=grid_rows,
            grid_cols=grid_cols,
            framerate=framerate,
            bitrate=bitrate,
            sei=sei
        )
        
        if "error" in result:
            return jsonify(result), 400
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Split-screen start error: {e}")
        return jsonify({"error": str(e)}), 500


@stream_routes.route("/start_multi_video", methods=["POST"])
def start_multi_video():
    """Start multi-video streaming"""
    try:
        data = request.get_json() or {}
        
        # Extract parameters
        group_id = data.get("group_id")
        video_files = data.get("video_files")
        
        # Optional parameters
        layout = data.get("layout", "grid")
        framerate = data.get("framerate", 30)
        bitrate = data.get("bitrate", "3000k")
        sei = data.get("sei")
        
        # Start stream
        result = stream_controller.start_multi_video_stream(
            group_id=group_id,
            video_files=video_files,
            layout=layout,
            framerate=framerate,
            bitrate=bitrate,
            sei=sei
        )
        
        if "error" in result:
            return jsonify(result), 400
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Multi-video start error: {e}")
        return jsonify({"error": str(e)}), 500


@stream_routes.route("/stop_stream", methods=["POST"])
def stop_stream():
    """Stop streaming for a group"""
    try:
        data = request.get_json() or {}
        group_id = data.get("group_id")
        
        if not group_id:
            return jsonify({"error": "group_id is required"}), 400
        
        # Stop stream
        result = stream_controller.stop_group_stream(group_id)
        
        if "error" in result:
            return jsonify(result), 400
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Stop stream error: {e}")
        return jsonify({"error": str(e)}), 500


@stream_routes.route("/stream_status/<group_id>", methods=["GET"])
def get_stream_status(group_id):
    """Get streaming status for a group"""
    try:
        if not group_id:
            return jsonify({"error": "group_id is required"}), 400
        
        # Get status
        result = stream_controller.stream_manager.get_stream_status(group_id)
        
        if "error" in result:
            return jsonify(result), 400
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Get status error: {e}")
        return jsonify({"error": str(e)}), 500


@stream_routes.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "stream_management",
        "version": "2.0.0"
    }), 200
