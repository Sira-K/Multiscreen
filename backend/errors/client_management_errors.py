# Client Management Error Codes (4xx)
# Multi-Screen SRT Streaming System - Client Management Module

class ClientError:
    """Client management error codes"""
    
    # Registration Errors (400-419)
    CLIENT_REGISTRATION_FAILED = 400
    CLIENT_ALREADY_REGISTERED = 401
    CLIENT_INVALID_ID = 402
    CLIENT_HOSTNAME_CONFLICT = 403
    CLIENT_INVALID_DATA = 404
    CLIENT_REGISTRATION_TIMEOUT = 405
    CLIENT_AUTH_FAILED = 406
    CLIENT_VERSION_MISMATCH = 407
    CLIENT_CAPACITY_EXCEEDED = 408
    CLIENT_DUPLICATE_REGISTRATION = 409
    
    # Assignment Errors (420-439)
    CLIENT_NOT_FOUND = 420
    CLIENT_ASSIGNMENT_FAILED = 421
    CLIENT_GROUP_NOT_FOUND = 422
    CLIENT_SCREEN_CONFLICT = 423
    CLIENT_ALREADY_ASSIGNED = 424
    CLIENT_GROUP_FULL = 425
    CLIENT_INCOMPATIBLE_CONFIG = 426
    CLIENT_ASSIGNMENT_TIMEOUT = 427
    CLIENT_PERMISSION_DENIED = 428
    CLIENT_STATE_INVALID = 429
    
    # Connection Errors (440-459)
    CLIENT_CONNECTION_FAILED = 440
    CLIENT_CONNECTION_LOST = 441
    CLIENT_HEARTBEAT_TIMEOUT = 442
    CLIENT_NETWORK_ERROR = 443
    CLIENT_CONNECTION_REFUSED = 444
    CLIENT_CONNECTION_RESET = 445
    CLIENT_BANDWIDTH_INSUFFICIENT = 446
    CLIENT_LATENCY_TOO_HIGH = 447
    CLIENT_CONNECTION_UNSTABLE = 448
    CLIENT_FIREWALL_BLOCKED = 449
    
    # Status and Monitoring Errors (460-479)
    CLIENT_STATUS_UNKNOWN = 460
    CLIENT_NOT_RESPONDING = 461
    CLIENT_HEALTH_CHECK_FAILED = 462
    CLIENT_PERFORMANCE_DEGRADED = 463
    CLIENT_RESOURCE_EXHAUSTED = 464
    CLIENT_STREAMING_ERROR = 465
    CLIENT_SYNC_LOST = 466
    CLIENT_BUFFER_ISSUES = 467
    CLIENT_DISPLAY_ERROR = 468
    CLIENT_HARDWARE_ERROR = 469
    
    # Configuration Errors (480-499)
    CLIENT_CONFIG_INVALID = 480
    CLIENT_CONFIG_MISSING = 481
    CLIENT_CONFIG_CONFLICT = 482
    CLIENT_UPDATE_FAILED = 483
    CLIENT_SETTINGS_ERROR = 484
    CLIENT_CAPABILITY_MISMATCH = 485
    CLIENT_RESOLUTION_ERROR = 486
    CLIENT_CODEC_UNSUPPORTED = 487
    CLIENT_PROFILE_ERROR = 488
    CLIENT_VALIDATION_FAILED = 489


