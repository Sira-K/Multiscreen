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
import socket
from typing import Dict, List, Any, Tuple, Optional

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

def build_complete_multi_video_ffmpeg_command(
    video_files: List[str],
    screen_count: int,
    orientation: str,
    output_width: int,
    output_height: int,
    srt_ip: str,
    srt_port: int,
    sei: str,
    group_name: str,
    persistent_streams: Dict[str, str],
    grid_rows: int = 2,
    grid_cols: int = 2
) -> List[str]:
    """
    Build complete FFmpeg command for multi-video streaming
    """
    
    # Validate inputs
    if len(video_files) != screen_count:
        raise ValueError(f"Number of video files ({len(video_files)}) must match screen count ({screen_count})")
    
    for video_file in video_files:
        if not os.path.exists(video_file):
            raise FileNotFoundError(f"Video file not found: {video_file}")
    
    # Find FFmpeg
    ffmpeg_path = find_ffmpeg_executable()
    
    # Build input args with looping
    input_args = []
    for i, video_file in enumerate(video_files):
        input_args.extend(["-stream_loop", "-1", "-i", video_file])
    
    # Start building the complete filter chain
    filter_parts = []
    
    # Step 1: Scale and combine videos based on orientation
    if orientation.lower() == "horizontal":
        section_width = output_width // screen_count
        section_height = output_height
        
        # Scale each input
        for i in range(screen_count):
            filter_parts.append(f"[{i}:v]scale={section_width}:{section_height}[v{i}]")
        
        # Concatenate horizontally
        hstack_inputs = "".join([f"[v{i}]" for i in range(screen_count)])
        filter_parts.append(f"{hstack_inputs}hstack=inputs={screen_count}[combined]")
        
    elif orientation.lower() == "vertical":
        section_width = output_width
        section_height = output_height // screen_count
        
        # Scale each input
        for i in range(screen_count):
            filter_parts.append(f"[{i}:v]scale={section_width}:{section_height}[v{i}]")
        
        # Concatenate vertically
        vstack_inputs = "".join([f"[v{i}]" for i in range(screen_count)])
        filter_parts.append(f"{vstack_inputs}vstack=inputs={screen_count}[combined]")
        
    elif orientation.lower() == "grid":
        if grid_rows * grid_cols != screen_count:
            grid_cols = int(screen_count ** 0.5)
            grid_rows = (screen_count + grid_cols - 1) // grid_cols
        
        section_width = output_width // grid_cols
        section_height = output_height // grid_rows
        
        # Scale each input
        for i in range(screen_count):
            filter_parts.append(f"[{i}:v]scale={section_width}:{section_height}[v{i}]")
        
        # Create grid rows
        for row in range(grid_rows):
            start_idx = row * grid_cols
            end_idx = start_idx + grid_cols
            row_inputs = "".join([f"[v{i}]" for i in range(start_idx, min(end_idx, screen_count))])
            cols_in_row = min(grid_cols, screen_count - start_idx)
            filter_parts.append(f"{row_inputs}hstack=inputs={cols_in_row}[row{row}]")
        
        # Stack rows vertically
        if grid_rows > 1:
            row_inputs = "".join([f"[row{i}]" for i in range(grid_rows)])
            filter_parts.append(f"{row_inputs}vstack=inputs={grid_rows}[combined]")
        else:
            filter_parts.append("[row0]copy[combined]")
    
    # Step 2: Split combined stream for individual outputs
    split_outputs = [f"[full_out]"] + [f"[split{i}]" for i in range(screen_count)]
    filter_parts.append(f"[combined]split={screen_count+1}{''.join(split_outputs)}")
    
    # Step 3: Crop individual screens from split outputs
    if orientation.lower() == "horizontal":
        section_width = output_width // screen_count
        for i in range(screen_count):
            start_x = i * section_width
            filter_parts.append(f"[split{i}]crop={section_width}:{output_height}:{start_x}:0[screen{i}]")
            
    elif orientation.lower() == "vertical":
        section_height = output_height // screen_count
        for i in range(screen_count):
            start_y = i * section_height
            filter_parts.append(f"[split{i}]crop={output_width}:{section_height}:0:{start_y}[screen{i}]")
            
    elif orientation.lower() == "grid":
        section_width = output_width // grid_cols
        section_height = output_height // grid_rows
        for i in range(screen_count):
            row = i // grid_cols
            col = i % grid_cols
            start_x = col * section_width
            start_y = row * section_height
            filter_parts.append(f"[split{i}]crop={section_width}:{section_height}:{start_x}:{start_y}[screen{i}]")
    
    # Combine all filter parts
    complete_filter = ";".join(filter_parts)
    
    # Build the complete FFmpeg command
    ffmpeg_cmd = [ffmpeg_path, "-y"] + input_args + ["-filter_complex", complete_filter]
    
    # Add outputs with SRT parameters
    srt_params = "latency=2000000&connect_timeout=5000&rcvbuf=67108864&sndbuf=67108864"
    
    # Combined stream (full video)
    combined_stream_id = persistent_streams["test"]
    combined_stream_path = f"live/{group_name}/{combined_stream_id}"
    combined_srt_url = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={combined_stream_path},m=publish&{srt_params}"
    
    ffmpeg_cmd.extend([
        "-map", "[full_out]",
        "-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency",
        "-maxrate", "4000k", "-bufsize", "8000k",
        "-bsf:v", f"h264_metadata=sei_user_data={sei}",
        "-pes_payload_size", "0", "-bf", "0", "-g", "30",
        "-f", "mpegts", combined_srt_url
    ])
    
    # Individual screen streams
    for i in range(screen_count):
        screen_stream_id = persistent_streams.get(f"test{i}", f"screen{i}")
        screen_stream_path = f"live/{group_name}/{screen_stream_id}"
        screen_srt_url = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={screen_stream_path},m=publish&{srt_params}"
        
        ffmpeg_cmd.extend([
            "-map", f"[screen{i}]",
            "-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency",
            "-bsf:v", f"h264_metadata=sei_user_data={sei}",
            "-pes_payload_size", "0", "-bf", "0", "-g", "30",
            "-f", "mpegts", screen_srt_url
        ])
    
    logger.info(f"Built complete multi-video FFmpeg command for {screen_count} videos in {orientation} layout")
    return ffmpeg_cmd

