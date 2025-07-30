"""
Stateless Stream Management - Pure Docker Discovery Architecture
No internal state - everything is discovered from Docker containers
"""

from flask import Blueprint, request, jsonify, current_app
import os
import json
import subprocess
import threading
import traceback
import psutil
import logging
import time
import uuid
from typing import Dict, List, Any, Optional

# Create blueprint
stream_bp = Blueprint('stream_management', __name__)

# Configure logger
logger = logging.getLogger(__name__)

# File to store only persistent stream IDs (not group state)
PERSISTENT_IDS_FILE = "persistent_stream_ids.json"

class PersistentIDManager:
    """Manages only persistent stream IDs - no group state"""
    
    def __init__(self):
        self.ids_data = {"streams": {}}
        self._lock = threading.RLock()
        self._load_ids()
    
    def _load_ids(self):
        """Load persistent stream IDs from file"""
        try:
            if os.path.exists(PERSISTENT_IDS_FILE):
                with open(PERSISTENT_IDS_FILE, 'r') as f:
                    self.ids_data = json.load(f)
                logger.info(f"Loaded persistent stream IDs from {PERSISTENT_IDS_FILE}")
            else:
                logger.info("No persistent stream IDs file found, starting fresh")
        except Exception as e:
            logger.error(f"Error loading persistent stream IDs: {e}")
            self.ids_data = {"streams": {}}
    
    def _save_ids(self):
        """Save persistent stream IDs to file"""
        try:
            with open(PERSISTENT_IDS_FILE, 'w') as f:
                json.dump(self.ids_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving persistent stream IDs: {e}")
    
    def get_stream_id(self, group_key: str, stream_name: str) -> str:
        """Get or create persistent stream ID"""
        with self._lock:
            if group_key not in self.ids_data["streams"]:
                self.ids_data["streams"][group_key] = {}
            
            if stream_name not in self.ids_data["streams"][group_key]:
                stream_id = str(uuid.uuid4())[:8]
                self.ids_data["streams"][group_key][stream_name] = stream_id
                self._save_ids()
                logger.info(f"Created new stream ID: {stream_name} -> {stream_id}")
            
            return self.ids_data["streams"][group_key][stream_name]

# Global persistent ID manager
id_manager = PersistentIDManager()



@stream_bp.route("/start_multi_video_srt", methods=["POST"])
def start_multi_video_srt():
    """
    Combine multiple video files and stream as one SRT stream with timestamp embedding.
    Creates a single wide/tall canvas that clients can crop for their specific screens.
    """
    try:
        data = request.get_json() or {}
        
        # Required parameters
        group_id = data.get("group_id")
        video_files_config = data.get("video_files", [])
        
        logger.info(f"🎬 START SINGLE-STREAM MULTI-VIDEO: group_id={group_id}, video_files={len(video_files_config)}")
        
        if not group_id:
            return jsonify({"error": "group_id is required"}), 400
        
        if not video_files_config:
            return jsonify({"error": "video_files list is required"}), 400
        
        # Use Docker discovery
        group = discover_group_from_docker(group_id)
        
        if not group:
            return jsonify({
                "error": f"Group '{group_id}' not found in Docker containers",
                "suggestion": "Create the group first using /create_group endpoint"
            }), 404
        
        group_name = group.get("name", group_id)
        logger.info(f"✅ Found group in Docker: {group_name}")
        
        # Check if Docker container is running
        if not group.get("docker_running", False):
            return jsonify({
                "error": f"Docker container for group '{group_name}' is not running",
                "suggestion": "Start the Docker container first",
                "docker_status": group.get("docker_status", "unknown")
            }), 400
        
        # Check if FFmpeg is already running for this group
        existing_ffmpeg = find_running_ffmpeg_for_group(group_id, group_name)
        if existing_ffmpeg:
            logger.info(f"⚠️ FFmpeg already running for group {group_name}")
            return jsonify({
                "message": f"Single-stream SRT streaming already active for group '{group_name}'",
                "group_id": group_id,
                "group_name": group_name,
                "running_processes": existing_ffmpeg,
                "status": "already_active"
            }), 200
        
        # Configuration with proper defaults
        screen_count = data.get("screen_count", group.get("screen_count", len(video_files_config)))
        orientation = data.get("orientation", group.get("orientation", "horizontal"))
        
        # Individual section dimensions (NOT canvas dimensions)
        output_width = data.get("output_width", 1920)  # Each section width
        output_height = data.get("output_height", 1080)  # Each section height
        
        # Grid layout parameters
        grid_rows = data.get("grid_rows", 2)
        grid_cols = data.get("grid_cols", 2)
        
        # SRT configuration
        ports = group.get("ports", {})
        srt_port = data.get("srt_port", ports.get("srt_port", 10080))
        srt_ip = data.get("srt_ip", "127.0.0.1")
        
        # Clean SEI (remove +000000 suffix if present)
        sei_raw = data.get("sei", "681d5c8f-80cd-4847-930a-99b9484b4a32+000000")
        
        # Keep the full format for h264_metadata filter
        sei = sei_raw if '+' in sei_raw else f"{sei_raw}+000000"
        
        logger.info(f"🔑 Using SEI: '{sei}'")
        
        # Calculate canvas dimensions
        if orientation.lower() == "horizontal":
            canvas_width = output_width * screen_count
            canvas_height = output_height
        elif orientation.lower() == "vertical":
            canvas_width = output_width
            canvas_height = output_height * screen_count
        elif orientation.lower() == "grid":
            if grid_rows * grid_cols != screen_count:
                grid_cols = int(screen_count ** 0.5)
                grid_rows = (screen_count + grid_cols - 1) // grid_cols
            canvas_width = output_width * grid_cols
            canvas_height = output_height * grid_rows
        else:
            return jsonify({"error": f"Invalid orientation: {orientation}"}), 400
        
        logger.info(f"📊 Single-Stream Config: {screen_count} screens, {orientation} layout")
        logger.info(f"📐 Canvas: {canvas_width}x{canvas_height}, Sections: {output_width}x{output_height}")
        
        # Validate video files count
        if len(video_files_config) != screen_count:
            return jsonify({
                "error": f"Video file count ({len(video_files_config)}) must match screen count ({screen_count})"
            }), 400
        
        # Process and validate video files
        video_files = []
        uploads_dir = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        
        # Sort video files by screen number
        video_files_config.sort(key=lambda x: x.get("screen", 0))
        
        # Validate screen assignments
        expected_screens = set(range(screen_count))
        actual_screens = set(config.get("screen", 0) for config in video_files_config)
        
        if expected_screens != actual_screens:
            return jsonify({
                "error": f"Invalid screen assignments. Expected: {sorted(expected_screens)}, Got: {sorted(actual_screens)}"
            }), 400
        
        for video_config in video_files_config:
            screen_num = video_config.get("screen", 0)
            file_name = video_config.get("file")
            
            if not file_name:
                return jsonify({"error": f"Missing file for screen {screen_num}"}), 400
            
            # Construct full file path
            if file_name.startswith('uploads/'):
                file_path = file_name
            else:
                # Try uploads first, then resized_video
                upload_path = os.path.join(uploads_dir, file_name)
                resized_path = os.path.join(current_app.config.get('DOWNLOAD_FOLDER', 'resized_video'), file_name)
                
                if os.path.exists(upload_path):
                    file_path = upload_path
                elif os.path.exists(resized_path):
                    file_path = resized_path
                else:
                    return jsonify({
                        "error": f"Video file not found: {file_name}",
                        "screen": screen_num,
                        "checked_paths": [upload_path, resized_path]
                    }), 404
            
            if not os.path.exists(file_path):
                return jsonify({
                    "error": f"Video file not found: {file_path}",
                    "screen": screen_num
                }), 404
            
            video_files.append(file_path)
            logger.info(f"📹 Screen {screen_num}: {os.path.basename(file_path)}")
        
        # Wait for SRT server to be ready
        logger.info(f"⏳ Waiting for SRT server to be ready...")
        if not wait_for_srt_server(srt_ip, srt_port, timeout=30):
            return jsonify({
                "error": f"SRT server at {srt_ip}:{srt_port} not ready",
                "suggestion": "Check Docker container logs"
            }), 500
        
        # Test SRT connection first
        logger.info(f"🧪 Testing SRT connection...")
        test_result = test_ffmpeg_srt_connection(srt_ip, srt_port, group_name, sei)
        
        if not test_result["success"]:
            return jsonify({
                "error": "SRT connection test failed",
                "test_result": test_result,
                "suggestion": "Check SRT server configuration"
            }), 500
        
        logger.info(f"✅ SRT test passed! Building single-stream FFmpeg command...")
        
        # Generate single stream ID
        stream_id = f"combined_{group_id}"
        
        # Build single-stream FFmpeg command using canvas overlay approach
        ffmpeg_cmd = build_single_stream_ffmpeg_command(
            video_files=video_files,
            screen_count=screen_count,
            orientation=orientation,
            output_width=output_width,
            output_height=output_height,
            srt_ip=srt_ip,
            srt_port=srt_port,
            sei=sei,
            group_name=group_name,
            stream_id=stream_id,
            grid_rows=grid_rows,
            grid_cols=grid_cols
        )
        
        logger.info(f"🎬 Single-stream FFmpeg command: {' '.join(ffmpeg_cmd[:10])}... (truncated)")
        
        # Start FFmpeg process
        try:
            process = start_ffmpeg_with_retry(ffmpeg_cmd, max_retries=3)
            
            logger.info(f"✅ Single-stream FFmpeg started with PID: {process.pid}")
            
            # Generate crop information for clients
            crop_info = generate_client_crop_info(
                screen_count=screen_count,
                orientation=orientation,
                output_width=output_width,
                output_height=output_height,
                grid_rows=grid_rows,
                grid_cols=grid_cols
            )
            
            # Single stream URL with optimized latency
            stream_path = f"live/{group_name}/{stream_id}"
            srt_params = "latency=200000&connect_timeout=5000&rcvbuf=67108864&sndbuf=67108864"
            client_stream_url = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={stream_path},m=request&{srt_params}"
            
            # Generate client connection examples
            client_examples = {}
            for i in range(screen_count):
                crop = crop_info[i]
                client_examples[f"screen_{i}"] = {
                    "description": f"Screen {i} ({orientation} layout)",
                    "stream_url": client_stream_url,
                    "crop_filter": f"crop={crop['width']}:{crop['height']}:{crop['x']}:{crop['y']}",
                    "player_command": f"./player \"{client_stream_url}\" --crop \"{crop['width']}:{crop['height']}:{crop['x']}:{crop['y']}\""
                }
            
            # Monitor FFmpeg output
            def monitor_ffmpeg_output(process, group_name):
                try:
                    consecutive_errors = 0
                    max_consecutive_errors = 3
                    
                    while process.poll() is None:
                        if process.stderr:
                            line = process.stderr.readline()
                            if line:
                                log_line = line.strip()
                                logger.info(f"FFmpeg[{group_name}]: {log_line}")
                                
                                if ("Input/output error" in log_line or 
                                    "Connection refused" in log_line or
                                    "Address already in use" in log_line):
                                    consecutive_errors += 1
                                    logger.warning(f"⚠️ Connection error detected ({consecutive_errors}/{max_consecutive_errors})")
                                    
                                    if consecutive_errors >= max_consecutive_errors:
                                        logger.error(f"💥 Too many consecutive errors, terminating process")
                                        process.terminate()
                                        break
                                else:
                                    consecutive_errors = 0
                    
                    exit_code = process.returncode
                    if exit_code == 0:
                        logger.info(f"✅ Single-stream FFmpeg for group '{group_name}' ended successfully")
                    else:
                        logger.error(f"💥 Single-stream FFmpeg for group '{group_name}' ended with exit code: {exit_code}")
                        
                except Exception as e:
                    logger.error(f"❌ Error monitoring single-stream FFmpeg: {e}")
            
            monitor_thread = threading.Thread(
                target=monitor_ffmpeg_output,
                args=(process, group_name),
                daemon=True
            )
            monitor_thread.start()
            
            # Wait to ensure process stabilizes
            time.sleep(2.0)
            
            if process.poll() is not None:
                exit_code = process.returncode
                stderr_output = process.stderr.read() if process.stderr else ""
                
                return jsonify({
                    "error": f"Single-stream FFmpeg failed to start (exit code {exit_code})",
                    "stderr": stderr_output,
                    "suggestion": "Check video file compatibility and SRT server status"
                }), 500
            
            return jsonify({
                "message": f"Single-stream multi-video SRT streaming started for group '{group_name}'",
                "group_id": group_id,
                "group_name": group_name,
                "process_id": process.pid,
                "configuration": {
                    "screen_count": screen_count,
                    "orientation": orientation,
                    "canvas_resolution": f"{canvas_width}x{canvas_height}",
                    "section_resolution": f"{output_width}x{output_height}",
                    "grid_layout": f"{grid_rows}x{grid_cols}" if orientation == "grid" else None,
                    "video_files": [
                        {
                            "screen": i,
                            "file": os.path.basename(video_files[i]),
                            "path": video_files[i]
                        } for i in range(len(video_files))
                    ]
                },
                "stream_info": {
                    "stream_url": client_stream_url,
                    "stream_path": stream_path,
                    "stream_id": stream_id,
                    "crop_information": crop_info
                },
                "client_instructions": {
                    "connection": f"All clients connect to: {client_stream_url}",
                    "cropping": "Each client crops their section using the crop_information provided",
                    "latency": "Stream optimized for 200ms latency with embedded timestamps"
                },
                "client_examples": client_examples,
                "status": "active",
                "test_result": test_result
            }), 200
            
        except Exception as e:
            logger.error(f"Error starting single-stream FFmpeg: {e}")
            return jsonify({
                "error": f"Failed to start single-stream FFmpeg: {str(e)}",
                "suggestion": "Check video files and SRT server status"
            }), 500
        
    except Exception as e:
        logger.error(f"❌ Error in start_multi_video_srt: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

def build_single_stream_ffmpeg_command(
    video_files: List[str],
    screen_count: int,
    orientation: str,
    output_width: int,
    output_height: int,
    srt_ip: str,
    srt_port: int,
    sei: str,
    group_name: str,
    stream_id: str,
    grid_rows: int = 2,
    grid_cols: int = 2,
    framerate: int = 30,
    bitrate: str = "6000k",
    debug_mode: bool = True
) -> List[str]:
    """
    Build FFmpeg command for single combined stream using canvas overlay approach.
    This matches the pattern from your working FFmpeg command.
    
    Args:
        debug_mode: If True, adds verbose logging and real-time output monitoring
    """
    
    ffmpeg_path = find_ffmpeg_executable()
    
    if debug_mode:
        print(f"\n🎬 BUILDING SINGLE-STREAM FFMPEG COMMAND")
        print(f"📊 Config: {screen_count} screens, {orientation} layout")
        print(f"📐 Sections: {output_width}x{output_height}, Framerate: {framerate}")
        print(f"📺 Videos: {[os.path.basename(f) for f in video_files]}")
        print("=" * 60)
    
    # Build input args with real-time flag for streaming
    input_args = []
    for i, video_file in enumerate(video_files):
        input_args.extend(["-stream_loop", "-1", "-re", "-i", video_file])
        if debug_mode:
            print(f"📹 Input {i}: {os.path.basename(video_file)}")
    
    # Calculate canvas dimensions
    if orientation.lower() == "horizontal":
        canvas_width = output_width * screen_count
        canvas_height = output_height
        section_width = output_width
        section_height = output_height
    elif orientation.lower() == "vertical":
        canvas_width = output_width
        canvas_height = output_height * screen_count
        section_width = output_width
        section_height = output_height
    elif orientation.lower() == "grid":
        if grid_rows * grid_cols != screen_count:
            grid_cols = int(screen_count ** 0.5)
            grid_rows = (screen_count + grid_cols - 1) // grid_cols
        canvas_width = output_width * grid_cols
        canvas_height = output_height * grid_rows
        section_width = output_width
        section_height = output_height
    
    if debug_mode:
        print(f"🖼️ Canvas: {canvas_width}x{canvas_height}")
        print(f"📱 Section size: {section_width}x{section_height}")
    
    # Build filter using canvas overlay approach (like your working command)
    filter_parts = []
    
    # Step 1: Create black canvas
    filter_parts.append(f"color=c=black:s={canvas_width}x{canvas_height}:r={framerate}[canvas]")
    
    # Step 2: Scale each input to section size
    for i in range(screen_count):
        filter_parts.append(f"[{i}:v]scale={section_width}:{section_height}[scaled{i}]")
    
    # Step 3: Overlay each video onto canvas at correct position
    current_stream = "[canvas]"
    for i in range(screen_count):
        if orientation.lower() == "horizontal":
            x_pos = i * section_width
            y_pos = 0
        elif orientation.lower() == "vertical":
            x_pos = 0
            y_pos = i * section_height
        elif orientation.lower() == "grid":
            row = i // grid_cols
            col = i % grid_cols
            x_pos = col * section_width
            y_pos = row * section_height
        
        next_stream = f"[overlay{i}]" if i < screen_count - 1 else "[final]"
        filter_parts.append(f"{current_stream}[scaled{i}]overlay=x={x_pos}:y={y_pos}{next_stream}")
        current_stream = f"[overlay{i}]"
        
        if debug_mode:
            print(f"🔄 Screen {i}: overlay at ({x_pos}, {y_pos})")
    
    complete_filter = ";".join(filter_parts)
    
    if debug_mode:
        print(f"🎛️ Filter chain: {complete_filter}")
    
    # Build FFmpeg command with ultra-low latency settings
    ffmpeg_cmd = [
        ffmpeg_path,
        "-y"  # Overwrite output
    ]
    
    # Add debug verbosity if in debug mode
    if debug_mode:
        ffmpeg_cmd.extend(["-v", "info"])  # Show detailed info
    else:
        ffmpeg_cmd.extend(["-v", "error"])  # Only show errors in production
    
    ffmpeg_cmd.extend(input_args + [
        "-filter_complex", complete_filter,
        "-map", "[final]",
        "-an",  # No audio for now
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-tune", "zerolatency",
        "-maxrate", bitrate,
        "-bufsize", str(int(bitrate.rstrip('k')) * 2) + "k",
        "-bsf:v", f"h264_metadata=sei_user_data={sei}",
        # Ultra low-latency settings (matching your working command)
        "-pes_payload_size", "0",
        "-bf", "0",  # No B-frames
        "-g", "1",   # Every frame is keyframe for minimal latency
        "-r", str(framerate),
        "-f", "mpegts"
    ])
    
    # SRT output configuration
    srt_params = "latency=200000&connect_timeout=5000&rcvbuf=67108864&sndbuf=67108864"
    stream_path = f"live/{group_name}/{stream_id}"
    srt_url = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={stream_path},m=publish&{srt_params}"
    ffmpeg_cmd.append(srt_url)
    
    if debug_mode:
        print(f"📡 SRT URL: {srt_url}")
        print(f"🔧 Complete command:")
        print(f"   {' '.join(ffmpeg_cmd[:10])}...")
        print(f"   ... {len(ffmpeg_cmd)} total arguments")
        print("=" * 60)
    
    return ffmpeg_cmd

def test_ffmpeg_srt_connection(srt_ip, srt_port, group_name, sei):
    """
    Test FFmpeg SRT connection with detailed error output
    """
    import subprocess
    
    logger.info(f"🧪 Testing FFmpeg SRT connection...")
    
    # Clean SEI (remove +000000 if present)
    if '+' not in sei:
        sei = f"{sei}+000000"
    logger.info(f"🔑 Using SEI for test: '{sei}'")

    # Test command
    test_cmd = [
        find_ffmpeg_executable(),
        "-v", "error",  # Show errors
        "-y",
        "-f", "lavfi", "-i", "testsrc=s=640x480:r=5:d=10",
        "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency",
        "-bsf:v", f"h264_metadata=sei_user_data={sei}",
        "-f", "mpegts",
        f"srt://{srt_ip}:{srt_port}?streamid=#!::r=live/{group_name}/test,m=publish"
    ]
    
    logger.info(f"🧪 Test command: {' '.join(test_cmd)}")
    
    try:
        # Run with detailed output capture
        result = subprocess.run(
            test_cmd,
            capture_output=True,
            text=True,
            timeout=15
        )
        
        # Print the actual error output to terminal/logs
        if result.stdout:
            logger.info(f"📺 FFmpeg stdout: {result.stdout}")
            print(f"📺 FFmpeg stdout: {result.stdout}")
            
        if result.stderr:
            logger.error(f"❌ FFmpeg stderr: {result.stderr}")
            print(f"❌ FFmpeg stderr: {result.stderr}")
        
        if result.returncode == 0:
            logger.info(f"✅ FFmpeg SRT test PASSED")
            return {"success": True, "output": result.stdout}
        else:
            logger.error(f"❌ FFmpeg SRT test FAILED with exit code {result.returncode}")
            
            # Try to identify the specific error
            error_output = (result.stderr + " " + result.stdout).lower()
            
            if "connection refused" in error_output:
                error_type = "Connection refused - SRT server may not be accepting connections"
            elif "timeout" in error_output or "timed out" in error_output:
                error_type = "Connection timeout - Network or server issue"
            elif "invalid" in error_output and "streamid" in error_output:
                error_type = "Invalid streamid format - Server doesn't accept this format"
            elif "permission denied" in error_output or "unauthorized" in error_output:
                error_type = "Permission denied - Authentication issue"
            elif "host" in error_output and "not found" in error_output:
                error_type = "Host not found - DNS or IP address issue"
            else:
                error_type = "Unknown error - check FFmpeg output above"
            
            logger.error(f"🔍 Error analysis: {error_type}")
            print(f"🔍 Error analysis: {error_type}")
            
            return {
                "success": False,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "error_analysis": error_type
            }
    
    except subprocess.TimeoutExpired:
        logger.error(f"⏰ FFmpeg test timed out after 15 seconds")
        print(f"⏰ FFmpeg test timed out after 15 seconds")
        return {"success": False, "error": "timeout"}
    
    except Exception as e:
        logger.error(f"💥 Exception during FFmpeg test: {e}")
        print(f"💥 Exception during FFmpeg test: {e}")
        return {"success": False, "error": str(e)}

def start_ffmpeg_with_retry(ffmpeg_cmd: List[str], max_retries: int = 3) -> subprocess.Popen:
    """Start FFmpeg with retry and show real-time output for debugging"""
    
    for attempt in range(max_retries):
        try:
            logger.info(f"🎬 Starting FFmpeg (attempt {attempt + 1}/{max_retries})")
            
            # Show the full command for debugging
            logger.info(f"🔧 Full command: {' '.join(ffmpeg_cmd)}")
            
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Combine stderr with stdout
                universal_newlines=True,
                bufsize=1
            )
            
            # Monitor output for 5 seconds to see what happens
            logger.info(f"📺 Monitoring FFmpeg startup for 5 seconds...")
            start_time = time.time()
            while time.time() - start_time < 5.0:
                if process.poll() is not None:
                    # Process ended
                    exit_code = process.returncode
                    # Read any remaining output
                    remaining_output = process.stdout.read() if process.stdout else ""
                    logger.error(f"💥 FFmpeg exited with code {exit_code}")
                    logger.error(f"💥 Output: {remaining_output}")
                    break
                
                # Read a line of output
                line = process.stdout.readline() if process.stdout else ""
                if line:
                    line = line.strip()
                    logger.info(f"FFmpeg: {line}")
                    print(f"FFmpeg: {line}")
                    
                    # Check for success indicators
                    if any(indicator in line.lower() for indicator in [
                        "frame=", "fps=", "bitrate=", "time="
                    ]):
                        logger.info(f"🟢 Streaming appears to be active!")
                        print(f"🟢 Streaming appears to be active!")
                        return process
                
                time.sleep(0.1)
            
            # If we get here, check if process is still alive
            if process.poll() is None:
                logger.info(f"✅ FFmpeg started successfully on attempt {attempt + 1}")
                return process
            else:
                exit_code = process.returncode
                logger.warning(f"⚠️ FFmpeg failed on attempt {attempt + 1} with exit code {exit_code}")
                
                if attempt < max_retries - 1:
                    logger.info(f"🔄 Retrying in 3 seconds...")
                    time.sleep(3)
                    continue
                else:
                    raise Exception(f"FFmpeg failed with exit code {exit_code}")
                    
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            else:
                logger.warning(f"⚠️ Attempt {attempt + 1} failed: {e}")
                time.sleep(3)
    
    raise Exception(f"FFmpeg failed to start after {max_retries} attempts")

def generate_client_crop_info(
    screen_count: int,
    orientation: str,
    output_width: int,
    output_height: int,
    grid_rows: int = 2,
    grid_cols: int = 2
) -> Dict[int, Dict[str, int]]:
    """
    Generate crop information for clients to extract their specific screen section.
    Returns dict with crop parameters for each screen.
    """
    crop_info = {}
    
    if orientation.lower() == "horizontal":
        section_width = output_width
        section_height = output_height
        for i in range(screen_count):
            crop_info[i] = {
                "width": section_width,
                "height": section_height,
                "x": i * section_width,
                "y": 0
            }
    
    elif orientation.lower() == "vertical":
        section_width = output_width
        section_height = output_height
        for i in range(screen_count):
            crop_info[i] = {
                "width": section_width,
                "height": section_height,
                "x": 0,
                "y": i * section_height
            }
    
    elif orientation.lower() == "grid":
        if grid_rows * grid_cols != screen_count:
            grid_cols = int(screen_count ** 0.5)
            grid_rows = (screen_count + grid_cols - 1) // grid_cols
        
        section_width = output_width
        section_height = output_height
        for i in range(screen_count):
            row = i // grid_cols
            col = i % grid_cols
            crop_info[i] = {
                "width": section_width,
                "height": section_height,
                "x": col * section_width,
                "y": row * section_height
            }
    
    return crop_info

def find_ffmpeg_executable() -> str:
    """Find FFmpeg executable path"""
    # Try custom build first
    custom_paths = [
        "./cmake-build-debug/external/Install/bin/ffmpeg",
        "./build/external/Install/bin/ffmpeg",
        "ffmpeg"
    ]
    
    for path in custom_paths:
        if os.path.exists(path) or path == "ffmpeg":
            return path
    
    raise FileNotFoundError("FFmpeg executable not found")

# Example usage and client integration
def get_client_stream_url(
    srt_ip: str,
    srt_port: int,
    group_name: str,
    stream_id: str,
    screen_index: Optional[int] = None
) -> str:
    """
    Generate SRT URL for client to receive stream.
    If screen_index is provided, includes crop parameters.
    """
    srt_params = "latency=200000&connect_timeout=5000&rcvbuf=67108864&sndbuf=67108864"
    stream_path = f"live/{group_name}/{stream_id}"
    
    url = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={stream_path},m=request&{srt_params}"
    
    return url

@stream_bp.route("/start_split_screen_srt", methods=["POST"])
def start_split_screen_srt():
    """
    Take one video file and split it across multiple screens by resizing and cropping.
    Creates a single wide/tall canvas where each screen shows a portion of the original video.
    """
    try:
        data = request.get_json() or {}
        
        # Required parameters
        group_id = data.get("group_id")
        video_file = data.get("video_file")  # Single video file
        
        logger.info(f"🎬 START SPLIT-SCREEN SRT: group_id={group_id}, video_file={video_file}")
        
        if not group_id:
            return jsonify({"error": "group_id is required"}), 400
        
        if not video_file:
            return jsonify({"error": "video_file is required"}), 400
        
        # Use Docker discovery
        group = discover_group_from_docker(group_id)
        
        if not group:
            return jsonify({
                "error": f"Group '{group_id}' not found in Docker containers",
                "suggestion": "Create the group first using /create_group endpoint"
            }), 404
        
        group_name = group.get("name", group_id)
        logger.info(f"✅ Found group in Docker: {group_name}")
        
        # Check if Docker container is running
        if not group.get("docker_running", False):
            return jsonify({
                "error": f"Docker container for group '{group_name}' is not running",
                "suggestion": "Start the Docker container first",
                "docker_status": group.get("docker_status", "unknown")
            }), 400
        
        # Check if FFmpeg is already running for this group
        existing_ffmpeg = find_running_ffmpeg_for_group(group_id, group_name)
        if existing_ffmpeg:
            logger.info(f"⚠️ FFmpeg already running for group {group_name}")
            return jsonify({
                "message": f"Split-screen SRT streaming already active for group '{group_name}'",
                "group_id": group_id,
                "group_name": group_name,
                "running_processes": existing_ffmpeg,
                "status": "already_active"
            }), 200
        
        # Configuration with proper defaults
        screen_count = data.get("screen_count", group.get("screen_count", 2))
        orientation = data.get("orientation", group.get("orientation", "horizontal"))
        
        # Individual section dimensions (what each client will see)
        output_width = data.get("output_width", 1920)
        output_height = data.get("output_height", 1080)
        
        # Grid layout parameters
        grid_rows = data.get("grid_rows", 2)
        grid_cols = data.get("grid_cols", 2)
        
        # SRT configuration
        ports = group.get("ports", {})
        srt_port = data.get("srt_port", ports.get("srt_port", 10080))
        srt_ip = data.get("srt_ip", "127.0.0.1")
        
        # SEI configuration
        sei_raw = data.get("sei", "681d5c8f-80cd-4847-930a-99b9484b4a32+000000")
        sei = sei_raw if '+' in sei_raw else f"{sei_raw}+000000"
        
        # Calculate canvas dimensions
        if orientation.lower() == "horizontal":
            canvas_width = output_width * screen_count
            canvas_height = output_height
        elif orientation.lower() == "vertical":
            canvas_width = output_width
            canvas_height = output_height * screen_count
        elif orientation.lower() == "grid":
            if grid_rows * grid_cols != screen_count:
                grid_cols = int(screen_count ** 0.5)
                grid_rows = (screen_count + grid_cols - 1) // grid_cols
            canvas_width = output_width * grid_cols
            canvas_height = output_height * grid_rows
        else:
            return jsonify({"error": f"Invalid orientation: {orientation}"}), 400
        
        logger.info(f"📊 Split-Screen Config: {screen_count} screens, {orientation} layout")
        logger.info(f"📐 Canvas: {canvas_width}x{canvas_height}, Sections: {output_width}x{output_height}")
        
        # Validate and process video file
        uploads_dir = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        
        # Construct full file path
        if video_file.startswith('uploads/'):
            file_path = video_file
        else:
            # Try uploads first, then resized_video
            upload_path = os.path.join(uploads_dir, video_file)
            resized_path = os.path.join(current_app.config.get('DOWNLOAD_FOLDER', 'resized_video'), video_file)
            
            if os.path.exists(upload_path):
                file_path = upload_path
            elif os.path.exists(resized_path):
                file_path = resized_path
            else:
                return jsonify({
                    "error": f"Video file not found: {video_file}",
                    "checked_paths": [upload_path, resized_path]
                }), 404
        
        if not os.path.exists(file_path):
            return jsonify({
                "error": f"Video file not found: {file_path}"
            }), 404
        
        logger.info(f"📹 Using video file: {os.path.basename(file_path)}")
        
        # Wait for SRT server to be ready
        logger.info(f"⏳ Waiting for SRT server to be ready...")
        if not wait_for_srt_server(srt_ip, srt_port, timeout=30):
            return jsonify({
                "error": f"SRT server at {srt_ip}:{srt_port} not ready",
                "suggestion": "Check Docker container logs"
            }), 500
        
        # Test SRT connection
        logger.info(f"🧪 Testing SRT connection...")
        test_result = test_ffmpeg_srt_connection(srt_ip, srt_port, group_name, sei)
        
        if not test_result["success"]:
            return jsonify({
                "error": "SRT connection test failed",
                "test_result": test_result,
                "suggestion": "Check the detailed error output in the server terminal/logs"
            }), 500
        
        logger.info(f"✅ SRT test passed! Building split-screen FFmpeg command...")
        
        # Generate single stream ID
        stream_id = f"split_{group_id}"
        
        # Build split-screen FFmpeg command
        ffmpeg_cmd = build_split_screen_ffmpeg_command(
            video_file=file_path,
            screen_count=screen_count,
            orientation=orientation,
            output_width=output_width,
            output_height=output_height,
            canvas_width=canvas_width,
            canvas_height=canvas_height,
            srt_ip=srt_ip,
            srt_port=srt_port,
            sei=sei,
            group_name=group_name,
            stream_id=stream_id,
            grid_rows=grid_rows,
            grid_cols=grid_cols
        )
        
        logger.info(f"🎬 Split-screen FFmpeg command: {' '.join(ffmpeg_cmd[:10])}... (truncated)")
        
        # Start FFmpeg process
        try:
            logger.info(f"🎬 Starting FFmpeg with real-time output...")
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=0
            )
            # Show output for first 10 seconds to verify it's working

            def monitor_output():
                for i in range(100):  # Show 100 lines of output
                    line = process.stdout.readline()
                    if line:
                        logger.info(f"FFmpeg: {line.strip()}")
                        print(f"FFmpeg: {line.strip()}")
                    time.sleep(0.1)

            monitor_thread = threading.Thread(target=monitor_output, daemon=True)
            monitor_thread.start()

            time.sleep(3)

            
            logger.info(f"✅ Split-screen FFmpeg started with PID: {process.pid}")
            
            # Generate crop information for clients
            crop_info = generate_client_crop_info(
                screen_count=screen_count,
                orientation=orientation,
                output_width=output_width,
                output_height=output_height,
                grid_rows=grid_rows,
                grid_cols=grid_cols
            )
            
            # Single stream URL with optimized latency
            stream_path = f"live/{group_name}/{stream_id}"
            srt_params = "latency=200000&connect_timeout=5000&rcvbuf=67108864&sndbuf=67108864"
            client_stream_url = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={stream_path},m=request&{srt_params}"
            
            # Generate client connection examples
            client_examples = {}
            for i in range(screen_count):
                crop = crop_info[i]
                client_examples[f"screen_{i}"] = {
                    "description": f"Screen {i} ({orientation} layout) - shows part of original video",
                    "stream_url": client_stream_url,
                    "crop_filter": f"crop={crop['width']}:{crop['height']}:{crop['x']}:{crop['y']}",
                    "player_command": f"./player \"{client_stream_url}\" --crop \"{crop['width']}:{crop['height']}:{crop['x']}:{crop['y']}\""
                }
            
            return jsonify({
                "message": f"Split-screen SRT streaming started for group '{group_name}'",
                "group_id": group_id,
                "group_name": group_name,
                "process_id": process.pid,
                "configuration": {
                    "screen_count": screen_count,
                    "orientation": orientation,
                    "canvas_resolution": f"{canvas_width}x{canvas_height}",
                    "section_resolution": f"{output_width}x{output_height}",
                    "grid_layout": f"{grid_rows}x{grid_cols}" if orientation == "grid" else None,
                    "source_video": os.path.basename(file_path),
                    "mode": "split_screen"
                },
                "stream_info": {
                    "stream_url": client_stream_url,
                    "stream_path": stream_path,
                    "stream_id": stream_id,
                    "crop_information": crop_info
                },
                "client_instructions": {
                    "connection": f"All clients connect to: {client_stream_url}",
                    "cropping": "Each client crops their section to see part of the original video",
                    "latency": "Stream optimized for 200ms latency with embedded timestamps"
                },
                "client_examples": client_examples,
                "status": "active",
                "test_result": test_result
            }), 200
            
        except Exception as e:
            logger.error(f"Error starting split-screen FFmpeg: {e}")
            return jsonify({
                "error": f"Failed to start split-screen FFmpeg: {str(e)}",
                "suggestion": "Check video file and SRT server status"
            }), 500
        
    except Exception as e:
        logger.error(f"❌ Error in start_split_screen_srt: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

def build_split_screen_ffmpeg_command(
    video_file: str,
    screen_count: int,
    orientation: str,
    output_width: int,
    output_height: int,
    canvas_width: int,
    canvas_height: int,
    srt_ip: str,
    srt_port: int,
    sei: str,
    group_name: str,
    stream_id: str,
    grid_rows: int = 2,
    grid_cols: int = 2,
    framerate: int = 30,
    bitrate: str = "6000k",
    debug_mode: bool = True
) -> List[str]:
    """
    Working split-screen approach using simple video filter
    """
    
    ffmpeg_path = find_ffmpeg_executable()
    
    if debug_mode:
        print(f"\n🎬 BUILDING WORKING SPLIT-SCREEN FFMPEG COMMAND")
        print(f"📊 Config: {screen_count} screens, {orientation} layout")
        print(f"📐 Canvas: {canvas_width}x{canvas_height}, Sections: {output_width}x{output_height}")
        print(f"📹 Source: {os.path.basename(video_file)} (using simple video filter)")
        print("=" * 60)
    
    # Build input with real-time flag
    input_args = ["-stream_loop", "-1", "-re", "-i", video_file]
    
    if debug_mode:
        print(f"📹 Input: {os.path.basename(video_file)} (looped with real-time)")
    
    # Use simple video filter instead of complex filter
    video_filter = f"fps={framerate},scale={canvas_width}:{canvas_height}:force_original_aspect_ratio=increase,crop={canvas_width}:{canvas_height}"
    
    if debug_mode:
        print(f"🎛️ Video filter: {video_filter}")
    
    # Build FFmpeg command
    ffmpeg_cmd = [
        ffmpeg_path,
        "-y"
    ]
    
    # Add debug verbosity if in debug mode
    if debug_mode:
        ffmpeg_cmd.extend(["-v", "info"])
    else:
        ffmpeg_cmd.extend(["-v", "error"])
    
    ffmpeg_cmd.extend(input_args + [
        "-vf", video_filter,  # Use -vf instead of -filter_complex
        "-an",  # No audio for now
        "-c:v", "libx264",
        "-preset", "veryfast", 
        "-tune", "zerolatency",
        "-maxrate", bitrate,
        "-bufsize", str(int(bitrate.rstrip('k')) * 2) + "k",
        "-bsf:v", f"h264_metadata=sei_user_data={sei}",
        # Ultra low-latency settings
        "-pes_payload_size", "0",
        "-bf", "0",
        "-g", "1",
        "-r", str(framerate),
        "-f", "mpegts"
    ])
    
    # SRT output
    srt_params = "latency=200000&connect_timeout=5000&rcvbuf=67108864&sndbuf=67108864"
    stream_path = f"live/{group_name}/{stream_id}"
    srt_url = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={stream_path},m=publish&{srt_params}"
    ffmpeg_cmd.append(srt_url)
    
    if debug_mode:
        print(f"📡 SRT URL: {srt_url}")
        print(f"🔧 Complete command:")
        command_str = ' '.join(ffmpeg_cmd)
        print(f"   {command_str}")
        print("=" * 60)
    
    return ffmpeg_cmd

@stream_bp.route("/stop_group_stream", methods=["POST"])
def stop_group_srt():
    """
    Stop all FFmpeg processes for a group
    """
    try:
        data = request.get_json() or {}
        group_id = data.get("group_id")
        
        logger.info(f"🛑 STOP GROUP SRT: group_id={group_id}")
        
        if not group_id:
            return jsonify({"error": "group_id is required"}), 400
        
        # Discover group from Docker
        group = discover_group_from_docker(group_id)
        
        if not group:
            return jsonify({
                "error": f"Group '{group_id}' not found in Docker containers"
            }), 404
        
        group_name = group.get("name", group_id)
        
        # Find running FFmpeg processes for this group
        running_processes = find_running_ffmpeg_for_group(group_id, group_name)
        
        if not running_processes:
            return jsonify({
                "message": f"No active streams found for group '{group_name}'",
                "group_id": group_id,
                "group_name": group_name,
                "status": "already_stopped"
            }), 200
        
        # Stop all FFmpeg processes for this group
        stopped_processes = []
        failed_processes = []
        
        for proc_info in running_processes:
            try:
                pid = proc_info["pid"]
                proc = psutil.Process(pid)
                
                logger.info(f"🔪 Terminating FFmpeg process {pid} for group {group_name}")
                proc.terminate()
                
                # Wait for graceful termination
                try:
                    proc.wait(timeout=5)
                    stopped_processes.append(proc_info)
                    logger.info(f"✅ Process {pid} terminated gracefully")
                except psutil.TimeoutExpired:
                    # Force kill if not terminated gracefully
                    logger.warning(f"⚠️ Force killing process {pid}")
                    proc.kill()
                    stopped_processes.append(proc_info)
                    
            except psutil.NoSuchProcess:
                # Process already stopped
                stopped_processes.append(proc_info)
                logger.info(f"✅ Process {proc_info['pid']} was already stopped")
            except Exception as e:
                logger.error(f"❌ Failed to stop process {proc_info['pid']}: {e}")
                failed_processes.append({**proc_info, "error": str(e)})
        
        return jsonify({
            "message": f"Stopped streams for group '{group_name}'",
            "group_id": group_id,
            "group_name": group_name,
            "stopped_processes": len(stopped_processes),
            "failed_processes": len(failed_processes),
            "details": {
                "stopped": stopped_processes,
                "failed": failed_processes
            },
            "status": "stopped"
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error stopping group SRT: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    
@stream_bp.route("/streaming_status/<group_id>", methods=["GET"])
def get_streaming_status(group_id: str):
    """
    Get streaming status for a specific group
    """
    try:
        logger.info(f"📊 GET STREAMING STATUS: group_id={group_id}")
        
        # Discover group from Docker
        group = discover_group_from_docker(group_id)
        
        if not group:
            return jsonify({
                "error": f"Group '{group_id}' not found in Docker containers"
            }), 404
        
        group_name = group.get("name", group_id)
        streaming_mode = group.get("streaming_mode", "multi_video") 
        
        # Find running FFmpeg processes
        running_processes = find_running_ffmpeg_for_group(group_id, group_name)
        
        is_streaming = len(running_processes) > 0
        
        # Get persistent streams for this group
        screen_count = group.get("screen_count", 2)
        persistent_streams = get_persistent_streams_for_group(group_id, group_name, screen_count)
        
        # Generate client URLs if streaming
        client_stream_urls = {}
        available_streams = []
        
        if is_streaming:
            ports = group.get("ports", {})
            srt_port = ports.get("srt_port", 10080)
            srt_ip = "127.0.0.1"  # Could be configurable
            
            # Combined stream
            combined_stream_path = f"live/{group_name}/{persistent_streams['test']}"
            client_stream_urls["combined"] = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={combined_stream_path},m=request,latency=5000000"
            available_streams.append(combined_stream_path)
            
            # Individual screen streams
            for i in range(screen_count):
                stream_name = f"screen{i}"
                screen_stream_id = persistent_streams.get(f"test{i}", f"screen{i}")
                screen_stream_path = f"live/{group_name}/{screen_stream_id}"
                client_stream_urls[stream_name] = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={screen_stream_path},m=request,latency=5000000"
                available_streams.append(screen_stream_path)
        
        return jsonify({
            "group_id": group_id,
            "group_name": group_name,
            "streaming_mode": streaming_mode,
            "screen_count": screen_count,     
            "orientation": group.get("orientation", "horizontal"), 
            "is_streaming": is_streaming,
            "process_count": len(running_processes),
            "process_id": running_processes[0]["pid"] if running_processes else None,
            "available_streams": available_streams,
            "client_stream_urls": client_stream_urls,
            "persistent_streams": persistent_streams,
            "running_processes": running_processes,
            "status": "active" if is_streaming else "inactive",
            "docker_running": group.get("docker_running", False),
            "docker_status": group.get("docker_status", "unknown")
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error getting streaming status: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@stream_bp.route("/all_streaming_statuses", methods=["GET"])
def get_all_streaming_statuses():
    """
    Get streaming status for all groups
    """
    try:
        logger.info("📊 GET ALL STREAMING STATUSES")
        
        # Find all FFmpeg processes
        all_ffmpeg_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and 'ffmpeg' in proc.info['name'].lower():
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    all_ffmpeg_processes.append({
                        "pid": proc.info['pid'],
                        "cmdline": cmdline,
                        "create_time": proc.create_time() if hasattr(proc, 'create_time') else None
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Find all SRS containers to discover groups
        streaming_statuses = {}
        
        try:
            cmd = [
                "docker", "ps", "-a",
                "--filter", "ancestor=ossrs/srs:5",
                "--format", "{{.ID}}\t{{.Names}}\t{{.Status}}"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.strip():
                        parts = line.split('\t')
                        if len(parts) >= 3:
                            container_id = parts[0]
                            container_name = parts[1]
                            status = parts[2]
                            
                            # Try to extract group ID from container labels
                            inspect_cmd = ["docker", "inspect", container_id, "--format", 
                                         "{{index .Config.Labels \"com.multiscreen.group.id\"}}"]
                            inspect_result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=5)
                            
                            if inspect_result.returncode == 0:
                                group_id = inspect_result.stdout.strip()
                                if group_id and group_id != "<no value>":
                                    # Get detailed group info
                                    group = get_container_details(container_id, group_id)
                                    if group:
                                        group_name = group.get("name", group_id)
                                        
                                        # Check if this group has running FFmpeg
                                        group_processes = [
                                            proc for proc in all_ffmpeg_processes
                                            if group_name in proc["cmdline"] or group_id in proc["cmdline"]
                                        ]
                                        
                                        streaming_statuses[group_id] = {
                                            "group_name": group_name,
                                            "is_streaming": len(group_processes) > 0,
                                            "process_count": len(group_processes),
                                            "docker_running": group.get("docker_running", False),
                                            "docker_status": group.get("docker_status", "unknown"),
                                            "container_name": group.get("container_name", "unknown")
                                        }
        
        except Exception as e:
            logger.warning(f"⚠️ Error discovering groups from Docker: {e}")
        
        return jsonify({
            "streaming_statuses": streaming_statuses,
            "total_ffmpeg_processes": len(all_ffmpeg_processes),
            "total_groups": len(streaming_statuses)
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error getting all streaming statuses: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    
def discover_group_from_docker(group_id: str) -> Optional[Dict[str, Any]]:
    """
    Discover group information purely from Docker container
    """
    try:
        logger.info(f"🔍 Looking for Docker container with group ID: {group_id}")
        
        # Method 1: Look for containers with the correct label
        cmd = [
            "docker", "ps", "-a",
            "--filter", f"label=com.multiscreen.group.id={group_id}",
            "--format", "{{.ID}}\t{{.Names}}\t{{.Status}}"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line.strip():
                    parts = line.split('\t')
                    if len(parts) >= 3:
                        container_id = parts[0]
                        container_name = parts[1]
                        status = parts[2]
                        logger.info(f"✅ Found container by label: {container_name} ({container_id})")
                        return get_container_details(container_id, group_id)
        
        # Method 2: Look for containers with naming pattern srs-group-{group_id_short}
        group_id_short = group_id[:8]  # First 8 chars
        container_name_pattern = f"srs-group-{group_id_short}"
        
        cmd = [
            "docker", "ps", "-a",
            "--filter", f"name={container_name_pattern}",
            "--format", "{{.ID}}\t{{.Names}}\t{{.Status}}"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line.strip():
                    parts = line.split('\t')
                    if len(parts) >= 3:
                        container_id = parts[0]
                        container_name = parts[1]
                        status = parts[2]
                        logger.info(f"✅ Found container by name pattern: {container_name} ({container_id})")
                        return get_container_details(container_id, group_id)
        
        # Method 3: Look for any SRS containers and check their labels
        cmd = [
            "docker", "ps", "-a",
            "--filter", "ancestor=ossrs/srs:5",
            "--format", "{{.ID}}\t{{.Names}}\t{{.Status}}"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line.strip():
                    parts = line.split('\t')
                    if len(parts) >= 3:
                        container_id = parts[0]
                        container_name = parts[1]
                        status = parts[2]
                        
                        # Check if this container has our group ID in its labels
                        inspect_cmd = ["docker", "inspect", container_id, "--format", 
                                     "{{index .Config.Labels \"com.multiscreen.group.id\"}}"]
                        inspect_result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=5)
                        
                        if inspect_result.returncode == 0:
                            found_group_id = inspect_result.stdout.strip()
                            if found_group_id == group_id:
                                logger.info(f"✅ Found container by SRS search: {container_name} ({container_id})")
                                return get_container_details(container_id, group_id)
        
        logger.warning(f"❌ No Docker container found for group {group_id}")
        return None
        
    except Exception as e:
        logger.error(f"Error discovering group from Docker: {e}")
        return None

def get_container_details(container_id: str, group_id: str) -> Dict[str, Any]:
    """
    Get detailed container information for a group
    """
    try:
        # Get detailed container info
        inspect_cmd = ["docker", "inspect", container_id]
        result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            logger.error(f"Failed to inspect container {container_id}: {result.stderr}")
            return None
        
        container_data = json.loads(result.stdout)[0]
        labels = container_data.get("Config", {}).get("Labels", {})
        state = container_data.get("State", {})
        
        # Extract group information from labels
        group_name = labels.get('com.multiscreen.group.name', f'group_{group_id[:8]}')
        description = labels.get('com.multiscreen.group.description', '')
        screen_count = int(labels.get('com.multiscreen.group.screen_count', 2))
        orientation = labels.get('com.multiscreen.group.orientation', 'horizontal')
        streaming_mode = labels.get('com.multiscreen.group.streaming_mode', 'multi_video')  # ✅ ADD THIS LINE
        created_timestamp = float(labels.get('com.multiscreen.group.created_at', time.time()))
        
        logger.info(f"📺 Container {container_id} streaming mode: {streaming_mode}")  # ✅ ADD THIS LINE
        
        # Extract port information
        ports = {
            'rtmp_port': int(labels.get('com.multiscreen.ports.rtmp', 1935)),
            'http_port': int(labels.get('com.multiscreen.ports.http', 1985)),
            'api_port': int(labels.get('com.multiscreen.ports.api', 8080)),
            'srt_port': int(labels.get('com.multiscreen.ports.srt', 10080))
        }
        
        # Determine container status
        is_running = state.get("Running", False)
        docker_status = "running" if is_running else "stopped"
        
        # Build group object
        group = {
            "id": group_id,
            "name": group_name,
            "description": description,
            "screen_count": screen_count,
            "orientation": orientation,
            "streaming_mode": streaming_mode,  # ✅ ADD THIS LINE
            "created_at": created_timestamp,
            "container_id": container_id,
            "container_name": container_data.get("Name", "").lstrip("/"),
            "docker_status": docker_status,
            "docker_running": is_running,
            "status": docker_status,
            "ports": ports,
            "created_at_formatted": time.strftime(
                "%Y-%m-%d %H:%M:%S",
                time.localtime(created_timestamp)
            )
        }
        
        logger.debug(f"✅ Container details for {group_name}: streaming_mode={streaming_mode}")  # ✅ ADD THIS LINE
        
        return group
        
    except Exception as e:
        logger.error(f"Error getting container details: {e}")
        return None

def find_running_ffmpeg_for_group(group_id: str, group_name: str) -> List[Dict[str, Any]]:
    """
    Find any running FFmpeg processes for a group
    """
    try:
        ffmpeg_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and 'ffmpeg' in proc.info['name'].lower():
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    
                    # Check if this FFmpeg process is for our group
                    if group_name in cmdline or group_id in cmdline:
                        ffmpeg_processes.append({
                            "pid": proc.info['pid'],
                            "cmdline": cmdline,
                            "create_time": proc.create_time() if hasattr(proc, 'create_time') else None
                        })
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return ffmpeg_processes
        
    except Exception as e:
        logger.error(f"Error finding FFmpeg processes: {e}")
        return []

def wait_for_srt_server(srt_ip: str, srt_port: int, timeout: int = 30) -> bool:
    """Wait for SRT server to be ready with better diagnostics"""
    logger.info(f"🔍 Waiting for SRT server at {srt_ip}:{srt_port}...")
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            # Method 1: Check with netstat
            netstat_check = subprocess.run(
                ["netstat", "-ln"], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            
            if netstat_check.returncode == 0:
                listening_ports = netstat_check.stdout
                if f":{srt_port}" in listening_ports:
                    logger.info(f"✅ SRT port {srt_port} is listening!")
                    return True
            
            # Method 2: Check with ss command (more reliable)
            try:
                ss_check = subprocess.run(
                    ["ss", "-lun"], 
                    capture_output=True, 
                    text=True, 
                    timeout=5
                )
                
                if ss_check.returncode == 0:
                    if f":{srt_port}" in ss_check.stdout:
                        logger.info(f"✅ SRT port {srt_port} is listening (via ss)!")
                        return True
            except FileNotFoundError:
                # ss command not available, continue with netstat
                pass
            
            # Method 3: Docker container check
            try:
                docker_check = subprocess.run(
                    ["docker", "ps", "--format", "table {{.Names}}\t{{.Ports}}", "--filter", f"publish={srt_port}"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if docker_check.returncode == 0 and docker_check.stdout.strip():
                    lines = docker_check.stdout.strip().split('\n')
                    if len(lines) > 1:  # Has header + at least one container
                        logger.info(f"✅ Docker container with port {srt_port} found!")
                        logger.info(f"📋 Container info:\n{docker_check.stdout}")
                        # Give it a moment for the service to be ready
                        time.sleep(2)
                        return True
                    else:
                        logger.warning(f"⚠️ No Docker container found exposing port {srt_port}")
                
            except Exception as e:
                logger.warning(f"⚠️ Docker check failed: {e}")
            
            logger.info(f"⏳ Port {srt_port} not yet listening... (checking again in 2s)")
            
        except subprocess.TimeoutExpired:
            logger.warning(f"⚠️ Network check command timed out")
        except Exception as e:
            logger.warning(f"⚠️ Error checking SRT server: {e}")
        
        time.sleep(2)
    
    logger.error(f"❌ Timeout waiting for SRT server after {timeout}s")
    
    # Final diagnostic information
    logger.error("🔍 Final diagnostics:")
    
    # Check if any SRT-related containers are running
    try:
        docker_ps = subprocess.run(
            ["docker", "ps", "--format", "table {{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if docker_ps.returncode == 0:
            logger.error(f"📋 Running containers:\n{docker_ps.stdout}")
        
    except Exception as e:
        logger.error(f"❌ Could not check Docker containers: {e}")
    
    # Check what's actually listening on similar ports
    try:
        netstat_all = subprocess.run(
            ["netstat", "-ln", "|", "grep", "1008"],
            shell=True,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if netstat_all.stdout.strip():
            logger.error(f"📋 Ports near {srt_port}:\n{netstat_all.stdout}")
    except Exception as e:
        logger.error(f"❌ Could not check similar ports: {e}")
    
    return False


def get_persistent_streams_for_group(group_id: str, group_name: str, split_count: int) -> Dict[str, str]:
    """Get persistent stream IDs for a group"""
    persistent_key = f"group_{group_id}"
    
    streams = {}
    
    # Always create the full stream
    streams["test"] = id_manager.get_stream_id(persistent_key, "test")
    
    # Create split streams only if needed
    for i in range(split_count):
        streams[f"test{i}"] = id_manager.get_stream_id(persistent_key, f"test{i}")
    
    return streams