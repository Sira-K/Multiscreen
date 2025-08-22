#!/usr/bin/env python3
"""
Test script for dual HDMI functionality
This script helps verify that both HDMI outputs are working correctly on X11
"""

import os
import sys
import subprocess
import time
import tkinter as tk
from tkinter import messagebox

def test_display(display_num, hdmi_name):
    """Test a specific display by creating a test window"""
    print(f"Testing {hdmi_name} (Display :{display_num}.0)...")
    
    # Set display environment
    os.environ['DISPLAY'] = f":{display_num}.0"
    
    try:
        # Create a simple test window
        root = tk.Tk()
        root.title(f"Test Window - {hdmi_name}")
        root.geometry("400x300")
        
        # Add some content
        label = tk.Label(root, text=f"Test Window for {hdmi_name}\nDisplay :{display_num}.0", 
                        font=("Arial", 16), fg="blue")
        label.pack(expand=True)
        
        # Add a button to close
        close_btn = tk.Button(root, text="Close Window", command=root.destroy)
        close_btn.pack(pady=20)
        
        # Make window fullscreen for testing
        root.attributes('-fullscreen', True)
        
        print(f"  ✓ {hdmi_name} window created successfully")
        print(f"  ✓ Window should be visible on {hdmi_name}")
        print(f"  ✓ Press the 'Close Window' button to continue")
        
        # Show window for 10 seconds or until closed
        root.after(10000, root.destroy)  # Auto-close after 10 seconds
        root.mainloop()
        
        print(f"  ✓ {hdmi_name} test completed successfully")
        return True
        
    except Exception as e:
        print(f"  ✗ Error testing {hdmi_name}: {e}")
        return False

