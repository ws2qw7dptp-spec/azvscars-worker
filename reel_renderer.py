import cv2
import os
import ffmpeg
import imageio_ffmpeg
import hashlib
import math

DEFAULT_AUDIO_FILES = [
    "mercy-line-vs-m5.mp3",
    "chrome-split.mp3",
]

def select_audio_file(output_path: str):
    override = os.environ.get("REEL_AUDIO_FILE", "").strip()
    candidates = [override] if override else DEFAULT_AUDIO_FILES

    existing = []
    for name in candidates:
        path = name if os.path.isabs(name) else os.path.join("assets", name)
        if os.path.exists(path):
            existing.append(path)

    if not existing:
        return None

    seed = os.path.basename(os.path.dirname(output_path)) or os.path.basename(output_path)
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return existing[int(digest[:8], 16) % len(existing)]

def render_reel(slide_paths: list, output_path: str, fps=30, slide_duration_sec=1.5):
    """
    Renders an MP4 video from a list of image paths using OpenCV.
    Very fast, uses hard cuts (no complex transitions) for maximum speed.
    Adds background audio if available.
    """
    if not slide_paths:
        raise ValueError("No slide paths provided.")
    
    # Read the first image to get dimensions
    first_frame = cv2.imread(slide_paths[0])
    if first_frame is None:
        raise ValueError(f"Could not read image: {slide_paths[0]}")
    
    height, width, layers = first_frame.shape
    
    # We first render video to a temporary path
    temp_vid = output_path + ".temp.mp4"
    
    # Define codec and create VideoWriter
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video = cv2.VideoWriter(temp_vid, fourcc, fps, (width, height))
    
    frames_per_slide = int(fps * slide_duration_sec)
    total_duration = len(slide_paths) * slide_duration_sec
    
    try:
        for slide_index, path in enumerate(slide_paths):
            frame = cv2.imread(path)
            if frame is None:
                print(f"Warning: Could not read {path}, skipping.")
                continue
            
            # Ensure it matches dimensions
            if frame.shape[:2] != (height, width):
                frame = cv2.resize(frame, (width, height))
            
            for i in range(frames_per_slide):
                t = i / max(1, frames_per_slide - 1)
                ease = 0.5 - 0.5 * math.cos(math.pi * t)
                zoom = 1.0 + 0.028 * ease
                crop_w = int(width / zoom)
                crop_h = int(height / zoom)
                drift = int((width - crop_w) * (0.2 + 0.6 * ((slide_index % 2) * (1 - ease) + (1 - slide_index % 2) * ease)))
                x = min(width - crop_w, max(0, drift))
                y = (height - crop_h) // 2
                animated = cv2.resize(frame[y:y + crop_h, x:x + crop_w], (width, height), interpolation=cv2.INTER_LINEAR)
                video.write(animated)
    finally:
        video.release()
        
    # Mux audio and video
    audio_file = select_audio_file(output_path)
    if audio_file:
        try:
            print(f"[reel] Using audio: {audio_file}")
            # Get the path to the internal ffmpeg executable downloaded by imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            
            vid_input = ffmpeg.input(temp_vid)
            aud_input = ffmpeg.input(audio_file)
            
            # Combine them. shortest=None maps to `-shortest` in ffmpeg, cutting audio at video length.
            out = ffmpeg.output(vid_input.video, aud_input.audio, output_path, vcodec='copy', acodec='aac', shortest=None)
            
            # Run the command
            out.run(cmd=ffmpeg_exe, overwrite_output=True, capture_stderr=True)
        except ffmpeg.Error as e:
            print(f"Failed to add audio: {e.stderr.decode('utf8')}")
            # If ffmpeg fails, fallback to just moving the video
            os.rename(temp_vid, output_path)
    else:
        # If no audio file exists, just use the temp video
        os.rename(temp_vid, output_path)
        
    # Cleanup temp video if it still exists
    if os.path.exists(temp_vid):
        os.remove(temp_vid)
    
    return output_path
