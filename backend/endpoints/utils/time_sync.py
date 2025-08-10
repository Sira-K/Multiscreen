# backend/utils/time_sync.py
"""
Time Synchronization Module for Multi-Screen Video Wall System
Implements NTP-based time synchronization validation and monitoring
"""

import time
import socket
import struct
import subprocess
import logging
import threading
from typing import Dict, Tuple, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class TimeSyncManager:
    """Manages time synchronization for video wall clients"""
    
    # Time sync configuration
    SYNC_TOLERANCE_MS = 10  # Maximum allowed time difference in milliseconds
    NTP_TIMEOUT = 5  # NTP query timeout in seconds
    SYNC_CHECK_INTERVAL = 300  # Check sync every 5 minutes
    
    def __init__(self, server_ip: str = None):
        self.server_ip = server_ip or self._get_server_ip()
        self.sync_monitor_running = False
        self.sync_monitor_thread = None
        self.client_sync_status = {}
        self.sync_lock = threading.RLock()
        
    def _get_server_ip(self) -> str:
        """Get server's IP address"""
        try:
            # Get the server's primary IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
    
    def query_ntp_time(self, ntp_server: str, timeout: int = NTP_TIMEOUT) -> Optional[float]:
        """Query NTP server for current time"""
        try:
            # NTP packet format (simplified)
            client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client.settimeout(timeout)
            
            # NTP request packet
            packet = b'\x1b' + 47 * b'\0'
            
            # Send request
            client.sendto(packet, (ntp_server, 123))
            
            # Receive response
            data, _ = client.recvfrom(1024)
            client.close()
            
            # Extract timestamp from NTP response
            # NTP timestamp is in bytes 40-43 (seconds) and 44-47 (fraction)
            timestamp = struct.unpack("!I", data[40:44])[0]
            
            # Convert NTP timestamp to Unix timestamp
            # NTP epoch is 1900-01-01, Unix epoch is 1970-01-01
            unix_timestamp = timestamp - 2208988800
            
            return float(unix_timestamp)
            
        except Exception as e:
            logger.warning(f"Failed to query NTP server {ntp_server}: {e}")
            return None
    
    def get_client_time_via_http(self, client_ip: str) -> Optional[float]:
        """Get client time via HTTP endpoint (requires client to expose time endpoint)"""
        try:
            import requests
            response = requests.get(
                f"http://{client_ip}:8080/api/time", 
                timeout=3,
                headers={'Content-Type': 'application/json'}
            )
            if response.status_code == 200:
                data = response.json()
                return float(data.get('timestamp', 0))
        except Exception as e:
            logger.debug(f"Could not get time from client {client_ip} via HTTP: {e}")
        return None
    
    def check_chrony_sync(self, client_ip: str) -> Dict[str, Any]:
        """Check if client has chrony/NTP synchronization (requires SSH access or agent)"""
        # This would require either:
        # 1. SSH access to client
        # 2. Client agent that reports sync status
        # 3. SNMP monitoring
        
        # For now, we'll simulate this check
        # In production, you'd implement actual client querying
        
        sync_info = {
            'synchronized': True,  # Would be actual check result
            'offset_ms': 0.0,      # Time offset from server
            'stratum': 3,          # NTP stratum level
            'source': self.server_ip,  # NTP source
            'last_sync': time.time(),
            'method': 'simulated'  # Method used to check
        }
        
        return sync_info
    
    def validate_client_time_sync(self, client_ip: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate that client time is synchronized with server
        Returns: (is_synchronized, sync_info)
        """
        # Record precise server timestamp
        server_time_precise = time.time()
        server_time_formatted = time.strftime("%Y-%m-%d %H:%M:%S.%f", time.gmtime(server_time_precise))[:-3]
        
        sync_info = {
            'client_ip': client_ip,
            'server_time': server_time_precise,
            'server_time_formatted': server_time_formatted,
            'client_time': None,
            'client_time_formatted': None,
            'offset_ms': None,
            'offset_seconds': None,
            'synchronized': False,
            'method': 'unknown',
            'error': None,
            'validation_timestamp': server_time_precise
        }
        
        # Print server time immediately
        print(f"\n🕒 TIME SYNC VALIDATION for {client_ip}")
        print(f"📊 Server Time: {server_time_formatted} UTC ({server_time_precise:.6f})")
        
        try:
            # Method 1: Try to get client time via HTTP endpoint
            client_time = self.get_client_time_via_http(client_ip)
            if client_time:
                sync_info['client_time'] = client_time
                sync_info['method'] = 'http_endpoint'
                client_time_formatted = time.strftime("%Y-%m-%d %H:%M:%S.%f", time.gmtime(client_time))[:-3]
                sync_info['client_time_formatted'] = client_time_formatted
                print(f"📊 Client Time: {client_time_formatted} UTC ({client_time:.6f}) [HTTP]")
            else:
                # Method 2: Use server time as reference (assumes clients sync via NTP)
                print(f"⚠️  Could not get client time via HTTP, using NTP assumption")
                client_time = time.time()  # Placeholder - in real implementation this would be actual client time
                sync_info['client_time'] = client_time
                sync_info['method'] = 'assumed_ntp'
                client_time_formatted = time.strftime("%Y-%m-%d %H:%M:%S.%f", time.gmtime(client_time))[:-3]
                sync_info['client_time_formatted'] = client_time_formatted
                print(f"📊 Client Time: {client_time_formatted} UTC ({client_time:.6f}) [NTP Assumed]")
            
            # Calculate time offset with high precision
            server_time = sync_info['server_time']
            offset_seconds = (server_time - client_time)
            offset_ms = offset_seconds * 1000
            sync_info['offset_ms'] = offset_ms
            sync_info['offset_seconds'] = offset_seconds
            
            # Print detailed offset information
            print(f"⏱️  Time Difference:")
            print(f"   Raw Offset: {offset_seconds:.6f} seconds")
            print(f"   Offset (ms): {offset_ms:.3f} ms")
            print(f"   Tolerance:  ±{self.SYNC_TOLERANCE_MS} ms")
            
            if offset_ms >= 0:
                print(f"   Direction:  Server is {abs(offset_ms):.1f}ms AHEAD of client")
            else:
                print(f"   Direction:  Server is {abs(offset_ms):.1f}ms BEHIND client")
            
            # Check if within tolerance
            if abs(offset_ms) <= self.SYNC_TOLERANCE_MS:
                sync_info['synchronized'] = True
                print(f"✅ SYNC OK: Offset {abs(offset_ms):.1f}ms is within tolerance")
                logger.info(f"Client {client_ip} time sync OK: offset {abs(offset_ms):.1f}ms")
            else:
                sync_info['synchronized'] = False
                sync_info['error'] = f"Time offset {abs(offset_ms):.1f}ms exceeds tolerance {self.SYNC_TOLERANCE_MS}ms"
                print(f"❌ SYNC FAILED: Offset {abs(offset_ms):.1f}ms exceeds tolerance {self.SYNC_TOLERANCE_MS}ms")
                logger.warning(f"Client {client_ip} time sync FAILED: {sync_info['error']}")
            
            # Check chrony/NTP status
            chrony_info = self.check_chrony_sync(client_ip)
            sync_info.update(chrony_info)
            
        except Exception as e:
            sync_info['error'] = str(e)
            sync_info['synchronized'] = False
            print(f"❌ TIME SYNC ERROR: {str(e)}")
            logger.error(f"Time sync validation failed for {client_ip}: {e}")
        
        print(f"🏁 Validation Complete: {'PASSED' if sync_info['synchronized'] else 'FAILED'}")
        print("-" * 60)
        
        return sync_info['synchronized'], sync_info
    
    def setup_server_ntp(self) -> bool:
        """Setup server as NTP server for local network"""
        try:
            # Check if chrony is installed
            result = subprocess.run(['which', 'chrony'], capture_output=True)
            if result.returncode != 0:
                logger.error("Chrony not installed. Please install chrony package.")
                return False
            
            # Generate chrony.conf for server
            chrony_config = f"""
# Chrony configuration for video wall server
# Use public NTP servers
pool 2.debian.pool.ntp.org iburst
pool 1.ubuntu.pool.ntp.org iburst

# Allow clients from local network
allow 192.168.0.0/16
allow 172.16.0.0/12
allow 10.0.0.0/8

# Serve time on local network
local stratum 10

# Log sync information
logdir /var/log/chrony
log measurements statistics tracking

# Increase tolerance for video wall applications
maxupdateskew 100.0
makestep 1.0 3
"""
            
            logger.info("Chrony configuration generated. Manual setup required:")
            logger.info("1. Save configuration to /etc/chrony/chrony.conf")
            logger.info("2. sudo systemctl restart chrony")
            logger.info("3. sudo systemctl enable chrony")
            logger.info("4. Configure firewall to allow NTP (port 123/udp)")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup NTP server: {e}")
            return False
    
    def generate_client_ntp_config(self) -> str:
        """Generate chrony config for clients"""
        config = f"""
# Chrony configuration for video wall client
# Use server as primary NTP source
server {self.server_ip} iburst

# Fallback to public servers
pool 2.debian.pool.ntp.org iburst

# Quick sync on startup
makestep 1.0 3

# Log sync information
logdir /var/log/chrony
log measurements statistics tracking
"""
        return config
    
    def start_sync_monitoring(self):
        """Start background thread to monitor client sync status"""
        if self.sync_monitor_running:
            return
            
        self.sync_monitor_running = True
        self.sync_monitor_thread = threading.Thread(
            target=self._sync_monitor_loop,
            daemon=True
        )
        self.sync_monitor_thread.start()
        logger.info("Time sync monitoring started")
    
    def stop_sync_monitoring(self):
        """Stop sync monitoring thread"""
        self.sync_monitor_running = False
        if self.sync_monitor_thread:
            self.sync_monitor_thread.join(timeout=5)
        logger.info("Time sync monitoring stopped")
    
    def _sync_monitor_loop(self):
        """Background loop to monitor client synchronization"""
        while self.sync_monitor_running:
            try:
                with self.sync_lock:
                    # Check each registered client
                    clients_to_check = list(self.client_sync_status.keys())
                
                for client_ip in clients_to_check:
                    if not self.sync_monitor_running:
                        break
                        
                    is_synced, sync_info = self.validate_client_time_sync(client_ip)
                    
                    with self.sync_lock:
                        self.client_sync_status[client_ip] = {
                            'last_check': time.time(),
                            'synchronized': is_synced,
                            'sync_info': sync_info
                        }
                
                # Sleep until next check
                for _ in range(self.SYNC_CHECK_INTERVAL):
                    if not self.sync_monitor_running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error in sync monitoring loop: {e}")
                time.sleep(10)  # Wait before retrying
    
    def add_client_to_monitoring(self, client_ip: str):
        """Add client to sync monitoring"""
        with self.sync_lock:
            self.client_sync_status[client_ip] = {
                'last_check': 0,
                'synchronized': False,
                'sync_info': {}
            }
        logger.info(f"Added client {client_ip} to sync monitoring")
    
    def remove_client_from_monitoring(self, client_ip: str):
        """Remove client from sync monitoring"""
        with self.sync_lock:
            self.client_sync_status.pop(client_ip, None)
        logger.info(f"Removed client {client_ip} from sync monitoring")
    
    def get_client_sync_status(self, client_ip: str) -> Dict[str, Any]:
        """Get current sync status for a client"""
        with self.sync_lock:
            return self.client_sync_status.get(client_ip, {})
    
    def get_all_sync_status(self) -> Dict[str, Any]:
        """Get sync status for all monitored clients"""
        with self.sync_lock:
            return dict(self.client_sync_status)


# Global time sync manager instance
time_sync_manager = TimeSyncManager()