def test_xrandr(display_num, hdmi_name):
    """Test xrandr functionality on a specific display"""
    print(f"Testing xrandr on {hdmi_name} (Display :{display_num}.0)...")
    
    try:
        # Test xrandr --listmonitors
        result = subprocess.run(['xrandr', '--display', f':{display_num}.0', '--listmonitors'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print(f"  ✓ xrandr --listmonitors works on {hdmi_name}")
            print(f"    {result.stdout.strip()}")
        else:
            print(f"  ✗ xrandr --listmonitors failed on {hdmi_name}: {result.stderr}")
            return False
        
        # Test xrandr --listoutputs
        result = subprocess.run(['xrandr', '--display', f':{display_num}.0', '--listoutputs'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print(f"  ✓ xrandr --listoutputs works on {hdmi_name}")
            print(f"    {result.stdout.strip()}")
        else:
            print(f"  ✗ xrandr --listoutputs failed on {hdmi_name}: {result.stderr}")
            return False
        
        return True
        
    except subprocess.TimeoutExpired:
        print(f"  ✗ xrandr timeout on {hdmi_name}")
        return False
    except Exception as e:
        print(f"  ✗ Error testing xrandr on {hdmi_name}: {e}")
        return False

def test_simple_app(display_num, hdmi_name):
    """Test running a simple application on a specific display"""
    print(f"Testing simple application on {hdmi_name} (Display :{display_num}.0)...")
    
    try:
        # Try to run xeyes (if available)
        result = subprocess.run(['xeyes', '-display', f':{display_num}.0'], 
                              timeout=5, capture_output=True)
        
        if result.returncode == 0:
            print(f"  ✓ xeyes works on {hdmi_name}")
            return True
        else:
            print(f"  ⚠ xeyes not available, trying alternative test")
            
            # Alternative: test with xwininfo
            result = subprocess.run(['xwininfo', '-display', f':{display_num}.0', '-root'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print(f"  ✓ xwininfo works on {hdmi_name}")
                return True
            else:
                print(f"  ✗ Basic X11 test failed on {hdmi_name}")
                return False
                
    except subprocess.TimeoutExpired:
        print(f"  ✓ Simple app test completed on {hdmi_name}")
        return True
    except FileNotFoundError:
        print(f"  ⚠ xeyes not found, skipping simple app test")
        return True
    except Exception as e:
        print(f"  ✗ Error testing simple app on {hdmi_name}: {e}")
        return False

def check_x11_session():
    """Check if we're running in an X11 session"""
    print("Checking X11 session...")
    
    display = os.environ.get('DISPLAY')
    xdg_session = os.environ.get('XDG_SESSION_TYPE')
    
    if display:
        print(f"  ✓ DISPLAY set to: {display}")
    else:
        print(f"  ⚠ DISPLAY not set")
    
    if xdg_session == 'x11':
        print(f"  ✓ XDG_SESSION_TYPE is: {xdg_session}")
    elif xdg_session == 'wayland':
        print(f"  ⚠ XDG_SESSION_TYPE is: {xdg_session} (expected: x11)")
        print(f"  You may need to switch to X11 for this test to work properly")
    else:
        print(f"  ⚠ XDG_SESSION_TYPE is: {xdg_session}")
    
    # Check for X11 server
    try:
        result = subprocess.run(['xset', 'q'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"  ✓ X11 server is accessible")
        else:
            print(f"  ✗ X11 server not accessible")
            return False
    except FileNotFoundError:
        print(f"  ⚠ xset not found - cannot verify X11 server")
    except Exception as e:
        print(f"  ⚠ Could not check X11 server: {e}")
    
    return True

def main():
    """Main test function"""
    print("=" * 60)
    print("DUAL HDMI X11 TEST SCRIPT")
    print("=" * 60)
    print()
    
    # Check if running on Raspberry Pi
    if os.path.exists('/proc/device-tree/model'):
        with open('/proc/device-tree/model', 'r') as f:
            model = f.read().strip()
            if 'Raspberry Pi' in model:
                print(f"✓ Detected: {model}")
            else:
                print(f"⚠ Running on: {model}")
    else:
        print("⚠ Could not detect device model")
    
    print()
    
    # Check X11 session
    if not check_x11_session():
        print("⚠ X11 session check failed")
        print("  This script is designed for X11 environments")
        print("  If you're using Wayland, you may need to switch to X11")
        print()
    
    # Test both displays
    displays = [
        (0, "HDMI1 (Primary)"),
        (1, "HDMI2 (Secondary)")
    ]
    
    results = {}
    
    for display_num, hdmi_name in displays:
        print(f"Testing {hdmi_name}...")
        print("-" * 40)
        
        success = True
        
        # Test 1: xrandr functionality
        if not test_xrandr(display_num, hdmi_name):
            success = False
        
        print()
        
        # Test 2: Simple application
        if not test_simple_app(display_num, hdmi_name):
            success = False
        
        print()
        
        # Test 3: Tkinter window (interactive)
        print(f"Creating test window on {hdmi_name}...")
        print("  This will open a fullscreen test window.")
        print("  Close it to continue testing.")
        print()
        
        if not test_display(display_num, hdmi_name):
            success = False
        
        results[hdmi_name] = success
        print()
        print(f"{hdmi_name} test {'PASSED' if success else 'FAILED'}")
        print("=" * 60)
        print()
    
    # Summary
    print("TEST SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for hdmi_name, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{hdmi_name}: {status}")
        if not success:
            all_passed = False
    
    print()
    
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("Your dual HDMI X11 setup is working correctly.")
        print()
        print("You can now run the multi-screen clients:")
        print("  Terminal 1: ./launch_hdmi1.sh")
        print("  Terminal 2: ./launch_hdmi2.sh")
        print()
        print("Or manually:")
        print("  Terminal 1: python3 client.py --target-screen HDMI1")
        print("  Terminal 2: python3 client.py --target-screen HDMI2")
    else:
        print("⚠ SOME TESTS FAILED")
        print("Please check the error messages above and verify your setup.")
        print()
        print("Common issues:")
        print("  1. Dual HDMI not enabled in /boot/config.txt")
        print("  2. X11 server not running on secondary display")
        print("  3. Display permissions issues")
        print("  4. Hardware connection problems")
        print()
        print("To switch from Wayland to X11:")
        print("  sudo nano /etc/gdm3/custom.conf")
        print("  Add: WaylandEnable=false")
        print("  sudo reboot")
    
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nTest failed with error: {e}")
        sys.exit(1)

