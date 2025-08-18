"""
Error Service Integration Examples

This file demonstrates how to integrate the comprehensive error handling system
into various parts of the Multi-Screen SRT Streaming System.
"""

from flask import jsonify, request
import logging
from typing import Dict, Any, Optional

# Import the error service
try:
    from ..services.error_service import ErrorService, ErrorCode, ErrorCategory
except ImportError:
    # Fallback if import fails
    try:
        from services.error_service import ErrorService, ErrorCode, ErrorCategory
    except ImportError:
        # Create minimal fallback
        class ErrorService:
            @staticmethod
            def create_error(error_code, context=None):
                return {"error": "Error service not available"}

logger = logging.getLogger(__name__)


def example_ffmpeg_error_handling():
    """
    Example: Handling FFmpeg process failures with structured errors
    """
    try:
        # Simulate FFmpeg process failure
        ffmpeg_process = None  # This would be your actual FFmpeg process
        
        if ffmpeg_process is None:
            # Create structured error response
            error_response = ErrorService.create_ffmpeg_error("process_failed", {
                "command": "ffmpeg -i input.mp4 -c:v libx264 output.mp4",
                "group_id": "example_group",
                "timestamp": "2025-08-15T10:30:00Z"
            })
            
            logger.error(f"FFmpeg process failed: {error_response['message']}")
            return jsonify(error_response), 500
            
    except Exception as e:
        logger.error(f"Unexpected error in FFmpeg handling: {e}")
        # Fallback to generic error
        return jsonify({"error": "Unexpected error occurred"}), 500


def example_srt_connection_error_handling():
    """
    Example: Handling SRT connection failures with structured errors
    """
    try:
        # Simulate SRT connection failure
        srt_ip = "192.168.1.100"
        srt_port = 9000
        connection_timeout = 5
        
        # This would be your actual SRT connection logic
        connection_successful = False
        
        if not connection_successful:
            # Create structured error response
            error_response = ErrorService.create_srt_error("connection_refused", {
                "srt_ip": srt_ip,
                "srt_port": srt_port,
                "timeout": connection_timeout,
                "group_id": "example_group",
                "attempt_number": 1
            })
            
            logger.error(f"SRT connection failed: {error_response['message']}")
            return jsonify(error_response), 503
            
    except Exception as e:
        logger.error(f"Unexpected error in SRT handling: {e}")
        return jsonify({"error": "Unexpected error occurred"}), 500


def example_docker_error_handling():
    """
    Example: Handling Docker service failures with structured errors
    """
    try:
        # Simulate Docker service check
        docker_service_running = False
        
        if not docker_service_running:
            # Create structured error response
            error_response = ErrorService.create_docker_error("service_not_running", {
                "service_name": "docker",
                "check_command": "sudo systemctl status docker",
                "group_id": "example_group",
                "system_info": {
                    "os": "Ubuntu 20.04",
                    "docker_version": "20.10.0"
                }
            })
            
            logger.error(f"Docker service error: {error_response['message']}")
            return jsonify(error_response), 503
            
    except Exception as e:
        logger.error(f"Unexpected error in Docker handling: {e}")
        return jsonify({"error": "Unexpected error occurred"}), 500


def example_video_file_error_handling():
    """
    Example: Handling video file processing errors with structured errors
    """
    try:
        # Simulate video file validation
        video_file_path = "/path/to/video.mp4"
        file_exists = False
        
        if not file_exists:
            # Create structured error response
            error_response = ErrorService.create_video_error("file_not_found", {
                "file_path": video_file_path,
                "requested_by": "split_stream_endpoint",
                "group_id": "example_group",
                "file_operation": "read"
            })
            
            logger.error(f"Video file error: {error_response['message']}")
            return jsonify(error_response), 404
            
    except Exception as e:
        logger.error(f"Unexpected error in video handling: {e}")
        return jsonify({"error": "Unexpected error occurred"}), 500


