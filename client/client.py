#!/usr/bin/env python3
"""
Enhanced Multi-Screen Client with Automatic Package Management
Automatically handles local package installation if global packages are restricted
"""

import sys
import os
from pathlib import Path

# Add local lib directory to Python path if it exists
LOCAL_LIB_DIR = Path(__file__).parent / "lib"
if LOCAL_LIB_DIR.exists():
    sys.path.insert(0, str(LOCAL_LIB_DIR))

def install_package_locally(package_name):
    """Install a package locally in the ./lib directory"""
    import subprocess
    
    print(f"📦 {package_name} package not found, attempting local installation...")
    
    # Create local lib directory
    LOCAL_LIB_DIR.mkdir(exist_ok=True)
    
    # Try different installation methods
    methods = [
        # Method 1: Standard pip install to target
        [sys.executable, "-m", "pip", "install", "--target", str(LOCAL_LIB_DIR), package_name],
        # Method 2: With --break-system-packages
        [sys.executable, "-m", "pip", "install", "--target", str(LOCAL_LIB_DIR), "--break-system-packages", package_name],
        # Method 3: User install as fallback
        [sys.executable, "-m", "pip", "install", "--user", package_name],
        # Method 4: User install with break system packages
        [sys.executable, "-m", "pip", "install", "--user", "--break-system-packages", package_name],
    ]
    
    for i, cmd in enumerate(methods):
        try:
            print(f"   Trying installation method {i+1}/4...")
            subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Add to path if installed locally
            if "--target" in cmd:
                sys.path.insert(0, str(LOCAL_LIB_DIR))
            
            print(f"✅ Successfully installed {package_name} (method {i+1})")
            return True
            
        except subprocess.CalledProcessError:
            continue
    
    # All methods failed
    print(f"❌ Failed to install {package_name} automatically")
    print(f"💡 Please install manually:")
    print(f"   sudo apt-get install python3-{package_name}")
    print(f"   OR: python3 -m pip install --user --break-system-packages {package_name}")
    return False

def ensure_package(package_name, import_name=None):
    """Ensure a package is available, install locally if needed"""
    if import_name is None:
        import_name = package_name
    
    try:
        __import__(import_name)
        return True
    except ImportError:
        if install_package_locally(package_name):
            try:
                __import__(import_name)
                return True
            except ImportError:
                return False
        return False

# Ensure required packages are available
if not ensure_package("requests"):
    print("Cannot continue without the requests package.")
    sys.exit(1)

# Now we can safely import everything
import requests
import argparse
import time
import logging
import subprocess
import json
import signal
import atexit
import threading
import socket
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlparse

# Try to import tkinter, install locally if needed
try:
    import tkinter as tk
    from tkinter import messagebox
except ImportError:
    print("⚠️  tkinter not available - GUI features will be disabled")
    print("💡 Install with: sudo apt-get install python3-tk")
    # Create dummy classes to prevent errors
    class DummyTk:
        def __init__(self, *args, **kwargs): pass
        def __getattr__(self, name): return lambda *args, **kwargs: None
    
    tk = DummyTk()
    messagebox = DummyTk()

from queue import Queue


class VideoPlayerThread:
    """Dedicated thread for video player management to ensure synchronized frame updates"""
    
    def __init__(self, client_instance, stream_url: str, stream_version: str, logger: logging.Logger):
        self.client = client_instance
        self.stream_url = stream_url
        self.stream_version = stream_version
        self.logger = logger
        self.running = True
        self.player_process = None
        self.player_type = None
        self._thread = None
        self._shutdown_event = threading.Event()
        
        # Start the dedicated thread
        self._thread = threading.Thread(
            target=self._run_player_thread,
            name=f"VideoPlayer-{client_instance.target_screen}",
            daemon=True
        )
        self._thread.start()
    
    def _run_player_thread(self):
        """Main thread loop for video player management"""
        try:
            self.logger.info(f"Video player thread started for {self.client.target_screen}")
            
            # Choose and start the optimal player
            if self._start_player():
                # Monitor the player in this thread
                self._monitor_player()
            else:
                self.logger.error(f"Failed to start player for {self.client.target_screen}")
                
        except Exception as e:
            self.logger.error(f"Video player thread error for {self.client.target_screen}: {e}")
        finally:
            self.logger.info(f"Video player thread stopped for {self.client.target_screen}")
    
    def _start_player(self) -> bool:
        """Start the video player process"""
        try:
            # Choose optimal player
            player_type, reason = self.client.choose_optimal_player(self.stream_url)
            self.player_type = player_type
            
            self.logger.info(f"Starting {player_type} for {self.client.target_screen}: {reason}")
            
            if player_type == "cpp_player":
                return self._start_cpp_player()
            else:
                return self._start_ffplay()
                
        except Exception as e:
            self.logger.error(f"Failed to start player for {self.client.target_screen}: {e}")
            return False
    
    def _start_cpp_player(self) -> bool:
        """Start the built C++ player"""
        try:
            if not self.client.player_executable:
                return False
                
            env = os.environ.copy()
            cmd = [self.client.player_executable, self.stream_url]
            
            self.player_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                cwd=os.path.dirname(self.client.player_executable),
                universal_newlines=True,
                bufsize=1
            )
            
            # Start output monitoring in separate thread
            threading.Thread(
                target=self._monitor_cpp_output,
                daemon=True
            ).start()
            
            self.logger.info(f"C++ player started for {self.client.target_screen} (PID: {self.player_process.pid})")
            return True
            
        except Exception as e:
            self.logger.error(f"C++ player error for {self.client.target_screen}: {e}")
            return False
    
    def _start_ffplay(self) -> bool:
        """Start ffplay"""
        try:
            cmd = [
                "ffplay",
                "-fflags", "nobuffer",
                "-flags", "low_delay", 
                "-framedrop",
                "-strict", "experimental",
                "-err_detect", "ignore_err",
                "-ec", "favor_inter",
                "-sync", "video",
                "-window_title", f"Multi-Screen Client - {self.client.display_name}",
                "-fs",
                "-autoexit",
                "-loglevel", "warning",
                self.stream_url
            ]
            
            self.player_process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Start output monitoring in separate thread
            threading.Thread(
                target=self._monitor_ffplay_output,
                daemon=True
            ).start()
            
            self.logger.info(f"ffplay started for {self.client.target_screen} (PID: {self.player_process.pid})")
            return True
            
        except Exception as e:
            self.logger.error(f"ffplay error for {self.client.target_screen}: {e}")
            return False
    
    def _monitor_cpp_output(self):
        """Monitor C++ player output"""
        try:
            for line in iter(self.player_process.stdout.readline, ''):
                if line.strip():
                    line_clean = line.strip()
                    if "SEI" in line_clean or "timestamp" in line_clean.lower():
                        self.logger.info(f"SEI: {line_clean}")
                    elif "TELEMETRY:" in line_clean:
                        self.logger.info(f"{line_clean}")
                    elif "ERROR" in line_clean.upper():
                        self.logger.error(f"{line_clean}")
                    elif "WARNING" in line_clean.upper():
                        self.logger.warning(f"{line_clean}")
                    else:
                        self.logger.debug(f"{line_clean}")
        except Exception as e:
            self.logger.debug(f"C++ output monitoring error: {e}")
    
    def _monitor_ffplay_output(self):
        """Monitor ffplay output"""
        try:
            for line in iter(self.player_process.stderr.readline, ''):
                if line.strip():
                    line_clean = line.strip()
                    if "decode_slice_header error" in line_clean:
                        continue  # Skip common errors
                    elif "error" in line_clean.lower():
                        self.logger.error(f"{line_clean}")
                    elif "warning" in line_clean.lower():
                        self.logger.warning(f"{line_clean}")
                    else:
                        self.logger.debug(f"{line_clean}")
        except Exception as e:
            self.logger.debug(f"ffplay output monitoring error: {e}")
    
    def _monitor_player(self):
        """Monitor the player process"""
        while self.running and self.player_process and self.player_process.poll() is None:
            time.sleep(0.1)  # 100ms sleep to avoid busy waiting
        
        if self.player_process:
            exit_code = self.player_process.returncode
            if exit_code == 0:
                self.logger.info(f"Player for {self.client.target_screen} ended normally")
            elif exit_code == 1:
                self.logger.warning(f"Player for {self.client.target_screen} connection lost")
            else:
                self.logger.error(f"Player for {self.client.target_screen} exited with code: {exit_code}")
    
    def stop(self):
        """Stop the video player thread"""
        self.running = False
        self._shutdown_event.set()
        
        if self.player_process:
            try:
                self.player_process.terminate()
                try:
                    self.player_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.player_process.kill()
                    try:
                        self.player_process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        pass
            except Exception as e:
                self.logger.error(f"Error stopping player for {self.client.target_screen}: {e}")
            finally:
                self.player_process = None
        
        # Wait for thread to finish
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)


