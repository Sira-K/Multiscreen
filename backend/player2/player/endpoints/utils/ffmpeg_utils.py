import logging
from typing import Tuple, List, Dict, Any

logger = logging.getLogger(__name__)

def build_ffmpeg_filter_chain(
    video_width: int, 
    video_height: int, 
    screen_count: int, 
    orientation: str, 
    srt_ip: str, 
    sei: str,
    grid_rows: int = 2,
    grid_cols: int = 2
) -> Tuple[str, List[str]]:
    """
    Build FFmpeg filter complex and output mappings for SRT streaming
    Now supports grid layouts in addition to horizontal and vertical
    
    Args:
        video_width: Width of the video in pixels
        video_height: Height of the video in pixels
        screen_count: Number of screens to split into
        orientation: 'horizontal', 'vertical', or 'grid'
        srt_ip: SRT server IP address
        sei: SEI user data for H.264 metadata
        grid_rows: Number of rows for grid layout (default: 2)
        grid_cols: Number of columns for grid layout (default: 2)
        
    Returns:
        Tuple of (filter_complex_str, output_mappings)
    """
    filter_complex = []
    output_mappings = []
    
    # Input validation
    if screen_count < 1:
        screen_count = 1
    
    # For grid layout, ensure screen_count matches grid dimensions
    if orientation.lower() == "grid":
        screen_count = grid_rows * grid_cols
    
    # Start with splitting the input
    split_str = f"[0:v]split={screen_count+1}[full]"
    for i in range(screen_count):
        split_str += f"[part{i}]"
    filter_complex.append(split_str + ";")
    
    # Build crops based on orientation
    if orientation.lower() == "horizontal":
        # Horizontal layout (left to right)
        section_width = video_width // screen_count
        remainder = video_width % screen_count
        
        for i in range(screen_count):
            current_width = section_width + (remainder if i == screen_count-1 else 0)
            start_x = i * section_width
            
            filter_complex.append(
                f"[part{i}]crop={current_width}:{video_height}:{start_x}:0[out{i}];"
            )
            
            output_mappings.extend([
                "-map", f"[out{i}]",
                "-an", "-c:v", "libx264",
                "-bsf:v", f"h264_metadata=sei_user_data={sei}",
                "-pes_payload_size", "0",
                "-bf", "0",
                "-g", "1",
                "-f", "mpegts", f"srt://{srt_ip}:10080?streamid=#!::r=live/test{i},m=publish"
            ])
            
    elif orientation.lower() == "vertical":
        # Vertical layout (top to bottom)
        section_height = video_height // screen_count
        remainder = video_height % screen_count
        
        for i in range(screen_count):
            current_height = section_height + (remainder if i == screen_count-1 else 0)
            start_y = i * section_height
            
            filter_complex.append(
                f"[part{i}]crop={video_width}:{current_height}:0:{start_y}[out{i}];"
            )
            
            output_mappings.extend([
                "-map", f"[out{i}]",
                "-an", "-c:v", "libx264",
                "-bsf:v", f"h264_metadata=sei_user_data={sei}",
                "-pes_payload_size", "0",
                "-bf", "0",
                "-g", "1",
                "-f", "mpegts", f"srt://{srt_ip}:10080?streamid=#!::r=live/test{i},m=publish"
            ])
            
    elif orientation.lower() == "grid":
        # Grid layout (rows × columns)
        section_width = video_width // grid_cols
        section_height = video_height // grid_rows
        width_remainder = video_width % grid_cols
        height_remainder = video_height % grid_rows
        
        for i in range(screen_count):
            # Calculate grid position
            row = i // grid_cols
            col = i % grid_cols
            
            # Calculate section dimensions (distribute remainder pixels)
            current_width = section_width + (width_remainder if col == grid_cols-1 else 0)
            current_height = section_height + (height_remainder if row == grid_rows-1 else 0)
            
            # Calculate starting position
            start_x = col * section_width
            start_y = row * section_height
            
            filter_complex.append(
                f"[part{i}]crop={current_width}:{current_height}:{start_x}:{start_y}[out{i}];"
            )
            
            output_mappings.extend([
                "-map", f"[out{i}]",
                "-an", "-c:v", "libx264",
                "-bsf:v", f"h264_metadata=sei_user_data={sei}",
                "-pes_payload_size", "0",
                "-bf", "0",
                "-g", "1",
                "-f", "mpegts", f"srt://{srt_ip}:10080?streamid=#!::r=live/test{i},m=publish"
            ])
    
    # Always add the full video output
    output_mappings.extend([
        "-map", "[full]",
        "-an", "-c:v", "libx264",
        "-bsf:v", f"h264_metadata=sei_user_data={sei}",
        "-pes_payload_size", "0",
        "-bf", "0",
        "-g", "1",
        "-f", "mpegts", f"srt://{srt_ip}:10080?streamid=#!::r=live/test,m=publish"
    ])
    
    # Remove the last semicolon from the filter complex
    if filter_complex[-1].endswith(';'):
        filter_complex[-1] = filter_complex[-1][:-1]
    
    # Combine all filter parts
    filter_complex_str = ''.join(filter_complex)
    
    return filter_complex_str, output_mappings

