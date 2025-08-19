# Multi-Screen Client Setup Guide

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Basic Usage](#basic-usage)
5. [Multi-Monitor Setup](#multi-monitor-setup)
6. [Hotkey Controls](#hotkey-controls)
7. [Advanced Configuration](#advanced-configuration)
8. [Troubleshooting](#troubleshooting)
9. [Examples](#examples)
10. [Auto-Startup](#auto-startup)

## Overview

The Multi-Screen Client is a Python-based application that connects to a video wall server and displays video streams with movable fullscreen windows. It supports multiple monitors and can be controlled via hotkeys to move between displays.

### Key Features
- **Movable Fullscreen Windows** - Use hotkeys to move between monitors
- **Smart Player Selection** - Automatically chooses between ffplay and C++ player
- **Multi-Monitor Support** - Works with 1-4+ monitors
- **Hotkey Controls** - Keyboard shortcuts for window management
- **Automatic Reconnection** - Handles network issues gracefully
- **Wayland/XWayland Compatible** - Works on modern Linux systems

## Prerequisites

### System Requirements
- **Operating System**: Linux (Ubuntu, Debian, Raspberry Pi OS, etc.)
- **Python**: Python 3.7 or higher
- **Display**: X11, Wayland, or XWayland
- **Network**: Internet connection for server communication

### Hardware Requirements
- **RAM**: Minimum 2GB (4GB recommended)
- **Storage**: 1GB free space
- **Network**: Ethernet or WiFi connection
- **Display**: HDMI, DPI, or USB display support

## Installation

### Step 1: Download and Prepare
```bash
# Clone or download the client files
cd /path/to/your/client/directory

# Make setup script executable
chmod +x setup_client.sh
```

### Step 2: Run Setup Script
```bash
# Run the automated setup
./setup_client.sh
```

The setup script will automatically:
- Install window management tools (wmctrl, xdotool, tkinter)
- Install ffmpeg for video playback
- Create convenience scripts
- Set up multi-monitor configuration tools

### Step 3: Verify Installation
```bash
# Check if required tools are installed
which ffmpeg
which wmctrl
which xdotool

# Test Python tkinter
python3 -c "import tkinter; print('✓ tkinter available')"
```

## Basic Usage

### Starting the Client

#### Method 1: Using the Convenience Script (Recommended)
```bash
./run_client.sh --server http://YOUR_SERVER_IP:5000 \
  --hostname YOUR_CLIENT_NAME --display-name "Display Name"
```

#### Method 2: Direct Python Command
```bash
python3 client.py --server http://YOUR_SERVER_IP:5000 \
  --hostname YOUR_CLIENT_NAME --display-name "Display Name"
```

#### Method 3: With Display Environment Variable
```bash
DISPLAY=:0 python3 client.py --server http://YOUR_SERVER_IP:5000 \
  --hostname YOUR_CLIENT_NAME --display-name "Display Name"
```

### Required Parameters
- **`--server`**: Server URL (e.g., `http://192.168.1.100:5000`)
- **`--hostname`**: Unique client identifier
- **`--display-name`**: Friendly name for admin interface

### Optional Parameters
- **`--force-ffplay`**: Force use of ffplay instead of smart selection
- **`--debug`**: Enable detailed logging

## Multi-Monitor Setup

### Automatic Setup
```bash
# Run the multi-monitor configuration script
./setup_multi_monitor.sh
```

This script offers several configuration options:
1. **Dual Monitor (Side by Side)** - Left/Right setup
2. **Dual Monitor (Stacked)** - Top/Bottom setup
3. **Triple Monitor (Horizontal)** - 3 monitors in a row
4. **Custom Configuration** - Manual setup
5. **Wayland/XWayland Status** - Check display system

### Manual Setup
```bash
# Check current monitor configuration
xrandr --listmonitors

# Configure dual monitors side by side
xrandr --output HDMI-1 --mode 1920x1080 --pos 0x0
xrandr --output HDMI-2 --mode 1920x1080 --pos 1920x0

# Configure triple monitors
xrandr --output HDMI-1 --mode 1920x1080 --pos 0x0
xrandr --output HDMI-2 --mode 1920x1080 --pos 1920x0
xrandr --output HDMI-3 --mode 1920x1080 --pos 3840x0
```

### Monitor Coordinate System
```
Monitor 1 (Left):     x=0, y=0
Monitor 2 (Right):    x=1920, y=0
Monitor 3 (Far Right): x=3840, y=0
Monitor 4 (Bottom):   x=0, y=1080
```

## Hotkey Controls

### Available Hotkeys
| Hotkey | Action | Description |
|--------|--------|-------------|
| **Ctrl+M** | Next Monitor | Move to next available monitor |
| **Ctrl+Right** | Next Monitor | Alternative to Ctrl+M |
| **Ctrl+Left** | Previous Monitor | Move to previous monitor |
| **Ctrl+1** | Monitor 1 | Move to left monitor |
| **Ctrl+2** | Monitor 2 | Move to right monitor |
| **Ctrl+3** | Monitor 3 | Move to far right monitor |
| **Ctrl+4** | Monitor 4 | Move to bottom monitor |
| **Ctrl+H** | Help | Show hotkey reference |

### How Hotkeys Work
1. **Window Manager** - Hidden Tkinter application captures hotkeys
2. **Window Detection** - Finds video window by title
3. **Position Calculation** - Calculates target monitor coordinates
4. **Window Movement** - Uses wmctrl/xdotool to move the window

### Hotkey Requirements
- **Client window must have focus** for hotkeys to work
- **Window manager must be running** (starts automatically with client)
- **Proper monitor configuration** must be set up

## Advanced Configuration

### Environment Variables
```bash
# Set display for specific monitor
export DISPLAY=:0

# Set custom window manager tools
export WINDOW_MANAGER_TOOL=wmctrl  # or xdotool
```

### Configuration Files
The client automatically detects and uses:
- System display configuration
- Monitor positions from xrandr
- Network settings from system

### Custom Monitor Positions
You can modify the monitor positions in the client code:
```python
self.monitor_positions = [
    (0, 0),      # Monitor 1 (left)
    (1920, 0),   # Monitor 2 (right)
    (3840, 0),   # Monitor 3 (far right)
    (0, 1080),   # Monitor 4 (bottom)
]
```

## Troubleshooting

### Common Issues

#### 1. Hotkeys Not Working
```bash
# Check if window manager is running
ps aux | grep python3 | grep client

# Verify window management tools
wmctrl -l
xdotool --version

# Check if client window has focus
# Click on the video window to give it focus
```

#### 2. Window Not Moving
```bash
# Check monitor configuration
xrandr --listmonitors

# Verify monitor positions
xrandr --query | grep -E "(HDMI|connected)"

# Test window movement manually
wmctrl -l  # List windows
wmctrl -ir WINDOW_ID -e 0,1920,0,-1,-1  # Move to x=1920, y=0
```

#### 3. Display Issues
```bash
# Check display system
echo $XDG_SESSION_TYPE
echo $WAYLAND_DISPLAY
echo $DISPLAY

# For Wayland users
# Monitors are configured through desktop environment settings
# Use hotkeys to move windows between monitors
```

#### 4. Network Connection Issues
```bash
# Test server connectivity
curl -I http://YOUR_SERVER_IP:5000

# Check firewall settings
sudo ufw status

# Verify network configuration
ip addr show
```

### Debug Mode
```bash
# Run client with debug logging
./run_client.sh --server http://YOUR_SERVER_IP:5000 \
  --hostname client-1 --display-name "Debug Client" --debug
```

## Examples

### Single Monitor Setup
```bash
# Basic single monitor client
./run_client.sh --server http://192.168.1.100:5000 \
  --hostname rpi-client-1 --display-name "Main Display"
```

### Dual Monitor Setup
```bash
# Configure monitors first
./setup_multi_monitor.sh
# Choose option 1 (Dual Monitor Side by Side)

# Start client on first monitor
./run_client.sh --server http://192.168.1.100:5000 \
  --hostname rpi-client-1 --display-name "Left Monitor"

# Use Ctrl+M to move to right monitor
# Use Ctrl+1 to return to left monitor
```

### Multiple Clients on Same Machine
```bash
# Terminal 1 - Client 1
./run_client.sh --server http://192.168.1.100:5000 \
  --hostname rpi-client-1 --display-name "Client 1" &

# Terminal 2 - Client 2  
./run_client.sh --server http://192.168.1.100:5000 \
  --hostname rpi-client-2 --display-name "Client 2" &

# Each client can be moved independently with hotkeys
```

### Production Deployment
```bash
# Edit systemd service template
nano multiscreen-client.service

# Install service
sudo cp multiscreen-client.service /etc/systemd/system/
sudo systemctl enable multiscreen-client.service
sudo systemctl start multiscreen-client.service

# Check service status
sudo systemctl status multiscreen-client.service
```

## Auto-Startup

### Systemd Service Setup
```bash
# 1. Edit the service file
sudo nano /etc/systemd/system/multiscreen-client.service

# 2. Update the service file with your details:
[Unit]
Description=Multi-Screen Client Service
After=network.target graphical-session.target
Wants=graphical-session.target

[Service]
Type=simple
User=YOUR_USERNAME
Environment=DISPLAY=:0
WorkingDirectory=/path/to/your/client
ExecStart=/usr/bin/python3 /path/to/your/client/client.py \
  --server http://YOUR_SERVER_IP:5000 \
  --hostname YOUR_CLIENT_NAME \
  --display-name "YOUR_DISPLAY_NAME"
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

# 3. Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable multiscreen-client.service
sudo systemctl start multiscreen-client.service
```

### Startup Script
```bash
# Create a startup script
cat > ~/start_client.sh << 'EOF'
#!/bin/bash
cd /path/to/your/client
./run_client.sh --server http://YOUR_SERVER_IP:5000 \
  --hostname YOUR_CLIENT_NAME --display-name "YOUR_DISPLAY_NAME"
EOF

chmod +x ~/start_client.sh

# Add to autostart
mkdir -p ~/.config/autostart
cat > ~/.config/autostart/multiscreen-client.desktop << EOF
[Desktop Entry]
Type=Application
Name=Multi-Screen Client
Exec=/home/YOUR_USERNAME/start_client.sh
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
EOF
```

## Command Reference

### Client Commands
```bash
# Basic client startup
./run_client.sh --server URL --hostname NAME --display-name "NAME"

# With debug logging
./run_client.sh --server URL --hostname NAME --display-name "NAME" --debug

# Force ffplay usage
./run_client.sh --server URL --hostname NAME --display-name "NAME" --force-ffplay

# Direct Python execution
python3 client.py --server URL --hostname NAME --display-name "NAME"
```

### Setup Commands
```bash
# Run setup script
./setup_client.sh

# Configure monitors
./setup_multi_monitor.sh

# Check setup status
ls -la *.sh
which ffmpeg wmctrl xdotool
```

### Monitor Commands
```bash
# Check monitor status
xrandr --listmonitors

# Configure monitors manually
xrandr --output HDMI-1 --mode 1920x1080 --pos 0x0
xrandr --output HDMI-2 --mode 1920x1080 --pos 1920x0

# Reset monitor configuration
xrandr --auto
```

### Service Commands
```bash
# Start service
sudo systemctl start multiscreen-client.service

# Stop service
sudo systemctl stop multiscreen-client.service

# Check status
sudo systemctl status multiscreen-client.service

# View logs
sudo journalctl -u multiscreen-client.service -f
```

## Support and Resources

### Getting Help
- **Hotkey Help**: Press `Ctrl+H` while client is running
- **Debug Mode**: Use `--debug` flag for detailed logging
- **Service Logs**: Check systemd logs for service issues

### File Locations
- **Client Script**: `./client.py`
- **Setup Script**: `./setup_client.sh`
- **Runner Script**: `./run_client.sh`
- **Monitor Setup**: `./setup_multi_monitor.sh`
- **Service Template**: `./multiscreen-client.service`

### Dependencies
- **ffmpeg**: Video playback
- **wmctrl**: Window management
- **xdotool**: X11 automation
- **tkinter**: Python GUI (hotkey handling)

---

## Quick Start Checklist

- [ ] Run `./setup_client.sh`
- [ ] Configure monitors with `./setup_multi_monitor.sh`
- [ ] Start client with `./run_client.sh`
- [ ] Test hotkeys (Ctrl+M, Ctrl+1-4)
- [ ] Configure auto-startup (optional)

**Your multi-screen client is now ready with movable window support!** 
