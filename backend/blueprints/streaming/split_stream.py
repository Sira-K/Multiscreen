"""
Split-Screen Streaming Blueprint - Based on Multi-Stream
This module handles split-screen video streaming where a single video file
is split into multiple screen regions and streamed individually.
Uses the exact same reliable structure as multi-stream.
"""

import os
import time
import logging
import threading
import subprocess
import select
from typing import Dict, List, Any, Optional
from flask import Blueprint, request, jsonify

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
split_stream_bp = Blueprint('split_stream', __name__)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def generate_stream_ids(base_stream_id: str, group_name: str, screen_count: int) -> Dict[str, str]:
    """Generate unique stream IDs for each screen"""
    stream_ids = {}
    
    # Combined stream ID
    stream_ids["combined"] = f"split_{base_stream_id}"
    
    # Individual screen stream IDs
    for i in range(screen_count):
        screen_key = f"test{i}"
        stream_ids[screen_key] = f"screen{i}_{base_stream_id}"
    
    return stream_ids

def calculate_canvas_dimensions(orientation: str, screen_count: int, output_width: int, output_height: int, grid_rows: int = 2, grid_cols: int = 2) -> tuple:
    """Calculate canvas dimensions based on orientation"""
    if orientation.lower() == "horizontal":
        return output_width * screen_count, output_height
    elif orientation.lower() == "vertical":
        return output_width, output_height * screen_count
    else:  # grid
        return output_width * grid_cols, output_height * grid_rows

def calculate_position(index: int, orientation: str, output_width: int, output_height: int, grid_cols: int = 2) -> tuple:
    """Calculate position for each screen in the canvas"""
    if orientation.lower() == "horizontal":
        return index * output_width, 0
    elif orientation.lower() == "vertical":
        return 0, index * output_height
    else:  # grid
        row = index // grid_cols
        col = index % grid_cols
        return col * output_width, row * output_height

def build_split_screen_filter_complex(
    video_file: str, canvas_width: int, canvas_height: int,
    output_width: int, output_height: int, orientation: str, screen_count: int,
    grid_rows: int = 2, grid_cols: int = 2, framerate: int = 30
) -> str:
    """Build split-screen filter complex - single video split into multiple screens"""
    
    filter_parts = []
    
    # Scale the single input video to canvas size
    filter_parts.append(f"[0:v]scale={canvas_width}:{canvas_height}:force_original_aspect_ratio=increase,fps={framerate}[scaled]")
    
    # Split the scaled video for multiple outputs
    split_count = screen_count + 1  # +1 for combined
    split_outputs = ["[combined]"] + [f"[screen{i}_pre]" for i in range(screen_count)]
    filter_parts.append(f"[scaled]split={split_count}{''.join(split_outputs)}")
    
    # Create individual screen crops
    for i in range(screen_count):
        x_crop, y_crop = calculate_position(i, orientation, output_width, output_height, grid_cols)
        filter_parts.append(f"[screen{i}_pre]crop={output_width}:{output_height}:{x_crop}:{y_crop}[screen{i}]")
    
    return ";".join(filter_parts)

