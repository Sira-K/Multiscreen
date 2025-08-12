"""
Split Screen Blueprint

Simple split-screen streaming endpoints using the new service architecture.
"""

from flask import Blueprint, request, jsonify
import logging

# Create blueprint
split_screen_bp = Blueprint('split_screen_stream', __name__)

# Configure logger
logger = logging.getLogger(__name__)

@split_screen_bp.route("/start_split_screen_srt", methods=["POST"])
def start_split_screen_srt():
    """Start split-screen streaming (legacy endpoint for compatibility)"""
    try:
        data = request.get_json() or {}
        
        group_id = data.get("group_id")
        video_file = data.get("video_file")
        
        if not group_id or not video_file:
            return jsonify({"error": "group_id and video_file are required"}), 400
        
        # For now, return a message directing users to the new endpoint
        return jsonify({
            "message": "This endpoint is deprecated. Please use /start_split_screen instead.",
            "new_endpoint": "/start_split_screen",
            "status": "deprecated"
        }), 200
        
    except Exception as e:
        logger.error(f"Split-screen start error: {e}")
        return jsonify({"error": str(e)}), 500

@split_screen_bp.route("/health", methods=["GET"])
def health():
    """Health check for split-screen blueprint"""
    return jsonify({
        "status": "healthy",
        "blueprint": "split_screen",
        "endpoints": [
            "/start_split_screen_srt (deprecated)",
            "/health"
        ]
    })
