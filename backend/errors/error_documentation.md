# Multi-Screen SRT Streaming System - Error Code Documentation

This document provides comprehensive documentation for all error codes used in the Multi-Screen SRT Streaming System. The error codes are organized by module and provide detailed information about common causes and solutions.

## Error Code Structure

The error codes follow a structured format:
- **1xx**: Stream Management Errors
- **2xx**: Docker Management Errors  
- **3xx**: Video Management Errors
- **4xx**: Client Management Errors
- **5xx**: System-Wide Errors

Each error code includes:
- **Error Code**: Numeric identifier
- **Message**: Brief error description
- **Meaning**: Plain English explanation of what the error indicates
- **Common Causes**: Most frequent reasons for the error
- **Primary Solution**: Main troubleshooting step

## 1xx - Stream Management Errors

### FFmpeg Process Errors (100-119)

| Code | Message | Meaning | Common Causes | Primary Solution |
|------|---------|---------|---------------|------------------|
| 100 | FFmpeg process failed to start | FFmpeg could not be launched or initialized on the system | FFmpeg binary not found, insufficient permissions, invalid arguments | Verify FFmpeg installation: `ffmpeg -version` |
| 101 | FFmpeg process terminated unexpectedly | FFmpeg was running but suddenly stopped or crashed | Out of memory, system killed process, hardware failure | Check system memory and monitor for OOM killer |
| 102 | FFmpeg startup timeout exceeded | FFmpeg failed to start up in time before a timeout limit | Network issues, high system load, server unresponsive | Check network connectivity to SRT server |
| 103 | Invalid FFmpeg command parameters | The command line arguments passed to FFmpeg are incorrect or malformed | Incorrect paths, invalid codecs, malformed URLs | Validate all file paths and parameters |
| 104 | Input video file not found | FFmpeg cannot locate the specified input video file | File deleted/moved, permission issues, network storage down | Verify file exists and is accessible |
| 105 | FFmpeg output stream error | FFmpeg encountered an error while trying to send output to destination | Network connection lost, SRT server overloaded, disk full | Check SRT server connectivity and capacity |
| 106 | Video encoding error in FFmpeg | FFmpeg failed during the video encoding/transcoding process | Hardware encoder failed, unsupported codec, insufficient resources | Switch to software encoding or reduce complexity |
| 107 | Too many consecutive FFmpeg errors | FFmpeg has encountered multiple errors in a row and was terminated | Persistent network issues, corrupted files, system instability | Identify and fix root cause of recurring errors |
| 108 | Critical FFmpeg error detected | FFmpeg encountered a severe error that requires immediate attention | Hardware failure, resource exhaustion, software bugs | Check hardware status and system logs |
| 109 | System resources exhausted for FFmpeg | The system lacks sufficient resources to run FFmpeg properly | Insufficient RAM/CPU, I/O bottlenecks, bandwidth limits | Add resources or optimize settings |

### SRT Connection Errors (120-139)

| Code | Message | Meaning | Common Causes | Primary Solution |
|------|---------|---------|---------------|------------------|
| 120 | SRT connection refused by server | The SRT server actively rejected the connection attempt | Server not running, firewall blocking, connection limit reached | Verify SRT server status: `docker ps` |
| 121 | SRT connection timeout | The attempt to connect to the SRT server took too long and timed out | High latency, server overloaded, incorrect IP/port | Check network latency: `ping <server-ip>` |
| 122 | SRT connection reset by peer | The SRT server forcibly closed an established connection | Server restart, network interruption, protocol violation | Check SRT server logs and restart if needed |
| 123 | SRT broken pipe error | The communication channel to the SRT server was broken unexpectedly | Connection terminated, network interface down, socket errors | Check remote server status and network stability |
| 124 | No route to SRT server host | The network cannot find a path to reach the SRT server | IP unreachable, routing issues, VPN disconnected | Test connectivity: `ping <server-ip>` |
| 125 | SRT port address already in use | Another process is already using the SRT port | Multiple servers on same port, port not released | Check port usage: `netstat -tulpn \| grep <port>` |
| 126 | SRT socket error occurred | A low-level socket error occurred during SRT communication | Socket limits exceeded, interface errors, kernel issues | Check system socket limits: `ulimit -n` |
| 127 | SRT handshake failure | The initial SRT protocol negotiation between client and server failed | Version mismatch, configuration errors, network interference | Verify SRT version compatibility |
| 128 | SRT authentication error | Authentication credentials were rejected during SRT connection | Invalid credentials, auth service down, method mismatch | Verify authentication credentials |
| 129 | SRT stream not found | The requested SRT stream does not exist on the server | Incorrect stream ID, stream not started, permission denied | Check if stream is running on server |

### Stream Configuration Errors (140-159)

| Code | Message | Meaning | Common Causes | Primary Solution |
|------|---------|---------|---------------|------------------|
| 140 | Missing required stream parameters | Essential information needed to configure the stream is missing | API request incomplete, config file missing fields | Validate all required parameters are provided |
| 141 | Invalid group ID provided | The specified group identifier is not valid or doesn't exist | Group doesn't exist, typo in ID, case sensitivity | Verify group exists: use /get_groups endpoint |
| 142 | Invalid video files configuration | The video files list provided is empty, malformed, or contains invalid entries | Empty array, incorrect paths, unsupported formats | Provide valid video files with correct paths |
| 143 | Stream group not found in Docker | The specified group has no corresponding Docker container | Container not created, manually deleted, Docker service down | Create Docker container for the group |
| 144 | Stream group Docker container not running | The group's Docker container exists but is currently stopped | Container stopped, crashed, insufficient resources | Start container: `docker start <container>` |
| 145 | Stream already exists for this group | A streaming process is already active for this group | Duplicate start request, previous stream not stopped | Stop existing stream before starting new one |
| 146 | Stream configuration mismatch | The stream settings don't match the group's requirements | Video count ≠ screen count, resolution incompatible | Ensure configuration matches group requirements |
| 147 | Stream layout configuration error | The screen layout specification is invalid or unsupported | Invalid arrangement, unsupported orientation | Use supported layouts (horizontal/vertical/grid) |
| 148 | Stream resolution error | The video resolution is incompatible with the streaming requirements | Input too low, aspect ratio mismatch, not divisible | Use compatible resolutions for layout |
| 149 | Stream codec configuration error | The video codec settings are invalid or unsupported | Unsupported codec, hardware incompatible, licensing | Use H.264 codec for maximum compatibility |

