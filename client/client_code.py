#!/usr/bin/env python3
"""
Auto-Fullscreen SRT Video Client for Raspberry Pi - Enhanced Version
==================================================================

Features:
- Auto-detects screen resolution (including headless Pi support)
- True fullscreen mode (no windowing)
- Proper aspect ratio with black bars
- SRT streaming with low latency
- Automatic server communication with validation
- Error handling and recovery
- Log rotation and better file handling
- Enhanced Raspberry Pi compatibility

Usage:
    python3 client_code.py
    python3 client_code.py --server http://192.168.1.100:5000
    python3 client_code.py --interval 5 --debug
    python3 client_code.py --diagnostics
"""

import requests
import json
import time
import socket
import uuid
import subprocess
import os
import signal
import sys
import argparse
import platform
import atexit
import threading
import tempfile
import re
from typing import Tuple, Optional, Dict, Any

# Configuration Constants
DEFAULT_SERVER_URL = "http://128.205.39.64:5000"
DEFAULT_SRT_IP = "128.205.39.64"
DEFAULT_POLL_INTERVAL = 3
DEBUG = True

# Global Variables
player_process = None
shutdown_requested = False
current_stream = None
last_server_response = None
screen_resolution = None

def get_safe_file_path(filename: str) -> str:
    """Get a safe file path with fallbacks for different permission scenarios"""
    # Try user home directory first
    home_path = os.path.expanduser(f"~/{filename}")
    try:
        # Test if we can write to home directory
        test_file = home_path + ".test"
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        return home_path
    except (OSError, PermissionError):
        pass
    
    # Try current directory
    current_path = f"./{filename}"
    try:
        test_file = current_path + ".test"
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        return current_path
    except (OSError, PermissionError):
        pass
    
    # Fall back to temp directory
    temp_path = os.path.join(tempfile.gettempdir(), filename)
    return temp_path

# File paths with safe handling
ID_FILE = get_safe_file_path(".srt_client_id")
LOG_FILE = get_safe_file_path(".srt_client.log")

def rotate_log_if_needed(max_size_mb: int = 10) -> None:
    """Rotate log file if it gets too large"""
    try:
        if os.path.exists(LOG_FILE):
            file_size = os.path.getsize(LOG_FILE)
            max_size_bytes = max_size_mb * 1024 * 1024
            
            if file_size > max_size_bytes:
                # Rename current log to .old
                old_log = LOG_FILE + '.old'
                if os.path.exists(old_log):
                    os.remove(old_log)
                os.rename(LOG_FILE, old_log)
                print(f"Log file rotated at {file_size} bytes")
    except Exception as e:
        # Don't let log rotation break the application
        pass

def log(message: str, level: str = "INFO") -> None:
    """Enhanced logging with timestamps, levels, and rotation"""
    timestamp = time.strftime('%H:%M:%S')
    log_entry = f"[{timestamp}] {level}: {message}"
    
    if DEBUG:
        print(log_entry)
    
    # Rotate log if needed (check every 100 log entries)
    if hasattr(log, 'call_count'):
        log.call_count += 1
    else:
        log.call_count = 1
    
    if log.call_count % 100 == 0:
        rotate_log_if_needed()
    
    # Write to log file
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(f"{log_entry}\n")
    except:
        pass  # Fail silently if can't write to log

def log_info(message: str) -> None:
    """Log info message"""
    log(message, "INFO")

def log_error(message: str) -> None:
    """Log error message"""
    log(message, "ERROR")

def log_warning(message: str) -> None:
    """Log warning message"""
    log(message, "WARN")

def log_success(message: str) -> None:
    """Log success message"""
    log(message, "SUCCESS")

def validate_stream_id(stream_id: str) -> bool:
    """Validate stream ID format"""
    if not isinstance(stream_id, str):
        return False
    
    # Allow alphanumeric characters, forward slash, and common separators
    if not re.match(r'^[a-zA-Z0-9/_\-]+$', stream_id):
        return False
    
    # Reasonable length limits
    if len(stream_id) < 1 or len(stream_id) > 100:
        return False
    
    return True

