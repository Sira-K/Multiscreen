# blueprints/stream_management.py
"""
Stream management with pure Docker discovery architecture.
No internal state - queries Docker to verify group existence and get configuration.
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
from typing import Dict, List, Any, Tuple, Optional

# Create blueprint
stream_bp = Blueprint('stream_management', __name__)

# Configure logger
logger = logging.getLogger(__name__)

# File to store persistent ID mappings
PERSISTENT_IDS_FILE = "persistent_stream_ids.json"

class PersistentIDManager:
    """Manages persistent IDs for groups and streams"""
    
    def __init__(self):
        self.ids_data = {"groups": {}, "streams": {}}
        self._lock = threading.RLock()
        self._load_ids()
    
    def _load_ids(self):
        """Load persistent IDs from file"""
        try:
            if os.path.exists(PERSISTENT_IDS_FILE):
                with open(PERSISTENT_IDS_FILE, 'r') as f:
                    self.ids_data = json.load(f)
                logger.info(f"Loaded persistent IDs from {PERSISTENT_IDS_FILE}")
            else:
                logger.info("No persistent IDs file found, starting fresh")
        except Exception as e:
            logger.error(f"Error loading persistent IDs: {e}")
            self.ids_data = {"groups": {}, "streams": {}}
    
    def _save_ids(self):
        """Save persistent IDs to file"""
        try:
            with open(PERSISTENT_IDS_FILE, 'w') as f:
                json.dump(self.ids_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving persistent IDs: {e}")
    
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

def get_group_from_docker(group_id: str) -> Optional[Dict[str, Any]]:
    """
    Get group information from Docker discovery
    
    Args:
        group_id: The group ID to find
        
    Returns:
        Group data dict or None if not found
    """
    try:
        from blueprints.docker_management import discover_groups
        
        discovery_result = discover_groups()
        if not discovery_result.get("success", False):
            logger.error(f"Failed to discover groups: {discovery_result.get('error')}")
            return None
        
        # Find the specific group
        for group in discovery_result.get("groups", []):
            if group.get("id") == group_id:
                return group
        
        logger.warning(f"Group {group_id} not found in Docker containers")
        return None
        
    except Exception as e:
        logger.error(f"Error getting group from Docker: {e}")
        return None

def get_active_clients_count() -> int:
    """Get count of active clients (placeholder - implement based on your client management)"""
    # This would typically query your client management system
    # For now, return a default value
    return 2

def find_ffmpeg_executable() -> str:
    """Find FFmpeg executable in common locations"""
    default_ffmpeg_paths = [
        "./cmake-build-debug/external/Install/bin/ffmpeg",
        "/usr/bin/ffmpeg", 
        "/usr/local/bin/ffmpeg",
        "ffmpeg"
    ]
    
    for path in default_ffmpeg_paths:
        if os.path.exists(path) or path == "ffmpeg":
            return path
    
    return "ffmpeg"  # Fallback to system PATH

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
    """
    Build FFmpeg filter chain for video splitting and streaming
    
    Args:
        video_width: Video width in pixels
        video_height: Video height in pixels  
        split_count: Number of split streams to create
        orientation: "horizontal", "vertical", or "grid"
        srt_ip: SRT server IP
        srt_port: SRT server port
        sei: SEI metadata string
        group_name: Group name for stream paths
        stream_ids: Dictionary mapping stream names to persistent IDs
        
    Returns:
        Tuple of (filter_complex_string, output_mappings_list)
    """
    filter_complex = []
    output_mappings = []
    
    if split_count == 0:
        # No splitting needed - just full stream
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
            
            # Use persistent stream ID
            stream_name = f"test{i}"
            stream_id = stream_ids[stream_name]
            
            output_mappings.extend([
                "-map", f"[out{i}]",
                "-an", "-c:v", "libx264",
                "-bsf:v", f"h264_metadata=sei_user_data={sei}",
                "-pes_payload_size", "0",
                "-bf", "0",
                "-g", "1",
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
            
            # Use persistent stream ID
            stream_name = f"test{i}"
            stream_id = stream_ids[stream_name]
            
            output_mappings.extend([
                "-map", f"[out{i}]",
                "-an", "-c:v", "libx264", 
                "-bsf:v", f"h264_metadata=sei_user_data={sei}",
                "-pes_payload_size", "0",
                "-bf", "0",
                "-g", "1",
                "-f", "mpegts", f"srt://{srt_ip}:{srt_port}?streamid=#!::r=live/{group_name}/{stream_id},m=publish"
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

@stream_bp.route("/start_group_srt", methods=["POST"])
def start_group_srt():
    """Start SRT streaming for a group - requires group to exist in Docker"""
    try:
        data = request.get_json() or {}
        
        # Extract required parameters
        group_id = data.get("group_id")
        video_file = data.get("video_file")
        
        logger.info(f"🚀 START GROUP SRT REQUEST: group_id={group_id}, video_file={video_file}")
        
        # Validation
        if not group_id:
            return jsonify({"error": "group_id is required"}), 400
        
        # Get group info from Docker discovery
        logger.info(f"🔍 Looking up group in Docker: {group_id}")
        group = get_group_from_docker(group_id)
        
        if not group:
            return jsonify({
                "error": f"Group '{group_id}' not found in Docker containers",
                "suggestion": "Create the group first using /create_group endpoint"
            }), 404
        
        group_name = group.get("name", group_id)
        logger.info(f"✅ Found group: {group_name}")
        
        # Check if Docker container is running
        if not group.get("docker_running", False):
            return jsonify({
                "error": f"Docker container for group '{group_name}' is not running",
                "suggestion": "Start the Docker container first",
                "docker_status": group.get("docker_status", "unknown")
            }), 400
        
        # Extract group configuration
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
        
        # SRT IP (use localhost since we're connecting to Docker container)
        srt_ip = data.get("srt_ip", "127.0.0.1")
        
        logger.info(f"📋 Group config - Screens: {screen_count}, Orientation: {orientation}, SRT Port: {srt_port}")
        
        # Get active clients to determine split count
        active_client_count = get_active_clients_count()
        
        # Calculate split_count based on active clients
        if active_client_count <= 1:
            split_count = 0
            logger.info("Creating only full stream (1 or fewer clients)")
        else:
            split_count = min(active_client_count, screen_count)
            logger.info(f"Creating {split_count} split streams for {active_client_count} clients")
        
        # Find FFmpeg path
        ffmpeg_path = data.get("ffmpeg_path", find_ffmpeg_executable())
        logger.info(f"Using FFmpeg at: {ffmpeg_path}")
        
        # Input configuration for FFmpeg
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
        
        # Create available streams list and URLs
        available_streams = []
        client_stream_urls = {}
        
        # Always add full stream
        full_stream_id = persistent_streams["test"]
        full_stream_path = f"live/{group_name}/{full_stream_id}"
        available_streams.append(full_stream_path)
        client_stream_urls["test"] = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={full_stream_path},m=request"
        
        # Add full stream output
        ffmpeg_cmd.extend([
            "-map", "0:v",
            "-an", "-c:v", "libx264",
            "-bsf:v", f"h264_metadata=sei_user_data={sei}",
            "-pes_payload_size", "0",
            "-bf", "0",
            "-g", "1",
            "-f", "mpegts", f"srt://{srt_ip}:{srt_port}?streamid=#!::r={full_stream_path},m=publish"
        ])
        
        # Add split streams if needed
        if split_count > 0:
            filter_complex_str, output_mappings = build_ffmpeg_filter_chain(
                video_width, video_height, split_count, orientation,
                srt_ip, srt_port, sei, group_name, persistent_streams
            )
            
            if filter_complex_str:
                ffmpeg_cmd.extend(["-filter_complex", filter_complex_str])
            
            ffmpeg_cmd.extend(output_mappings)
            
            # Add split streams to available streams
            for i in range(split_count):
                stream_name = f"test{i}"
                if stream_name in persistent_streams:
                    stream_id = persistent_streams[stream_name]
                    stream_path = f"live/{group_name}/{stream_id}"
                    available_streams.append(stream_path)
                    client_stream_urls[stream_name] = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={stream_path},m=request"
        
        logger.info(f"🔧 FFmpeg command: {' '.join(ffmpeg_cmd)}")
        
        # Start FFmpeg process
        try:
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            logger.info(f"✅ FFmpeg process started with PID: {process.pid}")
            
            # Start monitoring thread
            def monitor_ffmpeg_output(process, group_id, group_name):
                try:
                    while process.poll() is None:
                        output = process.stderr.readline()
                        if output:
                            logger.debug(f"FFmpeg[{group_name}]: {output.strip()}")
                    
                    logger.info(f"FFmpeg process for group '{group_name}' ended")
                    
                except Exception as e:
                    logger.error(f"Error monitoring FFmpeg output for group {group_name}: {e}")
            
            monitor_thread = threading.Thread(
                target=monitor_ffmpeg_output,
                args=(process, group_id, group_name),
                daemon=True
            )
            monitor_thread.start()
            
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
                "ffmpeg_command": " ".join(ffmpeg_cmd),
                "active_clients": active_client_count,
                "split_count": split_count,
                "video_source": video_source,
                "srt_port": srt_port,
                "docker_status": group.get("docker_status", "unknown")
            }), 200
            
        except FileNotFoundError:
            logger.error(f"FFmpeg not found at: {ffmpeg_path}")
            return jsonify({
                "error": f"FFmpeg not found at {ffmpeg_path}",
                "suggestion": "Install FFmpeg or provide correct path in ffmpeg_path parameter"
            }), 500
        except Exception as e:
            logger.error(f"Error starting FFmpeg: {e}")
            return jsonify({"error": f"Failed to start FFmpeg: {str(e)}"}), 500
        
    except Exception as e:
        logger.error(f"❌ Error in start_group_srt: {e}")
        traceback.print_exc()
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@stream_bp.route("/stop_group_srt", methods=["POST"])
def stop_group_srt():
    """Stop SRT streaming for a specific group"""
    try:
        data = request.get_json() or {}
        group_id = data.get("group_id")
        
        logger.info(f"🛑 STOP GROUP SRT REQUEST: group_id={group_id}")
        
        if not group_id:
            return jsonify({"error": "group_id is required"}), 400
        
        # Get group info from Docker discovery
        group = get_group_from_docker(group_id)
        
        if not group:
            return jsonify({
                "error": f"Group '{group_id}' not found in Docker containers"
            }), 404
        
        group_name = group.get("name", group_id)
        logger.info(f"🎯 Stopping streams for group: {group_name}")
        
        # Find and stop FFmpeg processes for this group
        stopped_processes = []
        
        try:
            # Look for FFmpeg processes that might be streaming for this group
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] and 'ffmpeg' in proc.info['name'].lower():
                        cmdline = ' '.join(proc.info['cmdline'] or [])
                        
                        # Check if this FFmpeg process is for our group
                        if group_name in cmdline or group_id in cmdline:
                            logger.info(f"🔍 Found FFmpeg process for group: PID {proc.info['pid']}")
                            
                            process = psutil.Process(proc.info['pid'])
                            process.terminate()
                            
                            # Wait for graceful termination
                            try:
                                process.wait(timeout=10)
                                logger.info(f"✅ FFmpeg process {proc.info['pid']} terminated gracefully")
                            except psutil.TimeoutExpired:
                                logger.warning(f"⚠️ Force killing FFmpeg process {proc.info['pid']}")
                                process.kill()
                            
                            stopped_processes.append(proc.info['pid'])
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except Exception as e:
            logger.error(f"Error finding FFmpeg processes: {e}")
        
        if stopped_processes:
            logger.info(f"✅ Stopped {len(stopped_processes)} FFmpeg processes for group '{group_name}'")
            return jsonify({
                "message": f"SRT streaming stopped for group '{group_name}'",
                "group_id": group_id,
                "group_name": group_name,
                "stopped_processes": stopped_processes,
                "status": "inactive"
            }), 200
        else:
            logger.info(f"ℹ️ No running FFmpeg processes found for group '{group_name}'")
            return jsonify({
                "message": f"No active streaming found for group '{group_name}'",
                "group_id": group_id,
                "group_name": group_name,
                "status": "inactive"
            }), 200
        
    except Exception as e:
        logger.error(f"❌ Error stopping group SRT: {e}")
        traceback.print_exc()
        return jsonify({
            "error": str(e)
        }), 500

def stop_group_streams(group_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Helper function to stop streams for a group (called by group management)
    
    Args:
        group_data: Group information
        
    Returns:
        Dict with success status and details
    """
    try:
        group_id = group_data.get("id")
        group_name = group_data.get("name", "unknown")
        
        logger.info(f"🛑 Stopping streams for group: {group_name} (ID: {group_id})")
        
        stopped_processes = []
        
        # Find and stop FFmpeg processes for this group
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and 'ffmpeg' in proc.info['name'].lower():
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    
                    # Check if this FFmpeg process is for our group
                    if group_name in cmdline or (group_id and group_id in cmdline):
                        logger.info(f"🔍 Found FFmpeg process for group: PID {proc.info['pid']}")
                        
                        process = psutil.Process(proc.info['pid'])
                        process.terminate()
                        
                        # Wait for graceful termination
                        try:
                            process.wait(timeout=10)
                            logger.info(f"✅ FFmpeg process {proc.info['pid']} terminated gracefully")
                        except psutil.TimeoutExpired:
                            logger.warning(f"⚠️ Force killing FFmpeg process {proc.info['pid']}")
                            process.kill()
                        
                        stopped_processes.append(proc.info['pid'])
                        
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