def build_group_ffmpeg_filter_chain(
    video_width: int,
    video_height: int,
    screen_count: int,
    orientation: str,
    srt_ip: str,
    srt_port: int,
    sei: str,
    group_id: str,
    grid_rows: int = 2,
    grid_cols: int = 2
) -> Tuple[str, List[str]]:
    """
    Build FFmpeg filter complex and output mappings for group-specific SRT streaming
    
    Args:
        video_width: Width of the video in pixels
        video_height: Height of the video in pixels
        screen_count: Number of screens to split into
        orientation: 'horizontal', 'vertical', or 'grid'
        srt_ip: SRT server IP address
        srt_port: SRT server port
        sei: SEI user data for H.264 metadata
        group_id: Group ID for stream naming
        grid_rows: Number of rows for grid layout (default: 2)
        grid_cols: Number of columns for grid layout (default: 2)
        
    Returns:
        Tuple of (filter_complex_str, output_mappings)
    """
    filter_complex = []
    output_mappings = []
    
    # Input validation
    if screen_count < 1:
        screen_count = 1
    
    # For grid layout, ensure screen_count matches grid dimensions
    if orientation.lower() == "grid":
        screen_count = grid_rows * grid_cols
    
    # Start with splitting the input
    split_str = f"[0:v]split={screen_count+1}[full]"
    for i in range(screen_count):
        split_str += f"[part{i}]"
    filter_complex.append(split_str + ";")
    
    # Build crops based on orientation
    if orientation.lower() == "horizontal":
        # Horizontal layout (left to right)
        section_width = video_width // screen_count
        remainder = video_width % screen_count
        
        for i in range(screen_count):
            current_width = section_width + (remainder if i == screen_count-1 else 0)
            start_x = i * section_width
            
            filter_complex.append(
                f"[part{i}]crop={current_width}:{video_height}:{start_x}:0[out{i}];"
            )
            
            output_mappings.extend([
                "-map", f"[out{i}]",
                "-an", "-c:v", "libx264",
                "-bsf:v", f"h264_metadata=sei_user_data={sei}",
                "-pes_payload_size", "0",
                "-bf", "0",
                "-g", "1",
                "-f", "mpegts", f"srt://{srt_ip}:{srt_port}?streamid=#!::r=live/{group_id}/test{i},m=publish"
            ])
            
    elif orientation.lower() == "vertical":
        # Vertical layout (top to bottom)
        section_height = video_height // screen_count
        remainder = video_height % screen_count
        
        for i in range(screen_count):
            current_height = section_height + (remainder if i == screen_count-1 else 0)
            start_y = i * section_height
            
            filter_complex.append(
                f"[part{i}]crop={video_width}:{current_height}:0:{start_y}[out{i}];"
            )
            
            output_mappings.extend([
                "-map", f"[out{i}]",
                "-an", "-c:v", "libx264",
                "-bsf:v", f"h264_metadata=sei_user_data={sei}",
                "-pes_payload_size", "0",
                "-bf", "0",
                "-g", "1",
                "-f", "mpegts", f"srt://{srt_ip}:{srt_port}?streamid=#!::r=live/{group_id}/test{i},m=publish"
            ])
            
    elif orientation.lower() == "grid":
        # Grid layout (rows × columns)
        section_width = video_width // grid_cols
        section_height = video_height // grid_rows
        width_remainder = video_width % grid_cols
        height_remainder = video_height % grid_rows
        
        for i in range(screen_count):
            # Calculate grid position
            row = i // grid_cols
            col = i % grid_cols
            
            # Calculate section dimensions (distribute remainder pixels)
            current_width = section_width + (width_remainder if col == grid_cols-1 else 0)
            current_height = section_height + (height_remainder if row == grid_rows-1 else 0)
            
            # Calculate starting position
            start_x = col * section_width
            start_y = row * section_height
            
            filter_complex.append(
                f"[part{i}]crop={current_width}:{current_height}:{start_x}:{start_y}[out{i}];"
            )
            
            output_mappings.extend([
                "-map", f"[out{i}]",
                "-an", "-c:v", "libx264",
                "-bsf:v", f"h264_metadata=sei_user_data={sei}",
                "-pes_payload_size", "0",
                "-bf", "0",
                "-g", "1",
                "-f", "mpegts", f"srt://{srt_ip}:{srt_port}?streamid=#!::r=live/{group_id}/test{i},m=publish"
            ])
    
    # Always add the full video output
    output_mappings.extend([
        "-map", "[full]",
        "-an", "-c:v", "libx264",
        "-bsf:v", f"h264_metadata=sei_user_data={sei}",
        "-pes_payload_size", "0",
        "-bf", "0",
        "-g", "1",
        "-f", "mpegts", f"srt://{srt_ip}:{srt_port}?streamid=#!::r=live/{group_id}/test,m=publish"
    ])
    
    # Remove the last semicolon from the filter complex
    if filter_complex[-1].endswith(';'):
        filter_complex[-1] = filter_complex[-1][:-1]
    
    # Combine all filter parts
    filter_complex_str = ''.join(filter_complex)
    
    return filter_complex_str, output_mappings

