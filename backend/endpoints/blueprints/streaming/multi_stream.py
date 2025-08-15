# blueprints/streaming/multi_stream.py
"""
Multi-video streaming functionality for multi-screen display system.
Handles combining multiple video files into synchronized streams.
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
multi_stream_bp = Blueprint('multi_stream', __name__)

# Configure logger
logger = logging.getLogger(__name__)

# Global storage for current active stream IDs
# This stores the stream IDs that are currently being used by active FFmpeg processes
_active_stream_ids = {}

def get_active_stream_ids(group_id: str) -> Dict[str, str]:
    """Get current active stream IDs for a group"""
    return _active_stream_ids.get(group_id, {})

def set_active_stream_ids(group_id: str, stream_ids: Dict[str, str]):
    """Set current active stream IDs for a group"""
    _active_stream_ids[group_id] = stream_ids
    logger.info(f"📝 Stored active stream IDs for group {group_id}: {stream_ids}")

def clear_active_stream_ids(group_id: str):
    """Clear current active stream IDs for a group when streaming stops"""
    if group_id in _active_stream_ids:
        del _active_stream_ids[group_id]
        logger.info(f"🗑️ Cleared active stream IDs for group {group_id}")

# ============================================================================
# FLASK ROUTE HANDLERS
# ============================================================================

@multi_stream_bp.route("/start_multi_video_srt", methods=["POST"])
def start_multi_video_srt():
    """
    Flask route handler for multi-video streaming with FIXED port resolution
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
        
        # Extract video files parameter
        video_files = data.get("video_files", [])
        if not video_files:
            return jsonify({"error": "video_files is required"}), 400
        
        # Get group configuration
        group_name = group.get("name", group_id)
        screen_count = data.get("screen_count", group.get("screen_count", 2))
        orientation = data.get("orientation", group.get("orientation", "horizontal"))
        output_width = data.get("output_width", 1920)
        output_height = data.get("output_height", 1080)
        
        # Get streaming parameters - FIX THE PORT RESOLUTION HERE
        ports = group.get("ports", {})
        srt_ip = data.get("srt_ip", "127.0.0.1")
        
        # IMPORTANT: Use the external port that clients connect to, not the internal Docker port
        # The Docker container maps external_port:10080/udp, so we need the external port
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
        
        # Get encoding parameters
        sei = data.get("sei", "681d5c8f-80cd-4847-930a-99b9484b4a32+000000")
        framerate = data.get("framerate", 30)
        bitrate = data.get("bitrate", "3000k")
        
        # Check for existing streams
        container_id = group.get("container_id")
        logger.info(f"🔍 Checking for existing FFmpeg processes...")
        logger.info(f"   Container ID: {container_id}")
        
        existing_ffmpeg = find_running_ffmpeg_for_group_strict(group_id, group_name, container_id)
        if existing_ffmpeg:
            logger.warning(f"⚠️  Found {len(existing_ffmpeg)} existing FFmpeg process(es)")
            logger.info("   Streaming already active, returning current status")
            return jsonify({
                "message": f"Multi-video streaming already active for group '{group_name}'",
                "status": "already_active"
            }), 200
        
        logger.info("✅ No existing streams found")
        
        # Generate unique stream ID
        base_stream_id = str(uuid.uuid4())[:8]
        stream_ids = generate_stream_ids(base_stream_id, group_name, screen_count)
        
        # Store active stream IDs
        set_active_stream_ids(group_id, stream_ids)
        
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
                clear_active_stream_ids(group_id)
                
                # Use error service for structured error response
                try:
                    from error_service import ErrorService, ErrorCode
                    error_response = ErrorService.create_srt_error("connection_timeout", {
                        "srt_ip": srt_ip,
                        "srt_port": srt_port,
                        "group_id": group_id,
                        "timeout": 5
                    })
                    return jsonify(error_response), 503
                except ImportError:
                    # Fallback to simple error if error service not available
                    return jsonify({"error": f"SRT server not ready: {srt_status['message']}"}), 503
                    
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
                clear_active_stream_ids(group_id)
                
                # Use error service for structured error response
                try:
                    from error_service import ErrorService, ErrorCode
                    error_response = ErrorService.create_srt_error("connection_timeout", {
                        "srt_ip": srt_ip,
                        "srt_port": srt_port,
                        "group_id": group_id,
                        "timeout": fallback_timeout,
                        "fallback_method": True
                    })
                    return jsonify(error_response), 503
                except ImportError:
                    # Fallback to simple error if error service not available
                    return jsonify({"error": f"SRT server not ready after {fallback_timeout}s"}), 500
        
        # Test SRT connection with actual FFmpeg test
        logger.info("🧪 Testing SRT connection with FFmpeg...")
        test_result = SRTService.test_connection(srt_ip, srt_port, group_name, sei)
        if not test_result["success"]:
            logger.error(f"❌ SRT connection test failed: {test_result}")
            clear_active_stream_ids(group_id)
            return jsonify({"error": "SRT connection test failed", "test_result": test_result}), 500
        logger.info("✅ SRT connection test passed")
        
        # Build FFmpeg command
        logger.info("✅ Using system FFmpeg (standard mode)")
        
        # Calculate canvas dimensions based on orientation
        if orientation.lower() == "horizontal":
            canvas_width = output_width * screen_count
            canvas_height = output_height
        elif orientation.lower() == "vertical":
            canvas_width = output_width
            canvas_height = output_height * screen_count
        else:  # grid
            grid_rows = data.get("grid_rows", 2)
            grid_cols = data.get("grid_cols", 2)
            canvas_width = output_width * grid_cols
            canvas_height = output_height * grid_rows
        
        logger.info(f"📊 Canvas: {canvas_width}x{canvas_height}, Sections: {output_width}x{output_height}")
        logger.info(f"🎬 Inputs: {len(video_files)}, Outputs: {screen_count + 1} streams")
        
        # Build FFmpeg command
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
            grid_rows=data.get("grid_rows", 2),
            grid_cols=data.get("grid_cols", 2),
            framerate=framerate,
            bitrate=bitrate,
            stream_ids=stream_ids  # ADD THIS LINE!
        )
        
        logger.info("🎬 Starting FFmpeg process...")
        logger.info(f"📋 FFmpeg command: {' '.join(ffmpeg_cmd)}")
        logger.info(f"📂 Working directory: {os.getcwd()}")
        
        # Log the stream URLs being created
        logger.info("🔗 STREAM URLs BEING CREATED:")
        combined_url = f"srt://{srt_ip}:{srt_port}?streamid=#!::r=live/{group_name}/{base_stream_id},m=publish"
        logger.info(f"   Combined: {combined_url}")
        
        for i in range(screen_count):
            screen_key = f"test{i}"
            individual_stream_id = stream_ids.get(screen_key, f"screen{i}_{base_stream_id}")
            screen_url = f"srt://{srt_ip}:{srt_port}?streamid=#!::r=live/{group_name}/{individual_stream_id},m=publish"
            logger.info(f"   Screen {i}: {screen_url}")
        
        logger.info(f"📡 Total streams: {screen_count + 1} (1 combined + {screen_count} individual)")
        
        # Verify input files exist
        logger.info("📁 Input files verification:")
        for i, video_file in enumerate(video_files):
            file_path = os.path.join("uploads", video_file)
            exists = os.path.exists(file_path)
            size = os.path.getsize(file_path) if exists else 0
            logger.info(f"  Input {i+1}: {file_path}")
            logger.info(f"    Exists: {exists}")
            logger.info(f"    Size: {size} bytes ({size / (1024*1024):.1f} MB)")
        
        # Launch FFmpeg process
        logger.info("🚀 Launching FFmpeg process...")
        process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        logger.info(f"✅ FFmpeg process started with PID: {process.pid}")
        
        # Monitor FFmpeg output for startup confirmation
        streaming_detected = False
        start_time = time.time()
        timeout = 5  # 5 seconds timeout
        frame_count = 0
        last_frame_time = time.time()
        
        logger.info("👀 Monitoring FFmpeg startup and continuous operation...")
        
        while time.time() - start_time < timeout:
            if process.poll() is not None:
                # Process has terminated
                stdout, stderr = process.communicate()
                logger.error(f"❌ FFmpeg process terminated unexpectedly")
                logger.error(f"   Return code: {process.returncode}")
                logger.error(f"   Output: {stdout}")
                clear_active_stream_ids(group_id)
                return jsonify({"error": "FFmpeg process terminated unexpectedly"}), 500
            
            # Non-blocking read with timeout
            try:
                import select
                if process.stdout and select.select([process.stdout], [], [], 0.5)[0]:
                    output = process.stdout.readline()
                    if output:
                        output = output.strip()
                        logger.info(f"FFmpeg[{process.pid}]: {output}")
                        
                        # Check for streaming indicators
                        if "frame=" in output and "fps=" in output:
                            frame_count += 1
                            last_frame_time = time.time()
                            if not streaming_detected:
                                streaming_detected = True
                                logger.info(f"✅ FFmpeg streaming started successfully! Frame {frame_count}")
                            else:
                                # Log progress every 10 frames
                                if frame_count % 10 == 0:
                                    logger.info(f"📊 Streaming progress: {frame_count} frames processed")
                        
                        # Check for errors
                        if any(error in output.lower() for error in [
                            "error", "failed", "invalid", "not found", "permission denied",
                            "no such file", "connection refused", "timeout", "unable to"
                        ]):
                            logger.error(f"❌ FFmpeg error detected: {output}")
                            
            except Exception as e:
                logger.debug(f"Error reading FFmpeg output: {e}")
                break
            
            # Check if we've been streaming successfully for a few seconds
            if streaming_detected and (time.time() - last_frame_time) > 5:
                logger.info("✅ FFmpeg streaming confirmed stable - startup monitoring complete")
                break
        
        if not streaming_detected:
            logger.warning("⚠️  Streaming detection timeout - but process is running")
        else:
            logger.info(f"🎬 FFmpeg streaming confirmed: {frame_count} frames processed")
        
        # Start background monitoring thread for continuous error detection
        def background_monitor():
            """Background thread to monitor FFmpeg process for errors"""
            try:
                logger.info(f"🔄 Starting background monitoring for FFmpeg PID {process.pid}")
                while process.poll() is None:
                    time.sleep(5)  # Check every 5 seconds
                    
                # Process has ended
                exit_code = process.returncode
                logger.warning(f"⚠️  FFmpeg process {process.pid} ended with exit code: {exit_code}")
                
                if exit_code != 0:
                    logger.error(f"❌ FFmpeg process failed with exit code: {exit_code}")
                    # Try to get any remaining output
                    try:
                        stdout, stderr = process.communicate(timeout=3)
                        if stdout:
                            logger.error(f"FFmpeg final output:\n{stdout}")
                    except:
                        pass
                        
            except Exception as e:
                logger.error(f"Background monitoring error: {e}")
        
        # Start background monitoring in daemon thread
        import threading
        monitor_thread = threading.Thread(target=background_monitor, daemon=True)
        monitor_thread.start()
        logger.info("✅ Background monitoring thread started")
        
        # Generate client URLs - Use EXTERNAL IP for clients, INTERNAL IP for publishing
        client_urls = {}
        
        # For client URLs, use the external IP that clients can actually reach
        external_srt_ip = "127.0.0.1"  # Local IP for testing
        external_srt_port = srt_port  # External port (e.g., 10100)
        
        # Combined stream URL
        client_urls["combined"] = f"srt://{external_srt_ip}:{external_srt_port}?streamid=#!::r=live/{group_name}/{base_stream_id},m=request,latency=5000000"
        
        # Individual screen URLs
        for i in range(screen_count):
            screen_key = f"test{i}"
            stream_id = stream_ids.get(screen_key)
            if not stream_id:
                logger.error(f"❌ Missing stream ID for screen {i} - key: {screen_key}")
                logger.error(f"   Available stream IDs: {stream_ids}")
                continue
            client_urls[f"screen{i}"] = f"srt://{external_srt_ip}:{external_srt_port}?streamid=#!::r=live/{group_name}/{stream_id},m=request,latency=5000000"
        
        # IMPORTANT: Resolve stream URLs for all assigned clients
        try:
            from blueprints.client_management.client_endpoints import resolve_stream_urls_for_group
            logger.info(f"🔄 Resolving stream URLs for all clients in group {group_name}")
            resolve_stream_urls_for_group(group_id, group_name)
        except ImportError:
            try:
                # Fallback for when running directly
                from client_management.client_endpoints import resolve_stream_urls_for_group
                logger.info(f"🔄 Resolving stream URLs for all clients in group {group_name}")
                resolve_stream_urls_for_group(group_id, group_name)
            except Exception as e:
                logger.warning(f"Could not resolve client stream URLs: {e}")
                # This is not critical - streaming will still work
        
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

