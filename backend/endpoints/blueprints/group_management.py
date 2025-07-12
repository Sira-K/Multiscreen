# backend/endpoints/blueprints/group_management.py
from flask import Blueprint, request, jsonify, current_app
import time
import threading
import logging
import uuid
import psutil
import os
import subprocess
from typing import Dict, List, Any, Optional, Tuple

# Create blueprint and logger
group_bp = Blueprint('group_management', __name__)
logger = logging.getLogger(__name__)

# Helper functions first
def get_state():
    """Get application state from current app context"""
    return current_app.config['APP_STATE']

def validate_group_data(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validate group creation data"""
    if not data:
        return False, "No JSON data provided"
    if not data.get("name", "").strip():
        return False, "Group name is required"
    return True, None

def get_next_available_ports(groups: Dict[str, Any]) -> Dict[str, int]:
    """Calculate next available port block for a new group"""
    max_offset = 0
    for group in groups.values():
        ports = group.get('ports', {})
        if ports:
            rtmp_port = ports.get('rtmp_port', 1935)
            current_offset = rtmp_port - 1935
            max_offset = max(max_offset, current_offset)
    
    next_offset = max_offset + 10
    return {
        "rtmp_port": 1935 + next_offset,
        "http_port": 1985 + next_offset, 
        "api_port": 8080 + next_offset,
        "srt_port": 10080 + next_offset
    }

def update_group_status(group_id: str, status: str):
    """Update group status in application state"""
    try:
        state = get_state()
        if hasattr(state, 'groups') and group_id in state.groups:
            with state.groups_lock:
                state.groups[group_id]['status'] = status
                state.groups[group_id]['last_updated'] = time.time()
                
                # Also update ffmpeg_process_id if we're setting to active and it's not set
                if status == 'active' and not state.groups[group_id].get('ffmpeg_process_id'):
                    # Try to find the FFmpeg process
                    import psutil
                    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                        try:
                            if proc.info['name'] and 'ffmpeg' in proc.info['name'].lower():
                                cmdline = proc.info['cmdline'] or []
                                # Check if this FFmpeg process is for our group
                                if any(group_id in str(arg) for arg in cmdline):
                                    state.groups[group_id]['ffmpeg_process_id'] = proc.info['pid']
                                    logger.info(f"🔍 Found FFmpeg process {proc.info['pid']} for group {group_id}")
                                    break
                        except:
                            continue
                
                logger.info(f"📊 Updated group {group_id} status to {status}")
                
                # Force update available streams when active
                if status == 'active' and not state.groups[group_id].get('available_streams'):
                    state.groups[group_id]['available_streams'] = [
                        f"live/{group_id}/test",
                        f"live/{group_id}/test0",
                        f"live/{group_id}/test1"
                    ]
                    logger.info(f"🎯 Added default streams for active group {group_id}")
                elif status == 'inactive':
                    state.groups[group_id]['available_streams'] = []
                    state.groups[group_id]['ffmpeg_process_id'] = None
                    state.groups[group_id]['current_video'] = None
                    logger.info(f"🧹 Cleaned up inactive group {group_id}")
                    
    except Exception as e:
        logger.error(f"Failed to update group status: {e}")

def get_group_by_id(group_id: str) -> Optional[Dict[str, Any]]:
    """Get group data by ID"""
    try:
        state = get_state()
        if hasattr(state, 'groups') and group_id in state.groups:
            return state.groups[group_id]
    except Exception as e:
        logger.error(f"Failed to get group {group_id}: {e}")
    return None

def is_process_running(process_id: int) -> bool:
    """Check if a process is running and is FFmpeg"""
    if not process_id:
        return False
    try:
        process = psutil.Process(process_id)
        return process.is_running() and 'ffmpeg' in process.name().lower()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False

def find_video_path(video_name: str) -> str:
    """Find the full path to a video file"""
    try:
        # Check in download folder (resized videos)
        download_folder = current_app.config.get('DOWNLOAD_FOLDER', './resized_video')
        download_path = os.path.join(download_folder, video_name)
        if os.path.exists(download_path):
            return download_path
        
        # Check in upload folder (original videos)
        upload_folder = current_app.config.get('UPLOAD_FOLDER', './uploads')
        upload_path = os.path.join(upload_folder, video_name)
        if os.path.exists(upload_path):
            return upload_path
        
        # If not found, return the download folder path (preferred location)
        return download_path
        
    except Exception as e:
        logger.warning(f"Error finding video path: {e}")
        return f"./resized_video/{video_name}"

def run_command(cmd: List[str], timeout: int = 30) -> Tuple[bool, str, str]:
    """Run a command securely and return its output"""
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

# Route handlers
@group_bp.route("/start_group_srt", methods=["POST"])
def start_group_srt():
    """Start SRT streaming for a group (frontend compatibility)"""
    try:
        data = request.get_json() or {}
        group_id = data.get('group_id')
        video_file = data.get('video_file')
        
        logger.info(f"🚀 START GROUP SRT REQUEST: group_id={group_id}, video_file={video_file}")
        
        if not group_id:
            return jsonify({"error": "group_id is required"}), 400
        
        if not video_file:
            return jsonify({"error": "video_file is required"}), 400
        
        # Get group info
        group = get_group_by_id(group_id)
        if not group:
            return jsonify({"error": f"Group {group_id} not found"}), 404
        
        logger.info(f"📋 Group before start: status={group.get('status')}, ffmpeg_pid={group.get('ffmpeg_process_id')}")
        
        # Update group status to starting
        update_group_status(group_id, 'starting')
        
        try:
            # Import and use the existing stream management
            from blueprints.stream_management import start_group_srt as stream_start_group_srt
            
            logger.info(f"🔄 Calling existing stream management for group {group_id}")
            
            # Call the existing stream management function
            result = stream_start_group_srt()
            
            logger.info(f"📊 Stream management result type: {type(result)}")
            
            # Handle different result types
            success = False
            response_data = None
            
            if isinstance(result, tuple):
                response_data, status_code = result
                logger.info(f"📈 Tuple result - status_code: {status_code}")
                success = status_code == 200
                
                # Extract JSON if it's a Flask response
                if hasattr(response_data, 'get_json'):
                    response_data = response_data.get_json()
                    logger.info(f"📄 Extracted JSON: {response_data}")
                    
            else:
                # Direct JSON response
                response_data = result
                success = True
                logger.info(f"📄 Direct result: {response_data}")
            
            # Update group status based on success
            if success:
                update_group_status(group_id, 'active')
                logger.info(f"✅ SUCCESSFULLY STARTED - Updated group {group_id} status to ACTIVE")
                
                # Ensure we return the result in the correct format
                if isinstance(result, tuple):
                    return result
                else:
                    return jsonify(response_data), 200
            else:
                update_group_status(group_id, 'inactive')
                logger.error(f"❌ FAILED TO START - Updated group {group_id} status to INACTIVE")
                return result
                
        except ImportError as e:
            logger.error(f"❌ Could not import stream management: {e}")
            update_group_status(group_id, 'inactive')
            return jsonify({"error": "Stream management not available"}), 500
        except Exception as e:
            logger.error(f"❌ Failed to start SRT stream: {e}")
            update_group_status(group_id, 'inactive')
            return jsonify({"error": str(e)}), 500
        
    except Exception as e:
        logger.error(f"❌ Error in start_group_srt: {e}")
        return jsonify({"error": f"Error starting group: {str(e)}"}), 500

@group_bp.route("/stop_group_srt", methods=["POST"])
def stop_group_srt():
    """Stop SRT streaming for a group (frontend compatibility)"""
    try:
        data = request.get_json() or {}
        group_id = data.get('group_id')
        
        logger.info(f"🛑 STOP GROUP SRT REQUEST: group_id={group_id}")
        
        if not group_id:
            return jsonify({"error": "group_id is required"}), 400
        
        # Get group info
        group = get_group_by_id(group_id)
        if not group:
            return jsonify({"error": f"Group {group_id} not found"}), 404
        
        logger.info(f"📋 Group before stop: status={group.get('status')}, ffmpeg_pid={group.get('ffmpeg_process_id')}")
        
        # Update group status to stopping
        update_group_status(group_id, 'stopping')
        
        try:
            # Import and use the existing stream management
            from blueprints.stream_management import stop_group_srt as stream_stop_group_srt
            
            logger.info(f"🔄 Calling existing stream management stop for group {group_id}")
            
            # Call the existing stream management function
            result = stream_stop_group_srt()
            
            logger.info(f"📊 Stream stop result: {result}")
            
            # Always update group status to inactive after stop
            update_group_status(group_id, 'inactive')
            logger.info(f"✅ SUCCESSFULLY STOPPED - Updated group {group_id} status to INACTIVE")
            
            return result
            
        except ImportError as e:
            logger.error(f"❌ Could not import stream management: {e}")
            update_group_status(group_id, 'inactive')
            return jsonify({"error": "Stream management not available"}), 500
        except Exception as e:
            logger.error(f"❌ Failed to stop SRT stream: {e}")
            update_group_status(group_id, 'inactive')
            return jsonify({"error": str(e)}), 500
        
    except Exception as e:
        logger.error(f"❌ Error in stop_group_srt: {e}")
        return jsonify({"error": f"Error stopping group: {str(e)}"}), 500

@group_bp.route("/create_group", methods=["POST"])
def create_group():
    """Create a new group for managing screens and clients"""
    try:
        logger.info("==== CREATE GROUP REQUEST RECEIVED ====")
        
        state = get_state()
        if not hasattr(state, 'groups_lock'):
            state.groups_lock = threading.RLock()
        if not hasattr(state, 'groups'):
            state.groups = {}
        
        data = request.get_json()
        is_valid, error_message = validate_group_data(data)
        if not is_valid:
            return jsonify({"error": error_message}), 400
            
        group_name = data.get("name").strip()
        description = data.get("description", "").strip()
        screen_count = int(data.get("screen_count", 2))
        orientation = data.get("orientation", "horizontal")
        
        # Check for duplicate names
        with state.groups_lock:
            for existing_group in state.groups.values():
                if existing_group.get("name") == group_name:
                    return jsonify({"error": f"Group name '{group_name}' already exists"}), 400
        
        # Generate unique group ID and assign ports
        group_id = str(uuid.uuid4())
        ports = get_next_available_ports(state.groups)
        
        # Create group data
        group_data = {
            "id": group_id,
            "name": group_name,
            "description": description,
            "screen_count": screen_count,
            "orientation": orientation,
            "status": "inactive",
            "ports": ports,
            "srt_port": ports["srt_port"],
            "created_at": time.time(),
            "created_at_formatted": time.strftime("%Y-%m-%d %H:%M:%S"),
            "docker_container_id": None,
            "ffmpeg_process_id": None,
            "available_streams": [],
            "current_video": None,
            "active_clients": 0,
            "total_clients": 0,
            "last_updated": time.time(),
            "container_name": None,
            "docker_status": "starting"
        }
        
        # Save group
        with state.groups_lock:
            state.groups[group_id] = group_data
        
        logger.info(f"✅ Created group '{group_name}' with ID {group_id} on ports {ports}")
        
        # Try to start Docker container
        try:
            from blueprints.docker_management import start_group_docker
            
            with current_app.test_request_context(
                json={"group_id": group_id},
                method='POST',
                content_type='application/json'
            ):
                docker_result = start_group_docker()
            
            if isinstance(docker_result, tuple):
                docker_response, status_code = docker_result
                if hasattr(docker_response, 'get_json'):
                    docker_data = docker_response.get_json()
                else:
                    docker_data = docker_response
            else:
                docker_data = docker_result
                status_code = 200
            
            if status_code == 200:
                container_id = docker_data.get("container_id")
                container_name = docker_data.get("container_name")
                docker_ports = docker_data.get("ports", {})
                
                with state.groups_lock:
                    group = state.groups[group_id]
                    group.update({
                        "docker_container_id": container_id,
                        "container_name": container_name,
                        "ports": docker_ports,
                        "srt_port": docker_ports.get("srt_port", ports["srt_port"]),
                        "docker_status": "running",
                        "container_id_short": container_id[:12] if container_id else None,
                        "port_summary": f"SRT:{docker_ports.get('srt_port', ports['srt_port'])}"
                    })
                
                logger.info(f"🐳 Docker container started: {container_id}")
            
        except Exception as docker_error:
            logger.warning(f"Docker creation failed: {docker_error}")
            # Continue without Docker
        
        final_group = state.groups[group_id]
        
        return jsonify({
            "message": f"Group '{group_name}' created successfully",
            "group": final_group
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating group: {e}")
        return jsonify({"error": f"Error creating group: {str(e)}"}), 500

@group_bp.route("/get_groups", methods=["GET"])
def get_groups_legacy():
    """Legacy endpoint for backward compatibility with frontend"""
    return get_groups()

@group_bp.route("/groups", methods=["GET"])
def get_groups():
    """Get all groups with their current status"""
    try:
        state = get_state()
        
        if not hasattr(state, 'groups'):
            return jsonify({"groups": []}), 200
        
        with state.groups_lock if hasattr(state, 'groups_lock') else threading.RLock():
            groups_list = []
            current_time = time.time()
            
            for group_id, group_data in state.groups.items():
                group_copy = dict(group_data)
                
                # Count active clients for this group
                active_clients = 0
                total_clients = 0
                
                if hasattr(state, 'clients'):
                    for client in state.clients.values():
                        if client.get('group_id') == group_id:
                            total_clients += 1
                            if current_time - client.get("last_seen", 0) <= 60:
                                active_clients += 1
                
                group_copy.update({
                    "active_clients": active_clients,
                    "total_clients": total_clients
                })
                
                # Add debug info
                logger.debug(f"📊 Group {group_data.get('name')}: status={group_data.get('status')}, ffmpeg_pid={group_data.get('ffmpeg_process_id')}")
                
                groups_list.append(group_copy)
            
            # Sort by creation time (newest first)
            groups_list.sort(key=lambda x: x.get('created_at', 0), reverse=True)
        
        return jsonify({
            "groups": groups_list,
            "total_count": len(groups_list)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting groups: {e}")
        return jsonify({
            "error": f"Failed to get groups: {str(e)}",
            "groups": []
        }), 500

@group_bp.route("/delete_group/<group_id>", methods=["DELETE"])
def delete_group_legacy(group_id):
    """Legacy delete endpoint for backward compatibility with frontend"""
    return delete_group(group_id)

@group_bp.route("/groups/<group_id>", methods=["DELETE"])
def delete_group(group_id):
    """Delete a group and clean up Docker container"""
    try:
        state = get_state()
        
        if not hasattr(state, 'groups') or group_id not in state.groups:
            return jsonify({"error": f"Group {group_id} not found"}), 404
        
        with state.groups_lock:
            group_data = state.groups[group_id]
            group_name = group_data.get('name', 'Unknown')
            
            # Stop FFmpeg process if running
            ffmpeg_process_id = group_data.get('ffmpeg_process_id')
            if ffmpeg_process_id and is_process_running(ffmpeg_process_id):
                try:
                    process = psutil.Process(ffmpeg_process_id)
                    process.terminate()
                    logger.info(f"Stopped FFmpeg process {ffmpeg_process_id}")
                except Exception as e:
                    logger.warning(f"Failed to stop FFmpeg process: {e}")
            
            # Stop and remove Docker container if it exists
            container_id = group_data.get('docker_container_id')
            if container_id:
                try:
                    stop_cmd = ["docker", "stop", container_id]
                    success, output, error = run_command(stop_cmd)
                    if success:
                        logger.info(f"Stopped Docker container {container_id[:12]}")
                    
                    remove_cmd = ["docker", "rm", container_id]
                    success, output, error = run_command(remove_cmd)
                    if success:
                        logger.info(f"Removed Docker container {container_id[:12]}")
                    
                except Exception as e:
                    logger.warning(f"Failed to clean up Docker container: {e}")
            
            # Remove group from state
            del state.groups[group_id]
            logger.info(f"✅ Deleted group '{group_name}' (ID: {group_id})")
        
        return jsonify({
            "message": f"Group '{group_name}' deleted successfully",
            "group_id": group_id
        }), 200
        
    except Exception as e:
        logger.error(f"Error deleting group: {e}")
        return jsonify({"error": f"Error deleting group: {str(e)}"}), 500

@group_bp.route("/api/groups/<group_id>/status", methods=["GET"])
def get_group_status(group_id):
    """Check the actual running status of a group's processes"""
    try:
        group = get_group_by_id(group_id)
        if not group:
            return jsonify({"error": "Group not found"}), 404
        
        # Check FFmpeg process status
        ffmpeg_running = is_process_running(group.get('ffmpeg_process_id'))
        ffmpeg_process_id = group.get('ffmpeg_process_id') if ffmpeg_running else None
        
        # Check Docker container status (simplified)
        docker_running = False
        docker_container_id = group.get('docker_container_id')
        if docker_container_id:
            try:
                import docker
                client = docker.from_env()
                container = client.containers.get(docker_container_id)
                docker_running = container.status == 'running'
            except:
                docker_running = False
                docker_container_id = None
        
        # Determine overall status
        is_running = ffmpeg_running
        
        # Update status if there's a mismatch
        current_status = group.get('status', 'inactive')
        if current_status != ('active' if is_running else 'inactive'):
            update_group_status(group_id, 'active' if is_running else 'inactive')
        
        return jsonify({
            "group_id": group_id,
            "is_running": is_running,
            "ffmpeg_running": ffmpeg_running,
            "ffmpeg_process_id": ffmpeg_process_id,
            "docker_running": docker_running,
            "docker_container_id": docker_container_id,
            "status": "active" if is_running else "inactive"
        })
        
    except Exception as e:
        logger.error(f"Failed to check group status for {group_id}: {e}")
        return jsonify({
            "error": f"Failed to check group status: {str(e)}",
            "is_running": False
        }), 500

@group_bp.route("/api/system/sync", methods=["POST"]) 
def sync_all_groups():
    """Sync status for all groups"""
    try:
        state = get_state()
        
        if not hasattr(state, 'groups'):
            return jsonify({"groups": [], "sync_results": []}), 200
        
        sync_results = []
        
        with state.groups_lock:
            for group_id, group_data in state.groups.items():
                try:
                    # Check process status
                    ffmpeg_running = is_process_running(group_data.get('ffmpeg_process_id'))
                    
                    # Determine new status
                    old_status = group_data.get('status', 'inactive')
                    new_status = "active" if ffmpeg_running else "inactive"
                    status_changed = old_status != new_status
                    
                    # Update status if changed
                    if status_changed:
                        group_data['status'] = new_status
                        group_data['last_updated'] = time.time()
                    
                    sync_results.append({
                        'group_id': group_id,
                        'group_name': group_data.get('name', 'Unknown'),
                        'old_status': old_status,
                        'new_status': new_status,
                        'status_changed': status_changed,
                        'ffmpeg_running': ffmpeg_running
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to sync group {group_id}: {e}")
                    sync_results.append({
                        'group_id': group_id,
                        'group_name': group_data.get('name', 'Unknown'),
                        'error': str(e),
                        'status_changed': False
                    })
        
        logger.info(f"Synchronized {len(sync_results)} groups")
        
        return jsonify({
            "message": f"Synchronized {len(sync_results)} groups",
            "sync_results": sync_results,
            "sync_timestamp": time.time()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to sync all groups: {e}")
        return jsonify({
            "error": f"Failed to sync groups: {str(e)}",
            "sync_timestamp": time.time()
        }), 500