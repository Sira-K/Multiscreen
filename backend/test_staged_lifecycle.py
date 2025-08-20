#!/usr/bin/env python3
"""
Test script to demonstrate the new staged client lifecycle system
"""

import time
import requests
import json

# Configuration
API_BASE_URL = "http://localhost:5000"
TEST_CLIENT_ID = "test-staged-lifecycle-001"

def test_staged_lifecycle():
    """Test the new staged client lifecycle system"""
    
    print("=== Testing Staged Client Lifecycle System ===\n")
    
    # 1. Check current auto-cleanup status
    print("1. Checking auto-cleanup status...")
    try:
        response = requests.post(f"{API_BASE_URL}/api/clients/control_auto_cleanup", 
                               json={"action": "status"})
        if response.status_code == 200:
            status = response.json()
            print(f"   Status: {status}")
        else:
            print(f"   Failed to get status: {response.status_code}")
            return
    except Exception as e:
        print(f"   Error: {e}")
        return
    
    # 2. Register a test client
    print(f"\n2. Registering test client: {TEST_CLIENT_ID}")
    try:
        response = requests.post(f"{API_BASE_URL}/api/clients/register", 
                               json={
                                   "hostname": TEST_CLIENT_ID,
                                   "display_name": "Test Staged Lifecycle Client",
                                   "platform": "test"
                               })
        if response.status_code == 200:
            result = response.json()
            print(f"   Client registered: {result}")
            actual_client_id = result.get('client_id')
            if actual_client_id:
                print(f"   Actual client ID: {actual_client_id}")
        else:
            print(f"   Failed to register: {response.status_code}")
            return
    except Exception as e:
        print(f"   Error: {e}")
        return
    
    # 3. Check initial client status (should be 'active')
    print("\n3. Checking initial client status...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/clients/list")
        if response.status_code == 200:
            clients = response.json()
            test_client = next((c for c in clients.get('clients', []) if c.get('client_id') == actual_client_id), None)
            if test_client:
                print(f"   Client found: {test_client.get('display_name')}")
                print(f"   Status: {test_client.get('status')}")
                print(f"   Is Active: {test_client.get('is_active')}")
                print(f"   Seconds ago: {test_client.get('seconds_ago')}")
            else:
                print("   Client not found in list")
                return
        else:
            print(f"   Failed to get clients: {response.status_code}")
            return
    except Exception as e:
        print(f"   Error: {e}")
        return
    
    # 4. Wait and monitor status changes
    print("\n4. Monitoring client status changes...")
    print("   Timeline:")
    print("   - 0-30s: Should be 'active' (green)")
    print("   - 30-120s: Should be 'inactive' (yellow)")
    print("   - 120s+: Should be 'disconnected' (red)")
    print("   - Auto-cleanup will remove 'disconnected' clients")
    
    start_time = time.time()
    last_status = None
    
    while time.time() - start_time < 180:  # Monitor for 3 minutes
        try:
            response = requests.get(f"{API_BASE_URL}/api/clients/list")
            if response.status_code == 200:
                clients = response.json()
                test_client = next((c for c in clients.get('clients', []) if c.get('client_id') == actual_client_id), None)
                
                if test_client:
                    current_status = test_client.get('status')
                    seconds_ago = test_client.get('seconds_ago', 0)
                    elapsed = time.time() - start_time
                    
                    if current_status != last_status:
                        print(f"   [{elapsed:.1f}s] Status changed to: {current_status} (last heartbeat: {seconds_ago}s ago)")
                        last_status = current_status
                    else:
                        print(f"   [{elapsed:.1f}s] Status: {current_status} (last heartbeat: {seconds_ago}s ago)")
                else:
                    elapsed = time.time() - start_time
                    print(f"   [{elapsed:.1f}s] ✓ Client removed by auto-cleanup!")
                    break
            else:
                print(f"   Failed to get clients: {response.status_code}")
                break
        except Exception as e:
            print(f"   Error: {e}")
            break
        
        time.sleep(10)  # Check every 10 seconds
    else:
        print("   ✗ Client was not removed within expected time")
    
    # 5. Check final status
    print("\n5. Final auto-cleanup status...")
    try:
        response = requests.post(f"{API_BASE_URL}/api/clients/control_auto_cleanup", 
                               json={"action": "status"})
        if response.status_code == 200:
            status = response.json()
            print(f"   Status: {status}")
        else:
            print(f"   Failed to get status: {response.status_code}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n=== Test Complete ===")
    print("\nFrontend should now show:")
    print("- Active clients (green)")
    print("- Inactive clients (yellow) - warning stage")
    print("- Disconnected clients (red) - will be removed")
    print("- Real-time status updates every 15 seconds")

if __name__ == "__main__":
    test_staged_lifecycle()
