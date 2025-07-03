# blueprints/docker_management.py - Updated with Group Support
"""
Modified docker_management.py to support multiple groups with separate Docker containers
while maintaining the exact Docker command structure from the readme.
"""

from flask import Blueprint, request, jsonify
import subprocess
import logging
import traceback
import shlex
from typing import Dict, List, Any, Tuple, Optional

# Configure logger
logger = logging.getLogger(__name__)

# Get current application state from app context
def get_state():
    from flask import current_app
    return current_app.config['APP_STATE']

# Create blueprint
docker_bp = Blueprint('docker_management', __name__)

def run_command(cmd: List[str], timeout: int = 30) -> Tuple[bool, str, str]:
    """
    Run a command securely and return its output
    
    Args:
        cmd: Command as a list of strings
        timeout: Timeout in seconds
        
    Returns:
        Tuple of (success, stdout, stderr)
    """
    try:
        # Execute command with timeout
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout
        )
        
        success = result.returncode == 0
        return success, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "", f"Command timed out after {timeout} seconds"
    except Exception as e:
        return False, "", f"Error executing command: {str(e)}"

def calculate_group_ports(group_id: str, groups: Dict[str, Any]) -> Dict[str, int]:
    """
    Calculate port assignments for a group based on its position
    
    Args:
        group_id: The group ID
        groups: Dictionary of all groups
        
    Returns:
        Dictionary with port assignments
    """
    # Sort group IDs to ensure consistent port assignment
    sorted_group_ids = sorted(groups.keys())
    
    try:
        group_index = sorted_group_ids.index(group_id)
    except ValueError:
        group_index = 0
    
    # Base port calculation: each group gets a block of 10 ports
    base_port_offset = group_index * 10
    
    return {
        "rtmp_port": 1935 + base_port_offset,      # 1935, 1945, 1955, etc.
        "http_port": 1985 + base_port_offset,      # 1985, 1995, 2005, etc.
        "api_port": 8080 + base_port_offset,       # 8080, 8090, 8100, etc.
        "srt_port": 10080 + base_port_offset       # 10080, 10090, 10100, etc.
    }

