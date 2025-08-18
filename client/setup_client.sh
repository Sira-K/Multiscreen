#!/bin/bash

# Multi-Screen Client Setup Script with Movable Window Support
# This script sets up the multi-screen client with window management tools
# Usage: ./setup_client.sh [options]
# Options:
#   --force-rebuild : Force rebuild of external dependencies
#   --jobs N       : Set number of parallel jobs (default: auto-detect)
#   --debug        : Build in debug mode (default)
#   --release      : Build in release mode
#   --clean        : Clean build directories before building
#   --help         : Show this help message

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
BUILD_TYPE="Debug"
FORCE_REBUILD=1
CLEAN_BUILD=0
PROJECT_ROOT="$(pwd)"
BUILD_DIR="cmake-build-debug"

# Auto-detect and change to multi-screen directory
find_project_root() {
    # Check if we're already in multi-screen directory
    if [ -f "CMakeLists.txt" ] && [ -d "player" ]; then
        print_status "Already in multi-screen project directory"
        return 0
    fi
    
    # Check if multi-screen is a subdirectory
    if [ -d "multi-screen" ] && [ -f "multi-screen/CMakeLists.txt" ]; then
        print_status "Found multi-screen subdirectory, changing to it..."
        cd multi-screen
        PROJECT_ROOT="$(pwd)"
        return 0
    fi
    
    # Check if we're inside multi-screen but not at root
    CURRENT_DIR="$(pwd)"
    while [ "$CURRENT_DIR" != "/" ]; do
        if [ -f "$CURRENT_DIR/CMakeLists.txt" ] && [ -d "$CURRENT_DIR/player" ]; then
            print_status "Found project root at: $CURRENT_DIR"
            cd "$CURRENT_DIR"
            PROJECT_ROOT="$(pwd)"
            return 0
        fi
        CURRENT_DIR="$(dirname "$CURRENT_DIR")"
    done
    
    # Try to find multi-screen in parent directory
    if [ -d "../multi-screen" ] && [ -f "../multi-screen/CMakeLists.txt" ]; then
        print_status "Found multi-screen in parent directory, changing to it..."
        cd ../multi-screen
        PROJECT_ROOT="$(pwd)"
        return 0
    fi
    
    # If no C++ project found, just use current directory for client setup
    print_status "No C++ project found - setting up client-only environment"
    print_status "Using current directory: $(pwd)"
    return 0
}

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_window() {
    echo -e "${BLUE}[WINDOW]${NC} $1"
}

# Function to detect number of CPU cores
detect_cpu_cores() {
    if command -v nproc &> /dev/null; then
        CORES=$(nproc)
    elif command -v sysctl &> /dev/null; then
        CORES=$(sysctl -n hw.ncpu)
    else
        CORES=4
    fi
    
    if [ "$CORES" -le 4 ]; then
        MAX_JOBS=3
    else
        MAX_JOBS=$((CORES - 1))
    fi
    
    echo $MAX_JOBS
}

