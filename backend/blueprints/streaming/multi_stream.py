# blueprints/streaming/multi_stream.py
"""
Single-mode optimized multi-video streaming functionality.
One reliable configuration that works consistently with good performance.
"""

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
import select
import glob
from typing import Dict, List, Any, Optional

# Import SRTService for connection testing
try:
    from ..services.srt_service import SRTService
except ImportError:
    try:
        from services.srt_service import SRTService
    except ImportError:
        class SRTService:
            @staticmethod
            def test_connection(srt_ip: str, srt_port: int, group_name: str, sei: str) -> Dict[str, Any]:
                logger.info(f"Testing SRT connection to {srt_ip}:{srt_port}")
                return {"success": True, "message": "SRT connection test skipped (fallback mode)"}
            
            @staticmethod
            def monitor_srt_server(srt_ip: str, srt_port: int, timeout: int = 5) -> Dict[str, Any]:
                return {"ready": True, "message": "SRT monitoring skipped (fallback mode)"}

# Create blueprint
multi_stream_bp = Blueprint('multi_stream', __name__)

# Configure logger
logger = logging.getLogger(__name__)

# Global storage for current active stream IDs
_active_stream_ids = {}

# ============================================================================
# ACTIVE STREAM ID MANAGEMENT
# ============================================================================

def get_active_stream_ids(group_id: str) -> Dict[str, str]:
    """Get current active stream IDs for a group"""
    return _active_stream_ids.get(group_id, {})

def set_active_stream_ids(group_id: str, stream_ids: Dict[str, str]):
    """Set current active stream IDs for a group"""
    _active_stream_ids[group_id] = stream_ids
    logger.info(f"Stored active stream IDs for group {group_id}: {stream_ids}")

def clear_active_stream_ids(group_id: str):
    """Clear current active stream IDs for a group when streaming stops"""
    if group_id in _active_stream_ids:
        del _active_stream_ids[group_id]
        logger.info(f"Cleared active stream IDs for group {group_id}")

# ============================================================================
# BACKGROUND MONITORING
# ============================================================================

def stream_monitor(process, group_id, group_name, stream_config):
    """
    Reliable background monitor for FFmpeg streams
    Single, consistent monitoring approach
    """
    try:
        logger.info(f" Starting stream monitor for {group_name} (PID: {process.pid})")
        
        frame_count = 0
        last_frame_time = time.time()
        last_resource_check = time.time()
        stall_warnings = 0
        
        # Single set of reliable configuration
        STALL_TIMEOUT = 30
        MAX_STALL_WARNINGS = 3
        RESOURCE_CHECK_INTERVAL = 60
        MAX_MEMORY_MB = 2000
        
        while process.poll() is None:
            try:
                current_time = time.time()
                
                # Read FFmpeg output
                if process.stdout and select.select([process.stdout], [], [], 0.1)[0]:
                    line = process.stdout.readline()
                    
                    if line:
                        line = line.strip()
                        
                        # Track frame progress
                        if "frame=" in line and "fps=" in line:
                            frame_count += 1
                            last_frame_time = current_time
                            stall_warnings = 0
                            
                            # Log progress every 500 frames
                            if frame_count % 500 == 0:
                                logger.info(f" {group_name}: {frame_count} frames processed")
                        
                        # Check for critical errors
                        critical_errors = [
                            "connection refused", "broken pipe", "network unreachable",
                            "out of memory", "resource temporarily unavailable",
                            "connection reset", "host unreachable"
                        ]
                        
                        line_lower = line.lower()
                        for error in critical_errors:
                            if error in line_lower:
                                logger.error(f" CRITICAL ERROR in {group_name}: {line}")
                                process.terminate()
                                return
                
                # Check for stalled stream
                time_since_frame = current_time - last_frame_time
                if frame_count > 0 and time_since_frame > STALL_TIMEOUT:
                    stall_warnings += 1
                    logger.error(f" STREAM STALLED: {group_name} ({time_since_frame:.1f}s since last frame)")
                    
                    if stall_warnings >= MAX_STALL_WARNINGS:
                        logger.error(f" TERMINATING STALLED STREAM: {group_name}")
                        process.terminate()
                        return
                
                # Periodic resource monitoring
                if current_time - last_resource_check >= RESOURCE_CHECK_INTERVAL:
                    try:
                        proc_info = psutil.Process(process.pid)
                        memory_mb = proc_info.memory_info().rss / 1024 / 1024
                        
                        if memory_mb > MAX_MEMORY_MB:
                            logger.error(f" HIGH MEMORY: {group_name} using {memory_mb:.1f}MB")
                            if memory_mb > MAX_MEMORY_MB * 2:
                                logger.error(f" TERMINATING due to memory leak")
                                process.terminate()
                                return
                        
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        logger.error(f" Process {process.pid} no longer exists")
                        return
                    
                    last_resource_check = current_time
                
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f" Monitor error for {group_name}: {e}")
                time.sleep(1)
        
        # Process ended
        exit_code = process.returncode
        logger.warning(f" {group_name} ended with exit code {exit_code}, {frame_count} total frames")
        
    except Exception as e:
        logger.error(f" Monitor crashed for {group_name}: {e}")
    finally:
        clear_active_stream_ids(group_id)

