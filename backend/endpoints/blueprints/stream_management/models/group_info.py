from dataclasses import dataclass
from typing import Dict, Any, Optional
import time

@dataclass
class GroupInfo:
    """Information about a group discovered from Docker"""
    id: str
    name: str
    description: str = ""
    screen_count: int = 2
    orientation: str = "horizontal"
    streaming_mode: str = "multi_video"
    created_at: float = 0.0
    container_id: str = ""
    container_name: str = ""
    docker_status: str = "unknown"
    docker_running: bool = False
    ports: Dict[str, int] = None
    
    def __post_init__(self):
        if self.ports is None:
            self.ports = {
                'rtmp_port': 1935,
                'http_port': 1985,
                'api_port': 8080,
                'srt_port': 10080
            }
        
        if self.created_at == 0.0:
            self.created_at = time.time()
    
    @property
    def created_at_formatted(self) -> str:
        """Format creation timestamp as human-readable string"""
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.created_at))
    
    @property
    def status(self) -> str:
        """Alias for docker_status for backward compatibility"""
        return self.docker_status
    
    @classmethod
    def from_container_data(cls, container_data: Dict[str, Any], group_id: str) -> 'GroupInfo':
        """Create GroupInfo from Docker container data"""
        labels = container_data.get("Config", {}).get("Labels", {})
        state = container_data.get("State", {})
        
        group_name = labels.get('com.multiscreen.group.name', f'group_{group_id[:8]}')
        description = labels.get('com.multiscreen.group.description', '')
        screen_count = int(labels.get('com.multiscreen.group.screen_count', 2))
        orientation = labels.get('com.multiscreen.group.orientation', 'horizontal')
        streaming_mode = labels.get('com.multiscreen.group.streaming_mode', 'multi_video')
        created_timestamp = float(labels.get('com.multiscreen.group.created_at', time.time()))
        
        ports = {
            'rtmp_port': int(labels.get('com.multiscreen.ports.rtmp', 1935)),
            'http_port': int(labels.get('com.multiscreen.ports.http', 1985)),
            'api_port': int(labels.get('com.multiscreen.ports.api', 8080)),
            'srt_port': int(labels.get('com.multiscreen.ports.srt', 10080))
        }
        
        is_running = state.get("Running", False)
        docker_status = "running" if is_running else "stopped"
        
        return cls(
            id=group_id,
            name=group_name,
            description=description,
            screen_count=screen_count,
            orientation=orientation,
            streaming_mode=streaming_mode,
            created_at=created_timestamp,
            container_id=container_data.get("Id", ""),
            container_name=container_data.get("Name", "").lstrip("/"),
            docker_status=docker_status,
            docker_running=is_running,
            ports=ports
        )