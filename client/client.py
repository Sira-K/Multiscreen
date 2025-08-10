#!/usr/bin/env python3
"""
Unified Multi-Screen Client with Chrony Time Synchronization
Implements OpenVideoWalls-style time sync using chrony/NTP for precise client-client synchronization
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

class ChronyTimeSync:
    """Chrony-based time synchronization service following OpenVideoWalls methodology"""
    
    def __init__(self, tolerance_ms: float = 50.0):
        self.tolerance_ms = tolerance_ms
        self.sync_status = {"synchronized": False, "offset_ms": float('inf')}
        self.logger = logging.getLogger(__name__)
        
    def check_chrony_installation(self) -> bool:
        """Check if chrony is installed and accessible"""
        try:
            result = subprocess.run(['chronyc', '--help'], capture_output=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def install_chrony_config(self) -> bool:
        """Generate and suggest chrony configuration for video wall synchronization"""
        config = self.generate_chrony_config()
        
        print(f"\n🕒 CHRONY CONFIGURATION FOR VIDEO WALL SYNCHRONIZATION")
        print(f"{'='*70}")
        print(f"Following OpenVideoWalls methodology for precise time sync")
        print(f"Tolerance: ±{self.tolerance_ms}ms for synchronized video playback")
        print(f"{'='*70}")
        
        print(f"\n📋 Required chrony configuration (/etc/chrony/chrony.conf):")
        print(f"{'─'*50}")
        print(config)
        print(f"{'─'*50}")
        
        print(f"\n🔧 Installation Steps:")
        print(f"1. sudo nano /etc/chrony/chrony.conf")
        print(f"2. Replace content with the configuration above")
        print(f"3. sudo systemctl restart chrony")
        print(f"4. sudo systemctl enable chrony")
        print(f"5. Wait 2-5 minutes for initial synchronization")
        
        return True
    
    def generate_chrony_config(self) -> str:
        """Generate chrony configuration optimized for video wall synchronization"""
        return """# Chrony Configuration for OpenVideoWalls Multi-Screen Synchronization
# Implements precise time sync methodology from OpenVideoWalls paper

# Multiple high-quality NTP sources for redundancy and accuracy
# All clients use the same sources = common time reference
pool pool.ntp.org iburst maxsources 3
pool time.google.com iburst maxsources 2  
pool time.cloudflare.com iburst maxsources 2

# Quick time correction on startup (OpenVideoWalls requirement)
# Allow steps up to 1 second for first 3 corrections
makestep 1.0 3

# Video wall optimizations
maxupdateskew 100.0    # Handle network jitter in video streaming environments
driftfile /var/lib/chrony/drift
rtcsync                # Keep hardware clock in sync

# Logging for monitoring sync quality
logdir /var/log/chrony
log measurements statistics tracking refclocks

# Security
cmdallow 127.0.0.1
bindcmdaddress 127.0.0.1
bindcmdaddress ::1

