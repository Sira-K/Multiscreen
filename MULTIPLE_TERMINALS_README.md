# Multiple Terminal Instances Support

## Overview

This update modifies the client identification system to allow multiple terminal instances from the same device to run simultaneously without conflicts. Previously, the system used only the hostname as the client identifier, which caused issues when multiple terminals tried to register from the same machine.

## What Changed

### 1. Client ID Format

**Before:** `client_id = hostname`
**After:** `client_id = f"{hostname}_{ip_address}"`

This creates unique identifiers like:
- `mymachine_192.168.1.100`
- `mymachine_192.168.1.101`
- `mymachine_127.0.0.1`

### 2. Backend Changes

#### `client_endpoints.py`
- Modified `register_client()` to combine hostname and IP address
- Updated logging to show both hostname and IP address clearly

#### `client_utils.py`
- Added helper functions to extract hostname and IP from client IDs
- Added functions to group clients by hostname
- Added display formatting functions

#### `info_endpoints.py`
- Enhanced client listing with cleaner hostname/IP display
- Added new `/list_by_hostname` endpoint for better management

#### `client_blueprint.py`
- Added route for the new hostname-grouped listing endpoint

### 3. Client Changes

#### `client.py`
- Added `_get_local_ip_address()` method for IP detection
- Added `client_id` property that generates unique IDs
- Updated all server requests to use the new client ID format
- Enhanced display information to show both hostname and IP

## How It Works

### 1. Client Registration
When a client registers:
1. Gets local IP address using socket connection
2. Creates unique client ID: `hostname_ipaddress`
3. Sends both hostname and IP to server
4. Server stores client with unique ID

### 2. Multiple Terminal Support
Now you can run multiple terminals from the same device:
```bash
# Terminal 1
python3 client.py --server http://192.168.1.100:5000 --hostname mymachine-term1 --name "Left Display"

# Terminal 2  
python3 client.py --server http://192.168.1.100:5000 --hostname mymachine-term2 --name "Right Display"

# Terminal 3
python3 client.py --server http://192.168.1.100:5000 --hostname mymachine-term3 --name "Center Display"
```

Each will get a unique client ID:
- `mymachine-term1_192.168.1.100`
- `mymachine-term2_192.168.1.100`  
- `mymachine-term3_192.168.1.100`

### 3. Admin Interface
The admin interface now shows:
- Clean hostname display
- IP address information
- Clients grouped by hostname
- Better management of multiple instances

## New Endpoints

### `/api/clients/list_by_hostname`
Returns clients grouped by hostname for easier management:
```json
{
  "hostname_groups": [
    {
      "hostname": "mymachine",
      "client_count": 3,
      "active_count": 3,
      "assigned_count": 2,
      "clients": [...]
    }
  ]
}
```

## Testing

Use the provided test script:
```bash
python3 test_multiple_terminals.py
```

This will:
1. Start 3 terminal instances simultaneously
2. Show unique client IDs for each
3. Demonstrate successful registration
4. Verify no conflicts occur

## Benefits

1. **No More Conflicts**: Multiple terminals can run from same device
2. **Better Management**: Admin can see all instances clearly
3. **Flexible Deployment**: Mix of single and multi-terminal setups
4. **Backward Compatible**: Existing single-terminal setups still work
5. **Clear Identification**: Easy to distinguish between instances

## Migration

No migration required for existing setups. The system automatically:
- Detects IP addresses for new registrations
- Creates unique IDs for new clients
- Maintains existing client records
- Provides enhanced admin interface

## Troubleshooting

### IP Detection Issues
If IP detection fails, the system falls back to:
1. Hostname-based identification
2. Loopback IP (127.0.0.1)
3. Manual IP specification via command line

### Network Configuration
Ensure:
- Clients can reach the server
- Network interfaces are properly configured
- Firewall allows client-server communication

## Future Enhancements

Potential improvements:
1. **Port-based identification**: Include port numbers for even more uniqueness
2. **Process ID integration**: Include PID in client identification
3. **Session tokens**: Add session-based authentication
4. **Auto-discovery**: Automatically detect and manage multiple instances
