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

@stream_bp.route("/start_multi_video_srt", methods=["POST"])
def start_multi_video_srt():
    """Combine multiple video files and stream as one SRT stream"""
    try:
        data = request.get_json() or {}
        
        group_id = data.get("group_id")
        video_files_config = data.get("video_files", [])
        
        logger.info("="*60)
        logger.info(" STARTING MULTI-VIDEO SRT STREAM")
        logger.info(f" Group ID: {group_id}")
        logger.info(f" Video files count: {len(video_files_config)}")
        logger.info("="*60)
        
        if not group_id or not video_files_config:
            logger.error(" Missing required parameters: group_id or video_files")
            return jsonify({"error": "group_id and video_files are required"}), 400
        
        # Log video files configuration
        logger.info(" Video files configuration:")
        for idx, video_config in enumerate(video_files_config):
            logger.info(f"   Screen {video_config.get('screen', idx)}: {video_config.get('file', 'Unknown')}")
        
        # Discover group
        logger.info(f" Discovering group '{group_id}' from Docker...")
        group = discover_group_from_docker(group_id)
        if not group:
            logger.error(f" Group '{group_id}' not found in Docker")
            return jsonify({"error": f"Group '{group_id}' not found"}), 404

        group_name = group.get("name", group_id)
        logger.info(f" Found group: '{group_name}'")
        
        # Check Docker status
        docker_running = group.get("docker_running", False)
        logger.info(f" Docker container status: {'Running' if docker_running else 'Stopped'}")
        
        if not docker_running:
            logger.error(f" Docker container for group '{group_name}' is not running")
            return jsonify({"error": f"Docker container for group '{group_name}' is not running"}), 400
        
        # Check for existing streams
        container_id = group.get("container_id")
        logger.info(f" Checking for existing FFmpeg processes...")
        logger.info(f"   Container ID: {container_id}")
        
        existing_ffmpeg = find_running_ffmpeg_for_group_strict(group_id, group_name, container_id)
        if existing_ffmpeg:
            logger.warning(f"  Found {len(existing_ffmpeg)} existing FFmpeg process(es)")
            logger.info("   Streaming already active, returning current status")
            return jsonify({
                "message": f"Multi-video streaming already active for group '{group_name}'",
                "status": "already_active"
            }), 200
        
        logger.info(" No existing streams found")
        
        # Configuration
        screen_count = data.get("screen_count", group.get("screen_count", len(video_files_config)))
        orientation = data.get("orientation", group.get("orientation", "horizontal"))
        output_width = data.get("output_width", 1920)
        output_height = data.get("output_height", 1080)
        grid_rows = data.get("grid_rows", 2)
        grid_cols = data.get("grid_cols", 2)
        
        logger.info("  Stream configuration:")
        logger.info(f"   Screen count: {screen_count}")
        logger.info(f"   Orientation: {orientation}")
        logger.info(f"   Output resolution: {output_width}x{output_height}")
        if orientation.lower() == "grid":
            logger.info(f"   Grid layout: {grid_rows}x{grid_cols}")
        
        ports = group.get("ports", {})
        srt_port = data.get("srt_port", ports.get("srt_port", 10080))
        srt_ip = data.get("srt_ip", "127.0.0.1")
        sei = "681d5c8f-80cd-4847-930a-99b9484b4a32+000000"
        
        logger.info(f" SRT configuration:")
        logger.info(f"   SRT server: {srt_ip}:{srt_port}")
        logger.info(f"   SEI metadata: {sei[:20]}...")
        
        # Calculate canvas dimensions
        logger.info(" Calculating canvas dimensions...")
        if orientation.lower() == "horizontal":
            canvas_width = output_width * screen_count
            canvas_height = output_height
            logger.info(f"   Horizontal layout: {canvas_width}x{canvas_height}")
        elif orientation.lower() == "vertical":
            canvas_width = output_width
            canvas_height = output_height * screen_count
            logger.info(f"   Vertical layout: {canvas_width}x{canvas_height}")
        elif orientation.lower() == "grid":
            if grid_rows * grid_cols != screen_count:
                grid_cols = int(screen_count ** 0.5)
                grid_rows = (screen_count + grid_cols - 1) // grid_cols
                logger.info(f"   Adjusted grid to: {grid_rows}x{grid_cols}")
            canvas_width = output_width * grid_cols
            canvas_height = output_height * grid_rows
            logger.info(f"   Grid layout: {canvas_width}x{canvas_height}")
        else:
            logger.error(f" Invalid orientation: {orientation}")
            return jsonify({"error": f"Invalid orientation: {orientation}"}), 400
        
        # Validate and process video files
        if len(video_files_config) != screen_count:
            logger.error(f" Video file count ({len(video_files_config)}) doesn't match screen count ({screen_count})")
            return jsonify({"error": f"Video file count must match screen count"}), 400
        
        uploads_dir = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        video_files_config.sort(key=lambda x: x.get("screen", 0))
        
        logger.info(" Validating video files...")
        for video_config in video_files_config:
            screen_num = video_config.get("screen", 0)
            file_name = video_config.get("file")
            
            if not file_name:
                logger.error(f" Missing file for screen {screen_num}")
                return jsonify({"error": f"Missing file for screen {screen_num}"}), 400
            
            logger.info(f"   Checking screen {screen_num}: {file_name}")
            
            if file_name.startswith('uploads/'):
                file_path = file_name
            else:
                upload_path = os.path.join(uploads_dir, file_name)
                resized_path = os.path.join(current_app.config.get('DOWNLOAD_FOLDER', 'resized_video'), file_name)
                
                if os.path.exists(upload_path):
                    file_path = upload_path
                    logger.info(f"      Found in uploads: {upload_path}")
                elif os.path.exists(resized_path):
                    file_path = resized_path
                    logger.info(f"      Found in resized: {resized_path}")
                else:
                    logger.error(f"      File not found: {file_name}")
                    return jsonify({"error": f"Video file not found: {file_name}"}), 404
            
            if not os.path.exists(file_path):
                logger.error(f" Video file path doesn't exist: {file_path}")
                return jsonify({"error": f"Video file not found: {file_path}"}), 404
            
            video_config["file_path"] = file_path
        
        video_files = [config["file_path"] for config in video_files_config]
        logger.info(f" All {len(video_files)} video files validated")
        
        # Wait for SRT server
        logger.info(f" Waiting for SRT server at {srt_ip}:{srt_port}...")
        if not wait_for_srt_server(srt_ip, srt_port, timeout=30):
            logger.error(f" SRT server at {srt_ip}:{srt_port} not ready after 30 seconds")
            return jsonify({"error": f"SRT server at {srt_ip}:{srt_port} not ready"}), 500
        logger.info(" SRT server is ready")
        
        # Test SRT connection
        logger.info(" Testing SRT connection...")
        test_result = test_ffmpeg_srt_connection(srt_ip, srt_port, group_name, sei)
        if not test_result["success"]:
            logger.error(f" SRT connection test failed: {test_result}")
            return jsonify({"error": "SRT connection test failed", "test_result": test_result}), 500
        logger.info(" SRT connection test passed")
        
        # Generate dynamic stream IDs for this session
        stream_ids = generate_stream_ids(group_id, group_name, screen_count)
        logger.info(f" Generated dynamic stream IDs: {stream_ids}")

        # Debug logging
        debug_log_stream_info(group_id, group_name, stream_ids["test"], srt_ip, srt_port, "MULTI-VIDEO MODE", screen_count)

        # Build FFmpeg command
        logger.info(" Building FFmpeg command...")
        ffmpeg_cmd = build_single_stream_ffmpeg_command(
            video_files,
            screen_count,
            orientation,
            output_width,
            output_height,
            srt_ip,
            srt_port,
            sei,
            group_name,
            group_id,
            grid_rows,
            grid_cols,
            30,
            "6000k",
            stream_ids  # Add this parameter
        )
        
        logger.info(f" FFmpeg command preview:")
        logger.info(f"   {' '.join(ffmpeg_cmd[:10])}...")
        logger.info(f"   Total arguments: {len(ffmpeg_cmd)}")
        
        # Log all the stream URLs that will be created
        logger.info("="*60)
        logger.info(f" CREATING MULTI-VIDEO STREAMS - SEPARATE OUTPUTS")
        logger.info(f" Group: {group_name} (ID: {group_id})")
        logger.info(f" Creating {screen_count + 1} streams:")
        logger.info(f"   - Combined: live/{group_name}/combined_{group_id}")
        logger.info("="*60)
        
        # Start FFmpeg process
        logger.info(" Starting FFmpeg process...")
        process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=0
        )
        
        logger.info(f" FFmpeg process started with PID: {process.pid}")
        
        # Monitor FFmpeg startup
        logger.info(" Monitoring FFmpeg startup...")
        startup_success, streaming_detected = monitor_ffmpeg(
            process, 
            stream_type="Multi-video FFmpeg",
            startup_timeout=5,
            startup_max_lines=20
        )
        
        if not startup_success:
            if process.poll() is not None:
                logger.error(f" FFmpeg process died with exit code: {process.returncode}")
                return jsonify({"error": f"Multi-video FFmpeg failed to start"}), 500
            logger.warning("  FFmpeg startup reported failure but process is still running")
        
        if not streaming_detected:
            logger.warning("  No streaming output detected during startup monitoring")
        else:
            logger.info(" Streaming output detected")
        
        # Generate response
        logger.info(" Generating response data...")
        crop_info = generate_client_crop_info(
            screen_count=screen_count,
            orientation=orientation,
            output_width=output_width,
            output_height=output_height,
            grid_rows=grid_rows,
            grid_cols=grid_cols
        )
        
        # Generate client stream URLs for ALL streams
        client_stream_urls = {}
        
        # Combined stream URL
        combined_stream_path = f"live/{group_name}/combined_{group_id}"
        srt_params = "latency=5000000&connect_timeout=10000&rcvbuf=67108864&sndbuf=67108864"
        client_stream_urls["combined"] = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={combined_stream_path},m=request&{srt_params}"
        
        # Individual screen URLs
        for i in range(screen_count):
            screen_key = f"test{i}"
            individual_stream_id = stream_ids.get(screen_key)
            individual_stream_path = f"live/{group_name}/{individual_stream_id}"
            client_stream_urls[f"screen{i}"] = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={individual_stream_path},m=request&{srt_params}"
        
        logger.info(" Client stream URLs:")
        for name, url in client_stream_urls.items():
            logger.info(f"   {name}: {url}")
        
        # Generate test result string
        test_result = f"ffplay '{client_stream_urls['combined']}'"
        
        logger.info("="*60)
        logger.info(" MULTI-VIDEO STREAMING STARTED SUCCESSFULLY")
        logger.info(f" Group: {group_name}")
        logger.info(f" Process PID: {process.pid}")
        logger.info(f" Screens: {screen_count}")
        logger.info(f" Combined Stream: {client_stream_urls['combined']}")
        logger.info(f" {screen_count} Individual streams also available")
        logger.info("="*60)
        
        return jsonify({
            "message": f"Multi-video SRT streaming started for group '{group_name}'",
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
                "stream_urls": client_stream_urls,
                "combined_stream_path": combined_stream_path,
                "stream_ids": stream_ids,
                "crop_information": crop_info
            },
            "status": "active",
            "test_result": test_result
        }), 200
        
    except Exception as e:
        logger.error("="*60)
        logger.error(" EXCEPTION IN start_multi_video_srt")
        logger.error(f" Error type: {type(e).__name__}")
        logger.error(f" Error message: {str(e)}")
        logger.error("Stack trace:", exc_info=True)
        logger.error("="*60)
        return jsonify({"error": str(e)}), 500
    
