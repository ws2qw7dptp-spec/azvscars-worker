import hashlib
import os
import subprocess
import tempfile

import cv2
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import reel_renderer


OUT_W = 1080
OUT_H = 1920
FPS = 30
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_DISPLAY = os.path.join(BASE_DIR, "Anton-Regular.ttf")
FONT_BOLD = os.path.join(BASE_DIR, "Montserrat-Black.ttf")
FONT_CONDENSED = os.path.join(BASE_DIR, "BarlowCondensed-Bold.ttf")
WHITE = (248, 248, 245)
RED = (244, 42, 38)
ORANGE = (255, 112, 32)


def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _cover(frame):
    height, width = frame.shape[:2]
    scale = max(OUT_W / width, OUT_H / height)
    resized = cv2.resize(frame, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_LANCZOS4)
    x = max(0, (resized.shape[1] - OUT_W) // 2)
    y = max(0, (resized.shape[0] - OUT_H) // 2)
    return resized[y:y + OUT_H, x:x + OUT_W]


def _watermark(frame):
    image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.rounded_rectangle((42, 68, 318, 148), radius=40, fill=(5, 8, 12, 176), outline=(255, 255, 255, 38), width=2)
    draw.ellipse((58, 82, 110, 134), fill=(10, 12, 16, 245), outline=RED, width=4)
    draw.text((84, 108), "VS", font=_font(FONT_CONDENSED, 24), fill=WHITE, anchor="mm")
    draw.text((132, 108), "AZVSCARS", font=_font(FONT_BOLD, 27), fill=WHITE, anchor="lm")
    return cv2.cvtColor(np.array(Image.alpha_composite(image, layer).convert("RGB")), cv2.COLOR_RGB2BGR)


def _clip_frames(path, seconds, seed):
    started = cv2.getTickCount()
    tick_freq = cv2.getTickFrequency() or 1
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        return []
    source_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    source_duration = frame_count / source_fps if frame_count else seconds
    available = max(0.0, source_duration - seconds - 0.1)
    ratio = int(hashlib.sha256(seed.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    start_seconds = available * (0.12 + ratio * 0.76)
    frames = []
    total = int(seconds * FPS)
    for index in range(total):
        if (cv2.getTickCount() - started) / tick_freq > 18:
            break
        cap.set(cv2.CAP_PROP_POS_MSEC, (start_seconds + index / FPS) * 1000)
        ok, frame = cap.read()
        if not ok:
            break
        frame = _cover(frame)
        frames.append(_watermark(frame))
    cap.release()
    return frames


def _join_with_dissolves(segments, transition_frames=7):
    result = []
    for segment in segments:
        if not segment:
            continue
        if not result:
            result.extend(segment)
            continue
        overlap = min(transition_frames, len(result), len(segment))
        tail = result[-overlap:]
        result = result[:-overlap]
        for index in range(overlap):
            alpha = (index + 1) / (overlap + 1)
            result.append(cv2.addWeighted(tail[index], 1.0 - alpha, segment[index], alpha, 0))
        result.extend(segment[overlap:])
    return result


def _end_card_frames(background_frame, seconds=1.6):
    rgb = cv2.cvtColor(background_frame, cv2.COLOR_BGR2RGB)
    background = Image.fromarray(rgb).filter(ImageFilter.GaussianBlur(34)).convert("RGBA")
    shade = Image.new("RGBA", background.size, (4, 7, 11, 208))
    base = Image.alpha_composite(background, shade)
    frames = []
    total = int(seconds * FPS)
    for index in range(total):
        progress = min(1.0, (index + 1) / max(1, int(total * 0.42)))
        eased = 1 - (1 - progress) ** 3
        layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        radius = int(156 * eased)
        cx, cy = OUT_W // 2, 600
        draw.ellipse((cx - radius - 12, cy - radius - 12, cx + radius + 12, cy + radius + 12), outline=ORANGE, width=8)
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=(8, 11, 16, 245), outline=RED, width=10)
        if eased > 0.72:
            alpha = int(255 * min(1.0, (eased - 0.72) / 0.28))
            draw.text((cx, cy), "VS", font=_font(FONT_DISPLAY, 132), fill=(*WHITE, alpha), anchor="mm")
        draw.text((cx, 960), "FOLLOW", font=_font(FONT_DISPLAY, 138), fill=WHITE, anchor="mm")
        draw.text((cx, 1105), "@azvscars", font=_font(FONT_BOLD, 58), fill=(214, 219, 226), anchor="mm")
        draw.rounded_rectangle((322, 1208, 758, 1218), radius=5, fill=RED)
        composed = Image.alpha_composite(base, layer).convert("RGB")
        frames.append(cv2.cvtColor(np.array(composed), cv2.COLOR_RGB2BGR))
    return frames


def _mux_car_audio(video_path, audio_paths, output_path, clip_seconds, duration):
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    command = [ffmpeg, "-y", "-i", video_path]
    for audio_path in audio_paths:
        command.extend(["-i", audio_path])

    filters = []
    labels = []
    for index in range(len(audio_paths)):
        label = f"car{index}"
        delay_ms = int(index * (clip_seconds - 0.23) * 1000)
        filters.append(
            f"[{index + 1}:a]"
            "silenceremove=start_periods=1:start_duration=0.02:start_threshold=-46dB,"
            f"atrim=duration={clip_seconds + 0.35:.3f},asetpts=PTS-STARTPTS,"
            "highpass=f=32,lowpass=f=15800,bass=g=4:f=95,"
            "acompressor=threshold=-15dB:ratio=3.5:attack=7:release=100,volume=1.05,"
            f"afade=t=in:st=0:d=0.08,afade=t=out:st={clip_seconds:.3f}:d=0.32,"
            f"adelay={delay_ms}|{delay_ms}[{label}]"
        )
        labels.append(f"[{label}]")
    filters.append(f"{''.join(labels)}amix=inputs={len(labels)}:duration=longest:normalize=0,apad[aout]")
    command.extend([
        "-filter_complex", ";".join(filters),
        "-map", "0:v:0", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-t", f"{duration:.3f}", "-movflags", "+faststart", output_path,
    ])
    completed = subprocess.run(command, capture_output=True, timeout=45)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.decode("utf-8", errors="replace")[-2000:])


def render_night_supercar_reel(video_paths, audio_paths, output_path, seed, clip_seconds=2.8):
    if not video_paths:
        raise ValueError("Night supercar Reel requires at least one video.")
    render_paths = list(video_paths)
    while len(render_paths) < 3:
        render_paths.append(render_paths[len(render_paths) % len(video_paths)])
    segments = [
        _clip_frames(path, clip_seconds, f"{seed}:{index}")
        for index, path in enumerate(render_paths[:3])
    ]
    if any(not segment for segment in segments):
        raise RuntimeError("A supercar video could not be decoded.")
    frames = _join_with_dissolves(segments)
    frames.extend(_end_card_frames(frames[-1]))

    with tempfile.TemporaryDirectory() as tmp:
        silent_path = os.path.join(tmp, "night_supercar_silent.mp4")
        reel_renderer._encode_frames(iter(frames), silent_path, FPS, OUT_W, OUT_H)
        valid_audio = [path for path in (audio_paths or []) if path and os.path.exists(path)]
        if len(valid_audio) >= 3:
            _mux_car_audio(silent_path, valid_audio[:3], output_path, clip_seconds, len(frames) / FPS)
        else:
            music = reel_renderer.select_audio_file(output_path)
            if music:
                reel_renderer._mux_audio(silent_path, music, output_path, len(frames) / FPS)
            else:
                os.replace(silent_path, output_path)
    return output_path
