#!/bin/bash
# Wayland Setup Script for Multi-Screen Client
# This script helps configure Wayland environment for multi-screen video streaming

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

# Function to check Wayland session
check_wayland_session() {
    print_status "Checking Wayland session..."
    
    wayland_display = os.environ.get('WAYLAND_DISPLAY')
    xdg_session = os.environ.get('XDG_SESSION_TYPE')
    
    if [[ -n "$WAYLAND_DISPLAY" ]]; then
        print_success "WAYLAND_DISPLAY set to: $WAYLAND_DISPLAY"
    else
        print_warning "WAYLAND_DISPLAY not set"
    fi
    
    if [[ "$XDG_SESSION_TYPE" == "wayland" ]]; then
        print_success "XDG_SESSION_TYPE is: $XDG_SESSION_TYPE"
    else
        print_warning "XDG_SESSION_TYPE is: $XDG_SESSION_TYPE (expected: wayland)"
    fi
    
    # Check for Wayland compositor
    if pgrep -f weston > /dev/null; then
        print_success "Weston compositor running (PID: $(pgrep -f weston))"
    elif pgrep -f sway > /dev/null; then
        print_success "Sway compositor running (PID: $(pgrep -f sway))"
    else
        print_warning "No Wayland compositor detected"
        return 1
    fi
    
    return 0
}

