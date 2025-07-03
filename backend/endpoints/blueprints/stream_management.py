from flask import Blueprint, request, jsonify, current_app
import os
import json
import subprocess
import threading
import traceback
import psutil
import logging
import time
from typing import Dict, List, Any, Tuple, Optional

try:
    from utils.video_utils import get_video_resolution
    from utils.ffmpeg_utils import build_ffmpeg_filter_chain, calculate_section_info, build_group_ffmpeg_filter_chain
    UTILS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Could not import utils: {e}")
    UTILS_AVAILABLE = False

from blueprints.client_management import get_available_videos

# Configure logger
logger = logging.getLogger(__name__)

# Create blueprint
stream_bp = Blueprint('stream', __name__)

# Get app state function
def get_state():
    return current_app.config['APP_STATE']

def build_simple_ffmpeg_filter_chain(
    video_width: int,
    video_height: int,
    screen_count: int,
    orientation: str,
    srt_ip: str,
    sei: str,
    grid_rows: int = 2,
    grid_cols: int = 2
) -> Tuple[str, List[str]]:
    """
    Fallback implementation of FFmpeg filter chain builder with grid support
    Used when utils.ffmpeg_utils is not available
    """
    filter_complex = []
    output_mappings = []
    
    # Input validation
    if screen_count < 1:
        screen_count = 1
    
    # For grid layout, ensure screen_count matches grid dimensions
    if orientation.lower() == "grid":
        screen_count = grid_rows * grid_cols
    
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
                "-f", "mpegts", f"srt://{srt_ip}:10080?streamid=#!::r=live/test{i},m=publish"
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
                "-f", "mpegts", f"srt://{srt_ip}:10080?streamid=#!::r=live/test{i},m=publish"
            ])
    elif orientation.lower() == "grid":
        # Grid layout (rows × columns)
        section_width = video_width // grid_cols
        section_height = video_height // grid_rows
        width_remainder = video_width % grid_cols
        height_remainder = video_height % grid_rows
        
        for i in range(screen_count):
            # Calculate grid position
            row = i // grid_cols
            col = i % grid_cols
            
            # Calculate section dimensions (distribute remainder pixels)
            current_width = section_width + (width_remainder if col == grid_cols-1 else 0)
            current_height = section_height + (height_remainder if row == grid_rows-1 else 0)
            
            # Calculate starting position
            start_x = col * section_width
            start_y = row * section_height
            
            filter_complex.append(
                f"[part{i}]crop={current_width}:{current_height}:{start_x}:{start_y}[out{i}];"
            )
            
            output_mappings.extend([
                "-map", f"[out{i}]",
                "-an", "-c:v", "libx264",
                "-bsf:v", f"h264_metadata=sei_user_data={sei}",
                "-pes_payload_size", "0",
                "-bf", "0",
                "-g", "1",
                "-f", "mpegts", f"srt://{srt_ip}:10080?streamid=#!::r=live/test{i},m=publish"
            ])
    
    # Always add the full video output
    output_mappings.extend([
        "-map", "[full]",
        "-an", "-c:v", "libx264",
        "-bsf:v", f"h264_metadata=sei_user_data={sei}",
        "-pes_payload_size", "0",
        "-bf", "0",
        "-g", "1",
        "-f", "mpegts", f"srt://{srt_ip}:10080?streamid=#!::r=live/test,m=publish"
    ])
    
    # Remove the last semicolon from the filter complex
    if filter_complex[-1].endswith(';'):
        filter_complex[-1] = filter_complex[-1][:-1]
    
    # Combine all filter parts
    filter_complex_str = ''.join(filter_complex)
    
    return filter_complex_str, output_mappings

def calculate_simple_section_info(
    video_width: int,
    video_height: int,
    screen_count: int,
    orientation: str,
    grid_rows: int = 2,
    grid_cols: int = 2
) -> List[Dict[str, Any]]:
    """
    Fallback implementation of section info calculator with grid support
    Used when utils.ffmpeg_utils is not available
    """
    section_info = []
    
    # Input validation
    if screen_count < 1:
        screen_count = 1
    
    # For grid layout, ensure screen_count matches grid dimensions
    if orientation.lower() == "grid":
        screen_count = grid_rows * grid_cols
    
    if orientation.lower() == "horizontal":
        section_width = video_width // screen_count
        remainder = video_width % screen_count
        
        for i in range(screen_count):
            current_width = section_width + (remainder if i == screen_count-1 else 0)
            start_x = i * section_width
            section_info.append({
                "section": i+1,
                "x": start_x,
                "y": 0,
                "width": current_width,
                "height": video_height,
                "stream_id": f"live/test{i}",
                "position": f"Column {i+1}",
                "layout_type": "horizontal"
            })
    elif orientation.lower() == "vertical":
        section_height = video_height // screen_count
        remainder = video_height % screen_count
        
        for i in range(screen_count):
            current_height = section_height + (remainder if i == screen_count-1 else 0)
            start_y = i * section_height
            section_info.append({
                "section": i+1,
                "x": 0,
                "y": start_y,
                "width": video_width,
                "height": current_height,
                "stream_id": f"live/test{i}",
                "position": f"Row {i+1}",
                "layout_type": "vertical"
            })
    elif orientation.lower() == "grid":
        section_width = video_width // grid_cols
        section_height = video_height // grid_rows
        width_remainder = video_width % grid_cols
        height_remainder = video_height % grid_rows
        
        for i in range(screen_count):
            # Calculate grid position
            row = i // grid_cols
            col = i % grid_cols
            
            # Calculate section dimensions (distribute remainder pixels)
            current_width = section_width + (width_remainder if col == grid_cols-1 else 0)
            current_height = section_height + (height_remainder if row == grid_rows-1 else 0)
            
            # Calculate starting position
            start_x = col * section_width
            start_y = row * section_height
            
            section_info.append({
                "section": i+1,
                "x": start_x,
                "y": start_y,
                "width": current_width,
                "height": current_height,
                "stream_id": f"live/test{i}",
                "position": f"Row {row+1}, Col {col+1}",
                "grid_row": row + 1,
                "grid_col": col + 1,
                "layout_type": "grid"
            })
            
    return section_info

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