@multi_stream_bp.route("/all_streaming_statuses", methods=["GET"])
def all_streaming_statuses():
    """Get streaming status for all groups"""
    try:
        logger.info("🔍 Getting streaming status for all groups...")
        
        # Discover all groups from Docker
        from blueprints.docker_management import discover_groups
        discovery_result = discover_groups()
        
        if not discovery_result.get("success", False):
            logger.error(f"Failed to discover groups: {discovery_result.get('error', 'Unknown error')}")
            return jsonify({"error": "Failed to discover groups"}), 500
        
        groups = discovery_result.get("groups", [])
        logger.info(f"Found {len(groups)} groups to check")
        
        streaming_statuses = {}
        containers_found = len(groups)
        
        # Get all running FFmpeg processes
        all_ffmpeg_processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
                try:
                    if proc.info['name'] == 'ffmpeg':
                        all_ffmpeg_processes.append({
                            'pid': proc.info['pid'],
                            'cmdline': proc.info['cmdline'],
                            'create_time': proc.info['create_time']
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception as e:
            logger.warning(f"Error getting FFmpeg processes: {e}")
        
        logger.info(f"Found {len(all_ffmpeg_processes)} total FFmpeg processes")
        
        # Check each group for streaming status
        for group in groups:
            group_id = group.get("id")
            group_name = group.get("name", group_id)
            container_id = group.get("container_id")
            
            if not container_id:
                continue
            
            # Find processes for this group
            group_processes = find_running_ffmpeg_for_group_strict(group_id, group_name, container_id)
            
            is_streaming = len(group_processes) > 0
            docker_running = group.get("docker_running", False)
            
            # Determine health status
            container_health = "HEALTHY" if docker_running and is_streaming else "UNHEALTHY" if docker_running else "OFFLINE"
            
            # Store status
            streaming_statuses[group_id] = {
                "group_name": group_name,
                "streaming_mode": group.get("streaming_mode", "unknown"),
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
                    "started_at": time.strftime('%Y-%m-%d %H:%M:%S', 
                                               time.localtime(proc.get('create_time', 0))),
                    "cmdline_preview": proc["cmdline"][:100] + "..." if len(proc["cmdline"]) > 100 else proc["cmdline"]
                } for proc in orphaned_processes
            ]
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting streaming statuses: {e}")
        return jsonify({"error": str(e)}), 500

@multi_stream_bp.route("/stop_stream", methods=["POST"])
def stop_stream():
    """Stop streaming for a specific group"""
    try:
        data = request.get_json() or {}
        group_id = data.get("group_id")
        
        if not group_id:
            return jsonify({"error": "group_id is required"}), 400
        
        logger.info(f"🛑 Stopping stream for group: {group_id}")
        
        # Discover group
        group = discover_group_from_docker(group_id)
        if not group:
            return jsonify({"error": f"Group '{group_id}' not found"}), 404
        
        group_name = group.get("name", group_id)
        container_id = group.get("container_id")
        
        # Find running FFmpeg processes for this group
        running_processes = find_running_ffmpeg_for_group_strict(group_id, group_name, container_id)
        
        if not running_processes:
            logger.info(f"✅ No active streams found for group '{group_name}'")
            clear_active_stream_ids(group_id)
            return jsonify({
                "message": f"No active streams found for group '{group_name}'",
                "status": "no_streams"
            }), 200
        
        # Stop each process
        stopped_count = 0
        for proc_info in running_processes:
            try:
                pid = proc_info["pid"]
                logger.info(f"🛑 Stopping FFmpeg process {pid} for group '{group_name}'")
                
                # Send SIGTERM first
                os.kill(pid, 15)  # SIGTERM
                
                # Wait a bit for graceful shutdown
                time.sleep(2)
                
                # Check if process is still running
                try:
                    os.kill(pid, 0)  # Check if process exists
                    logger.info(f"⚠️  Process {pid} still running, sending SIGKILL")
                    os.kill(pid, 9)  # SIGKILL
                except OSError:
                    # Process already terminated
                    pass
                
                stopped_count += 1
                logger.info(f"✅ Successfully stopped FFmpeg process {pid}")
                
            except Exception as e:
                logger.error(f"❌ Error stopping process {proc_info['pid']}: {e}")
        
        # Clear active stream IDs
        clear_active_stream_ids(group_id)
        
        logger.info(f"✅ Stopped {stopped_count} FFmpeg process(es) for group '{group_name}'")
        
        return jsonify({
            "message": f"Stopped {stopped_count} stream(s) for group '{group_name}'",
            "group_id": group_id,
            "group_name": group_name,
            "stopped_processes": stopped_count,
            "status": "stopped"
        }), 200
        
    except Exception as e:
        logger.error(f"Error stopping stream: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================================================
# COMMAND BUILDER FUNCTIONS
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
    Build FFmpeg command for multi-video streaming
    
    Args:
        video_files: List of video file paths
        screen_count: Number of screens
        orientation: Layout orientation (horizontal, vertical, grid)
        output_width: Width of each screen section
        output_height: Height of each screen section
        srt_ip: SRT server IP
        srt_port: SRT server port
        group_name: Group name for stream paths
        base_stream_id: Base stream ID
        grid_rows: Number of grid rows (for grid layout)
        grid_cols: Number of grid columns (for grid layout)
        framerate: Output framerate
        bitrate: Output bitrate
        stream_ids: Dictionary of stream IDs for each screen
        
    Returns:
        List of FFmpeg command arguments
    """
    if stream_ids is None:
        stream_ids = {
            "test": base_stream_id,
            "test0": f"{base_stream_id}_0",
            "test1": f"{base_stream_id}_1"
        }
    
    # Base FFmpeg command
    ffmpeg_cmd = [
        "ffmpeg", "-y", "-v", "error", "-stats",
        "-stream_loop", "-1", "-re"
    ]
    
    # Add input files
    for video_file in video_files:
        file_path = os.path.join("uploads", video_file)
        ffmpeg_cmd.extend(["-i", file_path])
    
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
    
    # Build filter complex - FIXED to use unique labels
    filter_parts = []
    
    # Create main canvas
    filter_parts.append(f"color=c=black:s={canvas_width}x{canvas_height}[canvas]")
    
    # Build overlay chain with unique labels
    current_canvas = "[canvas]"
    for i, video_file in enumerate(video_files):
        if orientation.lower() == "horizontal":
            x_pos = i * output_width
            y_pos = 0
        elif orientation.lower() == "vertical":
            x_pos = 0
            y_pos = i * output_height
        else:  # grid
            row = i // grid_cols
            col = i % grid_cols
            x_pos = col * output_width
            y_pos = row * output_height
        
        # Scale input video
        filter_parts.append(f"[{i}:v]scale={output_width}:{output_height}[scaled{i}]")
        
        # Overlay onto current canvas with unique label
        overlay_label = f"[overlay{i}]"
        filter_parts.append(f"{current_canvas}[scaled{i}]overlay=x={x_pos}:y={y_pos}{overlay_label}")
        current_canvas = overlay_label
    
    # Split the final canvas for multiple outputs
    split_outputs = []
    for i in range(screen_count + 1):  # +1 for combined stream
        split_outputs.append(f"[mon{i}]")
    
    # FFmpeg split syntax: split=N[out1][out2][out3]... (no commas)
    filter_parts.append(f"{current_canvas}split={len(split_outputs)}{''.join(split_outputs)}")
    
    # Add crop filters for individual screens
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
        
        filter_parts.append(f"[mon{i+1}]crop=w={output_width}:h={output_height}:x={x_crop}:y={y_crop}[mon{i+1}]")
    
    # Combine all filter parts
    filter_complex = ";".join(filter_parts)
    
    # Log the filter complex for debugging
    logger.info(f"🔧 Filter complex: {filter_complex}")
    
    ffmpeg_cmd.extend(["-filter_complex", filter_complex])
    
    # Add outputs
    # Combined stream
    ffmpeg_cmd.extend([
        "-map", "[mon0]",
        "-an", "-c:v", "libx264",
        "-preset", "faster", "-maxrate", bitrate, "-bufsize", str(int(bitrate.rstrip('k')) * 2) + "k",
        "-r", str(framerate), "-f", "mpegts",
        f"srt://{srt_ip}:{srt_port}?streamid=#!::r=live/{group_name}/{base_stream_id},m=publish"
    ])
    
    # Individual screen streams
    for i in range(screen_count):
        screen_key = f"test{i}"
        stream_id = stream_ids.get(screen_key)
        if not stream_id:
            logger.error(f"❌ Missing stream ID for screen {i} - key: {screen_key}")
            logger.error(f"   Available stream IDs: {stream_ids}")
            continue
        ffmpeg_cmd.extend([
            "-map", f"[mon{i+1}]",
            "-an", "-c:v", "libx264",
            "-preset", "faster", "-maxrate", bitrate, "-bufsize", str(int(bitrate.rstrip('k')) * 2) + "k",
            "-r", str(framerate), "-f", "mpegts",
            f"srt://{srt_ip}:{srt_port}?streamid=#!::r=live/{group_name}/{stream_id},m=publish"
        ])
    
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
