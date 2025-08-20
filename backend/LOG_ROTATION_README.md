# Log Rotation System

This system automatically keeps log files at a manageable size by maintaining only the newest 1000 lines in each log file.

## Features

- **Automatic Rotation**: Logs are automatically rotated when they exceed 1000 lines
- **Line-based Rotation**: Unlike traditional size-based rotation, this system counts lines for more predictable behavior
- **No Data Loss**: Only the oldest lines are removed, keeping recent information intact
- **Rotation Notices**: Each rotation adds a timestamp notice to the log file
- **Configurable**: Easy to change the line limit by modifying `MAX_LOG_LINES` in `logging_config.py`

## How It Works

### 1. Automatic Rotation
- The `LineRotatingFileHandler` class monitors each log file
- When a log file exceeds 1000 lines, it automatically truncates to keep only the newest lines
- A rotation notice is added to the end of the file

### 2. Startup Rotation
- When the Flask server starts, all existing log files are automatically rotated
- This ensures clean logs for each server session

### 3. Real-time Monitoring
- Rotation happens in real-time as logs are written
- No need to wait for file size limits or manual intervention

## Configuration

### Change Line Limit
Edit `logging_config.py`:
```python
# Configuration constants
MAX_LOG_LINES = 1000  # Change this value as needed
```

### Log Files Affected
- `all.log` - All application logs (DEBUG level)
- `errors.log` - Error logs only (ERROR level)
- `ffmpeg.log` - FFmpeg process logs (INFO level)
- `clients.log` - Client management logs (INFO level)
- `streaming.log` - Streaming operation logs (INFO level)
- `system.log` - System resource logs (INFO level)
- `flask_server.log` - Flask server logs

## Manual Operations

### Rotate All Logs
```bash
cd backend
python rotate_logs.py --logs-dir logs
```

### Rotate Specific Log File
```bash
python rotate_logs.py --logs-dir logs --file all.log
```

### Custom Line Limit
```bash
python rotate_logs.py --logs-dir logs --max-lines 500
```

## Automated Rotation

### Cron Job Setup
Add to your crontab to rotate logs every 6 hours:
```bash
# Edit crontab
crontab -e

# Add this line (adjust path as needed)
0 */6 * * * /path/to/backend/cron_rotate_logs.sh
```

### Manual Cron Job
```bash
# Run the cron script manually
./cron_rotate_logs.sh
```

## Benefits

1. **Disk Space**: Prevents log files from growing indefinitely
2. **Performance**: Smaller log files are faster to read and search
3. **Maintenance**: No need to manually clean up old logs
4. **Debugging**: Recent logs are always available and easy to find
5. **Consistency**: All log files maintain the same size limit

## Monitoring

### Check Log Sizes
```bash
wc -l logs/*.log
```

### Check Rotation History
```bash
tail -n 20 logs/rotation.log
```

### View Recent Logs
```bash
# View last 100 lines of any log
tail -n 100 logs/all.log

# Follow logs in real-time
tail -f logs/streaming.log
```

## Troubleshooting

### Logs Not Rotating
1. Check if `MAX_LOG_LINES` is set correctly
2. Verify log file permissions
3. Check for disk space issues

### Permission Errors
```bash
# Fix permissions if needed
chmod 644 logs/*.log
chmod 755 logs/
```

### Manual Cleanup
If automatic rotation fails, manually truncate logs:
```bash
# Keep only last 1000 lines
tail -n 1000 logs/all.log > logs/all.log.tmp && mv logs/all.log.tmp logs/all.log
```

## File Structure

```
backend/
├── logging_config.py          # Main logging configuration
├── rotate_logs.py            # Manual log rotation utility
├── cron_rotate_logs.sh       # Automated rotation script
├── LOG_ROTATION_README.md    # This documentation
└── logs/                     # Log files directory
    ├── all.log
    ├── errors.log
    ├── ffmpeg.log
    ├── clients.log
    ├── streaming.log
    ├── system.log
    ├── flask_server.log
    └── rotation.log          # Rotation operation log
```