# Function to setup window management tools
setup_window_tools() {
    print_window "=========================================="
    print_window "Setting up window management tools"
    print_window "=========================================="
    
    # Check and install wmctrl
    if command -v wmctrl &> /dev/null; then
        print_window " wmctrl is already installed"
    else
        print_window "Installing wmctrl..."
        if command -v apt-get &> /dev/null; then
            sudo apt-get update
            sudo apt-get install -y wmctrl
        elif command -v yum &> /dev/null; then
            sudo yum install -y wmctrl
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y wmctrl
        else
            print_error "Could not install wmctrl automatically. Please install it manually:"
            echo "  Ubuntu/Debian: sudo apt-get install wmctrl"
            echo "  RHEL/CentOS:   sudo yum install wmctrl"
            echo "  Fedora:        sudo dnf install wmctrl"
            return 1
        fi
    fi
    
    # Check and install xdotool
    if command -v xdotool &> /dev/null; then
        print_window " xdotool is already installed"
    else
        print_window "Installing xdotool..."
        if command -v apt-get &> /dev/null; then
            sudo apt-get install -y xdotool
        elif command -v yum &> /dev/null; then
            sudo yum install -y xdotool
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y xdotool
        else
            print_error "Could not install xdotool automatically. Please install it manually:"
            echo "  Ubuntu/Debian: sudo apt-get install xdotool"
            echo "  RHEL/CentOS:   sudo yum install xdotool"
            echo "  Fedora:        sudo dnf install xdotool"
            return 1
        fi
    fi
    
    # Check and install tkinter (Python GUI)
    if python3 -c "import tkinter" 2>/dev/null; then
        print_window " tkinter is already available"
    else
        print_window "Installing tkinter..."
        if command -v apt-get &> /dev/null; then
            sudo apt-get install -y python3-tk
        elif command -v yum &> /dev/null; then
            sudo yum install -y python3-tkinter
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y python3-tkinter
        else
            print_error "Could not install tkinter automatically. Please install it manually:"
            echo "  Ubuntu/Debian: sudo apt-get install python3-tk"
            echo "  RHEL/CentOS:   sudo yum install python3-tkinter"
            echo "  Fedora:        sudo dnf install python3-tkinter"
            return 1
        fi
    fi
    
    print_window " Window management tools setup completed successfully!"
}

# Function to setup ffmpeg
setup_ffmpeg() {
    print_status "=========================================="
    print_status "Setting up ffmpeg for video playback"
    print_status "=========================================="
    
    # Check if ffmpeg is already installed
    if command -v ffmpeg &> /dev/null; then
        print_status " ffmpeg is already installed"
        return 0
    fi
    
    print_status "Installing ffmpeg..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y ffmpeg
    elif command -v yum &> /dev/null; then
        sudo yum install -y ffmpeg
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y ffmpeg
    else
        print_error "Could not install ffmpeg automatically. Please install it manually:"
        echo "  Ubuntu/Debian: sudo apt-get install ffmpeg"
        echo "  RHEL/CentOS:   sudo yum install ffmpeg"
        echo "  Fedora:        sudo dnf install ffmpeg"
        return 1
    fi
    
    print_status " ffmpeg setup completed successfully!"
}

# Function to build the C++ player (optional)
build_player() {
    print_status "=========================================="
    print_status "Checking C++ player build requirements"
    print_status "=========================================="
    
    # Check if we're in the right directory for C++ build
    if [ ! -f "CMakeLists.txt" ] || [ ! -d "multi-screen" ]; then
        print_warning "C++ player source not found - skipping build"
        print_warning "Client will use ffplay fallback for all streams"
        return 0
    fi
    
    # Check if CMake is available
    if ! command -v cmake &> /dev/null; then
        print_warning "CMake not available - skipping C++ player build"
        print_warning "Client will use ffplay fallback for all streams"
        return 0
    fi
    
    print_status "Building C++ player for SEI streams..."
    
    # Clean build if requested
    if [ $CLEAN_BUILD -eq 1 ]; then
        print_status "Cleaning build directories..."
        rm -rf cmake-build-* build/
    fi
    
    # Create build directory
    mkdir -p "$BUILD_DIR"
    cd "$BUILD_DIR"
    
    # Configure with CMake
    print_status "Configuring build with CMake..."
    cmake .. -DCMAKE_BUILD_TYPE="$BUILD_TYPE"
    
    # Build
    print_status "Building player (this may take a while)..."
    make -j$(detect_cpu_cores)
    
    # Check if build was successful
    if [ -f "player/player" ]; then
        print_status " Player built successfully!"
        chmod +x player/player
    else
        print_warning "Build failed - C++ player will not be available"
        print_warning "Client will use ffplay fallback for all streams"
    fi
    
    cd ..
}

