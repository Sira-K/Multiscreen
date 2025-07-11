# blueprints/docker_management.py - Updated with Group Support
"""
Modified docker_management.py to support multiple groups with separate Docker containers
while maintaining the exact Docker command structure from the readme.
"""

from flask import Blueprint, request, jsonify
import subprocess
import logging
import traceback
import threading
import shlex
import time
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
    Calculate port assignments for a group based on creation order
    
    Args:
        group_id: The group ID
        groups: Dictionary of all groups
        
    Returns:
        Dictionary with port assignments
    """
    # Get the group's creation time to determine its index
    group = groups.get(group_id)
    if not group:
        # If group doesn't exist, use index 0
        group_index = 0
    else:
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


def recover_groups_from_docker():
    """Recover group information from running Docker containers with labels"""
    try:
        from app import get_state
        state = get_state()
        
        # Initialize groups if needed
        if not hasattr(state, 'groups'):
            state.groups = {}
        if not hasattr(state, 'groups_lock'):
            state.groups_lock = threading.RLock()
        
        # Find all containers with multi-screen labels
        cmd = [
            "docker", "ps", "-a", 
            "--filter", "label=com.multiscreen.project=multi-screen-display",
            "--format", "{{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Label \"com.multiscreen.group.id\"}}"
        ]
        
        success, output, error = run_command(cmd)
        if not success:
            logger.error(f"Failed to list Docker containers: {error}")
            return {}
        
        recovered_groups = {}
        
        for line in output.strip().split('\n'):
            if not line.strip():
                continue
                
            parts = line.split('\t')
            if len(parts) >= 4:
                container_id = parts[0]
                container_name = parts[1]
                status = parts[2]
                group_id = parts[3]
                
                if group_id and group_id != "<no value>":
                    # Get full container inspect data for all labels
                    inspect_cmd = ["docker", "inspect", container_id, "--format", 
                                 "{{range $key, $value := .Config.Labels}}{{$key}}={{$value}}\n{{end}}"]
                    
                    success, inspect_output, error = run_command(inspect_cmd)
                    if success:
                        labels = {}
                        for label_line in inspect_output.strip().split('\n'):
                            if '=' in label_line and label_line.startswith('com.multiscreen.'):
                                key, value = label_line.split('=', 1)
                                labels[key] = value
                        
                        # Reconstruct group from labels
                        if 'com.multiscreen.group.id' in labels:
                            group = {
                                "id": labels.get('com.multiscreen.group.id'),
                                "name": labels.get('com.multiscreen.group.name', 'Recovered Group'),
                                "description": labels.get('com.multiscreen.group.description', ''),
                                "screen_count": int(labels.get('com.multiscreen.group.screen_count', 2)),
                                "orientation": labels.get('com.multiscreen.group.orientation', 'horizontal'),
                                "created_at": float(labels.get('com.multiscreen.group.created_at', time.time())),
                                "status": "active" if "Up" in status else "inactive",
                                "clients": {},
                                "docker_container_id": container_id,
                                "container_name": container_name,
                                "ffmpeg_process_id": None,
                                "current_video": None,
                                "available_streams": [],
                                "screen_ips": {},
                                "docker_status": "running" if "Up" in status else "stopped",
                                "container_id_short": container_id[:12],
                                "total_clients": 0,
                                "active_clients": 0,
                                "last_activity": time.time(),
                                "created_at_formatted": time.strftime(
                                    "%Y-%m-%d %H:%M:%S", 
                                    time.localtime(float(labels.get('com.multiscreen.group.created_at', time.time())))
                                )
                            }
                            
                            # Extract ports from container
                            port_cmd = ["docker", "port", container_id]
                            success, port_output, error = run_command(port_cmd)
                            if success:
                                ports = {}
                                for port_line in port_output.strip().split('\n'):
                                    if ':' in port_line:
                                        # Format: "10080/udp -> 0.0.0.0:10080"
                                        container_port, host_binding = port_line.split(' -> ')
                                        host_port = int(host_binding.split(':')[-1])
                                        
                                        if '10080' in container_port:
                                            ports['srt_port'] = host_port
                                        elif '1935' in container_port:
                                            ports['rtmp_port'] = host_port
                                        elif '1985' in container_port:
                                            ports['http_port'] = host_port
                                        elif '8080' in container_port:
                                            ports['api_port'] = host_port
                                
                                group["ports"] = ports
                                group["srt_port"] = ports.get('srt_port')
                                group["port_summary"] = f"SRT:{ports.get('srt_port', 'N/A')}"
                            
                            recovered_groups[group_id] = group
                            logger.info(f"Recovered group '{group['name']}' from container {container_id[:12]}")
        
        # Merge recovered groups with existing groups
        with state.groups_lock:
            for group_id, group in recovered_groups.items():
                if group_id not in state.groups:
                    state.groups[group_id] = group
                    logger.info(f"Added recovered group: {group['name']}")
                else:
                    # Update container info for existing groups
                    existing_group = state.groups[group_id]
                    existing_group.update({
                        "docker_container_id": group["docker_container_id"],
                        "container_name": group["container_name"],
                        "docker_status": group["docker_status"],
                        "ports": group["ports"],
                        "srt_port": group["srt_port"],
                        "port_summary": group["port_summary"]
                    })
                    logger.info(f"Updated existing group with container info: {existing_group['name']}")
        
        logger.info(f"Recovered {len(recovered_groups)} groups from Docker containers")
        return recovered_groups
        
    except Exception as e:
        logger.error(f"Error recovering groups from Docker: {e}")
        traceback.print_exc()
        return {}
    

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
                    "ports": ports,
                    "status": group.get("status", "inactive")
                }), 200
            else:
                # Clear stale container ID
                group["docker_container_id"] = None
        
        # Command to run the SRT Docker container for this group
        # Using the exact structure from the readme but with group-specific ports
        container_name = f"srt-server-{group_name.lower().replace(' ', '-')}-{group_id[:8]}"
       
        labels = {
            "com.multiscreen.group.id": group_id,
            "com.multiscreen.group.name": group_name,
            "com.multiscreen.group.description": group.get("description", ""),
            "com.multiscreen.group.screen_count": str(group.get("screen_count", 2)),
            "com.multiscreen.group.orientation": group.get("orientation", "horizontal"),
            "com.multiscreen.group.created_at": str(group.get("created_at", time.time())),
            "com.multiscreen.project": "multi-screen-display",
            "com.multiscreen.version": "1.0"
        }

        cmd = [
            "docker", "run",
            "-d",  # Detached mode
            "--name", container_name,
            "--rm",  # Remove container when stopped
        ]

        for key, value in labels.items():
            cmd.extend(["--label", f"{key}={value}"])

        cmd.extend([
            "-p", f"{ports['rtmp_port']}:1935",     # RTMP port mapping
            "-p", f"{ports['http_port']}:1985",     # HTTP port mapping
            "-p", f"{ports['api_port']}:8080",      # API port mapping
            "-p", f"{ports['srt_port']}:10080/udp", # SRT port mapping (UDP)
            "ossrs/srs:5", 
            "./objs/srs", 
            "-c", "conf/srt.conf"
        ])

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
            # Store Docker container info
            state.groups[group_id]["docker_container_id"] = container_id
            state.groups[group_id]["ports"] = ports
            state.groups[group_id]["container_name"] = container_name
            
            # 🔥 CRITICAL: Only set status to "active" if SRT stream is also running
            # Docker alone should NOT make the group "active"
            if state.groups[group_id].get("ffmpeg_process_id"):
                # SRT is already running, so group should be active
                state.groups[group_id]["status"] = "active"
                logger.info(f"Group '{group_name}' status set to 'active' (Docker + SRT running)")
            else:
                # No SRT running, keep status as inactive (Docker is just infrastructure)
                state.groups[group_id]["status"] = "inactive"
                logger.info(f"Group '{group_name}' status kept as 'inactive' (Docker ready, no SRT)")
        
        current_status = state.groups[group_id]["status"]
        logger.info(f"Docker container started for group '{group_name}'. Container ID: {container_id}")
        
        return jsonify({
            "message": f"Docker container started for group '{group_name}'",
            "group_id": group_id,
            "group_name": group_name,
            "container_id": container_id,
            "container_name": container_name,
            "ports": ports,
            "status": current_status,
            "docker_running": True,
            "srt_running": bool(state.groups[group_id].get("ffmpeg_process_id"))
        }), 200
        
    except Exception as e:
        logger.error(f"Error starting Docker for group: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@docker_bp.route("/recover_groups", methods=["POST"])
def recover_groups():
    """Recover groups from Docker containers with labels"""
    try:
        recovered = recover_groups_from_docker()
        
        return jsonify({
            "message": f"Recovered {len(recovered)} groups from Docker containers",
            "recovered_groups": list(recovered.keys()),
            "groups": recovered
        }), 200
        
    except Exception as e:
        logger.error(f"Error in recover_groups endpoint: {e}")
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
