#!/bin/bash
# Enhanced Multi-Screen Client Setup Script (Corrected Version)
# This script installs all dependencies and sets up the environment for the client

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Global variables for cleanup tracking
SETUP_LOG="$HOME/.client_setup.log"
PACKAGES_INSTALLED=""
SYSTEM_CHANGES=""

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] $1" >> "$SETUP_LOG"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [SUCCESS] $1" >> "$SETUP_LOG"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [WARNING] $1" >> "$SETUP_LOG"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] $1" >> "$SETUP_LOG"
}

# Function to log system changes for cleanup
log_change() {
    echo "$1" >> "$SETUP_LOG"
    SYSTEM_CHANGES="$SYSTEM_CHANGES\n$1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to confirm action
confirm_action() {
    local message="$1"
    local default="${2:-n}"
    
    if [[ "$default" == "y" ]]; then
        read -p "$message [Y/n]: " -n 1 -r
        echo
        [[ $REPLY =~ ^[Nn]$ ]] && return 1 || return 0
    else
        read -p "$message [y/N]: " -n 1 -r
        echo
        [[ $REPLY =~ ^[Yy]$ ]] && return 0 || return 1
    fi
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
    log_change "DETECTED_OS=$OS $VER"
}

# Function to check Python version properly
check_python_version() {
    if command_exists python3; then
        if python3 -c "import sys; exit(0 if sys.version_info >= (3, 7) else 1)" 2>/dev/null; then
            PYTHON_VERSION=$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
            print_status "Python version: $PYTHON_VERSION (OK)"
            return 0
        else
            PYTHON_VERSION=$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:2])))" 2>/dev/null || echo "unknown")
            print_warning "Python version: $PYTHON_VERSION (needs upgrade)"
            return 1
        fi
    else
        print_warning "Python 3 is not installed"
        return 1
    fi
}

# Function to update package lists
update_packages() {
    print_status "Updating package lists..."
    
    if command_exists apt-get; then
        if sudo apt-get update; then
            log_change "UPDATED_APT_CACHE=true"
        else
            print_error "Failed to update apt cache"
            return 1
        fi
    elif command_exists dnf; then
        # Prioritize dnf over yum for newer systems
        if sudo dnf update -y; then
            log_change "UPDATED_DNF_CACHE=true"
        else
            print_error "Failed to update dnf cache"
            return 1
        fi
    elif command_exists yum; then
        if sudo yum update -y; then
            log_change "UPDATED_YUM_CACHE=true"
        else
            print_error "Failed to update yum cache"
            return 1
        fi
    elif command_exists pacman; then
        if sudo pacman -Sy; then
            log_change "UPDATED_PACMAN_CACHE=true"
        else
            print_error "Failed to update pacman cache"
            return 1
        fi
    else
        print_warning "Unknown package manager, skipping update"
        return 0
    fi
}

# Function to enable additional repositories
enable_repositories() {
    print_status "Checking and enabling additional repositories..."
    
    if command_exists yum && [[ "$OS" == *"CentOS"* || "$OS" == *"Red Hat"* || "$OS" == *"RHEL"* ]]; then
        # Enable EPEL for CentOS/RHEL
        if ! rpm -qa | grep -q epel-release; then
            print_status "Installing EPEL repository..."
            if sudo yum install -y epel-release; then
                log_change "INSTALLED_EPEL=true"
                PACKAGES_INSTALLED="$PACKAGES_INSTALLED epel-release"
            else
                print_error "Failed to install EPEL repository"
                return 1
            fi
        fi
        
        # Enable RPM Fusion for ffmpeg
        if ! rpm -qa | grep -q rpmfusion-free-release; then
            print_status "Installing RPM Fusion repository..."
            if [[ "$VER" == "7" ]]; then
                RPMFUSION_URL="https://download1.rpmfusion.org/free/el/rpmfusion-free-release-7.noarch.rpm"
            elif [[ "$VER" == "8" ]]; then
                RPMFUSION_URL="https://download1.rpmfusion.org/free/el/rpmfusion-free-release-8.noarch.rpm"
            elif [[ "$VER" == "9" ]]; then
                RPMFUSION_URL="https://download1.rpmfusion.org/free/el/rpmfusion-free-release-9.noarch.rpm"
            else
                print_warning "Unsupported RHEL/CentOS version for RPM Fusion: $VER"
                return 0
            fi
            
            if sudo yum localinstall --nogpgcheck -y "$RPMFUSION_URL"; then
                log_change "INSTALLED_RPMFUSION=true"
                PACKAGES_INSTALLED="$PACKAGES_INSTALLED rpmfusion-free-release"
            else
                print_warning "Failed to install RPM Fusion, ffmpeg may not be available"
            fi
        fi
    fi
}