@stream_bp.route("/start_group_srt", methods=["POST"])
def start_group_srt():
    """Start SRT streaming for a specific group with group-specific configuration"""
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
        
        # Check if group has a running Docker container
        container_id = group.get("docker_container_id")
        if not container_id:
            return jsonify({"error": f"Group '{group_name}' must have a running Docker container before starting SRT"}), 400
        
        # Check if group already has a running SRT stream
        existing_process_id = group.get("ffmpeg_process_id")
        if existing_process_id:
            try:
                process = psutil.Process(existing_process_id)
                if process.is_running():
                    return jsonify({
                        "message": f"Group '{group_name}' already has a running SRT stream",
                        "process_id": existing_process_id
                    }), 200
            except:
                # Process not found, clear the ID
                group["ffmpeg_process_id"] = None
        
        logger.info(f"Starting SRT stream for group '{group_name}' (ID: {group_id})")
        
        # Get group configuration
        screen_count = group.get("screen_count", 2)
        orientation = group.get("orientation", "horizontal")
        ports = group.get("ports", {})
        srt_port = ports.get("srt_port", 10080)
        
        # Get video file preference
        requested_file = data.get("mp4_file")
        video_file = data.get("video_file", requested_file)
        
        # Looping configuration
        enable_looping = data.get("enable_looping", True)
        loop_count = data.get("loop_count", -1)
        
        # Remove 'uploads/' prefix if present
        if video_file and video_file.startswith('uploads/'):
            video_file = video_file[8:]
        
        logger.info(f"Group config - Screens: {screen_count}, Orientation: {orientation}, SRT Port: {srt_port}")
        logger.info(f"Video file: {video_file}, Looping: {enable_looping}, Loop count: {loop_count}")
        
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
                logger.info(f"Video dimensions: {width}x{height} @ {framerate}fps")
        
        # Count active clients in this group
        current_time = time.time()
        active_clients = 0
        
        if hasattr(state, 'clients'):
            for client_data in state.clients.values():
                if (client_data.get("group_id") == group_id and 
                    current_time - client_data.get("last_seen", 0) <= 60):
                    active_clients += 1
        
        split_count = screen_count  # Always create all configured streams
        logger.info(f"Creating ALL {split_count} split streams for group {group_name} (configured screens: {screen_count}, active clients: {active_clients})")
        
        
        # Get SRT IP (use Docker container's host IP)
        srt_ip = getattr(state, 'srt_ip', '127.0.0.1')
        
        # SEI identifier for this group
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
            input_args = [
                "-f", "lavfi",
                "-i", f"testsrc=s={width}x{height}:r={framerate}"
            ]
            loop_mode = "automatic"
            video_source = "test_pattern"
        else:
            input_args = []
            
            if enable_looping and loop_count != 0:
                input_args.extend(["-stream_loop", str(loop_count)])
                loop_mode = "infinite" if loop_count == -1 else f"finite_{loop_count}"
            else:
                loop_mode = "once"
            
            input_args.extend(["-re", "-i", mp4_file])
            video_source = "video_file"
        
        # Build filter complex for group-specific streams
        if split_count > 0:
            if UTILS_AVAILABLE:
                filter_complex_str, output_mappings = build_group_ffmpeg_filter_chain(
                    width, height, split_count, orientation, srt_ip, srt_port, sei, group_id
                )
            else:
                filter_complex_str, output_mappings = build_simple_group_ffmpeg_filter_chain(
                    width, height, split_count, orientation, srt_ip, srt_port, sei, group_id
                )
        else:
            # Only full stream
            filter_complex_str = ""
            output_mappings = [
                "-map", "0:v",
                "-an", "-c:v", "libx264",
                "-bsf:v", f"h264_metadata=sei_user_data={sei}",
                "-pes_payload_size", "0",
                "-bf", "0",
                "-g", "1",
                "-f", "mpegts", f"srt://{srt_ip}:{srt_port}?streamid=#!::r=live/{group_id}/test,m=publish"
            ]
        
        # Construct FFmpeg command
        ffmpeg_cmd = [ffmpeg_path, "-y"] + input_args
        
        if filter_complex_str:
            ffmpeg_cmd.extend(["-filter_complex", filter_complex_str])
        
        ffmpeg_cmd.extend(output_mappings)
        
        logger.info(f"FFmpeg command for group {group_name}: {' '.join(ffmpeg_cmd)}")
        
        # Start FFmpeg process
        process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )
        
        # Update group state
        with state.groups_lock if hasattr(state, 'groups_lock') else threading.RLock():
            state.groups[group_id]["ffmpeg_process_id"] = process.pid
            state.groups[group_id]["status"] = "active"
            state.groups[group_id]["current_video"] = video_file or "test_pattern"
            
            # Update available streams
            available_streams = [f"live/{group_id}/test"]
            if split_count > 0:
                for i in range(split_count):
                    available_streams.append(f"live/{group_id}/test{i}")
            state.groups[group_id]["available_streams"] = available_streams
        
        # Start monitoring thread
        def monitor_group_output(process, group_id, group_name):
            while process.poll() is None:
                output = process.stderr.readline()
                if output:
                    logger.info(f"FFmpeg[{group_name}]: {output.strip()}")
            
            logger.info(f"FFmpeg process for group {group_name} ended")
            
            # Clear process ID when done
            if hasattr(state, 'groups') and group_id in state.groups:
                state.groups[group_id]["ffmpeg_process_id"] = None
                if state.groups[group_id]["status"] == "active":
                    state.groups[group_id]["status"] = "inactive"
        
        monitor_thread = threading.Thread(target=monitor_group_output, args=(process, group_id, group_name))
        monitor_thread.daemon = True
        monitor_thread.start()
        
        return jsonify({
            "message": f"SRT stream started for group '{group_name}'",
            "group_id": group_id,
            "group_name": group_name,
            "process_id": process.pid,
            "srt_port": srt_port,
            "available_streams": available_streams,
            "active_clients": active_clients,
            "split_count": split_count,
            "video_source": video_source,
            "loop_mode": loop_mode
        }), 200
        
    except Exception as e:
        logger.error(f"Error starting group SRT: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@stream_bp.route("/stop_group", methods=["POST"])
def stop_group():
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


@stream_bp.route("/stop_group_docker_only", methods=["POST"])
def stop_group_docker_only():
    """Stop only Docker container for a specific group (if SRT was running externally)"""
    try:
        state = get_state()
        data = request.get_json() or {}
        group_id = data.get("group_id")
        
        if not group_id:
            return jsonify({"error": "Missing group_id parameter"}), 400
            
        if not hasattr(state, 'groups') or group_id not in state.groups:
            return jsonify({"error": f"Group {group_id} not found"}), 404
            
        group = state.groups[group_id]
        group_name = group.get("name", group_id)
        container_id = group.get("docker_container_id")
        
        if not container_id:
            return jsonify({"error": f"No Docker container running for group '{group_name}'"}), 400
            
        # Validate container ID format (basic check)
        if not container_id.strip().replace('-', '').isalnum():
            return jsonify({"error": "Invalid container ID format"}), 400
            
        # Stop the container
        success, output, error = run_command(["docker", "stop", container_id])
        
        if not success:
            logger.error(f"Failed to stop Docker container for group {group_id}: {error}")
            return jsonify({"error": error}), 500
            
        # Update only Docker-related state
        with state.groups_lock if hasattr(state, 'groups_lock') else threading.RLock():
            state.groups[group_id]["docker_container_id"] = None
            # Only set to inactive if no SRT stream is running either
            if not group.get("ffmpeg_process_id"):
                state.groups[group_id]["status"] = "inactive"
            
        logger.info(f"Docker container stopped for group '{group_name}'. ID: {container_id}")
        
        return jsonify({
            "message": f"Docker container stopped for group '{group_name}'",
            "group_id": group_id,
            "group_name": group_name,
            "container_id": container_id
        }), 200
        
    except Exception as e:
        logger.error(f"Error stopping Docker only: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

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
                "-f", "mpegts", f"srt://{srt_ip}:{srt_port}?streamid=#!::r=live/{group_id}/test{i},m=publish"
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
                "-f", "mpegts", f"srt://{srt_ip}:{srt_port}?streamid=#!::r=live/{group_id}/test{i},m=publish"
            ])
    
    # Always add the full video output
    output_mappings.extend([
        "-map", "[full]",
        "-an", "-c:v", "libx264",
        "-bsf:v", f"h264_metadata=sei_user_data={sei}",
        "-pes_payload_size", "0",
        "-bf", "0",
        "-g", "1",
        "-f", "mpegts", f"srt://{srt_ip}:{srt_port}?streamid=#!::r=live/{group_id}/test,m=publish"
    ])
    
    # Remove the last semicolon from the filter complex
    if filter_complex[-1].endswith(';'):
        filter_complex[-1] = filter_complex[-1][:-1]
    
    # Combine all filter parts
    filter_complex_str = ''.join(filter_complex)
    
    return filter_complex_str, output_mappings

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
    
