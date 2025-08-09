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
            "Corrupted video file",
            "Unsupported video format",
            "File extension mismatch"
        ],
        "solutions": [
            "Verify file is a video before upload",
            "Check supported video formats",
            "Re-encode video to supported format",
            "Validate file extension matches content",
            "Add client-side file type validation"
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
            "Insufficient processing resources",
            "Processing parameters too demanding",
            "System overload during processing"
        ],
        "solutions": [
            "Increase processing timeout limits",
            "Add more CPU/GPU resources",
            "Optimize processing parameters",
            "Process during low-load periods",
            "Split large files into smaller segments"
        ]
    },
    
    # Storage Errors (380-399)
    380: {
        "message": "Insufficient storage space",
        "description": "Not enough disk space for video storage",
        "common_causes": [
            "Disk full or near capacity",
            "Quota limits exceeded",
            "Temporary files consuming space",
            "Backup retention too long"
        ],
        "solutions": [
            "Free up disk space",
            "Increase storage quota",
            "Clean temporary files",
            "Adjust backup retention",
            "Add more storage capacity"
        ]
    },
    
    381: {
        "message": "Storage permission error",
        "description": "Permission denied for storage operation",
        "common_causes": [
            "Incorrect file/directory permissions",
            "User lacks write access",
            "SELinux/AppArmor restrictions",
            "Mount point read-only"
        ],
        "solutions": [
            "Fix file/directory permissions",
            "Grant write access to user",
            "Configure security policies",
            "Remount with write permissions",
            "Check storage device status"
        ]
    }
}


def get_video_error_info(error_code):
    """
    Get detailed error information for a video error code
    
    Args:
        error_code (int): The video error code to look up
        
    Returns:
        dict: Error information including message, description, causes, and solutions
    """
    return VIDEO_ERROR_MESSAGES.get(error_code, {
        "message": f"Unknown video error {error_code}",
        "description": "An unrecognized error occurred in video management",
        "common_causes": ["Unknown video error condition"],
        "solutions": ["Check video logs for more details", "Contact system administrator"]
    })


def format_video_error_response(error_code, additional_context=None):
    """
    Format a standardized video error response for API endpoints
    
    Args:
        error_code (int): The video error code
        additional_context (dict): Additional context information
        
    Returns:
        dict: Formatted error response
    """
    error_info = get_video_error_info(error_code)
    response = {
        "success": False,
        "error_code": error_code,
        "error_message": error_info["message"],
        "description": error_info["description"],
        "category": "video_management"
    }
    
    if additional_context:
        response["context"] = additional_context
        
    return response


# Exception classes for different video error categories
class VideoManagementException(Exception):
    """Base exception for video management errors"""
    def __init__(self, error_code, message=None, context=None):
        self.error_code = error_code
        self.context = context or {}
        
        if message is None:
            error_info = get_video_error_info(error_code)
            message = error_info["message"]
            
        super().__init__(message)


class FileUploadException(VideoManagementException):
    """Exception for file upload errors (300-319)"""
    pass


class VideoValidationException(VideoManagementException):
    """Exception for video validation errors (320-339)"""
    pass


class FileManagementException(VideoManagementException):
    """Exception for file management errors (340-359)"""
    pass


class VideoProcessingException(VideoManagementException):
    """Exception for video processing errors (360-379)"""
    pass


class StorageException(VideoManagementException):
    """Exception for storage errors (380-399)"""
    pass