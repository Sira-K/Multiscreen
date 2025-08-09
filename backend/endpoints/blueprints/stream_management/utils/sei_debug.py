# backend/endpoints/blueprints/stream_management/utils/sei_debug.py
"""
SEI Debug Utility for OpenVideoWalls Timestamp Verification
This utility helps debug and verify SEI metadata generation
"""

import time
import subprocess
import threading
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class SEIDebugger:
    """Debug utility to monitor and verify SEI metadata"""
    
    def __init__(self, uuid: str, buffer_offset: float = 2.0):
        self.uuid = uuid
        self.buffer_offset = buffer_offset
        self.start_time = time.time()
        self.frame_count = 0
        self.sei_samples = []
        self._lock = threading.Lock()
        
    def log_sei_configuration(self):
        """Log detailed SEI configuration information"""
        current_time = time.time()
        
        logger.info("="*60)
        logger.info(" SEI METADATA CONFIGURATION (OpenVideoWalls)")
        logger.info("="*60)
        logger.info(f" UUID: {self.uuid}")
        logger.info(f" Current Unix timestamp: {int(current_time)}")
        logger.info(f" Buffer offset: {self.buffer_offset}s")
        logger.info(f" First frame time: {int(current_time + self.buffer_offset)}")
        logger.info(f" Timestamp format: Unix milliseconds as 16-char hex")
        logger.info("")
        
        # Show example SEI values for first few frames (30 FPS)
        logger.info(" Example SEI values (first 5 frames at 30 FPS):")
        for i in range(5):
            frame_time = current_time + self.buffer_offset + (i / 30.0)
            timestamp_ms = int(frame_time * 1000)
            hex_timestamp = f"{timestamp_ms:016x}"
            sei_value = f"{self.uuid}+{hex_timestamp}"
            logger.info(f"   Frame {i}: {sei_value}")
        
        logger.info("")
        logger.info(" FFmpeg expression will generate these dynamically")
        logger.info("="*60)
    
    def calculate_expected_sei(self, frame_number: int, framerate: float = 30.0) -> str:
        """Calculate expected SEI value for a given frame"""
        frame_time = self.start_time + self.buffer_offset + (frame_number / framerate)
        timestamp_ms = int(frame_time * 1000)
        hex_timestamp = f"{timestamp_ms:016x}"
        return f"{self.uuid}+{hex_timestamp}"
    
    def validate_sei_format(self, sei_value: str) -> Dict[str, any]:
        """Validate SEI format and extract information"""
        validation_result = {
            "valid": False,
            "uuid_match": False,
            "timestamp_hex": None,
            "timestamp_unix": None,
            "frame_time": None,
            "format_correct": False
        }
        
        try:
            if '+' not in sei_value:
                validation_result["error"] = "Missing '+' separator"
                return validation_result
            
            uuid_part, timestamp_part = sei_value.split('+', 1)
            
            # Check UUID
            validation_result["uuid_match"] = (uuid_part == self.uuid)
            
            # Check timestamp format (should be 16-char hex)
            validation_result["format_correct"] = (len(timestamp_part) == 16 and 
                                                 all(c in '0123456789abcdef' for c in timestamp_part.lower()))
            
            if validation_result["format_correct"]:
                # Convert hex to Unix timestamp
                timestamp_ms = int(timestamp_part, 16)
                timestamp_unix = timestamp_ms / 1000.0
                
                validation_result["timestamp_hex"] = timestamp_part
                validation_result["timestamp_unix"] = timestamp_unix
                validation_result["frame_time"] = timestamp_unix - self.start_time - self.buffer_offset
                validation_result["valid"] = validation_result["uuid_match"]
            
        except Exception as e:
            validation_result["error"] = str(e)
        
        return validation_result
    
    def log_sei_sample(self, sei_value: str, frame_number: Optional[int] = None):
        """Log a sample SEI value with validation"""
        with self._lock:
            self.frame_count += 1
            current_frame = frame_number if frame_number is not None else self.frame_count
            
            validation = self.validate_sei_format(sei_value)
            expected_sei = self.calculate_expected_sei(current_frame)
            
            logger.info(f" SEI Sample - Frame {current_frame}:")
            logger.info(f"   Actual:   {sei_value}")
            logger.info(f"   Expected: {expected_sei}")
            logger.info(f"   Valid:    {validation['valid']}")
            
            if validation["valid"]:
                logger.info(f"   Unix time: {validation['timestamp_unix']:.3f}")
                logger.info(f"   Frame time: {validation['frame_time']:.3f}s")
            else:
                logger.warning(f"   Issues: {validation}")
            
            # Store sample for analysis
            self.sei_samples.append({
                "frame": current_frame,
                "sei": sei_value,
                "validation": validation,
                "timestamp": time.time()
            })
    
    def create_ffmpeg_debug_command(self, input_file: str, output_url: str, sei_metadata: str) -> List[str]:
        """Create FFmpeg command with SEI debugging enabled"""
        from ..utils.ffmpeg_utils import find_ffmpeg_executable
        
        ffmpeg_path = find_ffmpeg_executable()
        
        return [
            ffmpeg_path,
            "-v", "info",  # More verbose for debugging
            "-re", "-i", input_file,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-tune", "zerolatency",
            "-g", "1",  # I-frames only
            "-bsf:v", f"h264_metadata=sei_user_data={sei_metadata}",
            "-f", "mpegts",
            output_url
        ]
    
    def monitor_ffmpeg_sei_output(self, process: subprocess.Popen):
        """Monitor FFmpeg output for SEI-related information"""
        def monitor_thread():
            frame_number = 0
            
            while process.poll() is None:
                line = process.stderr.readline() if process.stderr else ""
                if line:
                    line_stripped = line.strip()
                    
                    # Look for frame information
                    if 'frame=' in line_stripped:
                        frame_number += 1
                        if frame_number <= 10 or frame_number % 30 == 0:  # Log first 10 frames, then every second
                            expected_sei = self.calculate_expected_sei(frame_number)
                            logger.debug(f"Frame {frame_number} - Expected SEI: {expected_sei}")
                    
                    # Log any SEI-related messages
                    if 'sei' in line_stripped.lower() or 'metadata' in line_stripped.lower():
                        logger.info(f"FFmpeg SEI: {line_stripped}")
        
        monitor_thread = threading.Thread(target=monitor_thread, daemon=True)
        monitor_thread.start()
        return monitor_thread
    
    def generate_summary_report(self) -> Dict[str, any]:
        """Generate a summary report of SEI analysis"""
        if not self.sei_samples:
            return {"error": "No SEI samples collected"}
        
        valid_samples = [s for s in self.sei_samples if s["validation"]["valid"]]
        
        report = {
            "total_samples": len(self.sei_samples),
            "valid_samples": len(valid_samples),
            "validity_rate": len(valid_samples) / len(self.sei_samples) * 100,
            "uuid": self.uuid,
            "buffer_offset": self.buffer_offset,
            "start_time": self.start_time
        }
        
        if valid_samples:
            timestamps = [s["validation"]["timestamp_unix"] for s in valid_samples]
            report["timestamp_range"] = {
                "min": min(timestamps),
                "max": max(timestamps),
                "span_seconds": max(timestamps) - min(timestamps)
            }
            
            # Check timestamp progression
            if len(valid_samples) > 1:
                intervals = []
                for i in range(1, len(valid_samples)):
                    interval = valid_samples[i]["validation"]["timestamp_unix"] - valid_samples[i-1]["validation"]["timestamp_unix"]
                    intervals.append(interval)
                
                report["timestamp_intervals"] = {
                    "average": sum(intervals) / len(intervals),
                    "min": min(intervals),
                    "max": max(intervals),
                    "expected_30fps": 1/30.0
                }
        
        return report