def validate_ip_address(ip: str) -> bool:
    """Basic IP address validation"""
    if not isinstance(ip, str):
        return False
    
    try:
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        
        for part in parts:
            num = int(part)
            if num < 0 or num > 255:
                return False
        
        return True
    except (ValueError, AttributeError):
        return False

def get_client_id() -> str:
    """Get or create a unique client ID with better error handling"""
    try:
        if os.path.exists(ID_FILE):
            with open(ID_FILE, "r") as f:
                client_id = f.read().strip()
                if client_id:  # Make sure it's not empty
                    return client_id
    except (OSError, PermissionError) as e:
        log_warning(f"Could not read client ID file: {e}")
    
    # Generate new client ID
    hostname = platform.node()
    safe_hostname = ''.join(c for c in hostname if c.isalnum() or c in '-_').lower()
    client_id = f"srt-{safe_hostname}-{uuid.getnode()}-{uuid.uuid4().hex[:6]}"
    
    # Try to save it
    try:
        with open(ID_FILE, "w") as f:
            f.write(client_id)
        log_info(f"Created new client ID: {client_id}")
    except (OSError, PermissionError) as e:
        log_warning(f"Could not save client ID to file: {e}")
        # Continue with generated ID even if we can't save it
    
    return client_id

def get_local_ip() -> str:
    """Get the local IP address of this machine"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        log_warning(f"Could not determine local IP: {e}")
        try:
            return socket.gethostbyname(socket.gethostname())
        except:
            return "unknown"

def get_client_info() -> Dict[str, Any]:
    """Get comprehensive client information"""
    return {
        "hostname": platform.node(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "ip_address": get_local_ip(),
        "mac_address": hex(uuid.getnode()),
        "client_type": "srt_stream",
        "capabilities": ["fullscreen", "auto_resolution"],
        "registration_time": time.time()
    }

def detect_via_xrandr() -> Optional[Tuple[int, int]]:
    """Detect resolution using xrandr"""
    try:
        result = subprocess.run(['xrandr'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if '*' in line and '+' in line:  # Current resolution
                    parts = line.split()
                    for part in parts:
                        if 'x' in part and '*' in part:
                            resolution = part.split('*')[0]
                            if 'x' in resolution:
                                width, height = map(int, resolution.split('x'))
                                return width, height
    except Exception:
        pass
    return None

def detect_via_xdpyinfo() -> Optional[Tuple[int, int]]:
    """Detect resolution using xdpyinfo"""
    try:
        result = subprocess.run(['xdpyinfo'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'dimensions:' in line:
                    parts = line.split()
                    for part in parts:
                        if 'x' in part and 'pixel' not in part:
                            width, height = map(int, part.split('x'))
                            return width, height
    except Exception:
        pass
    return None

def detect_via_config_txt() -> Optional[Tuple[int, int]]:
    """Detect resolution from Raspberry Pi config.txt"""
    try:
        config_paths = ['/boot/config.txt', '/boot/firmware/config.txt']
        
        for config_path in config_paths:
            if not os.path.exists(config_path):
                continue
                
            with open(config_path, 'r') as f:
                content = f.read()
                
            # Look for HDMI settings
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('#'):
                    continue
                    
                if line.startswith('hdmi_mode='):
                    mode = line.split('=')[1]
                    # Common HDMI modes for Pi
                    hdmi_modes = {
                        '4': (1280, 720),    # 720p
                        '16': (1920, 1080),  # 1080p
                        '82': (1920, 1080),  # 1080p 60Hz
                        '85': (1280, 720),   # 720p 60Hz
                    }
                    if mode in hdmi_modes:
                        return hdmi_modes[mode]
                        
                elif line.startswith('hdmi_cvt='):
                    # Custom resolution: hdmi_cvt=width height framerate aspect marginX marginY interlace
                    parts = line.split('=')[1].split()
                    if len(parts) >= 2:
                        try:
                            width = int(parts[0])
                            height = int(parts[1])
                            return width, height
                        except ValueError:
                            continue
                            
    except Exception as e:
        log_warning(f"Config.txt detection failed: {e}")
    
    return None

def detect_via_framebuffer() -> Optional[Tuple[int, int]]:
    """Detect resolution via framebuffer"""
    try:
        with open('/sys/class/graphics/fb0/virtual_size', 'r') as f:
            line = f.read().strip()
            if ',' in line:
                width, height = map(int, line.split(','))
                return width, height
    except:
        pass
    return None

def detect_via_fbset() -> Optional[Tuple[int, int]]:
    """Detect resolution using fbset"""
    try:
        result = subprocess.run(['fbset', '-s'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'geometry' in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        width, height = int(parts[1]), int(parts[2])
                        return width, height
    except:
        pass
    return None

def detect_screen_resolution() -> Tuple[int, int]:
    """Auto-detect screen resolution using multiple methods"""
    global screen_resolution
    
    if screen_resolution:
        return screen_resolution
    
    log_info("🔍 Auto-detecting screen resolution...")
    
    detection_methods = [
        ("xrandr", detect_via_xrandr),
        ("xdpyinfo", detect_via_xdpyinfo),
        ("config.txt", detect_via_config_txt),  # Pi-specific
        ("framebuffer", detect_via_framebuffer),
        ("fbset", detect_via_fbset)
    ]
    
    for method_name, method_func in detection_methods:
        try:
            result = method_func()
            if result:
                width, height = result
                log_success(f"✅ Screen resolution detected: {width}x{height} (via {method_name})")
                screen_resolution = (width, height)
                return screen_resolution
        except Exception as e:
            log_warning(f"Detection method '{method_name}' failed: {e}")
    
    # Fallback resolutions in order of preference
    fallback_resolutions = [
        (1920, 1080),  # 1080p (most common)
        (1280, 720),   # 720p  
        (2560, 1440),  # 1440p
        (3840, 2160),  # 4K
        (1024, 768),   # 4:3
    ]
    
    width, height = fallback_resolutions[0]
    log_warning(f"⚠️  Using fallback resolution: {width}x{height}")
    screen_resolution = (width, height)
    return screen_resolution

def test_video_capabilities() -> Dict[str, bool]:
    """Test available video players including custom player"""
    log_info("🧪 Testing video capabilities...")
    
    capabilities = {
        "custom_player": False,
        "ffplay": False,
        "ffplay_srt": False,
        "vlc": False
    }
    
    # Test custom player first
    custom_player_path = "./cmake-build-debug/player/player"
    try:
        if os.path.exists(custom_player_path):
            # Test if the player executable works
            result = subprocess.run([custom_player_path], 
                                  capture_output=True, 
                                  timeout=2,
                                  input="", 
                                  text=True)
            # Even if it exits with error (no URL provided), if it runs, it's available
            capabilities["custom_player"] = True
            log_info("   ✅ Custom SRT Player found")
        else:
            log_info("   ❌ Custom SRT Player not found - compile with 'cmake --build ./cmake-build-debug --target player'")
    except Exception as e:
        log_warning(f"Custom player test failed: {e}")
    
    # Test FFplay (as backup)
    try:
        result = subprocess.run(['which', 'ffplay'], capture_output=True, timeout=3)
        capabilities["ffplay"] = result.returncode == 0
        
        if capabilities["ffplay"]:
            # Test SRT support
            result = subprocess.run(['ffplay', '-protocols'], capture_output=True, text=True, timeout=3)
            capabilities["ffplay_srt"] = 'srt' in result.stdout if result.returncode == 0 else False
            
    except Exception as e:
        log_warning(f"FFplay test failed: {e}")
    
    # Test VLC (as backup)
    try:
        result = subprocess.run(['which', 'cvlc'], capture_output=True, timeout=3)
        capabilities["vlc"] = result.returncode == 0
    except Exception as e:
        log_warning(f"VLC test failed: {e}")
    
    # Log results
    for capability, available in capabilities.items():
        status = "✅" if available else "❌"
        log_info(f"   {status} {capability}")
    
    return capabilities

def register_with_server(server_url: str, client_id: str, client_info: Dict[str, Any]) -> bool:
    """Register this SRT client with the server"""
    try:
        data = {
            "client_id": client_id,
            "client_info": client_info
        }
        
        log_info(f"📡 Registering SRT client with server...")
        log_info(f"   Client ID: {client_id}")
        log_info(f"   Server: {server_url}")
        
        response = requests.post(
            f"{server_url}/register_client",
            json=data,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            log_success(f"✅ Registration successful!")
            
            if result.get("stream_id"):
                log_info(f"   Initial stream assignment: {result['stream_id']}")
            
            return True
        else:
            log_error(f"❌ Registration failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        log_error(f"❌ Registration error: {e}")
        return False

def get_stream_assignment(server_url: str, client_id: str) -> Optional[Dict[str, Any]]:
    """Get current stream assignment from server with validation"""
    global last_server_response
    
    try:
        response = requests.post(
            f"{server_url}/client_status",
            json={"client_id": client_id},
            timeout=5
        )
        
        if response.status_code == 200:
            last_server_response = time.time()
            status_data = response.json()
            
            stream_id = status_data.get("stream_id")
            srt_ip = status_data.get("srt_ip", DEFAULT_SRT_IP)
            
            # Validate stream_id if provided
            if stream_id and not validate_stream_id(stream_id):
                log_error(f"Invalid stream_id received from server: {stream_id}")
                return None
            
            # Validate srt_ip
            if not validate_ip_address(srt_ip):
                log_error(f"Invalid SRT IP received from server: {srt_ip}")
                return None
            
            # Fix localhost SRT IP issue
            if srt_ip == "127.0.0.1":
                srt_ip = server_url.replace("http://", "").replace(":5000", "")
                log_warning(f"⚠️  Fixed SRT IP from localhost to: {srt_ip}")
                
                # Re-validate the fixed IP
                if not validate_ip_address(srt_ip):
                    log_error(f"Fixed SRT IP is still invalid: {srt_ip}")
                    return None
            
            log_info(f"📡 Status: stream='{stream_id}', srt_ip={srt_ip}")
            
            return {
                "stream_id": stream_id,
                "srt_ip": srt_ip,
                "orientation": status_data.get("orientation", "horizontal"),
                "status": status_data.get("status", "active")
            }
        else:
            log_error(f"❌ Status check failed: {response.status_code}")
            return None
            
    except Exception as e:
        log_error(f"❌ Server communication error: {e}")
        return None

def test_srt_connectivity(srt_ip: str, port: int = 10080) -> bool:
    """Test if SRT server is reachable"""
    try:
        log_info(f"🔍 Testing SRT connectivity to {srt_ip}:{port}...")
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((srt_ip, port))
        sock.close()
        
        if result == 0:
            log_success(f"✅ SRT server is reachable")
            return True
        else:
            log_error(f"❌ Cannot reach SRT server at {srt_ip}:{port}")
            return False
            
    except Exception as e:
        log_error(f"❌ SRT connectivity test failed: {e}")
        return False

def stop_player() -> None:
    """Stop any running video player processes"""
    global player_process
    
    if player_process:
        try:
            log_info(f"🛑 Stopping player process (PID: {player_process.pid})")
            player_process.terminate()
            
            try:
                player_process.wait(timeout=5)
                log_success("✅ Player stopped gracefully")
            except subprocess.TimeoutExpired:
                log_warning("⚠️  Force killing player process")
                player_process.kill()
                
        except Exception as e:
            log_error(f"❌ Error stopping player: {e}")
        
        player_process = None
    
    # Kill any lingering video processes
    for process_name in ["ffplay", "vlc", "cvlc"]:
        try:
            subprocess.run(["pkill", "-f", process_name], 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL)
        except:
            pass

def create_srt_url(stream_id: str, srt_ip: str, port: int = 10080) -> str:
    """Create properly formatted SRT URL"""
    # Clean up stream ID
    clean_stream_id = stream_id.replace('live/', '') if stream_id.startswith('live/') else stream_id
    
    # Build SRT URL with optimized parameters
    srt_url = (
        f"srt://{srt_ip}:{port}"
        f"?streamid=#!::r=live/{clean_stream_id},m=request"
        f"&latency=1000000"  # 1 second latency
        f"&rcvbuf=12058624"  # 12MB receive buffer
        f"&lossmaxttl=40"    # Max packet loss tolerance
    )
    
    return srt_url

def wait_for_player_startup(process, timeout: int = 10) -> bool:
    """Wait for player to start properly with better timing"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if process.poll() is not None:
            # Process exited
            return False
        
        # Check if player is actually running
        try:
            time.sleep(0.5)
            
            # If we've waited at least 3 seconds and process is still running,
            # consider it successful (increased from 2 for slower Pi models)
            if time.time() - start_time >= 3:
                return True
                
        except Exception:
            continue
    
    return process.poll() is None

