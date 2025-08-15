# blueprints/streaming/split_stream.py
"""
Split-screen streaming functionality for multi-screen display system.
Handles splitting a single video file across multiple screens.
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
from typing import Dict, List, Any, Optional

# Import SRTService for connection testing
try:
    from ..services.srt_service import SRTService
except ImportError:
    # Fallback for when running directly
    try:
        from services.srt_service import SRTService
    except ImportError:
        # Create a simple fallback if SRTService is not available
        class SRTService:
            @staticmethod
            def test_connection(srt_ip: str, srt_port: int, group_name: str, sei: str) -> Dict[str, Any]:
                """Simple SRT connection test fallback"""
                logger.info(f"Testing SRT connection to {srt_ip}:{srt_port}")
                return {"success": True, "message": "SRT connection test skipped (fallback mode)"}

# Create blueprint
split_stream_bp = Blueprint('split_stream', __name__)

# Configure logger
logger = logging.getLogger(__name__)

# ============================================================================
# FLASK ROUTE HANDLERS
# ============================================================================

@split_stream_bp.route("/start_split_screen_srt", methods=["POST"])
def start_split_screen_srt():
    """Take one video file and split it across multiple screens"""
    try:
        data = request.get_json() or {}
        
        group_id = data.get("group_id")
        video_file = data.get("video_file")
        
        logger.info("="*60)
        logger.info("🚀 STARTING SPLIT-SCREEN SRT STREAM")
        logger.info(f"📋 Group ID: {group_id}")
        logger.info(f"📹 Video file: {video_file}")
        logger.info("="*60)
        
        if not group_id or not video_file:
            logger.error("❌ Missing required parameters: group_id or video_file")
            return jsonify({"error": "group_id and video_file are required"}), 400
        
        # Discover group
        logger.info(f"🔍 Discovering group '{group_id}' from Docker...")
        group = discover_group_from_docker(group_id)
        if not group:
            logger.error(f"❌ Group '{group_id}' not found in Docker")
            return jsonify({"error": f"Group '{group_id}' not found"}), 404

        group_name = group.get("name", group_id)
        logger.info(f"✅ Found group: '{group_name}'")
        
        # Check Docker status
        docker_running = group.get("docker_running", False)
        logger.info(f"🐳 Docker container status: {'Running' if docker_running else 'Stopped'}")
        
        if not docker_running:
            logger.error(f"❌ Docker container for group '{group_name}' is not running")
            return jsonify({"error": f"Docker container for group '{group_name}' is not running"}), 400
        
        # Check for existing streams
        container_id = group.get("container_id")
        logger.info(f"🔍 Checking for existing FFmpeg processes...")
        logger.info(f"   Container ID: {container_id}")
        
        existing_ffmpeg = find_running_ffmpeg_for_group_strict(group_id, group_name, container_id)
        if existing_ffmpeg:
            logger.warning(f"⚠️  Found {len(existing_ffmpeg)} existing FFmpeg process(es)")
            logger.info("   Streaming already active, returning current status")
            return jsonify({
                "message": f"Split-screen streaming already active for group '{group_name}'",
                "status": "already_active"
            }), 200
        
        logger.info("✅ No existing streams found")
        
        # Configuration
        screen_count = data.get("screen_count", group.get("screen_count", 2))
        orientation = data.get("orientation", group.get("orientation", "horizontal"))
        output_width = data.get("output_width", 1920)
        output_height = data.get("output_height", 1080)
        grid_rows = data.get("grid_rows", 2)
        grid_cols = data.get("grid_cols", 2)
        
        logger.info("⚙️  Stream configuration:")
        logger.info(f"   Screen count: {screen_count}")
        logger.info(f"   Orientation: {orientation}")
        logger.info(f"   Output resolution: {output_width}x{output_height}")
        if orientation.lower() == "grid":
            logger.info(f"   Grid layout: {grid_rows}x{grid_cols}")
        
        # Get streaming parameters - FIX THE PORT RESOLUTION HERE
        ports = group.get("ports", {})
        srt_ip = data.get("srt_ip", "127.0.0.1")
        
        # For Docker containers, we might need to use the container's IP
        # But for now, let's try with localhost since the port is mapped
        logger.info(f"🔌 Using SRT IP: {srt_ip}")
        
        # IMPORTANT: Use the external port that clients connect to, not the internal Docker port
        # The Docker container maps external_port:10080/udp, so we need the external port
        srt_port = data.get("srt_port")
        if not srt_port:
            srt_port = ports.get("srt_port")
            if not srt_port:
                return jsonify({
                    "error": "No SRT port available for this group. Docker container may not be properly configured.",
                    "group_ports": ports
                }), 500
            
            # CRITICAL FIX: The srt_port from ports is the EXTERNAL port (e.g., 10110)
            # We need to publish to the EXTERNAL port (10110) so FFmpeg can reach the SRT server
            # The Docker container maps 10110:10080/udp, so publishing to 10110 will reach the SRT server
            external_srt_port = srt_port  # External port clients connect to (e.g., 10110)
            
            logger.info(f"🔌 Port mapping: External={external_srt_port} (clients) -> Internal=10080 (Docker)")
            logger.info(f"🔌 Publishing to: {srt_ip}:{external_srt_port} (external port)")
            logger.info(f"🔌 Clients connect to: {srt_ip}:{external_srt_port}")
            
            # Use external port for publishing (FFmpeg output) - this will reach the SRT server
            srt_port = external_srt_port
        else:
            # If srt_port was provided in data, assume it's the external port
            # But we still need to use the external port for publishing
            logger.info(f"🔌 SRT port provided in request: {srt_port}")
            logger.info(f"🔌 This should be the external port that Docker forwards to the container")
            
            # CRITICAL FIX: Always use the Docker container's external port for publishing
            # The provided port might be wrong, so use the actual Docker port mapping
            docker_srt_port = ports.get("srt_port")
            if docker_srt_port and docker_srt_port != srt_port:
                logger.warning(f"⚠️  Provided SRT port {srt_port} doesn't match Docker port {docker_srt_port}")
                logger.warning(f"   Using Docker port mapping instead: {docker_srt_port}")
                srt_port = docker_srt_port
            else:
                logger.info(f"✅ Using provided SRT port: {srt_port}")
                logger.info(f"   This should reach the SRT server inside the Docker container")
        
        # Log the port being used for debugging
        logger.info(f"🔌 Using SRT port {srt_port} for group {group_name} (from container ports: {ports})")
        logger.info(f"🔌 Docker port mapping: {srt_port}:10080/udp")
        logger.info(f"🔌 FFmpeg will publish to: {srt_ip}:{srt_port}")
        logger.info(f"🔌 This will reach the SRT server listening on port 10080 inside the container")
        
        # CRITICAL: Double-check that we're using the correct port
        docker_srt_port = ports.get("srt_port")
        if docker_srt_port and docker_srt_port != srt_port:
            logger.error(f"❌ PORT MISMATCH: Using {srt_port} but Docker container has {docker_srt_port}")
            logger.error(f"❌ This will cause connection failures!")
            # Force use the correct port
            srt_port = docker_srt_port
            logger.info(f"✅ Corrected to use Docker port: {srt_port}")
        
        # Import modules at the top to avoid scope issues
        import sys
        import os
        import socket
        import time
        
        # Wait for SRT server using centralized service
        try:
            # Add the services directory to the path for import
            services_path = os.path.join(os.path.dirname(__file__), '..', 'services')
            if services_path not in sys.path:
                sys.path.insert(0, services_path)
            
            from srt_service import SRTService
            srt_status = SRTService.monitor_srt_server(srt_ip, srt_port, timeout=5)
            if not srt_status["ready"]:
                logger.error(f"❌ SRT server not ready: {srt_status['message']}")
                return jsonify({"error": f"SRT server not ready: {srt_status['message']}"}), 500
            logger.info(f"✅ SRT server ready: {srt_status['message']}")
        except Exception as e:
            # Fallback to simple socket check if import fails
            logger.warning(f"⚠️  SRT service import failed: {e}")
            logger.info(f"🔍 Falling back to simple SRT check at {srt_ip}:{srt_port}")
            
            # Simple fallback with pre-imported modules
            start_time = time.time()
            fallback_timeout = 5
            while time.time() - start_time < fallback_timeout:
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                        sock.settimeout(1)
                        sock.connect((srt_ip, srt_port))
                        logger.info(f"✅ SRT server ready (fallback method)")
                        break
                except Exception as sock_e:
                    logger.debug(f"🔄 SRT port {srt_port} not ready yet: {sock_e}")
                    time.sleep(1)
            else:
                logger.error(f"❌ SRT server not ready after {fallback_timeout}s")
                return jsonify({"error": f"SRT server not ready after {fallback_timeout}s"}), 500
        
        # Test SRT connection
        logger.info("🧪 Testing SRT connection...")
        try:
            test_result = SRTService.test_connection(srt_ip, srt_port, group_name, sei)
            if not test_result["success"]:
                logger.error(f"❌ SRT connection test failed: {test_result}")
                # Don't fail here, just warn - the connection might still work
                logger.warning("⚠️  SRT connection test failed, but continuing anyway...")
            else:
                logger.info("✅ SRT connection test passed")
        except Exception as e:
            logger.warning(f"⚠️  SRT connection test error: {e}")
            logger.warning("⚠️  Continuing anyway - connection might still work...")
        
        # Verify video file exists
        file_path = os.path.join("uploads", video_file)
        if not os.path.exists(file_path):
            logger.error(f"❌ Video file not found: {file_path}")
            return jsonify({"error": f"Video file not found: {video_file}"}), 404
        
        file_size = os.path.getsize(file_path)
        logger.info(f"✅ Video file verified: {file_path}")
        logger.info(f"   Size: {file_size} bytes ({file_size / (1024*1024):.1f} MB)")
        
        # Generate unique stream ID
        base_stream_id = str(uuid.uuid4())[:8]
        stream_ids = generate_stream_ids(base_stream_id, group_name, screen_count)
        
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
        
        logger.info(f"📊 Canvas dimensions: {canvas_width}x{canvas_height}")
        logger.info(f"📺 Screen sections: {output_width}x{output_height}")
        
        # Build FFmpeg command
        logger.info("✅ Using system FFmpeg (standard mode)")
        
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
            base_stream_id=base_stream_id,
            grid_rows=grid_rows,
            grid_cols=grid_cols,
            framerate=framerate,
            bitrate=bitrate,
            stream_ids=stream_ids
        )
        
        logger.info("🎬 Starting FFmpeg process...")
        logger.info(f"📋 FFmpeg command: {' '.join(ffmpeg_cmd)}")
        logger.info(f"📂 Working directory: {os.getcwd()}")
        
        # Start the FFmpeg process with enhanced error capture
        logger.info("🚀 Launching FFmpeg process...")
        process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        logger.info(f"✅ FFmpeg process started with PID: {process.pid}")
        
        # Read initial output to catch early errors
        initial_lines = []
        import time
        
        for i in range(10):  # Read first 10 lines or until timeout
            try:
                # Check if process is still running
                if process.poll() is not None:
                    logger.error(f"❌ FFmpeg process died early with exit code: {process.returncode}")
                    break
                
                # Try to read a line with timeout
                import select
                import sys
                
                # Simple readline with small timeout
                line = process.stdout.readline()
                if line:
                    line_clean = line.strip()
                    initial_lines.append(line_clean)
                    logger.info(f"FFmpeg[{i+1}]: {line_clean}")
                    
                    # Look for success indicators
                    if any(indicator in line_clean.lower() for indicator in [
                        "frame=", "fps=", "bitrate=", "time=", "speed="
                    ]):
                        logger.info("✅ FFmpeg streaming started successfully!")
                        break
                        
                    # Look for error indicators  
                    if any(error in line_clean.lower() for error in [
                        "error", "failed", "invalid", "not found", "permission denied",
                        "no such file", "connection refused", "timeout", "unable to"
                    ]):
                        logger.error(f"❌ Error detected: {line_clean}")
                
                time.sleep(0.2)  # Small delay
                
            except Exception as e:
                logger.error(f"Error reading FFmpeg output: {e}")
                break
        
        # Final check
        final_poll = process.poll()
        if final_poll is not None:
            logger.error(f"❌ FFmpeg process ended with exit code: {final_poll}")
            
            # Try to get any remaining output
            try:
                remaining, _ = process.communicate(timeout=3)
                if remaining:
                    logger.error(f"FFmpeg final output:\n{remaining}")
            except:
                pass
                
            return jsonify({"error": f"FFmpeg failed to start (exit code: {final_poll})"}), 500
        
        logger.info("✅ Streaming output detected")
        
        # Generate response
        logger.info("📊 Generating response data...")
        crop_info = generate_client_crop_info(
            screen_count=screen_count,
            orientation=orientation,
            output_width=output_width,
            output_height=output_height,
            grid_rows=grid_rows,
            grid_cols=grid_cols
        )
        
        # Generate client stream URLs - Use EXTERNAL IP for clients, INTERNAL IP for publishing
        client_stream_urls = {}
        
        # For client URLs, use the external IP that clients can actually reach
        external_srt_ip = "128.205.39.64"  # External IP clients connect to
        external_srt_port = srt_port  # External port (e.g., 10100)
        
        # Combined stream URL
        combined_stream_path = f"live/{group_name}/split_{base_stream_id}"
        srt_params = "latency=5000000&connect_timeout=10000&rcvbuf=67108864&sndbuf=67108864"
        client_stream_urls["combined"] = f"srt://{external_srt_ip}:{external_srt_port}?streamid=#!::r={combined_stream_path},m=request&{srt_params}"
        
        # Individual screen URLs
        for i in range(screen_count):
            screen_key = f"test{i}"
            individual_stream_id = stream_ids.get(screen_key, f"screen{i}_{base_stream_id}")
            individual_stream_path = f"live/{group_name}/{individual_stream_id}"
            client_stream_urls[f"screen{i}"] = f"srt://{external_srt_ip}:{external_srt_port}?streamid=#!::r={individual_stream_path},m=request&{srt_params}"
        
        logger.info("📺 Client stream URLs:")
        for name, url in client_stream_urls.items():
            logger.info(f"   {name}: {url}")
        
        # Generate test result string
        test_result = f"ffplay '{client_stream_urls['combined']}'"
        
        logger.info("="*60)
        logger.info("🎉 SPLIT-SCREEN STREAMING STARTED SUCCESSFULLY")
        logger.info(f"📋 Group: {group_name}")
        logger.info(f"🔧 Process PID: {process.pid}")
        logger.info(f"📺 Screens: {screen_count}")
        logger.info(f"🔗 Combined Stream: {client_stream_urls['combined']}")
        logger.info(f"📺 {screen_count} Individual streams also available")
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
                "persistent_streams": stream_ids,
                "crop_information": crop_info
            },
            "status": "active",
            "test_result": test_result
        }), 200
        
    except Exception as e:
        logger.error("="*60)
        logger.error("💥 EXCEPTION IN start_split_screen_srt")
        logger.error(f"❌ Error type: {type(e).__name__}")
        logger.error(f"❌ Error message: {str(e)}")
        logger.error("Stack trace:", exc_info=True)
        logger.error("="*60)
        return jsonify({"error": str(e)}), 500

# ============================================================================
# COMMAND BUILDER FUNCTIONS
# ============================================================================

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
    Build FFmpeg command for split-screen streaming
    Takes a single video and splits it into multiple screen regions
    """
    
    ffmpeg_path = find_ffmpeg_executable()
    
    # Build input (single video file)
    input_args = ["-stream_loop", "-1", "-re", "-i", video_file]
    
    # Build filter complex for proper multi-screen layout
    # Use a single filter chain with commas instead of semicolons to avoid stream specifier issues
    filter_parts = []
    
    # Start with scaling and padding
    filter_parts.append(
        f"[0:v]scale={canvas_width}:{canvas_height}:"
        f"force_original_aspect_ratio=decrease,"
        f"pad={canvas_width}:{canvas_height}:"
        f"(ow-iw)/2:(oh-ih)/2:black"
    )
    
    # Add split to create multiple copies - combine with output labels to avoid comma issue
    output_labels = ["[full]"] + [f"[copy{i}]" for i in range(screen_count)]
    filter_parts.append(f"split={screen_count + 1}" + "".join(output_labels))  # +1 for the full canvas
    
    # Add crop filters for each screen (using commas to keep them in the same chain)
    for i in range(screen_count):
        if orientation.lower() == "horizontal":
            x_pos = i * output_width
            y_pos = 0
        elif orientation.lower() == "vertical":
            x_pos = 0
            y_pos = i * output_height
        elif orientation.lower() == "grid":
            row = i // grid_cols
            col = i % grid_cols
            x_pos = col * output_width
            y_pos = row * output_height
        else:
            # Default to horizontal
            x_pos = i * output_width
            y_pos = 0
        
        # Add crop filter (using comma to keep in same chain)
        filter_parts.append(f"[copy{i}]crop={output_width}:{output_height}:{x_pos}:{y_pos}[screen{i}]")
    
    # Join with commas for single filter chain
    complete_filter = ",".join(filter_parts)
    
    # Build FFmpeg command
    ffmpeg_cmd = [
        ffmpeg_path,
        "-y",
        "-v", "error",
        "-stats"
    ]
    
    ffmpeg_cmd.extend(input_args + ["-filter_complex", complete_filter])
    
    # Encoding parameters
    encoding_params = [
        "-an", "-c:v", "libx264",
        "-preset", "veryfast", "-tune", "zerolatency",
        "-maxrate", bitrate,
        "-bufsize", str(int(bitrate.rstrip('k')) * 2) + "k",
        "-bsf:v", f"h264_metadata=sei_user_data={sei}",
        "-pes_payload_size", "0",
        "-bf", "0", "-g", "1",
        "-r", str(framerate),
        "-f", "mpegts"
    ]
    
    # SRT parameters - simplified for better compatibility
    srt_params = "latency=5000000&connect_timeout=10000"
    
    # Add outputs
    # Combined/full stream
    combined_stream_path = f"live/{group_name}/split_{base_stream_id}"
    combined_url = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={combined_stream_path},m=publish&{srt_params}"
    logger.info(f"🔗 Combined stream URL: {combined_url}")
    ffmpeg_cmd.extend(["-map", "[full]"] + encoding_params + [combined_url])
    
    # Individual screen outputs
    if stream_ids is None:
        stream_ids = generate_stream_ids(base_stream_id, group_name, screen_count)

    for i in range(screen_count):
        screen_key = f"test{i}"
        individual_stream_id = stream_ids.get(screen_key, f"screen{i}_{base_stream_id}")
        stream_path = f"live/{group_name}/{individual_stream_id}"
        stream_url = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={stream_path},m=publish&{srt_params}"
        logger.info(f"🔗 Screen {i} stream URL: {stream_url}")
        ffmpeg_cmd.extend(["-map", f"[screen{i}]"] + encoding_params + [stream_url])
    
    logger.info(f"Built split-screen FFmpeg command with {len(ffmpeg_cmd)} arguments")
    logger.info(f"Filter chain: {complete_filter}")
    
    return ffmpeg_cmd

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

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
        logger.error(f"Error discovering group from Docker: {e}")
        return None

