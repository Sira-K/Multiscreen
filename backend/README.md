# Multi-Screen Video Streaming Server

A Flask-based server for managing multi-screen video streaming with SRT protocol and client management.

## Architecture

The server follows a clean, service-oriented architecture:

```
backend/
├── blueprints/           # Flask route handlers
│   ├── client_management/    # Client registration and management
│   ├── streaming/            # Stream management (multi/split)
│   ├── group_management.py   # Group operations
│   ├── video_management.py   # Video file operations
│   ├── screen_management.py  # Screen configuration
│   ├── docker_management.py  # Docker operations
│   └── error_management.py   # Error handling and logging
├── services/             # Business logic services
│   ├── docker_service.py      # Docker discovery and management
│   ├── ffmpeg_service.py      # FFmpeg utilities and commands
│   ├── srt_service.py         # SRT connection testing
│   ├── video_validation_service.py # Video file validation
│   └── error_service.py       # Error handling services
├── endpoints/            # API endpoint organization
│   ├── blueprints/           # Blueprint imports
│   ├── services/             # Service imports
│   └── uploads/              # Video file storage
├── logs/                 # Logging configuration and scripts
│   ├── logging_config.py     # Logging setup
│   ├── monitor_logs.py       # Log monitoring
│   └── cron_rotate_logs.sh   # Log rotation script
├── app_config.py         # Configuration management
├── flask_app.py          # Main Flask application
├── gunicorn.conf.py      # Gunicorn configuration
└── README.md             # This file
```

## Quick Start

### 1. Start the Server
```bash
cd backend
python3 flask_app.py
```

### 2. Start Split-Screen Streaming
```bash
curl -X POST http://localhost:5000/api/streaming/start_split_screen_srt \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "your-group-id",
    "video_file": "video.mp4",
    "orientation": "horizontal"
  }'
```

### 3. Start Multi-Video Streaming
```bash
curl -X POST http://localhost:5000/api/streaming/start_multi_video_srt \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "your-group-id",
    "video_files": ["video1.mp4", "video2.mp4"],
    "layout": "grid"
  }'
```

### 4. Stop Streaming
```bash
curl -X POST http://localhost:5000/api/streaming/stop_group_stream \
  -H "Content-Type: application/json" \
  -d '{"group_id": "your-group-id"}'
```

## Configuration

Edit `app_config.json` to customize:

- **Server settings** (host, port, debug)
- **File settings** (upload folder, max file size, allowed extensions)
- **Streaming settings** (default framerate, bitrate, SRT parameters)

## API Endpoints

### Client Management
- `POST /api/clients/register` - Register a new client
- `GET /api/clients/status` - Get client status
- `GET /api/clients/all` - Get all registered clients

### Stream Management
- `POST /api/streaming/start_split_screen_srt` - Start split-screen streaming
- `POST /api/streaming/start_multi_video_srt` - Start multi-video streaming
- `POST /api/streaming/stop_group_stream` - Stop streaming for a group
- `GET /api/streaming/all_streaming_statuses` - Get all streaming statuses

### Group Management
- `POST /api/groups/create` - Create a new group
- `GET /api/groups/all` - Get all groups
- `DELETE /api/groups/<group_id>` - Delete a group

### Video Management
- `POST /api/videos/upload` - Upload video file
- `GET /api/videos/all` - Get all available videos
- `DELETE /api/videos/<filename>` - Delete a video

### Docker Management
- `GET /api/docker/containers` - Get Docker container information
- `GET /api/docker/groups` - Discover groups from Docker

### System
- `GET /` - API information and endpoints
- `GET /health` - Health check

## Features

- **Split-Screen Streaming** - Single video split into multiple regions
- **Multi-Video Streaming** - Multiple videos combined into one stream
- **SRT Protocol** - Low-latency video streaming
- **Client Management** - Client registration and status tracking
- **Docker Integration** - Automatic group discovery
- **FFmpeg Integration** - Advanced video processing
- **Comprehensive Logging** - Centralized logging system
- **Error Management** - Robust error handling and reporting

## Code Quality

- **Single Responsibility** - Each class has one clear purpose
- **Clean Interfaces** - Simple, consistent method signatures
- **Error Handling** - Consistent error responses and logging
- **Type Hints** - Better code understanding
- **Modular Design** - Blueprint-based organization

## Logging

All logging is centralized in the `logs/` directory:
- **logging_config.py** - Main logging configuration
- **monitor_logs.py** - Log monitoring and rotation
- **cron_rotate_logs.sh** - Automated log rotation script

## Requirements

- Python 3.7+
- FFmpeg
- Docker (for group discovery)
- Flask
- Flask-CORS
- psutil

## Development

The server maintains backward compatibility with existing routes while providing new, cleaner API endpoints. All new development should use the `/api/` prefixed routes.