### Stream Monitoring Errors (160-179)

| Code | Message | Meaning | Common Causes | Primary Solution |
|------|---------|---------|---------------|------------------|
| 160 | Stream startup timeout exceeded | The stream took longer than expected to become operational | Network latency, system overload, large files | Increase startup timeout or reduce system load |
| 161 | Stream health check failed | Monitoring detected that the stream is not functioning properly | Stream stopped, network lost, encoding issues | Check if stream is actively encoding |
| 162 | Stream performance degraded | The stream's performance metrics have fallen below acceptable levels | High CPU/memory usage, insufficient bandwidth | Reduce system load or optimize settings |
| 163 | Stream bitrate too low | The stream's bitrate has dropped below the minimum required threshold | Network congestion, adaptive algorithm, hardware throttling | Check network bandwidth and hardware temperature |
| 164 | Stream experiencing frame drops | The stream is losing video frames during transmission | Encoding can't keep up, network slow, buffer overflow | Reduce encoding complexity or increase resources |
| 165 | Stream synchronization lost | Multiple streams or audio/video have lost synchronization | Different delays, network jitter, clock drift | Implement network time protocol (NTP) |
| 166 | Stream buffer overflow | The stream buffers are full and data is being lost | Input exceeds capacity, slow transmission, insufficient memory | Increase buffer allocation or reduce input rate |
| 167 | Stream buffer underrun | The stream buffers are empty causing interruptions in playback | Input too slow, network interruptions, inadequate pre-buffering | Increase pre-buffering or fix network issues |
| 168 | Stream quality degraded | The visual quality of the stream has become unacceptably poor | Compression artifacts, reduced bitrate, conversion errors | Increase bitrate or check encoding parameters |
| 169 | Network congestion affecting stream | Network traffic is interfering with stream delivery | Bandwidth fully used, multiple streams, equipment overload | Implement QoS or reduce concurrent streams |

### Video Processing Errors (180-199)

| Code | Message | Meaning | Common Causes | Primary Solution |
|------|---------|---------|---------------|------------------|
| 180 | Video file not found at specified path | The system cannot locate the video file at the given location | Incorrect path, file deleted, permission issues | Verify file path and accessibility |
| 181 | Video file is corrupted or unreadable | The video file data is damaged and cannot be processed | Incomplete transfer, storage errors, encoding interrupted | Re-upload file or restore from backup |
| 182 | Video format not supported | The video file format is not compatible with the system | Rare format, missing codecs, DRM protection | Convert to MP4 with H.264 codec |
| 183 | Video codec not supported | The video uses a codec that the system cannot handle | Proprietary codec, missing libraries, hardware unavailable | Re-encode with standard codec |
| 184 | Video resolution invalid or unsupported | The video resolution cannot be processed by the system | Too high, non-standard, not divisible for layout | Use standard resolutions (1920x1080, etc.) |
| 185 | Video duration invalid or too short | The video length is inappropriate for streaming purposes | Too short, metadata missing, corrupted duration | Use videos >1 second duration |
| 186 | Video file permission denied | The system lacks permission to access the video file | Wrong owner, restrictive permissions, SELinux blocking | Fix permissions: `chmod 644 filename` |
| 187 | Insufficient disk space for video processing | There is not enough storage space to process the video | Disk full, large files, temp files not cleaned | Free up disk space or add storage |
| 188 | Video processing operation failed | A general error occurred during video processing | FFmpeg error, conversion failure, memory exhaustion | Check FFmpeg logs and system resources |
| 189 | Video metadata extraction failed | The system cannot read information about the video file | Corrupted metadata, unsupported format, tool failure | Use alternative metadata tools |

## 2xx - Docker Management Errors

### Docker Service Errors (200-219)

| Code | Message | Meaning | Common Causes | Primary Solution |
|------|---------|---------|---------------|------------------|
| 200 | Docker service is not running | The Docker daemon process is not active on the system | Daemon not started, crashed, incomplete installation | Start Docker: `sudo systemctl start docker` |
| 201 | Failed to connect to Docker daemon | Cannot establish communication with the Docker service | Permission issues, socket access, daemon hung | Add user to docker group: `sudo usermod -aG docker $USER` |
| 202 | Docker permission denied | The user lacks necessary permissions to use Docker commands | User not in docker group, socket permissions, SELinux | Add user to docker group and re-login |
| 203 | Docker operation timeout | A Docker operation took longer than the allowed time limit | System overload, large operations, network issues | Increase timeout values or reduce system load |
| 204 | Docker version incompatible | The Docker version doesn't support required features or APIs | Old version, API mismatch, deprecated features | Update Docker to latest stable version |
| 205 | Docker resources exhausted | Docker has consumed all available system resources | Insufficient memory/CPU, too many containers | Free up resources or limit containers |
| 206 | Docker network error | Docker's networking functionality is not working properly | Bridge issues, IP conflicts, firewall, driver problems | Restart Docker networking |
| 207 | Docker storage error | Docker's storage system encountered an error | Driver malfunction, filesystem corruption, disk full | Clean up storage: `docker system prune` |
| 208 | Docker service unavailable | Docker service is temporarily not accessible | Daemon restarting, maintenance mode, dependency failure | Wait for service or check dependencies |
| 209 | Docker API error | The Docker API returned an unexpected or invalid response | API bug, invalid request, version incompatibility | Check logs and update Docker |

