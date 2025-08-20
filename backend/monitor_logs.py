#!/usr/bin/env python3
"""
Real-time Log Monitor for Multi-Screen Streaming System
Monitors all log files and displays them in real-time with filtering options
"""

import os
import sys
import time
import argparse
from datetime import datetime
import subprocess
from pathlib import Path

def get_log_files():
    """Get all available log files"""
    logs_dir = Path(__file__).parent / 'logs'
    if not logs_dir.exists():
        print(f"Logs directory not found: {logs_dir}")
        return []
    
    log_files = []
    for log_file in logs_dir.glob('*.log'):
        log_files.append({
            'path': log_file,
            'name': log_file.name,
            'size': log_file.stat().st_size if log_file.exists() else 0
        })
    
    return log_files

def monitor_log_file(log_file_path, filter_pattern=None, lines=50):
    """Monitor a single log file with tail -f"""
    try:
        # Show last N lines
        if lines > 0:
            print(f"\n Last {lines} lines of {log_file_path.name}:")
            print("=" * 80)
            
            try:
                result = subprocess.run(['tail', '-n', str(lines), str(log_file_path)], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n'):
                        if line and (not filter_pattern or filter_pattern.lower() in line.lower()):
                            print(line)
                else:
                    print(f"Error reading log file: {result.stderr}")
            except subprocess.TimeoutExpired:
                print(" Timeout reading log file")
        
        # Start tail -f monitoring
        print(f"\nStarting real-time monitoring of {log_file_path.name}")
        print("=" * 80)
        print("Press Ctrl+C to stop monitoring")
        print("=" * 80)
        
        cmd = ['tail', '-f', str(log_file_path)]
        if filter_pattern:
            cmd = ['tail', '-f', str(log_file_path), '|', 'grep', '-i', filter_pattern]
            cmd = f"tail -f {log_file_path} | grep -i '{filter_pattern}'"
            subprocess.run(cmd, shell=True)
        else:
            subprocess.run(cmd)
            
    except KeyboardInterrupt:
        print(f"\nStopped monitoring {log_file_path.name}")
    except Exception as e:
        print(f"Error monitoring {log_file_path.name}: {e}")

def show_log_summary():
    """Show summary of all log files"""
    log_files = get_log_files()
    if not log_files:
        return
    
    print("LOG FILES SUMMARY")
    print("=" * 80)
    
    for log_file in log_files:
        size_mb = log_file['size'] / (1024 * 1024)
        print(f"{log_file['name']:<20} {size_mb:>8.1f} MB")
    
    print("=" * 80)

def show_recent_errors(log_file_path, count=20):
    """Show recent error messages from a log file"""
    try:
        result = subprocess.run(['grep', '-i', 'error', str(log_file_path)], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            recent_errors = lines[-count:] if len(lines) > count else lines
            
            print(f"\nRecent errors in {log_file_path.name}:")
            print("=" * 80)
            
            for line in recent_errors:
                if line.strip():
                    print(line)
        else:
            print(f"No errors found in {log_file_path.name}")
            
    except subprocess.TimeoutExpired:
        print(" Timeout searching for errors")
    except Exception as e:
        print(f"Error searching for errors: {e}")

def show_ffmpeg_processes():
    """Show current FFmpeg processes"""
    try:
        result = subprocess.run(['pgrep', '-f', 'ffmpeg'], capture_output=True, text=True)
        
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            print(f"\nActive FFmpeg Processes: {len(pids)}")
            print("=" * 80)
            
            for pid in pids:
                if pid.strip():
                    try:
                        # Get process details
                        ps_result = subprocess.run(['ps', '-p', pid, '-o', 'pid,ppid,cmd'], 
                                                 capture_output=True, text=True, timeout=5)
                        if ps_result.returncode == 0:
                            lines = ps_result.stdout.strip().split('\n')
                            if len(lines) > 1:
                                print(f"PID {pid}: {lines[1]}")
                    except:
                        print(f"PID {pid}: <could not get details>")
        else:
            print("No FFmpeg processes currently running")
            
    except Exception as e:
        print(f"Error checking FFmpeg processes: {e}")

def main():
    parser = argparse.ArgumentParser(description='Monitor Multi-Screen Streaming System Logs')
    parser.add_argument('--file', '-f', help='Specific log file to monitor')
    parser.add_argument('--filter', help='Filter pattern for log lines')
    parser.add_argument('--errors', action='store_true', help='Show recent errors')
    parser.add_argument('--summary', action='store_true', help='Show log files summary')
    parser.add_argument('--ffmpeg', action='store_true', help='Show FFmpeg processes')
    parser.add_argument('--lines', '-n', type=int, default=50, help='Number of lines to show initially')
    
    args = parser.parse_args()
    
    print("Multi-Screen Streaming System Log Monitor")
    print("=" * 80)
    
    # Show summary
    if args.summary:
        show_log_summary()
        return
    
    # Show FFmpeg processes
    if args.ffmpeg:
        show_ffmpeg_processes()
        return
    
    # Get log files
    log_files = get_log_files()
    if not log_files:
        print("No log files found. Make sure the backend server is running.")
        return
    
    # If specific file requested
    if args.file:
        log_file = None
        for lf in log_files:
            if lf['name'] == args.file or lf['name'].startswith(args.file):
                log_file = lf
                break
        
        if not log_file:
            print(f"Log file '{args.file}' not found")
            print("Available log files:")
            for lf in log_files:
                print(f"  - {lf['name']}")
            return
        
        # Show errors if requested
        if args.errors:
            show_recent_errors(log_file['path'], args.lines)
            return
        
        # Monitor the file
        monitor_log_file(log_file['path'], args.filter, args.lines)
        return
    
    # Show errors for all files
    if args.errors:
        for log_file in log_files:
            show_recent_errors(log_file['path'], args.lines)
        return
    
    # Default: show summary and let user choose
    show_log_summary()
            print("\nUsage examples:")
    print("  python monitor_logs.py --file errors.log --filter 'ffmpeg'")
    print("  python monitor_logs.py --file ffmpeg.log --lines 100")
    print("  python monitor_logs.py --errors")
    print("  python monitor_logs.py --ffmpeg")
    print("  python monitor_logs.py --summary")

if __name__ == "__main__":
    main()
