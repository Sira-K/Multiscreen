# Docker Management Error Codes (2xx)
# Multi-Screen SRT Streaming System - Docker Management Module

class DockerError:
    """Docker management error codes"""
    
    # Docker Service Errors (200-219)
    DOCKER_SERVICE_NOT_RUNNING = 200
    DOCKER_DAEMON_CONNECTION_FAILED = 201
    DOCKER_PERMISSION_DENIED = 202
    DOCKER_SERVICE_TIMEOUT = 203
    DOCKER_VERSION_INCOMPATIBLE = 204
    DOCKER_RESOURCE_EXHAUSTED = 205
    DOCKER_NETWORK_ERROR = 206
    DOCKER_STORAGE_ERROR = 207
    DOCKER_SERVICE_UNAVAILABLE = 208
    DOCKER_API_ERROR = 209
    
    # Container Lifecycle Errors (220-239)
    CONTAINER_CREATE_FAILED = 220
    CONTAINER_START_FAILED = 221
    CONTAINER_STOP_FAILED = 222
    CONTAINER_REMOVE_FAILED = 223
    CONTAINER_NOT_FOUND = 224
    CONTAINER_ALREADY_EXISTS = 225
    CONTAINER_STATE_INVALID = 226
    CONTAINER_EXIT_ERROR = 227
    CONTAINER_RESTART_FAILED = 228
    CONTAINER_TIMEOUT = 229
    
    # Image Management Errors (240-259)
    IMAGE_NOT_FOUND = 240
    IMAGE_PULL_FAILED = 241
    IMAGE_PUSH_FAILED = 242
    IMAGE_BUILD_FAILED = 243
    IMAGE_TAG_INVALID = 244
    IMAGE_REGISTRY_ERROR = 245
    IMAGE_SIZE_TOO_LARGE = 246
    IMAGE_CORRUPTED = 247
    IMAGE_AUTHENTICATION_FAILED = 248
    IMAGE_DISK_SPACE_ERROR = 249
    
    # Port Management Errors (260-279)
    PORT_ALREADY_IN_USE = 260
    PORT_MAPPING_FAILED = 261
    PORT_RANGE_EXHAUSTED = 262
    PORT_INVALID = 263
    PORT_PERMISSION_DENIED = 264
    PORT_FIREWALL_BLOCKED = 265
    PORT_CONFLICT = 266
    PORT_ALLOCATION_FAILED = 267
    PORT_BINDING_ERROR = 268
    PORT_UNAVAILABLE = 269
    
    # Volume and Mount Errors (280-299)
    VOLUME_CREATE_FAILED = 280
    VOLUME_MOUNT_FAILED = 281
    VOLUME_NOT_FOUND = 282
    VOLUME_PERMISSION_DENIED = 283
    VOLUME_DISK_FULL = 284
    VOLUME_PATH_INVALID = 285
    VOLUME_IN_USE = 286
    VOLUME_CORRUPTED = 287
    VOLUME_DRIVER_ERROR = 288
    VOLUME_BACKUP_FAILED = 289