def start_ffmpeg_with_retry(ffmpeg_cmd: List[str], max_retries: int = 3) -> subprocess.Popen:
    """Start FFmpeg with retry mechanism for SRT connection issues"""
    
    for attempt in range(max_retries):
        try:
            logger.info(f"🎬 Starting FFmpeg (attempt {attempt + 1}/{max_retries})")
            
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            # Wait a bit to see if it starts successfully
            time.sleep(2.0)
            
            if process.poll() is None:
                logger.info(f"✅ FFmpeg started successfully on attempt {attempt + 1}")
                return process
            else:
                exit_code = process.returncode
                stderr_output = process.stderr.read() if process.stderr else ""
                logger.warning(f"⚠️ FFmpeg failed on attempt {attempt + 1} with exit code {exit_code}")
                
                # Check for specific connection issues
                if any(error in stderr_output for error in [
                    "Connection refused", "I/O error", "Address already in use", 
                    "No route to host", "Network is unreachable"
                ]):
                    logger.info(f"🔄 Network/SRT connection issue detected, retrying in 3 seconds...")
                    time.sleep(3)
                    continue
                else:
                    raise Exception(f"FFmpeg failed with exit code {exit_code}: {stderr_output}")
                    
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            else:
                logger.warning(f"⚠️ Attempt {attempt + 1} failed: {e}")
                time.sleep(3)
    
    raise Exception(f"FFmpeg failed to start after {max_retries} attempts")

def find_ffmpeg_executable() -> str:
    """Find FFmpeg executable"""
    paths = [
        "./cmake-build-debug/external/Install/bin/ffmpeg",
        "/usr/bin/ffmpeg", 
        "/usr/local/bin/ffmpeg",
        "ffmpeg"
    ]
    
    for path in paths:
        if os.path.exists(path) or path == "ffmpeg":
            return path
    
    return "ffmpeg"

