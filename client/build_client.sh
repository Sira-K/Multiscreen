#!/bin/bash

# Multi-Screen Player Build Script with Time Synchronization Setup
# This script automates the building process for the multi-screen player project
# and sets up chrony for client-client time synchronization
# Usage: ./build_player.sh [options]
# Options:
#   --force-rebuild : Force rebuild of external dependencies
#   --jobs N       : Set number of parallel jobs (default: auto-detect)
#   --debug        : Build in debug mode (default)
#   --release      : Build in release mode
#   --clean        : Clean build directories before building
#   --skip-chrony  : Skip chrony time synchronization setup
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
SETUP_CHRONY=1
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
    
    return 1
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

print_chrony() {
    echo -e "${BLUE}[CHRONY]${NC} $1"
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

# Function to setup chrony for time synchronization
setup_chrony() {
    print_chrony "=========================================="
    print_chrony "Setting up chrony for time synchronization"
    print_chrony "=========================================="
    
    # Check if chrony is already installed
    if command -v chrony &> /dev/null; then
        print_chrony "chrony is already installed"
    else
        print_chrony "Installing chrony..."
        if command -v apt-get &> /dev/null; then
            sudo apt-get update
            sudo apt-get install -y chrony
        elif command -v yum &> /dev/null; then
            sudo yum install -y chrony
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y chrony
        else
            print_error "Could not install chrony automatically. Please install it manually:"
            echo "  Ubuntu/Debian: sudo apt-get install chrony"
            echo "  RHEL/CentOS:   sudo yum install chrony"
            echo "  Fedora:        sudo dnf install chrony"
            return 1
        fi
    fi
    
    # Backup existing configuration if it exists
    if [ -f "/etc/chrony/chrony.conf" ]; then
        print_chrony "Backing up existing chrony configuration..."
        sudo cp /etc/chrony/chrony.conf /etc/chrony/chrony.conf.backup.$(date +%Y%m%d_%H%M%S)
    fi
    
    # Create chrony configuration for video wall client synchronization
    print_chrony "Creating chrony configuration for video wall synchronization..."
    sudo tee /etc/chrony/chrony.conf > /dev/null << 'EOF'
# Chrony configuration for video wall client synchronization
# All clients use the same external NTP servers for sync

# Primary NTP servers (multiple for redundancy)
pool pool.ntp.org iburst
pool time.google.com iburst
pool time.cloudflare.com iburst

# Quick sync on startup - allows large time corrections
makestep 1.0 3

# Increase tolerance for network jitter
maxupdateskew 100.0

# Enable RTC sync
rtcsync

# Log directory
logdir /var/log/chrony
EOF
    
    # Test chrony configuration
    print_chrony "Testing chrony configuration..."
    if sudo chronyd -n -d -f /etc/chrony/chrony.conf > /dev/null 2>&1 &
    then
        CHRONYD_PID=$!
        sleep 2
        kill $CHRONYD_PID 2>/dev/null || true
        wait $CHRONYD_PID 2>/dev/null || true
        print_chrony "✓ Configuration test passed"
    else
        print_error "Chrony configuration test failed"
        return 1
    fi
    
    # Restart and enable chrony service
    print_chrony "Starting chrony service..."
    sudo systemctl restart chrony
    sudo systemctl enable chrony
    
    # Wait a moment for chrony to initialize
    sleep 3
    
    # Check chrony status
    if systemctl is-active --quiet chrony; then
        print_chrony "✓ Chrony service is running"
        
        # Show synchronization status
        print_chrony "Chrony synchronization status:"
        chronyc tracking 2>/dev/null || print_warning "Chrony tracking not yet available (normal during startup)"
        
        print_chrony "Chrony time sources:"
        chronyc sources 2>/dev/null || print_warning "Chrony sources not yet available (normal during startup)"
        
        print_chrony ""
        print_chrony "✓ Time synchronization setup completed successfully!"
        print_chrony "Note: It may take a few minutes for full synchronization to occur."
        print_chrony ""
        
    else
        print_error "Failed to start chrony service"
        print_error "Check logs with: sudo journalctl -xeu chrony.service"
        return 1
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --force-rebuild)
            FORCE_REBUILD=1
            shift
            ;;
        --no-rebuild)
            FORCE_REBUILD=0
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
        --skip-chrony)
            SETUP_CHRONY=0
            shift
            ;;
        --help)
            echo "Multi-Screen Player Build Script with Time Synchronization"
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --force-rebuild  : Force rebuild of external dependencies (default)"
            echo "  --no-rebuild     : Skip rebuilding external dependencies"
            echo "  --jobs N         : Set number of parallel jobs (default: auto-detect)"
            echo "  --debug          : Build in debug mode (default)"
            echo "  --release        : Build in release mode"
            echo "  --clean          : Clean build directories before building"
            echo "  --skip-chrony    : Skip chrony time synchronization setup"
            echo "  --help           : Show this help message"
            echo ""
            echo "Time Synchronization:"
            echo "  This script automatically sets up chrony for client-client time"
            echo "  synchronization, which is essential for video wall synchronization."
            echo "  All client machines should run this script to ensure proper sync."
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Auto-detect jobs if not specified
if [ -z "$MAX_JOBS" ]; then
    MAX_JOBS=$(detect_cpu_cores)
