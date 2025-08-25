# Enhanced Multi-Screen Client

A powerful, multithreaded client for video wall systems that automatically detects multiple instances and enables synchronized video playback across multiple screens.

## 🚀 Key Features

- **Single-Threaded Architecture** - Optimized for Raspberry Pi efficiency
- **Synchronized Video Playback** - Perfect frame synchronization across all screens
- **Smart Player Selection** - Automatically chooses C++ player or ffplay
- **Target Screen Support** - Simple 1 or 2 screen targeting
- **Automatic Reconnection** - Handles network issues gracefully
- **Resource Management** - Proper cleanup and memory management
- **Pi Optimized** - Perfect for single-core and multi-core Raspberry Pi devices

## 📋 System Requirements

### **Hardware**
- **CPU**: Multi-core processor (2+ cores recommended)
- **RAM**: Minimum 2GB, 4GB+ recommended for multiple clients
- **Storage**: 1GB free space
- **Network**: Stable network connection to video server

### **Software**
- **OS**: Linux (Ubuntu 18.04+, Debian 10+, CentOS 7+, Raspberry Pi OS)
- **Python**: 3.7 or higher
- **Display**: X11 with multiple monitor support
- **Package Manager**: apt, yum, dnf, or pacman

## 🛠️ Installation & Setup

### **Quick Setup (Recommended)**

1. **Download the client files**
   ```bash
   git clone <your-repo-url>
   cd client
   ```

2. **Make setup script executable**
   ```bash
   chmod +x setup_client.sh
   ```

3. **Run the automated setup**
   ```bash
   ./setup_client.sh
   ```

The setup script will automatically:
- Install all system dependencies
- Install Python packages
- Build C++ player (if source available)
- Configure display environment
- Setup logging and rotation
- Test the installation

### **Manual Setup**

If you prefer manual installation:

1. **Install system dependencies**
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install -y ffmpeg wmctrl xdotool python3-tk python3-dev build-essential cmake git
   
   # CentOS/RHEL/Fedora
   sudo yum install -y ffmpeg wmctrl xdotool python3-tkinter python3-devel gcc gcc-c++ make cmake git
   ```

2. **Install Python dependencies**
   ```bash
   python3 -m pip install --user requests
   ```

3. **Build C++ player (optional)**
   ```bash
   cd multi-screen
   mkdir -p cmake-build-debug && cd cmake-build-debug
   cmake .. && make -j$(nproc)
   cd ../..
   ```

## 🎯 Usage

### **Basic Usage**

#### **Single Client (Screen 1)**
```bash
python3 client.py --server http://YOUR_SERVER:5000 \
  --hostname client1 --display-name "Screen1" \
  --target-screen 1
```

#### **Multiple Clients (Single-Threaded Per Process)**
```bash
# Terminal 1 - Screen 1
python3 client.py --server http://YOUR_SERVER:5000 \
  --hostname client1 --display-name "Screen1" \
  --target-screen 1

# Terminal 2 - Screen 2 (each client uses 1 thread)
python3 client.py --server http://YOUR_SERVER:5000 \
  --hostname client2 --display-name "Screen2" \
  --target-screen 2
```

### **Advanced Options**

#### **Debug Mode**
```bash
python3 client.py --server http://YOUR_SERVER:5000 \
  --hostname client1 --display-name "Screen1" \
  --target-screen 1 --debug
```

#### **Force ffplay**
```bash
python3 client.py --server http://YOUR_SERVER:5000 \
  --hostname client1 --display-name "Screen1" \
  --target-screen 1 --force-ffplay
```

### **Command Line Arguments**

| Argument | Required | Description | Example |
|----------|----------|-------------|---------|
| `--server` | ✅ | Server URL | `http://192.168.1.100:5000` |
| `--hostname` | ✅ | Unique client identifier | `rpi-client-1` |
| `--display-name` | ✅ | Display name for admin interface | `"Left Screen"` |
| `--target-screen` | ✅ | Target screen (1 or 2) | `1` |
| `--force-ffplay` | ❌ | Force ffplay instead of smart selection | |
| `--debug` | ❌ | Enable debug logging | |

## 🔍 How Single-Threaded Architecture Works

### **Optimized for Raspberry Pi**
The client uses a single-threaded architecture for maximum efficiency:

1. **Single Client**: Uses 1 main thread for all operations
2. **Multiple Clients**: Each runs in separate process with 1 thread each
3. **No Thread Contention**: Eliminates context switching overhead

### **Architecture Benefits**
- **Resource Efficiency**: Minimal CPU and memory usage
- **Stable Performance**: No thread synchronization issues
- **Pi Optimized**: Perfect for single-core and multi-core Raspberry Pi devices
- **Simple Management**: Easy to debug and monitor