### Container Lifecycle Errors (220-239)

| Code | Message | Meaning | Common Causes | Primary Solution |
|------|---------|---------|---------------|------------------|
| 220 | Container creation failed | Docker was unable to create a new container instance | Invalid config, image missing, resource limits, name conflicts | Verify configuration and image availability |
| 221 | Container start failed | The container was created but could not be started | App failed to start, port conflicts, volume issues | Check container logs: `docker logs <container>` |
| 222 | Container stop failed | Docker could not stop the running container gracefully | App not responding, hung state, communication issues | Force stop: `docker kill <container>` |
| 223 | Container removal failed | Docker could not delete the container from the system | Still running, volume mounts in use, filesystem locked | Stop container first: `docker stop <container>` |
| 224 | Container not found | Docker cannot find a container with the specified name or ID | Incorrect name/ID, already removed, different name | List containers: `docker ps -a` |
| 225 | Container with same name already exists | Cannot create container because the name is already taken | Previous container not removed, name collision | Remove existing: `docker rm <container>` |
| 226 | Container in invalid state | The container's current state prevents the requested operation | Wrong state for operation, transitional state, corrupted | Check state: `docker ps -a` |
| 227 | Container exited with error | The application inside the container crashed or failed | Application crash, config errors, resource limits | Check logs and fix application issues |
| 228 | Container restart failed | Docker could not restart the container successfully | Underlying startup issues, resource constraints | Try stop and start instead of restart |
| 229 | Container operation timeout | A container operation exceeded the maximum allowed time | Slow start/stop, resource contention, large images | Increase timeout or reduce load |

### Image Management Errors (240-259)

| Code | Message | Meaning | Common Causes | Primary Solution |
|------|---------|---------|---------------|------------------|
| 240 | Docker image not found | Docker cannot find the specified image locally or in registries | Incorrect name/tag, not pulled, registry unavailable | Pull image: `docker pull <image>` |
| 241 | Docker image pull failed | Docker could not download the image from a registry | Network issues, auth failure, image doesn't exist | Check network and registry credentials |
| 242 | Docker image push failed | Docker could not upload the image to a registry | Auth/permission issues, network problems, registry full | Verify registry write permissions |
| 243 | Docker image build failed | Docker could not build an image from a Dockerfile | Dockerfile errors, missing files, base image unavailable | Review Dockerfile for syntax errors |
| 244 | Invalid Docker image tag | The image tag format contains invalid characters or structure | Invalid characters, wrong format, too long | Use valid characters (a-z, 0-9, -, _, .) |
| 245 | Docker registry error | There was an error communicating with the Docker registry | Server unavailable, auth failure, API incompatibility | Check registry server status |
| 246 | Docker image size too large | The image exceeds size limits for storage or transfer | Unnecessary files, multiple layers, large base image | Use multi-stage builds to reduce size |
| 247 | Docker image corrupted | The image data is damaged and cannot be used | Storage errors, network corruption, incomplete pull | Remove and re-pull image |
| 248 | Docker registry authentication failed | Could not authenticate with the Docker registry | Invalid credentials, expired token, wrong auth method | Login: `docker login <registry>` |
| 249 | Insufficient disk space for Docker image | Not enough storage space to download or store the image | Storage full, large images consuming space | Clean up: `docker system prune -a` |

### Port Management Errors (260-279)

| Code | Message | Meaning | Common Causes | Primary Solution |
|------|---------|---------|---------------|------------------|
| 260 | Port already in use | Another process is currently using the requested port | Another container/service using port, not cleaned up | Find process: `netstat -tulpn \| grep <port>` |
| 261 | Port mapping failed | Docker could not create the port mapping between host and container | Invalid ports, firewall, network config, mode conflicts | Use valid port numbers and check firewall |
| 262 | Port range exhausted | All ports in the specified range are already allocated | All ports allocated, range too small, not managed | Expand port range or clean up allocations |
| 263 | Invalid port specification | The port number or mapping format is incorrect | Outside valid range, wrong syntax, reserved ports | Use ports 1-65535 with correct syntax |
| 264 | Port access permission denied | The user lacks permission to bind to the specified port | Privileged port without root, security policies | Use ports >1024 or run with privileges |
| 265 | Port blocked by firewall | Firewall rules are preventing access to the port | Host/network firewall, security policies | Configure firewall to allow port |
| 266 | Port configuration conflict | Multiple services are trying to use the same port | Multiple services on same port, compose conflicts | Use unique ports for each service |
| 267 | Port allocation failed | The system could not allocate the requested port | System limits, allocation table full, network errors | Check system limits and restart networking |
| 268 | Port binding error | An error occurred while binding the port to the container | Interface unavailable, IP conflicts, namespace issues | Verify network interface availability |
| 269 | Port unavailable | The requested port is not available for use | Reserved, TIME_WAIT state, blocked by policies | Wait or use different port |

### Volume and Mount Errors (280-299)

