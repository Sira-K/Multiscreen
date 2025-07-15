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

def discover_group_from_docker(group_id: str) -> Optional[Dict[str, Any]]:
    """
    Discover group information purely from Docker container
    Uses your actual Docker container naming and label scheme
    
    Args:
        group_id: The group ID to find
        
    Returns:
        Group data dict or None if not found
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
        logger.info("Available containers:")
        
        # Debug: List all containers
        debug_cmd = ["docker", "ps", "-a", "--format", "{{.Names}}\t{{.Image}}\t{{.Labels}}"]
        debug_result = subprocess.run(debug_cmd, capture_output=True, text=True, timeout=10)
        if debug_result.returncode == 0:
            for line in debug_result.stdout.strip().split('\n')[:5]:  # First 5 containers
                logger.info(f"  {line}")
        
        return None
        
    except Exception as e:
        logger.error(f"Error discovering group from Docker: {e}")
        return None

def get_container_details(container_id: str, group_id: str) -> Dict[str, Any]:
    """
    Get detailed container information for a group
    
    Args:
        container_id: Docker container ID
        group_id: Group ID
        
    Returns:
        Group data dictionary
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
    
    Args:
        group_id: Group ID
        group_name: Group name
        
    Returns:
        List of running FFmpeg process info
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
    ffmpeg_paths = [
        "./cmake-build-debug/external/Install/bin/ffmpeg",
        "/usr/bin/ffmpeg", 
        "/usr/local/bin/ffmpeg",
        "ffmpeg"
    ]
    
    ffmpeg_path = "ffmpeg"
    for path in ffmpeg_paths:
        if os.path.exists(path):
            ffmpeg_path = path
            break
    
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

def build_ffmpeg_filter_chain(
    video_width: int,
    video_height: int,
    split_count: int,
    orientation: str,
    srt_ip: str,
    srt_port: int,
    sei: str,
    group_name: str,
    stream_ids: Dict[str, str]
) -> Tuple[str, List[str]]:
    """Build FFmpeg filter chain for video splitting"""
    filter_complex = []
    output_mappings = []
    
    if split_count == 0:
        return "", []
    
    # Start with splitting the input
    split_str = f"[0:v]split={split_count+1}[full]"
    for i in range(split_count):
        split_str += f"[part{i}]"
    filter_complex.append(split_str)
    
    # Calculate section sizes based on orientation
    if orientation.lower() == "horizontal":
        section_width = video_width // split_count
        remainder = video_width % split_count
        
        for i in range(split_count):
            current_width = section_width + (remainder if i == split_count-1 else 0)
            start_x = i * section_width
            
            filter_complex.append(
                f"[part{i}]crop={current_width}:{video_height}:{start_x}:0[out{i}]"
            )
            
            stream_name = f"test{i}"
            stream_id = stream_ids[stream_name]
            
            output_mappings.extend([
                "-map", f"[out{i}]",
                "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency",
                "-bsf:v", f"h264_metadata=sei_user_data={sei}",
                "-pes_payload_size", "0", "-bf", "0", "-g", "30",
                "-f", "mpegts", f"srt://{srt_ip}:{srt_port}?streamid=#!::r=live/{group_name}/{stream_id},m=publish"
            ])
    
    elif orientation.lower() == "vertical":
        section_height = video_height // split_count
        remainder = video_height % split_count
        
        for i in range(split_count):
            current_height = section_height + (remainder if i == split_count-1 else 0)
            start_y = i * section_height
            
            filter_complex.append(
                f"[part{i}]crop={video_width}:{current_height}:0:{start_y}[out{i}]"
            )
            
            stream_name = f"test{i}"
            stream_id = stream_ids[stream_name]
            
            output_mappings.extend([
                "-map", f"[out{i}]",
                "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency",
                "-bsf:v", f"h264_metadata=sei_user_data={sei}",
                "-pes_payload_size", "0", "-bf", "0", "-g", "30",
                "-f", "mpegts", f"srt://{srt_ip}:{srt_port}?streamid=#!::r=live/{group_name}/{stream_id},m=publish"
            ])
    
    # Add the full stream output
    full_stream_id = stream_ids["test"]
    output_mappings.extend([
        "-map", "[full]",
        "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency",
        "-bsf:v", f"h264_metadata=sei_user_data={sei}",
        "-pes_payload_size", "0", "-bf", "0", "-g", "30",
        "-f", "mpegts", f"srt://{srt_ip}:{srt_port}?streamid=#!::r=live/{group_name}/{full_stream_id},m=publish"
    ])
    
    # Join filter parts with semicolons
    filter_str = ";".join([f for f in filter_complex if f.strip()])
    
    return filter_str, output_mappings

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

