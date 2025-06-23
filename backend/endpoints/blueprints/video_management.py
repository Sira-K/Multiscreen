# Enhanced video_management.py with multiple file upload support
from flask import Blueprint, request, jsonify, current_app, send_from_directory
import traceback
import time
import logging
import os
import subprocess
import threading
import uuid
from werkzeug.utils import secure_filename
from typing import Tuple, Optional, Dict, Any, List

# Configure logger
logger = logging.getLogger(__name__)

# Create blueprint
video_bp = Blueprint('video_management', __name__)

# Global dictionary to track processing jobs
processing_jobs: Dict[str, Dict[str, Any]] = {}

def get_state():
    """Get application state from current app context"""
    return current_app.config['APP_STATE']

def validate_upload(file) -> Tuple[bool, Optional[str]]:
    """
    Validate an uploaded file
    
    Args:
        file: The file to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not file:
        return False, "No file provided"
        
    # Check file extension
    allowed_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.webm'}
    filename = file.filename.lower()
    file_ext = os.path.splitext(filename)[1]
    
    if file_ext not in allowed_extensions:
        return False, f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}"
    
    # Check file size (e.g., max 2GB per file)
    max_size = 2 * 1024 * 1024 * 1024  # 2GB in bytes
    if hasattr(file, 'content_length') and file.content_length and file.content_length > max_size:
        return False, f"File too large. Maximum size: 2GB"
    
    return True, None

def resize_video_async(job_id: str, input_path: str, output_path: str, original_filename: str):
    """
    Resize video to 2K resolution using ffmpeg in a background thread
    
    Args:
        job_id: Unique identifier for this processing job
        input_path: Path to the original video
        output_path: Path where resized video will be saved
        original_filename: Original filename for logging
    """
    try:
        # Update job status
        processing_jobs[job_id]['status'] = 'processing'
        processing_jobs[job_id]['progress'] = 0
        processing_jobs[job_id]['started_at'] = time.time()
        
        logger.info(f"Starting async video resize for job {job_id}: {original_filename}")
        
        # 2K resolution is typically 2048x1080, but we'll use 1920x1080 (1080p) as it's more standard
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-vf', 'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2',
            '-c:a', 'copy',  # Copy audio without re-encoding
            '-y',  # Overwrite output file
            '-progress', 'pipe:1',  # Enable progress output
            output_path
        ]
        
        logger.info(f"Resizing video: {' '.join(cmd)}")
        
        # Run FFmpeg with progress tracking
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            universal_newlines=True
        )
        
        # Monitor progress
        total_duration = None
        while process.poll() is None:
            line = process.stdout.readline()
            if line:
                # Parse FFmpeg progress output
                if line.startswith('out_time_ms='):
                    try:
                        time_ms = int(line.split('=')[1])
                        if total_duration:
                            progress = min(int((time_ms / total_duration) * 100), 90)
                            processing_jobs[job_id]['progress'] = progress
                    except (ValueError, IndexError):
                        pass
                elif line.startswith('progress='):
                    if 'end' in line:
                        processing_jobs[job_id]['progress'] = 95
            
            # Fallback progress increment
            if processing_jobs[job_id]['progress'] < 85:
                processing_jobs[job_id]['progress'] = min(processing_jobs[job_id]['progress'] + 2, 85)
            
            time.sleep(1)
        
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            processing_jobs[job_id]['status'] = 'completed'
            processing_jobs[job_id]['progress'] = 100
            processing_jobs[job_id]['output_path'] = output_path
            processing_jobs[job_id]['completed_at'] = time.time()
            
            # Get file size
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                processing_jobs[job_id]['size'] = file_size
                processing_jobs[job_id]['size_mb'] = round(file_size / (1024 * 1024), 2)
            
            logger.info(f"Successfully resized video for job {job_id}: {output_path}")
        else:
            processing_jobs[job_id]['status'] = 'failed'
            processing_jobs[job_id]['error'] = f"FFmpeg error: {stderr}"
            processing_jobs[job_id]['failed_at'] = time.time()
            logger.error(f"FFmpeg error for job {job_id}: {stderr}")
            
    except Exception as e:
        processing_jobs[job_id]['status'] = 'failed'
        processing_jobs[job_id]['error'] = f"Processing error: {str(e)}"
        processing_jobs[job_id]['failed_at'] = time.time()
        logger.error(f"Error processing video for job {job_id}: {e}")

@video_bp.route('/get_videos', methods=['GET'])
def get_videos():
    """
    Get a list of all video files in the resized videos directory
    Returns:
        JSON response with list of video files
    """
    try:
        # Get the download folder from app config (where resized videos are stored)
        download_folder = current_app.config.get('DOWNLOAD_FOLDER', 'resized_video')
        
        # Debug log
        logger.info(f"Looking for videos in: {download_folder}")
        
        # Ensure the directory exists
        if not os.path.exists(download_folder):
            os.makedirs(download_folder)
            logger.warning(f"Created resized videos directory {download_folder}")
        
        # Get all files in the directory
        files = os.listdir(download_folder)
        
        # Filter for video files (mp4, mkv, avi, mov, webm)
        video_extensions = ('.mp4', '.mkv', '.avi', '.mov', '.webm')
        video_files = [f for f in files if f.lower().endswith(video_extensions)]
        
        # Create a list of video file objects
        videos = []
        for video_file in video_files:
            video_path = os.path.join(download_folder, video_file)
            file_size = os.path.getsize(video_path)
            
            videos.append({
                'name': video_file,
                'path': f"/resized_videos/{video_file}",
                'size': file_size,
                'size_mb': round(file_size / (1024 * 1024), 2)  # Size in MB
            })
        
        logger.info(f"Found {len(videos)} resized video files")
        
        return jsonify({
            'success': True,
            'videos': videos
        })
    
    except Exception as e:
        logger.error(f"Error getting videos: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f"Error getting videos: {str(e)}",
            'videos': []
        }), 500

@video_bp.route('/upload_video', methods=['POST'])
def upload_video():
    """
    Upload a video file and start async processing to 2K
    Now supports both single and multiple file uploads
    Expects:
        file: The video file(s) in the request files
    Returns:
        JSON response with job ID(s) for tracking processing
    """
    try:
        # Check if files are present in the request
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file part in the request'}), 400
        
        # Handle both single file and multiple files
        files = request.files.getlist('file')
        
        if not files or all(file.filename == '' for file in files):
            return jsonify({'success': False, 'message': 'No files selected'}), 400
        
        # Get folders from app config
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'raw_video_file')
        download_folder = current_app.config.get('DOWNLOAD_FOLDER', 'resized_video')
        
        # Create folders if they don't exist
        os.makedirs(upload_folder, exist_ok=True)
        os.makedirs(download_folder, exist_ok=True)
        
        upload_results = []
        failed_uploads = []
        
        for file in files:
            try:
                # Validate each file
                is_valid, error_message = validate_upload(file)
                if not is_valid:
                    failed_uploads.append({
                        'filename': file.filename,
                        'error': error_message
                    })
                    continue
                
                # Save the original file
                filename = secure_filename(file.filename)
                
                # Handle duplicate filenames
                base_name, ext = os.path.splitext(filename)
                counter = 1
                original_filename = filename
                
                while os.path.exists(os.path.join(upload_folder, filename)):
                    filename = f"{base_name}_{counter}{ext}"
                    counter += 1
                
                raw_file_path = os.path.join(upload_folder, filename)
                
                logger.info(f"Saving uploaded file {original_filename} as {filename} to {raw_file_path}")
                file.save(raw_file_path)
                
                # Get file size
                raw_size = os.path.getsize(raw_file_path)
                
                # Generate job ID and setup processing job
                job_id = str(uuid.uuid4())
                resized_filename = f"2k_{filename}"
                resized_file_path = os.path.join(download_folder, resized_filename)
                
                # Initialize job tracking
                processing_jobs[job_id] = {
                    'status': 'queued',
                    'progress': 0,
                    'original_filename': original_filename,
                    'saved_filename': filename,
                    'resized_filename': resized_filename,
                    'original_size': raw_size,
                    'original_size_mb': round(raw_size / (1024 * 1024), 2),
                    'created_at': time.time()
                }
                
                # Start processing in background thread
                thread = threading.Thread(
                    target=resize_video_async,
                    args=(job_id, raw_file_path, resized_file_path, original_filename)
                )
                thread.daemon = True
                thread.start()
                
                upload_results.append({
                    'original_filename': original_filename,
                    'saved_filename': filename,
                    'job_id': job_id,
                    'size_mb': round(raw_size / (1024 * 1024), 2)
                })
                
                logger.info(f"Started background processing for job {job_id} (file: {original_filename})")
                
            except Exception as e:
                logger.error(f"Error processing file {file.filename}: {str(e)}")
                failed_uploads.append({
                    'filename': file.filename,
                    'error': f"Processing error: {str(e)}"
                })
        
        # Prepare response
        if upload_results and not failed_uploads:
            # All files uploaded successfully
            return jsonify({
                'success': True,
                'message': f"Successfully uploaded {len(upload_results)} file(s). Processing started.",
                'uploads': upload_results,
                'total_uploaded': len(upload_results)
            }), 200
        elif upload_results and failed_uploads:
            # Some files uploaded, some failed
            return jsonify({
                'success': True,
                'message': f"Uploaded {len(upload_results)} file(s) successfully, {len(failed_uploads)} failed.",
                'uploads': upload_results,
                'failed': failed_uploads,
                'total_uploaded': len(upload_results),
                'total_failed': len(failed_uploads)
            }), 200
        else:
            # All files failed
            return jsonify({
                'success': False,
                'message': f"All {len(failed_uploads)} file(s) failed to upload.",
                'failed': failed_uploads,
                'total_failed': len(failed_uploads)
            }), 400
        
    except Exception as e:
        logger.error(f"Error uploading videos: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f"Error uploading videos: {str(e)}"
        }), 500

@video_bp.route('/batch_upload_status', methods=['GET'])
def get_batch_upload_status():
    """
    Get the status of multiple processing jobs
    
    Query Parameters:
        job_ids: Comma-separated list of job IDs
        
    Returns:
        JSON response with status of all requested jobs
    """
    try:
        job_ids_param = request.args.get('job_ids', '')
        
        if not job_ids_param:
            return jsonify({
                'success': False,
                'message': 'No job IDs provided'
            }), 400
        
        job_ids = [jid.strip() for jid in job_ids_param.split(',') if jid.strip()]
        
        if not job_ids:
            return jsonify({
                'success': False,
                'message': 'No valid job IDs provided'
            }), 400
        
        job_statuses = {}
        not_found_jobs = []
        
        for job_id in job_ids:
            if job_id in processing_jobs:
                job = processing_jobs[job_id]
                job_statuses[job_id] = {
                    'status': job['status'],
                    'progress': job['progress'],
                    'original_filename': job['original_filename'],
                    'original_size_mb': job['original_size_mb']
                }
                
                if job['status'] == 'completed':
                    job_statuses[job_id].update({
                        'resized_filename': job['resized_filename'],
                        'size': job.get('size', 0),
                        'size_mb': job.get('size_mb', 0),
                        'path': f"/resized_videos/{job['resized_filename']}"
                    })
                elif job['status'] == 'failed':
                    job_statuses[job_id]['error'] = job.get('error', 'Unknown error')
            else:
                not_found_jobs.append(job_id)
        
        # Calculate overall statistics
        total_jobs = len(job_ids)
        completed_jobs = len([j for j in job_statuses.values() if j['status'] == 'completed'])
        failed_jobs = len([j for j in job_statuses.values() if j['status'] == 'failed'])
        processing_jobs_count = len([j for j in job_statuses.values() if j['status'] in ['queued', 'processing']])
        
        overall_progress = 0
        if job_statuses:
            total_progress = sum(job['progress'] for job in job_statuses.values())
            overall_progress = round(total_progress / len(job_statuses))
        
        return jsonify({
            'success': True,
            'job_statuses': job_statuses,
            'not_found_jobs': not_found_jobs,
            'summary': {
                'total_jobs': total_jobs,
                'completed': completed_jobs,
                'failed': failed_jobs,
                'processing': processing_jobs_count,
                'not_found': len(not_found_jobs),
                'overall_progress': overall_progress
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting batch upload status: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error getting status: {str(e)}"
        }), 500

@video_bp.route('/processing_status/<job_id>', methods=['GET'])
def get_processing_status(job_id: str):
    """
    Get the status of a video processing job
    
    Args:
        job_id: The job ID to check
        
    Returns:
        JSON response with processing status
    """
    try:
        if job_id not in processing_jobs:
            return jsonify({
                'success': False,
                'message': 'Job not found'
            }), 404
        
        job = processing_jobs[job_id]
        
        response_data = {
            'success': True,
            'job_id': job_id,
            'status': job['status'],
            'progress': job['progress'],
            'original_filename': job['original_filename'],
            'original_size_mb': job['original_size_mb']
        }
        
        if job['status'] == 'completed':
            response_data.update({
                'resized_filename': job['resized_filename'],
                'size': job.get('size', 0),
                'size_mb': job.get('size_mb', 0),
                'path': f"/resized_videos/{job['resized_filename']}"
            })
        elif job['status'] == 'failed':
            response_data['error'] = job.get('error', 'Unknown error')
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error getting processing status: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error getting status: {str(e)}"
        }), 500

@video_bp.route('/cleanup_completed_jobs', methods=['POST'])
def cleanup_completed_jobs():
    """
    Clean up completed and failed processing jobs older than specified time
    
    Request Body:
        max_age_hours: Maximum age in hours for jobs to keep (default: 24)
        
    Returns:
        JSON response with cleanup results
    """
    try:
        data = request.get_json() or {}
        max_age_hours = data.get('max_age_hours', 24)
        max_age_seconds = max_age_hours * 3600
        
        current_time = time.time()
        jobs_to_remove = []
        
        for job_id, job in processing_jobs.items():
            job_age = current_time - job.get('created_at', current_time)
            
            # Remove completed/failed jobs older than max_age
            if (job['status'] in ['completed', 'failed'] and job_age > max_age_seconds):
                jobs_to_remove.append(job_id)
        
        # Remove the jobs
        for job_id in jobs_to_remove:
            del processing_jobs[job_id]
        
        return jsonify({
            'success': True,
            'message': f"Cleaned up {len(jobs_to_remove)} old processing jobs",
            'removed_jobs': len(jobs_to_remove),
            'remaining_jobs': len(processing_jobs)
        }), 200
        
    except Exception as e:
        logger.error(f"Error cleaning up jobs: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error during cleanup: {str(e)}"
        }), 500

# Keep existing endpoints for backward compatibility...
# (Include all the other existing endpoints from the original file)

@video_bp.route('/uploads/<filename>', methods=['GET'])
def serve_video_compatible(filename):
    """
    Serve a video file - tries resized first, then raw (for client compatibility)
    Args:
        filename: The name of the file to serve
    Returns:
        The video file
    """
    try:
        # Get folders from app config
        download_folder = current_app.config.get('DOWNLOAD_FOLDER', 'resized_video')
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'raw_video_file')
        
        # Make sure the filename is secure
        secure_name = secure_filename(filename)
        
        # Try resized video first (with 2k_ prefix)
        resized_name = f"2k_{secure_name}"
        resized_path = os.path.join(download_folder, resized_name)
        
        if os.path.exists(resized_path):
            logger.info(f"Serving resized video file: {resized_name}")
            return send_from_directory(download_folder, resized_name)
        
        # Try resized video without prefix
        resized_path_no_prefix = os.path.join(download_folder, secure_name)
        if os.path.exists(resized_path_no_prefix):
            logger.info(f"Serving resized video file: {secure_name}")
            return send_from_directory(download_folder, secure_name)
        
        # Fallback to raw video
        raw_path = os.path.join(upload_folder, secure_name)
        if os.path.exists(raw_path):
            logger.info(f"Serving raw video file (resized not available): {secure_name}")
            return send_from_directory(upload_folder, secure_name)
        
        # File not found anywhere
        logger.warning(f"Video file not found: {filename}")
        return jsonify({
            'success': False,
            'message': f"File {filename} not found in any location"
        }), 404
        
    except Exception as e:
        logger.error(f"Error serving video: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f"Error serving video: {str(e)}"
        }), 500

@video_bp.route('/resized_videos/<filename>', methods=['GET'])
def serve_resized_video(filename):
    """
    Serve a resized video file from the download folder
    Args:
        filename: The name of the file to serve
    Returns:
        The resized video file
    """
    try:
        # Get the download folder from app config
        download_folder = current_app.config.get('DOWNLOAD_FOLDER', 'resized_video')
        
        # Make sure the filename is secure
        secure_name = secure_filename(filename)
        
        # Check if the file exists
        file_path = os.path.join(download_folder, secure_name)
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'message': f"Resized file {filename} not found"
            }), 404
        
        # Log the download
        logger.info(f"Serving resized video file: {secure_name}")
        
        # Serve the file
        return send_from_directory(download_folder, secure_name)
        
    except Exception as e:
        logger.error(f"Error serving resized video: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f"Error serving resized video: {str(e)}"
        }), 500

@video_bp.route('/delete_video/<filename>', methods=['DELETE'])
def delete_video(filename: str):
    """
    Delete a video file from both raw and resized folders
    
    Args:
        filename: The name of the video file to delete
        
    Returns:
        JSON response indicating success/failure
    """
    try:
        # Secure the filename
        secure_name = secure_filename(filename)
        
        if not secure_name:
            return jsonify({
                'success': False,
                'message': 'Invalid filename provided'
            }), 400
        
        # Get folders from app config
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'raw_video_file')
        download_folder = current_app.config.get('DOWNLOAD_FOLDER', 'resized_video')
        
        deleted_files = []
        errors = []
        
        # Try to delete from raw videos folder
        raw_path = os.path.join(upload_folder, secure_name)
        if os.path.exists(raw_path):
            try:
                os.remove(raw_path)
                deleted_files.append(f"raw/{secure_name}")
                logger.info(f"Deleted raw video file: {raw_path}")
            except Exception as e:
                error_msg = f"Failed to delete raw file: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        # Try to delete from resized videos folder (with and without 2k_ prefix)
        resized_path = os.path.join(download_folder, secure_name)
        resized_path_with_prefix = os.path.join(download_folder, f"2k_{secure_name}")
        
        # Delete resized file without prefix
        if os.path.exists(resized_path):
            try:
                os.remove(resized_path)
                deleted_files.append(f"resized/{secure_name}")
                logger.info(f"Deleted resized video file: {resized_path}")
            except Exception as e:
                error_msg = f"Failed to delete resized file: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        # Delete resized file with 2k_ prefix
        if os.path.exists(resized_path_with_prefix):
            try:
                os.remove(resized_path_with_prefix)
                deleted_files.append(f"resized/2k_{secure_name}")
                logger.info(f"Deleted resized video file with prefix: {resized_path_with_prefix}")
            except Exception as e:
                error_msg = f"Failed to delete resized file with prefix: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        # Check if any files were deleted
        if not deleted_files and not errors:
            return jsonify({
                'success': False,
                'message': f'Video file "{secure_name}" not found in any location',
                'searched_locations': [
                    f"raw/{secure_name}",
                    f"resized/{secure_name}",
                    f"resized/2k_{secure_name}"
                ]
            }), 404
        
        # Prepare response
        if deleted_files and not errors:
            # Complete success
            return jsonify({
                'success': True,
                'message': f'Successfully deleted video "{secure_name}"',
                'deleted_files': deleted_files
            }), 200
        elif deleted_files and errors:
            # Partial success
            return jsonify({
                'success': True,
                'message': f'Partially deleted video "{secure_name}"',
                'deleted_files': deleted_files,
                'errors': errors
            }), 200
        else:
            # Complete failure
            return jsonify({
                'success': False,
                'message': f'Failed to delete video "{secure_name}"',
                'errors': errors
            }), 500
        
    except Exception as e:
        logger.error(f"Error deleting video {filename}: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f"Error deleting video: {str(e)}"
        }), 500

@video_bp.route('/video_status', methods=['GET'])
def get_video_status():
    """Get detailed status of video files and processing jobs"""
    try:
        # Get folders
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'raw_video_file')
        download_folder = current_app.config.get('DOWNLOAD_FOLDER', 'resized_video')
        
        # Count files in each folder
        raw_videos = []
        resized_videos = []
        
        if os.path.exists(upload_folder):
            raw_videos = [f for f in os.listdir(upload_folder) 
                         if f.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.webm'))]
        
        if os.path.exists(download_folder):
            resized_videos = [f for f in os.listdir(download_folder) 
                            if f.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.webm'))]
        
        # Check processing jobs
        active_jobs = {k: v for k, v in processing_jobs.items() 
                      if v['status'] in ['queued', 'processing']}
        
        completed_jobs = {k: v for k, v in processing_jobs.items() 
                         if v['status'] == 'completed'}
        
        failed_jobs = {k: v for k, v in processing_jobs.items() 
                      if v['status'] == 'failed'}
        
        return jsonify({
            'success': True,
            'folders': {
                'raw_folder': upload_folder,
                'resized_folder': download_folder
            },
            'file_counts': {
                'raw_videos': len(raw_videos),
                'resized_videos': len(resized_videos),
                'active_processing_jobs': len(active_jobs),
                'completed_jobs': len(completed_jobs),
                'failed_jobs': len(failed_jobs),
                'total_jobs': len(processing_jobs)
            },
            'raw_video_files': raw_videos,
            'resized_video_files': resized_videos,
            'processing_jobs': {
                'active': active_jobs,
                'completed': completed_jobs,
                'failed': failed_jobs
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting video status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500