| Code | Message | Meaning | Common Causes | Primary Solution |
|------|---------|---------|---------------|------------------|
| 280 | Volume creation failed | Docker could not create the requested volume | Disk full, name conflicts, storage driver errors | Check disk space and use unique names |
| 281 | Volume mount failed | Docker could not mount the volume inside the container | Volume missing, path conflicts, permission issues | Create volume: `docker volume create <n>` |
| 282 | Volume not found | Docker cannot find a volume with the specified name | Incorrect name, deleted, different context | List volumes: `docker volume ls` |
| 283 | Volume permission denied | The container cannot access the volume due to permission restrictions | Wrong ownership, container user lacks access | Fix volume data ownership and permissions |
| 284 | Volume disk full | The storage location for the volume has no free space | Storage full, logs filling space, backups consuming | Clean up volume data and add storage |
| 285 | Invalid volume path | The volume path specification contains errors or invalid characters | Invalid characters, relative paths, doesn't exist | Use absolute paths with valid characters |
| 286 | Volume in use | The volume is currently being used and cannot be modified | Mounted in running container, locked by process | Stop containers using volume |
| 287 | Volume data corrupted | The data stored in the volume is corrupted or damaged | Storage device failure, filesystem corruption | Run filesystem check or restore from backup |
| 288 | Volume driver error | The storage driver for the volume encountered an error | Driver not installed, config errors, network storage issues | Verify driver installation and configuration |
| 289 | Volume backup failed | The volume backup operation was unsuccessful | Insufficient space, destination inaccessible, tool errors | Ensure backup destination space and access |

## 3xx - Video Management Errors

### File Upload Errors (300-319)

| Code | Message | Meaning | Common Causes | Primary Solution |
|------|---------|---------|---------------|------------------|
| 300 | No files provided for upload | The upload request was submitted without any files attached | Empty file input, JavaScript issues, network interruption | Ensure files are selected before upload |
| 301 | Invalid file provided for upload | The uploaded file is not a valid video file format | Non-video file, wrong extension, corrupted header | Upload only video files (MP4, AVI, MOV) |
| 302 | Uploaded file exceeds size limit | The video file is larger than the maximum allowed upload size | File too large, high resolution, uncompressed | Compress video or increase server limits |
| 303 | Insufficient disk space for upload | The server does not have enough storage space to accept the upload | Server disk full, temp directory full, multiple uploads | Free up disk space or add storage |
| 304 | Upload permission denied | The system lacks permission to write the uploaded file to storage | Directory permissions, web server user, SELinux blocking | Fix upload directory permissions |
| 305 | Uploaded file format not supported | The video file format cannot be processed by the system | Rare format, proprietary codec, DRM protection | Convert to MP4 with H.264 codec |
| 306 | Uploaded file is corrupted | The video file data is damaged and cannot be processed | Network interruption, source corrupted, storage errors | Re-upload with stable connection |
| 307 | File upload timeout | The upload process took longer than the maximum allowed time | Large file, slow network, server busy | Increase timeout or use faster connection |
| 308 | Upload quota exceeded | The upload would exceed storage quota limits for the user or system | User quota full, system limits, daily limits | Delete old files or request quota increase |
| 309 | Virus or malware detected in upload | Security scanning found threats in the uploaded file | Infected file, false positive, suspicious content | Scan with updated antivirus before upload |

### File Validation Errors (320-339)

| Code | Message | Meaning | Common Causes | Primary Solution |
|------|---------|---------|---------------|------------------|
| 320 | Video codec not supported or invalid | The video uses a codec that cannot be processed by the system | Proprietary codec, missing libraries, corrupted info | Convert to H.264 or H.265 codec |
| 321 | Video resolution invalid or unsupported | The video resolution is incompatible with system requirements | Too high, non-standard, incompatible with layout | Use standard resolutions (1920x1080, 1280x720) |
| 322 | Video framerate invalid or unsupported | The video framerate cannot be handled by the streaming system | Too high, variable framerate, non-standard values | Use standard framerates (24, 25, 30, 60 fps) |
| 323 | Video duration invalid | The video length is inappropriate for streaming purposes | Too short, metadata missing, zero duration | Use videos with adequate duration (>5 seconds) |
| 324 | Video bitrate invalid | The video bitrate is outside acceptable parameters | Too high/low, variable bitrate, corrupted info | Use appropriate bitrate for quality/bandwidth |
| 325 | Video aspect ratio invalid | The video aspect ratio is incompatible with the display layout | Non-standard ratio, incompatible with layout | Use standard aspect ratios (16:9, 4:3) |
| 326 | Video format not supported | The video container format cannot be processed | Proprietary container, DRM protection, corrupted headers | Convert to MP4 or other supported format |
| 327 | Video metadata missing or incomplete | Essential information about the video file is not available | Missing headers, corruption, raw video | Re-encode to add proper metadata |
| 328 | Video header corrupted | The video file header contains invalid or damaged information | Transfer corruption, storage errors, incomplete writing | Re-upload or use video repair tools |
| 329 | Video stream structure invalid | The internal structure of the video file is malformed | Multiple streams, corrupted index, sync issues | Re-encode with single video stream |

### File Management Errors (340-359)

| Code | Message | Meaning | Common Causes | Primary Solution |
|------|---------|---------|---------------|------------------|
| 340 | Video file not found | The system cannot locate the video file at the specified location | Incorrect path, file deleted, permission issues | Verify file path and accessibility |
| 341 | Access denied to video file | The system lacks permission to read or access the video file | Restrictive permissions, user lacks access, SELinux | Fix file permissions: `chmod 644 filename` |
| 342 | Video file already exists | Cannot create the file because one with the same name already exists | Duplicate creation, naming conflict, race condition | Use unique filenames with timestamps |
| 343 | Video file currently in use | The file is locked by another process and cannot be modified | Being processed, player open, streaming active | Wait for other processes to finish |
| 344 | Video file corrupted | The video file data has been damaged and cannot be used | Storage errors, incomplete transfer, power failure | Restore from backup or re-create file |
| 345 | Video file size mismatch | The actual file size doesn't match the expected or reported size | Incomplete transfer, truncation, metadata incorrect | Re-transfer file completely |
| 346 | Video file move operation failed | The system could not move the file to the destination location | Destination missing, permissions, cross-device move | Create destination and fix permissions |
| 347 | Video file deletion failed | The system could not remove the video file from storage | File in use, permissions, filesystem errors | Stop processes using file before deletion |
| 348 | Video file copy operation failed | The system could not create a copy of the video file | Space insufficient, permissions, I/O errors | Ensure adequate space and permissions |
| 349 | Video file rename operation failed | The system could not change the name of the video file | Name conflicts, invalid characters, permissions | Use unique, valid filenames |

