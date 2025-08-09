# Enhanced video_management.py with multiple file upload support
from flask import Blueprint, request, jsonify, current_app, send_from_directory
import traceback
import time
import logging
import os
import subprocess
from werkzeug.utils import secure_filename
from typing import Tuple, Optional, Dict, Any
import time
import csv
import json
from datetime import datetime

from errors.system_errors import (
    SystemException,
    DatabaseException,
    NetworkException,
    format_system_error_response,
    get_system_error_info
)

# Configure logger
logger = logging.getLogger(__name__)

# Create blueprint
video_bp = Blueprint('video_management', __name__)

# Global dictionary to track processing jobs
processing_jobs: Dict[str, Dict[str, Any]] = {}

def get_state():
    """Get application state from current app context"""
    return current_app.config['APP_STATE']

def validate_upload(file) -> Tuple[bool, Optional[dict]]:
    """
    Validate an uploaded file
    
    Returns:
        Tuple of (is_valid, error_info_dict)
    """
    if not file:
        return False, format_system_error_response(
            503,  # SYSTEM_PERMISSION_DENIED
            {'reason': 'No file provided in request'}
        )
    
    # Check file extension
    allowed_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.webm'}
    filename = file.filename.lower()
    file_ext = os.path.splitext(filename)[1]
    
    if file_ext not in allowed_extensions:
        return False, format_system_error_response(
            501,  # SYSTEM_CONFIGURATION_ERROR
            {
                'filename': filename,
                'invalid_extension': file_ext,
                'allowed_extensions': list(allowed_extensions)
            }
        )
    
    # Check file size
    max_size = 2 * 1024 * 1024 * 1024  # 2GB
    if hasattr(file, 'content_length') and file.content_length and file.content_length > max_size:
        return False, format_system_error_response(
            508,  # SYSTEM_CAPACITY_EXCEEDED
            {
                'file_size': file.content_length,
                'max_allowed': max_size,
                'size_mb': round(file.content_length / (1024 * 1024), 2)
            }
        )
    
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
            # FFmpeg processing error
            error_info = get_system_error_info(506)  # SYSTEM_INTERNAL_ERROR
            processing_jobs[job_id]['status'] = 'failed'
            processing_jobs[job_id]['error_code'] = 506
            processing_jobs[job_id]['error_info'] = error_info
            processing_jobs[job_id]['error_context'] = {
                'ffmpeg_stderr': stderr,
                'return_code': process.returncode
            }
        
    except subprocess.TimeoutExpired:
        error_info = get_system_error_info(505)  # SYSTEM_TIMEOUT
        processing_jobs[job_id]['status'] = 'failed'
        processing_jobs[job_id]['error_code'] = 505
        processing_jobs[job_id]['error_info'] = error_info

    except Exception as e:
        error_info = get_system_error_info(506)  # SYSTEM_INTERNAL_ERROR
        processing_jobs[job_id]['status'] = 'failed'
        processing_jobs[job_id]['error_code'] = 506
        processing_jobs[job_id]['error_info'] = error_info
        processing_jobs[job_id]['error_context'] = {'exception': str(e)}

def create_video_response(success: bool, data: dict = None, error_code: int = None) -> Tuple[dict, int]:
    """
    Create a standardized response for video endpoints
    
    Args:
        success: Whether the operation was successful
        data: Response data for successful operations
        error_code: System error code for failures
        
    Returns:
        Tuple of (response_dict, http_status_code)
    """
    if success:
        response = {'success': True}
        if data:
            response.update(data)
        return response, 200
    else:
        if error_code:
            response = format_system_error_response(error_code, data or {})
        else:
            response = {
                'success': False,
                'error_code': 506,  # Default to internal error
                'error_message': 'Unknown error occurred',
                'context': data or {}
            }
        
        # Map error codes to HTTP status codes
        http_status_map = {
            500: 500, 501: 400, 502: 503, 503: 403, 504: 503,
            505: 504, 506: 500, 507: 503, 508: 507, 509: 400,
            520: 503, 524: 507, 525: 403
        }
        
        http_status = http_status_map.get(error_code, 500)
        return response, http_status
    
