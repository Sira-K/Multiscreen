import subprocess
import random
import time
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class SRTService:
    """Service for SRT connection testing and validation"""
    
    @staticmethod
    def wait_for_server(srt_ip: str, srt_port: int, timeout: int = 30) -> bool:
        """Wait for SRT server to be ready"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Check with netstat
                netstat_check = subprocess.run(
                    ["netstat", "-ln"], 
                    capture_output=True, 
                    text=True, 
                    timeout=5
                )
                
                if netstat_check.returncode == 0:
                    listening_ports = netstat_check.stdout
                    if f":{srt_port}" in listening_ports:
                        return True
                
                # Check with Docker
                try:
                    docker_check = subprocess.run(
                        ["docker", "ps", "--format", "table {{.Names}}\t{{.Ports}}", "--filter", f"publish={srt_port}"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    
                    if docker_check.returncode == 0 and docker_check.stdout.strip():
                        lines = docker_check.stdout.strip().split('\n')
                        if len(lines) > 1:
                            time.sleep(2)
                            return True
                    
                except Exception:
                    pass
                
            except subprocess.TimeoutExpired:
                pass
            except Exception:
                pass
            
            time.sleep(2)
        
        return False
    
    @staticmethod
    def test_connection(srt_ip: str, srt_port: int, group_name: str, sei: str, retry_count: int = 3) -> Dict[str, Any]:
        """Enhanced SRT connection test with retries and consistent parameters"""
        if '+' not in sei:
            sei = f"{sei}+000000"
        
        # Use consistent SRT parameters
        srt_params = "latency=5000000&connect_timeout=10000"
        
        for attempt in range(retry_count):
            test_stream_id = f"test_{random.randint(10000, 99999)}"
            
            test_cmd = [
                "ffmpeg",  # Assume ffmpeg is in PATH or will be resolved
                "-v", "error",
                "-y",
                "-f", "lavfi", "-i", f"testsrc=s=640x480:r=5:d={attempt+2}",
                "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency",
                "-bsf:v", f"h264_metadata=sei_user_data={sei}",
                "-f", "mpegts",
                f"srt://{srt_ip}:{srt_port}?streamid=#!::r=live/{group_name}/{test_stream_id},m=publish&{srt_params}"
            ]
            
            try:
                logger.info(f"SRT connection test attempt {attempt + 1}/{retry_count}")
                result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    logger.info("SRT connection test succeeded")
                    return {"success": True, "output": result.stdout}
                else:
                    logger.warning(f"SRT test attempt {attempt + 1} failed: {result.stderr}")
                    
                    if attempt < retry_count - 1:
                        time.sleep(2)
                        
            except subprocess.TimeoutExpired:
                logger.warning(f"SRT test attempt {attempt + 1} timed out")
                if attempt < retry_count - 1:
                    time.sleep(1)
            except Exception as e:
                logger.error(f"SRT test error: {e}")
        
        return {
            "success": False,
            "error": "All connection attempts failed",
            "retry_count": retry_count
        }