# Function to install Python dependencies
install_python_deps() {
    print_status "Installing Python dependencies..."
    
    # Check and install Python if needed
    if ! check_python_version; then
        print_status "Installing/upgrading Python 3..."
        
        if command_exists apt-get; then
            if sudo apt-get install -y python3 python3-pip python3-dev python3-tk python3-full; then
                log_change "INSTALLED_PYTHON3_APT=true"
                PACKAGES_INSTALLED="$PACKAGES_INSTALLED python3 python3-pip python3-dev python3-tk python3-full"
            else
                print_error "Failed to install Python 3 via apt"
                return 1
            fi
        elif command_exists dnf; then
            if sudo dnf install -y python3 python3-pip python3-devel python3-tkinter; then
                log_change "INSTALLED_PYTHON3_DNF=true"
                PACKAGES_INSTALLED="$PACKAGES_INSTALLED python3 python3-pip python3-devel python3-tkinter"
            else
                print_error "Failed to install Python 3 via dnf"
                return 1
            fi
        elif command_exists yum; then
            if sudo yum install -y python3 python3-pip python3-devel python3-tkinter; then
                log_change "INSTALLED_PYTHON3_YUM=true"
                PACKAGES_INSTALLED="$PACKAGES_INSTALLED python3 python3-pip python3-devel python3-tkinter"
            else
                print_error "Failed to install Python 3 via yum"
                return 1
            fi
        else
            print_error "Cannot install Python 3 - unknown package manager"
            return 1
        fi
        
        # Verify installation
        if ! check_python_version; then
            print_error "Python 3.7+ installation failed"
            return 1
        fi
    fi
    
    print_success "Python dependencies setup complete"
    print_status "The client will automatically install required packages (requests) locally when first run"
    print_status "No manual pip installation needed - the client handles everything!"
    
    return 0
}

