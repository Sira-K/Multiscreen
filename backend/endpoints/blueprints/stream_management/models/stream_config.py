from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum

class Orientation(Enum):
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    GRID = "grid"

class StreamingMode(Enum):
    MULTI_VIDEO = "multi_video"
    SPLIT_SCREEN = "split_screen"

@dataclass
class VideoFileConfig:
    """Configuration for a single video file"""
    screen: int
    file: str
    file_path: Optional[str] = None

@dataclass
class StreamConfig:
    """Complete stream configuration"""
    group_id: str
    screen_count: int
    orientation: Orientation
    output_width: int = 1920
    output_height: int = 1080
    grid_rows: int = 2
    grid_cols: int = 2
    srt_ip: str = "127.0.0.1"
    srt_port: int = 10080
    sei: str = "681d5c8f-80cd-4847-930a-99b9484b4a32+000000"
    framerate: int = 30
    bitrate: str = "3000k"
    
    # Mode-specific fields
    streaming_mode: StreamingMode = StreamingMode.MULTI_VIDEO
    video_files: Optional[List[VideoFileConfig]] = None
    single_video_file: Optional[str] = None
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if self.streaming_mode == StreamingMode.MULTI_VIDEO:
            if not self.video_files or len(self.video_files) != self.screen_count:
                raise ValueError(f"Multi-video mode requires {self.screen_count} video files")
        elif self.streaming_mode == StreamingMode.SPLIT_SCREEN:
            if not self.single_video_file:
                raise ValueError("Split-screen mode requires a single video file")
        
        # Ensure SEI has correct format
        if '+' not in self.sei:
            self.sei = f"{self.sei}+000000"
    
    @property
    def canvas_dimensions(self) -> tuple[int, int]:
        """Calculate canvas dimensions based on orientation"""
        if self.orientation == Orientation.HORIZONTAL:
            return self.output_width * self.screen_count, self.output_height
        elif self.orientation == Orientation.VERTICAL:
            return self.output_width, self.output_height * self.screen_count
        elif self.orientation == Orientation.GRID:
            cols = self.grid_cols
            rows = self.grid_rows
            if rows * cols != self.screen_count:
                cols = int(self.screen_count ** 0.5)
                rows = (self.screen_count + cols - 1) // cols
            return self.output_width * cols, self.output_height * rows
        
        raise ValueError(f"Unknown orientation: {self.orientation}")