# Function to check dependencies
check_dependencies() {
    print_status "Checking dependencies..."
    
    local missing_deps=()
    
    # Check for required packages
    for pkg in ffmpeg; do
        if ! command -v "$pkg" &> /dev/null; then
            missing_deps+=("$pkg")
        fi
    done
    
    # Check for Wayland-specific tools
    wayland_tools=()
    if command -v wlr-randr &> /dev/null; then
        wayland_tools+=("wlr-randr")
    fi
    if command -v swaymsg &> /dev/null; then
        wayland_tools+=("swaymsg")
    fi
    if command -v weston-info &> /dev/null; then
        wayland_tools+=("weston-info")
    fi
    
    if [[ ${#wayland_tools[@]} -eq 0 ]]; then
        missing_deps+=("wlr-randr or swaymsg or weston-info")
    fi
    
    # Check for window management tools
    window_tools=()
    if command -v ydotool &> /dev/null; then
        window_tools+=("ydotool")
    fi
    if command -v wtype &> /dev/null; then
        window_tools+=("wtype")
    fi
    
    if [[ ${#window_tools[@]} -eq 0 ]]; then
        missing_deps+=("ydotool or wtype")
    fi
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        print_warning "Missing dependencies: ${missing_deps[*]}"
        print_status "Installing missing packages..."
        sudo apt update
        sudo apt install -y "${missing_deps[@]}"
    else
        print_success "All dependencies are installed"
    fi
    
    # Show available tools
    print_status "Available Wayland tools:"
    for tool in "${wayland_tools[@]}"; do
        print_success "  ✓ $tool"
    done
    
    print_status "Available window management tools:"
    for tool in "${window_tools[@]}"; do
        print_success "  ✓ $tool"
    done
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
    
    # Check current Wayland output configuration
    print_status "Current Wayland outputs:"
    
    # Try wlr-randr first
    if command -v wlr-randr &> /dev/null; then
        if wlr-randr 2>/dev/null; then
            print_success "wlr-randr output retrieved"
        else
            print_warning "wlr-randr failed"
        fi
    fi
    
    # Try swaymsg as alternative
    if command -v swaymsg &> /dev/null; then
        if swaymsg -t get_outputs 2>/dev/null | jq -r '.[] | "\(.name): \(.model) (\(.make))"' 2>/dev/null; then
            print_success "swaymsg output retrieved"
        else
            print_warning "swaymsg failed"
        fi
    fi
    
    # Try weston-info as last resort
    if command -v weston-info &> /dev/null; then
        if weston-info 2>/dev/null | grep -i hdmi; then
            print_success "weston-info found HDMI outputs"
        else
            print_warning "weston-info no HDMI outputs found"
        fi
    fi
}

# Function to test Wayland outputs
test_wayland_outputs() {
    print_status "Testing Wayland outputs..."
    
    # Get list of outputs
    outputs=()
    
    if command -v wlr-randr &> /dev/null; then
        while IFS= read -r line; do
            if [[ -n "$line" && ! "$line" =~ ^[[:space:]] ]]; then
                outputs+=("$line")
            fi
        done < <(wlr-randr 2>/dev/null | grep -v '^[[:space:]]')
    elif command -v swaymsg &> /dev/null; then
        while IFS= read -r line; do
            if [[ -n "$line" ]]; then
                outputs+=("$line")
            fi
        done < <(swaymsg -t get_outputs 2>/dev/null | jq -r '.[] | .name' 2>/dev/null)
    fi
    
    if [[ ${#outputs[@]} -eq 0 ]]; then
        print_warning "No Wayland outputs detected"
        return 1
    fi
    
    print_success "Detected ${#outputs[@]} outputs: ${outputs[*]}"
    
    # Test each output
    for output in "${outputs[@]}"; do
        print_status "Testing output: $output"
        
        # Try to create a test window (this may not work on all Wayland setups)
        if command -v weston-terminal &> /dev/null; then
            if timeout 3s weston-terminal --title "Test-$output" &> /dev/null; then
                print_success "  ✓ weston-terminal works on $output"
                pkill -f "weston-terminal.*Test-$output" 2>/dev/null || true
            else
                print_warning "  ⚠ weston-terminal test failed on $output"
            fi
        else
            print_warning "  ⚠ weston-terminal not available for testing"
        fi
    done
    
    return 0
}

# Function to create client launch scripts
create_launch_scripts() {
    print_status "Creating client launch scripts..."
    
    local server_url="$1"
    
    # Create HDMI1 client script
    cat > launch_hdmi1_wayland.sh << EOF
#!/bin/bash
# Launch Wayland client for HDMI1 (Primary)

export WAYLAND_DISPLAY=wayland-0
export XDG_SESSION_TYPE=wayland
export HDMI_OUTPUT=HDMI1

echo "Starting HDMI1 Wayland client..."
python3 client_wayland.py \\
    --server "$server_url" \\
    --hostname "rpi-client-1" \\
    --display-name "HDMI1" \\
    --target-screen HDMI1

EOF

    # Create HDMI2 client script
    cat > launch_hdmi2_wayland.sh << EOF
#!/bin/bash
# Launch Wayland client for HDMI2 (Secondary)

export WAYLAND_DISPLAY=wayland-0
export XDG_SESSION_TYPE=wayland
export HDMI_OUTPUT=HDMI2

echo "Starting HDMI2 Wayland client..."
python3 client_wayland.py \\
    --server "$server_url" \\
    --hostname "rpi-client-2" \\
    --display-name "HDMI2" \\
    --target-screen HDMI2

EOF

    # Make scripts executable
    chmod +x launch_hdmi1_wayland.sh launch_hdmi2_wayland.sh
    
    print_success "Launch scripts created:"
    print_status "  - launch_hdmi1_wayland.sh (for HDMI1)"
    print_status "  - launch_hdmi2_wayland.sh (for HDMI2)"
}

# Function to create systemd services
create_systemd_services() {
    print_status "Creating systemd services..."
    
    local server_url="$1"
    local user_name=$(whoami)
    local script_dir=$(pwd)
    
    # Create HDMI1 service
    sudo tee /etc/systemd/system/multiscreen-wayland-hdmi1.service > /dev/null << EOF
[Unit]
Description=Multi-Screen Client Wayland HDMI1
After=network.target

[Service]
Type=simple
User=$user_name
WorkingDirectory=$script_dir
Environment=WAYLAND_DISPLAY=wayland-0
Environment=XDG_SESSION_TYPE=wayland
Environment=HDMI_OUTPUT=HDMI1
ExecStart=$script_dir/launch_hdmi1_wayland.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    # Create HDMI2 service
    sudo tee /etc/systemd/system/multiscreen-wayland-hdmi2.service > /dev/null << EOF
[Unit]
Description=Multi-Screen Client Wayland HDMI2
After=network.target

[Service]
Type=simple
User=$user_name
WorkingDirectory=$script_dir
Environment=WAYLAND_DISPLAY=wayland-0
Environment=XDG_SESSION_TYPE=wayland
Environment=HDMI_OUTPUT=HDMI2
ExecStart=$script_dir/launch_hdmi2_wayland.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd and enable services
    sudo systemctl daemon-reload
    
    print_success "Systemd services created:"
    print_status "  - multiscreen-wayland-hdmi1.service"
    print_status "  - multiscreen-wayland-hdmi2.service"
    
    print_status "To enable services (start on boot):"
    print_status "  sudo systemctl enable multiscreen-wayland-hdmi1.service"
    print_status "  sudo systemctl enable multiscreen-wayland-hdmi2.service"
    
    print_status "To start services manually:"
    print_status "  sudo systemctl start multiscreen-wayland-hdmi1.service"
    print_status "  sudo systemctl start multiscreen-wayland-hdmi2.service"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --server URL     Server URL for client configuration"
    echo "  --check-only     Only check system configuration (don't create scripts)"
    echo "  --help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --server http://192.168.1.100:5000"
    echo "  $0 --check-only"
    echo ""
}

# Main function
main() {
    local server_url=""
    local check_only=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --server)
                server_url="$2"
                shift 2
                ;;
            --check-only)
                check_only=true
                shift
                ;;
            --help)
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
    
    print_status "Wayland Multi-Screen Client Setup"
    print_status "================================="
    echo ""
    
    # Check prerequisites
    check_root
    check_raspberry_pi
    
    # Check Wayland session
    if ! check_wayland_session; then
        print_error "Not running in Wayland session"
        print_status "This script is designed for Wayland environments"
        print_status "If you're using X11, use the original setup script instead"
        exit 1
    fi
    
    # Check and install dependencies
    check_dependencies
    
    # Check HDMI configuration
    check_hdmi_config
    
    # Test Wayland outputs
    if ! test_wayland_outputs; then
        print_warning "Wayland output testing failed"
        print_status "You may need to check your Wayland configuration"
    fi
    
    if [[ "$check_only" == true ]]; then
        print_success "System check completed"
        print_status "Run without --check-only to create launch scripts and services"
        exit 0
    fi
    
    # Get server URL if not provided
    if [[ -z "$server_url" ]]; then
        print_status "Enter your server URL (e.g., http://192.168.1.100:5000):"
        read -r server_url
        
        if [[ -z "$server_url" ]]; then
            print_error "Server URL is required"
            exit 1
        fi
        
        if [[ ! "$server_url" =~ ^https?:// ]]; then
            print_error "Server URL must start with http:// or https://"
            exit 1
        fi
    fi
    
    # Create launch scripts
    create_launch_scripts "$server_url"
    
    # Create systemd services
    create_systemd_services "$server_url"
    
    echo ""
    print_success "Wayland setup completed successfully!"
    echo ""
    print_status "Next steps:"
    print_status "1. Test the setup: ./launch_hdmi1_wayland.sh"
    print_status "2. In another terminal: ./launch_hdmi2_wayland.sh"
    print_status "3. Use the web interface to assign clients to groups"
    print_status "4. Start streaming for synchronized video wall display"
    echo ""
    print_status "For troubleshooting, run: $0 --check-only"
}

# Run main function
main "$@"
