# Fix for FFmpeg SEI issues
# backend/endpoints/blueprints/stream_management/utils/ffmpeg_compatibility.py

import subprocess
import logging
import re
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

def check_ffmpeg_capabilities():
    """Check what SEI capabilities are available in the current FFmpeg build"""
    
    capabilities = {
        "h264_metadata": False,
        "sei_unregistered": False,
        "trace_headers": False,
        "version": None,
        "build_config": None
    }
    
    try:
        # Check FFmpeg version and build info
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            capabilities["version"] = result.stdout.split('\n')[0]
            capabilities["build_config"] = result.stdout
        
        # Check available bitstream filters
        result = subprocess.run(["ffmpeg", "-bsfs"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            if "h264_metadata" in result.stdout:
                capabilities["h264_metadata"] = True
            if "trace_headers" in result.stdout:
                capabilities["trace_headers"] = True
        
        # Check if we can use sei_unregistered (alternative approach)
        test_cmd = ["ffmpeg", "-f", "lavfi", "-i", "testsrc=duration=0.1:size=160x120", 
                   "-c:v", "libx264", "-x264-params", "sei=0", "-f", "null", "-"]
        result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            capabilities["sei_unregistered"] = True
            
    except Exception as e:
        logger.error(f"Error checking FFmpeg capabilities: {e}")
    
    return capabilities

def fix_sei_uuid_extraction(sei_raw: str) -> str:
    """Properly extract UUID from SEI, removing any static timestamp parts"""
    if not sei_raw:
        return "681d5c8f-80cd-4847-930a-99b9484b4a32"
    
    # Remove any existing timestamp parts
    if '+' in sei_raw:
        uuid_part = sei_raw.split('+')[0]
        logger.info(f"Extracted clean UUID: {uuid_part}")
        return uuid_part
    
    return sei_raw

def build_compatible_sei_command(uuid: str, current_unix_time: int, buffer_offset: int) -> Dict[str, Any]:
    """Build SEI command using available FFmpeg capabilities"""
    
    capabilities = check_ffmpeg_capabilities()
    logger.info(f"FFmpeg capabilities: {capabilities}")
    
    # Strategy 1: Use h264_metadata filter (preferred)
    if capabilities["h264_metadata"]:
        timestamp_expr = f"({current_unix_time}+{buffer_offset}+pts_time)*1000"
        # Fix the sprintf expression - remove extra escaping
        sei_expr = f"sprintf('%016x',{timestamp_expr})"
        sei_metadata = f"{uuid}+{sei_expr}"
        
        return {
            "method": "h264_metadata",
            "params": ["-bsf:v", f"h264_metadata=sei_user_data={sei_metadata}"],
            "sei_metadata": sei_metadata
        }
    
    # Strategy 2: Use x264 SEI parameters (fallback)
    else:
        logger.warning("h264_metadata filter not available, using x264 SEI parameters")
        
        # Calculate static timestamp for current moment
        static_timestamp = (current_unix_time + buffer_offset) * 1000
        static_hex = f"{static_timestamp:016x}"
        sei_static = f"{uuid}+{static_hex}"
        
        return {
            "method": "x264_params", 
            "params": ["-x264-params", f"sei={sei_static}"],
            "sei_metadata": sei_static,
            "warning": "Using static timestamp - synchronization may be limited"
        }

def get_ffmpeg_sei_solution() -> Dict[str, Any]:
    """Get the best available SEI solution for current FFmpeg"""
    
    # Check what's available
    caps = check_ffmpeg_capabilities()
    
    if caps["h264_metadata"]:
        return {
            "solution": "h264_metadata_filter",
            "dynamic_timestamps": True,
            "instructions": "Use -bsf:v h264_metadata=sei_user_data=... with sprintf expressions"
        }
    elif caps["sei_unregistered"]:
        return {
            "solution": "x264_sei_params", 
            "dynamic_timestamps": False,
            "instructions": "Use -x264-params sei=... with static timestamps"
        }
    else:
        return {
            "solution": "ffmpeg_upgrade_needed",
            "dynamic_timestamps": False,
            "instructions": "Install FFmpeg with H.264 metadata support"
        }

# Updated FFmpeg service with compatibility fixes
# backend/endpoints/blueprints/stream_management/services/ffmpeg_service.py (compatibility update)

def build_sei_parameters_compatible(config, current_unix_time: int, buffer_offset: int) -> List[str]:
    """Build SEI parameters - WORKING STATIC VERSION"""
    
    # Extract clean UUID (handle the +000000 issue)
    clean_uuid = config.sei.split('+')[0] if '+' in config.sei else config.sei
    logger.info(f"Final clean UUID: {clean_uuid}")
    
    # Use static timestamp (we know this works from terminal test)
    static_timestamp_ms = (current_unix_time + buffer_offset) * 1000
    static_hex = f"{static_timestamp_ms:016x}"
    sei_metadata = f"{clean_uuid}+{static_hex}"
    
    logger.info("="*50)
    logger.info(" SEI STATIC SOLUTION")
    logger.info("="*50)
    logger.info(f" Clean UUID: {clean_uuid}")
    logger.info(f" Timestamp: {static_timestamp_ms} -> {static_hex}")
    logger.info(f" SEI metadata: {sei_metadata}")
    logger.info("="*50)
    
    return ["-bsf:v", f"h264_metadata=sei_user_data={sei_metadata}"]

# Installation fix commands
FFMPEG_INSTALL_COMMANDS = {
    "ubuntu_official": [
        "sudo apt update",
        "sudo apt install ffmpeg"
    ],
    "ubuntu_ppa": [
        "sudo add-apt-repository ppa:savoury1/ffmpeg4",
        "sudo apt update", 
        "sudo apt install ffmpeg"
    ],
    "ubuntu_snap": [
        "sudo snap install ffmpeg"
    ],
    "compile_from_source": [
        "git clone https://git.ffmpeg.org/ffmpeg.git",
        "cd ffmpeg",
        "./configure --enable-libx264 --enable-gpl",
        "make -j$(nproc)",
        "sudo make install"
    ]
}

def suggest_ffmpeg_fix():
    """Suggest how to fix FFmpeg installation"""
    
    caps = check_ffmpeg_capabilities()
    
    logger.error("="*60)
    logger.error(" FFMPEG COMPATIBILITY ISSUE")
    logger.error("="*60)
    
    if caps["version"]:
        logger.error(f" Current FFmpeg: {caps['version']}")
    else:
        logger.error(" FFmpeg not found or not working")
    
    logger.error(" Required: FFmpeg with h264_metadata bitstream filter")
    logger.error("")
    logger.error(" Solutions:")
    logger.error(" 1. Install full FFmpeg build:")
    for cmd in FFMPEG_INSTALL_COMMANDS["ubuntu_official"]:
        logger.error(f"    {cmd}")
    
    logger.error("")
    logger.error(" 2. Or try PPA version:")
    for cmd in FFMPEG_INSTALL_COMMANDS["ubuntu_ppa"]:
        logger.error(f"    {cmd}")
    
    logger.error("")
    logger.error(" 3. Check current filters:")
    logger.error("    ffmpeg -bsfs | grep h264")
    logger.error("="*60)

# Quick test function
def test_sei_capability():
    """Quick test to verify SEI capability"""
    
    uuid = "681d5c8f-80cd-4847-930a-99b9484b4a32"
    
    # Test 1: h264_metadata filter
    test_cmd1 = [
        "ffmpeg", "-f", "lavfi", "-i", "testsrc=duration=0.5:size=160x120:rate=1",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-bsf:v", f"h264_metadata=sei_user_data={uuid}+1234567890abcdef",
        "-f", "null", "-"
    ]
    
    logger.info("Testing h264_metadata filter...")
    try:
        result = subprocess.run(test_cmd1, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            logger.info("✅ h264_metadata filter works!")
            return True
        else:
            logger.warning(f"❌ h264_metadata failed: {result.stderr[:200]}")
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
    
    # Test 2: x264 SEI parameters  
    test_cmd2 = [
        "ffmpeg", "-f", "lavfi", "-i", "testsrc=duration=0.5:size=160x120:rate=1", 
        "-c:v", "libx264", "-preset", "ultrafast",
        "-x264-params", f"sei={uuid}+1234567890abcdef",
        "-f", "null", "-"
    ]
    
    logger.info("Testing x264 SEI parameters...")
    try:
        result = subprocess.run(test_cmd2, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            logger.info("✅ x264 SEI parameters work!")
            return True
        else:
            logger.warning(f"❌ x264 SEI failed: {result.stderr[:200]}")
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
    
    logger.error("❌ No SEI methods work - FFmpeg upgrade needed")
    suggest_ffmpeg_fix()
    return False