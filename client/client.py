#!/usr/bin/env python3
"""
Unified Multi-Screen Client for Video Wall Systems
Simple, reliable client for multi-screen video streaming
"""
import argparse
import requests
import time
import logging
import subprocess
import sys
import os
import json
import signal
import atexit
import threading
import socket
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlparse
from pathlib import Path
import tkinter as tk
from tkinter import messagebox


class UnifiedMultiScreenClient:
    """
    Unified Multi-Screen Client for Video Wall Systems
    Simple and reliable client for multi-screen video streaming
    """
    
    def __init__(self, server_url: str, hostname: str = None, display_name: str = None, 
                 force_ffplay: bool = False):
        """
        Initialize the multi-screen client
        
        Args:
            server_url: Server URL (e.g., "http://192.168.1.100:5000")
            hostname: Unique client identifier
            display_name: Friendly display name
            force_ffplay: Force use of ffplay instead of smart selection
        """
        self.server_url = server_url.rstrip('/')
        self.hostname = hostname or socket.gethostname()
        self.display_name = display_name or f"Display-{self.hostname}"
        self.force_ffplay = force_ffplay
        
        # Window management
        self.window_manager = None
        self.current_monitor = 0
        self.monitor_positions = [
            (0, 0),      # Monitor 1 (left)
            (1920, 0),   # Monitor 2 (right)
            (3840, 0),   # Monitor 3 (if available)
            (0, 1080),   # Monitor 4 (bottom-left)
        ]
        
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
        
                # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        self.logger = logging.getLogger(__name__)
        
        # Setup signal handlers and cleanup
        self._setup_signal_handlers()
        atexit.register(self._emergency_cleanup)
        
        # Find player executable
        self.player_executable = self._find_player_executable()
    
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
            self.window_manager = tk.Tk()
            self.window_manager.withdraw()  # Hide the window
            self.window_manager.title("Multi-Screen Client Window Manager")
            
            # Bind hotkeys
            self.window_manager.bind('<Control-m>', self.move_to_next_monitor)
            self.window_manager.bind('<Control-Left>', self.move_to_previous_monitor)
            self.window_manager.bind('<Control-Right>', self.move_to_next_monitor)
            self.window_manager.bind('<Control-1>', lambda e: self.move_to_monitor(0))
            self.window_manager.bind('<Control-2>', lambda e: self.move_to_monitor(1))
            self.window_manager.bind('<Control-3>', lambda e: self.move_to_monitor(2))
            self.window_manager.bind('<Control-4>', lambda e: self.move_to_monitor(3))
            self.window_manager.bind('<Control-h>', self.show_help)
            
            # Make window always on top and focusable
            self.window_manager.attributes('-topmost', True)
            self.window_manager.focus_force()
            
            print(f"🎮 Window Manager Started")
            print(f"   Hotkeys:")
            print(f"     Ctrl+M or Ctrl+Right: Move to next monitor")
            print(f"     Ctrl+Left: Move to previous monitor")
            print(f"     Ctrl+1-4: Move to specific monitor")
            print(f"     Ctrl+H: Show help")
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to create window manager: {e}")
            return False
    
    def move_to_monitor(self, monitor_index: int):
        """Move the fullscreen window to a specific monitor"""
        if not self.player_process or self.player_process.poll() is not None:
            return
        
        if monitor_index >= len(self.monitor_positions):
            print(f"❌ Monitor {monitor_index + 1} not available")
            return
        
        x, y = self.monitor_positions[monitor_index]
        self.current_monitor = monitor_index
        
        try:
            # Use wmctrl to move the window (works with Wayland/XWayland)
            window_title = f"Multi-Screen Client - {self.display_name}"
            
            # Find the window by title
            result = subprocess.run(['wmctrl', '-l'], capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if window_title in line:
                        window_id = line.split()[0]
                        # Move window to new position
                        subprocess.run(['wmctrl', '-ir', window_id, '-e', f'0,{x},{y},-1,-1'])
                        print(f"🖥️  Moved to Monitor {monitor_index + 1} (x={x}, y={y})")
                        return
            
            # Fallback: try xdotool if wmctrl doesn't work
            subprocess.run(['xdotool', 'search', '--name', window_title, 'windowmove', str(x), str(y)])
            print(f"🖥️  Moved to Monitor {monitor_index + 1} (x={x}, y={y})")
            
        except FileNotFoundError:
            print(f"❌ Window management tools not found. Install with:")
            print(f"   sudo apt install wmctrl xdotool")
        except Exception as e:
            self.logger.error(f"Failed to move window: {e}")
    
    def move_to_next_monitor(self, event=None):
        """Move to the next monitor"""
        next_monitor = (self.current_monitor + 1) % len(self.monitor_positions)
        self.move_to_monitor(next_monitor)
    
    def move_to_previous_monitor(self, event=None):
        """Move to the previous monitor"""
        prev_monitor = (self.current_monitor - 1) % len(self.monitor_positions)
        self.move_to_monitor(prev_monitor)
    
    def show_help(self, event=None):
        """Show hotkey help"""
        help_text = """
🎮 Multi-Screen Client Hotkeys:

Ctrl+M or Ctrl+Right: Move to next monitor
Ctrl+Left: Move to previous monitor
Ctrl+1: Move to Monitor 1 (left)
Ctrl+2: Move to Monitor 2 (right)
Ctrl+3: Move to Monitor 3 (if available)
Ctrl+4: Move to Monitor 4 (bottom-left)
Ctrl+H: Show this help

Note: Make sure the client window has focus for hotkeys to work.
        """
        messagebox.showinfo("Multi-Screen Client Help", help_text)
    

    
    def detect_sei_in_stream(self, stream_url: str, timeout: int = 10) -> bool:
        """
        Detect if the stream contains SEI metadata by analyzing the first few seconds
        """
        try:
            print(f" Analyzing stream for SEI metadata...")
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
                            print(f" SEI metadata detected (pattern: {pattern[:16]}...)")
                            return True
                    
                    # Alternative: Check stderr for SEI-related messages
                    if stderr:
                        sei_indicators = ["sei", "user_data", "h264_metadata"]
                        for indicator in sei_indicators:
                            if indicator.lower() in stderr.lower():
                                print(f" SEI indicators found in stream analysis")
                                return True
                    
                    print(f" No SEI metadata detected - standard stream")
                    return False
                else:
                    print(f"  Could not analyze stream data")
                    return False
                    
            except subprocess.TimeoutExpired:
                print(f"  Stream analysis timeout - assuming no SEI")
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
            return "ffplay", "Forced ffplay mode (--force-ffplay)"
        
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
            print(f"\n{'='*80}")
            print(f" STARTING MULTI-SCREEN CLIENT REGISTRATION")
            print(f"   Client: {self.hostname}")
            print(f"   Local IP: {self._get_local_ip_address()}")
            print(f"   Client ID: {self.client_id}")
            print(f"   Display Name: {self.display_name}")
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
                "platform": f"multiscreen_{player_type}"  # Indicate multi-screen capability
            }
            
            print(f"\n Sending registration request...")
            request_sent_time = time.time()
            
            # Try new registration endpoint first, fallback to legacy
            try:
                print(f" Trying new endpoint: {self.server_url}/api/clients/register")
                print(f" Registration data: {json.dumps(registration_data, indent=2)}")
                response = requests.post(
                    f"{self.server_url}/api/clients/register",
                    json=registration_data,
                    timeout=10
                )
                endpoint_used = "new (/api/clients/register)"
                print(f" New endpoint succeeded with status: {response.status_code}")
            except requests.exceptions.RequestException as e:
                # Fallback to legacy endpoint (simplified data)
                print(f" New endpoint failed with RequestException: {e}")
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
                print(f" New endpoint failed with unexpected error: {e}")
                print(f" Error type: {type(e).__name__}")
                import traceback
                print(f" Traceback: {traceback.format_exc()}")
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
            
            print(f" Response received in {network_delay_ms:.1f}ms using {endpoint_used}")
            
            if response.status_code in [200, 202]:
                result = response.json()
                if result.get("success", True):  # Legacy endpoint doesn't have 'success' field
                    registration_end = time.time()
                    total_time_ms = (registration_end - registration_start) * 1000
                    
                    print(f"\n REGISTRATION SUCCESSFUL!")
                    print(f"   Client ID: {result.get('client_id', self.client_id)}")
                    print(f"   Status: {result.get('status', 'registered')}")
                    if 'server_time' in result:
                        print(f"   Server Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(result['server_time']))}")
                    print(f"   Total Registration Time: {total_time_ms:.1f}ms")
                    
                    self.registered = True
                    self.assignment_status = result.get('status', 'waiting_for_assignment')
                    self._server_client_id = result.get('client_id') # Store server-assigned ID
                    
                    # Show next steps
                    next_steps = result.get('next_steps', [
                        "Wait for admin to assign you to a group",
                        "Admin will use the web interface to make assignments",
                        "Client will automatically start playing when streaming begins"
                    ])
                    print(f"\n Next Steps:")
                    for step in next_steps:
                        print(f"    {step}")
                    
                    print(f"{'='*80}")
                    return True
                else:
                    print(f" Registration failed: {result.get('error', 'Unknown error')}")
                    return False
            else:
                print(f" Registration failed with HTTP status {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f" Registration error: {e}")
            self.logger.error(f"Registration error: {e}")
            return False
    
    def wait_for_assignment(self) -> bool:
        """Wait for admin to assign this client to a group and stream"""
        retry_count = 0
        
        print(f"\n Waiting for assignment from admin...")
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
                    
                    print(f"\n ASSIGNMENT COMPLETE!")
                    print(f"   Group: {group_name}")
                    print(f"   Stream: {stream_assignment}")
                    print(f"   Assignment Type: {data.get('assignment_status', 'unknown')}")
                    if data.get('screen_number') is not None:
                        print(f"   Screen Number: {data.get('screen_number')}")
                    print(f"   Stream URL: {self.current_stream_url}")
                    print(f"   Stream Version: {self.current_stream_version}")
                    return True
                
                elif status in ["waiting_for_group_assignment", "waiting_for_stream_assignment"]:
                    print(f" {message}")
                    retry_count = 0  # Don't count as failure
                
                elif status == "waiting_for_streaming":
                    group_name = data.get('group_name', 'unknown')
                    stream_assignment = data.get('stream_assignment', 'unknown')
                    print(f" {message}")
                    print(f"   Assigned to: {group_name}/{stream_assignment}")
                    print(f"   Waiting for admin to start streaming...")
                    retry_count = 0
                
                elif status == "group_not_found":
                    # The group might exist but Docker discovery is failing
                    # Keep waiting instead of giving up
                    group_id = data.get('group_id')
                    if retry_count % 6 == 0:
                        print(f"  Group validation failed, but continuing (Docker discovery issue)")
                        print(f"   Group ID: {group_id}")
                        print(f"   Will retry...")
                    # Don't print error every time
                    retry_count += 1
                    # Continue waiting instead of returning error
                
                elif status == "not_registered":
                    print(f" {message}")
                    print(f"   Client may have been removed from server")
                    return False
                
                else:
                    print(f"  Unexpected status: {status} - {message}")
                    retry_count += 1
                
                # Interruptible sleep
                if self._shutdown_event.wait(timeout=self.retry_interval):
                    print(f"   Shutdown requested during wait")
                    return False
                
            except Exception as e:
                print(f"  Network error ({retry_count + 1}/{self.max_retries}): {e}")
                retry_count += 1
                if self._shutdown_event.wait(timeout=self.retry_interval * 2):
                    print(f"   Shutdown requested during error wait")
                    return False
        
        if retry_count >= self.max_retries:
            print(f" Max retries reached, giving up")
            return False
        
        return False
    
    def fix_stream_url(self, stream_url: str) -> str:
        """Fix stream URL to use server IP instead of localhost"""
        if not stream_url:
            return stream_url
            
        if "127.0.0.1" in stream_url:
            fixed_url = stream_url.replace("127.0.0.1", self.server_ip)
            self.logger.info(f"Fixed stream URL: 127.0.0.1  {self.server_ip}")
            return fixed_url
        elif "localhost" in stream_url:
            fixed_url = stream_url.replace("localhost", self.server_ip)
            self.logger.info(f"Fixed stream URL: localhost  {self.server_ip}")
            return fixed_url
        else:
            return stream_url
    
    def play_stream(self) -> bool:
        """Start playing the assigned stream with optimal player selection"""
        if not self.current_stream_url:
            self.logger.error("No stream URL available")
            return False
            
        try:
            self.stop_stream()  # Clean up any existing player
            
            # Choose the optimal player for this stream
            player_type, reason = self.choose_optimal_player(self.current_stream_url)
            self.current_player_type = player_type
            
            print(f"\n SMART PLAYER SELECTION")
            print(f"   Selected: {player_type.upper()}")
            print(f"   Reason: {reason}")
            print(f"   Stream URL: {self.current_stream_url}")
            
            if player_type == "cpp_player":
                return self._play_with_cpp_player()
            else:
                return self._play_with_ffplay()
                    
        except Exception as e:
            self.logger.error(f"Player error: {e}")
            return False
    
    def _play_with_cpp_player(self) -> bool:
        """Start playing with the built C++ player (for SEI streams)"""
        try:
            print(f"\n STARTING C++ PLAYER (SEI MODE)")
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
                                self.logger.info(f" SEI: {line_clean}")
                            elif "TELEMETRY:" in line_clean:
                                self.logger.info(f" {line_clean}")
                            elif "ERROR" in line_clean.upper():
                                self.logger.error(f" {line_clean}")
                            elif "WARNING" in line_clean.upper():
                                self.logger.warning(f" {line_clean}")
                            else:
                                self.logger.debug(f" {line_clean}")
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
            print(f"\n STARTING FFPLAY (STANDARD MODE)")
            print(f"   Stream URL: {self.current_stream_url}")
            print(f"   Stream Version: {self.current_stream_version}")
            print(f"   Capability: Standard video playback")
            
            cmd = [
                "ffplay",
                "-fflags", "nobuffer",
                "-flags", "low_delay", 
                "-framedrop",
                "-strict", "experimental",
                "-window_title", f"Multi-Screen Client - {self.display_name}",
                "-fs",  # Fullscreen
                "-autoexit",
                "-loglevel", "warning",  # Reduce ffplay verbosity
                self.current_stream_url
            ]
            
            self.player_process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Monitor ffplay output (less verbose than C++ player)
            def monitor_ffplay_output():
                try:
                    for line in iter(self.player_process.stderr.readline, ''):
                        if line.strip():
                            line_clean = line.strip()
                            if "error" in line_clean.lower():
                                self.logger.error(f" {line_clean}")
                            elif "warning" in line_clean.lower():
                                self.logger.warning(f" {line_clean}")
                            else:
                                self.logger.debug(f" {line_clean}")
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
    
    def monitor_player(self) -> str:
        """Monitor the player process and check for stream changes"""
        if not self.player_process:
            return 'error'
        
        # Determine current player type for display
        player_display_name = "C++ Player" if self.current_player_type == "cpp_player" else "ffplay"
        
        print(f"\n MONITORING {player_display_name.upper()}")
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
                except tk.TclError:
                    # Window manager closed
                    break
            
            # Check for stream changes
            if current_time - last_stream_check >= stream_check_interval:
                if self._check_for_stream_change():
                    print(f" Stream change detected, will restart with optimal player...")
                    self.stop_stream()
                    return 'stream_changed'
                last_stream_check = current_time
            
            # Periodic health report
            if current_time - last_health_report >= health_report_interval:
                print(f" {player_display_name} health: PID={self.player_process.pid}, "
                      f"Running {int(current_time - last_health_report)}s")
                last_health_report = current_time
            
            # Check for shutdown
            if self._shutdown_event.wait(timeout=1):
                print(f" Shutdown requested during monitoring")
                self.stop_stream()
                return 'user_exit'
        
        # Player has stopped
        if self._shutdown_event.is_set() or not self.running:
            return 'user_exit'
        
        exit_code = self.player_process.returncode if self.player_process else -1
        
        if exit_code == 0:
            print(f" {player_display_name} ended normally")
            return 'stream_ended'
        elif exit_code == 1:
            print(f"  {player_display_name} connection lost or stream unavailable")
            return 'connection_lost'
        else:
            print(f" {player_display_name} exited with error code: {exit_code}")
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
                            self.logger.info(f"  URL: {self.current_stream_url}  {new_stream_url}")
                        if version_changed:
                            self.logger.info(f"  Version: {self.current_stream_version}  {new_stream_version}")
                        
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
        if self.player_process:
            try:
                pid = self.player_process.pid
                player_name = "C++ Player" if self.current_player_type == "cpp_player" else "ffplay"
                print(f" Stopping {player_name} (PID: {pid})")
                
                # Graceful termination
                self.player_process.terminate()
                
                try:
                    self.player_process.wait(timeout=3)
                    print(f" {player_name} stopped gracefully")
                except subprocess.TimeoutExpired:
                    print(f"  Force killing {player_name}")
                    self.player_process.kill()
                    
                    try:
                        self.player_process.wait(timeout=2)
                        print(f" {player_name} force-killed")
                    except subprocess.TimeoutExpired:
                        print(f" {player_name} unresponsive")
                        try:
                            os.kill(pid, signal.SIGKILL)
                        except (OSError, ProcessLookupError):
                            pass
                
            except (OSError, ProcessLookupError):
                print(f" Player process already terminated")
            except Exception as e:
                self.logger.error(f"Error stopping player: {e}")
            finally:
                self.player_process = None
                self.current_player_type = None
    
    def shutdown(self):
        """Initiate graceful shutdown"""
        if not self.running:
            return
        
        print(f"\n INITIATING GRACEFUL SHUTDOWN")
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
        
        print(f" Shutdown complete")
    
    def _emergency_cleanup(self):
        """Emergency cleanup for atexit"""
        if self.running:
            self.shutdown()
    
    def run(self):
        """Main execution flow"""
        try:
            print(f"\n{'='*80}")
            print(f" UNIFIED MULTI-SCREEN CLIENT")
            print(f"   Hostname: {self.hostname}")
            print(f"   Client ID: {self.client_id}")
            print(f"   Display Name: {self.display_name}")
            print(f"   Server: {self.server_url}")
            print(f"   Smart Player: {'Enabled' if not self.force_ffplay else 'Disabled (force ffplay)'}")
            print(f"   C++ Player: {'Available' if self.player_executable else 'Not found'}")
            print(f"{'='*80}")
            
            # Step 1: Register with server
            if not self.register():
                print(f" Registration failed - exiting")
                return
            
            # Step 1.5: Create window manager for hotkeys
            self.create_window_manager()
            
            # Step 2: Main loop - wait for assignment and play streams
            while self.running and not self._shutdown_event.is_set():
                # Wait for stream assignment
                if self.wait_for_assignment():
                    if self._shutdown_event.is_set():
                        break
                        
                    # Play the assigned stream
                    if self.play_stream():
                        # Monitor the player
                        stop_reason = self.monitor_player()
                        
                        if stop_reason == 'user_exit':
                            print(f" User requested exit")
                            break
                        elif stop_reason == 'stream_changed':
                            print(f" Stream changed, restarting...")
                            continue
                        elif stop_reason in ['stream_ended', 'connection_lost', 'error']:
                            print(f" Stream stopped ({stop_reason}), waiting for new assignment...")
                            self.current_stream_url = None
                            self.current_stream_version = None
                            self.current_player_type = None
                            continue
                        else:
                            print(f"  Unexpected stop reason: {stop_reason}")
                            break
                    else:
                        print(f" Failed to start player, retrying in 10 seconds...")
                        if self._shutdown_event.wait(timeout=10):
                            break
                else:
                    print(f" Assignment failed, retrying in 10 seconds...")
                    if self._shutdown_event.wait(timeout=10):
                        break
                        
        except Exception as e:
            print(f" Fatal error: {e}")
            self.logger.error(f"Fatal error in main loop: {e}")
        finally:
            print(f"\n MULTI-SCREEN CLIENT SHUTDOWN")
            self.shutdown()


def main():
    """Main entry point for the multi-screen client"""
    parser = argparse.ArgumentParser(
        prog='client.py',
        description="""
 Unified Multi-Screen Client for Video Wall Systems

A simple and reliable client for multi-screen video streaming that supports
automatic player selection with movable fullscreen windows.

Features:
   Automatic server registration with unique client identification
   Smart player selection (C++ player for SEI streams, ffplay fallback)
   Movable fullscreen windows with hotkeys
   Uses system default display (DISPLAY=:0.0)
   Automatic reconnection and error recovery
   Support for multiple instances on the same device
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
 BASIC USAGE EXAMPLES:

  Standard usage:
    python3 client.py --server http://192.168.1.100:5000 \\
      --hostname rpi-client-1 --display-name "Monitor 1"

  Multiple clients on same device:
    # Client 1:
    python3 client.py --server http://192.168.1.100:5000 \\
      --hostname rpi-client-1 --display-name "Client 1"

    # Client 2:
    python3 client.py --server http://192.168.1.100:5000 \\
      --hostname rpi-client-2 --display-name "Client 2"

  Note: Uses system default display (DISPLAY=:0.0)

  ADVANCED OPTIONS:

  Force ffplay for all streams (disable smart selection):
    python3 client.py --server http://192.168.1.100:5000 \\
      --hostname client-1 --display-name "Screen 1" --force-ffplay

  Multi-monitor setup with hotkeys:
    # Start client (will appear on first monitor)
    DISPLAY=:0 python3 client.py --server http://192.168.1.100:5000 \\
      --hostname client-1 --display-name "Monitor 1" &
    
    # Use hotkeys to move between monitors:
    # Ctrl+M or Ctrl+Right: Next monitor
    # Ctrl+Left: Previous monitor
    # Ctrl+1-4: Specific monitor

  Debug mode with detailed logging:
    python3 client.py --server http://192.168.1.100:5000 \\
      --hostname client-1 --display-name "Screen 1" --debug

 DEPLOYMENT EXAMPLES:

  Systemd service for Client 1:
    ExecStart=/usr/bin/python3 client.py \\
      --server http://192.168.1.100:5000 \\
      --hostname rpi-client-1 \\
      --display-name "Client 1"

  Systemd service for Client 2:
    ExecStart=/usr/bin/python3 client.py \\
      --server http://192.168.1.100:5000 \\
      --hostname rpi-client-2 \\
      --display-name "Client 2"

 SETUP PROCESS:

  1. Ensure ffmpeg/ffplay is installed:
     sudo apt install ffmpeg

  2. Start client:
     python3 client.py --server http://YOUR_SERVER_IP:5000 \\
       --hostname client-1 --display-name "Screen 1"

  3. Use web interface to assign clients to groups and start streaming



 TROUBLESHOOTING:

  Check display configuration:
    xrandr --listmonitors

  Test display:
    xeyes &

  View client logs:
    python3 client.py --server http://YOUR_SERVER_IP:5000 \\
      --hostname client-1 --display-name "Screen 1" --debug

For more information, visit: https://github.com/your-repo/openvideowalls
        """
    )
    
    # Required arguments group
    required_group = parser.add_argument_group(' Required Arguments')
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
    optional_group = parser.add_argument_group('  Optional Arguments')
    optional_group.add_argument('--force-ffplay', 
                               action='store_true',
                               help='Force use of ffplay for all streams (disable smart C++/ffplay selection)')

    optional_group.add_argument('--debug', 
                               action='store_true',
                               help='Enable debug logging (includes SEI detection details)')

    optional_group.add_argument('--version', 
                               action='version', 
                               version=' Unified Multi-Screen Client v3.0')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Validate server URL
    if not args.server.startswith(('http://', 'https://')):
        print(" Error: Server URL must start with http:// or https://")
        print("   Example: --server http://192.168.1.100:5000")
        print("   Example: --server https://videowall.example.com:5000")
        sys.exit(1)
    

    
    # Validate hostname (basic check)
    if not args.hostname.strip():
        print(" Error: Hostname cannot be empty")
        print("   Example: --hostname rpi-client-1")
        sys.exit(1)
    
    # Validate display name (basic check)
    if not args.display_name.strip():
        print(" Error: Display name cannot be empty")
        print("   Example: --display-name \"Monitor 1\"")
        sys.exit(1)
    
    # Configure logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        print(" Debug logging enabled")
    
    # Create and run client
    try:
        client = UnifiedMultiScreenClient(
            server_url=args.server,
            hostname=args.hostname,
            display_name=args.display_name,
            force_ffplay=args.force_ffplay
        )
        
        print(" Starting Unified Multi-Screen Client...")
        print("   Press Ctrl+C to stop gracefully")
        
        client.run()
        
    except KeyboardInterrupt:
        print("\n  Keyboard interrupt received")
    except Exception as e:
        print(f"\n Fatal error: {e}")
        logging.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()