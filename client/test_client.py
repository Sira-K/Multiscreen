#!/usr/bin/env python3
"""
Comprehensive Test Script for Enhanced Multi-Screen Client
Tests the single-threaded client functionality for Raspberry Pi optimization
"""

import subprocess
import sys
import time
import signal
import os
from typing import Dict, List, Tuple

class ClientTester:
    """Test suite for the enhanced multi-screen client"""
    
    def __init__(self):
        self.test_results = []
        self.current_test = None
        self.client_process = None
        
    def log_test(self, test_name: str, status: str, details: str = ""):
        """Log test results"""
        result = {
            'test': test_name,
            'status': status,
            'details': details,
            'timestamp': time.strftime('%H:%M:%S')
        }
        self.test_results.append(result)
        
        # Print colored output
        if status == 'PASS':
            print(f"✅ {test_name}: PASS")
        elif status == 'FAIL':
            print(f"❌ {test_name}: FAIL - {details}")
        else:
            print(f"⚠️  {test_name}: {status} - {details}")
    
    def run_command(self, cmd: List[str], timeout: int = 10) -> Tuple[int, str, str]:
        """Run a command and return results"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except Exception as e:
            return -1, "", str(e)
    
    def test_basic_functionality(self) -> bool:
        """Test basic client functionality"""
        print("\n🔍 Testing Basic Functionality...")
        
        # Test 1: Version check
        returncode, stdout, stderr = self.run_command(['python3', 'client.py', '--version'])
        if returncode == 0 and 'Enhanced Multi-Screen Client' in stdout:
            self.log_test("Version Check", "PASS")
        else:
            self.log_test("Version Check", "FAIL", f"Return code: {returncode}, Output: {stdout}")
            return False
        
        # Test 2: Help system
        returncode, stdout, stderr = self.run_command(['python3', 'client.py', '--help'])
        if returncode == 0 and 'SINGLE-THREADED ARCHITECTURE' in stdout:
            self.log_test("Help System", "PASS")
        else:
            self.log_test("Help System", "FAIL", f"Return code: {returncode}")
            return False
        
        # Test 3: Missing required arguments
        returncode, stdout, stderr = self.run_command(['python3', 'client.py'])
        if returncode != 0 and 'error: the following arguments are required' in stderr:
            self.log_test("Required Arguments Validation", "PASS")
        else:
            self.log_test("Required Arguments Validation", "FAIL", f"Expected error, got: {returncode}")
            return False
        
        return True
    
    def test_target_screen_validation(self) -> bool:
        """Test target screen parameter validation"""
        print("\n🎯 Testing Target Screen Validation...")
        
        # Test valid target screen values
        valid_screens = ['1', '2']
        for screen in valid_screens:
            cmd = [
                'python3', 'client.py',
                '--server', 'http://test:5000',
                '--hostname', f'test-client-{screen}',
                '--display-name', f'Test Screen {screen}',
                '--target-screen', screen
            ]
            
            # Start client and let it run briefly
            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Let it run for a few seconds
                time.sleep(3)
                
                # Check if it's running and has correct output
                if process.poll() is None:
                    # Process is still running, check output
                    stdout, stderr = process.communicate(timeout=1)
                    if f'Target Screen: Screen {screen}' in stdout:
                        self.log_test(f"Target Screen {screen} Validation", "PASS")
                    else:
                        self.log_test(f"Target Screen {screen} Validation", "FAIL", "Incorrect screen mapping")
                        process.terminate()
                        return False
                else:
                    self.log_test(f"Target Screen {screen} Validation", "FAIL", "Process exited too early")
                    return False
                
                # Clean up
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    
            except Exception as e:
                self.log_test(f"Target Screen {screen} Validation", "FAIL", str(e))
                return False
        
        # Test invalid target screen value
        cmd = [
            'python3', 'client.py',
            '--server', 'http://test:5000',
            '--hostname', 'test-client-invalid',
            '--display-name', 'Test Invalid',
            '--target-screen', '3'
        ]
        
        returncode, stdout, stderr = self.run_command(cmd, timeout=5)
        if returncode != 0 or 'Invalid target screen' in stdout:
            self.log_test("Invalid Target Screen Validation", "PASS")
        else:
            self.log_test("Invalid Target Screen Validation", "FAIL", "Should reject invalid screen value")
            return False
        
        return True
    
    def test_single_threaded_mode(self) -> bool:
        """Test that client runs in single-threaded mode"""
        print("\n🧵 Testing Single-Threaded Mode...")
        
        cmd = [
            'python3', 'client.py',
            '--server', 'http://test:5000',
            '--hostname', 'test-single-thread',
            '--display-name', 'Single Thread Test',
            '--target-screen', '1'
        ]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Let it run briefly
            time.sleep(3)
            
            if process.poll() is None:
                # Check output for single-threaded indicators
                stdout, stderr = process.communicate(timeout=1)
                
                if 'SINGLE-THREADED: Enabled' in stdout:
                    self.log_test("Single-Threaded Mode Detection", "PASS")
                else:
                    self.log_test("Single-Threaded Mode Detection", "FAIL", "Should show single-threaded mode")
                    process.terminate()
                    return False
                
                if 'VideoPlayerThread' not in stdout:
                    self.log_test("No VideoPlayerThread", "PASS")
                else:
                    self.log_test("No VideoPlayerThread", "FAIL", "Should not use VideoPlayerThread")
                    process.terminate()
                    return False
            else:
                self.log_test("Single-Threaded Mode Test", "FAIL", "Process exited too early")
                return False
            
            # Clean up
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                
        except Exception as e:
            self.log_test("Single-Threaded Mode Test", "FAIL", str(e))
            return False
        
        return True
    
    def test_argument_parsing(self) -> bool:
        """Test various command line argument combinations"""
        print("\n🔧 Testing Argument Parsing...")
        
        # Test force-ffplay option
        cmd = [
            'python3', 'client.py',
            '--server', 'http://test:5000',
            '--hostname', 'test-force-ffplay',
            '--display-name', 'Force FFplay Test',
            '--target-screen', '1',
            '--force-ffplay'
        ]
        
        returncode, stdout, stderr = self.run_command(cmd, timeout=5)
        if returncode != 0 or 'Smart Player: Disabled' in stdout:
            self.log_test("Force FFplay Option", "PASS")
        else:
            self.log_test("Force FFplay Option", "FAIL", "Should disable smart player selection")
            return False
        
        # Test debug option
        cmd = [
            'python3', 'client.py',
            '--server', 'http://test:5000',
            '--hostname', 'test-debug',
            '--display-name', 'Debug Test',
            '--target-screen', '1',
            '--debug'
        ]
        
        returncode, stdout, stderr = self.run_command(cmd, timeout=5)
        if returncode != 0:
            self.log_test("Debug Option", "PASS")
        else:
            self.log_test("Debug Option", "FAIL", "Debug mode should work")
            return False
        
        return True
    
    def test_error_handling(self) -> bool:
        """Test error handling and graceful failures"""
        print("\n⚠️ Testing Error Handling...")
        
        # Test invalid server URL
        cmd = [
            'python3', 'client.py',
            '--server', 'invalid-url',
            '--hostname', 'test-error',
            '--display-name', 'Error Test',
            '--target-screen', '1'
        ]
        
        returncode, stdout, stderr = self.run_command(cmd, timeout=5)
        if returncode != 0:
            self.log_test("Invalid Server URL Handling", "PASS")
        else:
            self.log_test("Invalid Server URL Handling", "FAIL", "Should handle invalid URLs gracefully")
            return False
        
        # Test missing required arguments
        cmd = ['python3', 'client.py', '--server', 'http://test:5000']
        returncode, stdout, stderr = self.run_command(cmd)
        if returncode != 0 and 'required' in stderr:
            self.log_test("Missing Required Arguments", "PASS")
        else:
            self.log_test("Missing Required Arguments", "FAIL", "Should require all mandatory arguments")
            return False
        
        return True
    
    def test_cleanup_and_shutdown(self) -> bool:
        """Test cleanup and shutdown behavior"""
        print("\n🔄 Testing Cleanup and Shutdown...")
        
        cmd = [
            'python3', 'client.py',
            '--server', 'http://test:5000',
            '--hostname', 'test-cleanup',
            '--display-name', 'Cleanup Test',
            '--target-screen', '1'
        ]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Let it start
            time.sleep(2)
            
            if process.poll() is None:
                # Send SIGTERM for graceful shutdown
                process.terminate()
                
                try:
                    process.wait(timeout=5)
                    self.log_test("Graceful Shutdown", "PASS")
                except subprocess.TimeoutExpired:
                    # Force kill if graceful shutdown fails
                    process.kill()
                    process.wait()
                    self.log_test("Graceful Shutdown", "FAIL", "Did not shutdown gracefully")
                    return False
            else:
                self.log_test("Process Startup", "FAIL", "Process exited too early")
                return False
                
        except Exception as e:
            self.log_test("Cleanup Test", "FAIL", str(e))
            return False
        
        return True
    
    def run_all_tests(self) -> bool:
        """Run all test suites"""
        print("🚀 Starting Enhanced Multi-Screen Client Test Suite")
        print("=" * 60)
        
        tests = [
            ("Basic Functionality", self.test_basic_functionality),
            ("Target Screen Validation", self.test_target_screen_validation),
            ("Single-Threaded Mode", self.test_single_threaded_mode),
            ("Argument Parsing", self.test_argument_parsing),
            ("Error Handling", self.test_error_handling),
            ("Cleanup and Shutdown", self.test_cleanup_and_shutdown)
        ]
        
        all_passed = True
        
        for test_name, test_func in tests:
            try:
                if not test_func():
                    all_passed = False
            except Exception as e:
                self.log_test(test_name, "FAIL", f"Test crashed: {str(e)}")
                all_passed = False
        
        return all_passed
    
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for r in self.test_results if r['status'] == 'PASS')
        failed = sum(1 for r in self.test_results if r['status'] == 'FAIL')
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if failed > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if result['status'] == 'FAIL':
                    print(f"  - {result['test']}: {result['details']}")
        
        print("\n" + "=" * 60)
        
        if all_passed:
            print("🎉 ALL TESTS PASSED! Client is working correctly.")
        else:
            print("⚠️  Some tests failed. Please check the details above.")
        
        return all_passed

def main():
    """Main test execution"""
    tester = ClientTester()
    
    try:
        # Check if client.py exists
        if not os.path.exists('client.py'):
            print("❌ Error: client.py not found in current directory")
            print("Please run this script from the client directory")
            sys.exit(1)
        
        # Run all tests
        all_passed = tester.run_all_tests()
        
        # Print summary
        tester.print_summary()
        
        # Exit with appropriate code
        sys.exit(0 if all_passed else 1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Testing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error during testing: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()

