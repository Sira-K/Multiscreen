import argparse
import requests
import time
import logging
import subprocess
import sys
import json
from typing import Optional

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

class MultiScreenClient:
    def __init__(self, server_url: str, hostname: str = None, display_name: str = None):
        """
        Multi-screen client that follows proper registration and assignment workflow
        
        Args:
            server_url: Server URL (e.g., "http://127.0.0.1:5000")
            hostname: Unique client identifier
            display_name: Friendly display name
        """
        self.server_url = server_url.rstrip('/')
        self.hostname = hostname or f"client-{int(time.time())}"
        self.display_name = display_name or f"Display Client {self.hostname}"
        self.assigned_group_id = None
        self.current_stream_url = None
        self.player_process = None
        self.running = False
        self.check_interval = 5  # seconds
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        self.logger = logging.getLogger(__name__)

    def register_with_backend(self) -> bool:
        """Step 1: Register client with backend server"""
        try:
            self.logger.info(f"🔄 Registering client '{self.display_name}' with backend...")
            
            response = requests.post(
                f"{self.server_url}/register_client",
                json={
                    "hostname": self.hostname,
                    "ip_address": "127.0.0.1",  # Client IP
                    "display_name": self.display_name
                },
                timeout=10
            )
            
            if response.status_code == 200:
                self.logger.info(f"✅ Successfully registered client: {self.hostname}")
                data = response.json()
                self.logger.info(f"📝 Registration response: {data.get('message', 'Registered')}")
                return True
            else:
                self.logger.error(f"❌ Registration failed ({response.status_code}): {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Registration error: {e}")
            return False

    def wait_for_group_assignment(self) -> Optional[str]:
        """Step 2: Wait for admin to assign this client to a group"""
        self.logger.info(f"⏳ Waiting for group assignment...")
        self.logger.info(f"💡 Admin can assign this client using the web interface or API")
        
        while self.running:
            try:
                # Check all clients to see if this one is assigned
                response = requests.get(
                    f"{self.server_url}/get_clients",
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    clients = data.get("clients", [])
                    
                    # Find our client in the list
                    for client in clients:
                        if client.get("client_id") == self.hostname or client.get("hostname") == self.hostname:
                            # Check if client is assigned to a group
                            group_id = client.get("group_id")
                            if group_id:
                                group_name = client.get("group_name", group_id)
                                self.assigned_group_id = group_id
                                
                                self.logger.info(f"✅ Assigned to group: {group_name} (ID: {group_id})")
                                return group_id
                            else:
                                self.logger.info(f"⏳ Still waiting for group assignment...")
                                break
                    else:
                        self.logger.info(f"⏳ Client not found in registered clients list...")
                        
                else:
                    self.logger.warning(f"⚠️ Failed to get clients: {response.text}")
                
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                self.logger.info("🛑 Interrupted by user")
                self.running = False
                return None
            except Exception as e:
                self.logger.warning(f"⚠️ Error checking assignment: {e}")
                time.sleep(self.check_interval)
        
        return None

    def wait_for_group_streaming(self, group_id: str) -> Optional[str]:
        """Step 3: Wait for the assigned group to start streaming"""
        self.logger.info(f"⏳ Waiting for group {group_id} to start streaming...")
        
        while self.running:
            try:
                # Check all groups to find our assigned group
                response = requests.get(
                    f"{self.server_url}/get_groups",
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    groups = data.get("groups", [])
                    
                    self.logger.debug(f"🔍 Checking {len(groups)} groups for group_id: {group_id}")
                    
                    # Find our group in the list
                    target_group = None
                    for group in groups:
                        if group.get("id") == group_id:
                            target_group = group
                            break
                    
                    if target_group:
                        group_name = target_group.get("name", group_id)
                        
                        # Check if group Docker is running
                        docker_running = target_group.get("docker_running", False)
                        if not docker_running:
                            self.logger.info(f"⏳ Group '{group_name}' Docker container not running...")
                            time.sleep(self.check_interval)
                            continue
                        
                        # Check if there are any FFmpeg processes running (indicating streaming)
                        # This is a better indicator than docker_running alone
                        self.logger.info(f"✅ Group '{group_name}' Docker is running, checking for active streams...")
                        
                        # Try to get stream URL and connect
                        stream_url = self.build_stream_url_from_group(target_group)
                        if stream_url:
                            # Test the connection by trying to start the player
                            if self.test_stream_availability(stream_url):
                                self.logger.info(f"🎯 Stream is available!")
                                return stream_url
                            else:
                                self.logger.info(f"⏳ Stream not yet ready, waiting...")
                        else:
                            self.logger.error(f"❌ Could not build stream URL for group")
                    else:
                        self.logger.warning(f"⚠️ Group {group_id} not found in groups list")
                        # Debug: show available groups
                        available_groups = [g.get("id", "unknown") for g in groups]
                        self.logger.debug(f"Available groups: {available_groups}")
                else:
                    self.logger.warning(f"⚠️ Failed to get groups: {response.text}")
                
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                self.logger.info("🛑 Interrupted by user")
                self.running = False
                return None
            except Exception as e:
                self.logger.warning(f"⚠️ Error checking group status: {e}")
                time.sleep(self.check_interval)
        
        return None

    def test_stream_availability(self, stream_url: str) -> bool:
        """Test if SRT stream is actually available by trying ffprobe"""
        try:
            # Quick test with ffprobe to see if stream is available
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-timeout", "2000000",  # 2 second timeout
                stream_url
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=3)
            return result.returncode == 0
            
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            # If ffprobe not available or times out, assume stream might be ready
            # The actual player will handle connection issues
            return True

    def build_stream_url_from_group(self, group_data: dict) -> Optional[str]:
        """Build SRT stream URL from group data (updated for new structure)"""
        try:
            self.logger.debug(f"🔍 Building stream URL from group data: {group_data}")
            
            # Get SRT port from group ports
            ports = group_data.get("ports", {})
            srt_port = ports.get("srt_port", 10081)
            group_name = group_data.get("name", "unknown")
            group_id = group_data.get("id", "unknown")
            
            self.logger.info(f"📡 Group: {group_name}, SRT Port: {srt_port}")
            
            # Extract server IP
            server_ip = self.server_url.split('//')[1].split(':')[0]
            
            # Try to get the actual stream ID from your streaming system
            # First, try to get the stream status from the backend
            stream_id = self.get_active_stream_id(group_id, group_name)
            
            if stream_id:
                stream_url = f"srt://{server_ip}:{srt_port}?streamid=#!::r=live/{group_name}/{stream_id},m=request,latency=5000000"
                self.logger.info(f"🎯 Built stream URL with ID: {stream_url}")
            else:
                # Fallback to simple format
                stream_url = f"srt://{server_ip}:{srt_port}?streamid=#!::r=live/{group_name}/test,m=request,latency=5000000"
                self.logger.info(f"🎯 Built fallback stream URL: {stream_url}")
            
            return stream_url
            
        except Exception as e:
            self.logger.error(f"❌ Error building stream URL: {e}")
            return None

    def get_active_stream_id(self, group_id: str, group_name: str) -> Optional[str]:
        """Try to get the active stream ID from the backend"""
        try:
            # Try to use the stream status endpoint if it exists
            response = requests.get(
                f"{self.server_url}/get_group_status",
                params={"group_id": group_id},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                groups = data.get("groups", {})
                if group_id in groups:
                    group = groups[group_id]
                    persistent_streams = group.get("persistent_streams", {})
                    stream_id = persistent_streams.get("test")
                    if stream_id:
                        self.logger.info(f"🔑 Found stream ID: {stream_id}")
                        return stream_id
            
            # If that doesn't work, try a different approach
            # Check the ffmpeg processes to extract the stream ID
            self.logger.debug("Trying to extract stream ID from system processes...")
            return self.extract_stream_id_from_processes(group_name)
            
        except Exception as e:
            self.logger.debug(f"Could not get stream ID: {e}")
            return None

    def extract_stream_id_from_processes(self, group_name: str) -> Optional[str]:
        """Try to extract stream ID from running ffmpeg processes"""
        try:
            if not PSUTIL_AVAILABLE:
                self.logger.debug("psutil not available, cannot extract stream ID")
                return None
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] and 'ffmpeg' in proc.info['name'].lower():
                        cmdline = ' '.join(proc.info['cmdline'] or [])
                        
                        # Look for the group name in the command line
                        if group_name in cmdline and 'live/' in cmdline:
                            # Extract stream ID from SRT URL
                            import re
                            match = re.search(rf'live/{group_name}/([^,\s]+)', cmdline)
                            if match:
                                stream_id = match.group(1)
                                self.logger.info(f"🔍 Extracted stream ID from process: {stream_id}")
                                return stream_id
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Error extracting stream ID: {e}")
            return None



    def play_stream(self, stream_url: str) -> bool:
        """Step 4: Start playing the SRT stream"""
        try:
            self.stop_stream()  # Clean up any existing player
            
            self.logger.info(f"🎬 Starting SRT player...")
            
            # Try custom player first
            cmd = [
                "./cmake-build-debug/player/player",
                stream_url
            ]
            
            try:
                self.player_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                self.logger.info(f"✅ Custom player started (PID: {self.player_process.pid})")
                return True
            except FileNotFoundError:
                # Fallback to ffplay
                self.logger.info("Custom player not found, using ffplay...")
                cmd = [
                    "ffplay",
                    "-fflags", "nobuffer",
                    "-flags", "low_delay",
                    "-framedrop",
                    "-strict", "experimental",
                    "-loglevel", "quiet",
                    stream_url
                ]
                self.player_process = subprocess.Popen(cmd)
                self.logger.info(f"✅ FFplay started (PID: {self.player_process.pid})")
                return True
            
        except Exception as e:
            self.logger.error(f"❌ Player error: {e}")
            return False

    def stop_stream(self):
        """Stop the player if running"""
        if self.player_process:
            try:
                self.logger.info("🛑 Stopping player...")
                self.player_process.terminate()
                self.player_process.wait(timeout=5)
                self.logger.info("✅ Player stopped")
            except subprocess.TimeoutExpired:
                self.logger.warning("⚠️ Force killing player...")
                self.player_process.kill()
            except Exception as e:
                self.logger.warning(f"⚠️ Error stopping player: {e}")
            finally:
                self.player_process = None

    def monitor_stream(self):
        """Monitor the stream and handle disconnections"""
        self.logger.info("👀 Monitoring stream...")
        
        while self.running:
            try:
                if self.player_process:
                    # Check if player is still running
                    if self.player_process.poll() is not None:
                        exit_code = self.player_process.returncode
                        self.logger.warning(f"⚠️ Player exited with code {exit_code}")
                        
                        if exit_code != 0:
                            self.logger.info("🔄 Attempting to restart stream...")
                            # Wait for stream to be available again
                            if self.assigned_group_id:
                                stream_url = self.wait_for_group_streaming(self.assigned_group_id)
                                if stream_url:
                                    self.play_stream(stream_url)
                                else:
                                    break
                            else:
                                break
                        else:
                            break  # Clean exit
                else:
                    break
                
                time.sleep(1)
                
            except KeyboardInterrupt:
                self.logger.info("🛑 Interrupted by user")
                break
            except Exception as e:
                self.logger.error(f"❌ Error monitoring stream: {e}")
                break

    def run(self):
        """Main execution flow"""
        self.logger.info("🚀 Starting Multi-Screen Display Client")
        self.running = True
        
        try:
            # Step 1: Register with backend
            if not self.register_with_backend():
                self.logger.error("❌ Failed to register with backend")
                return
            
            # Step 2: Wait for group assignment
            group_id = self.wait_for_group_assignment()
            if not group_id:
                self.logger.error("❌ No group assignment received")
                return
            
            # Step 3: Wait for group to start streaming
            stream_url = self.wait_for_group_streaming(group_id)
            if not stream_url:
                self.logger.error("❌ No stream available")
                return
            
            # Step 4: Start playing and monitor
            if self.play_stream(stream_url):
                self.monitor_stream()
            else:
                self.logger.error("❌ Failed to start player")
                
        except KeyboardInterrupt:
            self.logger.info("🛑 Interrupted by user")
        finally:
            self.running = False
            self.stop_stream()
            self.logger.info("✅ Client stopped")

def main():
    parser = argparse.ArgumentParser(description='Multi-Screen Display Client')
    parser.add_argument('--server', required=True, help='Server URL (e.g., http://127.0.0.1:5000)')
    parser.add_argument('--hostname', help='Custom client hostname')
    parser.add_argument('--name', help='Display name for this client')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    client = MultiScreenClient(
        server_url=args.server,
        hostname=args.hostname,
        display_name=args.name
    )
    
    client.run()

if __name__ == "__main__":
    main()


# Example usage:
# python client.py --server http://127.0.0.1:5000 --name "Conference Room Display"