# Function to create convenience scripts
create_scripts() {
    print_status "=========================================="
    print_status "Creating convenience scripts"
    print_status "=========================================="
    
    # Create run_client.sh script
    cat > "$PROJECT_ROOT/run_client.sh" << 'EOF'
#!/bin/bash
# Multi-Screen Client Runner Script
# This script runs the multi-screen client with common options

# Default values
SERVER_URL="http://192.168.1.100:5000"
HOSTNAME=""
DISPLAY_NAME=""
FORCE_FFPLAY=""
DEBUG=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --server)
            SERVER_URL="$2"
            shift 2
            ;;
        --hostname)
            HOSTNAME="$2"
            shift 2
            ;;
        --display-name)
            DISPLAY_NAME="$2"
            shift 2
            ;;
        --force-ffplay)
            FORCE_FFPLAY="--force-ffplay"
            shift
            ;;
        --debug)
            DEBUG="--debug"
            shift
            ;;
        --help)
            echo "Multi-Screen Client Runner"
            echo "Usage: $0 [options]"
            echo ""
            echo "Required Options:"
            echo "  --server URL         : Server URL (default: http://192.168.1.100:5000)"
            echo "  --hostname NAME      : Client hostname (required)"
            echo "  --display-name NAME  : Display name for admin interface (required)"
            echo ""
            echo "Optional Options:"
            echo "  --force-ffplay       : Force use of ffplay instead of smart selection"
            echo "  --debug              : Enable debug logging"
            echo "  --help               : Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 --server http://192.168.1.100:5000 --hostname rpi-client-1 --display-name \"Monitor 1\""
            echo "  $0 --server http://192.168.1.100:5000 --hostname rpi-client-2 --display-name \"Monitor 2\" --force-ffplay"
            echo ""
            echo "Hotkeys (once running):"
            echo "  Ctrl+M or Ctrl+Right: Move to next monitor"
            echo "  Ctrl+Left: Move to previous monitor"
            echo "  Ctrl+1-4: Move to specific monitor"
            echo "  Ctrl+H: Show help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check required arguments
if [ -z "$HOSTNAME" ] || [ -z "$DISPLAY_NAME" ]; then
    echo "Error: --hostname and --display-name are required"
    echo "Use --help for usage information"
    exit 1
fi

echo "Starting Multi-Screen Client..."
echo "Server: $SERVER_URL"
echo "Hostname: $HOSTNAME"
echo "Display Name: $DISPLAY_NAME"
echo "Force ffplay: $([ -n "$FORCE_FFPLAY" ] && echo "Yes" || echo "No")"
echo "Debug mode: $([ -n "$DEBUG" ] && echo "Yes" || echo "No")"
echo ""
echo "Hotkeys:"
echo "  Ctrl+M: Move to next monitor"
echo "  Ctrl+1-4: Move to specific monitor"
echo "  Ctrl+H: Show help"
echo ""

# Run the client
python3 client.py --server "$SERVER_URL" --hostname "$HOSTNAME" --display-name "$DISPLAY_NAME" $FORCE_FFPLAY $DEBUG
EOF

    chmod +x "$PROJECT_ROOT/run_client.sh"
    print_status " Created run_client.sh script"
    
    # Create multi-monitor setup script
    cat > "$PROJECT_ROOT/setup_multi_monitor.sh" << 'EOF'
#!/bin/bash
# Multi-Monitor Setup Script for Raspberry Pi
# This script helps configure multiple monitors for video wall setup

echo "  Multi-Monitor Setup for Raspberry Pi"
echo "=========================================="

# Check if we're on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo "  This script is designed for Raspberry Pi"
    echo "   It may work on other systems but is not tested"
    echo ""
fi

# Check current display setup
echo " Current Display Configuration:"
if command -v xrandr &> /dev/null; then
    xrandr --listmonitors
else
    echo "xrandr not available - cannot check current setup"
fi

echo ""
echo " Monitor Configuration Options:"
echo "1. Dual Monitor (Side by Side)"
echo "2. Dual Monitor (Stacked)"
echo "3. Triple Monitor (Horizontal)"
echo "4. Custom Configuration"
echo "5. Check Wayland/XWayland Status"
echo ""

read -p "Select option (1-5): " choice

