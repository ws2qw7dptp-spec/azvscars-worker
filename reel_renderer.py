import cv2
import os
import ffmpeg
import imageio_ffmpeg

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
        for path in slide_paths:
            frame = cv2.imread(path)
            if frame is None:
                print(f"Warning: Could not read {path}, skipping.")
                continue
            
            # Ensure it matches dimensions
            if frame.shape[:2] != (height, width):
                frame = cv2.resize(frame, (width, height))
            
            # Write the frame multiple times for duration
            for _ in range(frames_per_slide):
                video.write(frame)
    finally:
        video.release()
        
    # Mux audio and video
    audio_file = os.path.join("assets", "phonk.mp3")
    if os.path.exists(audio_file):
        try:
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