@video_bp.route('/get_videos', methods=['GET'])
def get_videos():
    """
    Get a list of all video files in the uploads directory
    Returns:
        JSON response with list of video files
    """
    try:
        # Get the upload folder from app config (where uploaded videos are stored)
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        
        # Debug log
        logger.info(f"Looking for videos in: {upload_folder}")
        
        # Ensure the directory exists
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
            logger.warning(f"Created uploads directory {upload_folder}")
        
        # Get all files in the directory
        files = os.listdir(upload_folder)
        
        # Filter for video files (mp4, mkv, avi, mov, webm)
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
                'size_mb': round(file_size / (1024 * 1024), 2)  # Size in MB
            })
        
        logger.info(f"Found {len(videos)} video files in uploads")
        
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
    Upload video files directly without any processing/resizing
    """
    # Record start time immediately
    start_time = time.time()
    start_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    
    # Initialize timing data collection
    timing_data = {
        'start_time': start_time,
        'start_datetime': start_datetime,
        'validation_time': 0,
        'file_operations_time': 0,
        'total_save_time': 0,
        'individual_files': [],
        'request_processing_time': 0,
        'directory_creation_time': 0
    }
    
    def write_timing_data_to_files(timing_info, upload_results, failed_uploads):
        """Write comprehensive timing and size data to output files"""
        try:
            # Create output directory if it doesn't exist
            output_dir = current_app.config.get('TIMING_OUTPUT_DIR', 'upload_timing_logs')
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate timestamp for filenames
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # 1. Write comprehensive JSON log
            json_filename = os.path.join(output_dir, f'upload_timing_{timestamp}.json')
            comprehensive_data = {
                'session_info': {
                    'timestamp': timestamp,
                    'session_id': f"upload_{timestamp}",
                    'started_at': timing_info['started_at'],
                    'completed_at': timing_info['completed_at'],
                    'total_duration_seconds': timing_info['total_time_seconds']
                },
                'summary_metrics': {
                    'files_processed': timing_info['files_processed'],
                    'successful_uploads': timing_info['successful_uploads'],
                    'failed_uploads': timing_info['failed_uploads'],
                    'success_rate_percent': round((timing_info['successful_uploads'] / timing_info['files_processed']) * 100, 2) if timing_info['files_processed'] > 0 else 0,
                    'total_files_size_mb': timing_info['total_files_size_mb'],
                    'total_files_size_bytes': timing_info['total_files_size_bytes'],
                    'average_file_size_mb': timing_info['average_file_size_mb'],
                    'upload_speed_mbps': timing_info['upload_speed_mbps']
                },
                'timing_breakdown': {
                    'request_processing_time': timing_info['request_processing_time'],
                    'directory_creation_time': timing_info['directory_creation_time'],
                    'total_validation_time': timing_info['total_validation_time'],
                    'total_file_operations_time': timing_info['total_file_operations_time'],
                    'total_save_time': timing_info['total_save_time'],
                    'average_time_per_file': timing_info['average_time_per_file'],
                    'average_save_time_per_file': timing_info['average_save_time_per_file']
                },
                'individual_files': timing_info['individual_file_timings'],
                'successful_uploads': upload_results,
                'failed_uploads': failed_uploads
            }
            
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(comprehensive_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f" Comprehensive timing data written to: {json_filename}")
            
            # 2. Write CSV summary for easy analysis
            csv_filename = os.path.join(output_dir, f'upload_summary_{timestamp}.csv')
            with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write header
                writer.writerow([
                    'Timestamp', 'Session_ID', 'Total_Duration_Seconds', 'Files_Processed', 
                    'Successful_Uploads', 'Failed_Uploads', 'Success_Rate_Percent',
                    'Total_Size_MB', 'Total_Size_Bytes', 'Average_File_Size_MB',
                    'Upload_Speed_Mbps', 'Request_Processing_Time', 'Directory_Creation_Time',
                    'Total_Validation_Time', 'Total_File_Operations_Time', 'Total_Save_Time',
                    'Average_Time_Per_File', 'Average_Save_Time_Per_File'
                ])
                
                # Write data row
                writer.writerow([
                    timestamp, f"upload_{timestamp}", timing_info['total_time_seconds'],
                    timing_info['files_processed'], timing_info['successful_uploads'], 
                    timing_info['failed_uploads'], 
                    round((timing_info['successful_uploads'] / timing_info['files_processed']) * 100, 2) if timing_info['files_processed'] > 0 else 0,
                    timing_info['total_files_size_mb'], timing_info['total_files_size_bytes'],
                    timing_info['average_file_size_mb'], timing_info['upload_speed_mbps'],
                    timing_info['request_processing_time'], timing_info['directory_creation_time'],
                    timing_info['total_validation_time'], timing_info['total_file_operations_time'],
                    timing_info['total_save_time'], timing_info['average_time_per_file'],
                    timing_info['average_save_time_per_file']
                ])
            
            logger.info(f" Summary CSV written to: {csv_filename}")
            
            # 3. Write individual file details CSV
            files_csv_filename = os.path.join(output_dir, f'individual_files_{timestamp}.csv')
            with open(files_csv_filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write header
                writer.writerow([
                    'Session_ID', 'Filename', 'File_Size_Bytes', 'File_Size_MB', 
                    'Validation_Time', 'Filename_Processing_Time', 'Save_Time',
                    'Size_Check_Time', 'Total_Time', 'Status', 'Error_Message'
                ])
                
                # Write individual file data
                for file_data in timing_info['individual_file_timings']:
                    writer.writerow([
                        f"upload_{timestamp}", file_data.get('filename', 'Unknown'),
                        file_data.get('file_size_bytes', 0), file_data.get('file_size_mb', 0),
                        file_data.get('validation_time', 0), file_data.get('filename_processing_time', 0),
                        file_data.get('save_time', 0), file_data.get('size_check_time', 0),
                        file_data.get('total_time', 0), 
                        'Failed' if 'error' in file_data else 'Success',
                        file_data.get('error', '')
                    ])
            
            logger.info(f" Individual files CSV written to: {files_csv_filename}")
            
            # 4. Append to master log file for historical tracking
            master_log_filename = os.path.join(output_dir, 'upload_history_master.csv')
            file_exists = os.path.exists(master_log_filename)
            
            with open(master_log_filename, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write header if file doesn't exist
                if not file_exists:
                    writer.writerow([
                        'Timestamp', 'Session_ID', 'Total_Duration_Seconds', 'Files_Processed', 
                        'Successful_Uploads', 'Failed_Uploads', 'Success_Rate_Percent',
                        'Total_Size_MB', 'Upload_Speed_Mbps', 'Average_Time_Per_File'
                    ])
                
                # Append this session's data
                writer.writerow([
                    timestamp, f"upload_{timestamp}", timing_info['total_time_seconds'],
                    timing_info['files_processed'], timing_info['successful_uploads'], 
                    timing_info['failed_uploads'], 
                    round((timing_info['successful_uploads'] / timing_info['files_processed']) * 100, 2) if timing_info['files_processed'] > 0 else 0,
                    timing_info['total_files_size_mb'], timing_info['upload_speed_mbps'],
                    timing_info['average_time_per_file']
                ])
            
            logger.info(f" Master history log updated: {master_log_filename}")
            
            return {
                'json_file': json_filename,
                'summary_csv': csv_filename,
                'files_csv': files_csv_filename,
                'master_log': master_log_filename
            }
            
        except Exception as write_error:
            logger.error(f" Failed to write timing data to files: {write_error}")
            return None
    
    try:
        # Request processing timing
        request_start = time.time()
        
        # Check if files are present
        if 'video' not in request.files:
            error_response = format_system_error_response(
                501,  # SYSTEM_CONFIGURATION_ERROR
                {'missing_field': 'video', 'elapsed_time': time.time() - start_time}
            )
            logger.error(f"Error {error_response['error_code']}: {error_response['error_message']}")
            return jsonify(error_response), 400
        
        files_received_time = time.time()
        files = request.files.getlist('video')
        timing_data['request_processing_time'] = files_received_time - request_start
        
        logger.info(f" Files received after {files_received_time - start_time:.2f}s")
        logger.info(f"Number of files received: {len(files)}")
        
        if not files or all(file.filename == '' for file in files):
            elapsed = time.time() - start_time
            logger.error(f" No files selected or all filenames are empty (after {elapsed:.2f}s)")
            return jsonify({'success': False, 'message': 'No files selected'}), 400
        
        # Get upload folder
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'raw_video_file')
        
        # Directory creation timing
        dir_start = time.time()
        try:
            os.makedirs(upload_folder, exist_ok=True)
            timing_data['directory_creation_time'] = time.time() - dir_start
        except Exception as mkdir_error:
            error_response = format_system_error_response(
                524,  # DATABASE_DISK_FULL or use 503 for permission
                {
                    'directory': upload_folder,
                    'error': str(mkdir_error),
                    'elapsed_time': time.time() - start_time
                }
            )
            logger.error(f"Error {error_response['error_code']}: {error_response['error_message']}")
            return jsonify(error_response), 500
        
        upload_results = []
        failed_uploads = []
        total_validation_time = 0
        total_file_ops_time = 0
        total_save_time = 0
        
        for i, file in enumerate(files):
            file_start_time = time.time()
            file_timing = {
                'filename': file.filename,
                'file_size_bytes': 0,
                'file_size_mb': 0,
                'validation_time': 0,
                'filename_processing_time': 0,
                'save_time': 0,
                'size_check_time': 0,
                'total_time': 0
            }
            
            try:
                logger.info(f" Processing file {i+1}/{len(files)}: {file.filename}")
                
                # Validate file with proper timing
                validation_start = time.time()
                is_valid, error_info = validate_upload(file)
                validation_time = time.time() - validation_start
                file_timing['validation_time'] = validation_time
                total_validation_time += validation_time
                
                if not is_valid:
                    failed_uploads.append({
                        'filename': file.filename, 
                        'error_code': error_info.get('error_code'),
                        'error_message': error_info.get('error_message'),
                        'context': error_info.get('context', {})
                    })
                    logger.warning(f"File validation failed with error {error_info.get('error_code')}")
                    file_timing['error'] = f"Validation failed: {error_info.get('error_message')}"
                    timing_data['individual_files'].append(file_timing)
                    continue
                
                # Filename processing
                filename_start = time.time()
                filename = secure_filename(file.filename)
                logger.info(f" Secured filename: {filename}")
                
                # Handle duplicates
                base_name, ext = os.path.splitext(filename)
                counter = 1
                original_filename = filename
                
                while os.path.exists(os.path.join(upload_folder, filename)):
                    filename = f"{base_name}_{counter}{ext}"
                    counter += 1
                
                if filename != original_filename:
                    logger.info(f" Renamed file from {original_filename} to {filename} to avoid duplicate")
                
                file_path = os.path.join(upload_folder, filename)
                logger.info(f" Final file path: {file_path}")
                
                filename_processing_time = time.time() - filename_start
                file_timing['filename_processing_time'] = filename_processing_time
                total_file_ops_time += filename_processing_time
                
                # Save the file with proper error handling
                save_start_time = time.time()
                try:
                    file.save(file_path)
                    save_duration = time.time() - save_start_time
                    file_timing['save_time'] = save_duration
                    total_save_time += save_duration
                    logger.info(f" File saved successfully in {save_duration:.2f}s to: {file_path}")
                    
                except IOError as save_error:
                    save_duration = time.time() - save_start_time
                    file_timing['save_time'] = save_duration
                    # Disk full or write permission error
                    error_info = format_system_error_response(
                        524 if 'space' in str(save_error).lower() else 503,
                        {'filename': filename, 'path': file_path, 'error': str(save_error)}
                    )
                    failed_uploads.append({
                        'filename': file.filename,
                        **error_info
                    })
                    file_timing['error'] = error_info.get('error_message')
                    timing_data['individual_files'].append(file_timing)
                    continue
                    
                except Exception as save_error:
                    save_duration = time.time() - save_start_time
                    file_timing['save_time'] = save_duration
                    # Generic system error
                    error_info = format_system_error_response(
                        506,  # SYSTEM_INTERNAL_ERROR
                        {'filename': filename, 'error': str(save_error)}
                    )
                    failed_uploads.append({
                        'filename': file.filename,
                        **error_info
                    })
                    file_timing['error'] = error_info.get('error_message')
                    timing_data['individual_files'].append(file_timing)
                    continue
                
                # Check if file was actually saved
                if not os.path.exists(file_path):
                    logger.error(f" File was not saved successfully: {file_path}")
                    error_info = format_system_error_response(
                        506,  # SYSTEM_INTERNAL_ERROR
                        {'filename': filename, 'reason': 'File not found after save'}
                    )
                    failed_uploads.append({
                        'filename': file.filename,
                        **error_info
                    })
                    file_timing['error'] = 'File not found after save'
                    timing_data['individual_files'].append(file_timing)
                    continue
                
                # Get file size
                size_check_start = time.time()
                try:
                    file_size = os.path.getsize(file_path)
                    size_mb = round(file_size / (1024 * 1024), 2)
                    size_check_time = time.time() - size_check_start
                    file_timing['size_check_time'] = size_check_time
                    file_timing['file_size_bytes'] = file_size
                    file_timing['file_size_mb'] = size_mb
                    logger.info(f" Saved file size: {file_size} bytes ({size_mb} MB)")
                except Exception as size_error:
                    size_check_time = time.time() - size_check_start
                    file_timing['size_check_time'] = size_check_time
                    file_timing['file_size_bytes'] = 0
                    file_timing['file_size_mb'] = 0
                    logger.error(f" Could not get file size: {size_error}")
                    file_size = 0
                    size_mb = 0
                
                # Success - add to results
                file_total_time = time.time() - file_start_time
                file_timing['total_time'] = file_total_time
                timing_data['individual_files'].append(file_timing)
                
                upload_results.append({
                    'original_filename': file.filename,
                    'saved_filename': filename,
                    'size_mb': size_mb,
                    'status': 'completed',
                    'path': file_path,
                    'processing_time_seconds': round(file_total_time, 2)
                })
                
                logger.info(f" Successfully processed {filename} in {file_total_time:.2f}s")
                
            except Exception as file_error:
                # Catch-all for unexpected errors
                file_error_time = time.time() - file_start_time
                file_timing['total_time'] = file_error_time
                file_timing['error'] = str(file_error)
                timing_data['individual_files'].append(file_timing)
                
                error_info = format_system_error_response(
                    506,  # SYSTEM_INTERNAL_ERROR
                    {
                        'filename': file.filename,
                        'error': str(file_error),
                        'file_index': i
                    }
                )
                failed_uploads.append({
                    'filename': file.filename,
                    **error_info
                })
                
                logger.error(f" Error processing file {file.filename} after {file_error_time:.2f}s: {file_error}")
                logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Calculate additional metrics for comprehensive timing
        total_files_size_bytes = sum(ft.get('file_size_bytes', 0) for ft in timing_data['individual_files'] if 'error' not in ft)
        total_files_size_mb = round(total_files_size_bytes / (1024 * 1024), 2)
        
        # Calculate comprehensive timing results
        total_time = time.time() - start_time
        end_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        # Comprehensive timing data collection
        comprehensive_timing = {
            'total_time_seconds': round(total_time, 2),
            'started_at': start_datetime,
            'completed_at': end_datetime,
            'request_processing_time': round(timing_data['request_processing_time'], 3),
            'directory_creation_time': round(timing_data['directory_creation_time'], 3),
            'total_validation_time': round(total_validation_time, 3),
            'total_file_operations_time': round(total_file_ops_time, 3),
            'total_save_time': round(total_save_time, 3),
            'files_processed': len(files),
            'successful_uploads': len(upload_results),
            'failed_uploads': len(failed_uploads),
            'total_files_size_bytes': total_files_size_bytes,
            'total_files_size_mb': total_files_size_mb,
            'average_time_per_file': round(total_time / len(files) if files else 0, 3),
            'average_save_time_per_file': round(total_save_time / len(upload_results) if upload_results else 0, 3),
            'average_file_size_mb': round(total_files_size_mb / len(upload_results) if upload_results else 0, 2),
            'upload_speed_mbps': round((total_files_size_mb * 8) / total_save_time if total_save_time > 0 else 0, 2),
            'individual_file_timings': timing_data['individual_files']
        }
        
        # Write timing data to files
        output_files = write_timing_data_to_files(comprehensive_timing, upload_results, failed_uploads)
        
        # Log comprehensive timing data
        logger.info(f" Upload complete - Success: {len(upload_results)}, Failed: {len(failed_uploads)}")
        logger.info(f" Total processing time: {total_time:.2f} seconds")
        logger.info(f" COMPREHENSIVE TIMING DATA:")
        logger.info(f"    Request processing: {comprehensive_timing['request_processing_time']:.3f}s")
        logger.info(f"    Directory creation: {comprehensive_timing['directory_creation_time']:.3f}s")
        logger.info(f"    Total validation: {comprehensive_timing['total_validation_time']:.3f}s")
        logger.info(f"    File operations: {comprehensive_timing['total_file_operations_time']:.3f}s")
        logger.info(f"    Total save time: {comprehensive_timing['total_save_time']:.3f}s")
        logger.info(f"    Total files size: {comprehensive_timing['total_files_size_mb']} MB ({comprehensive_timing['total_files_size_bytes']} bytes)")
        logger.info(f"    Avg time per file: {comprehensive_timing['average_time_per_file']:.3f}s")
        logger.info(f"    Avg save time per file: {comprehensive_timing['average_save_time_per_file']:.3f}s")
        logger.info(f"    Avg file size: {comprehensive_timing['average_file_size_mb']} MB")
        logger.info(f"    Upload speed: {comprehensive_timing['upload_speed_mbps']} Mbps")
        logger.info(f" === UPLOAD FINISHED at {end_datetime} ===")
        
        # Add output file info to response if files were written successfully
        if output_files:
            comprehensive_timing['output_files'] = output_files
        
        # Return results with comprehensive timing
        if upload_results:
            response = {
                'success': True,
                'message': f"Successfully uploaded {len(upload_results)} file(s)",
                'uploads': upload_results,
                'timing': comprehensive_timing
            }
            if failed_uploads:
                response['failed'] = failed_uploads
            
            logger.info(" === UPLOAD SUCCESS ===")
            return jsonify(response), 200
        else:
            logger.error(f" === ALL UPLOADS FAILED after {total_time:.2f}s ===")
            return jsonify({
                'success': False,
                'message': "All uploads failed",
                'failed': failed_uploads,
                'timing': comprehensive_timing
            }), 400
        
    except Exception as e:
        total_time = time.time() - start_time
        error_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        # Comprehensive error timing
        error_timing = {
            'total_time_seconds': round(total_time, 2),
            'started_at': start_datetime,
            'error_at': error_datetime,
            'request_processing_time': round(timing_data.get('request_processing_time', 0), 3),
            'directory_creation_time': round(timing_data.get('directory_creation_time', 0), 3),
            'partial_file_timings': timing_data.get('individual_files', [])
        }
        
        logger.error(f" === UPLOAD ERROR after {total_time:.2f}s === {str(e)}")
        logger.error(f"Error occurred at: {error_datetime}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        logger.error(f" ERROR TIMING DATA: {error_timing}")
        
        return jsonify({
            'success': False, 
            'message': str(e),
            'timing': error_timing
        }), 500

    
@video_bp.route('/delete_video', methods=['POST'])
def delete_video_post():
    """
    Delete a video file using POST method (frontend compatibility)
    
    Request Body:
        video_name: The name of the video file to delete
        
    Returns:
        JSON response indicating success/failure
    """
    try:
        data = request.get_json()
        if not data or 'video_name' not in data:
            return jsonify(format_system_error_response(
                501,  # SYSTEM_CONFIGURATION_ERROR
                {'missing_field': 'video_name'}
            )), 400
        
        video_name = data['video_name']
        logger.info(f"Received delete request for video: {video_name}")
        
        # Secure the filename
        secure_name = secure_filename(video_name)
        
        if not secure_name:
            return jsonify({
                'success': False,
                'message': 'Invalid filename provided'
            }), 400
        
        # Get folders from app config
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'raw_video_file')
        download_folder = current_app.config.get('DOWNLOAD_FOLDER', 'resized_video')
        
        logger.info(f"Looking for video files in: upload_folder={upload_folder}, download_folder={download_folder}")
        
        deleted_files = []
        errors = []
        
        # Try to delete from raw videos folder (uploads)
        raw_path = os.path.join(upload_folder, secure_name)
        logger.info(f"Checking raw video path: {raw_path}")
        
        if os.path.exists(raw_path):
            try:
                os.remove(raw_path)
                deleted_files.append(f"raw/{secure_name}")
                logger.info(f" Deleted raw video file: {raw_path}")
            except Exception as e:
                error_msg = f"Failed to delete raw file: {str(e)}"
                errors.append(error_msg)
                logger.error(f" {error_msg}")
        else:
            logger.info(f"Raw video file not found: {raw_path}")
        
        # Try to delete from resized videos folder (with and without 2k_ prefix)
        resized_path = os.path.join(download_folder, secure_name)
        resized_path_with_prefix = os.path.join(download_folder, f"2k_{secure_name}")
        
        logger.info(f"Checking resized video paths: {resized_path}, {resized_path_with_prefix}")
        
        # Delete resized file without prefix
        if os.path.exists(resized_path):
            try:
                os.remove(resized_path)
                deleted_files.append(f"resized/{secure_name}")
                logger.info(f" Deleted resized video file: {resized_path}")
            except Exception as e:
                error_msg = f"Failed to delete resized file: {str(e)}"
                errors.append(error_msg)
                logger.error(f" {error_msg}")
        else:
            logger.info(f"Resized video file not found: {resized_path}")
        
        # Delete resized file with 2k_ prefix
        if os.path.exists(resized_path_with_prefix):
            try:
                os.remove(resized_path_with_prefix)
                deleted_files.append(f"resized/2k_{secure_name}")
                logger.info(f" Deleted resized video file with prefix: {resized_path_with_prefix}")
            except Exception as e:
                error_msg = f"Failed to delete resized file with prefix: {str(e)}"
                errors.append(error_msg)
                logger.error(f" {error_msg}")
        else:
            logger.info(f"Resized video file with prefix not found: {resized_path_with_prefix}")
        
        # Check if any files were deleted
        if not deleted_files and not errors:
            return jsonify(format_system_error_response(
                224,  # Container not found (or create a video-specific code)
                {
                    'video_name': secure_name,
                    'searched_locations': [
                        f"raw/{secure_name}",
                        f"resized/{secure_name}",
                        f"resized/2k_{secure_name}"
                    ]
                }
            )), 404
        
        # Prepare response
        if deleted_files and not errors:
            # Complete success
            logger.info(f"Successfully deleted video '{secure_name}': {deleted_files}")
            return jsonify({
                'success': True,
                'message': f'Successfully deleted video "{secure_name}"',
                'deleted_files': deleted_files
            }), 200
        elif deleted_files and errors:
            # Partial success
            logger.warning(f"Partially deleted video '{secure_name}': deleted={deleted_files}, errors={errors}")
            return jsonify({
                'success': True,
                'message': f'Partially deleted video "{secure_name}"',
                'deleted_files': deleted_files,
                'errors': errors
            }), 200
        elif errors and not deleted_files:
            return jsonify(format_system_error_response(
                503,  # SYSTEM_PERMISSION_DENIED
                {'video_name': secure_name, 'errors': errors}
            )), 500
        else:
            # Complete failure
            logger.error(f"Failed to delete video '{secure_name}': {errors}")
            return jsonify({
                'success': False,
                'message': f'Failed to delete video "{secure_name}"',
                'errors': errors
            }), 500
        
    except Exception as e:
        return jsonify(format_system_error_response(
            506,  # SYSTEM_INTERNAL_ERROR
            {'operation': 'delete_video', 'error': str(e)}
        )), 500


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
                        'path': f"/uploads/{job['resized_filename']}"
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
                'path': f"/uploads/{job['resized_filename']}"
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


@video_bp.route('/video_status', methods=['GET'])
def get_video_status():
    """Get detailed status of video files and processing jobs"""
    try:
        # Get folders
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'raw_video_file')
        download_folder = current_app.config.get('DOWNLOAD_FOLDER', 'resized_video')
        
        # Count files in each folder
        raw_videos = []
        uploads = []
        
        if os.path.exists(upload_folder):
            raw_videos = [f for f in os.listdir(upload_folder) 
                         if f.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.webm'))]
        
        if os.path.exists(download_folder):
            uploads = [f for f in os.listdir(download_folder) 
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
                'uploads': len(uploads),
                'active_processing_jobs': len(active_jobs),
                'completed_jobs': len(completed_jobs),
                'failed_jobs': len(failed_jobs),
                'total_jobs': len(processing_jobs)
            },
            'raw_video_files': raw_videos,
            'resized_video_files': uploads,
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