def build_split_screen_ffmpeg_command(
    video_file: str,
    canvas_width: int,
    canvas_height: int,
    output_width: int,
    output_height: int,
    screen_count: int,
    orientation: str,
    srt_ip: str,
    srt_port: int,
    group_name: str,
    base_stream_id: str,
    stream_ids: Dict[str, str],
    grid_rows: int = 2,
    grid_cols: int = 2,
    framerate: int = 30,
    bitrate: str = "3000k",
    sei: str = "681d5c8f-80cd-4847-930a-99b9484b4a32+000000"
) -> List[str]:
    """Build FFmpeg command for split-screen streaming - using multi-stream structure"""
    
    logger.info(f" Building split-screen FFmpeg command")
    logger.info(f"   Video: {video_file}, Screens: {screen_count}")
    logger.info(f"   Output: {output_width}x{output_height}, Orientation: {orientation}")
    
    # Use the exact same structure as multi-stream (which works)
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-v", "error",
        "-nostats",
        "-thread_queue_size", "512",
        "-avoid_negative_ts", "make_zero"
    ]
    
    # Add input (single video file)
    file_path = os.path.join("uploads", video_file)
    ffmpeg_cmd.extend([
        "-stream_loop", "-1",
        "-re",
        "-fflags", "+genpts",
        "-i", file_path
    ])
    
    # Build filter complex
    filter_complex = build_split_screen_filter_complex(
        video_file, canvas_width, canvas_height, output_width, output_height,
        orientation, screen_count, grid_rows, grid_cols, framerate
    )
    
    ffmpeg_cmd.extend(["-filter_complex", filter_complex])
    
    # Use the exact same encoding settings as multi-stream
    base_encoding = [
        "-c:v", "libx264",
        "-preset", "faster",
        "-crf", "24",
        "-g", "30",
        "-threads", "4",
        "-tune", "zerolatency",
        "-profile:v", "main",
        "-level", "4.0",
        "-pix_fmt", "yuv420p",
        "-r", str(framerate),
        "-maxrate", bitrate,
        "-bufsize", str(int(bitrate.rstrip('k')) * 1.5) + "k",
        "-f", "mpegts"
    ]
    
    # Add outputs using the same pattern as multi-stream
    # Combined stream
    combined_stream_path = f"live/{group_name}/{base_stream_id}"
    combined_url = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={combined_stream_path},m=publish"
    ffmpeg_cmd.extend(["-map", "[combined]"] + base_encoding + [combined_url])
    
    # Individual screen outputs
    for i in range(screen_count):
        screen_key = f"test{i}"
        individual_stream_id = stream_ids.get(screen_key, f"screen{i}_{base_stream_id}")
        stream_path = f"live/{group_name}/{individual_stream_id}"
        stream_url = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={stream_path},m=publish"
        ffmpeg_cmd.extend(["-map", f"[screen{i}]"] + base_encoding + [stream_url])
    
    logger.info(f"Built split-screen FFmpeg command with {len(ffmpeg_cmd)} arguments")
    logger.info(f"Filter chain: {filter_complex}")
    logger.info(f" Using 'faster' preset with 30-frame keyframes, 4 threads")
    logger.info(f" Resource optimization: 512 input queue, 4 encoding threads, CRF 24 quality")
    
    return ffmpeg_cmd

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

def generate_client_urls(srt_ip: str, srt_port: int, group_name: str, base_stream_id: str, stream_ids: Dict[str, str], screen_count: int) -> Dict[str, str]:
    """Generate client URLs for split-screen streaming"""
    client_urls = {}
    
    # Combined stream URL
    combined_stream_path = f"live/{group_name}/{base_stream_id}"
    client_urls["combined"] = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={combined_stream_path},m=request,latency=5000000"
    
    # Individual screen URLs
    for i in range(screen_count):
        screen_key = f"test{i}"
        individual_stream_id = stream_ids.get(screen_key, f"screen{i}_{base_stream_id}")
        individual_stream_path = f"live/{group_name}/{individual_stream_id}"
        client_urls[f"screen{i}"] = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={individual_stream_path},m=request,latency=5000000"
    
    return client_urls

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

def get_all_ffmpeg_processes() -> List[Dict[str, Any]]:
    """Get all running FFmpeg processes"""
    try:
        import psutil
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
    except ImportError:
        logger.warning("psutil not available, returning empty process list")
        return []
    except Exception as e:
        logger.error(f"Error getting FFmpeg processes: {e}")
        return []

# ============================================================================
# BACKGROUND MONITORING
# ============================================================================

def stream_monitor(process, group_id: str, group_name: str, stream_config: Dict[str, Any]):
    """Monitor streaming process in background"""
    logger.info(f" Starting stream monitor for {group_name} (PID: {process.pid})")
    
    try:
        while process.poll() is None:
            time.sleep(10)
            # Process is still running
            logger.debug(f"Stream {group_name} (PID: {process.pid}) is still running")
        
        logger.warning(f"Stream {group_name} (PID: {process.pid}) terminated with code {process.returncode}")
        
    except Exception as e:
        logger.error(f"Error monitoring stream {group_name}: {e}")

