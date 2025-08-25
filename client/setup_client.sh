#!/bin/bash
# Enhanced Multi-Screen Client Setup Script
# This script installs all dependencies and sets up the environment for the client

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_error "This script should not be run as root"
        print_error "Please run as a regular user with sudo privileges"
        exit 1
    fi
}

# Function to detect OS
detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
    elif type lsb_release >/dev/null 2>&1; then
        OS=$(lsb_release -si)
        VER=$(lsb_release -sr)
    elif [[ -f /etc/lsb-release ]]; then
        . /etc/lsb-release
        OS=$DISTRIB_ID
        VER=$DISTRIB_RELEASE
    elif [[ -f /etc/debian_version ]]; then
        OS=Debian
        VER=$(cat /etc/debian_version)
    elif [[ -f /etc/SuSe-release ]]; then
        OS=SuSE
    elif [[ -f /etc/redhat-release ]]; then
        OS=RedHat
    else
        OS=$(uname -s)
        VER=$(uname -r)
    fi
    
    print_status "Detected OS: $OS $VER"
}

# Function to update package lists
update_packages() {
    print_status "Updating package lists..."
    
    if command_exists apt-get; then
        sudo apt-get update
    elif command_exists yum; then
        sudo yum update
    elif command_exists dnf; then
        sudo dnf update
    elif command_exists pacman; then
        sudo pacman -Sy
    else
        print_warning "Unknown package manager, skipping update"
    fi
}

# Function to install Python dependencies
install_python_deps() {
    print_status "Installing Python dependencies..."
    
    # Check Python version
    if command_exists python3; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
        print_status "Python version: $PYTHON_VERSION"
        
        if [[ "$PYTHON_VERSION" < "3.7" ]]; then
            print_error "Python 3.7+ is required. Current version: $PYTHON_VERSION"
            print_status "Installing Python 3.7+..."
            
            if command_exists apt-get; then
                sudo apt-get install -y python3.9 python3.9-pip python3.9-dev
                sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 1
            elif command_exists yum; then
                sudo yum install -y python39 python39-pip python39-devel
            else
                print_error "Please install Python 3.7+ manually"
                exit 1
            fi
        fi
    else
        print_error "Python 3 is not installed"
        print_status "Installing Python 3..."
        
        if command_exists apt-get; then
            sudo apt-get install -y python3 python3-pip python3-dev
        elif command_exists yum; then
            sudo yum install -y python3 python3-pip python3-devel
        else
            print_error "Please install Python 3 manually"
            exit 1
        fi
    fi
    
    # Install pip if not available
    if ! command_exists pip3; then
        print_status "Installing pip3..."
        if command_exists apt-get; then
            sudo apt-get install -y python3-pip
        elif command_exists yum; then
            sudo yum install -y python3-pip
        fi
    fi
    
    # Upgrade pip
    print_status "Upgrading pip..."
    python3 -m pip install --upgrade pip
    
    # Install required Python packages
    print_status "Installing Python packages..."
    python3 -m pip install --user requests
}

# Function to install system dependencies
install_system_deps() {
    print_status "Installing system dependencies..."
    
    if command_exists apt-get; then
        # Debian/Ubuntu
        sudo apt-get install -y \
            ffmpeg \
            wmctrl \
            xdotool \
            python3-tk \
            python3-dev \
            build-essential \
            cmake \
            git \
            curl \
            wget \
            htop \
            vim \
            nano
    elif command_exists yum; then
        # CentOS/RHEL/Fedora
        sudo yum install -y \
            ffmpeg \
            wmctrl \
            xdotool \
            python3-tkinter \
            python3-devel \
            gcc \
            gcc-c++ \
            make \
            cmake \
            git \
            curl \
            wget \
            htop \
            vim \
            nano
    elif command_exists dnf; then
        # Fedora
        sudo dnf install -y \
            ffmpeg \
            wmctrl \
            xdotool \
            python3-tkinter \
            python3-devel \
            gcc \
            gcc-c++ \
            make \
            cmake \
            git \
            curl \
            wget \
            htop \
            vim \
            nano
    elif command_exists pacman; then
        # Arch Linux
        sudo pacman -S --noconfirm \
            ffmpeg \
            wmctrl \
            xdotool \
            tk \
            python \
            base-devel \
            cmake \
            git \
            curl \
            wget \
            htop \
            vim \
            nano
    else
        print_warning "Unknown package manager, please install dependencies manually"
        print_status "Required packages: ffmpeg, wmctrl, xdotool, python3-tk, build tools"
    fi
}

# Function to install C++ player (optional)
install_cpp_player() {
    print_status "Checking for C++ player..."
    
    if [[ -d "multi-screen" ]]; then
        print_status "C++ player source found, attempting to build..."
        
        cd multi-screen
        
        # Create build directory
        mkdir -p cmake-build-debug
        cd cmake-build-debug
        
        # Configure and build
        if command_exists cmake; then
            cmake ..
            make -j$(nproc)
            
            if [[ -f "player/player" ]]; then
                print_success "C++ player built successfully"
                # Make executable
                chmod +x player/player
            else
                print_warning "C++ player build failed, will use ffplay fallback"
            fi
        else
            print_warning "CMake not found, skipping C++ player build"
        fi
        
        cd ../..
    else
        print_status "C++ player source not found, will use ffplay"
    fi
}

