#!/bin/bash

# Raspberry Pi SRT Client Automatic Setup Script
# Following hwsel's multi-screen project guidelines
# Author: Sira-K
# Compatible with: Raspberry Pi OS (64-bit) on Raspberry Pi 4B

set -e  # Exit on any error

# Configuration
PROJECT_NAME="multi-screen"
PROJECT_DIR="$HOME/multi-screen"  # Use $HOME instead of hardcoded /home/pi
SERVICE_NAME="srt-client"
SERVICE_USER="$USER"  # Use current user instead of hardcoded pi
SERVER_URL=""  # Will be set during setup
CLIENT_HOSTNAME=""  # Will be auto-generated
DISPLAY_NAME=""  # Will be set during setup
SYSTEM_TYPE=""  # Will be detected

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

# Check if running as root
check_user() {
    if [[ $EUID -eq 0 ]]; then
        error "This script should not be run as root. Please run as the pi user."
        exit 1
    fi
}

# Check system type and adapt accordingly
check_system() {
    if [[ -f /proc/device-tree/model ]] && grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
        local model=$(tr -d '\0' < /proc/device-tree/model)
        log "Detected: $model"
        SYSTEM_TYPE="raspberry_pi"
    elif grep -q "Ubuntu" /etc/os-release 2>/dev/null; then
        log "Detected: Ubuntu system"
        SYSTEM_TYPE="ubuntu"
    elif [[ -n "$WSL_DISTRO_NAME" ]]; then
        log "Detected: WSL Ubuntu environment"
        SYSTEM_TYPE="wsl"
    else
        log "Detected: Generic Linux system"
        SYSTEM_TYPE="generic"
    fi
}

# Update system packages with error handling
update_system() {
    log "Updating system packages..."
    
    # Fix broken repositories first
    log "Checking for broken repositories..."
    
    # Remove problematic PPA if it exists
    if [[ -f /etc/apt/sources.list.d/mc3man-ubuntu-trusty-media-jammy.list ]]; then
        warning "Removing broken mc3man PPA..."
        sudo rm -f /etc/apt/sources.list.d/mc3man-ubuntu-trusty-media-jammy.list
    fi
    
    # Try to update package lists
    if ! sudo apt update; then
        warning "Package update had issues, but continuing..."
    fi
    
    # Upgrade packages (optional on WSL/dev systems)
    if [[ "$SYSTEM_TYPE" == "raspberry_pi" ]]; then
        sudo apt upgrade -y
    else
        read -p "Upgrade all packages? This may take time on WSL/Ubuntu (y/N): " -r
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo apt upgrade -y
        fi
    fi
}

# Install required dependencies with system-specific adaptations
install_dependencies() {
    log "Installing build dependencies for $SYSTEM_TYPE..."
    
    # Essential build tools
    sudo apt install -y \
        build-essential \
        cmake \
        ninja-build \
        pkg-config \
        git \
        curl \
        wget \
        python3 \
        python3-pip \
        python3-venv
    
    # Development libraries (with fallbacks for different Ubuntu versions)
    log "Installing media libraries..."
    
    # Try to install FFmpeg development libraries
    if ! sudo apt install -y \
        libavformat-dev \
        libavcodec-dev \
        libavutil-dev \
        libswscale-dev \
        libavfilter-dev \
        libavdevice-dev; then
        warning "Some FFmpeg libraries unavailable. The build process will download them."
    fi
    
    # Try other libraries with fallbacks
    sudo apt install -y \
        libcurl4-openssl-dev \
        libssl-dev \
        zlib1g-dev || warning "Some SSL/curl libraries unavailable"
    
    # SDL2 for display (may not be needed on headless systems)
    if [[ "$SYSTEM_TYPE" != "wsl" ]]; then
        sudo apt install -y libsdl2-dev || warning "SDL2 not available - player may run in headless mode"
    fi
    
    # Modern JSON library
    sudo apt install -y nlohmann-json3-dev || warning "nlohmann-json not available - will be built from source"
    
    # Logging library
    sudo apt install -y libspdlog-dev || warning "spdlog not available - will be built from source"
    
    # Additional useful packages
    sudo apt install -y \
        htop \
        screen \
        rsync || warning "Some utility packages unavailable"
    
    # Python packages
    pip3 install --user requests psutil || warning "Some Python packages unavailable"
    
    log "Dependencies installation completed (some may have been skipped)"
}