# ============================================================================
# FFMPEG COMMAND BUILDER - SINGLE RELIABLE MODE
# ============================================================================

def build_reliable_ffmpeg_command(
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
    bitrate: str = "2500k",
    stream_ids: Dict[str, str] = None
) -> List[str]:
    """
    Build single, reliable FFmpeg command
    Optimized for consistency and performance without mode complexity
    """
    
    if stream_ids is None:
        stream_ids = generate_stream_ids(base_stream_id, group_name, screen_count)
    
    logger.info(f" Building reliable FFmpeg command")
    logger.info(f"   Videos: {len(video_files)}, Screens: {screen_count}")
    logger.info(f"   Output: {output_width}x{output_height}, Orientation: {orientation}")
    
    # Reliable base command - proven settings
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-v", "error",
        "-nostats",
        "-thread_queue_size", "512",
        "-avoid_negative_ts", "make_zero"
    ]
    
    # Add inputs
    for video_file in video_files:
        file_path = os.path.join("uploads", video_file)
        ffmpeg_cmd.extend([
            "-stream_loop", "-1",
            "-re",
            "-fflags", "+genpts",
            "-i", file_path
        ])
    
    # Calculate canvas dimensions
    canvas_width, canvas_height = calculate_canvas_dimensions(
        orientation, screen_count, output_width, output_height, grid_rows, grid_cols
    )
    
    # Build filter complex - always create both combined and individual streams
    filter_complex = build_reliable_filter_complex(
        video_files, canvas_width, canvas_height,
        output_width, output_height, orientation, screen_count,
        grid_rows, grid_cols, framerate
    )
    
    ffmpeg_cmd.extend(["-filter_complex", filter_complex])
    
    # Reliable encoding settings - balanced performance and quality
    base_encoding = [
        "-c:v", "libx264",
        "-preset", "faster",           # Good balance of speed and quality
        "-crf", "24",                  # Good quality
        "-g", "30",                    # 1 second keyframes
        "-threads", "4",               # Reasonable thread count
        "-tune", "zerolatency",        # Low latency
        "-profile:v", "main",          # Widely compatible
        "-level", "4.0",
        "-pix_fmt", "yuv420p",
        "-r", str(framerate),
        "-maxrate", bitrate,
        "-bufsize", str(int(bitrate.rstrip('k')) * 1.5) + "k",
        "-f", "mpegts"
    ]
    
    # Combined stream output
    ffmpeg_cmd.extend(["-map", "[combined]"] + base_encoding + [
        f"srt://{srt_ip}:{srt_port}?streamid=#!::r=live/{group_name}/{base_stream_id},m=publish"
    ])
    
    # Individual screen outputs (create all requested screens)
    for i in range(screen_count):
        screen_key = f"test{i}"
        stream_id = stream_ids.get(screen_key, f"{base_stream_id}_{i}")
        
        ffmpeg_cmd.extend(["-map", f"[screen{i}]"] + base_encoding + [
            f"srt://{srt_ip}:{srt_port}?streamid=#!::r=live/{group_name}/{stream_id},m=publish"
        ])
    
    logger.info(f" Created {screen_count + 1} streams (1 combined + {screen_count} individual)")
    logger.info(f" Using 'faster' preset with 30-frame keyframes, 4 threads")
    
    return ffmpeg_cmd