### Processing Errors (360-379)

| Code | Message | Meaning | Common Causes | Primary Solution |
|------|---------|---------|---------------|------------------|
| 360 | Video processing operation failed | A general error occurred during video processing operations | Tool errors, invalid parameters, resource exhaustion | Check processing tool logs and system resources |
| 361 | Video processing timeout | The processing operation took longer than the maximum allowed time | Large files, system overload, inefficient parameters | Increase timeout or reduce system load |
| 362 | Insufficient memory for video processing | The system ran out of RAM while processing the video | High resolution, memory leaks, multiple operations | Add RAM or reduce video resolution |
| 363 | CPU overload during video processing | The processing consumed too much CPU power and was throttled | Complex operations, multiple jobs, inefficient algorithms | Use hardware encoding or limit concurrent jobs |
| 364 | Codec error during video processing | The video codec encountered an error during processing | Unsupported parameters, library malfunction, hardware failure | Update codec libraries or switch to software |
| 365 | Resolution error during video processing | An error occurred while changing or processing video resolution | Invalid scaling, codec limitations, memory insufficient | Use valid scaling parameters and check limits |
| 366 | Framerate error during video processing | An error occurred while processing or converting video framerate | Invalid conversion, format limitations, timing issues | Use standard framerates and check format support |
| 367 | Quality error during video processing | The video quality became unacceptably degraded during processing | Bitrate too low, lossy chain, incompatible settings | Increase bitrate and minimize lossy steps |
| 368 | Output error during video processing | An error occurred while writing the processed video output | Directory inaccessible, disk full, format unsupported | Fix output directory and ensure adequate space |
| 369 | Video processing interrupted | The processing operation was stopped before completion | User cancellation, system shutdown, process killed | Restart processing or implement checkpoints |

### Storage Errors (380-399)

| Code | Message | Meaning | Common Causes | Primary Solution |
|------|---------|---------|---------------|------------------|
| 380 | Insufficient storage space | The storage system lacks adequate space for video operations | Disk full, large files, temp files not cleaned | Free up space or add storage capacity |
| 381 | Storage permission error | The system lacks necessary permissions for storage operations | Directory restrictions, user lacks access, security policies | Fix directory permissions and user access |
| 382 | Storage device error | The physical storage device is malfunctioning | Hard drive failure, SSD wear, controller malfunction | Check device health and replace if needed |
| 383 | Network storage error | An error occurred while accessing network-attached storage | Connectivity lost, server unavailable, auth failure | Check network connectivity and credentials |
| 384 | Storage quota exceeded | The operation would exceed allocated storage quota limits | User quota full, project limits, large files | Clean up files or request quota increase |
| 385 | Invalid storage path | The storage path specification contains errors or is invalid | Invalid characters, doesn't exist, path too long | Use valid paths and create if needed |
| 386 | Storage backup failed | The backup operation for video storage was unsuccessful | Destination inaccessible, space insufficient, tool errors | Verify backup destination and configuration |
| 387 | Storage cleanup failed | The automatic cleanup of old video files was unsuccessful | Files locked, permissions, filesystem errors | Stop processes and fix permissions |
| 388 | Storage migration failed | The transfer of video files to new storage location failed | Space insufficient, permissions, corruption during transfer | Ensure adequate space and verify integrity |
| 389 | Storage corruption detected | The storage system shows signs of data corruption | Filesystem corruption, hardware failure, power issues | Run filesystem check or restore from backup |

## 4xx - Client Management Errors

### Registration Errors (400-419)

| Code | Message | Meaning | Common Causes | Primary Solution |
|------|---------|---------|---------------|------------------|
| 400 | Client registration failed | The system was unable to register the client device | Invalid info, service unavailable, database issues | Verify client information and service status |
| 401 | Client already registered | The client is already registered and cannot register again | Duplicate attempt, network interruption, cleanup needed | Check registration status before retry |
| 402 | Invalid client ID provided | The client identifier format or content is not valid | Invalid characters, wrong length, empty ID | Generate valid client ID following requirements |
| 403 | Client hostname conflict | The client hostname is already in use by another device | Multiple clients same hostname, not unique | Ensure each client has unique hostname |
| 404 | Invalid client data | The client registration data is incomplete or malformed | Missing fields, wrong types, malformed capabilities | Provide all required fields with correct types |
| 405 | Client registration timeout | The registration process took longer than the allowed time | Server overload, high latency, database slow | Increase timeout or reduce server load |
| 406 | Client authentication failed | The client could not be authenticated during registration | Invalid credentials, service down, certificate issues | Verify authentication credentials |
| 407 | Client version mismatch | The client software version is incompatible with the server | Client too old, API incompatible, feature missing | Update client to compatible version |
| 408 | Client registration capacity exceeded | The system has reached the maximum number of registered clients | Client limit reached, license restrictions, resource limits | Increase limits or clean up inactive clients |
| 409 | Duplicate client registration detected | The client is attempting to register multiple times simultaneously | Software bug, network issues, load balancer duplication | Fix client software and implement deduplication |

