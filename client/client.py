import argparse
import requests
import time
import logging
import subprocess
import sys
import os
import tempfile
import shutil
import signal
import atexit
from typing import Optional
from urllib.parse import urlparse
import threading
from pathlib import Path

class MultiScreenClient:
    def __init__(self, server_url: str, hostname: str = None, display_name: str = None):
        """
        Client that waits for admin to assign it to a stream
        Uses integrated C++ player instead of ffplay for better performance
        
        Args:
            server_url: Server URL (e.g., "http://128.205.39.64:5001")
            hostname: Unique client identifier
            display_name: Friendly display name
        """
        self.server_url = server_url.rstrip('/')
        self.hostname = hostname or f"client-{int(time.time())}"
        self.display_name = display_name or self.hostname
        self.current_stream_url = None
        self.current_stream_version = None
        self.player_process = None
        self.running = True
        self.retry_interval = 5  # seconds
        self.max_retries = 60    # 5 minutes total wait time
        self._shutdown_event = threading.Event()
        
        # Extract server IP from server URL for stream URL fixing
        parsed_url = urlparse(self.server_url)
        self.server_ip = parsed_url.hostname or "127.0.0.1"
        
        # Player executable path
        self.player_executable = None
        self.build_dir = None
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        self.logger = logging.getLogger(__name__)
        
        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()
        
        # Register cleanup function
        atexit.register(self._emergency_cleanup)
        
        # Initialize the C++ player
        self._setup_cpp_player()

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            signal_name = signal.Signals(signum).name
            self.logger.info(f"🛑 Received {signal_name} signal, initiating graceful shutdown...")
            self.shutdown()
        
        # Handle SIGINT (Ctrl+C) and SIGTERM
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # On Unix systems, also handle SIGHUP
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, signal_handler)

    def shutdown(self):
        """Initiate graceful shutdown"""
        if not self.running:
            return  # Already shutting down
        
        self.logger.info("🔄 Starting graceful shutdown...")
        self.running = False
        self._shutdown_event.set()
        
        # Stop the player immediately
        self.stop_stream()
        
        # Give monitoring threads a moment to notice shutdown
        time.sleep(0.5)

    def _setup_cpp_player(self):
        """Setup the C++ player - use existing build if available, fallback to building our own"""
        try:
            # First, try to use existing compiled player
            existing_player_path = Path(__file__).parent / "multi-screen" / "cmake-build-debug" / "player" / "player"
            
            if existing_player_path.exists():
                self.player_executable = str(existing_player_path)
                self.logger.info(f"✅ Using existing C++ player: {self.player_executable}")
                self.build_dir = None  # No need for temporary build directory
                return
            
            # Fallback to building our own if existing player not found
            self.logger.info("🔨 Existing player not found, building C++ video player...")
            
            # Create build directory
            self.build_dir = tempfile.mkdtemp(prefix="multiscreen_player_")
            self.logger.info(f"📁 Build directory: {self.build_dir}")
            
            # Copy source files to build directory
            current_dir = Path(__file__).parent / "multi-screen" / "player"
            source_files = [
                "main.cpp",
                "receive_from_server.cpp", 
                "receive_from_server.h",
                "display_to_screen.cpp",
                "display_to_screen.h", 
                "safe_queue.cpp",
                "safe_queue.h",
                "CMakeLists.txt"
            ]
            
            for file in source_files:
                src_path = current_dir / file
                if src_path.exists():
                    shutil.copy2(src_path, self.build_dir)
                    self.logger.debug(f"📄 Copied {file}")
                else:
                    self.logger.warning(f"⚠️ Source file not found: {file}")
            
            # Create enhanced CMakeLists.txt
            self._create_cmake_file()
            
            # Build the player
            if self._build_player():
                self.player_executable = os.path.join(self.build_dir, "player")
                self.logger.info("✅ C++ player built successfully")
            else:
                self.logger.error("❌ Failed to build C++ player, falling back to ffplay")
                self.player_executable = None
                
        except Exception as e:
            self.logger.error(f"❌ Error setting up C++ player: {e}")
            self.player_executable = None

    def _create_cmake_file(self):
        """Create comprehensive CMakeLists.txt"""
        cmake_content = """cmake_minimum_required(VERSION 3.16)
project(MultiScreenPlayer)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find required packages
find_package(PkgConfig REQUIRED)

# Find FFmpeg components
pkg_check_modules(PKG_FFMPEG REQUIRED IMPORTED_TARGET
    libavformat
    libavcodec
    libavutil
    libswscale
)

# Find other dependencies
pkg_check_modules(PKG_CURL REQUIRED IMPORTED_TARGET libcurl)
pkg_check_modules(PKG_SDL2 REQUIRED IMPORTED_TARGET sdl2)

# Find spdlog
find_package(spdlog REQUIRED)

# Find nlohmann_json
find_package(nlohmann_json REQUIRED)

# Add executable
add_executable(
    player
    main.cpp
    receive_from_server.cpp
    display_to_screen.cpp
    safe_queue.cpp
)

# Link libraries
target_link_libraries(
    player PRIVATE
    PkgConfig::PKG_FFMPEG
    PkgConfig::PKG_CURL
    PkgConfig::PKG_SDL2
    spdlog::spdlog
    nlohmann_json::nlohmann_json
    $<$<BOOL:${MINGW}>:ws2_32>
)

# Compiler-specific options
if(MSVC)
    target_compile_options(player PRIVATE /W4)
else()
    target_compile_options(player PRIVATE -Wall -Wextra -Wpedantic)
endif()

# Set output directory
set_target_properties(player PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}
)
"""
        
        cmake_path = os.path.join(self.build_dir, "CMakeLists.txt")
        with open(cmake_path, 'w') as f:
            f.write(cmake_content)

    def _build_player(self) -> bool:
        """Build the C++ player using CMake"""
        try:
            self.logger.info("🔧 Building C++ player...")
            
            # Check for required tools
            if not self._check_build_dependencies():
                return False
            
            build_commands = [
                # Configure
                ["cmake", "-B", "build", "-S", ".", "-DCMAKE_BUILD_TYPE=Release"],
                # Build
                ["cmake", "--build", "build", "--config", "Release"]
            ]
            
            for cmd in build_commands:
                self.logger.debug(f"🔧 Running: {' '.join(cmd)}")
                result = subprocess.run(
                    cmd,
                    cwd=self.build_dir,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                
                if result.returncode != 0:
                    self.logger.error(f"❌ Build command failed: {' '.join(cmd)}")
                    self.logger.error(f"❌ Error output: {result.stderr}")
                    return False
                else:
                    self.logger.debug(f"✅ Command succeeded: {' '.join(cmd)}")
            
            # Check if executable was created
            potential_paths = [
                os.path.join(self.build_dir, "build", "player"),
                os.path.join(self.build_dir, "build", "Release", "player"),
                os.path.join(self.build_dir, "build", "player.exe"),
                os.path.join(self.build_dir, "build", "Release", "player.exe"),
            ]
            
            for path in potential_paths:
                if os.path.exists(path):
                    # Copy to root of build directory for easier access
                    final_path = os.path.join(self.build_dir, "player")
                    if not os.path.exists(final_path):
                        shutil.copy2(path, final_path)
                    self.logger.info(f"✅ Player executable: {final_path}")
                    return True
            
            self.logger.error("❌ Player executable not found after build")
            return False
            
        except subprocess.TimeoutExpired:
            self.logger.error("❌ Build timeout exceeded")
            return False
        except Exception as e:
            self.logger.error(f"❌ Build error: {e}")
            return False

    def _check_build_dependencies(self) -> bool:
        """Check if required build tools are available"""
        required_tools = ["cmake", "pkg-config"]
        
        for tool in required_tools:
            if not shutil.which(tool):
                self.logger.error(f"❌ Required tool not found: {tool}")
                self.logger.error("📋 Please install build dependencies:")
                self.logger.error("   Ubuntu/Debian: sudo apt-get install cmake pkg-config libavformat-dev libavcodec-dev libavutil-dev libswscale-dev libcurl4-openssl-dev libsdl2-dev libspdlog-dev nlohmann-json3-dev")
                self.logger.error("   macOS: brew install cmake pkg-config ffmpeg curl sdl2 spdlog nlohmann-json")
                return False
        
        return True

    def fix_stream_url(self, stream_url: str) -> str:
        """
        Fix stream URL to use server IP instead of localhost
        
        Args:
            stream_url: Original stream URL from server
            
        Returns:
            Fixed stream URL with correct server IP
        """
        if not stream_url:
            return stream_url
            
        # Replace 127.0.0.1 or localhost with actual server IP
        if "127.0.0.1" in stream_url:
            fixed_url = stream_url.replace("127.0.0.1", self.server_ip)
            self.logger.info(f"🔧 Fixed stream URL:")
            self.logger.info(f"   Original: {stream_url}")
            self.logger.info(f"   Fixed:    {fixed_url}")
            return fixed_url
        elif "localhost" in stream_url:
            fixed_url = stream_url.replace("localhost", self.server_ip)
            self.logger.info(f"🔧 Fixed stream URL:")
            self.logger.info(f"   Original: {stream_url}")
            self.logger.info(f"   Fixed:    {fixed_url}")
            return fixed_url
        else:
            # URL already has correct IP
            self.logger.debug(f"✅ Stream URL already has correct IP: {stream_url}")
            return stream_url

    def register(self) -> bool:
        """Register client with server"""
        try:
            self.logger.info(f"🚀 Starting Multi-Screen Client: {self.hostname}")
            self.logger.info(f"🌐 Server: {self.server_url}")
            self.logger.info(f"🎯 Server IP: {self.server_ip}")
            
            player_type = "cpp_player" if self.player_executable else "ffplay_fallback"
            
            response = requests.post(
                f"{self.server_url}/register_client",
                json={
                    "hostname": self.hostname,
                    "display_name": self.display_name,
                    "platform": f"python_client_with_{player_type}"
                },
                timeout=10
            )
            if response.status_code == 200:
                self.logger.info(f"✅ Registered as {self.hostname} (using {player_type})")
                self.logger.info("📋 Waiting for admin to assign this client to a group and stream...")
                return True
            self.logger.error(f"❌ Registration failed: {response.text}")
            return False
        except Exception as e:
            self.logger.error(f"❌ Registration error: {e}")
            return False

    def wait_for_assignment(self) -> bool:
        """Wait for admin to assign this client to a group and stream"""
        retry_count = 0
        
        while self.running and not self._shutdown_event.is_set() and retry_count < self.max_retries:
            try:
                # Poll server for assignment status
                response = requests.post(
                    f"{self.server_url}/wait_for_stream",
                    json={"client_id": self.hostname},
                    timeout=10
                )
                
                if response.status_code != 200:
                    raise Exception(response.text)
                
                data = response.json()
                status = data.get('status')
                message = data.get('message', '')
                
                if status == "ready_to_play":
                    # 🎉 Everything is ready!
                    original_stream_url = data.get('stream_url')
                    self.current_stream_url = self.fix_stream_url(original_stream_url)
                    
                    # Handle stream version - only use server version if provided
                    server_version = data.get('stream_version')
                    if server_version is not None:
                        self.current_stream_version = server_version
                    else:
                        # Server doesn't provide versions, use timestamp for this session only
                        if self.current_stream_version is None:
                            self.current_stream_version = int(time.time())
                        # Keep existing version if server doesn't provide one
                    
                    group_name = data.get('group_name', 'unknown')
                    stream_assignment = data.get('stream_assignment', 'unknown')
                    
                    self.logger.info(f"🎉 Ready to play!")
                    self.logger.info(f"   Group: {group_name}")
                    self.logger.info(f"   Stream: {stream_assignment}")
                    self.logger.info(f"   Version: {self.current_stream_version}")
                    self.logger.info(f"   Final URL: {self.current_stream_url}")
                    return True
                
                elif status == "waiting_for_group_assignment":
                    # Admin hasn't assigned client to a group yet
                    self.logger.info(f"📋 {message}")
                    self.logger.info(f"    ➜ Admin: Use /assign_client_to_group to assign '{self.hostname}' to a group")
                    retry_count = 0  # Don't count this as a failure
                
                elif status == "waiting_for_stream_assignment":
                    # Client is in a group but no stream assigned yet
                    group_id = data.get('group_id', 'unknown')
                    self.logger.info(f"📋 {message}")
                    self.logger.info(f"    ➜ Admin: Assign '{self.hostname}' to a stream in group '{group_id}'")
                    self.logger.info(f"    ➜ Use /assign_client_stream or /auto_assign_group_clients")
                    retry_count = 0  # Don't count this as a failure
                
                elif status == "waiting_for_streaming":
                    # Client assigned but streaming not started yet
                    group_name = data.get('group_name', 'unknown')
                    stream_assignment = data.get('stream_assignment', 'unknown')
                    self.logger.info(f"📋 {message}")
                    self.logger.info(f"    ➜ Assigned to group '{group_name}', stream '{stream_assignment}'")
                    self.logger.info(f"    ➜ Admin: Start streaming with /start_multi_video_srt or /start_group_srt")
                    retry_count = 0  # Don't count this as a failure
                
                elif status == "group_not_running":
                    # Docker container not running
                    group_name = data.get('group_name', 'unknown')
                    self.logger.warning(f"⚠️ {message}")
                    self.logger.info(f"    ➜ Admin: Start Docker container for group '{group_name}'")
                    retry_count = 0  # Don't count this as a failure
                
                elif status == "not_registered":
                    # Client somehow got unregistered
                    self.logger.error(f"❌ {message}")
                    return False
                
                else:
                    self.logger.warning(f"⚠️ Unexpected status: {status} - {message}")
                    retry_count += 1
                
                # Use shutdown event for interruptible sleep
                if self._shutdown_event.wait(timeout=self.retry_interval):
                    self.logger.info("🛑 Shutdown requested during wait")
                    return False
                
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"🌐 Network error ({retry_count + 1}/{self.max_retries}): {e}")
                retry_count += 1
                if self._shutdown_event.wait(timeout=self.retry_interval * 2):
                    self.logger.info("🛑 Shutdown requested during error wait")
                    return False
            except Exception as e:
                self.logger.error(f"❌ Unexpected error: {e}")
                retry_count += 1
                if self._shutdown_event.wait(timeout=self.retry_interval):
                    self.logger.info("🛑 Shutdown requested during error wait")
                    return False
        
        if retry_count >= self.max_retries:
            self.logger.error("❌ Max retries reached, giving up")
            return False
        
        return False  # This should only happen if self.running becomes False

    def _check_for_stream_change(self) -> bool:
        """
        Check if the stream URL or version has changed on the server
        Only returns True for actual content changes or stream stoppage
        
        Returns:
            True if stream has meaningfully changed, False otherwise
        """
        try:
            response = requests.post(
                f"{self.server_url}/wait_for_stream",
                json={"client_id": self.hostname},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status')
                
                # Log the response for debugging
                self.logger.debug(f"🔍 Stream check - Status: {status}")
                
                if status == "ready_to_play":
                    new_stream_url = self.fix_stream_url(data.get('stream_url'))
                    new_stream_version = data.get('stream_version')
                    
                    # Only check for meaningful changes
                    
                    # 1. Check if stream URL actually changed (different content)
                    url_changed = (new_stream_url and 
                                 self.current_stream_url and 
                                 new_stream_url != self.current_stream_url)
                    
                    # 2. Check if version changed (only if server provides versions)
                    version_changed = False
                    if (new_stream_version is not None and 
                        self.current_stream_version is not None):
                        version_changed = new_stream_version != self.current_stream_version
                    
                    # 3. Log what we found
                    if url_changed or version_changed:
                        self.logger.info(f"🔄 Meaningful stream change detected:")
                        if url_changed:
                            self.logger.info(f"   URL changed: {self.current_stream_url} → {new_stream_url}")
                        if version_changed:
                            self.logger.info(f"   Version changed: {self.current_stream_version} → {new_stream_version}")
                        
                        # Update our tracking
                        self.current_stream_url = new_stream_url
                        if new_stream_version is not None:
                            self.current_stream_version = new_stream_version
                        return True
                    else:
                        # No meaningful changes - stream is stable
                        self.logger.debug(f"🔍 Stream stable - no changes needed")
                        return False
                        
                elif status in ["waiting_for_streaming", "group_not_running", "not_registered"]:
                    # These indicate the stream/group has stopped
                    self.logger.info(f"🛑 Stream stopped on server side: {status}")
                    return True
                    
                elif status in ["waiting_for_group_assignment", "waiting_for_stream_assignment"]:
                    # These are assignment states - don't restart if we're already playing
                    self.logger.debug(f"🔍 Server in assignment state: {status} - keeping current stream")
                    return False
                    
                else:
                    # Unknown status - log but don't restart
                    self.logger.warning(f"⚠️ Unknown server status: {status} - keeping current stream")
                    return False
                    
            else:
                # Server error - don't restart, just log
                self.logger.debug(f"🔍 Server returned {response.status_code} - keeping current stream")
                return False
            
        except Exception as e:
            # Network/other errors - don't restart
            self.logger.debug(f"🔍 Stream check failed (keeping current stream): {e}")
            return False

    def play_stream(self) -> bool:
        """Start playing the assigned stream with C++ player or ffplay fallback"""
        if not self.current_stream_url:
            self.logger.error("❌ No stream URL available")
            return False
            
        try:
            self.stop_stream()  # Clean up any existing player
            
            if self.player_executable and os.path.exists(self.player_executable):
                return self._play_with_cpp_player()
            else:
                self.logger.warning("⚠️ C++ player not available, falling back to ffplay")
                return self._play_with_ffplay()
                
        except Exception as e:
            self.logger.error(f"❌ Player error: {e}")
            return False

    def _play_with_cpp_player(self) -> bool:
        """Start playing with the built C++ player"""
        try:
            self.logger.info(f"🎬 Starting C++ video player...")
            self.logger.info(f"🔗 Connecting to: {self.current_stream_url}")
            self.logger.info(f"📱 Stream version: {self.current_stream_version}")
            
            # Set environment variables if needed
            env = os.environ.copy()
            
            cmd = [self.player_executable, self.current_stream_url]
            
            # Capture both stdout and stderr for debugging
            self.player_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout
                env=env,
                cwd=self.build_dir or os.path.dirname(self.player_executable),
                universal_newlines=True,
                bufsize=1  # Line buffered
            )
            
            # Start a thread to monitor C++ player output
            def monitor_cpp_output():
                try:
                    for line in iter(self.player_process.stdout.readline, ''):
                        if line.strip():
                            # Log each frame and telemetry data from C++ player
                            if "TELEMETRY:" in line:
                                self.logger.info(f"🎯 {line.strip()}")
                            elif "FRAME_#" in line:
                                self.logger.debug(f"📺 {line.strip()}")
                            elif "STATS_REPORT:" in line:
                                self.logger.info(f"📊 {line.strip()}")
                            elif "FREEZE_DETECTED:" in line:
                                self.logger.error(f"🚨 {line.strip()}")
                            elif "ERROR" in line.upper() or "error" in line:
                                self.logger.error(f"❌ C++ Player: {line.strip()}")
                            elif "WARNING" in line.upper() or "warning" in line or "warn" in line:
                                self.logger.warning(f"⚠️ C++ Player: {line.strip()}")
                            else:
                                self.logger.debug(f"🔧 C++ Player: {line.strip()}")
                except Exception as e:
                    self.logger.error(f"❌ Error monitoring C++ output: {e}")
                finally:
                    if self.player_process and self.player_process.stdout:
                        self.player_process.stdout.close()
            
            output_thread = threading.Thread(target=monitor_cpp_output, daemon=True)
            output_thread.start()
            
            self.logger.info(f"✅ C++ Player started (PID: {self.player_process.pid})")
            self.logger.info("🎥 Video should be playing now!")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ C++ Player error: {e}")
            return False

    def _play_with_ffplay(self) -> bool:
        """Fallback to ffplay if C++ player not available"""
        try:
            self.logger.info(f"🎬 Starting ffplay fallback...")
            self.logger.info(f"🔗 Connecting to: {self.current_stream_url}")
            self.logger.info(f"📱 Stream version: {self.current_stream_version}")
            
            cmd = [
                "ffplay",
                "-fflags", "nobuffer",
                "-flags", "low_delay",
                "-framedrop",
                "-strict", "experimental",
                "-autoexit",  # Exit when stream ends
                self.current_stream_url
            ]
            
            self.player_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.logger.info(f"✅ ffplay started (PID: {self.player_process.pid})")
            self.logger.info("🎥 Video should be playing now!")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ ffplay error: {e}")
            return False

    def monitor_player(self) -> str:
        """
        Monitor the player process and check for stream changes
        
        Returns:
            String indicating why player stopped: 'stream_ended', 'connection_lost', 'user_exit', 'error', 'stream_changed'
        """
        if not self.player_process:
            return 'error'
        
        self.logger.info("🔄 Monitoring video player...")
        
        # Check for stream changes every 10 seconds
        last_stream_check = time.time()
        stream_check_interval = 10  # seconds
        last_health_report = time.time()
        health_report_interval = 30  # seconds
        
        while self.running and not self._shutdown_event.is_set() and self.player_process.poll() is None:
            current_time = time.time()
            
            # Periodically check if stream URL has changed
            if current_time - last_stream_check >= stream_check_interval:
                if self._check_for_stream_change():
                    self.logger.info("🔄 Stream change detected, restarting player...")
                    self.stop_stream()
                    return 'stream_changed'
                last_stream_check = current_time
            
            # Periodic health report
            if current_time - last_health_report >= health_report_interval:
                self.logger.info(f"💓 Player health check: PID={self.player_process.pid}, Running for {int(current_time - last_health_report)}s")
                last_health_report = current_time
            
            # Check for shutdown with shorter sleep to be more responsive
            if self._shutdown_event.wait(timeout=1):
                self.logger.info("🛑 Shutdown requested during player monitoring")
                self.stop_stream()
                return 'user_exit'
        
        # Player has stopped, determine why
        if self._shutdown_event.is_set() or not self.running:
            return 'user_exit'
        
        exit_code = self.player_process.returncode if self.player_process else -1
        
        if exit_code == 0:
            self.logger.info("📺 Stream ended normally")
            return 'stream_ended'
        elif exit_code == 1:
            self.logger.warning("⚠️ Connection lost or stream unavailable")
            return 'connection_lost'
        else:
            self.logger.error(f"❌ Player exited with error code: {exit_code}")
            return 'error'

    def stop_stream(self):
        """Stop the player if running with comprehensive cleanup"""
        if self.player_process:
            try:
                pid = self.player_process.pid
                self.logger.info(f"🛑 Stopping player (PID: {pid})")
                
                # Step 1: Send SIGTERM for graceful shutdown
                self.player_process.terminate()
                
                try:
                    # Wait up to 3 seconds for graceful termination
                    self.player_process.wait(timeout=3)
                    self.logger.info("✅ Player stopped gracefully")
                except subprocess.TimeoutExpired:
                    # Step 2: Force kill if still running
                    self.logger.warning("⚠️ Player didn't stop gracefully, sending SIGKILL")
                    self.player_process.kill()
                    
                    try:
                        # Wait up to 2 more seconds after SIGKILL
                        self.player_process.wait(timeout=2)
                        self.logger.info("✅ Player force-killed successfully")
                    except subprocess.TimeoutExpired:
                        self.logger.error(f"❌ Player process {pid} is unresponsive, may be zombie")
                        
                        # Step 3: Try system-level kill as last resort
                        try:
                            os.kill(pid, signal.SIGKILL)
                            time.sleep(0.5)
                            self.logger.warning(f"⚠️ Used system kill on PID {pid}")
                        except (OSError, ProcessLookupError):
                            # Process might already be dead
                            pass
                
            except (OSError, ProcessLookupError):
                # Process already terminated
                self.logger.debug("🔍 Player process already terminated")
            except Exception as e:
                self.logger.error(f"❌ Error stopping player: {e}")
            finally:
                self.player_process = None
                
                # Additional cleanup: Kill any orphaned ffmpeg/player processes
                self._kill_orphaned_processes()
    
    def _kill_orphaned_processes(self):
        """Kill any orphaned video processes that might still be running"""
        try:
            import psutil
            current_pid = os.getpid()
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    # Look for our player processes
                    if (proc.info['name'] in ['player', 'ffplay', 'ffmpeg'] and 
                        proc.info['pid'] != current_pid):
                        
                        # Check if it's our stream URL in the command line
                        cmdline = ' '.join(proc.info['cmdline'] or [])
                        if (self.current_stream_url and 
                            (self.server_ip in cmdline or 'srt://' in cmdline)):
                            self.logger.warning(f"🧹 Killing orphaned process: {proc.info['name']} (PID: {proc.info['pid']})")
                            proc.kill()
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        except ImportError:
            # psutil not available, use basic approach
            try:
                # Try to kill any processes with our stream URL
                if self.current_stream_url and self.server_ip:
                    import subprocess
                    result = subprocess.run(['pgrep', '-f', self.server_ip], 
                                          capture_output=True, text=True)
                    if result.returncode == 0:
                        pids = result.stdout.strip().split('\n')
                        for pid in pids:
                            if pid.strip() and pid.strip() != str(os.getpid()):
                                try:
                                    os.kill(int(pid.strip()), signal.SIGKILL)
                                    self.logger.warning(f"🧹 Killed process PID: {pid}")
                                except (OSError, ValueError):
                                    pass
            except Exception as e:
                self.logger.debug(f"🔍 Orphan cleanup failed: {e}")

    def _emergency_cleanup(self):
        """Emergency cleanup function for atexit"""
        if self.running:
            self.stop_stream()
            self.cleanup()

    def cleanup(self):
        """Clean up build directory and other resources"""
        try:
            if self.build_dir and os.path.exists(self.build_dir):
                shutil.rmtree(self.build_dir)
                self.logger.debug(f"🧹 Cleaned up build directory: {self.build_dir}")
        except Exception as e:
            self.logger.warning(f"⚠️ Error cleaning up: {e}")

    def run(self):
        """Main execution flow with stream restart capability and graceful shutdown"""
        if not self.register():
            return
            
        try:
            while self.running and not self._shutdown_event.is_set():
                self.logger.info("⏳ Waiting for admin assignment...")
                self.logger.info("📝 Admin needs to:")
                self.logger.info("   1. Assign this client to a group")
                self.logger.info("   2. Assign this client to a specific stream")
                self.logger.info("   3. Start streaming for the group")
                
                # Wait for stream assignment
                if self.wait_for_assignment():
                    if self._shutdown_event.is_set():
                        break
                        
                    if self.play_stream():
                        # Monitor the player and handle when it stops
                        stop_reason = self.monitor_player()
                        
                        if stop_reason == 'user_exit':
                            self.logger.info("👋 User requested exit")
                            break
                        elif stop_reason == 'stream_changed':
                            self.logger.info("🔄 Stream changed, restarting with new content...")
                            # Continue the loop to restart with new stream
                            continue
                        elif stop_reason in ['stream_ended', 'connection_lost', 'error']:
                            self.logger.info("🔄 Stream stopped, waiting for new assignment...")
                            self.current_stream_url = None  # Clear current stream
                            self.current_stream_version = None
                            # Continue the loop to wait for new assignment
                        else:
                            self.logger.warning(f"⚠️ Unexpected stop reason: {stop_reason}")
                            break
                    else:
                        self.logger.error("❌ Failed to start video player")
                        self.logger.info("⏳ Retrying in 10 seconds...")
                        
                        # Interruptible sleep
                        if self._shutdown_event.wait(timeout=10):
                            break
                        # Continue the loop to retry
                else:
                    self.logger.info("⏳ Assignment failed, retrying in 10 seconds...")
                    
                    # Interruptible sleep
                    if self._shutdown_event.wait(timeout=10):
                        break
                    # Continue the loop to retry
                    
        except Exception as e:
            self.logger.error(f"❌ Unexpected error in main loop: {e}")
        finally:
            self.logger.info("🔄 Performing final cleanup...")
            self.running = False
            self.stop_stream()
            self.cleanup()
            self.logger.info("👋 Client stopped cleanly")

def main():
    parser = argparse.ArgumentParser(description='Multi-Screen Display Client with C++ Player and Graceful Shutdown')
    parser.add_argument('--server', required=True, help='Server URL (e.g., http://128.205.39.64:5001)')
    parser.add_argument('--hostname', help='Custom client ID (default: auto-generated)')
    parser.add_argument('--name', help='Display name for admin interface')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--force-ffplay', action='store_true', help='Force use of ffplay instead of C++ player')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    client = MultiScreenClient(
        server_url=args.server,
        hostname=args.hostname,
        display_name=args.name
    )
    
    # Override player if forced
    if args.force_ffplay:
        client.logger.info("🔧 Forcing ffplay usage")
        client.player_executable = None
    
    try:
        client.run()
    except KeyboardInterrupt:
        # This should be handled by signal handlers now, but keep as backup
        print("\n🛑 Keyboard interrupt received...")
        client.shutdown()
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        client.shutdown()

if __name__ == "__main__":
    main()
