from flask import Blueprint, request, jsonify
import time
import logging

from ..services import DockerService, StreamIDService
from ..utils.monitoring_utils import ProcessMonitor
from ..utils.response_utils import ResponseFormatter

# Create blueprint
status_bp = Blueprint('stream_status', __name__)

# Configure logger
logger = logging.getLogger(__name__)

# Global services
stream_id_service = StreamIDService()

@status_bp.route("/stop_group_stream", methods=["POST"])
def stop_group_srt():
    """Stop all FFmpeg processes for a group"""
    try:
        data = request.get_json() or {}
        group_id = data.get("group_id")
        
        if not group_id:
            return jsonify({"error": "group_id is required"}), 400
        
        group = DockerService.discover_group(group_id)
        if not group:
            return jsonify({"error": f"Group '{group_id}' not found"}), 404
        
        group_name = group.name
        container_id = group.container_id
        
        running_processes = ProcessMonitor.find_ffmpeg_processes_for_group(group_id, group_name, container_id)
        
        if not running_processes:
            return jsonify({
                "message": f"No active streams found for group '{group_name}'",
                "status": "already_stopped"
            }), 200
        
        # Stop processes
        stopped_processes, failed_processes = ProcessMonitor.stop_processes(running_processes)
        
        return jsonify({
            "message": f"Stopped streams for group '{group_name}'",
            "group_id": group_id,
            "group_name": group_name,
            "stopped_processes": len(stopped_processes),
            "failed_processes": len(failed_processes),
            "status": "stopped"
        }), 200
        
    except Exception as e:
        logger.error(f"Error stopping group SRT: {e}")
        return jsonify({"error": str(e)}), 500

@status_bp.route("/streaming_status/<group_id>", methods=["GET"])
def get_streaming_status(group_id: str):
    """Get streaming status for a specific group"""
    try:
        group = DockerService.discover_group(group_id)
        if not group:
            return jsonify({"error": f"Group '{group_id}' not found"}), 404
        
        group_name = group.name
        container_id = group.container_id
        
        running_processes = ProcessMonitor.find_ffmpeg_processes_for_group(group_id, group_name, container_id)
        
        # Get persistent streams for this group
        persistent_streams = stream_id_service.get_group_streams(group_id, group_name, group.screen_count)
        
        # Format response
        response = ResponseFormatter.format_status_response(
            group_id, group_name, group.__dict__, running_processes, persistent_streams
        )
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error getting streaming status: {e}")
        return jsonify({"error": str(e)}), 500

@status_bp.route("/all_streaming_statuses", methods=["GET"])
def get_all_streaming_statuses():
    """Get streaming status for all groups"""
    try:
        # Get all FFmpeg processes
        all_ffmpeg_processes = ProcessMonitor.get_all_ffmpeg_processes()
        
        # Get all groups from Docker
        all_groups = DockerService.get_all_groups()
        
        streaming_statuses = {}
        assigned_pids = set()
        
        for group in all_groups:
            group_id = group.id
            group_name = group.name
            
            # Find processes for this group
            group_processes = ProcessMonitor.find_ffmpeg_processes_for_group(
                group_id, group_name, group.container_id
            )
            
            # Track assigned PIDs
            for proc in group_processes:
                assigned_pids.add(proc["pid"])
            
            is_streaming = len(group_processes) > 0
            
            # Determine health status
            container_health = "HEALTHY" if group.docker_running and is_streaming else "UNHEALTHY" if group.docker_running else "OFFLINE"
            
            # Get persistent streams
            persistent_streams = stream_id_service.get_group_streams(group_id, group_name, group.screen_count)
            
            # Store status
            streaming_statuses[group_id] = {
                "group_name": group_name,
                "streaming_mode": group.streaming_mode,
                "is_streaming": is_streaming,
                "process_count": len(group_processes),
                "docker_running": group.docker_running,
                "docker_status": group.docker_status,
                "container_name": group.container_name,
                "container_id": group.container_id,
                "health_status": container_health,
                "persistent_streams": persistent_streams,
                "processes": [
                    {
                        "pid": proc["pid"],
                        "uptime_seconds": time.time() - proc.get('create_time', time.time()),
                        "started_at": time.strftime('%Y-%m-%d %H:%M:%S', 
                                                   time.localtime(proc.get('create_time', 0))),
                        "cmdline_preview": proc["cmdline"][:100] + "..." if len(proc["cmdline"]) > 100 else proc["cmdline"]
                    } for proc in group_processes
                ]
            }
        
        # Calculate summary
        active_streams = sum(1 for status in streaming_statuses.values() if status["is_streaming"])
        total_processes = sum(status["process_count"] for status in streaming_statuses.values())
        healthy_groups = sum(1 for status in streaming_statuses.values() if status["health_status"] == "HEALTHY")
        
        # Detect orphaned processes
        orphaned_processes = [proc for proc in all_ffmpeg_processes if proc["pid"] not in assigned_pids]
        
        return jsonify({
            "streaming_statuses": streaming_statuses,
            "summary": {
                "total_groups": len(streaming_statuses),
                "active_streams": active_streams,
                "healthy_groups": healthy_groups,
                "total_ffmpeg_processes": len(all_ffmpeg_processes),
                "assigned_processes": len(assigned_pids),
                "orphaned_processes": len(orphaned_processes),
                "containers_found": len(all_groups)
            },
            "orphaned_processes": [
                {
                    "pid": proc["pid"],
                    "uptime_seconds": time.time() - proc.get('create_time', time.time()),
                    "cmdline_preview": proc["cmdline"][:100] + "..." if len(proc["cmdline"]) > 100 else proc["cmdline"]
                } for proc in orphaned_processes
            ]
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting all streaming statuses: {e}")
        return jsonify({"error": str(e)}), 500