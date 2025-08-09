# Stream Management Error Codes (1xx)
# Multi-Screen SRT Streaming System - Stream Management Module

class StreamError:
    """Base class for stream management errors"""
    
    # FFmpeg Process Errors (100-119)
    FFMPEG_START_FAILURE = 100
    FFMPEG_PROCESS_DIED = 101
    FFMPEG_TIMEOUT = 102
    FFMPEG_COMMAND_INVALID = 103
    FFMPEG_INPUT_NOT_FOUND = 104
    FFMPEG_OUTPUT_ERROR = 105
    FFMPEG_ENCODING_ERROR = 106
    FFMPEG_CONSECUTIVE_ERRORS = 107
    FFMPEG_CRITICAL_ERROR = 108
    FFMPEG_RESOURCE_EXHAUSTED = 109
    
    # SRT Connection Errors (120-139)
    SRT_CONNECTION_REFUSED = 120
    SRT_CONNECTION_TIMEOUT = 121
    SRT_CONNECTION_RESET = 122
    SRT_BROKEN_PIPE = 123
    SRT_NO_ROUTE_TO_HOST = 124
    SRT_ADDRESS_IN_USE = 125
    SRT_SOCKET_ERROR = 126
    SRT_HANDSHAKE_FAILURE = 127
    SRT_AUTHENTICATION_ERROR = 128
    SRT_STREAM_NOT_FOUND = 129
    
    # Stream Configuration Errors (140-159)
    STREAM_MISSING_PARAMETERS = 140
    STREAM_INVALID_GROUP_ID = 141
    STREAM_INVALID_VIDEO_FILES = 142
    STREAM_GROUP_NOT_FOUND = 143
    STREAM_GROUP_NOT_RUNNING = 144
    STREAM_ALREADY_EXISTS = 145
    STREAM_CONFIG_MISMATCH = 146
    STREAM_LAYOUT_ERROR = 147
    STREAM_RESOLUTION_ERROR = 148
    STREAM_CODEC_ERROR = 149
    
    # Stream Monitoring Errors (160-179)
    STREAM_STARTUP_TIMEOUT = 160
    STREAM_HEALTH_CHECK_FAILED = 161
    STREAM_PERFORMANCE_DEGRADED = 162
    STREAM_BITRATE_TOO_LOW = 163
    STREAM_FRAME_DROPS = 164
    STREAM_SYNC_LOST = 165
    STREAM_BUFFER_OVERFLOW = 166
    STREAM_BUFFER_UNDERRUN = 167
    STREAM_QUALITY_DEGRADED = 168
    STREAM_NETWORK_CONGESTION = 169
    
    # Video Processing Errors (180-199)
    VIDEO_FILE_NOT_FOUND = 180
    VIDEO_FILE_CORRUPT = 181
    VIDEO_FORMAT_UNSUPPORTED = 182
    VIDEO_CODEC_UNSUPPORTED = 183
    VIDEO_RESOLUTION_INVALID = 184
    VIDEO_DURATION_INVALID = 185
    VIDEO_PERMISSIONS_ERROR = 186
    VIDEO_DISK_SPACE_ERROR = 187
    VIDEO_PROCESSING_ERROR = 188
    VIDEO_METADATA_ERROR = 189