def start_fullscreen_player(stream_id: str, srt_ip: str) -> Optional[subprocess.Popen]:
    """Start custom SRT player in fullscreen mode"""
    global player_process
    
    stop_player()  # Stop any existing player
    
    if shutdown_requested:
        log_warning("⚠️  Shutdown requested, not starting player")
        return None
    
    try:
        # Create SRT URL
        srt_url = create_srt_url(stream_id, srt_ip)
        
        log_info(f"🎬 Starting CUSTOM SRT player...")
        log_info(f"   Stream ID: {stream_id}")
        log_info(f"   SRT Server: {srt_ip}:10080")
        log_info(f"   SRT URL: {srt_url}")
        
        # Test SRT connectivity first
        if not test_srt_connectivity(srt_ip):
            log_error("❌ SRT server not reachable, skipping player start")
            return None
        
        # Path to your custom player
        player_path = "./cmake-build-debug/player/player"
        
        # Check if custom player exists
        if not os.path.exists(player_path):
            log_error(f"❌ Custom player not found at: {player_path}")
            log_info("💡 Make sure you've compiled the player with:")
            log_info("   cmake --build ./cmake-build-debug --target player")
            return None
        
        # Player configurations with your custom player
        player_configs = [
            {
                "name": "Custom SRT Player",
                "cmd": [player_path, srt_url]
            },
            {
                "name": "Custom Player (fallback)",
                "cmd": [player_path, srt_url]
            }
        ]
        
        # Try to start the custom player
        for i, config in enumerate(player_configs):
            log_info(f"🔄 Attempt {i+1}: {config['name']}")
            
            cmd = config["cmd"]
            log_info(f"   🎯 Command: {' '.join(cmd)}")
            
            try:
                # Start the custom player
                player_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    cwd=".",  # Set working directory
                    preexec_fn=os.setsid if platform.system() == "Linux" else None
                )
                
                # Wait for proper startup
                if wait_for_player_startup(player_process, timeout=15):  # Longer timeout for custom player
                    log_success(f"   ✅ {config['name']} started successfully!")
                    log_success(f"   📺 PID: {player_process.pid}")
                    return player_process
                else:
                    # Player failed - get error details
                    try:
                        stdout, stderr = player_process.communicate(timeout=3)
                        log_error(f"   ❌ {config['name']} failed to start")
                        
                        if stderr:
                            # Show error details
                            error_lines = [line.strip() for line in stderr.split('\n') if line.strip()]
                            for line in error_lines[-5:]:  # Show last 5 error lines
                                log_error(f"      {line}")
                        
                        if stdout:
                            # Show any stdout output
                            output_lines = [line.strip() for line in stdout.split('\n') if line.strip()]
                            for line in output_lines[-3:]:  # Show last 3 output lines
                                log_info(f"      {line}")
                                
                    except:
                        log_error(f"   ❌ {config['name']} exited with code: {player_process.returncode}")
                    
                    player_process = None
                    continue
                    
            except Exception as e:
                log_error(f"   ❌ Exception starting {config['name']}: {e}")
                continue
        
        log_error("❌ Custom player failed to start!")
        log_info("💡 Troubleshooting:")
        log_info("   - Check if player was compiled: cmake --build ./cmake-build-debug --target player")
        log_info("   - Test manually: ./cmake-build-debug/player/player 'srt://128.205.39.64:10080?streamid=#!::r=live/test1,m=request'")
        log_info("   - Check SRT stream availability on server")
        
        return None
        
    except Exception as e:
        log_error(f"❌ Error starting custom player: {e}")
        import traceback
        log_error(traceback.format_exc())
        return None

