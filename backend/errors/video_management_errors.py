# Video Management Error Codes (3xx)
# Multi-Screen SRT Streaming System - Video Management Module

class VideoError:
    """Video management error codes"""
    
    # File Upload Errors (300-319)
    UPLOAD_NO_FILES = 300
    UPLOAD_INVALID_FILE = 301
    UPLOAD_FILE_TOO_LARGE = 302
    UPLOAD_DISK_FULL = 303
    UPLOAD_PERMISSION_DENIED = 304
    UPLOAD_INVALID_FORMAT = 305
    UPLOAD_CORRUPTED = 306
    UPLOAD_TIMEOUT = 307
    UPLOAD_QUOTA_EXCEEDED = 308
    UPLOAD_VIRUS_DETECTED = 309
    
    # File Validation Errors (320-339)
    VIDEO_INVALID_CODEC = 320
    VIDEO_INVALID_RESOLUTION = 321
    VIDEO_INVALID_FRAMERATE = 322
    VIDEO_INVALID_DURATION = 323
    VIDEO_INVALID_BITRATE = 324
    VIDEO_INVALID_ASPECT_RATIO = 325
    VIDEO_UNSUPPORTED_FORMAT = 326
    VIDEO_METADATA_MISSING = 327
    VIDEO_HEADER_CORRUPTED = 328
    VIDEO_STREAM_INVALID = 329
    
    # File Management Errors (340-359)
    FILE_NOT_FOUND = 340
    FILE_ACCESS_DENIED = 341
    FILE_ALREADY_EXISTS = 342
    FILE_IN_USE = 343
    FILE_CORRUPTED = 344
    FILE_SIZE_MISMATCH = 345
    FILE_MOVE_FAILED = 346
    FILE_DELETE_FAILED = 347
    FILE_COPY_FAILED = 348
    FILE_RENAME_FAILED = 349
    
    # Processing Errors (360-379)
    PROCESSING_FAILED = 360
    PROCESSING_TIMEOUT = 361
    PROCESSING_MEMORY_ERROR = 362
    PROCESSING_CPU_OVERLOAD = 363
    PROCESSING_CODEC_ERROR = 364
    PROCESSING_RESOLUTION_ERROR = 365
    PROCESSING_FRAMERATE_ERROR = 366
    PROCESSING_QUALITY_ERROR = 367
    PROCESSING_OUTPUT_ERROR = 368
    PROCESSING_INTERRUPTED = 369
    
    # Storage Errors (380-399)
    STORAGE_INSUFFICIENT_SPACE = 380
    STORAGE_PERMISSION_ERROR = 381
    STORAGE_DEVICE_ERROR = 382
    STORAGE_NETWORK_ERROR = 383
    STORAGE_QUOTA_EXCEEDED = 384
    STORAGE_PATH_INVALID = 385
    STORAGE_BACKUP_FAILED = 386
    STORAGE_CLEANUP_FAILED = 387
    STORAGE_MIGRATION_FAILED = 388
    STORAGE_CORRUPTION = 389