# Error Messages and Descriptions
STREAM_ERROR_MESSAGES = {
    # FFmpeg Process Errors (100-119)
    100: {
        "message": "FFmpeg process failed to start",
        "description": "The FFmpeg process could not be launched",
        "common_causes": [
            "FFmpeg binary not found in system PATH",
            "Insufficient system permissions",
            "Invalid command line arguments",
            "System resource constraints"
        ],
        "solutions": [
            "Verify FFmpeg is installed: 'ffmpeg -version'",
            "Check system PATH includes FFmpeg binary location",
            "Ensure sufficient RAM and CPU resources",
            "Validate FFmpeg command parameters",
            "Check system logs for permission errors"
        ]
    },
    
    101: {
        "message": "FFmpeg process terminated unexpectedly",
        "description": "The running FFmpeg process crashed or was killed",
        "common_causes": [
            "Out of memory (OOM) condition",
            "System killed process due to resource limits",
            "Hardware failure or instability",
            "Invalid input file or corruption"
        ],
        "solutions": [
            "Check system memory usage and increase if needed",
            "Monitor system logs for OOM killer messages",
            "Validate input video files are not corrupted",
            "Reduce encoding complexity or resolution",
            "Check hardware stability and cooling"
        ]
    },
    
    102: {
        "message": "FFmpeg startup timeout exceeded",
        "description": "FFmpeg took too long to initialize and start streaming",
        "common_causes": [
            "Network connectivity issues to SRT server",
            "High system load causing delays",
            "Large input files requiring extensive processing",
            "SRT server overloaded or unresponsive"
        ],
        "solutions": [
            "Check network connection to SRT server",
            "Reduce system load and free up resources",
            "Use smaller test files for initial validation",
            "Increase startup timeout in configuration",
            "Verify SRT server is running and accessible"
        ]
    },
    
    103: {
        "message": "Invalid FFmpeg command parameters",
        "description": "The generated FFmpeg command contains invalid arguments",
        "common_causes": [
            "Incorrect video file paths or names",
            "Invalid resolution or codec parameters",
            "Malformed SRT URLs or connection strings",
            "Incompatible FFmpeg version"
        ],
        "solutions": [
            "Validate all file paths exist and are accessible",
            "Check video resolution and codec compatibility",
            "Verify SRT connection strings are properly formatted",
            "Update FFmpeg to compatible version",
            "Test command manually in terminal"
        ]
    },
    
    104: {
        "message": "Input video file not found",
        "description": "FFmpeg cannot locate the specified input video file",
        "common_causes": [
            "File path is incorrect or file was deleted",
            "Insufficient file system permissions",
            "Network storage disconnected",
            "File name contains special characters"
        ],
        "solutions": [
            "Verify file exists at specified path",
            "Check file permissions and ownership",
            "Ensure network storage is mounted and accessible",
            "Rename files to remove special characters",
            "Use absolute paths instead of relative paths"
        ]
    },
    
    105: {
        "message": "FFmpeg output stream error",
        "description": "Error occurred while writing output stream",
        "common_causes": [
            "Network connection to SRT server lost",
            "SRT server reached connection limit",
            "Disk full on output destination",
            "Output format not supported by destination"
        ],
        "solutions": [
            "Check SRT server connectivity and status",
            "Verify SRT server connection limits",
            "Ensure adequate disk space on output destination",
            "Validate output format compatibility",
            "Monitor network stability and bandwidth"
        ]
    },
    
    106: {
        "message": "Video encoding error in FFmpeg",
        "description": "Error occurred during video encoding process",
        "common_causes": [
            "Hardware encoder unavailable or failed",
            "Unsupported codec or format combination",
            "Insufficient CPU/GPU resources for encoding",
            "Invalid encoding parameters"
        ],
        "solutions": [
            "Switch to software encoding if hardware fails",
            "Reduce encoding complexity or bitrate",
            "Verify codec support on current system",
            "Allocate more CPU/GPU resources",
            "Update graphics drivers for hardware encoding"
        ]
    },
    
    107: {
        "message": "Too many consecutive FFmpeg errors",
        "description": "FFmpeg encountered multiple consecutive errors and was terminated",
        "common_causes": [
            "Persistent network connectivity issues",
            "Corrupted input video files",
            "System instability or hardware issues",
            "Incompatible configuration parameters"
        ],
        "solutions": [
            "Identify and fix root cause of recurring errors",
            "Validate input files are not corrupted",
            "Check system stability and hardware health",
            "Review and correct configuration parameters",
            "Implement exponential backoff for retry logic"
        ]
    },
    
    108: {
        "message": "Critical FFmpeg error detected",
        "description": "FFmpeg encountered a critical error requiring immediate attention",
        "common_causes": [
            "Hardware failure or malfunction",
            "Critical system resource exhaustion",
            "Security or permission violations",
            "Software bugs or incompatibilities"
        ],
        "solutions": [
            "Check hardware status and error logs",
            "Free up critical system resources",
            "Review security policies and permissions",
            "Update software to latest stable versions",
            "Contact system administrator if needed"
        ]
    },
    
    109: {
        "message": "System resources exhausted for FFmpeg",
        "description": "Insufficient system resources to run FFmpeg process",
        "common_causes": [
            "Insufficient RAM for video processing",
            "CPU overload from multiple processes",
            "Disk I/O bottlenecks",
            "Network bandwidth limitations"
        ],
        "solutions": [
            "Add more system RAM or reduce memory usage",
            "Reduce concurrent processes or encoding jobs",
            "Optimize disk I/O with faster storage",
            "Ensure adequate network bandwidth",
            "Use lower resolution or bitrate settings"
        ]
    },

    # SRT Connection Errors (120-139)
    120: {
        "message": "SRT connection refused by server",
        "description": "The SRT server actively refused the connection attempt",
        "common_causes": [
            "SRT server is not running or listening",
            "Firewall blocking connection on SRT port",
            "SRT server reached maximum connection limit",
            "Authentication required but not provided"
        ],
        "solutions": [
            "Verify SRT server is running: 'docker ps'",
            "Check firewall rules for SRT port (usually 10080)",
            "Increase SRT server connection limits",
            "Provide correct authentication credentials",
            "Verify SRT server configuration"
        ]
    },
    
    121: {
        "message": "SRT connection timeout",
        "description": "Connection attempt to SRT server timed out",
        "common_causes": [
            "Network latency too high",
            "SRT server overloaded and slow to respond",
            "Packet loss on network path",
            "Incorrect SRT server IP or port"
        ],
        "solutions": [
            "Check network latency: 'ping <srt-server-ip>'",
            "Reduce SRT server load or scale up resources",
            "Investigate and fix network packet loss",
            "Verify correct SRT server IP and port",
            "Increase connection timeout values"
        ]
    },
    
    122: {
        "message": "SRT connection reset by peer",
        "description": "The SRT connection was reset by the remote server",
        "common_causes": [
            "SRT server restarted or crashed",
            "Network path changed or interrupted",
            "SRT server detected protocol violation",
            "Resource limits exceeded on server"
        ],
        "solutions": [
            "Check SRT server logs for restart/crash reasons",
            "Verify network path stability",
            "Review SRT protocol compliance in client",
            "Monitor SRT server resource usage",
            "Implement automatic reconnection logic"
        ]
    },
    
    123: {
        "message": "SRT broken pipe error",
        "description": "The SRT connection pipe was broken unexpectedly",
        "common_causes": [
            "Remote SRT server terminated connection",
            "Network interface went down",
            "Process killed while writing to socket",
            "System-level socket errors"
        ],
        "solutions": [
            "Check remote SRT server status and logs",
            "Verify network interface is up and stable",
            "Monitor system process management",
            "Check system socket limits and errors",
            "Implement robust error handling and reconnection"
        ]
    },
    
    124: {
        "message": "No route to SRT server host",
        "description": "Network routing cannot reach the SRT server",
        "common_causes": [
            "SRT server IP address unreachable",
            "Network routing configuration issues",
            "VPN or tunnel disconnected",
            "DNS resolution failures"
        ],
        "solutions": [
            "Test network connectivity: 'ping <srt-server-ip>'",
            "Check routing table: 'route -n' or 'ip route'",
            "Verify VPN/tunnel connections are active",
            "Test DNS resolution: 'nslookup <hostname>'",
            "Configure correct network routes"
        ]
    },
    
    125: {
        "message": "SRT port address already in use",
        "description": "The SRT port is already bound by another process",
        "common_causes": [
            "Multiple SRT servers trying to use same port",
            "Previous process didn't release port properly",
            "Port conflict with other applications",
            "Docker container port mapping conflicts"
        ],
        "solutions": [
            "Check port usage: 'netstat -tulpn | grep <port>'",
            "Kill processes using the port if safe",
            "Use different port numbers for multiple servers",
            "Restart Docker containers to clear port bindings",
            "Configure unique port mappings for each service"
        ]
    },
    
    126: {
        "message": "SRT socket error occurred",
        "description": "Generic socket error in SRT connection",
        "common_causes": [
            "System socket limits exceeded",
            "Network interface errors",
            "Socket permission issues",
            "Kernel networking problems"
        ],
        "solutions": [
            "Check system socket limits: 'ulimit -n'",
            "Verify network interface status",
            "Review socket permissions and capabilities",
            "Check kernel networking logs",
            "Restart networking services if needed"
        ]
    },
    
    127: {
        "message": "SRT handshake failure",
        "description": "SRT protocol handshake failed during connection",
        "common_causes": [
            "SRT version mismatch between client/server",
            "Incorrect SRT parameters or configuration",
            "Network interference during handshake",
            "Authentication or encryption issues"
        ],
        "solutions": [
            "Verify SRT version compatibility",
            "Check SRT configuration parameters",
            "Test with minimal SRT configuration",
            "Review authentication settings",
            "Analyze SRT handshake logs for details"
        ]
    },
    
    128: {
        "message": "SRT authentication error",
        "description": "Authentication failed for SRT connection",
        "common_causes": [
            "Incorrect username or password",
            "Authentication not enabled on server",
            "Token or key authentication failure",
            "Authentication method mismatch"
        ],
        "solutions": [
            "Verify authentication credentials are correct",
            "Enable authentication on SRT server if required",
            "Check token/key validity and format",
            "Ensure client and server use same auth method",
            "Review SRT server authentication logs"
        ]
    },
    
    129: {
        "message": "SRT stream not found",
        "description": "The requested SRT stream does not exist on server",
        "common_causes": [
            "Stream ID or name is incorrect",
            "Stream was stopped or not yet started",
            "Permission denied for stream access",
            "Stream server configuration issues"
        ],
        "solutions": [
            "Verify correct stream ID and naming",
            "Check if stream is actively running on server",
            "Review stream access permissions",
            "Validate stream server configuration",
            "List available streams on server"
        ]
    },

    # Stream Configuration Errors (140-159)
    140: {
        "message": "Missing required stream parameters",
        "description": "Essential parameters for stream configuration are missing",
        "common_causes": [
            "API request missing group_id or video_files",
            "Configuration file incomplete",
            "Frontend form validation bypassed",
            "Required environment variables not set"
        ],
        "solutions": [
            "Validate API requests include all required fields",
            "Complete configuration file with missing parameters",
            "Fix frontend validation to catch missing fields",
            "Set required environment variables",
            "Review API documentation for required parameters"
        ]
    },
    
    141: {
        "message": "Invalid group ID provided",
        "description": "The specified group ID is not valid or recognized",
        "common_causes": [
            "Group ID doesn't exist in system",
            "Group was deleted but reference remains",
            "Invalid characters in group ID",
            "Case sensitivity issues in group ID"
        ],
        "solutions": [
            "Verify group exists: use /get_groups endpoint",
            "Create group before referencing it",
            "Use only valid characters in group IDs",
            "Check case sensitivity of group ID matching",
            "Clean up orphaned group references"
        ]
    },
    
    142: {
        "message": "Invalid video files configuration",
        "description": "The video files array is empty, invalid, or malformed",
        "common_causes": [
            "Empty video_files array in request",
            "Video file paths are incorrect",
            "File format not supported",
            "Missing screen assignments for videos"
        ],
        "solutions": [
            "Provide at least one video file in configuration",
            "Verify all video file paths are correct and accessible",
            "Use supported video formats (MP4, AVI, MOV)",
            "Assign each video to appropriate screen number",
            "Validate video files exist before streaming"
        ]
    },
    
    143: {
        "message": "Stream group not found in Docker",
        "description": "The specified group has no corresponding Docker container",
        "common_causes": [
            "Group exists but Docker container not created",
            "Docker container was manually deleted",
            "Group creation process failed partially",
            "Docker service is not running"
        ],
        "solutions": [
            "Create Docker container for the group",
            "Restart group creation process",
            "Check Docker service status: 'systemctl status docker'",
            "Manually create container using group configuration",
            "Verify Docker container naming conventions"
        ]
    },
    
    144: {
        "message": "Stream group Docker container not running",
        "description": "The group's Docker container exists but is not currently running",
        "common_causes": [
            "Container was stopped manually",
            "Container crashed due to configuration error",
            "Insufficient system resources for container",
            "Docker service restart without container restart"
        ],
        "solutions": [
            "Start the container: 'docker start <container_name>'",
            "Check container logs: 'docker logs <container_name>'",
            "Verify system has adequate resources",
            "Fix container configuration if needed",
            "Set container restart policy to 'always'"
        ]
    },
    
    145: {
        "message": "Stream already exists for this group",
        "description": "A stream is already running for the specified group",
        "common_causes": [
            "Multiple stream start requests for same group",
            "Previous stream not properly stopped",
            "Process management race condition",
            "Concurrent API requests"
        ],
        "solutions": [
            "Stop existing stream before starting new one",
            "Check running FFmpeg processes for the group",
            "Implement proper API request serialization",
            "Use process locks to prevent race conditions",
            "Add stream status checking before starting"
        ]
    },
    
    146: {
        "message": "Stream configuration mismatch",
        "description": "Stream configuration doesn't match group requirements",
        "common_causes": [
            "Video count doesn't match group screen count",
            "Resolution mismatch for group layout",
            "Incompatible streaming mode selection",
            "Codec requirements not met"
        ],
        "solutions": [
            "Ensure video count matches group screen count",
            "Verify resolution compatibility with layout",
            "Select appropriate streaming mode for group",
            "Use compatible codecs for streaming",
            "Review group configuration requirements"
        ]
    },
    
    147: {
        "message": "Stream layout configuration error",
        "description": "The layout configuration is invalid or incompatible",
        "common_causes": [
            "Invalid screen arrangement specification",
            "Unsupported orientation for screen count",
            "Grid layout dimensions don't match screen count",
            "Resolution calculations failed"
        ],
        "solutions": [
            "Use supported screen arrangements (horizontal/vertical/grid)",
            "Verify orientation supports the screen count",
            "Ensure grid dimensions multiply to screen count",
            "Check resolution calculation logic",
            "Use standard layout templates"
        ]
    },
    
    148: {
        "message": "Stream resolution error",
        "description": "Video resolution is incompatible with streaming requirements",
        "common_causes": [
            "Input video resolution too low",
            "Aspect ratio mismatch with layout",
            "Resolution not divisible for grid layout",
            "Output resolution exceeds limits"
        ],
        "solutions": [
            "Use higher resolution input videos",
            "Crop or pad videos to match aspect ratio",
            "Ensure resolution is divisible for splitting",
            "Reduce output resolution if too high",
            "Use video preprocessing to fix resolution"
        ]
    },
    
    149: {
        "message": "Stream codec configuration error",
        "description": "Video codec settings are invalid or unsupported",
        "common_causes": [
            "Unsupported codec for SRT streaming",
            "Codec parameters incompatible with hardware",
            "Encoding profile not supported",
            "Codec licensing issues"
        ],
        "solutions": [
            "Use H.264 codec for maximum compatibility",
            "Check hardware codec support",
            "Use compatible encoding profiles (baseline/main)",
            "Verify codec licensing and availability",
            "Test codec settings with simple streams first"
        ]
    },

    # Stream Monitoring Errors (160-179)
    160: {
        "message": "Stream startup timeout exceeded",
        "description": "Stream took too long to start and become ready",
        "common_causes": [
            "Network latency to SRT server too high",
            "System overloaded with other processes",
            "Large video files causing slow initialization",
            "Hardware encoding initialization delays"
        ],
        "solutions": [
            "Increase startup timeout configuration",
            "Reduce system load before starting streams",
            "Use smaller video files for testing",
            "Pre-initialize hardware encoders",
            "Check network path to SRT server"
        ]
    },
    
    161: {
        "message": "Stream health check failed",
        "description": "Stream health monitoring detected failure",
        "common_causes": [
            "Stream stopped producing frames",
            "Network connection to SRT server lost",
            "Encoding quality degraded significantly",
            "Buffer levels critically low or high"
        ],
        "solutions": [
            "Check if stream is still actively encoding",
            "Verify SRT server connectivity",
            "Monitor encoding quality metrics",
            "Adjust buffer size and management",
            "Restart stream if health cannot be restored"
        ]
    },
    
    162: {
        "message": "Stream performance degraded",
        "description": "Stream performance has fallen below acceptable thresholds",
        "common_causes": [
            "System CPU/memory usage too high",
            "Network bandwidth insufficient",
            "Storage I/O bottlenecks",
            "Concurrent streams competing for resources"
        ],
        "solutions": [
            "Reduce system load and free up resources",
            "Increase available network bandwidth",
            "Use faster storage or reduce I/O load",
            "Limit number of concurrent streams",
            "Optimize encoding settings for performance"
        ]
    },
    
    163: {
        "message": "Stream bitrate too low",
        "description": "Stream bitrate has dropped below minimum threshold",
        "common_causes": [
            "Network congestion reducing available bandwidth",
            "Adaptive bitrate algorithm being too aggressive",
            "Source video complexity too high for bitrate",
            "Hardware encoder throttling due to heat"
        ],
        "solutions": [
            "Check network bandwidth and congestion",
            "Adjust adaptive bitrate algorithm parameters",
            "Increase target bitrate for complex content",
            "Monitor hardware temperature and cooling",
            "Use constant bitrate mode if needed"
        ]
    },
    
    164: {
        "message": "Stream experiencing frame drops",
        "description": "Significant frame drops detected in stream",
        "common_causes": [
            "Encoding cannot keep up with source framerate",
            "Network cannot transmit frames fast enough",
            "System running out of processing power",
            "Buffer overflow causing frame discards"
        ],
        "solutions": [
            "Reduce encoding complexity or resolution",
            "Increase network bandwidth or reduce congestion",
            "Allocate more CPU/GPU resources to encoding",
            "Adjust buffer sizes and management strategy",
            "Lower source framerate if acceptable"
        ]
    },
    
    165: {
        "message": "Stream synchronization lost",
        "description": "Audio/video synchronization or multi-stream sync lost",
        "common_causes": [
            "Different processing delays for audio/video",
            "Network jitter affecting stream timing",
            "Clock drift between streaming components",
            "Buffer management inconsistencies"
        ],
        "solutions": [
            "Adjust audio/video synchronization offsets",
            "Implement jitter buffer to smooth network timing",
            "Use network time protocol (NTP) for clock sync",
            "Standardize buffer management across streams",
            "Monitor and correct timing drift regularly"
        ]
    },
    
    166: {
        "message": "Stream buffer overflow",
        "description": "Stream buffers are overflowing, causing data loss",
        "common_causes": [
            "Input rate exceeds processing capacity",
            "Network transmission slower than input rate",
            "Insufficient buffer memory allocation",
            "Blocking operations in stream pipeline"
        ],
        "solutions": [
            "Reduce input rate or increase processing power",
            "Improve network transmission capacity",
            "Increase buffer memory allocation",
            "Remove blocking operations from stream pipeline",
            "Implement proper backpressure handling"
        ]
    },
    
    167: {
        "message": "Stream buffer underrun",
        "description": "Stream buffers are empty, causing interruptions",
        "common_causes": [
            "Input source cannot provide data fast enough",
            "Network interruptions causing data gaps",
            "Processing pipeline stalls or delays",
            "Inadequate pre-buffering"
        ],
        "solutions": [
            "Ensure input source can sustain required data rate",
            "Fix network interruptions and improve stability",
            "Optimize processing pipeline for consistent flow",
            "Increase pre-buffering to handle variations",
            "Implement adaptive buffering strategies"
        ]
    },
    
    168: {
        "message": "Stream quality degraded",
        "description": "Stream quality metrics indicate significant degradation",
        "common_causes": [
            "Compression artifacts increasing",
            "Resolution or bitrate automatically reduced",
            "Color space or format conversion errors",
            "Source quality issues propagating"
        ],
        "solutions": [
            "Increase bitrate allocation for better quality",
            "Check resolution scaling algorithms",
            "Verify color space conversion accuracy",
            "Improve source video quality",
            "Monitor quality metrics and adjust encoding"
        ]
    },
    
    169: {
        "message": "Network congestion affecting stream",
        "description": "Network congestion is impacting stream delivery",
        "common_causes": [
            "Network bandwidth fully utilized",
            "Multiple streams competing for bandwidth",
            "Network equipment overload",
            "ISP or WAN congestion"
        ],
        "solutions": [
            "Implement Quality of Service (QoS) prioritization",
            "Reduce number of concurrent streams",
            "Upgrade network equipment capacity",
            "Use adaptive bitrate to handle congestion",
            "Schedule high-bandwidth operations during off-peak"
        ]
    },

    # Video Processing Errors (180-199)
    180: {
        "message": "Video file not found at specified path",
        "description": "The system cannot locate the video file",
        "common_causes": [
            "Incorrect file path in configuration",
            "Video file was deleted or moved",
            "File system permission issues",
            "Network storage disconnected"
        ],
        "solutions": [
            "Verify file path is correct and absolute",
            "Check if file exists at expected location",
            "Ensure adequate file system permissions",
            "Verify network storage is mounted",
            "Use file existence check before processing"
        ]
    },
    
    181: {
        "message": "Video file is corrupted or unreadable",
        "description": "The video file cannot be processed due to corruption",
        "common_causes": [
            "Incomplete file upload or transfer",
            "Storage device errors or failures",
            "File system corruption",
            "Encoding process interrupted"
        ],
        "solutions": [
            "Re-upload or transfer the video file",
            "Check storage device health and errors",
            "Run file system check and repair",
            "Use file integrity verification tools",
            "Test with known good video files"
        ]
    },
    
    182: {
        "message": "Video format not supported",
        "description": "The video file format is not supported by the system",
        "common_causes": [
            "Unsupported container format (not MP4/AVI/MOV)",
            "Proprietary or rare video format",
            "Missing codec support in FFmpeg",
            "DRM-protected content"
        ],
        "solutions": [
            "Convert video to supported format (MP4 recommended)",
            "Install additional FFmpeg codecs if needed",
            "Use standard video formats for compatibility",
            "Remove DRM protection if legally permitted",
            "Check FFmpeg format support: 'ffmpeg -formats'"
        ]
    },
    
    183: {
        "message": "Video codec not supported",
        "description": "The video codec is not supported for processing",
        "common_causes": [
            "Proprietary or patent-encumbered codec",
            "Old or obsolete codec version",
            "Missing codec library or plugin",
            "Hardware decoder not available"
        ],
        "solutions": [
            "Re-encode video with H.264 or H.265",
            "Install missing codec libraries",
            "Use software decoding instead of hardware",
            "Convert video using compatible codec",
            "Check codec support: 'ffmpeg -codecs'"
        ]
    },
    
    184: {
        "message": "Video resolution invalid or unsupported",
        "description": "The video resolution cannot be processed by the system",
        "common_causes": [
            "Resolution too high for system capabilities",
            "Non-standard or odd resolution values",
            "Resolution not divisible for layout splitting",
            "Aspect ratio incompatible with layout"
        ],
        "solutions": [
            "Reduce video resolution to supported levels",
            "Use standard resolution values (1920x1080, etc.)",
            "Ensure resolution is divisible for grid layouts",
            "Crop or pad video to compatible aspect ratio",
            "Check system hardware limitations"
        ]
    },
    
    185: {
        "message": "Video duration invalid or too short",
        "description": "The video duration is invalid or unsuitable for streaming",
        "common_causes": [
            "Video file too short for meaningful streaming",
            "Duration metadata missing or incorrect",
            "Video file is actually an image",
            "Corrupted video file with invalid duration"
        ],
        "solutions": [
            "Use video files with adequate duration (>1 second)",
            "Repair video metadata using video tools",
            "Verify file is actually a video, not image",
            "Create longer video content for streaming",
            "Loop short videos to extend duration"
        ]
    },
    
    186: {
        "message": "Video file permission denied",
        "description": "Insufficient permissions to access the video file",
        "common_causes": [
            "File owned by different user",
            "Directory permissions prevent access",
            "SELinux or AppArmor blocking access",
            "File system mounted read-only"
        ],
        "solutions": [
            "Change file ownership: 'chown user:group filename'",
            "Adjust file permissions: 'chmod 644 filename'",
            "Check directory permissions for read access",
            "Review SELinux/AppArmor policies",
            "Remount file system with write permissions"
        ]
    },
    
    187: {
        "message": "Insufficient disk space for video processing",
        "description": "Not enough disk space to process or store video",
        "common_causes": [
            "Disk partition full or nearly full",
            "Large video files requiring processing space",
            "Temporary files not cleaned up",
            "Multiple concurrent video operations"
        ],
        "solutions": [
            "Free up disk space by removing old files",
            "Add more storage capacity to system",
            "Clean up temporary and cache files",
            "Use external storage for large video files",
            "Implement automatic cleanup of processed files"
        ]
    },
    
    188: {
        "message": "Video processing operation failed",
        "description": "General video processing error occurred",
        "common_causes": [
            "FFmpeg processing command failed",
            "Video conversion or scaling error",
            "Memory exhaustion during processing",
            "Unsupported processing operation"
        ],
        "solutions": [
            "Check FFmpeg logs for specific error details",
            "Try simpler processing operations first",
            "Increase available system memory",
            "Use alternative processing tools if needed",
            "Break down complex operations into steps"
        ]
    },
    
    189: {
        "message": "Video metadata extraction failed",
        "description": "Cannot read or parse video file metadata",
        "common_causes": [
            "Corrupted or missing metadata in file",
            "Unsupported metadata format",
            "File header corruption",
            "Metadata extraction tool failure"
        ],
        "solutions": [
            "Use alternative metadata extraction tools",
            "Repair video file metadata if possible",
            "Re-encode video to fix metadata issues",
            "Skip metadata-dependent operations",
            "Use default values when metadata unavailable"
        ]
    }
}