class UnifiedMultiScreenClient:
    """Enhanced multi-screen client with automatic screen targeting"""
    
    def __init__(self, server_url: str, hostname: str, display_name: str, 
                 force_ffplay: bool = False, target_screen: str = None):
        """
        Initialize the multi-screen client
        
        Args:
            server_url: Server URL to connect to
            hostname: Client hostname for identification
            display_name: Display name for admin interface
            force_ffplay: Force use of ffplay for all streams
            target_screen: Target screen (1 or 2)
        """
        # Setup logging first
        self.logger = logging.getLogger(__name__)
        
        self.server_url = server_url
        self.hostname = hostname
        self.display_name = display_name
        self.force_ffplay = force_ffplay
        self.target_screen = target_screen
        
        # Parse target screen to monitor index
        self.target_monitor_index = self._parse_target_screen(target_screen)
        
        # Single-threaded mode for Raspberry Pi efficiency
        self.use_multithreading = False  # Always single-threaded
        self.video_player_thread = None  # Not used in single-threaded mode
        
        # Stream management
        self.current_stream_url = None
        self.current_stream_version = None
        self.current_player_type = None
        self.player_process = None
        self.running = True
        self.retry_interval = 5
        self.max_retries = 60
        self._shutdown_event = threading.Event()
        
        # Client state
        self.registered = False
        self.assignment_status = "waiting_for_assignment"
        
        # Server-assigned client ID (set after registration)
        self._server_client_id = None
        
        # Extract server IP for stream URL fixing
        parsed_url = urlparse(self.server_url)
        self.server_ip = parsed_url.hostname or "127.0.0.1"
        
        # Setup signal handlers and cleanup
        self._setup_signal_handlers()
        atexit.register(self._emergency_cleanup)
        
        # Find player executable
        self.player_executable = self._find_player_executable()
        
        # Window management (simplified - no movement needed)
        self.window_manager = None
        
        # Log single-threaded status
        self.logger.info(f"Single-threaded mode - optimized for Raspberry Pi efficiency")
        print(f"🔧 SINGLE-THREADED: Enabled (Raspberry Pi optimized)")
        print(f"📦 AUTO-INSTALL: Python packages installed automatically as needed")
    
    def _detect_multiple_clients(self) -> bool:
        """Single-threaded mode - always returns False for Raspberry Pi efficiency"""
        # Simplified to single-threaded mode for better performance on single-core devices
        # Each client runs in its own process with 1 main thread
        return False
    
    def _parse_target_screen(self, target_screen: str) -> int:
        """Parse target screen parameter and return monitor index"""
        if not target_screen:
            return 0  # Default to first monitor
        
        target = target_screen.strip()
        
        # Only accept 1 or 2
        if target == "1":
            self.logger.info(f"Target screen '{target_screen}' mapped to monitor 1")
            return 0
        elif target == "2":
            self.logger.info(f"Target screen '{target_screen}' mapped to monitor 2")
            return 1
        else:
            self.logger.warning(f"Invalid target screen '{target_screen}', must be 1 or 2. Defaulting to monitor 1")
            return 0
    
    def _get_target_screen_info(self) -> Dict[str, Any]:
        """Get information about the target screen"""
        screen_names = ['Screen 1', 'Screen 2']
        screen_name = screen_names[self.target_monitor_index] if self.target_monitor_index < len(screen_names) else f"Screen {self.target_monitor_index + 1}"
        
        return {
            'index': self.target_monitor_index,
            'name': screen_name,
            'specified': self.target_screen
        }

    @property
    def client_id(self) -> str:
        """Generate unique client ID using hostname and IP address"""
        # Use server-assigned client ID if available, otherwise generate one
        if self._server_client_id:
            return self._server_client_id
        
        try:
            local_ip = self._get_local_ip_address()
            return f"{self.hostname}_{local_ip}"
        except Exception:
            # Fallback to hostname if IP detection fails
            return self.hostname
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            signal_name = signal.Signals(signum).name
            self.logger.info(f"Received {signal_name} signal, initiating graceful shutdown...")
            self.shutdown()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, signal_handler)
    
    def _find_player_executable(self) -> Optional[str]:
        """Find the C++ player executable"""
        if self.force_ffplay:
            self.logger.info("Forcing ffplay usage (--force-ffplay specified)")
            return None
        
        search_paths = [
            Path(__file__).parent / "multi-screen" / "cmake-build-debug" / "player" / "player",
            Path(__file__).parent / "cmake-build-debug" / "player" / "player", 
            Path(__file__).parent / "build" / "player" / "player",
            Path(__file__).parent / "player" / "player",
            Path("./multi-screen/cmake-build-debug/player/player"),
            Path("./cmake-build-debug/player/player"),
            Path("./build/player/player"),
            Path("./player/player")
        ]
        
        for player_path in search_paths:
            if player_path.exists() and os.access(player_path, os.X_OK):
                self.logger.info(f"Found C++ player: {player_path}")
                return str(player_path.absolute())
        
        self.logger.warning("C++ player not found, will use ffplay fallback")
        return None
    
    def _get_local_ip_address(self) -> str:
        """Get the local IP address for unique client identification"""
        try:
            # Try to get the IP address that would be used to connect to the server
            # This helps distinguish between multiple terminal instances on the same machine
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((self.server_ip, 80))  # Connect to server IP
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception as e:
            self.logger.warning(f"Could not determine local IP address: {e}")
            # Fallback: try to get any non-loopback IP
            try:
                hostname = socket.gethostname()
                local_ip = socket.gethostbyname(hostname)
                if local_ip.startswith('127.'):
                    # If it's loopback, try alternative method
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.connect(("8.8.8.8", 80))  # Connect to external IP
                    local_ip = s.getsockname()[0]
                    s.close()
                return local_ip
            except Exception:
                # Final fallback: use loopback IP
                return "127.0.0.1"
    
    def create_window_manager(self):
        """Create a hidden window manager for hotkey handling"""
        try:
            # Create a simple window manager (no hotkeys needed)
            self.window_manager = tk.Tk()
            self.window_manager.title(f"Multi-Screen Client - {self.display_name}")
            self.window_manager.geometry("400x200")
            self.window_manager.configure(bg='black')
            
            # Add a simple label
            label = tk.Label(self.window_manager, 
                           text=f"Client: {self.display_name}\nTarget: {self.target_screen or 'Default'}\nStatus: Running",
                           fg='white', bg='black', font=('Arial', 12))
            label.pack(expand=True)
            
            # Make window always on top and focusable
            self.window_manager.attributes('-topmost', True)
            self.window_manager.focus_force()
            
            print(f"🖥️  Window Manager Started")
            print(f"   Target Screen: {self.target_screen or 'Default'}")
            print(f"   Note: Monitor movement disabled")
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to create window manager: {e}")
            return False
    
    def move_to_monitor(self, monitor_index: int):
        """Stub method - monitor movement not needed"""
        print(f"Monitor movement disabled - window will appear on default screen")
        self.logger.info(f"Monitor movement requested but disabled")
    
    def auto_position_window(self):
        """Auto-position window on target screen"""
        if self.target_screen:
            print(f"\n🎯 TARGET SCREEN: {self.target_screen}")
            target_info = self._get_target_screen_info()
            print(f"   Target: {target_info['name']}")
            
            # Check if we have positioning tools available
            if not self._check_positioning_tools():
                print(f"   Note: Window positioning tools not available")
                print(f"   Install with: sudo apt-get install wmctrl xdotool")
                return
            
            # Get monitor information
            geometry = self._get_monitor_geometry()
            if geometry:
                print(f"   Monitor: {geometry['width']}x{geometry['height']} at +{geometry['x']}+{geometry['y']}")
            else:
                print(f"   Note: Could not detect monitor layout")
                print(f"   Run 'xrandr --listmonitors' to check your setup")
        
        self.logger.info(f"Auto-positioning for target screen {self.target_screen}")
    
    def _check_positioning_tools(self) -> bool:
        """Check if window positioning tools are available"""
        try:
            subprocess.run(['wmctrl', '--version'], capture_output=True, timeout=2)
            return True
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def move_to_next_monitor(self, event=None):
        """Stub method - monitor movement not needed"""
        print(f"Monitor movement disabled")
        self.logger.info(f"Next monitor movement requested but disabled")
    
    def move_to_previous_monitor(self, event=None):
        """Stub method - monitor movement not needed"""
        print(f"Monitor movement disabled")
        self.logger.info(f"Previous monitor movement requested but disabled")
    
    def show_help(self, event=None):
        """Show simplified help"""
        target_info = self._get_target_screen_info()
        help_text = f"""
Multi-Screen Client Help:

Target Screen: {target_info['name']}
Note: Monitor movement has been disabled.
Windows will appear on the default screen.

Press Ctrl+C to stop the client.
        """
        try:
            messagebox.showinfo("Multi-Screen Client Help", help_text)
        except:
            print(help_text)
    
    def detect_sei_in_stream(self, stream_url: str, timeout: int = 10) -> bool:
        """
        Detect if the stream contains SEI metadata by analyzing the first few seconds
        """
        try:
            print(f"🔍 Analyzing stream for SEI metadata...")
            print(f"   Stream URL: {stream_url}")
            
            # Use ffprobe to analyze the stream for a short duration
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-select_streams", "v:0",
                "-show_entries", "frame=pkt_data",
                "-of", "csv=p=0",
                "-read_intervals", f"%+#10",  # Read first 10 frames
                "-timeout", str(timeout * 1000000),  # Convert to microseconds
                stream_url
            ]
            
            self.logger.debug(f"SEI detection command: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                
                # Check if we got any frame data
                if stdout and len(stdout.strip()) > 0:
                    # Look for patterns that might indicate SEI data
                    sei_patterns = [
                        "681d5c8f-80cd-4847-930a-99b9484b4a32",  # OpenVideoWalls UUID
                        "00000000000000000000000000000000",      # Static SEI pattern
                    ]
                    
                    for pattern in sei_patterns:
                        if pattern.lower() in stdout.lower():
                            print(f"✅ SEI metadata detected (pattern: {pattern[:16]}...)")
                            return True
                    
                    # Alternative: Check stderr for SEI-related messages
                    if stderr:
                        sei_indicators = ["sei", "user_data", "h264_metadata"]
                        for indicator in sei_indicators:
                            if indicator.lower() in stderr.lower():
                                print(f"✅ SEI indicators found in stream analysis")
                                return True
                    
                    print(f"❌ No SEI metadata detected - standard stream")
                    return False
                else:
                    print(f"⚠️  Could not analyze stream data")
                    return False
                    
            except subprocess.TimeoutExpired:
                print(f"⏱️  Stream analysis timeout - assuming no SEI")
                process.kill()
                return False
                
        except FileNotFoundError:
            self.logger.warning("ffprobe not found - cannot detect SEI, assuming no SEI")
            return False
        except Exception as e:
            self.logger.warning(f"SEI detection failed: {e} - assuming no SEI")
            return False
    
    def choose_optimal_player(self, stream_url: str) -> Tuple[str, str]:
        """Choose the optimal player based on stream characteristics"""
        # If forced to use ffplay, don't bother detecting
        if self.force_ffplay:
            return "ffplay", "Forced ffplay mode (--force-ffplay specified)"
        
        # If C++ player not available, use ffplay
        if not self.player_executable or not os.path.exists(self.player_executable):
            return "ffplay", "C++ player not available"
        
        # Detect SEI metadata in the stream
        has_sei = self.detect_sei_in_stream(stream_url)
        
        if has_sei:
            return "cpp_player", "SEI metadata detected - using C++ player for synchronization"
        else:
            return "ffplay", "No SEI metadata - using ffplay for standard playback"
    
    def register(self) -> bool:
        """Register client with server"""
        try:
            target_info = self._get_target_screen_info()
            
            print(f"\n{'='*80}")
            print(f"🚀 STARTING MULTI-SCREEN CLIENT REGISTRATION")
            print(f"   Client: {self.hostname}")
            print(f"   Local IP: {self._get_local_ip_address()}")
            print(f"   Client ID: {self.client_id}")
            print(f"   Display Name: {self.display_name}")
            print(f"   Target Screen: {target_info['name']}")
            if 'warning' in target_info:
                print(f"   Warning: {target_info['warning']}")
            print(f"   Server: {self.server_url}")
            print(f"   Server IP: {self.server_ip}")
            print(f"   Smart Player: {'Enabled' if not self.force_ffplay else 'Disabled (force ffplay)'}")
            
            registration_start = time.time()
            registration_start_formatted = time.strftime("%Y-%m-%d %H:%M:%S.%f", time.gmtime(registration_start))[:-3]
            print(f"   Start Time: {registration_start_formatted} UTC")
            print(f"{'='*80}")
            
            # Create platform string indicating player capability
            if self.force_ffplay:
                player_type = "ffplay_only"
            elif not self.player_executable:
                player_type = "ffplay_fb"  # fallback
            else:
                player_type = "smart_sel"  # smart selection
            
            # Get local IP address for unique client identification
            local_ip = self._get_local_ip_address()
            
            registration_data = {
                "hostname": self.hostname,
                "ip_address": local_ip,  # Include IP address for unique client ID
                "display_name": self.display_name,
                "platform": f"multiscreen_{player_type}",  # Indicate multi-screen capability
                "target_screen": self.target_screen,  # Include target screen info
                "target_monitor": target_info['index']
            }
            
            print(f"\n📡 Sending registration request...")
            request_sent_time = time.time()
            
            # Try new registration endpoint first, fallback to legacy
            try:
                print(f"🔄 Trying new endpoint: {self.server_url}/api/clients/register")
                print(f"📋 Registration data: {json.dumps(registration_data, indent=2)}")
                response = requests.post(
                    f"{self.server_url}/api/clients/register",
                    json=registration_data,
                    timeout=10
                )
                endpoint_used = "new (/api/clients/register)"
                print(f"✅ New endpoint succeeded with status: {response.status_code}")
            except requests.exceptions.RequestException as e:
                # Fallback to legacy endpoint (simplified data)
                print(f"❌ New endpoint failed with RequestException: {e}")
                self.logger.info("New endpoint failed, trying legacy endpoint...")
                legacy_data = {
                    "hostname": self.hostname,
                    "display_name": self.display_name,
                    "platform": f"multiscreen_{player_type}"
                }
                response = requests.post(
                    f"{self.server_url}/register_client",
                    json=legacy_data,
                    timeout=10
                )
                endpoint_used = "legacy (/register_client)"
            except Exception as e:
                # Catch any other exceptions
                print(f"❌ New endpoint failed with unexpected error: {e}")
                print(f"🔧 Error type: {type(e).__name__}")
                import traceback
                print(f"📄 Traceback: {traceback.format_exc()}")
                # Fallback to legacy endpoint (simplified data)
                self.logger.info("New endpoint failed, trying legacy endpoint...")
                legacy_data = {
                    "hostname": self.hostname,
                    "display_name": self.display_name,
                    "platform": f"multiscreen_{player_type}"
                }
                response = requests.post(
                    f"{self.server_url}/register_client",
                    json=legacy_data,
                    timeout=10
                )
                endpoint_used = "legacy (/register_client)"
            
            response_received_time = time.time()
            network_delay_ms = (response_received_time - request_sent_time) * 1000
            
            print(f"📨 Response received in {network_delay_ms:.1f}ms using {endpoint_used}")
            
            if response.status_code in [200, 202]:
                result = response.json()
                if result.get("success", True):  # Legacy endpoint doesn't have 'success' field
                    registration_end = time.time()
                    total_time_ms = (registration_end - registration_start) * 1000
                    
                    print(f"\n🎉 REGISTRATION SUCCESSFUL!")
                    print(f"   Client ID: {result.get('client_id', self.client_id)}")
                    print(f"   Status: {result.get('status', 'registered')}")
                    if 'server_time' in result:
                        print(f"   Server Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(result['server_time']))}")
                    print(f"   Total Registration Time: {total_time_ms:.1f}ms")
                    
                    self.registered = True
                    self.assignment_status = result.get('status', 'waiting_for_assignment')
                    self._server_client_id = result.get('client_id') # Store server-assigned ID
                    
                    # Initialize heartbeat tracking
                    self.last_heartbeat = time.time()
                    
                    # Show next steps
                    next_steps = result.get('next_steps', [
                        "Wait for admin to assign you to a group",
                        "Admin will use the web interface to make assignments",
                        "Client will automatically start playing when streaming begins"
                    ])
                    print(f"\n📋 Next Steps:")
                    for step in next_steps:
                        print(f"    {step}")
                    
                    print(f"{'='*80}")
                    return True
                else:
                    print(f"❌ Registration failed: {result.get('error', 'Unknown error')}")
                    return False
            else:
                print(f"❌ Registration failed with HTTP status {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"💥 Registration error: {e}")
            self.logger.error(f"Registration error: {e}")
            return False
    
    def wait_for_assignment(self) -> bool:
        """Wait for admin to assign this client to a group and stream"""
        retry_count = 0
        
        print(f"\n⏳ Waiting for assignment from admin...")
        print(f"   Admin needs to:")
        print(f"   1. Assign this client to a group")
        print(f"   2. Assign this client to a specific stream/screen")
        print(f"   3. Start streaming for the group")
        print(f"   (Check the web interface at {self.server_url})")
        
        while self.running and not self._shutdown_event.is_set() and retry_count < self.max_retries:
            try:
                # Use new endpoint if available, fallback to legacy
                try:
                    response = requests.post(
                        f"{self.server_url}/api/clients/wait_for_assignment",
                        json={"client_id": self.client_id},
                        timeout=10
                    )
                except requests.exceptions.RequestException:
                    # Fallback to legacy endpoint
                    response = requests.post(
                        f"{self.server_url}/wait_for_stream",
                        json={"client_id": self.client_id},
                        timeout=10
                    )
                
                if response.status_code not in [200, 202]:
                    raise Exception(f"HTTP {response.status_code}: {response.text}")
                
                data = response.json()
                status = data.get('status')
                message = data.get('message', '')
                
                # Update heartbeat since we're actively communicating with server
                self.last_heartbeat = time.time()
                
                self.logger.debug(f"Server response: status={status}")
                
                if status == "ready_to_play":
                    # Stream is ready!
                    original_stream_url = data.get('stream_url')
                    self.current_stream_url = self.fix_stream_url(original_stream_url)
                    
                    # Handle stream version
                    server_version = data.get('stream_version')
                    if server_version is not None:
                        self.current_stream_version = server_version
                    else:
                        if self.current_stream_version is None:
                            self.current_stream_version = int(time.time())
                    
                    group_name = data.get('group_name', 'unknown')
                    stream_assignment = data.get('stream_assignment', 'unknown')
                    
                    print(f"\n🎯 ASSIGNMENT COMPLETE!")
                    print(f"   Group: {group_name}")
                    print(f"   Stream: {stream_assignment}")
                    print(f"   Assignment Type: {data.get('assignment_status', 'unknown')}")
                    if data.get('screen_number') is not None:
                        print(f"   Screen Number: {data.get('screen_number')}")
                    print(f"   Stream URL: {self.current_stream_url}")
                    print(f"   Stream Version: {self.current_stream_version}")
                    return True
                
                elif status in ["waiting_for_group_assignment", "waiting_for_stream_assignment"]:
                    print(f"⏳ {message}")
                    retry_count = 0  # Don't count as failure
                
                elif status == "waiting_for_streaming":
                    group_name = data.get('group_name', 'unknown')
                    stream_assignment = data.get('stream_assignment', 'unknown')
                    print(f"⏳ {message}")
                    print(f"   Assigned to: {group_name}/{stream_assignment}")
                    print(f"   Waiting for admin to start streaming...")
                    retry_count = 0
                
                elif status == "group_not_found":
                    # The group might exist but Docker discovery is failing
                    # Keep waiting instead of giving up
                    group_id = data.get('group_id')
                    if retry_count % 6 == 0:
                        print(f"⚠️  Group validation failed, but continuing (Docker discovery issue)")
                        print(f"   Group ID: {group_id}")
                        print(f"   Will retry...")
                    # Don't print error every time
                    retry_count += 1
                    # Continue waiting instead of returning error
                
                elif status == "not_registered":
                    print(f"❌ {message}")
                    print(f"   Client may have been removed from server")
                    return False
                
                else:
                    print(f"❓ Unexpected status: {status} - {message}")
                    retry_count += 1
                
                # Interruptible sleep
                if self._shutdown_event.wait(timeout=self.retry_interval):
                    print(f"🛑 Shutdown requested during wait")
                    return False
                
            except Exception as e:
                print(f"🌐 Network error ({retry_count + 1}/{self.max_retries}): {e}")
                retry_count += 1
                if self._shutdown_event.wait(timeout=self.retry_interval * 2):
                    print(f"🛑 Shutdown requested during error wait")
                    return False
        
        if retry_count >= self.max_retries:
            print(f"❌ Max retries reached, giving up")
            return False
        
        return False

    def send_heartbeat(self) -> bool:
        """Send heartbeat to server to keep connection alive"""
        try:
            response = requests.post(
                f"{self.server_url}/api/clients/heartbeat",
                json={
                    "client_id": self.client_id
                },
                timeout=10
            )
            data = response.json()
            
            if data.get("success", False):
                print(f"💓 Heartbeat sent successfully")
                return True
            else:
                print(f"💔 Heartbeat failed: {data.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
                print(f"💔 Heartbeat request failed: {e}")
                return False
    
    def fix_stream_url(self, stream_url: str) -> str:
        """Fix stream URL to use server IP instead of localhost"""
        if not stream_url:
            return stream_url
            
        if "127.0.0.1" in stream_url:
            fixed_url = stream_url.replace("127.0.0.1", self.server_ip)
            self.logger.info(f"Fixed stream URL: 127.0.0.1 → {self.server_ip}")
            return fixed_url
        elif "localhost" in stream_url:
            fixed_url = stream_url.replace("localhost", self.server_ip)
            self.logger.info(f"Fixed stream URL: localhost → {self.server_ip}")
            return fixed_url
        else:
            return stream_url
    
    def play_stream(self) -> bool:
        """Start playing the assigned stream with single-threaded player selection"""
        if not self.current_stream_url:
            self.logger.error("No stream URL available")
            return False
            
        try:
            self.stop_stream()  # Clean up any existing player
            
            # Single-threaded mode (optimized for Raspberry Pi)
            print(f"\n🎬 SINGLE-THREADED VIDEO PLAYER")
            print(f"   Mode: Main thread playback (Raspberry Pi optimized)")
            print(f"   Target Screen: {self.target_screen}")
            print(f"   Stream URL: {self.current_stream_url}")
            
            # Choose the optimal player for this stream
            player_type, reason = self.choose_optimal_player(self.current_stream_url)
            self.current_player_type = player_type
            
            print(f"   Selected: {player_type.upper()}")
            print(f"   Reason: {reason}")
            
            if player_type == "cpp_player":
                result = self._play_with_cpp_player()
            else:
                result = self._play_with_ffplay()
            
            # Auto-position window on target screen if specified
            if result and self.target_screen:
                threading.Thread(target=self.auto_position_window, daemon=True).start()
            
            return result
                
        except Exception as e:
            self.logger.error(f"Player error: {e}")
            return False
    
    def _play_with_cpp_player(self) -> bool:
        """Start playing with the built C++ player (for SEI streams)"""
        try:
            print(f"\n🚀 STARTING C++ PLAYER (SEI MODE)")
            print(f"   Stream URL: {self.current_stream_url}")
            print(f"   Stream Version: {self.current_stream_version}")
            print(f"   Capability: SEI timestamp processing")
            
            env = os.environ.copy()
            cmd = [self.player_executable, self.current_stream_url]
            
            self.player_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                cwd=os.path.dirname(self.player_executable),
                universal_newlines=True,
                bufsize=1
            )
            
            # Monitor C++ player output with SEI-specific logging
            def monitor_cpp_output():
                try:
                    for line in iter(self.player_process.stdout.readline, ''):
                        if line.strip():
                            line_clean = line.strip()
                            if "SEI" in line_clean or "timestamp" in line_clean.lower():
                                self.logger.info(f"🔍 SEI: {line_clean}")
                            elif "TELEMETRY:" in line_clean:
                                self.logger.info(f"📊 {line_clean}")
                            elif "ERROR" in line_clean.upper():
                                self.logger.error(f"❌ {line_clean}")
                            elif "WARNING" in line_clean.upper():
                                self.logger.warning(f"⚠️ {line_clean}")
                            else:
                                self.logger.debug(f"ℹ️ {line_clean}")
                except Exception as e:
                    self.logger.error(f"Error monitoring C++ output: {e}")
                finally:
                    if self.player_process and self.player_process.stdout:
                        self.player_process.stdout.close()
            
            output_thread = threading.Thread(target=monitor_cpp_output, daemon=True)
            output_thread.start()
            
            print(f"   Player PID: {self.player_process.pid}")
            print(f"   Status: Playing with SEI processing")
            self.logger.info(f"C++ Player started for SEI stream")
            return True
            
        except Exception as e:
            self.logger.error(f"C++ Player error: {e}")
            return False
    
    def _play_with_ffplay(self) -> bool:
        """Start playing with ffplay (for standard streams without SEI)"""
        try:
            print(f"\n🚀 STARTING FFPLAY (STANDARD MODE)")
            print(f"   Stream URL: {self.current_stream_url}")
            print(f"   Stream Version: {self.current_stream_version}")
            print(f"   Capability: Standard video playback")
            print(f"   Target Screen: {self.target_screen}")
            
            # Get monitor information for positioning
            geometry_info = self._get_monitor_geometry()
            
            # Simple ffplay command that works
            cmd = [
                "ffplay",
                "-fflags", "nobuffer",
                "-flags", "low_delay", 
                "-framedrop",
                "-strict", "experimental",
                "-err_detect", "ignore_err",
                "-ec", "favor_inter",
                "-sync", "video",
                "-window_title", f"Multi-Screen Client - {self.display_name}",
                "-fs",  # Start fullscreen
                "-autoexit",
                "-loglevel", "info",
                self.current_stream_url
            ]
            
            if geometry_info:
                print(f"   Monitor detected: {geometry_info['width']}x{geometry_info['height']} at +{geometry_info['x']}+{geometry_info['y']}")
            else:
                print(f"   Monitor detection failed, using default positioning")
            
            self.player_process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Move window to target screen after it starts (if needed)
            if geometry_info and self.target_screen and self.target_screen != "1":
                # Only move if target is not screen 1 (default)
                positioning_delay = 3.0  # 3 seconds delay for stream to stabilize
                threading.Timer(positioning_delay, self._move_to_target_screen, args=(geometry_info,)).start()
                print(f"   Window will be moved to Screen {self.target_screen} in {positioning_delay} seconds")
            
            # Monitor ffplay output
            def monitor_ffplay_output():
                try:
                    for line in iter(self.player_process.stderr.readline, ''):
                        if line.strip():
                            line_clean = line.strip()
                            # Show connection and SRT-related messages
                            if any(keyword in line_clean.lower() for keyword in ['srt', 'connection', 'connect', 'timeout', 'failed', 'error']):
                                print(f"🔌 {line_clean}")
                                self.logger.info(f"FFplay: {line_clean}")
                            # Skip configuration spam
                            elif "configuration:" in line_clean:
                                continue
                            elif "decode_slice_header error" in line_clean:
                                continue
                            else:
                                self.logger.debug(f"FFplay: {line_clean}")
                except Exception as e:
                    self.logger.debug(f"Error monitoring ffplay output: {e}")
            
            output_thread = threading.Thread(target=monitor_ffplay_output, daemon=True)
            output_thread.start()
            
            print(f"   Player PID: {self.player_process.pid}")
            print(f"   Status: Playing standard stream")
            self.logger.info(f"ffplay started for standard stream")
            return True
            
        except Exception as e:
            self.logger.error(f"ffplay error: {e}")
            return False
    
    def _move_to_target_screen(self, geometry: Dict[str, int]):
        """Move ffplay window to target screen"""
        try:
            print(f"   Attempting to move window to Screen {self.target_screen}")
            
            # Give stream time to start
            time.sleep(1)
            
            # Find the ffplay window
            result = subprocess.run(['wmctrl', '-l'], capture_output=True, text=True, timeout=5)
            
            if result.returncode != 0:
                print(f"   wmctrl not available - window will stay on default screen")
                return
            
            window_id = None
            for line in result.stdout.split('\n'):
                if 'Multi-Screen Client' in line:
                    window_id = line.split()[0]
                    break
            
            if window_id:
                x, y = geometry['x'], geometry['y']
                w, h = geometry['width'], geometry['height']
                
                # Remove fullscreen first
                subprocess.run(['wmctrl', '-i', '-r', window_id, '-b', 'remove,fullscreen'], 
                             timeout=5, capture_output=True)
                
                time.sleep(0.5)
                
                # Move window to correct screen
                subprocess.run(['wmctrl', '-i', '-r', window_id, '-e', f'0,{x},{y},{w},{h}'], 
                             timeout=5, capture_output=True)
                
                time.sleep(0.5)
                
                # Make fullscreen again
                subprocess.run(['wmctrl', '-i', '-r', window_id, '-b', 'add,fullscreen'], 
                             timeout=5, capture_output=True)
                
                print(f"✅ Window moved to Screen {self.target_screen}")
                
            else:
                print(f"   Could not find ffplay window - it may already be positioned correctly")
                
        except Exception as e:
            print(f"   Window positioning failed: {e}")
            print(f"   Stream will continue on default screen")
    
    def _make_window_fullscreen_on_screen(self, geometry: Dict[str, int]):
        """Make ffplay window fullscreen on the target screen with retries"""
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                print(f"   Attempting window positioning (attempt {attempt + 1}/{max_attempts})")
                
                # Give more time for stream to stabilize
                if attempt > 0:
                    time.sleep(2)  # Additional delay between retries
                else:
                    time.sleep(1)  # Initial delay
                
                # Find the ffplay window
                result = subprocess.run(['wmctrl', '-l'], capture_output=True, text=True, timeout=5)
                
                if result.returncode != 0:
                    print(f"   Could not list windows (attempt {attempt + 1})")
                    continue
                
                window_id = None
                windows_found = []
                
                for line in result.stdout.split('\n'):
                    if line.strip():
                        windows_found.append(line.strip())
                        if 'Multi-Screen Client' in line or 'ffplay' in line:
                            window_id = line.split()[0]
                            break
                
                print(f"   Found {len(windows_found)} windows, ffplay window: {'found' if window_id else 'not found'}")
                
                if window_id:
                    x, y = geometry['x'], geometry['y']
                    w, h = geometry['width'], geometry['height']
                    
                    print(f"   Moving window {window_id} to {w}x{h} at +{x}+{y}")
                    
                    # Step 1: Move and resize window to correct screen
                    move_result = subprocess.run(
                        ['wmctrl', '-i', '-r', window_id, '-e', f'0,{x},{y},{w},{h}'], 
                        timeout=5, capture_output=True
                    )
                    
                    if move_result.returncode == 0:
                        print(f"   Window moved successfully")
                        time.sleep(1)  # Allow window to settle
                        
                        # Step 2: Make it fullscreen
                        fs_result = subprocess.run(
                            ['wmctrl', '-i', '-r', window_id, '-b', 'add,fullscreen'], 
                            timeout=5, capture_output=True
                        )
                        
                        if fs_result.returncode == 0:
                            print(f"   Window made fullscreen on Screen {self.target_screen} ({w}x{h} at +{x}+{y})")
                            return  # Success, exit function
                        else:
                            print(f"   Failed to make fullscreen: {fs_result.stderr.decode()}")
                    else:
                        print(f"   Failed to move window: {move_result.stderr.decode()}")
                
                else:
                    print(f"   ffplay window not found in window list")
                    if windows_found:
                        print(f"   Available windows: {windows_found[:3]}")  # Show first 3
                
            except Exception as e:
                print(f"   Window positioning attempt {attempt + 1} failed: {e}")
        
        print(f"   All window positioning attempts failed - stream will play on default screen")
    
    def _get_monitor_geometry(self) -> Optional[Dict[str, int]]:
        """Get geometry information for the target monitor"""
        try:
            if not self.target_screen:
                return None
            
            # Use xrandr to get monitor information
            result = subprocess.run(['xrandr', '--listmonitors'], 
                                  capture_output=True, text=True, timeout=5)
            
            if result.returncode != 0:
                return None
            
            print(f"Debug - xrandr output:\n{result.stdout}")
            
            monitors = []
            for line in result.stdout.split('\n'):
                if '+' in line and not line.strip().startswith('Monitors:'):
                    # Parse monitor info: " 1: +DP-2 1920/510x1080/287+1920+0  DP-2"
                    # or: " 0: +HDMI-1 1920/510x1080/287+0+0  HDMI-1"
                    parts = line.strip().split()
                    if len(parts) >= 3:
                        geometry = parts[2]  # "1920/510x1080/287+1920+0"
                        print(f"Debug - parsing geometry: {geometry}")
                        
                        if 'x' in geometry and '+' in geometry:
                            try:
                                # Split by '/' to get width and height parts
                                # Format: width/mmwidth x height/mmheight + x + y
                                before_plus = geometry.split('+')[0]  # "1920/510x1080/287"
                                width_part = before_plus.split('x')[0]  # "1920/510"
                                height_part = before_plus.split('x')[1]  # "1080/287"
                                
                                width = int(width_part.split('/')[0])   # 1920
                                height = int(height_part.split('/')[0]) # 1080
                                
                                # Get position
                                pos_parts = geometry.split('+')[1:]  # ['1920', '0']
                                x = int(pos_parts[0]) if len(pos_parts) > 0 else 0
                                y = int(pos_parts[1]) if len(pos_parts) > 1 else 0
                                
                                monitor_info = {
                                    'width': width,
                                    'height': height,
                                    'x': x,
                                    'y': y
                                }
                                
                                print(f"Debug - parsed monitor: {monitor_info}")
                                monitors.append(monitor_info)
                                
                            except (ValueError, IndexError) as e:
                                print(f"Debug - failed to parse geometry {geometry}: {e}")
                                continue
            
            print(f"Debug - found {len(monitors)} monitors: {monitors}")
            
            # Select monitor based on target screen
            if self.target_screen == "1" and len(monitors) >= 1:
                return monitors[0]
            elif self.target_screen == "2" and len(monitors) >= 2:
                return monitors[1]
            elif len(monitors) >= 1:
                # Fallback to first monitor
                return monitors[0]
                
            return None
            
        except Exception as e:
            self.logger.debug(f"Failed to get monitor geometry: {e}")
            print(f"Debug - exception getting monitor geometry: {e}")
            return None
    
    def _position_ffplay_window(self, geometry: Dict[str, int]):
        """Position ffplay window on the correct monitor using wmctrl"""
        try:
            # Give ffplay more time to fully initialize
            time.sleep(1)
            
            # Find the ffplay window
            result = subprocess.run(['wmctrl', '-l'], capture_output=True, text=True, timeout=5)
            
            if result.returncode != 0:
                return
            
            window_id = None
            for line in result.stdout.split('\n'):
                if 'Multi-Screen Client' in line or 'ffplay' in line:
                    window_id = line.split()[0]
                    break
            
            if window_id:
                # Move and resize window
                x, y = geometry['x'], geometry['y']
                w, h = geometry['width'], geometry['height']
                
                # Move window to correct position
                subprocess.run(['wmctrl', '-i', '-r', window_id, '-e', f'0,{x},{y},{w},{h}'], 
                             timeout=5)
                
                # Make it fullscreen on that monitor
                subprocess.run(['wmctrl', '-i', '-r', window_id, '-b', 'add,fullscreen'], 
                             timeout=5)
                
                print(f"✅ Positioned window on Screen {self.target_screen} ({w}x{h} at +{x}+{y})")
                
            else:
                print(f"⚠️  Could not find ffplay window to position")
                
        except Exception as e:
            self.logger.debug(f"Failed to position window: {e}")
            print(f"⚠️  Window positioning failed: {e}")
    
    def monitor_player(self) -> str:
        """Monitor the player process and check for stream changes"""
        if not self.player_process:
            return 'error'
        
        # Determine current player type for display
        player_display_name = "C++ Player" if self.current_player_type == "cpp_player" else "ffplay"
        
        print(f"\n👀 MONITORING {player_display_name.upper()}")
        print(f"   PID: {self.player_process.pid}")
        print(f"   Stream: {self.current_stream_url}")
        print(f"   Player Type: {self.current_player_type}")
        
        last_stream_check = time.time()
        stream_check_interval = 10
        last_health_report = time.time()
        health_report_interval = 30
        
        while self.running and not self._shutdown_event.is_set() and self.player_process.poll() is None:
            current_time = time.time()
            
            # Handle window manager events
            if self.window_manager:
                try:
                    self.window_manager.update()
                except:
                    # Window manager closed or tk not available
                    break
            
            # Check for stream changes
            if current_time - last_stream_check >= stream_check_interval:
                if self._check_for_stream_change():
                    print(f"🔄 Stream change detected, will restart with optimal player...")
                    self.stop_stream()
                    return 'stream_changed'
                last_stream_check = current_time
            
            # Periodic health report
            if current_time - last_health_report >= health_report_interval:
                print(f"💚 {player_display_name} health: PID={self.player_process.pid}, "
                      f"Running {int(current_time - last_health_report)}s")
                last_health_report = current_time
            
            # Check for shutdown
            if self._shutdown_event.wait(timeout=1):
                print(f"🛑 Shutdown requested during monitoring")
                self.stop_stream()
                return 'user_exit'
        
        # Player has stopped
        if self._shutdown_event.is_set() or not self.running:
            return 'user_exit'
        
        exit_code = self.player_process.returncode if self.player_process else -1
        
        if exit_code == 0:
            print(f"✅ {player_display_name} ended normally")
            return 'stream_ended'
        elif exit_code == 1:
            print(f"🔌 {player_display_name} connection lost or stream unavailable")
            return 'connection_lost'
        else:
            print(f"❌ {player_display_name} exited with error code: {exit_code}")
            return 'error'
    
    def _check_for_stream_change(self) -> bool:
        """Check if the stream URL or version has changed on the server"""
        try:
            # Use new endpoint if available, fallback to legacy
            try:
                response = requests.post(
                    f"{self.server_url}/api/clients/wait_for_assignment",
                    json={"client_id": self.client_id},
                    timeout=5
                )
            except requests.exceptions.RequestException:
                response = requests.post(
                    f"{self.server_url}/wait_for_stream",
                    json={"client_id": self.client_id},
                    timeout=5
                )
            
            # Accept both 200 and 202 as valid responses
            if response.status_code in [200, 202]:
                data = response.json()
                status = data.get('status')
                
                if status == "ready_to_play":
                    new_stream_url = self.fix_stream_url(data.get('stream_url'))
                    new_stream_version = data.get('stream_version')
                    
                    # Check for meaningful changes
                    url_changed = (new_stream_url and 
                                self.current_stream_url and 
                                new_stream_url != self.current_stream_url)
                    
                    version_changed = False
                    if new_stream_version is not None and self.current_stream_version is not None:
                        version_changed = (new_stream_version != self.current_stream_version)
                    
                    if url_changed or version_changed:
                        self.logger.info(f"Stream change detected:")
                        if url_changed:
                            self.logger.info(f"  URL: {self.current_stream_url} → {new_stream_url}")
                        if version_changed:
                            self.logger.info(f"  Version: {self.current_stream_version} → {new_stream_version}")
                        
                        self.current_stream_url = new_stream_url
                        if new_stream_version is not None:
                            self.current_stream_version = new_stream_version
                        return True
                    
                elif status in ["waiting_for_streaming", "group_not_running", "not_registered"]:
                    # These statuses indicate the stream has stopped
                    self.logger.info(f"Stream stopped on server: {status}")
                    return True
                
                # For waiting states (202), no change needed
                elif response.status_code == 202:
                    self.logger.debug(f"Stream check: still waiting ({status})")
                    return False
                    
            elif response.status_code == 404:
                # Client not found - may have been unregistered
                self.logger.warning("Client not found on server during stream check")
                return True
                
            else:
                # Unexpected status code
                self.logger.debug(f"Stream check returned unexpected status: {response.status_code}")
                
            return False
            
        except requests.exceptions.Timeout:
            # Timeout is not necessarily an error for a quick check
            self.logger.debug("Stream check timed out - assuming no change")
            return False
            
        except Exception as e:
            self.logger.debug(f"Stream check failed: {e}")
            return False
    
    def stop_stream(self):
        """Stop the player with comprehensive cleanup"""
        # Stop single-threaded player if active
        if self.player_process:
            try:
                pid = self.player_process.pid
                player_name = "C++ Player" if self.current_player_type == "cpp_player" else "ffplay"
                print(f"🛑 Stopping {player_name} (PID: {pid})")
                
                # Graceful termination
                self.player_process.terminate()
                
                try:
                    self.player_process.wait(timeout=3)
                    print(f"✅ {player_name} stopped gracefully")
                except subprocess.TimeoutExpired:
                    print(f"💀 Force killing {player_name}")
                    self.player_process.kill()
                    
                    try:
                        self.player_process.wait(timeout=2)
                        print(f"✅ {player_name} force-killed")
                    except subprocess.TimeoutExpired:
                        print(f"⚠️ {player_name} unresponsive")
                        try:
                            os.kill(pid, signal.SIGKILL)
                        except (OSError, ProcessLookupError):
                            pass
                
            except (OSError, ProcessLookupError):
                print(f"ℹ️ Player process already terminated")
            except Exception as e:
                self.logger.error(f"Error stopping player: {e}")
            finally:
                self.player_process = None
                self.current_player_type = None
    
    def shutdown(self):
        """Initiate graceful shutdown"""
        if not self.running:
            return
        
        print(f"\n🛑 INITIATING GRACEFUL SHUTDOWN")
        self.running = False
        self._shutdown_event.set()
        
        # Stop components
        self.stop_stream()
        
        # Clean up window manager
        if self.window_manager:
            try:
                self.window_manager.destroy()
            except:
                pass
            self.window_manager = None
        
        print(f"✅ Shutdown complete")
    
    def _emergency_cleanup(self):
        """Emergency cleanup for atexit"""
        if self.running:
            self.shutdown()
    
    def run(self):
        """Main execution flow"""
        try:
            target_info = self._get_target_screen_info()
            
            print(f"\n{'='*80}")
            print(f"🚀 UNIFIED MULTI-SCREEN CLIENT (ENHANCED)")
            print(f"   Hostname: {self.hostname}")
            print(f"   Client ID: {self.client_id}")
            print(f"   Display Name: {self.display_name}")
            print(f"   Target Screen: {target_info['name']}")
            if 'warning' in target_info:
                print(f"   Warning: {target_info['warning']}")
            print(f"   Server: {self.server_url}")
            print(f"   Smart Player: {'Enabled' if not self.force_ffplay else 'Disabled (force ffplay)'}")
            print(f"   C++ Player: {'Available' if self.player_executable else 'Not found'}")
            print(f"   Auto-Install: Enabled (packages installed automatically)")
            print(f"{'='*80}")
            
            # Step 1: Register with server
            if not self.register():
                print(f"❌ Registration failed - exiting")
                return
            
            # Step 1.5: Create window manager for hotkeys
            self.create_window_manager()
            
            # Step 2: Main loop - wait for assignment and play streams
            while self.running and not self._shutdown_event.is_set():
                # Send periodic heartbeat to keep connection alive
                if hasattr(self, 'last_heartbeat') and (time.time() - self.last_heartbeat) > 30:
                    self.send_heartbeat()
                    self.last_heartbeat = time.time()
                elif not hasattr(self, 'last_heartbeat'):
                    self.last_heartbeat = time.time()
                
                # Wait for stream assignment
                if self.wait_for_assignment():
                    if self._shutdown_event.is_set():
                        break
                        
                    # Play the assigned stream
                    if self.play_stream():
                        # Monitor the player
                        stop_reason = self.monitor_player()
                        
                        if stop_reason == 'user_exit':
                            print(f"👋 User requested exit")
                            break
                        elif stop_reason == 'stream_changed':
                            print(f"🔄 Stream changed, restarting...")
                            continue
                        elif stop_reason in ['stream_ended', 'connection_lost', 'error']:
                            print(f"⏹️ Stream stopped ({stop_reason}), waiting for new assignment...")
                            self.current_stream_url = None
                            self.current_stream_version = None
                            self.current_player_type = None
                            continue
                        else:
                            print(f"❓ Unexpected stop reason: {stop_reason}")
                            break
                    else:
                        print(f"❌ Failed to start player, retrying in 10 seconds...")
                        if self._shutdown_event.wait(timeout=10):
                            break
                else:
                    print(f"❌ Assignment failed, retrying in 10 seconds...")
                    if self._shutdown_event.wait(timeout=10):
                        break
                        
        except Exception as e:
            print(f"💥 Fatal error: {e}")
            self.logger.error(f"Fatal error in main loop: {e}")
        finally:
            print(f"\n🏁 MULTI-SCREEN CLIENT SHUTDOWN")
            self.shutdown()

    def get_player_status(self) -> Dict[str, Any]:
        """Get the current status of the video player"""
        status = {
            'multithreading_enabled': False,  # Always single-threaded
            'target_screen': self.target_screen,
            'stream_url': self.current_stream_url,
            'stream_version': self.current_stream_version,
            'player_type': self.current_player_type,
            'running': self.running,
            'player_process': self.player_process.pid if self.player_process else None,
            'auto_install_enabled': True  # New feature indicator
        }
        
        return status


def main():
    """Main entry point for the enhanced multi-screen client"""
    # Setup logging first
    log_dir = Path.home() / "client_logs"
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "client.log"),
            logging.StreamHandler()
        ]
    )
    
    parser = argparse.ArgumentParser(
        prog='client.py',
        description="""
🚀 Enhanced Multi-Screen Client for Video Wall Systems

A simple and reliable client for multi-screen video streaming that supports
automatic player selection with target screen identification, optimized for
Raspberry Pi and single-threaded efficiency.

✨ NEW: Automatic package installation - no setup script needed!

Features:
   📦 Automatic Python package installation (requests, etc.)
   🔄 Automatic server registration with unique client identification
   🎯 Smart player selection (C++ player for SEI streams, ffplay fallback)
   📺 Target screen identification (1 or 2 for simple targeting)
   🧵 Single-threaded mode optimized for Raspberry Pi performance
   ⚡ Efficient resource usage with 1 thread per client
   🖥️ Uses system default display (DISPLAY=:0.0)
   🔁 Automatic reconnection and error recovery
   📊 Support for multiple instances (each in separate process)
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🎯 BASIC USAGE EXAMPLES:

  Standard usage:
    python3 client.py --server http://192.168.1.100:5000 \\
      --hostname rpi-client-1 --display-name "Monitor 1"

  Target specific screen:
    python3 client.py --server http://192.168.1.100:5000 \\
      --hostname rpi-client-1 --display-name "Screen1" \\
      --target-screen 1

    python3 client.py --server http://192.168.1.100:5000 \\
      --hostname rpi-client-2 --display-name "Screen2" \\
      --target-screen 2

  Target screen values:
    --target-screen 1         # Screen 1
    --target-screen 2         # Screen 2

📺 DUAL SCREEN SETUP (Recommended for Raspberry Pi):

  Terminal 1 (Screen 1):
    python3 client.py --server http://192.168.1.100:5000 \\
      --hostname rpi-client-1 --display-name "Screen1" \\
      --target-screen 1

  Terminal 2 (Screen 2):
    python3 client.py --server http://192.168.1.100:5000 \\
      --hostname rpi-client-2 --display-name "Screen2" \\
      --target-screen 2

  Note: Each client runs in its own process with 1 thread for optimal Pi performance

⚙️ ADVANCED OPTIONS:

  Force ffplay for all streams (disable smart selection):
    python3 client.py --server http://192.168.1.100:5000 \\
      --hostname client-1 --display-name "Screen 1" --force-ffplay

  Debug mode with detailed logging:
    python3 client.py --server http://192.168.1.100:5000 \\
      --hostname client-1 --display-name "Screen 1" --debug

📦 AUTOMATIC PACKAGE INSTALLATION:

  How it works:
  1. Client checks for required packages (requests, tkinter)
  2. If missing, automatically installs to local ./lib directory
  3. No global Python environment changes
  4. No virtual environments or complex setup needed
  5. Just run the client and it handles everything!

  Installation methods tried (in order):
  1. Install to local ./lib directory (--target)
  2. Install with --break-system-packages if needed
  3. Fallback to --user installation
  4. Graceful failure with helpful instructions

🧵 SINGLE-THREADED ARCHITECTURE:

  Raspberry Pi Optimization:
  - Each client uses exactly 1 main thread
  - Video playback happens in the main thread
  - Server communication is minimal and non-blocking
  - Perfect for single-core and multi-core Pi devices

  Benefits:
  - No context switching overhead between threads
  - Stable performance on limited hardware
  - Efficient resource usage
  - Simple and reliable operation

🔧 TROUBLESHOOTING:

  If automatic package installation fails:
    sudo apt-get install python3-requests python3-tk

  Check display configuration:
    xrandr --listmonitors

  Test with debug mode:
    python3 client.py --server http://YOUR_SERVER_IP:5000 \\
      --hostname test-client --display-name "Test" \\
      --target-screen 1 --debug

For more information, visit: https://github.com/your-repo/openvideowalls
        """
    )
    
    # Required arguments group
    required_group = parser.add_argument_group('🔧 Required Arguments')
    required_group.add_argument('--server', 
                               required=True,
                               metavar='URL',
                               help='Server URL - Example: http://192.168.1.100:5000')
    required_group.add_argument('--hostname', 
                               required=True,
                               metavar='NAME',
                               help='Client hostname - Example: rpi-client-1')
    required_group.add_argument('--display-name', 
                               required=True,
                               metavar='NAME',
                               help='Display name for admin interface - Example: "Monitor 1"')
    
    # Optional arguments group
    optional_group = parser.add_argument_group('⚙️ Optional Arguments')
    optional_group.add_argument('--target-screen', 
                               metavar='SCREEN',
                               help='Target screen (1 or 2)')
    optional_group.add_argument('--force-ffplay', 
                               action='store_true',
                               help='Force use of ffplay for all streams (disable smart C++/ffplay selection)')

    optional_group.add_argument('--debug', 
                               action='store_true',
                               help='Enable debug logging (includes SEI detection details and auto-install info)')

    optional_group.add_argument('--version', 
                               action='version', 
                               version='🚀 Enhanced Multi-Screen Client v4.0 (Auto-Install Edition)')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Validate server URL
    if not args.server.startswith(('http://', 'https://')):
        print("❌ Error: Server URL must start with http:// or https://")
        print("   Example: --server http://192.168.1.100:5000")
        print("   Example: --server https://videowall.example.com:5000")
        sys.exit(1)
    
    # Validate hostname (basic check)
    if not args.hostname.strip():
        print("❌ Error: Hostname cannot be empty")
        print("   Example: --hostname rpi-client-1")
        sys.exit(1)
    
    # Validate display name (basic check)
    if not args.display_name.strip():
        print("❌ Error: Display name cannot be empty")
        print("   Example: --display-name \"Monitor 1\"")
        sys.exit(1)
    
    # Configure logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        print("🐛 Debug logging enabled")
    
    # Show target screen info if specified
    if args.target_screen:
        print(f"🎯 Target screen specified: '{args.target_screen}'")
    
    # Create and run client
    try:
        print("🚀 Starting Enhanced Multi-Screen Client (Auto-Install Edition)...")
        print("📦 Python packages will be installed automatically if needed")
        print("🛑 Press Ctrl+C to stop gracefully")
        print()
        
        client = UnifiedMultiScreenClient(
            server_url=args.server,
            hostname=args.hostname,
            display_name=args.display_name,
            force_ffplay=args.force_ffplay,
            target_screen=args.target_screen
        )
        
        client.run()
        
    except KeyboardInterrupt:
        print("\n🛑 Keyboard interrupt received")
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        logging.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
