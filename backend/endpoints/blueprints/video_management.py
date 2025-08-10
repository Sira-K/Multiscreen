# Simple video_management.py with single uploads folder support
from flask import Blueprint, request, jsonify, current_app
import logging
import os
from werkzeug.utils import secure_filename
from typing import Dict, Any

# Configure logger
logger = logging.getLogger(__name__)

# Create blueprint
video_bp = Blueprint('video_management', __name__)

# Global dictionary to track processing jobs
processing_jobs: Dict[str, Dict[str, Any]] = {}

def get_state():
    """Get application state from current app context"""
    return current_app.config['APP_STATE']

def validate_upload(file):
    """
    Validate an uploaded file
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not file:
        return False, 'No file provided in request'
    
    # Check file extension
    allowed_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.webm'}
    filename = file.filename.lower()
    file_ext = os.path.splitext(filename)[1]
    
    if file_ext not in allowed_extensions:
        return False, f'File extension {file_ext} not allowed. Allowed: {", ".join(allowed_extensions)}'
    
    # Check file size (2GB limit)
    max_size = 2 * 1024 * 1024 * 1024  # 2GB
    if hasattr(file, 'content_length') and file.content_length and file.content_length > max_size:
        size_mb = round(file.content_length / (1024 * 1024), 2)
        return False, f'File size {size_mb}MB exceeds maximum allowed size of 2GB'
    
    return True, None

@video_bp.route('/get_videos', methods=['GET'])
def get_videos():
    """
    Get a list of all video files in the uploads directory
    Returns:
        JSON response with list of video files
    """
    try:
        # Get the upload folder from app config
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        
        # Ensure the directory exists
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        
        # Get all files in the directory
        files = os.listdir(upload_folder)
        
        # Filter for video files
        video_extensions = ('.mp4', '.mkv', '.avi', '.mov', '.webm')
        video_files = [f for f in files if f.lower().endswith(video_extensions)]
        
        # Create a list of video file objects
        videos = []
        for video_file in video_files:
            video_path = os.path.join(upload_folder, video_file)
            file_size = os.path.getsize(video_path)
            
            videos.append({
                'name': video_file,
                'path': f"/uploads/{video_file}",
                'size': file_size,
                'size_mb': round(file_size / (1024 * 1024), 2)
            })
        
        return jsonify({
            'success': True,
            'videos': videos
        })
    
    except Exception as e:
        logger.error(f"Error getting videos: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error getting videos: {str(e)}",
            'videos': []
        }), 500
    
    
@video_bp.route('/upload_video', methods=['POST'])
def upload_video():
    """
    Upload video files directly to uploads folder
    """
    try:
        # Check if files are present
        if 'video' not in request.files:
            return jsonify({
                'success': False,
                'message': 'No video field in request'
            }), 400
        
        files = request.files.getlist('video')
        
        if not files or all(file.filename == '' for file in files):
            return jsonify({
                'success': False, 
                'message': 'No files selected'
            }), 400
        
        # Get upload folder
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        
        # Create directory if it doesn't exist
        try:
            os.makedirs(upload_folder, exist_ok=True)
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Could not create upload directory: {str(e)}'
            }), 500
        
        upload_results = []
        failed_uploads = []
        
        for file in files:
            try:
                # Validate file
                is_valid, error_message = validate_upload(file)
                
                if not is_valid:
                    failed_uploads.append({
                        'filename': file.filename,
                        'error': error_message
                    })
                    continue
                
                # Process filename
                filename = secure_filename(file.filename)
                
                if not filename:
                    failed_uploads.append({
                        'filename': file.filename,
                        'error': 'Invalid filename'
                    })
                    continue
                
                # Handle duplicates
                base_name, ext = os.path.splitext(filename)
                counter = 1
                original_filename = filename
                
                while os.path.exists(os.path.join(upload_folder, filename)):
                    filename = f"{base_name}_{counter}{ext}"
                    counter += 1
                
                file_path = os.path.join(upload_folder, filename)
                
                # Save the file
                try:
                    file.save(file_path)
                except Exception as e:
                    failed_uploads.append({
                        'filename': file.filename,
                        'error': f'Failed to save file: {str(e)}'
                    })
                    continue
                
                # Check if file was actually saved
                if not os.path.exists(file_path):
                    failed_uploads.append({
                        'filename': file.filename,
                        'error': 'File not found after save'
                    })
                    continue
                
                # Get file size
                try:
                    file_size = os.path.getsize(file_path)
                    size_mb = round(file_size / (1024 * 1024), 2)
                except Exception:
                    file_size = 0
                    size_mb = 0
                
                # Success - add to results
                upload_results.append({
                    'original_filename': file.filename,
                    'saved_filename': filename,
                    'size_mb': size_mb,
                    'status': 'completed',
                    'path': file_path
                })
                
            except Exception as e:
                failed_uploads.append({
                    'filename': file.filename,
                    'error': f'Unexpected error: {str(e)}'
                })
        
        # Return results
        if upload_results:
            response = {
                'success': True,
                'message': f"Successfully uploaded {len(upload_results)} file(s)",
                'uploads': upload_results
            }
            if failed_uploads:
                response['failed'] = failed_uploads
            
            return jsonify(response), 200
        else:
            return jsonify({
                'success': False,
                'message': "All uploads failed",
                'failed': failed_uploads
            }), 400
        
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({
            'success': False, 
            'message': f'Upload error: {str(e)}'
        }), 500

    
@video_bp.route('/delete_video', methods=['POST'])
def delete_video_post():
    """
    Delete a video file using POST method
    Only looks in the uploads folder
    
    Request Body:
        video_name: The name of the video file to delete
        
    Returns:
        JSON response indicating success/failure
    """
    try:
        data = request.get_json()
        if not data or 'video_name' not in data:
            return jsonify({
                'success': False,
                'message': 'video_name field is required'
            }), 400
        
        video_name = data['video_name']
        
        # Secure the filename
        secure_name = secure_filename(video_name)
        
        if not secure_name:
            return jsonify({
                'success': False,
                'message': 'Invalid filename provided'
            }), 400
        
        # Get upload folder from app config
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        
        # Try to delete from uploads folder
        video_path = os.path.join(upload_folder, secure_name)
        
        if os.path.exists(video_path):
            try:
                os.remove(video_path)
                return jsonify({
                    'success': True,
                    'message': f'Successfully deleted video "{secure_name}"'
                }), 200
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'Failed to delete video: {str(e)}'
                }), 500
        else:
            return jsonify({
                'success': False,
                'message': f'Video file "{secure_name}" not found'
            }), 404
        
    except Exception as e:
        logger.error(f"Delete error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Delete error: {str(e)}'
        }), 500


@video_bp.route('/video_status', methods=['GET'])
def get_video_status():
    """Get status of video files in uploads folder"""
    try:
        # Get upload folder
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        
        # Count files in uploads folder
        videos = []
        
        if os.path.exists(upload_folder):
            videos = [f for f in os.listdir(upload_folder) 
                     if f.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.webm'))]
        
        # Check processing jobs
        active_jobs = len([j for j in processing_jobs.values() if j['status'] in ['queued', 'processing']])
        completed_jobs = len([j for j in processing_jobs.values() if j['status'] == 'completed'])
        failed_jobs = len([j for j in processing_jobs.values() if j['status'] == 'failed'])
        
        return jsonify({
            'success': True,
            'uploads_folder': upload_folder,
            'video_count': len(videos),
            'video_files': videos,
            'processing_jobs': {
                'active': active_jobs,
                'completed': completed_jobs,
                'failed': failed_jobs,
                'total': len(processing_jobs)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting video status: {e}")
        return jsonify({
            'success': False,
            'message': f'Error getting video status: {str(e)}'
        }), 500


# Processing job management endpoints (keeping for compatibility)

@video_bp.route('/processing_status/<job_id>', methods=['GET'])
def get_processing_status(job_id: str):
    """Get the status of a video processing job"""
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
            'progress': job.get('progress', 0),
            'original_filename': job.get('original_filename', 'Unknown')
        }
        
        if job['status'] == 'completed':
            response_data.update({
                'filename': job.get('filename', job.get('original_filename', 'Unknown')),
                'path': f"/uploads/{job.get('filename', job.get('original_filename', 'Unknown'))}"
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


@video_bp.route('/batch_upload_status', methods=['GET'])
def get_batch_upload_status():
    """Get the status of multiple processing jobs"""
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
                    'progress': job.get('progress', 0),
                    'original_filename': job.get('original_filename', 'Unknown')
                }
                
                if job['status'] == 'completed':
                    job_statuses[job_id].update({
                        'filename': job.get('filename', job.get('original_filename', 'Unknown')),
                        'path': f"/uploads/{job.get('filename', job.get('original_filename', 'Unknown'))}"
                    })
                elif job['status'] == 'failed':
                    job_statuses[job_id]['error'] = job.get('error', 'Unknown error')
            else:
                not_found_jobs.append(job_id)
        
        # Calculate simple statistics
        total_jobs = len(job_ids)
        completed_count = len([j for j in job_statuses.values() if j['status'] == 'completed'])
        failed_count = len([j for j in job_statuses.values() if j['status'] == 'failed'])
        processing_count = len([j for j in job_statuses.values() if j['status'] in ['queued', 'processing']])
        
        return jsonify({
            'success': True,
            'job_statuses': job_statuses,
            'not_found_jobs': not_found_jobs,
            'summary': {
                'total_jobs': total_jobs,
                'completed': completed_count,
                'failed': failed_count,
                'processing': processing_count,
                'not_found': len(not_found_jobs)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting batch upload status: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error getting status: {str(e)}"
        }), 500


@video_bp.route('/cleanup_completed_jobs', methods=['POST'])
def cleanup_completed_jobs():
    """Clean up old completed and failed processing jobs"""
    try:
        data = request.get_json() or {}
        max_age_hours = data.get('max_age_hours', 24)
        max_age_seconds = max_age_hours * 3600
        
        import time
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