@stream_bp.route("/start_group_srt", methods=["POST"])
def start_group_srt():
    """Start SRT streaming for a group - Pure Docker Discovery, No State"""
    try:
        data = request.get_json() or {}
        
        # Extract required parameters
        group_id = data.get("group_id")
        video_file = data.get("video_file")
        
        logger.info(f"🚀 START STATELESS SRT: group_id={group_id}, video_file={video_file}")
        
        # Validation
        if not group_id:
            return jsonify({"error": "group_id is required"}), 400
        
        # Discover group from Docker - this is our single source of truth
        logger.info(f"🔍 Discovering group from Docker: {group_id}")
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
        
        # Extract configuration from request or use Docker defaults
        screen_count = data.get("screen_count", group.get("screen_count", 2))
        orientation = data.get("orientation", group.get("orientation", "horizontal"))
        ports = group.get("ports", {})
        srt_port = data.get("srt_port", ports.get("srt_port", 10080))
        
        # Video configuration
        enable_looping = data.get("enable_looping", True)
        video_width = data.get("video_width", 3840)
        video_height = data.get("video_height", 1080)
        framerate = data.get("framerate", 30)
        
        # SEI identifier
        sei = data.get("sei", "681d5c8f-80cd-4847-930a-99b9484b4a32+000000")
        
        # SRT IP
        srt_ip = data.get("srt_ip", "127.0.0.1")
        
        logger.info(f"📋 Config - Screens: {screen_count}, Orientation: {orientation}, SRT Port: {srt_port}")
        
        # WAIT FOR SRT SERVER TO BE READY
        logger.info(f"⏳ Waiting for SRT server to be ready...")
        if not wait_for_srt_server(srt_ip, srt_port, timeout=30):
            return jsonify({
                "error": f"SRT server at {srt_ip}:{srt_port} not ready",
                "suggestion": "Check Docker container logs"
            }), 500
        
        # Calculate split count (simple logic - can be customized)
        active_client_count = data.get("active_clients", 2)  # Frontend can specify
        
        if active_client_count <= 1:
            split_count = 0
            logger.info("Creating only full stream")
        else:
            split_count = min(active_client_count, screen_count)
            logger.info(f"Creating {split_count} split streams")
        
        # Find FFmpeg
        ffmpeg_path = data.get("ffmpeg_path", find_ffmpeg_executable())
        
        # TEST SRT CONNECTION FIRST
        logger.info(f"🧪 Testing SRT connection...")
        test_result = test_ffmpeg_srt_connection(srt_ip, srt_port, group_name, sei)
        
        if not test_result["success"]:
            return jsonify({
                "error": "SRT connection test failed",
                "test_result": test_result,
                "suggestion": "Check SRT server configuration"
            }), 500
        
        logger.info(f"✅ SRT test passed! Starting main stream...")
        
        # Input configuration
        if video_file and os.path.exists(video_file):
            input_args = ["-re", "-i", video_file]
            if enable_looping:
                input_args.extend(["-stream_loop", "-1"])
            video_source = video_file
        else:
            input_args = [
                "-re", "-f", "lavfi", 
                "-i", f"testsrc=s={video_width}x{video_height}:r={framerate}"
            ]
            video_source = "test_pattern"
        
        # Get persistent streams
        persistent_streams = get_persistent_streams_for_group(group_id, group_name, split_count)
        
        # Build FFmpeg command
        ffmpeg_cmd = [ffmpeg_path, "-y"] + input_args
        
        # Create stream URLs
        available_streams = []
        client_stream_urls = {}
        
        # Always add full stream
        full_stream_id = persistent_streams["test"]
        full_stream_path = f"live/{group_name}/{full_stream_id}"
        available_streams.append(full_stream_path)
        client_stream_urls["test"] = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={full_stream_path},m=request"
        
        if split_count > 0:
            # Build filter chain
            filter_complex_str, output_mappings = build_ffmpeg_filter_chain(
                video_width, video_height, split_count, orientation,
                srt_ip, srt_port, sei, group_name, persistent_streams
            )
            
            ffmpeg_cmd.extend(["-filter_complex", filter_complex_str])
            ffmpeg_cmd.extend(output_mappings)
            
            # Add split streams to URLs
            for i in range(split_count):
                stream_name = f"test{i}"
                if stream_name in persistent_streams:
                    stream_id = persistent_streams[stream_name]
                    stream_path = f"live/{group_name}/{stream_id}"
                    available_streams.append(stream_path)
                    client_stream_urls[stream_name] = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={stream_path},m=request"
        else:
            # Only full stream
            ffmpeg_cmd.extend([
                "-map", "0:v",
                "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency",
                "-bsf:v", f"h264_metadata=sei_user_data={sei}",
                "-pes_payload_size", "0", "-bf", "0", "-g", "30",
                "-f", "mpegts", f"srt://{srt_ip}:{srt_port}?streamid=#!::r={full_stream_path},m=publish"
            ])
        
        logger.info(f"🎬 FFmpeg command: {' '.join(ffmpeg_cmd)}")
        
        # Start FFmpeg process
        try:
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            logger.info(f"✅ FFmpeg started with PID: {process.pid}")
            
            # Start monitoring thread (but don't store state)
            def monitor_ffmpeg_output(process, group_name):
                try:
                    while process.poll() is None:
                        if process.stderr:
                            line = process.stderr.readline()
                            if line:
                                logger.info(f"FFmpeg[{group_name}]: {line.strip()}")
                    
                    exit_code = process.returncode
                    if exit_code == 0:
                        logger.info(f"✅ FFmpeg for group '{group_name}' ended successfully")
                    else:
                        logger.error(f"💥 FFmpeg for group '{group_name}' ended with exit code: {exit_code}")
                        
                except Exception as e:
                    logger.error(f"❌ Error monitoring FFmpeg: {e}")
            
            monitor_thread = threading.Thread(
                target=monitor_ffmpeg_output,
                args=(process, group_name),
                daemon=True
            )
            monitor_thread.start()
            
            # Wait to ensure process starts
            time.sleep(1.0)
            
            if process.poll() is not None:
                exit_code = process.returncode
                stderr_output = process.stderr.read() if process.stderr else ""
                
                return jsonify({
                    "error": f"FFmpeg failed immediately with exit code {exit_code}",
                    "stderr": stderr_output,
                    "ffmpeg_command": " ".join(ffmpeg_cmd)
                }), 500
            
            return jsonify({
                "message": f"SRT streaming started for group '{group_name}'",
                "group_id": group_id,
                "group_name": group_name,
                "process_id": process.pid,
                "screen_count": screen_count,
                "orientation": orientation,
                "persistent_streams": persistent_streams,
                "available_streams": available_streams,
                "client_stream_urls": client_stream_urls,
                "status": "active",
                "split_count": split_count,
                "video_source": video_source,
                "srt_port": srt_port,
                "test_result": test_result
            }), 200
            
        except Exception as e:
            logger.error(f"Error starting FFmpeg: {e}")
            return jsonify({"error": f"Failed to start FFmpeg: {str(e)}"}), 500
        
    except Exception as e:
        logger.error(f"❌ Error in stateless start_group_srt: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@stream_bp.route("/stop_group_srt", methods=["POST"])
def stop_group_srt():
    """Stop SRT streaming for a group - Stateless"""
    try:
        data = request.get_json() or {}
        group_id = data.get("group_id")
        
        logger.info(f"🛑 STOP STATELESS SRT: group_id={group_id}")
        
        if not group_id:
            return jsonify({"error": "group_id is required"}), 400
        
        # Discover group from Docker
        group = discover_group_from_docker(group_id)
        
        if not group:
            return jsonify({
                "error": f"Group '{group_id}' not found in Docker containers"
            }), 404
        
        group_name = group.get("name", group_id)
        
        # Find and stop FFmpeg processes
        ffmpeg_processes = find_running_ffmpeg_for_group(group_id, group_name)
        stopped_processes = []
        
        for proc_info in ffmpeg_processes:
            try:
                process = psutil.Process(proc_info["pid"])
                process.terminate()
                
                try:
                    process.wait(timeout=10)
                    logger.info(f"✅ FFmpeg process {proc_info['pid']} terminated gracefully")
                except psutil.TimeoutExpired:
                    logger.warning(f"⚠️ Force killing FFmpeg process {proc_info['pid']}")
                    process.kill()
                
                stopped_processes.append(proc_info["pid"])
                
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                logger.warning(f"Process {proc_info['pid']} no longer exists: {e}")
                continue
        
        if stopped_processes:
            return jsonify({
                "message": f"SRT streaming stopped for group '{group_name}'",
                "group_id": group_id,
                "group_name": group_name,
                "stopped_processes": stopped_processes,
                "status": "inactive"
            }), 200
        else:
            return jsonify({
                "message": f"No active streaming found for group '{group_name}'",
                "group_id": group_id,
                "group_name": group_name,
                "status": "inactive"
            }), 200
        
    except Exception as e:
        logger.error(f"❌ Error stopping stateless SRT: {e}")
        return jsonify({"error": str(e)}), 500

@stream_bp.route("/get_group_status", methods=["GET"])
def get_group_status():
    """Get status of all groups - Pure Docker Discovery"""
    try:
        group_id = request.args.get('group_id')
        
        # Find all multiscreen Docker containers
        cmd = ["docker", "ps", "--format", "json", "--filter", "label=multiscreen.group.id"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            return jsonify({"error": "Failed to query Docker containers"}), 500
        
        containers = []
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                try:
                    containers.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        
        groups_status = {}
        
        for container in containers:
            # Get detailed info
            inspect_cmd = ["docker", "inspect", container["ID"]]
            inspect_result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=5)
            
            if inspect_result.returncode != 0:
                continue
                
            container_info = json.loads(inspect_result.stdout)[0]
            labels = container_info.get("Config", {}).get("Labels", {})
            
            gid = labels.get("multiscreen.group.id")
            if not gid or (group_id and gid != group_id):
                continue
                
            group_name = labels.get("multiscreen.group.name", f"group_{gid}")
            
            # Check for running FFmpeg
            ffmpeg_processes = find_running_ffmpeg_for_group(gid, group_name)
            
            # Get persistent streams
            persistent_streams = get_persistent_streams_for_group(gid, group_name, 0)
            
            groups_status[gid] = {
                "group_id": gid,
                "group_name": group_name,
                "docker_running": container_info.get("State", {}).get("Running", False),
                "docker_status": container_info.get("State", {}).get("Status", "unknown"),
                "streaming": len(ffmpeg_processes) > 0,
                "ffmpeg_processes": ffmpeg_processes,
                "persistent_streams": persistent_streams,
                "screen_count": int(labels.get("multiscreen.group.screen_count", "2")),
                "orientation": labels.get("multiscreen.group.orientation", "horizontal"),
                "ports": {
                    "srt_port": int(labels.get("multiscreen.group.srt_port", "10080")),
                    "api_port": int(labels.get("multiscreen.group.api_port", "8080")),
                    "http_port": int(labels.get("multiscreen.group.http_port", "1985")),
                    "rtmp_port": int(labels.get("multiscreen.group.rtmp_port", "1935"))
                }
            }
        
        return jsonify({
            "groups": groups_status,
            "total_groups": len(groups_status),
            "active_streams": len([g for g in groups_status.values() if g["streaming"]]),
            "timestamp": time.time()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting group status: {e}")
        return jsonify({"error": str(e)}), 500

@stream_bp.route("/test_srt_connection", methods=["POST"])
def test_srt_connection():
    """Test SRT connection for a group - Stateless"""
    try:
        data = request.get_json() or {}
        group_id = data.get("group_id")
        
        if not group_id:
            return jsonify({"error": "group_id is required"}), 400
        
        # Discover group from Docker
        group = discover_group_from_docker(group_id)
        
        if not group:
            return jsonify({
                "error": f"Group '{group_id}' not found in Docker containers"
            }), 404
        
        group_name = group.get("name", group_id)
        ports = group.get("ports", {})
        srt_port = ports.get("srt_port", 10080)
        srt_ip = data.get("srt_ip", "127.0.0.1")
        sei = data.get("sei", "681d5c8f-80cd-4847-930a-99b9484b4a32+000000")
        
        # Test SRT connection
        test_result = test_ffmpeg_srt_connection(srt_ip, srt_port, group_name, sei)
        
        return jsonify({
            "group_id": group_id,
            "group_name": group_name,
            "test_result": test_result,
            "docker_running": group.get("docker_running", False),
            "srt_endpoint": f"{srt_ip}:{srt_port}",
            "timestamp": time.time()
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error testing SRT connection: {e}")
        return jsonify({"error": str(e)}), 500

# Helper functions for other modules
def stop_group_streams(group_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Helper function to stop streams for a group (called by group management)
    Stateless version - just find and kill processes
    """
    try:
        group_id = group_data.get("id")
        group_name = group_data.get("name", "unknown")
        
        logger.info(f"🛑 Stopping streams for group: {group_name} (ID: {group_id})")
        
        # Find and stop FFmpeg processes
        ffmpeg_processes = find_running_ffmpeg_for_group(group_id, group_name)
        stopped_processes = []
        
        for proc_info in ffmpeg_processes:
            try:
                process = psutil.Process(proc_info["pid"])
                process.terminate()
                
                try:
                    process.wait(timeout=10)
                    logger.info(f"✅ FFmpeg process {proc_info['pid']} terminated gracefully")
                except psutil.TimeoutExpired:
                    logger.warning(f"⚠️ Force killing FFmpeg process {proc_info['pid']}")
                    process.kill()
                
                stopped_processes.append(proc_info["pid"])
                
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return {
            "success": True,
            "message": f"Stopped {len(stopped_processes)} processes for group '{group_name}'",
            "stopped_processes": stopped_processes
        }
        
    except Exception as e:
        logger.error(f"Error stopping group streams: {e}")
        return {
            "success": False,
            "error": str(e)
        }