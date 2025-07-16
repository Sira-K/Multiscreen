import argparse
import requests
import time
import logging
import subprocess
import sys
from typing import Optional

class MultiScreenClient:
    def __init__(self, server_url: str, hostname: str = None, display_name: str = None):
        """
        Auto-assigning client that always requests the full 'test' stream
        
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
        self.running = False
        self.retry_interval = 5  # seconds
        self.max_retries = 12    # max attempts (1 minute total)
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        self.logger = logging.getLogger(__name__)

    def register(self) -> bool:
        """Register client with server"""
        try:
            response = requests.post(
                f"{self.server_url}/register_client",
                json={
                    "hostname": self.hostname,
                    "display_name": self.display_name,
                    "platform": "python_auto_client"
                },
                timeout=10
            )
            if response.status_code == 200:
                self.logger.info(f"Registered as {self.hostname}")
                return True
            self.logger.error(f"Registration failed: {response.text}")
            return False
        except Exception as e:
            self.logger.error(f"Registration error: {e}")
            return False

    def auto_assign_stream(self, group_id: str) -> bool:
        """Automatically assign the full 'test' stream to this client"""
        try:
            server_ip = self.server_url.split('//')[1].split(':')[0]
            response = requests.post(
                f"{self.server_url}/assign_client_stream",
                json={
                    "client_id": self.hostname,
                    "group_id": group_id,
                    "stream_name": "test",  # Always request full stream
                    "srt_ip": server_ip
                },
                timeout=5
            )
            if response.status_code == 200:
                self.logger.info("Automatically assigned to full stream")
                return True
            self.logger.warning(f"Stream assignment failed: {response.text}")
            return False
        except Exception as e:
            self.logger.warning(f"Assignment error: {e}")
            return False

    def monitor_stream(self) -> bool:
        """Monitor status until stream is ready"""
        retry_count = 0
        self.running = True
        
        while self.running and retry_count < self.max_retries:
            try:
                # Check current status
                response = requests.post(
                    f"{self.server_url}/wait_for_stream",
                    json={"client_id": self.hostname},
                    timeout=10
                )
                
                if response.status_code != 200:
                    raise Exception(response.text)
                
                data = response.json()
                status = data.get('status')
                
                if status == "ready_to_play":
                    self.current_stream_url = data.get('stream_url')
                    self.logger.info(f"Stream ready: {self.current_stream_url}")
                    return True
                
                elif status == "waiting_for_stream_assignment":
                    if data.get('group_id'):
                        if not self.auto_assign_stream(data['group_id']):
                            retry_count += 1
                    else:
                        self.logger.warning("No group ID received")
                        retry_count += 1
                
                elif status in ["waiting_for_streaming", "group_not_running"]:
                    self.logger.info(data.get('message', status))
                    retry_count = 0  # Reset counter for expected waits
                
                else:
                    self.logger.warning(f"Unexpected status: {status}")
                    retry_count += 1
                
                time.sleep(self.retry_interval)
                
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Network error ({retry_count + 1}/{self.max_retries}): {e}")
                retry_count += 1
                time.sleep(self.retry_interval * 2)
            except KeyboardInterrupt:
                self.logger.info("Shutting down...")
                self.running = False
                return False
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
                retry_count += 1
                time.sleep(self.retry_interval)
        
        if retry_count >= self.max_retries:
            self.logger.error("Max retries reached, giving up")
        return False

    def play_stream(self) -> bool:
        """Start playing the current stream with ffplay"""
        if not self.current_stream_url:
            self.logger.error("No stream URL available")
            return False
            
        try:
            self.stop_stream()  # Clean up any existing player
            
            self.logger.info(f"Starting player for stream...")
            cmd = [
                "ffplay",
                "-fflags", "nobuffer",
                "-flags", "low_delay",
                "-framedrop",
                "-strict", "experimental",
                self.current_stream_url
            ]
            self.player_process = subprocess.Popen(cmd)
            self.logger.info(f"Player started (PID: {self.player_process.pid})")
            return True
            
        except Exception as e:
            self.logger.error(f"Player error: {e}")
            return False

    def stop_stream(self):
        """Stop the player if running"""
        if self.player_process:
            try:
                self.player_process.terminate()
                self.player_process.wait(timeout=2)
            except Exception as e:
                self.logger.warning(f"Error stopping player: {e}")
            finally:
                self.player_process = None

    def run(self):
        """Main execution flow"""
        if not self.register():
            return
            
        try:
            if self.monitor_stream():
                self.play_stream()
                # Keep running while player is active
                while (self.running and self.player_process and 
                       self.player_process.poll() is None):
                    time.sleep(1)
        finally:
            self.running = False
            self.stop_stream()
            self.logger.info("Client stopped")

def main():
    parser = argparse.ArgumentParser(description='Auto-Assigning Display Client')
    parser.add_argument('--server', required=True, help='Server URL')
    parser.add_argument('--hostname', help='Custom client ID')
    parser.add_argument('--name', help='Display name')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    client = MultiScreenClient(
        server_url=args.server,
        hostname=args.hostname,
        display_name=args.name
    )
    client.run()

if __name__ == "__main__":
    main()