# Clone the project repository
clone_project() {
    log "Cloning the multi-screen project..."
    
    if [[ -d "$PROJECT_DIR" ]]; then
        warning "Project directory already exists. Updating..."
        cd "$PROJECT_DIR"
        git pull origin main || git pull origin master || warning "Could not update repository"
    else
        # Clone your adapted repository (replace with your actual repo URL)
        git clone https://github.com/sira-k/multi-screen.git "$PROJECT_DIR" || \
        git clone https://github.com/hwsel/multi-screen.git "$PROJECT_DIR"
        cd "$PROJECT_DIR"
    fi
    
    log "Project cloned/updated successfully"
}

# Configure CMake and build the project
build_project() {
    log "Configuring CMake project..."
    cd "$PROJECT_DIR"
    
    # Check CMake version
    local cmake_version=$(cmake --version | head -n1 | grep -oE '[0-9]+\.[0-9]+' | head -n1)
    info "CMake version: $cmake_version"
    
    # Determine number of build jobs based on CPU cores
    local cpu_cores=$(nproc)
    local build_jobs=3
    if [[ $cpu_cores -lt 4 ]]; then
        build_jobs=3
    else
        build_jobs=$((cpu_cores - 1))  # Leave one core free
    fi
    
    log "Using $build_jobs build jobs for $cpu_cores CPU cores"
    
    # Configure CMake (following hwsel's guidelines)
    cmake \
        -DEP_BUILD_ALWAYS=1L \
        -DEP_J=$build_jobs \
        -DCMAKE_BUILD_TYPE=Debug \
        -DCMAKE_MAKE_PROGRAM=/usr/bin/ninja \
        -G Ninja \
        -S . \
        -B ./cmake-build-debug
    
    log "CMake configuration completed"
    
    # Build the client player
    log "Building the client player..."
    cmake \
        --build ./cmake-build-debug \
        --clean-first \
        --target player \
        -j $build_jobs
    
    # Verify the player was built
    if [[ -f "./cmake-build-debug/player/player" ]]; then
        log "Player built successfully"
        # Make sure it's executable
        chmod +x "./cmake-build-debug/player/player"
    else
        error "Player binary not found after build"
        exit 1
    fi
}

