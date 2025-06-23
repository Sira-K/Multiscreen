from flask import Blueprint, request, jsonify
import logging
import traceback
from config import save_config

# Get current application state from app context
def get_state():
    from flask import current_app
    return current_app.config['APP_STATE']

# Create blueprint
screen_bp = Blueprint('screen_management', __name__)

# Configure logger
logger = logging.getLogger(__name__)

@screen_bp.route("/set_screen_ips", methods=["POST"])
def set_screen_ips():
    """Configure screen count, IPs, orientation, and grid layout"""
    try:
        # Get the app state
        state = get_state()
        
        # Parse JSON data
        data = request.get_json()
        if data is None:
            return jsonify({"error": "Invalid JSON data"}), 400
            
        logger.info(f"Screen configuration request: {data}")
        
        # Extract data from the request
        ips = data.get("ips", {})
        new_screen_count = int(data.get("screenCount", 0))
        new_orientation = data.get("orientation", "horizontal")
        new_grid_rows = int(data.get("gridRows", 2))
        new_grid_cols = int(data.get("gridCols", 2))
        
        # Convert numeric keys to strings if needed
        formatted_ips = {str(k): v for k, v in ips.items()}
        
        # Validate data
        if new_screen_count <= 0:
            return jsonify({"error": "Invalid screen count"}), 400
            
        # Validate grid dimensions
        if new_orientation == "grid":
            if new_grid_rows <= 0 or new_grid_cols <= 0:
                return jsonify({"error": "Invalid grid dimensions"}), 400
            
            # For grid layout, ensure screen count matches grid dimensions
            expected_count = new_grid_rows * new_grid_cols
            if new_screen_count != expected_count:
                logger.warning(f"Screen count {new_screen_count} doesn't match grid {new_grid_rows}x{new_grid_cols} = {expected_count}")
                new_screen_count = expected_count
                logger.info(f"Adjusted screen count to {new_screen_count}")
        
        # Update global state
        state.screen_ips = formatted_ips
        state.screen_count = new_screen_count
        state.orientation = new_orientation
        state.grid_rows = new_grid_rows
        state.grid_cols = new_grid_cols
        
        # Save configuration
        if not save_config(state):
            return jsonify({"error": "Failed to save configuration"}), 500
        
        # Build response message
        if new_orientation == "grid":
            layout_description = f"{new_grid_rows}×{new_grid_cols} grid layout ({new_screen_count} screens)"
        else:
            layout_description = f"{new_orientation} layout ({new_screen_count} screens)"
        
        # Return success
        return jsonify({
            "message": f"Screen configuration updated: {layout_description}",
            "screen_count": state.screen_count,
            "orientation": state.orientation,
            "grid_rows": state.grid_rows,
            "grid_cols": state.grid_cols,
            "screen_ips": state.screen_ips,
            "layout_description": layout_description
        }), 200
        
    except Exception as e:
        logger.error(f"Error in set_screen_ips: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@screen_bp.route("/screen_status", methods=["GET"])
def get_screen_status():
    """Get current screen configuration status including grid settings"""
    try:
        # Get the app state
        state = get_state()
        
        # Get current configuration
        screen_count = getattr(state, 'screen_count', 2)
        orientation = getattr(state, 'orientation', 'horizontal')
        grid_rows = getattr(state, 'grid_rows', 2)
        grid_cols = getattr(state, 'grid_cols', 2)
        screen_ips = getattr(state, 'screen_ips', {})
        
        # Build layout description
        if orientation == "grid":
            layout_description = f"{grid_rows}×{grid_cols} grid layout ({screen_count} screens)"
        else:
            layout_description = f"{orientation} layout ({screen_count} screens)"
        
        return jsonify({
            "screen_count": screen_count,
            "orientation": orientation,
            "grid_rows": grid_rows,
            "grid_cols": grid_cols,
            "screen_ips": screen_ips,
            "layout_description": layout_description,
            "effective_screens": grid_rows * grid_cols if orientation == "grid" else screen_count
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting screen status: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@screen_bp.route("/launch_player", methods=["POST"])
def launch_player():
    """Launch a player on a specific screen with grid position support"""
    try:
        # Get the app state
        state = get_state()
        
        # Parse request data
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        screen_id = data.get("screenId")
        stream_url = data.get("streamUrl")
        orientation = data.get("orientation", "horizontal")
        grid_rows = data.get("gridRows", 2)
        grid_cols = data.get("gridCols", 2)
        grid_position = data.get("gridPosition", {})
        
        if not screen_id or not stream_url:
            return jsonify({"error": "Missing screenId or streamUrl"}), 400
        
        logger.info(f"Launching player for screen {screen_id}")
        logger.info(f"Stream URL: {stream_url}")
        logger.info(f"Layout: {orientation}")
        
        if orientation == "grid":
            logger.info(f"Grid layout: {grid_rows}×{grid_cols}")
            if grid_position:
                logger.info(f"Grid position: Row {grid_position.get('row', '?')}, Col {grid_position.get('col', '?')}")
        
        # Get screen IP if configured
        screen_ips = getattr(state, 'screen_ips', {})
        screen_ip = screen_ips.get(str(screen_id))
        
        if screen_ip:
            logger.info(f"Screen IP configured: {screen_ip}")
            # TODO: Implement remote player launch to specific IP
            message = f"Player launch requested for screen {screen_id} at {screen_ip}"
            
            # Build position description
            if orientation == "grid" and grid_position:
                position_desc = f" (Grid R{grid_position.get('row', '?')}C{grid_position.get('col', '?')})"
            else:
                position_desc = f" ({orientation} layout)"
            
            message += position_desc
        else:
            logger.info(f"No IP configured for screen {screen_id}")
            message = f"Player launch requested for screen {screen_id} (no IP configured)"
        
        # For now, just return success - actual player launch implementation would go here
        return jsonify({
            "message": message,
            "screen_id": screen_id,
            "stream_url": stream_url,
            "orientation": orientation,
            "grid_info": {
                "rows": grid_rows,
                "cols": grid_cols,
                "position": grid_position
            } if orientation == "grid" else None,
            "screen_ip": screen_ip
        }), 200
        
    except Exception as e:
        logger.error(f"Error launching player: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500