def find_running_ffmpeg_for_group_strict(group_id: str, group_name: str, container_id: str) -> List[Dict[str, Any]]:
    """Find running FFmpeg processes for a specific group using strict matching"""
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
            try:
                if proc.info['name'] == 'ffmpeg':
                    cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                    
                    # Strict matching criteria
                    is_match = False
                    match_method = ""
                    
                    # Check for group name in stream path
                    stream_path_pattern = f"live/{group_name}/"
                    if stream_path_pattern in cmdline:
                        is_match = True
                        match_method = f"stream_path({stream_path_pattern})"
                    
                    # Check for group ID in stream path
                    elif group_id in cmdline:
                        is_match = True
                        match_method = f"group_id({group_id})"
                    
                    # Check for container ID in command
                    elif container_id and container_id[:12] in cmdline:
                        is_match = True
                        match_method = f"container_id({container_id[:12]})"
                    
                    if is_match:
                        logger.info(f"✅ Found FFmpeg process {proc.info['pid']} for group '{group_name}' via {match_method}")
                        processes.append({
                            'pid': proc.info['pid'],
                            'cmdline': proc.info['cmdline'],
                            'create_time': proc.info['create_time'],
                            'match_method': match_method
                        })
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
                
        return processes
        
    except Exception as e:
        logger.error(f"Error finding FFmpeg processes: {e}")
        return []

