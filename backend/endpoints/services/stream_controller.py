"""
Stream Controller Service

Handles starting and stopping of video streams.
"""

import logging
from typing import Dict, List, Optional
from .stream_manager import StreamManager
from .stream_builder import StreamBuilder
from .stream_validator import StreamValidator

logger = logging.getLogger(__name__)


class StreamController:
    """Controls stream operations (start/stop)"""
    
    def __init__(self):
        self.stream_manager = StreamManager()
        self.stream_builder = StreamBuilder()
        self.stream_validator = StreamValidator()
    
    def start_split_screen_stream(self, group_id: str, video_file: str, **kwargs) -> Dict:
        """Start a split-screen streaming session"""
        try:
            logger.info("🚀 Starting split-screen stream...")
            
            # Validate inputs
            validation_result = self.stream_validator.validate_split_screen_request(
                group_id, video_file, **kwargs
            )
            if not validation_result["valid"]:
                return {"error": validation_result["message"]}
            
            # Discover group
            group = self.stream_manager.discover_group(group_id)
            if not group:
                return {"error": f"Group '{group_id}' not found"}
            
            group_name = group.get("name", group_id)
            container_id = group.get("container_id")
            
            # Check for existing streams
            existing_streams = self.stream_manager.check_existing_streams(
                group_id, group_name, container_id
            )
            if existing_streams:
                logger.info(f"⚠️  Found {len(existing_streams)} existing streams")
                return self._get_existing_stream_status(group_id, group_name, existing_streams)
            
            # Validate video file
            video_valid, video_path = self.stream_manager.validate_video_file(video_file)
            if not video_valid:
                return {"error": f"Video file validation failed: {video_path}"}
            
            # Get SRT configuration
            srt_config = self._get_srt_config(group)
            if not srt_config:
                return {"error": "Failed to get SRT configuration"}
            
            # Test SRT connection
            if not self.stream_manager.test_srt_connection(
                srt_config["ip"], srt_config["port"]
            ):
                return {"error": "SRT server connection failed"}
            
            # Build FFmpeg command
            ffmpeg_cmd = self.stream_builder.build_split_screen_command(
                video_path=video_path,
                group=group,
                srt_config=srt_config,
                **kwargs
            )
            
            # Start stream process
            pid = self.stream_manager.start_stream_process(
                ffmpeg_cmd, f"Split-Screen ({group_name})", group_name
            )
            if not pid:
                return {"error": "Failed to start FFmpeg process"}
            
            # Monitor startup
            startup_success, streaming_detected = self.stream_manager.monitor_stream_startup(
                pid, f"Split-Screen ({group_name})"
            )
            
            if not startup_success:
                return {"error": "Split-screen stream failed to start properly"}
            
            # Generate response
            response = self._generate_split_screen_response(
                group_id, group_name, srt_config, pid, **kwargs
            )
            
            logger.info(f"✅ Split-screen stream started successfully for group '{group_name}'")
            return response
            
        except Exception as e:
            logger.error(f"Failed to start split-screen stream: {e}")
            return {"error": str(e)}
    
    def start_multi_video_stream(self, group_id: str, video_files: List[str], **kwargs) -> Dict:
        """Start a multi-video streaming session"""
        try:
            logger.info("🚀 Starting multi-video stream...")
            
            # Validate inputs
            validation_result = self.stream_validator.validate_multi_video_request(
                group_id, video_files, **kwargs
            )
            if not validation_result["valid"]:
                return {"error": validation_result["message"]}
            
            # Discover group
            group = self.stream_manager.discover_group(group_id)
            if not group:
                return {"error": f"Group '{group_id}' not found"}
            
            group_name = group.get("name", group_id)
            container_id = group.get("container_id")
            
            # Check for existing streams
            existing_streams = self.stream_manager.check_existing_streams(
                group_id, group_name, container_id
            )
            if existing_streams:
                logger.info(f"⚠️  Found {len(existing_streams)} existing streams")
                return self._get_existing_stream_status(group_id, group_name, existing_streams)
            
            # Validate video files
            video_paths = []
            for video_file in video_files:
                video_valid, video_path = self.stream_manager.validate_video_file(video_file)
                if not video_valid:
                    return {"error": f"Video file validation failed: {video_path}"}
                video_paths.append(video_path)
            
            # Get SRT configuration
            srt_config = self._get_srt_config(group)
            if not srt_config:
                return {"error": "Failed to get SRT configuration"}
            
            # Test SRT connection
            if not self.stream_manager.test_srt_connection(
                srt_config["ip"], srt_config["port"]
            ):
                return {"error": "SRT server connection failed"}
            
            # Build FFmpeg command
            ffmpeg_cmd = self.stream_builder.build_multi_video_command(
                video_paths=video_paths,
                group=group,
                srt_config=srt_config,
                **kwargs
            )
            
            # Start stream process
            pid = self.stream_manager.start_stream_process(
                ffmpeg_cmd, f"Multi-Video ({group_name})", group_name
            )
            if not pid:
                return {"error": "Failed to start FFmpeg process"}
            
            # Monitor startup
            startup_success, streaming_detected = self.stream_manager.monitor_stream_startup(
                pid, f"Multi-Video ({group_name})"
            )
            
            if not startup_success:
                return {"error": "Multi-video stream failed to start properly"}
            
            # Generate response
            response = self._generate_multi_video_response(
                group_id, group_name, srt_config, pid, video_paths, **kwargs
            )
            
            logger.info(f"✅ Multi-video stream started successfully for group '{group_name}'")
            return response
            
        except Exception as e:
            logger.error(f"Failed to start multi-video stream: {e}")
            return {"error": str(e)}
    
    def stop_group_stream(self, group_id: str) -> Dict:
        """Stop all streams for a specific group"""
        try:
            logger.info(f"🛑 Stopping streams for group {group_id}...")
            
            # Discover group
            group = self.stream_manager.discover_group(group_id)
            if not group:
                return {"error": f"Group '{group_id}' not found"}
            
            group_name = group.get("name", group_id)
            container_id = group.get("container_id")
            
            # Find running processes
            running_processes = self.stream_manager.check_existing_streams(
                group_id, group_name, container_id
            )
            
            if not running_processes:
                return {
                    "message": f"No active streams found for group '{group_name}'",
                    "status": "already_stopped"
                }
            
            # Stop processes
            stopped_count = 0
            failed_count = 0
            
            for proc_info in running_processes:
                pid = proc_info["pid"]
                if self.stream_manager.stop_stream_process(pid):
                    stopped_count += 1
                else:
                    failed_count += 1
            
            # Clear active stream IDs
            self._clear_active_stream_ids(group_id)
            
            return {
                "message": f"Stopped streams for group '{group_name}'",
                "group_id": group_id,
                "group_name": group_name,
                "stopped_processes": stopped_count,
                "failed_processes": failed_count,
                "status": "stopped"
            }
            
        except Exception as e:
            logger.error(f"Failed to stop group streams: {e}")
            return {"error": str(e)}
    
    def _get_srt_config(self, group: Dict) -> Optional[Dict]:
        """Extract SRT configuration from group info"""
        try:
            ports = group.get("ports", {})
            srt_port = ports.get("srt_port")
            
            if not srt_port:
                logger.error("No SRT port found in group configuration")
                return None
            
            return {
                "ip": "127.0.0.1",
                "port": srt_port
            }
            
        except Exception as e:
            logger.error(f"Failed to get SRT config: {e}")
            return None
    
    def _get_existing_stream_status(self, group_id: str, group_name: str, existing_streams: List[Dict]) -> Dict:
        """Generate response for existing streams"""
        return {
            "message": f"Streaming already active for group '{group_name}'",
            "group_id": group_id,
            "group_name": group_name,
            "status": "already_active",
            "active_processes": len(existing_streams),
            "processes": existing_streams
        }
    
    def _generate_split_screen_response(self, group_id: str, group_name: str, srt_config: Dict, pid: int, **kwargs) -> Dict:
        """Generate response for split-screen stream"""
        return {
            "status": "active",
            "group_id": group_id,
            "group_name": group_name,
            "process_id": pid,
            "message": f"Split-screen SRT streaming started for group '{group_name}'"
        }
    
    def _generate_multi_video_response(self, group_id: str, group_name: str, srt_config: Dict, pid: int, video_paths: List[str], **kwargs) -> Dict:
        """Generate response for multi-video stream"""
        return {
            "status": "active",
            "group_id": group_id,
            "group_name": group_name,
            "process_id": pid,
            "message": f"Multi-video SRT streaming started for group '{group_name}'"
        }
    
    def _clear_active_stream_ids(self, group_id: str):
        """Clear active stream IDs for a group"""
        try:
            from ..blueprints.stream_management import clear_active_stream_ids
            clear_active_stream_ids(group_id)
        except Exception as e:
            logger.warning(f"Failed to clear active stream IDs: {e}")
