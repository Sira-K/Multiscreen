# Dual HDMI Setup for Raspberry Pi 5

This guide explains how to set up and use the modified multi-screen client to display video streams on both HDMI outputs of a Raspberry Pi 5.

## Overview

The modified client now supports targeting specific HDMI outputs, allowing you to run two separate client instances that will display streams on different screens simultaneously.

## Prerequisites

- Raspberry Pi 5 with dual HDMI outputs
- Raspberry Pi OS (Bullseye or newer)
- Python 3.7+
- ffmpeg/ffplay
- X11 server running on both displays

## Hardware Setup

### 1. Enable Dual HDMI

Ensure dual HDMI is enabled in your Raspberry Pi configuration:

```bash
# Edit boot configuration
sudo nano /boot/config.txt

# Add or verify this line exists:
dtoverlay=vc4-kms-v3d

# Reboot to apply changes
sudo reboot
```

### 2. Connect Displays

- Connect your first display to HDMI1 (primary)
- Connect your second display to HDMI2 (secondary)

## Software Setup

### 1. Install Dependencies

```bash
# Update package list
sudo apt update

# Install required packages
sudo apt install -y ffmpeg wmctrl xdotool xrandr

# Verify installations
ffplay --version
xrandr --version
```

### 2. Verify Display Configuration

Check if both displays are detected:

```bash
# List all monitors
xrandr --listmonitors

# List all outputs
xrandr --listoutputs

# Check X11 displays
ps aux | grep X
```

You should see both HDMI outputs listed.

### 3. Test Displays

Test both displays to ensure they're working:

```bash
# Test HDMI1 (Display :0.0)
DISPLAY=:0.0 xeyes &

# Test HDMI2 (Display :1.0)
DISPLAY=:1.0 xeyes &

# Kill test applications
pkill xeyes
```

## Quick Setup

### Option 1: Automated Setup Script

Use the provided setup script for easy configuration:

```bash
# Make script executable
chmod +x setup_dual_hdmi.sh

# Run full setup
./setup_dual_hdmi.sh --server http://YOUR_SERVER_IP:5000

# Or just check configuration
./setup_dual_hdmi.sh --check-only
```

The script will:
- Check your system configuration
- Test both displays
- Create launch scripts
- Optionally create systemd services

### Option 2: Manual Setup

If you prefer manual setup, follow these steps:

#### Step 1: Create Launch Scripts

**launch_hdmi1.sh** (for HDMI1):
```bash
#!/bin/bash
export DISPLAY=:0.0
export HDMI_OUTPUT=HDMI1

python3 client.py \
    --server http://YOUR_SERVER_IP:5000 \
    --hostname "rpi-client-1" \
    --display-name "HDMI1" \
    --target-screen HDMI1
```

**launch_hdmi2.sh** (for HDMI2):
```bash
#!/bin/bash
export DISPLAY=:1.0
export HDMI_OUTPUT=HDMI2

python3 client.py \
    --server http://YOUR_SERVER_IP:5000 \
    --hostname "rpi-client-2" \
    --display-name "HDMI2" \
    --target-screen HDMI2
```

Make them executable:
```bash
chmod +x launch_hdmi1.sh launch_hdmi2.sh
```

## Running the Clients

### Method 1: Manual Launch (Recommended for Testing)

Open two terminal windows and run:

**Terminal 1 (HDMI1):**
```bash
./launch_hdmi1.sh
```

**Terminal 2 (HDMI2):**
```bash
./launch_hdmi2.sh
```

### Method 2: Systemd Services (Recommended for Production)

If you used the setup script with systemd services:

```bash
# Enable services to start on boot
sudo systemctl enable multiscreen-hdmi1.service
sudo systemctl enable multiscreen-hdmi2.service

# Start services
sudo systemctl start multiscreen-hdmi1.service
sudo systemctl start multiscreen-hdmi2.service

# Check status
sudo systemctl status multiscreen-hdmi1.service
sudo systemctl status multiscreen-hdmi2.service

# View logs
sudo journalctl -u multiscreen-hdmi1.service -f
sudo journalctl -u multiscreen-hdmi2.service -f
```

## Command Line Options

The modified client supports these new options:

```bash
python3 client.py \
    --server http://YOUR_SERVER_IP:5000 \
    --hostname "client-name" \
    --display-name "Display Name" \
    --target-screen HDMI1    # or HDMI2, 0, 1, primary, secondary
    --hdmi-output HDMI1      # alternative to --target-screen
    --force-ffplay           # force ffplay instead of smart selection
```

### Target Screen Values

- `HDMI1` or `0` or `primary` → Display :0.0
- `HDMI2` or `1` or `secondary` → Display :1.0

## How It Works

### Display Targeting

