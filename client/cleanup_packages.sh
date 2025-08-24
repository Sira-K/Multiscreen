#!/bin/bash

# Package Cleanup Script for Testing Multi-Screen Client Setup
# This script removes packages to test the setup script from a clean state
# Usage: ./cleanup_packages.sh [options]

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Script configuration
FORCE_REMOVE=false
BACKUP_CONFIG=true

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

# Function to check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_error "This script should not be run as root"
        print_info "Please run as a regular user with sudo privileges"
        exit 1
    fi
}

# Function to backup boot config
backup_boot_config() {
    if [[ $BACKUP_CONFIG == true ]]; then
        print_step "Backing up boot configuration..."
        
        if [[ -f /boot/config.txt ]]; then
            sudo cp /boot/config.txt /boot/config.txt.backup.cleanup.$(date +%Y%m%d_%H%M%S)
            print_success "Boot config backed up"
        fi
        
        if [[ -f /boot/firmware/config.txt ]]; then
            sudo cp /boot/firmware/config.txt /boot/firmware/config.txt.backup.cleanup.$(date +%Y%m%d_%H%M%S)
            print_success "Firmware config backed up"
        fi
    fi
}

# Function to remove multi-screen client packages
remove_packages() {
    print_step "Removing multi-screen client packages..."
    
    # List of packages to remove (same as what setup script installs)
    PACKAGES_TO_REMOVE=(
        "ffmpeg"
        "wmctrl"
        "xdotool"
        "python3-tk"
        "x11-apps"
        "python3-requests"
        "curl"
        "git"
    )
    
    # Check which packages are actually installed
    installed_packages=()
    for package in "${PACKAGES_TO_REMOVE[@]}"; do
        if dpkg -l | grep -q "^ii  $package "; then
            installed_packages+=("$package")
        fi
    done
    
    if [[ ${#installed_packages[@]} -eq 0 ]]; then
        print_info "No target packages found to remove"
        return 0
    fi
    
    print_warning "The following packages will be removed:"
    for package in "${installed_packages[@]}"; do
        echo "  - $package"
    done
    echo
    
    if [[ $FORCE_REMOVE != true ]]; then
        print_warning "This will remove packages needed for the multi-screen client"
        print_info "Continue with removal? (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            print_info "Package removal cancelled"
            return 0
        fi
    fi
    
    print_step "Removing packages..."
    sudo apt remove --purge -y "${installed_packages[@]}"
    
    print_step "Cleaning up unused dependencies..."
    sudo apt autoremove -y
    sudo apt autoclean
    
    print_success "Packages removed successfully"
}

# Function to remove dual HDMI configuration
remove_dual_hdmi_config() {
    print_step "Removing dual HDMI configuration..."
    
    # Check both possible config locations
    config_files=()
    if [[ -f /boot/config.txt ]]; then
        config_files+=("/boot/config.txt")
    fi
    if [[ -f /boot/firmware/config.txt ]]; then
        config_files+=("/boot/firmware/config.txt")
    fi
    
    if [[ ${#config_files[@]} -eq 0 ]]; then
        print_warning "No boot config files found"
        return 0
    fi
    
    for config_file in "${config_files[@]}"; do
        if grep -q "dtoverlay=vc4-kms-v3d" "$config_file" 2>/dev/null; then
            print_info "Found dual HDMI config in $config_file"
            
            if [[ $FORCE_REMOVE != true ]]; then
                print_warning "Remove dual HDMI configuration from $config_file? (y/N)"
                read -r response
                if [[ ! "$response" =~ ^[Yy]$ ]]; then
                    continue
                fi
            fi
            
            # Remove multi-screen client configuration
            print_step "Removing configuration from $config_file..."
            
            # Create a temporary file without the multi-screen config
            sudo grep -v "# Multi-Screen Client Configuration" "$config_file" > /tmp/config_clean1
            sudo grep -v "# Added by install script" /tmp/config_clean1 > /tmp/config_clean2
            sudo grep -v "dtoverlay=vc4-kms-v3d" /tmp/config_clean2 > /tmp/config_clean3
            sudo grep -v "max_framebuffers=2" /tmp/config_clean3 > /tmp/config_clean4
            sudo grep -v "disable_fw_kms_setup=1" /tmp/config_clean4 > /tmp/config_clean5
            sudo grep -v "disable_overscan=1" /tmp/config_clean5 > /tmp/config_final
            
            # Replace original with cleaned version
            sudo cp /tmp/config_final "$config_file"
            sudo rm -f /tmp/config_clean* /tmp/config_final
            
            print_success "Configuration removed from $config_file"
        else
            print_info "No dual HDMI config found in $config_file"
        fi
    done
}

# Function to reset display system (optional)
reset_display_system() {
    print_step "Checking display system configuration..."
    
    current_session="$XDG_SESSION_TYPE"
    print_info "Current session type: $current_session"
    
    if [[ "$current_session" == "x11" ]]; then
        if [[ $FORCE_REMOVE != true ]]; then
            print_info "Currently using X11. Reset to default (Wayland)? (y/N)"
            read -r response
            if [[ ! "$response" =~ ^[Yy]$ ]]; then
                print_info "Keeping X11 configuration"
                return 0
            fi
        fi
        
        print_step "Resetting to default display system..."
        
        # Reset GDM configuration if it exists
        if [[ -f /etc/gdm3/custom.conf ]]; then
            if grep -q "WaylandEnable=false" /etc/gdm3/custom.conf; then
                print_info "Removing X11 configuration from GDM..."
                sudo cp /etc/gdm3/custom.conf /etc/gdm3/custom.conf.backup.cleanup.$(date +%Y%m%d_%H%M%S)
                sudo sed -i '/WaylandEnable=false/d' /etc/gdm3/custom.conf
                print_success "GDM configuration reset"
            fi
        fi
        
        print_warning "Reboot required for display system changes to take effect"
    else
        print_info "Display system appears to be at default settings"
    fi
}

# Function to show current system state
show_system_state() {
    print_header "CURRENT SYSTEM STATE"
    
    echo
    print_info "Display System:"
    echo "  XDG_SESSION_TYPE: $XDG_SESSION_TYPE"
    echo "  DISPLAY: $DISPLAY"
    echo "  WAYLAND_DISPLAY: $WAYLAND_DISPLAY"
    
    echo
    print_info "Package Status:"
    packages_to_check=("ffmpeg" "wmctrl" "xdotool" "python3-tk" "x11-apps")
    for package in "${packages_to_check[@]}"; do
        if dpkg -l | grep -q "^ii  $package "; then
            echo "  ✓ $package - INSTALLED"
        else
            echo "  ✗ $package - NOT INSTALLED"
        fi
    done
    
    echo
    print_info "Dual HDMI Configuration:"
    if grep -q "dtoverlay=vc4-kms-v3d" /boot/config.txt 2>/dev/null || grep -q "dtoverlay=vc4-kms-v3d" /boot/firmware/config.txt 2>/dev/null; then
        echo "  ✓ Dual HDMI enabled"
    else
        echo "  ✗ Dual HDMI not configured"
    fi
    
    echo
    print_info "Monitor Detection:"
    if command -v xrandr &> /dev/null; then
        monitor_count=$(xrandr --listmonitors 2>/dev/null | grep -c "^[[:space:]]*[0-9]:" || echo "0")
        echo "  Detected monitors: $monitor_count"
    else
        echo "  xrandr not available"
    fi
}

# Function to show usage
show_usage() {
    cat << EOF
Package Cleanup Script for Testing Multi-Screen Client Setup

Usage: $0 [OPTIONS]

OPTIONS:
    -f, --force         Force removal without prompts
    --no-backup         Skip backing up configuration files
    --display-reset     Also reset display system to defaults
    --show-state        Show current system state and exit
    -h, --help          Show this help message

EXAMPLES:
    $0                      # Interactive cleanup
    $0 --show-state         # Show current state
    $0 -f                   # Force cleanup without prompts
    $0 -f --display-reset   # Full cleanup including display system

WHAT THIS SCRIPT REMOVES:
    • ffmpeg, wmctrl, xdotool, python3-tk, x11-apps
    • python3-requests, curl, git
    • Dual HDMI configuration from boot config
    • Optionally: X11 display system configuration

SAFETY FEATURES:
    • Backs up configuration files before changes
    • Interactive prompts (unless --force used)
    • Shows what will be removed before doing it
    • Can show current state without making changes

This script prepares your system for testing the setup script from a clean state.

EOF
}

# Main execution function
main() {
    local show_state_only=false
    local reset_display=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -f|--force)
                FORCE_REMOVE=true
                shift
                ;;
            --no-backup)
                BACKUP_CONFIG=false
                shift
                ;;
            --display-reset)
                reset_display=true
                shift
                ;;
            --show-state)
                show_state_only=true
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
    
    print_header "MULTI-SCREEN CLIENT CLEANUP SCRIPT"
    
    # Show current state if requested
    if [[ $show_state_only == true ]]; then
        show_system_state
        exit 0
    fi
    
    echo
    print_warning "This script will remove packages and configuration for testing purposes"
    print_info "Configuration files will be backed up before removal"
    echo
    
    if [[ $FORCE_REMOVE != true ]]; then
        print_warning "Continue with cleanup? (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            print_info "Cleanup cancelled"
            exit 0
        fi
    fi
    
    # Run cleanup steps
    check_root
    backup_boot_config
    remove_packages
    remove_dual_hdmi_config
    
    if [[ $reset_display == true ]]; then
        reset_display_system
    fi
    
    echo
    print_header "CLEANUP COMPLETE!"
    
    echo
    print_success "System has been cleaned up for testing"
    print_info "You can now run the setup script to test from a clean state"
    echo
    print_info "To test your setup script:"
    echo "  ./install_dependencies.sh"
    echo
    print_info "To see current system state:"
    echo "  $0 --show-state"
    
    if grep -q "dtoverlay=vc4-kms-v3d" /boot/config.txt 2>/dev/null || grep -q "dtoverlay=vc4-kms-v3d" /boot/firmware/config.txt 2>/dev/null; then
        echo
        print_warning "Note: Some configuration may still be present"
        print_info "Check with: $0 --show-state"
    fi
    
    if [[ $reset_display == true ]]; then
        echo
        print_warning "REBOOT RECOMMENDED for all changes to take effect"
    fi
    
    echo
    print_success "Ready for setup script testing! 🧪"
}

# Run main function with all arguments
main "$@"
