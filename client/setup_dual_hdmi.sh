#!/bin/bash
# Dual HDMI Setup Script for Raspberry Pi 5
# This script helps configure dual HDMI outputs for multi-screen video streaming

set -e

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

# Function to check if running on Raspberry Pi
check_raspberry_pi() {
    if [[ -f /proc/device-tree/model ]]; then
        if grep -q "Raspberry Pi" /proc/device-tree/model; then
            print_success "Raspberry Pi detected"
            return 0
        fi
    fi
    print_warning "This script is designed for Raspberry Pi. Continue anyway? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
    return 1
}

# Function to check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_error "This script should not be run as root"
        print_status "Please run as a regular user with sudo privileges"
        exit 1
    fi
}

# Function to check dependencies
check_dependencies() {
    print_status "Checking dependencies..."
    
    local missing_deps=()
    
    # Check for required packages
    for pkg in xrandr ffmpeg wmctrl xdotool; do
        if ! command -v "$pkg" &> /dev/null; then
            missing_deps+=("$pkg")
        fi
    done
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        print_warning "Missing dependencies: ${missing_deps[*]}"
        print_status "Installing missing packages..."
        sudo apt update
        sudo apt install -y "${missing_deps[@]}"
    else
        print_success "All dependencies are installed"
    fi
}

# Function to check HDMI configuration
check_hdmi_config() {
    print_status "Checking HDMI configuration..."
    
    # Check if dual HDMI is enabled
    if [[ -f /boot/config.txt ]]; then
        if grep -q "dtoverlay=vc4-kms-v3d" /boot/config.txt; then
            print_success "Dual HDMI overlay is enabled"
        else
            print_warning "Dual HDMI overlay not found in /boot/config.txt"
            print_status "You may need to add: dtoverlay=vc4-kms-v3d"
        fi
    fi
    
    # Check current display configuration
    print_status "Current display configuration:"
    xrandr --listmonitors || print_warning "Could not list monitors"
    
    print_status "Current outputs:"
    xrandr --listoutputs || print_warning "Could not list outputs"
}

# Function to test displays
test_displays() {
    print_status "Testing displays..."
    
    # Test primary display (HDMI1)
    print_status "Testing HDMI1 (Display :0.0)..."
    if timeout 5s DISPLAY=:0.0 xeyes &> /dev/null; then
        print_success "HDMI1 (Display :0.0) is working"
        pkill xeyes 2>/dev/null || true
    else
        print_warning "HDMI1 (Display :0.0) may have issues"
    fi
    
    # Test secondary display (HDMI2)
    print_status "Testing HDMI2 (Display :1.0)..."
    if timeout 5s DISPLAY=:1.0 xeyes &> /dev/null; then
        print_success "HDMI2 (Display :1.0) is working"
        pkill xeyes 2>/dev/null || true
    else
        print_warning "HDMI2 (Display :1.0) may have issues"
    fi
}

# Function to create client launch scripts
create_launch_scripts() {
    print_status "Creating client launch scripts..."
    
    local server_url="$1"
    
    # Create HDMI1 client script
    cat > launch_hdmi1.sh << EOF
#!/bin/bash
# Launch client for HDMI1 (Display :0.0)

export DISPLAY=:0.0
export HDMI_OUTPUT=HDMI1

echo "Starting HDMI1 client..."
python3 client.py \\
    --server "$server_url" \\
    --hostname "rpi-client-1" \\
    --display-name "HDMI1" \\
    --target-screen HDMI1

EOF

    # Create HDMI2 client script
    cat > launch_hdmi2.sh << EOF
#!/bin/bash
# Launch client for HDMI2 (Display :1.0)

export DISPLAY=:1.0
export HDMI_OUTPUT=HDMI2

echo "Starting HDMI2 client..."
python3 client.py \\
    --server "$server_url" \\
    --hostname "rpi-client-2" \\
    --display-name "HDMI2" \\
    --target-screen HDMI2

EOF

    # Make scripts executable
    chmod +x launch_hdmi1.sh launch_hdmi2.sh
    
    print_success "Launch scripts created:"
    print_status "  - launch_hdmi1.sh (for HDMI1)"
    print_status "  - launch_hdmi2.sh (for HDMI2)"
}

