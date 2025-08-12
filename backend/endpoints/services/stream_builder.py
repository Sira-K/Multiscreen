"""
Stream Builder Service

Builds FFmpeg commands for different stream types.
"""

import logging
import uuid
from typing import Dict, List
from .ffmpeg_service import FFmpegService

logger = logging.getLogger(__name__)


class StreamBuilder:
    """Builds FFmpeg commands for streaming operations"""
    
    def __init__(self):
        self.ffmpeg_service = FFmpegService()
    
    def build_split_screen_command(self, video_path: str, group: Dict, srt_config: Dict, **kwargs) -> List[str]:
        """Build FFmpeg command for split-screen streaming"""
        try:
            # Extract parameters
            screen_count = group.get("screen_count", 2)
            orientation = kwargs.get("orientation", "horizontal")
            output_width = kwargs.get("output_width", 1920)
            output_height = kwargs.get("output_height", 1080)
            canvas_width = kwargs.get("canvas_width", output_width * screen_count)
            canvas_height = kwargs.get("canvas_height", output_height)
            framerate = kwargs.get("framerate", 30)
            bitrate = kwargs.get("bitrate", "3000k")
            sei = kwargs.get("sei", self._generate_sei())
            
            # Calculate grid layout if needed
            grid_rows = kwargs.get("grid_rows", 2)
            grid_cols = kwargs.get("grid_cols", 2)
            
            if orientation == "grid":
                canvas_width = output_width * grid_cols
                canvas_height = output_height * grid_rows
            
            # Build filter complex
            filter_complex = self._build_split_screen_filter(
                screen_count, orientation, output_width, output_height,
                canvas_width, canvas_height, grid_rows, grid_cols
            )
            
            # Build base command
            ffmpeg_cmd = self._build_base_command(video_path, filter_complex)
            
            # Add outputs
            ffmpeg_cmd = self._add_split_screen_outputs(
                ffmpeg_cmd, group, srt_config, screen_count, 
                output_width, output_height, framerate, bitrate, sei
            )
            
            logger.info(f"Built split-screen FFmpeg command with {len(ffmpeg_cmd)} arguments")
            return ffmpeg_cmd
            
        except Exception as e:
            logger.error(f"Failed to build split-screen command: {e}")
            raise
    
    def build_multi_video_command(self, video_paths: List[str], group: Dict, srt_config: Dict, **kwargs) -> List[str]:
        """Build FFmpeg command for multi-video streaming"""
        try:
            # Extract parameters
            layout = kwargs.get("layout", "grid")
            framerate = kwargs.get("framerate", 30)
            bitrate = kwargs.get("bitrate", "3000k")
            sei = kwargs.get("sei", self._generate_sei())
            
            # Build filter complex
            filter_complex = self._build_multi_video_filter(video_paths, layout)
            
            # Build base command
            ffmpeg_cmd = self._build_base_command(video_paths[0], filter_complex)
            
            # Add multiple video inputs
            for i, video_path in enumerate(video_paths[1:], 1):
                ffmpeg_cmd.extend(["-i", video_path])
            
            # Add outputs
            ffmpeg_cmd = self._add_multi_video_outputs(
                ffmpeg_cmd, group, srt_config, len(video_paths),
                framerate, bitrate, sei
            )
            
            logger.info(f"Built multi-video FFmpeg command with {len(ffmpeg_cmd)} arguments")
            return ffmpeg_cmd
            
        except Exception as e:
            logger.error(f"Failed to build multi-video command: {e}")
            raise
    
    def _build_split_screen_filter(self, screen_count: int, orientation: str, 
                                 output_width: int, output_height: int,
                                 canvas_width: int, canvas_height: int,
                                 grid_rows: int, grid_cols: int) -> str:
        """Build filter complex for split-screen layout"""
        filter_parts = []
        
        # Start with scaling and padding
        filter_parts.append(
            f"[0:v]scale={canvas_width}:{canvas_height}:"
            f"force_original_aspect_ratio=decrease,"
            f"pad={canvas_width}:{canvas_height}:"
            f"(ow-iw)/2:(oh-ih)/2:black"
        )
        
        # Add split to create multiple copies
        output_labels = ["[full]"] + [f"[copy{i}]" for i in range(screen_count)]
        filter_parts.append(f"split={screen_count + 1}" + "".join(output_labels))
        
        # Add crop filters for each screen
        for i in range(screen_count):
            if orientation == "horizontal":
                x_pos = i * output_width
                y_pos = 0
            elif orientation == "vertical":
                x_pos = 0
                y_pos = i * output_height
            elif orientation == "grid":
                row = i // grid_cols
                col = i % grid_cols
                x_pos = col * output_width
                y_pos = row * output_height
            else:
                x_pos = i * output_width
                y_pos = 0
            
            filter_parts.append(f"[copy{i}]crop={output_width}:{output_height}:{x_pos}:{y_pos}[screen{i}]")
        
        return ",".join(filter_parts)
    
    def _build_multi_video_filter(self, video_paths: List[str], layout: str) -> str:
        """Build filter complex for multi-video layout"""
        filter_parts = []
        
        # Create input labels
        input_labels = [f"[{i}:v]" for i in range(len(video_paths))]
        
        if layout == "grid":
            # Simple grid layout
            filter_parts.append(f"{','.join(input_labels)}hstack=inputs={len(video_paths)}[combined]")
        elif layout == "horizontal":
            filter_parts.append(f"{','.join(input_labels)}hstack=inputs={len(video_paths)}[combined]")
        elif layout == "vertical":
            filter_parts.append(f"{','.join(input_labels)}vstack=inputs={len(video_paths)}[combined]")
        
        return ",".join(filter_parts)
    
    def _build_base_command(self, video_path: str, filter_complex: str) -> List[str]:
        """Build base FFmpeg command"""
        ffmpeg_path = self.ffmpeg_service.find_ffmpeg_executable()
        
        return [
            ffmpeg_path,
            "-y",
            "-v", "error",
            "-stats",
            "-stream_loop", "-1",
            "-re",
            "-i", video_path,
            "-filter_complex", filter_complex
        ]
    
    def _add_split_screen_outputs(self, ffmpeg_cmd: List[str], group: Dict, 
                                 srt_config: Dict, screen_count: int,
                                 output_width: int, output_height: int,
                                 framerate: int, bitrate: str, sei: str) -> List[str]:
        """Add outputs for split-screen streaming"""
        # Encoding parameters
        encoding_params = self._build_encoding_params(framerate, bitrate, sei)
        
        # SRT parameters
        srt_params = self._build_srt_params()
        
        # Group info
        group_name = group.get("name", "unknown")
        base_stream_id = self._generate_stream_id()
        
        # Combined stream output
        combined_stream_path = f"live/{group_name}/split_{base_stream_id}"
        combined_url = f"srt://{srt_config['ip']}:{srt_config['port']}?streamid=#!::r={combined_stream_path},m=publish&{srt_params}"
        ffmpeg_cmd.extend(["-map", "[full]"] + encoding_params + [combined_url])
        
        # Individual screen outputs
        for i in range(screen_count):
            individual_stream_id = f"screen{i}_{base_stream_id}"
            stream_path = f"live/{group_name}/{individual_stream_id}"
            stream_url = f"srt://{srt_config['ip']}:{srt_config['port']}?streamid=#!::r={stream_path},m=publish&{srt_params}"
            ffmpeg_cmd.extend(["-map", f"[screen{i}]"] + encoding_params + [stream_url])
        
        return ffmpeg_cmd
    
    def _add_multi_video_outputs(self, ffmpeg_cmd: List[str], group: Dict,
                                srt_config: Dict, video_count: int,
                                framerate: int, bitrate: str, sei: str) -> List[str]:
        """Add outputs for multi-video streaming"""
        # Encoding parameters
        encoding_params = self._build_encoding_params(framerate, bitrate, sei)
        
        # SRT parameters
        srt_params = self._build_srt_params()
        
        # Group info
        group_name = group.get("name", "unknown")
        base_stream_id = self._generate_stream_id()
        
        # Combined stream output
        combined_stream_path = f"live/{group_name}/multi_{base_stream_id}"
        combined_url = f"srt://{srt_config['ip']}:{srt_config['port']}?streamid=#!::r={combined_stream_path},m=publish&{srt_params}"
        ffmpeg_cmd.extend(["-map", "[combined]"] + encoding_params + [combined_url])
        
        return ffmpeg_cmd
    
    def _build_encoding_params(self, framerate: int, bitrate: str, sei: str) -> List[str]:
        """Build video encoding parameters"""
        return [
            "-an", "-c:v", "libx264",
            "-preset", "veryfast", "-tune", "zerolatency",
            "-maxrate", bitrate,
            "-bufsize", str(int(bitrate.rstrip('k')) * 2) + "k",
            "-bsf:v", f"h264_metadata=sei_user_data={sei}",
            "-pes_payload_size", "0",
            "-bf", "0", "-g", "1",
            "-r", str(framerate),
            "-f", "mpegts"
        ]
    
    def _build_srt_params(self) -> str:
        """Build SRT connection parameters"""
        return "latency=5000000&connect_timeout=5000&rcvbuf=67108864&sndbuf=67108864"
    
    def _generate_sei(self) -> str:
        """Generate SEI metadata"""
        return f"{uuid.uuid4().hex}+000000"
    
    def _generate_stream_id(self) -> str:
        """Generate unique stream ID"""
        return uuid.uuid4().hex[:8]