def cleanup() -> None:
    """Clean up resources on shutdown"""
    log_info("🧹 Performing cleanup...")
    stop_player()
    log_success("✅ Cleanup completed")

def signal_handler(sig, frame) -> None:
    """Handle shutdown signals gracefully"""
    global shutdown_requested
    
    if shutdown_requested:
        log_warning("Multiple shutdown signals received, exiting immediately")
        sys.exit(1)
        
    shutdown_requested = True
    log_info(f"📡 Received signal {sig}, shutting down gracefully...")
    cleanup()
    sys.exit(0)

def run_diagnostics(server_url: str) -> None:
    """Run comprehensive diagnostics"""
    log_info("🔬 Running system diagnostics...")
    
    # Test 1: Screen detection
    width, height = detect_screen_resolution()
    log_info(f"   Screen: {width}x{height}")
    
    # Test 2: Video capabilities  
    capabilities = test_video_capabilities()
    
    # Test 3: Server connectivity
    try:
        response = requests.get(f"{server_url}/ping", timeout=5)
        if response.status_code == 200:
            log_success("   ✅ Server reachable")
        else:
            log_error(f"   ❌ Server error: {response.status_code}")
    except Exception as e:
        log_error(f"   ❌ Server unreachable: {e}")
    
    # Test 4: SRT connectivity
    srt_ip = server_url.replace("http://", "").replace(":5000", "")
    test_srt_connectivity(srt_ip)
    
    # Test 5: File permissions
    log_info(f"   Client ID file: {ID_FILE}")
    log_info(f"   Log file: {LOG_FILE}")
    try:
        test_client_id = get_client_id()
        log_success(f"   ✅ File permissions OK, Client ID: {test_client_id}")
    except Exception as e:
        log_error(f"   ❌ File permission issue: {e}")
    
    log_info("🔬 Diagnostics completed")

