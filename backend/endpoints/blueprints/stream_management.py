# File to store persistent ID mappings
PERSISTENT_IDS_FILE = "persistent_stream_ids.json"#!/usr/bin/env python3
"""
Modified streaming_management.py with persistent group and stream IDs
Ensures that group and stream IDs remain consistent across start/stop cycles
"""

import json
import os
import time
import uuid
import logging
import subprocess
import threading
import traceback
from typing import Dict, List, Tuple, Any, Optional
from flask import Blueprint, request, jsonify
import psutil

# Import utility functions at the top of the file
try:
    from utils.video_utils import get_video_resolution
    from utils.ffmpeg_utils import build_ffmpeg_filter_chain, calculate_section_info
    UTILS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Could not import utils: {e}")
    UTILS_AVAILABLE = False

from blueprints.client_management import get_available_videos

# Configure logger
logger = logging.getLogger(__name__)

def get_available_streams():
    """Get available streams based on connected clients - matches old behavior"""
    state = get_state()
    active_clients = 0
    
    if hasattr(state, 'clients'):
        current_time = time.time()
        for client in state.clients.values():
            if current_time - client.get("last_seen", 0) <= 60:
                active_clients += 1
    
    # Return format matching old code
    available_streams = ["live/test"]
    if active_clients > 1:
        for i in range(min(active_clients, 4)):  # Max 4 streams
            available_streams.append(f"live/test{i}")
    
    return {
        "available_streams": available_streams,
        "active_clients": active_clients,
        "max_screens": 4
    }

def find_video_file(requested_file: str = None) -> Tuple[str, bool]:
    """
    Find a video file to use for streaming - matches old behavior
    
    Args:
        requested_file: Specific file requested (optional)
        
    Returns:
        Tuple of (file_path, use_test_pattern)
    """
    from flask import current_app
    
    # First, try to use resized videos (preferred)
    download_folder = current_app.config.get('DOWNLOAD_FOLDER', 'resized_video')
    
    if requested_file:
        # Check if specific file exists in resized folder
        resized_path = os.path.join(download_folder, requested_file)
        if os.path.isfile(resized_path):
            logger.info(f"Using requested resized video: {resized_path}")
            return resized_path, False
            
        # Check if it exists with 2k_ prefix
        prefixed_name = f"2k_{requested_file}"
        prefixed_path = os.path.join(download_folder, prefixed_name)
        if os.path.isfile(prefixed_path):
            logger.info(f"Using prefixed resized video: {prefixed_path}")
            return prefixed_path, False
    
    # If no specific file requested, find any resized video
    if os.path.exists(download_folder):
        video_extensions = ('.mp4', '.mkv', '.avi', '.mov', '.webm')
        try:
            for filename in os.listdir(download_folder):
                if filename.lower().endswith(video_extensions):
                    file_path = os.path.join(download_folder, filename)
                    logger.info(f"Using available resized video: {file_path}")
                    return file_path, False
        except Exception as e:
            logger.warning(f"Error scanning resized videos folder: {e}")
    
    # Fallback: try raw videos folder
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'raw_video_file')
    
    if requested_file:
        raw_path = os.path.join(upload_folder, requested_file)
        if os.path.isfile(raw_path):
            logger.warning(f"Using raw video (resized version not found): {raw_path}")
            return raw_path, False
    
    # Find any raw video as last resort
    if os.path.exists(upload_folder):
        video_extensions = ('.mp4', '.mkv', '.avi', '.mov', '.webm')
        try:
            for filename in os.listdir(upload_folder):
                if filename.lower().endswith(video_extensions):
                    file_path = os.path.join(upload_folder, filename)
                    logger.warning(f"Using available raw video: {file_path}")
                    return file_path, False
        except Exception as e:
            logger.warning(f"Error scanning raw videos folder: {e}")
    
    # No video files found, use test pattern
    logger.info("No video files found, will use test pattern")
    return "", True