# Error Messages and Descriptions
DOCKER_ERROR_MESSAGES = {
    # Docker Service Errors (200-219)
    200: {
        "message": "Docker service is not running",
        "description": "The Docker daemon is not active or accessible",
        "common_causes": [
            "Docker daemon not started",
            "Docker service stopped or crashed",
            "System boot sequence incomplete",
            "Docker installation incomplete"
        ],
        "solutions": [
            "Start Docker service: 'sudo systemctl start docker'",
            "Enable Docker on boot: 'sudo systemctl enable docker'",
            "Check Docker status: 'sudo systemctl status docker'",
            "Restart Docker service: 'sudo systemctl restart docker'",
            "Verify Docker installation is complete"
        ]
    },
    
    201: {
        "message": "Failed to connect to Docker daemon",
        "description": "Cannot establish connection to Docker daemon",
        "common_causes": [
            "Docker daemon not listening on expected socket",
            "Permission issues accessing Docker socket",
            "Docker daemon crashed or hung",
            "Firewall blocking Docker API access"
        ],
        "solutions": [
            "Check Docker daemon status and restart if needed",
            "Add user to docker group: 'sudo usermod -aG docker $USER'",
            "Verify Docker socket permissions: 'ls -la /var/run/docker.sock'",
            "Check if Docker API is accessible: 'docker version'",
            "Restart Docker daemon: 'sudo systemctl restart docker'"
        ]
    },
    
    202: {
        "message": "Docker permission denied",
        "description": "Insufficient permissions to execute Docker operations",
        "common_causes": [
            "User not in docker group",
            "Docker socket has restrictive permissions",
            "SELinux or AppArmor blocking access",
            "Running as non-root without proper setup"
        ],
        "solutions": [
            "Add user to docker group: 'sudo usermod -aG docker $USER'",
            "Log out and back in to refresh group membership",
            "Run with sudo if necessary: 'sudo docker ...'",
            "Check SELinux/AppArmor policies for Docker",
            "Verify Docker socket permissions are correct"
        ]
    },
    
    203: {
        "message": "Docker operation timeout",
        "description": "Docker operation exceeded maximum allowed time",
        "common_causes": [
            "System under heavy load",
            "Large image operations taking too long",
            "Network connectivity issues",
            "Resource constraints causing delays"
        ],
        "solutions": [
            "Increase timeout values in configuration",
            "Reduce system load and free resources",
            "Check network connectivity for image operations",
            "Break large operations into smaller steps",
            "Monitor system resource usage during operations"
        ]
    },
    
    204: {
        "message": "Docker version incompatible",
        "description": "Docker version does not support required features",
        "common_causes": [
            "Docker version too old for required features",
            "API version mismatch",
            "Deprecated features being used",
            "Client/server version mismatch"
        ],
        "solutions": [
            "Update Docker to latest stable version",
            "Check Docker version compatibility: 'docker version'",
            "Update Docker Compose if using older version",
            "Use compatible API version in scripts",
            "Review feature requirements vs Docker version"
        ]
    },
    
    205: {
        "message": "Docker resources exhausted",
        "description": "System resources insufficient for Docker operation",
        "common_causes": [
            "Insufficient memory for container operations",
            "CPU resources fully utilized",
            "Disk space exhausted",
            "Too many running containers"
        ],
        "solutions": [
            "Free up system memory by stopping unused containers",
            "Reduce CPU load by limiting concurrent operations",
            "Clean up disk space and unused images",
            "Implement resource limits for containers",
            "Monitor system resources: 'docker system df'"
        ]
    },
    
    206: {
        "message": "Docker network error",
        "description": "Docker networking configuration or operation failed",
        "common_causes": [
            "Network bridge configuration issues",
            "IP address conflicts",
            "Firewall blocking Docker networks",
            "Network driver problems"
        ],
        "solutions": [
            "Restart Docker networking: 'sudo systemctl restart docker'",
            "Check network configuration: 'docker network ls'",
            "Resolve IP address conflicts",
            "Configure firewall rules for Docker networks",
            "Reset Docker networks if corrupted"
        ]
    },
    
    207: {
        "message": "Docker storage error",
        "description": "Docker storage driver or filesystem error",
        "common_causes": [
            "Storage driver malfunction",
            "Filesystem corruption",
            "Insufficient disk space",
            "Storage device failures"
        ],
        "solutions": [
            "Check disk space: 'df -h'",
            "Clean up Docker storage: 'docker system prune'",
            "Check filesystem health: 'fsck'",
            "Verify storage device health",
            "Consider changing storage driver if persistent"
        ]
    },
    
    208: {
        "message": "Docker service unavailable",
        "description": "Docker service is temporarily unavailable",
        "common_causes": [
            "Docker daemon restarting",
            "System maintenance mode",
            "Resource limitations causing temporary unavailability",
            "Dependency service failures"
        ],
        "solutions": [
            "Wait for Docker service to become available",
            "Check system maintenance schedules",
            "Monitor system resource usage",
            "Verify all Docker dependencies are running",
            "Restart Docker service if hung"
        ]
    },
    
    209: {
        "message": "Docker API error",
        "description": "Docker API returned an unexpected error",
        "common_causes": [
            "Docker API bug or malfunction",
            "Invalid API request format",
            "API version compatibility issues",
            "Docker daemon internal error"
        ],
        "solutions": [
            "Check Docker daemon logs for detailed errors",
            "Verify API request format and parameters",
            "Update Docker to fix known API bugs",
            "Use alternative API endpoints if available",
            "Report bug to Docker if reproducible"
        ]
    },

    # Container Lifecycle Errors (220-239)
    220: {
        "message": "Container creation failed",
        "description": "Unable to create new Docker container",
        "common_causes": [
            "Invalid container configuration",
            "Image not found or corrupted",
            "Resource limits exceeded",
            "Name conflicts with existing container"
        ],
        "solutions": [
            "Verify container configuration parameters",
            "Ensure required image is available locally",
            "Check system resource availability",
            "Use unique container names",
            "Remove conflicting containers if safe"
        ]
    },
    
    221: {
        "message": "Container start failed",
        "description": "Container exists but failed to start",
        "common_causes": [
            "Application inside container failed to start",
            "Port conflicts preventing startup",
            "Volume mount failures",
            "Resource constraints at startup"
        ],
        "solutions": [
            "Check container logs: 'docker logs <container>'",
            "Resolve port conflicts with other containers",
            "Verify volume mounts are accessible",
            "Ensure adequate resources for container startup",
            "Fix application configuration inside container"
        ]
    },
    
    222: {
        "message": "Container stop failed",
        "description": "Unable to stop running container gracefully",
        "common_causes": [
            "Application not responding to stop signal",
            "Container in unresponsive state",
            "Process holding resources preventing stop",
            "Docker daemon communication issues"
        ],
        "solutions": [
            "Use force stop: 'docker kill <container>'",
            "Check if container process is hung",
            "Identify processes preventing shutdown",
            "Restart Docker daemon if communication fails",
            "Wait longer for graceful shutdown"
        ]
    },
    
    223: {
        "message": "Container removal failed",
        "description": "Unable to remove container from system",
        "common_causes": [
            "Container still running and not stopped",
            "Volume mounts still in use",
            "Container filesystem locked",
            "Dependencies preventing removal"
        ],
        "solutions": [
            "Stop container before removal: 'docker stop <container>'",
            "Force remove if necessary: 'docker rm -f <container>'",
            "Unmount volumes if they're preventing removal",
            "Check for processes using container filesystem",
            "Remove dependent containers first"
        ]
    },
    
    224: {
        "message": "Container not found",
        "description": "Specified container does not exist",
        "common_causes": [
            "Container name or ID incorrect",
            "Container was already removed",
            "Container created with different name",
            "Case sensitivity in container names"
        ],
        "solutions": [
            "List containers: 'docker ps -a'",
            "Verify correct container name or ID",
            "Check if container was removed or renamed",
            "Use container ID instead of name",
            "Create container if it should exist"
        ]
    },
    
    225: {
        "message": "Container with same name already exists",
        "description": "Cannot create container because name is already in use",
        "common_causes": [
            "Previous container with same name not removed",
            "Container name collision",
            "Script creating duplicate containers",
            "Container restart policies keeping old instances"
        ],
        "solutions": [
            "Remove existing container: 'docker rm <container>'",
            "Use different container name",
            "Check container restart policies",
            "Use --rm flag for temporary containers",
            "Implement container name uniqueness checks"
        ]
    },
    
    226: {
        "message": "Container in invalid state",
        "description": "Container state prevents requested operation",
        "common_causes": [
            "Attempting to start already running container",
            "Trying to stop already stopped container",
            "Container in transitional state",
            "Container filesystem corrupted"
        ],
        "solutions": [
            "Check current container state: 'docker ps -a'",
            "Wait for container to finish transitioning",
            "Force restart if container state is corrupted",
            "Remove and recreate container if filesystem corrupted",
            "Use appropriate commands for current state"
        ]
    },
    
    227: {
        "message": "Container exited with error",
        "description": "Container process terminated with non-zero exit code",
        "common_causes": [
            "Application error or crash inside container",
            "Configuration errors in containerized application",
            "Resource limits causing application failure",
            "Missing dependencies or files"
        ],
        "solutions": [
            "Check container logs: 'docker logs <container>'",
            "Fix application configuration errors",
            "Increase resource limits if needed",
            "Ensure all dependencies are available",
            "Debug application startup process"
        ]
    },
    
    228: {
        "message": "Container restart failed",
        "description": "Unable to restart container successfully",
        "common_causes": [
            "Underlying issues preventing startup",
            "Resource constraints at restart time",
            "Configuration changes breaking restart",
            "Docker daemon issues during restart"
        ],
        "solutions": [
            "Check logs for restart failure reasons",
            "Ensure adequate system resources",
            "Verify container configuration hasn't changed",
            "Try stop and start instead of restart",
            "Restart Docker daemon if needed"
        ]
    },
    
    229: {
        "message": "Container operation timeout",
        "description": "Container operation exceeded maximum allowed time",
        "common_causes": [
            "Container taking too long to start or stop",
            "Resource contention causing delays",
            "Network operations timing out",
            "Large container images causing delays"
        ],
        "solutions": [
            "Increase timeout values in configuration",
            "Reduce system load during operations",
            "Use smaller, optimized container images",
            "Check network connectivity for operations",
            "Monitor system resources during operations"
        ]
    },

    # Image Management Errors (240-259)
    240: {
        "message": "Docker image not found",
        "description": "Specified Docker image does not exist locally or in registry",
        "common_causes": [
            "Image name or tag incorrect",
            "Image not pulled from registry",
            "Registry unavailable or authentication failed",
            "Image was deleted from local storage"
        ],
        "solutions": [
            "Pull image from registry: 'docker pull <image>'",
            "Verify correct image name and tag",
            "Check registry availability and authentication",
            "List local images: 'docker images'",
            "Build image locally if it's a custom image"
        ]
    },
    
    241: {
        "message": "Docker image pull failed",
        "description": "Unable to download image from registry",
        "common_causes": [
            "Network connectivity issues",
            "Registry authentication failure",
            "Image does not exist in registry",
            "Insufficient disk space for image"
        ],
        "solutions": [
            "Check network connectivity to registry",
            "Verify registry credentials: 'docker login'",
            "Confirm image exists in registry",
            "Free up disk space: 'docker system prune'",
            "Try pulling from different registry mirror"
        ]
    },
    
    242: {
        "message": "Docker image push failed",
        "description": "Unable to upload image to registry",
        "common_causes": [
            "Registry authentication or permission issues",
            "Network upload problems",
            "Registry storage full",
            "Image too large for registry limits"
        ],
        "solutions": [
            "Verify registry write permissions",
            "Check network upload bandwidth and stability",
            "Ensure registry has adequate storage",
            "Reduce image size by optimizing layers",
            "Use registry-specific upload tools if available"
        ]
    },
    
    243: {
        "message": "Docker image build failed",
        "description": "Unable to build Docker image from Dockerfile",
        "common_causes": [
            "Dockerfile syntax errors",
            "Build context issues or missing files",
            "Base image unavailable",
            "Network issues during build steps"
        ],
        "solutions": [
            "Review Dockerfile for syntax errors",
            "Ensure all required files are in build context",
            "Verify base image is available and accessible",
            "Check network connectivity during build",
            "Use multi-stage builds to optimize image size"
        ]
    },
    
    244: {
        "message": "Invalid Docker image tag",
        "description": "Image tag format is invalid or contains illegal characters",
        "common_causes": [
            "Tag contains invalid characters",
            "Tag format doesn't follow naming conventions",
            "Tag too long for registry limits",
            "Reserved tag names being used"
        ],
        "solutions": [
            "Use valid characters in tags (a-z, 0-9, -, _, .)",
            "Follow Docker tag naming conventions",
            "Keep tag length under registry limits",
            "Avoid reserved tag names like 'latest'",
            "Use semantic versioning for tags"
        ]
    },
    
    245: {
        "message": "Docker registry error",
        "description": "Error communicating with Docker registry",
        "common_causes": [
            "Registry server unavailable",
            "Authentication or authorization failure",
            "Registry API version incompatibility",
            "Network connectivity issues"
        ],
        "solutions": [
            "Check registry server status and availability",
            "Verify authentication credentials are correct",
            "Update Docker client for registry compatibility",
            "Test network connectivity to registry",
            "Use alternative registry if primary unavailable"
        ]
    },
    
    246: {
        "message": "Docker image size too large",
        "description": "Image exceeds size limits for registry or system",
        "common_causes": [
            "Image contains unnecessary large files",
            "Multiple large layers in image",
            "Base image is too large",
            "Build artifacts not cleaned up"
        ],
        "solutions": [
            "Use multi-stage builds to reduce final image size",
            "Remove unnecessary files and dependencies",
            "Use smaller base images (alpine, scratch)",
            "Clean up build artifacts and caches",
            "Optimize layer structure to minimize size"
        ]
    },
    
    247: {
        "message": "Docker image corrupted",
        "description": "Image data is corrupted and cannot be used",
        "common_causes": [
            "Storage device errors during image operations",
            "Network corruption during image transfer",
            "Filesystem corruption affecting image storage",
            "Incomplete image pull or build"
        ],
        "solutions": [
            "Remove corrupted image: 'docker rmi <image>'",
            "Re-pull image from registry",
            "Check storage device health",
            "Verify network integrity during transfers",
            "Rebuild image from source if custom"
        ]
    },
    
    248: {
        "message": "Docker registry authentication failed",
        "description": "Cannot authenticate with Docker registry",
        "common_causes": [
            "Invalid username or password",
            "Authentication token expired",
            "Registry requires specific authentication method",
            "Network proxy interfering with auth"
        ],
        "solutions": [
            "Verify registry credentials are correct",
            "Login to registry: 'docker login <registry>'",
            "Refresh authentication tokens if expired",
            "Configure proxy settings for registry access",
            "Use registry-specific authentication methods"
        ]
    },
    
    249: {
        "message": "Insufficient disk space for Docker image",
        "description": "Not enough disk space to store or process image",
        "common_causes": [
            "Docker storage directory full",
            "Large image requiring more space than available",
            "Multiple large images consuming disk space",
            "Temporary files not cleaned up"
        ],
        "solutions": [
            "Clean up Docker storage: 'docker system prune -a'",
            "Remove unused images: 'docker image prune'",
            "Add more disk space to system",
            "Move Docker storage to larger partition",
            "Use external storage for large images"
        ]
    },

    # Port Management Errors (260-279)
    260: {
        "message": "Port already in use",
        "description": "The requested port is already bound by another process",
        "common_causes": [
            "Another container using the same port",
            "Host service running on the port",
            "Previous container not properly cleaned up",
            "Port binding conflicts in Docker compose"
        ],
        "solutions": [
            "Find process using port: 'netstat -tulpn | grep <port>'",
            "Use different port for new container",
            "Stop service or container using the port",
            "Clean up stopped containers: 'docker container prune'",
            "Configure unique port mappings for all services"
        ]
    },
    
    261: {
        "message": "Port mapping failed",
        "description": "Unable to create port mapping between host and container",
        "common_causes": [
            "Invalid port numbers or ranges",
            "Firewall blocking port access",
            "Network configuration issues",
            "Container networking mode conflicts"
        ],
        "solutions": [
            "Use valid port numbers (1-65535)",
            "Configure firewall rules for required ports",
            "Check network configuration and routing",
            "Verify container networking mode supports port mapping",
            "Test port accessibility from host"
        ]
    },
    
    262: {
        "message": "Port range exhausted",
        "description": "No available ports in specified range",
        "common_causes": [
            "All ports in range already allocated",
            "Port range too small for number of services",
            "Port allocation not properly managed",
            "System port limits reached"
        ],
        "solutions": [
            "Expand port range for allocation",
            "Clean up unused port allocations",
            "Implement better port management strategy",
            "Use dynamic port allocation where possible",
            "Monitor and track port usage"
        ]
    },
    
    263: {
        "message": "Invalid port specification",
        "description": "Port number or specification is invalid",
        "common_causes": [
            "Port number outside valid range (1-65535)",
            "Invalid port mapping syntax",
            "Reserved port numbers being used",
            "Port specification format incorrect"
        ],
        "solutions": [
            "Use port numbers between 1 and 65535",
            "Follow correct port mapping syntax (host:container)",
            "Avoid reserved port numbers (0-1023 without privileges)",
            "Validate port specifications before use",
            "Use Docker port mapping documentation as reference"
        ]
    },
    
    264: {
        "message": "Port access permission denied",
        "description": "Insufficient permissions to bind to specified port",
        "common_causes": [
            "Trying to bind to privileged port (<1024) without root",
            "User lacks permission to bind ports",
            "SELinux or security policies blocking port binding",
            "Container running without adequate privileges"
        ],
        "solutions": [
            "Use ports above 1024 for non-root containers",
            "Run container with appropriate privileges",
            "Configure SELinux policies for port binding",
            "Use --privileged flag if necessary and safe",
            "Set container capabilities for port binding"
        ]
    },
    
    265: {
        "message": "Port blocked by firewall",
        "description": "Firewall is blocking access to the specified port",
        "common_causes": [
            "Host firewall blocking incoming connections",
            "Network firewall blocking port access",
            "Docker firewall rules not properly configured",
            "Cloud provider security groups blocking port"
        ],
        "solutions": [
            "Configure host firewall to allow port access",
            "Update network firewall rules",
            "Check Docker's iptables rules",
            "Configure cloud provider security groups",
            "Test port accessibility with telnet or nc"
        ]
    },
    
    266: {
        "message": "Port configuration conflict",
        "description": "Port configuration conflicts with other services",
        "common_causes": [
            "Multiple services configured for same port",
            "Docker compose port conflicts",
            "Load balancer configuration conflicts",
            "Service discovery port conflicts"
        ],
        "solutions": [
            "Review all service port configurations",
            "Use unique ports for each service",
            "Implement port allocation management",
            "Configure load balancer port routing properly",
            "Use service discovery with dynamic ports"
        ]
    },
    
    267: {
        "message": "Port allocation failed",
        "description": "System failed to allocate requested port",
        "common_causes": [
            "System port allocation limits reached",
            "Port allocation table full",
            "Network subsystem errors",
            "Resource exhaustion affecting port allocation"
        ],
        "solutions": [
            "Check system port allocation limits",
            "Increase system network limits if possible",
            "Restart network services to clear allocation table",
            "Free up system resources",
            "Use port pooling or sharing strategies"
        ]
    },
    
    268: {
        "message": "Port binding error",
        "description": "Error occurred while binding port to container",
        "common_causes": [
            "Network interface not available",
            "IP address binding conflicts",
            "Container network namespace issues",
            "Docker network driver problems"
        ],
        "solutions": [
            "Verify network interface is up and available",
            "Check IP address conflicts and resolution",
            "Restart container to fix namespace issues",
            "Restart Docker daemon to fix network driver",
            "Use different network configuration if needed"
        ]
    },
    
    269: {
        "message": "Port unavailable",
        "description": "Requested port is not available for use",
        "common_causes": [
            "Port reserved by system or other applications",
            "Port in TIME_WAIT state from previous connections",
            "Network service occupying the port",
            "Port blocked by system policies"
        ],
        "solutions": [
            "Wait for port to become available",
            "Use different port number",
            "Check system policies blocking port access",
            "Kill processes holding port in TIME_WAIT state"
        ]
    },

    # Volume and Mount Errors (280-299)
    280: {
        "message": "Volume creation failed",
        "description": "Unable to create Docker volume",
        "common_causes": [
            "Insufficient disk space for volume",
            "Volume name conflicts with existing volume",
            "Storage driver errors",
            "Permission issues with volume storage location"
        ],
        "solutions": [
            "Check available disk space: 'df -h'",
            "Use unique volume names",
            "Verify storage driver is working properly",
            "Check permissions on Docker volume storage directory",
            "Clean up unused volumes: 'docker volume prune'"
        ]
    },
    
    281: {
        "message": "Volume mount failed",
        "description": "Unable to mount volume in container",
        "common_causes": [
            "Volume does not exist",
            "Mount path conflicts inside container",
            "Permission issues with volume data",
            "Volume driver not available"
        ],
        "solutions": [
            "Create volume before mounting: 'docker volume create <name>'",
            "Use unique mount paths inside container",
            "Fix volume data permissions",
            "Ensure volume driver is available and working",
            "Verify volume exists: 'docker volume ls'"
        ]
    },
    
    282: {
        "message": "Volume not found",
        "description": "Specified volume does not exist",
        "common_causes": [
            "Volume name incorrect or misspelled",
            "Volume was deleted or never created",
            "Volume exists in different Docker context",
            "Case sensitivity issues with volume names"
        ],
        "solutions": [
            "List available volumes: 'docker volume ls'",
            "Create volume if it should exist",
            "Verify correct volume name spelling",
            "Check Docker context if using multiple contexts",
            "Use volume inspection: 'docker volume inspect <name>'"
        ]
    },
    
    283: {
        "message": "Volume permission denied",
        "description": "Insufficient permissions to access volume",
        "common_causes": [
            "Volume data owned by different user",
            "Container user lacks access to volume data",
            "SELinux policies blocking volume access",
            "Volume mounted with incorrect permissions"
        ],
        "solutions": [
            "Fix volume data ownership and permissions",
            "Run container with appropriate user ID",
            "Configure SELinux labels for volume access",
            "Mount volume with correct permission flags",
            "Use Docker volume with proper driver options"
        ]
    },
    
    284: {
        "message": "Volume disk full",
        "description": "Volume storage location has insufficient space",
        "common_causes": [
            "Docker volume storage directory full",
            "Application writing too much data to volume",
            "Log files filling up volume space",
            "Backup files consuming volume space"
        ],
        "solutions": [
            "Clean up volume data and remove old files",
            "Add more disk space to system",
            "Implement log rotation for applications",
            "Move large files to external storage",
            "Monitor volume usage regularly"
        ]
    },
    
    285: {
        "message": "Invalid volume path",
        "description": "Volume path specification is invalid",
        "common_causes": [
            "Path contains invalid characters",
            "Relative paths used instead of absolute",
            "Path does not exist on host system",
            "Path specification format incorrect"
        ],
        "solutions": [
            "Use absolute paths for volume mounts",
            "Verify path exists on host system",
            "Follow Docker volume path syntax",
            "Create directory path if it should exist",
            "Use proper path separators for operating system"
        ]
    },
    
    286: {
        "message": "Volume in use",
        "description": "Volume is currently in use and cannot be modified",
        "common_causes": [
            "Volume mounted in running container",
            "Multiple containers using same volume",
            "Volume being backed up or processed",
            "Volume locked by system process"
        ],
        "solutions": [
            "Stop containers using the volume",
            "Wait for volume operations to complete",
            "Identify processes using volume: 'lsof +D <volume_path>'",
            "Use volume sharing strategies if multiple access needed",
            "Schedule volume operations during maintenance windows"
        ]
    },
    
    287: {
        "message": "Volume data corrupted",
        "description": "Volume data is corrupted and cannot be accessed",
        "common_causes": [
            "Storage device failures",
            "Filesystem corruption on volume",
            "Improper container shutdown corrupting data",
            "Hardware issues affecting storage"
        ],
        "solutions": [
            "Check storage device health and errors",
            "Run filesystem check on volume: 'fsck'",
            "Restore volume from backup if available",
            "Recreate volume if data can be regenerated",
            "Implement proper container shutdown procedures"
        ]
    },
    
    288: {
        "message": "Volume driver error",
        "description": "Volume driver encountered an error",
        "common_causes": [
            "Volume driver not properly installed",
            "Driver configuration errors",
            "Driver compatibility issues with Docker version",
            "Network storage driver connection problems"
        ],
        "solutions": [
            "Verify volume driver installation and configuration",
            "Update volume driver to compatible version",
            "Check driver documentation for configuration requirements",
            "Test driver functionality independently",
            "Use alternative volume driver if needed"
        ]
    },
    
    289: {
        "message": "Volume backup failed",
        "description": "Unable to backup volume data",
        "common_causes": [
            "Insufficient space for backup storage",
            "Backup destination not accessible",
            "Volume data locked during backup",
            "Backup tool configuration errors"
        ],
        "solutions": [
            "Ensure adequate space for backup storage",
            "Verify backup destination is accessible",
            "Stop containers before backing up volumes",
            "Fix backup tool configuration",
            "Use volume snapshots if storage supports them"
        ]
    }
}


