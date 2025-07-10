from flask import Blueprint, request, jsonify, current_app
import os
import subprocess
import threading
import traceback
import psutil
import logging
import time
from typing import Dict, List, Any, Tuple, Optional

try:
    from utils.video_utils import get_video_resolution
    from utils.ffmpeg_utils import build_ffmpeg_filter_chain
    UTILS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Could not import utils: {e}")
    UTILS_AVAILABLE = False

# Configure logger
logger = logging.getLogger(__name__)

# Create blueprint
stream_bp = Blueprint('stream', __name__)

# Get app state function
def get_state():
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

def find_video_file(requested_file: str = None) -> Tuple[str, bool]:
    """
    Find a video file to use for streaming
    
    Args:
        requested_file: Specific file requested (optional)
        
    Returns:
        Tuple of (file_path, use_test_pattern)
    """
    # First, try to use resized videos (preferred)
    download_folder = current_app.config.get('DOWNLOAD_FOLDER', 'resized_video')
    
    if requested_file:
        # Check if specific file exists in resized folder
        resized_path = os.path.join(download_folder, requested_file)
        if os.path.isfile(resized_path):
            logger.info(f"Using requested resized video: {resized_path}")
            return resized_path, False
            
        # Check if it exists with 2k_ prefix
        prefixed_name = f"2k_{requested_file}"
        prefixed_path = os.path.join(download_folder, prefixed_name)
        if os.path.isfile(prefixed_path):
            logger.info(f"Using prefixed resized video: {prefixed_path}")
            return prefixed_path, False
    
    # If no specific file requested, find any resized video
    if os.path.exists(download_folder):
        video_extensions = ('.mp4', '.mkv', '.avi', '.mov', '.webm')
        try:
            for filename in os.listdir(download_folder):
                if filename.lower().endswith(video_extensions):
                    file_path = os.path.join(download_folder, filename)
                    logger.info(f"Using available resized video: {file_path}")
                    return file_path, False
        except Exception as e:
            logger.warning(f"Error scanning resized videos folder: {e}")
    
    # Fallback: try raw videos folder
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'raw_video_file')
    
    if requested_file:
        raw_path = os.path.join(upload_folder, requested_file)
        if os.path.isfile(raw_path):
            logger.warning(f"Using raw video (resized version not found): {raw_path}")
            return raw_path, False
    
    # Find any raw video as last resort
    if os.path.exists(upload_folder):
        video_extensions = ('.mp4', '.mkv', '.avi', '.mov', '.webm')
        try:
            for filename in os.listdir(upload_folder):
                if filename.lower().endswith(video_extensions):
                    file_path = os.path.join(upload_folder, filename)
                    logger.warning(f"Using available raw video: {file_path}")
                    return file_path, False
        except Exception as e:
            logger.warning(f"Error scanning raw videos folder: {e}")
    
    # No video files found, use test pattern
    logger.info("No video files found, will use test pattern")
    return "", True

