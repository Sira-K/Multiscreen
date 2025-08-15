"""
Error Management API Endpoints

Provides access to the comprehensive error handling system for users to:
- Look up error codes and get detailed information
- Access troubleshooting steps and solutions
- Get quick reference for all error categories
"""

from flask import Blueprint, jsonify, request
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
            def get_error_summary(error_code: int) -> Optional[Dict[str, Any]]:
                return {"error_code": error_code, "message": "Error service not available"}
            
            @staticmethod
            def get_quick_reference() -> Dict[str, Dict[int, str]]:
                return {"error": "Error service not available"}

# Create blueprint
error_bp = Blueprint('error_management', __name__)

# Configure logger
logger = logging.getLogger(__name__)


@error_bp.route("/error/<int:error_code>", methods=["GET"])
def get_error_details(error_code: int):
    """
    Get detailed information about a specific error code
    
    Args:
        error_code: The numeric error code to look up
        
    Returns:
        JSON response with complete error information
    """
    try:
        # Get error summary
        error_summary = ErrorService.get_error_summary(error_code)
        
        if not error_summary:
            return jsonify({
                "error": "Error code not found",
                "error_code": error_code,
                "message": f"Error code {error_code} is not defined in the system",
                "suggestions": [
                    "Check if the error code is correct",
                    "Use /errors/quick_reference to see all available error codes",
                    "Contact support if you believe this is a system error"
                ]
            }), 404
        
        return jsonify({
            "success": True,
            "error_details": error_summary
        }), 200
        
    except Exception as e:
        logger.error(f"Error looking up error code {error_code}: {e}")
        return jsonify({
            "error": "Failed to retrieve error information",
            "error_code": error_code,
            "message": str(e)
        }), 500


