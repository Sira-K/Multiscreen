from flask import Blueprint, request, jsonify, current_app
import os
import json
import subprocess
import threading
import psutil
import logging
import time
import uuid
import socket
import random
from typing import Dict, List, Any, Optional

# Create blueprint
stream_bp = Blueprint('stream_management', __name__)

# Configure logger
logger = logging.getLogger(__name__)

# ============================================================================
# FLASK ROUTE HANDLERS
# ============================================================================

@stream_bp.route("/start_multi_video_srt", methods=["POST"])
def start_multi_video_srt():
    """
    Flask route handler for multi-video streaming
    Extracts parameters from request and calls the command builder
    """
    try:
        # Get data from Flask request
        data = request.get_json() or {}
        
        # Extract required parameters
        group_id = data.get("group_id")
        if not group_id:
            return jsonify({"error": "group_id is required"}), 400
        
        # Discover group from Docker
        group = discover_group_from_docker(group_id)
        if not group:
            return jsonify({"error": f"Group '{group_id}' not found"}), 404
        
        # Extract parameters from request or use defaults
        video_files = data.get("video_files", [])
        if not video_files:
            return jsonify({"error": "video_files list is required"}), 400
        
        # Get group configuration
        group_name = group.get("name", group_id)
        screen_count = data.get("screen_count", group.get("screen_count", 2))
        orientation = data.get("orientation", group.get("orientation", "horizontal"))
        output_width = data.get("output_width", 1920)
        output_height = data.get("output_height", 1080)
        
        # Get streaming parameters
        ports = group.get("ports", {})
        srt_ip = data.get("srt_ip", "127.0.0.1")
        srt_port = data.get("srt_port", ports.get("srt_port", 10080))
        sei = data.get("sei", "00000000000000000000000000000000+000000")
        base_stream_id = data.get("base_stream_id", group_id[:8])
        
        # Grid parameters for grid layout
        grid_rows = data.get("grid_rows", 2)
        grid_cols = data.get("grid_cols", 2)
        
        # Encoding parameters
        framerate = data.get("framerate", 30)
        bitrate = data.get("bitrate", "3000k")
        
        # Generate stream IDs
        stream_ids = generate_stream_ids(base_stream_id, group_name, screen_count)
        
        # Check if already streaming
        running_processes = find_running_ffmpeg_for_group_strict(group_id, group_name, group.get("container_id"))
        if running_processes:
            return jsonify({
                "error": "Stream already active for this group",
                "process_count": len(running_processes)
            }), 409
        
        # Wait for SRT server
        if not wait_for_srt_server(srt_ip, srt_port):
            return jsonify({"error": "SRT server not ready"}), 503
        
        # Build the FFmpeg command
        ffmpeg_cmd = build_multi_video_ffmpeg_command(
            video_files=video_files,
            screen_count=screen_count,
            orientation=orientation,
            output_width=output_width,
            output_height=output_height,
            srt_ip=srt_ip,
            srt_port=srt_port,
            sei=sei,
            group_name=group_name,
            base_stream_id=base_stream_id,
            grid_rows=grid_rows,
            grid_cols=grid_cols,
            framerate=framerate,
            bitrate=bitrate,
            stream_ids=stream_ids
        )
        
        # Start the FFmpeg process
        process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Monitor the process
        startup_success, streaming_detected = monitor_ffmpeg(
            process,
            stream_type=f"Multi-Video ({group_name})",
            startup_timeout=10,
            startup_max_lines=30
        )
        
        if not startup_success:
            process.terminate()
            return jsonify({"error": "Failed to start streaming"}), 500
        
        # Debug logging
        debug_log_stream_info(
            group_id, group_name, base_stream_id, 
            srt_ip, srt_port, "MULTI-VIDEO MODE", screen_count
        )
        
        # Generate client URLs
        client_urls = {}
        client_urls["combined"] = f"srt://{srt_ip}:{srt_port}?streamid=#!::r=live/{group_name}/{base_stream_id},m=request,latency=5000000"
        
        for i in range(screen_count):
            screen_key = f"test{i}"
            stream_id = stream_ids.get(screen_key, f"screen{i}_{base_stream_id}")
            client_urls[f"screen{i}"] = f"srt://{srt_ip}:{srt_port}?streamid=#!::r=live/{group_name}/{stream_id},m=request,latency=5000000"
        
        return jsonify({
            "success": True,
            "message": "Multi-video streaming started",
            "process_id": process.pid,
            "group_id": group_id,
            "group_name": group_name,
            "stream_ids": stream_ids,
            "client_urls": client_urls,
            "streaming_detected": streaming_detected
        }), 200
        
    except Exception as e:
        logger.error(f"Error starting multi-video stream: {e}")
        return jsonify({"error": str(e)}), 500


