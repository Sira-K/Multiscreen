# blueprints/docker_management.py
"""
Docker management functions for pure Docker discovery architecture.
Provides create_docker, delete_docker, and discover_groups functions.
"""

from flask import Blueprint
import subprocess
import logging
import traceback
import json
import time
import uuid
from typing import Dict, List, Any, Tuple, Optional

# Configure logger
logger = logging.getLogger(__name__)

# Create blueprint for any remaining endpoints
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
        logger.debug(f"🔧 Running command: {' '.join(cmd)}")
        
        # Execute command with timeout
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout
        )
        
        success = result.returncode == 0
        if not success:
            logger.warning(f"⚠️ Command failed with return code {result.returncode}: {' '.join(cmd)}")
            
        return success, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        logger.error(f"⏰ Command timed out after {timeout} seconds: {' '.join(cmd)}")
        return False, "", f"Command timed out after {timeout} seconds"
    except Exception as e:
        logger.error(f"❌ Error executing command: {e}")
        return False, "", f"Error executing command: {str(e)}"

def calculate_group_ports(group_index: int) -> Dict[str, int]:
    """
    Calculate port assignments for a group based on its index
    
    Args:
        group_index: The group's position in creation order (0-based)
        
    Returns:
        Dictionary with port assignments
    """
    # Base port calculation: each group gets a block of 10 ports
    base_port_offset = group_index * 10
    
    return {
        "rtmp_port": 1935 + base_port_offset,      # 1935, 1945, 1955, etc.
        "http_port": 1985 + base_port_offset,      # 1985, 1995, 2005, etc.
        "api_port": 8080 + base_port_offset,       # 8080, 8090, 8100, etc.
        "srt_port": 10080 + base_port_offset       # 10080, 10090, 10100, etc.
    }