# Function to setup display environment
setup_display() {
    print_status "Setting up display environment..."
    
    # Check if X11 is available
    if [[ -z "$DISPLAY" ]]; then
        print_warning "DISPLAY variable not set"
        print_status "Setting DISPLAY to :0.0"
        export DISPLAY=:0.0
        echo 'export DISPLAY=:0.0' >> ~/.bashrc
    fi
    
    # Check if running in X11
    if ! xset q >/dev/null 2>&1; then
        print_warning "X11 server not accessible"
        print_status "This may cause issues with window management"
        print_status "Consider running: startx or connecting to existing X server"
    fi
    
    # Check for multiple monitors
    if command_exists xrandr; then
        MONITOR_COUNT=$(xrandr --listmonitors | grep -c "Monitor")
        print_status "Detected $MONITOR_COUNT monitor(s)"
        
        if [[ $MONITOR_COUNT -lt 2 ]]; then
            print_warning "Less than 2 monitors detected"
            print_status "Client will still work but may not need multithreading"
        fi
    fi
}

# Function to setup logging
setup_logging() {
    print_status "Setting up logging..."
    
    # Create log directory
    mkdir -p ~/client_logs
    
    # Create log rotation script
    cat > ~/client_logs/rotate_logs.sh << 'EOF'
#!/bin/bash
# Log rotation script for client logs

LOG_DIR="$HOME/client_logs"
MAX_SIZE="10M"
MAX_FILES=5

find "$LOG_DIR" -name "*.log" -size +$MAX_SIZE -exec truncate -s 0 {} \;
find "$LOG_DIR" -name "*.log.*" -mtime +7 -delete

# Keep only the last MAX_FILES log files
ls -t "$LOG_DIR"/*.log 2>/dev/null | tail -n +$((MAX_FILES + 1)) | xargs -r rm
EOF
    
    chmod +x ~/client_logs/rotate_logs.sh
    
    # Add to crontab for daily rotation
    (crontab -l 2>/dev/null; echo "0 2 * * * $HOME/client_logs/rotate_logs.sh") | crontab -
    
    print_success "Logging setup complete"
}

# Function to create systemd service (optional)
create_systemd_service() {
    print_status "Creating systemd service..."
    
    if [[ -f "flask-server.service" ]]; then
        print_status "Found existing service file, installing..."
        sudo cp flask-server.service /etc/systemd/system/
        sudo systemctl daemon-reload
        sudo systemctl enable flask-server.service
        print_success "Systemd service installed and enabled"
    else
        print_status "No service file found, skipping systemd setup"
    fi
}

# Function to test client
test_client() {
    print_status "Testing client installation..."
    
    # Test Python imports
    if python3 -c "import requests, tkinter, subprocess, threading" 2>/dev/null; then
        print_success "Python dependencies working"
    else
        print_error "Python dependencies test failed"
        return 1
    fi
    
    # Test ffmpeg
    if command_exists ffmpeg; then
        print_success "ffmpeg available"
    else
        print_error "ffmpeg not found"
        return 1
    fi
    
    # Test client.py
    if [[ -f "client.py" ]]; then
        print_status "Testing client.py..."
        if python3 client.py --help >/dev/null 2>&1; then
            print_success "Client.py working correctly"
        else
            print_error "Client.py test failed"
            return 1
        fi
    else
        print_error "client.py not found"
        return 1
    fi
    
    return 0
}

# Function to show usage examples
show_examples() {
    print_status "Setup complete! Here are usage examples:"
    echo
    echo "Single Client (Screen 1):"
    echo "  python3 client.py --server http://YOUR_SERVER:5000 \\"
    echo "    --hostname client1 --display-name 'Screen1' --target-screen 1"
    echo
    echo "Multiple Clients (Single-Threaded Per Process):"
echo "  # Terminal 1 - Screen 1"
echo "  python3 client.py --server http://YOUR_SERVER:5000 \\"
echo "    --hostname client1 --display-name 'Screen1' --target-screen 1"
echo
echo "  # Terminal 2 - Screen 2 (each client uses 1 thread)"
echo "  python3 client.py --server http://YOUR_SERVER:5000 \\"
echo "    --hostname client2 --display-name 'Screen2' --target-screen 2"
    echo
    echo "Debug Mode:"
    echo "  python3 client.py --server http://YOUR_SERVER:5000 \\"
    echo "    --hostname client1 --display-name 'Screen1' --target-screen 1 --debug"
    echo
    echo "Force ffplay:"
    echo "  python3 client.py --server http://YOUR_SERVER:5000 \\"
    echo "    --hostname client1 --display-name 'Screen1' --target-screen 1 --force-ffplay"
}

# Main setup function
main() {
    echo "============================================================"
    echo "Enhanced Multi-Screen Client Setup Script"
    echo "============================================================"
    echo
    
    # Check prerequisites
    check_root
    detect_os
    
    # Update and install
    update_packages
    install_system_deps
    install_python_deps
    install_cpp_player
    
    # Setup environment
    setup_display
    setup_logging
    create_systemd_service
    
    # Test installation
    if test_client; then
        print_success "Client setup completed successfully!"
        echo
        show_examples
    else
        print_error "Client setup failed. Please check the errors above."
        exit 1
    fi
}

# Run main function
main "$@"