@stream_bp.route("/start_split_screen_srt", methods=["POST"])
def start_split_screen_srt():
    """
    Flask route handler for split-screen streaming
    Extracts parameters from request and calls the command builder
    """
    try:
        # Get data from Flask request
        data = request.get_json() or {}
        
        # Extract required parameters
        group_id = data.get("group_id")
        if not group_id:
            return jsonify({"error": "group_id is required"}), 400
        
        # Discover group from Docker
        group = discover_group_from_docker(group_id)
        if not group:
            return jsonify({"error": f"Group '{group_id}' not found"}), 404
        
        # Extract video file parameter
        video_file = data.get("video_file")
        if not video_file:
            return jsonify({"error": "video_file is required"}), 400
        
        # Get group configuration
        group_name = group.get("name", group_id)
        screen_count = data.get("screen_count", group.get("screen_count", 2))
        orientation = data.get("orientation", group.get("orientation", "horizontal"))
        output_width = data.get("output_width", 1920)
        output_height = data.get("output_height", 1080)
        
        # Calculate canvas dimensions
        if orientation.lower() == "horizontal":
            canvas_width = output_width * screen_count
            canvas_height = output_height
        elif orientation.lower() == "vertical":
            canvas_width = output_width
            canvas_height = output_height * screen_count
        elif orientation.lower() == "grid":
            grid_cols = data.get("grid_cols", int(screen_count ** 0.5))
            grid_rows = data.get("grid_rows", (screen_count + grid_cols - 1) // grid_cols)
            canvas_width = output_width * grid_cols
            canvas_height = output_height * grid_rows
        else:
            canvas_width = output_width * screen_count
            canvas_height = output_height
        
        # Get streaming parameters
        ports = group.get("ports", {})
        srt_ip = data.get("srt_ip", "127.0.0.1")
        srt_port = data.get("srt_port", ports.get("srt_port", 10080))
        sei = data.get("sei", "00000000000000000000000000000000+000000")
        base_stream_id = data.get("base_stream_id", group_id[:8])
        
        # Grid parameters
        grid_rows = data.get("grid_rows", 2)
        grid_cols = data.get("grid_cols", 2)
        
        # Encoding parameters
        framerate = data.get("framerate", 30)
        bitrate = data.get("bitrate", "3000k")
        
        # Generate stream IDs
        stream_ids = generate_stream_ids(base_stream_id, group_name, screen_count)
        
        # Check if already streaming
        running_processes = find_running_ffmpeg_for_group_strict(group_id, group_name, group.get("container_id"))
        if running_processes:
            return jsonify({
                "error": "Stream already active for this group",
                "process_count": len(running_processes)
            }), 409
        
        # Wait for SRT server
        if not wait_for_srt_server(srt_ip, srt_port):
            return jsonify({"error": "SRT server not ready"}), 503
        
        # Build the FFmpeg command
        ffmpeg_cmd = build_split_screen_ffmpeg_command(
            video_file=video_file,
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
            base_stream_id=base_stream_id,
            grid_rows=grid_rows,
            grid_cols=grid_cols,
            framerate=framerate,
            bitrate=bitrate,
            stream_ids=stream_ids
        )
        
        # Start the FFmpeg process
        process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Monitor the process
        startup_success, streaming_detected = monitor_ffmpeg(
            process,
            stream_type=f"Split-Screen ({group_name})",
            startup_timeout=10,
            startup_max_lines=30
        )
        
        if not startup_success:
            process.terminate()
            return jsonify({"error": "Failed to start streaming"}), 500
        
        # Debug logging
        debug_log_stream_info(
            group_id, group_name, f"split_{base_stream_id}", 
            srt_ip, srt_port, "SPLIT-SCREEN MODE", screen_count
        )
        
        # Generate client URLs
        client_urls = {}
        client_urls["combined"] = f"srt://{srt_ip}:{srt_port}?streamid=#!::r=live/{group_name}/split_{base_stream_id},m=request,latency=5000000"
        
        for i in range(screen_count):
            screen_key = f"test{i}"
            stream_id = stream_ids.get(screen_key, f"screen{i}_{base_stream_id}")
            client_urls[f"screen{i}"] = f"srt://{srt_ip}:{srt_port}?streamid=#!::r=live/{group_name}/{stream_id},m=request,latency=5000000"
        
        return jsonify({
            "success": True,
            "message": "Split-screen streaming started",
            "process_id": process.pid,
            "group_id": group_id,
            "group_name": group_name,
            "stream_ids": stream_ids,
            "client_urls": client_urls,
            "streaming_detected": streaming_detected
        }), 200
        
    except Exception as e:
        logger.error(f"Error starting split-screen stream: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# COMMAND BUILDER FUNCTIONS (Separated from Flask routes)
# ============================================================================

def build_multi_video_ffmpeg_command(
    video_files: List[str],
    screen_count: int,
    orientation: str,
    output_width: int,
    output_height: int,
    srt_ip: str,
    srt_port: int,
    sei: str,
    group_name: str,
    base_stream_id: str,
    grid_rows: int = 2,
    grid_cols: int = 2,
    framerate: int = 30,
    bitrate: str = "3000k",
    stream_ids: Dict[str, str] = None
) -> List[str]:
    """
    ENHANCED: Multi-video mode with OpenVideoWalls SEI timestamp support
    Takes multiple video files and creates a combined canvas
    This is a pure function that builds commands - NOT a Flask route
    """
    
    ffmpeg_path = find_ffmpeg_executable()
    
    # Enhanced SEI handling for OpenVideoWalls
    if _has_openvideowall_support(ffmpeg_path):
        # Use OpenVideoWalls UUID + automatic timestamp replacement
        sei_metadata = "681d5c8f-80cd-4847-930a-99b9484b4a32+000000"
        logger.info("✅ Multi-video mode using OpenVideoWalls dynamic SEI timestamps")
    else:
        # Use provided SEI (static timestamps)
        sei_metadata = sei
        logger.warning("⚠️  Multi-video mode using static SEI timestamps")
    
    # Build input arguments
    input_args = []
    for i, video_file in enumerate(video_files):
        input_args.extend(["-stream_loop", "-1", "-re", "-i", video_file])
    
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
    
    # Build filter complex
    filter_parts = []
    filter_parts.append(f"color=c=black:s={canvas_width}x{canvas_height}:r={framerate}[canvas]")
    
    # Scale each input
    for i in range(screen_count):
        filter_parts.append(f"[{i}:v]scale={section_width}:{section_height}[scaled{i}]")
    
    # Overlay videos onto canvas
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
        
        next_stream = f"[overlay{i}]" if i < screen_count - 1 else "[combined]"
        filter_parts.append(f"{current_stream}[scaled{i}]overlay=x={x_pos}:y={y_pos}{next_stream}")
        current_stream = f"[overlay{i}]"
    
    # Split for outputs
    split_outputs = f"[combined]split={screen_count + 1}[full]"
    for i in range(screen_count):
        split_outputs += f"[copy{i}]"
    filter_parts.append(split_outputs)
    
    # Create crop filters
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
        else:
            x_pos = i * section_width
            y_pos = 0
        
        filter_parts.append(f"[copy{i}]crop={section_width}:{section_height}:{x_pos}:{y_pos}[screen{i}]")
    
    complete_filter = ";".join(filter_parts)
    
    # Build FFmpeg command structure
    ffmpeg_cmd = [ffmpeg_path, "-y", "-v", "error", "-stats"]
    ffmpeg_cmd.extend(input_args + ["-filter_complex", complete_filter])
    
    # Encoding parameters with OpenVideoWalls optimizations
    if _has_openvideowall_support(ffmpeg_path):
        # OpenVideoWalls optimized encoding
        encoding_params = [
            "-an", "-c:v", "libx264",
            "-preset", "veryfast", "-tune", "zerolatency",
            "-maxrate", bitrate, "-bufsize", str(int(bitrate.rstrip('k')) * 2) + "k",
            "-bsf:v", f"h264_metadata=sei_user_data={sei_metadata}",
            "-pes_payload_size", "0", "-bf", "0", "-g", "1",
            "-r", str(framerate), "-f", "mpegts"
        ]
        srt_params = "latency=5000000&connect_timeout=5000&rcvbuf=67108864&sndbuf=67108864"
    else:
        # Original encoding parameters
        encoding_params = [
            "-an", "-c:v", "libx264", "-maxrate", bitrate,
            "-bufsize", str(int(bitrate.rstrip('k')) * 2) + "k",
            "-bsf:v", f"h264_metadata=sei_user_data={sei_metadata}",
            "-pes_payload_size", "0", "-r", str(framerate), "-f", "mpegts"
        ]
        srt_params = "latency=1000000"
    
    # Add outputs
    combined_url = f"srt://{srt_ip}:{srt_port}?streamid=#!::r=live/{group_name}/{base_stream_id},m=publish&{srt_params}"
    ffmpeg_cmd.extend(["-map", "[full]"] + encoding_params + [combined_url])
    
    if stream_ids is None:
        stream_ids = generate_stream_ids(base_stream_id, group_name, screen_count)

    for i in range(screen_count):
        screen_key = f"test{i}"
        individual_stream_id = stream_ids.get(screen_key, f"screen{i}_{base_stream_id}")
        stream_path = f"live/{group_name}/{individual_stream_id}"
        stream_url = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={stream_path},m=publish&{srt_params}"
        ffmpeg_cmd.extend(["-map", f"[screen{i}]"] + encoding_params + [stream_url])
    
    return ffmpeg_cmd


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
    base_stream_id: str,
    grid_rows: int = 2,
    grid_cols: int = 2,
    framerate: int = 30,
    bitrate: str = "3000k",
    stream_ids: Dict[str, str] = None
) -> List[str]:
    """
    ENHANCED: Split-screen mode with OpenVideoWalls SEI timestamp support
    Takes a single video and splits it into multiple screen regions
    This is a pure function that builds commands - NOT a Flask route
    """
    
    ffmpeg_path = find_ffmpeg_executable()
    
    # Enhanced SEI handling for OpenVideoWalls
    if _has_openvideowall_support(ffmpeg_path):
        # Use OpenVideoWalls UUID + automatic timestamp replacement
        sei_metadata = "681d5c8f-80cd-4847-930a-99b9484b4a32+000000"
        logger.info("✅ Split-screen mode using OpenVideoWalls dynamic SEI timestamps")
    else:
        # Use provided SEI (static timestamps)
        sei_metadata = sei
        logger.warning("⚠️  Split-screen mode using static SEI timestamps")
    
    # Build input (single video file)
    input_args = ["-stream_loop", "-1", "-re", "-i", video_file]
    
    # Build filter complex for split-screen
    filter_parts = []
    
    # Scale input to canvas size
    filter_parts.append(f"[0:v]fps={framerate},scale={canvas_width}:{canvas_height}:force_original_aspect_ratio=increase,crop={canvas_width}:{canvas_height}[scaled]")
    
    # Split for full output and individual crops
    filter_parts.append(f"[scaled]split={screen_count + 1}[full]" + "".join(f"[copy{i}]" for i in range(screen_count)))
    
    # Calculate section dimensions
    if orientation.lower() == "horizontal":
        section_width = output_width
        section_height = output_height
    elif orientation.lower() == "vertical":
        section_width = output_width
        section_height = output_height
    elif orientation.lower() == "grid":
        if grid_rows * grid_cols != screen_count:
            grid_cols = int(screen_count ** 0.5)
            grid_rows = (screen_count + grid_cols - 1) // grid_cols
        section_width = output_width
        section_height = output_height
    
    # Create crop filters for each screen
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
        
        filter_parts.append(f"[copy{i}]crop={section_width}:{section_height}:{x_pos}:{y_pos}[screen{i}]")
    
    complete_filter = ";".join(filter_parts)
    
    # Build FFmpeg command structure
    ffmpeg_cmd = [ffmpeg_path, "-y", "-v", "error", "-stats"]
    ffmpeg_cmd.extend(input_args + ["-filter_complex", complete_filter])
    
    # Encoding parameters with OpenVideoWalls optimizations
    if _has_openvideowall_support(ffmpeg_path):
        # OpenVideoWalls optimized encoding for split-screen
        encoding_params = [
            "-an", "-c:v", "libx264",
            "-preset", "veryfast", "-tune", "zerolatency",
            "-maxrate", bitrate, "-bufsize", str(int(bitrate.rstrip('k')) * 2) + "k",
            "-bsf:v", f"h264_metadata=sei_user_data={sei_metadata}",
            "-pes_payload_size", "0", "-bf", "0", "-g", "1",
            "-r", str(framerate), "-f", "mpegts"
        ]
        srt_params = "latency=5000000&connect_timeout=5000&rcvbuf=67108864&sndbuf=67108864"
        logger.debug("Using OpenVideoWalls optimized encoding for split-screen")
    else:
        # Original encoding parameters for split-screen
        encoding_params = [
            "-an", "-c:v", "libx264", "-maxrate", bitrate,
            "-bufsize", str(int(bitrate.rstrip('k')) * 2) + "k",
            "-bsf:v", f"h264_metadata=sei_user_data={sei_metadata}",
            "-pes_payload_size", "0", "-r", str(framerate), "-f", "mpegts"
        ]
        srt_params = "latency=1000000"
        logger.debug("Using standard encoding for split-screen")
    
    # Add outputs
    # Combined/full stream
    combined_url = f"srt://{srt_ip}:{srt_port}?streamid=#!::r=live/{group_name}/split_{base_stream_id},m=publish&{srt_params}"
    ffmpeg_cmd.extend(["-map", "[full]"] + encoding_params + [combined_url])
    
    # Individual screen outputs
    if stream_ids is None:
        stream_ids = generate_stream_ids(base_stream_id, group_name, screen_count)

    for i in range(screen_count):
        screen_key = f"test{i}"
        individual_stream_id = stream_ids.get(screen_key, f"screen{i}_{base_stream_id}")
        stream_path = f"live/{group_name}/{individual_stream_id}"
        stream_url = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={stream_path},m=publish&{srt_params}"
        ffmpeg_cmd.extend(["-map", f"[screen{i}]"] + encoding_params + [stream_url])
    
    return ffmpeg_cmd


# ============================================================================
# EXISTING ROUTES (Keep as-is)
# ============================================================================

@stream_bp.route("/stop_group_stream", methods=["POST"])
def stop_group_srt():
    """Stop all FFmpeg processes for a group"""
    try:
        data = request.get_json() or {}
        group_id = data.get("group_id")
        
        if not group_id:
            return jsonify({"error": "group_id is required"}), 400
        
        group = discover_group_from_docker(group_id)
        if not group:
            return jsonify({"error": f"Group '{group_id}' not found"}), 404
        
        group_name = group.get("name", group_id)
        container_id = group.get("container_id")
        
        running_processes = find_running_ffmpeg_for_group_strict(group_id, group_name, container_id)
        
        if not running_processes:
            return jsonify({
                "message": f"No active streams found for group '{group_name}'",
                "status": "already_stopped"
            }), 200
        
        # Stop processes
        stopped_processes = []
        failed_processes = []
        
        for proc_info in running_processes:
            try:
                pid = proc_info["pid"]
                proc = psutil.Process(pid)
                proc.terminate()
                
                try:
                    proc.wait(timeout=5)
                    stopped_processes.append(proc_info)
                except psutil.TimeoutExpired:
                    proc.kill()
                    stopped_processes.append(proc_info)
                    
            except psutil.NoSuchProcess:
                stopped_processes.append(proc_info)
            except Exception as e:
                logger.error(f"Failed to stop process {proc_info['pid']}: {e}")
                failed_processes.append({**proc_info, "error": str(e)})
        
        return jsonify({
            "message": f"Stopped streams for group '{group_name}'",
            "group_id": group_id,
            "group_name": group_name,
            "stopped_processes": len(stopped_processes),
            "failed_processes": len(failed_processes),
            "status": "stopped"
        }), 200
        
    except Exception as e:
        logger.error(f"Error stopping group SRT: {e}")
        return jsonify({"error": str(e)}), 500


@stream_bp.route("/streaming_status/<group_id>", methods=["GET"])
def get_streaming_status(group_id: str):
    """Get streaming status for a specific group"""
    try:
        group = discover_group_from_docker(group_id)
        if not group:
            return jsonify({"error": f"Group '{group_id}' not found"}), 404
        
        group_name = group.get("name", group_id)
        streaming_mode = group.get("streaming_mode", "multi_video") 
        container_id = group.get("container_id")
        
        running_processes = find_running_ffmpeg_for_group_strict(group_id, group_name, container_id)
        is_streaming = len(running_processes) > 0
        
        # Generate dynamic stream IDs for status display
        screen_count = group.get("screen_count", 2)
        stream_ids = generate_stream_ids(group_id, group_name, screen_count) if is_streaming else {}
        
        # Generate client URLs if streaming
        client_stream_urls = {}
        available_streams = []
        
        if is_streaming and stream_ids:
            ports = group.get("ports", {})
            srt_port = ports.get("srt_port", 10080)
            srt_ip = "127.0.0.1"
            
            combined_stream_path = f"live/{group_name}/{stream_ids.get('test', 'unknown')}"
            client_stream_urls["combined"] = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={combined_stream_path},m=request,latency=5000000"
            available_streams.append(combined_stream_path)
            
            for i in range(screen_count):
                stream_name = f"screen{i}"
                screen_stream_id = stream_ids.get(f"test{i}", f"screen{i}")
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
            "stream_ids": stream_ids,
            "running_processes": [
                {
                    "pid": proc["pid"],
                    "match_method": proc.get("match_method", "unknown"),
                    "uptime_seconds": time.time() - proc.get('create_time', time.time()),
                    "cmdline_preview": proc["cmdline"][:100] + "..." if len(proc["cmdline"]) > 100 else proc["cmdline"]
                } for proc in running_processes
            ],
            "status": "active" if is_streaming else "inactive",
            "docker_running": group.get("docker_running", False),
            "docker_status": group.get("docker_status", "unknown")
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting streaming status: {e}")
        return jsonify({"error": str(e)}), 500


@stream_bp.route("/all_streaming_statuses", methods=["GET"])
def get_all_streaming_statuses():
    """Get streaming status for all groups"""
    try:
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
        containers_found = 0
        
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
                            containers_found += 1
                            
                            # Extract group ID from container labels
                            inspect_cmd = ["docker", "inspect", container_id, "--format", 
                                         "{{index .Config.Labels \"com.multiscreen.group.id\"}}"]
                            inspect_result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=5)
                            
                            if inspect_result.returncode == 0:
                                group_id = inspect_result.stdout.strip()
                                if group_id and group_id != "<no value>":
                                    group = get_container_details(container_id, group_id)
                                    if group:
                                        group_name = group.get("name", group_id)
                                        streaming_mode = group.get("streaming_mode", "unknown")
                                        
                                        # Find processes using strict matching
                                        group_processes = []
                                        
                                        for proc in all_ffmpeg_processes:
                                            cmdline = proc["cmdline"]
                                            is_match = False
                                            match_method = ""
                                            
                                            # Strict matching
                                            stream_path_pattern = f"live/{group_name}/"
                                            if stream_path_pattern in cmdline:
                                                is_match = True
                                                match_method = f"stream_path({stream_path_pattern})"
                                            elif group_id in cmdline:
                                                is_match = True
                                                match_method = f"full_group_id({group_id})"
                                            elif container_id[:12] in cmdline:
                                                is_match = True
                                                match_method = f"container_id({container_id[:12]})"
                                            
                                            if is_match:
                                                # Check not already claimed
                                                already_claimed = False
                                                for other_group_id, other_status in streaming_statuses.items():
                                                    if other_group_id != group_id:
                                                        if any(p["pid"] == proc["pid"] for p in other_status.get("processes", [])):
                                                            already_claimed = True
                                                            break
                                                
                                                if not already_claimed:
                                                    group_processes.append(proc)
                                        
                                        is_streaming = len(group_processes) > 0
                                        docker_running = group.get("docker_running", False)
                                        
                                        # Determine health status
                                        container_health = "HEALTHY" if docker_running and is_streaming else "UNHEALTHY" if docker_running else "OFFLINE"
                                        
                                        # Store status
                                        streaming_statuses[group_id] = {
                                            "group_name": group_name,
                                            "streaming_mode": streaming_mode,
                                            "is_streaming": is_streaming,
                                            "process_count": len(group_processes),
                                            "docker_running": docker_running,
                                            "docker_status": group.get("docker_status", "unknown"),
                                            "container_name": group.get("container_name", "unknown"),
                                            "container_id": container_id,
                                            "health_status": container_health,
                                            "processes": [
                                                {
                                                    "pid": proc["pid"],
                                                    "uptime_seconds": time.time() - proc.get('create_time', time.time()),
                                                    "started_at": time.strftime('%Y-%m-%d %H:%M:%S', 
                                                                               time.localtime(proc.get('create_time', 0))),
                                                    "cmdline_preview": proc["cmdline"][:100] + "..." if len(proc["cmdline"]) > 100 else proc["cmdline"]
                                                } for proc in group_processes
                                            ]
                                        }
        
        except Exception as e:
            logger.warning(f"Error discovering groups from Docker: {e}")
        
        # Calculate summary
        active_streams = sum(1 for status in streaming_statuses.values() if status["is_streaming"])
        total_processes = sum(status["process_count"] for status in streaming_statuses.values())
        healthy_groups = sum(1 for status in streaming_statuses.values() if status["health_status"] == "HEALTHY")
        
        # Detect orphaned processes
        assigned_pids = set()
        for status in streaming_statuses.values():
            for proc in status["processes"]:
                assigned_pids.add(proc["pid"])
        
        orphaned_processes = [proc for proc in all_ffmpeg_processes if proc["pid"] not in assigned_pids]
        
        return jsonify({
            "streaming_statuses": streaming_statuses,
            "summary": {
                "total_groups": len(streaming_statuses),
                "active_streams": active_streams,
                "healthy_groups": healthy_groups,
                "total_ffmpeg_processes": len(all_ffmpeg_processes),
                "assigned_processes": len(assigned_pids),
                "orphaned_processes": len(orphaned_processes),
                "containers_found": containers_found
            },
            "orphaned_processes": [
                {
                    "pid": proc["pid"],
                    "uptime_seconds": time.time() - proc.get('create_time', time.time()),
                    "cmdline_preview": proc["cmdline"][:100] + "..." if len(proc["cmdline"]) > 100 else proc["cmdline"]
                } for proc in orphaned_processes
            ]
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting all streaming statuses: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# HELPER FUNCTIONS (All your existing helper functions)
# ============================================================================

def monitor_ffmpeg(process, stream_type="FFmpeg", startup_timeout=5, startup_max_lines=20):
    """Monitor FFmpeg process startup and continuous operation"""
    streaming_detected = False
    startup_success = True
    startup_complete = False
    
    def monitor_startup_phase():
        nonlocal streaming_detected, startup_success, startup_complete
        start_time = time.time()
        lines_shown = 0
        
        output_stream = process.stdout if process.stderr is None else process.stderr
        if output_stream is None:
            startup_success = False
            startup_complete = True
            return
        
        while (time.time() - start_time < startup_timeout and 
               lines_shown < startup_max_lines and
               not startup_complete):
            
            if process.poll() is not None:
                logger.error(f"{stream_type} process ended early with code: {process.returncode}")
                startup_success = False
                startup_complete = True
                break
                
            line = output_stream.readline()
            if line:
                line_stripped = line.strip()
                
                # Skip verbose startup info
                if any(skip in line_stripped.lower() for skip in [
                    'ffmpeg version', 'built with gcc', 'configuration:',
                    'libavutil', 'libavcodec', 'libavformat', 'libavdevice',
                    'libavfilter', 'libswscale', 'libswresample', 'libpostproc'
                ]):
                    continue
                    
                if line_stripped:
                    logger.debug(f"{stream_type}: {line_stripped}")
                    lines_shown += 1
                    
                    # Success indicators
                    if any(indicator in line_stripped.lower() for indicator in [
                        'frame=', 'fps=', 'speed=', 'time=', 'bitrate='
                    ]):
                        streaming_detected = True
                        
                    # Error indicators
                    if any(error in line_stripped.lower() for error in [
                        'error', 'failed', 'connection refused', 'cannot'
                    ]):
                        logger.error(f"{stream_type} error: {line_stripped}")
                        startup_success = False
                        
            time.sleep(2)
        
        startup_complete = True

    def monitor_continuous_phase():
        nonlocal startup_complete
        
        while not startup_complete and process.poll() is None:
            time.sleep(0.1)
        
        if process.poll() is not None:
            return
        
        output_stream = process.stdout if process.stderr is None else process.stderr
        if output_stream is None:
            return
        
        frame_count = 0
        last_stats_time = time.time()
        stats_interval = 30
        
        while process.poll() is None:
            line = output_stream.readline()
            if line:
                line_stripped = line.strip()
                
                if line_stripped:
                    if 'frame=' in line_stripped:
                        frame_count += 1
                    
                    current_time = time.time()
                    
                    # Log errors immediately
                    if any(keyword in line_stripped.lower() for keyword in [
                        'error', 'failed', 'warning', 'connection refused', 'timeout'
                    ]):
                        logger.error(f"{stream_type}: {line_stripped}")
                    
                    # Log stats periodically
                    elif (any(keyword in line_stripped.lower() for keyword in [
                        'frame=', 'fps=', 'bitrate=', 'speed='
                    ]) and current_time - last_stats_time >= stats_interval):
                        logger.info(f"{stream_type}: {line_stripped}")
                        last_stats_time = current_time
            
            time.sleep(0.01)
        
        exit_code = process.returncode
        if exit_code != 0:
            logger.error(f"{stream_type} ended with exit code: {exit_code} (processed ~{frame_count} frames)")

    def monitor_errors():
        nonlocal startup_success
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        output_stream = process.stdout if process.stderr is None else process.stderr
        if output_stream is None:
            return
        
        while process.poll() is None:
            line = output_stream.readline()
            if line:
                log_line = line.strip()
                
                if any(critical_error in log_line.lower() for critical_error in [
                    "input/output error", "connection refused", "address already in use",
                    "connection reset", "broken pipe", "no route to host"
                ]):
                    consecutive_errors += 1
                    
                    if consecutive_errors >= max_consecutive_errors:
                        logger.error(f"Too many consecutive errors, terminating {stream_type}")
                        process.terminate()
                        startup_success = False
                        break
                else:
                    if any(success_indicator in log_line.lower() for success_indicator in [
                        "frame=", "fps=", "bitrate="
                    ]):
                        consecutive_errors = 0

    # Start monitoring threads
    startup_thread = threading.Thread(target=monitor_startup_phase, daemon=True)
    continuous_thread = threading.Thread(target=monitor_continuous_phase, daemon=True)
    error_thread = threading.Thread(target=monitor_errors, daemon=True)
    
    startup_thread.start()
    continuous_thread.start() 
    error_thread.start()
    
    startup_thread.join(startup_timeout + 5)
    
    return startup_success, streaming_detected


# Add all remaining helper functions here...
# (I'll continue with the rest of the helper functions)

def find_ffmpeg_executable() -> str:
    """Find FFmpeg executable path - ENHANCED with OpenVideoWalls detection"""
    
    # Priority order: OpenVideoWalls custom FFmpeg first, then existing paths
    custom_paths = [
        # OpenVideoWalls custom FFmpeg with SEI timestamp support
        "./cmake-build-debug/external/Install/bin/ffmpeg",
        "../cmake-build-debug/external/Install/bin/ffmpeg", 
        "../../cmake-build-debug/external/Install/bin/ffmpeg",
        "./multi-screen/cmake-build-debug/external/Install/bin/ffmpeg",
        
        # Original paths (preserved for compatibility)
        "./build/external/Install/bin/ffmpeg",
        "ffmpeg"
    ]
    
    for path in custom_paths:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path) and os.access(abs_path, os.X_OK):
            # Verify if it's the OpenVideoWalls custom FFmpeg
            if _verify_openvideowall_support(abs_path):
                logger.info(f"✅ Using OpenVideoWalls custom FFmpeg: {abs_path}")
                return abs_path
            elif path == "ffmpeg":
                # System FFmpeg fallback (warn about limited functionality)
                logger.warning("⚠️  Using system FFmpeg - SEI timestamps will be static!")
                return path
            else:
                logger.debug(f"Found FFmpeg at {abs_path} but lacks OpenVideoWalls support")
                continue
        elif path == "ffmpeg":
            # Fallback to system ffmpeg
            logger.warning("⚠️  Using system FFmpeg - dynamic timestamps unavailable")
            return path
    
    raise FileNotFoundError("FFmpeg executable not found")


def discover_group_from_docker(group_id: str) -> Optional[Dict[str, Any]]:
    """Discover group information from Docker container"""
    try:
        # Method 1: Look for containers with correct label
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
                        return get_container_details(container_id, group_id)
        
        # Method 2: Look for containers with naming pattern
        group_id_short = group_id[:8]
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
                        return get_container_details(container_id, group_id)
        
        return None
        
    except Exception as e:
        logger.error(f"Error discovering group from Docker: {e}")
        return None


def get_container_details(container_id: str, group_id: str) -> Dict[str, Any]:
    """Get detailed container information for a group"""
    try:
        inspect_cmd = ["docker", "inspect", container_id]
        result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            return None
        
        container_data = json.loads(result.stdout)[0]
        labels = container_data.get("Config", {}).get("Labels", {})
        state = container_data.get("State", {})
        
        # Extract group information
        group_name = labels.get('com.multiscreen.group.name', f'group_{group_id[:8]}')
        description = labels.get('com.multiscreen.group.description', '')
        screen_count = int(labels.get('com.multiscreen.group.screen_count', 2))
        orientation = labels.get('com.multiscreen.group.orientation', 'horizontal')
        streaming_mode = labels.get('com.multiscreen.group.streaming_mode', 'multi_video')
        created_timestamp = float(labels.get('com.multiscreen.group.created_at', time.time()))
        
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
            "streaming_mode": streaming_mode,
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
        
        return group
        
    except Exception as e:
        logger.error(f"Error getting container details: {e}")
        return None


def find_running_ffmpeg_for_group_strict(group_id: str, group_name: str, container_id: str = None) -> List[Dict[str, Any]]:
    """Find running FFmpeg processes for a group using strict matching"""
    try:
        ffmpeg_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and 'ffmpeg' in proc.info['name'].lower():
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    
                    is_match = False
                    match_method = ""
                    
                    # Strict matching
                    stream_path_pattern = f"live/{group_name}/"
                    if stream_path_pattern in cmdline:
                        is_match = True
                        match_method = f"stream_path({stream_path_pattern})"
                    elif group_id in cmdline:
                        is_match = True
                        match_method = f"full_group_id({group_id})"
                    elif container_id and container_id[:12] in cmdline:
                        is_match = True
                        match_method = f"container_id({container_id[:12]})"
                    
                    if is_match:
                        ffmpeg_processes.append({
                            "pid": proc.info['pid'],
                            "cmdline": cmdline,
                            "create_time": proc.create_time() if hasattr(proc, 'create_time') else None,
                            "match_method": match_method
                        })
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return ffmpeg_processes
        
    except Exception as e:
        logger.error(f"Error finding FFmpeg processes for group {group_name}: {e}")
        return []


def wait_for_srt_server(srt_ip: str, srt_port: int, timeout: int = 30) -> bool:
    """Wait for SRT server to be ready"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            # Try to connect to the SRT port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((srt_ip, srt_port))
            sock.close()
            
            if result == 0:
                return True
                
        except Exception:
            pass
        
        time.sleep(2)
    
    return False


def generate_stream_ids(group_id: str, group_name: str, screen_count: int) -> Dict[str, str]:
    """Generate dynamic stream IDs for a session (not persistent)"""
    streams = {}
    
    # Generate a unique session ID based on current time and group
    session_id = str(uuid.uuid4())[:8]
    
    # Main/combined stream
    streams["test"] = f"{session_id}"
    
    # Individual screen streams
    for i in range(screen_count):
        streams[f"test{i}"] = f"{session_id}_{i}"
    
    return streams


def debug_log_stream_info(group_id, group_name, stream_id, srt_ip, srt_port, mode="", screen_count=0):
    """ENHANCED: Debug function with OpenVideoWalls information for both modes"""
    stream_path = f"live/{group_name}/{stream_id}"
    client_url = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={stream_path},m=request,latency=5000000"
    
    # Check FFmpeg capabilities
    ffmpeg_path = find_ffmpeg_executable()
    has_openvideowall = _has_openvideowall_support(ffmpeg_path)
    
    logger.info("="*60)
    logger.info(f" STREAM STARTED - {mode}")
    
    # Show OpenVideoWalls status for both modes
    if has_openvideowall:
        logger.info(" 🎯 OpenVideoWalls: ENABLED (Dynamic SEI timestamps)")
        if "MULTI-VIDEO" in mode:
            logger.info(" 🎯 Multi-video synchronization: Frame-accurate")
        elif "SPLIT-SCREEN" in mode:
            logger.info(" 🎯 Split-screen synchronization: Frame-accurate")
    else:
        logger.info(" ⚠️  OpenVideoWalls: LIMITED (Static SEI timestamps)")
        if "MULTI-VIDEO" in mode:
            logger.info(" ⚠️  Multi-video synchronization: Basic only")
        elif "SPLIT-SCREEN" in mode:
            logger.info(" ⚠️  Split-screen synchronization: Basic only")
    
    logger.info(f" Group: {group_name} (ID: {group_id})")
    logger.info(f" Stream ID: {stream_id}")
    logger.info(f" Stream Path: {stream_path}")
    logger.info(f" Client URL: {client_url}")
    logger.info(f" Test: ffplay '{client_url}'")
    
    # Mode-specific information
    if mode == "MULTI-VIDEO MODE" and screen_count > 0:
        logger.info("-"*60)
        logger.info(" Multiple video files combined into synchronized streams")
        logger.info(" Individual Screen URLs available when streaming is active")
        if has_openvideowall:
            logger.info(" 🎯 Each video gets frame-accurate timestamps for sync")
    elif mode == "SPLIT-SCREEN MODE" and screen_count > 0:
        logger.info("-"*60)
        logger.info(" Single video split into multiple synchronized regions")
        logger.info(" Individual Screen URLs available when streaming is active")
        if has_openvideowall:
            logger.info(" 🎯 Each region gets frame-accurate timestamps for sync")
    
    logger.info("="*60)


def _verify_openvideowall_support(ffmpeg_path: str) -> bool:
    """Check if FFmpeg has OpenVideoWalls SEI timestamp support"""
    try:
        # Quick test for h264_metadata filter with SEI
        test_cmd = [
            ffmpeg_path, "-f", "lavfi", "-i", "testsrc=duration=0.1:size=32x32:rate=1",
            "-frames:v", "1", "-c:v", "libx264", "-preset", "ultrafast",
            "-bsf:v", "h264_metadata=sei_user_data=681d5c8f-80cd-4847-930a-99b9484b4a32+000000",
            "-f", "null", "-"
        ]
        
        result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=5)
        return result.returncode == 0
        
    except Exception:
        return False


def _has_openvideowall_support(ffmpeg_path: str) -> bool:
    """Cache-friendly check for OpenVideoWalls support"""
    if not hasattr(_has_openvideowall_support, 'cache'):
        _has_openvideowall_support.cache = {}
    
    if ffmpeg_path not in _has_openvideowall_support.cache:
        _has_openvideowall_support.cache[ffmpeg_path] = _verify_openvideowall_support(ffmpeg_path)
    
    return _has_openvideowall_support.cache[ffmpeg_path]


def _log_openvideowall_status():
    """Log OpenVideoWalls capability status on module load"""
    try:
        ffmpeg_path = find_ffmpeg_executable()
        has_support = _has_openvideowall_support(ffmpeg_path)
        
        logger.info("=" * 50)
        logger.info(" OPENVIDEOWALL STATUS")
        logger.info("=" * 50)
        logger.info(f" FFmpeg path: {ffmpeg_path}")
        
        if has_support:
            logger.info(" 🎯 OpenVideoWalls: ENABLED")
            logger.info(" ✅ Dynamic SEI timestamps: Available")
            logger.info(" ✅ Multi-video synchronization: Supported")
            logger.info(" ✅ Split-screen synchronization: Supported")
        else:
            logger.info(" ⚠️  OpenVideoWalls: LIMITED")
            logger.info(" ❌ Dynamic SEI timestamps: Unavailable") 
            logger.info(" ⚠️  Multi-video synchronization: Basic only")
            logger.info(" ⚠️  Split-screen synchronization: Basic only")
            
        logger.info("=" * 50)
        
    except Exception as e:
        logger.warning(f"Could not determine OpenVideoWalls status: {e}")


# Initialize on import
try:
    _log_openvideowall_status()
except Exception:
    pass