def build_simple_group_ffmpeg_filter_chain(
    video_width: int,
    video_height: int,
    screen_count: int,
    orientation: str,
    srt_ip: str,
    srt_port: int,
    sei: str,
    group_id: str
) -> Tuple[str, List[str]]:
    """
    Build FFmpeg filter chain for group-specific SRT streaming
    """
    filter_complex = []
    output_mappings = []
    
    # Start with splitting the input
    split_str = f"[0:v]split={screen_count+1}[full]"
    for i in range(screen_count):
        split_str += f"[part{i}]"
    filter_complex.append(split_str + ";")
    
    # Calculate section sizes based on orientation
    if orientation.lower() == "horizontal":
        section_width = video_width // screen_count
        remainder = video_width % screen_count
        
        for i in range(screen_count):
            current_width = section_width + (remainder if i == screen_count-1 else 0)
            start_x = i * section_width
            
            filter_complex.append(
                f"[part{i}]crop={current_width}:{video_height}:{start_x}:0[out{i}];"
            )
            
            output_mappings.extend([
                "-map", f"[out{i}]",
                "-an", "-c:v", "libx264",
                "-bsf:v", f"h264_metadata=sei_user_data={sei}",
                "-pes_payload_size", "0",
                "-bf", "0",
                "-g", "1",
                "-f", "mpegts", f"srt://{srt_ip}:10080?streamid=#!::r=live/{group_id}/test{i},m=publish"
            ])
    elif orientation.lower() == "vertical":
        section_height = video_height // screen_count
        remainder = video_height % screen_count
        
        for i in range(screen_count):
            current_height = section_height + (remainder if i == screen_count-1 else 0)
            start_y = i * section_height
            
            filter_complex.append(
                f"[part{i}]crop={video_width}:{current_height}:0:{start_y}[out{i}];"
            )
            
            output_mappings.extend([
                "-map", f"[out{i}]",
                "-an", "-c:v", "libx264",
                "-bsf:v", f"h264_metadata=sei_user_data={sei}",
                "-pes_payload_size", "0",
                "-bf", "0",
                "-g", "1",
                "-f", "mpegts", f"srt://{srt_ip}:10080?streamid=#!::r=live/{group_id}/test{i},m=publish"
            ])
    
    # Always add the full video output
    output_mappings.extend([
        "-map", "[full]",
        "-an", "-c:v", "libx264",
        "-bsf:v", f"h264_metadata=sei_user_data={sei}",
        "-pes_payload_size", "0",
        "-bf", "0",
        "-g", "1",
        "-f", "mpegts", f"srt://{srt_ip}:10080?streamid=#!::r=live/{group_id}/test,m=publish"
    ])
    
    # Remove the last semicolon from the filter complex
    if filter_complex[-1].endswith(';'):
        filter_complex[-1] = filter_complex[-1][:-1]
    
    # Combine all filter parts
    filter_complex_str = ''.join(filter_complex)
    
    return filter_complex_str, output_mappings


    """Stop both SRT streaming and Docker container for a specific group"""
    try:
        # Get app state
        state = get_state()
        
        # Get group ID from request
        data = request.get_json() or {}
        group_id = data.get("group_id")
        
        if not group_id:
            return jsonify({"error": "Missing group_id parameter"}), 400
            
        if not hasattr(state, 'groups') or group_id not in state.groups:
            return jsonify({"error": f"Group {group_id} not found"}), 404
            
        group = state.groups[group_id]
        group_name = group.get("name", group_id)
        
        results = {
            "group_id": group_id,
            "group_name": group_name,
            "srt_stopped": False,
            "docker_stopped": False,
            "messages": [],
            "errors": []
        }
        
        # Step 1: Stop SRT stream if running
        ffmpeg_process_id = group.get("ffmpeg_process_id")
        if ffmpeg_process_id:
            try:
                logger.info(f"Stopping SRT stream for group '{group_name}' (PID: {ffmpeg_process_id})")
                
                process = psutil.Process(ffmpeg_process_id)
                process.terminate()
                
                try:
                    process.wait(timeout=5)
                    logger.info(f"SRT process for group {group_name} terminated gracefully")
                    results["messages"].append(f"SRT stream stopped gracefully (PID: {ffmpeg_process_id})")
                except:
                    logger.warning(f"SRT process for group {group_name} did not terminate gracefully, force killing")
                    process.kill()
                    results["messages"].append(f"SRT stream force-killed (PID: {ffmpeg_process_id})")
                
                results["srt_stopped"] = True
                
            except Exception as e:
                error_msg = f"Failed to stop SRT stream: {str(e)}"
                logger.error(f"Error stopping SRT process for group {group_name}: {e}")
                results["errors"].append(error_msg)
        else:
            results["messages"].append("No SRT stream was running")
        
        # Step 2: Stop Docker container if running
        container_id = group.get("docker_container_id")
        if container_id:
            try:
                logger.info(f"Stopping Docker container for group '{group_name}' (ID: {container_id})")
                
                # Validate container ID format (basic check)
                if not container_id.strip().replace('-', '').isalnum():
                    raise ValueError("Invalid container ID format")
                
                # Stop the container
                success, output, error = run_command(["docker", "stop", container_id])
                
                if success:
                    logger.info(f"Docker container stopped for group '{group_name}'. ID: {container_id}")
                    results["messages"].append(f"Docker container stopped (ID: {container_id})")
                    results["docker_stopped"] = True
                else:
                    error_msg = f"Failed to stop Docker container: {error}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
                    
            except Exception as e:
                error_msg = f"Failed to stop Docker container: {str(e)}"
                logger.error(f"Error stopping Docker container for group {group_name}: {e}")
                results["errors"].append(error_msg)
        else:
            results["messages"].append("No Docker container was running")
        
        # Step 3: Update group state (always do this to clean up)
        try:
            with state.groups_lock if hasattr(state, 'groups_lock') else threading.RLock():
                state.groups[group_id]["ffmpeg_process_id"] = None
                state.groups[group_id]["docker_container_id"] = None
                state.groups[group_id]["status"] = "inactive"
                state.groups[group_id]["available_streams"] = []
                
            results["messages"].append("Group state updated to inactive")
            logger.info(f"Group '{group_name}' state updated to inactive")
            
        except Exception as e:
            error_msg = f"Failed to update group state: {str(e)}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
        
        # Determine response status
        if results["errors"]:
            if results["srt_stopped"] or results["docker_stopped"]:
                # Partial success
                results["status"] = "partial_success"
                return jsonify(results), 207  # Multi-Status
            else:
                # Complete failure
                results["status"] = "failed"
                return jsonify(results), 500
        else:
            # Complete success
            results["status"] = "success"
            results["message"] = f"Group '{group_name}' stopped successfully"
            return jsonify(results), 200
            
    except Exception as e:
        error_msg = f"Error stopping group: {str(e)}"
        logger.error(error_msg)
        traceback.print_exc()
        return jsonify({
            "error": error_msg,
            "group_id": group_id if 'group_id' in locals() else None,
            "traceback": traceback.format_exc()
        }), 500

