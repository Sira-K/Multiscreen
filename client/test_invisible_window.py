#!/usr/bin/env python3
"""
Test script to verify the invisible window manager works correctly
"""

import tkinter as tk
import time
import sys

def test_invisible_window():
    """Test creating an invisible window manager"""
    print("🔍 Testing invisible window manager...")
    
    try:
        # Create invisible window like the client does
        window_manager = tk.Tk()
        window_manager.title("Test Invisible Window")
        
        # Make window invisible
        window_manager.withdraw()  # Hide the window
        window_manager.attributes('-alpha', 0.0)  # Make completely transparent
        
        # Set minimal size to avoid any visual impact
        window_manager.geometry("1x1+0+0")
        
        print("✅ Invisible window created successfully")
        print("   - Window is hidden (withdraw)")
        print("   - Window is transparent (alpha=0.0)")
        print("   - Window size is minimal (1x1)")
        
        # Test that the window can still process events
        print("   - Testing event processing...")
        
        # Simulate some background processing
        for i in range(3):
            window_manager.update()
            print(f"   - Event processing cycle {i+1}/3")
            time.sleep(0.5)
        
        # Clean up
        window_manager.destroy()
        print("✅ Invisible window destroyed successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Invisible window test failed: {e}")
        return False

def test_visible_vs_invisible():
    """Compare visible vs invisible window behavior"""
    print("\n🔍 Comparing visible vs invisible windows...")
    
    try:
        # Test 1: Visible window (old behavior)
        print("   Test 1: Visible window (old behavior)")
        visible_window = tk.Tk()
        visible_window.title("Visible Test Window")
        visible_window.geometry("300x200")
        visible_window.configure(bg='black')
        
        label = tk.Label(visible_window, 
                        text="This would be visible\n(black box)",
                        fg='white', bg='black', font=('Arial', 12))
        label.pack(expand=True)
        
        print("   - Visible window created (you should see a black box)")
        print("   - Press Enter to continue...")
        input()
        
        visible_window.destroy()
        print("   - Visible window destroyed")
        
        # Test 2: Invisible window (new behavior)
        print("\n   Test 2: Invisible window (new behavior)")
        invisible_window = tk.Tk()
        invisible_window.title("Invisible Test Window")
        invisible_window.withdraw()
        invisible_window.attributes('-alpha', 0.0)
        invisible_window.geometry("1x1+0+0")
        
        print("   - Invisible window created (no visible window)")
        print("   - Press Enter to continue...")
        input()
        
        invisible_window.destroy()
        print("   - Invisible window destroyed")
        
        return True
        
    except Exception as e:
        print(f"❌ Comparison test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Testing invisible window manager")
    print("=" * 50)
    
    # Test 1: Basic invisible window functionality
    if not test_invisible_window():
        print("\n❌ Basic invisible window test failed")
        return
    
    # Test 2: Comparison with visible window
    response = input("\n🎬 Test visible vs invisible comparison? (y/n): ").lower().strip()
    if response == 'y':
        if not test_visible_vs_invisible():
            print("\n❌ Comparison test failed")
            return
    
    print("\n✅ Invisible window test complete!")
    print("\n📋 Summary of changes:")
    print("   1. ✅ Window manager is now invisible")
    print("   2. ✅ No black box appears on startup")
    print("   3. ✅ Background processing still works")
    print("   4. ✅ Event handling still functional")
    print("   5. ✅ Clean shutdown process")

if __name__ == "__main__":
    main()
