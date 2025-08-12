"""
Stream Manager Service

Core stream management functionality for multi-screen and split-screen streaming.
"""

import logging
import psutil
from typing import Dict, List, Optional, Tuple
from .docker_service import DockerService
from .ffmpeg_service import FFmpegService
from .srt_service import SRTService

logger = logging.getLogger(__name__)


class StreamManager:
    """Manages video streaming operations for multi-screen displays"""
    
    def __init__(self):
        self.docker_service = DockerService()
        self.ffmpeg_service = FFmpegService()
        self.srt_service = SRTService()
    
    def discover_group(self, group_id: str) -> Optional[Dict]:
        """Discover Docker group information"""
        try:
            return self.docker_service.discover_group(group_id)
        except Exception as e:
            logger.error(f"Failed to discover group {group_id}: {e}")
            return None
    
    def check_existing_streams(self, group_id: str, group_name: str, container_id: str) -> List[Dict]:
        """Check for existing FFmpeg processes for a group"""
        try:
            from ..blueprints.stream_management import find_running_ffmpeg_for_group_strict
            return find_running_ffmpeg_for_group_strict(group_id, group_name, container_id)
        except Exception as e:
            logger.error(f"Failed to check existing streams: {e}")
            return []
    
    def validate_video_file(self, video_file: str) -> Tuple[bool, str]:
        """Validate video file accessibility and format"""
        try:
            from ..blueprints.stream_management import validate_video_file
            return validate_video_file(video_file), video_file
        except Exception as e:
            logger.error(f"Video validation failed: {e}")
            return False, str(e)
    
    def test_srt_connection(self, srt_ip: str, srt_port: int) -> bool:
        """Test SRT server connectivity"""
        try:
            return self.srt_service.test_connection(srt_ip, srt_port)
        except Exception as e:
            logger.error(f"SRT connection test failed: {e}")
            return False
    
    def start_stream_process(self, ffmpeg_cmd: List[str], stream_type: str, group_name: str) -> Optional[int]:
        """Start FFmpeg streaming process"""
        try:
            import subprocess
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            logger.info(f"✅ {stream_type} process started with PID: {process.pid}")
            return process.pid
            
        except Exception as e:
            logger.error(f"Failed to start {stream_type} process: {e}")
            return None
    
    def monitor_stream_startup(self, process, stream_type: str, timeout: int = 10) -> Tuple[bool, bool]:
        """Monitor FFmpeg process startup"""
        try:
            from ..blueprints.stream_management import monitor_ffmpeg
            return monitor_ffmpeg(process, stream_type, timeout, 30)
        except Exception as e:
            logger.error(f"Stream monitoring failed: {e}")
            return False, False
    
    def stop_stream_process(self, pid: int) -> bool:
        """Stop a specific stream process"""
        try:
            process = psutil.Process(pid)
            process.terminate()
            
            try:
                process.wait(timeout=5)
                logger.info(f"✅ Process {pid} terminated gracefully")
                return True
            except psutil.TimeoutExpired:
                process.kill()
                logger.info(f"⚠️  Process {pid} had to be killed")
                return True
                
        except psutil.NoSuchProcess:
            logger.info(f"Process {pid} already terminated")
            return True
        except Exception as e:
            logger.error(f"Failed to stop process {pid}: {e}")
            return False
    
    def get_stream_status(self, group_id: str) -> Dict:
        """Get current streaming status for a group"""
        try:
            group = self.discover_group(group_id)
            if not group:
                return {"error": f"Group '{group_id}' not found"}
            
            group_name = group.get("name", group_id)
            container_id = group.get("container_id")
            running_processes = self.check_existing_streams(group_id, group_name, container_id)
            
            return {
                "group_id": group_id,
                "group_name": group_name,
                "is_streaming": len(running_processes) > 0,
                "active_processes": len(running_processes),
                "processes": running_processes
            }
            
        except Exception as e:
            logger.error(f"Failed to get stream status: {e}")
            return {"error": str(e)}
