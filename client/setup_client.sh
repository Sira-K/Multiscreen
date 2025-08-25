#!/bin/bash
# Multi-Screen Video Streaming Client Setup Script
# Installs all required dependencies for the client

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

# Function to detect OS
detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
    elif type lsb_release >/dev/null 2>&1; then
        OS=$(lsb_release -si)
        VER=$(lsb_release -sr)
    elif [[ -f /etc/debian_version ]]; then
        OS=Debian
        VER=$(cat /etc/debian_version)
    else
        OS=$(uname -s)
        VER=$(uname -r)
    fi
    
    echo "$OS"
}

# Function to install Python packages
install_python_packages() {
    print_status "Installing Python packages..."
    
    # Check if pip is available
    if ! command_exists pip3; then
        print_error "pip3 not found. Installing pip..."
        if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]] || [[ "$OS" == *"Raspbian"* ]]; then
            sudo apt-get update
            sudo apt-get install -y python3-pip
        elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]]; then
            sudo yum install -y python3-pip
        else
            print_error "Unsupported OS for pip installation"
            exit 1
        fi
    fi
    
    # Install required Python packages
    print_status "Installing required Python packages..."
    pip3 install --user requests
    
    print_success "Python packages installed successfully"
}

# Function to install system dependencies
install_system_dependencies() {
    print_status "Installing system dependencies..."
    
    if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]] || [[ "$OS" == *"Raspbian"* ]]; then
        # Update package list
        sudo apt-get update
        
        # Install FFmpeg (includes ffplay and ffprobe)
        if ! command_exists ffplay; then
            print_status "Installing FFmpeg..."
            sudo apt-get install -y ffmpeg
        else
            print_status "FFmpeg already installed"
        fi
        
        # Install Python3 if not present
        if ! command_exists python3; then
            print_status "Installing Python3..."
            sudo apt-get install -y python3
        fi
        
        # Install additional dependencies
        sudo apt-get install -y python3-dev python3-setuptools
        
    elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]]; then
        # Enable EPEL repository
        sudo yum install -y epel-release
        
        # Install FFmpeg
        if ! command_exists ffplay; then
            print_status "Installing FFmpeg..."
            sudo yum install -y ffmpeg
        fi
        
        # Install Python3
        if ! command_exists python3; then
            print_status "Installing Python3..."
            sudo yum install -y python3 python3-pip
        fi
        
    else
        print_warning "Unsupported OS: $OS"
        print_warning "Please install FFmpeg and Python3 manually"
    fi
    
    print_success "System dependencies installed successfully"
}

# Function to verify installations
verify_installations() {
    print_status "Verifying installations..."
    
    local all_good=true
    
    # Check Python3
    if command_exists python3; then
        local python_version=$(python3 --version 2>&1)
        print_success "Python3: $python_version"
    else
        print_error "Python3 not found"
        all_good=false
    fi
    
    # Check pip3
    if command_exists pip3; then
        local pip_version=$(pip3 --version 2>&1)
        print_success "pip3: $pip_version"
    else
        print_error "pip3 not found"
        all_good=false
    fi
    
    # Check FFmpeg
    if command_exists ffmpeg; then
        local ffmpeg_version=$(ffmpeg -version | head -n1)
        print_success "FFmpeg: $ffmpeg_version"
    else
        print_error "FFmpeg not found"
        all_good=false
    fi
    
    # Check ffplay
    if command_exists ffplay; then
        print_success "ffplay: Available"
    else
        print_error "ffplay not found"
        all_good=false
    fi
    
    # Check ffprobe
    if command_exists ffprobe; then
        print_success "ffprobe: Available"
    else
        print_error "ffprobe not found"
        all_good=false
    fi
    
    # Check Python packages
    if python3 -c "import requests" 2>/dev/null; then
        print_success "requests package: Installed"
    else
        print_error "requests package: Not installed"
        all_good=false
    fi
    
    if [[ "$all_good" == true ]]; then
        print_success "All dependencies verified successfully!"
        return 0
    else
        print_error "Some dependencies are missing. Please check the errors above."
        return 1
    fi
}

# Function to test the client
test_client() {
    print_status "Testing client installation..."
    
    if python3 -c "import sys; sys.path.insert(0, '.'); import client; print('Client import successful')" 2>/dev/null; then
        print_success "Client can be imported successfully"
    else
        print_warning "Client import test failed (this is normal if server is not running)"
    fi
    
    print_status "Client setup complete!"
    print_status "You can now run the client with:"
    echo "  python3 client.py --server <server-url> --hostname <client-name> --display-name <display-name>"
}

# Main execution
main() {
    echo "=========================================="
    echo "Multi-Screen Video Streaming Client Setup"
    echo "=========================================="
    echo
    
    # Check if running as root
    if [[ $EUID -eq 0 ]]; then
        print_error "This script should not be run as root"
        print_error "Please run as a regular user with sudo privileges"
        exit 1
    fi
    
    # Detect OS
    OS=$(detect_os)
    print_status "Detected OS: $OS"
    echo
    
    # Install system dependencies
    install_system_dependencies
    echo
    
    # Install Python packages
    install_python_packages
    echo
    
    # Verify installations
    if verify_installations; then
        echo
        test_client
    else
        echo
        print_error "Setup incomplete. Please resolve the missing dependencies."
        exit 1
    fi
}

# Run main function
main "$@"