@stream_bp.route("/start_multi_video_srt", methods=["POST"])
def start_multi_video_srt():
    """
    Combine multiple video files and stream as one SRT stream
    """
    try:
        data = request.get_json() or {}
        
        # Required parameters
        group_id = data.get("group_id")
        video_files_config = data.get("video_files", [])
        
        logger.info(f"🎬 START MULTI-VIDEO SRT: group_id={group_id}, video_files={len(video_files_config)}")
        
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
                "message": f"SRT streaming already active for group '{group_name}'",
                "group_id": group_id,
                "group_name": group_name,
                "running_processes": existing_ffmpeg,
                "status": "already_active"
            }), 200
        
        # Configuration
        screen_count = data.get("screen_count", group.get("screen_count", len(video_files_config)))
        orientation = data.get("orientation", group.get("orientation", "horizontal"))
        output_width = data.get("output_width", 3840)
        output_height = data.get("output_height", 1080)
        
        # Grid layout parameters
        grid_rows = data.get("grid_rows", 2)
        grid_cols = data.get("grid_cols", 2)
        
        # SRT configuration
        ports = group.get("ports", {})
        srt_port = data.get("srt_port", ports.get("srt_port", 10080))
        srt_ip = data.get("srt_ip", "127.0.0.1")
        sei = data.get("sei", "681d5c8f-80cd-4847-930a-99b9484b4a32+000000")
        
        logger.info(f"📊 Multi-Video Config: {screen_count} screens, {orientation} layout, {len(video_files_config)} video files")
        
        # Process video files
        video_files = []
        uploads_dir = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        
        # Sort video files by screen number
        video_files_config.sort(key=lambda x: x.get("screen", 0))
        
        for video_config in video_files_config:
            screen_num = video_config.get("screen", 0)
            file_name = video_config.get("file")
            
            if not file_name:
                return jsonify({"error": f"Missing file for screen {screen_num}"}), 400
            
            # Construct full file path
            if file_name.startswith('uploads/'):
                file_path = file_name
            elif file_name.startswith('resized_video/'):
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
        
        logger.info(f"✅ SRT test passed! Building multi-video FFmpeg command...")
        
        # Get persistent stream IDs
        persistent_streams = get_persistent_streams_for_group(group_id, group_name, screen_count)
        
        # Build complete FFmpeg command
        ffmpeg_cmd = build_complete_multi_video_ffmpeg_command(
            video_files=video_files,
            screen_count=screen_count,
            orientation=orientation,
            output_width=output_width,
            output_height=output_height,
            srt_ip=srt_ip,
            srt_port=srt_port,
            sei=sei,
            group_name=group_name,
            persistent_streams=persistent_streams,
            grid_rows=grid_rows,
            grid_cols=grid_cols
        )
        
        logger.info(f"🎬 Multi-Video FFmpeg command: {' '.join(ffmpeg_cmd[:15])}... (truncated)")
        
        # Start FFmpeg process
        try:
            process = start_ffmpeg_with_retry(ffmpeg_cmd, max_retries=3)
            
            logger.info(f"✅ Multi-video FFmpeg started with PID: {process.pid}")
            
            # Generate stream URLs for clients
            available_streams = []
            client_stream_urls = {}
            
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
                        logger.info(f"✅ Multi-video FFmpeg for group '{group_name}' ended successfully")
                    else:
                        logger.error(f"💥 Multi-video FFmpeg for group '{group_name}' ended with exit code: {exit_code}")
                        
                except Exception as e:
                    logger.error(f"❌ Error monitoring multi-video FFmpeg: {e}")
            
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
                    "error": f"Multi-video FFmpeg failed to start (exit code {exit_code})",
                    "stderr": stderr_output,
                    "suggestion": "Check video file compatibility and SRT server status"
                }), 500
            
            return jsonify({
                "message": f"Multi-video SRT streaming started for group '{group_name}'",
                "group_id": group_id,
                "group_name": group_name,
                "process_id": process.pid,
                "configuration": {
                    "screen_count": screen_count,
                    "orientation": orientation,
                    "output_resolution": f"{output_width}x{output_height}",
                    "grid_layout": f"{grid_rows}x{grid_cols}" if orientation == "grid" else None,
                    "video_files": [os.path.basename(f) for f in video_files]
                },
                "available_streams": available_streams,
                "client_stream_urls": client_stream_urls,
                "persistent_streams": persistent_streams,
                "status": "active",
                "test_result": test_result
            }), 200
            
        except Exception as e:
            logger.error(f"Error starting multi-video FFmpeg: {e}")
            return jsonify({
                "error": f"Failed to start multi-video FFmpeg: {str(e)}",
                "suggestion": "Check video files and SRT server status"
            }), 500
        
    except Exception as e:
        logger.error(f"❌ Error in start_multi_video_srt: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@stream_bp.route("/stop_group_srt", methods=["POST"])
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
        inspect_result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=10)
        
        if inspect_result.returncode != 0:
            logger.error(f"Failed to inspect container: {inspect_result.stderr}")
            return None
        
        container_info = json.loads(inspect_result.stdout)[0]
        labels = container_info.get("Config", {}).get("Labels", {}) or {}
        container_name = container_info.get("Name", "").lstrip("/")
        
        # Extract ports from container configuration
        ports = {}
        port_bindings = container_info.get("NetworkSettings", {}).get("Ports", {}) or {}
        
        # Parse port mappings
        for container_port, host_bindings in port_bindings.items():
            if host_bindings:
                host_port = int(host_bindings[0]["HostPort"])
                if "1935" in container_port:
                    ports["rtmp_port"] = host_port
                elif "1985" in container_port:
                    ports["http_port"] = host_port
                elif "8080" in container_port:
                    ports["api_port"] = host_port
                elif "10080" in container_port:
                    ports["srt_port"] = host_port
        
        # Set default ports if not found
        if not ports.get("srt_port"):
            ports["srt_port"] = 10080
        if not ports.get("api_port"):
            ports["api_port"] = 8080
        if not ports.get("http_port"):
            ports["http_port"] = 1985
        if not ports.get("rtmp_port"):
            ports["rtmp_port"] = 1935
        
        # Extract group information from Docker labels (with fallbacks)
        group = {
            "id": group_id,
            "name": labels.get("com.multiscreen.group.name") or labels.get("multiscreen.group.name") or f"group_{group_id[:8]}",
            "container_id": container_id,
            "container_name": container_name,
            "docker_running": container_info.get("State", {}).get("Running", False),
            "docker_status": container_info.get("State", {}).get("Status", "unknown"),
            "screen_count": int(labels.get("com.multiscreen.group.screen_count") or 
                                labels.get("multiscreen.group.screen_count") or "2"),
            "orientation": (labels.get("com.multiscreen.group.orientation") or 
                           labels.get("multiscreen.group.orientation") or "horizontal"),
            "ports": ports
        }
        
        logger.info(f"✅ Discovered group from Docker: {group['name']} (container: {container_name})")
        logger.info(f"   - Docker running: {group['docker_running']}")
        logger.info(f"   - Status: {group['docker_status']}")
        logger.info(f"   - Ports: {ports}")
        
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
    """Wait for SRT server to be ready"""
    logger.info(f"🔍 Waiting for SRT server at {srt_ip}:{srt_port}...")
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            # Check if port is listening
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
                else:
                    logger.info(f"⏳ Port {srt_port} not yet listening...")
            
        except Exception as e:
            logger.warning(f"⚠️ Error checking SRT server: {e}")
        
        time.sleep(2)
    
    logger.error(f"❌ Timeout waiting for SRT server after {timeout}s")
    return False

