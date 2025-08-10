#!/usr/bin/env python3
"""
Unified Multi-Screen Client with Smart Player Selection
Complete client implementation with integrated time sync, registration, video playback,
and automatic SEI detection for optimal player selection
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
import struct
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlparse
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

class ClientTimeService:
    """Time synchronization service for the client"""
    
    def __init__(self, port=8080):
        self.port = port
        self.server = None
        self.server_thread = None
        self.running = False
    
    def start(self):
        """Start the time service"""
        if self.running:
            return
        
        try:
            self.server = HTTPServer(('0.0.0.0', self.port), TimeServiceHandler)
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            self.running = True
            logging.info(f"🕒 Client time service started on port {self.port}")
        except Exception as e:
            logging.warning(f"Could not start time service on port {self.port}: {e}")
            self.running = False
    
    def stop(self):
        """Stop the time service"""
        if self.running and self.server:
            try:
                self.server.shutdown()
                self.server.server_close()
                self.running = False
                logging.info("🕒 Client time service stopped")
            except Exception as e:
                logging.error(f"Error stopping time service: {e}")
    
    def is_running(self):
        return self.running

class TimeServiceHandler(BaseHTTPRequestHandler):
    """HTTP handler for client time service"""
    
    def do_GET(self):
        """Handle GET requests for time information"""
        try:
            if self.path == '/api/time':
                self.handle_time_request()
            elif self.path == '/api/sync-status':
                self.handle_sync_status_request()
            elif self.path == '/api/health':
                self.handle_health_request()
            else:
                self.send_error(404, "Endpoint not found")
        except Exception as e:
            logging.error(f"Error handling time request: {e}")
            self.send_error(500, f"Internal server error: {str(e)}")
    
    def handle_time_request(self):
        """Return current system time with detailed logging"""
        request_received_time = time.time()
        current_time = time.time()
        
        # Print detailed timing information
        print(f"\n🟦 CLIENT TIME REQUEST RECEIVED")
        print(f"📊 Request Time: {time.strftime('%Y-%m-%d %H:%M:%S.%f', time.gmtime(request_received_time))[:-3]} UTC")
        print(f"📊 Response Time: {time.strftime('%Y-%m-%d %H:%M:%S.%f', time.gmtime(current_time))[:-3]} UTC")
        print(f"📊 Processing Delay: {(current_time - request_received_time) * 1000:.3f} ms")
        print(f"📊 Timestamp: {current_time:.6f}")
        
        response_data = {
            "timestamp": current_time,
            "timestamp_ms": current_time * 1000,
            "iso_time": time.strftime("%Y-%m-%dT%H:%M:%S.%fZ", time.gmtime(current_time)),
            "local_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(current_time)),
            "timezone": time.tzname[0],
            "source": "system_clock",
            "request_received": request_received_time,
            "processing_time_ms": (current_time - request_received_time) * 1000
        }
        
        print(f"✅ Sending time response to server")
        print(f"-" * 50)
        
        self.send_json_response(response_data)
    
    def handle_sync_status_request(self):
        """Return NTP/chrony synchronization status"""
        try:
            sync_status = self.get_chrony_status()
            self.send_json_response(sync_status)
        except Exception as e:
            error_response = {
                "error": f"Failed to get sync status: {str(e)}",
                "synchronized": False,
                "method": "error"
            }
            self.send_json_response(error_response, status_code=500)
    
    def handle_health_request(self):
        """Return client health status"""
        health_data = {
            "status": "healthy",
            "timestamp": time.time(),
            "uptime": self.get_system_uptime(),
            "load_average": self.get_load_average()
        }
        self.send_json_response(health_data)
    
    def get_chrony_status(self):
        """Get chrony synchronization status"""
        try:
            result = subprocess.run(['chronyc', 'tracking'], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                tracking_info = self.parse_chrony_tracking(result.stdout)
                return {
                    "synchronized": True,
                    "method": "chrony",
                    "tracking": tracking_info,
                    "timestamp": time.time()
                }
            else:
                return {
                    "synchronized": False,
                    "error": "chronyc command failed",
                    "method": "chrony",
                    "timestamp": time.time()
                }
        except subprocess.TimeoutExpired:
            return {"synchronized": False, "error": "chronyc timeout", "method": "chrony"}
        except FileNotFoundError:
            return {"synchronized": False, "error": "chrony not installed", "method": "chrony"}
        except Exception as e:
            return {"synchronized": False, "error": str(e), "method": "chrony"}
    
    def parse_chrony_tracking(self, output):
        """Parse chronyc tracking output"""
        tracking = {}
        for line in output.split('\n'):
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()
                
                if 'offset' in key and 'ms' in value:
                    try:
                        tracking[key] = float(value.replace('ms', '').strip())
                        tracking[f"{key}_unit"] = "ms"
                    except ValueError:
                        tracking[key] = value
                elif 'stratum' in key:
                    try:
                        tracking[key] = int(value)
                    except ValueError:
                        tracking[key] = value
                else:
                    tracking[key] = value
        return tracking
    
    def get_system_uptime(self):
        """Get system uptime in seconds"""
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
            return uptime_seconds
        except Exception:
            return None
    
    def get_load_average(self):
        """Get system load average"""
        try:
            with open('/proc/loadavg', 'r') as f:
                load_data = f.readline().split()
            return {
                "1min": float(load_data[0]),
                "5min": float(load_data[1]),
                "15min": float(load_data[2])
            }
        except Exception:
            return None
    
    def send_json_response(self, data, status_code=200):
        """Send JSON response"""
        response_json = json.dumps(data, indent=2)
        
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_json)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        self.wfile.write(response_json.encode('utf-8'))
    
    def log_message(self, format, *args):
        """Override to use our logger"""
        logging.debug(f"{self.client_address[0]} - {format % args}")

class UnifiedMultiScreenClient:
    """
    Unified Multi-Screen Client with Smart Player Selection
    Complete client implementation with time sync, registration, video playback,
    and automatic SEI detection for optimal player selection
    """
    
    def __init__(self, server_url: str, hostname: str = None, display_name: str = None, 
                 force_ffplay: bool = False, enforce_time_sync: bool = True):
        """
        Initialize the unified client
        
        Args:
            server_url: Server URL (e.g., "http://192.168.1.100:5000")
            hostname: Unique client identifier
            display_name: Friendly display name
            force_ffplay: Force use of ffplay instead of smart selection
            enforce_time_sync: Enable time synchronization validation
        """
        self.server_url = server_url.rstrip('/')
        self.hostname = hostname or socket.gethostname()
        self.display_name = display_name or f"Display-{self.hostname}"
        self.force_ffplay = force_ffplay
        self.enforce_time_sync = enforce_time_sync
        
        # Stream management
        self.current_stream_url = None
        self.current_stream_version = None
        self.current_player_type = None
        self.player_process = None
        self.running = True
        self.retry_interval = 5
        self.max_retries = 60
        self._shutdown_event = threading.Event()
        
        # Time synchronization
        self.time_service = ClientTimeService(port=8080)
        self.registered = False
        self.assignment_status = "waiting_for_assignment"
        
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
    
    def detect_sei_in_stream(self, stream_url: str, timeout: int = 10) -> bool:
        """
        Detect if the stream contains SEI metadata by analyzing the first few seconds
        
        Args:
            stream_url: SRT stream URL to analyze
            timeout: Maximum time to spend analyzing (seconds)
            
        Returns:
            bool: True if SEI metadata detected, False otherwise
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
                    # SEI user data typically contains recognizable patterns
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
                    
                    print(f"📺 No SEI metadata detected - standard stream")
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
        """
        Choose the optimal player based on stream characteristics
        
        Args:
            stream_url: SRT stream URL to play
            
        Returns:
            Tuple[str, str]: (player_type, reason)
                player_type: "cpp_player" or "ffplay"
                reason: Human-readable explanation
        """
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
    
    def start_time_service(self):
        """Start the client time service"""
        if self.enforce_time_sync:
            self.time_service.start()
            # Give the service a moment to start
            time.sleep(0.5)
    
    def stop_time_service(self):
        """Stop the client time service"""
        self.time_service.stop()
    
    def register(self) -> bool:
        """Register client with server including time sync validation"""
        try:
            print(f"\n{'='*80}")
            print(f"🚀 STARTING UNIFIED CLIENT REGISTRATION")
            print(f"   Client: {self.hostname}")
            print(f"   Display Name: {self.display_name}")
            print(f"   Server: {self.server_url}")
            print(f"   Server IP: {self.server_ip}")
            print(f"   Time Sync: {'Enabled' if self.enforce_time_sync else 'Disabled'}")
            print(f"   Smart Player: {'Enabled' if not self.force_ffplay else 'Disabled (force ffplay)'}")
            
            # Start time service if time sync is enabled
            if self.enforce_time_sync:
                self.start_time_service()
                if self.time_service.is_running():
                    print(f"   Time Service: Running on port {self.time_service.port}")
                else:
                    print(f"   Time Service: Failed to start (will use fallback)")
            
            registration_start = time.time()
            registration_start_formatted = time.strftime("%Y-%m-%d %H:%M:%S.%f", time.gmtime(registration_start))[:-3]
            print(f"   Start Time: {registration_start_formatted} UTC")
            print(f"{'='*80}")
            
            # Create short platform string (max 32 chars)
            if self.force_ffplay:
                player_type = "ffplay_only"
            elif not self.player_executable:
                player_type = "ffplay_fb"  # fallback
            else:
                player_type = "smart_sel"  # smart selection
            
            registration_data = {
                "hostname": self.hostname,
                "display_name": self.display_name,
                "platform": f"unified_{player_type}",  # Max 18 chars
                "enforce_time_sync": self.enforce_time_sync
            }
            
            print(f"\n📡 Sending registration request...")
            request_sent_time = time.time()
            
            # Try new registration endpoint first, fallback to legacy
            try:
                response = requests.post(
                    f"{self.server_url}/api/clients/register",
                    json=registration_data,
                    timeout=10
                )
                endpoint_used = "new (/api/clients/register)"
            except requests.exceptions.RequestException:
                # Fallback to legacy endpoint
                self.logger.info("New endpoint failed, trying legacy endpoint...")
                response = requests.post(
                    f"{self.server_url}/register_client",
                    json=registration_data,
                    timeout=10
                )
                endpoint_used = "legacy (/register_client)"
            
            response_received_time = time.time()
            network_delay_ms = (response_received_time - request_sent_time) * 1000
            
            print(f"📡 Response received in {network_delay_ms:.1f}ms using {endpoint_used}")
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success", True):  # Legacy endpoint doesn't have 'success' field
                    registration_end = time.time()
                    total_time_ms = (registration_end - registration_start) * 1000
                    
                    print(f"\n✅ REGISTRATION SUCCESSFUL!")
                    print(f"   Client ID: {result.get('client_id', self.hostname)}")
                    print(f"   Status: {result.get('status', 'registered')}")
                    print(f"   Time Sync Validated: {result.get('time_sync_validated', False)}")
                    if 'server_time' in result:
                        print(f"   Server Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(result['server_time']))}")
                    print(f"   Total Registration Time: {total_time_ms:.1f}ms")
                    
                    # Display time sync information if available
                    if 'sync_info' in result:
                        sync_info = result['sync_info']
                        offset = sync_info.get('offset_ms', 0)
                        print(f"\n🕒 TIME SYNCHRONIZATION DETAILS:")
                        print(f"   Synchronized: {sync_info.get('synchronized', False)}")
                        print(f"   Clock Offset: {offset:.1f}ms")
                        print(f"   Method: {sync_info.get('method', 'unknown')}")
                        if abs(offset) < 10:
                            print(f"   Quality: ✅ Excellent (< 10ms)")
                        elif abs(offset) < 50:
                            print(f"   Quality: ✅ Good (< 50ms)")
                        else:
                            print(f"   Quality: ⚠️  Needs improvement (> 50ms)")
                    
                    self.registered = True
                    self.assignment_status = result.get('status', 'waiting_for_assignment')
                    
                    # Show next steps
                    next_steps = result.get('next_steps', [
                        "Wait for admin to assign you to a group",
                        "Admin will use the web interface to make assignments"
                    ])
                    print(f"\n📋 Next Steps:")
                    for step in next_steps:
                        print(f"   • {step}")
                    
                    print(f"{'='*80}")
                    return True
                else:
                    print(f"❌ Registration failed: {result.get('error', 'Unknown error')}")
                    return False
                    
            elif response.status_code == 400:
                error_data = response.json()
                error_code = error_data.get('error_code')
                
                if error_code == 466:  # CLIENT_SYNC_LOST - time sync error
                    print(f"\n❌ TIME SYNCHRONIZATION REQUIRED")
                    print(f"   Error: {error_data['error']}")
                    print(f"   Tolerance: {error_data.get('tolerance_ms', 50)}ms")
                    
                    if 'sync_info' in error_data:
                        sync_info = error_data['sync_info']
                        print(f"   Server Time: {sync_info.get('server_time_formatted', 'N/A')}")
                        print(f"   Client Time: {sync_info.get('client_time_formatted', 'N/A')}")
                        print(f"   Actual Offset: {sync_info.get('offset_ms', 0):.1f}ms")
                    
                    if 'server_ntp_config' in error_data:
                        print(f"\n📋 NTP Configuration needed:")
                        print(error_data['server_ntp_config'])
                        
                    if 'setup_instructions' in error_data:
                        print(f"\n🔧 Setup Instructions:")
                        for instruction in error_data['setup_instructions']:
                            print(f"   {instruction}")
                    
                    print(f"\n💡 Quick Fix Suggestions:")
                    print(f"   1. Check if chrony is running: sudo systemctl status chrony")
                    print(f"   2. Check time sync: chronyc tracking")
                    print(f"   3. Restart chrony: sudo systemctl restart chrony")
                    print(f"   4. Use --no-time-sync flag to bypass (not recommended)")
                    print(f"{'='*80}")
                    return False
                else:
                    print(f"❌ Registration failed: {error_data.get('error', 'Unknown error')}")
                    return False
            else:
                print(f"❌ Registration failed with HTTP status {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Registration error: {e}")
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
                        json={"client_id": self.hostname},
                        timeout=10
                    )
                except requests.exceptions.RequestException:
                    # Fallback to legacy endpoint
                    response = requests.post(
                        f"{self.server_url}/wait_for_stream",
                        json={"client_id": self.hostname},
                        timeout=10
                    )
                
                if response.status_code != 200:
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
                    
                    print(f"\n🎉 ASSIGNMENT COMPLETE!")
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
                
                elif status in ["group_not_running", "group_not_found"]:
                    print(f"❌ {message}")
                    retry_count = 0
                
                elif status == "not_registered":
                    print(f"❌ {message}")
                    print(f"   Client may have been removed from server")
                    return False
                
                else:
                    print(f"⚠️  Unexpected status: {status} - {message}")
                    retry_count += 1
                
                # Interruptible sleep
                if self._shutdown_event.wait(timeout=self.retry_interval):
                    print(f"   Shutdown requested during wait")
                    return False
                
            except Exception as e:
                print(f"⚠️  Network error ({retry_count + 1}/{self.max_retries}): {e}")
                retry_count += 1
                if self._shutdown_event.wait(timeout=self.retry_interval * 2):
                    print(f"   Shutdown requested during error wait")
                    return False
        
        if retry_count >= self.max_retries:
            print(f"❌ Max retries reached, giving up")
            return False
        
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
        """Start playing the assigned stream with optimal player selection"""
        if not self.current_stream_url:
            self.logger.error("No stream URL available")
            return False
            
        try:
            self.stop_stream()  # Clean up any existing player
            
            # Choose the optimal player for this stream
            player_type, reason = self.choose_optimal_player(self.current_stream_url)
            self.current_player_type = player_type
            
            print(f"\n🎬 SMART PLAYER SELECTION")
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
            print(f"\n🎯 STARTING C++ PLAYER (SEI MODE)")
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
                                self.logger.info(f"🎯 SEI: {line_clean}")
                            elif "TELEMETRY:" in line_clean:
                                self.logger.info(f"📊 {line_clean}")
                            elif "ERROR" in line_clean.upper():
                                self.logger.error(f"❌ {line_clean}")
                            elif "WARNING" in line_clean.upper():
                                self.logger.warning(f"⚠️ {line_clean}")
                            else:
                                self.logger.debug(f"🎯 {line_clean}")
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
            print(f"\n📺 STARTING FFPLAY (STANDARD MODE)")
            print(f"   Stream URL: {self.current_stream_url}")
            print(f"   Stream Version: {self.current_stream_version}")
            print(f"   Capability: Standard video playback")
            
            cmd = [
                "ffplay",
                "-fflags", "nobuffer",
                "-flags", "low_delay", 
                "-framedrop",
                "-strict", "experimental",
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
                                self.logger.error(f"📺 {line_clean}")
                            elif "warning" in line_clean.lower():
                                self.logger.warning(f"📺 {line_clean}")
                            else:
                                self.logger.debug(f"📺 {line_clean}")
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
        
        print(f"\n📺 MONITORING {player_display_name.upper()}")
        print(f"   PID: {self.player_process.pid}")
        print(f"   Stream: {self.current_stream_url}")
        print(f"   Player Type: {self.current_player_type}")
        
        last_stream_check = time.time()
        stream_check_interval = 10
        last_health_report = time.time()
        health_report_interval = 30
        
        while self.running and not self._shutdown_event.is_set() and self.player_process.poll() is None:
            current_time = time.time()
            
            # Check for stream changes
            if current_time - last_stream_check >= stream_check_interval:
                if self._check_for_stream_change():
                    print(f"🔄 Stream change detected, will restart with optimal player...")
                    self.stop_stream()
                    return 'stream_changed'
                last_stream_check = current_time
            
            # Periodic health report
            if current_time - last_health_report >= health_report_interval:
                print(f"💓 {player_display_name} health: PID={self.player_process.pid}, Running {int(current_time - last_health_report)}s")
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
            print(f"⚠️  {player_display_name} connection lost or stream unavailable")
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
                    json={"client_id": self.hostname},
                    timeout=5
                )
            except requests.exceptions.RequestException:
                response = requests.post(
                    f"{self.server_url}/wait_for_stream",
                    json={"client_id": self.hostname},
                    timeout=5
                )
            
            if response.status_code == 200:
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
                    if (new_stream_version is not None and 
                        self.current_stream_version is not None):
                        version_changed = new_stream_version != self.current_stream_version
                    
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
                    self.logger.info(f"Stream stopped on server: {status}")
                    return True
                    
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
                print(f"🛑 Stopping {player_name} (PID: {pid})")
                
                # Graceful termination
                self.player_process.terminate()
                
                try:
                    self.player_process.wait(timeout=3)
                    print(f"✅ {player_name} stopped gracefully")
                except subprocess.TimeoutExpired:
                    print(f"⚠️  Force killing {player_name}")
                    self.player_process.kill()
                    
                    try:
                        self.player_process.wait(timeout=2)
                        print(f"✅ {player_name} force-killed")
                    except subprocess.TimeoutExpired:
                        print(f"❌ {player_name} unresponsive")
                        try:
                            os.kill(pid, signal.SIGKILL)
                        except (OSError, ProcessLookupError):
                            pass
                
            except (OSError, ProcessLookupError):
                print(f"🔍 Player process already terminated")
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
        self.stop_time_service()
        
        print(f"✅ Shutdown complete")
    
    def _emergency_cleanup(self):
        """Emergency cleanup for atexit"""
        if self.running:
            self.shutdown()
    
    def run(self):
        """Main execution flow"""
        try:
            print(f"\n{'='*80}")
            print(f"🎯 UNIFIED MULTI-SCREEN CLIENT STARTING")
            print(f"   Hostname: {self.hostname}")
            print(f"   Display Name: {self.display_name}")
            print(f"   Server: {self.server_url}")
            print(f"   Time Sync: {'Enabled' if self.enforce_time_sync else 'Disabled'}")
            print(f"   Smart Player: {'Enabled' if not self.force_ffplay else 'Disabled (force ffplay)'}")
            print(f"   C++ Player: {'Available' if self.player_executable else 'Not found'}")
            print(f"{'='*80}")
            
            # Step 1: Register with server
            if not self.register():
                print(f"❌ Registration failed - exiting")
                return
            
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
                            print(f"👋 User requested exit")
                            break
                        elif stop_reason == 'stream_changed':
                            print(f"🔄 Stream changed, restarting...")
                            continue
                        elif stop_reason in ['stream_ended', 'connection_lost', 'error']:
                            print(f"📺 Stream stopped ({stop_reason}), waiting for new assignment...")
                            self.current_stream_url = None
                            self.current_stream_version = None
                            self.current_player_type = None
                            continue
                        else:
                            print(f"⚠️  Unexpected stop reason: {stop_reason}")
                            break
                    else:
                        print(f"❌ Failed to start player, retrying in 10 seconds...")
                        if self._shutdown_event.wait(timeout=10):
                            break
                else:
                    print(f"⏳ Assignment failed, retrying in 10 seconds...")
                    if self._shutdown_event.wait(timeout=10):
                        break
                        
        except Exception as e:
            print(f"❌ Fatal error: {e}")
            self.logger.error(f"Fatal error in main loop: {e}")
        finally:
            print(f"\n🏁 UNIFIED CLIENT SHUTDOWN")
            self.shutdown()