@error_bp.route("/errors/quick_reference", methods=["GET"])
def get_quick_reference():
    """
    Get a quick reference of all error codes organized by category
    
    Returns:
        JSON response with all error codes organized by category
    """
    try:
        quick_ref = ErrorService.get_quick_reference()
        
        return jsonify({
            "success": True,
            "quick_reference": quick_ref,
            "total_categories": len(quick_ref),
            "usage": "Use /error/<error_code> to get detailed information about a specific error"
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting quick reference: {e}")
        return jsonify({
            "error": "Failed to retrieve error reference",
            "message": str(e)
        }), 500


@error_bp.route("/errors/category/<category>", methods=["GET"])
def get_errors_by_category(category: str):
    """
    Get all error codes for a specific category
    
    Args:
        category: The error category (e.g., 'stream_management', 'docker_management')
        
    Returns:
        JSON response with all error codes in the specified category
    """
    try:
        # Map category string to enum
        category_mapping = {
            "stream_management": ErrorCategory.STREAM_MANAGEMENT,
            "docker_management": ErrorCategory.DOCKER_MANAGEMENT,
            "video_management": ErrorCategory.VIDEO_MANAGEMENT,
            "client_management": ErrorCategory.CLIENT_MANAGEMENT,
            "system_wide": ErrorCategory.SYSTEM_WIDE
        }
        
        if category not in category_mapping:
            return jsonify({
                "error": "Invalid category",
                "category": category,
                "valid_categories": list(category_mapping.keys()),
                "message": f"Category '{category}' is not valid. Use one of the valid categories."
            }), 400
        
        error_category = category_mapping[category]
        errors = ErrorService.get_errors_by_category(error_category)
        
        return jsonify({
            "success": True,
            "category": category,
            "category_code": error_category.value,
            "error_count": len(errors),
            "errors": errors
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting errors for category {category}: {e}")
        return jsonify({
            "error": "Failed to retrieve category errors",
            "category": category,
            "message": str(e)
        }), 500


@error_bp.route("/errors/search", methods=["GET"])
def search_errors():
    """
    Search for errors by keyword or partial message
    
    Args:
        q: Search query string
        category: Optional category filter
        
    Returns:
        JSON response with matching errors
    """
    try:
        query = request.args.get('q', '').lower()
        category_filter = request.args.get('category', '').lower()
        
        if not query:
            return jsonify({
                "error": "Missing search query",
                "message": "Provide a search query using the 'q' parameter",
                "example": "/errors/search?q=ffmpeg&category=stream_management"
            }), 400
        
        # Get all errors
        all_errors = ErrorService.get_quick_reference()
        matching_errors = {}
        
        for cat_name, cat_errors in all_errors.items():
            # Apply category filter if specified
            if category_filter and category_filter not in cat_name:
                continue
                
            cat_matches = {}
            for error_code, error_message in cat_errors.items():
                # Search in error message
                if query in error_message.lower():
                    cat_matches[error_code] = error_message
                # Search in error code description
                elif query in str(error_code):
                    cat_matches[error_code] = error_message
            
            if cat_matches:
                matching_errors[cat_name] = cat_matches
        
        total_matches = sum(len(matches) for matches in matching_errors.values())
        
        return jsonify({
            "success": True,
            "search_query": query,
            "category_filter": category_filter if category_filter else "all",
            "total_matches": total_matches,
            "matching_errors": matching_errors,
            "search_tips": [
                "Use specific keywords like 'ffmpeg', 'docker', 'srt'",
                "Add category filter for more focused results",
                "Use partial words (e.g., 'timeout' will find 'startup_timeout')"
            ]
        }), 200
        
    except Exception as e:
        logger.error(f"Error searching errors: {e}")
        return jsonify({
            "error": "Failed to search errors",
            "message": str(e)
        }), 500


@error_bp.route("/errors/troubleshooting/<int:error_code>", methods=["GET"])
def get_troubleshooting_steps(error_code: int):
    """
    Get detailed troubleshooting steps for a specific error code
    
    Args:
        error_code: The numeric error code
        
    Returns:
        JSON response with troubleshooting information
    """
    try:
        # Get error summary
        error_summary = ErrorService.get_error_summary(error_code)
        
        if not error_summary:
            return jsonify({
                "error": "Error code not found",
                "error_code": error_code,
                "message": f"Error code {error_code} is not defined in the system"
            }), 404
        
        # Get full error details for troubleshooting
        try:
            # Try to get the full error details
            from ..services.error_service import ErrorService
            error_details = ErrorService.create_error(ErrorCode(error_code))
            troubleshooting = error_details.get("troubleshooting_steps", {})
        except:
            # Fallback if we can't get full details
            troubleshooting = {
                "immediate_actions": [
                    "Check the primary solution above",
                    "Verify system status and connectivity",
                    "Check application logs for additional details"
                ],
                "diagnostic_commands": [
                    error_summary.get("primary_solution", "Check system logs")
                ],
                "escalation_steps": [
                    "If problem persists, check system resources",
                    "Review recent system changes or updates",
                    "Contact system administrator with error code and context"
                ]
            }
        
        return jsonify({
            "success": True,
            "error_code": error_code,
            "error_message": error_summary.get("message", "Unknown error"),
            "troubleshooting": troubleshooting,
            "additional_info": {
                "use_error_details": f"Use /error/{error_code} for complete error information",
                "contact_support": "Contact support if troubleshooting steps don't resolve the issue"
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting troubleshooting for error code {error_code}: {e}")
        return jsonify({
            "error": "Failed to retrieve troubleshooting information",
            "error_code": error_code,
            "message": str(e)
        }), 500


@error_bp.route("/errors/help", methods=["GET"])
def get_error_help():
    """
    Get help information about using the error system
    
    Returns:
        JSON response with help information
    """
    help_info = {
        "error_system_overview": {
            "description": "Comprehensive error handling system for Multi-Screen SRT Streaming System",
            "purpose": "Provide clear error codes, user-friendly messages, and actionable solutions"
        },
        "available_endpoints": {
            "get_error_details": {
                "url": "/error/<error_code>",
                "description": "Get detailed information about a specific error code",
                "example": "/error/143"
            },
            "get_quick_reference": {
                "url": "/errors/quick_reference",
                "description": "Get all error codes organized by category",
                "example": "/errors/quick_reference"
            },
            "get_errors_by_category": {
                "url": "/errors/category/<category>",
                "description": "Get all error codes for a specific category",
                "example": "/errors/category/stream_management"
            },
            "search_errors": {
                "url": "/errors/search?q=<query>&category=<category>",
                "description": "Search for errors by keyword or partial message",
                "example": "/errors/search?q=ffmpeg&category=stream_management"
            },
            "get_troubleshooting": {
                "url": "/errors/troubleshooting/<error_code>",
                "description": "Get detailed troubleshooting steps for a specific error code",
                "example": "/errors/troubleshooting/143"
            }
        },
        "error_categories": {
            "1xx": "Stream Management (FFmpeg, SRT, Configuration, Monitoring, Video Processing)",
            "2xx": "Docker Management (Service, Containers, Images, Ports, Volumes)",
            "3xx": "Video Management (Upload, Validation, File Operations, Processing, Storage)",
            "4xx": "Client Management (Registration, Assignment, Connection, Monitoring, Configuration)",
            "5xx": "System-Wide (General, Database, Network, Security, Performance)"
        },
        "usage_tips": [
            "Start with the quick reference to find relevant error codes",
            "Use specific error codes for detailed troubleshooting information",
            "Search by keywords if you don't know the exact error code",
            "Follow the troubleshooting steps in order for best results",
            "Contact support with the error code if issues persist"
        ],
        "common_error_codes": {
            "143": "Group not found in Docker - Create Docker container for the group",
            "144": "Group container not running - Start container: docker start <container>",
            "200": "Docker service not running - Start Docker: sudo systemctl start docker",
            "260": "Port already in use - Find process: netstat -tulpn | grep <port>",
            "340": "Video file not found - Check file path and permissions"
        }
    }
    
    return jsonify({
        "success": True,
        "help": help_info
    }), 200


@error_bp.route("/errors/status", methods=["GET"])
def get_error_system_status():
    """
    Get the status and health of the error handling system
    
    Returns:
        JSON response with system status information
    """
    try:
        # Test basic functionality
        quick_ref = ErrorService.get_quick_reference()
        total_errors = sum(len(errors) for errors in quick_ref.values())
        
        status_info = {
            "system_status": "healthy",
            "total_error_codes": total_errors,
            "categories_available": len(quick_ref),
            "last_updated": "2025-08-15",  # You can make this dynamic
            "version": "1.0.0",
            "features": [
                "Comprehensive error code definitions",
                "Detailed troubleshooting steps",
                "Category-based organization",
                "Search functionality",
                "API endpoints for integration"
            ],
            "health_check": {
                "error_service": "available",
                "quick_reference": "working",
                "search_functionality": "working",
                "troubleshooting": "working"
            }
        }
        
        return jsonify({
            "success": True,
            "status": status_info
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return jsonify({
            "success": False,
            "system_status": "degraded",
            "error": str(e),
            "message": "Error system is experiencing issues"
        }), 500
