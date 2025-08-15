#!/usr/bin/env python3
"""
Test script to demonstrate multiple terminal instances from the same device
This shows how the new hostname + IP address client ID system works
"""

import socket
import time
import threading
from client.client import MultiScreenClient

def get_local_ip():
    """Get local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"

def run_client_instance(instance_name, server_url, hostname, display_name):
    """Run a single client instance"""
    print(f"\n🚀 Starting {instance_name}")
    print(f"   Hostname: {hostname}")
    print(f"   Display: {display_name}")
    print(f"   Local IP: {get_local_ip()}")
    
    try:
        client = MultiScreenClient(
            server_url=server_url,
            hostname=hostname,
            display_name=display_name
        )
        
        print(f"   Generated Client ID: {client.client_id}")
        
        # Register with server
        if client.register():
            print(f"✅ {instance_name} registered successfully")
            print(f"   Server Client ID: {client.client_id}")
            
            # Wait for assignment
            print(f"⏳ {instance_name} waiting for assignment...")
            if client.wait_for_assignment():
                print(f"🎉 {instance_name} assignment complete!")
            else:
                print(f"❌ {instance_name} assignment failed")
        else:
            print(f"❌ {instance_name} registration failed")
            
    except Exception as e:
        print(f"❌ {instance_name} error: {e}")

def main():
    """Main test function"""
    print("🧪 TESTING MULTIPLE TERMINAL INSTANCES FROM SAME DEVICE")
    print("=" * 70)
    
    # Configuration
    server_url = "http://localhost:5000"  # Adjust as needed
    base_hostname = socket.gethostname()
    
    print(f"Server: {server_url}")
    print(f"Base Hostname: {base_hostname}")
    print(f"Local IP: {get_local_ip()}")
    print("=" * 70)
    
    # Create multiple client instances
    instances = [
        ("Terminal 1", f"{base_hostname}-term1", "Left Display"),
        ("Terminal 2", f"{base_hostname}-term2", "Right Display"),
        ("Terminal 3", f"{base_hostname}-term3", "Center Display")
    ]
    
    # Run instances in separate threads
    threads = []
    for instance_name, hostname, display_name in instances:
        thread = threading.Thread(
            target=run_client_instance,
            args=(instance_name, server_url, hostname, display_name)
        )
        threads.append(thread)
        thread.start()
        
        # Small delay between starts
        time.sleep(1)
    
    # Wait for all instances to complete
    for thread in threads:
        thread.join()
    
    print("\n🏁 All test instances completed")
    print("\n📋 Expected Results:")
    print("   - Each terminal should have a unique client ID")
    print("   - Format: hostname-termX_IPADDRESS")
    print("   - All should be able to register simultaneously")
    print("   - Each can be assigned to different streams")

if __name__ == "__main__":
    main()