def main():
    """Main entry point with comprehensive argument parsing"""
    parser = argparse.ArgumentParser(
        description='Unified Multi-Screen Client with Smart Player Selection',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Smart player selection (automatic SEI detection)
  python3 unified_client.py --server http://192.168.1.100:5000
  
  # Force ffplay for all streams
  python3 unified_client.py --server http://192.168.1.100:5000 --force-ffplay
  
  # Disable time synchronization
  python3 unified_client.py --server http://192.168.1.100:5000 --no-time-sync
  
  # Custom hostname and display name
  python3 unified_client.py --server http://192.168.1.100:5000 --hostname display-001 --name "Main Display"
  
  # Debug mode with detailed SEI detection logging
  python3 unified_client.py --server http://192.168.1.100:5000 --debug
        """
    )
    
    # Required arguments
    parser.add_argument('--server', required=True, 
                       help='Server URL (e.g., http://192.168.1.100:5000)')
    
    # Optional arguments
    parser.add_argument('--hostname', 
                       help='Custom client hostname (default: system hostname)')
    parser.add_argument('--name', dest='display_name',
                       help='Display name for admin interface (default: Display-{hostname})')
    parser.add_argument('--no-time-sync', action='store_true',
                       help='Disable time synchronization validation')
    parser.add_argument('--force-ffplay', action='store_true',
                       help='Force use of ffplay for all streams (disable smart selection)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging including SEI detection details')
    parser.add_argument('--version', action='version', version='Unified Multi-Screen Client v2.1')
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        print(f"🐛 Debug logging enabled (includes SEI detection)")
    
    # Validate server URL
    if not args.server.startswith(('http://', 'https://')):
        print(f"❌ Error: Server URL must start with http:// or https://")
        print(f"   Example: --server http://192.168.1.100:5000")
        sys.exit(1)
    
    # Create and run client
    try:
        client = UnifiedMultiScreenClient(
            server_url=args.server,
            hostname=args.hostname,
            display_name=args.display_name,
            force_ffplay=args.force_ffplay,
            enforce_time_sync=not args.no_time_sync
        )
        
        print(f"🎬 Starting Unified Multi-Screen Client with Smart Player Selection...")
        print(f"   Press Ctrl+C to stop gracefully")
        
        client.run()
        
    except KeyboardInterrupt:
        print(f"\n⌨️  Keyboard interrupt received")
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        logging.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()