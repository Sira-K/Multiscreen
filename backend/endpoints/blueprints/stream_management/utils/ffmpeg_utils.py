import os
import logging

logger = logging.getLogger(__name__)

def find_ffmpeg_executable() -> str:
    """Find FFmpeg executable path"""
    custom_paths = [
        "./cmake-build-debug/external/Install/bin/ffmpeg",
        "./build/external/Install/bin/ffmpeg",
        "ffmpeg"
    ]
    
    for path in custom_paths:
        if os.path.exists(path) or path == "ffmpeg":
            return path
    
    raise FileNotFoundError("FFmpeg executable not found")