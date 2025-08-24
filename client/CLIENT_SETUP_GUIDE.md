# Complete Multi-Screen Client Setup Guide
## From Fresh Raspberry Pi to Running Video Wall Client

This guide will take you from a factory-fresh Raspberry Pi to a fully working dual-screen video wall client with automatic positioning.

---

## Table of Contents
1. [Initial Raspberry Pi Setup](#1-initial-raspberry-pi-setup)
2. [System Configuration](#2-system-configuration)
3. [Display System Setup](#3-display-system-setup)
4. [Dual HDMI Configuration](#4-dual-hdmi-configuration)
5. [Installing Dependencies](#5-installing-dependencies)
6. [Testing the Setup](#6-testing-the-setup)
7. [Running the Client](#7-running-the-client)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Initial Raspberry Pi Setup

### **Hardware Requirements:**
- Raspberry Pi 5 (recommended) or Raspberry Pi 4
- MicroSD card (32GB+ recommended)
- Two HDMI displays/monitors
- Two HDMI cables
- Keyboard and mouse (for initial setup)
- Ethernet cable or WiFi connection

### **Install Raspberry Pi OS:**

1. **Download Raspberry Pi Imager:**
   - Go to https://www.raspberrypi.org/software/
   - Download and install Raspberry Pi Imager

2. **Flash the OS:**
   - Insert your MicroSD card
   - Open Raspberry Pi Imager
   - Choose "Raspberry Pi OS (64-bit)" (recommended)
   - Select your MicroSD card
   - Click "Write"

3. **First Boot:**
   - Insert SD card into Raspberry Pi
   - Connect HDMI cable to **HDMI0** port (the one closest to USB-C power)
   - Connect keyboard, mouse, and power
   - Boot and follow the welcome wizard

4. **Complete Initial Setup:**
   - Set country, language, timezone
   - Create user account (remember this username)
   - Connect to WiFi or Ethernet
   - Update software when prompted

---

## 2. System Configuration

### **Update the System:**
```bash
sudo apt update && sudo apt upgrade -y
```

### **Enable SSH (Optional but Recommended):**
```bash
sudo systemctl enable ssh
sudo systemctl start ssh
```

### **Install Essential Tools:**
```bash
sudo apt install -y git curl wget vim nano
```

---

## 3. Display System Setup

### **Switch to X11 (Required for Window Management):**

The multi-screen client works best with X11 instead of Wayland for reliable window positioning.

1. **Open Raspberry Pi Configuration:**
   ```bash
   sudo raspi-config
   ```

2. **Navigate to Advanced Options:**
   - Select "6 Advanced Options"
   - Select "A6 Wayland"
   - Choose "X11" 
   - Select "OK"
   - Choose "Finish"

3. **Reboot to Apply Changes:**
   ```bash
   sudo reboot
   ```

4. **Verify X11 is Active:**
   After reboot, check:
   ```bash
   echo $XDG_SESSION_TYPE
   # Should show: x11
   ```

---

## 4. Dual HDMI Configuration

### **Enable Dual HDMI Support:**

1. **Open Raspberry Pi Configuration:**
   ```bash
   sudo raspi-config
   ```

2. **Enable Advanced Display Options:**
   - Select "2 Display Options"
   - Select "D3 Composite" 
   - Choose "No" (disable composite)
   - Select "OK"

3. **Configure Boot Options:**
   - Go back to main menu
   - Select "6 Advanced Options"
   - Select "A1 Expand Filesystem"
   - Select "OK"

4. **Manual Boot Config (Alternative Method):**
   If raspi-config doesn't have the option, edit manually:
   ```bash
   sudo nano /boot/config.txt
   ```
   
   Add these lines at the end:
   ```
   # Dual HDMI Configuration
   dtoverlay=vc4-kms-v3d
   max_framebuffers=2
   disable_fw_kms_setup=1
   disable_overscan=1
   ```

5. **Reboot to Apply HDMI Changes:**
   ```bash
   sudo reboot
   ```

6. **Connect Both Displays:**
   - Connect first display to **HDMI0** (closest to USB-C power)
   - Connect second display to **HDMI1** (closest to Ethernet port)
   - Both displays should now work

7. **Verify Dual HDMI Setup:**
   ```bash
   xrandr --listmonitors
   ```
   
   You should see something like:
   ```
   Monitors: 2
    0: +*HDMI-1 1920/598x1080/336+0+0  HDMI-1
    1: +HDMI-2 1920/531x1080/299+1920+0  HDMI-2
   ```

---

## 5. Installing Dependencies

### **Install Required Packages:**

```bash
# Update package list
sudo apt update

# Install video and window management tools
sudo apt install -y ffmpeg wmctrl xdotool python3-tk x11-apps

# Install development tools (optional, for C++ player)
sudo apt install -y build-essential cmake git

# Install Python requirements
sudo apt install -y python3-pip python3-requests
```

### **Verify Installation:**
```bash
# Test each tool
ffplay --version
wmctrl --version
xdotool --version
python3 -c "import tkinter; print('✓ tkinter works')"
python3 -c "import requests; print('✓ requests works')"
```

---

## 6. Testing the Setup

### **Test Display Configuration:**
```bash
# Check monitor layout
xrandr --listmonitors

# List available outputs
xrandr --listoutputs
```

### **Test Video Playback on Each Monitor:**

**Test HDMI1 (Left Monitor):**
```bash
ffplay -f lavfi -i testsrc2=size=1920x1080:rate=30 \
  -window_title "Test HDMI1" -x 1920 -y 1080 -left 0 -top 0 -t 5
```

**Test HDMI2 (Right Monitor):**
```bash
ffplay -f lavfi -i testsrc2=size=1920x1080:rate=30 \
  -window_title "Test HDMI2" -x 1920 -y 1080 -left 1920 -top 0 -t 5
```

You should see:
- Test pattern on left monitor (HDMI1) for 5 seconds
- Test pattern on right monitor (HDMI2) for 5 seconds

### **Test Window Movement:**
```bash
# Open a test window
xeyes &

# Get the window ID
wmctrl -l

# Move window to right monitor (replace WINDOW_ID with actual ID)
wmctrl -ir WINDOW_ID -e 0,1920,0,-1,-1

# Move window to left monitor
wmctrl -ir WINDOW_ID -e 0,0,0,-1,-1

# Close test window
pkill xeyes
```

---

## 7. Running the Client

### **Download/Setup Your Client:**

1. **Create Project Directory:**
   ```bash
   mkdir -p ~/multiscreen-client
   cd ~/multiscreen-client
   ```

2. **Place Your Enhanced client.py:**
   - Copy your enhanced `client.py` file to this directory
   - Make sure it includes the `--target-screen` functionality

3. **Verify Client Syntax:**
   ```bash
   python3 -m py_compile client.py
   echo "✓ Client syntax is valid"
   ```

### **Run the Client:**

**Terminal 1 - HDMI1 (Left Monitor):**
```bash
python3 client.py \
  --server http://YOUR_SERVER_IP:5000 \
  --hostname rpi-client-1 \
  --display-name "HDMI-1" \
  --target-screen HDMI1
```

**Terminal 2 - HDMI2 (Right Monitor):**
```bash
python3 client.py \
  --server http://YOUR_SERVER_IP:5000 \
  --hostname rpi-client-2 \
  --display-name "HDMI-2" \
  --target-screen HDMI2
```

### **What Should Happen:**

1. **Registration:** Each client connects to the server
2. **Assignment:** Admin assigns clients to groups/streams via web interface
3. **Auto-Positioning:** Video automatically appears on the correct monitor
4. **Playback:** Synchronized video streams play on both displays

### **Hotkey Controls (While Running):**
- **Ctrl+1:** Move video to left monitor (HDMI1)
- **Ctrl+2:** Move video to right monitor (HDMI2)
- **Ctrl+M:** Move to next monitor
- **Ctrl+H:** Show help

---

## 8. Troubleshooting

### **Common Issues and Solutions:**

#### **Issue: Only one monitor works**
**Solution:**
```bash
# Check HDMI connections are secure
# Verify both displays are powered on
# Check boot config:
grep "dtoverlay=vc4-kms-v3d" /boot/config.txt

# If missing, add it:
echo "dtoverlay=vc4-kms-v3d" | sudo tee -a /boot/config.txt
sudo reboot
```

#### **Issue: Window positioning doesn't work**
**Solution:**
```bash
# Verify X11 is active:
echo $XDG_SESSION_TYPE  # Should show "x11"

# If showing "wayland", switch to X11:
sudo raspi-config
# Advanced Options → Wayland → X11 → Reboot

# Test window tools:
wmctrl --version
xdotool --version
```

#### **Issue: "command not found" errors**
**Solution:**
```bash
# Install missing packages:
sudo apt update
sudo apt install -y ffmpeg wmctrl xdotool python3-tk
```

#### **Issue: Client won't connect to server**
**Solution:**
```bash
# Test network connectivity:
ping YOUR_SERVER_IP

# Test server accessibility:
curl -I http://YOUR_SERVER_IP:5000

# Check firewall:
sudo ufw status
```

#### **Issue: Video has decode errors**
**Solution:**
```bash
# Test with a simple stream:
ffplay http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4

# Check network bandwidth
# Verify server stream quality
```

### **Debug Mode:**
Run client with debug logging:
```bash
python3 client.py \
  --server http://YOUR_SERVER_IP:5000 \
  --hostname rpi-client-1 \
  --display-name "HDMI-1" \
  --target-screen HDMI1 \
  --debug
```

### **Check System Status:**
```bash
# Display configuration:
xrandr --listmonitors
xrandr --listoutputs

# Running processes:
ps aux | grep python3

# Window list:
wmctrl -l

# System resources:
htop
```

---

## Summary Checklist

- [ ] **Fresh Raspberry Pi OS installed and updated**
- [ ] **X11 display system configured (not Wayland)**
- [ ] **Dual HDMI enabled in boot config**
- [ ] **Both monitors detected and working**
- [ ] **All dependencies installed (ffmpeg, wmctrl, xdotool, etc.)**
- [ ] **Video test works on both monitors**
- [ ] **Window movement test works**
- [ ] **Enhanced client.py with --target-screen functionality**
- [ ] **Network connectivity to server confirmed**
- [ ] **Both client instances can connect and register**

## Quick Reference Commands

```bash
# Check display system
echo $XDG_SESSION_TYPE

# List monitors
xrandr --listmonitors

# Test video on HDMI1
ffplay -f lavfi -i testsrc2=size=1920x1080:rate=30 -left 0 -top 0 -t 3

# Test video on HDMI2  
ffplay -f lavfi -i testsrc2=size=1920x1080:rate=30 -left 1920 -top 0 -t 3

# Run client on HDMI1
python3 client.py --server http://SERVER:5000 --hostname client-1 --display-name "HDMI-1" --target-screen HDMI1

# Run client on HDMI2
python3 client.py --server http://SERVER:5000 --hostname client-2 --display-name "HDMI-2" --target-screen HDMI2
```

---

**Your dual-screen video wall client is now ready!** 🎉

The video streams will automatically position themselves on the correct monitors, and you can use hotkeys to move them if needed. The setup provides reliable, synchronized video playback across multiple displays with precise window management.
