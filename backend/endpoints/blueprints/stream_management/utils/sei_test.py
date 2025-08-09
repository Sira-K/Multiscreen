# backend/endpoints/blueprints/stream_management/utils/sei_test.py
"""
SEI Test Utility - Standalone script to test SEI metadata generation
"""

import time
import subprocess
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_sei_generation():
    """Test SEI metadata generation with a simple FFmpeg command"""
    
    # Configuration
    uuid = "681d5c8f-80cd-4847-930a-99b9484b4a32"
    current_unix_time = int(time.time())
    buffer_offset = 2
    
    # Calculate expected SEI values
    logger.info("="*60)
    logger.info(" SEI METADATA TEST")
    logger.info("="*60)
    logger.info(f" UUID: {uuid}")
    logger.info(f" Current Unix time: {current_unix_time}")
    logger.info(f" Buffer offset: {buffer_offset}s")
    
    # Show expected SEI values for first few frames
    logger.info(" Expected SEI values (30 FPS):")
    for frame in range(5):
        frame_time = current_unix_time + buffer_offset + (frame / 30.0)
        timestamp_ms = int(frame_time * 1000)
        hex_timestamp = f"{timestamp_ms:016x}"
        sei_value = f"{uuid}+{hex_timestamp}"
        logger.info(f"   Frame {frame}: {sei_value}")
    
    # Create FFmpeg test command
    timestamp_expr = f"({current_unix_time}+{buffer_offset}+pts_time)*1000"
    sei_timestamp_expr = f"sprintf('%016llx',{timestamp_expr})"
    sei_metadata = f"{uuid}+{sei_timestamp_expr}"
    
    logger.info(f" FFmpeg SEI expression: {sei_metadata}")
    
    # Test command (generates 5 seconds of test video with SEI)
    test_cmd = [
        "ffmpeg",
        "-f", "lavfi",
        "-i", "testsrc=duration=5:size=320x240:rate=30",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-tune", "zerolatency",
        "-g", "1",  # I-frames only
        "-bsf:v", f"h264_metadata=sei_user_data={sei_metadata}",
        "-f", "null",
        "-"
    ]
    
    logger.info(" Running FFmpeg test command...")
    logger.info(f" Command: {' '.join(test_cmd)}")
    
    try:
        result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            logger.info(" ✅ FFmpeg test successful!")
            logger.info(" SEI metadata generation is working")
        else:
            logger.error(f" ❌ FFmpeg test failed with return code: {result.returncode}")
            logger.error(f" stderr: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        logger.error(" ❌ FFmpeg test timed out")
    except FileNotFoundError:
        logger.error(" ❌ FFmpeg not found in PATH")
    except Exception as e:
        logger.error(f" ❌ Test failed: {e}")

def verify_sei_command_syntax():
    """Verify that the SEI command syntax is correct"""
    
    uuid = "681d5c8f-80cd-4847-930a-99b9484b4a32"
    current_time = int(time.time())
    
    logger.info("="*60)
    logger.info(" SEI COMMAND SYNTAX VERIFICATION")
    logger.info("="*60)
    
    # Test different expression formats
    expressions = [
        # Simple static test
        f"{uuid}+{current_time * 1000:016x}",
        
        # Dynamic with pts_time
        f"{uuid}+sprintf('%016llx',({current_time}+2+pts_time)*1000)",
        
        # Alternative format
        f"{uuid}+sprintf('%016x',({current_time}+2)*1000+pts_time*1000)",
    ]
    
    for i, expr in enumerate(expressions):
        logger.info(f" Expression {i+1}: {expr}")
        
        # Test with simple FFmpeg command
        test_cmd = [
            "ffmpeg",
            "-f", "lavfi",
            "-i", "testsrc=duration=1:size=160x120:rate=1",
            "-frames:v", "1",
            "-c:v", "libx264",
            "-bsf:v", f"h264_metadata=sei_user_data={expr}",
            "-f", "null",
            "-"
        ]
        
        try:
            result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                logger.info(f"   ✅ Expression {i+1} syntax is valid")
            else:
                logger.error(f"   ❌ Expression {i+1} failed: {result.stderr[:100]}")
        except Exception as e:
            logger.error(f"   ❌ Expression {i+1} test error: {e}")

def extract_sei_from_stream(stream_url: str, duration: int = 10):
    """Extract SEI metadata from an SRT stream for verification"""
    
    logger.info("="*60)
    logger.info(f" EXTRACTING SEI FROM STREAM: {stream_url}")
    logger.info("="*60)
    
    # FFmpeg command to read stream and extract SEI
    extract_cmd = [
        "ffmpeg",
        "-i", stream_url,
        "-t", str(duration),
        "-c:v", "copy",
        "-bsf:v", "trace_headers",
        "-f", "null",
        "-"
    ]
    
    logger.info(f" Running extraction command for {duration} seconds...")
    
    try:
        process = subprocess.Popen(
            extract_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        sei_count = 0
        for line in process.stderr:
            if 'sei' in line.lower() or 'user_data' in line.lower():
                logger.info(f" SEI detected: {line.strip()}")
                sei_count += 1
                
                if sei_count >= 10:  # Limit output
                    logger.info(" ... (truncated after 10 SEI samples)")
                    break
        
        process.terminate()
        
        if sei_count > 0:
            logger.info(f" ✅ Found {sei_count} SEI samples in stream")
        else:
            logger.warning(" ⚠️  No SEI metadata detected in stream")
            
    except Exception as e:
        logger.error(f" ❌ Extraction failed: {e}")

if __name__ == "__main__":
    print("SEI Metadata Test Utility")
    print("Choose test:")
    print("1. Test SEI generation")
    print("2. Verify command syntax")
    print("3. Extract SEI from stream (provide SRT URL)")
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice == "1":
        test_sei_generation()
    elif choice == "2":
        verify_sei_command_syntax()
    elif choice == "3":
        url = input("Enter SRT stream URL: ").strip()
        if url:
            extract_sei_from_stream(url)
        else:
            print("No URL provided")
    else:
        print("Invalid choice")

# Backend integration functions
def debug_stream_sei(group_name: str, stream_id: str, srt_ip: str, srt_port: int):
    """Debug SEI metadata for a specific stream"""
    stream_url = f"srt://{srt_ip}:{srt_port}?streamid=#!::r=live/{group_name}/{stream_id},m=request"
    logger.info(f"Debugging SEI for stream: {stream_url}")
    extract_sei_from_stream(stream_url, duration=5)

def log_current_sei_values(uuid: str, frame_count: int = 10):
    """Log what SEI values should look like right now"""
    current_time = time.time()
    buffer_offset = 2.0
    
    logger.info(" CURRENT EXPECTED SEI VALUES:")
    logger.info(f" Base time: {current_time:.3f}")
    logger.info(f" Buffer offset: {buffer_offset}s")
    
    for frame in range(frame_count):
        frame_time = current_time + buffer_offset + (frame / 30.0)
        timestamp_ms = int(frame_time * 1000)
        hex_timestamp = f"{timestamp_ms:016x}"
        sei_value = f"{uuid}+{hex_timestamp}"
        logger.info(f" Frame {frame:2d}: {sei_value}")