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

@stream_bp.route("/start_srt", methods=["POST"])
def start_srt():
    """Start SRT streaming with FFmpeg - Now supports grid layouts"""
    try:
        # Get app state
        state = get_state()
        
        logger.info("Starting SRT stream with grid support...")
        sei = "681d5c8f-80cd-4847-930a-99b9484b4a32+000000"
        
        # Get parameters from the request
        data = request.get_json() or {}
        requested_file = data.get("mp4_file")
        
        # Remove 'uploads/' prefix if present (for backward compatibility)
        if requested_file and requested_file.startswith('uploads/'):
            requested_file = requested_file[8:]
        
        # Looping configuration options
        enable_looping = data.get("enable_looping", True)
        loop_count = data.get("loop_count", -1)
        
        # Grid configuration from state
        screen_count = getattr(state, 'screen_count', 4)
        orientation = getattr(state, 'orientation', 'horizontal')
        grid_rows = getattr(state, 'grid_rows', 2)
        grid_cols = getattr(state, 'grid_cols', 2)
        
        logger.info(f"Requested file: {requested_file}")
        logger.info(f"Layout: {orientation}, Screen count: {screen_count}")
        if orientation == 'grid':
            logger.info(f"Grid layout: {grid_rows}×{grid_cols}")
        logger.info(f"Looping enabled: {enable_looping}, loop count: {loop_count}")
        
        # Find the best video file to use
        mp4_file, use_test_pattern = find_video_file(requested_file)
        
        # Get video dimensions
        width = 3840
        height = 1080
        framerate = 30
        
        if not use_test_pattern and UTILS_AVAILABLE:
            logger.info("Getting video dimensions with ffprobe...")
            result = get_video_resolution(mp4_file)
            if result and result[0] and result[1]:
                width, height, framerate = result
                logger.info(f"Video dimensions: {width}x{height} @ {framerate}fps")
        
        # ===== DYNAMIC STREAM GENERATION BASED ON CLIENTS =====
        # ===== ALWAYS CREATE ALL CONFIGURED STREAMS =====
        logger.info("Creating all configured streams...")
        streams_info = get_available_streams()
        active_client_count = streams_info["active_clients"]

        logger.info(f"Active clients: {active_client_count}")

        # Always create all configured streams
        if orientation == 'grid':
            split_count = grid_rows * grid_cols
        else:
            split_count = screen_count
        logger.info(f"Creating ALL {split_count} split streams ({orientation} layout) regardless of client count")
        
        # Get SRT IP from state
        srt_ip = getattr(state, 'srt_ip', '127.0.0.1')
        
        # Stop any existing FFmpeg process
        # Instead of killing any process with stored PID
        if hasattr(state, 'ffmpeg_process_id') and state.ffmpeg_process_id:
            try:
                process = psutil.Process(state.ffmpeg_process_id)
                
                # ADD SAFETY CHECK: Only kill if it's actually FFmpeg
                if 'ffmpeg' in process.name().lower() and 'ffplay' not in process.name().lower():
                    process.terminate()
                    # ... rest of cleanup
                else:
                    logger.warning(f"Process {state.ffmpeg_process_id} is not FFmpeg: {process.name()}")
                    
            except:
                pass
        # Prepare FFmpeg command
        ffmpeg_path = os.path.join(current_app.root_path, 'cmake-build-debug/external/Install/bin/ffmpeg')
        if not os.path.exists(ffmpeg_path):
            try:
                ffmpeg_path = subprocess.check_output(['which', 'ffmpeg']).decode().strip()
            except:
                ffmpeg_path = 'ffmpeg'
        
        # Build input arguments with advanced looping control
        if use_test_pattern:
            # Test pattern loops automatically
            input_args = [
                "-f", "lavfi",
                "-i", f"testsrc=s={width}x{height}:r={framerate}"
            ]
            loop_mode = "automatic"
            video_source = "test_pattern"
        else:
            # Video file with configurable looping
            input_args = []
            
            if enable_looping and loop_count != 0:
                # Add stream loop parameter
                input_args.extend(["-stream_loop", str(loop_count)])
                
                if loop_count == -1:
                    loop_mode = "infinite"
                    logger.info("Video will loop infinitely")
                else:
                    loop_mode = f"finite_{loop_count}"
                    logger.info(f"Video will loop {loop_count} times (total plays: {loop_count + 1})")
            else:
                loop_mode = "once"
                logger.info("Video will play once (no looping)")
            
            # Add other video input parameters
            input_args.extend([
                "-re",  # Read input at native frame rate
                "-i", mp4_file
            ])
            
            # Determine if we're using resized or raw video
            download_folder = current_app.config.get('DOWNLOAD_FOLDER', 'resized_video')
            if mp4_file.startswith(download_folder):
                video_source = "resized_video"
            else:
                video_source = "raw_video"
        
        # ===== USE DYNAMIC FILTER CHAIN BUILDER WITH GRID SUPPORT =====
        if split_count > 0:
            if UTILS_AVAILABLE:
                filter_complex_str, output_mappings = build_ffmpeg_filter_chain(
                    width, height, split_count, orientation, srt_ip, sei, grid_rows, grid_cols
                )
            else:
                filter_complex_str, output_mappings = build_simple_ffmpeg_filter_chain(
                    width, height, split_count, orientation, srt_ip, sei, grid_rows, grid_cols
                )
        else:
            # Only full stream - simple case
            filter_complex_str = ""
            output_mappings = [
                "-map", "0:v",
                "-an", "-c:v", "libx264",
                "-bsf:v", f"h264_metadata=sei_user_data={sei}",
                "-pes_payload_size", "0",
                "-bf", "0",
                "-g", "1",
                "-f", "mpegts", f"srt://{srt_ip}:10080?streamid=#!::r=live/test,m=publish"
            ]
        
        # Construct the final FFmpeg command
        ffmpeg_cmd = [
            ffmpeg_path,
            "-y"
        ] + input_args
        
        # Add filter complex only if we have splits
        if filter_complex_str:
            ffmpeg_cmd.extend(["-filter_complex", filter_complex_str])
        
        # Add output mappings
        ffmpeg_cmd.extend(output_mappings)
        
        # Print full command for debugging
        logger.info("Executing FFmpeg command:")
        logger.info(" ".join(ffmpeg_cmd))
        
        # Start the ffmpeg process
        process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )
        
        # Store the process ID globally
        state.ffmpeg_process_id = process.pid
        
        # Create a background thread to capture and print output in real-time
        def monitor_output(process):
            while process.poll() is None:
                output = process.stderr.readline()
                if output:
                    logger.info(f"FFmpeg: {output.strip()}")
            
            logger.info(f"FFmpeg process {process.pid} ended")
        
        # Start the monitoring thread
        monitor_thread = threading.Thread(target=monitor_output, args=(process,))
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # ===== CALCULATE SECTION DETAILS FOR RESPONSE =====
        if split_count > 0:
            if UTILS_AVAILABLE:
                section_info = calculate_section_info(
                    width, height, split_count, orientation, grid_rows, grid_cols
                )
            else:
                section_info = calculate_simple_section_info(
                    width, height, split_count, orientation, grid_rows, grid_cols
                )
        else:
            section_info = [{
                "section": 1,
                "x": 0,
                "y": 0,
                "width": width,
                "height": height,
                "stream_id": "live/test",
                "position": "Full Screen",
                "layout_type": orientation
            }]
        
        # Build available streams list
        created_streams = ["live/test"]
        if split_count > 0:
            for i in range(split_count):
                created_streams.append(f"live/test{i}")
        
        # Build layout description
        if orientation == 'grid':
            layout_description = f"{grid_rows}×{grid_cols} grid"
        else:
            layout_description = f"{orientation} layout"
        
        # Determine message based on video source and looping configuration
        if use_test_pattern:
            message = f"SRT stream started with test pattern ({layout_description}, automatic loop)"
        elif video_source == "resized_video":
            if enable_looping and loop_count == -1:
                message = f"SRT stream started with 2K resized video ({layout_description}, infinite loop)"
            elif enable_looping and loop_count > 0:
                message = f"SRT stream started with 2K resized video ({layout_description}, loop {loop_count} times)"
            else:
                message = f"SRT stream started with 2K resized video ({layout_description}, play once)"
        else:  # raw_video
            if enable_looping and loop_count == -1:
                message = f"SRT stream started with raw video ({layout_description}, infinite loop) - Consider using resized version"
            elif enable_looping and loop_count > 0:
                message = f"SRT stream started with raw video ({layout_description}, loop {loop_count} times) - Consider using resized version"
            else:
                message = f"SRT stream started with raw video ({layout_description}, play once) - Consider using resized version"
        
        # Return comprehensive response
        return jsonify({
            "message": message,
            "pid": process.pid,
            "input_file": None if use_test_pattern else mp4_file,
            "video_dimensions": f"{width}x{height}",
            "screen_count": screen_count,
            "orientation": orientation,
            "grid_rows": grid_rows,
            "grid_cols": grid_cols,
            "layout_description": layout_description,
            "srt_ip": srt_ip,
            "section_details": section_info,
            "available_streams": created_streams,
            "active_clients": active_client_count,
            "generated_sections": split_count,
            "streaming_mode": "full_only" if split_count == 0 else f"{split_count}_splits",
            "utils_available": UTILS_AVAILABLE,
            # Looping information
            "looping_enabled": enable_looping,
            "loop_count": loop_count,
            "loop_mode": loop_mode,
            "video_source": video_source,
            # Folder information
            "raw_folder": current_app.config.get('UPLOAD_FOLDER', 'raw_video_file'),
            "resized_folder": current_app.config.get('DOWNLOAD_FOLDER', 'resized_video')
        }), 200
        
    except Exception as e:
        error_msg = f"Error starting SRT stream: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return jsonify({
            "error": error_msg,
            "traceback": traceback.format_exc()
        }), 500

