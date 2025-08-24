#!/bin/bash

# Multi-Screen Client Dependencies Installation Script
# This script installs dependencies for the enhanced multi-screen client
# Usage: ./install_dependencies.sh [options]

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/setup.log"
FORCE_INSTALL=false
SKIP_REBOOT=false

# Function to print colored output
print_header() {
    echo -e "${PURPLE}================================${NC}"
    echo -e "${PURPLE}$1${NC}"
    echo -e "${PURPLE}================================${NC}"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
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

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Function to check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_error "This script should not be run as root"
        print_info "Please run as a regular user with sudo privileges"
        exit 1
    fi
}

# Function to check if running on Raspberry Pi
check_raspberry_pi() {
    print_step "Checking system compatibility..."
    
    if [[ -f /proc/device-tree/model ]]; then
        MODEL=$(cat /proc/device-tree/model 2>/dev/null)
        if [[ "$MODEL" == *"Raspberry Pi"* ]]; then
            print_success "Detected: $MODEL"
            log_message "System: $MODEL"
            return 0
        fi
    fi
    
    print_warning "Not running on Raspberry Pi - some features may not work"
    if [[ $FORCE_INSTALL != true ]]; then
        print_info "Continue anyway? (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Function to update system packages
update_system() {
    print_step "Updating system packages..."
    log_message "Starting system update"
    
    sudo apt update 2>&1 | tee -a "$LOG_FILE"
    if [[ $FORCE_INSTALL == true ]]; then
        sudo apt upgrade -y 2>&1 | tee -a "$LOG_FILE"
    else
        print_info "Upgrade system packages? (y/N)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            sudo apt upgrade -y 2>&1 | tee -a "$LOG_FILE"
        fi
    fi
    
    print_success "System packages updated"
    log_message "System update completed"
}

# Function to install required packages
install_packages() {
    print_step "Installing required packages..."
    log_message "Starting package installation"
    
    # Core packages (must have)
    CORE_PACKAGES=(
        "ffmpeg"           # Video playback
        "wmctrl"           # Window management
        "xdotool"          # X11 automation
        "curl"             # Network utilities
        "git"              # Version control
    )
    
    # Python packages (try multiple variants)
    PYTHON_PACKAGES=(
        "python3-requests" # Python HTTP library
    )
    
    # Tkinter packages (try different names for different OS versions)
    TKINTER_PACKAGES=(
        "python3-tk"       # Standard name
        "python3-tkinter"  # Alternative name
        "tk-dev"           # Development package
        "tkinter"          # Sometimes just this
    )
    
    # X11 packages (nice to have)
    X11_PACKAGES=(
        "x11-apps"         # X11 utilities (xeyes, etc.)
    )
    
    # Install core packages first
    print_info "Installing core packages..."
    missing_core=()
    for package in "${CORE_PACKAGES[@]}"; do
        if ! dpkg -l | grep -q "^ii  $package "; then
            missing_core+=("$package")
        fi
    done
    
    if [[ ${#missing_core[@]} -gt 0 ]]; then
        print_info "Installing: ${missing_core[*]}"
        if ! sudo apt install -y "${missing_core[@]}" 2>&1 | tee -a "$LOG_FILE"; then
            print_error "Failed to install core packages: ${missing_core[*]}"
            return 1
        fi
    fi
    
    # Install Python packages
    print_info "Installing Python packages..."
    missing_python=()
    for package in "${PYTHON_PACKAGES[@]}"; do
        if ! dpkg -l | grep -q "^ii  $package "; then
            missing_python+=("$package")
        fi
    done
    
    if [[ ${#missing_python[@]} -gt 0 ]]; then
        print_info "Installing: ${missing_python[*]}"
        if ! sudo apt install -y "${missing_python[@]}" 2>&1 | tee -a "$LOG_FILE"; then
            print_warning "Failed to install some Python packages, trying pip..."
            # Fallback to pip for requests
            if ! python3 -c "import requests" 2>/dev/null; then
                sudo apt install -y python3-pip 2>&1 | tee -a "$LOG_FILE" || true
                pip3 install requests 2>&1 | tee -a "$LOG_FILE" || true
            fi
        fi
    fi
    
    # Try to install Tkinter (try different package names)
    print_info "Installing Tkinter (GUI support)..."
    tkinter_installed=false
    
    # First check if tkinter is already available
    if python3 -c "import tkinter" 2>/dev/null; then
        print_success "Tkinter already available"
        tkinter_installed=true
    else
        # Try different package names
        for package in "${TKINTER_PACKAGES[@]}"; do
            if dpkg -l | grep -q "^ii  $package "; then
                print_success "$package already installed"
                tkinter_installed=true
                break
            fi
            
            print_info "Trying to install $package..."
            if sudo apt install -y "$package" 2>&1 | tee -a "$LOG_FILE"; then
                print_success "$package installed successfully"
                tkinter_installed=true
                break
            else
                print_warning "Failed to install $package, trying next option..."
            fi
        done
    fi
    
    # If tkinter still not available, try alternative approaches
    if ! $tkinter_installed; then
        print_warning "Standard tkinter packages failed, trying alternatives..."
        
        # Try installing python3-dev and building
        print_info "Installing development packages..."
        sudo apt install -y python3-dev python3-pip build-essential 2>&1 | tee -a "$LOG_FILE" || true
        
        # Update package cache and try again
        print_info "Updating package cache and retrying..."
        sudo apt update 2>&1 | tee -a "$LOG_FILE"
        
        if sudo apt install -y python3-tk 2>&1 | tee -a "$LOG_FILE"; then
            print_success "python3-tk installed on retry"
            tkinter_installed=true
        else
            print_warning "Could not install tkinter packages"
            print_info "Hotkeys may not work, but video playback will still function"
        fi
    fi
    
    # Install X11 packages (optional)
    print_info "Installing X11 utilities..."
    missing_x11=()
    for package in "${X11_PACKAGES[@]}"; do
        if ! dpkg -l | grep -q "^ii  $package "; then
            missing_x11+=("$package")
        fi
    done
    
    if [[ ${#missing_x11[@]} -gt 0 ]]; then
        print_info "Installing: ${missing_x11[*]}"
        if ! sudo apt install -y "${missing_x11[@]}" 2>&1 | tee -a "$LOG_FILE"; then
            print_warning "Failed to install X11 utilities (optional)"
        fi
    fi
    
    # Final verification
    print_step "Verifying installations..."
    
    # Check core tools
    failed_tools=()
    for tool in ffmpeg wmctrl xdotool; do
        if ! command -v "$tool" &> /dev/null; then
            failed_tools+=("$tool")
        fi
    done
    
    if [[ ${#failed_tools[@]} -gt 0 ]]; then
        print_error "Critical tools missing: ${failed_tools[*]}"
        return 1
    fi
    
    # Check Python modules
    if ! python3 -c "import requests" 2>/dev/null; then
        print_warning "Python requests module not available"
        print_info "Client may have networking issues"
    fi
    
    if ! python3 -c "import tkinter" 2>/dev/null; then
        print_warning "Python tkinter module not available"
        print_info "Hotkeys will not work, but video playback will still function"
    else
        print_success "Tkinter available - hotkeys will work"
    fi
    
    print_success "Package installation completed"
    log_message "Package installation completed"
}

# Function to configure dual HDMI
configure_dual_hdmi() {
    print_step "Configuring dual HDMI support..."
    log_message "Starting dual HDMI configuration"
    
    # Check if already configured
    if grep -q "dtoverlay=vc4-kms-v3d" /boot/config.txt 2>/dev/null; then
        print_success "Dual HDMI overlay already enabled"
        return 0
    fi
    
    # Backup config
    sudo cp /boot/config.txt /boot/config.txt.backup.$(date +%Y%m%d_%H%M%S)
    print_info "Backed up /boot/config.txt"
    
    # Add dual HDMI configuration
    print_info "Adding dual HDMI configuration to /boot/config.txt..."
    sudo tee -a /boot/config.txt > /dev/null << 'EOF'

# Multi-Screen Client Configuration
# Added by install script
dtoverlay=vc4-kms-v3d
max_framebuffers=2
disable_fw_kms_setup=1
disable_overscan=1
EOF
    
    print_success "Dual HDMI configuration added"
    print_warning "Reboot required for changes to take effect"
    log_message "Dual HDMI configuration completed"
}

# Function to test display setup
test_display_setup() {
    print_step "Testing display configuration..."
    log_message "Starting display test"
    
    # Check current display system
    print_info "Display system: $XDG_SESSION_TYPE"
    print_info "Current display: $DISPLAY"
    
    if [[ "$XDG_SESSION_TYPE" == "wayland" ]]; then
        print_warning "Wayland detected - X11 is recommended for better window management"
        print_info "Please use 'sudo raspi-config' to switch to X11:"
        print_info "  Advanced Options → Wayland → X11 → Reboot"
    elif [[ "$XDG_SESSION_TYPE" == "x11" ]]; then
        print_success "X11 detected - optimal for window management"
    else
        print_warning "Unknown display system: $XDG_SESSION_TYPE"
    fi
    
    # Test xrandr
    if command -v xrandr &> /dev/null; then
        print_info "Available monitors:"
        xrandr --listmonitors 2>/dev/null || print_warning "Could not list monitors"
        
        print_info "Available outputs:"
        xrandr --listoutputs 2>/dev/null || print_warning "Could not list outputs"
    else
        print_warning "xrandr not available"
    fi
    
    # Test window management tools
    if command -v wmctrl &> /dev/null; then
        print_success "wmctrl available"
    else
        print_error "wmctrl not available"
        return 1
    fi
    
    if command -v xdotool &> /dev/null; then
        print_success "xdotool available"
    else
        print_error "xdotool not available"
        return 1
    fi
    
    # Test ffplay
    if command -v ffplay &> /dev/null; then
        print_success "ffplay available"
    else
        print_error "ffplay not available"
        return 1
    fi
    
    log_message "Display test completed"
}

# Function to run final tests
run_final_tests() {
    print_step "Running final validation tests..."
    log_message "Starting final tests"
    
    # Test 1: Check client.py exists
    if [[ -f "$SCRIPT_DIR/client.py" ]]; then
        print_success "client.py found"
    else
        print_warning "client.py not found in $SCRIPT_DIR"
        print_info "Make sure your enhanced client.py is in this directory"
    fi
    
    # Test 2: Check Python imports
    if python3 -c "import tkinter, subprocess, requests, argparse" 2>/dev/null; then
        print_success "Python dependencies available"
    else
        print_error "Python dependencies missing"
        return 1
    fi
    
    # Test 3: Check X11 tools
    local tools_ok=true
    for tool in wmctrl xdotool ffplay; do
        if command -v "$tool" &> /dev/null; then
            print_success "$tool available"
        else
            print_error "$tool not available"
            tools_ok=false
        fi
    done
    
    if [[ $tools_ok != true ]]; then
        return 1
    fi
    
    # Test 4: Test display access
    if DISPLAY=:0 xset q &>/dev/null; then
        print_success "X11 display accessible"
    else
        print_warning "X11 display not accessible (may need GUI session)"
    fi
    
    # Test 5: Test client.py syntax (if it exists)
    if [[ -f "$SCRIPT_DIR/client.py" ]]; then
        if python3 -m py_compile "$SCRIPT_DIR/client.py" 2>/dev/null; then
            print_success "client.py syntax is valid"
        else
            print_warning "client.py has syntax issues"
        fi
    fi
    
    print_success "Validation tests completed"
    log_message "Final tests completed"
}

# Function to show final instructions
show_final_instructions() {
    print_header "SETUP COMPLETE!"
    
    echo
    print_success "All dependencies installed successfully!"
    echo
    
    if [[ -f "$SCRIPT_DIR/client.py" ]]; then
        print_success "Your existing client.py is ready to use"
    else
        print_warning "client.py not found - make sure your enhanced client is in this directory"
    fi
    
    echo
    print_info "You can now use your client with all dependencies installed:"
    echo
    print_info "Example usage:"
    echo "  python3 client.py --server http://YOUR_SERVER:5000 --hostname rpi-client-1 --display-name \"HDMI-1\" --target-screen HDMI1"
    echo "  python3 client.py --server http://YOUR_SERVER:5000 --hostname rpi-client-2 --display-name \"HDMI-2\" --target-screen HDMI2"
    echo
    print_info "Quick test (optional):"
    echo "  ffplay -f lavfi -i testsrc2=size=1920x1080:rate=30 -window_title \"Test HDMI1\" -x 1920 -y 1080 -left 0 -top 0 -t 3"
    echo "  ffplay -f lavfi -i testsrc2=size=1920x1080:rate=30 -window_title \"Test HDMI2\" -x 1920 -y 1080 -left 1920 -top 0 -t 3"
    echo
    
    if [[ "$XDG_SESSION_TYPE" == "x11" ]]; then
        print_success "X11 display system detected - optimal configuration"
    elif [[ "$XDG_SESSION_TYPE" == "wayland" ]]; then
        print_warning "Wayland detected - please switch to X11 for optimal performance"
        print_info "Use: sudo raspi-config → Advanced Options → Wayland → X11 → Reboot"
    fi
    
    if grep -q "dtoverlay=vc4-kms-v3d" /boot/config.txt 2>/dev/null; then
        if [[ $SKIP_REBOOT != true ]]; then
            print_warning "REBOOT REQUIRED for dual HDMI changes to take effect"
            print_info "Reboot now? (y/N)"
            read -r response
            if [[ "$response" =~ ^[Yy]$ ]]; then
                print_info "Rebooting in 5 seconds... Press Ctrl+C to cancel"
                sleep 5
                sudo reboot
            else
                print_warning "Remember to reboot later for changes to take effect"
            fi
        fi
    else
        print_success "Dual HDMI already configured"
    fi
    
    echo
    print_info "Installed packages:"
    echo "  ✓ ffmpeg (video playback)"
    echo "  ✓ wmctrl (window management)"
    echo "  ✓ xdotool (X11 automation)"
    echo "  ✓ python3-tk (GUI support)"
    echo "  ✓ x11-apps (testing tools)"
    echo "  ✓ python3-requests (HTTP library)"
    echo
    print_info "Setup log saved to: $LOG_FILE"
    print_success "Ready to use with your existing client.py! 🎉"
}

# Function to show usage
show_usage() {
    cat << EOF
Multi-Screen Client Dependencies Installation Script

Usage: $0 [OPTIONS]

OPTIONS:
    -f, --force         Force installation without prompts
    -s, --skip-reboot   Skip reboot prompt
    -h, --help          Show this help message

EXAMPLES:
    $0                  # Interactive setup
    $0 -f               # Force setup without prompts
    $0 -f -s            # Force setup, skip reboot

This script will:
1. Check system compatibility
2. Update system packages
3. Install required packages (ffmpeg, wmctrl, xdotool, etc.)
4. Configure dual HDMI support
5. Test display setup
6. Run validation tests

Note: If you're using Wayland, please switch to X11 using 'sudo raspi-config'
Your existing client.py will remain unchanged.

EOF
}

# Main execution function
main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -f|--force)
                FORCE_INSTALL=true
                shift
                ;;
            -s|--skip-reboot)
                SKIP_REBOOT=true
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Start logging
    echo "Setup started at $(date)" > "$LOG_FILE"
    
    print_header "MULTI-SCREEN CLIENT DEPENDENCIES SETUP"
    
    echo
    print_info "This script will install dependencies for the multi-screen client"
    print_info "Your existing client.py will NOT be modified"
    print_info "No convenience scripts will be created"
    print_info "Log file: $LOG_FILE"
    echo
    
    if [[ $FORCE_INSTALL != true ]]; then
        print_info "Continue with setup? (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            print_info "Setup cancelled"
            exit 0
        fi
    fi
    
    # Run setup steps
    check_root
    check_raspberry_pi
    update_system
    install_packages
    configure_dual_hdmi
    test_display_setup
    run_final_tests
    show_final_instructions
    
    log_message "Setup completed successfully"
}

# Run main function with all arguments
main "$@"