### Assignment Errors (420-439)

| Code | Message | Meaning | Common Causes | Primary Solution |
|------|---------|---------|---------------|------------------|
| 420 | Client not found in system | The specified client does not exist in the registration database | Never registered, expired, incorrect ID | Register client before assignment |
| 421 | Client assignment failed | The system could not assign the client to the requested target | Target missing, incompatible, resource constraints | Verify target exists and compatibility |
| 422 | Group not found for client assignment | The target group for assignment does not exist | Group doesn't exist, deleted, incorrect ID | Verify group exists before assignment |
| 423 | Screen assignment conflict | The screen assignment conflicts with existing assignments | Multiple clients same screen, exceeds count, race condition | Use unique screen assignments |
| 424 | Client already assigned | The client is already assigned to a group or stream | Duplicate assignment, not cleared, state inconsistency | Clear existing assignment first |
| 425 | Group capacity full | The target group has reached its maximum client capacity | All screens assigned, client limit reached | Use different group or remove inactive clients |
| 426 | Client configuration incompatible | The client's capabilities don't match the assignment requirements | Resolution mismatch, codec insufficient, network requirements | Update client config to match requirements |
| 427 | Client assignment timeout | The assignment process took longer than the allowed time | Network delays, server overload, client unresponsive | Increase timeout and check responsiveness |
| 428 | Client assignment permission denied | The user lacks permission to perform the client assignment | User lacks privileges, client unauthorized, policy restrictions | Ensure proper permissions for assignment |
| 429 | Client in invalid state for assignment | The client's current state prevents assignment | Not ready, error state, maintenance, transition in progress | Wait for valid state or reset client |

### Connection Errors (440-459)

| Code | Message | Meaning | Common Causes | Primary Solution |
|------|---------|---------|---------------|------------------|
| 440 | Client connection failed | The system could not establish a connection to the client | Device offline, network issues, software not running | Verify device is online and software running |
| 441 | Client connection lost | An established connection to the client was unexpectedly lost | Network interruption, device shutdown, software crashed | Check network stability and device status |
| 442 | Client heartbeat timeout | The client failed to respond to heartbeat requests within the timeout | Overloaded, network latency, software hung | Reduce load and increase timeout values |
| 443 | Client network error | A network-related error occurred in communication with the client | Packet loss, congestion, interface errors, DNS issues | Fix network issues and improve stability |
| 444 | Client connection refused | The client actively refused the connection attempt | Not listening, firewall blocking, auth rejected | Configure client firewall and services |
| 445 | Client connection reset | The client forcibly closed an established connection | Software restart, network path changed, protocol violation | Check software stability and network consistency |
| 446 | Insufficient bandwidth for client | The network bandwidth is inadequate for client operations | Low bandwidth, multiple clients, congestion | Increase bandwidth or implement QoS |
| 447 | Network latency too high for client | The network delay between server and client exceeds limits | Physical distance, inefficient routing, equipment delays | Use edge servers or optimize routing |
| 448 | Client connection unstable | The connection quality to the client is inconsistent | Intermittent issues, moving connections, equipment failures | Fix connectivity issues and use redundancy |
| 449 | Client connection blocked by firewall | Firewall rules are preventing connection to the client | Client/network firewall, security policies, port forwarding | Configure firewall rules for client access |

### Status and Monitoring Errors (460-479)

| Code | Message | Meaning | Common Causes | Primary Solution |
|------|---------|---------|---------------|------------------|
| 460 | Client status unknown | The system cannot determine the current state of the client | Not responding, monitoring unavailable, transitional state | Check client responsiveness and monitoring |
| 461 | Client not responding | The client is not responding to requests or commands | Software hung, overloaded, network issues, power saving | Restart client software or check resources |
| 462 | Client health check failed | The client failed system health monitoring checks | Performance below threshold, hardware issues, errors | Investigate and fix performance/hardware issues |
| 463 | Client performance degraded | The client's performance has fallen below acceptable levels | CPU/memory overload, network congestion, I/O bottlenecks | Reduce load and optimize performance |
| 464 | Client resources exhausted | The client has run out of critical system resources | Memory/CPU/storage full, connection limits | Free up resources or upgrade hardware |
| 465 | Client streaming error | An error occurred in the client's streaming functionality | Protocol errors, decoder issues, display problems | Check streaming implementation and hardware |
| 466 | Client synchronization lost | The client lost synchronization with other clients or the server | Clock drift, network jitter, processing delays | Implement NTP and jitter buffers |
| 467 | Client buffer issues | The client is experiencing buffer underrun or overflow problems | Buffer underrun/overflow, inconsistent delivery | Adjust buffer sizes and improve consistency |
| 468 | Client display error | An error occurred in the client's display or rendering system | Hardware malfunction, driver issues, connection problems | Check display hardware and drivers |
| 469 | Client hardware error | A hardware malfunction was detected on the client device | Component failure, overheating, power issues | Diagnose and repair/replace hardware |

### Configuration Errors (480-499)