@stream_bp.route("/stop_srt", methods=["POST"])
def stop_srt():
    """Stop the SRT FFmpeg stream"""
    try:
        # Get app state
        state = get_state()
        
        logger.info("Stopping SRT stream...")
        
        # Try to get the process ID from state or request
        data = request.get_json(silent=True) or {}
        process_id = data.get("pid") or getattr(state, 'ffmpeg_process_id', None)
        
        if not process_id:
            logger.info("No PID provided, attempting to find FFmpeg processes...")
            # Try to find ffmpeg processes
            ffmpeg_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
                try:
                    if 'ffmpeg' in proc.info['name'].lower() or (proc.info['cmdline'] and 'ffmpeg' in ' '.join(proc.info['cmdline']).lower()):
                        ffmpeg_processes.append(proc)
                except:
                    pass
            
            if not ffmpeg_processes:
                return jsonify({"message": "No FFmpeg processes found running"}), 200
            
            # Sort by creation time (newest first) and take the first one
            ffmpeg_processes.sort(key=lambda p: p.info['create_time'], reverse=True)
            process_id = ffmpeg_processes[0].info['pid']
            logger.info(f"Found FFmpeg process with PID: {process_id}")
        
        logger.info(f"Stopping FFmpeg process with PID: {process_id}")
        
        # Try to terminate the process
        try:
            process = psutil.Process(process_id)
            process.terminate()
            
            # Wait for it to terminate
            try:
                process.wait(timeout=5)
                logger.info(f"Process {process_id} terminated gracefully")
            except:
                # Force kill if it doesn't terminate
                logger.warning(f"Process {process_id} did not terminate gracefully, force killing")
                process.kill()
            
            # Clear stored process ID
            if hasattr(state, 'ffmpeg_process_id') and state.ffmpeg_process_id == process_id:
                state.ffmpeg_process_id = None
                
            return jsonify({
                "message": "SRT stream stopped successfully",
                "pid": process_id
            }), 200
            
        except Exception as e:
            error_msg = f"Error stopping process {process_id}: {str(e)}"
            logger.error(error_msg)
            
            # Try to find and kill all ffmpeg processes as a fallback
            try:
                subprocess.run(["pkill", "-f", "ffmpeg"], 
                               stdout=subprocess.DEVNULL, 
                               stderr=subprocess.DEVNULL)
                logger.info("Tried pkill -f ffmpeg as fallback")
            except:
                pass
                
            # Clear stored process ID anyway
            if hasattr(state, 'ffmpeg_process_id'):
                state.ffmpeg_process_id = None
                
            return jsonify({
                "message": "Attempted to stop all FFmpeg processes",
                "error": error_msg
            }), 200
    
    except Exception as e:
        error_msg = f"Error stopping SRT stream: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        
        # Try to kill ffmpeg processes anyway
        try:
            subprocess.run(["pkill", "-f", "ffmpeg"], 
                          stdout=subprocess.DEVNULL, 
                          stderr=subprocess.DEVNULL)
        except:
            pass
            
        return jsonify({
            "error": error_msg,
            "message": "Attempted emergency shutdown of all FFmpeg processes",
            "traceback": traceback.format_exc()
        }), 500
    
