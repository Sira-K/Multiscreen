"""
Split-Screen Streaming Blueprint

This module handles split-screen video streaming where a single video file
is split into multiple screen regions and streamed individually.
"""

import os
import time
import logging
import threading
import subprocess
import select
import socket
from typing import Dict, Any, List, Optional
from flask import Blueprint, request, jsonify

import psutil

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
split_stream_bp = Blueprint('split_stream', __name__)

# ============================================================================
# CONFIGURATION CONSTANTS
# ============================================================================

# Memory optimization settings
MAX_LOG_LINES = 1000
MEMORY_OPTIMIZATION = {
    "thread_queue_size": 512,
    "max_muxing_queue_size": 1024,
    "warning_threshold": 2000,  # MB
    "critical_threshold": 4000,  # MB
}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def find_ffmpeg_executable() -> str:
    """Find FFmpeg executable in system PATH"""
    try:
        result = subprocess.run(['which', 'ffmpeg'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    
    # Fallback to common locations
    common_paths = ['/usr/bin/ffmpeg', '/usr/local/bin/ffmpeg', '/opt/ffmpeg/bin/ffmpeg']
    for path in common_paths:
        if os.path.exists(path):
            return path
    
    return 'ffmpeg'  # Hope it's in PATH

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
    canvas_width: int, canvas_height: int,
    output_width: int, output_height: int, 
    orientation: str, screen_count: int,
    grid_rows: int = 2, grid_cols: int = 2
) -> str:
    """Build filter complex for split-screen layout - proper canvas-based approach"""
    
    if screen_count == 2 and orientation.lower() == "horizontal":
        # Horizontal split: expand video to completely fill canvas, then crop portions
        # This creates a "zoomed in" effect where each screen shows a different part
        filter_complex = (
            f"[0:v]scale={canvas_width}:{canvas_height}:force_original_aspect_ratio=increase[scaled];"
            f"[scaled]split=3[combined][copy0][copy1];"
            f"[copy0]crop={output_width}:{output_height}:0:0[screen0];"
            f"[copy1]crop={output_width}:{output_height}:{output_width}:0[screen1]"
        )
    elif screen_count == 2 and orientation.lower() == "vertical":
        # Vertical split: expand video to completely fill canvas, then crop portions
        filter_complex = (
            f"[0:v]scale={canvas_width}:{canvas_height}:force_original_aspect_ratio=increase[scaled];"
            f"[scaled]split=3[combined][copy0][copy1];"
            f"[copy0]crop={output_width}:{output_height}:0:0[screen0];"
            f"[copy1]crop={output_width}:{output_height}:0:{output_height}[screen1]"
        )
    elif orientation.lower() == "grid":
        # Grid layout: expand video to completely fill canvas, then crop portions
        filter_parts = [
            f"[0:v]scale={canvas_width}:{canvas_height}:force_original_aspect_ratio=increase[scaled]",
            f"[scaled]split={screen_count + 1}[combined]" + "".join([f"[copy{i}]" for i in range(screen_count)])
        ]
        
        for i in range(screen_count):
            x_pos, y_pos = calculate_position(i, orientation, output_width, output_height, grid_cols)
            filter_parts.append(f"[copy{i}]crop={output_width}:{output_height}:{x_pos}:{y_pos}[screen{i}]")
        
        filter_complex = ";".join(filter_parts)
    else:
        # Fallback: simple split without positioning
        filter_parts = [f"[0:v]split={screen_count + 1}[full]" + "".join([f"[copy{i}]" for i in range(screen_count)])]
        
        for i in range(screen_count):
            filter_parts.append(f"[copy{i}]scale={output_width}:{output_height}[screen{i}]")
        
        filter_complex = ",".join(filter_parts)
    
    return filter_complex

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
    
    # Use the exact same structure as multi-stream (which works)
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-v", "error",
        "-nostats",
        "-thread_queue_size", "512",
        "-avoid_negative_ts", "make_zero"
    ]
    
    # Add input (single video file)
    ffmpeg_cmd.extend([
        "-stream_loop", "-1",
        "-re",
        "-fflags", "+genpts",
        "-i", video_file
    ])
    
    # Build filter complex
    filter_complex = build_split_screen_filter_complex(
        canvas_width, canvas_height, output_width, output_height,
        orientation, screen_count, grid_rows, grid_cols
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
    """Generate client URLs for streams - matching multi-stream format exactly"""
    client_urls = {
        "combined": f"srt://{srt_ip}:{srt_port}?streamid=#!::r=live/{group_name}/{base_stream_id},m=request,latency=5000000"
    }
    
    # Individual screen URLs - same format as multi-stream
    for i in range(screen_count):
        screen_key = f"test{i}"
        stream_id = stream_ids.get(screen_key)
        if stream_id:
            client_urls[f"screen{i}"] = f"srt://{srt_ip}:{srt_port}?streamid=#!::r=live/{group_name}/{stream_id},m=request,latency=5000000"

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
        
        # Get memory thresholds from config if available
        try:
            MAX_MEMORY_MB = MEMORY_OPTIMIZATION.get("warning_threshold", 2000)
            CRITICAL_MEMORY_MB = MEMORY_OPTIMIZATION.get("critical_threshold", 4000)
        except NameError:
            MAX_MEMORY_MB = 2000
            CRITICAL_MEMORY_MB = 4000
        
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
                            if memory_mb > CRITICAL_MEMORY_MB:
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

# ============================================================================
# FLASK ROUTES
# ============================================================================

@split_stream_bp.route("/start_split_screen_srt", methods=["POST"])
def start_split_screen_srt():
    """Take one video file and split it across multiple screens"""
    try:
        # Clean up old containers first
        cleanup_count = cleanup_old_srs_containers(max_containers=3)
        if cleanup_count > 0:
            logger.info(f" Cleaned up {cleanup_count} old containers")
        
        data = request.get_json() or {}
        
        group_id = data.get("group_id")
        video_file = data.get("video_file")
        
        logger.info("="*60)
        logger.info(f"STARTING SPLIT-SCREEN STREAM: {group_id} -> {video_file}")
        logger.info("="*60)
        
        if not group_id or not video_file:
            logger.error("Missing required parameters: group_id or video_file")
            return jsonify({"error": "group_id and video_file are required"}), 400
        
        # Discover group
        logger.info(f"Discovering group '{group_id}' from Docker...")
        try:
            from blueprints.docker_management import discover_groups
            result = discover_groups()
            if result.get("success", False):
                groups = result.get("groups", [])
                group = next((g for g in groups if g.get("id") == group_id), None)
            else:
                group = None
        except ImportError:
            group = None
        
        if not group:
            logger.error(f"Group '{group_id}' not found in Docker")
            return jsonify({"error": f"Group '{group_id}' not found"}), 404

        group_name = group.get("name", group_id)
        logger.info(f"Found group: '{group_name}'")
        
        # Check Docker status
        docker_running = group.get("docker_running", False)
        logger.info(f"Docker container status: {'Running' if docker_running else 'Stopped'}")
        
        if not docker_running:
            logger.error(f"Docker container for group '{group_name}' is not running")
            return jsonify({"error": f"Docker container for group '{group_name}' is not running"}), 400
        
        # Configuration
        screen_count = data.get("screen_count", group.get("screen_count", 2))
        orientation = data.get("orientation", group.get("orientation", "horizontal"))
        output_width = data.get("output_width", 1920)
        output_height = data.get("output_height", 1080)
        grid_rows = data.get("grid_rows", 2)
        grid_cols = data.get("grid_cols", 2)
        
        logger.info(f"Config: {screen_count} screens, {orientation}, {output_width}x{output_height}, Grid: {grid_rows}x{grid_cols}")

        # Get streaming parameters
        ports = group.get("ports", {})
        srt_ip = data.get("srt_ip", "127.0.0.1")
        
        logger.info(f"Using SRT IP: {srt_ip}")
        
        srt_port = data.get("srt_port")
        if not srt_port:
            srt_port = ports.get("srt_port")
            if not srt_port:
                return jsonify({
                    "error": "No SRT port available for this group. Docker container may not be properly configured.",
                    "group_ports": ports
                }), 500
            
            external_srt_port = srt_port
            logger.info(f"Port mapping: {external_srt_port}->10080, Publishing: {srt_ip}:{external_srt_port}")
            srt_port = external_srt_port
        else:
            logger.info(f"SRT port provided: {srt_port} (external Docker port)")
        
        # Get encoding parameters
        framerate = data.get("framerate", 30)
        bitrate = data.get("bitrate", "3000k")
        sei = data.get("sei", "681d5c8f-80cd-4847-930a-99b9484b4a32+000000")
        
        # Optimize bitrate based on screen count (matching multi_stream.py approach)
        if isinstance(bitrate, str) and bitrate.endswith('k'):
            base_bitrate = int(bitrate.rstrip('k'))
            # Adjust bitrate based on screen count for better resource management
            if screen_count > 4:
                optimized_bitrate = max(base_bitrate // 2, 1000)  # Reduce for high screen counts
            elif screen_count > 2:
                optimized_bitrate = int(base_bitrate * 0.8)  # Slight reduction for medium screen counts
            else:
                optimized_bitrate = base_bitrate  # Keep original for low screen counts
            
            bitrate = f"{optimized_bitrate}k"
            logger.info(f"Bitrate optimization: {base_bitrate}k -> {bitrate} for {screen_count} screens")
        
        # Optimize thread count based on screen count
        optimal_threads = min(screen_count * 2, 8)  # 2 threads per screen, max 8
        logger.info(f"Thread optimization: {optimal_threads} threads for {screen_count} screens")
        
        # Get memory optimization settings
        try:
            from streaming_config import MEMORY_OPTIMIZATION, get_encoding_preset, check_memory_usage
            memory_info = check_memory_usage()
            if memory_info:
                available_gb = memory_info["available_gb"]
                encoding_preset = get_encoding_preset(available_gb)
                logger.info(f"Memory optimization: {available_gb:.1f}GB available, using {encoding_preset['preset']} preset")
            else:
                encoding_preset = {"preset": "faster", "tune": "zerolatency", "g": "30", "bf": "0", "refs": "2"}
                logger.info("Using default encoding preset for memory optimization")
        except ImportError:
            encoding_preset = {"preset": "faster", "tune": "zerolatency", "g": "30", "bf": "0", "refs": "2"}
            logger.info("Using fallback encoding preset (streaming_config.py not available)")
        
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
        base_stream_id = f"{group_id}_{int(time.time())}"
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
        
        # Test a simple filter complex to isolate the issue
        try:
            simple_test_cmd = ["ffmpeg", "-i", abs_file_path, "-vf", "scale=1920:1080", "-frames:v", "1", "-f", "null", "-", "-v", "quiet"]
            result = subprocess.run(simple_test_cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                logger.info("   Simple filter test passed")
            else:
                logger.error(f"   Simple filter test failed: {result.stderr}")
        except Exception as e:
            logger.error(f"   Error testing simple filter: {e}")
        
        # Test the exact filter complex we're going to use
        try:
            test_filter = "[0:v]scale=3840:1080:force_original_aspect_ratio=increase[scaled];[scaled]split=3[combined][copy0][copy1];[copy0]crop=1920:1080:0:0[screen0];[copy1]crop=1920:1080:1920:0[screen1]"
            test_cmd = ["ffmpeg", "-i", abs_file_path, "-filter_complex", f'"{test_filter}"', "-map", "[combined]", "-frames:v", "1", "-f", "null", "-", "-v", "quiet"]
            result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                logger.info("   Complex filter test passed")
            else:
                logger.error(f"   Complex filter test failed: {result.stderr}")
                logger.error(f"   Command was: {' '.join(test_cmd)}")
        except Exception as e:
            logger.error(f"   Error testing complex filter: {e}")
        
        # Build FFmpeg command
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
        client_urls = generate_client_urls(srt_ip, srt_port, group_name, base_stream_id, stream_ids, screen_count)
        
        # Generate client stream URLs - matching multi-stream format exactly
        client_stream_urls = {}
        external_srt_ip = "127.0.0.1"  # Local IP for testing
        external_srt_port = srt_port
        
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
        test_result = "success" if check_srt_port_simple(srt_ip, srt_port) else "failed"
        
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
            "encoding": f"{encoding_preset['preset']} preset, CRF 24, {encoding_preset['g']}-frame keyframes, {optimal_threads} threads",
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

@split_stream_bp.route("/all_streaming_statuses", methods=["GET"])
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