# Error Messages and Descriptions
CLIENT_ERROR_MESSAGES = {
    # Registration Errors (400-419)
    400: {
        "message": "Client registration failed",
        "description": "Unable to register client with the system",
        "common_causes": [
            "Invalid client information provided",
            "Server registration service unavailable",
            "Database connection issues",
            "Registration request malformed"
        ],
        "solutions": [
            "Verify client information is complete and valid",
            "Check server registration service status",
            "Ensure database connectivity",
            "Validate registration request format",
            "Retry registration with exponential backoff"
        ]
    },
    
    401: {
        "message": "Client already registered",
        "description": "Client is already registered in the system",
        "common_causes": [
            "Duplicate registration attempt",
            "Client reconnecting after network interruption",
            "Previous registration not properly cleaned up",
            "Multiple client instances on same device"
        ],
        "solutions": [
            "Check if client is already registered before retry",
            "Unregister client before re-registration if needed",
            "Clean up stale registrations periodically",
            "Use unique client IDs to prevent conflicts",
            "Implement registration update instead of new registration"
        ]
    },
    
    402: {
        "message": "Invalid client ID provided",
        "description": "Client ID format or content is invalid",
        "common_causes": [
            "Client ID contains invalid characters",
            "Client ID too long or too short",
            "Client ID format doesn't match requirements",
            "Empty or null client ID provided"
        ],
        "solutions": [
            "Generate valid client ID following system requirements",
            "Use alphanumeric characters and allowed symbols only",
            "Ensure client ID length is within limits",
            "Validate client ID format before registration",
            "Use UUID or similar standard for client IDs"
        ]
    },
    
    403: {
        "message": "Client hostname conflict",
        "description": "Client hostname conflicts with existing registration",
        "common_causes": [
            "Multiple clients using same hostname",
            "Hostname not unique in network environment",
            "Client cloning without changing hostname",
            "DNS resolution returning same hostname"
        ],
        "solutions": [
            "Ensure each client has unique hostname",
            "Add unique suffixes to hostnames if needed",
            "Use MAC address or hardware ID in hostname",
            "Configure DNS to return unique hostnames",
            "Allow multiple clients per hostname with different IDs"
        ]
    },
    
    404: {
        "message": "Invalid client data",
        "description": "Client registration data is invalid or incomplete",
        "common_causes": [
            "Required fields missing from registration data",
            "Data types incorrect for client information",
            "Client capabilities data malformed",
            "Version information invalid or missing"
        ],
        "solutions": [
            "Provide all required registration fields",
            "Use correct data types for each field",
            "Validate client capabilities before registration",
            "Include valid version information",
            "Follow client registration API documentation"
        ]
    },
    
    405: {
        "message": "Client registration timeout",
        "description": "Registration process exceeded maximum allowed time",
        "common_causes": [
            "Server overloaded with registration requests",
            "Network latency too high for timely registration",
            "Database operations taking too long",
            "Client taking too long to respond"
        ],
        "solutions": [
            "Increase registration timeout values",
            "Reduce server load during registration",
            "Optimize database operations for faster response",
            "Improve network connectivity for registration",
            "Implement registration queuing system"
        ]
    },
    
    406: {
        "message": "Client authentication failed",
        "description": "Client failed to authenticate during registration",
        "common_causes": [
            "Invalid authentication credentials",
            "Authentication service unavailable",
            "Client certificate invalid or expired",
            "Authentication protocol mismatch"
        ],
        "solutions": [
            "Verify client authentication credentials",
            "Check authentication service availability",
            "Update or renew client certificates",
            "Use correct authentication protocol",
            "Check system time for certificate validation"
        ]
    },
    
    407: {
        "message": "Client version mismatch",
        "description": "Client version is incompatible with server",
        "common_causes": [
            "Client software too old for server requirements",
            "Server API version incompatible with client",
            "Feature requirements not met by client version",
            "Protocol version mismatch"
        ],
        "solutions": [
            "Update client software to compatible version",
            "Check server API version requirements",
            "Verify client supports required features",
            "Use compatible protocol version",
            "Implement version negotiation if possible"
        ]
    },
    
    408: {
        "message": "Client registration capacity exceeded",
        "description": "Maximum number of registered clients reached",
        "common_causes": [
            "System client limit reached",
            "License restrictions on client count",
            "Resource limitations preventing more clients",
            "Database capacity limits reached"
        ],
        "solutions": [
            "Increase system client limits if possible",
            "Upgrade license to allow more clients",
            "Add more system resources for client management",
            "Clean up inactive or stale client registrations",
            "Implement client registration queuing"
        ]
    },
    
    409: {
        "message": "Duplicate client registration detected",
        "description": "Client is attempting to register multiple times",
        "common_causes": [
            "Client software bug causing multiple registrations",
            "Network issues causing registration retries",
            "Load balancer duplicating registration requests",
            "Client restart without proper cleanup"
        ],
        "solutions": [
            "Fix client software to prevent duplicate registrations",
            "Implement registration deduplication logic",
            "Configure load balancer to prevent duplication",
            "Clean up client state on restart",
            "Use registration tokens to prevent duplicates"
        ]
    },

    # Assignment Errors (420-439)
    420: {
        "message": "Client not found in system",
        "description": "Specified client does not exist in the system",
        "common_causes": [
            "Client never registered with system",
            "Client was unregistered or expired",
            "Client ID incorrect or misspelled",
            "Database inconsistency with client records"
        ],
        "solutions": [
            "Register client before attempting assignment",
            "Verify client ID is correct and exists",
            "Check client registration status",
            "Clean up database inconsistencies",
            "Re-register client if registration expired"
        ]
    },
    
    421: {
        "message": "Client assignment failed",
        "description": "Unable to assign client to group or stream",
        "common_causes": [
            "Assignment target doesn't exist",
            "Client incompatible with assignment target",
            "Resource constraints preventing assignment",
            "Assignment process interrupted"
        ],
        "solutions": [
            "Verify assignment target exists and is available",
            "Check client compatibility with target",
            "Ensure adequate resources for assignment",
            "Retry assignment process if interrupted",
            "Use alternative assignment if primary fails"
        ]
    },
    
    422: {
        "message": "Group not found for client assignment",
        "description": "Specified group does not exist for assignment",
        "common_causes": [
            "Group ID incorrect or doesn't exist",
            "Group was deleted but assignment attempted",
            "Group not yet created in system",
            "Case sensitivity issues with group ID"
        ],
        "solutions": [
            "Verify group exists before assignment",
            "Create group if it should exist",
            "Check group ID spelling and case",
            "List available groups for reference",
            "Use valid group IDs for assignments"
        ]
    },
    
    423: {
        "message": "Screen assignment conflict",
        "description": "Client screen assignment conflicts with existing assignment",
        "common_causes": [
            "Multiple clients assigned to same screen",
            "Screen number exceeds group screen count",
            "Assignment race condition occurred",
            "Screen already in use by another client"
        ],
        "solutions": [
            "Use unique screen assignments for each client",
            "Verify screen number is within group limits",
            "Implement assignment locking to prevent races",
            "Check existing assignments before new assignment",
            "Use automatic screen assignment if manual fails"
        ]
    },
    
    424: {
        "message": "Client already assigned",
        "description": "Client is already assigned to a group or stream",
        "common_causes": [
            "Duplicate assignment attempt",
            "Client assignment not cleared before new assignment",
            "Assignment state inconsistency",
            "Multiple assignment requests processed"
        ],
        "solutions": [
            "Clear existing assignment before new assignment",
            "Check client assignment status before assigning",
            "Implement assignment state consistency checks",
            "Use assignment updates instead of new assignments",
            "Synchronize assignment operations properly"
        ]
    },
    
    425: {
        "message": "Group capacity full",
        "description": "Group has reached maximum client capacity",
        "common_causes": [
            "All screens in group already assigned",
            "Group client limit reached",
            "Resource limitations preventing more assignments",
            "Group configuration limits exceeded"
        ],
        "solutions": [
            "Use different group with available capacity",
            "Increase group screen count if possible",
            "Remove inactive clients from group",
            "Create additional groups for more clients",
            "Implement client assignment queuing"
        ]
    },
    
    426: {
        "message": "Client configuration incompatible",
        "description": "Client configuration incompatible with assignment target",
        "common_causes": [
            "Client resolution incompatible with group",
            "Client codec support insufficient",
            "Network requirements not met by client",
            "Hardware capabilities insufficient"
        ],
        "solutions": [
            "Update client configuration to match requirements",
            "Use compatible group settings for client",
            "Upgrade client hardware if needed",
            "Configure group to accommodate client capabilities",
            "Use alternative assignment with compatible settings"
        ]
    },
    
    427: {
        "message": "Client assignment timeout",
        "description": "Assignment process exceeded maximum allowed time",
        "common_causes": [
            "Network delays in assignment process",
            "Server overload affecting assignment speed",
            "Client not responding to assignment requests",
            "Resource allocation taking too long"
        ],
        "solutions": [
            "Increase assignment timeout values",
            "Reduce server load during assignments",
            "Check client responsiveness to requests",
            "Optimize resource allocation process",
            "Implement assignment retry with backoff"
        ]
    },
    
    428: {
        "message": "Client assignment permission denied",
        "description": "Insufficient permissions for client assignment",
        "common_causes": [
            "User lacks assignment privileges",
            "Client not authorized for target group",
            "Assignment policy restrictions",
            "Security policies preventing assignment"
        ],
        "solutions": [
            "Ensure user has assignment permissions",
            "Authorize client for target group access",
            "Review and update assignment policies",
            "Configure security policies for assignments",
            "Use administrator account for assignments"
        ]
    },
    
    429: {
        "message": "Client in invalid state for assignment",
        "description": "Client state prevents assignment operation",
        "common_causes": [
            "Client not ready for assignment",
            "Client in error or disconnected state",
            "Client undergoing maintenance or update",
            "Client state transition in progress"
        ],
        "solutions": [
            "Wait for client to reach ready state",
            "Fix client errors before assignment",
            "Complete maintenance or updates before assignment",
            "Wait for state transition to complete",
            "Reset client to valid state if needed"
        ]
    },

    # Connection Errors (440-459)
    440: {
        "message": "Client connection failed",
        "description": "Unable to establish connection with client",
        "common_causes": [
            "Client device offline or unreachable",
            "Network connectivity issues",
            "Client software not running",
            "Firewall blocking connection attempts"
        ],
        "solutions": [
            "Verify client device is online and accessible",
            "Check network connectivity to client",
            "Ensure client software is running",
            "Configure firewall to allow connections",
            "Use alternative connection methods if available"
        ]
    },
    
    441: {
        "message": "Client connection lost",
        "description": "Connection to client was lost unexpectedly",
        "common_causes": [
            "Network interruption or instability",
            "Client device power loss or shutdown",
            "Client software crashed or stopped",
            "Network equipment failure"
        ],
        "solutions": [
            "Check network stability and connectivity",
            "Verify client device power and status",
            "Restart client software if crashed",
            "Check network equipment status",
            "Implement automatic reconnection logic"
        ]
    },
    
    442: {
        "message": "Client heartbeat timeout",
        "description": "Client failed to respond to heartbeat requests",
        "common_causes": [
            "Client overloaded and unable to respond",
            "Network latency causing heartbeat delays",
            "Client software hung or frozen",
            "Heartbeat timeout configured too low"
        ],
        "solutions": [
            "Reduce client load to improve responsiveness",
            "Increase heartbeat timeout values",
            "Restart client software if hung",
            "Improve network latency to client",
            "Implement heartbeat retry logic"
        ]
    },
    
    443: {
        "message": "Client network error",
        "description": "Network error occurred in client communication",
        "common_causes": [
            "Network packet loss or corruption",
            "Network congestion affecting communication",
            "Network interface errors on client",
            "DNS resolution issues for client"
        ],
        "solutions": [
            "Check and fix network packet loss",
            "Reduce network congestion or increase bandwidth",
            "Fix client network interface issues",
            "Resolve DNS issues for client connectivity",
            "Use alternative network paths if available"
        ]
    },
    
    444: {
        "message": "Client connection refused",
        "description": "Client actively refused connection attempt",
        "common_causes": [
            "Client not listening on expected port",
            "Client firewall blocking incoming connections",
            "Client authentication rejecting connection",
            "Client at connection limit"
        ],
        "solutions": [
            "Verify client is listening on correct port",
            "Configure client firewall to allow connections",
            "Update client authentication settings",
            "Increase client connection limits",
            "Check client service status and restart if needed"
        ]
    },
    
    445: {
        "message": "Client connection reset",
        "description": "Client connection was reset unexpectedly",
        "common_causes": [
            "Client software restarted during connection",
            "Network path changed affecting connection",
            "Client detected protocol violation",
            "Client resource limits exceeded"
        ],
        "solutions": [
            "Check client software stability and logs",
            "Verify network path consistency",
            "Review protocol compliance in communication",
            "Monitor client resource usage",
            "Implement robust reconnection handling"
        ]
    },
    
    446: {
        "message": "Insufficient bandwidth for client",
        "description": "Network bandwidth inadequate for client operations",
        "common_causes": [
            "Network bandwidth too low for streaming",
            "Multiple clients competing for bandwidth",
            "Network congestion affecting throughput",
            "Client requirements exceeding available bandwidth"
        ],
        "solutions": [
            "Increase network bandwidth capacity",
            "Implement bandwidth management and QoS",
            "Reduce streaming quality to match bandwidth",
            "Schedule high-bandwidth operations during off-peak",
            "Use bandwidth optimization techniques"
        ]
    },
    
    447: {
        "message": "Network latency too high for client",
        "description": "Network latency exceeds acceptable limits",
        "common_causes": [
            "Physical distance to client too great",
            "Network routing inefficient for client",
            "Network equipment introducing delays",
            "Internet connectivity with high latency"
        ],
        "solutions": [
            "Use edge servers closer to clients",
            "Optimize network routing to clients",
            "Upgrade network equipment for lower latency",
            "Use latency compensation techniques",
            "Consider alternative network paths"
        ]
    },
    
    448: {
        "message": "Client connection unstable",
        "description": "Client connection quality is unstable",
        "common_causes": [
            "Intermittent network connectivity issues",
            "Client moving between network connections",
            "Network equipment intermittent failures",
            "Power or environmental issues at client"
        ],
        "solutions": [
            "Fix intermittent network connectivity issues",
            "Use connection bonding or redundancy",
            "Replace faulty network equipment",
            "Improve client power and environmental conditions",
            "Implement adaptive connection management"
        ]
    },
    
    449: {
        "message": "Client connection blocked by firewall",
        "description": "Firewall is blocking connection to client",
        "common_causes": [
            "Client firewall blocking required ports",
            "Network firewall rules preventing connection",
            "Security policies blocking client communication",
            "Port forwarding not configured properly"
        ],
        "solutions": [
            "Configure client firewall to allow required ports",
            "Update network firewall rules for client access",
            "Review and update security policies",
            "Configure port forwarding for client access",
            "Use VPN or tunneling if direct access blocked"
        ]
    },

    # Status and Monitoring Errors (460-479)
    460: {
        "message": "Client status unknown",
        "description": "Unable to determine current client status",
        "common_causes": [
            "Client not responding to status requests",
            "Status monitoring service unavailable",
            "Client in transitional state",
            "Communication errors preventing status updates"
        ],
        "solutions": [
            "Check client responsiveness to requests",
            "Verify status monitoring service is running",
            "Wait for client state transition to complete",
            "Fix communication issues with client",
            "Implement alternative status checking methods"
        ]
    },
    
    461: {
        "message": "Client not responding",
        "description": "Client is not responding to requests or commands",
        "common_causes": [
            "Client software hung or frozen",
            "Client device overloaded or out of resources",
            "Network connectivity preventing responses",
            "Client in power saving or sleep mode"
        ],
        "solutions": [
            "Restart client software or device",
            "Reduce client load and free up resources",
            "Fix network connectivity issues",
            "Wake client from power saving mode",
            "Check client hardware status and health"
        ]
    },
    
    462: {
        "message": "Client health check failed",
        "description": "Client failed system health monitoring checks",
        "common_causes": [
            "Client performance below acceptable thresholds",
            "Client hardware issues detected",
            "Client software errors or instability",
            "Client resource exhaustion"
        ],
        "solutions": [
            "Investigate and fix client performance issues",
            "Check and repair client hardware problems",
            "Fix client software errors and update if needed",
            "Free up client resources or add more capacity",
            "Implement client health monitoring and alerts"
        ]
    },
    
    463: {
        "message": "Client performance degraded",
        "description": "Client performance has fallen below acceptable levels",
        "common_causes": [
            "Client CPU or memory overload",
            "Network congestion affecting client",
            "Client storage I/O bottlenecks",
            "Background processes consuming resources"
        ],
        "solutions": [
            "Reduce client CPU and memory usage",
            "Improve network bandwidth and reduce congestion",
            "Optimize client storage and I/O performance",
            "Stop unnecessary background processes",
            "Monitor and manage client resource usage"
        ]
    },
    
    464: {
        "message": "Client resources exhausted",
        "description": "Client has run out of critical system resources",
        "common_causes": [
            "Client memory fully utilized",
            "Client CPU at maximum capacity",
            "Client storage space exhausted",
            "Client network connections at limit"
        ],
        "solutions": [
            "Free up client memory by closing applications",
            "Reduce CPU load on client system",
            "Clean up client storage space",
            "Close unnecessary network connections",
            "Upgrade client hardware if resource limits persist"
        ]
    },
    
    465: {
        "message": "Client streaming error",
        "description": "Error occurred in client's streaming functionality",
        "common_causes": [
            "Streaming protocol errors on client",
            "Client decoder issues with stream",
            "Network issues affecting stream quality",
            "Client display hardware problems"
        ],
        "solutions": [
            "Check client streaming protocol implementation",
            "Update client decoder software or drivers",
            "Fix network issues affecting stream delivery",
            "Check client display hardware and drivers",
            "Use alternative streaming methods if needed"
        ]
    },
    
    466: {
        "message": "Client synchronization lost",
        "description": "Client lost synchronization with other clients or server",
        "common_causes": [
            "Client clock drift from system time",
            "Network jitter affecting synchronization",
            "Client processing delays causing desync",
            "Synchronization protocol errors"
        ],
        "solutions": [
            "Synchronize client clock with network time",
            "Implement jitter buffer for network stability",
            "Optimize client processing for consistent timing",
            "Fix synchronization protocol implementation",
            "Use hardware-based synchronization if available"
        ]
    },
    
    467: {
        "message": "Client buffer issues",
        "description": "Client experiencing buffer underrun or overflow",
        "common_causes": [
            "Client buffer size inadequate for conditions",
            "Network delivery inconsistent with buffer rates",
            "Client processing unable to keep up",
            "Buffer management algorithm issues"
        ],
        "solutions": [
            "Adjust client buffer sizes for conditions",
            "Improve network delivery consistency",
            "Optimize client processing performance",
            "Fix buffer management algorithms",
            "Implement adaptive buffering strategies"
        ]
    },
    
    468: {
        "message": "Client display error",
        "description": "Error in client's display or rendering system",
        "common_causes": [
            "Display hardware malfunction",
            "Graphics driver issues on client",
            "Display resolution or format incompatibility",
            "Display connection problems"
        ],
        "solutions": [
            "Check and repair display hardware",
            "Update graphics drivers on client",
            "Use compatible display resolution and format",
            "Fix display connection and cables",
            "Test with alternative display if available"
        ]
    },
    
    469: {
        "message": "Client hardware error",
        "description": "Hardware malfunction detected on client device",
        "common_causes": [
            "Component failure in client device",
            "Overheating causing hardware instability",
            "Power supply issues affecting hardware",
            "Hardware compatibility problems"
        ],
        "solutions": [
            "Diagnose and replace failed hardware components",
            "Improve cooling and thermal management",
            "Check and fix power supply issues",
            "Verify hardware compatibility and configuration",
            "Run hardware diagnostic tools"
        ]
    },

    # Configuration Errors (480-499)
    480: {
        "message": "Client configuration invalid",
        "description": "Client configuration settings are invalid",
        "common_causes": [
            "Configuration file corrupted or malformed",
            "Invalid parameter values in configuration",
            "Configuration version incompatible",
            "Missing required configuration settings"
        ],
        "solutions": [
            "Restore configuration from backup or defaults",
            "Validate all configuration parameter values",
            "Update configuration to compatible version",
            "Add missing required configuration settings",
            "Use configuration validation tools"
        ]
    },
    
    481: {
        "message": "Client configuration missing",
        "description": "Required client configuration is not available",
        "common_causes": [
            "Configuration file not found or deleted",
            "Configuration not deployed to client",
            "Configuration service unavailable",
            "Client unable to access configuration location"
        ],
        "solutions": [
            "Deploy configuration file to client",
            "Ensure configuration service is accessible",
            "Create default configuration if none exists",
            "Fix client access to configuration location",
            "Implement configuration backup and recovery"
        ]
    },
    
    482: {
        "message": "Client configuration conflict",
        "description": "Configuration conflicts with system requirements",
        "common_causes": [
            "Configuration parameters contradict each other",
            "Client config incompatible with server config",
            "Hardware limitations conflict with config",
            "Network settings conflict with requirements"
        ],
        "solutions": [
            "Resolve conflicting configuration parameters",
            "Align client config with server requirements",
            "Adjust config to match hardware capabilities",
            "Fix network configuration conflicts",
            "Use configuration validation to detect conflicts"
        ]
    },
    
    483: {
        "message": "Client configuration update failed",
        "description": "Unable to update client configuration",
        "common_causes": [
            "Client unable to write configuration changes",
            "Configuration service unavailable for updates",
            "Permission issues preventing config updates",
            "Configuration validation failed for updates"
        ],
        "solutions": [
            "Ensure client has write access to config files",
            "Verify configuration service is available",
            "Fix permissions for configuration updates",
            "Validate configuration before applying updates",
            "Use configuration management tools for updates"
        ]
    },
    
    484: {
        "message": "Client settings error",
        "description": "Error in client application settings",
        "common_causes": [
            "Application settings corrupted",
            "Settings incompatible with current version",
            "User settings conflict with system settings",
            "Settings storage issues"
        ],
        "solutions": [
            "Reset application settings to defaults",
            "Update settings for current application version",
            "Resolve conflicts between user and system settings",
            "Fix settings storage and access issues",
            "Implement settings validation and repair"
        ]
    },
    
    485: {
        "message": "Client capability mismatch",
        "description": "Client capabilities don't match system requirements",
        "common_causes": [
            "Client hardware insufficient for requirements",
            "Client software features missing",
            "Client version too old for required capabilities",
            "Client configuration disabling needed features"
        ],
        "solutions": [
            "Upgrade client hardware to meet requirements",
            "Update client software to add missing features",
            "Upgrade client to version with required capabilities",
            "Enable required features in client configuration",
            "Use alternative configuration matching capabilities"
        ]
    },
    
    486: {
        "message": "Client resolution error",
        "description": "Client display resolution configuration error",
        "common_causes": [
            "Resolution not supported by client display",
            "Resolution configuration invalid or corrupted",
            "Graphics hardware unable to support resolution",
            "Resolution incompatible with streaming format"
        ],
        "solutions": [
            "Use resolution supported by client display",
            "Fix resolution configuration settings",
            "Update graphics drivers for resolution support",
            "Use compatible resolution for streaming format",
            "Test resolution compatibility before deployment"
        ]
    },
    
    487: {
        "message": "Client codec unsupported",
        "description": "Client does not support required codec",
        "common_causes": [
            "Codec not installed on client system",
            "Client hardware lacks codec support",
            "Codec version incompatible with client",
            "Codec licensing issues on client"
        ],
        "solutions": [
            "Install required codec on client system",
            "Use hardware-supported codecs for client",
            "Update codec to compatible version",
            "Resolve codec licensing issues",
            "Use alternative codec supported by client"
        ]
    },
    
    488: {
        "message": "Client profile error",
        "description": "Error in client profile or user configuration",
        "common_causes": [
            "Client profile corrupted or invalid",
            "Profile permissions incorrect",
            "Profile storage issues",
            "Profile version incompatible"
        ],
        "solutions": [
            "Restore client profile from backup",
            "Fix profile permissions and access",
            "Resolve profile storage issues",
            "Update profile to compatible version",
            "Create new profile if recovery fails"
        ]
    },
    
    489: {
        "message": "Client configuration validation failed",
        "description": "Client configuration failed validation checks",
        "common_causes": [
            "Configuration parameters outside valid ranges",
            "Required configuration fields missing",
            "Configuration format invalid",
            "Configuration dependencies not met"
        ],
        "solutions": [
            "Use valid parameter ranges in configuration",
            "Add missing required configuration fields",
            "Fix configuration format issues",
            "Resolve configuration dependencies",
            "Use configuration schema validation"
        ]
    }
}


