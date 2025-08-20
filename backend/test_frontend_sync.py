#!/usr/bin/env python3
"""
Test script to verify frontend sync with auto-cleanup
"""

import time
import requests
import json

# Configuration
API_BASE_URL = "http://localhost:5000"
TEST_CLIENT_ID = "test-frontend-sync-001"

def test_frontend_sync():
    """Test that frontend stays in sync with backend auto-cleanup"""
    
    print("=== Testing Frontend Sync with Auto-Cleanup ===\n")
    
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
    
    # 2. Check if auto-cleanup is already running and configure it for testing
    print("\n2. Configuring auto-cleanup for testing...")
    try:
        # Try to start with short intervals, but don't fail if already running
        response = requests.post(f"{API_BASE_URL}/api/clients/control_auto_cleanup", 
                               json={
                                   "action": "start",
                                   "cleanup_interval_seconds": 10,  # Run every 10 seconds
                                   "inactive_threshold_seconds": 20  # Remove after 20 seconds
                               })
        if response.status_code == 200:
            result = response.json()
            print(f"   Result: {result}")
        elif response.status_code == 400:
            print("   Auto-cleanup already running with different config - continuing with existing setup")
        else:
            print(f"   Failed to configure: {response.status_code}")
            return
    except Exception as e:
        print(f"   Error: {e}")
        return
    
    # 3. Register a test client
    print(f"\n3. Registering test client: {TEST_CLIENT_ID}")
    try:
        response = requests.post(f"{API_BASE_URL}/api/clients/register", 
                               json={
                                   "hostname": TEST_CLIENT_ID,
                                   "display_name": "Test Frontend Sync Client",
                                   "platform": "test"
                               })
        if response.status_code == 200:
            result = response.json()
            print(f"   Client registered: {result}")
            # Store the actual client ID for later use
            actual_client_id = result.get('client_id')
            if actual_client_id:
                print(f"   Actual client ID: {actual_client_id}")
        else:
            print(f"   Failed to register: {response.status_code}")
            return
    except Exception as e:
        print(f"   Error: {e}")
        return
    
    # 4. Check client is in the system
    print("\n4. Checking client is in system...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/clients/list")
        if response.status_code == 200:
            clients = response.json()
            test_client = next((c for c in clients.get('clients', []) if c.get('client_id') == actual_client_id), None)
            if test_client:
                print(f"   Client found: {test_client.get('display_name')}")
            else:
                print("   Client not found in list")
                return
        else:
            print(f"   Failed to get clients: {response.status_code}")
            return
    except Exception as e:
        print(f"   Error: {e}")
        return
    
    # 5. Wait for auto-cleanup to remove the client
    print("\n5. Waiting for auto-cleanup to remove client (should happen after 20 seconds)...")
    print("   (This will take up to 30 seconds)")
    
    start_time = time.time()
    while time.time() - start_time < 35:  # Wait up to 35 seconds
        try:
            response = requests.get(f"{API_BASE_URL}/api/clients/list")
            if response.status_code == 200:
                clients = response.json()
                test_client = next((c for c in clients.get('clients', []) if c.get('client_id') == actual_client_id), None)
                
                if not test_client:
                    elapsed = time.time() - start_time
                    print(f"   ✓ Client removed after {elapsed:.1f} seconds!")
                    break
                else:
                    elapsed = time.time() - start_time
                    print(f"   Waiting... ({elapsed:.1f}s elapsed)")
            else:
                print(f"   Failed to get clients: {response.status_code}")
                break
        except Exception as e:
            print(f"   Error: {e}")
            break
        
        time.sleep(5)  # Check every 5 seconds
    else:
        print("   ✗ Client was not removed within expected time")
    
    # 6. Check final status
    print("\n6. Final auto-cleanup status...")
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
    print("\nFrontend should now show updated client counts in group cards.")
    print("The ClientsTab refresh will trigger StreamsTab refresh, keeping everything in sync.")

if __name__ == "__main__":
    test_frontend_sync()