@stream_bp.route("/start_split_screen_srt", methods=["POST"])
def start_split_screen_srt():
    """Take one video file and split it across multiple screens"""
    try:
        data = request.get_json() or {}
        
        group_id = data.get("group_id")
        video_file = data.get("video_file")
        
        logger.info("="*60)
        logger.info(" STARTING SPLIT-SCREEN SRT STREAM")
        logger.info(f" Group ID: {group_id}")
        logger.info(f" Video file: {video_file}")
        logger.info("="*60)
        
        if not group_id or not video_file:
            logger.error(" Missing required parameters: group_id or video_file")
            return jsonify({"error": "group_id and video_file are required"}), 400
        
        # Discover group
        logger.info(f" Discovering group '{group_id}' from Docker...")
        group = discover_group_from_docker(group_id)
        if not group:
            logger.error(f" Group '{group_id}' not found in Docker")
            return jsonify({"error": f"Group '{group_id}' not found"}), 404
        
        group_name = group.get("name", group_id)
        logger.info(f" Found group: '{group_name}'")
        
        # Check Docker status
        docker_running = group.get("docker_running", False)
        logger.info(f" Docker container status: {'Running' if docker_running else 'Stopped'}")
        
        if not docker_running:
            logger.error(f" Docker container for group '{group_name}' is not running")
            return jsonify({"error": f"Docker container for group '{group_name}' is not running"}), 400
        
        # Check for existing streams
        container_id = group.get("container_id")
        logger.info(f" Checking for existing FFmpeg processes...")
        logger.info(f"   Container ID: {container_id}")
        
        existing_ffmpeg = find_running_ffmpeg_for_group_strict(group_id, group_name, container_id)
        if existing_ffmpeg:
            logger.warning(f"  Found {len(existing_ffmpeg)} existing FFmpeg process(es)")
            logger.info("   Streaming already active, returning current status")
            return jsonify({
                "message": f"Split-screen streaming already active for group '{group_name}'",
                "status": "already_active"
            }), 200
        
        logger.info(" No existing streams found")
        
        # Configuration
        screen_count = data.get("screen_count", group.get("screen_count", 2))
        orientation = data.get("orientation", group.get("orientation", "horizontal"))
        output_width = data.get("output_width", 1920)
        output_height = data.get("output_height", 1080)
        grid_rows = data.get("grid_rows", 2)
        grid_cols = data.get("grid_cols", 2)
        
        logger.info("  Stream configuration:")
        logger.info(f"   Screen count: {screen_count}")
        logger.info(f"   Orientation: {orientation}")
        logger.info(f"   Output resolution: {output_width}x{output_height}")
        if orientation.lower() == "grid":
            logger.info(f"   Grid layout: {grid_rows}x{grid_cols}")
        
        ports = group.get("ports", {})
        srt_port = data.get("srt_port", ports.get("srt_port", 10080))
        srt_ip = data.get("srt_ip", "127.0.0.1")
        sei_raw = data.get("sei", "681d5c8f-80cd-4847-930a-99b9484b4a32+000000")
        sei = sei_raw if '+' in sei_raw else f"{sei_raw}+000000"
        
        logger.info(f" SRT configuration:")
        logger.info(f"   SRT server: {srt_ip}:{srt_port}")
        logger.info(f"   SEI metadata: {sei[:20]}...")
        
        # Calculate canvas dimensions
        logger.info(" Calculating canvas dimensions...")
        if orientation.lower() == "horizontal":
            canvas_width = output_width * screen_count
            canvas_height = output_height
            logger.info(f"   Horizontal layout: {canvas_width}x{canvas_height}")
        elif orientation.lower() == "vertical":
            canvas_width = output_width
            canvas_height = output_height * screen_count
            logger.info(f"   Vertical layout: {canvas_width}x{canvas_height}")
        elif orientation.lower() == "grid":
            if grid_rows * grid_cols != screen_count:
                grid_cols = int(screen_count ** 0.5)
                grid_rows = (screen_count + grid_cols - 1) // grid_cols
                logger.info(f"   Adjusted grid to: {grid_rows}x{grid_cols}")
            canvas_width = output_width * grid_cols
            canvas_height = output_height * grid_rows
            logger.info(f"   Grid layout: {canvas_width}x{canvas_height}")
        else:
            logger.error(f" Invalid orientation: {orientation}")
            return jsonify({"error": f"Invalid orientation: {orientation}"}), 400
        
        # Validate and process video file
        uploads_dir = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        
        logger.info(f" Validating video file: {video_file}")
        if video_file.startswith('uploads/'):
            file_path = video_file
        else:
            upload_path = os.path.join(uploads_dir, video_file)
            resized_path = os.path.join(current_app.config.get('DOWNLOAD_FOLDER', 'resized_video'), video_file)
            
            if os.path.exists(upload_path):
                file_path = upload_path
                logger.info(f"    Found in uploads: {upload_path}")
            elif os.path.exists(resized_path):
                file_path = resized_path
                logger.info(f"    Found in resized: {resized_path}")
            else:
                logger.error(f"    File not found: {video_file}")
                return jsonify({"error": f"Video file not found: {video_file}"}), 404
        
        if not os.path.exists(file_path):
            logger.error(f" Video file path doesn't exist: {file_path}")
            return jsonify({"error": f"Video file not found: {file_path}"}), 404
        
        logger.info(" Video file validated")
        
        # Wait for SRT server
        logger.info(f" Waiting for SRT server at {srt_ip}:{srt_port}...")
        if not wait_for_srt_server(srt_ip, srt_port, timeout=30):
            logger.error(f" SRT server at {srt_ip}:{srt_port} not ready after 30 seconds")
            return jsonify({"error": f"SRT server at {srt_ip}:{srt_port} not ready"}), 500
        logger.info(" SRT server is ready")
        
        # Test SRT connection
        logger.info(" Testing SRT connection...")
        test_result = test_ffmpeg_srt_connection(srt_ip, srt_port, group_name, sei)
        if not test_result["success"]:
            logger.error(f" SRT connection test failed: {test_result}")
            return jsonify({"error": "SRT connection test failed", "test_result": test_result}), 500
        logger.info(" SRT connection test passed")
        
        # Get persistent stream IDs
        stream_ids = generate_stream_ids(group_id, group_name, screen_count)
        logger.info(f" Generated dynamic stream IDs: {stream_ids}")

        # Debug logging
        debug_log_stream_info(group_id, group_name, f"split_{group_id}", srt_ip, srt_port, "SPLIT-SCREEN MODE", screen_count)

        # Build FFmpeg command with multiple outputs
        logger.info(" Building FFmpeg command...")
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
            base_stream_id=group_id,
            grid_rows=grid_rows,
            grid_cols=grid_cols,
            stream_ids=stream_ids
        )
        
        logger.info(f" FFmpeg command preview:")
        logger.info(f"   {' '.join(ffmpeg_cmd[:10])}...")
        logger.info(f"   Total arguments: {len(ffmpeg_cmd)}")
        
        # Log all the stream URLs that will be created
        logger.info("="*60)
        logger.info(f" CREATING SPLIT-SCREEN STREAMS - MULTIPLE OUTPUTS")
        logger.info(f" Group: {group_name} (ID: {group_id})")
        logger.info(f" Creating {screen_count + 1} streams:")
        logger.info(f"   - Full/Combined: live/{group_name}/split_{group_id}")
        
        for i in range(screen_count):
            screen_key = f"test{i}"
            stream_id_screen = stream_ids.get(screen_key)
            logger.info(f"   - Screen {i}: live/{group_name}/{stream_id_screen}")
        logger.info("="*60)
        
        # Start FFmpeg process
        logger.info(" Starting FFmpeg process...")
        process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=0
        )
        
        logger.info(f" FFmpeg process started with PID: {process.pid}")
        
        # Monitor FFmpeg startup
        logger.info(" Monitoring FFmpeg startup...")
        startup_success, streaming_detected = monitor_ffmpeg(
            process,
            stream_type="Split-screen FFmpeg", 
            startup_timeout=5,
            startup_max_lines=20
        )
        
        if not startup_success:
            if process.poll() is not None:
                logger.error(f" FFmpeg process died with exit code: {process.returncode}")
                return jsonify({"error": f"Split-screen FFmpeg failed to start"}), 500
            logger.warning("  FFmpeg startup reported failure but process is still running")
        
        if not streaming_detected:
            logger.warning("  No streaming output detected during startup monitoring")
        else:
            logger.info(" Streaming output detected")
        
        # Generate response
        logger.info(" Generating response data...")
        crop_info = generate_client_crop_info(
            screen_count=screen_count,
            orientation=orientation,
            output_width=output_width,
            output_height=output_height,
            grid_rows=grid_rows,
            grid_cols=grid_cols
        )
        
        # Generate client stream URLs for ALL streams
        client_stream_urls = {}
        
        # Full/Combined stream URL
        combined_stream_path = f"live/{group_name}/split_{group_id}"
        srt_params = "latency=5000000&connect_timeout=10000&rcvbuf=67108864&sndbuf=67108864"
        client_stream_urls["combined"] = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={combined_stream_path},m=request&{srt_params}"
        
        # Individual screen URLs
        for i in range(screen_count):
            screen_key = f"test{i}"
            individual_stream_id = stream_ids.get(screen_key)
            individual_stream_path = f"live/{group_name}/{individual_stream_id}"
            client_stream_urls[f"screen{i}"] = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={individual_stream_path},m=request&{srt_params}"
        
        logger.info(" Client stream URLs:")
        for name, url in client_stream_urls.items():
            logger.info(f"   {name}: {url}")
        
        # Generate test result string
        test_result = f"ffplay '{client_stream_urls['combined']}'"
        
        logger.info("="*60)
        logger.info(" SPLIT-SCREEN STREAMING STARTED SUCCESSFULLY")
        logger.info(f" Group: {group_name}")
        logger.info(f" Process PID: {process.pid}")
        logger.info(f" Screens: {screen_count}")
        logger.info(f" Combined Stream: {client_stream_urls['combined']}")
        logger.info(f" {screen_count} Individual screen streams also available")
        logger.info("="*60)
        
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
                "stream_urls": client_stream_urls,
                "combined_stream_path": combined_stream_path,
                "stream_ids": stream_ids,
                "crop_information": crop_info
            },
            "status": "active",
            "test_result": test_result
        }), 200
        
    except Exception as e:
        logger.error("="*60)
        logger.error(" EXCEPTION IN start_split_screen_srt")
        logger.error(f" Error type: {type(e).__name__}")
        logger.error(f" Error message: {str(e)}")
        logger.error("Stack trace:", exc_info=True)
        logger.error("="*60)
        return jsonify({"error": str(e)}), 500
    
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
        
        # Generate dynamic stream IDs for status display (these won't match actual running streams)
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

