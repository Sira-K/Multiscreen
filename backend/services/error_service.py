"""
Comprehensive Error Handling Service for Multi-Screen SRT Streaming System

This service provides structured error codes, user-friendly messages, and actionable solutions
for all error conditions in the system.
"""

import logging
from typing import Dict, Any, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Error categories for organization"""
    STREAM_MANAGEMENT = "1xx"
    DOCKER_MANAGEMENT = "2xx"
    VIDEO_MANAGEMENT = "3xx"
    CLIENT_MANAGEMENT = "4xx"
    SYSTEM_WIDE = "5xx"


class ErrorCode(Enum):
    """Comprehensive error codes for the system"""
    
    # Stream Management Errors (100-199)
    FFMPEG_PROCESS_FAILED = 100
    FFMPEG_PROCESS_TERMINATED = 101
    FFMPEG_STARTUP_TIMEOUT = 102
    FFMPEG_INVALID_PARAMS = 103
    FFMPEG_INPUT_NOT_FOUND = 104
    FFMPEG_OUTPUT_ERROR = 105
    FFMPEG_ENCODING_ERROR = 106
    FFMPEG_TOO_MANY_ERRORS = 107
    FFMPEG_CRITICAL_ERROR = 108
    FFMPEG_RESOURCES_EXHAUSTED = 109
    
    # SRT Connection Errors (120-139)
    SRT_CONNECTION_REFUSED = 120
    SRT_CONNECTION_TIMEOUT = 121
    SRT_CONNECTION_RESET = 122
    SRT_BROKEN_PIPE = 123
    SRT_NO_ROUTE = 124
    SRT_PORT_IN_USE = 125
    SRT_SOCKET_ERROR = 126
    SRT_HANDSHAKE_FAILURE = 127
    SRT_AUTH_ERROR = 128
    SRT_STREAM_NOT_FOUND = 129
    
    # Stream Configuration Errors (140-159)
    MISSING_STREAM_PARAMS = 140
    INVALID_GROUP_ID = 141
    INVALID_VIDEO_FILES = 142
    GROUP_NOT_FOUND_IN_DOCKER = 143
    GROUP_CONTAINER_NOT_RUNNING = 144
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
    VIDEO_FILE_CORRUPTED = 181
    VIDEO_FORMAT_NOT_SUPPORTED = 182
    VIDEO_CODEC_NOT_SUPPORTED = 183
    VIDEO_RESOLUTION_INVALID = 184
    VIDEO_DURATION_INVALID = 185
    VIDEO_PERMISSION_DENIED = 186
    VIDEO_INSUFFICIENT_DISK_SPACE = 187
    VIDEO_PROCESSING_FAILED = 188
    VIDEO_METADATA_EXTRACTION_FAILED = 189
    
    # Docker Management Errors (200-299)
    DOCKER_SERVICE_NOT_RUNNING = 200
    DOCKER_CONNECTION_FAILED = 201
    DOCKER_PERMISSION_DENIED = 202
    DOCKER_OPERATION_TIMEOUT = 203
    DOCKER_VERSION_INCOMPATIBLE = 204
    DOCKER_RESOURCES_EXHAUSTED = 205
    DOCKER_NETWORK_ERROR = 206
    DOCKER_STORAGE_ERROR = 207
    DOCKER_SERVICE_UNAVAILABLE = 208
    DOCKER_API_ERROR = 209
    
    # Container Lifecycle Errors (220-239)
    CONTAINER_CREATION_FAILED = 220
    CONTAINER_START_FAILED = 221
    CONTAINER_STOP_FAILED = 222
    CONTAINER_REMOVAL_FAILED = 223
    CONTAINER_NOT_FOUND = 224
    CONTAINER_NAME_CONFLICT = 225
    CONTAINER_INVALID_STATE = 226
    CONTAINER_EXITED_WITH_ERROR = 227
    CONTAINER_RESTART_FAILED = 228
    CONTAINER_OPERATION_TIMEOUT = 229
    
    # Port Management Errors (260-279)
    PORT_ALREADY_IN_USE = 260
    PORT_MAPPING_FAILED = 261
    PORT_RANGE_EXHAUSTED = 262
    PORT_INVALID_SPECIFICATION = 263
    PORT_ACCESS_PERMISSION_DENIED = 264
    PORT_BLOCKED_BY_FIREWALL = 265
    PORT_CONFIGURATION_CONFLICT = 266
    PORT_ALLOCATION_FAILED = 267
    PORT_BINDING_ERROR = 268
    PORT_UNAVAILABLE = 269
    
    # Video Management Errors (300-399)
    NO_FILES_PROVIDED = 300
    INVALID_FILE_PROVIDED = 301
    FILE_EXCEEDS_SIZE_LIMIT = 302
    INSUFFICIENT_DISK_SPACE = 303
    UPLOAD_PERMISSION_DENIED = 304
    FILE_FORMAT_NOT_SUPPORTED = 305
    FILE_CORRUPTED = 306
    UPLOAD_TIMEOUT = 307
    UPLOAD_QUOTA_EXCEEDED = 308
    VIRUS_DETECTED = 309
    
    # Client Management Errors (400-499)
    CLIENT_REGISTRATION_FAILED = 400
    CLIENT_ALREADY_REGISTERED = 401
    INVALID_CLIENT_ID = 402
    CLIENT_HOSTNAME_CONFLICT = 403
    INVALID_CLIENT_DATA = 404
    CLIENT_REGISTRATION_TIMEOUT = 405
    CLIENT_AUTHENTICATION_FAILED = 406
    CLIENT_VERSION_MISMATCH = 407
    CLIENT_REGISTRATION_CAPACITY_EXCEEDED = 408
    DUPLICATE_CLIENT_REGISTRATION = 409
    
    # System-Wide Errors (500-599)
    SYSTEM_INITIALIZATION_FAILED = 500
    SYSTEM_CONFIGURATION_ERROR = 501
    SYSTEM_RESOURCES_EXHAUSTED = 502
    SYSTEM_PERMISSION_DENIED = 503
    SYSTEM_SERVICE_UNAVAILABLE = 504
    SYSTEM_OPERATION_TIMEOUT = 505
    SYSTEM_INTERNAL_ERROR = 506
    SYSTEM_IN_MAINTENANCE_MODE = 507
    SYSTEM_CAPACITY_EXCEEDED = 508
    INCOMPATIBLE_SYSTEM_VERSION = 509
    
    # Database Errors (520-539)
    DATABASE_CONNECTION_FAILED = 520
    DATABASE_QUERY_FAILED = 521
    DATABASE_TRANSACTION_FAILED = 522
    DATABASE_CORRUPTION_DETECTED = 523
    DATABASE_DISK_FULL = 524
    DATABASE_PERMISSION_DENIED = 525
    DATABASE_OPERATION_TIMEOUT = 526
    DATABASE_SCHEMA_MISMATCH = 527
    DATABASE_BACKUP_FAILED = 528
    DATABASE_RESTORE_FAILED = 529
    
    # Network Errors (540-559)
    NETWORK_INTERFACE_ERROR = 540
    NETWORK_ROUTING_ERROR = 541
    DNS_RESOLUTION_FAILED = 542
    FIREWALL_BLOCKING_ACCESS = 543
    NETWORK_BANDWIDTH_EXHAUSTED = 544
    NETWORK_LATENCY_TOO_HIGH = 545
    NETWORK_PACKET_LOSS = 546
    NETWORK_PORT_UNAVAILABLE = 547
    SSL_TLS_NETWORK_ERROR = 548
    NETWORK_PROXY_ERROR = 549


class ErrorService:
    """Centralized error handling service"""
    
    # Error definitions with detailed information
    ERROR_DEFINITIONS = {
        # Stream Management Errors
        ErrorCode.FFMPEG_PROCESS_FAILED: {
            "message": "FFmpeg process failed to start",
            "meaning": "FFmpeg could not be launched or initialized on the system",
            "common_causes": ["FFmpeg binary not found", "insufficient permissions", "invalid arguments"],
            "primary_solution": "Verify FFmpeg installation: `ffmpeg -version`",
            "detailed_solutions": [
                "Check if FFmpeg is installed: `which ffmpeg`",
                "Verify FFmpeg permissions: `ls -la $(which ffmpeg)`",
                "Test FFmpeg manually: `ffmpeg -version`",
                "Check system PATH: `echo $PATH`"
            ],
            "category": ErrorCategory.STREAM_MANAGEMENT
        },
        
        ErrorCode.FFMPEG_PROCESS_TERMINATED: {
            "message": "FFmpeg process terminated unexpectedly",
            "meaning": "FFmpeg was running but suddenly stopped or crashed",
            "common_causes": ["Out of memory", "system killed process", "hardware failure"],
            "primary_solution": "Check system memory and monitor for OOM killer",
            "detailed_solutions": [
                "Check system memory: `free -h`",
                "Check for OOM killer: `dmesg | grep -i 'killed process'`",
                "Monitor system resources: `htop` or `top`",
                "Check FFmpeg logs for error details"
            ],
            "category": ErrorCategory.STREAM_MANAGEMENT
        },
        
        ErrorCode.FFMPEG_STARTUP_TIMEOUT: {
            "message": "FFmpeg startup timeout exceeded",
            "meaning": "FFmpeg failed to start up in time before a timeout limit",
            "common_causes": ["Network issues", "high system load", "server unresponsive"],
            "primary_solution": "Check network connectivity to SRT server",
            "detailed_solutions": [
                "Test network connectivity: `ping <srt-server-ip>`",
                "Check SRT server status: `docker ps`",
                "Verify port accessibility: `telnet <ip> <port>`",
                "Increase startup timeout in configuration"
            ],
            "category": ErrorCategory.STREAM_MANAGEMENT
        },
        
        # SRT Connection Errors
        ErrorCode.SRT_CONNECTION_REFUSED: {
            "message": "SRT connection refused by server",
            "meaning": "The SRT server actively rejected the connection attempt",
            "common_causes": ["Server not running", "firewall blocking", "connection limit reached"],
            "primary_solution": "Verify SRT server status: `docker ps`",
            "detailed_solutions": [
                "Check Docker container status: `docker ps -a`",
                "Start container if stopped: `docker start <container-id>`",
                "Check firewall rules: `sudo ufw status`",
                "Verify port configuration in Docker"
            ],
            "category": ErrorCategory.STREAM_MANAGEMENT
        },
        
        ErrorCode.SRT_CONNECTION_TIMEOUT: {
            "message": "SRT connection timeout",
            "meaning": "The attempt to connect to the SRT server took too long and timed out",
            "common_causes": ["High latency", "server overloaded", "incorrect IP/port"],
            "primary_solution": "Check network latency: `ping <server-ip>`",
            "detailed_solutions": [
                "Test network latency: `ping <server-ip>`",
                "Check server load: `docker stats <container-id>`",
                "Verify IP/port configuration",
                "Check network congestion and bandwidth"
            ],
            "category": ErrorCategory.STREAM_MANAGEMENT
        },
        
        # Stream Configuration Errors
        ErrorCode.GROUP_NOT_FOUND_IN_DOCKER: {
            "message": "Stream group not found in Docker",
            "meaning": "The specified group has no corresponding Docker container",
            "common_causes": ["Container not created", "manually deleted", "Docker service down"],
            "primary_solution": "Create Docker container for the group",
            "detailed_solutions": [
                "Check Docker service: `sudo systemctl status docker`",
                "List all containers: `docker ps -a`",
                "Create container for group using group management API",
                "Verify group configuration and labels"
            ],
            "category": ErrorCategory.STREAM_MANAGEMENT
        },
        
        ErrorCode.GROUP_CONTAINER_NOT_RUNNING: {
            "message": "Stream group Docker container not running",
            "meaning": "The group's Docker container exists but is currently stopped",
            "common_causes": ["Container stopped", "crashed", "insufficient resources"],
            "primary_solution": "Start container: `docker start <container>`",
            "detailed_solutions": [
                "Start container: `docker start <container-id>`",
                "Check container logs: `docker logs <container-id>`",
                "Verify resource availability: `docker stats <container-id>`",
                "Check container health status"
            ],
            "category": ErrorCategory.STREAM_MANAGEMENT
        },
        
        ErrorCode.STREAM_ALREADY_EXISTS: {
            "message": "Stream already exists for this group",
            "meaning": "A streaming process is already active for this group",
            "common_causes": ["Duplicate start request", "previous stream not stopped"],
            "primary_solution": "Stop existing stream before starting new one",
            "detailed_solutions": [
                "Stop existing stream using stop API endpoint",
                "Check running processes: `ps aux | grep ffmpeg`",
                "Kill FFmpeg processes: `pkill -f ffmpeg`",
                "Verify no duplicate streaming requests"
            ],
            "category": ErrorCategory.STREAM_MANAGEMENT
        },
        
        # Video Processing Errors
        ErrorCode.VIDEO_FILE_NOT_FOUND: {
            "message": "Video file not found at specified path",
            "meaning": "The system cannot locate the video file at the given location",
            "common_causes": ["Incorrect path", "file deleted", "permission issues"],
            "primary_solution": "Verify file exists and is accessible",
            "detailed_solutions": [
                "Check file path: `ls -la <file-path>`",
                "Verify file permissions: `stat <file-path>`",
                "Check if file was moved or deleted",
                "Ensure correct relative/absolute path"
            ],
            "category": ErrorCategory.VIDEO_MANAGEMENT
        },
        
        ErrorCode.VIDEO_FILE_CORRUPTED: {
            "message": "Video file is corrupted or unreadable",
            "meaning": "The video file data is damaged and cannot be processed",
            "common_causes": ["Incomplete transfer", "storage errors", "encoding interrupted"],
            "primary_solution": "Re-upload file or restore from backup",
            "detailed_solutions": [
                "Re-upload the video file completely",
                "Check file integrity: `ffprobe <file-path>`",
                "Verify file size matches expected",
                "Check storage device health"
            ],
            "category": ErrorCategory.VIDEO_MANAGEMENT
        },
        
        # Docker Management Errors
        ErrorCode.DOCKER_SERVICE_NOT_RUNNING: {
            "message": "Docker service is not running",
            "meaning": "The Docker daemon process is not active on the system",
            "common_causes": ["Daemon not started", "crashed", "incomplete installation"],
            "primary_solution": "Start Docker: `sudo systemctl start docker`",
            "detailed_solutions": [
                "Start Docker service: `sudo systemctl start docker`",
                "Check service status: `sudo systemctl status docker`",
                "Enable auto-start: `sudo systemctl enable docker`",
                "Check Docker installation: `docker --version`"
            ],
            "category": ErrorCategory.DOCKER_MANAGEMENT
        },
        
        ErrorCode.PORT_ALREADY_IN_USE: {
            "message": "Port already in use",
            "meaning": "Another process is currently using the requested port",
            "common_causes": ["Another container/service using port", "not cleaned up"],
            "primary_solution": "Find process: `netstat -tulpn | grep <port>`",
            "detailed_solutions": [
                "Find process using port: `netstat -tulpn | grep <port>`",
                "Check Docker port mappings: `docker port <container-id>`",
                "Stop conflicting service or container",
                "Use different port number"
            ],
            "category": ErrorCategory.DOCKER_MANAGEMENT
        },
        
        # System-Wide Errors
        ErrorCode.SYSTEM_RESOURCES_EXHAUSTED: {
            "message": "System resources exhausted",
            "meaning": "The system has run out of critical resources needed to operate",
            "common_causes": ["Memory/CPU/disk/network fully utilized"],
            "primary_solution": "Free up resources or add capacity",
            "detailed_solutions": [
                "Check system resources: `htop`, `df -h`, `free -h`",
                "Kill unnecessary processes: `pkill -f <process-name>`",
                "Clean up temporary files and logs",
                "Restart resource-intensive services"
            ],
            "category": ErrorCategory.SYSTEM_WIDE
        },
        
        ErrorCode.SYSTEM_PERMISSION_DENIED: {
            "message": "System permission denied",
            "meaning": "The system lacks necessary permissions to perform operations",
            "common_causes": ["Service account lacks privileges", "restrictive permissions"],
            "primary_solution": "Grant required privileges and fix permissions",
            "detailed_solutions": [
                "Check user permissions: `id`",
                "Add user to required groups: `sudo usermod -aG <group> <user>`",
                "Fix file permissions: `sudo chmod <permissions> <file>`",
                "Check SELinux status: `getenforce`"
            ],
            "category": ErrorCategory.SYSTEM_WIDE
        }
    }
    
    @classmethod
    def create_error(cls, error_code: ErrorCode, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a comprehensive error response
        
        Args:
            error_code: The specific error code
            context: Additional context information (file paths, IDs, etc.)
            
        Returns:
            Dict containing complete error information
        """
        if error_code not in cls.ERROR_DEFINITIONS:
            # Fallback for unknown error codes
            error_info = {
                "message": "Unknown error occurred",
                "meaning": "An unexpected error occurred that is not documented",
                "common_causes": ["System bug", "unhandled exception", "configuration error"],
                "primary_solution": "Check system logs and contact support",
                "detailed_solutions": ["Review application logs", "check system status", "contact system administrator"],
                "category": ErrorCategory.SYSTEM_WIDE
            }
        else:
            error_info = cls.ERROR_DEFINITIONS[error_code]
        
        # Build the error response
        error_response = {
            "error_code": error_code.value,
            "error_category": error_info["category"].value,
            "message": error_info["message"],
            "meaning": error_info["meaning"],
            "common_causes": error_info["common_causes"],
            "primary_solution": error_info["primary_solution"],
            "detailed_solutions": error_info["detailed_solutions"],
            "troubleshooting_steps": cls._generate_troubleshooting_steps(error_info),
            "context": context or {},
            "timestamp": cls._get_timestamp()
        }
        
        # Log the error for debugging
        logger.error(f"Error {error_code.value}: {error_info['message']}", extra={
            "error_code": error_code.value,
            "error_category": error_info["category"].value,
            "context": context
        })
        
        return error_response
    
    @classmethod
    def create_ffmpeg_error(cls, error_type: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create FFmpeg-specific error responses"""
        error_mapping = {
            "process_failed": ErrorCode.FFMPEG_PROCESS_FAILED,
            "process_terminated": ErrorCode.FFMPEG_PROCESS_TERMINATED,
            "startup_timeout": ErrorCode.FFMPEG_STARTUP_TIMEOUT,
            "invalid_params": ErrorCode.FFMPEG_INVALID_PARAMS,
            "input_not_found": ErrorCode.FFMPEG_INPUT_NOT_FOUND,
            "output_error": ErrorCode.FFMPEG_OUTPUT_ERROR,
            "encoding_error": ErrorCode.FFMPEG_ENCODING_ERROR,
            "too_many_errors": ErrorCode.FFMPEG_TOO_MANY_ERRORS,
            "critical_error": ErrorCode.FFMPEG_CRITICAL_ERROR,
            "resources_exhausted": ErrorCode.FFMPEG_RESOURCES_EXHAUSTED
        }
        
        error_code = error_mapping.get(error_type, ErrorCode.FFMPEG_PROCESS_FAILED)
        return cls.create_error(error_code, context)
    
    @classmethod
    def create_srt_error(cls, error_type: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create SRT-specific error responses"""
        error_mapping = {
            "connection_refused": ErrorCode.SRT_CONNECTION_REFUSED,
            "connection_timeout": ErrorCode.SRT_CONNECTION_TIMEOUT,
            "connection_reset": ErrorCode.SRT_CONNECTION_RESET,
            "broken_pipe": ErrorCode.SRT_BROKEN_PIPE,
            "no_route": ErrorCode.SRT_NO_ROUTE,
            "port_in_use": ErrorCode.SRT_PORT_IN_USE,
            "socket_error": ErrorCode.SRT_SOCKET_ERROR,
            "handshake_failure": ErrorCode.SRT_HANDSHAKE_FAILURE,
            "auth_error": ErrorCode.SRT_AUTH_ERROR,
            "stream_not_found": ErrorCode.SRT_STREAM_NOT_FOUND
        }
        
        error_code = error_mapping.get(error_type, ErrorCode.SRT_CONNECTION_REFUSED)
        return cls.create_error(error_code, context)
    
    @classmethod
    def create_docker_error(cls, error_type: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create Docker-specific error responses"""
        error_mapping = {
            "service_not_running": ErrorCode.DOCKER_SERVICE_NOT_RUNNING,
            "connection_failed": ErrorCode.DOCKER_CONNECTION_FAILED,
            "permission_denied": ErrorCode.DOCKER_PERMISSION_DENIED,
            "operation_timeout": ErrorCode.DOCKER_OPERATION_TIMEOUT,
            "version_incompatible": ErrorCode.DOCKER_VERSION_INCOMPATIBLE,
            "resources_exhausted": ErrorCode.DOCKER_RESOURCES_EXHAUSTED,
            "network_error": ErrorCode.DOCKER_NETWORK_ERROR,
            "storage_error": ErrorCode.DOCKER_STORAGE_ERROR,
            "service_unavailable": ErrorCode.DOCKER_SERVICE_UNAVAILABLE,
            "api_error": ErrorCode.DOCKER_API_ERROR
        }
        
        error_code = error_mapping.get(error_type, ErrorCode.DOCKER_SERVICE_NOT_RUNNING)
        return cls.create_error(error_code, context)
    
    @classmethod
    def create_video_error(cls, error_type: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create video-specific error responses"""
        error_mapping = {
            "file_not_found": ErrorCode.VIDEO_FILE_NOT_FOUND,
            "file_corrupted": ErrorCode.VIDEO_FILE_CORRUPTED,
            "format_not_supported": ErrorCode.VIDEO_FORMAT_NOT_SUPPORTED,
            "codec_not_supported": ErrorCode.VIDEO_CODEC_NOT_SUPPORTED,
            "resolution_invalid": ErrorCode.VIDEO_RESOLUTION_INVALID,
            "duration_invalid": ErrorCode.VIDEO_DURATION_INVALID,
            "permission_denied": ErrorCode.VIDEO_PERMISSION_DENIED,
            "insufficient_disk_space": ErrorCode.VIDEO_INSUFFICIENT_DISK_SPACE,
            "processing_failed": ErrorCode.VIDEO_PROCESSING_FAILED,
            "metadata_extraction_failed": ErrorCode.VIDEO_METADATA_EXTRACTION_FAILED
        }
        
        error_code = error_mapping.get(error_type, ErrorCode.VIDEO_FILE_NOT_FOUND)
        return cls.create_error(error_code, context)
    
    @classmethod
    def _generate_troubleshooting_steps(cls, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """Generate structured troubleshooting steps"""
        return {
            "immediate_actions": [
                "Check the primary solution above",
                "Verify system status and connectivity",
                "Check application logs for additional details"
            ],
            "diagnostic_commands": [
                error_info["primary_solution"]
            ] + error_info["detailed_solutions"][:2],  # Limit to first 2 detailed solutions
            "escalation_steps": [
                "If problem persists, check system resources",
                "Review recent system changes or updates",
                "Contact system administrator with error code and context"
            ]
        }
    
    @classmethod
    def _get_timestamp(cls) -> str:
        """Get current timestamp for error tracking"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    @classmethod
    def get_error_summary(cls, error_code: int) -> Optional[Dict[str, Any]]:
        """Get a summary of an error code for quick reference"""
        for code, info in cls.ERROR_DEFINITIONS.items():
            if code.value == error_code:
                return {
                    "error_code": code.value,
                    "message": info["message"],
                    "primary_solution": info["primary_solution"],
                    "category": info["category"].value
                }
        return None
    
    @classmethod
    def get_errors_by_category(cls, category: ErrorCategory) -> Dict[int, str]:
        """Get all error codes and messages for a specific category"""
        errors = {}
        for code, info in cls.ERROR_DEFINITIONS.items():
            if info["category"] == category:
                errors[code.value] = info["message"]
        return errors
    
    @classmethod
    def get_quick_reference(cls) -> Dict[str, Dict[int, str]]:
        """Get quick reference for all error categories"""
        return {
            "stream_management": cls.get_errors_by_category(ErrorCategory.STREAM_MANAGEMENT),
            "docker_management": cls.get_errors_by_category(ErrorCategory.DOCKER_MANAGEMENT),
            "video_management": cls.get_errors_by_category(ErrorCategory.VIDEO_MANAGEMENT),
            "client_management": cls.get_errors_by_category(ErrorCategory.CLIENT_MANAGEMENT),
            "system_wide": cls.get_errors_by_category(ErrorCategory.SYSTEM_WIDE)
        }