def calculate_canvas_dimensions(orientation: str, screen_count: int, output_width: int, output_height: int, grid_rows: int, grid_cols: int) -> tuple:
    """Calculate canvas dimensions based on orientation"""
    if orientation.lower() == "horizontal":
        return output_width * screen_count, output_height
    elif orientation.lower() == "vertical":
        return output_width, output_height * screen_count
    else:  # grid
        return output_width * grid_cols, output_height * grid_rows

def build_reliable_filter_complex(
    video_files, canvas_width, canvas_height,
    output_width, output_height, orientation, screen_count,
    grid_rows, grid_cols, framerate
):
    """Build reliable filter complex that always works"""
    
    filter_parts = []
    
    # Scale all inputs
    for i, video_file in enumerate(video_files):
        filter_parts.append(f"[{i}:v]scale={output_width}:{output_height},fps={framerate}[scaled{i}]")
    
    # Create combined canvas
    filter_parts.append(f"color=c=black:s={canvas_width}x{canvas_height}:r={framerate}[canvas]")
    
    # Overlay videos onto canvas for combined stream
    current = "[canvas]"
    for i in range(min(len(video_files), screen_count)):
        x_pos, y_pos = calculate_position(i, orientation, output_width, output_height, grid_cols)
        next_label = "[combined_full]" if i == min(len(video_files), screen_count) - 1 else f"[overlay{i}]"
        filter_parts.append(f"{current}[scaled{i}]overlay={x_pos}:{y_pos}{next_label}")
        current = next_label
    
    # Split the combined stream for multiple outputs
    split_count = screen_count + 1  # +1 for combined
    split_outputs = ["[combined]"] + [f"[screen{i}_pre]" for i in range(screen_count)]
    filter_parts.append(f"[combined_full]split={split_count}{''.join(split_outputs)}")
    
    # Create individual screen crops
    for i in range(screen_count):
        x_crop, y_crop = calculate_position(i, orientation, output_width, output_height, grid_cols)
        filter_parts.append(f"[screen{i}_pre]crop={output_width}:{output_height}:{x_crop}:{y_crop}[screen{i}]")
    
    return ";".join(filter_parts)

def calculate_position(index, orientation, output_width, output_height, grid_cols):
    """Calculate x,y position for video placement"""
    if orientation.lower() == "horizontal":
        return index * output_width, 0
    elif orientation.lower() == "vertical":
        return 0, index * output_height
    else:  # grid
        row = index // grid_cols
        col = index % grid_cols
        return col * output_width, row * output_height

# ============================================================================
# FLASK ROUTE HANDLERS
# ============================================================================