def example_stream_configuration_error_handling():
    """
    Example: Handling stream configuration errors with structured errors
    """
    try:
        # Simulate stream configuration validation
        group_id = "invalid_group"
        video_files = []
        
        if not video_files:
            # Create structured error response
            error_response = ErrorService.create_error(ErrorCode.INVALID_VIDEO_FILES, {
                "group_id": group_id,
                "video_files_count": len(video_files),
                "required_minimum": 1,
                "endpoint": "start_multi_video_srt"
            })
            
            logger.error(f"Stream configuration error: {error_response['message']}")
            return jsonify(error_response), 400
            
    except Exception as e:
        logger.error(f"Unexpected error in configuration handling: {e}")
        return jsonify({"error": "Unexpected error occurred"}), 500


def example_system_resource_error_handling():
    """
    Example: Handling system resource exhaustion with structured errors
    """
    try:
        # Simulate system resource check
        available_memory = 512  # MB
        required_memory = 1024  # MB
        
        if available_memory < required_memory:
            # Create structured error response
            error_response = ErrorService.create_error(ErrorCode.SYSTEM_RESOURCES_EXHAUSTED, {
                "resource_type": "memory",
                "available": f"{available_memory}MB",
                "required": f"{required_memory}MB",
                "deficit": f"{required_memory - available_memory}MB",
                "operation": "video_streaming",
                "group_id": "example_group"
            })
            
            logger.error(f"System resource error: {error_response['message']}")
            return jsonify(error_response), 503
            
    except Exception as e:
        logger.error(f"Unexpected error in resource handling: {e}")
        return jsonify({"error": "Unexpected error occurred"}), 500


def example_error_with_context_and_logging():
    """
    Example: Comprehensive error handling with context and logging
    """
    try:
        # Simulate a complex operation that might fail
        operation_name = "multi_video_stream_startup"
        group_id = "example_group_123"
        
        # This would be your actual operation logic
        operation_successful = False
        
        if not operation_successful:
            # Create comprehensive error context
            error_context = {
                "operation": operation_name,
                "group_id": group_id,
                "timestamp": "2025-08-15T10:30:00Z",
                "user_id": "user_456",
                "request_data": {
                    "video_count": 4,
                    "layout": "2x2",
                    "resolution": "1920x1080"
                },
                "system_state": {
                    "docker_containers": 3,
                    "active_streams": 2,
                    "memory_usage": "75%",
                    "cpu_usage": "60%"
                },
                "previous_errors": [
                    {"code": 143, "time": "2025-08-15T10:25:00Z"},
                    {"code": 200, "time": "2025-08-15T10:20:00Z"}
                ]
            }
            
            # Create structured error response
            error_response = ErrorService.create_error(ErrorCode.STREAM_CONFIG_MISMATCH, error_context)
            
            # Log the error with full context
            logger.error(f"Stream configuration mismatch: {error_response['message']}", extra={
                "error_code": error_response['error_code'],
                "error_category": error_response['error_category'],
                "context": error_context,
                "troubleshooting_steps": error_response['troubleshooting_steps']
            })
            
            return jsonify(error_response), 400
            
    except Exception as e:
        logger.error(f"Unexpected error in operation: {e}")
        return jsonify({"error": "Unexpected error occurred"}), 500


def example_error_recovery_and_retry():
    """
    Example: Error handling with recovery and retry logic
    """
    try:
        # Simulate a recoverable operation
        max_retries = 3
        current_attempt = 1
        
        while current_attempt <= max_retries:
            try:
                # This would be your actual operation
                operation_successful = False  # Simulate failure
                
                if operation_successful:
                    logger.info(f"Operation succeeded on attempt {current_attempt}")
                    return jsonify({"success": True, "attempt": current_attempt}), 200
                    
            except Exception as e:
                logger.warning(f"Operation failed on attempt {current_attempt}: {e}")
                
                if current_attempt == max_retries:
                    # Create error response for final failure
                    error_response = ErrorService.create_error(ErrorCode.FFMPEG_TOO_MANY_ERRORS, {
                        "operation": "video_processing",
                        "max_retries": max_retries,
                        "final_error": str(e),
                        "group_id": "example_group"
                    })
                    
                    logger.error(f"Operation failed after {max_retries} attempts: {error_response['message']}")
                    return jsonify(error_response), 500
                
                current_attempt += 1
                # Wait before retry (exponential backoff)
                import time
                time.sleep(2 ** current_attempt)
                
    except Exception as e:
        logger.error(f"Unexpected error in retry logic: {e}")
        return jsonify({"error": "Unexpected error occurred"}), 500