def get_next_available_ports() -> Dict[str, int]:
    """
    Get the next available port block by checking existing containers
    
    Returns:
        Dictionary with port assignments for the new group
    """
    try:
        # Get all existing containers with our labels
        discovery_result = discover_groups()
        
        if not discovery_result.get("success", False):
            logger.warning("⚠️ Could not discover existing groups, using default ports")
            return calculate_group_ports(0)
        
        existing_groups = discovery_result.get("groups", [])
        
        if not existing_groups:
            logger.info("📊 No existing groups found, using first port block")
            return calculate_group_ports(0)
        
        # Find the highest port offset in use
        max_offset = 0
        for group in existing_groups:
            ports = group.get("ports", {})
            if ports:
                srt_port = ports.get("srt_port", 10080)
                current_offset = srt_port - 10080
                max_offset = max(max_offset, current_offset)
        
        # Use the next available offset
        next_index = (max_offset // 10) + 1
        
        logger.info(f"📊 Next available port index: {next_index}")
        return calculate_group_ports(next_index)
        
    except Exception as e:
        logger.error(f"❌ Error calculating ports: {e}")
        # Fallback to default ports
        return calculate_group_ports(0)

def create_docker(group_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a Docker container for a group
    
    Args:
        group_data: Group information including name, description, etc.
        
    Returns:
        Dict with success status, container info, and any errors
    """
    try:
        logger.info(f"🐳 Creating Docker container for group: {group_data.get('name')}")
        
        # Check if Docker is available
        success, docker_version, error = run_command(["docker", "--version"])
        if not success:
            logger.error(f"❌ Docker not available: {error}")
            return {
                "success": False,
                "error": "Docker is not available on this system",
                "details": error
            }
        
        logger.info(f"✅ Docker available: {docker_version}")
        
        # Generate unique container ID and name
        group_name = group_data.get("name", "unnamed_group")
        group_id = str(uuid.uuid4())
        container_name = f"srs-group-{group_name.lower().replace(' ', '-').replace('_', '-')}-{group_id[:8]}"
        
        # Check if container with similar name already exists
        existing_check_cmd = ["docker", "ps", "-a", "--filter", f"name={container_name}", "--format", "{{.Names}}"]
        success, existing_output, _ = run_command(existing_check_cmd)
        
        if success and existing_output.strip():
            logger.error(f"❌ Container with similar name already exists: {container_name}")
            return {
                "success": False,
                "error": f"Container with similar name already exists: {container_name}",
                "existing_container": existing_output.strip()
            }
        
        # Get port assignments
        ports = get_next_available_ports()
        
        # Prepare Docker labels for group metadata
        labels = {
            "com.multiscreen.project": "multi-screen-display",
            "com.multiscreen.group.id": group_id,
            "com.multiscreen.group.name": group_name,
            "com.multiscreen.group.description": group_data.get("description", ""),
            "com.multiscreen.group.screen_count": str(group_data.get("screen_count", 2)),
            "com.multiscreen.group.orientation": group_data.get("orientation", "horizontal"),
            "com.multiscreen.group.created_at": str(group_data.get("created_at", time.time())),
            "com.multiscreen.ports.rtmp": str(ports["rtmp_port"]),
            "com.multiscreen.ports.http": str(ports["http_port"]),
            "com.multiscreen.ports.api": str(ports["api_port"]),
            "com.multiscreen.ports.srt": str(ports["srt_port"])
        }
        
        # Build Docker command - following the exact structure from README
        docker_cmd = [
            "docker", "run",
            "--rm",  # Remove container when it stops
            "-d",    # Run in detached mode
            "--name", container_name,
            # Port mappings
            "-p", f"{ports['rtmp_port']}:1935",
            "-p", f"{ports['http_port']}:1985", 
            "-p", f"{ports['api_port']}:8080",
            "-p", f"{ports['srt_port']}:10080/udp"
        ]
        
        # Add labels
        for key, value in labels.items():
            docker_cmd.extend(["--label", f"{key}={value}"])
        
        # Add SRS image and config
        docker_cmd.extend([
            "ossrs/srs:5",
            "./objs/srs", "-c", "conf/srt.conf"
        ])
        
        logger.info(f"🚀 Starting Docker container: {container_name}")
        logger.debug(f"🔧 Docker command: {' '.join(docker_cmd)}")
        
        # Execute Docker command
        success, container_id_output, error = run_command(docker_cmd, timeout=60)
        
        if not success:
            logger.error(f"❌ Failed to start Docker container: {error}")
            return {
                "success": False,
                "error": f"Failed to start Docker container: {error}",
                "command": " ".join(docker_cmd)
            }
        
        container_id = container_id_output.strip()
        logger.info(f"✅ Docker container started successfully")
        logger.info(f"📦 Container ID: {container_id}")
        logger.info(f"🏷️ Container Name: {container_name}")
        logger.info(f"🔌 Ports: RTMP={ports['rtmp_port']}, HTTP={ports['http_port']}, API={ports['api_port']}, SRT={ports['srt_port']}")
        
        # Wait a moment for container to fully start
        time.sleep(2)
        
        # Verify container is running
        verify_cmd = ["docker", "ps", "--filter", f"id={container_id}", "--format", "{{.Status}}"]
        success, status_output, _ = run_command(verify_cmd)
        
        container_status = "unknown"
        if success and status_output.strip():
            container_status = status_output.strip()
            logger.info(f"📊 Container status: {container_status}")
        
        return {
            "success": True,
            "message": f"Docker container created successfully for group '{group_name}'",
            "container_id": container_id,
            "container_name": container_name,
            "group_id": group_id,
            "group_name": group_name,
            "ports": ports,
            "status": container_status,
            "labels": labels
        }
        
    except Exception as e:
        logger.error(f"❌ Error creating Docker container: {e}")
        traceback.print_exc()
        return {
            "success": False,
            "error": f"Error creating Docker container: {str(e)}",
            "traceback": traceback.format_exc()
        }

def delete_docker(group_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Delete a Docker container for a group
    
    Args:
        group_data: Group information including container_id or container_name
        
    Returns:
        Dict with success status and any errors
    """
    try:
        group_name = group_data.get("name", "unknown")
        container_id = group_data.get("container_id")
        container_name = group_data.get("container_name")
        
        logger.info(f"🗑️ Deleting Docker container for group: {group_name}")
        
        # Need either container_id or container_name to delete
        if not container_id and not container_name:
            logger.error("❌ No container_id or container_name provided for deletion")
            return {
                "success": False,
                "error": "No container_id or container_name provided for deletion"
            }
        
        # Use container_id if available, otherwise use container_name
        target = container_id if container_id else container_name
        target_type = "ID" if container_id else "name"
        
        logger.info(f"🎯 Target container {target_type}: {target}")
        
        # Check if container exists and get its status
        check_cmd = ["docker", "ps", "-a", "--filter", f"{'id' if container_id else 'name'}={target}", 
                    "--format", "{{.ID}}\t{{.Names}}\t{{.Status}}"]
        
        success, check_output, error = run_command(check_cmd)
        
        if not success:
            logger.error(f"❌ Failed to check container status: {error}")
            return {
                "success": False,
                "error": f"Failed to check container status: {error}"
            }
        
        if not check_output.strip():
            logger.warning(f"⚠️ Container not found: {target}")
            return {
                "success": True,  # Consider this success since container doesn't exist
                "message": f"Container {target} not found (may already be deleted)",
                "warning": "Container not found"
            }
        
        # Parse container info
        container_info = check_output.strip().split('\t')
        actual_container_id = container_info[0]
        actual_container_name = container_info[1]
        current_status = container_info[2] if len(container_info) > 2 else "unknown"
        
        logger.info(f"📋 Found container: {actual_container_name} (ID: {actual_container_id}) - Status: {current_status}")
        
        # Stop container if it's running
        if "Up" in current_status:
            logger.info(f"🛑 Stopping running container: {actual_container_name}")
            
            stop_cmd = ["docker", "stop", actual_container_id]
            success, stop_output, stop_error = run_command(stop_cmd, timeout=30)
            
            if not success:
                logger.error(f"❌ Failed to stop container: {stop_error}")
                return {
                    "success": False,
                    "error": f"Failed to stop container: {stop_error}",
                    "container_id": actual_container_id,
                    "container_name": actual_container_name
                }
            
            logger.info(f"✅ Container stopped successfully")
        
        # Remove container (this will work whether it's stopped or already exited)
        logger.info(f"🗑️ Removing container: {actual_container_name}")
        
        remove_cmd = ["docker", "rm", actual_container_id]
        success, remove_output, remove_error = run_command(remove_cmd)
        
        if not success:
            # If rm fails, try with force flag
            logger.warning(f"⚠️ Normal remove failed, trying force remove: {remove_error}")
            
            force_remove_cmd = ["docker", "rm", "-f", actual_container_id]
            success, remove_output, remove_error = run_command(force_remove_cmd)
            
            if not success:
                logger.error(f"❌ Failed to remove container even with force: {remove_error}")
                return {
                    "success": False,
                    "error": f"Failed to remove container: {remove_error}",
                    "container_id": actual_container_id,
                    "container_name": actual_container_name
                }
        
        logger.info(f"✅ Container removed successfully")
        logger.info(f"🎉 Docker container deletion completed for group: {group_name}")
        
        return {
            "success": True,
            "message": f"Docker container deleted successfully for group '{group_name}'",
            "container_id": actual_container_id,
            "container_name": actual_container_name,
            "group_name": group_name
        }
        
    except Exception as e:
        logger.error(f"❌ Error deleting Docker container: {e}")
        traceback.print_exc()
        return {
            "success": False,
            "error": f"Error deleting Docker container: {str(e)}",
            "traceback": traceback.format_exc()
        }

def discover_groups() -> Dict[str, Any]:
    """
    Discover all groups by querying Docker containers with multi-screen labels
    
    Returns:
        Dict with success status, groups list, and any errors
    """
    try:
        logger.info("🔍 Discovering groups from Docker containers")
        
        # Check if Docker is available
        success, docker_version, error = run_command(["docker", "--version"])
        if not success:
            logger.error(f"❌ Docker not available: {error}")
            return {
                "success": False,
                "error": "Docker is not available on this system",
                "groups": []
            }
        
        # Find all containers with multi-screen labels
        cmd = [
            "docker", "ps", "-a",
            "--filter", "label=com.multiscreen.project=multi-screen-display",
            "--format", "{{.ID}}\t{{.Names}}\t{{.Status}}\t{{.CreatedAt}}"
        ]
        
        success, output, error = run_command(cmd)
        if not success:
            logger.error(f"❌ Failed to list Docker containers: {error}")
            return {
                "success": False,
                "error": f"Failed to list Docker containers: {error}",
                "groups": []
            }
        
        if not output.strip():
            logger.info("📋 No multi-screen containers found")
            return {
                "success": True,
                "message": "No groups found",
                "groups": [],
                "total": 0
            }
        
        groups = []
        
        for line in output.strip().split('\n'):
            if not line.strip():
                continue
                
            parts = line.split('\t')
            if len(parts) >= 3:
                container_id = parts[0]
                container_name = parts[1]
                status = parts[2]
                created_at = parts[3] if len(parts) > 3 else "unknown"
                
                logger.debug(f"🔍 Processing container: {container_name} ({container_id[:12]})")
                
                # Get all labels for this container
                inspect_cmd = [
                    "docker", "inspect", container_id,
                    "--format", "{{range $key, $value := .Config.Labels}}{{$key}}={{$value}}\n{{end}}"
                ]
                
                success, inspect_output, inspect_error = run_command(inspect_cmd)
                if not success:
                    logger.warning(f"⚠️ Failed to inspect container {container_id}: {inspect_error}")
                    continue
                
                # Parse labels
                labels = {}
                for label_line in inspect_output.strip().split('\n'):
                    if '=' in label_line and label_line.startswith('com.multiscreen.'):
                        key, value = label_line.split('=', 1)
                        labels[key] = value
                
                # Extract group information from labels
                group_id = labels.get('com.multiscreen.group.id', container_id)
                group_name = labels.get('com.multiscreen.group.name', container_name.replace('srs-group-', ''))
                description = labels.get('com.multiscreen.group.description', '')
                screen_count = int(labels.get('com.multiscreen.group.screen_count', 2))
                orientation = labels.get('com.multiscreen.group.orientation', 'horizontal')
                created_timestamp = float(labels.get('com.multiscreen.group.created_at', time.time()))
                
                # Extract port information
                ports = {
                    'rtmp_port': int(labels.get('com.multiscreen.ports.rtmp', 1935)),
                    'http_port': int(labels.get('com.multiscreen.ports.http', 1985)),
                    'api_port': int(labels.get('com.multiscreen.ports.api', 8080)),
                    'srt_port': int(labels.get('com.multiscreen.ports.srt', 10080))
                }
                
                # Determine container status
                is_running = "Up" in status
                docker_status = "running" if is_running else "stopped"
                
                # Build group object
                group = {
                    "id": group_id,
                    "name": group_name,
                    "description": description,
                    "screen_count": screen_count,
                    "orientation": orientation,
                    "created_at": created_timestamp,
                    "container_id": container_id,
                    "container_name": container_name,
                    "docker_status": docker_status,
                    "docker_running": is_running,
                    "status": docker_status,  # Overall status (can be updated by stream management)
                    "ports": ports,
                    "created_at_formatted": time.strftime(
                        "%Y-%m-%d %H:%M:%S",
                        time.localtime(created_timestamp)
                    ),
                    "docker_created_at": created_at
                }
                
                groups.append(group)
                logger.debug(f"✅ Added group: {group_name} (Docker: {docker_status})")
        
        # Sort groups by creation time (newest first)
        groups.sort(key=lambda g: g.get('created_at', 0), reverse=True)
        
        logger.info(f"✅ Discovered {len(groups)} groups from Docker containers")
        
        return {
            "success": True,
            "message": f"Found {len(groups)} groups",
            "groups": groups,
            "total": len(groups),
            "discovery_timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"❌ Error discovering groups from Docker: {e}")
        traceback.print_exc()
        return {
            "success": False,
            "error": f"Error discovering groups: {str(e)}",
            "groups": [],
            "traceback": traceback.format_exc()
        }

# Health check endpoint for Docker management
@docker_bp.route("/docker_status", methods=["GET"])
def docker_status():
    """Get Docker system status and multi-screen containers"""
    try:
        logger.info("🏥 Docker health check requested")
        
        # Check Docker availability
        success, docker_version, error = run_command(["docker", "--version"])
        if not success:
            return {
                "docker_available": False,
                "error": error,
                "groups_count": 0
            }, 500
        
        # Get groups discovery
        discovery_result = discover_groups()
        
        return {
            "docker_available": True,
            "docker_version": docker_version,
            "groups_discovery": discovery_result,
            "groups_count": len(discovery_result.get("groups", [])),
            "timestamp": time.time()
        }, 200
        
    except Exception as e:
        logger.error(f"❌ Error in Docker status check: {e}")
        return {
            "docker_available": False,
            "error": str(e),
            "groups_count": 0
        }, 500