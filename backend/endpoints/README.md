# Multi-Screen Video Streaming Server

A clean, simple Flask-based server for managing multi-screen video streaming with SRT protocol.

## 🏗️ Architecture

The server follows a clean, service-oriented architecture:

```
endpoints/
├── services/           # Business logic services
│   ├── stream_manager.py      # Core stream operations
│   ├── stream_controller.py   # Start/stop control
│   ├── stream_validator.py    # Input validation
│   ├── stream_builder.py      # FFmpeg commands
│   ├── docker_service.py      # Docker discovery
│   ├── ffmpeg_service.py      # FFmpeg utilities
│   └── srt_service.py         # SRT connection testing
├── blueprints/         # Flask route handlers
│   ├── clean_stream_routes.py # New clean routes
│   ├── stream_management.py   # Legacy routes
│   ├── docker_management.py   # Docker operations
│   ├── video_management.py    # Video operations
│   ├── group_management.py    # Group operations
│   └── client_management.py   # Client operations
├── uploads/            # Video file storage
├── app_config.py       # Configuration management
├── flask_app.py        # Main Flask application
└── README.md           # This file
```

## 🚀 Quick Start

### 1. Start the Server
```bash
cd endpoints
python3 flask_app.py
```

### 2. Start Split-Screen Streaming
```bash
curl -X POST http://localhost:5000/start_split_screen \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "your-group-id",
    "video_file": "video.mp4",
    "orientation": "horizontal"
  }'
```

### 3. Start Multi-Video Streaming
```bash
curl -X POST http://localhost:5000/start_multi_video \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "your-group-id",
    "video_files": ["video1.mp4", "video2.mp4"],
    "layout": "grid"
  }'
```

### 4. Stop Streaming
```bash
curl -X POST http://localhost:5000/stop_stream \
  -H "Content-Type: application/json" \
  -d '{"group_id": "your-group-id"}'
```

## 🔧 Configuration

Edit `app_config.json` to customize:

- **Server settings** (host, port, debug)
- **File settings** (upload folder, max file size, allowed extensions)
- **Streaming settings** (default framerate, bitrate, SRT parameters)

## 📡 API Endpoints

### Stream Management
- `POST /start_split_screen` - Start split-screen streaming
- `POST /start_multi_video` - Start multi-video streaming
- `POST /stop_stream` - Stop streaming for a group
- `GET /stream_status/<group_id>` - Get streaming status

### System
- `GET /` - API information
- `GET /health` - Health check

## 🎯 Features

- **Split-Screen Streaming** - Single video split into multiple regions
- **Multi-Video Streaming** - Multiple videos combined into one stream
- **SRT Protocol** - Low-latency video streaming
- **Docker Integration** - Automatic group discovery
- **FFmpeg Integration** - Advanced video processing
- **Clean Architecture** - Easy to maintain and extend

## 🧹 Code Quality

- **Single Responsibility** - Each class has one clear purpose
- **Clean Interfaces** - Simple, consistent method signatures
- **Error Handling** - Consistent error responses
- **Type Hints** - Better code understanding
- **Logging** - Comprehensive operation logging

## 🔄 Migration

The server maintains backward compatibility with existing routes while providing new, cleaner endpoints. You can gradually migrate from old routes to new ones.

## 📝 Requirements

- Python 3.7+
- FFmpeg
- Docker (for group discovery)
- Flask
- psutil