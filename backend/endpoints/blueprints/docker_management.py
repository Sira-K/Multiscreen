# backend/endpoints/blueprints/docker_management.py
from flask import Blueprint, request, jsonify, current_app
import subprocess
import logging
import threading
import time
from typing import Dict, List, Any, Tuple, Optional

# Configure logger
logger = logging.getLogger(__name__)

# Create blueprint
docker_bp = Blueprint('docker_management', __name__)

def get_state():
    """Get current application state from app context"""
    return current_app.config['APP_STATE']

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
    Calculate port assignments for a group based on creation order
    
    Args:
        group_id: The group ID
        groups: Dictionary of all groups
        
    Returns:
        Dictionary with port assignments
    """
    # Sort groups by creation time to get stable ordering
    sorted_groups = sorted(
        groups.items(), 
        key=lambda x: x[1].get('created_at', 0)
    )
    
    # Find this group's position in the creation order
    group_index = 0
    for i, (gid, _) in enumerate(sorted_groups):
        if gid == group_id:
            group_index = i
            break
    
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
                    "container_name": group.get("container_name"),
                    "ports": ports
                }), 200
        
        # Create container name using first 8 chars of group ID
        container_name = f"srs-group-{group_id[:8]}"
        
        # Build Docker command exactly as specified in the README
        cmd = [
            "docker", "run", 
            "--rm", 
            "-d",  # Run in detached mode
            "--name", container_name,
            "-p", f"{ports['rtmp_port']}:1935",     # RTMP port mapping
            "-p", f"{ports['http_port']}:1985",     # HTTP port mapping
            "-p", f"{ports['api_port']}:8080",      # API port mapping
            "-p", f"{ports['srt_port']}:10080/udp", # SRT port mapping (UDP)
            "ossrs/srs:5", 
            "./objs/srs", 
            "-c", "conf/srt.conf"
        ]
        
        logger.info(f"🐳 Starting Docker container for group '{group_name}'")
        logger.info(f"📊 Ports: RTMP={ports['rtmp_port']}, HTTP={ports['http_port']}, API={ports['api_port']}, SRT={ports['srt_port']}")
        logger.info(f"🔧 Docker command: {' '.join(cmd)}")
        
        # Run the command
        success, container_id, error = run_command(cmd, timeout=60)
        
        if not success:
            logger.error(f"❌ Failed to start Docker container for group {group_id}: {error}")
            return jsonify({
                "error": f"Failed to start Docker container: {error}",
                "cmd": ' '.join(cmd)
            }), 500
        
        # Verify container is actually running
        time.sleep(2)  # Give container a moment to start
        check_cmd = ["docker", "ps", "-q", "--filter", f"id={container_id}"]
        success, output, _ = run_command(check_cmd)
        
        if not success or not output.strip():
            logger.error(f"❌ Docker container {container_id} failed to start properly")
            return jsonify({
                "error": "Docker container failed to start properly",
                "container_id": container_id
            }), 500
        
        logger.info(f"✅ Docker container started successfully: {container_id[:12]}")
        
        return jsonify({
            "message": f"Docker container started for group '{group_name}'",
            "container_id": container_id,
            "container_name": container_name,
            "ports": ports,
            "status": "running"
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error starting Docker container: {e}")
        return jsonify({
            "error": f"Error starting Docker container: {str(e)}"
        }), 500

@docker_bp.route("/stop_group_docker", methods=["POST"])
def stop_group_docker():
    """Stop a Docker container for a specific group"""
    try:
        # Get group ID from request
        data = request.get_json() or {}
        group_id = data.get("group_id")
        
        if not group_id:
            return jsonify({"error": "Missing group_id parameter"}), 400
        
        state = get_state()
        
        if not hasattr(state, 'groups') or group_id not in state.groups:
            return jsonify({"error": f"Group {group_id} not found"}), 404
        
        group = state.groups[group_id]
        container_id = group.get("docker_container_id")
        
        if not container_id:
            return jsonify({"error": "No Docker container found for this group"}), 400
        
        # Stop the container
        cmd = ["docker", "stop", container_id]
        success, output, error = run_command(cmd)
        
        if not success:
            logger.error(f"Failed to stop Docker container {container_id}: {error}")
            return jsonify({"error": f"Failed to stop container: {error}"}), 500
        
        # Update group state
        with state.groups_lock:
            state.groups[group_id]["docker_container_id"] = None
            state.groups[group_id]["container_name"] = None
            state.groups[group_id]["docker_status"] = "stopped"
            state.groups[group_id]["status"] = "inactive"
        
        logger.info(f"✅ Stopped Docker container for group {group_id}")
        
        return jsonify({
            "message": f"Docker container stopped for group",
            "container_id": container_id
        }), 200
        
    except Exception as e:
        logger.error(f"Error stopping Docker container: {e}")
        return jsonify({"error": f"Error stopping Docker container: {str(e)}"}), 500

@docker_bp.route("/docker/status", methods=["GET"])
def docker_status():
    """Get Docker service status"""
    try:
        # Check if Docker is available
        success, version, error = run_command(["docker", "--version"])
        
        if not success:
            return jsonify({
                "available": False,
                "error": error
            }), 200
        
        # Get running containers
        cmd = ["docker", "ps", "--format", "table {{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}"]
        success, output, error = run_command(cmd)
        
        containers = []
        if success and output:
            lines = output.split('\n')[1:]  # Skip header
            for line in lines:
                if line.strip():
                    parts = line.split('\t')
                    if len(parts) >= 4:
                        containers.append({
                            "id": parts[0],
                            "name": parts[1],
                            "status": parts[2],
                            "ports": parts[3]
                        })
        
        return jsonify({
            "available": True,
            "version": version,
            "running_containers": containers
        }), 200
        
    except Exception as e:
        logger.error(f"Error checking Docker status: {e}")
        return jsonify({
            "available": False,
            "error": f"Error checking Docker status: {str(e)}"
        }), 500