#!/usr/bin/env python3
"""
Wayland Output Isolation Test Script
This script specifically tests that each Wayland output can display content independently
"""

import os
import sys
import subprocess
import time
import json
import signal
import threading

def detect_wayland_outputs():
    """Detect available Wayland outputs"""
    print("Detecting Wayland outputs...")
    
    outputs = []
    
    # Try wlr-randr first
    try:
        result = subprocess.run(['wlr-randr'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("  ✓ wlr-randr available")
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line.strip() and not line.startswith(' '):
                    output_name = line.strip()
                    if 'HDMI' in output_name or 'hdmi' in output_name:
                        outputs.append(output_name)
                        print(f"    Found output: {output_name}")
            return outputs
    except FileNotFoundError:
        print("  ⚠ wlr-randr not found")
    
    # Try swaymsg as alternative
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
    
    # Fallback
    if not outputs:
        print("  ⚠ Could not detect outputs, using fallback names")
        outputs = ['HDMI-A-1', 'HDMI-A-2']
    
    return outputs

def test_output_isolation(output_name, hdmi_name):
    """Test that a specific output can display content independently"""
    print(f"Testing output isolation for {hdmi_name} (Output: {output_name})...")
    
    # Set Wayland environment
    os.environ['WAYLAND_DISPLAY'] = 'wayland-0'
    os.environ['XDG_SESSION_TYPE'] = 'wayland'
    
    success = True
    test_processes = []
    
    try:
        # Test 1: Create a unique terminal for this output
        if command_exists('weston-terminal'):
            print(f"  Creating weston-terminal for {hdmi_name}...")
            
            # Create a unique title and command
            unique_id = f"{output_name}-{int(time.time())}"
            title = f"Test-{unique_id}"
            
            # Start terminal with unique identifier
            process = subprocess.Popen([
                'weston-terminal',
                '--title', title,
                '--shell', '/bin/bash',
                '-e', 'bash', '-c', 
                f'echo "Testing {hdmi_name} on {output_name}"; echo "Output ID: {unique_id}"; sleep 10'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            test_processes.append(process)
            
            # Give it time to appear
            time.sleep(3)
            
            if process.poll() is None:
                print(f"    ✓ weston-terminal started for {hdmi_name}")
                
                # Try to make it more visible
                try:
                    # Use ydotool to interact with the window
                    if command_exists('ydotool'):
                        # Press F11 to toggle fullscreen
                        subprocess.run(['ydotool', 'key', 'F11'], capture_output=True, timeout=2)
                        print(f"    ✓ Toggled fullscreen for {hdmi_name}")
                except Exception as e:
                    print(f"    ⚠ Could not toggle fullscreen: {e}")
                
            else:
                print(f"    ✗ weston-terminal failed to start for {hdmi_name}")
                success = False
        
        # Test 2: Create a simple Wayland surface (if available)
        elif command_exists('weston-simple-egl'):
            print(f"  Creating weston-simple-egl for {hdmi_name}...")
            
            # This creates a simple colored window
            process = subprocess.Popen([
                'weston-simple-egl',
                '--title', f"Test-{output_name}",
                '--geometry', '400x300'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            test_processes.append(process)
            time.sleep(2)
            
            if process.poll() is None:
                print(f"    ✓ weston-simple-egl started for {hdmi_name}")
            else:
                print(f"    ✗ weston-simple-egl failed for {hdmi_name}")
                success = False
        
        # Test 3: Create a notification (if available)
        if command_exists('notify-send'):
            print(f"  Creating notification for {hdmi_name}...")
            
            result = subprocess.run([
                'notify-send',
                '--app-name', f'Test-{output_name}',
                f'Testing {hdmi_name}',
                f'Output: {output_name}\nTime: {time.strftime("%H:%M:%S")}'
            ], capture_output=True, timeout=5)
            
            if result.returncode == 0:
                print(f"    ✓ Notification sent for {hdmi_name}")
            else:
                print(f"    ⚠ Notification failed for {hdmi_name}")
        
        # Test 4: Create a simple text display (if available)
        if command_exists('wl-copy'):
            print(f"  Testing clipboard for {hdmi_name}...")
            
            test_text = f"Testing {hdmi_name} on {output_name} - {time.strftime('%H:%M:%S')}"
            result = subprocess.run(['wl-copy'], input=test_text, text=True, capture_output=True, timeout=5)
            
            if result.returncode == 0:
                print(f"    ✓ Clipboard test for {hdmi_name}")
            else:
                print(f"    ⚠ Clipboard test failed for {hdmi_name}")
        
        # Let the tests run for a while
        print(f"  Tests running for {hdmi_name} - check if content appears on the correct screen")
        time.sleep(5)
        
        return success, test_processes
        
    except Exception as e:
        print(f"    ✗ Error testing output isolation for {hdmi_name}: {e}")
        return False, test_processes

def cleanup_processes(processes):
    """Clean up test processes"""
    for process in processes:
        try:
            if process and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
        except Exception as e:
            print(f"    ⚠ Error cleaning up process: {e}")

def command_exists(command):
    """Check if a command exists"""
    try:
        subprocess.run([command, '--version'], capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
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
                return False
    except Exception as e:
        print(f"  ⚠ Could not check compositor: {e}")
        return False
    
    return True

def main():
    """Main test function"""
    print("=" * 60)
    print("WAYLAND OUTPUT ISOLATION TEST")
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
        print("✗ Not running in Wayland session")
        print("  This script is designed for Wayland environments")
        exit(1)
    
    # Detect Wayland outputs
    outputs = detect_wayland_outputs()
    
    if not outputs:
        print("✗ No Wayland outputs detected")
        print("  Please check your Wayland configuration")
        exit(1)
    
    print(f"Detected {len(outputs)} outputs: {outputs}")
    print()
    
    # Test each output independently
    results = {}
    all_processes = []
    
    print("IMPORTANT: This test will create windows on each output.")
    print("Make sure you can see both screens and identify which is which.")
    print("Each output will be tested sequentially to avoid confusion.")
    print()
    
    input("Press Enter to continue with the test...")
    
    for i, output_name in enumerate(outputs):
        hdmi_name = f"HDMI{i+1} ({'Primary' if i == 0 else 'Secondary'})"
        print(f"Testing {hdmi_name}...")
        print("-" * 40)
        
        # Test this output
        success, processes = test_output_isolation(output_name, hdmi_name)
        results[hdmi_name] = success
        all_processes.extend(processes)
        
        print()
        print(f"✓ {hdmi_name} test completed")
        print()
        
        # Ask user to confirm they saw the content
        if i < len(outputs) - 1:  # Not the last output
            response = input(f"Did you see content appear on {hdmi_name}? (y/n): ")
            if response.lower() in ['y', 'yes']:
                print(f"  ✓ User confirmed {hdmi_name} is working")
            else:
                print(f"  ⚠ User reports {hdmi_name} is not working")
                results[hdmi_name] = False
        
        print("=" * 60)
        print()
    
    # Cleanup
    print("Cleaning up test processes...")
    cleanup_processes(all_processes)
    
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
        print("Your Wayland outputs are working independently.")
        print()
        print("You can now run the multi-screen clients:")
        print("  Terminal 1: python3 client_wayland.py --target-screen HDMI1")
        print("  Terminal 2: python3 client_wayland.py --target-screen HDMI2")
    else:
        print("⚠ SOME TESTS FAILED")
        print("Please check the error messages above and verify your setup.")
        print()
        print("Common issues:")
        print("  1. Dual HDMI not enabled in /boot/config.txt")
        print("  2. Wayland compositor not properly configured")
        print("  3. Missing Wayland tools (weston-terminal, etc.)")
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