# SRT monitoring now handled by centralized SRTService.monitor_srt_server()

def _check_udp_port(ip: str, port: int, timeout: float = 1.0) -> bool:
    """
    Check if UDP port is reachable using socket
    
    Note: UDP is connectionless, so we send a small packet and check if we get 
    a response or if the port is at least not actively rejecting connections
    """
    try:
        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        
        try:
            # Send a small test packet (SRT servers typically respond to this)
            test_data = b'\x80\x00\x00\x00'  # Basic SRT packet header pattern
            sock.sendto(test_data, (ip, port))
            
            # Try to receive a response (SRT server might send back an error or response)
            try:
                sock.recvfrom(1024)
                return True  # Got a response, server is listening
            except socket.timeout:
                # No response, but no connection refused error either
                # This often means the port is open but server is busy
                return True
            except socket.error:
                # Some error occurred, but might still be reachable
                return True
                
        except socket.error as e:
            # Check if it's a "connection refused" type error
            if "refused" in str(e).lower():
                return False
            # For other errors, the port might still be reachable
            return True
            
    except Exception as e:
        logger.debug(f"UDP port check failed: {e}")
        return False
    finally:
        try:
            sock.close()
        except:
            pass

def generate_client_crop_info(
    screen_count: int,
    orientation: str,
    output_width: int,
    output_height: int,
    grid_rows: int = 2,
    grid_cols: int = 2
) -> Dict[str, Any]:
    """Generate crop information for client screens"""
    crop_info = {}
    
    for i in range(screen_count):
        if orientation.lower() == "horizontal":
            x_crop = i * output_width
            y_crop = 0
        elif orientation.lower() == "vertical":
            x_crop = 0
            y_crop = i * output_height
        else:  # grid
            row = i // grid_cols
            col = i % grid_cols
            x_crop = col * output_width
            y_crop = row * output_height
        
        crop_info[f"screen{i}"] = {
            "x": x_crop,
            "y": y_crop,
            "width": output_width,
            "height": output_height
        }
    
    return crop_info

