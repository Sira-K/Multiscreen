# FFplay Display Positioning Fixes

## Problem
The `client.py` file had issues with ffplay not displaying on the correct display/monitor. The main problems were:

1. **Complex window positioning logic** - Used `wmctrl` to move windows after they were created
2. **Timing issues** - Window positioning happened after ffplay started, causing race conditions
3. **Missing display environment** - No explicit `DISPLAY` environment variable set
4. **Monitor geometry parsing bugs** - Complex parsing logic that could fail with different `xrandr` output formats

## Solution
Simplified the approach by using ffplay's built-in positioning capabilities:

### 1. Improved Monitor Detection
- **Fixed geometry parsing** in `_get_monitor_geometry()` method
- **Better error handling** with proper logging
- **Simplified parsing logic** that handles various `xrandr` output formats

### 2. Enhanced FFplay Command
- **Added `DISPLAY=:0.0` environment variable** to ensure proper display targeting
- **Used ffplay's `-x` and `-y` arguments** for direct positioning
- **Simplified command structure** with proper argument ordering

### 3. Removed Complex Window Management
- **Eliminated `wmctrl` dependency** - no longer needed
- **Removed post-startup window positioning** - positioning happens at startup
- **Simplified legacy methods** to stub functions
- **Made window manager invisible** - no visible black box on startup

## Key Changes

### Before (Complex Approach)
```python
# Start ffplay normally
cmd = ["ffplay", "-fs", stream_url]
process = subprocess.Popen(cmd)

# Then try to move window after it starts
threading.Timer(3.0, self._move_to_target_screen, args=(geometry,)).start()
```

### After (Simplified Approach)
```python
# Set proper environment
env = os.environ.copy()
env['DISPLAY'] = ':0.0'

# Build command with positioning
cmd = ["ffplay", "-x", str(x), "-y", str(y), "-fs", stream_url]
process = subprocess.Popen(cmd, env=env)
```

## Benefits

1. **More Reliable** - No timing issues or race conditions
2. **Simpler** - Fewer dependencies and less complex code
3. **Faster** - No delays waiting for window positioning
4. **More Compatible** - Works with different window managers
5. **Better Error Handling** - Clearer logging and error messages
6. **No Visible UI** - Invisible background window (no black box)

## Testing

Use the included test script to verify the fixes:

```bash
python3 test_display_fix.py
```

This will:
1. Test monitor detection using `xrandr`
2. Verify geometry parsing works correctly
3. Optionally test ffplay positioning on each detected monitor

## Usage

The client now works more reliably with target screen specification:

```bash
# Screen 1 (default)
python3 client.py --server http://192.168.1.100:5000 \
  --hostname client-1 --display-name "Screen1" \
  --target-screen 1

# Screen 2 (secondary monitor)
python3 client.py --server http://192.168.1.100:5000 \
  --hostname client-2 --display-name "Screen2" \
  --target-screen 2
```

## Technical Details

### Monitor Geometry Format
The code now properly parses `xrandr --listmonitors` output:
```
 0: +HDMI-1 1920/510x1080/287+0+0  HDMI-1
 1: +DP-2 1920/510x1080/287+1920+0  DP-2
```

### FFplay Positioning Arguments
- `-x <x>` - Set window X position
- `-y <y>` - Set window Y position  
- `-fs` - Make fullscreen
- `DISPLAY=:0.0` - Ensure proper display targeting

### Environment Variables
- `DISPLAY=:0.0` - Explicitly set display for X11 applications
- Inherits other environment variables from parent process

## Troubleshooting

If positioning still doesn't work:

1. **Check monitor setup**: `xrandr --listmonitors`
2. **Verify display**: `echo $DISPLAY`
3. **Test ffplay manually**: `DISPLAY=:0.0 ffplay -x 1920 -y 0 -fs test.mp4`
4. **Check logs**: Look for monitor detection messages in client output

## Files Modified

- `client.py` - Main client with positioning fixes
- `test_display_fix.py` - Test script for verification
- `DISPLAY_FIX_SUMMARY.md` - This documentation
