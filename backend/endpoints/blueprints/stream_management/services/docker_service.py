import subprocess
import json
import logging
from typing import Optional, List, Dict, Any
from ..models.group_info import GroupInfo

logger = logging.getLogger(__name__)

class DockerService:
    """Service for Docker container discovery and management"""
    
    @staticmethod
    def discover_group(group_id: str) -> Optional[GroupInfo]:
        """Discover group information from Docker container"""
        try:
            # Method 1: Look for containers with correct label
            cmd = [
                "docker", "ps", "-a",
                "--filter", f"label=com.multiscreen.group.id={group_id}",
                "--format", "{{.ID}}\t{{.Names}}\t{{.Status}}"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.strip():
                        parts = line.split('\t')
                        if len(parts) >= 3:
                            container_id = parts[0]
                            return DockerService._get_container_details(container_id, group_id)
            
            # Method 2: Look for containers with naming pattern
            group_id_short = group_id[:8]
            container_name_pattern = f"srs-group-{group_id_short}"
            
            cmd = [
                "docker", "ps", "-a",
                "--filter", f"name={container_name_pattern}",
                "--format", "{{.ID}}\t{{.Names}}\t{{.Status}}"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.strip():
                        parts = line.split('\t')
                        if len(parts) >= 3:
                            container_id = parts[0]
                            return DockerService._get_container_details(container_id, group_id)
            
            return None
            
        except Exception as e:
            logger.error(f"Error discovering group from Docker: {e}")
            return None
    
    @staticmethod
    def _get_container_details(container_id: str, group_id: str) -> Optional[GroupInfo]:
        """Get detailed container information for a group"""
        try:
            inspect_cmd = ["docker", "inspect", container_id]
            result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                return None
            
            container_data = json.loads(result.stdout)[0]
            return GroupInfo.from_container_data(container_data, group_id)
            
        except Exception as e:
            logger.error(f"Error getting container details: {e}")
            return None
    
    @staticmethod
    def get_all_groups() -> List[GroupInfo]:
        """Get all groups from Docker containers"""
        groups = []
        
        try:
            cmd = [
                "docker", "ps", "-a",
                "--filter", "ancestor=ossrs/srs:5",
                "--format", "{{.ID}}\t{{.Names}}\t{{.Status}}"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                
                for line in lines:
                    if line.strip():
                        parts = line.split('\t')
                        if len(parts) >= 3:
                            container_id = parts[0]
                            
                            # Extract group ID from container labels
                            inspect_cmd = ["docker", "inspect", container_id, "--format", 
                                         "{{index .Config.Labels \"com.multiscreen.group.id\"}}"]
                            inspect_result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=5)
                            
                            if inspect_result.returncode == 0:
                                group_id = inspect_result.stdout.strip()
                                if group_id and group_id != "<no value>":
                                    group = DockerService._get_container_details(container_id, group_id)
                                    if group:
                                        groups.append(group)
        
        except Exception as e:
            logger.warning(f"Error discovering groups from Docker: {e}")
        
        return groups