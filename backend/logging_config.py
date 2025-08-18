"""
Comprehensive Logging Configuration for Multi-Screen Streaming System
Provides detailed logging for debugging streaming issues, FFmpeg processes, and system resources
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime

def setup_comprehensive_logging():
    """Setup comprehensive logging for the streaming system"""
    
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler (INFO level)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler for all logs (DEBUG level)
    all_logs_file = os.path.join(logs_dir, 'all.log')
    all_handler = logging.handlers.RotatingFileHandler(
        all_logs_file, maxBytes=10*1024*1024, backupCount=5
    )
    all_handler.setLevel(logging.DEBUG)
    all_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(all_handler)
    
    # File handler for errors only (ERROR level)
    error_logs_file = os.path.join(logs_dir, 'errors.log')
    error_handler = logging.handlers.RotatingFileHandler(
        error_logs_file, maxBytes=5*1024*1024, backupCount=3
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)
    
    # File handler for FFmpeg-specific logs (INFO level)
    ffmpeg_logs_file = os.path.join(logs_dir, 'ffmpeg.log')
    ffmpeg_handler = logging.handlers.RotatingFileHandler(
        ffmpeg_logs_file, maxBytes=5*1024*1024, backupCount=3
    )
    ffmpeg_handler.setLevel(logging.INFO)
    ffmpeg_handler.setFormatter(detailed_formatter)
    
    # Create FFmpeg logger
    ffmpeg_logger = logging.getLogger('ffmpeg')
    ffmpeg_logger.setLevel(logging.INFO)
    ffmpeg_logger.addHandler(ffmpeg_handler)
    
    # File handler for client management logs (INFO level)
    client_logs_file = os.path.join(logs_dir, 'clients.log')
    client_handler = logging.handlers.RotatingFileHandler(
        client_logs_file, maxBytes=5*1024*1024, backupCount=3
    )
    client_handler.setLevel(logging.INFO)
    client_handler.setFormatter(detailed_formatter)
    
    # Create client management logger
    client_logger = logging.getLogger('blueprints.client_management')
    client_logger.setLevel(logging.INFO)
    client_logger.addHandler(client_handler)
    
    # File handler for streaming logs (INFO level)
    streaming_logs_file = os.path.join(logs_dir, 'streaming.log')
    streaming_handler = logging.handlers.RotatingFileHandler(
        streaming_logs_file, maxBytes=5*1024*1024, backupCount=3
    )
    streaming_handler.setLevel(logging.INFO)
    streaming_handler.setFormatter(detailed_formatter)
    
    # Create streaming logger
    streaming_logger = logging.getLogger('blueprints.streaming')
    streaming_logger.setLevel(logging.INFO)
    streaming_logger.addHandler(streaming_handler)
    
    # File handler for system resource logs (INFO level)
    system_logs_file = os.path.join(logs_dir, 'system.log')
    system_handler = logging.handlers.RotatingFileHandler(
        system_logs_file, maxBytes=2*1024*1024, backupCount=2
    )
    system_handler.setLevel(logging.INFO)
    system_handler.setFormatter(detailed_formatter)
    
    # Create system logger
    system_logger = logging.getLogger('system')
    system_logger.setLevel(logging.INFO)
    system_logger.addHandler(system_handler)
    
    # Log startup message
    root_logger.info("=" * 80)
    root_logger.info("COMPREHENSIVE LOGGING SYSTEM STARTED")
    root_logger.info(f"Logs directory: {logs_dir}")
    root_logger.info(f"Log files:")
    root_logger.info(f"   - All logs: {all_logs_file}")
    root_logger.info(f"   - Errors only: {error_logs_file}")
    root_logger.info(f"   - FFmpeg: {ffmpeg_logs_file}")
    root_logger.info(f"   - Clients: {client_logs_file}")
    root_logger.info(f"   - Streaming: {streaming_logs_file}")
    root_logger.info(f"   - System: {system_logs_file}")
    root_logger.info("=" * 80)
    
    return root_logger

def log_system_resources():
    """Log current system resource usage"""
    try:
        import psutil
        
        system_logger = logging.getLogger('system')
        
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        
        # Disk usage
        disk = psutil.disk_usage('/')
        
        # Process count
        process_count = len(psutil.pids())
        
        # FFmpeg processes
        ffmpeg_count = 0
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] == 'ffmpeg':
                    ffmpeg_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        system_logger.info(f"System Resources: CPU={cpu_percent:.1f}%, "
                          f"Memory={memory.percent:.1f}% ({memory.used/1024/1024/1024:.1f}GB), "
                          f"Disk={disk.percent:.1f}%, "
                          f"Processes={process_count}, "
                          f"FFmpeg={ffmpeg_count}")
        
        # Warning thresholds
        if memory.percent > 80:
            system_logger.warning(f"High memory usage: {memory.percent:.1f}%")
        if disk.percent > 90:
            system_logger.warning(f"Low disk space: {disk.percent:.1f}%")
        if cpu_percent > 90:
            system_logger.warning(f"High CPU usage: {cpu_percent:.1f}%")
            
    except Exception as e:
        logging.error(f"Could not log system resources: {e}")

def log_ffmpeg_process_details(pid: int, process_name: str = "FFmpeg"):
    """Log detailed information about a specific FFmpeg process"""
    try:
        import psutil
        
        ffmpeg_logger = logging.getLogger('ffmpeg')
        
        proc = psutil.Process(pid)
        
        # Process info
        create_time = proc.create_time()
        cpu_percent = proc.cpu_percent()
        memory_info = proc.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        
        # Command line
        cmdline = ' '.join(proc.cmdline()) if proc.cmdline() else "Unknown"
        
        ffmpeg_logger.info(f"{process_name} Process Details:")
        ffmpeg_logger.info(f"   PID: {pid}")
        ffmpeg_logger.info(f"   Started: {datetime.fromtimestamp(create_time).strftime('%Y-%m-%d %H:%M:%S')}")
        ffmpeg_logger.info(f"   CPU: {cpu_percent:.1f}%")
        ffmpeg_logger.info(f"   Memory: {memory_mb:.1f}MB")
        ffmpeg_logger.info(f"   Command: {cmdline[:200]}...")
        
    except Exception as e:
        logging.error(f"Could not log FFmpeg process details: {e}")

if __name__ == "__main__":
    # Test the logging setup
    setup_comprehensive_logging()
    logging.info("Logging system test successful")
    log_system_resources()
