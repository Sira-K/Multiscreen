# Multi-Screen Client - Wayland Version

This is the **Wayland-compatible version** of the Unified Multi-Screen Client for Video Wall Systems. It's designed to work with modern Linux systems that use Wayland instead of X11.

## What's Different from X11 Version?

### **Display Management**
- **X11**: Uses `DISPLAY=:0.0`, `:1.0` for different screens
- **Wayland**: Uses `WAYLAND_DISPLAY=wayland-0` with output names like `HDMI-A-1`, `HDMI-A-2`

### **Window Management**
- **X11**: Uses `wmctrl`, `xdotool` for window manipulation
- **Wayland**: Uses `ydotool`, `wtype` for Wayland-compatible window control

### **Output Detection**
- **X11**: Uses `xrandr` to detect displays
- **Wayland**: Uses `wlr-randr`, `swaymsg`, or `weston-info` to detect outputs

## Prerequisites

### **1. Wayland Session**
Make sure you're running in a Wayland session:
```bash
echo $XDG_SESSION_TYPE
# Should show: wayland

echo $WAYLAND_DISPLAY
# Should show: wayland-0
```

### **2. Required Packages**
Install the necessary dependencies:
```bash
# Core dependencies
sudo apt install ffmpeg

# Wayland tools (at least one of these)
sudo apt install wlr-randr    # For wlroots-based compositors
sudo apt install sway          # For Sway compositor
sudo apt install weston        # For Weston compositor

# Window management tools (at least one of these)
sudo apt install ydotool       # Recommended for Wayland
sudo apt install wtype         # Alternative to ydotool
```

### **3. Dual HDMI Support**
For Raspberry Pi 5, ensure dual HDMI is enabled:
```bash
# Edit boot configuration
sudo nano /boot/config.txt

# Add or verify this line exists:
dtoverlay=vc4-kms-v3d

# Reboot to apply changes
sudo reboot
```

## Quick Setup

### **Option 1: Automated Setup**
Use the provided setup script:
```bash
# Make script executable
chmod +x setup_wayland.sh

# Run full setup
./setup_wayland.sh --server http://YOUR_SERVER_IP:5000

# Or just check configuration
./setup_wayland.sh --check-only
```

### **Option 2: Manual Setup**
Create launch scripts manually:

**HDMI1 Client (Primary):**
```bash
cat > launch_hdmi1_wayland.sh << 'EOF'
#!/bin/bash
export WAYLAND_DISPLAY=wayland-0
export XDG_SESSION_TYPE=wayland
export HDMI_OUTPUT=HDMI1

python3 client_wayland.py \
    --server http://YOUR_SERVER_IP:5000 \
    --hostname rpi-client-1 \
    --display-name "HDMI1" \
    --target-screen HDMI1
EOF

chmod +x launch_hdmi1_wayland.sh
```

**HDMI2 Client (Secondary):**
```bash
cat > launch_hdmi2_wayland.sh << 'EOF'
#!/bin/bash
export WAYLAND_DISPLAY=wayland-0
export XDG_SESSION_TYPE=wayland
export HDMI_OUTPUT=HDMI2

python3 client_wayland.py \
    --server http://YOUR_SERVER_IP:5000 \
    --hostname rpi-client-2 \
    --display-name "HDMI2" \
    --target-screen HDMI2
EOF

chmod +x launch_hdmi2_wayland.sh
```

## Usage

### **Basic Usage**
```bash
# Single HDMI setup
python3 client_wayland.py \
    --server http://192.168.1.100:5000 \
    --hostname rpi-client-1 \
    --display-name "Monitor 1"

# Dual HDMI setup
# Terminal 1 - HDMI1:
python3 client_wayland.py \
    --server http://192.168.1.100:5000 \
    --hostname rpi-client-1 \
    --display-name "HDMI1" \
    --target-screen HDMI1

# Terminal 2 - HDMI2:
python3 client_wayland.py \
    --server http://192.168.1.100:5000 \
    --hostname rpi-client-2 \
    --display-name "HDMI2" \
    --target-screen HDMI2
```

### **Alternative Syntax**
```bash
# Using display numbers
python3 client_wayland.py \
    --server http://192.168.1.100:5000 \
    --hostname rpi-client-1 \
    --display-name "Screen 1" \
    --target-screen 0

python3 client_wayland.py \
    --server http://192.168.1.100:5000 \
    --hostname rpi-client-2 \
    --display-name "Screen 2" \
    --target-screen 1
```

## Testing Your Setup

### **1. Test Wayland Outputs**
```bash
# Check available outputs
wlr-randr

# Or with Sway
swaymsg -t get_outputs

# Or with Weston
weston-info
```

### **2. Test Window Management**
```bash
# Test ydotool
ydotool --version

# Test wtype
wtype --version

# Test mouse movement
ydotool mousemove 100 100
```