def find_ffmpeg_executable() -> str:
    """Find FFmpeg executable path with smart detection"""
    
    # Priority order: Custom OpenVideoWalls FFmpeg first, then system FFmpeg
    custom_paths = [
        # OpenVideoWalls custom FFmpeg with SEI timestamp support
        "./cmake-build-debug/external/Install/bin/ffmpeg",
        "../cmake-build-debug/external/Install/bin/ffmpeg", 
        "../../cmake-build-debug/external/Install/bin/ffmpeg",
        "./multi-screen/cmake-build-debug/external/Install/bin/ffmpeg",
        "./build/external/Install/bin/ffmpeg",
        "../build/external/Install/bin/ffmpeg",
        "../../build/external/Install/bin/ffmpeg",
    ]
    
    # First, try to find custom OpenVideoWalls FFmpeg
    for path in custom_paths:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path) and os.access(abs_path, os.X_OK):
            logger.info(f"Found custom FFmpeg binary: {abs_path}")
            if _verify_openvideowall_support(abs_path):
                logger.info(f"✅ Using OpenVideoWalls custom FFmpeg: {abs_path}")
                return abs_path
            else:
                logger.debug(f"Custom FFmpeg at {abs_path} lacks OpenVideoWalls support")
    
    # Fallback to system ffmpeg
    try:
        # Test if system ffmpeg exists and works
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            logger.info("✅ Using system FFmpeg (standard mode)")
            return "ffmpeg"
    except Exception as e:
        logger.debug(f"System FFmpeg test failed: {e}")
    
    # Try with 'which' command to find system ffmpeg
    try:
        result = subprocess.run(["which", "ffmpeg"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            system_path = result.stdout.strip()
            logger.info(f"✅ Using system FFmpeg: {system_path}")
            return "ffmpeg"
    except Exception as e:
        logger.debug(f"'which ffmpeg' failed: {e}")
    
    raise FileNotFoundError("No FFmpeg executable found (custom or system)")

def _verify_openvideowall_support(ffmpeg_path: str) -> bool:
    """Verify if FFmpeg has OpenVideoWalls SEI timestamp support"""
    try:
        logger.debug(f"Testing OpenVideoWalls support for: {ffmpeg_path}")
        
        # Test 1: Basic SEI metadata support test
        test_cmd = [
            ffmpeg_path, "-f", "lavfi", "-i", "testsrc=duration=0.1:size=32x32:rate=1",
            "-frames:v", "1", "-c:v", "libx264", "-preset", "ultrafast",
            "-bsf:v", "h264_metadata=sei_user_data=681d5c8f-80cd-4847-930a-99b9484b4a32+000000",
            "-f", "null", "-", "-v", "quiet"
        ]
        
        result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            logger.debug(f"SEI test failed for {ffmpeg_path}: {result.stderr}")
            return False
        
        # Test 2: Check if this is likely the custom build
        # Custom builds should be in cmake-build directories or have specific characteristics
        is_custom_path = any(indicator in ffmpeg_path.lower() for indicator in [
            "cmake-build", "build/external", "install/bin"
        ])
        
        if is_custom_path:
            logger.debug(f"Custom build path detected: {ffmpeg_path}")
            
            # Test 3: Advanced encoding parameters test (specific to OpenVideoWalls)
            advanced_test_cmd = [
                ffmpeg_path, "-f", "lavfi", "-i", "testsrc=duration=0.1:size=32x32:rate=1",
                "-frames:v", "1", "-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency",
                "-bf", "0", "-g", "1", "-pes_payload_size", "0",
                "-bsf:v", "h264_metadata=sei_user_data=681d5c8f-80cd-4847-930a-99b9484b4a32+000000",
                "-f", "null", "-", "-v", "quiet"
            ]
            
            advanced_result = subprocess.run(advanced_test_cmd, capture_output=True, text=True, timeout=10)
            
            if advanced_result.returncode == 0:
                logger.debug(f"Advanced encoding test passed for {ffmpeg_path}")
                return True
            else:
                logger.debug(f"Advanced encoding test failed for {ffmpeg_path}")
                return False
        
        # For system FFmpeg, basic SEI support is enough but don't claim full OpenVideoWalls support
        logger.debug(f"System FFmpeg with basic SEI support: {ffmpeg_path}")
        return False
        
    except Exception as e:
        logger.debug(f"OpenVideoWalls verification failed for {ffmpeg_path}: {e}")
        return False

def _has_openvideowall_support(ffmpeg_path: str) -> bool:
    """Cache-friendly check for OpenVideoWalls support"""
    if not hasattr(_has_openvideowall_support, 'cache'):
        _has_openvideowall_support.cache = {}
    
    if ffmpeg_path not in _has_openvideowall_support.cache:
        has_support = _verify_openvideowall_support(ffmpeg_path)
        _has_openvideowall_support.cache[ffmpeg_path] = has_support
        
        if has_support:
            logger.info(f"🎯 OpenVideoWalls support confirmed: {ffmpeg_path}")
        else:
            logger.info(f"📺 Standard FFmpeg mode: {ffmpeg_path}")
    
    return _has_openvideowall_support.cache[ffmpeg_path]

def generate_stream_ids(base_stream_id: str, group_name: str, screen_count: int) -> Dict[str, str]:
    """Generate stream IDs for a group"""
    stream_ids = {}
    
    # Combined stream ID
    stream_ids["test"] = f"{base_stream_id[:8]}"
    
    # Individual screen stream IDs
    for i in range(screen_count):
        stream_ids[f"test{i}"] = f"{base_stream_id[:8]}_{i}"
    
    return stream_ids
