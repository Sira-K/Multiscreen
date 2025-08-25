#!/usr/bin/env python3
"""
Test script to verify the ffplay display positioning fixes
"""

import subprocess
import sys
import os

def test_monitor_detection():
    """Test monitor detection using xrandr"""
    print("🔍 Testing monitor detection...")
    
    try:
        result = subprocess.run(['xrandr', '--listmonitors'], 
                              capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            print("✅ xrandr command successful")
            print(f"Output:\n{result.stdout}")
            
            # Parse monitors like the client does
            monitors = []
            for line in result.stdout.split('\n'):
                if '+' in line and not line.strip().startswith('Monitors:'):
                    parts = line.strip().split()
                    if len(parts) >= 3:
                        geometry = parts[2]
                        print(f"Parsing geometry: {geometry}")
                        
                        if 'x' in geometry and '+' in geometry:
                            try:
                                geom_parts = geometry.split('+')
                                if len(geom_parts) >= 3:
                                    size_part = geom_parts[0]
                                    if 'x' in size_part:
                                        width_part, height_part = size_part.split('x', 1)
                                        width = int(width_part.split('/')[0])
                                        height = int(height_part.split('/')[0])
                                        x = int(geom_parts[1])
                                        y = int(geom_parts[2])
                                        
                                        monitor_info = {
                                            'width': width,
                                            'height': height,
                                            'x': x,
                                            'y': y
                                        }
                                        monitors.append(monitor_info)
                                        print(f"✅ Parsed monitor: {monitor_info}")
                            except (ValueError, IndexError) as e:
                                print(f"❌ Failed to parse geometry {geometry}: {e}")
            
            print(f"\n📊 Found {len(monitors)} monitors:")
            for i, monitor in enumerate(monitors):
                print(f"   Monitor {i+1}: {monitor['width']}x{monitor['height']} at +{monitor['x']}+{monitor['y']}")
            
            return monitors
        else:
            print(f"❌ xrandr command failed: {result.stderr}")
            return []
            
    except Exception as e:
        print(f"❌ Monitor detection error: {e}")
        return []

def test_ffplay_positioning():
    """Test ffplay positioning with a test video"""
    print("\n🎬 Testing ffplay positioning...")
    
    # Test video URL (you can replace with a local test video)
    test_url = "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
    
    monitors = test_monitor_detection()
    
    if not monitors:
        print("❌ No monitors detected, cannot test positioning")
        return
    
    # Test positioning on each monitor
    for i, monitor in enumerate(monitors):
        print(f"\n🎯 Testing positioning on Monitor {i+1}:")
        print(f"   Position: {monitor['width']}x{monitor['height']} at +{monitor['x']}+{monitor['y']}")
        
        # Build ffplay command with positioning
        cmd = [
            "ffplay",
            "-x", str(monitor['x']),
            "-y", str(monitor['y']),
            "-fs",  # Fullscreen
            "-autoexit",
            "-loglevel", "info",
            test_url
        ]
        
        print(f"   Command: {' '.join(cmd[:6])}...")
        
        # Set environment
        env = os.environ.copy()
        env['DISPLAY'] = ':0.0'
        
        try:
            # Start ffplay for a short duration
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env
            )
            
            print(f"   ✅ ffplay started (PID: {process.pid})")
            print(f"   ⏱️  Playing for 5 seconds...")
            
            # Let it play for 5 seconds
            import time
            time.sleep(5)
            
            # Stop the process
            process.terminate()
            try:
                process.wait(timeout=3)
                print(f"   ✅ ffplay stopped gracefully")
            except subprocess.TimeoutExpired:
                process.kill()
                print(f"   ⚠️  ffplay force-killed")
            
        except Exception as e:
            print(f"   ❌ ffplay error: {e}")

def main():
    """Main test function"""
    print("🚀 Testing ffplay display positioning fixes")
    print("=" * 50)
    
    # Test 1: Monitor detection
    monitors = test_monitor_detection()
    
    if not monitors:
        print("\n❌ No monitors detected - check your display setup")
        print("   Run 'xrandr --listmonitors' manually to verify")
        return
    
    # Test 2: ffplay positioning (optional)
    response = input("\n🎬 Test ffplay positioning? (y/n): ").lower().strip()
    if response == 'y':
        test_ffplay_positioning()
    
    print("\n✅ Display positioning test complete!")
    print("\n📋 Summary of fixes:")
    print("   1. ✅ Improved monitor geometry parsing")
    print("   2. ✅ Added DISPLAY=:0.0 environment variable")
    print("   3. ✅ Simplified ffplay positioning with -x/-y arguments")
    print("   4. ✅ Removed complex wmctrl-based window positioning")
    print("   5. ✅ Better error handling and logging")

if __name__ == "__main__":
    main()