# Function to create systemd services
create_systemd_services() {
    print_status "Creating systemd services..."
    
    local server_url="$1"
    local user_name=$(whoami)
    local script_dir=$(pwd)
    
    # Create HDMI1 service
    sudo tee /etc/systemd/system/multiscreen-hdmi1.service > /dev/null << EOF
[Unit]
Description=Multi-Screen Client HDMI1
After=network.target

[Service]
Type=simple
User=$user_name
WorkingDirectory=$script_dir
Environment=DISPLAY=:0.0
Environment=HDMI_OUTPUT=HDMI1
ExecStart=$script_dir/launch_hdmi1.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    # Create HDMI2 service
    sudo tee /etc/systemd/system/multiscreen-hdmi2.service > /dev/null << EOF
[Unit]
Description=Multi-Screen Client HDMI2
After=network.target

[Service]
Type=simple
User=$user_name
WorkingDirectory=$script_dir
Environment=DISPLAY=:1.0
Environment=HDMI_OUTPUT=HDMI2
ExecStart=$script_dir/launch_hdmi2.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd and enable services
    sudo systemctl daemon-reload
    
    print_success "Systemd services created:"
    print_status "  - multiscreen-hdmi1.service"
    print_status "  - multiscreen-hdmi2.service"
    
    print_status "To enable services:"
    print_status "  sudo systemctl enable multiscreen-hdmi1.service"
    print_status "  sudo systemctl enable multiscreen-hdmi2.service"
    
    print_status "To start services:"
    print_status "  sudo systemctl start multiscreen-hdmi1.service"
    print_status "  sudo systemctl start multiscreen-hdmi2.service"
}

# Function to show usage
show_usage() {
    cat << EOF
Dual HDMI Setup Script for Raspberry Pi 5

Usage: $0 [OPTIONS]

OPTIONS:
    -s, --server URL     Server URL (required)
    -c, --check-only     Only check configuration, don't create scripts
    -h, --help          Show this help message

EXAMPLES:
    # Full setup with server URL
    $0 --server http://192.168.1.100:5000
    
    # Check configuration only
    $0 --check-only
    
    # Help
    $0 --help

This script will:
1. Check if your system supports dual HDMI
2. Verify display configuration
3. Test both displays
4. Create launch scripts for both HDMI outputs
5. Create systemd services (optional)

EOF
}

# Main function
main() {
    local server_url=""
    local check_only=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -s|--server)
                server_url="$2"
                shift 2
                ;;
            -c|--check-only)
                check_only=true
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
    
    # Check if server URL is provided (unless check-only mode)
    if [[ -z "$server_url" && "$check_only" == false ]]; then
        print_error "Server URL is required"
        print_status "Use --server URL or --check-only"
        show_usage
        exit 1
    fi
    
    print_status "Starting Dual HDMI Setup..."
    echo
    
    # Run checks
    check_raspberry_pi
    check_root
    check_dependencies
    check_hdmi_config
    test_displays
    
    if [[ "$check_only" == true ]]; then
        print_success "Configuration check complete"
        exit 0
    fi
    
    echo
    print_status "Creating client launch scripts..."
    create_launch_scripts "$server_url"
    
    echo
    print_warning "Do you want to create systemd services? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        create_systemd_services "$server_url"
    fi
    
    echo
    print_success "Dual HDMI setup complete!"
    print_status "To start clients manually:"
    print_status "  Terminal 1: ./launch_hdmi1.sh"
    print_status "  Terminal 2: ./launch_hdmi2.sh"
    
    if [[ "$response" =~ ^[Yy]$ ]]; then
        print_status "Or use systemd services:"
        print_status "  sudo systemctl start multiscreen-hdmi1.service"
        print_status "  sudo systemctl start multiscreen-hdmi2.service"
    fi
}

# Run main function with all arguments
main "$@"

