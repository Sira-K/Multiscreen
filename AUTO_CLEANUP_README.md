# Automatic Client Cleanup Feature

## Overview

The multi-screen display system now includes automatic cleanup functionality that automatically removes inactive clients after a configurable period of inactivity. This feature helps maintain a clean system by removing clients that are no longer connected or responding.

## How It Works

### Default Behavior
- **Cleanup Interval**: Every 30 seconds
- **Inactivity Threshold**: 2 minutes (120 seconds)
- **Automatic Start**: Enabled by default when the server starts

### Process
1. The system runs a background thread that checks for inactive clients every 30 seconds
2. Clients are considered inactive if they haven't sent a heartbeat or been seen for more than 2 minutes
3. Inactive clients are automatically removed from the system
4. Clients that are actively streaming are protected from automatic removal (unless force mode is enabled)

## Configuration

### Backend Configuration

The auto-cleanup can be configured through the Flask app initialization in `backend/flask_app.py`:

```python
# Start automatic cleanup of inactive clients (runs every 30 seconds, removes clients after 2 minutes)
state.start_auto_cleanup(cleanup_interval_seconds=30, inactive_threshold_seconds=120)
```

### Runtime Configuration

You can control the auto-cleanup at runtime using the API endpoints:

#### Start Auto-Cleanup
```bash
POST /api/clients/control_auto_cleanup
{
  "action": "start",
  "cleanup_interval_seconds": 30,
  "inactive_threshold_seconds": 120
}
```

#### Stop Auto-Cleanup
```bash
POST /api/clients/control_auto_cleanup
{
  "action": "stop"
}
```

#### Check Status
```bash
POST /api/clients/control_auto_cleanup
{
  "action": "status"
}
```

## API Endpoints

### New Endpoints

1. **`POST /api/clients/control_auto_cleanup`** - Control auto-cleanup
2. **`POST /api/clients/bulk_remove_clients`** - Bulk remove multiple clients
3. **`POST /api/clients/cleanup_inactive_clients`** - Manual cleanup of inactive clients

### Existing Endpoints Enhanced

- **`POST /api/clients/remove_client`** - Remove individual client (already existed)

## Frontend Integration

### Auto-Cleanup Control Panel

The frontend now includes an auto-cleanup control panel in the ClientsTab component that shows:
- Current auto-cleanup status (Active/Inactive)
- Start/Stop toggle button
- Information about the cleanup threshold

### Features
- Real-time status display
- One-click enable/disable
- Visual indicators for active state
- Automatic status updates every 30 seconds

## Safety Features

### Protection Mechanisms
1. **Streaming Protection**: Clients actively streaming are not automatically removed
2. **Configurable Thresholds**: Minimum cleanup interval of 10 seconds, minimum inactivity threshold of 30 seconds
3. **Force Mode**: Optional override to remove clients even if streaming (use with caution)
4. **Error Handling**: Comprehensive error handling and logging

### Logging
All cleanup operations are logged with detailed information:
- Client identification (name, ID)
- Reason for removal
- Timestamp and duration
- Success/failure status

## Testing

### Test Script
A test script is provided at `backend/test_auto_cleanup.py` that:
1. Registers a test client
2. Waits for auto-cleanup to remove it
3. Verifies the cleanup process works correctly

### Running Tests
```bash
cd backend
python test_auto_cleanup.py
```

## Monitoring

### Log Files
Auto-cleanup activities are logged to:
- `backend/logs/all.log` - General system log
- `backend/logs/clients.log` - Client-specific operations

### Key Log Messages
- `Auto-cleanup started: clients will be removed after 2 minutes of inactivity`
- `Auto-removed inactive client: {client_name} ({client_id}) after {threshold}s of inactivity`
- `Auto-cleanup completed: {removed_count} inactive clients removed, {failed_count} failed`

## Performance Considerations

### Resource Usage
- **Memory**: Minimal impact - only stores client state
- **CPU**: Low impact - runs every 30 seconds with simple operations
- **Network**: No additional network traffic

### Scalability
- Designed to handle hundreds of clients efficiently
- Thread-safe implementation with proper locking
- Configurable intervals to balance responsiveness and performance

## Troubleshooting

### Common Issues

1. **Clients not being removed**
   - Check if auto-cleanup is running: `POST /api/clients/control_auto_cleanup` with `{"action": "status"}`
   - Verify client inactivity threshold is appropriate
   - Check logs for error messages

2. **Auto-cleanup not starting**
   - Check server logs for initialization errors
   - Verify client state is properly initialized
   - Check if cleanup thread is running

3. **Performance issues**
   - Increase cleanup interval (e.g., from 30 to 60 seconds)
   - Adjust inactivity threshold based on your use case
   - Monitor system resources during cleanup operations

### Debug Mode
Enable debug logging by setting the log level to DEBUG in your logging configuration.

## Future Enhancements

### Planned Features
1. **Webhook Notifications**: Send notifications when clients are auto-removed
2. **Metrics Dashboard**: Real-time statistics on cleanup operations
3. **Conditional Cleanup**: Different thresholds for different client types
4. **Backup/Restore**: Ability to restore accidentally removed clients

### Configuration Options
1. **Per-Group Thresholds**: Different cleanup rules for different groups
2. **Time-Based Rules**: Different thresholds during business hours vs. off-hours
3. **Client Priority**: Protect high-priority clients from automatic removal

## Support

For issues or questions about the auto-cleanup feature:
1. Check the logs for error messages
2. Verify configuration settings
3. Test with the provided test script
4. Review this documentation

## Changelog

### Version 2.0.0
- Initial implementation of automatic client cleanup
- Default 2-minute inactivity threshold
- 30-second cleanup interval
- Frontend control panel
- Comprehensive API endpoints
- Safety features and protection mechanisms
