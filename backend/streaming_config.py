"""
Streaming Configuration for Multi-Screen Video System
Optimizes FFmpeg parameters to prevent memory crashes
"""

# Memory optimization settings
MEMORY_OPTIMIZATION = {
    # Input queue limits
    "thread_queue_size": 512,
    "max_muxing_queue_size": 1024,
    
    # Output queue limits
    "output_queue_size": 512,
    
    # Frame buffering
    "max_frames": 100,  # Maximum frames to buffer
    
    # Memory thresholds (in MB)
    "warning_threshold": 2000,  # Warning at 2GB
    "critical_threshold": 4000,  # Critical at 4GB
    "max_allowed": 6000,  # Maximum allowed 6GB
    
    # Auto-restart settings
    "auto_restart": True,
    "restart_delay": 5,  # Seconds to wait before restart
    "max_restarts": 3,  # Maximum restart attempts
}

# FFmpeg encoding presets for different memory constraints
ENCODING_PRESETS = {
    "low_memory": {
        "preset": "ultrafast",
        "tune": "zerolatency",
        "g": "15",  # Keyframe every 15 frames
        "bf": "0",  # No B-frames
        "refs": "1",  # Single reference frame
        "sc_threshold": "0",  # Disable scene change detection
    },
    "balanced": {
        "preset": "veryfast",
        "tune": "zerolatency",
        "g": "30",  # Keyframe every 30 frames
        "bf": "0",  # No B-frames
        "refs": "2",  # Two reference frames
        "sc_threshold": "40",  # Moderate scene change detection
    },
    "high_quality": {
        "preset": "faster",
        "tune": "zerolatency",
        "g": "60",  # Keyframe every 60 frames
        "bf": "1",  # One B-frame
        "refs": "3",  # Three reference frames
        "sc_threshold": "80",  # High scene change detection
    }
}

# Stream quality settings based on available memory
def get_encoding_preset(available_memory_gb: float) -> dict:
    """Get encoding preset based on available system memory"""
    if available_memory_gb < 4:
        return ENCODING_PRESETS["low_memory"]
    elif available_memory_gb < 8:
        return ENCODING_PRESETS["balanced"]
    else:
        return ENCODING_PRESETS["high_quality"]

# Memory monitoring functions
def check_memory_usage():
    """Check current system memory usage"""
    try:
        import psutil
        memory = psutil.virtual_memory()
        return {
            "total_gb": memory.total / (1024**3),
            "available_gb": memory.available / (1024**3),
            "used_gb": memory.used / (1024**3),
            "percent": memory.percent
        }
    except ImportError:
        return None

def should_restart_stream(memory_mb: float) -> bool:
    """Determine if stream should be restarted due to memory usage"""
    if memory_mb > MEMORY_OPTIMIZATION["critical_threshold"]:
        return True
    return False

def get_optimized_ffmpeg_flags(memory_constraint: str = "balanced") -> list:
    """Get optimized FFmpeg flags for memory usage"""
    preset = ENCODING_PRESETS.get(memory_constraint, ENCODING_PRESETS["balanced"])
    
    flags = [
        "-thread_queue_size", str(MEMORY_OPTIMIZATION["thread_queue_size"]),
        "-max_muxing_queue_size", str(MEMORY_OPTIMIZATION["max_muxing_queue_size"]),
        "-fflags", "+genpts+discardcorrupt",
        "-avoid_negative_ts", "make_zero",
        "-preset", preset["preset"],
        "-tune", preset["tune"],
        "-g", preset["g"],
        "-bf", preset["bf"],
        "-refs", preset["refs"],
        "-sc_threshold", preset["sc_threshold"],
    ]
    
    return flags

# Stream configuration validation
def validate_stream_config(video_files: list, screen_count: int, output_resolution: str) -> dict:
    """Validate stream configuration and suggest optimizations"""
    total_input_size = len(video_files)
    
    # Calculate estimated memory usage
    estimated_memory_mb = total_input_size * 100  # ~100MB per input file
    estimated_memory_mb += screen_count * 200     # ~200MB per output stream
    
    # Check if configuration is within limits
    is_safe = estimated_memory_mb < MEMORY_OPTIMIZATION["max_allowed"]
    
    suggestions = []
    if not is_safe:
        if total_input_size > 3:
            suggestions.append("Reduce number of input videos")
        if screen_count > 4:
            suggestions.append("Reduce number of output screens")
        suggestions.append("Use 'low_memory' encoding preset")
    
    return {
        "estimated_memory_mb": estimated_memory_mb,
        "is_safe": is_safe,
        "suggestions": suggestions,
        "recommended_preset": "low_memory" if not is_safe else "balanced"
    }

if __name__ == "__main__":
    # Test the configuration
    print("Streaming Configuration Test")
    print("=" * 50)
    
    # Test memory check
    memory_info = check_memory_usage()
    if memory_info:
        print(f"System Memory: {memory_info['total_gb']:.1f}GB total, {memory_info['available_gb']:.1f}GB available")
    
    # Test encoding presets
    print(f"Encoding Presets: {list(ENCODING_PRESETS.keys())}")
    
    # Test stream validation
    test_config = validate_stream_config(["video1.mp4", "video2.mp4", "video3.mp4"], 3, "1920x1080")
    print(f"Test Config: {test_config['estimated_memory_mb']}MB, Safe: {test_config['is_safe']}")
    
    print("Configuration test completed")
