# Multi-Screen SRT Control Server - Refactored

This repository contains a Flask-based server for controlling multi-screen SRT (Secure Reliable Transport) video streaming. The application has been refactored to use Flask Blueprints for better code organization and maintainability.

## Project Structure

The project is organized as follows:

```
srt_control_server/
├── app.py                    # Application entry point
├── config.py                 # Configuration management
├── models/
│   └── app_state.py          # Application state model
├── utils/
│   ├── __init__.py
│   ├── video_utils.py        # Video processing utilities
│   └── ffmpeg_utils.py       # FFmpeg command building utilities
├── blueprints/
│   ├── __init__.py
│   ├── screen_management.py  # Screen and network endpoints
│   ├── docker_management.py  # Docker container endpoints
│   ├── stream_management.py  # SRT stream endpoints
│   └── client_management.py  # Client registration and management endpoints
├── static/                   # Static files (if any)
│   └── ...
├── templates/                # HTML templates (if any)
│   └── ...
└── uploads/                  # Directory for uploaded videos
    └── ...
```

## Features

- Configure multiple screens with different orientations (horizontal/vertical)
- Manage Docker containers for SRT streaming
- Control FFmpeg processes for video stream splitting
- Client registration and management
- Upload and process video files

## API Endpoints

### Screen Management
- `POST /set_screen_ips` - Configure screen count, IPs, and orientation

### Docker Management
- `POST /start_docker` - Start the SRT Docker container
- `POST /stop_docker` - Stop the SRT Docker container

### Stream Management
- `POST /start_srt` - Start SRT stream using FFmpeg
- `POST /stop_srt` - Stop the running FFmpeg process
- `POST /upload_video` - Upload and validate a video file

### Client Management
- `POST /register_client` - Register a client device with the server
- `POST /client_status` - Check what stream a client should be displaying
- `GET /get_clients` - Get a list of all registered clients
- `POST /assign_stream` - Assign a specific stream to a client
- `POST /rename_client` - Rename a client for easier identification

## Installation

1. Clone the repository
2. Install dependencies: `pip install flask flask-cors psutil`
3. Ensure FFmpeg is installed on your system
4. Run the application: `python app.py`

## Usage

The server will start on port 5000 by default. You can interact with it using HTTP requests to the various endpoints.