def discover_group_from_docker(group_id: str) -> Optional[Dict[str, Any]]:
    """Discover group information from Docker"""
    try:
        from ..docker_management import discover_groups
        
        discovery_result = discover_groups()
        if discovery_result.get("success", False):
            for group in discovery_result.get("groups", []):
                if group.get("id") == group_id:
                    logger.info(f"Found group: '{group.get('name', group_id)}'")
                    logger.info(f"Docker container status: {'Running' if group.get('docker_running') else 'Stopped'}")
                    return group
        
        logger.error(f"Group '{group_id}' not found in Docker discovery")
        return None
        
    except ImportError as e:
        logger.error(f"Docker management not available: {e}")
        return None
    except Exception as e:
        logger.error(f"Error discovering group: {e}")
        return None

def get_active_stream_ids(group_id: str) -> Dict[str, str]:
    """Get active stream IDs for a group"""
    try:
        from .stream_management import get_active_stream_ids
        return get_active_stream_ids(group_id)
    except ImportError:
        logger.warning("stream_management not available, returning empty stream IDs")
        return {}

# ============================================================================
# FLASK ROUTE HANDLERS
# ============================================================================

@split_stream_bp.route("/start_split_screen_srt", methods=["POST"])
def start_split_screen_srt():
    """
    Start split-screen SRT streaming - using multi-stream structure
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
        
        video_file = data.get("video_file")
        if not video_file:
            return jsonify({"error": "video_file is required"}), 400
        
        logger.info("="*60)
        logger.info(f"STARTING SPLIT-SCREEN STREAM: {group_id} -> {video_file}")
        logger.info("="*60)
        
        # Discover group from Docker
        group = discover_group_from_docker(group_id)
        if not group:
            return jsonify({"error": f"Group '{group_id}' not found"}), 404
        
        # Get configuration
        group_name = group.get("name", group_id)
        screen_count = data.get("screen_count", group.get("screen_count", 2))
        orientation = data.get("orientation", group.get("orientation", "horizontal"))
        output_width = data.get("output_width", 1920)
        output_height = data.get("output_height", 1080)
        grid_rows = data.get("grid_rows", 2)
        grid_cols = data.get("grid_cols", 2)
        
        logger.info(f"Config: {screen_count} screens, {orientation}, {output_width}x{output_height}, Grid: {grid_rows}x{grid_cols}")
        
        # Get streaming parameters
        ports = group.get("ports", {})
        srt_ip = data.get("srt_ip", "127.0.0.1")  # Use localhost for server-side
        
        logger.info(f"Using SRT IP: {srt_ip}")
        
        # Get SRT port - use external Docker port for publishing (like multi-stream)
        srt_port = data.get("srt_port")
        logger.info(f"SRT port from request data: {srt_port}")
        
        if not srt_port:
            srt_port = ports.get("srt_port")
            logger.info(f"SRT port from Docker discovery: {srt_port}")
            if not srt_port:
                return jsonify({
                    "error": "No SRT port available for this group. Docker container may not be properly configured.",
                    "group_ports": ports
                }), 500
        
        # Force the correct port - this is the key fix!
        logger.info(f"Final SRT port for publishing: {srt_port}")
        logger.info(f"Group ports from Docker: {ports}")
        
        # Ensure we're using the external Docker port (not internal)
        if srt_port == 10080:
            logger.warning(f"Detected internal port 10080, forcing to external port from Docker discovery")
            srt_port = ports.get("srt_port")
            logger.info(f"Corrected SRT port: {srt_port}")
        
        # Get encoding parameters
        framerate = data.get("framerate", 30)
        bitrate = data.get("bitrate", "3000k")
        sei = data.get("sei", "681d5c8f-80cd-4847-930a-99b9484b4a32+000000")
        
        # Calculate canvas dimensions
        if orientation.lower() == "horizontal":
            canvas_width = output_width * screen_count
            canvas_height = output_height
        elif orientation.lower() == "vertical":
            canvas_width = output_width
            canvas_height = output_height * screen_count
        else:  # grid
            canvas_width = output_width * grid_cols
            canvas_height = output_height * grid_rows
        
        logger.info(f"Canvas dimensions: {canvas_width}x{canvas_height}")
        
        # Generate stream IDs
        base_stream_id = group_id  # Use full group ID like client management
        stream_ids = generate_stream_ids(base_stream_id, group_name, screen_count)
        
        # Verify video file exists and get full path
        file_path = os.path.join("uploads", video_file)
        if not os.path.exists(file_path):
            logger.error(f"Video file not found: {file_path}")
            return jsonify({"error": f"Video file not found: {video_file}"}), 404
        
        # Get absolute path to avoid any working directory issues
        abs_file_path = os.path.abspath(file_path)
        file_size = os.path.getsize(abs_file_path)
        logger.info(f"Video file verified: {abs_file_path}")
        logger.info(f"   Size: {file_size} bytes ({file_size / (1024*1024):.1f} MB)")
        logger.info(f"   Working directory: {os.getcwd()}")
        
        # Test if FFmpeg can read the video file
        try:
            test_cmd = ["ffmpeg", "-i", abs_file_path, "-f", "null", "-", "-v", "quiet"]
            result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                logger.info("   FFmpeg can read video file successfully")
            else:
                logger.error(f"   FFmpeg cannot read video file: {result.stderr}")
                return jsonify({"error": f"FFmpeg cannot read video file: {result.stderr}"}), 400
        except Exception as e:
            logger.error(f"   Error testing video file with FFmpeg: {e}")
            return jsonify({"error": f"Error testing video file: {e}"}), 400
        
        # Build FFmpeg command
        logger.info(f"Building FFmpeg command with srt_ip={srt_ip}, srt_port={srt_port}")
        ffmpeg_cmd = build_split_screen_ffmpeg_command(
            abs_file_path, canvas_width, canvas_height, output_width, output_height,
            screen_count, orientation, srt_ip, srt_port, group_name, base_stream_id,
            stream_ids, grid_rows, grid_cols, framerate, bitrate, sei
        )
        
        # Launch FFmpeg using reliable approach from multi_stream.py
        logger.info(" Launching reliable FFmpeg process...")
        process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
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
        # Use external port for client URLs (Docker port mapping)
        external_srt_port = ports.get("srt_port")  # Get external port from Docker
        
        # Use external IP for client URLs (clients need to connect to external IP)
        external_srt_ip = "128.205.39.64"  # External IP for client connections
        client_urls = generate_client_urls(external_srt_ip, external_srt_port, group_name, base_stream_id, stream_ids, screen_count)
        
        # Generate client stream URLs - matching multi-stream format exactly
        client_stream_urls = {}
        
        # Use external port for client URLs (Docker port mapping)
        external_srt_port = ports.get("srt_port")  # Get external port from Docker
        
        # Use external IP for client URLs (clients need to connect to external IP)
        external_srt_ip = "128.205.39.64"  # External IP for client connections
        
        # Combined stream URL - same format as multi-stream
        combined_stream_path = f"live/{group_name}/{base_stream_id}"
        client_stream_urls["combined"] = f"srt://{external_srt_ip}:{external_srt_port}?streamid=#!::r={combined_stream_path},m=request,latency=5000000"
        
        # Individual screen URLs - same format as multi-stream
        for i in range(screen_count):
            screen_key = f"test{i}"
            individual_stream_id = stream_ids.get(screen_key, f"screen{i}_{base_stream_id}")
            individual_stream_path = f"live/{group_name}/{individual_stream_id}"
            client_stream_urls[f"screen{i}"] = f"srt://{external_srt_ip}:{external_srt_port}?streamid=#!::r={individual_stream_path},m=request,latency=5000000"
        
        # Log the stream URLs for easy access
        logger.info("="*60)
        logger.info("STREAM URLs:")
        logger.info(f"Combined Stream: {client_stream_urls['combined']}")
        for i in range(screen_count):
            logger.info(f"Screen {i}: {client_stream_urls[f'screen{i}']}")
        logger.info("="*60)
        
        # Build response
        combined_stream_path = f"live/{group_name}/split_{base_stream_id}"
        crop_info = []
        
        for i in range(screen_count):
            x_pos, y_pos = calculate_position(i, orientation, output_width, output_height, grid_cols)
            crop_info.append({
                "screen": i,
                "position": {"x": x_pos, "y": y_pos},
                "dimensions": {"width": output_width, "height": output_height}
            })
        
        # Test SRT connection
        try:
            from .client_utils import check_srt_port_simple
            test_result = "success" if check_srt_port_simple(srt_ip, srt_port) else "failed"
        except ImportError:
            test_result = "unknown"
        
        logger.info("="*60)
        logger.info(f"SPLIT-SCREEN STREAM STARTED SUCCESSFULLY")
        logger.info(f"Group: {group_name}")
        logger.info(f"Process ID: {process.pid}")
        logger.info(f"Streaming: {'Yes' if streaming_detected else 'No'}")
        logger.info("="*60)
        
        return jsonify({
            "success": True,
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
                "persistent_streams": stream_ids,
                "crop_information": crop_info
            },
            "status": "active",
            "test_result": test_result,
            "client_urls": client_urls,
            "streaming_detected": streaming_detected,
            "streams_created": screen_count + 1,
            "encoding": f"faster preset, CRF 24, 30-frame keyframes, 4 threads",
            "stream_ids": stream_ids
        }), 200
        
    except Exception as e:
        logger.error(f"Error starting split-screen stream: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@split_stream_bp.route("/get_stream_urls/<group_id>", methods=["GET"])
def get_stream_urls(group_id: str):
    """Get stream URLs for a specific group"""
    try:
        from ..docker_management import discover_groups
        discovery_result = discover_groups()
        
        if not discovery_result.get("success", False):
            return jsonify({"error": "Failed to discover groups"}), 500
        
        groups = discovery_result.get("groups", [])
        group = next((g for g in groups if g.get("id") == group_id), None)
        
        if not group:
            return jsonify({"error": f"Group '{group_id}' not found"}), 404
        
        group_name = group.get("name", group_id)
        
        # Get active stream IDs for this group
        from .stream_management import get_active_stream_ids
        stream_ids = get_active_stream_ids(group_id)
        
        if not stream_ids:
            return jsonify({"error": "No active streams found for this group"}), 404
        
        # Generate URLs
        srt_ip = "127.0.0.1"  # Use localhost like multi-stream
        srt_port = group.get("ports", {}).get("srt_port")  # Get port from Docker discovery
        if not srt_port:
            return jsonify({"error": "No SRT port available for this group"}), 500
        base_stream_id = group_id  # Use full group ID like client management
        
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

@split_stream_bp.route("/all_streaming_statuses", methods=["GET"])
def all_streaming_statuses():
    """Get streaming status for all groups"""
    try:
        from ..docker_management import discover_groups
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

            # For now, just check if there are any FFmpeg processes
            # In a real implementation, you'd want to match processes to groups
            group_processes = [p for p in all_ffmpeg_processes if group_name in str(p.get('cmdline', ''))]
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

# ============================================================================
# UTILITY FUNCTIONS FOR OTHER MODULES
# ============================================================================

def find_running_ffmpeg_for_group_strict(group_id: str, group_name: str, container_id: str) -> List[Dict[str, Any]]:
    """Find running FFmpeg processes for a specific group"""
    try:
        all_processes = get_all_ffmpeg_processes()
        group_processes = []
        
        for proc in all_processes:
            cmdline = ' '.join(proc.get('cmdline', []))
            if group_name in cmdline or group_id in cmdline:
                group_processes.append(proc)
        
        return group_processes
    except Exception as e:
        logger.error(f"Error finding FFmpeg processes for group {group_name}: {e}")
        return []

def stop_group_streams(group_id: str, group_name: str) -> bool:
    """Stop all streaming processes for a group"""
    try:
        processes = find_running_ffmpeg_for_group_strict(group_id, group_name, None)
        stopped_count = 0
        
        for proc in processes:
            try:
                pid = proc["pid"]
                logger.info(f"Stopping FFmpeg process {pid} for group {group_name}")
                os.kill(pid, 15)  # SIGTERM
                stopped_count += 1
            except Exception as e:
                logger.error(f"Error stopping process {proc.get('pid')}: {e}")
        
        logger.info(f"Stopped {stopped_count} streaming processes for group {group_name}")
        return stopped_count > 0
        
    except Exception as e:
        logger.error(f"Error stopping group streams: {e}")
        return False