def send_websocket_update(group_id: str, event_type: str, data: dict):
    """Send WebSocket update if available"""
    try:
        from flask import current_app
        broadcast_functions = current_app.config.get('WEBSOCKET_BROADCAST', {})
        
        if event_type == 'group_status' and 'group_status' in broadcast_functions:
            broadcast_functions['group_status'](group_id, data)
        elif event_type == 'system_status' and 'system_status' in broadcast_functions:
            broadcast_functions['system_status']()
            
    except Exception as e:
        logger.warning(f"Failed to send WebSocket update: {e}")

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


@stream_bp.route("/start_group_complete", methods=["POST"])
def start_group_complete():
    """Start both Docker container and SRT streaming for a group in one operation"""
    try:
        # Get app state
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
        
        results = {
            "group_id": group_id,
            "group_name": group_name,
            "docker_started": False,
            "srt_started": False,
            "messages": [],
            "errors": []
        }
        
        logger.info(f"Starting complete group setup for '{group_name}' (ID: {group_id})")
        
        # Step 1: Start Docker container
        try:
            # Check if Docker is available
            success, docker_version, error = run_command(["docker", "--version"])
            if not success:
                raise Exception(f"Docker not available: {error}")
            
            # Check if group already has a running container
            existing_container_id = group.get("docker_container_id")
            if existing_container_id:
                # Check if container is still running
                check_cmd = ["docker", "ps", "-q", "--filter", f"id={existing_container_id}"]
                success, output, _ = run_command(check_cmd)
                if success and output.strip():
                    results["messages"].append(f"Docker container already running (ID: {existing_container_id})")
                    results["docker_started"] = True
                else:
                    # Clear stale container ID
                    group["docker_container_id"] = None
            
            if not results["docker_started"]:
                # Calculate ports for this group
                ports = calculate_group_ports(group_id, state.groups)
                
                # Start new Docker container
                container_name = f"srs-group-{group_id[:8]}"
                
                cmd = [
                    "docker", "run", 
                    "--rm", 
                    "-d",
                    "--name", container_name,
                    "-p", f"{ports['rtmp_port']}:1935",
                    "-p", f"{ports['http_port']}:1985",
                    "-p", f"{ports['api_port']}:8080",
                    "-p", f"{ports['srt_port']}:10080/udp",
                    "ossrs/srs:5", 
                    "./objs/srs", 
                    "-c", "conf/srt.conf"
                ]
                
                logger.info(f"Starting Docker container: {' '.join(cmd)}")
                success, container_id, error = run_command(cmd)
                
                if not success:
                    raise Exception(f"Failed to start Docker container: {error}")
                
                # Update group state with Docker info
                with state.groups_lock if hasattr(state, 'groups_lock') else threading.RLock():
                    state.groups[group_id]["docker_container_id"] = container_id
                    state.groups[group_id]["ports"] = ports
                    state.groups[group_id]["container_name"] = container_name
                
                results["messages"].append(f"Docker container started (ID: {container_id})")
                results["docker_started"] = True
                
                # Wait a moment for container to fully start
                time.sleep(2)
            
        except Exception as e:
            error_msg = f"Failed to start Docker container: {str(e)}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
            return jsonify(results), 500
        
        # Step 2: Start SRT streaming (only if Docker started successfully)
        if results["docker_started"]:
            try:
                # Check if SRT is already running
                existing_process_id = group.get("ffmpeg_process_id")
                if existing_process_id:
                    try:
                        process = psutil.Process(existing_process_id)
                        if process.is_running():
                            results["messages"].append(f"SRT stream already running (PID: {existing_process_id})")
                            results["srt_started"] = True
                        else:
                            # Clear stale process ID
                            group["ffmpeg_process_id"] = None
                    except:
                        # Process not found, clear the ID
                        group["ffmpeg_process_id"] = None
                
                if not results["srt_started"]:
                    # Start SRT streaming using the existing start_group_srt logic
                    # Extract configuration
                    screen_count = group.get("screen_count", 2)
                    orientation = group.get("orientation", "horizontal")
                    ports = group.get("ports", {})
                    srt_port = ports.get("srt_port", 10080)
                    
                    # Get video file preference from request
                    video_file = data.get("video_file") or data.get("mp4_file")
                    enable_looping = data.get("enable_looping", True)
                    loop_count = data.get("loop_count", -1)
                    
                    # Remove 'uploads/' prefix if present
                    if video_file and video_file.startswith('uploads/'):
                        video_file = video_file[8:]
                    
                    # Find video file
                    mp4_file, use_test_pattern = find_video_file(video_file)
                    
                    # Get video dimensions
                    width = 3840
                    height = 1080
                    framerate = 30
                    
                    if not use_test_pattern and UTILS_AVAILABLE:
                        result = get_video_resolution(mp4_file)
                        if result and result[0] and result[1]:
                            width, height, framerate = result
                    
                    # Get SRT IP
                    srt_ip = getattr(state, 'srt_ip', '128.205.39.64')
                    sei = "681d5c8f-80cd-4847-930a-99b9484b4a32+000000"
                    
                    # Find FFmpeg
                    ffmpeg_path = os.path.join(current_app.root_path, 'cmake-build-debug/external/Install/bin/ffmpeg')
                    if not os.path.exists(ffmpeg_path):
                        try:
                            ffmpeg_path = subprocess.check_output(['which', 'ffmpeg']).decode().strip()
                        except:
                            ffmpeg_path = 'ffmpeg'
                    
                    # Build input arguments
                    if use_test_pattern:
                        input_args = ["-f", "lavfi", "-i", f"testsrc=s={width}x{height}:r={framerate}"]
                        video_source = "test_pattern"
                    else:
                        input_args = []
                        if enable_looping and loop_count != 0:
                            input_args.extend(["-stream_loop", str(loop_count)])
                        input_args.extend(["-re", "-i", mp4_file])
                        video_source = "video_file"
                    
                    # Build filter complex
                    if UTILS_AVAILABLE:

                        filter_complex_str, output_mappings = build_ffmpeg_filter_chain(
                            width, height, screen_count, orientation, srt_ip, sei
                        )
                    else:
                        filter_complex_str, output_mappings = build_simple_group_ffmpeg_filter_chain(
                            width, height, screen_count, orientation, srt_ip, srt_port, sei, group_id
                        )
                    
                    # Construct FFmpeg command
                    ffmpeg_cmd = [ffmpeg_path, "-y"] + input_args
                    if filter_complex_str:
                        ffmpeg_cmd.extend(["-filter_complex", filter_complex_str])
                    ffmpeg_cmd.extend(output_mappings)
                    
                    # Start FFmpeg process
                    process = subprocess.Popen(
                        ffmpeg_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True,
                        bufsize=1
                    )
                    
                    # Update group state
                    available_streams = [f"live/{group_id}/test"]
                    for i in range(screen_count):
                        available_streams.append(f"live/{group_id}/test{i}")
                    
                    with state.groups_lock if hasattr(state, 'groups_lock') else threading.RLock():
                        state.groups[group_id]["ffmpeg_process_id"] = process.pid
                        state.groups[group_id]["status"] = "active"
                        state.groups[group_id]["current_video"] = video_file or "test_pattern"
                        state.groups[group_id]["available_streams"] = available_streams
                    
                    # Start monitoring thread
                    def monitor_group_output(process, group_id, group_name):
                        while process.poll() is None:
                            output = process.stderr.readline()
                            if output:
                                logger.info(f"FFmpeg[{group_name}]: {output.strip()}")
                        
                        logger.info(f"FFmpeg process for group {group_name} ended")
                        if hasattr(state, 'groups') and group_id in state.groups:
                            state.groups[group_id]["ffmpeg_process_id"] = None
                            if state.groups[group_id]["status"] == "active":
                                state.groups[group_id]["status"] = "inactive"
                    
                    monitor_thread = threading.Thread(target=monitor_group_output, args=(process, group_id, group_name))
                    monitor_thread.daemon = True
                    monitor_thread.start()
                    
                    results["messages"].append(f"SRT stream started (PID: {process.pid})")
                    results["srt_started"] = True
                    results["process_id"] = process.pid
                    results["available_streams"] = available_streams
                    results["video_source"] = video_source
                    
            except Exception as e:
                error_msg = f"Failed to start SRT stream: {str(e)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
        
        # Determine response status
        if results["docker_started"] and results["srt_started"]:
            send_websocket_update(group_id, 'group_status', {
                'name': group_name,
                'status': 'active',
                'streaming': True,
                'docker_running': True,
                'available_streams': results.get('available_streams', [])
            })
            
            results["status"] = "success"
            results["message"] = f"Group '{group_name}' started successfully (Docker + SRT)"
            return jsonify(results), 200
        elif results["docker_started"] or results["srt_started"]:
            results["status"] = "partial_success"
            results["message"] = f"Group '{group_name}' partially started"
            return jsonify(results), 207
        else:
            results["status"] = "failed"
            results["message"] = f"Failed to start group '{group_name}'"
            return jsonify(results), 500
            
    except Exception as e:
        error_msg = f"Error starting complete group: {str(e)}"
        logger.error(error_msg)
        traceback.print_exc()
        return jsonify({
            "error": error_msg,
            "group_id": group_id if 'group_id' in locals() else None
        }), 500