### **Thread Architecture**
```
Main Client Thread (All Operations)
    ├── Server Communication (non-blocking)
    ├── Video Playback Management
    ├── Stream Monitoring
    └── Process Supervision
```

### **Why Single-Threaded?**
- **Raspberry Pi Limitation**: Limited threads available
- **Performance**: No context switching overhead
- **Reliability**: Simpler, more stable operation
- **Resource Usage**: Lower memory and CPU consumption

## 🐛 Common Errors & Solutions

### **1. Python Import Errors**

#### **Error**: `ModuleNotFoundError: No module named 'requests'`
**Solution**:
```bash
python3 -m pip install --user requests
```

#### **Error**: `ModuleNotFoundError: No module named 'tkinter'`
**Solution**:
```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# CentOS/RHEL/Fedora
sudo yum install python3-tkinter
```

### **2. Display Errors**

#### **Error**: `DISPLAY not set`
**Solution**:
```bash
export DISPLAY=:0.0
echo 'export DISPLAY=:0.0' >> ~/.bashrc
```

#### **Error**: `Cannot connect to X server`
**Solution**:
```bash
# Start X server
startx

# Or connect to existing server
export DISPLAY=:0.0
```

### **3. Permission Errors**

#### **Error**: `Permission denied: 'client.py'`
**Solution**:
```bash
chmod +x client.py
```

#### **Error**: `Cannot open display`
**Solution**:
```bash
# Check if running in X11
xset q

# If not, start X server or connect to existing one
```

### **4. Network Errors**

#### **Error**: `Connection refused`
**Solution**:
- Verify server is running
- Check server URL and port
- Ensure firewall allows connections
- Test with: `curl http://YOUR_SERVER:5000`

#### **Error**: `Timeout`
**Solution**:
- Check network stability
- Increase timeout values if needed
- Verify server response time

### **5. Video Player Errors**

#### **Error**: `ffplay not found`
**Solution**:
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# CentOS/RHEL/Fedora
sudo yum install ffmpeg
```

#### **Error**: `C++ player build failed`
**Solution**:
- Install build tools: `sudo apt-get install build-essential cmake`
- Check C++ source code availability
- Client will automatically fallback to ffplay

## 🚨 Client Crashes & Recovery

### **Immediate Actions**

1. **Check client status**
   ```bash
   ps aux | grep client.py
   ```

2. **Check logs**
   ```bash
   tail -f ~/client_logs/client.log
   ```

3. **Restart client**
   ```bash
   # Kill existing process
   pkill -f client.py
   
   # Restart
   python3 client.py --server http://YOUR_SERVER:5000 \
     --hostname client1 --display-name "Screen1" \
     --target-screen 1
   ```

### **Common Crash Causes**

#### **1. Memory Issues**
**Symptoms**: Client stops responding, high memory usage
**Solutions**:
```bash
# Check memory usage
free -h
htop

# Restart client
pkill -f client.py
python3 client.py [your-args]
```

#### **2. Network Issues**
**Symptoms**: Connection lost, timeout errors
**Solutions**:
```bash
# Test network connectivity
ping YOUR_SERVER_IP
curl http://YOUR_SERVER:5000

# Restart with retry
python3 client.py [your-args]
```

#### **3. Display Issues**
**Symptoms**: X11 errors, display not accessible
**Solutions**:
```bash
# Check display
xset q

# Restart X server if needed
sudo systemctl restart display-manager

# Or restart client
python3 client.py [your-args]
```

#### **4. Resource Exhaustion**
**Symptoms**: High CPU usage, slow response
**Solutions**:
```bash
# Check system resources
htop
df -h

# Restart client
pkill -f client.py
python3 client.py [your-args]
```

### **Automatic Recovery**

The client includes automatic recovery features:

1. **Automatic Reconnection** - Reconnects to server on network issues
2. **Stream Recovery** - Automatically restarts video streams
3. **Error Handling** - Graceful degradation on errors
4. **Resource Cleanup** - Proper cleanup on crashes

### **Prevention Strategies**

1. **Regular Monitoring**
   ```bash
   # Check client status
   ps aux | grep client.py
   
   # Monitor logs
   tail -f ~/client_logs/client.log
   ```

2. **Resource Limits**
   ```bash
   # Set memory limits
   ulimit -v 2097152  # 2GB virtual memory
   
   # Set CPU limits
   ulimit -t 3600     # 1 hour CPU time
   ```

3. **Scheduled Restarts**
   ```bash
   # Add to crontab for daily restart
   (crontab -l 2>/dev/null; echo "0 3 * * * pkill -f client.py && sleep 10 && cd /path/to/client && python3 client.py [your-args]") | crontab -
   ```

## 📊 Monitoring & Debugging

### **Status Information**

Get detailed client status:
```python
# In Python
status = client.get_player_status()
print(f"Multithreading: {status['multithreading_enabled']}")
print(f"Thread Running: {status['thread_running']}")
print(f"Player PID: {status['player_process']}")
```

### **Logging**

Enable debug logging:
```bash
python3 client.py --server http://YOUR_SERVER:5000 \
  --hostname client1 --display-name "Screen1" \
  --target-screen 1 --debug