| Code | Message | Meaning | Common Causes | Primary Solution |
|------|---------|---------|---------------|------------------|
| 480 | Client configuration invalid | The client's configuration settings are invalid or corrupted | Corrupted file, invalid values, version incompatible | Restore from backup or use defaults |
| 481 | Client configuration missing | Required client configuration is not available | File not found, not deployed, service unavailable | Deploy configuration file to client |
| 482 | Client configuration conflict | The configuration conflicts with system requirements | Contradictory parameters, server incompatible, hardware limits | Resolve conflicts and align configurations |
| 483 | Client configuration update failed | The system could not update the client's configuration | Write access denied, service unavailable, validation failed | Ensure write access and service availability |
| 484 | Client settings error | An error occurred in the client application settings | Settings corrupted, version incompatible, conflicts | Reset to defaults and resolve conflicts |
| 485 | Client capability mismatch | The client's capabilities don't match system requirements | Hardware insufficient, features missing, version too old | Upgrade hardware/software to meet requirements |
| 486 | Client resolution error | An error occurred with the client's display resolution configuration | Not supported, configuration invalid, hardware unable | Use supported resolution and update drivers |
| 487 | Client codec unsupported | The client does not support the required video codec | Not installed, hardware lacks support, licensing issues | Install codecs or use supported alternatives |
| 488 | Client profile error | An error occurred in the client profile or user configuration | Corrupted, permissions incorrect, storage issues | Restore profile or create new one |
| 489 | Client configuration validation failed | The client configuration failed validation checks | Invalid ranges, missing fields, format errors | Use valid parameters and complete configuration |

## 5xx - System-Wide Errors

### General System Errors (500-519)

| Code | Message | Meaning | Common Causes | Primary Solution |
|------|---------|---------|---------------|------------------|
| 500 | System initialization failed | The system could not start up or initialize properly | Config missing, services unavailable, database connection failed | Check configuration and service dependencies |
| 501 | System configuration error | The system configuration is invalid or contains errors | Syntax errors, missing parameters, conflicting settings | Validate configuration and resolve conflicts |
| 502 | System resources exhausted | The system has run out of critical resources needed to operate | Memory/CPU/disk/network fully utilized | Free up resources or add capacity |
| 503 | System permission denied | The system lacks necessary permissions to perform operations | Service account lacks privileges, restrictive permissions | Grant required privileges and fix permissions |
| 504 | System service unavailable | A critical system service is not available or accessible | Service crashed, dependency missing, overloaded | Restart services and check dependencies |
| 505 | System operation timeout | A system operation exceeded the maximum allowed time limit | Overload, network latency, resource contention | Increase timeouts and optimize performance |
| 506 | System internal error | An unexpected internal error occurred in the system | Software bug, unhandled exception, memory corruption | Check logs and update software |
| 507 | System in maintenance mode | The system is currently in maintenance mode and unavailable | Scheduled maintenance, updates, emergency maintenance | Wait for maintenance completion |
| 508 | System capacity exceeded | The system has reached its maximum operational capacity | User/connection/processing/storage limits reached | Increase capacity or implement load management |
| 509 | Incompatible system version | The system version is incompatible with requirements | Software too old, version mismatch, API incompatibility | Update to compatible versions |

### Database Errors (520-539)

| Code | Message | Meaning | Common Causes | Primary Solution |
|------|---------|---------|---------------|------------------|
| 520 | Database connection failed | The system could not connect to the database server | Server not running, network lost, invalid credentials | Start database and check connectivity |
| 521 | Database query failed | A database query could not be executed successfully | SQL syntax errors, missing tables, constraint violations | Fix SQL syntax and verify schema |
| 522 | Database transaction failed | A database transaction could not be completed | Deadlocks, timeouts, constraint violations | Implement deadlock retry and fix constraints |
| 523 | Database corruption detected | The database data or structure has been corrupted | Hardware failure, improper shutdown, filesystem corruption | Restore from backup or run repair tools |
| 524 | Database disk full | The database storage has run out of available space | Files grew beyond space, logs not truncated | Add disk space and manage log files |
| 525 | Database permission denied | The system lacks permission to access the database | User lacks privileges, file permissions, security policies | Grant database privileges and fix permissions |
| 526 | Database operation timeout | A database operation exceeded the maximum allowed time | Complex queries, locks, insufficient resources | Optimize queries and add resources |
| 527 | Database schema mismatch | The database schema doesn't match the expected version | Migration not applied, version mismatch, manual changes | Run migrations and synchronize schema |
| 528 | Database backup failed | The database backup operation was unsuccessful | Space insufficient, destination inaccessible, tool errors | Ensure backup space and fix configuration |
| 529 | Database restore failed | The database restore operation was unsuccessful | Backup corrupted, permissions insufficient, incompatibility | Verify backup integrity and permissions |

### Network Errors (540-559)

| Code | Message | Meaning | Common Causes | Primary Solution |
|------|---------|---------|---------------|------------------|
| 540 | Network interface error | A network interface is malfunctioning or misconfigured | Hardware failure, driver issues, configuration errors | Check hardware and update drivers |
| 541 | Network routing error | Network routing is not working properly | Routing misconfiguration, gateway unreachable, protocol failures | Fix routing configuration and gateways |
| 542 | DNS resolution failed | The system could not resolve domain names to IP addresses | DNS server down, configuration errors, connectivity lost | Check DNS servers and configuration |
| 543 | Firewall blocking network access | Firewall rules are preventing required network communication | Restrictive rules, ports not opened, application blocked | Review and adjust firewall rules |
| 544 | Network bandwidth exhausted | All available network bandwidth is being used | High traffic, insufficient capacity, congestion | Implement QoS and increase capacity |
| 545 | Network latency too high | Network delays exceed acceptable thresholds | Physical distance, inefficient routing, congestion | Use edge servers and optimize routing |
| 546 | Network packet loss detected | Significant data packets are being lost during transmission | Congestion, faulty equipment, interference | Fix equipment and reduce congestion |
| 547 | Network port unavailable | The requested network port is not available for use | Port in use, blocked, outside allowed range | Use different port or configure access |
| 548 | SSL/TLS network error | An error occurred in SSL/TLS encrypted communication | Certificate invalid, version mismatch, cipher incompatibility | Update certificates and SSL configuration |
| 549 | Network proxy error | An error occurred with network proxy configuration or operation | Server unavailable, auth failed, configuration incorrect | Fix proxy configuration and authentication |

