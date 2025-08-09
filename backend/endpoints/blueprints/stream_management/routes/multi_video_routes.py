# backend/endpoints/blueprints/stream_management/routes/multi_video_routes.py
from flask import Blueprint, request, jsonify
import subprocess
import logging
import time
from typing import List

from ..models.stream_config import StreamConfig, VideoFileConfig, Orientation, StreamingMode
from ..services import FFmpegService, SRTService, DockerService, StreamIDService, VideoValidationService
from ..utils.response_utils import ResponseFormatter
from errors.stream_management_errors import (
    StreamError, format_error_response, 
    FFmpegException, SRTConnectionException, StreamConfigException
)

# Create blueprint
multi_video_bp = Blueprint('multi_video_stream', __name__)

# Configure logger
logger = logging.getLogger(__name__)

# Global services
stream_id_service = StreamIDService()

def extract_sei_uuid(sei_value: str) -> str:
    """Extract UUID from SEI value, removing static timestamp"""
    if not sei_value:
        return "681d5c8f-80cd-4847-930a-99b9484b4a32"
    
    if '+' in sei_value:
        uuid_part = sei_value.split('+')[0]
        logger.debug(f"Extracted UUID from SEI: {uuid_part}")
        return uuid_part
    
    return sei_value

@multi_video_bp.route("/start_multi_video_srt", methods=["POST"])
def start_multi_video_srt():
    """Combine multiple video files and stream as one SRT stream with dynamic timestamps"""
    try:
        data = request.get_json() or {}
        
        group_id = data.get("group_id")
        video_files_config = data.get("video_files", [])
        
        logger.info("="*60)
        logger.info(" STARTING MULTI-VIDEO SRT STREAM (OpenVideoWalls)")
        logger.info(f" Group ID: {group_id}")
        logger.info(f" Video files count: {len(video_files_config)}")
        logger.info(" Implementation: Dynamic Timestamps as per OpenVideoWalls paper")
        logger.info("="*60)
        
        # Validate required parameters
        if not group_id or not video_files_config:
            logger.error(" Missing required parameters: group_id or video_files")
            return jsonify(format_error_response(
                StreamError.STREAM_MISSING_PARAMETERS,
                {'missing': ['group_id', 'video_files'] if not group_id and not video_files_config 
                           else ['group_id'] if not group_id else ['video_files']}
            )), 400
        
        # Log video files configuration
        logger.info(" Video files configuration:")
        for idx, video_config in enumerate(video_files_config):
            logger.info(f"   Screen {video_config.get('screen', idx)}: {video_config.get('file', 'Unknown')}")
        
        # Discover group
        logger.info(f" Discovering group '{group_id}' from Docker...")
        group = DockerService.discover_group(group_id)
        if not group:
            logger.error(f" Group '{group_id}' not found in Docker")
            return jsonify(format_error_response(
                StreamError.STREAM_GROUP_NOT_FOUND,
                {'group_id': group_id}
            )), 404

        group_name = group.name
        logger.info(f" Found group: '{group_name}'")
        
        # Check Docker status
        logger.info(f" Docker container status: {'Running' if group.docker_running else 'Stopped'}")
        
        if not group.docker_running:
            logger.error(f" Docker container for group '{group_name}' is not running")
            return jsonify(format_error_response(
                StreamError.STREAM_GROUP_NOT_RUNNING,
                {'group_id': group_id, 'group_name': group_name, 'container_status': 'stopped'}
            )), 400
        
        # Check for existing streams
        from ..utils.monitoring_utils import ProcessMonitor
        existing_ffmpeg = ProcessMonitor.find_ffmpeg_processes_for_group(group_id, group_name, group.container_id)
        if existing_ffmpeg:
            logger.warning(f"  Found {len(existing_ffmpeg)} existing FFmpeg process(es)")
            return jsonify(format_error_response(
                StreamError.STREAM_ALREADY_EXISTS,
                {'group_id': group_id, 'process_count': len(existing_ffmpeg), 
                 'process_pids': [p['pid'] for p in existing_ffmpeg]}
            )), 409
        
        logger.info(" No existing streams found")
        
        # Extract UUID from SEI for dynamic timestamp support
        sei_raw = data.get("sei", "681d5c8f-80cd-4847-930a-99b9484b4a32+000000")
        from ..utils.ffmpeg_compatibility import fix_sei_uuid_extraction
        sei_uuid = fix_sei_uuid_extraction(sei_raw)
        
        # Build stream configuration
        video_file_configs = [
            VideoFileConfig(screen=config.get("screen", i), file=config.get("file"))
            for i, config in enumerate(video_files_config)
        ]
        
        logger.info(f"DEBUG: sei_raw = {sei_raw}")
        logger.info(f"DEBUG: sei_uuid = {sei_uuid}")

        stream_config = StreamConfig(
            group_id=group_id,
            screen_count=data.get("screen_count", group.screen_count),
            orientation=Orientation(data.get("orientation", group.orientation)),
            output_width=data.get("output_width", 1920),
            output_height=data.get("output_height", 1080),
            grid_rows=data.get("grid_rows", 2),
            grid_cols=data.get("grid_cols", 2),
            srt_ip=data.get("srt_ip", "127.0.0.1"),
            srt_port=data.get("srt_port", group.ports.get("srt_port", 10080)),
            sei=sei_uuid,  # Use UUID only - timestamps will be dynamic  <-- THIS LINE IS CORRECT
            streaming_mode=StreamingMode.MULTI_VIDEO,
            video_files=video_file_configs,
            framerate=data.get("framerate", 30),
            bitrate=data.get("bitrate", "3000k")
        )
        
        # Validate configuration
        if len(video_file_configs) != stream_config.screen_count:
            logger.error(f" Video file count ({len(video_file_configs)}) doesn't match screen count ({stream_config.screen_count})")
            return jsonify(format_error_response(
                StreamError.STREAM_CONFIG_MISMATCH,
                {'video_count': len(video_file_configs), 'screen_count': stream_config.screen_count}
            )), 400
        
        # Log dynamic timestamp configuration
        current_time = time.time()
        offset_seconds = 2.0
        buffer_time = current_time + offset_seconds
        
        logger.info("  Stream configuration (OpenVideoWalls):")
        logger.info(f"   Screen count: {stream_config.screen_count}")
        logger.info(f"   Orientation: {stream_config.orientation.value}")
        logger.info(f"   Output resolution: {stream_config.output_width}x{stream_config.output_height}")
        logger.info(f"   SEI UUID: {stream_config.sei}")
        logger.info(f"   Timestamp mode: DYNAMIC")
        logger.info(f"   Current Unix time: {int(current_time)}")
        logger.info(f"   Buffer offset: {offset_seconds}s")
        logger.info(f"   First frame time: {int(buffer_time)}")
        
        # Validate video files
        logger.info(" Validating video files...")
        try:
            VideoValidationService.validate_video_files(stream_config.video_files)
        except (FileNotFoundError, ValueError) as e:
            return jsonify(format_error_response(
                StreamError.VIDEO_FILE_NOT_FOUND,
                {'error': str(e)}
            )), 404
        
        logger.info(f" All {len(stream_config.video_files)} video files validated")
        
        # Wait for SRT server
        logger.info(f" Waiting for SRT server at {stream_config.srt_ip}:{stream_config.srt_port}...")
        if not SRTService.wait_for_server(stream_config.srt_ip, stream_config.srt_port, timeout=30):
            logger.error(f" SRT server not ready after 30 seconds")
            return jsonify(format_error_response(
                StreamError.SRT_CONNECTION_TIMEOUT,
                {'srt_ip': stream_config.srt_ip, 'srt_port': stream_config.srt_port, 'timeout': 30}
            )), 503
        
        # Test SRT connection with UUID only (dynamic timestamps will be added by FFmpeg)
        logger.info(" Testing SRT connection...")
        test_result = SRTService.test_connection(stream_config.srt_ip, stream_config.srt_port, group_name, stream_config.sei)
        if not test_result["success"]:
            logger.error(f" SRT connection test failed: {test_result}")
            return jsonify(format_error_response(
                StreamError.SRT_CONNECTION_REFUSED,
                {'srt_ip': stream_config.srt_ip, 'srt_port': stream_config.srt_port, 'test_result': test_result}
            )), 503
        
        # Get persistent streams
        persistent_streams = stream_id_service.get_group_streams(group_id, group_name, stream_config.screen_count)
        logger.info(f" Using persistent stream IDs: {persistent_streams}")

        # Build FFmpeg command with dynamic timestamps
        logger.info(" Building FFmpeg command with OpenVideoWalls dynamic timestamps...")
        ffmpeg_cmd = FFmpegService.build_multi_video_command_with_dynamic_timestamps(stream_config, persistent_streams)
        
        logger.info(f" FFmpeg command preview (dynamic timestamps):")
        logger.info(f"   {' '.join(ffmpeg_cmd[:10])}...")
        logger.info(f"   Total arguments: {len(ffmpeg_cmd)}")
        
        # Log the dynamic timestamp implementation details
        logger.info(" Dynamic Timestamp Implementation:")
        logger.info("   - Server embeds Unix timestamps in SEI metadata")
        logger.info("   - Formula: timestamp = current_time + offset + frame_time")
        logger.info("   - Client synchronizes using these timestamps")
        logger.info("   - Follows OpenVideoWalls paper specification")
        
        # Debug: Show example SEI values that will be generated
        logger.info(" SEI Debug Information:")
        logger.info(f"   Base UUID: {stream_config.sei}")
        logger.info(f"   Current Unix time: {int(current_time)}")
        logger.info(f"   Buffer offset: {offset_seconds}s")
        first_frame_time = int(current_time + offset_seconds)
        logger.info(f"   First frame Unix time: {first_frame_time}")
        logger.info(f"   First frame hex: {first_frame_time * 1000:016x}")
        logger.info(f"   Example SEI (frame 0): {stream_config.sei}+{first_frame_time * 1000:016x}")
        logger.info(f"   Example SEI (frame 1): {stream_config.sei}+{int((current_time + offset_seconds + 1/30) * 1000):016x}")
        logger.info(f"   SEI will change dynamically for each frame")
        
        # Start FFmpeg process
        logger.info(" Starting FFmpeg process...")
        try:
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=0
            )
        except FileNotFoundError:
            return jsonify(format_error_response(
                StreamError.FFMPEG_COMMAND_INVALID,
                {'reason': 'FFmpeg executable not found'}
            )), 500
        except Exception as e:
            return jsonify(format_error_response(
                StreamError.FFMPEG_START_FAILURE,
                {'error': str(e), 'command_length': len(ffmpeg_cmd)}
            )), 500
        
        logger.info(f" FFmpeg process started with PID: {process.pid}")
        
        # Monitor FFmpeg startup
        logger.info(" Monitoring FFmpeg startup...")
        startup_success, streaming_detected = FFmpegService.monitor_process(
            process, 
            stream_type="Multi-video FFmpeg (OpenVideoWalls)",
            startup_timeout=8,  # Increased timeout for dynamic timestamp processing
            startup_max_lines=25
        )
        
        if not startup_success:
            if process.poll() is not None:
                logger.error(f" FFmpeg process died with exit code: {process.returncode}")
                return jsonify(format_error_response(
                    StreamError.FFMPEG_PROCESS_DIED,
                    {'exit_code': process.returncode, 'pid': process.pid}
                )), 500
            else:
                logger.warning("  FFmpeg startup reported issues but process is still running")
        
        if not streaming_detected:
            logger.warning("  No streaming output detected during startup monitoring")
            logger.info("  This may be normal with dynamic timestamp processing")
        else:
            logger.info(" Streaming output detected - dynamic timestamps active")
        
        # Generate client stream URLs
        client_stream_urls = ResponseFormatter.generate_client_stream_urls(
            stream_config, group_name, persistent_streams, "combined"
        )
        
        # Generate response with dynamic timestamp information
        response = ResponseFormatter.format_stream_response(
            stream_config, group_name, process.pid, persistent_streams, 
            client_stream_urls, "multi_video"
        )
        
        # Add OpenVideoWalls specific information
        response["openvideowalls"] = {
            "timestamp_mode": "dynamic",
            "sei_uuid": stream_config.sei,
            "synchronization": "unix_timestamp_based",
            "paper_implementation": True,
            "current_unix_time": int(time.time()),
            "buffer_offset_seconds": offset_seconds
        }
        
        logger.info("="*60)
        logger.info(" MULTI-VIDEO STREAMING STARTED (OpenVideoWalls)")
        logger.info(f" Group: {group_name}")
        logger.info(f" Process PID: {process.pid}")
        logger.info(f" Screens: {stream_config.screen_count}")
        logger.info(f" Timestamp mode: DYNAMIC")
        logger.info(f" Combined Stream: {client_stream_urls['combined']}")
        logger.info(f" Client synchronization: Unix timestamp based")
        logger.info("="*60)
        
        return jsonify(response), 200
        
    except FFmpegException as e:
        logger.error(f"FFmpeg error: {e}")
        return jsonify(format_error_response(e.error_code, e.context)), 500
    except SRTConnectionException as e:
        logger.error(f"SRT connection error: {e}")
        return jsonify(format_error_response(e.error_code, e.context)), 503
    except StreamConfigException as e:
        logger.error(f"Stream configuration error: {e}")
        return jsonify(format_error_response(e.error_code, e.context)), 400
    except Exception as e:
        logger.error(f"Unexpected error in start_multi_video_srt: {e}", exc_info=True)
        return jsonify(format_error_response(
            StreamError.FFMPEG_CRITICAL_ERROR,
            {'error': str(e), 'type': type(e).__name__}
        )), 500