# Helper functions

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
    base_stream_id: str,
    grid_rows: int = 2,
    grid_cols: int = 2,
    framerate: int = 30,
    bitrate: str = "3000k",
    stream_ids: Dict[str, str] = None 
) -> List[str]:
    """
    Build FFmpeg command that creates multiple video streams - one combined and individual crops
    Similar to hwsel's approach
    """
    
    ffmpeg_path = find_ffmpeg_executable()
    
    # Build input args
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
    
    # Build filter - first combine all videos
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
    
    # Now split the combined output and create crops for each screen
    filter_parts.append(f"[combined]split={screen_count + 1}[full]" + "".join(f"[copy{i}]" for i in range(screen_count)))
    
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
    
    # Build FFmpeg command
    ffmpeg_cmd = [
        ffmpeg_path,
        "-y",
        "-v", "error",
        "-stats"
    ]
    
    ffmpeg_cmd.extend(input_args + ["-filter_complex", complete_filter])
    
    # Common encoding parameters
    encoding_params = [
        "-an",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-tune", "zerolatency",
        "-maxrate", bitrate,
        "-bufsize", str(int(bitrate.rstrip('k')) * 2) + "k",
        "-bsf:v", f"h264_metadata=sei_user_data={sei}",
        "-pes_payload_size", "0",
        "-bf", "0",
        "-g", "1",
        "-r", str(framerate),
        "-f", "mpegts"
    ]
    
    # SRT parameters
    srt_params = "latency=5000000&connect_timeout=5000&rcvbuf=67108864&sndbuf=67108864"
    
    # Add output for combined stream
    combined_stream_path = f"live/{group_name}/combined_{base_stream_id}"
    combined_url = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={combined_stream_path},m=publish&{srt_params}"
    ffmpeg_cmd.extend(["-map", "[full]"] + encoding_params + [combined_url])
    
    # Add output for each individual screen
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
    video_file: str,  # Change from video_files: List[str] to video_file: str
    screen_count: int,
    orientation: str,
    output_width: int,
    output_height: int,
    canvas_width: int,    # Keep these parameters or calculate them
    canvas_height: int,   # Keep these parameters or calculate them
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
    """Build FFmpeg command for split-screen streaming with multiple outputs"""
    
    ffmpeg_path = find_ffmpeg_executable()
    
    # Build input
    input_args = ["-stream_loop", "-1", "-re", "-i", video_file]
    
    # Build filter complex to create both full and cropped outputs
    filter_parts = []
    
    # First, scale the input to canvas size
    filter_parts.append(f"[0:v]fps={framerate},scale={canvas_width}:{canvas_height}:force_original_aspect_ratio=increase,crop={canvas_width}:{canvas_height}[scaled]")
    
    # Split the scaled video for full output and crops
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
    
    # Build FFmpeg command
    ffmpeg_cmd = [
        ffmpeg_path,
        "-y",
        "-v", "error",
        "-stats"
    ]
    
    ffmpeg_cmd.extend(input_args + ["-filter_complex", complete_filter])
    
    # Common encoding parameters
    encoding_params = [
        "-an",
        "-c:v", "libx264",
        "-preset", "veryfast", 
        "-tune", "zerolatency",
        "-maxrate", bitrate,
        "-bufsize", str(int(bitrate.rstrip('k')) * 2) + "k",
        "-bsf:v", f"h264_metadata=sei_user_data={sei}",
        "-pes_payload_size", "0",
        "-bf", "0",
        "-g", "1",
        "-r", str(framerate),
        "-f", "mpegts"
    ]
    
    # SRT parameters
    srt_params = "latency=5000000&connect_timeout=5000&rcvbuf=67108864&sndbuf=67108864"
    
    # Add output for combined/full stream
    combined_stream_path = f"live/{group_name}/split_{base_stream_id}"
    combined_url = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={combined_stream_path},m=publish&{srt_params}"
    ffmpeg_cmd.extend(["-map", "[full]"] + encoding_params + [combined_url])
    
    # Add output for each individual screen
    if stream_ids is None:
        stream_ids = generate_stream_ids(base_stream_id, group_name, screen_count)

    for i in range(screen_count):
        screen_key = f"test{i}"
        individual_stream_id = stream_ids.get(screen_key, f"screen{i}_{base_stream_id}")
        stream_path = f"live/{group_name}/{individual_stream_id}"
        stream_url = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={stream_path},m=publish&{srt_params}"
        
        ffmpeg_cmd.extend(["-map", f"[screen{i}]"] + encoding_params + [stream_url])
    
    return ffmpeg_cmd

