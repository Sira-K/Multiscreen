# System-Wide Error Codes (5xx)
# Multi-Screen SRT Streaming System - System-Wide Errors

class SystemError:
    """System-wide error codes"""
    
    # General System Errors (500-519)
    SYSTEM_INITIALIZATION_FAILED = 500
    SYSTEM_CONFIGURATION_ERROR = 501
    SYSTEM_RESOURCE_EXHAUSTED = 502
    SYSTEM_PERMISSION_DENIED = 503
    SYSTEM_SERVICE_UNAVAILABLE = 504
    SYSTEM_TIMEOUT = 505
    SYSTEM_INTERNAL_ERROR = 506
    SYSTEM_MAINTENANCE_MODE = 507
    SYSTEM_CAPACITY_EXCEEDED = 508
    SYSTEM_INCOMPATIBLE_VERSION = 509
    
    # Database Errors (520-539)
    DATABASE_CONNECTION_FAILED = 520
    DATABASE_QUERY_FAILED = 521
    DATABASE_TRANSACTION_FAILED = 522
    DATABASE_CORRUPTION = 523
    DATABASE_DISK_FULL = 524
    DATABASE_PERMISSION_DENIED = 525
    DATABASE_TIMEOUT = 526
    DATABASE_SCHEMA_MISMATCH = 527
    DATABASE_BACKUP_FAILED = 528
    DATABASE_RESTORE_FAILED = 529
    
    # Network Errors (540-559)
    NETWORK_INTERFACE_ERROR = 540
    NETWORK_ROUTING_ERROR = 541
    NETWORK_DNS_RESOLUTION_FAILED = 542
    NETWORK_FIREWALL_BLOCKING = 543
    NETWORK_BANDWIDTH_EXHAUSTED = 544
    NETWORK_LATENCY_TOO_HIGH = 545
    NETWORK_PACKET_LOSS = 546
    NETWORK_PORT_UNAVAILABLE = 547
    NETWORK_SSL_ERROR = 548
    NETWORK_PROXY_ERROR = 549
    
    # Security Errors (560-579)
    SECURITY_AUTHENTICATION_FAILED = 560
    SECURITY_AUTHORIZATION_DENIED = 561
    SECURITY_TOKEN_EXPIRED = 562
    SECURITY_TOKEN_INVALID = 563
    SECURITY_CERTIFICATE_INVALID = 564
    SECURITY_ENCRYPTION_ERROR = 565
    SECURITY_INTRUSION_DETECTED = 566
    SECURITY_POLICY_VIOLATION = 567
    SECURITY_AUDIT_FAILED = 568
    SECURITY_KEY_MANAGEMENT_ERROR = 569
    
    # Performance and Monitoring Errors (580-599)
    PERFORMANCE_THRESHOLD_EXCEEDED = 580
    MONITORING_SERVICE_FAILED = 581
    METRICS_COLLECTION_FAILED = 582
    ALERTING_SYSTEM_FAILED = 583
    LOG_SYSTEM_FAILED = 584
    HEALTH_CHECK_FAILED = 585
    LOAD_BALANCER_ERROR = 586
    FAILOVER_FAILED = 587
    BACKUP_SYSTEM_FAILED = 588
    RECOVERY_FAILED = 589