### Security Errors (560-579)

| Code | Message | Meaning | Common Causes | Primary Solution |
|------|---------|---------|---------------|------------------|
| 560 | Authentication failed | User or system authentication was unsuccessful | Invalid credentials, service unavailable, token expired | Verify credentials and service status |
| 561 | Authorization denied | The user or system lacks authorization for the requested operation | Lacks permissions, policy denying, service malfunction | Grant required permissions and check policies |
| 562 | Security token expired | The authentication or authorization token has exceeded its lifetime | Exceeded lifetime, clock skew, not refreshed | Refresh tokens and synchronize clocks |
| 563 | Security token invalid | The authentication or authorization token is not valid | Corrupted, untrusted source, signature failed | Obtain new token from trusted source |
| 564 | Security certificate invalid | The security certificate is not valid or trusted | Expired, untrusted authority, hostname mismatch | Renew certificates and fix configuration |
| 565 | Encryption error | An error occurred during encryption or decryption operations | Invalid keys, unsupported algorithm, data corruption | Verify keys and use supported algorithms |
| 566 | Security intrusion detected | The security system detected a potential security breach | Suspicious patterns, failed attempts, malicious activity | Investigate incident and strengthen security |
| 567 | Security policy violation | An operation violates established security policies | Action not allowed, compliance not met, policy triggered | Modify operation or update policies |
| 568 | Security audit failed | The security audit process failed or found security issues | Vulnerabilities found, compliance violations, tool errors | Fix vulnerabilities and ensure compliance |
| 569 | Key management error | An error occurred in cryptographic key management | Generation failed, storage issues, rotation failed | Fix key management system and processes |

### Performance and Monitoring Errors (580-599)

| Code | Message | Meaning | Common Causes | Primary Solution |
|------|---------|---------|---------------|------------------|
| 580 | Performance threshold exceeded | System performance metrics have exceeded acceptable limits | Load higher than capacity, bottlenecks, inefficient code | Reduce load and optimize performance |
| 581 | Monitoring service failed | The system monitoring service is not functioning | Service crashed, configuration errors, connectivity lost | Restart monitoring and fix configuration |
| 582 | Metrics collection failed | The system could not collect performance or operational metrics | Agent not running, access denied, format errors | Start agents and fix access permissions |
| 583 | Alerting system failed | The alerting and notification system is not working | Service unavailable, configuration errors, channels blocked | Check service and fix alert configuration |
| 584 | Log system failed | The system logging functionality has failed | Storage full, service stopped, permissions issues | Free storage and fix log service |
| 585 | Health check failed | System health monitoring detected problems | Components not responding, limits exceeded, dependencies unavailable | Check components and fix dependencies |
| 586 | Load balancer error | The load balancer is not functioning properly | Service unavailable, backends not responding, configuration errors | Check load balancer and backend health |
| 587 | Failover failed | The system failover process was unsuccessful | Backup systems not ready, triggers not working, sync issues | Ensure backup readiness and fix triggers |
| 588 | Backup system failed | The system backup process was unsuccessful | Storage full, service errors, corruption during backup | Fix storage and backup service issues |
| 589 | System recovery failed | The system recovery process was unsuccessful | Backup corrupted, procedures incorrect, hardware issues | Use verified backups and fix hardware |

## Error Handling Best Practices

### For Developers

1. **Always use specific error codes** instead of generic messages
2. **Include relevant context** in error responses (file paths, configuration values, etc.)
3. **Log detailed error information** for debugging while returning user-friendly messages
4. **Implement retry logic** for transient errors (network timeouts, resource exhaustion)
5. **Validate inputs early** to catch configuration errors before processing

### For System Administrators

1. **Monitor error frequency** and patterns to identify systemic issues
2. **Set up automated alerts** for critical error categories (5xx system errors)
3. **Maintain error logs** with sufficient detail for troubleshooting
4. **Document common resolution steps** for your specific environment
5. **Test error scenarios** during maintenance windows to verify monitoring

### For Users

1. **Check error code documentation** before contacting support
2. **Include error codes and context** when reporting issues
3. **Try suggested solutions** in order of likelihood
4. **Check system status** and network connectivity first
5. **Keep logs and screenshots** of error conditions for troubleshooting

## Quick Reference: Most Common Errors

| Code | Module | Error | Meaning | Quick Fix |
|------|--------|-------|---------|----------|
| 143 | Stream | Group not found in Docker | The specified group has no corresponding Docker container | Create Docker container: `docker run ossrs/srs:5` |
| 144 | Stream | Group container not running | The group's Docker container exists but is currently stopped | Start container: `docker start <container>` |
| 200 | Docker | Service not running | The Docker daemon process is not active on the system | Start Docker: `sudo systemctl start docker` |
| 260 | Docker | Port already in use | Another process is currently using the requested port | Find process: `netstat -tulpn \| grep <port>` |
| 340 | Video | File not found | The system cannot locate the video file at the specified location | Check file path and permissions |
| 400 | Client | Registration failed | The system was unable to register the client device | Verify client information completeness |
| 520 | System | Database connection failed | The system could not connect to the database server | Check database service and connectivity |

## Error Code Ranges Summary

- **100-199**: Stream Management (FFmpeg, SRT, Configuration, Monitoring, Video Processing)
- **200-299**: Docker Management (Service, Containers, Images, Ports, Volumes)
- **300-399**: Video Management (Upload, Validation, File Operations, Processing, Storage)
- **400-499**: Client Management (Registration, Assignment, Connection, Monitoring, Configuration)
- **500-599**: System-Wide (General, Database, Network, Security, Performance)