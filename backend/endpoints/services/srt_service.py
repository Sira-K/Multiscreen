"""
SRT Service

Simple SRT connection testing for streaming operations.
"""

import socket
import time
import logging
import subprocess
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class SRTService:
    """Service for SRT connection testing"""
    
    @classmethod
    def test_connection(cls, srt_ip: str, srt_port: int, 
                       group_name: str = "unknown", sei: str = None) -> Dict:
        """Test SRT connection to a server"""
        try:
            logger.info(f"Testing SRT connection to {srt_ip}:{srt_port}")
            
            # Test basic socket connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)
            
            try:
                # Try to connect to the port
                sock.connect((srt_ip, srt_port))
                logger.info(f"✅ Socket connection successful to {srt_ip}:{srt_port}")
                sock.close()
                
                # Test with FFmpeg if available
                ffmpeg_test = cls._test_with_ffmpeg(srt_ip, srt_port, group_name, sei)
                if ffmpeg_test["success"]:
                    return {
                        "success": True,
                        "message": f"SRT connection test passed for {group_name}",
                        "ip": srt_ip,
                        "port": srt_port,
                        "ffmpeg_test": ffmpeg_test
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Socket connection works but FFmpeg test failed",
                        "ip": srt_ip,
                        "port": srt_port,
                        "ffmpeg_test": ffmpeg_test
                    }
                    
            except socket.error as e:
                logger.error(f"❌ Socket connection failed: {e}")
                return {
                    "success": False,
                    "message": f"Socket connection failed: {e}",
                    "ip": srt_ip,
                    "port": srt_port,
                    "error": str(e)
                }
                
        except Exception as e:
            logger.error(f"SRT connection test error: {e}")
            return {
                "success": False,
                "message": f"Connection test error: {e}",
                "ip": srt_ip,
                "port": srt_port,
                "error": str(e)
            }
    
    @classmethod
    def wait_for_server(cls, srt_ip: str, srt_port: int, timeout: int = 5) -> bool:
        """Wait for SRT server to become available (optimized for speed)"""
        logger.info(f"🔍 Waiting for SRT server at {srt_ip}:{srt_port} (timeout: {timeout}s)")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                result = cls.test_connection(srt_ip, srt_port)
                if result["success"]:
                    logger.info(f"✅ SRT server is ready at {srt_ip}:{srt_port}")
                    return True
                    
                time.sleep(1)  # Faster polling
                
            except Exception as e:
                logger.debug(f"SRT server check failed: {e}")
                time.sleep(1)  # Faster polling
        
        logger.error(f"❌ SRT server not ready after {timeout} seconds")
        return False
    
    @classmethod
    def monitor_srt_server(cls, srt_ip: str, srt_port: int, timeout: int = 5) -> Dict[str, any]:
        """
        Fast SRT server monitoring with detailed status
        
        Args:
            srt_ip: SRT server IP address
            srt_port: SRT server port
            timeout: Maximum time to wait in seconds
            
        Returns:
            Dict with monitoring results:
            {
                "success": bool,
                "ready": bool,
                "message": str,
                "response_time_ms": float,
                "details": Dict
            }
        """
        logger.info(f"🔍 Fast SRT monitoring: {srt_ip}:{srt_port} (timeout: {timeout}s)")
        
        start_time = time.time()
        check_count = 0
        
        while time.time() - start_time < timeout:
            check_count += 1
            check_start = time.time()
            
            try:
                # Fast UDP port check
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(0.5)  # Very fast timeout
                
                try:
                    # Quick connection test
                    sock.connect((srt_ip, srt_port))
                    response_time = (time.time() - check_start) * 1000  # Convert to milliseconds
                    
                    logger.info(f"✅ SRT server ready in {response_time:.1f}ms (check #{check_count})")
                    sock.close()
                    
                    return {
                        "success": True,
                        "ready": True,
                        "message": f"SRT server ready in {response_time:.1f}ms",
                        "response_time_ms": response_time,
                        "checks_performed": check_count,
                        "total_time_ms": (time.time() - start_time) * 1000,
                        "details": {
                            "ip": srt_ip,
                            "port": srt_port,
                            "final_check": check_count
                        }
                    }
                    
                except socket.error as e:
                    if "refused" in str(e).lower():
                        # Port is closed/rejected - server definitely not ready
                        logger.debug(f"Port {srt_port} rejected connection (check #{check_count})")
                    else:
                        logger.debug(f"Port {srt_port} check failed (check #{check_count}): {e}")
                        
                finally:
                    sock.close()
                    
            except Exception as e:
                logger.debug(f"SRT check error (check #{check_count}): {e}")
            
            # Fast polling interval
            time.sleep(0.5)
        
        # Timeout reached
        total_time = (time.time() - start_time) * 1000
        logger.error(f"❌ SRT server not ready after {timeout}s ({total_time:.1f}ms, {check_count} checks)")
        
        return {
            "success": False,
            "ready": False,
            "message": f"SRT server not ready after {timeout}s",
            "response_time_ms": None,
            "checks_performed": check_count,
            "total_time_ms": total_time,
            "details": {
                "ip": srt_ip,
                "port": srt_port,
                "timeout": timeout,
                "final_check": check_count
            }
        }
    
    @classmethod
    def _test_with_ffmpeg(cls, srt_ip: str, srt_port: int, 
                          group_name: str, sei: str = None) -> Dict:
        """Test SRT connection using FFmpeg"""
        try:
            # Simple FFmpeg test command
            test_cmd = [
                "ffmpeg",
                "-f", "lavfi",
                "-i", "testsrc=duration=1:size=320x240:rate=1",
                "-c:v", "libx264",
                "-t", "1",
                "-f", "mpegts",
                f"srt://{srt_ip}:{srt_port}?streamid=#!::r=test/{group_name},m=publish"
            ]
            
            logger.info(f"Testing SRT with FFmpeg: {' '.join(test_cmd[:5])}...")
            
            # Run FFmpeg test
            result = subprocess.run(
                test_cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "message": "FFmpeg SRT test successful",
                    "output": result.stdout
                }
            else:
                return {
                    "success": False,
                    "message": "FFmpeg SRT test failed",
                    "error": result.stderr,
                    "return_code": result.returncode
                }
                
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "message": "FFmpeg SRT test timed out",
                "error": "Timeout"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"FFmpeg SRT test error: {e}",
                "error": str(e)
            }
    
    @classmethod
    def get_srt_status(cls, srt_ip: str, srt_port: int) -> Dict:
        """Get SRT server status"""
        try:
            # Test connection
            connection_test = cls.test_connection(srt_ip, srt_port)
            
            # Check if port is listening
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2)
            
            try:
                sock.connect((srt_ip, srt_port))
                port_status = "listening"
                sock.close()
            except socket.error:
                port_status = "not_listening"
            
            return {
                "ip": srt_ip,
                "port": srt_port,
                "port_status": port_status,
                "connection_test": connection_test,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Failed to get SRT status: {e}")
            return {
                "ip": srt_ip,
                "port": srt_port,
                "error": str(e),
                "timestamp": time.time()
            }