def test_ffmpeg_srt_connection(srt_ip, srt_port, group_name, sei, retry_count=3):
    """Enhanced SRT connection test with retries and consistent parameters"""
    if '+' not in sei:
        sei = f"{sei}+000000"
    
    # Use consistent SRT parameters
    srt_params = "latency=5000000&connect_timeout=10000"  # Increased timeouts
    
    for attempt in range(retry_count):
        test_stream_id = f"test_{random.randint(10000, 99999)}"  # Random ID to avoid conflicts
        
        test_cmd = [
            find_ffmpeg_executable(),
            "-v", "error",
            "-y",
            "-f", "lavfi", "-i", f"testsrc=s=640x480:r=5:d={attempt+2}",  # Vary duration
            "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency",
            "-bsf:v", f"h264_metadata=sei_user_data={sei}",
            "-f", "mpegts",
            f"srt://{srt_ip}:{srt_port}?streamid=#!::r=live/{group_name}/{test_stream_id},m=publish&{srt_params}"
        ]
        
        try:
            logger.info(f"SRT connection test attempt {attempt + 1}/{retry_count}")
            result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                logger.info("SRT connection test succeeded")
                return {"success": True, "output": result.stdout}
            else:
                logger.warning(f"SRT test attempt {attempt + 1} failed: {result.stderr}")
                
                if attempt < retry_count - 1:
                    time.sleep(2)  # Wait before retry
                    
        except subprocess.TimeoutExpired:
            logger.warning(f"SRT test attempt {attempt + 1} timed out")
            if attempt < retry_count - 1:
                time.sleep(1)
        except Exception as e:
            logger.error(f"SRT test error: {e}")
    
    return {
        "success": False,
        "error": "All connection attempts failed",
        "retry_count": retry_count
    }