@stream_bp.route("/stop_group_complete", methods=["POST"])
def stop_group_complete():
    """Stop both SRT streaming and Docker container for a group in one operation"""
    try:
        # Get app state
        state = get_state()
        
        # Get group ID from request
        data = request.get_json() or {}
        group_id = data.get("group_id")
        
        if not group_id:
            return jsonify({"error": "Missing group_id parameter"}), 400
            
        if not hasattr(state, 'groups') or group_id not in state.groups:
            return jsonify({"error": f"Group {group_id} not found"}), 404
            
        group = state.groups[group_id]
        group_name = group.get("name", group_id)
        
        results = {
            "group_id": group_id,
            "group_name": group_name,
            "srt_stopped": False,
            "docker_stopped": False,
            "messages": [],
            "errors": []
        }
        
        logger.info(f"Stopping complete group setup for '{group_name}' (ID: {group_id})")
        
        # Step 1: Stop SRT stream if running
        ffmpeg_process_id = group.get("ffmpeg_process_id")
        if ffmpeg_process_id:
            try:
                logger.info(f"Stopping SRT stream (PID: {ffmpeg_process_id})")
                
                process = psutil.Process(ffmpeg_process_id)
                process.terminate()
                
                try:
                    process.wait(timeout=5)
                    results["messages"].append(f"SRT stream stopped gracefully (PID: {ffmpeg_process_id})")
                except:
                    process.kill()
                    results["messages"].append(f"SRT stream force-killed (PID: {ffmpeg_process_id})")
                
                results["srt_stopped"] = True
                
            except Exception as e:
                error_msg = f"Failed to stop SRT stream: {str(e)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
        else:
            results["messages"].append("No SRT stream was running")
            results["srt_stopped"] = True  # Consider it "stopped" if it wasn't running
        
        # Step 2: Stop Docker container if running
        container_id = group.get("docker_container_id")
        if container_id:
            try:
                logger.info(f"Stopping Docker container (ID: {container_id})")
                
                # Validate container ID format
                if not container_id.strip().replace('-', '').isalnum():
                    raise ValueError("Invalid container ID format")
                
                # Stop the container
                success, output, error = run_command(["docker", "stop", container_id])
                
                if success:
                    results["messages"].append(f"Docker container stopped (ID: {container_id})")
                    results["docker_stopped"] = True
                else:
                    error_msg = f"Failed to stop Docker container: {error}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
                    
            except Exception as e:
                error_msg = f"Failed to stop Docker container: {str(e)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
        else:
            results["messages"].append("No Docker container was running")
            results["docker_stopped"] = True  # Consider it "stopped" if it wasn't running
        
        # Step 3: Update group state (always do this to clean up)
        try:
            with state.groups_lock if hasattr(state, 'groups_lock') else threading.RLock():
                state.groups[group_id]["ffmpeg_process_id"] = None
                state.groups[group_id]["docker_container_id"] = None
                state.groups[group_id]["status"] = "inactive"
                state.groups[group_id]["available_streams"] = []
                
            results["messages"].append("Group state updated to inactive")
            
        except Exception as e:
            error_msg = f"Failed to update group state: {str(e)}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
        
        # Determine response status
        if results["srt_stopped"] and results["docker_stopped"]:
            send_websocket_update(group_id, 'group_status', {
                'name': group_name,
                'status': 'inactive',
                'streaming': False,
                'docker_running': False,
                'available_streams': []
            })
            
            results["status"] = "success"
            results["message"] = f"Group '{group_name}' stopped successfully (SRT + Docker)"
            return jsonify(results), 200
        elif results["srt_stopped"] or results["docker_stopped"]:
            results["status"] = "partial_success"
            results["message"] = f"Group '{group_name}' partially stopped"
            return jsonify(results), 207
        else:
            results["status"] = "failed"
            results["message"] = f"Failed to stop group '{group_name}'"
            return jsonify(results), 500
            
    except Exception as e:
        error_msg = f"Error stopping complete group: {str(e)}"
        logger.error(error_msg)
        traceback.print_exc()
        return jsonify({
            "error": error_msg,
            "group_id": group_id if 'group_id' in locals() else None
        }), 500

