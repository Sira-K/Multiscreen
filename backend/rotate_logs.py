#!/usr/bin/env python3
"""
Log Rotation Utility for Multi-Screen Streaming System

This script manually rotates existing log files to keep only the newest N lines.
Useful for cleaning up old logs without losing recent information.
"""

import os
import sys
from datetime import datetime

def rotate_log_file(log_path, max_lines=1000):
    """Rotate a single log file to keep only the newest N lines"""
    try:
        if not os.path.exists(log_path):
            print(f"Log file not found: {log_path}")
            return False
        
        # Read all lines
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        original_lines = len(lines)
        
        if original_lines <= max_lines:
            print(f"No rotation needed: {log_path} has {original_lines} lines (≤ {max_lines})")
            return False
        
        # Keep only the newest lines
        new_lines = lines[-max_lines:]
        
        # Write back the truncated content
        with open(log_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        
        # Add rotation notice
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"\n# Log file manually rotated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - kept newest {len(new_lines)} lines\n")
        
        print(f"✓ Rotated: {log_path} ({original_lines} -> {len(new_lines)} lines)")
        return True
        
    except Exception as e:
        print(f"✗ Error rotating {log_path}: {e}")
        return False

def rotate_all_logs(logs_dir, max_lines=1000):
    """Rotate all log files in the logs directory"""
    if not os.path.exists(logs_dir):
        print(f"Logs directory not found: {logs_dir}")
        return
    
    print(f"Rotating log files in: {logs_dir}")
    print(f"Target: {max_lines} lines per file")
    print("-" * 50)
    
    log_files = [
        'all.log',
        'errors.log', 
        'ffmpeg.log',
        'clients.log',
        'streaming.log',
        'system.log',
        'flask_server.log'  # Include flask server log
    ]
    
    rotated_count = 0
    total_lines_removed = 0
    
    for log_file in log_files:
        log_path = os.path.join(logs_dir, log_file)
        if os.path.exists(log_path):
            try:
                # Count original lines
                with open(log_path, 'r', encoding='utf-8') as f:
                    original_lines = len(f.readlines())
                
                if rotate_log_file(log_path, max_lines):
                    rotated_count += 1
                    lines_removed = original_lines - max_lines
                    total_lines_removed += lines_removed
            except Exception as e:
                print(f"✗ Error processing {log_file}: {e}")
        else:
            print(f"- Skipped: {log_file} (not found)")
    
    print("-" * 50)
    if rotated_count > 0:
        print(f"✓ Successfully rotated {rotated_count} log files")
        print(f"✓ Total lines removed: {total_lines_removed:,}")
        print(f"✓ Space saved: approximately {total_lines_removed * 0.1:.1f} MB")
    else:
        print("No log files needed rotation")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Rotate log files to keep only the newest N lines')
    parser.add_argument('--logs-dir', default='logs', help='Logs directory path (default: logs)')
    parser.add_argument('--max-lines', type=int, default=1000, help='Maximum lines to keep per file (default: 1000)')
    parser.add_argument('--file', help='Rotate specific log file only')
    
    args = parser.parse_args()
    
    # Resolve logs directory path
    if not os.path.isabs(args.logs_dir):
        args.logs_dir = os.path.join(os.path.dirname(__file__), args.logs_dir)
    
    if args.file:
        # Rotate specific file
        log_path = os.path.join(args.logs_dir, args.file)
        if rotate_log_file(log_path, args.max_lines):
            print(f"✓ Successfully rotated {args.file}")
        else:
            sys.exit(1)
    else:
        # Rotate all log files
        rotate_all_logs(args.logs_dir, args.max_lines)

if __name__ == "__main__":
    main()