def generate_client_crop_info(
    screen_count: int,
    orientation: str,
    output_width: int,
    output_height: int,
    grid_rows: int = 2,
    grid_cols: int = 2
) -> Dict[int, Dict[str, int]]:
    """Generate crop information for clients"""
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
    custom_paths = [
        "./cmake-build-debug/external/Install/bin/ffmpeg",
        "./build/external/Install/bin/ffmpeg",
        "ffmpeg"
    ]
    
    for path in custom_paths:
        if os.path.exists(path) or path == "ffmpeg":
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

def find_running_ffmpeg_for_group(group_id: str, group_name: str) -> List[Dict[str, Any]]:
    """Legacy function - forwards to strict version"""
    return find_running_ffmpeg_for_group_strict(group_id, group_name)

def wait_for_srt_server(srt_ip: str, srt_port: int, timeout: int = 30) -> bool:
    """Wait for SRT server to be ready"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            # Check with netstat
            netstat_check = subprocess.run(
                ["netstat", "-ln"], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            
            if netstat_check.returncode == 0:
                listening_ports = netstat_check.stdout
                if f":{srt_port}" in listening_ports:
                    return True
            
            # Check with Docker
            try:
                docker_check = subprocess.run(
                    ["docker", "ps", "--format", "table {{.Names}}\t{{.Ports}}", "--filter", f"publish={srt_port}"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if docker_check.returncode == 0 and docker_check.stdout.strip():
                    lines = docker_check.stdout.strip().split('\n')
                    if len(lines) > 1:
                        time.sleep(2)
                        return True
                
            except Exception:
                pass
            
        except subprocess.TimeoutExpired:
            pass
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
    """Simple debug function to log valid stream information"""
    stream_path = f"live/{group_name}/{stream_id}"
    client_url = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={stream_path},m=request,latency=5000000"
    
    logger.info("="*60)
    logger.info(f" STREAM STARTED - {mode}")
    logger.info(f" Group: {group_name} (ID: {group_id})")
    logger.info(f" Stream ID: {stream_id}")
    logger.info(f" Stream Path: {stream_path}")
    logger.info(f" Client URL: {client_url}")
    logger.info(f" Test: ffplay '{client_url}'")
    
    # If multi-video mode, show individual screen URLs
    if mode == "MULTI-VIDEO MODE" and screen_count > 0:
        logger.info("-"*60)
        logger.info(" Individual Screen URLs available when streaming is active")
    
    logger.info("="*60)