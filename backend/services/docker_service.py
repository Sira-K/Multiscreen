import subprocess
import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class DockerGroup:
    """Represents a Docker group configuration"""
    group_id: str
    name: str
    container_id: str
    container_name: str
    docker_running: bool
    docker_status: str
    ports: Dict[str, int]
    screen_count: int
    orientation: str

class DockerService:
    """Service for Docker container operations"""
    
    @classmethod
    def discover_group(cls, group_id: str) -> Optional[DockerGroup]:
        """Discover a specific group from Docker containers"""
        logger.info(f"Discovering group '{group_id}' from Docker containers")
        
        try:
            # Get all groups
            groups = cls.discover_all_groups()
            
            # Find the specific group
            for group in groups:
                if group.group_id == group_id:
                    logger.info(f"Found group: {group.name}")
                    return group
            
            logger.warning(f"Group '{group_id}' not found in Docker containers")
            return None
            
        except Exception as e:
            logger.error(f"Error discovering group '{group_id}': {e}")
            return None
    
    @classmethod
    def discover_all_groups(cls) -> list:
        """Discover all groups from Docker containers"""
        logger.info("Discovering groups from Docker containers")
        
        try:
            # Run docker ps to get all running containers
            cmd = [
                "docker", "ps", 
                "--format", "json"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                logger.error(f"Docker command failed: {result.stderr}")
                return []
            
            groups = []
            logger.debug(f"Docker output: {result.stdout}")
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                
                try:
                    container_info = json.loads(line)
                    logger.debug(f"Parsing container: {container_info}")
                    logger.debug(f"Container info type: {type(container_info)}")
                    logger.debug(f"Container info keys: {container_info.keys() if hasattr(container_info, 'keys') else 'No keys'}")
                    
                    # Check if this container has group labels
                    labels = container_info.get("Labels", {})
                    logger.debug(f"Labels: {labels}")
                    if "com.multiscreen.group.id" not in labels:
                        logger.debug(f"Container {container_info.get('Names', 'unknown')} has no group labels, skipping")
                        continue
                    
                    group = cls._parse_container_info(container_info)
                    if group:
                        groups.append(group)
                        logger.debug(f"Successfully parsed group: {group}")
                    else:
                        logger.debug(f"Failed to parse group from container: {container_info}")
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse container info: {e}")
                    continue
                except Exception as e:
                    logger.warning(f"Unexpected error parsing container: {e}")
                    logger.warning(f"Error type: {type(e)}")
                    logger.warning(f"Error details: {e}")
                    continue
            
            logger.info(f"Discovered {len(groups)} groups from Docker containers")
            return groups
            
        except Exception as e:
            logger.error(f"Error discovering Docker groups: {e}")
            return []
    
    @classmethod
    def _parse_container_info(cls, container_info: Dict[str, Any]) -> Optional[DockerGroup]:
        """Parse Docker container information into a DockerGroup object"""
        try:
            # Extract labels and parse them from comma-separated string to dict
            labels_str = container_info.get("Labels", "")
            logger.debug(f"Container labels string: {labels_str}")
            
            # Parse labels string into dictionary
            labels = {}
            if labels_str:
                for label in labels_str.split(','):
                    if '=' in label:
                        key, value = label.split('=', 1)
                        labels[key.strip()] = value.strip()
            
            logger.debug(f"Parsed labels dict: {labels}")
            
            # Get group information from labels
            group_id = labels.get("com.multiscreen.group.id")
            logger.debug(f"Found group_id: {group_id}")
            if not group_id:
                logger.debug("No group_id found in labels")
                return None
            
            group_name = labels.get("com.multiscreen.group.name", "unknown")
            screen_count = int(labels.get("com.multiscreen.screen_count", 2))
            orientation = labels.get("com.multiscreen.orientation", "horizontal")
            
            # Parse ports from individual labels
            ports = {}
            ports["api_port"] = int(labels.get("com.multiscreen.ports.api", 8080))
            ports["http_port"] = int(labels.get("com.multiscreen.ports.http", 1985))
            ports["rtmp_port"] = int(labels.get("com.multiscreen.ports.rtmp", 1935))
            ports["srt_port"] = int(labels.get("com.multiscreen.ports.srt", 10080))
            
            # Create DockerGroup object
            group = DockerGroup(
                group_id=group_id,
                name=group_name,
                container_id=container_info.get("ID", ""),
                container_name=container_info.get("Names", ""),
                docker_running=container_info.get("State") == "running",
                docker_status=container_info.get("State", "unknown"),
                ports=ports,
                screen_count=screen_count,
                orientation=orientation
            )
            
            return group
            
        except Exception as e:
            logger.warning(f"Failed to parse container info: {e}")
            return None