# Performance tuning for sub-50ms synchronization
minpoll 4              # Poll every 16 seconds minimum
maxpoll 6              # Poll every 64 seconds maximum
"""
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get comprehensive chrony synchronization status"""
        try:
            # Get tracking information
            tracking_result = subprocess.run(
                ['chronyc', 'tracking'], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            
            if tracking_result.returncode != 0:
                return {
                    "synchronized": False,
                    "error": "chrony not running or accessible",
                    "offset_ms": float('inf'),
                    "stratum": None,
                    "reference": None
                }
            
            tracking_data = self.parse_chrony_tracking(tracking_result.stdout)
            
            # Get sources information for additional context
            sources_result = subprocess.run(
                ['chronyc', 'sources'], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            
            sources_data = []
            if sources_result.returncode == 0:
                sources_data = self.parse_chrony_sources(sources_result.stdout)
            
            # Calculate synchronization quality
            offset_ms = tracking_data.get('last_offset_ms', float('inf'))
            is_synchronized = (
                abs(offset_ms) <= self.tolerance_ms and 
                tracking_data.get('stratum', 16) < 16 and
                tracking_data.get('reference_id') != '127.127.1.1'  # Not using local clock
            )
            
            sync_status = {
                "synchronized": is_synchronized,
                "offset_ms": offset_ms,
                "tolerance_ms": self.tolerance_ms,
                "stratum": tracking_data.get('stratum'),
                "reference": tracking_data.get('reference_name'),
                "reference_id": tracking_data.get('reference_id'),
                "root_delay_ms": tracking_data.get('root_delay_ms'),
                "root_dispersion_ms": tracking_data.get('root_dispersion_ms'),
                "last_update_ago": tracking_data.get('last_update_ago'),
                "leap_status": tracking_data.get('leap_status'),
                "sources_count": len(sources_data),
                "sources": sources_data[:3],  # Top 3 sources
                "timestamp": time.time()
            }
            
            self.sync_status = sync_status
            return sync_status
            
        except subprocess.TimeoutExpired:
            return {"synchronized": False, "error": "chronyc timeout", "offset_ms": float('inf')}
        except Exception as e:
            return {"synchronized": False, "error": str(e), "offset_ms": float('inf')}
    
    def parse_chrony_tracking(self, output: str) -> Dict[str, Any]:
        """Parse chronyc tracking output into structured data"""
        tracking = {}
        
        for line in output.split('\n'):
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()
                
                # Parse specific fields
                if 'reference_id' in key:
                    tracking['reference_id'] = value.split()[0]
                    if '(' in value and ')' in value:
                        tracking['reference_name'] = value.split('(')[1].split(')')[0]
                
                elif 'stratum' in key:
                    try:
                        tracking['stratum'] = int(value)
                    except ValueError:
                        tracking['stratum'] = 16
                
                elif 'root_delay' in key:
                    try:
                        delay_sec = float(value.split()[0])
                        tracking['root_delay_ms'] = delay_sec * 1000
                    except (ValueError, IndexError):
                        tracking['root_delay_ms'] = None
                
                elif 'root_dispersion' in key:
                    try:
                        disp_sec = float(value.split()[0])
                        tracking['root_dispersion_ms'] = disp_sec * 1000
                    except (ValueError, IndexError):
                        tracking['root_dispersion_ms'] = None
                
                elif 'last_offset' in key:
                    try:
                        # Parse offset (can be in seconds or milliseconds)
                        if 'ms' in value:
                            tracking['last_offset_ms'] = float(value.replace('ms', '').strip())
                        else:
                            offset_sec = float(value.split()[0])
                            tracking['last_offset_ms'] = offset_sec * 1000
                    except (ValueError, IndexError):
                        tracking['last_offset_ms'] = float('inf')
                
                elif 'last_update' in key:
                    tracking['last_update_ago'] = value
                
                elif 'leap_status' in key:
                    tracking['leap_status'] = value
                
                else:
                    tracking[key] = value
        
        return tracking
    
    def parse_chrony_sources(self, output: str) -> list:
        """Parse chronyc sources output"""
        sources = []
        lines = output.split('\n')
        
        for line in lines[2:]:  # Skip header lines
            line = line.strip()
            if line and not line.startswith('='):
                parts = line.split()
                if len(parts) >= 4:
                    source = {
                        'indicator': parts[0][0] if parts[0] else '',
                        'name': parts[0][1:] if len(parts[0]) > 1 else parts[1] if len(parts) > 1 else '',
                        'stratum': parts[1] if len(parts) > 1 else '',
                        'poll': parts[2] if len(parts) > 2 else '',
                        'reach': parts[3] if len(parts) > 3 else '',
                        'lastRx': parts[4] if len(parts) > 4 else '',
                        'last_sample': parts[5:] if len(parts) > 5 else []
                    }
                    sources.append(source)
        
        return sources
    
    def wait_for_synchronization(self, max_wait_minutes: int = 10) -> bool:
        """Wait for chrony to achieve synchronization within tolerance"""
        print(f"\n⏱️  WAITING FOR CHRONY SYNCHRONIZATION")
        print(f"   Tolerance: ±{self.tolerance_ms}ms")
        print(f"   Max wait: {max_wait_minutes} minutes")
        print(f"   Following OpenVideoWalls sync methodology...")
        
        start_time = time.time()
        max_wait_seconds = max_wait_minutes * 60
        check_interval = 10  # Check every 10 seconds
        
        while (time.time() - start_time) < max_wait_seconds:
            status = self.get_sync_status()
            
            offset_ms = status.get('offset_ms', float('inf'))
            synchronized = status.get('synchronized', False)
            stratum = status.get('stratum', 16)
            
            print(f"   Status: Offset={offset_ms:.1f}ms, Stratum={stratum}, Sync={synchronized}")
            
            if synchronized:
                print(f"✅ SYNCHRONIZATION ACHIEVED!")
                print(f"   Final offset: {offset_ms:.1f}ms (within ±{self.tolerance_ms}ms)")
                print(f"   Time to sync: {(time.time() - start_time):.1f} seconds")
                return True
            
            time.sleep(check_interval)
        
        print(f"⏰ Synchronization timeout after {max_wait_minutes} minutes")
        final_status = self.get_sync_status()
        print(f"   Final offset: {final_status.get('offset_ms', 'unknown')}ms")
        return False
    
    def print_detailed_status(self):
        """Print comprehensive sync status for debugging"""
        status = self.get_sync_status()
        
        print(f"\n📊 CHRONY SYNCHRONIZATION STATUS")
        print(f"{'='*50}")
        print(f"Synchronized: {'✅ YES' if status.get('synchronized') else '❌ NO'}")
        print(f"Time Offset: {status.get('offset_ms', 'unknown'):.1f}ms")
        print(f"Tolerance: ±{self.tolerance_ms}ms")
        print(f"Stratum: {status.get('stratum', 'unknown')}")
        print(f"Reference: {status.get('reference', 'unknown')}")
        print(f"Root Delay: {status.get('root_delay_ms', 'unknown'):.1f}ms")
        print(f"Root Dispersion: {status.get('root_dispersion_ms', 'unknown'):.1f}ms")
        print(f"Last Update: {status.get('last_update_ago', 'unknown')}")
        print(f"Sources: {status.get('sources_count', 0)}")
        
        if status.get('error'):
            print(f"Error: {status['error']}")
        
        print(f"{'='*50}")

class UnifiedMultiScreenClient:
    """
    Unified Multi-Screen Client with Chrony Time Synchronization
    Implements OpenVideoWalls synchronization methodology
    """
    
    def __init__(self, server_url: str, hostname: str = None, display_name: str = None, 
                 force_ffplay: bool = False, sync_tolerance_ms: float = 50.0):
        """
        Initialize the unified client with chrony time sync
        
        Args:
            server_url: Server URL (e.g., "http://192.168.1.100:5000")
            hostname: Unique client identifier
            display_name: Friendly display name
            force_ffplay: Force use of ffplay instead of smart selection
            sync_tolerance_ms: Time sync tolerance in milliseconds (OpenVideoWalls: 50ms)
        """
        self.server_url = server_url.rstrip('/')
        self.hostname = hostname or socket.gethostname()
        self.display_name = display_name or f"Display-{self.hostname}"
        self.force_ffplay = force_ffplay
        
        # Stream management
        self.current_stream_url = None
        self.current_stream_version = None
        self.current_player_type = None
        self.player_process = None
        self.running = True
        self.retry_interval = 5
        self.max_retries = 60
        self._shutdown_event = threading.Event()
        
        # Chrony time synchronization (OpenVideoWalls methodology)
        self.time_sync = ChronyTimeSync(tolerance_ms=sync_tolerance_ms)
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
    
    def check_time_synchronization(self) -> bool:
        """Check and validate chrony time synchronization"""
        print(f"\n🕒 CHECKING CHRONY TIME SYNCHRONIZATION")
        print(f"Following OpenVideoWalls methodology for video wall sync")
        
        # Check if chrony is installed
        if not self.time_sync.check_chrony_installation():
            print(f"\n❌ CHRONY NOT INSTALLED")
            print(f"Please install chrony: sudo apt install chrony")
            return False
        
        # Get current sync status
        status = self.time_sync.get_sync_status()
        
        if status.get('synchronized'):
            print(f"✅ CHRONY SYNCHRONIZED")
            print(f"   Offset: {status.get('offset_ms', 'unknown'):.1f}ms")
            print(f"   Stratum: {status.get('stratum', 'unknown')}")
            print(f"   Reference: {status.get('reference', 'unknown')}")
            return True
        
        elif status.get('error'):
            print(f"\n⚠️  CHRONY STATUS: {status['error']}")
            
            if 'not running' in status['error'].lower():
                print(f"\n🔧 CHRONY SETUP REQUIRED")
                self.time_sync.install_chrony_config()
                
                print(f"\nAfter configuration, restart this client to check sync status.")
                return False
            
            return False
        
        else:
            print(f"\n⏱️  CHRONY SYNCHRONIZING...")
            print(f"   Current offset: {status.get('offset_ms', 'unknown'):.1f}ms")
            print(f"   Target: ±{self.time_sync.tolerance_ms}ms")
            
            # Wait for synchronization
            if self.time_sync.wait_for_synchronization(max_wait_minutes=5):
                return True
            else:
                print(f"\n⚠️  Synchronization incomplete, but proceeding...")
                print(f"   Video sync quality may be reduced")
                return True  # Allow to proceed with degraded sync
    
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
        """Register client with server including chrony sync validation"""
        try:
            print(f"\n{'='*80}")
            print(f"🚀 STARTING UNIFIED CLIENT REGISTRATION")
            print(f"   Client: {self.hostname}")
            print(f"   Display Name: {self.display_name}")
            print(f"   Server: {self.server_url}")
            print(f"   Server IP: {self.server_ip}")
            print(f"   Time Sync: Chrony/NTP (OpenVideoWalls methodology)")
            print(f"   Tolerance: ±{self.time_sync.tolerance_ms}ms")
            print(f"   Smart Player: {'Enabled' if not self.force_ffplay else 'Disabled (force ffplay)'}")
            
            # Check chrony synchronization FIRST
            if not self.check_time_synchronization():
                print(f"\n❌ Time synchronization check failed")
                print(f"   Video wall sync may be degraded")
                print(f"   Configure chrony before proceeding for best results")
                # Still allow registration to proceed
            
            registration_start = time.time()
            registration_start_formatted = time.strftime("%Y-%m-%d %H:%M:%S.%f", time.gmtime(registration_start))[:-3]
            print(f"   Start Time: {registration_start_formatted} UTC")
            print(f"{'='*80}")
            
            # Create platform string indicating chrony sync capability
            if self.force_ffplay:
                player_type = "ffplay_only"
            elif not self.player_executable:
                player_type = "ffplay_fb"  # fallback
            else:
                player_type = "smart_sel"  # smart selection
            
            # Get chrony sync status for registration
            sync_status = self.time_sync.get_sync_status()
            
            registration_data = {
                "hostname": self.hostname,
                "display_name": self.display_name,
                "platform": f"chrony_{player_type}",  # Indicate chrony sync
                "time_sync_method": "chrony",
                "sync_tolerance_ms": self.time_sync.tolerance_ms,
                "sync_status": {
                    "synchronized": sync_status.get('synchronized', False),
                    "offset_ms": sync_status.get('offset_ms'),
                    "stratum": sync_status.get('stratum'),
                    "reference": sync_status.get('reference')
                }
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
                # Fallback to legacy endpoint (simplified data)
                self.logger.info("New endpoint failed, trying legacy endpoint...")
                legacy_data = {
                    "hostname": self.hostname,
                    "display_name": self.display_name,
                    "platform": f"chrony_{player_type}"
                }
                response = requests.post(
                    f"{self.server_url}/register_client",
                    json=legacy_data,
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
                    print(f"   Time Sync: Chrony/NTP")
                    if 'server_time' in result:
                        print(f"   Server Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(result['server_time']))}")
                    print(f"   Total Registration Time: {total_time_ms:.1f}ms")
                    
                    # Display chrony sync status
                    current_status = self.time_sync.get_sync_status()
                    print(f"\n🕒 CHRONY SYNCHRONIZATION STATUS:")
                    print(f"   Synchronized: {'✅ YES' if current_status.get('synchronized') else '⚠️ PARTIAL'}")
                    print(f"   Clock Offset: {current_status.get('offset_ms', 'unknown'):.1f}ms")
                    print(f"   Tolerance: ±{self.time_sync.tolerance_ms}ms")
                    print(f"   Stratum: {current_status.get('stratum', 'unknown')}")
                    print(f"   Reference: {current_status.get('reference', 'unknown')}")
                    
                    offset = current_status.get('offset_ms', float('inf'))
                    if abs(offset) < 10:
                        print(f"   Quality: ✅ Excellent (< 10ms) - Optimal for video walls")
                    elif abs(offset) < 50:
                        print(f"   Quality: ✅ Good (< 50ms) - Suitable for video walls")
                    elif abs(offset) < 100:
                        print(f"   Quality: ⚠️ Fair (< 100ms) - May show minor desync")
                    else:
                        print(f"   Quality: ❌ Poor (> 100ms) - Significant desync expected")
                    
                    self.registered = True
                    self.assignment_status = result.get('status', 'waiting_for_assignment')
                    
                    # Show next steps
                    next_steps = result.get('next_steps', [
                        "Wait for admin to assign you to a group",
                        "Admin will use the web interface to make assignments",
                        "Chrony will continue syncing in background for optimal timing"
                    ])
                    print(f"\n📋 Next Steps:")
                    for step in next_steps:
                        print(f"   • {step}")
                    
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
            
            # Check chrony sync status before starting playback
            sync_status = self.time_sync.get_sync_status()
            if not sync_status.get('synchronized'):
                print(f"\n⚠️  WARNING: Chrony not fully synchronized")
                print(f"   Current offset: {sync_status.get('offset_ms', 'unknown'):.1f}ms")
                print(f"   Video sync quality may be reduced")
            
            # Choose the optimal player for this stream
            player_type, reason = self.choose_optimal_player(self.current_stream_url)
            self.current_player_type = player_type
            
            print(f"\n🎬 SMART PLAYER SELECTION")
            print(f"   Selected: {player_type.upper()}")
            print(f"   Reason: {reason}")
            print(f"   Stream URL: {self.current_stream_url}")
            print(f"   Time Sync: Chrony (offset: {sync_status.get('offset_ms', 'unknown'):.1f}ms)")
            
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
            print(f"   Capability: SEI timestamp processing + Chrony sync")
            
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
            print(f"   Status: Playing with SEI processing + chrony time sync")
            self.logger.info(f"C++ Player started for SEI stream with chrony sync")
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
            print(f"   Capability: Standard video playback + chrony time sync")
            
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
            print(f"   Status: Playing standard stream with chrony time sync")
            self.logger.info(f"ffplay started for standard stream with chrony sync")
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
        print(f"   Time Sync: Chrony/NTP")
        
        last_stream_check = time.time()
        stream_check_interval = 10
        last_health_report = time.time()
        health_report_interval = 30
        last_sync_check = time.time()
        sync_check_interval = 60  # Check chrony sync every minute
        
        while self.running and not self._shutdown_event.is_set() and self.player_process.poll() is None:
            current_time = time.time()
            
            # Check for stream changes
            if current_time - last_stream_check >= stream_check_interval:
                if self._check_for_stream_change():
                    print(f"🔄 Stream change detected, will restart with optimal player...")
                    self.stop_stream()
                    return 'stream_changed'
                last_stream_check = current_time
            
            # Check chrony sync status periodically
            if current_time - last_sync_check >= sync_check_interval:
                sync_status = self.time_sync.get_sync_status()
                offset_ms = sync_status.get('offset_ms', float('inf'))
                synchronized = sync_status.get('synchronized', False)
                
                print(f"🕒 Chrony status: offset={offset_ms:.1f}ms, sync={synchronized}")
                
                if not synchronized or abs(offset_ms) > self.time_sync.tolerance_ms:
                    print(f"⚠️  Time sync degraded - video sync quality may be affected")
                
                last_sync_check = current_time
            
            # Periodic health report
            if current_time - last_health_report >= health_report_interval:
                sync_status = self.time_sync.get_sync_status()
                print(f"💓 {player_display_name} health: PID={self.player_process.pid}, "
                      f"Running {int(current_time - last_health_report)}s, "
                      f"Sync offset: {sync_status.get('offset_ms', 'unknown'):.1f}ms")
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
        
        print(f"✅ Shutdown complete")
    
    def _emergency_cleanup(self):
        """Emergency cleanup for atexit"""
        if self.running:
            self.shutdown()
    
    def run(self):
        """Main execution flow with chrony time synchronization"""
        try:
            print(f"\n{'='*80}")
            print(f"🎯 UNIFIED MULTI-SCREEN CLIENT WITH CHRONY SYNC")
            print(f"   Following OpenVideoWalls synchronization methodology")
            print(f"   Hostname: {self.hostname}")
            print(f"   Display Name: {self.display_name}")
            print(f"   Server: {self.server_url}")
            print(f"   Time Sync: Chrony/NTP (tolerance: ±{self.time_sync.tolerance_ms}ms)")
            print(f"   Smart Player: {'Enabled' if not self.force_ffplay else 'Disabled (force ffplay)'}")
            print(f"   C++ Player: {'Available' if self.player_executable else 'Not found'}")
            print(f"{'='*80}")
            
            # Step 1: Register with server (includes chrony sync check)
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
    """Main entry point with chrony-based time synchronization"""
    parser = argparse.ArgumentParser(
        description='Unified Multi-Screen Client with Chrony Time Synchronization',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
OpenVideoWalls Time Synchronization:
  This client uses chrony/NTP for precise time synchronization following the
  OpenVideoWalls methodology. All clients sync to common NTP servers, achieving
  sub-50ms accuracy for synchronized video wall playback.

Examples:
  # Standard usage with chrony sync (recommended)
  python3 chrony_client.py --server http://192.168.1.100:5000
  
  # High precision mode (10ms tolerance)
  python3 chrony_client.py --server http://192.168.1.100:5000 --sync-tolerance 10
  
  # Force ffplay for all streams
  python3 chrony_client.py --server http://192.168.1.100:5000 --force-ffplay
  
  # Custom hostname and display name
  python3 chrony_client.py --server http://192.168.1.100:5000 --hostname display-001 --name "Main Display"
  
  # Debug mode with detailed chrony and SEI logging
  python3 chrony_client.py --server http://192.168.1.100:5000 --debug
  
  # Show chrony configuration and exit
  python3 chrony_client.py --setup-chrony

Chrony Setup:
  1. Install: sudo apt install chrony
  2. Configure: Use --setup-chrony to get configuration
  3. Restart: sudo systemctl restart chrony
  4. Wait 2-5 minutes for initial synchronization
        """
    )
    
    # Required arguments
    parser.add_argument('--server', 
                       help='Server URL (e.g., http://192.168.1.100:5000)')
    
    # Optional arguments
    parser.add_argument('--hostname', 
                       help='Custom client hostname (default: system hostname)')
    parser.add_argument('--name', dest='display_name',
                       help='Display name for admin interface (default: Display-{hostname})')
    parser.add_argument('--sync-tolerance', type=float, default=50.0,
                       help='Time synchronization tolerance in milliseconds (default: 50ms)')
    parser.add_argument('--force-ffplay', action='store_true',
                       help='Force use of ffplay for all streams (disable smart selection)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging including chrony and SEI detection details')
    parser.add_argument('--setup-chrony', action='store_true',
                       help='Show chrony configuration for video wall sync and exit')
    parser.add_argument('--check-sync', action='store_true',
                       help='Check chrony synchronization status and exit')
    parser.add_argument('--version', action='version', 
                       version='Unified Multi-Screen Client with Chrony Sync v2.2')
    
    args = parser.parse_args()
    
    # Handle setup/check modes
    if args.setup_chrony:
        print(f"🕒 CHRONY SETUP FOR OPENVIDEOWALLS SYNCHRONIZATION")
        time_sync = ChronyTimeSync(tolerance_ms=args.sync_tolerance)
        time_sync.install_chrony_config()
        return
    
    if args.check_sync:
        print(f"🕒 CHECKING CHRONY SYNCHRONIZATION STATUS")
        time_sync = ChronyTimeSync(tolerance_ms=args.sync_tolerance)
        if not time_sync.check_chrony_installation():
            print(f"❌ chrony not installed or not accessible")
            print(f"   Install with: sudo apt install chrony")
            sys.exit(1)
        time_sync.print_detailed_status()
        return
    
    # Server URL is required for normal operation
    if not args.server:
        print(f"❌ Error: --server is required for normal operation")
        print(f"   Use --setup-chrony to configure chrony")
        print(f"   Use --check-sync to check synchronization status")
        print(f"   Example: --server http://192.168.1.100:5000")
        sys.exit(1)
    
    # Configure logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        print(f"🐛 Debug logging enabled (includes chrony and SEI detection)")
    
    # Validate server URL
    if not args.server.startswith(('http://', 'https://')):
        print(f"❌ Error: Server URL must start with http:// or https://")
        print(f"   Example: --server http://192.168.1.100:5000")
        sys.exit(1)
    
    # Validate sync tolerance
    if args.sync_tolerance <= 0 or args.sync_tolerance > 1000:
        print(f"❌ Error: Sync tolerance must be between 0.1 and 1000 milliseconds")
        sys.exit(1)
    
    # Create and run client
    try:
        client = UnifiedMultiScreenClient(
            server_url=args.server,
            hostname=args.hostname,
            display_name=args.display_name,
            force_ffplay=args.force_ffplay,
            sync_tolerance_ms=args.sync_tolerance
        )
        
        print(f"🎬 Starting Unified Multi-Screen Client with Chrony Synchronization...")
        print(f"   Following OpenVideoWalls methodology for precise timing")
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