@multi_stream_bp.route("/start_multi_video_srt", methods=["POST"])
def start_multi_video_srt():
    """
    Single-mode reliable multi-video streaming
    """
    try:
        # Clean up old containers first
        cleanup_count = cleanup_old_srs_containers(max_containers=3)
        if cleanup_count > 0:
            logger.info(f" Cleaned up {cleanup_count} old containers")
        
        # Get request data
        data = request.get_json() or {}
        
        # Extract required parameters
        group_id = data.get("group_id")
        if not group_id:
            return jsonify({"error": "group_id is required"}), 400
        
        # Discover group from Docker
        group = discover_group_from_docker(group_id)
        if not group:
            return jsonify({"error": f"Group '{group_id}' not found"}), 404
        
        # Extract video files
        video_files = data.get("video_files", [])
        if not video_files:
            return jsonify({"error": "video_files is required"}), 400
        
        # Get configuration
        group_name = group.get("name", group_id)
        screen_count = data.get("screen_count", group.get("screen_count", 2))
        orientation = data.get("orientation", group.get("orientation", "horizontal"))
        output_width = data.get("output_width", 1920)
        output_height = data.get("output_height", 1080)
        
        # Get streaming parameters
        ports = group.get("ports", {})
        srt_ip = data.get("srt_ip", "127.0.0.1")
        srt_port = ports.get("srt_port")
        
        if not srt_port:
            return jsonify({
                "error": "No SRT port available for this group",
                "group_ports": ports
            }), 500
        
        # Get encoding parameters
        sei = data.get("sei", "681d5c8f-80cd-4847-930a-99b9484b4a32+000000")
        framerate = data.get("framerate", 30)
        bitrate = data.get("bitrate", "2500k")
        
        logger.info(f" Starting reliable streaming for {group_name}")
        logger.info(f"   Port: {srt_port}, Videos: {len(video_files)}, Screens: {screen_count}")
        
        # Check for existing streams
        container_id = group.get("container_id")
        existing_ffmpeg = find_running_ffmpeg_for_group_strict(group_id, group_name, container_id)
        if existing_ffmpeg:
            logger.warning(f"Streaming already active for group '{group_name}'")
            return jsonify({
                "message": f"Multi-video streaming already active for group '{group_name}'",
                "status": "already_active"
            }), 200
        
        # Generate stream IDs
        base_stream_id = str(uuid.uuid4())[:8]
        stream_ids = generate_stream_ids(base_stream_id, group_name, screen_count)
        set_active_stream_ids(group_id, stream_ids)
        
        # Wait for SRT server
        try:
            srt_status = SRTService.monitor_srt_server(srt_ip, srt_port, timeout=5)
            if not srt_status["ready"]:
                logger.error(f"SRT server not ready: {srt_status['message']}")
                clear_active_stream_ids(group_id)
                return jsonify({"error": f"SRT server not ready: {srt_status['message']}"}), 503
            logger.info("SRT server ready")
        except Exception as e:
            logger.warning(f"SRT service check failed, using fallback: {e}")
            if not check_srt_port_simple(srt_ip, srt_port, timeout=5):
                clear_active_stream_ids(group_id)
                return jsonify({"error": "SRT server not ready after 5s"}), 500
        
        # Test SRT connection
        test_result = SRTService.test_connection(srt_ip, srt_port, group_name, sei)
        if not test_result["success"]:
            logger.error(f"SRT connection test failed: {test_result}")
            clear_active_stream_ids(group_id)
            return jsonify({"error": "SRT connection test failed"}), 500
        
        # Build reliable FFmpeg command
        ffmpeg_cmd = build_reliable_ffmpeg_command(
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
            grid_rows=data.get("grid_rows", 2),
            grid_cols=data.get("grid_cols", 2),
            framerate=framerate,
            bitrate=bitrate,
            stream_ids=stream_ids
        )
        
        # Verify input files
        for video_file in video_files:
            file_path = os.path.join("uploads", video_file)
            if not os.path.exists(file_path):
                clear_active_stream_ids(group_id)
                return jsonify({"error": f"Video file not found: {video_file}"}), 400
        
        # Launch FFmpeg
        logger.info(" Launching reliable FFmpeg process...")
        process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        logger.info(f" FFmpeg started: PID {process.pid}")
        
        # Monitor startup
        streaming_detected = monitor_ffmpeg_startup(process, timeout=10)
        
        # Start background monitoring
        stream_config = {
            "stream_ids": stream_ids,
            "srt_port": srt_port,
            "group_name": group_name
        }
        
        monitor_thread = threading.Thread(
            target=stream_monitor,
            args=(process, group_id, group_name, stream_config),
            daemon=True
        )
        monitor_thread.start()
        logger.info("Background monitoring started")
        
        # Generate client URLs
        client_urls = generate_client_urls(srt_ip, srt_port, group_name, base_stream_id, stream_ids, screen_count)
        
        # Log the stream URLs for easy access
        logger.info("="*60)
        logger.info("STREAM URLs:")
        logger.info(f"Combined Stream: {client_urls['combined']}")
        for i in range(screen_count):
            screen_key = f"screen{i}"
            if screen_key in client_urls:
                logger.info(f"Screen {i}: {client_urls[screen_key]}")
        logger.info("="*60)
        
        # Resolve stream URLs for clients
        try:
            from blueprints.client_management.client_endpoints import resolve_stream_urls_for_group
            resolve_stream_urls_for_group(group_id, group_name)
        except ImportError:
            logger.warning("Could not resolve client stream URLs")
        
        return jsonify({
            "success": True,
            "message": f"Reliable multi-video streaming started for {group_name}",
            "process_id": process.pid,
            "group_id": group_id,
            "group_name": group_name,
            "stream_ids": stream_ids,
            "client_urls": client_urls,
            "streaming_detected": streaming_detected,
            "streams_created": screen_count + 1,
            "encoding": "faster preset, CRF 24, 30-frame keyframes"
        }), 200
        
    except Exception as e:
        logger.error(f"Error starting reliable streaming: {e}")
        if 'group_id' in locals():
            clear_active_stream_ids(group_id)
        return jsonify({"error": str(e)}), 500

