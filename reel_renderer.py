import hashlib
import math
import os
import subprocess

import cv2
import imageio_ffmpeg


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


def _ease(value):
    return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, value)))


def _animate(frame, progress, direction):
    height, width = frame.shape[:2]
    eased = _ease(progress)
    zoom = 1.0 + 0.014 * eased
    crop_w = max(2, int(width / zoom))
    crop_h = max(2, int(height / zoom))
    travel_x = width - crop_w
    travel_y = height - crop_h
    x_ratio = eased if direction > 0 else 1.0 - eased
    x = int(travel_x * x_ratio)
    y = int(travel_y * (0.35 + 0.3 * eased))
    crop = frame[y:y + crop_h, x:x + crop_w]
    return cv2.resize(crop, (width, height), interpolation=cv2.INTER_LANCZOS4)


def _encode_frames(frames, output_path, fps, width, height):
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    command = [
        ffmpeg_exe,
        "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-pix_fmt", "bgr24",
        "-s", f"{width}x{height}",
        "-r", str(fps),
        "-i", "-",
        "-an",
        "-c:v", "libx264",
        "-preset", os.environ.get("REEL_ENCODE_PRESET", "medium"),
        "-crf", os.environ.get("REEL_CRF", "17"),
        "-profile:v", "high",
        "-level", "4.1",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path,
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        for frame in frames:
            process.stdin.write(frame.tobytes())
        process.stdin.close()
        stderr = process.stderr.read()
        return_code = process.wait()
    except Exception:
        process.kill()
        raise
    if return_code != 0:
        raise RuntimeError(f"FFmpeg video encode failed: {stderr.decode('utf-8', errors='replace')[-2000:]}")


def _mux_audio(video_path, audio_path, output_path, duration):
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    fade_start = max(0.0, duration - 0.65)
    command = [
        ffmpeg_exe,
        "-y",
        "-i", video_path,
        "-stream_loop", "-1",
        "-i", audio_path,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-af", f"afade=t=out:st={fade_start:.2f}:d=0.65",
        "-t", f"{duration:.3f}",
        "-movflags", "+faststart",
        output_path,
    ]
    completed = subprocess.run(command, capture_output=True)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.decode("utf-8", errors="replace")[-2000:])


def _mux_audio_segments(video_path, audio_paths, output_path, segment_duration):
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    command = [ffmpeg_exe, "-y", "-i", video_path]
    for audio_path in audio_paths:
        command.extend(["-i", audio_path])

    chains = []
    labels = []
    fade_out = max(0.35, segment_duration - 0.28)
    for index in range(len(audio_paths)):
        label = f"a{index}"
        labels.append(f"[{label}]")
        chains.append(
            f"[{index + 1}:a]"
            "silenceremove=start_periods=1:start_duration=0.02:start_threshold=-46dB,"
            f"atrim=duration={segment_duration:.3f},asetpts=PTS-STARTPTS,"
            "highpass=f=35,lowpass=f=15500,acompressor=threshold=-16dB:ratio=3:attack=8:release=90,"
            f"afade=t=in:st=0:d=0.10,afade=t=out:st={fade_out:.3f}:d=0.28,"
            f"apad=pad_dur={segment_duration:.3f},atrim=duration={segment_duration:.3f}[{label}]"
        )
    chains.append(f"{''.join(labels)}concat=n={len(labels)}:v=0:a=1[outa]")
    total_duration = segment_duration * len(audio_paths)
    command.extend([
        "-filter_complex", ";".join(chains),
        "-map", "0:v:0",
        "-map", "[outa]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-t", f"{total_duration:.3f}",
        "-movflags", "+faststart",
        output_path,
    ])
    completed = subprocess.run(command, capture_output=True)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.decode("utf-8", errors="replace")[-2000:])


def render_reel(slide_paths: list, output_path: str, fps=30, slide_duration_sec=1.5, audio_files=None):
    """Render a polished vertical H.264 reel with eased motion and soft transitions."""
    if not slide_paths:
        raise ValueError("No slide paths provided.")

    slides = []
    for path in slide_paths:
        frame = cv2.imread(path)
        if frame is None:
            raise ValueError(f"Could not read image: {path}")
        slides.append(frame)
    height, width = slides[0].shape[:2]
    slides = [
        frame if frame.shape[:2] == (height, width)
        else cv2.resize(frame, (width, height), interpolation=cv2.INTER_LANCZOS4)
        for frame in slides
    ]

    frames_per_slide = max(1, int(round(fps * slide_duration_sec)))
    transition_frames = min(max(4, int(round(fps * 0.24))), frames_per_slide // 3)
    total_frames = frames_per_slide * len(slides)
    total_duration = total_frames / fps

    def frame_stream():
        for slide_index, frame in enumerate(slides):
            direction = 1 if slide_index % 2 == 0 else -1
            for frame_index in range(frames_per_slide):
                progress = frame_index / max(1, frames_per_slide - 1)
                current = _animate(frame, progress, direction)
                if slide_index < len(slides) - 1 and frame_index >= frames_per_slide - transition_frames:
                    blend_index = frame_index - (frames_per_slide - transition_frames)
                    alpha = _ease((blend_index + 1) / transition_frames)
                    upcoming = _animate(slides[slide_index + 1], blend_index / transition_frames, -direction)
                    current = cv2.addWeighted(current, 1.0 - alpha, upcoming, alpha, 0)
                yield current

    temp_video = output_path + ".silent.mp4"
    _encode_frames(frame_stream(), temp_video, fps, width, height)
    valid_audio = [path for path in (audio_files or []) if path and os.path.exists(path)]
    audio_file = select_audio_file(output_path)
    try:
        if len(valid_audio) == len(slides):
            print(f"[reel] Using {len(valid_audio)} per-card startup sounds")
            _mux_audio_segments(temp_video, valid_audio, output_path, slide_duration_sec)
        elif audio_file:
            print(f"[reel] Using audio: {audio_file}")
            _mux_audio(temp_video, audio_file, output_path, total_duration)
        else:
            os.replace(temp_video, output_path)
    finally:
        if os.path.exists(temp_video):
            os.remove(temp_video)
    return output_path
