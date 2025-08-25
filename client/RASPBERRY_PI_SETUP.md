# Raspberry Pi Setup Guide

Complete setup guide for running the Multi-Screen Video Streaming Client on a fresh Raspberry Pi installation.

## Prerequisites

- Raspberry Pi 4B (recommended) or Raspberry Pi 3B+
- MicroSD card (16GB+ recommended)
- Power supply (5V/3A recommended for Pi 4B)
- Network connection (Ethernet or WiFi)
- Monitor/display for initial setup

## Step 1: Install Raspberry Pi OS

### Download and Flash
1. **Download Raspberry Pi Imager** from [raspberrypi.com](https://www.raspberrypi.com/software/)
2. **Insert microSD card** into your computer
3. **Open Raspberry Pi Imager**
4. **Choose OS**: Select "Raspberry Pi OS (64-bit)" (recommended)
5. **Choose Storage**: Select your microSD card
6. **Click Write** and wait for completion

### First Boot Configuration
1. **Insert microSD card** into Raspberry Pi
2. **Connect power, monitor, and keyboard**
3. **Wait for first boot** (may take several minutes)
4. **Complete initial setup**:
   - Set country, language, and timezone
   - Create username and password
   - Connect to WiFi (if using wireless)
   - Update system software when prompted

## Step 2: System Update and Configuration

### Update System
```bash
# Update package list and upgrade packages
sudo apt update && sudo apt upgrade -y

# Reboot to ensure all updates are applied
sudo reboot
```

### Enable Required Services
```bash
# Enable SSH (for remote access)
sudo raspi-config
# Navigate to: Interface Options > SSH > Enable

# Enable VNC (optional, for remote desktop)
sudo raspi-config
# Navigate to: Interface Options > VNC > Enable

# Enable I2C (if using hardware displays)
sudo raspi-config
# Navigate to: Interface Options > I2C > Enable
```

### Configure Display (if using multiple monitors)
```bash
# Check current display configuration
xrandr --listmonitors

# Configure displays in raspi-config
sudo raspi-config
# Navigate to: Display Options > Screen Configuration
```

## Step 3: Install Required Software

### Install System Dependencies
```bash
# Install essential packages
sudo apt install -y \
    git \
    python3 \
    python3-pip \
    python3-dev \
    ffmpeg \
    vim \
    htop \
    curl \
    wget

# Verify installations
python3 --version
ffmpeg -version
```

### Install Python Packages
```bash
# Upgrade pip
python3 -m pip install --upgrade pip

# Install required Python packages
pip3 install --user requests
```

## Step 4: Clone and Setup Client

### Clone Repository
```bash
# Navigate to home directory
cd ~

# Clone the repository
git clone https://github.com/Sira-K/Multiscreen
cd UB_Intern

# Make setup script executable
chmod +x client/setup_client.sh
```

### Run Setup Script
```bash
# Navigate to client directory
cd client

# Run the automatic setup script
./setup_client.sh

# The script will:
# - Verify all dependencies are installed
# - Test the client installation
# - Provide usage instructions
```

## Step 5: Configure Network

### Static IP (Recommended for Video Streaming)
```bash
# Edit network configuration
sudo nano /etc/dhcpcd.conf

# Add at the end (adjust for your network):
interface eth0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=8.8.8.8 8.8.4.4

# Save and exit (Ctrl+X, Y, Enter)
# Restart networking
sudo systemctl restart dhcpcd
```

### Firewall Configuration
```bash
# Install ufw if not present
sudo apt install -y ufw

# Allow SSH and HTTP
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443

# Enable firewall
sudo ufw enable
```

## Step 6: Test Client Installation

### Basic Test
```bash
# Test client import
python3 -c "import client; print('Client import successful')"

# Test ffplay
ffplay -version

# Test network connectivity
ping -c 4 8.8.8.8
```

### Run Client (Test Mode)
```bash
# Test client with a local server (if available)
python3 client.py --server http://localhost:5000 --hostname test-pi --display-name "Test Display"

# Or test with external server
python3 client.py --server http://your-server-ip:5000 --hostname pi1 --display-name "Display 1"
```

## Step 7: Performance Optimization

### Overclock (Optional - Pi 4B only)
```bash
# Edit config file
sudo nano /boot/config.txt

# Add these lines (adjust values based on your cooling):
over_voltage=2
arm_freq=1750
gpu_freq=600

# Save and reboot
sudo reboot
```

### Memory and GPU Configuration
```bash
# Edit config file
sudo nano /boot/config.txt

# Add these lines:
gpu_mem=128
gpu_mem_256=128
gpu_mem_512=128
gpu_mem_1024=128

# Save and reboot
sudo reboot
```

### Disable Unnecessary Services
```bash
# Disable Bluetooth (if not needed)
sudo systemctl disable bluetooth

# Disable WiFi (if using Ethernet)
sudo systemctl disable wpa_supplicant

# Disable desktop (if running headless)
sudo systemctl set-default multi-user.target
```

## Step 8: Monitoring and Maintenance

### System Monitoring
```bash
# Install monitoring tools
sudo apt install -y htop iotop nethogs

# Monitor system resources
htop
iotop
nethogs
```

### Log Management
```bash
# View client logs
tail -f ~/client_logs/client.log

# View system logs
journalctl -f

# Monitor network connections
ss -tulpn
```

### Automatic Updates (Optional)
```bash
# Install unattended-upgrades
sudo apt install -y unattended-upgrades

# Configure automatic security updates
sudo dpkg-reconfigure -plow unattended-upgrades
```

## Step 9: Running Multiple Clients

### Multiple Terminals
```bash
# Terminal 1 - Client for Display 1
python3 client.py --server http://your-server:5000 --hostname pi1 --display-name "Display 1" &

# Terminal 2 - Client for Display 2
python3 client.py --server http://your-server:5000 --hostname pi2 --display-name "Display 2" &

# Check running processes
ps aux | grep "python3 client.py"
```

### Screen Sessions (Recommended for Production)
```bash
# Install screen
sudo apt install -y screen

# Create screen session for client 1
screen -S client1
python3 client.py --server http://your-server:5000 --hostname pi1 --display-name "Display 1"

# Detach from session (Ctrl+A, D)

# Create screen session for client 2
screen -S client2
python3 client.py --server http://your-server:5000 --hostname pi2 --display-name "Display 2"

# Detach from session (Ctrl+A, D)

# List sessions
screen -ls

# Reattach to session
screen -r client1
```

## Step 10: Troubleshooting

### Common Issues

#### Client Won't Start
```bash
# Check Python version
python3 --version

# Check dependencies
pip3 list | grep requests

# Check ffplay
which ffplay

# Check network
ping your-server-ip
```

#### Video Playback Issues
```bash
# Check display permissions
echo $DISPLAY

# Test ffplay manually
ffplay -fs test-video.mp4

# Check GPU memory
vcgencmd get_mem gpu

# Check temperature
vcgencmd measure_temp
```

#### Network Issues
```bash
# Check network configuration
ip addr show

# Check routing
ip route show

# Test DNS
nslookup your-server-domain

# Check firewall
sudo ufw status
```

### Performance Issues
```bash
# Check CPU usage
top

# Check memory usage
free -h

# Check disk I/O
iostat

# Check network I/O
iftop
```

## Step 11: Production Deployment

### Systemd Service (Recommended)
```bash
# Create service file
sudo nano /etc/systemd/system/video-client.service

# Add content:
[Unit]
Description=Video Streaming Client
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/UB_Intern/client
ExecStart=/usr/bin/python3 client.py --server http://your-server:5000 --hostname pi1 --display-name "Display 1"
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable video-client
sudo systemctl start video-client

# Check status
sudo systemctl status video-client
```

### Auto-start on Boot
```bash
# Add to rc.local
sudo nano /etc/rc.local

# Add before "exit 0":
cd /home/pi/UB_Intern/client
python3 client.py --server http://your-server:5000 --hostname pi1 --display-name "Display 1" &
python3 client.py --server http://your-server:5000 --hostname pi2 --display-name "Display 2" &
```

## Step 12: Security Considerations

### User Permissions
```bash
# Create dedicated user for video client
sudo adduser videoclient
sudo usermod -aG video videoclient

# Switch to dedicated user
su - videoclient
```

### Network Security
```bash
# Configure firewall rules
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow from your-server-ip to any port 22
sudo ufw allow from your-server-ip to any port 80
sudo ufw allow from your-server-ip to any port 443
```

### Regular Updates
```bash
# Set up automatic updates
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades

# Schedule regular reboots
sudo crontab -e
# Add: 0 3 * * 0 /sbin/reboot
```

## Support and Resources

### Documentation
- [Raspberry Pi Documentation](https://www.raspberrypi.com/documentation/)
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
- [Python Documentation](https://docs.python.org/)

### Community
- [Raspberry Pi Forums](https://forums.raspberrypi.com/)
- [Stack Overflow](https://stackoverflow.com/questions/tagged/raspberry-pi)

### Monitoring Tools
- **htop**: Process monitoring
- **iotop**: Disk I/O monitoring
- **nethogs**: Network usage monitoring
- **vcgencmd**: Raspberry Pi specific commands

## Quick Reference Commands

```bash
# Start client
python3 client.py --server http://server:5000 --hostname pi1 --display-name "Display 1"

# Check client status
ps aux | grep "python3 client.py"

# View logs
tail -f ~/client_logs/client.log

# Monitor system
htop

# Check temperature
vcgencmd measure_temp

# Check GPU memory
vcgencmd get_mem gpu

# Restart networking
sudo systemctl restart dhcpcd

# Update system
sudo apt update && sudo apt upgrade -y
```

## Next Steps

After completing this setup:

1. **Test with your streaming server**
2. **Configure multiple displays** if needed
3. **Set up monitoring and logging**
4. **Implement automatic restart** on failures
5. **Consider backup strategies** for configuration

Your Raspberry Pi is now ready for production video streaming!