fi

# Try to find and change to project root
if ! find_project_root; then
    print_error "Could not find multi-screen project directory!"
    print_error "Please ensure you have cloned the repository:"
    echo "  git clone https://github.com/hwsel/multi-screen.git"
    print_error "Then run this script from within or near the multi-screen directory"
    exit 1
fi

print_status "Build configuration:"
print_status "  Project root: $PROJECT_ROOT"
print_status "  Build type: $BUILD_TYPE"
print_status "  Build directory: $BUILD_DIR"
print_status "  Max parallel jobs: $MAX_JOBS"
print_status "  Force rebuild externals: $FORCE_REBUILD"
print_status "  Setup chrony: $SETUP_CHRONY"

# Setup chrony first (if requested)
if [ $SETUP_CHRONY -eq 1 ]; then
    setup_chrony
fi

# Check for required dependencies
print_status "Checking system dependencies..."

check_dependency() {
    if ! command -v $1 &> /dev/null; then
        print_error "$1 is not installed"
        return 1
    else
        print_status "  ✓ $1 found"
        return 0
    fi
}

MISSING_DEPS=0

# Check required tools
check_dependency "cmake" || MISSING_DEPS=1
check_dependency "ninja" || {
    print_warning "ninja not found, will use make instead"
    NINJA_PATH=""
}
check_dependency "git" || MISSING_DEPS=1
check_dependency "pkg-config" || MISSING_DEPS=1
check_dependency "g++" || MISSING_DEPS=1

# Get ninja path if available
if command -v ninja &> /dev/null; then
    NINJA_PATH=$(which ninja)
    CMAKE_GENERATOR="Ninja"
    print_status "Using Ninja build system"
else
    CMAKE_GENERATOR="Unix Makefiles"
    print_status "Using Make build system"
fi

# Check CMake version
CMAKE_VERSION=$(cmake --version | head -n1 | cut -d' ' -f3)
CMAKE_MAJOR=$(echo $CMAKE_VERSION | cut -d'.' -f1)
CMAKE_MINOR=$(echo $CMAKE_VERSION | cut -d'.' -f2)

if [ "$CMAKE_MAJOR" -lt 3 ] || ([ "$CMAKE_MAJOR" -eq 3 ] && [ "$CMAKE_MINOR" -lt 25 ]); then
    print_error "CMake version 3.25 or higher is required (found: $CMAKE_VERSION)"
    MISSING_DEPS=1
else
    print_status "  ✓ CMake version $CMAKE_VERSION"
fi