def example_error_aggregation():
    """
    Example: Aggregating multiple errors into a comprehensive report
    """
    try:
        # Simulate collecting multiple errors
        errors_collected = []
        
        # Check multiple system components
        checks = [
            ("docker_service", "docker", "service_not_running"),
            ("srt_server", "srt", "connection_timeout"),
            ("ffmpeg_process", "ffmpeg", "process_failed")
        ]
        
        for check_name, service_type, error_type in checks:
            try:
                # This would be your actual health check
                check_passed = False  # Simulate failure
                
                if not check_passed:
                    if service_type == "docker":
                        error_response = ErrorService.create_docker_error(error_type, {
                            "check_name": check_name,
                            "timestamp": "2025-08-15T10:30:00Z"
                        })
                    elif service_type == "srt":
                        error_response = ErrorService.create_srt_error(error_type, {
                            "check_name": check_name,
                            "timestamp": "2025-08-15T10:30:00Z"
                        })
                    elif service_type == "ffmpeg":
                        error_response = ErrorService.create_ffmpeg_error(error_type, {
                            "check_name": check_name,
                            "timestamp": "2025-08-15T10:30:00Z"
                        })
                    
                    errors_collected.append(error_response)
                    
            except Exception as e:
                logger.error(f"Error during {check_name} check: {e}")
        
        if errors_collected:
            # Create aggregated error report
            aggregated_report = {
                "summary": f"System health check failed with {len(errors_collected)} errors",
                "total_errors": len(errors_collected),
                "errors": errors_collected,
                "system_status": "degraded",
                "recommended_actions": [
                    "Check Docker service status",
                    "Verify SRT server connectivity",
                    "Ensure FFmpeg is properly installed"
                ],
                "timestamp": "2025-08-15T10:30:00Z"
            }
            
            logger.error(f"System health check failed: {aggregated_report['summary']}")
            return jsonify(aggregated_report), 503
        
        # All checks passed
        return jsonify({
            "system_status": "healthy",
            "message": "All system components are functioning normally"
        }), 200
        
    except Exception as e:
        logger.error(f"Unexpected error in health check: {e}")
        return jsonify({"error": "Unexpected error occurred"}), 500


# Example usage in a Flask route
def example_flask_route():
    """
    Example Flask route showing error service integration
    """
    try:
        # Your route logic here
        data = request.get_json()
        
        if not data:
            error_response = ErrorService.create_error(ErrorCode.MISSING_STREAM_PARAMS, {
                "endpoint": "start_multi_video_srt",
                "required_fields": ["group_id", "video_files"],
                "received_data": str(data)
            })
            return jsonify(error_response), 400
        
        # Continue with normal processing...
        return jsonify({"success": True}), 200
        
    except Exception as e:
        logger.error(f"Route error: {e}")
        error_response = ErrorService.create_error(ErrorCode.SYSTEM_INTERNAL_ERROR, {
            "endpoint": "start_multi_video_srt",
            "error_details": str(e)
        })
        return jsonify(error_response), 500


if __name__ == "__main__":
    # Example usage
    print("Error Service Integration Examples")
    print("=" * 40)
    
    # Test various error scenarios
    examples = [
        example_ffmpeg_error_handling,
        example_srt_connection_error_handling,
        example_docker_error_handling,
        example_video_file_error_handling,
        example_stream_configuration_error_handling,
        example_system_resource_error_handling,
        example_error_with_context_and_logging,
        example_error_recovery_and_retry,
        example_error_aggregation
    ]
    
    for example in examples:
        print(f"\nTesting: {example.__name__}")
        try:
            result = example()
            print(f"Result: {result}")
        except Exception as e:
            print(f"Error: {e}")
    
    print("\nExamples completed!")