def calculate_section_info(
    video_width: int, 
    video_height: int, 
    screen_count: int, 
    orientation: str,
    grid_rows: int = 2,
    grid_cols: int = 2
) -> List[Dict[str, Any]]:
    """
    Calculate section details for client visualization
    Now supports grid layouts in addition to horizontal and vertical
    
    Args:
        video_width: Width of the video in pixels
        video_height: Height of the video in pixels
        screen_count: Number of screens to split into
        orientation: 'horizontal', 'vertical', or 'grid'
        grid_rows: Number of rows for grid layout (default: 2)
        grid_cols: Number of columns for grid layout (default: 2)
        
    Returns:
        List of section info dictionaries
    """
    section_info = []
    
    # Input validation
    if screen_count < 1:
        screen_count = 1
    
    # For grid layout, ensure screen_count matches grid dimensions
    if orientation.lower() == "grid":
        screen_count = grid_rows * grid_cols
    
    if orientation.lower() == "horizontal":
        # Horizontal layout (left to right)
        section_width = video_width // screen_count
        remainder = video_width % screen_count
        
        for i in range(screen_count):
            current_width = section_width + (remainder if i == screen_count-1 else 0)
            start_x = i * section_width
            section_info.append({
                "section": i+1,
                "x": start_x,
                "y": 0,
                "width": current_width,
                "height": video_height,
                "stream_id": f"live/test{i}",
                "position": f"Column {i+1}",
                "layout_type": "horizontal"
            })
            
    elif orientation.lower() == "vertical":
        # Vertical layout (top to bottom)
        section_height = video_height // screen_count
        remainder = video_height % screen_count
        
        for i in range(screen_count):
            current_height = section_height + (remainder if i == screen_count-1 else 0)
            start_y = i * section_height
            section_info.append({
                "section": i+1,
                "x": 0,
                "y": start_y,
                "width": video_width,
                "height": current_height,
                "stream_id": f"live/test{i}",
                "position": f"Row {i+1}",
                "layout_type": "vertical"
            })
            
    elif orientation.lower() == "grid":
        # Grid layout (rows × columns)
        section_width = video_width // grid_cols
        section_height = video_height // grid_rows
        width_remainder = video_width % grid_cols
        height_remainder = video_height % grid_rows
        
        for i in range(screen_count):
            # Calculate grid position
            row = i // grid_cols
            col = i % grid_cols
            
            # Calculate section dimensions (distribute remainder pixels)
            current_width = section_width + (width_remainder if col == grid_cols-1 else 0)
            current_height = section_height + (height_remainder if row == grid_rows-1 else 0)
            
            # Calculate starting position
            start_x = col * section_width
            start_y = row * section_height
            
            section_info.append({
                "section": i+1,
                "x": start_x,
                "y": start_y,
                "width": current_width,
                "height": current_height,
                "stream_id": f"live/test{i}",
                "position": f"Row {row+1}, Col {col+1}",
                "grid_row": row + 1,
                "grid_col": col + 1,
                "layout_type": "grid"
            })
            
    return section_info

def get_stream_display_name(stream_id: str, layout_type: str = "horizontal", grid_rows: int = 2, grid_cols: int = 2) -> str:
    """
    Get descriptive name for a stream ID based on layout type
    
    Args:
        stream_id: The stream ID (e.g., "live/test1")
        layout_type: "horizontal", "vertical", or "grid"
        grid_rows: Number of grid rows
        grid_cols: Number of grid columns
        
    Returns:
        Human-readable stream name
    """
    if not stream_id:
        return 'None'
    
    clean_id = stream_id.replace('live/', '')
    
    # Handle the full stream
    if clean_id == 'test':
        return 'Full Video'
    
    # Handle numbered streams
    if clean_id.startswith('test'):
        try:
            stream_number = int(clean_id.replace('test', ''))
        except ValueError:
            return clean_id
        
        if layout_type == "horizontal":
            return f"Column {stream_number + 1}"
        elif layout_type == "vertical":
            return f"Row {stream_number + 1}"
        elif layout_type == "grid":
            row = stream_number // grid_cols + 1
            col = stream_number % grid_cols + 1
            return f"Grid R{row}C{col}"
        else:
            return f"Section {stream_number + 1}"
    
    return clean_id