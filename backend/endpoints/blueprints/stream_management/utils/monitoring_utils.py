import psutil
import time
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class ProcessMonitor:
    """Utility class for monitoring FFmpeg processes"""
    
    @staticmethod
    def find_ffmpeg_processes_for_group(group_id: str, group_name: str, container_id: str = None) -> List[Dict[str, Any]]:
        """Find running FFmpeg processes for a group using strict matching"""
        try:
            ffmpeg_processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] and 'ffmpeg' in proc.info['name'].lower():
                        cmdline = ' '.join(proc.info['cmdline'] or [])
                        
                        is_match = False
                        match_method = ""
                        
                        # Strict matching
                        stream_path_pattern = f"live/{group_name}/"
                        if stream_path_pattern in cmdline:
                            is_match = True
                            match_method = f"stream_path({stream_path_pattern})"
                        elif group_id in cmdline:
                            is_match = True
                            match_method = f"full_group_id({group_id})"
                        elif container_id and container_id[:12] in cmdline:
                            is_match = True
                            match_method = f"container_id({container_id[:12]})"
                        
                        if is_match:
                            ffmpeg_processes.append({
                                "pid": proc.info['pid'],
                                "cmdline": cmdline,
                                "create_time": proc.create_time() if hasattr(proc, 'create_time') else None,
                                "match_method": match_method
                            })
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return ffmpeg_processes
            
        except Exception as e:
            logger.error(f"Error finding FFmpeg processes for group {group_name}: {e}")
            return []
    
    @staticmethod
    def get_all_ffmpeg_processes() -> List[Dict[str, Any]]:
        """Get all FFmpeg processes running on the system"""
        all_ffmpeg_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and 'ffmpeg' in proc.info['name'].lower():
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    all_ffmpeg_processes.append({
                        "pid": proc.info['pid'],
                        "cmdline": cmdline,
                        "create_time": proc.create_time() if hasattr(proc, 'create_time') else None
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return all_ffmpeg_processes
    
    @staticmethod
    def stop_processes(process_infos: List[Dict[str, Any]]) -> tuple[List[Dict], List[Dict]]:
        """Stop a list of processes"""
        stopped_processes = []
        failed_processes = []
        
        for proc_info in process_infos:
            try:
                pid = proc_info["pid"]
                proc = psutil.Process(pid)
                proc.terminate()
                
                try:
                    proc.wait(timeout=5)
                    stopped_processes.append(proc_info)
                except psutil.TimeoutExpired:
                    proc.kill()
                    stopped_processes.append(proc_info)
                    
            except psutil.NoSuchProcess:
                stopped_processes.append(proc_info)
            except Exception as e:
                logger.error(f"Failed to stop process {proc_info['pid']}: {e}")
                failed_processes.append({**proc_info, "error": str(e)})
        
        return stopped_processes, failed_processes