def get_docker_error_info(error_code):
    """
    Get detailed error information for a Docker error code
    
    Args:
        error_code (int): The Docker error code to look up
        
    Returns:
        dict: Error information including message, description, causes, and solutions
    """
    return DOCKER_ERROR_MESSAGES.get(error_code, {
        "message": f"Unknown Docker error {error_code}",
        "description": "An unrecognized error occurred in Docker management",
        "common_causes": ["Unknown Docker error condition"],
        "solutions": ["Check Docker logs for more details", "Contact system administrator"]
    })


def format_docker_error_response(error_code, additional_context=None):
    """
    Format a standardized Docker error response for API endpoints
    
    Args:
        error_code (int): The Docker error code
        additional_context (dict): Additional context information
        
    Returns:
        dict: Formatted error response
    """
    error_info = get_docker_error_info(error_code)
    response = {
        "success": False,
        "error_code": error_code,
        "error_message": error_info["message"],
        "description": error_info["description"],
        "category": "docker_management"
    }
    
    if additional_context:
        response["context"] = additional_context
        
    return response


# Exception classes for different Docker error categories
class DockerManagementException(Exception):
    """Base exception for Docker management errors"""
    def __init__(self, error_code, message=None, context=None):
        self.error_code = error_code
        self.context = context or {}
        
        if message is None:
            error_info = get_docker_error_info(error_code)
            message = error_info["message"]
            
        super().__init__(message)


class DockerServiceException(DockerManagementException):
    """Exception for Docker service errors (200-219)"""
    pass


class ContainerLifecycleException(DockerManagementException):
    """Exception for container lifecycle errors (220-239)"""
    pass


class ImageManagementException(DockerManagementException):
    """Exception for image management errors (240-259)"""
    pass


class PortManagementException(DockerManagementException):
    """Exception for port management errors (260-279)"""
    pass


class VolumeManagementException(DockerManagementException):
    """Exception for volume and mount errors (280-299)"""
    pass