def main() -> None:
    """Main application entry point"""
    global shutdown_requested, current_stream, DEBUG
    
    # Set up signal handlers
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Auto-Fullscreen SRT Video Client - Enhanced Version",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 client_code.py
  python3 client_code.py --server http://192.168.1.100:5000 
  python3 client_code.py --interval 5 --debug
  python3 client_code.py --diagnostics
        """
    )
    
    parser.add_argument("--server", default=DEFAULT_SERVER_URL,
                        help=f"Server URL (default: {DEFAULT_SERVER_URL})")
    parser.add_argument("--interval", type=int, default=DEFAULT_POLL_INTERVAL,
                        help=f"Polling interval in seconds (default: {DEFAULT_POLL_INTERVAL})")
    parser.add_argument("--srt-ip", default=None,
                        help="Override SRT server IP address")
    parser.add_argument("--debug", action="store_true",
                        help="Enable verbose debug logging")
    parser.add_argument("--diagnostics", action="store_true",
                        help="Run diagnostics and exit")
    parser.add_argument("--player-path", default="./cmake-build-debug/player/player",
                    help="Path to custom SRT player executable")
    parser.add_argument("--fallback-to-ffplay", action="store_true",
                        help="Fall back to ffplay if custom player fails")
    
    args = parser.parse_args()
    
    # Configure debugging
    DEBUG = args.debug or DEBUG
    
    # Clear old log file on startup
    try:
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)
    except:
        pass
    
    # Print startup banner
    log_success("🎬 AUTO-FULLSCREEN SRT CLIENT - ENHANCED")
    log_success("=" * 45)
    
    client_id = get_client_id()
    client_info = get_client_info()
    
    log_info(f"🏷️  Client ID: {client_id}")
    log_info(f"📍 Local IP: {get_local_ip()}")
    log_info(f"🎯 Server: {args.server}")
    log_info(f"⏱️  Poll interval: {args.interval}s")
    log_info(f"🖥️  Platform: {platform.system()} {platform.release()}")
    
    # Run diagnostics if requested
    if args.diagnostics:
        run_diagnostics(args.server)
        return
    
    # Test system capabilities
    test_video_capabilities()
    
    # Register with server
    log_info("📡 Registering with server...")
    if not register_with_server(args.server, client_id, client_info):
        log_warning("⚠️  Registration failed, but continuing anyway...")
    
    # Main loop
    log_info("🔄 Starting main loop...")
    consecutive_failures = 0
    max_failures = 10
    
    while not shutdown_requested:
        try:
            # Get stream assignment from server
            status = get_stream_assignment(args.server, client_id)
            
            if status:
                consecutive_failures = 0  # Reset failure counter
                
                stream_id = status.get("stream_id")
                srt_ip = status.get("srt_ip", DEFAULT_SRT_IP)
                
                # Override SRT IP if specified
                if args.srt_ip:
                    srt_ip = args.srt_ip
                    log_info(f"🔧 Using override SRT IP: {srt_ip}")
                
                log_info(f"📊 Processing: stream='{stream_id}', current='{current_stream}'")
                
                # Handle stream changes
                if stream_id and stream_id != current_stream:
                    log_info(f"🔄 Stream change: '{current_stream}' → '{stream_id}'")
                    
                    new_player = start_fullscreen_player(
                        stream_id, 
                        srt_ip, 
                        player_path=args.player_path, 
                        allow_fallback=args.fallback_to_ffplay
                    )
                    if new_player:
                        current_stream = stream_id
                        log_success(f"✅ Now streaming: {stream_id}")
                    else:
                        log_error(f"❌ Failed to start stream: {stream_id}")
                
                elif not stream_id and current_stream:
                    log_info("⏹️  No stream assigned - stopping player")
                    stop_player()
                    current_stream = None
                
                # Check if player died
                elif player_process and player_process.poll() is not None:
                    log_warning(f"💀 Player died (exit code: {player_process.returncode})")
                    
                    if current_stream:
                        log_info("🔄 Restarting player...")
                        new_player = start_fullscreen_player(
                            current_stream, 
                            srt_ip, 
                            player_path=args.player_path, 
                            allow_fallback=args.fallback_to_ffplay
                        )
                        if not new_player:
                            log_error("❌ Failed to restart player")
                            current_stream = None
                
            else:
                consecutive_failures += 1
                log_error(f"❌ Server communication failed (attempt {consecutive_failures}/{max_failures})")
                
                if consecutive_failures >= max_failures:
                    log_error("💀 Too many consecutive failures - check server status")
                    # Could implement reconnection backoff here
            
            # Wait before next poll
            time.sleep(args.interval)
            
        except KeyboardInterrupt:
            log_info("⌨️  Keyboard interrupt received")
            break
        except Exception as e:
            log_error(f"❌ Unexpected error in main loop: {e}")
            import traceback
            log_error(traceback.format_exc())
            time.sleep(10)  # Wait longer after unexpected errors
    
    log_success("🏁 SRT client shutdown complete")

if __name__ == "__main__":
    main()