# Add these endpoints to your existing stream_management.py file

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

@stream_bp.route("/stop_group_srt", methods=["POST"])
def stop_group_srt():
    """Stop SRT streaming for a specific group"""
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
        process_id = group.get("ffmpeg_process_id")
        
        if not process_id:
            return jsonify({"error": f"No SRT stream running for group '{group_name}'"}), 400
        
        logger.info(f"Stopping SRT stream for group '{group_name}' (PID: {process_id})")
        
        try:
            process = psutil.Process(process_id)
            process.terminate()
            
            try:
                process.wait(timeout=5)
                logger.info(f"SRT process for group {group_name} terminated gracefully")
            except:
                logger.warning(f"SRT process for group {group_name} did not terminate gracefully, force killing")
                process.kill()
                
        except Exception as e:
            logger.error(f"Error stopping SRT process for group {group_name}: {e}")
        
        # Update group state
        with state.groups_lock if hasattr(state, 'groups_lock') else threading.RLock():
            state.groups[group_id]["ffmpeg_process_id"] = None
            state.groups[group_id]["status"] = "inactive"
            state.groups[group_id]["available_streams"] = []
        
        return jsonify({
            "message": f"SRT stream stopped for group '{group_name}'",
            "group_id": group_id,
            "group_name": group_name,
            "process_id": process_id
        }), 200
        
    except Exception as e:
        logger.error(f"Error stopping group SRT: {e}")
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
    
