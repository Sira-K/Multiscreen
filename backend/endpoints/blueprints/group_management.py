# blueprints/group_management.py
from flask import Blueprint, request, jsonify, current_app
import traceback
import time
import threading
import logging
import os
import subprocess
import uuid
from typing import Dict, List, Any, Optional, Tuple

# Create blueprint
group_bp = Blueprint('group_management', __name__)

# Configure logging
logger = logging.getLogger(__name__)

def get_state():
    """Get application state from current app context"""
    return current_app.config['APP_STATE']

def validate_group_data(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate group creation/update data
    
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
        
    return True, None


def get_next_available_ports(groups: Dict[str, Any]) -> Dict[str, int]:
    """
    Get the next available port block for a new group
    
    Args:
        groups: Dictionary of all existing groups
        
    Returns:
        Dictionary with port assignments for the new group
    """
    # Find the highest port offset currently in use
    max_offset = 0
    for group in groups.values():
        ports = group.get('ports', {})
        if ports:
            rtmp_port = ports.get('rtmp_port', 1935)
            current_offset = rtmp_port - 1935
            max_offset = max(max_offset, current_offset)
    
    # Use the next available offset
    next_offset = max_offset + 10
    
    return {
        "rtmp_port": 1935 + next_offset,
        "http_port": 1985 + next_offset,
        "api_port": 8080 + next_offset,
        "srt_port": 10080 + next_offset
    }

def sync_groups_with_docker(state):
    """
    Synchronize groups with running Docker containers.
    This function will:
    1. Find all running SRS Docker containers
    2. Extract group metadata from Docker labels
    3. Match them to existing groups or create new groups for orphaned containers
    4. Update group statuses based on container states
    """
    import subprocess
    import re
    import json
    import time
    import threading
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Get all running Docker containers with their names, IDs, and labels
        cmd = ["docker", "ps", "--format", "{{.ID}}\t{{.Names}}\t{{.Ports}}\t{{.Labels}}"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        running_containers = []
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                parts = line.split('\t')
                if len(parts) >= 2:
                    container_id = parts[0]
                    container_name = parts[1]
                    ports = parts[2] if len(parts) > 2 else ""
                    labels = parts[3] if len(parts) > 3 else ""
                    
                    # Only process SRS group containers
                    if container_name.startswith('srs-group-'):
                        running_containers.append({
                            'id': container_id,
                            'name': container_name,
                            'ports': ports,
                            'labels': labels
                        })
        
        logger.info(f"Found {len(running_containers)} running SRS containers")
        
        # Process each running container
        for container in running_containers:
            container_id = container['id']
            container_name = container['name']
            ports_str = container['ports']
            labels_str = container['labels']
            
            # Extract group metadata from Docker labels
            group_metadata = extract_group_metadata_from_labels(labels_str)
            stored_group_id = group_metadata.get('group_id')
            stored_group_name = group_metadata.get('group_name')
            
            # Try to match to existing group
            matching_group_id = None
            
            # First try: exact group ID match from labels
            if stored_group_id and stored_group_id in state.groups:
                matching_group_id = stored_group_id
            
            # Second try: match by container name pattern
            if not matching_group_id:
                group_id_short = container_name.replace('srs-group-', '')
                for group_id, group_data in state.groups.items():
                    if group_id.startswith(group_id_short):
                        existing_container_id = group_data.get("docker_container_id")
                        if not existing_container_id or existing_container_id == container_id:
                            matching_group_id = group_id
                            break
            
            if matching_group_id:
                # Update existing group with container info
                with state.groups_lock if hasattr(state, 'groups_lock') else threading.RLock():
                    group = state.groups[matching_group_id]
                    
                    # Only update if container ID has changed or was missing
                    if group.get("docker_container_id") != container_id:
                        group["docker_container_id"] = container_id
                        group["container_name"] = container_name
                        
                        # Parse and update port mappings from container
                        parsed_ports = parse_container_ports(ports_str)
                        if parsed_ports:
                            group["ports"] = parsed_ports
                        
                        # Status logic: Docker alone = inactive, Docker + SRT = active
                        srt_running = bool(group.get("ffmpeg_process_id"))
                        if srt_running:
                            group["status"] = "active"  # Both Docker and SRT running
                        else:
                            group["status"] = "inactive"  # Only Docker running
                        
                        logger.info(f"Synced existing group '{group['name']}' with container {container_id}")
            else:
                # Check if any existing group already has this container ID
                container_already_assigned = False
                for existing_group in state.groups.values():
                    if existing_group.get("docker_container_id") == container_id:
                        container_already_assigned = True
                        break
                
                if not container_already_assigned:
                    # Create new group for orphaned container using metadata from labels
                    if stored_group_id and stored_group_name:
                        # Use metadata from Docker labels
                        new_group_id = stored_group_id
                        recovered_name = stored_group_name
                        screen_count = int(group_metadata.get('screen_count', 2))
                        orientation = group_metadata.get('orientation', 'horizontal')
                        description = group_metadata.get('description', 'Recovered from Docker container')
                        created_at = float(group_metadata.get('created_at', time.time()))
                        recovered_flag = False  # This is a proper recovery, not orphaned
                    else:
                        # Fallback for containers without proper labels
                        group_id_short = container_name.replace('srs-group-', '')
                        new_group_id = f"recovered-{group_id_short}-{int(time.time())}"
                        recovered_name = f"Recovered Group ({group_id_short})"
                        screen_count = 2
                        orientation = "horizontal"
                        description = f"Automatically recovered from Docker container {container_name}"
                        created_at = time.time()
                        recovered_flag = True
                    
                    # Parse ports from container to determine base configuration
                    parsed_ports = parse_container_ports(ports_str)
                    srt_port = parsed_ports.get('srt_port', 10080) if parsed_ports else 10080
                    
                    new_group = {
                        "id": new_group_id,
                        "name": recovered_name,
                        "description": description,
                        "screen_count": screen_count,
                        "orientation": orientation,
                        "created_at": created_at,
                        "status": "inactive",  # Docker only = inactive (no SRT stream detected)
                        "clients": {},
                        "docker_container_id": container_id,
                        "ffmpeg_process_id": None,
                        "current_video": None,
                        "available_streams": [],  # Empty until SRT starts
                        "srt_port": srt_port,
                        "base_port": srt_port - 10080,  # Calculate base port offset
                        "screen_ips": {},
                        "total_clients": 0,
                        "active_clients": 0,
                        "last_activity": time.time(),
                        "container_name": container_name,
                        "ports": parsed_ports or {},
                        "recovered": recovered_flag,  # True only for containers without proper metadata
                        # Additional fields for compatibility
                        "docker_status": "running",
                        "container_id_short": container_id[:12],
                        "port_summary": f"SRT:{srt_port}",
                        "created_at_formatted": time.strftime(
                            "%Y-%m-%d %H:%M:%S",
                            time.localtime(created_at)
                        )
                    }
                    
                    with state.groups_lock if hasattr(state, 'groups_lock') else threading.RLock():
                        state.groups[new_group_id] = new_group
                    
                    recovery_type = "metadata" if not recovered_flag else "orphaned"
                    logger.info(f"Created new group '{recovered_name}' for {recovery_type} container {container_id}")
        
        # Mark groups as inactive if their containers are no longer running
        running_container_ids = {c['id'] for c in running_containers}
        
        with state.groups_lock if hasattr(state, 'groups_lock') else threading.RLock():
            for group_id, group_data in state.groups.items():
                stored_container_id = group_data.get("docker_container_id")
                if stored_container_id and stored_container_id not in running_container_ids:
                    # Container is no longer running
                    group_data["docker_container_id"] = None
                    group_data["status"] = "inactive"
                    group_data["available_streams"] = []
                    group_data["docker_status"] = "stopped"
                    group_data["container_id_short"] = None
                    logger.info(f"Marked group '{group_data.get('name', group_id)}' as inactive - container no longer running")
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to query Docker containers: {e}")
    except Exception as e:
        logger.error(f"Error syncing groups with Docker: {e}")
        import traceback
        traceback.print_exc()


def parse_container_ports(ports_str):
    """
    Parse Docker container port mappings from 'docker ps' output.
    Example input: "0.0.0.0:1935->1935/tcp, 0.0.0.0:1985->1985/tcp, 0.0.0.0:8080->8080/tcp, 0.0.0.0:10080->10080/udp"
    """
    import re
    import logging
    
    logger = logging.getLogger(__name__)
    """
    Parse Docker container port mappings from 'docker ps' output.
    Example input: "0.0.0.0:1935->1935/tcp, 0.0.0.0:1985->1985/tcp, 0.0.0.0:8080->8080/tcp, 0.0.0.0:10080->10080/udp"
    """
    try:
        ports = {}
        if not ports_str:
            return ports
        
        # Split by comma and parse each port mapping
        port_mappings = ports_str.split(', ')
        
        for mapping in port_mappings:
            # Extract host port and container port
            match = re.search(r'0\.0\.0\.0:(\d+)->(\d+)/(tcp|udp)', mapping.strip())
            if match:
                host_port = int(match.group(1))
                container_port = int(match.group(2))
                protocol = match.group(3)
                
                # Map to our port naming convention
                if container_port == 1935:
                    ports['rtmp_port'] = host_port
                elif container_port == 1985:
                    ports['http_port'] = host_port
                elif container_port == 8080:
                    ports['api_port'] = host_port
                elif container_port == 10080:
                    ports['srt_port'] = host_port
        
        return ports
    except Exception as e:
        logger.error(f"Error parsing container ports '{ports_str}': {e}")
        return {}



@group_bp.route("/create_group", methods=["POST"])
def create_group():
    """Create a new group with Docker container"""
    try:
        logger.info("==== CREATE GROUP REQUEST RECEIVED ====")
        state = get_state()
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        name = data.get("name", "").strip()
        if not name:
            return jsonify({"error": "Group name is required"}), 400
        
        description = data.get("description", "").strip()
        screen_count = data.get("screen_count", 2)
        orientation = data.get("orientation", "horizontal")
        
        # Initialize groups and locks if needed
        if not hasattr(state, 'groups'):
            state.groups = {}
        
        if not hasattr(state, 'groups_lock'):
            state.groups_lock = threading.RLock()
        
        # Check for name conflicts
        with state.groups_lock:
            for existing_group in state.groups.values():
                if existing_group.get("name") == name:
                    return jsonify({"error": f"Group name '{name}' already exists"}), 400
        
        # Generate new group ID
        group_id = str(uuid.uuid4())
        
        # Calculate ports for this group using the enhanced function
        # Import the enhanced calculate_group_ports function
        def calculate_group_ports_enhanced(group_id: str, groups: Dict[str, Any]) -> Dict[str, int]:
            """Enhanced port calculation with conflict detection"""
            import logging
            logger = logging.getLogger(__name__)
            
            # Sort group IDs to ensure consistent port assignment
            sorted_group_ids = sorted(groups.keys())
            
            try:
                group_index = sorted_group_ids.index(group_id)
            except ValueError:
                # If group not found in list, assign next available index
                group_index = len(sorted_group_ids)
            
            # Base port calculation: each group gets a block of 10 ports
            base_port_offset = group_index * 10
            
            # Ensure we don't conflict with other groups' ports
            used_ports = set()
            for other_group_id, other_group in groups.items():
                if other_group_id != group_id and other_group.get("ports"):
                    other_ports = other_group["ports"]
                    used_ports.update([
                        other_ports.get("rtmp_port"),
                        other_ports.get("http_port"), 
                        other_ports.get("api_port"),
                        other_ports.get("srt_port")
                    ])
            
            # Calculate ports and check for conflicts
            max_attempts = 50  # Prevent infinite loop
            attempts = 0
            
            while attempts < max_attempts:
                proposed_ports = {
                    "rtmp_port": 1935 + base_port_offset,      # 1935, 1945, 1955, etc.
                    "http_port": 1985 + base_port_offset,      # 1985, 1995, 2005, etc.
                    "api_port": 8080 + base_port_offset,       # 8080, 8090, 8100, etc.
                    "srt_port": 10080 + base_port_offset       # 10080, 10090, 10100, etc.
                }
                
                # Check if any proposed port conflicts with existing ports
                conflict = any(port in used_ports for port in proposed_ports.values() if port)
                
                if not conflict:
                    logger.info(f"Assigned ports for group {group_id}: {proposed_ports}")
                    return proposed_ports
                
                # If conflict, try next block
                base_port_offset += 10
                attempts += 1
            
            # Fallback if we couldn't find free ports
            logger.warning(f"Could not find free ports after {max_attempts} attempts, using defaults")
            return {
                "rtmp_port": 1935 + base_port_offset,
                "http_port": 1985 + base_port_offset,
                "api_port": 8080 + base_port_offset,
                "srt_port": 10080 + base_port_offset
            }
        
        # Create temporary group entry to calculate ports correctly
        temp_groups = dict(state.groups)
        temp_groups[group_id] = {}  # Temporary entry for port calculation
        ports = calculate_group_ports_enhanced(group_id, temp_groups)
        
        logger.info(f"Calculated ports for group '{name}': {ports}")
        
        # CREATE THE GROUP FIRST (with complete structure matching get_groups expectations)
        initial_group = {
            "id": group_id,
            "name": name,
            "description": description,
            "screen_count": screen_count,
            "orientation": orientation,
            "created_at": time.time(),
            "status": "inactive",  # Start as inactive, Docker will set to active
            "clients": {},
            "docker_container_id": None,
            "ffmpeg_process_id": None,
            "current_video": None,
            "available_streams": [],  # Will be populated when Docker starts
            # Network configuration
            "srt_port": ports["srt_port"],
            "base_port": ports["srt_port"] - 10080,  # Calculate base port offset
            "screen_ips": {},
            "ports": ports,  # Store calculated ports
            "container_name": None,  # Will be set by Docker
            # Statistics (matching get_groups structure)
            "total_clients": 0,
            "active_clients": 0,
            "last_activity": time.time(),
            # Additional fields for compatibility
            "docker_status": "stopped",
            "container_id_short": None,
            "port_summary": f"SRT:{ports['srt_port']}",
            "created_at_formatted": time.strftime(
                "%Y-%m-%d %H:%M:%S", 
                time.localtime(time.time())
            )
        }
        
        # Save the group BEFORE trying to start Docker
        with state.groups_lock:
            state.groups[group_id] = initial_group
        
        logger.info(f"Created initial group entry for '{name}' with ID: {group_id}")
        logger.info(f"Assigned ports: RTMP={ports['rtmp_port']}, HTTP={ports['http_port']}, API={ports['api_port']}, SRT={ports['srt_port']}")
        
        # NOW start Docker container for this group
        try:
            from blueprints.docker_management import start_group_docker
            
            # Create a test request context with the group_id
            with current_app.test_request_context(
                json={"group_id": group_id},
                method='POST',
                content_type='application/json'
            ):
                docker_result = start_group_docker()
            
            # Handle the response properly
            if isinstance(docker_result, tuple):
                docker_response, status_code = docker_result
                # Extract JSON from Flask response
                if hasattr(docker_response, 'get_json'):
                    docker_data = docker_response.get_json()
                else:
                    docker_data = docker_response
            else:
                # Direct JSON response
                docker_data = docker_result
                status_code = 200
            
            if status_code != 200:
                # Docker failed - clean up the group
                with state.groups_lock:
                    if group_id in state.groups:
                        del state.groups[group_id]
                
                docker_error_msg = docker_data.get("error", "Unknown error") if isinstance(docker_data, dict) else str(docker_data)
                logger.error(f"Docker creation failed with status {status_code}: {docker_error_msg}")
                return jsonify({
                    "error": f"Failed to create Docker container for group '{name}'",
                    "docker_error": docker_error_msg,
                    "status_code": status_code
                }), 500
            
            # Docker succeeded - update the group with container information
            container_id = docker_data.get("container_id")
            container_name = docker_data.get("container_name")
            docker_ports = docker_data.get("ports", {})
            
            # Update the group with Docker info but keep status logic correct
            with state.groups_lock:
                group = state.groups[group_id]
                group.update({
                    "docker_container_id": container_id,
                    "container_name": container_name,
                    "ports": docker_ports,  # Use actual ports from Docker
                    "srt_port": docker_ports.get("srt_port", ports["srt_port"]),
                    # Docker status fields
                    "docker_status": "running",
                    "container_id_short": container_id[:12] if container_id else None,
                    "port_summary": f"SRT:{docker_ports.get('srt_port', ports['srt_port'])}",
                })
                
                # IMPORTANT: Status logic correction
                # Docker running alone = status "inactive" (Docker ready but no SRT stream)
                # Docker + SRT = status "active" (both running)
                # Since we only started Docker, keep status as "inactive"
                if group.get("status") == "active" and not group.get("ffmpeg_process_id"):
                    group["status"] = "inactive"  # Override Docker management's status
                
                # Available streams should be empty until SRT starts
                group["available_streams"] = []
            
            logger.info(f"Successfully updated group '{name}' with Docker container: {container_id}")
            logger.info(f"Group status kept as 'inactive' - Docker ready, SRT not started yet")
            
        except Exception as docker_error:
            # Docker failed - clean up the group
            with state.groups_lock:
                if group_id in state.groups:
                    del state.groups[group_id]
            
            logger.error(f"Docker creation failed for group '{name}': {docker_error}")
            return jsonify({
                "error": f"Failed to create Docker container for group '{name}'",
                "docker_error": str(docker_error)
            }), 500
        
        # Get the final group state
        final_group = state.groups[group_id]
        
        logger.info(f"Successfully created group '{name}' with ID: {group_id}")
        logger.info(f"Final group status: {final_group.get('status')}")
        logger.info(f"Docker status: {final_group.get('docker_status')}")
        logger.info(f"Available streams: {len(final_group.get('available_streams', []))}")
        
        # Return response matching the structure expected by clients
        return jsonify({
            "message": f"Group '{name}' created successfully with Docker container",
            "group": final_group,
            "docker_info": {
                "container_id": final_group.get("docker_container_id"),
                "container_name": final_group.get("container_name"),
                "ports": final_group.get("ports", {}),
                "srt_port": final_group.get("srt_port"),
                "docker_status": final_group.get("docker_status")
            },
            "synchronization_ready": True  # Indicates this group is ready for get_groups sync
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating group: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@group_bp.route("/get_groups", methods=["GET"])
def get_groups():
    """Get a list of all groups with their status and statistics"""
    import logging
    import traceback
    import time
    import threading
    from flask import jsonify
    
    logger = logging.getLogger(__name__)
    logger.info("==== GET_GROUPS REQUEST RECEIVED ====")
    state = get_state()
    try:
        if not hasattr(state, 'groups'):
            state.groups = {}
        
        if not hasattr(state, 'groups_lock'):
            state.groups_lock = threading.RLock()
        
        # First, synchronize with running Docker containers (but only if not recently synced)
        current_time = time.time()
        last_sync_time = getattr(state, '_last_docker_sync', 0)
        sync_interval = 10  # Only sync every 10 seconds to prevent duplicates
        
        if current_time - last_sync_time > sync_interval:
            sync_groups_with_docker(state)
            state._last_docker_sync = current_time
            logger.info("Docker synchronization completed")
        else:
            logger.info(f"Skipping Docker sync - last sync was {current_time - last_sync_time:.1f}s ago")
        
        with state.groups_lock:
            current_time = time.time()
            groups_list = []
           
            for group_id, group_data in state.groups.items():
                # Create a copy for modification
                group = dict(group_data)
               
                # Update client statistics
                active_clients = 0
                total_clients = len(group.get("clients", {}))
               
                for client_data in group.get("clients", {}).values():
                    if current_time - client_data.get("last_seen", 0) <= 60:  # 1 minute threshold
                        active_clients += 1
               
                group["active_clients"] = active_clients
                group["total_clients"] = total_clients
               
                # Update available streams based on group status and screen count
                # Only set available streams if BOTH Docker AND SRT are running
                docker_running = bool(group.get("docker_container_id"))
                srt_running = bool(group.get("ffmpeg_process_id"))
                
                if docker_running and srt_running:
                    # Both Docker and SRT running = fully active
                    group["status"] = "active"
                    streams = [f"live/{group_id}/test"]  # Full stream
                    screen_count = group.get("screen_count", 2)
                    for i in range(screen_count):
                        streams.append(f"live/{group_id}/test{i}")
                    group["available_streams"] = streams
                elif docker_running and not srt_running:
                    # Docker running but no SRT = inactive (ready to start SRT)
                    group["status"] = "inactive"
                    group["available_streams"] = []
                else:
                    # Neither running = inactive
                    group["status"] = "inactive"
                    group["available_streams"] = []
               
                # Format creation time
                group["created_at_formatted"] = time.strftime(
                    "%Y-%m-%d %H:%M:%S",
                    time.localtime(group.get("created_at", current_time))
                )
                
                # Add Docker status information
                container_id = group.get("docker_container_id")
                if container_id:
                    group["docker_status"] = "running"
                    group["container_id_short"] = container_id[:12]  # Show shortened ID
                else:
                    group["docker_status"] = "stopped"
                    group["container_id_short"] = None
                
                # Add port information if available
                if group.get("ports"):
                    group["port_summary"] = f"SRT:{group['ports'].get('srt_port', 'N/A')}"
                
                groups_list.append(group)
           
            logger.info(f"Returning {len(groups_list)} groups (after Docker sync)")
           
            return jsonify({
                "groups": groups_list,
                "total": len(state.groups),
                "docker_synced": True
            }), 200
           
    except Exception as e:
        logger.error(f"Error getting groups: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    

@group_bp.route("/update_group/<group_id>", methods=["PUT"])
def update_group(group_id: str):
    """Update group settings"""
    try:
        state = get_state()
        
        if not hasattr(state, 'groups') or group_id not in state.groups:
            return jsonify({"error": "Group not found"}), 404
            
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        with state.groups_lock:
            group = state.groups[group_id]
            
            # Update allowed fields
            if "name" in data and data["name"].strip():
                # Check for name conflicts
                new_name = data["name"].strip()
                for gid, existing_group in state.groups.items():
                    if gid != group_id and existing_group.get("name", "").lower() == new_name.lower():
                        return jsonify({"error": f"Group name '{new_name}' already exists"}), 400
                group["name"] = new_name
                
            if "description" in data:
                group["description"] = data["description"].strip()
                
            if "screen_count" in data:
                group["screen_count"] = int(data["screen_count"])
                
            if "orientation" in data:
                group["orientation"] = data["orientation"]
                
            if "screen_ips" in data:
                group["screen_ips"] = data["screen_ips"]
            
            group["last_activity"] = time.time()
        
        return jsonify({
            "message": f"Group updated successfully",
            "group": state.groups[group_id]
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating group: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@group_bp.route("/delete_group/<group_id>", methods=["DELETE"])
def delete_group(group_id: str):
    """Delete a group and clean up all associated resources (SRT stream + Docker container removal)"""
    try:
        state = get_state()
        
        if not hasattr(state, 'groups') or group_id not in state.groups:
            return jsonify({"error": "Group not found"}), 404
            
        group = state.groups[group_id]
        group_name = group.get("name", group_id)
        
        logger.info(f"🗑️ Deleting group '{group_name}' (ID: {group_id})")
        
        cleanup_results = {
            "srt_stopped": False,
            "docker_stopped": False,
            "docker_removed": False,
            "messages": [],
            "errors": []
        }
        
        with state.groups_lock:
            # Step 1: Stop SRT stream if running
            ffmpeg_process_id = group.get("ffmpeg_process_id")
            if ffmpeg_process_id:
                try:
                    logger.info(f"Stopping SRT stream for group '{group_name}' (PID: {ffmpeg_process_id})")
                    
                    import psutil
                    process = psutil.Process(ffmpeg_process_id)
                    process.terminate()
                    
                    try:
                        process.wait(timeout=5)
                        cleanup_results["messages"].append(f"SRT stream stopped gracefully (PID: {ffmpeg_process_id})")
                    except:
                        process.kill()
                        cleanup_results["messages"].append(f"SRT stream force-killed (PID: {ffmpeg_process_id})")
                    
                    cleanup_results["srt_stopped"] = True
                    logger.info(f"✅ SRT stream stopped for group '{group_name}'")
                    
                except Exception as e:
                    error_msg = f"Failed to stop SRT stream: {str(e)}"
                    logger.error(error_msg)
                    cleanup_results["errors"].append(error_msg)
            else:
                cleanup_results["messages"].append("No SRT stream was running")
                cleanup_results["srt_stopped"] = True
            
            # Step 2: Stop and Remove Docker container if exists
            container_id = group.get("docker_container_id")
            if container_id:
                try:
                    logger.info(f"Stopping and removing Docker container for group '{group_name}' (ID: {container_id})")
                    
                    # Import the run_command function from docker_management
                    from blueprints.docker_management import run_command
                    
                    # Validate container ID format (basic check)
                    if not container_id.strip().replace('-', '').isalnum():
                        raise ValueError("Invalid container ID format")
                    
                    # Step 2a: Stop the container (if running)
                    logger.info(f"Stopping Docker container: {container_id}")
                    success, stop_output, stop_error = run_command(["docker", "stop", container_id])
                    
                    if success:
                        cleanup_results["messages"].append(f"Docker container stopped (ID: {container_id})")
                        cleanup_results["docker_stopped"] = True
                        logger.info(f"✅ Docker container stopped for group '{group_name}'")
                    else:
                        # Container might already be stopped, continue with removal
                        logger.warning(f"Docker stop failed (container may already be stopped): {stop_error}")
                        cleanup_results["messages"].append(f"Docker stop warning: {stop_error}")
                        cleanup_results["docker_stopped"] = True  # Consider it stopped for removal
                    
                    # Step 2b: Remove the container completely
                    logger.info(f"Removing Docker container: {container_id}")
                    success, remove_output, remove_error = run_command(["docker", "rm", "-f", container_id])
                    
                    if success:
                        cleanup_results["messages"].append(f"Docker container removed completely (ID: {container_id})")
                        cleanup_results["docker_removed"] = True
                        logger.info(f"✅ Docker container removed for group '{group_name}'")
                    else:
                        error_msg = f"Failed to remove Docker container: {remove_error}"
                        logger.error(error_msg)
                        cleanup_results["errors"].append(error_msg)
                        
                        # Try alternative removal approach
                        logger.info("Attempting force removal with different approach...")
                        success, alt_output, alt_error = run_command(["docker", "container", "rm", "-f", container_id])
                        
                        if success:
                            cleanup_results["messages"].append(f"Docker container force-removed (ID: {container_id})")
                            cleanup_results["docker_removed"] = True
                            logger.info(f"✅ Docker container force-removed for group '{group_name}'")
                        else:
                            error_msg = f"Failed to force-remove Docker container: {alt_error}"
                            logger.error(error_msg)
                            cleanup_results["errors"].append(error_msg)
                    
                    # Step 2c: Clean up any dangling volumes/networks (optional)
                    try:
                        # Remove any volumes associated with this container
                        logger.info("Cleaning up Docker volumes...")
                        volume_success, volume_output, volume_error = run_command([
                            "docker", "volume", "prune", "-f"
                        ])
                        if volume_success:
                            cleanup_results["messages"].append("Docker volumes cleaned up")
                        
                        # Clean up networks if needed
                        logger.info("Cleaning up Docker networks...")
                        network_success, network_output, network_error = run_command([
                            "docker", "network", "prune", "-f"
                        ])
                        if network_success:
                            cleanup_results["messages"].append("Docker networks cleaned up")
                            
                    except Exception as cleanup_e:
                        logger.warning(f"Docker cleanup warning: {cleanup_e}")
                        cleanup_results["messages"].append(f"Docker cleanup warning: {str(cleanup_e)}")
                        
                except Exception as e:
                    error_msg = f"Failed to stop/remove Docker container: {str(e)}"
                    logger.error(error_msg)
                    cleanup_results["errors"].append(error_msg)
            else:
                cleanup_results["messages"].append("No Docker container was running")
                cleanup_results["docker_stopped"] = True
                cleanup_results["docker_removed"] = True
            
            # Step 3: Unassign all clients from this group
            if group.get("clients"):
                # Remove group assignment from clients
                if hasattr(state, 'clients'):
                    for client_id in group["clients"].keys():
                        if client_id in state.clients:
                            state.clients[client_id]["group_id"] = None
                            state.clients[client_id]["stream_id"] = None
                cleanup_results["messages"].append(f"Unassigned {len(group['clients'])} clients from group")
            
            # Step 4: Clean up any temporary files associated with this group
            try:
                # Clean up any uploaded videos or temporary files for this group
                import os
                temp_dir = f"/tmp/multiscreen_group_{group_id}"
                if os.path.exists(temp_dir):
                    import shutil
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    cleanup_results["messages"].append("Temporary files cleaned up")
            except Exception as e:
                logger.warning(f"Temp file cleanup warning: {e}")
                cleanup_results["messages"].append(f"Temp file cleanup warning: {str(e)}")
            
            # Step 5: Delete the group from the database
            del state.groups[group_id]
            logger.info(f"✅ Group '{group_name}' deleted from database")
        
        # Step 6: Verify Docker container is completely gone
        verification_results = []
        if container_id:
            try:
                from blueprints.docker_management import run_command
                
                # Check if container still exists
                success, inspect_output, inspect_error = run_command([
                    "docker", "inspect", container_id
                ])
                
                if not success:
                    # Container doesn't exist - good!
                    verification_results.append(f"✅ Verified: Docker container {container_id} no longer exists")
                else:
                    # Container still exists - warning
                    verification_results.append(f"⚠️ Warning: Docker container {container_id} may still exist")
                    cleanup_results["errors"].append(f"Container verification failed - container may still exist")
                    
            except Exception as e:
                verification_results.append(f"Could not verify container removal: {str(e)}")
        
        cleanup_results["verification"] = verification_results
        
        # Determine success based on cleanup results
        complete_success = (
            cleanup_results["srt_stopped"] and 
            cleanup_results["docker_stopped"] and 
            cleanup_results["docker_removed"] and 
            len(cleanup_results["errors"]) == 0
        )
        
        if complete_success:
            return jsonify({
                "message": f"Group '{group_name}' and all associated resources deleted successfully",
                "group_name": group_name,
                "cleanup_results": cleanup_results,
                "status": "completely_deleted"
            }), 200
        elif cleanup_results["errors"]:
            # Some cleanup failed, but group was still deleted
            return jsonify({
                "message": f"Group '{group_name}' deleted with some cleanup warnings",
                "group_name": group_name,
                "cleanup_results": cleanup_results,
                "status": "deleted_with_warnings"
            }), 207  # Multi-Status (partial success)
        else:
            # Partial success
            return jsonify({
                "message": f"Group '{group_name}' deleted with partial cleanup",
                "group_name": group_name,
                "cleanup_results": cleanup_results,
                "status": "deleted_partial"
            }), 206  # Partial Content
        
    except Exception as e:
        logger.error(f"Error deleting group: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@group_bp.route("/assign_client_to_group", methods=["POST"])
def assign_client_to_group():
    """Assign a client to a specific group"""
    try:
        state = get_state()
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        client_id = data.get("client_id")
        group_id = data.get("group_id")
        
        if not client_id:
            return jsonify({"error": "Missing client_id"}), 400
            
        # Initialize groups and clients if needed
        if not hasattr(state, 'groups'):
            state.groups = {}
        if not hasattr(state, 'clients'):
            state.clients = {}
            
        # Validate group exists (if group_id is provided)
        if group_id and group_id not in state.groups:
            return jsonify({"error": "Group not found"}), 404
            
        # Validate client exists
        if client_id not in state.clients:
            return jsonify({"error": "Client not found"}), 404
        
        with state.clients_lock if hasattr(state, 'clients_lock') else threading.RLock():
            with state.groups_lock if hasattr(state, 'groups_lock') else threading.RLock():
                client = state.clients[client_id]
                old_group_id = client.get("group_id")
                
                # Remove from old group
                if old_group_id and old_group_id in state.groups:
                    if client_id in state.groups[old_group_id].get("clients", {}):
                        del state.groups[old_group_id]["clients"][client_id]
                
                # Add to new group
                if group_id:
                    if "clients" not in state.groups[group_id]:
                        state.groups[group_id]["clients"] = {}
                    state.groups[group_id]["clients"][client_id] = {
                        "assigned_at": time.time(),
                        "stream_id": None
                    }
                    client["group_id"] = group_id
                    
                    # Auto-assign a stream within the group
                    group = state.groups[group_id]
                    if group.get("available_streams"):
                        # Assign the first available stream
                        client["stream_id"] = group["available_streams"][0]
                else:
                    client["group_id"] = None
                    client["stream_id"] = None
        
        message = f"Client {client_id} assigned to group {group_id}" if group_id else f"Client {client_id} removed from all groups"
        
        return jsonify({
            "message": message,
            "client": state.clients[client_id]
        }), 200
        
    except Exception as e:
        logger.error(f"Error assigning client to group: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@group_bp.route("/group_clients/<group_id>", methods=["GET"])
def get_group_clients(group_id: str):
    """Get all clients belonging to a specific group"""
    try:
        state = get_state()
        
        if not hasattr(state, 'groups') or group_id not in state.groups:
            return jsonify({"error": "Group not found"}), 404
            
        if not hasattr(state, 'clients'):
            state.clients = {}
            
        current_time = time.time()
        group_clients = []
        
        with state.clients_lock if hasattr(state, 'clients_lock') else threading.RLock():
            for client_id, client_data in state.clients.items():
                if client_data.get("group_id") == group_id:
                    # Create a copy for modification
                    client = dict(client_data)
                    
                    # Update status
                    if current_time - client_data.get("last_seen", 0) <= 60:
                        client["status"] = "active"
                    else:
                        client["status"] = "inactive"
                    
                    # Add formatted last seen
                    seconds_ago = int(current_time - client_data.get("last_seen", 0))
                    client["last_seen_formatted"] = format_time_ago(seconds_ago)
                    
                    group_clients.append(client)
        
        return jsonify({
            "group_id": group_id,
            "clients": group_clients,
            "total": len(group_clients),
            "active": len([c for c in group_clients if c["status"] == "active"])
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting group clients: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


def format_time_ago(seconds_ago: int) -> str:
    """Format a time difference in seconds into a human-readable string"""
    if seconds_ago < 60:
        return f"{seconds_ago} seconds ago"
    elif seconds_ago < 3600:
        minutes = seconds_ago // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    else:
        hours = seconds_ago // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"

# Helper function to get group-specific available streams
def get_group_available_streams(group_id: str) -> Dict[str, Any]:
    """
    Get available streams for a specific group
    """
    state = get_state()
    
    if not hasattr(state, 'groups') or group_id not in state.groups:
        return {
            "available_streams": [],
            "active_clients": 0,
            "max_screens": 1
        }
    
    group = state.groups[group_id]
    screen_count = group.get("screen_count", 2)
    
    # Count active clients in this group
    current_time = time.time()
    active_clients = 0
    
    if hasattr(state, 'clients'):
        for client_data in state.clients.values():
            if (client_data.get("group_id") == group_id and 
                current_time - client_data.get("last_seen", 0) <= 60):
                active_clients += 1
    
    # Build available streams for this group
    available_streams = [f"live/{group_id}/test"]  # Full stream
    
    if active_clients >= 2:
        for i in range(min(active_clients, screen_count)):
            available_streams.append(f"live/{group_id}/test{i}")
    
    return {
        "available_streams": available_streams,
        "active_clients": active_clients,
        "max_screens": screen_count,
        "group_name": group.get("name", group_id)
    }