case $choice in
    1)
        echo "Setting up dual monitors side by side..."
        if command -v xrandr &> /dev/null; then
            # Try to detect HDMI outputs
            HDMI_OUTPUTS=$(xrandr | grep "HDMI" | grep "connected" | awk '{print $1}' | head -2)
            if [ -n "$HDMI_OUTPUTS" ]; then
                echo "Detected HDMI outputs: $HDMI_OUTPUTS"
                # Configure side by side
                xrandr --output $(echo $HDMI_OUTPUTS | awk '{print $1}') --mode 1920x1080 --pos 0x0
                xrandr --output $(echo $HDMI_OUTPUTS | awk '{print $2}') --mode 1920x1080 --pos 1920x0
                echo " Dual monitor setup configured"
            else
                echo "Could not detect HDMI outputs automatically"
                echo "Please configure manually using xrandr"
            fi
        else
            echo "xrandr not available - please configure monitors manually"
        fi
        ;;
    2)
        echo "Setting up dual monitors stacked..."
        if command -v xrandr &> /dev/null; then
            HDMI_OUTPUTS=$(xrandr | grep "HDMI" | grep "connected" | awk '{print $1}' | head -2)
            if [ -n "$HDMI_OUTPUTS" ]; then
                echo "Detected HDMI outputs: $HDMI_OUTPUTS"
                # Configure stacked
                xrandr --output $(echo $HDMI_OUTPUTS | awk '{print $1}') --mode 1920x1080 --pos 0x0
                xrandr --output $(echo $HDMI_OUTPUTS | awk '{print $2}') --mode 1920x1080 --pos 0x1080
                echo " Dual monitor setup configured"
            else
                echo "Could not detect HDMI outputs automatically"
                echo "Please configure manually using xrandr"
            fi
        else
            echo "xrandr not available - please configure monitors manually"
        fi
        ;;
    3)
        echo "Setting up triple monitors horizontally..."
        if command -v xrandr &> /dev/null; then
            HDMI_OUTPUTS=$(xrandr | grep "HDMI" | grep "connected" | awk '{print $1}' | head -3)
            if [ -n "$HDMI_OUTPUTS" ]; then
                echo "Detected HDMI outputs: $HDMI_OUTPUTS"
                # Configure horizontal
                xrandr --output $(echo $HDMI_OUTPUTS | awk '{print $1}') --mode 1920x1080 --pos 0x0
                xrandr --output $(echo $HDMI_OUTPUTS | awk '{print $2}') --mode 1920x1080 --pos 1920x0
                xrandr --output $(echo $HDMI_OUTPUTS | awk '{print $3}') --mode 1920x1080 --pos 3840x0
                echo " Triple monitor setup configured"
            else
                echo "Could not detect HDMI outputs automatically"
                echo "Please configure manually using xrandr"
            fi
        else
            echo "xrandr not available - please configure monitors manually"
        fi
        ;;
    4)
        echo "Custom configuration..."
        echo "Please use xrandr manually to configure your monitors"
        echo "Example: xrandr --output HDMI-1 --mode 1920x1080 --pos 0x0"
        ;;
    5)
        echo "Checking display system..."
        echo "XDG_SESSION_TYPE: $XDG_SESSION_TYPE"
        echo "WAYLAND_DISPLAY: $WAYLAND_DISPLAY"
        echo "DISPLAY: $DISPLAY"
        echo ""
        if [ "$XDG_SESSION_TYPE" = "wayland" ]; then
            echo " You're using Wayland"
            echo "   - Use the client hotkeys to move windows between monitors"
            echo "   - Monitors are configured through desktop environment settings"
        else
            echo " You're using X11/XWayland"
            echo "   - Use xrandr to configure monitor positions"
            echo "   - Use the client hotkeys to move windows between monitors"
        fi
        ;;
    *)
        echo "Invalid option selected"
        exit 1
        ;;
esac

