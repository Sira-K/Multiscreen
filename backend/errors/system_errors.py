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
            "Database connection failed during startup",
            "Essential system dependencies missing"
        ],
        "solutions": [
            "Check configuration files for errors",
            "Ensure all required services are running",
            "Verify database connectivity and permissions",
            "Install missing system dependencies",
            "Review system logs for initialization errors"
        ]
    },
    
    501: {
        "message": "System configuration error",
        "description": "System configuration is invalid or incomplete",
        "common_causes": [
            "Configuration file syntax errors",
            "Missing required configuration parameters",
            "Configuration values outside valid ranges",
            "Conflicting configuration settings"
        ],
        "solutions": [
            "Validate configuration file syntax",
            "Add missing required configuration parameters",
            "Use valid ranges for configuration values",
            "Resolve conflicting configuration settings",
            "Use configuration validation tools"
        ]
    },
    
    502: {
        "message": "System resources exhausted",
        "description": "System has run out of critical resources",
        "common_causes": [
            "Memory exhaustion from system processes",
            "CPU overload from high system demand",
            "Disk space completely utilized",
            "Network bandwidth fully consumed"
        ],
        "solutions": [
            "Free up memory by stopping unnecessary processes",
            "Reduce CPU load or add more processing power",
            "Clean up disk space and add storage if needed",
            "Optimize network usage or increase bandwidth",
            "Monitor resource usage and set up alerts"
        ]
    },
    
    503: {
        "message": "System permission denied",
        "description": "System lacks necessary permissions for operation",
        "common_causes": [
            "Service account lacks required privileges",
            "File system permissions too restrictive",
            "Security policies preventing system operations",
            "User account not in required groups"
        ],
        "solutions": [
            "Grant required privileges to service account",
            "Adjust file system permissions appropriately",
            "Update security policies for system needs",
            "Add user account to required system groups",
            "Use elevated privileges where necessary"
        ]
    },
    
    504: {
        "message": "System service unavailable",
        "description": "Critical system service is not available",
        "common_causes": [
            "Service crashed or stopped unexpectedly",
            "Service dependency not available",
            "Service overloaded and unresponsive",
            "Network connectivity to service lost"
        ],
        "solutions": [
            "Restart crashed or stopped services",
            "Ensure service dependencies are running",
            "Reduce service load or scale up resources",
            "Fix network connectivity issues",
            "Check service health and logs"
        ]
    },
    
    505: {
        "message": "System operation timeout",
        "description": "System operation exceeded maximum allowed time",
        "common_causes": [
            "System overload causing operation delays",
            "Network latency affecting remote operations",
            "Database operations taking too long",
            "Resource contention causing bottlenecks"
        ],
        "solutions": [
            "Increase timeout values for operations",
            "Reduce system load to improve performance",
            "Optimize database queries and operations",
            "Resolve resource contention issues",
            "Use asynchronous operations where possible"
        ]
    },
    
    506: {
        "message": "System internal error",
        "description": "Unexpected internal system error occurred",
        "common_causes": [
            "Software bug or logic error",
            "Unhandled exception in system code",
            "Memory corruption or data structure issues",
            "Race condition or concurrency problems"
        ],
        "solutions": [
            "Check system logs for detailed error information",
            "Report bug to system developers",
            "Restart affected system components",
            "Update system software to latest version",
            "Implement additional error handling"
        ]
    },
    
    507: {
        "message": "System in maintenance mode",
        "description": "System is currently in maintenance mode",
        "common_causes": [
            "Scheduled maintenance window active",
            "System updates being applied",
            "Emergency maintenance required",
            "System administrator initiated maintenance"
        ],
        "solutions": [
            "Wait for maintenance window to complete",
            "Check maintenance schedule and notifications",
            "Contact administrator for emergency access",
            "Use alternative systems during maintenance",
            "Plan operations outside maintenance windows"
        ]
    },
    
    508: {
        "message": "System capacity exceeded",
        "description": "System has reached maximum operational capacity",
        "common_causes": [
            "User or connection limits reached",
            "Processing capacity fully utilized",
            "Storage capacity limits exceeded",
            "License limits preventing expansion"
        ],
        "solutions": [
            "Increase system capacity limits",
            "Add more processing or storage resources",
            "Implement load balancing or scaling",
            "Upgrade licenses to allow higher capacity",
            "Queue or schedule operations to manage load"
        ]
    },
    
    509: {
        "message": "Incompatible system version",
        "description": "System version is incompatible with requirements",
        "common_causes": [
            "System software too old for requirements",
            "Component version mismatch",
            "API version incompatibility",
            "Database schema version mismatch"
        ],
        "solutions": [
            "Update system to compatible version",
            "Ensure all components are compatible versions",
            "Use compatible API versions",
            "Migrate database schema to compatible version",
            "Check version compatibility before upgrades"
        ]
    },

    # Database Errors (520-539)
    520: {
        "message": "Database connection failed",
        "description": "Unable to connect to database server",
        "common_causes": [
            "Database server not running",
            "Network connectivity to database lost",
            "Invalid database credentials",
            "Connection pool exhausted"
        ],
        "solutions": [
            "Start database server if stopped",
            "Check network connectivity to database",
            "Verify database credentials are correct",
            "Increase connection pool size",
            "Check database server logs for errors"
        ]
    },
    
    521: {
        "message": "Database query failed",
        "description": "Database query execution failed",
        "common_causes": [
            "SQL syntax errors in query",
            "Database table or column doesn't exist",
            "Database constraints violated",
            "Query timeout due to complexity"
        ],
        "solutions": [
            "Fix SQL syntax errors in queries",
            "Verify database schema and table structure",
            "Resolve constraint violations in data",
            "Optimize queries for better performance",
            "Increase query timeout values if needed"
        ]
    },
    
    522: {
        "message": "Database transaction failed",
        "description": "Database transaction could not be completed",
        "common_causes": [
            "Transaction deadlock occurred",
            "Transaction timeout exceeded",
            "Constraint violations during transaction",
            "Database connection lost during transaction"
        ],
        "solutions": [
            "Implement deadlock detection and retry",
            "Increase transaction timeout values",
            "Fix data to resolve constraint violations",
            "Handle connection loss with transaction retry",
            "Optimize transaction logic for efficiency"
        ]
    },
    
    523: {
        "message": "Database corruption detected",
        "description": "Database data or structure is corrupted",
        "common_causes": [
            "Hardware failure affecting database storage",
            "Improper database shutdown",
            "File system corruption",
            "Software bug corrupting database"
        ],
        "solutions": [
            "Restore database from backup",
            "Run database repair and consistency checks",
            "Check and repair underlying file system",
            "Replace failing hardware if detected",
            "Update database software to fix bugs"
        ]
    },
    
    524: {
        "message": "Database disk full",
        "description": "Database storage is full",
        "common_causes": [
            "Database files grew beyond available space",
            "Transaction logs not being truncated",
            "Backup files consuming disk space",
            "Temporary files not being cleaned up"
        ],
        "solutions": [
            "Add more disk space for database",
            "Truncate or archive old transaction logs",
            "Move backup files to external storage",
            "Clean up temporary database files",
            "Implement database space monitoring"
        ]
    },
    
    525: {
        "message": "Database permission denied",
        "description": "Insufficient permissions for database operation",
        "common_causes": [
            "Database user lacks required privileges",
            "File system permissions prevent access",
            "Database security policies blocking operation",
            "User not granted access to specific tables"
        ],
        "solutions": [
            "Grant required privileges to database user",
            "Fix file system permissions for database files",
            "Update database security policies",
            "Grant user access to required tables",
            "Use database administrator account if needed"
        ]
    },
    
    526: {
        "message": "Database operation timeout",
        "description": "Database operation exceeded time limit",
        "common_causes": [
            "Complex query taking too long to execute",
            "Database locked by other operations",
            "Insufficient database resources",
            "Network latency to database server"
        ],
        "solutions": [
            "Optimize queries for better performance",
            "Reduce database locking conflicts",
            "Add more database resources",
            "Improve network connectivity to database",
            "Increase timeout values for operations"
        ]
    },
    
    527: {
        "message": "Database schema mismatch",
        "description": "Database schema doesn't match expected version",
        "common_causes": [
            "Database migration not applied",
            "Schema version mismatch between components",
            "Manual schema changes not synchronized",
            "Database restore from wrong version"
        ],
        "solutions": [
            "Run database migration scripts",
            "Synchronize schema versions across components",
            "Apply missing schema changes",
            "Restore database from correct version backup",
            "Use database version control tools"
        ]
    },
    
    528: {
        "message": "Database backup failed",
        "description": "Unable to create database backup",
        "common_causes": [
            "Insufficient disk space for backup",
            "Backup destination not accessible",
            "Database locked during backup attempt",
            "Backup tool configuration errors"
        ],
        "solutions": [
            "Ensure adequate disk space for backup",
            "Verify backup destination accessibility",
            "Schedule backup during low activity periods",
            "Fix backup tool configuration",
            "Use online backup methods if available"
        ]
    },
    
    529: {
        "message": "Database restore failed",
        "description": "Unable to restore database from backup",
        "common_causes": [
            "Backup file corrupted or invalid",
            "Insufficient permissions for restore",
            "Database schema incompatibility",
            "Restore interrupted by system issues"
        ],
        "solutions": [
            "Verify backup file integrity",
            "Ensure adequate permissions for restore",
            "Use compatible backup version for restore",
            "Complete restore without interruption",
            "Test backup files regularly"
        ]
    },

    # Network Errors (540-559)
    540: {
        "message": "Network interface error",
        "description": "Network interface malfunction or configuration error",
        "common_causes": [
            "Network interface hardware failure",
            "Network driver issues",
            "Interface configuration errors",
            "Cable or physical connection problems"
        ],
        "solutions": [
            "Check network interface hardware",
            "Update or reinstall network drivers",
            "Fix network interface configuration",
            "Check and replace network cables",
            "Test with alternative network interface"
        ]
    },
    
    541: {
        "message": "Network routing error",
        "description": "Network routing configuration or operation failed",
        "common_causes": [
            "Routing table misconfiguration",
            "Network gateway unreachable",
            "Routing protocol failures",
            "Network topology changes"
        ],
        "solutions": [
            "Fix routing table configuration",
            "Verify network gateway accessibility",
            "Check routing protocol configuration",
            "Update routing for topology changes",
            "Use static routes as fallback"
        ]
    },
    
    542: {
        "message": "DNS resolution failed",
        "description": "Unable to resolve domain names to IP addresses",
        "common_causes": [
            "DNS server unavailable or unreachable",
            "DNS configuration errors",
            "Network connectivity to DNS servers lost",
            "DNS cache corruption"
        ],
        "solutions": [
            "Check DNS server availability",
            "Fix DNS configuration settings",
            "Verify network connectivity to DNS servers",
            "Clear and rebuild DNS cache",
            "Use alternative DNS servers"
        ]
    },
    
    543: {
        "message": "Firewall blocking network access",
        "description": "Firewall rules are blocking required network access",
        "common_causes": [
            "Firewall rules too restrictive",
            "Required ports not opened in firewall",
            "Application not allowed through firewall",
            "Firewall configuration errors"
        ],
        "solutions": [
            "Review and adjust firewall rules",
            "Open required ports in firewall",
            "Add application to firewall exceptions",
            "Fix firewall configuration errors",
            "Test network access after firewall changes"
        ]
    },
    
    544: {
        "message": "Network bandwidth exhausted",
        "description": "Available network bandwidth is fully utilized",
        "common_causes": [
            "High network traffic consuming bandwidth",
            "Multiple applications competing for bandwidth",
            "Network capacity insufficient for demand",
            "Network congestion from external sources"
        ],
        "solutions": [
            "Implement Quality of Service (QoS) policies",
            "Increase network bandwidth capacity",
            "Optimize applications for bandwidth efficiency",
            "Schedule high-bandwidth operations",
            "Monitor and manage network traffic"
        ]
    },
    
    545: {
        "message": "Network latency too high",
        "description": "Network latency exceeds acceptable thresholds",
        "common_causes": [
            "Physical distance