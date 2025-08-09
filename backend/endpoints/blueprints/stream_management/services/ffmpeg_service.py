# backend/endpoints/blueprints/stream_management/services/ffmpeg_service.py
import os
import subprocess
import threading
import time
import logging
from typing import List, Dict, Any, Tuple
from ..models.stream_config import StreamConfig, Orientation
from ..utils.ffmpeg_utils import find_ffmpeg_executable

logger = logging.getLogger(__name__)

class FFmpegService:
    """FFmpeg service with OpenVideoWalls dynamic timestamp support"""
    
    @staticmethod
    def build_multi_video_command_with_dynamic_timestamps(
        config: StreamConfig, persistent_streams: Dict[str, str]
    ) -> List[str]:
        """
        Build FFmpeg command for multi-video streaming with dynamic timestamps
        
        Implements OpenVideoWalls paper approach:
        - Server embeds Unix timestamps in SEI metadata
        - Timestamps calculated as: current_time + offset + frame_time
        - Each frame gets unique timestamp for synchronization
        """
        if not config.video_files:
            raise ValueError("Multi-video mode requires video files")
        
        ffmpeg_path = find_ffmpeg_executable()
        
        # Build input args
        input_args = []
        for video_config in config.video_files:
            input_args.extend(["-stream_loop", "-1", "-re", "-i", video_config.file_path])
        
        # Calculate dimensions
        canvas_width, canvas_height = config.canvas_dimensions
        section_width = config.output_width
        section_height = config.output_height
        
        # Build filter complex
        filter_parts = []
        filter_parts.append(f"color=c=black:s={canvas_width}x{canvas_height}:r={config.framerate}[canvas]")
        
        # Scale each input
        for i in range(config.screen_count):
            filter_parts.append(f"[{i}:v]scale={section_width}:{section_height}[scaled{i}]")
        
        # Overlay videos onto canvas
        current_stream = "[canvas]"
        for i in range(config.screen_count):
            x_pos, y_pos = FFmpegService._calculate_position(i, config)
            next_stream = f"[overlay{i}]" if i < config.screen_count - 1 else "[combined]"
            filter_parts.append(f"{current_stream}[scaled{i}]overlay=x={x_pos}:y={y_pos}{next_stream}")
            current_stream = f"[overlay{i}]"
        
        # Split for individual crops
        filter_parts.append(f"[combined]split={config.screen_count + 1}[full]" + "".join(f"[copy{i}]" for i in range(config.screen_count)))
        
        # Create crop filters
        for i in range(config.screen_count):
            x_pos, y_pos = FFmpegService._calculate_position(i, config)
            filter_parts.append(f"[copy{i}]crop={section_width}:{section_height}:{x_pos}:{y_pos}[screen{i}]")
        
        complete_filter = ";".join(filter_parts)
        
        # Build FFmpeg command
        ffmpeg_cmd = [
            ffmpeg_path,
            "-y",
            "-v", "error",
            "-stats"
        ]
        
        ffmpeg_cmd.extend(input_args + ["-filter_complex", complete_filter])
        
        # Dynamic timestamp implementation (OpenVideoWalls approach)
        current_unix_time = int(time.time())
        buffer_offset = 2  # 2 second buffer (as recommended in paper)
        
        logger.info(f"Dynamic timestamp configuration:")
        logger.info(f"  Current Unix time: {current_unix_time}")
        logger.info(f"  Buffer offset: {buffer_offset}s")
        logger.info(f"  First frame timestamp: {current_unix_time + buffer_offset}")
        
        # Add outputs with dynamic timestamps
        FFmpegService._add_stream_outputs_with_dynamic_timestamps(
            ffmpeg_cmd, config, persistent_streams, "combined", current_unix_time, buffer_offset
        )
        
        return ffmpeg_cmd
    
    @staticmethod
    def build_split_screen_command_with_dynamic_timestamps(
        config: StreamConfig, persistent_streams: Dict[str, str]
    ) -> List[str]:
        """Build FFmpeg command for split-screen with dynamic timestamps"""
        if not config.single_video_file:
            raise ValueError("Split-screen mode requires a single video file")
        
        ffmpeg_path = find_ffmpeg_executable()
        
        # Build input
        input_args = ["-stream_loop", "-1", "-re", "-i", config.single_video_file]
        
        # Calculate dimensions
        canvas_width, canvas_height = config.canvas_dimensions
        section_width = config.output_width
        section_height = config.output_height
        
        # Build filter complex
        filter_parts = []
        
        # Scale input to canvas size
        filter_parts.append(f"[0:v]fps={config.framerate},scale={canvas_width}:{canvas_height}:force_original_aspect_ratio=increase,crop={canvas_width}:{canvas_height}[scaled]")
        
        # Split for full output and crops
        filter_parts.append(f"[scaled]split={config.screen_count + 1}[full]" + "".join(f"[copy{i}]" for i in range(config.screen_count)))
        
        # Create crop filters
        for i in range(config.screen_count):
            x_pos, y_pos = FFmpegService._calculate_position(i, config)
            filter_parts.append(f"[copy{i}]crop={section_width}:{section_height}:{x_pos}:{y_pos}[screen{i}]")
        
        complete_filter = ";".join(filter_parts)
        
        # Build FFmpeg command
        ffmpeg_cmd = [
            ffmpeg_path,
            "-y",
            "-v", "error",
            "-stats"
        ]
        
        ffmpeg_cmd.extend(input_args + ["-filter_complex", complete_filter])
        
        # Dynamic timestamps for split-screen
        current_unix_time = int(time.time())
        buffer_offset = 2
        
        # Add outputs with dynamic timestamps
        FFmpegService._add_stream_outputs_with_dynamic_timestamps(
            ffmpeg_cmd, config, persistent_streams, "split", current_unix_time, buffer_offset
        )
        
        return ffmpeg_cmd
    
    @staticmethod
    def _add_stream_outputs_with_dynamic_timestamps(
        ffmpeg_cmd: List[str], 
        config: StreamConfig, 
        persistent_streams: Dict[str, str], 
        stream_prefix: str,
        current_unix_time: int,
        buffer_offset: int
    ):
        """
        Add stream outputs with dynamic timestamp embedding
        
        This implements the OpenVideoWalls timestamp approach:
        - Each frame gets: UUID + hex(unix_timestamp_ms)
        - Timestamp = current_time + offset + frame_time
        """
        
        # Calculate dynamic timestamp expression for FFmpeg
        # This creates a unique timestamp for each frame
        timestamp_expr = f"({current_unix_time}+{buffer_offset}+pts_time)*1000"
        
        # Convert to 16-character hex string (as expected by OpenVideoWalls clients)
        sei_timestamp_expr = f"sprintf(\\%016llx\\,{timestamp_expr})"
        
        # SEI compatibility check and solution
        from ..utils.ffmpeg_compatibility import build_sei_parameters_compatible, test_sei_capability
        
        # Test SEI capability first
        if not test_sei_capability():
            raise ValueError("FFmpeg does not support required SEI metadata features")
        
        # Get compatible SEI parameters
        sei_params = build_sei_parameters_compatible(config, current_unix_time, buffer_offset)
        
        # Common encoding parameters with compatible SEI
        encoding_params = [
            "-an",  # No audio
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-tune", "zerolatency",
            "-maxrate", config.bitrate,
            "-bufsize", str(int(config.bitrate.rstrip('k')) * 2) + "k",
            # Use compatible SEI method
            *sei_params,
            "-pes_payload_size", "0",
            "-bf", "0",
            "-g", "1",  # I-frames only (as per OpenVideoWalls paper)
            "-r", str(config.framerate),
            "-f", "mpegts"
        ]
        # SRT parameters
        srt_params = "latency=5000000&connect_timeout=5000&rcvbuf=67108864&sndbuf=67108864"
        
        # Add combined stream output
        combined_stream_path = f"live/{config.group_id}/{stream_prefix}_{config.group_id}"
        combined_url = f"srt://{config.srt_ip}:{config.srt_port}?streamid=#!::r={combined_stream_path},m=publish&{srt_params}"
        ffmpeg_cmd.extend(["-map", "[full]"] + encoding_params + [combined_url])
        
        # Add individual screen outputs
        for i in range(config.screen_count):
            screen_key = f"test{i}"
            individual_stream_id = persistent_streams.get(screen_key, f"screen{i}_{config.group_id}")
            stream_path = f"live/{config.group_id}/{individual_stream_id}"
            stream_url = f"srt://{config.srt_ip}:{config.srt_port}?streamid=#!::r={stream_path},m=publish&{srt_params}"
            
            ffmpeg_cmd.extend(["-map", f"[screen{i}]"] + encoding_params + [stream_url])
    
    @staticmethod
    def _calculate_position(screen_index: int, config: StreamConfig) -> Tuple[int, int]:
        """Calculate x,y position for a screen based on orientation"""
        if config.orientation == Orientation.HORIZONTAL:
            return screen_index * config.output_width, 0
        elif config.orientation == Orientation.VERTICAL:
            return 0, screen_index * config.output_height
        elif config.orientation == Orientation.GRID:
            cols = config.grid_cols
            rows = config.grid_rows
            if rows * cols != config.screen_count:
                cols = int(config.screen_count ** 0.5)
                rows = (config.screen_count + cols - 1) // cols
            
            row = screen_index // cols
            col = screen_index % cols
            return col * config.output_width, row * config.output_height
        
        raise ValueError(f"Unknown orientation: {config.orientation}")
    
    # Backward compatibility methods
    @staticmethod
    def build_multi_video_command(config: StreamConfig, persistent_streams: Dict[str, str]) -> List[str]:
        """Legacy method - now uses dynamic timestamps"""
        return FFmpegService.build_multi_video_command_with_dynamic_timestamps(config, persistent_streams)
    
    @staticmethod
    def build_split_screen_command(config: StreamConfig, persistent_streams: Dict[str, str]) -> List[str]:
        """Legacy method - now uses dynamic timestamps"""
        return FFmpegService.build_split_screen_command_with_dynamic_timestamps(config, persistent_streams)
    
    @staticmethod
    def monitor_process(process: subprocess.Popen, stream_type: str = "FFmpeg", 
                       startup_timeout: int = 5, startup_max_lines: int = 20) -> Tuple[bool, bool]:
        """Monitor FFmpeg process startup and continuous operation"""
        streaming_detected = False
        startup_success = True
        startup_complete = False
        
        def monitor_startup_phase():
            nonlocal streaming_detected, startup_success, startup_complete
            start_time = time.time()
            lines_shown = 0
            
            output_stream = process.stdout if process.stderr is None else process.stderr
            if output_stream is None:
                startup_success = False
                startup_complete = True
                return
            
            while (time.time() - start_time < startup_timeout and 
                   lines_shown < startup_max_lines and
                   not startup_complete):
                
                if process.poll() is not None:
                    logger.error(f"{stream_type} process ended early with code: {process.returncode}")
                    startup_success = False
                    startup_complete = True
                    break
                    
                line = output_stream.readline()
                if line:
                    line_stripped = line.strip()
                    
                    # Skip verbose startup info
                    if any(skip in line_stripped.lower() for skip in [
                        'ffmpeg version', 'built with gcc', 'configuration:',
                        'libavutil', 'libavcodec', 'libavformat', 'libavdevice',
                        'libavfilter', 'libswscale', 'libswresample', 'libpostproc'
                    ]):
                        continue
                        
                    if line_stripped:
                        logger.debug(f"{stream_type}: {line_stripped}")
                        lines_shown += 1
                        
                        # Success indicators
                        if any(indicator in line_stripped.lower() for indicator in [
                            'frame=', 'fps=', 'speed=', 'time=', 'bitrate='
                        ]):
                            streaming_detected = True
                            
                        # Error indicators
                        if any(error in line_stripped.lower() for error in [
                            'error', 'failed', 'connection refused', 'cannot'
                        ]):
                            logger.error(f"{stream_type} error: {line_stripped}")
                            startup_success = False
                            
                time.sleep(0.1)
            
            startup_complete = True

        def monitor_continuous_phase():
            nonlocal startup_complete
            
            while not startup_complete and process.poll() is None:
                time.sleep(0.1)
            
            if process.poll() is not None:
                return
            
            output_stream = process.stdout if process.stderr is None else process.stderr
            if output_stream is None:
                return
            
            frame_count = 0
            last_stats_time = time.time()
            stats_interval = 30
            
            while process.poll() is None:
                line = output_stream.readline()
                if line:
                    line_stripped = line.strip()
                    
                    if line_stripped:
                        if 'frame=' in line_stripped:
                            frame_count += 1
                        
                        current_time = time.time()
                        
                        # Log errors immediately
                        if any(keyword in line_stripped.lower() for keyword in [
                            'error', 'failed', 'warning', 'connection refused', 'timeout'
                        ]):
                            logger.error(f"{stream_type}: {line_stripped}")
                        
                        # Log stats periodically
                        elif (any(keyword in line_stripped.lower() for keyword in [
                            'frame=', 'fps=', 'bitrate=', 'speed='
                        ]) and current_time - last_stats_time >= stats_interval):
                            logger.info(f"{stream_type}: {line_stripped}")
                            last_stats_time = current_time
                
                time.sleep(0.01)
            
            exit_code = process.returncode
            if exit_code != 0:
                logger.error(f"{stream_type} ended with exit code: {exit_code} (processed ~{frame_count} frames)")

        # Start monitoring threads
        startup_thread = threading.Thread(target=monitor_startup_phase, daemon=True)
        continuous_thread = threading.Thread(target=monitor_continuous_phase, daemon=True)
        
        startup_thread.start()
        continuous_thread.start()
        
        startup_thread.join(startup_timeout + 5)
        
        return startup_success, streaming_detected