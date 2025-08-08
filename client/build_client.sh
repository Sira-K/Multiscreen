#!/bin/bash

# Multi-Screen Player Build Script
# This script automates the building process for the multi-screen player project
# Usage: ./build_player.sh [options]
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
        --help)
            echo "Multi-Screen Player Build Script"
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --force-rebuild  : Force rebuild of external dependencies (default)"
            echo "  --no-rebuild     : Skip rebuilding external dependencies"
            echo "  --jobs N         : Set number of parallel jobs (default: auto-detect)"
            echo "  --debug          : Build in debug mode (default)"
            echo "  --release        : Build in release mode"
            echo "  --clean          : Clean build directories before building"
            echo "  --help           : Show this help message"
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

print_status "Build process completed successfully!"