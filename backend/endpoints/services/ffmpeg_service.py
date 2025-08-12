"""
FFmpeg Service

Simple FFmpeg operations for video streaming.
"""

import subprocess
import time
import logging
import os
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


class FFmpegService:
    """Service for FFmpeg operations"""
    
    @classmethod
    def find_ffmpeg_executable(cls) -> str:
        """Find FFmpeg executable path"""
        # Common FFmpeg paths
        possible_paths = [
            "ffmpeg",
            "/usr/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
            "/opt/ffmpeg/bin/ffmpeg"
        ]
        
        for path in possible_paths:
            try:
                result = subprocess.run([path, "-version"], 
                                      capture_output=True, timeout=5)
                if result.returncode == 0:
                    logger.info(f"Found FFmpeg at: {path}")
                    return path
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
        
        # If not found, return default
        logger.warning("FFmpeg not found in common paths, using 'ffmpeg'")
        return "ffmpeg"
    
    @classmethod
    def test_ffmpeg_installation(cls) -> bool:
        """Test if FFmpeg is properly installed"""
        try:
            ffmpeg_path = cls.find_ffmpeg_executable()
            result = subprocess.run([ffmpeg_path, "-version"], 
                                  capture_output=True, timeout=10)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"FFmpeg test failed: {e}")
            return False
    
    @classmethod
    def get_ffmpeg_version(cls) -> str:
        """Get FFmpeg version"""
        try:
            ffmpeg_path = cls.find_ffmpeg_executable()
            result = subprocess.run([ffmpeg_path, "-version"], 
                                  capture_output=True, timeout=10)
            if result.returncode == 0:
                # Extract version from first line
                first_line = result.stdout.decode().split('\n')[0]
                return first_line
            return "Unknown"
        except Exception as e:
            logger.error(f"Failed to get FFmpeg version: {e}")
            return "Error"
    
    @classmethod
    def build_simple_command(cls, input_file: str, output_file: str, 
                           codec: str = "libx264", bitrate: str = "3000k") -> List[str]:
        """Build a simple FFmpeg command"""
        ffmpeg_path = cls.find_ffmpeg_executable()
        
        return [
            ffmpeg_path,
            "-y",  # Overwrite output
            "-i", input_file,
            "-c:v", codec,
            "-b:v", bitrate,
            "-preset", "fast",
            output_file
        ]
    
    @classmethod
    def run_command(cls, command: List[str], timeout: int = 300) -> Tuple[bool, str]:
        """Run an FFmpeg command and return success status and output"""
        try:
            logger.info(f"Running FFmpeg command: {' '.join(command[:5])}...")
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                logger.info("FFmpeg command completed successfully")
                return True, result.stdout
            else:
                logger.error(f"FFmpeg command failed: {result.stderr}")
                return False, result.stderr
                
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg command timed out")
            return False, "Command timed out"
        except Exception as e:
            logger.error(f"FFmpeg command error: {e}")
            return False, str(e)
    
    @classmethod
    def get_video_info(cls, video_file: str) -> Dict[str, Any]:
        """Get video file information"""
        try:
            ffmpeg_path = cls.find_ffmpeg_executable()
            command = [
                ffmpeg_path,
                "-i", video_file,
                "-f", "null",
                "-"
            ]
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Parse output for video info
            info = {}
            for line in result.stderr.split('\n'):
                if "Duration:" in line:
                    # Extract duration
                    duration_match = line.split("Duration: ")[1].split(",")[0]
                    info['duration'] = duration_match.strip()
                elif "Stream #0:0" in line and "Video:" in line:
                    # Extract video stream info
                    parts = line.split("Video: ")[1].split(",")
                    if len(parts) >= 2:
                        codec = parts[0].strip()
                        resolution = parts[1].strip()
                        info['codec'] = codec
                        info['resolution'] = resolution
                elif "Stream #0:1" in line and "Audio:" in line:
                    # Extract audio stream info
                    parts = line.split("Audio: ")[1].split(",")
                    if len(parts) >= 1:
                        codec = parts[0].strip()
                        info['audio_codec'] = codec
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to get video info: {e}")
            return {"error": str(e)}
    
    @classmethod
    def create_thumbnail(cls, video_file: str, output_file: str, 
                        time_position: str = "00:00:05") -> bool:
        """Create a thumbnail from video"""
        try:
            ffmpeg_path = cls.find_ffmpeg_executable()
            command = [
                ffmpeg_path,
                "-y",
                "-ss", time_position,
                "-i", video_file,
                "-vframes", "1",
                "-q:v", "2",
                output_file
            ]
            
            success, _ = cls.run_command(command, timeout=60)
            return success
            
        except Exception as e:
            logger.error(f"Failed to create thumbnail: {e}")
            return False
