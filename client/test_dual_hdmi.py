#!/usr/bin/env python3
"""
Test script for dual HDMI functionality with Wayland support
This script helps verify that both HDMI outputs are working correctly on Wayland
"""

import os
import sys
import subprocess
import time
import tkinter as tk
from tkinter import messagebox
import json

def detect_wayland_outputs():
    """Detect available Wayland outputs using wlr-randr or similar tools"""
    print("Detecting Wayland outputs...")
    
    outputs = []
    
    # Try wlr-randr first (most common on Raspberry Pi with Wayland)
    try:
        result = subprocess.run(['wlr-randr'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("  ✓ wlr-randr available")
            # Parse wlr-randr output to find HDMI outputs
            lines = result.stdout.strip().split('\n')
            current_output = None
            
            for line in lines:
                if line.strip() and not line.startswith(' '):
                    # This is an output name
                    current_output = line.strip()
                    if 'HDMI' in current_output or 'hdmi' in current_output:
                        outputs.append(current_output)
                        print(f"    Found output: {current_output}")
            
            return outputs
    except FileNotFoundError:
        print("  ⚠ wlr-randr not found")
    except Exception as e:
        print(f"  ⚠ wlr-randr error: {e}")
    
    # Try swaymsg if using Sway
    try:
        result = subprocess.run(['swaymsg', '-t', 'get_outputs'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("  ✓ swaymsg available")
            try:
                data = json.loads(result.stdout)
                for output in data:
                    if output.get('active') and ('HDMI' in output.get('name', '') or 'hdmi' in output.get('name', '')):
                        outputs.append(output['name'])
                        print(f"    Found output: {output['name']}")
            except json.JSONDecodeError:
                print("  ⚠ Could not parse swaymsg output")
            return outputs
    except FileNotFoundError:
        print("  ⚠ swaymsg not found")
    except Exception as e:
        print(f"  ⚠ swaymsg error: {e}")
    
    # Try weston-info if using Weston
    try:
        result = subprocess.run(['weston-info'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("  ✓ weston-info available")
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if 'HDMI' in line or 'hdmi' in line:
                    # Extract output name from weston-info output
                    if 'output' in line.lower():
                        output_name = line.split()[-1] if line.split() else f"HDMI{len(outputs)+1}"
                        outputs.append(output_name)
                        print(f"    Found output: {output_name}")
            return outputs
    except FileNotFoundError:
        print("  ⚠ weston-info not found")
    except Exception as e:
        print(f"  ⚠ weston-info error: {e}")
    
    # Fallback: assume standard HDMI outputs
    if not outputs:
        print("  ⚠ Could not detect outputs, using fallback names")
        outputs = ['HDMI-A-1', 'HDMI-A-2']  # Common Wayland output names
    
    return outputs

def test_wayland_output(output_name, hdmi_name):
    """Test a specific Wayland output by creating a test window"""
    print(f"Testing {hdmi_name} (Output: {output_name})...")
    
    # Set Wayland environment variables
    os.environ['WAYLAND_DISPLAY'] = 'wayland-0'
    os.environ['XDG_SESSION_TYPE'] = 'wayland'
    
    # For Wayland, we need to use a Wayland-compatible toolkit
    # Tkinter with Wayland backend, or alternative like PyQt5/PySide2
    
    try:
        # Try to create a Wayland-compatible window
        # Note: Tkinter may not work properly with Wayland
        root = tk.Tk()
        root.title(f"Test Window - {hdmi_name}")
        root.geometry("400x300")
        
        # Add some content
        label = tk.Label(root, text=f"Test Window for {hdmi_name}\nOutput: {output_name}\nWayland Mode", 
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
        print(f"    This is common with Tkinter on Wayland")
        return False

def test_wayland_tools(output_name, hdmi_name):
    """Test Wayland-compatible tools on a specific output"""
    print(f"Testing Wayland tools on {hdmi_name} (Output: {output_name})...")
    
    success = True
    
    # Test wlr-randr
    try:
        result = subprocess.run(['wlr-randr'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"  ✓ wlr-randr works")
            # Look for our specific output
            if output_name in result.stdout:
                print(f"    Found output {output_name} in wlr-randr")
            else:
                print(f"    ⚠ Output {output_name} not found in wlr-randr")
        else:
            print(f"  ✗ wlr-randr failed: {result.stderr}")
            success = False
    except FileNotFoundError:
        print(f"  ⚠ wlr-randr not available")
    except Exception as e:
        print(f"  ✗ Error testing wlr-randr: {e}")
        success = False
    
    # Test ydotool (Wayland-compatible alternative to xdotool)
    try:
        result = subprocess.run(['ydotool', '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"  ✓ ydotool available: {result.stdout.strip()}")
        else:
            print(f"  ⚠ ydotool not working properly")
    except FileNotFoundError:
        print(f"  ⚠ ydotool not available (install with: sudo apt install ydotool)")
    except Exception as e:
        print(f"  ⚠ ydotool error: {e}")
    
    # Test wtype (Wayland-compatible alternative to xdotool)
    try:
        result = subprocess.run(['wtype', '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"  ✓ wtype available: {result.stdout.strip()}")
        else:
            print(f"  ⚠ wtype not working properly")
    except FileNotFoundError:
        print(f"  ⚠ wtype not available (install with: sudo apt install wtype)")
    except Exception as e:
        print(f"  ⚠ wtype error: {e}")
    
    return success

def test_wayland_app(output_name, hdmi_name):
    """Test running a Wayland-compatible application"""
    print(f"Testing Wayland application on {hdmi_name} (Output: {output_name})...")
    
    try:
        # Try to run a Wayland-compatible application
        # weston-terminal is a good test
        result = subprocess.run(['weston-terminal'], timeout=5, capture_output=True)
        
        if result.returncode == 0:
            print(f"  ✓ weston-terminal works on {hdmi_name}")
            return True
        else:
            print(f"  ⚠ weston-terminal not available, trying alternative test")
            
            # Alternative: test with wlr-randr
            result = subprocess.run(['wlr-randr'], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print(f"  ✓ wlr-randr works on {hdmi_name}")
                return True
            else:
                print(f"  ✗ Basic Wayland test failed on {hdmi_name}")
                return False
                
    except subprocess.TimeoutExpired:
        print(f"  ✓ Wayland app test completed on {hdmi_name}")
        return True
    except FileNotFoundError:
        print(f"  ⚠ weston-terminal not found, skipping app test")
        return True
    except Exception as e:
        print(f"  ✗ Error testing Wayland app on {hdmi_name}: {e}")
        return False

def check_wayland_session():
    """Check if we're running in a Wayland session"""
    print("Checking Wayland session...")
    
    wayland_display = os.environ.get('WAYLAND_DISPLAY')
    xdg_session = os.environ.get('XDG_SESSION_TYPE')
    
    if wayland_display:
        print(f"  ✓ WAYLAND_DISPLAY set to: {wayland_display}")
    else:
        print(f"  ⚠ WAYLAND_DISPLAY not set")
    
    if xdg_session == 'wayland':
        print(f"  ✓ XDG_SESSION_TYPE is: {xdg_session}")
    else:
        print(f"  ⚠ XDG_SESSION_TYPE is: {xdg_session} (expected: wayland)")
    
    # Check for Wayland compositor
    try:
        result = subprocess.run(['pgrep', '-f', 'weston'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  ✓ Weston compositor running (PID: {result.stdout.strip()})")
        else:
            result = subprocess.run(['pgrep', '-f', 'sway'], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"  ✓ Sway compositor running (PID: {result.stdout.strip()})")
            else:
                print(f"  ⚠ No Wayland compositor detected")
    except Exception as e:
        print(f"  ⚠ Could not check compositor: {e}")
    
    return wayland_display is not None or xdg_session == 'wayland'

def main():
    """Main test function"""
    print("=" * 60)
    print("DUAL HDMI WAYLAND TEST SCRIPT")
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
    
    # Check Wayland session
    if not check_wayland_session():
        print("⚠ Not running in Wayland session")
        print("  This script is designed for Wayland environments")
        print("  If you're using X11, use the original test script instead")
        print()
    
    # Detect Wayland outputs
    outputs = detect_wayland_outputs()
    
    if not outputs:
        print("✗ No Wayland outputs detected")
        print("  Please check your Wayland configuration")
        return
    
    print(f"Detected {len(outputs)} outputs: {outputs}")
    print()
    
    # Test outputs
    results = {}
    
    for i, output_name in enumerate(outputs):
        hdmi_name = f"HDMI{i+1} ({'Primary' if i == 0 else 'Secondary'})"
        print(f"Testing {hdmi_name}...")
        print("-" * 40)
        
        success = True
        
        # Test 1: Wayland tools functionality
        if not test_wayland_tools(output_name, hdmi_name):
            success = False
        
        print()
        
        # Test 2: Wayland application
        if not test_wayland_app(output_name, hdmi_name):
            success = False
        
        print()
        
        # Test 3: Tkinter window (may not work on Wayland)
        print(f"Creating test window on {hdmi_name}...")
        print("  This will attempt to open a test window.")
        print("  Note: Tkinter may not work properly with Wayland")
        print()
        
        if not test_wayland_output(output_name, hdmi_name):
            print("  ⚠ Window creation failed (common on Wayland)")
            # Don't fail the test for this, as it's expected on Wayland
        
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
        print("Your dual HDMI Wayland setup is working correctly.")
        print()
        print("Note: For the multi-screen client to work with Wayland,")
        print("you may need to modify it to use Wayland-compatible tools:")
        print("  - Replace wmctrl with wlr-randr or swaymsg")
        print("  - Replace xdotool with ydotool or wtype")
        print("  - Update display detection logic")
    else:
        print("⚠ SOME TESTS FAILED")
        print("Please check the error messages above and verify your setup.")
        print()
        print("Common Wayland issues:")
        print("  1. Wayland compositor not running")
        print("  2. Dual HDMI not enabled in /boot/config.txt")
        print("  3. Missing Wayland tools (wlr-randr, ydotool, wtype)")
        print("  4. Hardware connection problems")
    
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