def test_ffmpeg_srt_connection(srt_ip: str, srt_port: int, group_name: str, sei: str) -> dict:
    """Test FFmpeg SRT connection"""
    logger.info(f"🧪 Testing FFmpeg SRT connection...")
    
    # Find FFmpeg
    ffmpeg_path = find_ffmpeg_executable()
    
    # Build minimal test command
    test_cmd = [
        ffmpeg_path, "-y",
        "-f", "lavfi", "-i", "testsrc=s=640x480:r=5:d=10",
        "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency",
        "-bsf:v", f"h264_metadata=sei_user_data={sei}",
        "-f", "mpegts", f"srt://{srt_ip}:{srt_port}?streamid=#!::r=live/{group_name}/test,m=publish"
    ]
    
    logger.info(f"🧪 Test command: {' '.join(test_cmd)}")
    
    try:
        result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=15)
        
        success = result.returncode == 0
        
        if success:
            logger.info(f"✅ FFmpeg SRT test PASSED!")
        else:
            logger.error(f"❌ FFmpeg SRT test FAILED with exit code {result.returncode}")
        
        return {
            "success": success,
            "exit_code": result.returncode,
            "stderr": result.stderr,
            "command": " ".join(test_cmd)
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "exit_code": -1,
            "error": "Test timed out after 15 seconds"
        }
    except Exception as e:
        return {
            "success": False,
            "exit_code": -1,
            "error": str(e)
        }

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