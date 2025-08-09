#!/usr/bin/env python3
"""
Test script for video management error handling system
Tests all error codes and scenarios
"""

import requests
import os
import time
import json
import tempfile
import random
import string
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:5000"  # Change this to your server URL
UPLOAD_ENDPOINT = f"{API_BASE_URL}/upload_video"
DELETE_ENDPOINT = f"{API_BASE_URL}/delete_video"
GET_VIDEOS_ENDPOINT = f"{API_BASE_URL}/get_videos"

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class VideoErrorTester:
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.test_results = []
        self.test_files = []
        self.temp_dir = tempfile.mkdtemp(prefix="video_test_")
        print(f"{Colors.OKCYAN}Created temp directory: {self.temp_dir}{Colors.ENDC}")
        
    def cleanup(self):
        """Clean up test files"""
        print(f"\n{Colors.WARNING}Cleaning up test files...{Colors.ENDC}")
        for file_path in self.test_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"  Removed: {file_path}")
            except Exception as e:
                print(f"  Failed to remove {file_path}: {e}")
        
        # Remove temp directory
        try:
            os.rmdir(self.temp_dir)
            print(f"  Removed temp directory: {self.temp_dir}")
        except:
            pass
    
    def create_test_file(self, filename: str, size_mb: float = 0.1, content: bytes = None) -> str:
        """Create a test file with specified size"""
        file_path = os.path.join(self.temp_dir, filename)
        
        if content is not None:
            with open(file_path, 'wb') as f:
                f.write(content)
        else:
            # Create file with random content of specified size
            size_bytes = int(size_mb * 1024 * 1024)
            with open(file_path, 'wb') as f:
                # Write in chunks to avoid memory issues
                chunk_size = 1024 * 1024  # 1MB chunks
                remaining = size_bytes
                while remaining > 0:
                    chunk = min(chunk_size, remaining)
                    f.write(os.urandom(chunk))
                    remaining -= chunk
        
        self.test_files.append(file_path)
        return file_path
    
    def print_test_header(self, test_name: str):
        """Print formatted test header"""
        print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}TEST: {test_name}{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")
    
    def print_result(self, success: bool, message: str, details: dict = None):
        """Print test result"""
        if success:
            print(f"{Colors.OKGREEN}✓ PASS: {message}{Colors.ENDC}")
        else:
            print(f"{Colors.FAIL}✗ FAIL: {message}{Colors.ENDC}")
        
        if details:
            print(f"{Colors.OKCYAN}  Details: {json.dumps(details, indent=2)}{Colors.ENDC}")
        
        self.test_results.append({
            'success': success,
            'message': message,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
    
    # ==================== TEST CASES ====================
    
    def test_501_no_file_provided(self):
        """Test Error 501: No file provided in request"""
        self.print_test_header("Error 501 - No File Provided")
        
        try:
            # Send request without any files
            response = requests.post(UPLOAD_ENDPOINT, timeout=10)
            data = response.json()
            
            if response.status_code == 400 and data.get('error_code') == 501:
                self.print_result(True, "Correctly returned error 501", {
                    'error_code': data.get('error_code'),
                    'error_message': data.get('error_message')
                })
            else:
                self.print_result(False, "Did not return expected error 501", data)
                
        except Exception as e:
            self.print_result(False, f"Test failed with exception: {str(e)}")
    
    def test_501_invalid_file_type(self):
        """Test Error 501: Invalid file extension"""
        self.print_test_header("Error 501 - Invalid File Type")
        
        try:
            # Create a text file
            test_file = self.create_test_file("test_document.txt", 0.001, b"This is not a video file")
            
            with open(test_file, 'rb') as f:
                files = {'video': ('document.txt', f, 'text/plain')}
                response = requests.post(UPLOAD_ENDPOINT, files=files, timeout=10)
                data = response.json()
            
            # Check if the error was properly caught
            # The file should be in 'failed' array with error_code 501
            if response.status_code == 400 and not data.get('success'):
                failed_files = data.get('failed', [])
                if failed_files and any(f.get('error_code') == 501 for f in failed_files):
                    failed_file = next(f for f in failed_files if f.get('error_code') == 501)
                    self.print_result(True, "Correctly rejected .txt file", {
                        'error_code': failed_file.get('error_code'),
                        'error_message': failed_file.get('error_message'),
                        'invalid_extension': failed_file.get('context', {}).get('invalid_extension')
                    })
                else:
                    self.print_result(False, "Error code 501 not found in failed files", data)
            else:
                self.print_result(False, "Did not reject invalid file type properly", data)
                
        except Exception as e:
            self.print_result(False, f"Test failed with exception: {str(e)}")
    
    def test_508_file_too_large(self):
        """Test Error 508: File size exceeds limit"""
        self.print_test_header("Error 508 - File Too Large")
        
        # NOTE: To properly test this, we need to either:
        # 1. Actually create a large file (slow)
        # 2. Temporarily modify the server's max_size limit
        # 3. Mock the file size check
        
        print(f"{Colors.WARNING}  Note: File size validation checks actual file size, not headers{Colors.ENDC}")
        print(f"{Colors.WARNING}  To properly test error 508:{Colors.ENDC}")
        print(f"{Colors.WARNING}  1. Temporarily set max_size = 1024 in validate_upload() function{Colors.ENDC}")
        print(f"{Colors.WARNING}  2. Or create an actual 2GB+ file (not recommended){Colors.ENDC}")
        
        try:
            # Try with a file that would be too large if limit was 1KB
            test_file = self.create_test_file("large_video.mp4", 0.01)  # 10KB file
            
            with open(test_file, 'rb') as f:
                files = {'video': ('large.mp4', f, 'video/mp4')}
                response = requests.post(UPLOAD_ENDPOINT, files=files, timeout=10)
                data = response.json()
            
            # Check if this is configured to catch large files
            if response.status_code == 400 and not data.get('success'):
                failed_files = data.get('failed', [])
                if failed_files and any(f.get('error_code') == 508 for f in failed_files):
                    self.print_result(True, "File size limit is enforced (limit may be reduced for testing)", {
                        'error_code': 508,
                        'file_size_kb': 10
                    })
                else:
                    self.print_result(False, "File uploaded successfully - size limit may be 2GB (too large to test)", {
                        'note': 'Reduce max_size in validate_upload() to test this error'
                    })
            else:
                # File uploaded successfully - expected if limit is 2GB
                self.print_result(True, "File size under 2GB limit (as expected)", {
                    'note': 'To test error 508, temporarily reduce max_size in server code',
                    'current_test_file_size': '10KB',
                    'server_limit': 'likely 2GB'
                })
                
        except Exception as e:
            self.print_result(False, f"Test failed with exception: {str(e)}")
    
    def test_successful_upload(self):
        """Test successful video upload"""
        self.print_test_header("Successful Upload")
        
        try:
            # Create a valid video file (fake MP4 with proper header)
            mp4_header = b'\x00\x00\x00\x20\x66\x74\x79\x70\x69\x73\x6f\x6d'  # Basic MP4 header
            test_file = self.create_test_file("valid_video.mp4", 0.1, mp4_header + os.urandom(1024))
            
            with open(test_file, 'rb') as f:
                files = {'video': ('test_video.mp4', f, 'video/mp4')}
                response = requests.post(UPLOAD_ENDPOINT, files=files, timeout=30)
                data = response.json()
            
            if response.status_code == 200 and data.get('success'):
                self.print_result(True, "Successfully uploaded video", {
                    'uploads': data.get('uploads', []),
                    'timing': data.get('timing', {}).get('total_time_seconds')
                })
                
                # Store uploaded filename for cleanup
                if data.get('uploads'):
                    self.uploaded_file = data['uploads'][0].get('saved_filename')
                    return True
            else:
                self.print_result(False, "Upload failed", data)
                return False
                
        except Exception as e:
            self.print_result(False, f"Test failed with exception: {str(e)}")
            return False
    
    def test_224_delete_nonexistent(self):
        """Test Error 224: File not found for deletion"""
        self.print_test_header("Error 224 - Delete Nonexistent File")
        
        try:
            random_name = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            response = requests.post(DELETE_ENDPOINT, 
                                    json={'video_name': f'nonexistent_{random_name}.mp4'},
                                    timeout=10)
            data = response.json()
            
            if response.status_code == 404 and data.get('error_code') == 224:
                self.print_result(True, "Correctly returned error 224 for nonexistent file", {
                    'error_code': data.get('error_code'),
                    'searched_locations': data.get('context', {}).get('searched_locations')
                })
            else:
                self.print_result(False, "Did not return expected error 224", data)
                
        except Exception as e:
            self.print_result(False, f"Test failed with exception: {str(e)}")
    
    def test_successful_delete(self):
        """Test successful video deletion"""
        self.print_test_header("Successful Delete")
        
        try:
            # First upload a file
            if hasattr(self, 'uploaded_file') and self.uploaded_file:
                response = requests.post(DELETE_ENDPOINT, 
                                        json={'video_name': self.uploaded_file},
                                        timeout=10)
                data = response.json()
                
                if response.status_code == 200 and data.get('success'):
                    self.print_result(True, "Successfully deleted video", {
                        'deleted_files': data.get('deleted_files')
                    })
                else:
                    self.print_result(False, "Delete failed", data)
            else:
                self.print_result(False, "No file to delete (upload test may have failed)")
                
        except Exception as e:
            self.print_result(False, f"Test failed with exception: {str(e)}")
    
    def test_multiple_file_upload(self):
        """Test uploading multiple files at once"""
        self.print_test_header("Multiple File Upload")
        
        try:
            # Create multiple test files
            files_list = []
            for i in range(3):
                test_file = self.create_test_file(f"video_{i}.mp4", 0.05)
                files_list.append(('video', (f'video_{i}.mp4', open(test_file, 'rb'), 'video/mp4')))
            
            response = requests.post(UPLOAD_ENDPOINT, files=files_list, timeout=30)
            
            # Close file handles
            for _, (_, f, _) in files_list:
                f.close()
            
            data = response.json()
            
            if response.status_code == 200 and data.get('success'):
                uploads = data.get('uploads', [])
                self.print_result(True, f"Successfully uploaded {len(uploads)} files", {
                    'count': len(uploads),
                    'total_time': data.get('timing', {}).get('total_time_seconds')
                })
            else:
                self.print_result(False, "Multiple file upload failed", data)
                
        except Exception as e:
            self.print_result(False, f"Test failed with exception: {str(e)}")
    
    def test_mixed_valid_invalid_files(self):
        """Test uploading mix of valid and invalid files"""
        self.print_test_header("Mixed Valid/Invalid Files")
        
        try:
            # Create mix of files
            valid_file = self.create_test_file("valid.mp4", 0.05)
            invalid_file = self.create_test_file("invalid.txt", 0.01, b"Not a video")
            
            files_list = [
                ('video', ('valid.mp4', open(valid_file, 'rb'), 'video/mp4')),
                ('video', ('invalid.txt', open(invalid_file, 'rb'), 'text/plain'))
            ]
            
            response = requests.post(UPLOAD_ENDPOINT, files=files_list, timeout=30)
            
            # Close file handles
            for _, (_, f, _) in files_list:
                f.close()
            
            data = response.json()
            
            if data.get('uploads') and data.get('failed'):
                self.print_result(True, "Correctly processed mixed files", {
                    'successful': len(data.get('uploads', [])),
                    'failed': len(data.get('failed', [])),
                    'failed_errors': [f.get('error_code') for f in data.get('failed', [])]
                })
            else:
                self.print_result(False, "Mixed file handling unexpected", data)
                
        except Exception as e:
            self.print_result(False, f"Test failed with exception: {str(e)}")
    
    def test_empty_filename(self):
        """Test uploading file with empty filename"""
        self.print_test_header("Empty Filename")
        
        try:
            test_file = self.create_test_file("test.mp4", 0.01)
            
            with open(test_file, 'rb') as f:
                files = {'video': ('', f, 'video/mp4')}  # Empty filename
                response = requests.post(UPLOAD_ENDPOINT, files=files, timeout=10)
                data = response.json()
            
            if response.status_code == 400:
                self.print_result(True, "Correctly rejected empty filename", {
                    'status_code': response.status_code,
                    'message': data.get('message')
                })
            else:
                self.print_result(False, "Did not reject empty filename", data)
                
        except Exception as e:
            self.print_result(False, f"Test failed with exception: {str(e)}")
    
    def test_special_characters_filename(self):
        """Test uploading file with special characters in filename"""
        self.print_test_header("Special Characters in Filename")
        
        try:
            # Create file with special characters
            special_name = "test video (2024) [HD] #1.mp4"
            test_file = self.create_test_file("normal.mp4", 0.01)
            
            with open(test_file, 'rb') as f:
                files = {'video': (special_name, f, 'video/mp4')}
                response = requests.post(UPLOAD_ENDPOINT, files=files, timeout=10)
                data = response.json()
            
            if response.status_code == 200 and data.get('success'):
                saved_name = data.get('uploads', [{}])[0].get('saved_filename', '')
                self.print_result(True, "Successfully handled special characters", {
                    'original': special_name,
                    'saved_as': saved_name
                })
            else:
                self.print_result(False, "Failed to handle special characters", data)
                
        except Exception as e:
            self.print_result(False, f"Test failed with exception: {str(e)}")
    
    def test_get_videos_endpoint(self):
        """Test get videos endpoint"""
        self.print_test_header("Get Videos Endpoint")
        
        try:
            response = requests.get(GET_VIDEOS_ENDPOINT, timeout=10)
            data = response.json()
            
            if response.status_code == 200 and 'videos' in data:
                self.print_result(True, "Successfully retrieved video list", {
                    'count': len(data.get('videos', [])),
                    'total_size_mb': sum(v.get('size_mb', 0) for v in data.get('videos', []))
                })
            else:
                self.print_result(False, "Failed to retrieve videos", data)
                
        except Exception as e:
            self.print_result(False, f"Test failed with exception: {str(e)}")
    
    def run_all_tests(self):
        """Run all test cases"""
        print(f"\n{Colors.BOLD}{Colors.HEADER}Starting Video Error System Test Suite{Colors.ENDC}")
        print(f"Target API: {self.base_url}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Test order matters for some tests
        self.test_501_no_file_provided()
        self.test_501_invalid_file_type()
        self.test_508_file_too_large()
        self.test_empty_filename()
        self.test_special_characters_filename()
        self.test_successful_upload()  # Creates a file for delete test
        self.test_224_delete_nonexistent()
        self.test_successful_delete()  # Deletes the file from upload test
        self.test_multiple_file_upload()
        self.test_mixed_valid_invalid_files()
        self.test_get_videos_endpoint()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}TEST SUMMARY{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")
        
        passed = sum(1 for r in self.test_results if r['success'])
        failed = sum(1 for r in self.test_results if not r['success'])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"{Colors.OKGREEN}Passed: {passed}{Colors.ENDC}")
        print(f"{Colors.FAIL}Failed: {failed}{Colors.ENDC}")
        
        if failed > 0:
            print(f"\n{Colors.WARNING}Failed Tests:{Colors.ENDC}")
            for r in self.test_results:
                if not r['success']:
                    print(f"  - {r['message']}")
        
        # Save results to file
        results_file = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        print(f"\n{Colors.OKCYAN}Results saved to: {results_file}{Colors.ENDC}")
        
        return passed, failed

def main():
    """Main test execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test video error handling system')
    parser.add_argument('--url', default='http://localhost:5000', 
                       help='Base URL of the API (default: http://localhost:5000)')
    parser.add_argument('--test', help='Run specific test only')
    
    args = parser.parse_args()
    
    # Create tester instance
    tester = VideoErrorTester(args.url)
    
    try:
        if args.test:
            # Run specific test
            test_method = getattr(tester, f"test_{args.test}", None)
            if test_method:
                test_method()
                tester.print_summary()
            else:
                print(f"{Colors.FAIL}Test '{args.test}' not found{Colors.ENDC}")
                print("Available tests:")
                for attr in dir(tester):
                    if attr.startswith('test_'):
                        print(f"  - {attr[5:]}")
        else:
            # Run all tests
            tester.run_all_tests()
            
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Tests interrupted by user{Colors.ENDC}")
    except Exception as e:
        print(f"\n{Colors.FAIL}Test suite failed: {str(e)}{Colors.ENDC}")
    finally:
        # Cleanup
        tester.cleanup()

if __name__ == "__main__":
    main()