def get_client_error_info(error_code):
    """
    Get detailed error information for a client error code
    
    Args:
        error_code (int): The client error code to look up
        
    Returns:
        dict: Error information including message, description, causes, and solutions
    """
    return CLIENT_ERROR_MESSAGES.get(error_code, {
        "message": f"Unknown client error {error_code}",
        "description": "An unrecognized error occurred in client management",
        "common_causes": ["Unknown client error condition"],
        "solutions": ["Check client logs for more details", "Contact system administrator"]
    })


def format_client_error_response(error_code, additional_context=None):
    """
    Format a standardized client error response for API endpoints
    
    Args:
        error_code (int): The client error code
        additional_context (dict): Additional context information
        
    Returns:
        dict: Formatted error response
    """
    error_info = get_client_error_info(error_code)
    response = {
        "success": False,
        "error_code": error_code,
        "error_message": error_info["message"],
        "description": error_info["description"],
        "category": "client_management"
    }
    
    if additional_context:
        response["context"] = additional_context
        
    return response


# Exception classes for different client error categories
class ClientManagementException(Exception):
    """Base exception for client management errors"""
    def __init__(self, error_code, message=None, context=None):
        self.error_code = error_code
        self.context = context or {}
        
        if message is None:
            error_info = get_client_error_info(error_code)
            message = error_info["message"]
            
        super().__init__(message)


class ClientRegistrationException(ClientManagementException):
    """Exception for client registration errors (400-419)"""
    pass


class ClientAssignmentException(ClientManagementException):
    """Exception for client assignment errors (420-439)"""
    pass


class ClientConnectionException(ClientManagementException):
    """Exception for client connection errors (440-459)"""
    pass


class ClientMonitoringException(ClientManagementException):
    """Exception for client status and monitoring errors (460-479)"""
    pass


class ClientConfigurationException(ClientManagementException):
    """Exception for client configuration errors (480-499)"""
    pass