class PersistentIDManager:
    """Manages persistent group and stream IDs across application restarts"""
    
    def __init__(self, storage_file: str = PERSISTENT_IDS_FILE):
        self.storage_file = storage_file
        self.ids_data = self._load_ids()
        self._lock = threading.RLock()
    
    def _load_ids(self) -> Dict[str, Any]:
        """Load existing ID mappings from file"""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)
                    logger.info(f"Loaded persistent IDs from {self.storage_file}")
                    return data
        except Exception as e:
            logger.warning(f"Could not load persistent IDs: {e}")
        
        # Return default structure
        return {
            "groups": {},  # group_name -> group_id mapping
            "streams": {},  # group_id -> {stream_name -> stream_id} mapping
            "metadata": {
                "created_at": time.time(),
                "last_updated": time.time()
            }
        }
    
    def _save_ids(self):
        """Save current ID mappings to file"""
        try:
            with self._lock:
                self.ids_data["metadata"]["last_updated"] = time.time()
                
                # Create backup of existing file
                if os.path.exists(self.storage_file):
                    backup_file = f"{self.storage_file}.backup"
                    os.rename(self.storage_file, backup_file)
                
                # Write new data
                with open(self.storage_file, 'w') as f:
                    json.dump(self.ids_data, f, indent=2)
                
                logger.info(f"Saved persistent IDs to {self.storage_file}")
                
        except Exception as e:
            logger.error(f"Failed to save persistent IDs: {e}")
    
    def get_group_id(self, group_name: str) -> str:
        """Get persistent group ID for a group name"""
        with self._lock:
            if group_name not in self.ids_data["groups"]:
                # Generate new UUID for this group
                group_id = str(uuid.uuid4())
                self.ids_data["groups"][group_name] = group_id
                self.ids_data["streams"][group_id] = {}
                self._save_ids()
                logger.info(f"Created new persistent group ID {group_id} for group '{group_name}'")
            else:
                group_id = self.ids_data["groups"][group_name]
                logger.info(f"Using existing group ID {group_id} for group '{group_name}'")
            
            return group_id
    
    def get_stream_id(self, group_id: str, stream_name: str) -> str:
        """Get persistent stream ID for a stream within a group"""
        with self._lock:
            if group_id not in self.ids_data["streams"]:
                self.ids_data["streams"][group_id] = {}
            
            if stream_name not in self.ids_data["streams"][group_id]:
                # Generate new UUID for this stream
                stream_id = str(uuid.uuid4())
                self.ids_data["streams"][group_id][stream_name] = stream_id
                self._save_ids()
                logger.info(f"Created new persistent stream ID {stream_id} for stream '{stream_name}' in group {group_id}")
            else:
                stream_id = self.ids_data["streams"][group_id][stream_name]
                logger.info(f"Using existing stream ID {stream_id} for stream '{stream_name}' in group {group_id}")
            
            return stream_id
    
    def get_group_streams(self, group_id: str) -> Dict[str, str]:
        """Get all persistent stream mappings for a group"""
        with self._lock:
            return self.ids_data["streams"].get(group_id, {}).copy()
    
    def list_all_groups(self) -> Dict[str, str]:
        """Get all group name -> group_id mappings"""
        with self._lock:
            return self.ids_data["groups"].copy()
    
    def remove_group(self, group_name: str) -> bool:
        """Remove a group and its streams from persistent storage"""
        with self._lock:
            if group_name in self.ids_data["groups"]:
                group_id = self.ids_data["groups"][group_name]
                del self.ids_data["groups"][group_name]
                if group_id in self.ids_data["streams"]:
                    del self.ids_data["streams"][group_id]
                self._save_ids()
                logger.info(f"Removed persistent group '{group_name}' and its streams")
                return True
            return False
    
    def remove_stream(self, group_id: str, stream_name: str) -> bool:
        """Remove a specific stream from persistent storage"""
        with self._lock:
            if (group_id in self.ids_data["streams"] and 
                stream_name in self.ids_data["streams"][group_id]):
                del self.ids_data["streams"][group_id][stream_name]
                self._save_ids()
                logger.info(f"Removed persistent stream '{stream_name}' from group {group_id}")
                return True
            return False

# Global persistent ID manager
id_manager = PersistentIDManager()

# Blueprint for streaming management
stream_bp = Blueprint('streaming', __name__)

def get_state():
    """Get application state - this should be implemented according to your app structure"""
    # This is a placeholder - replace with your actual state management
    from flask import current_app
    return current_app.config.get('APP_STATE')

def get_or_create_persistent_streams_for_group(group_id: str, group_name: str, split_count: int) -> Dict[str, str]:
    """Get persistent stream IDs for a group, creating only what's needed like old code"""
    # For frontend compatibility, use the actual group_id as the persistent key
    persistent_key = f"group_{group_id}"
    
    # Create persistent streams for this group
    streams = {}
    
    # Always create the full stream
    streams["test"] = id_manager.get_stream_id(persistent_key, "test")
    
    # Create split streams only if we need them (like old code)
    for i in range(split_count):
        streams[f"test{i}"] = id_manager.get_stream_id(persistent_key, f"test{i}")
    
    return streams

