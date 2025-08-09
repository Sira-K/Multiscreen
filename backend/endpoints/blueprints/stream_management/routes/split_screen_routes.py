from flask import Blueprint, request, jsonify
import subprocess
import logging

from ..models.stream_config import StreamConfig, Orientation, StreamingMode
from ..services import FFmpegService, SRTService, DockerService, StreamIDService, VideoValidationService
from ..utils.response_utils import ResponseFormatter
from errors.stream_management_errors import (
    StreamError, format_error_response,
    FFmpegException, SRTConnectionException, StreamConfigException
)

# Create blueprint
split_screen_bp = Blueprint('split_screen_stream', __name__)

# Configure logger
logger = logging.getLogger(__name__)

# Global services
stream_id_service = StreamIDService()

@split_screen_bp.route("/start_split_screen_srt", methods=["POST"])
def start_split_screen_srt():
    """Take one video file and split it across multiple screens"""
    try:
        data = request.get_json() or {}
        
        group_id = data.get("group_id")
        video_file = data.get("video_file")
        
        logger.info("="*60)
        logger.info(" STARTING SPLIT-SCREEN SRT STREAM")
        logger.info(f" Group ID: {group_id}")
        logger.info(f" Video file: {video_file}")
        logger.info("="*60)
        
        if not group_id or not video_file:
            logger.error(" Missing required parameters: group_id or video_file")
            return jsonify({"error": "group_id and video_file are required"}), 400
        
        # Discover group
        logger.info(f" Discovering group '{group_id}' from Docker...")
        group = DockerService.discover_group(group_id)
        if not group:
            logger.error(f" Group '{group_id}' not found in Docker")
            return jsonify({"error": f"Group '{group_id}' not found"}), 404
        
        group_name = group.name
        logger.info(f" Found group: '{group_name}'")
        
        # Check Docker status
        logger.info(f" Docker container status: {'Running' if group.docker_running else 'Stopped'}")
        
        if not group.docker_running:
            logger.error(f" Docker container for group '{group_name}' is not running")
            return jsonify({"error": f"Docker container for group '{group_name}' is not running"}), 400
        
        # Check for existing streams
        from ..utils.monitoring_utils import ProcessMonitor
        existing_ffmpeg = ProcessMonitor.find_ffmpeg_processes_for_group(group_id, group_name, group.container_id)
        if existing_ffmpeg:
            logger.warning(f"  Found {len(existing_ffmpeg)} existing FFmpeg process(es)")
            logger.info("   Streaming already active, returning current status")
            return jsonify({
                "message": f"Split-screen streaming already active for group '{group_name}'",
                "status": "already_active"
            }), 200
        
        logger.info(" No existing streams found")
        
        # Build stream configuration
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
            sei=data.get("sei", "681d5c8f-80cd-4847-930a-99b9484b4a32+000000"),
            streaming_mode=StreamingMode.SPLIT_SCREEN,
            single_video_file=video_file
        )
        
        logger.info("  Stream configuration:")
        logger.info(f"   Screen count: {stream_config.screen_count}")
        logger.info(f"   Orientation: {stream_config.orientation.value}")
        logger.info(f"   Output resolution: {stream_config.output_width}x{stream_config.output_height}")
        
        # Validate video file
        logger.info(f" Validating video file: {video_file}")
        try:
            validated_path = VideoValidationService.validate_single_video_file(video_file)
            stream_config.single_video_file = validated_path
        except FileNotFoundError as e:
            logger.error(f" Video file validation failed: {e}")
            return jsonify({"error": str(e)}), 404
        
        logger.info(" Video file validated")
        
        # Wait for SRT server
        logger.info(f" Waiting for SRT server at {stream_config.srt_ip}:{stream_config.srt_port}...")
        if not SRTService.wait_for_server(stream_config.srt_ip, stream_config.srt_port, timeout=30):
            logger.error(f" SRT server not ready after 30 seconds")
            return jsonify({"error": f"SRT server at {stream_config.srt_ip}:{stream_config.srt_port} not ready"}), 500
        logger.info(" SRT server is ready")
        
        # Test SRT connection
        logger.info(" Testing SRT connection...")
        test_result = SRTService.test_connection(stream_config.srt_ip, stream_config.srt_port, group_name, stream_config.sei)
        if not test_result["success"]:
            logger.error(f" SRT connection test failed: {test_result}")
            return jsonify({"error": "SRT connection test failed", "test_result": test_result}), 500
        logger.info(" SRT connection test passed")
        
        # Get persistent streams
        persistent_streams = stream_id_service.get_group_streams(group_id, group_name, stream_config.screen_count)
        logger.info(f" Persistent streams: {persistent_streams}")

        # Build FFmpeg command
        logger.info(" Building FFmpeg command...")
        ffmpeg_cmd = FFmpegService.build_split_screen_command(stream_config, persistent_streams)
        
        logger.info(f" FFmpeg command preview:")
        logger.info(f"   {' '.join(ffmpeg_cmd[:10])}...")
        logger.info(f"   Total arguments: {len(ffmpeg_cmd)}")
        
        # Start FFmpeg process
        logger.info(" Starting FFmpeg process...")
        process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=0
        )
        
        logger.info(f" FFmpeg process started with PID: {process.pid}")
        
        # Monitor FFmpeg startup
        logger.info(" Monitoring FFmpeg startup...")
        startup_success, streaming_detected = FFmpegService.monitor_process(
            process,
            stream_type="Split-screen FFmpeg", 
            startup_timeout=5,
            startup_max_lines=20
        )
        
        if not startup_success:
            if process.poll() is not None:
                logger.error(f" FFmpeg process died with exit code: {process.returncode}")
                return jsonify({"error": f"Split-screen FFmpeg failed to start"}), 500
            logger.warning("  FFmpeg startup reported failure but process is still running")
        
        if not streaming_detected:
            logger.warning("  No streaming output detected during startup monitoring")
        else:
            logger.info(" Streaming output detected")
        
        # Generate client stream URLs
        client_stream_urls = ResponseFormatter.generate_client_stream_urls(
            stream_config, group_name, persistent_streams, "split"
        )
        
        # Generate response
        response = ResponseFormatter.format_stream_response(
            stream_config, group_name, process.pid, persistent_streams, 
            client_stream_urls, "split_screen"
        )
        
        logger.info("="*60)
        logger.info(" SPLIT-SCREEN STREAMING STARTED SUCCESSFULLY")
        logger.info(f" Group: {group_name}")
        logger.info(f" Process PID: {process.pid}")
        logger.info(f" Screens: {stream_config.screen_count}")
        logger.info(f" Combined Stream: {client_stream_urls['combined']}")
        logger.info("="*60)
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error("="*60)
        logger.error(" EXCEPTION IN start_split_screen_srt")
        logger.error(f" Error type: {type(e).__name__}")
        logger.error(f" Error message: {str(e)}")
        logger.error("Stack trace:", exc_info=True)
        logger.error("="*60)
        return jsonify({"error": str(e)}), 500