# Setup Python client
setup_python_client() {
    log "Setting up Python client..."
    cd "$PROJECT_DIR"
    
    # Check if client directory exists
    if [[ ! -d "client" ]]; then
        warning "Client directory not found. Creating basic client setup..."
        mkdir -p client
        
        # Create a basic client.py if it doesn't exist
        cat > client/client.py << 'EOF'
#!/usr/bin/env python3
"""
Basic SRT Client for Raspberry Pi
Connects to the multi-screen control server
"""

import argparse
import requests
import time
import logging
import subprocess
import sys
import os
import signal
import atexit
from pathlib import Path

class SRTClient:
    def __init__(self, server_url, hostname=None, display_name=None):
        self.server_url = server_url.rstrip('/')
        self.hostname = hostname or f"rpi-{int(time.time())}"
        self.display_name = display_name or self.hostname
        self.player_process = None
        self.running = True
        
        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Find player executable
        self.player_path = self._find_player()
        
    def _find_player(self):
        """Find the compiled player executable"""
        project_root = Path(__file__).parent.parent
        player_path = project_root / "cmake-build-debug" / "player" / "player"
        
        if player_path.exists():
            return str(player_path)
        else:
            self.logger.error("Player executable not found. Run build first.")
            sys.exit(1)
    
    def _signal_handler(self, signum, frame):
        self.logger.info("Received shutdown signal. Cleaning up...")
        self.shutdown()
    
    def shutdown(self):
        self.running = False
        if self.player_process:
            self.player_process.terminate()
        sys.exit(0)
    
    def register(self):
        """Register with the server"""
        try:
            data = {
                "client_id": self.hostname,
                "hostname": self.hostname,
                "display_name": self.display_name,
                "platform": "Raspberry Pi"
            }
            
            response = requests.post(f"{self.server_url}/register_client", json=data, timeout=10)
            
            if response.status_code == 200:
                self.logger.info("Successfully registered with server")
                return True
            else:
                self.logger.error(f"Registration failed: {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Registration error: {e}")
            return False
    
    def check_assignment(self):
        """Check for stream assignment from server"""
        try:
            response = requests.post(
                f"{self.server_url}/client_status",
                json={"client_id": self.hostname},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("status"), data.get("stream_url"), data.get("message", "")
            else:
                return "error", None, f"Server error: {response.status_code}"
                
        except Exception as e:
            return "error", None, f"Network error: {e}"
    
    def start_stream(self, stream_url):
        """Start playing the assigned stream"""
        if self.player_process:
            self.stop_stream()
        
        try:
            self.logger.info(f"Starting stream: {stream_url}")
            self.player_process = subprocess.Popen([self.player_path, stream_url])
            return True
        except Exception as e:
            self.logger.error(f"Failed to start stream: {e}")
            return False
    
    def stop_stream(self):
        """Stop the current stream"""
        if self.player_process:
            self.player_process.terminate()
            self.player_process.wait()
            self.player_process = None
            self.logger.info("Stream stopped")
    
    def run(self):
        """Main execution loop"""
        if not self.register():
            return
        
        self.logger.info("Waiting for stream assignment...")
        
        while self.running:
            status, stream_url, message = self.check_assignment()
            
            if status == "assigned" and stream_url:
                if not self.player_process or self.player_process.poll() is not None:
                    self.start_stream(stream_url)
            elif status in ["waiting", "no_assignment"]:
                if self.player_process and self.player_process.poll() is None:
                    self.stop_stream()
            
            time.sleep(5)  # Check every 5 seconds

def main():
    parser = argparse.ArgumentParser(description="SRT Client for Raspberry Pi")
    parser.add_argument("server_url", help="Server URL (e.g., http://192.168.1.100:5000)")
    parser.add_argument("--hostname", help="Client hostname")
    parser.add_argument("--display-name", help="Display name for the client")
    
    args = parser.parse_args()
    
    client = SRTClient(args.server_url, args.hostname, args.display_name)
    client.run()

if __name__ == "__main__":
    main()
EOF
        
        chmod +x client/client.py
    fi
    
    log "Python client setup completed"
}

# Get user input for configuration
get_user_configuration() {
    log "Gathering configuration information..."
    
    # Get server URL
    while [[ -z "$SERVER_URL" ]]; do
        read -p "Enter the server URL (e.g., http://192.168.1.100:5000): " SERVER_URL
        if [[ ! "$SERVER_URL" =~ ^https?:// ]]; then
            error "Please enter a valid URL starting with http:// or https://"
            SERVER_URL=""
        fi
    done
    
    # Generate default hostname
    local mac_suffix=$(cat /sys/class/net/eth0/address 2>/dev/null | tail -c 6 | tr -d ':' | tr '[:lower:]' '[:upper:]' || echo "$(date +%s)")
    local default_hostname="rpi-client-$mac_suffix"
    
    read -p "Enter client hostname [$default_hostname]: " CLIENT_HOSTNAME
    CLIENT_HOSTNAME=${CLIENT_HOSTNAME:-$default_hostname}
    
    read -p "Enter display name [$CLIENT_HOSTNAME]: " DISPLAY_NAME
    DISPLAY_NAME=${DISPLAY_NAME:-$CLIENT_HOSTNAME}
    
    info "Configuration:"
    info "  Server URL: $SERVER_URL"
    info "  Hostname: $CLIENT_HOSTNAME"
    info "  Display Name: $DISPLAY_NAME"
}

# Create systemd service
create_service() {
    log "Creating systemd service..."
    
    # Create service file
    sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null << EOF
[Unit]
Description=SRT Multi-Screen Client
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=0

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$PROJECT_DIR
Environment=DISPLAY=:0
Environment=XDG_RUNTIME_DIR=/run/user/1000
ExecStart=/usr/bin/python3 $PROJECT_DIR/client/client.py "$SERVER_URL" --hostname "$CLIENT_HOSTNAME" --display-name "$DISPLAY_NAME"
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd and enable service
    sudo systemctl daemon-reload
    sudo systemctl enable $SERVICE_NAME
    
    log "Systemd service created and enabled"
}

# Setup auto-start on boot
setup_autostart() {
    log "Setting up auto-start configuration..."
    
    # Enable auto-login for pi user (optional)
    read -p "Enable auto-login for pi user? This allows the client to start automatically on boot. (y/N): " -r
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo systemctl set-default multi-user.target
        sudo systemctl enable getty@tty1
        
        # Configure auto-login
        sudo mkdir -p /etc/systemd/system/getty@tty1.service.d
        sudo tee /etc/systemd/system/getty@tty1.service.d/override.conf > /dev/null << EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin pi --noclear %I \$TERM
EOF
        
        log "Auto-login enabled"
    fi
    
    # Add to user's .bashrc for manual starts
    if ! grep -q "# SRT Client aliases" ~/.bashrc; then
        cat >> ~/.bashrc << EOF

# SRT Client aliases
alias srt-start='sudo systemctl start $SERVICE_NAME'
alias srt-stop='sudo systemctl stop $SERVICE_NAME'
alias srt-restart='sudo systemctl restart $SERVICE_NAME'
alias srt-status='sudo systemctl status $SERVICE_NAME'
alias srt-logs='sudo journalctl -u $SERVICE_NAME -f'
EOF
        log "Convenience aliases added to ~/.bashrc"
    fi
}

# Test the installation
test_installation() {
    log "Testing installation..."
    
    # Test player executable
    if [[ -x "$PROJECT_DIR/cmake-build-debug/player/player" ]]; then
        log "✅ Player executable found and is executable"
    else
        error "❌ Player executable not found or not executable"
        return 1
    fi
    
    # Test Python client
    if [[ -x "$PROJECT_DIR/client/client.py" ]]; then
        log "✅ Python client found and is executable"
    else
        error "❌ Python client not found or not executable"
        return 1
    fi
    
    # Test service
    if sudo systemctl is-enabled $SERVICE_NAME &>/dev/null; then
        log "✅ Systemd service is enabled"
    else
        error "❌ Systemd service is not enabled"
        return 1
    fi
    
    log "Installation test completed successfully"
}

# Main installation function
main() {
    log "Starting SRT Client automatic setup for Raspberry Pi"
    log "Following hwsel's multi-screen project guidelines"
    
    check_user
    check_system
    
    # Installation steps
    update_system
    install_dependencies
    clone_project
    build_project
    setup_python_client
    get_user_configuration
    create_service
    setup_autostart
    test_installation
    
    log "🎉 Installation completed successfully!"
    echo
    info "Next steps:"
    info "1. Start the service: sudo systemctl start $SERVICE_NAME"
    info "2. Check status: sudo systemctl status $SERVICE_NAME"
    info "3. View logs: sudo journalctl -u $SERVICE_NAME -f"
    info "4. The client will automatically register with your server"
    info "5. Use the web interface to assign this client to a group and stream"
    echo
    info "Convenience commands (available after next login):"
    info "- srt-start    : Start the client service"
    info "- srt-stop     : Stop the client service"
    info "- srt-restart  : Restart the client service"
    info "- srt-status   : Check service status"
    info "- srt-logs     : View real-time logs"
    echo
    warning "Reboot recommended to ensure all services start properly"
    
    read -p "Reboot now? (y/N): " -r
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo reboot
    fi
}

# Run main function
main "$@"