# Function to install system dependencies
install_system_deps() {
    print_status "Installing system dependencies..."
    
    local common_packages=""
    local gui_packages=""
    local build_packages=""
    local util_packages=""
    
    if command_exists apt-get; then
        # Debian/Ubuntu
        common_packages="ffmpeg curl wget git"
        gui_packages="wmctrl xdotool python3-tk x11-utils xinit"
        build_packages="build-essential cmake pkg-config"
        util_packages="htop vim nano net-tools procps"
        
        local all_packages="$common_packages $gui_packages $build_packages $util_packages"
        
        if sudo apt-get install -y $all_packages; then
            log_change "INSTALLED_APT_PACKAGES=$all_packages"
            PACKAGES_INSTALLED="$PACKAGES_INSTALLED $all_packages"
        else
            print_error "Failed to install system packages via apt"
            return 1
        fi
        
    elif command_exists dnf; then
        # Fedora
        common_packages="ffmpeg curl wget git"
        gui_packages="wmctrl xdotool python3-tkinter xorg-x11-utils xorg-x11-xinit"
        build_packages="gcc gcc-c++ make cmake pkgconfig"
        util_packages="htop vim nano net-tools procps-ng"
        
        local all_packages="$common_packages $gui_packages $build_packages $util_packages"
        
        if sudo dnf install -y $all_packages; then
            log_change "INSTALLED_DNF_PACKAGES=$all_packages"
            PACKAGES_INSTALLED="$PACKAGES_INSTALLED $all_packages"
        else
            print_error "Failed to install system packages via dnf"
            return 1
        fi
        
    elif command_exists yum; then
        # CentOS/RHEL
        common_packages="ffmpeg curl wget git"
        gui_packages="wmctrl xdotool python3-tkinter xorg-x11-utils xorg-x11-xinit"
        build_packages="gcc gcc-c++ make cmake pkgconfig"
        util_packages="htop vim nano net-tools procps-ng"
        
        local all_packages="$common_packages $gui_packages $build_packages $util_packages"
        
        if sudo yum install -y $all_packages; then
            log_change "INSTALLED_YUM_PACKAGES=$all_packages"
            PACKAGES_INSTALLED="$PACKAGES_INSTALLED $all_packages"
        else
            print_error "Failed to install system packages via yum"
            return 1
        fi
        
    elif command_exists pacman; then
        # Arch Linux
        common_packages="ffmpeg curl wget git"
        gui_packages="wmctrl xdotool tk xorg-xrandr xorg-xinit"
        build_packages="base-devel cmake pkgconf"
        util_packages="htop vim nano net-tools procps-ng"
        
        local all_packages="$common_packages $gui_packages $build_packages $util_packages"
        
        if sudo pacman -S --noconfirm $all_packages; then
            log_change "INSTALLED_PACMAN_PACKAGES=$all_packages"
            PACKAGES_INSTALLED="$PACKAGES_INSTALLED $all_packages"
        else
            print_error "Failed to install system packages via pacman"
            return 1
        fi
        
    else
        print_error "Unknown package manager, cannot install dependencies"
        print_status "Required packages: ffmpeg, wmctrl, xdotool, python3-tk, build tools"
        return 1
    fi
}

# Function to install C++ player (optional)
install_cpp_player() {
    print_status "Checking for C++ player..."
    
    if [[ -d "multi-screen" ]]; then
        print_status "C++ player source found, attempting to build..."
        
        local original_dir="$(pwd)"
        
        if ! cd multi-screen; then
            print_warning "Cannot enter multi-screen directory"
            cd "$original_dir"
            return 0
        fi
        
        # Create build directory
        if ! mkdir -p cmake-build-debug; then
            print_warning "Cannot create build directory"
            cd "$original_dir"
            return 0
        fi
        
        if ! cd cmake-build-debug; then
            print_warning "Cannot enter build directory"
            cd "$original_dir"
            return 0
        fi
        
        # Configure and build
        if command_exists cmake; then
            print_status "Configuring with CMake..."
            if cmake ..; then
                print_status "Building C++ player..."
                if make -j$(nproc); then
                    if [[ -f "player/player" ]]; then
                        print_success "C++ player built successfully"
                        chmod +x player/player
                        log_change "BUILT_CPP_PLAYER=true"
                        log_change "CPP_PLAYER_PATH=$(pwd)/player/player"
                    else
                        print_warning "C++ player executable not found after build"
                    fi
                else
                    print_warning "C++ player build failed, will use ffplay fallback"
                fi
            else
                print_warning "CMake configuration failed, will use ffplay fallback"
            fi
        else
            print_warning "CMake not found, skipping C++ player build"
        fi
        
        cd "$original_dir"
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
        
        # Add to bashrc if not already there
        if ! grep -q "export DISPLAY=:0.0" ~/.bashrc 2>/dev/null; then
            echo 'export DISPLAY=:0.0' >> ~/.bashrc
            log_change "ADDED_DISPLAY_TO_BASHRC=true"
        fi
    fi
    
    # Check if running in X11
    if command_exists xset; then
        if xset q >/dev/null 2>&1; then
            print_success "X11 server is accessible"
        else
            print_warning "X11 server not accessible"
            print_status "You may need to run 'startx' or connect to existing X server"
        fi
    else
        print_warning "xset command not available, cannot test X11 connectivity"
    fi
    
    # Check for multiple monitors
    if command_exists xrandr; then
        local monitor_count
        monitor_count=$(xrandr --listmonitors 2>/dev/null | grep -c "Monitor" || echo "0")
        print_status "Detected $monitor_count monitor(s)"
        log_change "DETECTED_MONITORS=$monitor_count"
        
        if [[ $monitor_count -lt 2 ]]; then
            print_warning "Less than 2 monitors detected"
            print_status "Multi-screen functionality may be limited"
        fi
    else
        print_warning "xrandr not available, cannot detect monitors"
    fi
}

