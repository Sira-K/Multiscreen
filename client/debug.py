#!/usr/bin/env python3
"""
Debug script to check client state in the Flask application
Run this on the server while the Flask app is running
"""

import requests
import json
import sys

def check_client_state(server_url, client_id):
    """Check if client exists and its state"""
    
    print(f"🔍 Debugging Client State Issue")
    print(f"=" * 50)
    print(f"Server: {server_url}")
    print(f"Client ID: {client_id}")
    print()
    
    # 1. Check if client is registered by listing all clients
    print("Step 1: Listing all registered clients...")
    try:
        response = requests.get(f"{server_url}/api/clients/list", timeout=5)
        if response.status_code == 200:
            data = response.json()
            clients = data.get("clients", {})
            print(f"Found {len(clients)} registered clients:")
            for cid, cdata in clients.items():
                print(f"  - {cid}: {cdata.get('display_name', 'unknown')} (status: {cdata.get('assignment_status', 'unknown')})")
            
            if client_id in clients:
                print(f"\n✅ Client '{client_id}' is registered!")
                print(f"Client data: {json.dumps(clients[client_id], indent=2)}")
            else:
                print(f"\n❌ Client '{client_id}' NOT found in registered clients!")
                print(f"Available client IDs: {list(clients.keys())}")
        else:
            print(f"Failed to list clients: HTTP {response.status_code}")
    except Exception as e:
        print(f"Error listing clients: {e}")
    
    print()
    
    # 2. Try to get specific client details
    print("Step 2: Getting specific client details...")
    try:
        response = requests.get(f"{server_url}/api/clients/get_client/{client_id}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Client details retrieved:")
            print(json.dumps(data, indent=2))
        else:
            print(f"❌ Failed to get client details: HTTP {response.status_code}")
            if response.text:
                print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error getting client details: {e}")
    
    print()
    
    # 3. Test wait_for_assignment endpoint
    print("Step 3: Testing wait_for_assignment endpoint...")
    try:
        payload = {"client_id": client_id}
        response = requests.post(
            f"{server_url}/api/clients/wait_for_assignment",
            json=payload,
            timeout=5
        )
        print(f"Response status: HTTP {response.status_code}")
        if response.status_code in [200, 202]:
            data = response.json()
            print(f"✅ wait_for_assignment successful:")
            print(f"  Status: {data.get('status', 'unknown')}")
            print(f"  Message: {data.get('message', 'none')}")
        elif response.status_code == 404:
            print(f"❌ Client not found (404)")
            data = response.json() if response.text else {}
            print(f"  Message: {data.get('message', 'No details')}")
        else:
            print(f"❌ Unexpected response: {response.text}")
    except Exception as e:
        print(f"Error testing wait_for_assignment: {e}")
    
    print()
    print("=" * 50)
    
    # 4. Suggestions
    print("\n💡 Troubleshooting suggestions:")
    print("1. Check if the client_id matches exactly (case-sensitive)")
    print("2. Verify the client registration was successful")
    print("3. Check Flask app logs for any errors during registration")
    print("4. Ensure the state is being properly maintained between requests")
    print("5. Try re-registering the client")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_client.py <server_url> [client_id]")
        print("Example: python debug_client.py http://128.205.39.64:5000 nooky")
        sys.exit(1)
    
    server_url = sys.argv[1].rstrip('/')
    client_id = sys.argv[2] if len(sys.argv) > 2 else "nooky"
    
    check_client_state(server_url, client_id)