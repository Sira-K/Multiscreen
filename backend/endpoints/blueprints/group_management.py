# blueprints/group_management.py
"""
Group management with pure Docker discovery architecture.
No internal state - Docker containers are the single source of truth.
"""

from flask import Blueprint, request, jsonify
import logging
import traceback
import time
from typing import Dict, List, Any, Optional

# Create blueprint
group_bp = Blueprint('group_management', __name__)

# Configure logging
logger = logging.getLogger(__name__)

def validate_group_data(data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate group creation data
    
    Args:
        data: The group data to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not data:
        return False, "No JSON data provided"
        
    if not data.get("name"):
        return False, "Missing group name"
        
    if not data.get("name").strip():
        return False, "Group name cannot be empty"
        
    # Validate name format (Docker container names have restrictions)
    name = data.get("name").strip()
    if not name.replace("-", "").replace("_", "").isalnum():
        return False, "Group name can only contain letters, numbers, hyphens, and underscores"
        
    if len(name) > 50:
        return False, "Group name must be 50 characters or less"
        
    return True, None

@group_bp.route("/create_group", methods=["POST"])
def create_group():
    """Create a new group by creating a Docker container"""
    try:
        data = request.get_json() or {}
        
        logger.info(f" CREATE GROUP REQUEST: {data}")
        
        # Validate input data
        is_valid, error_message = validate_group_data(data)
        if not is_valid:
            logger.error(f" Validation failed: {error_message}")
            return jsonify({"error": error_message}), 400
        
        # Extract group data
        group_name = data.get("name").strip()
        description = data.get("description", "").strip()
        screen_count = data.get("screen_count", 2)
        orientation = data.get("orientation", "horizontal")
        streaming_mode = data.get("streaming_mode", "multi_video")

        
        # Validate screen_count
        if not isinstance(screen_count, int) or screen_count < 1 or screen_count > 16:
            return jsonify({"error": "screen_count must be an integer between 1 and 16"}), 400
            
        # Validate orientation
        valid_orientations = ["horizontal", "vertical", "grid"]
        if orientation not in valid_orientations:
            return jsonify({"error": f"orientation must be one of: {valid_orientations}"}), 400
        
        valid_streaming_modes = ["multi_video", "single_video_split"]
        if streaming_mode not in valid_streaming_modes:
            return jsonify({"error": f"streaming_mode must be one of: {valid_streaming_modes}"}), 400
        
        # Prepare group data for Docker creation
        group_data = {
            "name": group_name,
            "description": description,
            "screen_count": screen_count,
            "orientation": orientation,
            "streaming_mode": streaming_mode,
            "created_at": time.time()
        }
        
        logger.info(f" Creating Docker container for group: {group_name}")
        
        # Import and call Docker creation function
        try:
            from blueprints.docker_management import create_docker
            
            # Create Docker container first
            docker_result = create_docker(group_data)
            
            # Check if Docker creation was successful
            if not docker_result.get("success", False):
                error_msg = docker_result.get("error", "Unknown Docker creation error")
                logger.error(f" Docker creation failed: {error_msg}")
                return jsonify({
                    "error": f"Failed to create Docker container: {error_msg}",
                    "details": docker_result
                }), 500
            
            logger.info(f" Docker container created successfully for group: {group_name}")
            
            # Now get the updated groups list from Docker discovery
            groups_result = get_groups_from_docker()
            
            if not groups_result.get("success", False):
                logger.warning(" Group created but failed to retrieve updated groups list")
                # Still return success since Docker container was created
                return jsonify({
                    "message": f"Group '{group_name}' created successfully",
                    "docker_info": docker_result,
                    "warning": "Could not retrieve updated groups list"
                }), 201
            
            # Find the newly created group in the results
            created_group = None
            for group in groups_result.get("groups", []):
                if group.get("name") == group_name:
                    created_group = group
                    break
            
            if created_group:
                logger.info(f" Successfully created and verified group: {group_name}")
                return jsonify({
                    "message": f"Group '{group_name}' created successfully",
                    "group": created_group,
                    "total_groups": len(groups_result.get("groups", []))
                }), 201
            else:
                logger.warning(f" Group created but not found in discovery results")
                return jsonify({
                    "message": f"Group '{group_name}' created successfully",
                    "docker_info": docker_result,
                    "warning": "Group not immediately visible in discovery"
                }), 201
            
        except ImportError as e:
            logger.error(f" Could not import docker_management: {e}")
            return jsonify({
                "error": "Docker management module not available",
                "details": str(e)
            }), 500
        except Exception as e:
            logger.error(f" Error during Docker creation: {e}")
            traceback.print_exc()
            return jsonify({
                "error": f"Failed to create group: {str(e)}",
                "traceback": traceback.format_exc()
            }), 500
        
    except Exception as e:
        logger.error(f" Error in create_group: {e}")
        traceback.print_exc()
        return jsonify({
            "error": f"Error creating group: {str(e)}"
        }), 500

@group_bp.route("/delete_group", methods=["POST"])
def delete_group():
    """Delete a group by stopping streams and removing Docker container"""
    try:
        data = request.get_json() or {}
        group_id = data.get("group_id")
        group_name = data.get("group_name")
        
        logger.info(f" DELETE GROUP REQUEST: group_id={group_id}, group_name={group_name}")
        
        # Need either group_id or group_name
        if not group_id and not group_name:
            return jsonify({"error": "Either group_id or group_name is required"}), 400
        
        # First, get current groups to find the target group
        groups_result = get_groups_from_docker()
        if not groups_result.get("success", False):
            logger.error(" Failed to get current groups for deletion")
            return jsonify({"error": "Could not retrieve current groups"}), 500
        
        # Find the target group
        target_group = None
        for group in groups_result.get("groups", []):
            if (group_id and group.get("id") == group_id) or \
               (group_name and group.get("name") == group_name):
                target_group = group
                break
        
        if not target_group:
            identifier = group_id or group_name
            logger.warning(f" Group not found for deletion: {identifier}")
            return jsonify({"error": f"Group '{identifier}' not found"}), 404
        
        target_name = target_group.get("name", "unknown")
        target_id = target_group.get("id", "unknown")
        
        logger.info(f" Found target group for deletion: {target_name} (ID: {target_id})")
        
        # Step 1: Stop any running streams for this group
        logger.info(f" Stopping streams for group: {target_name}")
        try:
            from blueprints.stream_management import stop_group_streams
            
            # Try to stop streams (don't fail deletion if this fails)
            stop_result = stop_group_streams(target_group)
            if stop_result.get("success"):
                logger.info(f" Streams stopped for group: {target_name}")
            else:
                logger.warning(f" Failed to stop streams, continuing with deletion: {stop_result.get('error')}")
                
        except ImportError:
            logger.warning(" Stream management not available, skipping stream stop")
        except Exception as e:
            logger.warning(f" Error stopping streams, continuing with deletion: {e}")
        
        # Step 2: Delete Docker container
        logger.info(f" Deleting Docker container for group: {target_name}")
        try:
            from blueprints.docker_management import delete_docker
            
            docker_result = delete_docker(target_group)
            
            if not docker_result.get("success", False):
                error_msg = docker_result.get("error", "Unknown Docker deletion error")
                logger.error(f" Docker deletion failed: {error_msg}")
                return jsonify({
                    "error": f"Failed to delete Docker container: {error_msg}",
                    "details": docker_result
                }), 500
            
            logger.info(f" Docker container deleted successfully for group: {target_name}")
            
        except ImportError as e:
            logger.error(f" Could not import docker_management: {e}")
            return jsonify({
                "error": "Docker management module not available",
                "details": str(e)
            }), 500
        except Exception as e:
            logger.error(f" Error during Docker deletion: {e}")
            traceback.print_exc()
            return jsonify({
                "error": f"Failed to delete Docker container: {str(e)}"
            }), 500
        
        # Step 3: Get updated groups list
        logger.info(" Retrieving updated groups list after deletion")
        updated_groups_result = get_groups_from_docker()
        
        if updated_groups_result.get("success", False):
            remaining_groups = updated_groups_result.get("groups", [])
            logger.info(f" Group '{target_name}' deleted successfully. {len(remaining_groups)} groups remaining.")
            
            return jsonify({
                "message": f"Group '{target_name}' deleted successfully",
                "deleted_group": {
                    "id": target_id,
                    "name": target_name
                },
                "remaining_groups": remaining_groups,
                "total_remaining": len(remaining_groups)
            }), 200
        else:
            logger.warning(" Group deleted but failed to retrieve updated groups list")
            return jsonify({
                "message": f"Group '{target_name}' deleted successfully",
                "deleted_group": {
                    "id": target_id,
                    "name": target_name
                },
                "warning": "Could not retrieve updated groups list"
            }), 200
        
    except Exception as e:
        logger.error(f" Error in delete_group: {e}")
        traceback.print_exc()
        return jsonify({
            "error": f"Error deleting group: {str(e)}"
        }), 500

@group_bp.route("/get_groups", methods=["GET"])
def get_groups():
    """Get all groups by discovering them from Docker containers"""
    try:
        logger.info(" GET GROUPS REQUEST - Discovering from Docker")
        
        # Get groups from Docker discovery
        result = get_groups_from_docker()
        
        if result.get("success", False):
            groups = result.get("groups", [])
            logger.info(f" Found {len(groups)} groups from Docker discovery")
            
            return jsonify({
                "groups": groups,
                "total": len(groups),
                "discovery_timestamp": time.time(),
                "source": "docker_discovery"
            }), 200
        else:
            error_msg = result.get("error", "Unknown error during Docker discovery")
            logger.error(f" Docker discovery failed: {error_msg}")
            return jsonify({
                "error": f"Failed to discover groups: {error_msg}",
                "groups": [],
                "total": 0
            }), 500
        
    except Exception as e:
        logger.error(f" Error in get_groups: {e}")
        traceback.print_exc()
        return jsonify({
            "error": f"Error retrieving groups: {str(e)}",
            "groups": [],
            "total": 0
        }), 500

def get_groups_from_docker() -> Dict[str, Any]:
    """
    Helper function to discover groups from Docker containers
    
    Returns:
        Dict with success status, groups list, and any errors
    """
    try:
        from blueprints.docker_management import discover_groups
        
        # Call Docker discovery function
        return discover_groups()
        
    except ImportError as e:
        logger.error(f" Could not import docker_management: {e}")
        return {
            "success": False,
            "error": "Docker management module not available",
            "groups": []
        }
    except Exception as e:
        logger.error(f" Error in Docker discovery: {e}")
        return {
            "success": False,
            "error": str(e),
            "groups": []
        }