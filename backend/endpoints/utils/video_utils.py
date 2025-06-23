import subprocess
import logging
import shlex
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

def get_video_resolution(file_path: str) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """
    Get video dimensions and framerate using ffprobe
    
    Args:
        file_path: Path to the video file
        
    Returns:
        Tuple of (width, height, framerate) or (None, None, None) on error
    """
    try:
        # Use shlex to handle file paths with spaces properly
        cmd = [
            "ffprobe", 
            "-v", "error", 
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate",
            "-of", "default=noprint_wrappers=1:nokey=0", 
            file_path
        ]
        
        # Set timeout to prevent hanging
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=10  # 10 second timeout
        )
        
        if result.returncode != 0:
            logger.error(f"ffprobe error: {result.stderr}")
            return None, None, None
            
        # Parse the output
        metadata = {}
        for line in result.stdout.strip().split("\n"):
            if '=' in line:
                key, value = line.split('=', 1)  # Split on first = only
                metadata[key.strip()] = value.strip()
            
        # Extract values with proper error handling
        try:
            width = int(metadata.get("width", "0"))
            height = int(metadata.get("height", "0"))
        except (ValueError, TypeError):
            logger.error("Could not parse width/height as integers")
            return None, None, None
            
        # Extract framerate (often in the format "num/denom")
        framerate = 30  # Default fallback
        try:
            frame_rate_str = metadata.get("r_frame_rate", "30/1")
            
            if '/' in frame_rate_str:
                num, denom = frame_rate_str.split('/')
                framerate = round(float(num) / float(denom))
            else:
                framerate = round(float(frame_rate_str))
                
        except (ValueError, ZeroDivisionError):
            logger.warning(f"Could not parse framerate '{frame_rate_str}', using default 30fps")
            
        # Validate that we got reasonable values
        if width <= 0 or height <= 0:
            logger.error(f"Invalid dimensions: {width}x{height}")
            return None, None, None
            
        return width, height, framerate
        
    except subprocess.TimeoutExpired:
        logger.error("Timeout while running ffprobe")
        return None, None, None
    except Exception as e:
        logger.error(f"Error reading video metadata: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None

def ffmpeg_monitor_output(process):
    """Monitor and log ffmpeg output in real-time"""
    while process.poll() is None:  # While process is running
        output = process.stderr.readline()
        if output:
            logger.info(f"FFmpeg: {output.strip()}")
    
    # Process has ended
    logger.info(f"FFmpeg process ended with return code: {process.returncode}")
    
    # Read any remaining output
    remaining_output = process.stderr.read()
    if remaining_output:
        for line in remaining_output.strip().split('\n'):
            logger.info(f"FFmpeg: {line.strip()}")