@docker_bp.route("/start_group_docker", methods=["POST"])
def start_group_docker():
    """Start a Docker container for a specific group"""
    try:
        # Get the app state
        state = get_state()
        
        # Get group ID from request
        data = request.get_json() or {}
        group_id = data.get("group_id")
        
        if not group_id:
            return jsonify({"error": "Missing group_id parameter"}), 400
            
        # Initialize groups if needed
        if not hasattr(state, 'groups'):
            state.groups = {}
            
        if group_id not in state.groups:
            return jsonify({"error": f"Group {group_id} not found"}), 404
            
        # Check if Docker is available
        success, docker_version, error = run_command(["docker", "--version"])
        if not success:
            logger.error(f"Docker not available: {error}")
            return jsonify({
                "error": "Docker is not available on this system",
                "details": error
            }), 500
        
        # Get group data and calculate ports
        group = state.groups[group_id]
        group_name = group.get("name", group_id)
        ports = calculate_group_ports(group_id, state.groups)
        
        # Check if group already has a running container
        existing_container_id = group.get("docker_container_id")
        if existing_container_id:
            # Check if container is still running
            check_cmd = ["docker", "ps", "-q", "--filter", f"id={existing_container_id}"]
            success, output, _ = run_command(check_cmd)
            if success and output.strip():
                return jsonify({
                    "message": f"Group '{group_name}' already has a running Docker container",
                    "container_id": existing_container_id,
                    "ports": ports
                }), 200
        
        # Command to run the SRT Docker container for this group
        # Using the exact structure from the readme but with group-specific ports
        container_name = f"srs-group-{group_id[:8]}"  # Use first 8 chars of group ID
        
        cmd = [
            "docker", "run", 
            "--rm", 
            "-d",  # Run in detached mode
            "--name", container_name,  # Give it a specific name
            "-p", f"{ports['rtmp_port']}:1935",     # RTMP port mapping
            "-p", f"{ports['http_port']}:1985",     # HTTP port mapping
            "-p", f"{ports['api_port']}:8080",      # API port mapping
            "-p", f"{ports['srt_port']}:10080/udp", # SRT port mapping (UDP)
            "ossrs/srs:5", 
            "./objs/srs", 
            "-c", "conf/srt.conf"
        ]
        
        logger.info(f"Starting Docker container for group '{group_name}' with ports: {ports}")
        logger.info(f"Docker command: {' '.join(cmd)}")
        
        # Run the command
        success, container_id, error = run_command(cmd)
        
        if not success:
            logger.error(f"Failed to start Docker container for group {group_id}: {error}")
            return jsonify({"error": error}), 500
            
        # Update group state
        if not hasattr(state, 'groups_lock'):
            state.groups_lock = threading.RLock()
            
        with state.groups_lock:
            state.groups[group_id]["docker_container_id"] = container_id
            state.groups[group_id]["status"] = "active"
            state.groups[group_id]["ports"] = ports
            state.groups[group_id]["container_name"] = container_name
        
        logger.info(f"Docker container started for group '{group_name}'. ID: {container_id}")
        
        return jsonify({
            "message": f"Docker container started for group '{group_name}'",
            "group_id": group_id,
            "group_name": group_name,
            "container_id": container_id,
            "container_name": container_name,
            "ports": ports
        }), 200
        
    except Exception as e:
        logger.error(f"Error starting Docker for group: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@docker_bp.route("/stop_group_docker", methods=["POST"])
def stop_group_docker():
    """Stop the Docker container for a specific group"""
    try:
        # Get the app state
        state = get_state()
        
        # Get group ID from request
        data = request.get_json() or {}
        group_id = data.get("group_id")
        
        if not group_id:
            return jsonify({"error": "Missing group_id parameter"}), 400
            
        # Initialize groups if needed
        if not hasattr(state, 'groups'):
            state.groups = {}
            
        if group_id not in state.groups:
            return jsonify({"error": f"Group {group_id} not found"}), 404
            
        group = state.groups[group_id]
        group_name = group.get("name", group_id)
        container_id = group.get("docker_container_id")
        
        if not container_id:
            return jsonify({"error": f"No Docker container ID found for group '{group_name}'"}), 400
            
        # Validate container ID format (basic check)
        if not container_id.strip().replace('-', '').isalnum():
            return jsonify({"error": "Invalid container ID format"}), 400
            
        # Stop the container
        success, output, error = run_command(["docker", "stop", container_id])
        
        if not success:
            logger.error(f"Failed to stop Docker container for group {group_id}: {error}")
            return jsonify({"error": error}), 500
            
        # Update group state
        with state.groups_lock if hasattr(state, 'groups_lock') else threading.RLock():
            state.groups[group_id]["docker_container_id"] = None
            state.groups[group_id]["status"] = "inactive"
            state.groups[group_id]["ffmpeg_process_id"] = None  # Also clear FFmpeg process if any
            
        logger.info(f"Docker container stopped for group '{group_name}'. ID: {container_id}")
        
        return jsonify({
            "message": f"Docker container stopped for group '{group_name}'",
            "group_id": group_id,
            "group_name": group_name,
            "container_id": container_id
        }), 200
        
    except Exception as e:
        logger.error(f"Error stopping Docker for group: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


    """Legacy endpoint - stops Docker for the specified container or first group"""
    try:
        state = get_state()
        
        # Try to get container ID from request first
        data = request.get_json(silent=True) or {}
        container_id = data.get("container_id")
        
        if container_id:
            # Legacy mode - stop specific container
            if not container_id.strip().replace('-', '').isalnum():
                return jsonify({"error": "Invalid container ID format"}), 400
                
            success, output, error = run_command(["docker", "stop", container_id])
            
            if not success:
                logger.error(f"Failed to stop Docker container: {error}")
                return jsonify({"error": error}), 500
                
            # Clear from any group that has this container ID
            if hasattr(state, 'groups'):
                for group in state.groups.values():
                    if group.get("docker_container_id") == container_id:
                        group["docker_container_id"] = None
                        group["status"] = "inactive"
                        break
                        
            return jsonify({
                "message": f"Docker container stopped successfully",
                "container_id": container_id
            }), 200
        else:
            # No container ID provided, try to find from groups
            if not hasattr(state, 'groups') or not state.groups:
                return jsonify({"error": "No Docker containers found"}), 400
                
            # Use the first group with a running container
            for group_id, group in state.groups.items():
                if group.get("docker_container_id"):
                    from flask import current_app
                    with current_app.test_request_context(json={"group_id": group_id}):
                        return stop_group_docker()
            
            return jsonify({"error": "No running Docker containers found"}), 400
            
    except Exception as e:
        logger.error(f"Error in legacy stop_docker: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@docker_bp.route("/stop_all_docker", methods=["POST"])
def stop_all_docker():
    """Stop all running Docker containers for all groups"""
    try:
        # Get the app state
        state = get_state()
        
        # Get list of all running containers
        success, container_ids, error = run_command(["docker", "ps", "-q"])
        
        if not success:
            logger.error(f"Failed to list Docker containers: {error}")
            return jsonify({"error": error}), 500
        
        # Parse container IDs (split by newline and remove empty strings)
        container_ids = [cid for cid in container_ids.split('\n') if cid]
        
        if not container_ids:
            logger.info("No running Docker containers found")
            # Clear all container IDs from groups
            if hasattr(state, 'groups'):
                for group in state.groups.values():
                    group["docker_container_id"] = None
                    group["status"] = "inactive"
            return jsonify({"message": "No running Docker containers found"}), 200
        
        # Stop all containers
        stopped_containers = []
        failed_containers = []
        
        for container_id in container_ids:
            success, output, error = run_command(["docker", "stop", container_id])
            
            if success:
                stopped_containers.append(container_id)
                logger.info(f"Docker container stopped. ID: {container_id}")
            else:
                failed_containers.append({"id": container_id, "error": error})
                logger.error(f"Failed to stop container {container_id}: {error}")
        
        # Clear container IDs from all groups
        if hasattr(state, 'groups'):
            with state.groups_lock if hasattr(state, 'groups_lock') else threading.RLock():
                for group in state.groups.values():
                    group["docker_container_id"] = None
                    group["status"] = "inactive"
                    group["ffmpeg_process_id"] = None
        
        return jsonify({
            "message": f"Stopped {len(stopped_containers)} Docker containers",
            "stopped_containers": stopped_containers,
            "failed_containers": failed_containers
        }), 200
        
    except Exception as e:
        logger.error(f"Error stopping all Docker containers: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