```

Log locations:
- **Client logs**: `~/client_logs/`
- **System logs**: `/var/log/syslog` or `/var/log/messages`
- **X11 logs**: `~/.xsession-errors`

### **Performance Monitoring**

```bash
# Monitor CPU and memory
htop

# Monitor network
iftop

# Monitor disk I/O
iotop

# Monitor processes
ps aux | grep client.py
```

## 🔧 Troubleshooting Guide

### **Client Won't Start**

1. **Check Python version**
   ```bash
   python3 --version  # Should be 3.7+
   ```

2. **Check dependencies**
   ```bash
   python3 -c "import requests, tkinter, subprocess, threading"
   ```

3. **Check permissions**
   ```bash
   ls -la client.py
   chmod +x client.py
   ```

4. **Check display**
   ```bash
   echo $DISPLAY
   xset q
   ```

### **Video Not Playing**

1. **Check ffmpeg**
   ```bash
   ffmpeg -version
   ```

2. **Check stream URL**
   ```bash
   curl -I YOUR_STREAM_URL
   ```

3. **Check player processes**
   ```bash
   ps aux | grep ffplay
   ps aux | grep player
   ```

4. **Check logs**
   ```bash
   tail -f ~/client_logs/client.log
   ```

### **Multithreading Not Working**

1. **Check detection**
   ```bash
   pgrep -f client.py
   w -h
   ```

2. **Check client status**
   ```bash
   # Look for "MULTITHREADING: Enabled" in output
   python3 client.py --help
   ```

3. **Force multithreading test**
   ```bash
   # Start two clients in different terminals
   # Second client should show multithreading enabled
   ```

### **Performance Issues**

1. **Check system resources**
   ```bash
   htop
   free -h
   df -h
   ```

2. **Check network**
   ```bash
   ping YOUR_SERVER_IP
   iperf3 -c YOUR_SERVER_IP
   ```

3. **Optimize settings**
   ```bash
   # Use debug mode to see detailed info
   python3 client.py --debug [your-args]
   ```

## 📚 Advanced Configuration

### **Environment Variables**

```bash
# Set display
export DISPLAY=:0.0

# Set Python path
export PYTHONPATH=/path/to/client:$PYTHONPATH

# Set log level
export CLIENT_LOG_LEVEL=DEBUG
```

### **Configuration Files**

Create `~/.client_config`:
```bash
# Client configuration
CLIENT_LOG_LEVEL=INFO
CLIENT_LOG_FILE=~/client_logs/client.log
CLIENT_TIMEOUT=30
CLIENT_RETRY_COUNT=5
```

### **Systemd Service**

Create `/etc/systemd/system/video-client.service`:
```ini
[Unit]
Description=Video Wall Client
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/client
ExecStart=/usr/bin/python3 client.py --server http://YOUR_SERVER:5000 --hostname client1 --display-name "Screen1" --target-screen 1
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable video-client.service
sudo systemctl start video-client.service
```

## 🆘 Getting Help

### **Before Asking for Help**

1. **Check this README** for common solutions
2. **Enable debug mode** and check logs
3. **Verify system requirements** are met
4. **Test with minimal configuration**

### **Information to Provide**

When reporting issues, include:

1. **System Information**
   ```bash
   uname -a
   python3 --version
   ffmpeg -version
   ```

2. **Error Messages**
   - Full error output
   - Log files
   - Debug mode output

3. **Configuration**
   - Command line arguments
   - Server URL and settings
   - Network configuration

4. **Steps to Reproduce**
   - Exact commands run
   - Expected vs actual behavior
   - When the issue occurs

### **Support Channels**

- **Documentation**: This README
- **Logs**: Check `~/client_logs/` directory
- **Debug Mode**: Use `--debug` flag for detailed output
- **System Monitoring**: Use `htop`, `ps`, `netstat` commands

## 📝 Changelog

### **Version 2.1 (Current)**
- ✅ **Single-threaded architecture for Raspberry Pi efficiency**
- ✅ **Simplified target screen parameter (1 or 2 only)**
- ✅ **Enhanced error handling and recovery**
- ✅ **Improved resource management**
- ✅ **Optimized for single-core and multi-core Pi devices**

### **Version 2.0 (Previous)**
- Automatic multithreading detection
- VideoPlayerThread class for synchronized playback
- Complex threading architecture

### **Version 1.0 (Initial)**
- Basic client functionality
- Manual window positioning
- Single-threaded video playback

## 📄 License

This project is part of the UB Intern video wall system.

---

**Need help?** Check this README first, then enable debug mode and check the logs for detailed information.
