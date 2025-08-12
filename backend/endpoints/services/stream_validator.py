"""
Stream Validator Service

Validates input parameters for stream operations.
"""

import logging
import os
from typing import Dict, List

logger = logging.getLogger(__name__)


class StreamValidator:
    """Validates stream operation inputs"""
    
    def __init__(self):
        self.supported_video_formats = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
        self.max_video_files = 10
        self.max_file_size_mb = 1000  # 1GB
    
    def validate_split_screen_request(self, group_id: str, video_file: str, **kwargs) -> Dict:
        """Validate split-screen stream request"""
        try:
            # Validate group ID
            if not group_id or not isinstance(group_id, str):
                return {
                    "valid": False,
                    "message": "group_id is required and must be a string"
                }
            
            # Validate video file
            if not video_file or not isinstance(video_file, str):
                return {
                    "valid": False,
                    "message": "video_file is required and must be a string"
                }
            
            # Validate video file path
            video_validation = self._validate_video_file_path(video_file)
            if not video_validation["valid"]:
                return video_validation
            
            # Validate optional parameters
            optional_validation = self._validate_optional_split_screen_params(**kwargs)
            if not optional_validation["valid"]:
                return optional_validation
            
            return {"valid": True}
            
        except Exception as e:
            logger.error(f"Split-screen validation error: {e}")
            return {
                "valid": False,
                "message": f"Validation error: {str(e)}"
            }
    
    def validate_multi_video_request(self, group_id: str, video_files: List[str], **kwargs) -> Dict:
        """Validate multi-video stream request"""
        try:
            # Validate group ID
            if not group_id or not isinstance(group_id, str):
                return {
                    "valid": False,
                    "message": "group_id is required and must be a string"
                }
            
            # Validate video files list
            if not video_files or not isinstance(video_files, list):
                return {
                    "valid": False,
                    "message": "video_files is required and must be a list"
                }
            
            if len(video_files) == 0:
                return {
                    "valid": False,
                    "message": "At least one video file is required"
                }
            
            if len(video_files) > self.max_video_files:
                return {
                    "valid": False,
                    "message": f"Maximum {self.max_video_files} video files allowed"
                }
            
            # Validate each video file
            for i, video_file in enumerate(video_files):
                if not isinstance(video_file, str):
                    return {
                        "valid": False,
                        "message": f"Video file {i} must be a string"
                    }
                
                video_validation = self._validate_video_file_path(video_file)
                if not video_validation["valid"]:
                    return video_validation
            
            # Validate optional parameters
            optional_validation = self._validate_optional_multi_video_params(**kwargs)
            if not optional_validation["valid"]:
                return optional_validation
            
            return {"valid": True}
            
        except Exception as e:
            logger.error(f"Multi-video validation error: {e}")
            return {
                "valid": False,
                "message": f"Validation error: {str(e)}"
            }
    
    def validate_stop_request(self, group_id: str) -> Dict:
        """Validate stop stream request"""
        try:
            if not group_id or not isinstance(group_id, str):
                return {
                    "valid": False,
                    "message": "group_id is required and must be a string"
                }
            
            return {"valid": True}
            
        except Exception as e:
            logger.error(f"Stop request validation error: {e}")
            return {
                "valid": False,
                "message": f"Validation error: {str(e)}"
            }
    
    def _validate_video_file_path(self, video_file: str) -> Dict:
        """Validate individual video file path"""
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
                    return {
                        "valid": False,
                        "message": f"Video file not found: {video_file}"
                    }
                video_file = uploads_path
            
            # Check file extension
            file_ext = os.path.splitext(video_file)[1].lower()
            if file_ext not in self.supported_video_formats:
                return {
                    "valid": False,
                    "message": f"Unsupported video format: {file_ext}. Supported: {', '.join(self.supported_video_formats)}"
                }
            
            # Check file size
            file_size_mb = os.path.getsize(video_file) / (1024 * 1024)
            if file_size_mb > self.max_file_size_mb:
                return {
                    "valid": False,
                    "message": f"Video file too large: {file_size_mb:.1f}MB. Maximum: {self.max_file_size_mb}MB"
                }
            
            return {"valid": True}
            
        except Exception as e:
            logger.error(f"Video file validation error: {e}")
            return {
                "valid": False,
                "message": f"Video file validation error: {str(e)}"
            }
    
    def _validate_optional_split_screen_params(self, **kwargs) -> Dict:
        """Validate optional split-screen parameters"""
        try:
            # Validate orientation
            orientation = kwargs.get("orientation", "horizontal")
            if orientation not in ["horizontal", "vertical", "grid"]:
                return {
                    "valid": False,
                    "message": f"Invalid orientation: {orientation}. Must be horizontal, vertical, or grid"
                }
            
            # Validate grid parameters if grid orientation
            if orientation == "grid":
                grid_rows = kwargs.get("grid_rows", 2)
                grid_cols = kwargs.get("grid_cols", 2)
                
                if not isinstance(grid_rows, int) or grid_rows < 1:
                    return {
                        "valid": False,
                        "message": "grid_rows must be a positive integer"
                    }
                
                if not isinstance(grid_cols, int) or grid_cols < 1:
                    return {
                        "valid": False,
                        "message": "grid_cols must be a positive integer"
                    }
            
            # Validate framerate
            framerate = kwargs.get("framerate", 30)
            if not isinstance(framerate, int) or framerate < 1 or framerate > 120:
                return {
                    "valid": False,
                    "message": "framerate must be between 1 and 120"
                }
            
            # Validate bitrate
            bitrate = kwargs.get("bitrate", "3000k")
            if not isinstance(bitrate, str) or not bitrate.endswith('k'):
                return {
                    "valid": False,
                    "message": "bitrate must be a string ending with 'k' (e.g., '3000k')"
                }
            
            return {"valid": True}
            
        except Exception as e:
            logger.error(f"Optional parameter validation error: {e}")
            return {
                "valid": False,
                "message": f"Parameter validation error: {str(e)}"
            }
    
    def _validate_optional_multi_video_params(self, **kwargs) -> Dict:
        """Validate optional multi-video parameters"""
        try:
            # Validate layout
            layout = kwargs.get("layout", "grid")
            if layout not in ["grid", "horizontal", "vertical"]:
                return {
                    "valid": False,
                    "message": f"Invalid layout: {layout}. Must be grid, horizontal, or vertical"
                }
            
            # Validate framerate
            framerate = kwargs.get("framerate", 30)
            if not isinstance(framerate, int) or framerate < 1 or framerate > 120:
                return {
                    "valid": False,
                    "message": "framerate must be between 1 and 120"
                }
            
            # Validate bitrate
            bitrate = kwargs.get("bitrate", "3000k")
            if not isinstance(bitrate, str) or not bitrate.endswith('k'):
                return {
                    "valid": False,
                    "message": "bitrate must be a string ending with 'k' (e.g., '3000k')"
                }
            
            return {"valid": True}
            
        except Exception as e:
            logger.error(f"Optional multi-video parameter validation error: {e}")
            return {
                "valid": False,
                "message": f"Parameter validation error: {str(e)}"
            }