# Error Messages and Descriptions
VIDEO_ERROR_MESSAGES = {
    # File Upload Errors (300-319)
    300: {
        "message": "No files provided for upload",
        "description": "Upload request contains no files to process",
        "common_causes": [
            "Empty file input in web form",
            "JavaScript not sending files in request",
            "Network interruption during file transmission",
            "File input element not properly configured"
        ],
        "solutions": [
            "Ensure files are selected before upload",
            "Check JavaScript file handling code",
            "Verify network stability during upload",
            "Fix HTML form file input configuration",
            "Add client-side validation for file selection"
        ]
    },
    
    301: {
        "message": "Invalid file provided for upload",
        "description": "The uploaded file is not a valid video file",
        "common_causes": [
            "Non-video file uploaded (document, image, etc.)",
            "File extension doesn't match content type",
            "Corrupted file header or metadata",
            "Unsupported video container format"
        ],
        "solutions": [
            "Upload only video files (MP4, AVI, MOV, MKV)",
            "Verify file extension matches actual content",
            "Check file integrity and re-upload if corrupted",
            "Convert to supported format before upload",
            "Use file type validation on client side"
        ]
    },
    
    302: {
        "message": "Uploaded file exceeds size limit",
        "description": "Video file is larger than maximum allowed size",
        "common_causes": [
            "Video file too large for system limits",
            "High resolution or long duration video",
            "Uncompressed or lossless video format",
            "Multiple large files uploaded simultaneously"
        ],
        "solutions": [
            "Compress video to reduce file size",
            "Use lower resolution or shorter duration",
            "Split large videos into smaller segments",
            "Increase server upload size limits if possible",
            "Use video compression tools before upload"
        ]
    },
    
    303: {
        "message": "Insufficient disk space for upload",
        "description": "Server storage is full and cannot accept upload",
        "common_causes": [
            "Server disk partition full",
            "Temporary upload directory full",
            "Multiple concurrent uploads consuming space",
            "Old files not cleaned up properly"
        ],
        "solutions": [
            "Free up disk space by removing old files",
            "Implement automatic cleanup of old uploads",
            "Add more storage capacity to server",
            "Use external storage for large video files",
            "Monitor disk usage and set up alerts"
        ]
    },
    
    304: {
        "message": "Upload permission denied",
        "description": "Insufficient permissions to write uploaded file",
        "common_causes": [
            "Upload directory has restrictive permissions",
            "Web server user lacks write permissions",
            "SELinux or AppArmor blocking file writes",
            "File system mounted read-only"
        ],
        "solutions": [
            "Fix upload directory permissions: 'chmod 755 upload_dir'",
            "Ensure web server user can write to upload directory",
            "Configure SELinux/AppArmor policies for uploads",
            "Remount file system with write permissions",
            "Check disk space and file system health"
        ]
    },
    
    305: {
        "message": "Uploaded file format not supported",
        "description": "Video file format is not supported by the system",
        "common_causes": [
            "Rare or proprietary video format",
            "Very old video codec not supported",
            "Raw or uncompressed video format",
            "DRM-protected video content"
        ],
        "solutions": [
            "Convert video to MP4 with H.264 codec",
            "Use standard video formats (MP4, AVI, MOV)",
            "Install additional codec support if needed",
            "Remove DRM protection if legally permitted",
            "Check supported formats in system documentation"
        ]
    },
    
    306: {
        "message": "Uploaded file is corrupted",
        "description": "Video file data is corrupted and cannot be processed",
        "common_causes": [
            "Network interruption during upload",
            "Source file was already corrupted",
            "Storage device errors during write",
            "Incomplete file transfer"
        ],
        "solutions": [
            "Re-upload the file with stable network connection",
            "Verify source file integrity before upload",
            "Check server storage device health",
            "Use file checksums to verify complete transfer",
            "Implement upload resumption for large files"
        ]
    },
    
    307: {
        "message": "File upload timeout",
        "description": "Upload process exceeded maximum allowed time",
        "common_causes": [
            "Very large file size causing long upload time",
            "Slow network connection",
            "Server busy with other operations",
            "Upload timeout configured too low"
        ],
        "solutions": [
            "Increase upload timeout limits in server config",
            "Use faster network connection for uploads",
            "Compress files before uploading",
            "Implement chunked upload for large files",
            "Upload during off-peak hours"
        ]
    },
    
    308: {
        "message": "Upload quota exceeded",
        "description": "User or system upload quota has been exceeded",
        "common_causes": [
            "User storage quota fully utilized",
            "System-wide upload limits reached",
            "Daily or monthly upload limits exceeded",
            "Account limits for file count reached"
        ],
        "solutions": [
            "Delete old files to free up quota space",
            "Request quota increase if needed",
            "Wait for quota reset period",
            "Use file compression to reduce space usage",
            "Implement quota management and monitoring"
        ]
    },
    
    309: {
        "message": "Virus or malware detected in upload",
        "description": "Security scan detected threats in uploaded file",
        "common_causes": [
            "File infected with virus or malware",
            "False positive from security scanner",
            "Suspicious file characteristics detected",
            "File contains potentially harmful content"
        ],
        "solutions": [
            "Scan file with updated antivirus before upload",
            "Use clean, known-good video files",
            "Contact administrator if false positive suspected",
            "Re-encode video to remove any embedded threats",
            "Use trusted sources for video content"
        ]
    },

    # File Validation Errors (320-339)
    320: {
        "message": "Video codec not supported or invalid",
        "description": "Video uses unsupported or corrupted codec",
        "common_causes": [
            "Proprietary or patent-encumbered codec",
            "Codec not installed on system",
            "Corrupted codec information in file",
            "Very old or obsolete codec version"
        ],
        "solutions": [
            "Convert video to H.264 or H.265 codec",
            "Install required codec libraries",
            "Use ffmpeg to transcode to supported codec",
            "Check video file with mediainfo tool",
            "Re-encode video with standard codecs"
        ]
    },
    
    321: {
        "message": "Video resolution invalid or unsupported",
        "description": "Video resolution is outside supported parameters",
        "common_causes": [
            "Resolution too high for system processing",
            "Non-standard resolution causing issues",
            "Resolution not suitable for streaming layout",
            "Aspect ratio incompatible with requirements"
        ],
        "solutions": [
            "Use standard resolutions (1920x1080, 1280x720)",
            "Scale video to supported resolution",
            "Ensure resolution matches layout requirements",
            "Check maximum resolution limits in system",
            "Use aspect ratio compatible with display layout"
        ]
    },
    
    322: {
        "message": "Video framerate invalid or unsupported",
        "description": "Video framerate is outside acceptable range",
        "common_causes": [
            "Framerate too high causing processing issues",
            "Variable framerate causing synchronization problems",
            "Non-standard framerate values",
            "Framerate incompatible with streaming requirements"
        ],
        "solutions": [
            "Use standard framerates (24, 25, 30, 60 fps)",
            "Convert to constant framerate",
            "Reduce framerate if too high for system",
            "Check framerate requirements for streaming",
            "Use video editing tools to fix framerate issues"
        ]
    },
    
    323: {
        "message": "Video duration invalid",
        "description": "Video duration is outside acceptable parameters",
        "common_causes": [
            "Video too short for meaningful streaming",
            "Duration metadata corrupted or missing",
            "Very long video causing resource issues",
            "Zero duration indicating corrupted file"
        ],
        "solutions": [
            "Use videos with adequate duration (>5 seconds)",
            "Fix duration metadata in video file",
            "Split very long videos into shorter segments",
            "Verify video file is not corrupted",
            "Use video tools to repair duration information"
        ]
    },
    
    324: {
        "message": "Video bitrate invalid",
        "description": "Video bitrate is outside acceptable range",
        "common_causes": [
            "Bitrate too high for network bandwidth",
            "Bitrate too low causing quality issues",
            "Variable bitrate causing streaming problems",
            "Corrupted bitrate information"
        ],
        "solutions": [
            "Use appropriate bitrate for target quality",
            "Convert to constant bitrate if needed",
            "Adjust bitrate based on resolution and framerate",
            "Check network bandwidth requirements",
            "Use video encoding best practices for bitrate"
        ]
    },
    
    325: {
        "message": "Video aspect ratio invalid",
        "description": "Video aspect ratio is incompatible with system requirements",
        "common_causes": [
            "Aspect ratio doesn't match display layout",
            "Non-standard aspect ratio causing display issues",
            "Aspect ratio incompatible with multi-screen setup",
            "Corrupted aspect ratio metadata"
        ],
        "solutions": [
            "Use standard aspect ratios (16:9, 4:3)",
            "Crop or pad video to match required aspect ratio",
            "Check aspect ratio compatibility with layout",
            "Use video editing tools to fix aspect ratio",
            "Verify display requirements for aspect ratio"
        ]
    },
    
    326: {
        "message": "Video format not supported",
        "description": "Video container format is not supported",
        "common_causes": [
            "Proprietary or rare container format",
            "Format not supported by processing tools",
            "DRM-protected content",
            "Corrupted format headers"
        ],
        "solutions": [
            "Convert to MP4 or other supported format",
            "Use format conversion tools like ffmpeg",
            "Remove DRM if legally permitted",
            "Check supported formats documentation",
            "Use standard container formats for compatibility"
        ]
    },
    
    327: {
        "message": "Video metadata missing or incomplete",
        "description": "Required video metadata is not available",
        "common_causes": [
            "Video file missing standard metadata",
            "Metadata corruption during transfer",
            "Raw video without proper headers",
            "Metadata stripped during processing"
        ],
        "solutions": [
            "Re-encode video to add proper metadata",
            "Use video tools to repair metadata",
            "Extract metadata manually if possible",
            "Use alternative methods for video analysis",
            "Ensure metadata preservation during processing"
        ]
    },
    
    328: {
        "message": "Video header corrupted",
        "description": "Video file header is corrupted or unreadable",
        "common_causes": [
            "File transfer corruption",
            "Storage device errors",
            "Incomplete file writing",
            "File system corruption"
        ],
        "solutions": [
            "Re-upload or re-create the video file",
            "Use video repair tools to fix headers",
            "Check storage device health",
            "Verify file system integrity",
            "Use backup copy if available"
        ]
    },
    
    329: {
        "message": "Video stream structure invalid",
        "description": "Video internal stream structure is invalid",
        "common_causes": [
            "Multiple video streams in single file",
            "Corrupted stream index or structure",
            "Incomplete video encoding process",
            "Stream synchronization issues"
        ],
        "solutions": [
            "Re-encode video with single video stream",
            "Use video repair tools to fix stream structure",
            "Extract and re-mux video streams",
            "Check video encoding process for errors",
            "Use professional video tools for complex repairs"
        ]
    },

    # File Management Errors (340-359)
    340: {
        "message": "Video file not found",
        "description": "Specified video file cannot be located",
        "common_causes": [
            "Incorrect file path or filename",
            "File was deleted or moved",
            "Permission issues preventing access",
            "Network storage disconnected"
        ],
        "solutions": [
            "Verify file path and filename are correct",
            "Check if file was moved or deleted",
            "Ensure adequate permissions for file access",
            "Verify network storage connection",
            "Use absolute paths instead of relative paths"
        ]
    },
    
    341: {
        "message": "Access denied to video file",
        "description": "Insufficient permissions to access video file",
        "common_causes": [
            "File permissions too restrictive",
            "User lacks read access to file",
            "Directory permissions prevent access",
            "SELinux or security policies blocking access"
        ],
        "solutions": [
            "Fix file permissions: 'chmod 644 filename'",
            "Ensure user has read access to file and directory",
            "Check and modify SELinux policies if needed",
            "Run process with appropriate user privileges",
            "Verify file ownership is correct"
        ]
    },
    
    342: {
        "message": "Video file already exists",
        "description": "Cannot create file because it already exists",
        "common_causes": [
            "Attempting to create duplicate file",
            "File naming conflict in upload process",
            "Previous upload not properly cleaned up",
            "Race condition in file creation"
        ],
        "solutions": [
            "Use unique filenames or add timestamps",
            "Check for existing files before creation",
            "Implement proper file naming strategies",
            "Clean up incomplete uploads",
            "Use file locking to prevent race conditions"
        ]
    },
    
    343: {
        "message": "Video file currently in use",
        "description": "File is locked by another process and cannot be modified",
        "common_causes": [
            "File being processed by another operation",
            "Video player or editor has file open",
            "Streaming process using the file",
            "File system lock preventing access"
        ],
        "solutions": [
            "Wait for other processes to finish using file",
            "Stop video processing or streaming operations",
            "Close video players or editors using the file",
            "Check for zombie processes holding file locks",
            "Restart services if file locks are stuck"
        ]
    },
    
    344: {
        "message": "Video file corrupted",
        "description": "Video file data integrity has been compromised",
        "common_causes": [
            "Storage device errors or failures",
            "Incomplete file writing or transfer",
            "File system corruption",
            "Power failure during file operations"
        ],
        "solutions": [
            "Restore file from backup if available",
            "Re-upload or re-create the file",
            "Check storage device health and replace if needed",
            "Run file system check and repair",
            "Use file recovery tools if data is valuable"
        ]
    },
    
    345: {
        "message": "Video file size mismatch",
        "description": "File size doesn't match expected or reported size",
        "common_causes": [
            "Incomplete file transfer or upload",
            "File truncation during processing",
            "Metadata size information incorrect",
            "File compression or decompression errors"
        ],
        "solutions": [
            "Re-transfer file completely",
            "Verify file integrity with checksums",
            "Check file transfer process for errors",
            "Use reliable transfer methods with verification",
            "Monitor file size during transfer operations"
        ]
    },
    
    346: {
        "message": "Video file move operation failed",
        "description": "Unable to move file to destination location",
        "common_causes": [
            "Destination directory doesn't exist",
            "Insufficient permissions for move operation",
            "Cross-device move without proper handling",
            "Destination file system full"
        ],
        "solutions": [
            "Create destination directory before move",
            "Ensure adequate permissions for source and destination",
            "Use copy and delete for cross-device moves",
            "Check destination file system space",
            "Verify both source and destination paths are valid"
        ]
    },
    
    347: {
        "message": "Video file deletion failed",
        "description": "Unable to delete video file from system",
        "common_causes": [
            "File is currently in use by another process",
            "Insufficient permissions to delete file",
            "File system errors preventing deletion",
            "File attributes preventing deletion (immutable, etc.)"
        ],
        "solutions": [
            "Stop processes using the file before deletion",
            "Ensure adequate permissions for deletion",
            "Check file system health and repair if needed",
            "Remove special file attributes if present",
            "Use force deletion options if safe"
        ]
    },
    
    348: {
        "message": "Video file copy operation failed",
        "description": "Unable to copy file to destination",
        "common_causes": [
            "Insufficient space at destination",
            "Permission issues with source or destination",
            "I/O errors during copy operation",
            "File corruption during copy process"
        ],
        "solutions": [
            "Ensure adequate space at destination",
            "Fix permissions for copy operation",
            "Check storage device health",
            "Verify file integrity after copy",
            "Use robust copy methods with error checking"
        ]
    },
    
    349: {
        "message": "Video file rename operation failed",
        "description": "Unable to rename video file",
        "common_causes": [
            "File name conflicts with existing files",
            "Invalid characters in new filename",
            "File currently in use preventing rename",
            "Permission issues with file or directory"
        ],
        "solutions": [
            "Choose unique filename that doesn't conflict",
            "Use valid characters in filenames",
            "Stop processes using file before rename",
            "Ensure adequate permissions for rename operation",
            "Check directory permissions for write access"
        ]
    },

    # Processing Errors (360-379)
    360: {
        "message": "Video processing operation failed",
        "description": "General failure in video processing pipeline",
        "common_causes": [
            "FFmpeg or processing tool errors",
            "Invalid processing parameters",
            "System resource exhaustion",
            "Input file compatibility issues"
        ],
        "solutions": [
            "Check processing tool logs for specific errors",
            "Verify processing parameters are correct",
            "Ensure adequate system resources",
            "Test with simpler processing operations",
            "Update processing tools to latest versions"
        ]
    },
    
    361: {
        "message": "Video processing timeout",
        "description": "Processing operation exceeded maximum allowed time",
        "common_causes": [
            "Very large or complex video files",
            "System overload affecting processing speed",
            "Inefficient processing parameters",
            "Hardware limitations causing slow processing"
        ],
        "solutions": [
            "Increase processing timeout limits",
            "Use more efficient processing parameters",
            "Reduce system load during processing",
            "Process smaller segments of video",
            "Upgrade hardware for faster processing"
        ]
    },
    
    362: {
        "message": "Insufficient memory for video processing",
        "description": "Processing ran out of available memory",
        "common_causes": [
            "Video resolution too high for available RAM",
            "Memory leak in processing application",
            "Multiple concurrent processing operations",
            "System memory fragmentation"
        ],
        "solutions": [
            "Reduce video resolution for processing",
            "Restart processing application to clear memory leaks",
            "Limit concurrent processing operations",
            "Add more system RAM if possible",
            "Use streaming processing instead of loading entire video"
        ]
    },
    
    363: {
        "message": "CPU overload during video processing",
        "description": "Processing consumed too much