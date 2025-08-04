import subprocess
import os

def generate_large_test_video(size_mb, output_filename):
    """Generate a test video with duration scaled to target size"""
    # Scale duration much more aggressively - larger files need much longer videos
    duration = max(300, size_mb * 2)  # At least 5 minutes, 2 seconds per MB target
    
    print(f"Generating {output_filename} with {duration} second duration...")
    
    cmd = [
        'ffmpeg', '-f', 'lavfi',
        '-i', f'testsrc=duration={duration}:size=1920x1080:rate=30',
        '-c:v', 'libx264',
        '-crf', '0',  # Lossless compression
        '-preset', 'ultrafast',
        '-fs', f'{size_mb}M',  # Stop at target size
        '-y',
        output_filename
    ]
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        actual_size = os.path.getsize(output_filename) / (1024 * 1024)
        print(f"Generated {output_filename}: {actual_size:.2f} MB (target: {size_mb} MB)")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error generating {output_filename}: {e}")
        return False

# Generate test videos
sizes = [100, 250, 500, 1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900, 2000]

for size in sizes:
    filename = f"test_video_{size}MB.mp4"
    generate_large_test_video(size, filename)