import os
import time
import logging
from typing import Dict, Any, List
from ..models.stream_config import StreamConfig

logger = logging.getLogger(__name__)

class ResponseFormatter:
    """Utility class for formatting API responses"""
    
    @staticmethod
    def format_stream_response(
        config: StreamConfig,
        group_name: str,
        process_id: int,
        persistent_streams: Dict[str, str],
        client_stream_urls: Dict[str, str],
        mode: str = "multi_video"
    ) -> Dict[str, Any]:
        """Format successful stream start response"""
        canvas_width, canvas_height = config.canvas_dimensions
        
        response = {
            "message": f"{mode.replace('_', '-').title()} SRT streaming started for group '{group_name}'",
            "group_id": config.group_id,
            "group_name": group_name,
            "process_id": process_id,
            "configuration": {
                "screen_count": config.screen_count,
                "orientation": config.orientation.value,
                "canvas_resolution": f"{canvas_width}x{canvas_height}",
                "section_resolution": f"{config.output_width}x{config.output_height}",
                "mode": mode
            },
            "stream_info": {
                "stream_urls": client_stream_urls,
                "persistent_streams": persistent_streams,
                "crop_information": ResponseFormatter.generate_crop_info(config)
            },
            "status": "active"
        }
        
        # Add mode-specific configuration
        if mode == "multi_video" and config.video_files:
            response["configuration"]["video_files"] = [
                {
                    "screen": video_config.screen,
                    "file": os.path.basename(video_config.file_path),
                    "path": video_config.file_path
                } for video_config in config.video_files
            ]
        elif mode == "split_screen" and config.single_video_file:
            response["configuration"]["source_video"] = os.path.basename(config.single_video_file)
        
        if config.orientation.value == "grid":
            response["configuration"]["grid_layout"] = f"{config.grid_rows}x{config.grid_cols}"
        
        # Add test command
        combined_url = client_stream_urls.get("combined", "")
        if combined_url:
            response["test_result"] = f"ffplay '{combined_url}'"
        
        return response
    
    @staticmethod
    def generate_crop_info(config: StreamConfig) -> Dict[int, Dict[str, int]]:
        """Generate crop information for clients"""
        crop_info = {}
        
        for i in range(config.screen_count):
            if config.orientation.value == "horizontal":
                crop_info[i] = {
                    "width": config.output_width,
                    "height": config.output_height,
                    "x": i * config.output_width,
                    "y": 0
                }
            elif config.orientation.value == "vertical":
                crop_info[i] = {
                    "width": config.output_width,
                    "height": config.output_height,
                    "x": 0,
                    "y": i * config.output_height
                }
            elif config.orientation.value == "grid":
                cols = config.grid_cols
                rows = config.grid_rows
                if rows * cols != config.screen_count:
                    cols = int(config.screen_count ** 0.5)
                    rows = (config.screen_count + cols - 1) // cols
                
                row = i // cols
                col = i % cols
                crop_info[i] = {
                    "width": config.output_width,
                    "height": config.output_height,
                    "x": col * config.output_width,
                    "y": row * config.output_height
                }
        
        return crop_info
    
    @staticmethod
    def generate_client_stream_urls(
        config: StreamConfig,
        group_name: str,
        persistent_streams: Dict[str, str],
        stream_prefix: str = "combined"
    ) -> Dict[str, str]:
        """Generate client stream URLs for all streams"""
        client_stream_urls = {}
        
        # Combined stream URL
        combined_stream_path = f"live/{group_name}/{stream_prefix}_{config.group_id}"
        srt_params = "latency=5000000&connect_timeout=10000&rcvbuf=67108864&sndbuf=67108864"
        client_stream_urls["combined"] = f"srt://{config.srt_ip}:{config.srt_port}?streamid=#!::r={combined_stream_path},m=request&{srt_params}"
        
        # Individual screen URLs
        for i in range(config.screen_count):
            screen_key = f"test{i}"
            individual_stream_id = persistent_streams.get(screen_key)
            if individual_stream_id:
                individual_stream_path = f"live/{group_name}/{individual_stream_id}"
                client_stream_urls[f"screen{i}"] = f"srt://{config.srt_ip}:{config.srt_port}?streamid=#!::r={individual_stream_path},m=request&{srt_params}"
        
        return client_stream_urls
    
    @staticmethod
    def format_status_response(
        group_id: str,
        group_name: str,
        group_info: Dict[str, Any],
        running_processes: List[Dict[str, Any]],
        persistent_streams: Dict[str, str]
    ) -> Dict[str, Any]:
        """Format streaming status response"""
        is_streaming = len(running_processes) > 0
        
        # Generate client URLs if streaming
        client_stream_urls = {}
        available_streams = []
        
        if is_streaming:
            ports = group_info.get("ports", {})
            srt_port = ports.get("srt_port", 10080)
            srt_ip = "127.0.0.1"
            
            combined_stream_path = f"live/{group_name}/{persistent_streams['test']}"
            client_stream_urls["combined"] = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={combined_stream_path},m=request,latency=5000000"
            available_streams.append(combined_stream_path)
            
            screen_count = group_info.get("screen_count", 2)
            for i in range(screen_count):
                stream_name = f"screen{i}"
                screen_stream_id = persistent_streams.get(f"test{i}", f"screen{i}")
                screen_stream_path = f"live/{group_name}/{screen_stream_id}"
                client_stream_urls[stream_name] = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={screen_stream_path},m=request,latency=5000000"
                available_streams.append(screen_stream_path)
        
        return {
            "group_id": group_id,
            "group_name": group_name,
            "streaming_mode": group_info.get("streaming_mode", "multi_video"),
            "screen_count": group_info.get("screen_count", 2),
            "orientation": group_info.get("orientation", "horizontal"),
            "is_streaming": is_streaming,
            "process_count": len(running_processes),
            "process_id": running_processes[0]["pid"] if running_processes else None,
            "available_streams": available_streams,
            "client_stream_urls": client_stream_urls,
            "persistent_streams": persistent_streams,
            "running_processes": [
                {
                    "pid": proc["pid"],
                    "match_method": proc.get("match_method", "unknown"),
                    "uptime_seconds": time.time() - proc.get('create_time', time.time()),
                    "cmdline_preview": proc["cmdline"][:100] + "..." if len(proc["cmdline"]) > 100 else proc["cmdline"]
                } for proc in running_processes
            ],
            "status": "active" if is_streaming else "inactive",
            "docker_running": group_info.get("docker_running", False),
            "docker_status": group_info.get("docker_status", "unknown")
        }