1. **Client Initialization**: Each client determines its target display based on the `--target-screen` parameter
2. **Environment Setup**: The client sets `DISPLAY=:X.0` and `HDMI_OUTPUT=HDMIY` environment variables
3. **X11 Connection**: All X11 operations (tkinter, ffplay, etc.) use the specified display
4. **Stream Display**: Video streams appear on the targeted HDMI output

### Multiple Instances

- **Client 1** targets HDMI1 (Display :0.0)
- **Client 2** targets HDMI2 (Display :1.0)
- Each client operates independently on its assigned display
- Both streams can run simultaneously without interference

## Troubleshooting

### Common Issues

#### 1. "Display not available" Error

```bash
# Check if X11 server is running on the display
ps aux | grep X

# Test display manually
DISPLAY=:1.0 xrandr --listmonitors

# Verify HDMI connection
xrandr --listoutputs
```

#### 2. Permission Denied

```bash
# Check display permissions
ls -la /tmp/.X11-unix/

# Fix permissions if needed
xhost +local:
```

#### 3. No Such Display

```bash
# Check if dual HDMI is enabled
grep "dtoverlay=vc4-kms-v3d" /boot/config.txt

# Reboot if overlay was added
sudo reboot

# Verify displays after reboot
xrandr --listmonitors
```

#### 4. Stream Not Appearing

```bash
# Check client logs for errors
# Verify the client is using the correct display
echo $DISPLAY

# Test with a simple application
DISPLAY=:1.0 xeyes &
```

### Debug Mode

Run clients with debug logging:

```bash
python3 client.py \
    --server http://YOUR_SERVER_IP:5000 \
    --hostname "client-1" \
    --display-name "HDMI1" \
    --target-screen HDMI1 \
    --debug
```

### Display Verification

```bash
# Check current display configuration
xrandr --listmonitors

# Test specific displays
DISPLAY=:0.0 xrandr --listmonitors  # HDMI1
DISPLAY=:1.0 xrandr --listmonitors  # HDMI2

# Check X11 server processes
ps aux | grep X
```

## Advanced Configuration

### Custom Display Numbers

If you need to use different display numbers:

```bash
# Client 1 on display :2.0
python3 client.py \
    --server http://YOUR_SERVER_IP:5000 \
    --hostname "client-1" \
    --display-name "Display 1" \
    --target-screen 2

# Client 2 on display :3.0
python3 client.py \
    --server http://YOUR_SERVER_IP:5000 \
    --hostname "client-2" \
    --display-name "Display 2" \
    --target-screen 3
```

### Environment Variables

You can also set environment variables directly:

```bash
# HDMI1 client
export DISPLAY=:0.0
export HDMI_OUTPUT=HDMI1
python3 client.py --server http://YOUR_SERVER_IP:5000 \
    --hostname "client-1" --display-name "HDMI1"

# HDMI2 client
export DISPLAY=:1.0
export HDMI_OUTPUT=HDMI2
python3 client.py --server http://YOUR_SERVER_IP:5000 \
    --hostname "client-2" --display-name "HDMI2"
```

## Performance Considerations

### Resource Usage

- Each client instance uses separate processes
- Memory usage: ~50-100MB per client
- CPU usage depends on video decoding requirements
- Network bandwidth: depends on stream quality

### Optimization Tips

1. **Use C++ Player**: For SEI-enabled streams, the C++ player provides better synchronization
2. **Monitor Resources**: Use `htop` or `top` to monitor system resources
3. **Network**: Ensure stable network connection for smooth streaming
4. **Cooling**: Raspberry Pi 5 can get warm under load; ensure adequate cooling

## Monitoring and Maintenance

### Log Files

If using systemd services, logs are available via:

```bash
# View real-time logs
sudo journalctl -u multiscreen-hdmi1.service -f
sudo journalctl -u multiscreen-hdmi2.service -f

# View recent logs
sudo journalctl -u multiscreen-hdmi1.service --since "1 hour ago"
```

### Health Checks

```bash
# Check service status
sudo systemctl status multiscreen-hdmi1.service
sudo systemctl status multiscreen-hdmi2.service

# Check display status
xrandr --listmonitors
xrandr --listoutputs

# Test displays
DISPLAY=:0.0 xrandr --listmonitors
DISPLAY=:1.0 xrandr --listmonitors
```

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Run with `--debug` flag for detailed logging
3. Verify your hardware configuration
4. Check the main project documentation

## Changelog

### Version 3.0 (Dual HDMI Support)
- Added `--target-screen` and `--hdmi-output` parameters
- Automatic display environment configuration
- Support for multiple X11 displays
- Enhanced window management for specific displays
- Setup script for easy dual HDMI configuration
- Systemd service templates
- Comprehensive troubleshooting guide

---

**Note**: This dual HDMI setup is specifically designed for Raspberry Pi 5 and similar devices with multiple display outputs. The client will automatically detect and configure the appropriate display environment based on your parameters.

