from flask import Blueprint
import logging

from .routes import multi_video_bp, split_screen_bp, status_bp

# Configure logger
logger = logging.getLogger(__name__)

# Create main blueprint
stream_bp = Blueprint('stream_management', __name__)

def register_stream_routes():
    """Register all stream management sub-blueprints"""
    
    # Register multi-video routes
    stream_bp.register_blueprint(multi_video_bp, url_prefix='/multi_video')
    
    # Register split-screen routes  
    stream_bp.register_blueprint(split_screen_bp, url_prefix='/split_screen')
    
    # Register status routes
    stream_bp.register_blueprint(status_bp, url_prefix='/status')
    
    logger.info("Registered all stream management routes")

# Register routes when module is imported
register_stream_routes()

# Backward compatibility - expose original endpoints at root level
from .routes.multi_video_routes import start_multi_video_srt
from .routes.split_screen_routes import start_split_screen_srt  
from .routes.status_routes import stop_group_srt, get_streaming_status, get_all_streaming_statuses

# Register backward compatible routes
@stream_bp.route("/start_multi_video_srt", methods=["POST"])
def legacy_start_multi_video_srt():
    """Legacy endpoint for backward compatibility"""
    from .routes.multi_video_routes import start_multi_video_srt
    return start_multi_video_srt()

@stream_bp.route("/start_split_screen_srt", methods=["POST"])  
def legacy_start_split_screen_srt():
    """Legacy endpoint for backward compatibility"""
    from .routes.split_screen_routes import start_split_screen_srt
    return start_split_screen_srt()

@stream_bp.route("/stop_group_stream", methods=["POST"])
def legacy_stop_group_stream():
    """Legacy endpoint for backward compatibility"""
    from .routes.status_routes import stop_group_srt
    return stop_group_srt()

@stream_bp.route("/streaming_status/<group_id>", methods=["GET"])
def legacy_streaming_status(group_id: str):
    """Legacy endpoint for backward compatibility"""
    from .routes.status_routes import get_streaming_status
    return get_streaming_status(group_id)

@stream_bp.route("/all_streaming_statuses", methods=["GET"])
def legacy_all_streaming_statuses():
    """Legacy endpoint for backward compatibility"""
    from .routes.status_routes import get_all_streaming_statuses
    return get_all_streaming_statuses()

# Helper functions for backward compatibility
def get_persistent_streams_for_group(group_id: str, group_name: str, screen_count: int):
    """Legacy function for backward compatibility"""
    from .services import StreamIDService
    service = StreamIDService()
    return service.get_group_streams(group_id, group_name, screen_count)

def discover_group_from_docker(group_id: str):
    """Legacy function for backward compatibility"""
    from .services import DockerService
    group = DockerService.discover_group(group_id)
    return group.__dict__ if group else None

def find_running_ffmpeg_for_group_strict(group_id: str, group_name: str, container_id: str = None):
    """Legacy function for backward compatibility"""
    from .utils.monitoring_utils import ProcessMonitor
    return ProcessMonitor.find_ffmpeg_processes_for_group(group_id, group_name, container_id)

def test_ffmpeg_srt_connection(srt_ip: str, srt_port: int, group_name: str, sei: str):
    """Legacy function for backward compatibility"""
    from .services import SRTService
    return SRTService.test_connection(srt_ip, srt_port, group_name, sei)

def wait_for_srt_server(srt_ip: str, srt_port: int, timeout: int = 30):
    """Legacy function for backward compatibility"""
    from .services import SRTService
    return SRTService.wait_for_server(srt_ip, srt_port, timeout)

def generate_client_crop_info(screen_count: int, orientation: str, output_width: int, 
                            output_height: int, grid_rows: int = 2, grid_cols: int = 2):
    """Legacy function for backward compatibility"""
    from .models.stream_config import StreamConfig, Orientation
    from .utils.response_utils import ResponseFormatter
    
    config = StreamConfig(
        group_id="legacy",
        screen_count=screen_count,
        orientation=Orientation(orientation),
        output_width=output_width,
        output_height=output_height,
        grid_rows=grid_rows,
        grid_cols=grid_cols
    )
    
    return ResponseFormatter.generate_crop_info(config)

def debug_log_stream_info(group_id: str, group_name: str, stream_id: str, 
                         srt_ip: str, srt_port: int, mode: str = "", screen_count: int = 0):
    """Legacy debug logging function"""
    import logging
    logger = logging.getLogger(__name__)
    
    stream_path = f"live/{group_name}/{stream_id}"
    client_url = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={stream_path},m=request,latency=5000000"
    
    logger.info("="*60)
    logger.info(f" STREAM STARTED - {mode}")
    logger.info(f" Group: {group_name} (ID: {group_id})")
    logger.info(f" Stream ID: {stream_id}")
    logger.info(f" Stream Path: {stream_path}")
    logger.info(f" Client URL: {client_url}")
    logger.info(f" Test: ffplay '{client_url}'")
    logger.info("="*60)

# Export legacy functions for backward compatibility
__all__ = [
    'stream_bp',
    'get_persistent_streams_for_group',
    'discover_group_from_docker', 
    'find_running_ffmpeg_for_group_strict',
    'test_ffmpeg_srt_connection',
    'wait_for_srt_server',
    'generate_client_crop_info',
    'debug_log_stream_info'
]