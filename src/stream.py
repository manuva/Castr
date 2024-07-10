import os
import time
import subprocess
import psutil
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Duration for which the stream should run (11 hours in seconds)
timeout = 39600

# Start time
start_time = time.time()

# Initial bitrate
bitrate = 4000

# Get environment variables
audio_file = os.getenv('AUDIO_FILE')
video_file = os.getenv('VIDEO_FILE')
log_file_path = os.getenv('LOG_FILE_PATH')
youtube_stream_url = os.getenv('YOUTUBE_STREAM_URL')

# Function to get current network bandwidth usage in kbps
def get_bandwidth():
    net_io = psutil.net_io_counters()
    bandwidth = (net_io.bytes_sent + net_io.bytes_recv) * 8 / 1024  # Convert bytes to kbps
    return bandwidth

# Function to adjust bitrate based on network bandwidth
def adjust_bitrate(current_bitrate, bandwidth, threshold=5000):
    if bandwidth < threshold:
        return max(500, current_bitrate - 500)
    else:
        return min(8000, current_bitrate + 500)

# Function to run FFmpeg command with adjusted bitrate
def run_ffmpeg(bitrate):
    ffmpeg_command = [
        'ffmpeg', '-loglevel', 'info', '-y', '-re',
        '-i', video_file,
        '-i', audio_file,
        '-c:v', 'libx264', '-preset', 'ultrafast', '-b:v', f'{bitrate}k', '-maxrate', f'{bitrate}k', '-bufsize', f'{bitrate * 5}k',
        '-framerate', '24', '-video_size', '1920x1080', '-vf', 'format=yuv420p', '-g', '50', '-shortest', '-strict', 'experimental',
        '-c:a', 'aac', '-b:a', '128k', '-ar', '44100',
        '-map', '0:v:0', '-map', '1:a:0',
        '-f', 'flv', youtube_stream_url
    ]

    # Capture stdout and stderr
    process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()

    # Log FFmpeg output to a file
    with open(log_file_path, 'a') as log_file:
        log_file.write(f"FFmpeg stdout: {stdout.decode('utf-8')}\n")
        log_file.write(f"FFmpeg stderr: {stderr.decode('utf-8')}\n")

    # Print FFmpeg output
    print("FFmpeg stdout:", stdout.decode('utf-8'))
    print("FFmpeg stderr:", stderr.decode('utf-8'))

    return process

# Main loop to run the stream
while True:
    elapsed_time = time.time() - start_time
    if elapsed_time >= timeout:
        print("11 hours have passed. Restarting the stream...")
        time.sleep(10)
        start_time = time.time()

    # Get current network bandwidth usage
    bandwidth = get_bandwidth()

    # Adjust bitrate based on network bandwidth
    new_bitrate = adjust_bitrate(bitrate, bandwidth)
    bitrate = new_bitrate
    print(f"Current bitrate: {bitrate} kbps, Bandwidth: {bandwidth:.2f} kbps")

    # Run FFmpeg with adjusted bitrate
    ffmpeg_process = run_ffmpeg(bitrate)

    # Wait for the process to finish or manually terminate
    try:
        ffmpeg_process.wait(timeout=5)  # Wait for 5 seconds for the process to finish
    except subprocess.TimeoutExpired:
        print("FFmpeg process is still running. Terminating...")
        ffmpeg_process.terminate()
        ffmpeg_process.wait()  # Wait for the process to terminate

    # Sleep before re-evaluating
    time.sleep(10)