@multi_stream_bp.route("/get_stream_urls/<group_id>", methods=["GET"])
def get_stream_urls(group_id: str):
    """Get stream URLs for a specific group"""
    try:
        from blueprints.docker_management import discover_groups
        discovery_result = discover_groups()
        
        if not discovery_result.get("success", False):
            return jsonify({"error": "Failed to discover groups"}), 500
        
        groups = discovery_result.get("groups", [])
        group = next((g for g in groups if g.get("id") == group_id), None)
        
        if not group:
            return jsonify({"error": f"Group '{group_id}' not found"}), 404
        
        group_name = group.get("name", group_id)
        
        # Get active stream IDs for this group
        from blueprints.streaming.stream_management import get_active_stream_ids
        stream_ids = get_active_stream_ids(group_id)
        
        if not stream_ids:
            return jsonify({"error": "No active streams found for this group"}), 404
        
        # Generate URLs
        srt_ip = "127.0.0.1"
        srt_port = 10080  # Default port
        base_stream_id = f"{group_id}_{int(time.time())}"
        
        client_urls = generate_client_urls(srt_ip, srt_port, group_name, base_stream_id, stream_ids, len(stream_ids))
        
        return jsonify({
            "success": True,
            "group_id": group_id,
            "group_name": group_name,
            "stream_urls": client_urls,
            "stream_ids": stream_ids
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting stream URLs: {e}")
        return jsonify({"error": str(e)}), 500

@multi_stream_bp.route("/all_streaming_statuses", methods=["GET"])
def all_streaming_statuses():
    """Get streaming status for all groups"""
    try:
        from blueprints.docker_management import discover_groups
        discovery_result = discover_groups()
        
        if not discovery_result.get("success", False):
            return jsonify({"error": "Failed to discover groups"}), 500
        
        groups = discovery_result.get("groups", [])
        streaming_statuses = {}
        all_ffmpeg_processes = get_all_ffmpeg_processes()
        
        for group in groups:
            group_id = group.get("id")
            group_name = group.get("name", group_id)
            container_id = group.get("container_id")
            
            if not container_id:
                continue
            
            group_processes = find_running_ffmpeg_for_group_strict(group_id, group_name, container_id)
            is_streaming = len(group_processes) > 0
            docker_running = group.get("docker_running", False)
            
            health_status = "HEALTHY" if docker_running and is_streaming else "UNHEALTHY" if docker_running else "OFFLINE"
            
            streaming_statuses[group_id] = {
                "group_name": group_name,
                "is_streaming": is_streaming,
                "process_count": len(group_processes),
                "docker_running": docker_running,
                "health_status": health_status,
                "processes": [
                    {
                        "pid": proc["pid"],
                        "uptime_seconds": time.time() - proc.get('create_time', time.time()),
                        "started_at": time.strftime('%Y-%m-%d %H:%M:%S', 
                                                   time.localtime(proc.get('create_time', 0)))
                    } for proc in group_processes
                ]
            }
        
        # Calculate summary
        active_streams = sum(1 for status in streaming_statuses.values() if status["is_streaming"])
        healthy_groups = sum(1 for status in streaming_statuses.values() if status["health_status"] == "HEALTHY")
        
        return jsonify({
            "streaming_statuses": streaming_statuses,
            "summary": {
                "total_groups": len(streaming_statuses),
                "active_streams": active_streams,
                "healthy_groups": healthy_groups,
                "total_ffmpeg_processes": len(all_ffmpeg_processes)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting streaming statuses: {e}")
        return jsonify({"error": str(e)}), 500

@multi_stream_bp.route("/stop_group_stream", methods=["POST", "OPTIONS"])
def stop_group_stream():
    """Stop streaming for a specific group"""
    if request.method == "OPTIONS":
        response = jsonify({"message": "OK"})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type")
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        return response
    
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
            clear_active_stream_ids(group_id)
            return jsonify({
                "message": f"No active streams found for group '{group_name}'",
                "status": "no_streams"
            }), 200
        
        stopped_count = stop_ffmpeg_processes(running_processes, group_name)
        clear_active_stream_ids(group_id)
        
        return jsonify({
            "message": f"Stopped {stopped_count} stream(s) for group '{group_name}'",
            "status": "stopped",
            "stopped_processes": stopped_count
        }), 200
        
    except Exception as e:
        logger.error(f"Error stopping group stream: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def cleanup_old_srs_containers(max_containers: int = 3):
    """Clean up old SRS containers"""
    try:
        cmd = ["docker", "ps", "-a", "--filter", "ancestor=ossrs/srs:5", "--format", "{{.ID}}\t{{.CreatedAt}}\t{{.Status}}"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0 or not result.stdout.strip():
            return 0
        
        lines = result.stdout.strip().split('\n')
        containers = []
        
        for line in lines:
            if line.strip():
                parts = line.split('\t')
                if len(parts) >= 3:
                    containers.append((parts[0], parts[1], parts[2]))
        
        if len(containers) <= max_containers:
            return 0
        
        containers.sort(key=lambda x: x[1], reverse=True)
        containers_to_remove = containers[max_containers:]
        
        removed_count = 0
        for container_id, _, status in containers_to_remove:
            try:
                if "Up" in status:
                    subprocess.run(["docker", "stop", container_id], capture_output=True, timeout=10)
                subprocess.run(["docker", "rm", container_id], capture_output=True, timeout=10)
                removed_count += 1
            except:
                continue
        
        return removed_count
    except:
        return 0

def discover_group_from_docker(group_id: str) -> Optional[Dict[str, Any]]:
    """Discover a specific group from Docker containers"""
    try:
        from blueprints.docker_management import discover_groups
        result = discover_groups()
        if result.get("success", False):
            groups = result.get("groups", [])
            for group in groups:
                if group.get("id") == group_id:
                    return group
        return None
    except Exception as e:
        logger.error(f"Error discovering group: {e}")
        return None

def find_running_ffmpeg_for_group_strict(group_id: str, group_name: str, container_id: str) -> List[Dict[str, Any]]:
    """Find running FFmpeg processes for a specific group"""
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
            try:
                if proc.info['name'] == 'ffmpeg':
                    cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                    
                    # Check for group identifiers
                    stream_path_pattern = f"live/{group_name}/"
                    if stream_path_pattern in cmdline or group_id in cmdline:
                        processes.append({
                            'pid': proc.info['pid'],
                            'cmdline': proc.info['cmdline'],
                            'create_time': proc.info['create_time']
                        })
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
                
        return processes
    except Exception as e:
        logger.error(f"Error finding FFmpeg processes: {e}")
        return []

def check_srt_port_simple(ip: str, port: int, timeout: float = 5.0) -> bool:
    """Simple SRT port check"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(1)
                sock.connect((ip, port))
                return True
        except:
            time.sleep(1)
    return False

def generate_stream_ids(base_stream_id: str, group_name: str, screen_count: int) -> Dict[str, str]:
    """Generate stream IDs for a group"""
    stream_ids = {"test": f"{base_stream_id[:8]}"}
    for i in range(screen_count):
        stream_ids[f"test{i}"] = f"{base_stream_id[:8]}_{i}"
    return stream_ids

def generate_client_urls(srt_ip: str, srt_port: int, group_name: str, base_stream_id: str, stream_ids: Dict[str, str], screen_count: int) -> Dict[str, str]:
    """Generate client URLs for streams"""
    client_urls = {
        "combined": f"srt://{srt_ip}:{srt_port}?streamid=#!::r=live/{group_name}/{base_stream_id},m=request,latency=5000000"
    }
    
    # Individual screen URLs
    for i in range(screen_count):
        screen_key = f"test{i}"
        stream_id = stream_ids.get(screen_key)
        if stream_id:
            client_urls[f"screen{i}"] = f"srt://{srt_ip}:{srt_port}?streamid=#!::r=live/{group_name}/{stream_id},m=request,latency=5000000"
    
    return client_urls

def monitor_ffmpeg_startup(process, timeout: int = 10) -> bool:
    """Monitor FFmpeg startup for streaming confirmation"""
    streaming_detected = False
    start_time = time.time()
    frame_count = 0
    
    logger.info(" Monitoring FFmpeg startup...")
    
    while time.time() - start_time < timeout:
        if process.poll() is not None:
            logger.error(f"FFmpeg process terminated unexpectedly (return code: {process.returncode})")
            return False
        
        try:
            if process.stdout and select.select([process.stdout], [], [], 0.5)[0]:
                output = process.stdout.readline()
                if output:
                    output = output.strip()
                    logger.debug(f"FFmpeg[{process.pid}]: {output}")
                    
                    # Check for streaming indicators
                    if "frame=" in output and "fps=" in output:
                        frame_count += 1
                        if not streaming_detected:
                            streaming_detected = True
                            logger.info(f" FFmpeg streaming started: {output}")
                        
                        # Consider startup successful after a few frames
                        if frame_count >= 3:
                            logger.info(" FFmpeg startup confirmed")
                            return True
                    
                    # Check for errors
                    if any(error in output.lower() for error in [
                        "error", "failed", "invalid", "not found", "permission denied",
                        "connection refused", "timeout", "unable to"
                    ]):
                        logger.error(f" FFmpeg error detected: {output}")
                        
        except Exception as e:
            logger.debug(f"Error reading FFmpeg output: {e}")
            break
    
    logger.warning(f" FFmpeg startup timeout after {timeout}s, frames: {frame_count}")
    return streaming_detected

def get_all_ffmpeg_processes() -> List[Dict[str, Any]]:
    """Get all running FFmpeg processes"""
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
            try:
                if proc.info['name'] == 'ffmpeg':
                    processes.append({
                        'pid': proc.info['pid'],
                        'cmdline': proc.info['cmdline'],
                        'create_time': proc.info['create_time']
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return processes
    except Exception as e:
        logger.error(f"Error getting FFmpeg processes: {e}")
        return []

def stop_ffmpeg_processes(processes: List[Dict[str, Any]], group_name: str) -> int:
    """Stop FFmpeg processes gracefully"""
    stopped_count = 0
    
    for proc_info in processes:
        try:
            pid = proc_info["pid"]
            logger.info(f" Stopping FFmpeg process {pid} for group '{group_name}'")
            
            # Send SIGTERM first for graceful shutdown
            os.kill(pid, 15)  # SIGTERM
            
            # Wait for graceful shutdown
            time.sleep(2)
            
            # Check if process is still running
            try:
                os.kill(pid, 0)  # Check if process exists
                logger.info(f"Process {pid} still running, sending SIGKILL")
                os.kill(pid, 9)  # SIGKILL
            except OSError:
                # Process already terminated
                pass
            
            stopped_count += 1
            logger.info(f" Successfully stopped FFmpeg process {pid}")
            
        except Exception as e:
            logger.error(f"Error stopping process {proc_info['pid']}: {e}")
    
    return stopped_count