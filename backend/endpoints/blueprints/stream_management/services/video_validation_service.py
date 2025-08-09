import os
import logging
from typing import List, Optional
from flask import current_app
from ..models.stream_config import VideoFileConfig

logger = logging.getLogger(__name__)

class VideoValidationService:
    """Service for validating video files and paths"""
    
    @staticmethod
    def validate_video_files(video_files_config: List[VideoFileConfig]) -> List[VideoFileConfig]:
        """Validate and resolve paths for video files"""
        uploads_dir = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        resized_dir = current_app.config.get('DOWNLOAD_FOLDER', 'resized_video')
        
        for video_config in video_files_config:
            file_name = video_config.file
            
            if not file_name:
                raise ValueError(f"Missing file name for screen {video_config.screen}")
            
            logger.info(f"Validating screen {video_config.screen}: {file_name}")
            
            # Resolve file path
            if file_name.startswith('uploads/'):
                file_path = file_name
            else:
                upload_path = os.path.join(uploads_dir, file_name)
                resized_path = os.path.join(resized_dir, file_name)
                
                if os.path.exists(upload_path):
                    file_path = upload_path
                    logger.info(f"Found in uploads: {upload_path}")
                elif os.path.exists(resized_path):
                    file_path = resized_path
                    logger.info(f"Found in resized: {resized_path}")
                else:
                    logger.error(f"File not found: {file_name}")
                    raise FileNotFoundError(f"Video file not found: {file_name}")
            
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Video file path doesn't exist: {file_path}")
            
            video_config.file_path = file_path
        
        return video_files_config
    
    @staticmethod
    def validate_single_video_file(video_file: str) -> str:
        """Validate and resolve path for a single video file"""
        uploads_dir = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        resized_dir = current_app.config.get('DOWNLOAD_FOLDER', 'resized_video')
        
        logger.info(f"Validating video file: {video_file}")
        
        if video_file.startswith('uploads/'):
            file_path = video_file
        else:
            upload_path = os.path.join(uploads_dir, video_file)
            resized_path = os.path.join(resized_dir, video_file)
            
            if os.path.exists(upload_path):
                file_path = upload_path
                logger.info(f"Found in uploads: {upload_path}")
            elif os.path.exists(resized_path):
                file_path = resized_path
                logger.info(f"Found in resized: {resized_path}")
            else:
                logger.error(f"File not found: {video_file}")
                raise FileNotFoundError(f"Video file not found: {video_file}")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Video file path doesn't exist: {file_path}")
        
        logger.info("Video file validated")
        return file_path