# Error Messages and Descriptions
SYSTEM_ERROR_MESSAGES = {
    # General System Errors (500-519)
    500: {
        "message": "System initialization failed",
        "description": "System failed to start up properly",
        "common_causes": [
            "Configuration files missing or corrupted",
            "Required services not available",
            "System dependencies not met",
            "Critical resources unavailable"
        ],
        "solutions": [
            "Check system configuration files",
            "Ensure all required services are running",
            "Verify system dependencies are installed",
            "Check system logs for initialization errors",
            "Restart system with default configuration"
        ]
    },
    
    501: {
        "message": "System configuration error",
        "description": "System configuration is invalid or corrupted",
        "common_causes": [
            "Invalid configuration file syntax",
            "Missing required configuration parameters",
            "Configuration file permissions issues",
            "Incompatible configuration values"
        ],
        "solutions": [
            "Validate configuration file syntax",
            "Add missing configuration parameters",
            "Fix file permissions for configuration",
            "Use default configuration as template",
            "Check configuration documentation"
        ]
    },
    
    502: {
        "message": "System resources exhausted",
        "description": "Critical system resources are depleted",
        "common_causes": [
            "Out of memory (RAM)",
            "CPU at 100% utilization",
            "File descriptor limits reached",
            "Thread/process limits exceeded"
        ],
        "solutions": [
            "Free up system memory",
            "Reduce CPU load or scale horizontally",
            "Increase ulimit for file descriptors",
            "Optimize resource usage in application",
            "Add more system resources"
        ]
    },
    
    503: {
        "message": "System permission denied",
        "description": "Insufficient permissions for system operation",
        "common_causes": [
            "User lacks required system permissions",
            "SELinux/AppArmor blocking operation",
            "File system permissions too restrictive",
            "Container security policies blocking access"
        ],
        "solutions": [
            "Grant necessary permissions to user",
            "Configure SELinux/AppArmor policies",
            "Fix file system permissions",
            "Adjust container security policies",
            "Run with appropriate privileges"
        ]
    },
    
    504: {
        "message": "System service unavailable",
        "description": "Critical system service is not available",
        "common_causes": [
            "Service crashed or stopped",
            "Service dependency not available",
            "Service overloaded",
            "Network connectivity lost"
        ],
        "solutions": [
            "Restart the service",
            "Check service dependencies",
            "Reduce service load",
            "Fix network connectivity",
            "Check service logs"
        ]
    },
    
    505: {
        "message": "System operation timeout",
        "description": "System operation exceeded time limit",
        "common_causes": [
            "System overload",
            "Network latency",
            "Database operations slow",
            "Resource contention"
        ],
        "solutions": [
            "Increase timeout values",
            "Reduce system load",
            "Optimize database queries",
            "Resolve resource contention",
            "Use asynchronous operations"
        ]
    },
    
    # Database Errors (520-539)
    520: {
        "message": "Database connection failed",
        "description": "Unable to establish database connection",
        "common_causes": [
            "Database server not running",
            "Network connectivity issues",
            "Invalid connection credentials",
            "Database firewall blocking"
        ],
        "solutions": [
            "Start database server",
            "Fix network connectivity",
            "Verify connection credentials",
            "Configure firewall rules",
            "Check database logs"
        ]
    },
    
    521: {
        "message": "Database query failed",
        "description": "Database query execution failed",
        "common_causes": [
            "SQL syntax error",
            "Table or column doesn't exist",
            "Data type mismatch",
            "Query timeout"
        ],
        "solutions": [
            "Fix SQL syntax",
            "Verify table/column exists",
            "Check data types",
            "Optimize query performance",
            "Increase query timeout"
        ]
    },
    
    # Network Errors (540-559)
    540: {
        "message": "Network interface error",
        "description": "Network interface malfunction",
        "common_causes": [
            "Network adapter failure",
            "Driver issues",
            "Hardware malfunction",
            "Configuration error"
        ],
        "solutions": [
            "Restart network interface",
            "Update network drivers",
            "Check hardware connections",
            "Fix network configuration",
            "Replace faulty hardware"
        ]
    },
    
    541: {
        "message": "Network routing error",
        "description": "Network routing configuration problem",
        "common_causes": [
            "Invalid routing table",
            "Gateway unreachable",
            "Routing loops",
            "Network topology changes"
        ],
        "solutions": [
            "Fix routing table",
            "Verify gateway accessibility",
            "Check routing protocols",
            "Update for topology changes",
            "Use static routes"
        ]
    },
    
    # Security Errors (560-579)
    560: {
        "message": "Authentication failed",
        "description": "User authentication unsuccessful",
        "common_causes": [
            "Invalid credentials",
            "Account locked",
            "Authentication service down",
            "Certificate issues"
        ],
        "solutions": [
            "Verify credentials",
            "Unlock account",
            "Check authentication service",
            "Fix certificate issues",
            "Reset authentication"
        ]
    },
    
    561: {
        "message": "Authorization denied",
        "description": "User lacks required permissions",
        "common_causes": [
            "Insufficient privileges",
            "Role not assigned",
            "Policy restrictions",
            "Token invalid"
        ],
        "solutions": [
            "Grant required permissions",
            "Assign appropriate role",
            "Update security policies",
            "Refresh access token",
            "Contact administrator"
        ]
    },
    
    # Performance Errors (580-599)
    580: {
        "message": "Performance threshold exceeded",
        "description": "System performance below acceptable levels",
        "common_causes": [
            "High system load",
            "Memory pressure",
            "I/O bottlenecks",
            "Network congestion"
        ],
        "solutions": [
            "Scale system resources",
            "Optimize performance",
            "Implement caching",
            "Load balancing",
            "Performance tuning"
        ]
    },
    
    585: {
        "message": "Health check failed",
        "description": "System health check unsuccessful",
        "common_causes": [
            "Service unresponsive",
            "Resource constraints",
            "Component failure",
            "Network issues"
        ],
        "solutions": [
            "Restart services",
            "Free resources",
            "Replace failed components",
            "Fix network issues",
            "Review health criteria"
        ]
    }
}


def get_system_error_info(error_code):
    """
    Get detailed error information for a system error code
    
    Args:
        error_code (int): The system error code to look up
        
    Returns:
        dict: Error information including message, description, causes, and solutions
    """
    return SYSTEM_ERROR_MESSAGES.get(error_code, {
        "message": f"Unknown system error {error_code}",
        "description": "An unrecognized system error occurred",
        "common_causes": ["Unknown system error condition"],
        "solutions": ["Check system logs for more details", "Contact system administrator"]
    })


def format_system_error_response(error_code, additional_context=None):
    """
    Format a standardized system error response for API endpoints
    
    Args:
        error_code (int): The system error code
        additional_context (dict): Additional context information
        
    Returns:
        dict: Formatted error response
    """
    error_info = get_system_error_info(error_code)
    response = {
        "success": False,
        "error_code": error_code,
        "error_message": error_info["message"],
        "description": error_info["description"],
        "category": "system"
    }
    
    if additional_context:
        response["context"] = additional_context
        
    return response


# Exception classes for different system error categories
class SystemException(Exception):
    """Base exception for system errors"""
    def __init__(self, error_code, message=None, context=None):
        self.error_code = error_code
        self.context = context or {}
        
        if message is None:
            error_info = get_system_error_info(error_code)
            message = error_info["message"]
            
        super().__init__(message)


class SystemInitException(SystemException):
    """Exception for system initialization errors (500-519)"""
    pass


class DatabaseException(SystemException):
    """Exception for database errors (520-539)"""
    pass


class NetworkException(SystemException):
    """Exception for network errors (540-559)"""
    pass


class SecurityException(SystemException):
    """Exception for security errors (560-579)"""
    pass


class PerformanceException(SystemException):
    """Exception for performance and monitoring errors (580-599)"""
    pass