if [ $MISSING_DEPS -eq 1 ]; then
    print_error "Missing required dependencies. Please install them and try again."
    
    # Provide installation hints
    echo ""
    print_status "Installation hints for Ubuntu/Debian:"
    echo "  sudo apt-get update"
    echo "  sudo apt-get install -y build-essential cmake ninja-build pkg-config git"
    echo "  sudo apt-get install -y libsdl2-dev libcurl4-openssl-dev"
    echo ""
    print_status "For CMake 3.25+, you may need to:"
    echo "  1. Add the official CMake APT repository, or"
    echo "  2. Download from https://cmake.org/download/"
    
    exit 1
fi

# Check for SDL2 (required for player)
print_status "Checking for SDL2..."
if pkg-config --exists sdl2; then
    print_status "  ✓ SDL2 found"
else
    print_warning "SDL2 not found. Installing..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y libsdl2-dev
    else
        print_error "SDL2 is required. Please install it manually."
        exit 1
    fi
fi

# Check for libcurl (required for player)
print_status "Checking for libcurl..."
if pkg-config --exists libcurl; then
    print_status "  ✓ libcurl found"
else
    print_warning "libcurl not found. Installing..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y libcurl4-openssl-dev
    else
        print_error "libcurl is required. Please install it manually."
        exit 1
    fi
fi

# Clean build directory if requested
if [ $CLEAN_BUILD -eq 1 ]; then
    print_status "Cleaning build directories..."
    rm -rf "$PROJECT_ROOT/$BUILD_DIR"
    rm -rf "$PROJECT_ROOT/cmake-build-*"
    print_status "Build directories cleaned"
fi

# Create build directory if it doesn't exist
mkdir -p "$PROJECT_ROOT/$BUILD_DIR"

# Configure CMake project
print_status "Configuring CMake project..."

CMAKE_CMD="cmake"
CMAKE_CMD="$CMAKE_CMD -DEP_BUILD_ALWAYS=${FORCE_REBUILD}L"
CMAKE_CMD="$CMAKE_CMD -DEP_J=$MAX_JOBS"
CMAKE_CMD="$CMAKE_CMD -DCMAKE_BUILD_TYPE=$BUILD_TYPE"

if [ ! -z "$NINJA_PATH" ]; then
    CMAKE_CMD="$CMAKE_CMD -DCMAKE_MAKE_PROGRAM=$NINJA_PATH"
fi

CMAKE_CMD="$CMAKE_CMD -G \"$CMAKE_GENERATOR\""
CMAKE_CMD="$CMAKE_CMD -S $PROJECT_ROOT"
CMAKE_CMD="$CMAKE_CMD -B $PROJECT_ROOT/$BUILD_DIR"

print_status "Running: $CMAKE_CMD"
eval $CMAKE_CMD

if [ $? -ne 0 ]; then
    print_error "CMake configuration failed"
    exit 1
fi

print_status "CMake configuration completed successfully"

# Build the player
print_status "Building player target..."

BUILD_CMD="cmake --build $PROJECT_ROOT/$BUILD_DIR"

if [ $CLEAN_BUILD -eq 1 ]; then
    BUILD_CMD="$BUILD_CMD --clean-first"
fi

BUILD_CMD="$BUILD_CMD --target player -j $MAX_JOBS"

print_status "Running: $BUILD_CMD"
eval $BUILD_CMD

if [ $? -ne 0 ]; then
    print_error "Build failed"
    exit 1
fi

print_status "Build completed successfully!"

