#!/usr/bin/env python3
"""
Test script for auto-cleanup functionality
"""

import time
import requests
import json

# Configuration
API_BASE_URL = "http://localhost:5000"
TEST_CLIENT_ID = "test-auto-cleanup-001"

def test_auto_cleanup():
    """Test the auto-cleanup functionality"""
    
    print("=== Testing Auto-Cleanup Functionality ===\n")
    
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
    
    # 2. Start auto-cleanup if not running
    print("\n2. Starting auto-cleanup...")
    try:
        response = requests.post(f"{API_BASE_URL}/api/clients/control_auto_cleanup", 
                               json={
                                   "action": "start",
                                   "cleanup_interval_seconds": 10,  # Run every 10 seconds for testing
                                   "inactive_threshold_seconds": 30  # Remove after 30 seconds for testing
                               })
        if response.status_code == 200:
            result = response.json()
            print(f"   Result: {result}")
        else:
            print(f"   Failed to start: {response.status_code}")
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
                                   "display_name": "Test Auto-Cleanup Client",
                                   "platform": "test"
                               })
        if response.status_code == 200:
            result = response.json()
            print(f"   Client registered: {result}")
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
            test_client = next((c for c in clients.get('clients', []) if c.get('client_id') == TEST_CLIENT_ID), None)
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
    print("\n5. Waiting for auto-cleanup to remove client (should happen after 30 seconds)...")
    print("   (This will take up to 40 seconds)")
    
    start_time = time.time()
    while time.time() - start_time < 45:  # Wait up to 45 seconds
        try:
            response = requests.get(f"{API_BASE_URL}/api/clients/list")
            if response.status_code == 200:
                clients = response.json()
                test_client = next((c for c in clients.get('clients', []) if c.get('client_id') == TEST_CLIENT_ID), None)
                
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

if __name__ == "__main__":
    test_auto_cleanup()
