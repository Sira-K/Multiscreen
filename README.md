# Multi-Screen Video Streaming Client

A lightweight, single-threaded video streaming client designed for Raspberry Pi and multi-screen video wall systems. The client automatically handles package installation and provides efficient video playback with minimal resource usage.

## Features

- **Single-threaded architecture** - Optimized for Raspberry Pi efficiency
- **Automatic package management** - Installs required Python packages automatically
- **Smart player selection** - Automatically chooses between C++ player and ffplay
- **Server integration** - Connects to video streaming server for content management
- **Automatic reconnection** - Handles network interruptions gracefully
- **Resource efficient** - Minimal memory and CPU footprint

## Architecture

### Threading Model
Each client runs with exactly 2 threads:
- **Main Thread**: Handles server communication, stream management, and client logic
- **Output Thread**: Monitors video player output for errors and status updates

### Process Model
- Each client runs as a separate process
- Multiple clients can run simultaneously on the same device
- Perfect for multi-core systems (e.g., 2 clients on 4-core Raspberry Pi)

## Requirements

- Python 3.7+
- FFmpeg (for video playback)
- Python requests package
- Network access to streaming server
- Linux/Unix environment (tested on Raspberry Pi OS)

## Installation

### Raspberry Pi Setup (Recommended)

For complete setup from a fresh Raspberry Pi installation, see the comprehensive guide:
**[RASPBERRY_PI_SETUP.md](RASPBERRY_PI_SETUP.md)**

### Automatic Setup (Recommended)

The client includes an automatic setup script that installs all required dependencies:

```bash
# Clone the repository
git clone <repository-url>
cd UB_Intern

# Run the setup script
cd client
./setup_client.sh

# The script will install:
# - Python 3.7+
# - FFmpeg (includes ffplay and ffprobe)
# - Python requests package
# - All system dependencies
```

### Manual Installation

If you prefer to install dependencies manually:

```bash
# Install system dependencies (Ubuntu/Debian/Raspberry Pi)
sudo apt-get update
sudo apt-get install -y python3 python3-pip ffmpeg

# Install Python packages
pip3 install --user -r client/requirements.txt

# Run the client directly
python3 client/client.py --server <server-url> --hostname <client-name> --display-name <display-name>
```

## Usage

### Basic Usage

```bash
python3 client/client.py --server http://192.168.1.100:5000 --hostname rpi1 --display-name "Screen1"
```

### Command Line Arguments

- `--server`: Server URL (required)
- `--hostname`: Unique client identifier (required)
- `--display-name`: Display name for admin interface (required)
- `--force-ffplay`: Force use of ffplay for all streams
- `--debug`: Enable debug logging

### Running Multiple Clients

```bash
# Terminal 1 - Client for Screen 1
python3 client/client.py --server http://192.168.1.100:5000 --hostname rpi1 --display-name "Screen1" &

# Terminal 2 - Client for Screen 2
python3 client/client.py --server http://192.168.1.100:5000 --hostname rpi2 --display-name "Screen2" &
```

## Server Integration

The client automatically:
1. Registers with the streaming server
2. Waits for content assignment
3. Plays assigned streams
4. Monitors stream health
5. Reconnects on network issues

## Performance Characteristics

- **Memory Usage**: ~20MB per client
- **CPU Usage**: Minimal (I/O bound operations)
- **Thread Count**: 2 threads per client
- **Process Count**: 1 process per client
- **Network**: Low bandwidth for control, high bandwidth for video

## Troubleshooting

### Common Issues

1. **Package Installation Fails**
   - Ensure internet connectivity
   - Check Python version (3.7+ required)
   - Verify pip is available

2. **Video Playback Issues**
   - Verify ffplay is installed
   - Check network connectivity to server
   - Ensure proper display permissions

3. **Registration Fails**
   - Verify server URL is correct
   - Check network connectivity
   - Ensure server is running

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
python3 client/client.py --server <url> --hostname <name> --display-name <display> --debug
```

## Development

### Code Structure

- `client/client.py`: Main client implementation
- `backend/`: Server-side code (separate project)
- `frontend/`: Web interface (separate project)

### Key Components

- **UnifiedMultiScreenClient**: Main client class
- **Video playback**: ffplay integration with output monitoring
- **Server communication**: REST API integration
- **Error handling**: Graceful failure and recovery

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]