def get_error_info(error_code):
    """
    Get detailed error information for a given error code
    
    Args:
        error_code (int): The error code to look up
        
    Returns:
        dict: Error information including message, description, causes, and solutions
    """
    return STREAM_ERROR_MESSAGES.get(error_code, {
        "message": f"Unknown stream error {error_code}",
        "description": "An unrecognized error occurred in stream management",
        "common_causes": ["Unknown error condition"],
        "solutions": ["Check system logs for more details", "Contact system administrator"]
    })


def format_error_response(error_code, additional_context=None):
    """
    Format a standardized error response for API endpoints
    
    Args:
        error_code (int): The error code
        additional_context (dict): Additional context information
        
    Returns:
        dict: Formatted error response
    """
    error_info = get_error_info(error_code)
    response = {
        "success": False,
        "error_code": error_code,
        "error_message": error_info["message"],
        "description": error_info["description"],
        "category": "stream_management"
    }
    
    if additional_context:
        response["context"] = additional_context
        
    return response


# Exception classes for different error categories
class StreamManagementException(Exception):
    """Base exception for stream management errors"""
    def __init__(self, error_code, message=None, context=None):
        self.error_code = error_code
        self.context = context or {}
        
        if message is None:
            error_info = get_error_info(error_code)
            message = error_info["message"]
            
        super().__init__(message)


class FFmpegException(StreamManagementException):
    """Exception for FFmpeg-related errors (100-119)"""
    pass


class SRTConnectionException(StreamManagementException):
    """Exception for SRT connection errors (120-139)"""
    pass


class StreamConfigException(StreamManagementException):
    """Exception for stream configuration errors (140-159)"""
    pass


class StreamMonitoringException(StreamManagementException):
    """Exception for stream monitoring errors (160-179)"""
    pass


class VideoProcessingException(StreamManagementException):
    """Exception for video processing errors (180-199)"""
    pass