def build_simple_group_ffmpeg_filter_chain(
    video_width: int,
    video_height: int,
    split_count: int,  # Changed from screen_count to split_count
    orientation: str,
    srt_ip: str,
    srt_port: int,
    sei: str,
    group_id: str,
    group_name: str
) -> Tuple[str, List[str]]:
    """
    Build FFmpeg filter chain for group-specific SRT streaming with persistent IDs
    Now matches old code behavior - only creates splits for active clients
    """
    filter_complex = []
    output_mappings = []
    
    # Get persistent streams for this group (only what we need)
    persistent_streams = get_or_create_persistent_streams_for_group(group_id, group_name, split_count)
    
    # Start with splitting the input (like old code)
    split_str = f"[0:v]split={split_count+1}[full]"
    for i in range(split_count):
        split_str += f"[part{i}]"
    filter_complex.append(split_str)
    
    # Calculate section sizes based on orientation (like old code)
    if orientation.lower() == "horizontal":
        section_width = video_width // split_count
        remainder = video_width % split_count
        
        for i in range(split_count):
            current_width = section_width + (remainder if i == split_count-1 else 0)
            start_x = i * section_width
            
            filter_complex.append(
                f"[part{i}]crop={current_width}:{video_height}:{start_x}:0[out{i}]"
            )
            
            # Use persistent stream ID instead of dynamic naming
            stream_name = f"test{i}"
            persistent_stream_id = persistent_streams[stream_name]
            
            output_mappings.extend([
                "-map", f"[out{i}]",
                "-an", "-c:v", "libx264",
                "-bsf:v", f"h264_metadata=sei_user_data={sei}",
                "-pes_payload_size", "0",
                "-bf", "0",
                "-g", "1",
                "-f", "mpegts", f"srt://{srt_ip}:{srt_port}?streamid=#!::r=live/{group_name}/{persistent_stream_id},m=publish"
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
            
            # Use persistent stream ID instead of dynamic naming
            stream_name = f"test{i}"
            persistent_stream_id = persistent_streams[stream_name]
            
            output_mappings.extend([
                "-map", f"[out{i}]",
                "-an", "-c:v", "libx264",
                "-bsf:v", f"h264_metadata=sei_user_data={sei}",
                "-pes_payload_size", "0",
                "-bf", "0",
                "-g", "1",
                "-f", "mpegts", f"srt://{srt_ip}:{srt_port}?streamid=#!::r=live/{group_name}/{persistent_stream_id},m=publish"
            ])
    
    # Always add the full video output with persistent ID
    full_stream_id = persistent_streams["test"]
    output_mappings.extend([
        "-map", "[full]",
        "-an", "-c:v", "libx264",
        "-bsf:v", f"h264_metadata=sei_user_data={sei}",
        "-pes_payload_size", "0",
        "-bf", "0",
        "-g", "1",
        "-f", "mpegts", f"srt://{srt_ip}:{srt_port}?streamid=#!::r=live/{group_name}/{full_stream_id},m=publish"
    ])
    
    # Join filter parts with semicolons, but remove empty parts and trailing semicolons
    filter_str = ";".join([f for f in filter_complex if f.strip()])
    
    return filter_str, output_mappings

@stream_bp.route("/start_group_srt", methods=["POST"])
def start_group_srt():
    """Start SRT streaming for a group with persistent IDs"""
    try:
        state = get_state()
        data = request.get_json() or {}
        
        # Handle both frontend group_id and group_name
        frontend_group_id = data.get("group_id")
        group_name = data.get("group_name")
        
        # If frontend provides group_id, find the corresponding group
        if frontend_group_id and hasattr(state, 'groups') and frontend_group_id in state.groups:
            existing_group = state.groups[frontend_group_id]
            group_name = existing_group.get("name", f"group_{frontend_group_id}")
            group_id = frontend_group_id
            logger.info(f"Using existing frontend group ID: {group_id} with name: {group_name}")
        else:
            # Fallback to creating/finding persistent group
            if not group_name:
                group_name = "default_group"
            group_id = id_manager.get_group_id(group_name)
            logger.info(f"Using persistent group ID: {group_id} for name: {group_name}")
        
        logger.info(f"Starting SRT stream for group '{group_name}' with ID: {group_id}")
        
        # Initialize groups if needed
        if not hasattr(state, 'groups'):
            state.groups = {}
        
        # Create or update group in state
        if group_id not in state.groups:
            state.groups[group_id] = {
                "id": group_id,
                "name": group_name,
                "created_at": time.time(),
                "status": "inactive",
                "clients": {},
                "ffmpeg_process_id": None
            }
        else:
            state.groups[group_id]["name"] = group_name
        
        group = state.groups[group_id]
        
        # Check if group already has a running SRT stream
        existing_process_id = group.get("ffmpeg_process_id")
        if existing_process_id:
            try:
                process = psutil.Process(existing_process_id)
                if process.is_running():
                    return jsonify({
                        "message": f"Group '{group_name}' already has a running SRT stream",
                        "group_id": group_id,
                        "process_id": existing_process_id,
                        "persistent_streams": get_or_create_persistent_streams_for_group(group_id, group_name, 2)
                    }), 200
            except:
                group["ffmpeg_process_id"] = None
        
        # Get group configuration
        screen_count = data.get("screen_count", group.get("screen_count", 2))
        orientation = data.get("orientation", group.get("orientation", "horizontal"))
        srt_ip = data.get("srt_ip", getattr(state, 'srt_ip', '127.0.0.1'))
        srt_port = data.get("srt_port", group.get("srt_port", 10080))
        
        # Video configuration
        video_file = data.get("video_file")
        enable_looping = data.get("enable_looping", True)
        video_width = data.get("video_width", 3840)
        video_height = data.get("video_height", 1080)
        framerate = data.get("framerate", 30)
        
        # SEI identifier
        sei = data.get("sei", "681d5c8f-80cd-4847-930a-99b9484b4a32+000000")
        
        # Update group configuration
        group.update({
            "screen_count": screen_count,
            "orientation": orientation,
            "srt_port": srt_port,
            "video_width": video_width,
            "video_height": video_height
        })
        
        logger.info(f"Group config - Screens: {screen_count}, Orientation: {orientation}, SRT Port: {srt_port}")
        
        # ===== GET ACTIVE CLIENTS (like old code) =====
        streams_info = get_available_streams()
        available_streams_info = streams_info["available_streams"]
        active_client_count = streams_info["active_clients"]
        
        logger.info(f"Active clients: {active_client_count}")
        logger.info(f"Available streams: {available_streams_info}")
        
        # Calculate split_count based on active clients (like old code)
        if active_client_count <= 1:
            split_count = 0
            logger.info("Creating only full stream (1 or fewer clients)")
        else:
            split_count = min(active_client_count, screen_count)
            logger.info(f"Creating {split_count} split streams for {active_client_count} clients")
        
        # Find FFmpeg path
        default_ffmpeg_paths = [
            "./cmake-build-debug/external/Install/bin/ffmpeg",
            "/usr/bin/ffmpeg", 
            "/usr/local/bin/ffmpeg",
            "ffmpeg"
        ]
        
        ffmpeg_path = data.get("ffmpeg_path")
        if not ffmpeg_path:
            for path in default_ffmpeg_paths:
                if os.path.exists(path) or path == "ffmpeg":
                    ffmpeg_path = path
                    break
            
        if not ffmpeg_path:
            ffmpeg_path = "ffmpeg"
        
        logger.info(f"Using FFmpeg at: {ffmpeg_path}")
        
        # Input configuration for FFmpeg
        if video_file and os.path.exists(video_file):
            input_args = ["-re", "-i", video_file]
            if enable_looping:
                input_args.extend(["-stream_loop", "-1"])
        else:
            input_args = [
                "-re", "-f", "lavfi", 
                "-i", f"testsrc=s={video_width}x{video_height}:r={framerate}"
            ]
        
        # Get persistent streams first
        persistent_streams = get_or_create_persistent_streams_for_group(group_id, group_name, split_count)
        
        # Build filter chain with persistent IDs
        if split_count > 0:
            filter_complex_str, output_mappings = build_simple_group_ffmpeg_filter_chain(
                video_width, video_height, split_count, orientation,
                srt_ip, srt_port, sei, group_id, group_name
            )
        else:
            # Only full stream - simple case
            filter_complex_str = ""
            full_stream_id = persistent_streams["test"]
            output_mappings = [
                "-map", "0:v",
                "-an", "-c:v", "libx264",
                "-bsf:v", f"h264_metadata=sei_user_data={sei}",
                "-pes_payload_size", "0",
                "-bf", "0",
                "-g", "1",
                "-f", "mpegts", f"srt://{srt_ip}:{srt_port}?streamid=#!::r=live/{group_name}/{full_stream_id},m=publish"
            ]
        
        # Construct FFmpeg command
        ffmpeg_cmd = [ffmpeg_path, "-y"] + input_args
        
        if filter_complex_str:
            ffmpeg_cmd.extend(["-filter_complex", filter_complex_str])
        
        ffmpeg_cmd.extend(output_mappings)
        
        logger.info(f"FFmpeg command for group {group_name}: {' '.join(ffmpeg_cmd)}")
        
        # Start FFmpeg process
        try:
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            # Update group state for active streaming
            with getattr(state, 'groups_lock', threading.RLock()):
                state.groups[group_id]["ffmpeg_process_id"] = process.pid
                state.groups[group_id]["status"] = "active"
                state.groups[group_id]["current_video"] = video_file or "test_pattern"
                state.groups[group_id]["persistent_streams"] = persistent_streams
                
                # Create available streams list with persistent IDs and URLs
                available_streams = []
                client_stream_urls = {}
                
                # Always add full stream
                full_stream_id = persistent_streams["test"]
                full_stream_path = f"live/{group_name}/{full_stream_id}"
                available_streams.append(full_stream_path)
                client_stream_urls["test"] = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={full_stream_path},m=request"
                
                # Add split streams only if they were created
                for i in range(split_count):
                    stream_name = f"test{i}"
                    if stream_name in persistent_streams:
                        stream_id = persistent_streams[stream_name]
                        stream_path = f"live/{group_name}/{stream_id}"
                        available_streams.append(stream_path)
                        client_stream_urls[stream_name] = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={stream_path},m=request"
                
                state.groups[group_id]["available_streams"] = available_streams
                state.groups[group_id]["client_stream_urls"] = client_stream_urls
            
            # Start monitoring thread
            def monitor_group_output(process, group_id, group_name):
                try:
                    while process.poll() is None:
                        output = process.stderr.readline()
                        if output:
                            logger.info(f"FFmpeg[{group_name}]: {output.strip()}")
                    
                    logger.info(f"FFmpeg process for group '{group_name}' ended")
                    with getattr(state, 'groups_lock', threading.RLock()):
                        if group_id in state.groups:
                            state.groups[group_id]["ffmpeg_process_id"] = None
                            state.groups[group_id]["status"] = "inactive"
                except Exception as e:
                    logger.error(f"Error monitoring FFmpeg output for group {group_name}: {e}")
            
            monitor_thread = threading.Thread(
                target=monitor_group_output,
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
                "video_source": video_file or "test_pattern"
            }), 200
            
        except FileNotFoundError as e:
            logger.error(f"FFmpeg not found: {e}")
            return jsonify({
                "error": f"FFmpeg not found at {ffmpeg_path}",
                "suggestion": "Install FFmpeg or provide correct path in ffmpeg_path parameter",
                "tried_paths": default_ffmpeg_paths
            }), 500
        except Exception as e:
            logger.error(f"Error starting FFmpeg: {e}")
            return jsonify({"error": f"Failed to start FFmpeg: {str(e)}"}), 500
        
    except Exception as e:
        logger.error(f"Error starting group SRT with persistent IDs: {e}")
        traceback.print_exc()
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

# Make sure your /stop_group_srt endpoint in stream_management.py looks exactly like this:

@stream_bp.route("/stop_group_srt", methods=["POST"])
def stop_group_srt():
    """Stop SRT streaming for a specific group"""
    try:
        # Get app state
        state = get_state()
        
        # Get group ID from request
        data = request.get_json() or {}
        group_id = data.get("group_id")
        
        if not group_id:
            return jsonify({"error": "Missing group_id parameter"}), 400
            
        if not hasattr(state, 'groups') or group_id not in state.groups:
            return jsonify({"error": f"Group {group_id} not found"}), 404
            
        group = state.groups[group_id]
        group_name = group.get("name", group_id)
        process_id = group.get("ffmpeg_process_id")
        
        if not process_id:
            # No SRT stream running, but update status anyway
            with state.groups_lock if hasattr(state, 'groups_lock') else threading.RLock():
                state.groups[group_id]["status"] = "inactive"
                state.groups[group_id]["available_streams"] = []
            
            return jsonify({
                "message": f"No SRT stream was running for group '{group_name}'",
                "group_id": group_id,
                "group_name": group_name
            }), 200
        
        logger.info(f"Stopping SRT stream for group '{group_name}' (PID: {process_id})")
        
        try:
            process = psutil.Process(process_id)
            process.terminate()
            
            try:
                process.wait(timeout=5)
                logger.info(f"SRT process for group {group_name} terminated gracefully")
            except:
                logger.warning(f"SRT process for group {group_name} did not terminate gracefully, force killing")
                process.kill()
                
        except Exception as e:
            logger.error(f"Error stopping SRT process for group {group_name}: {e}")
        
        # 🔥 CRITICAL: Update group state to inactive
        with state.groups_lock if hasattr(state, 'groups_lock') else threading.RLock():
            state.groups[group_id]["ffmpeg_process_id"] = None
            state.groups[group_id]["status"] = "inactive"  # ← This is the key line
            state.groups[group_id]["available_streams"] = []
            
        logger.info(f"✅ Updated group '{group_name}' status to 'inactive'")
        
        return jsonify({
            "message": f"SRT stream stopped for group '{group_name}'",
            "group_id": group_id,
            "group_name": group_name,
            "status": "inactive"  # Return the new status
        }), 200
        
    except Exception as e:
        logger.error(f"Error stopping SRT for group: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@stream_bp.route("/get_group_streams/<group_name>", methods=["GET"])
def get_group_streams(group_name: str):
    """Get stream IDs for a group"""
    try:
        group_id = id_manager.get_group_id(group_name)
        persistent_streams = id_manager.get_group_streams(group_id)
        
        return jsonify({
            "group_name": group_name,
            "group_id": group_id,
            "streams": persistent_streams,
            "stream_urls": {
                stream_name: f"live/{group_name}/{stream_id}"
                for stream_name, stream_id in persistent_streams.items()
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting group streams: {e}")
        return jsonify({"error": str(e)}), 500

@stream_bp.route("/debug/list_all_groups", methods=["GET"])
def debug_list_all_groups():
    """Debug endpoint - List all groups with their IDs"""
    try:
        all_groups = id_manager.list_all_groups()
        groups_info = []
        
        for group_name, group_id in all_groups.items():
            streams = id_manager.get_group_streams(group_id)
            groups_info.append({
                "name": group_name,
                "id": group_id,
                "stream_count": len(streams),
                "streams": streams
            })
        
        return jsonify({
            "groups": groups_info,
            "total": len(all_groups),
            "note": "This is a debug endpoint showing persistent ID mappings"
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing groups: {e}")
        return jsonify({"error": str(e)}), 500

@stream_bp.route("/admin/reset_stream_ids", methods=["POST"])
def admin_reset_stream_ids():
    """Admin endpoint - Reset all persistent IDs (use with caution!)"""
    try:
        data = request.get_json() or {}
        confirm = data.get("confirm", False)
        
        if not confirm:
            return jsonify({
                "error": "This action will reset all persistent IDs. Send {\"confirm\": true} to proceed."
            }), 400
        
        # Create backup
        backup_file = f"{PERSISTENT_IDS_FILE}.backup.{int(time.time())}"
        if os.path.exists(PERSISTENT_IDS_FILE):
            import shutil
            shutil.copy2(PERSISTENT_IDS_FILE, backup_file)
            logger.info(f"Created backup: {backup_file}")
        
        # Reset ID manager
        global id_manager
        id_manager = PersistentIDManager()
        
        return jsonify({
            "message": "Persistent IDs reset successfully",
            "backup_created": backup_file if os.path.exists(backup_file) else None
        }), 200
        
    except Exception as e:
        logger.error(f"Error resetting IDs: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Test the persistent ID manager
    print("Testing Persistent ID Manager...")
    
    # Test group creation
    group1_id = id_manager.get_group_id("test_group_1")
    print(f"Group 1 ID: {group1_id}")
    
    # Test stream creation
    stream1_id = id_manager.get_stream_id(group1_id, "test0")
    stream2_id = id_manager.get_stream_id(group1_id, "test1")
    print(f"Stream IDs: {stream1_id}, {stream2_id}")
    
    # Test persistence
    group1_id_again = id_manager.get_group_id("test_group_1")
    stream1_id_again = id_manager.get_stream_id(group1_id, "test0")
    
    print(f"IDs are persistent: {group1_id == group1_id_again and stream1_id == stream1_id_again}")
    
    # List all data
    print("All groups:", id_manager.list_all_groups())
    print("Group streams:", id_manager.get_group_streams(group1_id))