@stream_bp.route("/get_group_srt_status", methods=["GET"])
def get_group_srt_status():
    """Get SRT streaming status for all groups or a specific group"""
    try:
        state = get_state()
        
        # Get optional group ID filter
        group_id = request.args.get('group_id')
        
        if not hasattr(state, 'groups'):
            state.groups = {}
        
        srt_status = {}
        
        # Filter groups
        groups_to_check = {group_id: state.groups[group_id]} if group_id and group_id in state.groups else state.groups
        
        for gid, group in groups_to_check.items():
            process_id = group.get("ffmpeg_process_id")
            group_name = group.get("name", gid)
            
            if not process_id:
                srt_status[gid] = {
                    "group_name": group_name,
                    "streaming": False,
                    "message": "No SRT process ID available"
                }
                continue
                
            # Check if the process is running
            try:
                process = psutil.Process(process_id)
                is_running = process.is_running()
            except:
                is_running = False
                # Clear the process ID if not running
                group["ffmpeg_process_id"] = None
                group["status"] = "inactive"
            
            srt_status[gid] = {
                "group_name": group_name,
                "streaming": is_running,
                "process_id": process_id if is_running else None,
                "available_streams": group.get("available_streams", []),
                "current_video": group.get("current_video"),
                "ports": group.get("ports", {}),
                "active_clients": len([c for c in getattr(state, 'clients', {}).values() 
                                     if c.get('group_id') == gid]),
                "last_started": group.get("last_started")
            }
        
        return jsonify({
            "srt_status": srt_status,
            "total_groups": len(groups_to_check),
            "active_streams": len([s for s in srt_status.values() if s["streaming"]])
        }), 200
        
    except Exception as e:
        logger.error(f"Error checking group SRT status: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500