echo ""
echo " Setup complete!"
echo ""
echo "Next steps:"
echo "1. Start your multi-screen client:"
echo "   ./run_client.sh --server http://YOUR_SERVER:5000 --hostname client-1 --display-name \"Monitor 1\""
echo ""
echo "2. Use hotkeys to move the window:"
echo "   Ctrl+M: Next monitor"
echo "   Ctrl+1-4: Specific monitor"
echo "   Ctrl+H: Show help"
EOF

    chmod +x "$PROJECT_ROOT/setup_multi_monitor.sh"
    print_status " Created setup_multi_monitor.sh script"
    
    # Create systemd service template
    cat > "$PROJECT_ROOT/multiscreen-client.service" << 'EOF'
[Unit]
Description=Multi-Screen Client Service
After=network.target graphical-session.target
Wants=graphical-session.target

[Service]
Type=simple
User=pi
Environment=DISPLAY=:0
WorkingDirectory=/home/pi/multiscreen-client
ExecStart=/usr/bin/python3 /home/pi/multiscreen-client/client.py --server http://YOUR_SERVER_IP:5000 --hostname CLIENT_HOSTNAME --display-name "DISPLAY_NAME"
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    print_status " Created systemd service template"
}

# Function to show help
show_help() {
    echo "Multi-Screen Client Setup Script"
    echo "================================="
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --force-rebuild : Force rebuild of external dependencies"
    echo "  --jobs N        : Set number of parallel jobs (default: auto-detect)"
    echo "  --debug         : Build in debug mode (default)"
    echo "  --release       : Build in release mode"
    echo "  --clean         : Clean build directories before building"
    echo "  --help          : Show this help message"
    echo ""
    echo "This script will:"
    echo "1. Install window management tools (wmctrl, xdotool, tkinter)"
    echo "2. Install ffmpeg for video playback"
    echo "3. Build the C++ player for SEI streams"
    echo "4. Create convenience scripts for running the client"
    echo "5. Set up multi-monitor configuration"
    echo ""
    echo "After setup, you can:"
    echo "- Run clients: ./run_client.sh --hostname client-1 --display-name \"Monitor 1\""
    echo "- Configure monitors: ./setup_multi_monitor.sh"
    echo "- Use hotkeys to move windows between monitors"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --force-rebuild)
            FORCE_REBUILD=1
            shift
            ;;
        --jobs)
            MAX_JOBS="$2"
            shift 2
            ;;
        --debug)
            BUILD_TYPE="Debug"
            BUILD_DIR="cmake-build-debug"
            shift
            ;;
        --release)
            BUILD_TYPE="Release"
            BUILD_DIR="cmake-build-release"
            shift
            ;;
        --clean)
            CLEAN_BUILD=1
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Main execution
echo " Multi-Screen Client Setup Script"
echo "===================================="
echo ""

# Find project root (or use current directory for client-only setup)
find_project_root
print_status "Project root: $PROJECT_ROOT"

# Setup window management tools
setup_window_tools

# Setup ffmpeg
setup_ffmpeg

# Build the player
build_player

# Create convenience scripts
create_scripts

# Final summary
echo ""
print_status "=========================================="
print_status "Setup Complete!"
print_status "=========================================="
echo ""

print_window " Window management tools installed (wmctrl, xdotool, tkinter)"
print_status " ffmpeg installed for video playback"
if [ -f "$BUILD_DIR/player/player" ]; then
    print_status " C++ player built successfully (SEI stream support)"
else
    print_status " ffplay fallback configured (all streams)"
fi
print_status " Convenience scripts created"
echo ""

print_status " Next steps:"
echo "1. Configure your monitors:"
echo "   ./setup_multi_monitor.sh"
echo ""
echo "2. Start your first client:"
echo "   ./run_client.sh --server http://YOUR_SERVER:5000 --hostname client-1 --display-name \"Monitor 1\""
echo ""
echo "3. Use hotkeys to move windows:"
echo "   Ctrl+M: Next monitor"
echo "   Ctrl+1-4: Specific monitor"
echo "   Ctrl+H: Show help"
echo ""

print_status " For more information:"
echo "- Client help: ./run_client.sh --help"
echo "- Monitor setup: ./setup_multi_monitor.sh --help"
echo "- Hotkey reference: Press Ctrl+H while client is running"

print_status " Setup completed successfully!"
print_status "Your multi-screen client is ready with movable window support!"