# Function to setup logging
setup_logging() {
    print_status "Setting up logging..."
    
    # Create log directory
    if mkdir -p ~/client_logs; then
        log_change "CREATED_LOG_DIR=$HOME/client_logs"
    else
        print_error "Failed to create log directory"
        return 1
    fi
    
    # Create log rotation script
    local rotate_script="$HOME/client_logs/rotate_logs.sh"
    cat > "$rotate_script" << 'EOF'
#!/bin/bash
# Log rotation script for client logs

LOG_DIR="$HOME/client_logs"
MAX_SIZE="10M"
MAX_FILES=5

# Truncate large log files
find "$LOG_DIR" -name "*.log" -size +$MAX_SIZE -exec truncate -s 0 {} \;

# Remove old rotated logs
find "$LOG_DIR" -name "*.log.*" -mtime +7 -delete

# Keep only the last MAX_FILES log files
for log_file in "$LOG_DIR"/*.log; do
    if [[ -f "$log_file" ]]; then
        ls -t "${log_file}"* 2>/dev/null | tail -n +$((MAX_FILES + 1)) | xargs -r rm
    fi
done
EOF
    
    if chmod +x "$rotate_script"; then
        log_change "CREATED_LOG_ROTATION_SCRIPT=$rotate_script"
    else
        print_error "Failed to create log rotation script"
        return 1
    fi
    
    # Add to crontab for daily rotation (only if not already there)
    local cron_entry="0 2 * * * $HOME/client_logs/rotate_logs.sh"
    if ! crontab -l 2>/dev/null | grep -q "rotate_logs.sh"; then
        if (crontab -l 2>/dev/null; echo "$cron_entry") | crontab -; then
            log_change "ADDED_CRON_JOB=$cron_entry"
        else
            print_warning "Failed to add cron job for log rotation"
        fi
    else
        print_status "Log rotation cron job already exists"
    fi
    
    print_success "Logging setup complete"
}

# Function to create systemd service (optional)
create_systemd_service() {
    print_status "Checking for systemd service..."
    
    # Look for potential service files
    local service_files=("client.service" "video-client.service" "multi-screen-client.service")
    local found_service=""
    
    for service_file in "${service_files[@]}"; do
        if [[ -f "$service_file" ]]; then
            found_service="$service_file"
            break
        fi
    done
    
    if [[ -n "$found_service" ]]; then
        print_status "Found service file: $found_service"
        print_status "Installing systemd service..."
        
        if sudo cp "$found_service" /etc/systemd/system/; then
            if sudo systemctl daemon-reload; then
                if sudo systemctl enable "$found_service"; then
                    log_change "INSTALLED_SYSTEMD_SERVICE=$found_service"
                    print_success "Systemd service installed and enabled"
                else
                    print_warning "Failed to enable systemd service"
                fi
            else
                print_warning "Failed to reload systemd daemon"
            fi
        else
            print_warning "Failed to copy service file"
        fi
    else
        print_status "No systemd service file found, skipping systemd setup"
    fi
}

# Function to test client
test_client() {
    print_status "Testing client installation..."
    
    local test_failures=0
    
    # Test Python imports
    print_status "Testing Python dependencies..."
    if python3 -c "import requests, tkinter, subprocess, threading" 2>/dev/null; then
        print_success "Python dependencies working"
    else
        print_error "Python dependencies test failed"
        test_failures=$((test_failures + 1))
    fi
    
    # Test ffmpeg
    print_status "Testing ffmpeg..."
    if command_exists ffmpeg; then
        if ffmpeg -version >/dev/null 2>&1; then
            print_success "ffmpeg working"
        else
            print_error "ffmpeg not working properly"
            test_failures=$((test_failures + 1))
        fi
    else
        print_error "ffmpeg not found"
        test_failures=$((test_failures + 1))
    fi
    
    # Test window management tools
    print_status "Testing window management tools..."
    if command_exists wmctrl && command_exists xdotool; then
        print_success "Window management tools available"
    else
        print_warning "Some window management tools missing (wmctrl/xdotool)"
    fi
    
    # Test client.py
    print_status "Testing client.py..."
    if [[ -f "client.py" ]]; then
        if python3 client.py --help >/dev/null 2>&1; then
            print_success "client.py working correctly"
        else
            print_error "client.py test failed"
            test_failures=$((test_failures + 1))
        fi
    else
        print_error "client.py not found"
        test_failures=$((test_failures + 1))
    fi
    
    # Test network connectivity
    print_status "Testing network connectivity..."
    if command_exists curl; then
        if curl -s --connect-timeout 5 http://google.com >/dev/null 2>&1; then
            print_success "Network connectivity working"
        else
            print_warning "Network connectivity test failed"
        fi
    else
        print_warning "curl not available for network test"
    fi
    
    if [[ $test_failures -eq 0 ]]; then
        print_success "All critical tests passed"
        return 0
    else
        print_error "$test_failures critical test(s) failed"
        return 1
    fi
}

# Function to show usage examples
show_examples() {
    print_success "Setup complete! Here are usage examples:"
    echo
    
    print_status "🎉 NEW: The client now automatically installs required Python packages!"
    print_status "You can run the client directly without worrying about dependencies."
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
    echo "Debug Mode (shows auto-install process):"
    echo "  python3 client.py --server http://YOUR_SERVER:5000 \\"
    echo "    --hostname client1 --display-name 'Screen1' --target-screen 1 --debug"
    echo
    echo "Force ffplay:"
    echo "  python3 client.py --server http://YOUR_SERVER:5000 \\"
    echo "    --hostname client1 --display-name 'Screen1' --target-screen 1 --force-ffplay"
    echo
    echo "📦 Package Installation:"
    echo "  - The client automatically installs missing packages to ./lib/"
    echo "  - No global Python environment changes"
    echo "  - No virtual environments needed"
    echo "  - Just run and go!"
    echo
    echo "To cleanup this installation, run: ./cleanup_client.sh"
}

# Function to handle errors and cleanup
cleanup_on_error() {
    print_error "Setup failed. Check the log at: $SETUP_LOG"
    print_status "You can run ./cleanup_client.sh to remove changes"
    exit 1
}

# Main setup function
main() {
    # Initialize log
    echo "=== Enhanced Multi-Screen Client Setup Log ===" > "$SETUP_LOG"
    echo "Started: $(date)" >> "$SETUP_LOG"
    
    # Set up error handling
    trap cleanup_on_error ERR
    
    echo "============================================================"
    echo "Enhanced Multi-Screen Client Setup Script (Corrected)"
    echo "============================================================"
    echo
    
    # Check prerequisites
    check_root
    detect_os
    
    # Enable repositories first (before update)
    enable_repositories
    
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
        echo "Completed: $(date)" >> "$SETUP_LOG"
        echo
        show_examples
    else
        print_error "Client setup completed with some issues. Check the log for details."
        print_status "Log file: $SETUP_LOG"
        exit 1
    fi
}

# Run main function
main "$@"