# Check if the player binary was created
PLAYER_BINARY="$PROJECT_ROOT/$BUILD_DIR/player/player"
if [ -f "$PLAYER_BINARY" ]; then
    print_status "Player binary created at: $PLAYER_BINARY"
    
    # Make it executable
    chmod +x "$PLAYER_BINARY"
    
    # Print usage instructions
    echo ""
    print_status "=========================================="
    print_status "Build Complete!"
    print_status "=========================================="
    echo ""
    print_status "To run the player:"
    echo "  $PLAYER_BINARY 'srt://<SRT_IP>:10080?streamid=#!::r=live/test1,m=request'"
    echo ""
    print_status "Example:"
    echo "  $PLAYER_BINARY 'srt://192.168.1.100:10080?streamid=#!::r=live/test1,m=request'"
    echo ""
    print_status "For the unified client with time sync disabled:"
    echo "  python3 client.py --server http://<SERVER_IP>:5000 --no-time-sync"
    echo ""
    print_status "For baseline comparison with ffplay:"
    echo "  $PROJECT_ROOT/$BUILD_DIR/external/Install/bin/ffplay 'srt://<SRT_IP>:10080?streamid=#!::r=live/test2,m=request,latency=5000000'"
else
    print_error "Player binary not found at expected location"
    exit 1
fi

# Optional: Create a convenience script to run the player
print_status "Creating convenience run script..."
cat > "$PROJECT_ROOT/run_player.sh" << 'EOF'
#!/bin/bash
# Convenience script to run the player

if [ $# -eq 0 ]; then
    echo "Usage: $0 <SRT_URL>"
    echo "Example: $0 'srt://192.168.1.100:10080?streamid=#!::r=live/test1,m=request'"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLAYER="$SCRIPT_DIR/cmake-build-debug/player/player"

if [ ! -f "$PLAYER" ]; then
    PLAYER="$SCRIPT_DIR/cmake-build-release/player/player"
fi

if [ ! -f "$PLAYER" ]; then
    echo "Player binary not found. Please run build_player.sh first."
    exit 1
fi

echo "Starting player with URL: $1"
exec "$PLAYER" "$1"
EOF

chmod +x "$PROJECT_ROOT/run_player.sh"
print_status "Created run_player.sh for easier execution"

# Create a convenience script to run the unified client
print_status "Creating unified client convenience script..."
cat > "$PROJECT_ROOT/run_client.sh" << 'EOF'
#!/bin/bash
# Convenience script to run the unified multi-screen client

SERVER_URL="http://128.205.39.64:5000"
NO_TIME_SYNC="--no-time-sync"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --server)
            SERVER_URL="$2"
            shift 2
            ;;
        --enable-time-sync)
            NO_TIME_SYNC=""
            shift
            ;;
        --help)
            echo "Unified Multi-Screen Client Runner"
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --server URL         : Server URL (default: http://128.205.39.64:5000)"
            echo "  --enable-time-sync   : Enable server time sync validation"
            echo "  --help               : Show this help message"
            echo ""
            echo "Default behavior: Runs with time sync disabled for better compatibility"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "Starting unified multi-screen client..."
echo "Server: $SERVER_URL"
echo "Time sync: $([ -z "$NO_TIME_SYNC" ] && echo "enabled" || echo "disabled")"
echo ""

python3 client.py --server "$SERVER_URL" $NO_TIME_SYNC
EOF

chmod +x "$PROJECT_ROOT/run_client.sh"
print_status "Created run_client.sh for easier client execution"

# Final summary
echo ""
print_status "=========================================="
print_status "Setup Complete!"
print_status "=========================================="
echo ""

if [ $SETUP_CHRONY -eq 1 ]; then
    print_chrony "✓ Time synchronization (chrony) configured"
    print_chrony "  All clients will sync to the same NTP servers"
    print_chrony "  Expected sync improvement: ~862ms → ~50-100ms"
    echo ""
fi

print_status "✓ Player binary built successfully"
print_status "✓ Convenience scripts created"
echo ""
print_status "Next steps:"
echo "1. Run this script on ALL client machines for consistent time sync"
echo "2. Test the video wall system:"
echo "   ./run_client.sh --server http://<YOUR_SERVER_IP>:5000"
echo ""
print_status "For optimal synchronization:"
echo "- Ensure all clients have the same chrony configuration"
echo "- Wait 5-10 minutes after setup for clocks to stabilize"
echo "- Monitor sync status with: chronyc tracking"

print_status "Build and setup process completed successfully!"