### **3. Run Test Script**
Use the modified test script:
```bash
python3 test_dual_hdmi.py
```

## Troubleshooting

### **Common Issues**

#### **1. "Not running in Wayland session"**
```bash
# Check your session type
echo $XDG_SESSION_TYPE

# If it shows "x11", you need to switch to Wayland
# Edit GDM configuration:
sudo nano /etc/gdm3/custom.conf
# Add: WaylandEnable=true
# Reboot
```

#### **2. "No Wayland outputs detected"**
```bash
# Check if dual HDMI is enabled
grep "dtoverlay=vc4-kms-v3d" /boot/config.txt

# Check for Wayland compositor
ps aux | grep -E "(weston|sway)"

# Verify HDMI connections
ls /sys/class/drm/
```

#### **3. "Window management tools not found"**
```bash
# Install ydotool (recommended)
sudo apt install ydotool

# Or install wtype
sudo apt install wtype

# Test installation
ydotool --version
```

#### **4. "Tkinter window creation failed"**
This is **expected behavior** on Wayland. Tkinter doesn't work well with Wayland by default. The client will continue to function for video playback, but the hotkey window manager may not work properly.

### **Debug Mode**
Enable detailed logging:
```bash
python3 client_wayland.py \
    --server http://YOUR_SERVER_IP:5000 \
    --hostname client-1 \
    --display-name "Screen 1" \
    --debug
```

### **Check System Status**
```bash
# Run system check
./setup_wayland.sh --check-only

# Check Wayland environment
echo "WAYLAND_DISPLAY: $WAYLAND_DISPLAY"
echo "XDG_SESSION_TYPE: $XDG_SESSION_TYPE"

# Check available tools
which wlr-randr swaymsg weston-info ydotool wtype
```

## Systemd Services

### **Create Services**
The setup script automatically creates systemd services:
```bash
# Enable services (start on boot)
sudo systemctl enable multiscreen-wayland-hdmi1.service
sudo systemctl enable multiscreen-wayland-hdmi2.service

# Start services manually
sudo systemctl start multiscreen-wayland-hdmi1.service
sudo systemctl start multiscreen-wayland-hdmi2.service

# Check status
sudo systemctl status multiscreen-wayland-hdmi1.service
sudo systemctl status multiscreen-wayland-hdmi2.service
```

### **Service Logs**
```bash
# View logs
sudo journalctl -u multiscreen-wayland-hdmi1.service -f
sudo journalctl -u multiscreen-wayland-hdmi2.service -f
```

## Limitations

### **Known Issues**

1. **Tkinter Compatibility**: Tkinter windows may not display properly on Wayland
2. **Window Management**: Limited window manipulation compared to X11
3. **Hotkey Support**: May not work reliably on all Wayland setups
4. **Output Switching**: Monitor switching is more limited than X11 version

### **Workarounds**

1. **Use ydotool/wtype**: These provide better Wayland compatibility
2. **Focus on Video Playback**: The core video streaming functionality works well
3. **Manual Output Selection**: Use `--target-screen` to specify which HDMI output to use
4. **Systemd Services**: Use services for automatic startup instead of manual terminal management

## Migration from X11

### **If You're Switching from X11**

1. **Backup your X11 configuration**
2. **Install Wayland dependencies**
3. **Switch to Wayland session**
4. **Use the Wayland client instead of X11 client**
5. **Update your launch scripts and systemd services**

### **Command Comparison**

| X11 Command | Wayland Equivalent |
|-------------|-------------------|
| `DISPLAY=:0.0` | `WAYLAND_DISPLAY=wayland-0` |
| `xrandr --listmonitors` | `wlr-randr` or `swaymsg -t get_outputs` |
| `wmctrl -l` | `swaymsg -t get_tree` |
| `xdotool mousemove` | `ydotool mousemove` |

## Support

### **Getting Help**

1. **Check the troubleshooting section above**
2. **Run system diagnostics**: `./setup_wayland.sh --check-only`
3. **Enable debug mode**: Add `--debug` to client commands
4. **Check system logs**: `journalctl` for systemd services

### **Reporting Issues**

When reporting issues, include:
- Raspberry Pi model and OS version
- Wayland compositor (Weston/Sway/other)
- Output of `./setup_wayland.sh --check-only`
- Client debug logs with `--debug` flag
- System environment variables

## Files

- **`client_wayland.py`**: Main Wayland-compatible client
- **`test_dual_hdmi.py`**: Modified test script for Wayland
- **`setup_wayland.sh`**: Automated setup script
- **`README_WAYLAND.md`**: This documentation

## License

Same as the original multi-screen client project.

---

**Note**: This Wayland version is designed to provide compatibility with modern Linux systems while maintaining the core functionality of the multi-screen client. Some advanced features may work differently than the X11 version, but the essential video streaming and synchronization capabilities remain intact.