# Usage example in stream management
def debug_sei_metadata(uuid: str, buffer_offset: float = 2.0):
    """Helper function to debug SEI metadata configuration"""
    debugger = SEIDebugger(uuid, buffer_offset)
    debugger.log_sei_configuration()
    return debugger

# Integration with existing FFmpeg service
def log_ffmpeg_sei_debug(config, current_unix_time: int, buffer_offset: int):
    """Log detailed SEI debugging information for FFmpeg command"""
    logger.info("="*70)
    logger.info(" FFMPEG SEI METADATA DEBUG")
    logger.info("="*70)
    
    # Show the actual FFmpeg expression
    timestamp_expr = f"({current_unix_time}+{buffer_offset}+pts_time)*1000"
    sei_timestamp_expr = f"sprintf(\\%016llx\\,{timestamp_expr})"
    sei_metadata = f"{config.sei}+{sei_timestamp_expr}"
    
    logger.info(f" SEI Configuration:")
    logger.info(f"   UUID: {config.sei}")
    logger.info(f"   Timestamp expression: {timestamp_expr}")
    logger.info(f"   Printf expression: {sei_timestamp_expr}")
    logger.info(f"   Full SEI metadata: {sei_metadata}")
    
    # Calculate and show expected values for verification
    logger.info(f" Expected SEI Values:")
    for frame in [0, 1, 30, 60]:  # Frames 0, 1, 1 second, 2 seconds
        frame_time_offset = frame / 30.0  # Assuming 30 FPS
        expected_timestamp = (current_unix_time + buffer_offset + frame_time_offset) * 1000
        expected_hex = f"{int(expected_timestamp):016x}"
        expected_sei = f"{config.sei}+{expected_hex}"
        logger.info(f"   Frame {frame:2d}: {expected_sei}")
    
    logger.info("")
    logger.info(" Client should receive frames with these SEI values")
    logger.info(" Timestamps will increment by ~33ms per frame (30 FPS)")
    logger.info("="*70)