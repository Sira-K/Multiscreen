import argparse
import requests
import time
import logging
import subprocess
import sys
from typing import Optional
from urllib.parse import urlparse

class MultiScreenClient:
    def __init__(self, server_url: str, hostname: str = None, display_name: str = None):
        """
        Client that waits for admin to assign it to a stream
        Automatically fixes stream URLs to use server IP instead of localhost
        
        Args:
            server_url: Server URL (e.g., "http://128.205.39.64:5001")
            hostname: Unique client identifier
            display_name: Friendly display name
        """
        self.server_url = server_url.rstrip('/')
        self.hostname = hostname or f"client-{int(time.time())}"
        self.display_name = display_name or self.hostname
        self.current_stream_url = None
        self.player_process = None
        self.running = True
        self.retry_interval = 5  # seconds
        self.max_retries = 60    # 5 minutes total wait time
        
        # Extract server IP from server URL for stream URL fixing
        parsed_url = urlparse(self.server_url)
        self.server_ip = parsed_url.hostname or "127.0.0.1"
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        self.logger = logging.getLogger(__name__)

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
            self.logger.info(f"✅ Stream URL already has correct IP: {stream_url}")
            return stream_url

    def register(self) -> bool:
        """Register client with server"""
        try:
            self.logger.info(f"🚀 Starting Multi-Screen Client: {self.hostname}")
            self.logger.info(f"🌐 Server: {self.server_url}")
            self.logger.info(f"🎯 Server IP: {self.server_ip}")
            
            response = requests.post(
                f"{self.server_url}/register_client",
                json={
                    "hostname": self.hostname,
                    "display_name": self.display_name,
                    "platform": "python_client_fixed_ip"
                },
                timeout=10
            )
            if response.status_code == 200:
                self.logger.info(f"✅ Registered as {self.hostname}")
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
        
        while self.running and retry_count < self.max_retries:
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
                    
                    group_name = data.get('group_name', 'unknown')
                    stream_assignment = data.get('stream_assignment', 'unknown')
                    
                    self.logger.info(f"🎉 Ready to play!")
                    self.logger.info(f"   Group: {group_name}")
                    self.logger.info(f"   Stream: {stream_assignment}")
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
                
                time.sleep(self.retry_interval)
                
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"🌐 Network error ({retry_count + 1}/{self.max_retries}): {e}")
                retry_count += 1
                time.sleep(self.retry_interval * 2)
            except KeyboardInterrupt:
                self.logger.info("👋 Shutting down...")
                self.running = False
                return False
            except Exception as e:
                self.logger.error(f"❌ Unexpected error: {e}")
                retry_count += 1
                time.sleep(self.retry_interval)
        
        if retry_count >= self.max_retries:
            self.logger.error("❌ Max retries reached, giving up")
            return False
        
        return False  # This should only happen if self.running becomes False

    def play_stream(self) -> bool:
        """Start playing the assigned stream with ffplay"""
        if not self.current_stream_url:
            self.logger.error("❌ No stream URL available")
            return False
            
        try:
            self.stop_stream()  # Clean up any existing player
            
            self.logger.info(f"🎬 Starting video player...")
            self.logger.info(f"🔗 Connecting to: {self.current_stream_url}")
            
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
            self.logger.info(f"✅ Player started (PID: {self.player_process.pid})")
            self.logger.info("🎥 Video should be playing now!")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Player error: {e}")
            return False

    def monitor_player(self) -> str:
        """
        Monitor the player process and return reason for stopping
        
        Returns:
            String indicating why player stopped: 'stream_ended', 'connection_lost', 'user_exit', 'error'
        """
        if not self.player_process:
            return 'error'
        
        self.logger.info("🔄 Monitoring video player...")
        
        while self.running and self.player_process.poll() is None:
            time.sleep(1)
        
        # Player has stopped, determine why
        exit_code = self.player_process.returncode
        
        if not self.running:
            return 'user_exit'
        elif exit_code == 0:
            self.logger.info("📺 Stream ended normally")
            return 'stream_ended'
        elif exit_code == 1:
            self.logger.warning("⚠️ Connection lost or stream unavailable")
            return 'connection_lost'
        else:
            self.logger.error(f"❌ Player exited with error code: {exit_code}")
            return 'error'

    def stop_stream(self):
        """Stop the player if running"""
        if self.player_process:
            try:
                self.player_process.terminate()
                self.player_process.wait(timeout=2)
            except Exception as e:
                self.logger.warning(f"⚠️ Error stopping player: {e}")
            finally:
                self.player_process = None

    def run(self):
        """Main execution flow with stream restart capability"""
        if not self.register():
            return
            
        try:
            while self.running:
                self.logger.info("⏳ Waiting for admin assignment...")
                self.logger.info("📝 Admin needs to:")
                self.logger.info("   1. Assign this client to a group")
                self.logger.info("   2. Assign this client to a specific stream")
                self.logger.info("   3. Start streaming for the group")
                
                # Wait for stream assignment
                if self.wait_for_assignment():
                    if self.play_stream():
                        # Monitor the player and handle when it stops
                        stop_reason = self.monitor_player()
                        
                        if stop_reason == 'user_exit':
                            self.logger.info("👋 User requested exit")
                            break
                        elif stop_reason in ['stream_ended', 'connection_lost', 'error']:
                            self.logger.info("🔄 Stream stopped, waiting for new assignment...")
                            self.current_stream_url = None  # Clear current stream
                            # Continue the loop to wait for new assignment
                        else:
                            self.logger.warning(f"⚠️ Unexpected stop reason: {stop_reason}")
                            break
                    else:
                        self.logger.error("❌ Failed to start video player")
                        self.logger.info("⏳ Retrying in 10 seconds...")
                        time.sleep(10)
                        # Continue the loop to retry
                else:
                    self.logger.info("⏳ Assignment failed, retrying in 10 seconds...")
                    time.sleep(10)
                    # Continue the loop to retry
                    
        except KeyboardInterrupt:
            self.logger.info("👋 Keyboard interrupt received")
        finally:
            self.running = False
            self.stop_stream()
            self.logger.info("👋 Client stopped")

def main():
    parser = argparse.ArgumentParser(description='Multi-Screen Display Client (Fixed IP)')
    parser.add_argument('--server', required=True, help='Server URL (e.g., http://128.205.39.64:5001)')
    parser.add_argument('--hostname', help='Custom client ID (default: auto-generated)')
    parser.add_argument('--name', help='Display name for admin interface')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    client = MultiScreenClient(
        server_url=args.server,
        hostname=args.hostname,
        display_name=args.name
    )
    
    try:
        client.run()
    except KeyboardInterrupt:
        print("\n👋 Shutting down client...")
        client.running = False
        client.stop_stream()

if __name__ == "__main__":
    main()
