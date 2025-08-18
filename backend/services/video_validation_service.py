"""
Video Validation Service

Simple video file validation for streaming operations.
"""

import os
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class VideoValidationService:
    """Service for validating video files"""
    
    @classmethod
    def validate_single_video_file(cls, video_file: str) -> str:
        """Validate a single video file and return the validated path"""
        try:
            # Check if file exists
            if not os.path.exists(video_file):
                # Try to find in uploads directory
                uploads_path = os.path.join(
                    os.path.dirname(__file__), 
                    "..", 
                    "uploads", 
                    os.path.basename(video_file)
                )
                if not os.path.exists(uploads_path):
                    raise FileNotFoundError(f"Video file not found: {video_file}")
                video_file = uploads_path
            
            # Check file extension
            file_ext = os.path.splitext(video_file)[1].lower()
            supported_formats = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
            
            if file_ext not in supported_formats:
                raise ValueError(f"Unsupported video format: {file_ext}")
            
            # Check file size
            file_size_mb = os.path.getsize(video_file) / (1024 * 1024)
            max_size_mb = 1000  # 1GB
            
            if file_size_mb > max_size_mb:
                raise ValueError(f"Video file too large: {file_size_mb:.1f}MB")
            
            logger.info(f"Video file validated: {video_file}")
            return video_file
            
        except Exception as e:
            logger.error(f"Video validation failed: {e}")
            raise
    
    @classmethod
    def validate_video_files(cls, video_files: list) -> list:
        """Validate multiple video files"""
        validated_files = []
        
        for video_file in video_files:
            try:
                validated_path = cls.validate_single_video_file(video_file)
                validated_files.append(validated_path)
            except Exception as e:
                logger.error(f"Failed to validate {video_file}: {e}")
                raise
        
        return validated_files
    
    @classmethod
    def get_video_info(cls, video_file: str) -> dict:
        """Get basic video file information"""
        try:
            if not os.path.exists(video_file):
                raise FileNotFoundError(f"Video file not found: {video_file}")
            
            stat_info = os.stat(video_file)
            
            return {
                "path": video_file,
                "size_mb": round(stat_info.st_size / (1024 * 1024), 2),
                "extension": os.path.splitext(video_file)[1].lower(),
                "filename": os.path.basename(video_file)
            }
            
        except Exception as e:
            logger.error(f"Failed to get video info: {e}")
            return {"error": str(e)}
