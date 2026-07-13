import os
import subprocess
import tempfile

import cv2
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import reel_renderer


OUT_W, OUT_H = 1080, 1920
FPS = 30
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(BASE_DIR, "BarlowCondensed-Bold.ttf")
COLOR_RED = (229, 9, 20)
COLOR_WHITE = (255, 255, 255)


def _font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception:
        return ImageFont.load_default()


def _fit_font(draw, text, max_w, start, min_size=28):
    size = start
    font = _font(size)
    while draw.textlength(text, font=font) > max_w and size > min_size:
        size -= 2
        font = _font(size)
    return font


def _cover_resize(frame):
    h, w = frame.shape[:2]
    scale = max(OUT_W / w, OUT_H / h)
    nw, nh = int(w * scale), int(h * scale)
    resized = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_AREA)
    x = max(0, (nw - OUT_W) // 2)
    y = max(0, (nh - OUT_H) // 2)
    return resized[y:y + OUT_H, x:x + OUT_W]


def _draw_overlay(frame, text, subtext=None, progress=0.0, title=False, show_divider=True):
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(rgb).convert("RGBA")
    overlay = Image.new("RGBA", (OUT_W, OUT_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    draw.rectangle([0, 0, OUT_W, 320], fill=(0, 0, 0, 135))
    draw.rectangle([0, OUT_H - 320, OUT_W, OUT_H], fill=(0, 0, 0, 155))
    if show_divider:
        draw.rectangle([OUT_W // 2 - 3, 0, OUT_W // 2 + 3, OUT_H], fill=(*COLOR_RED, 180))

    draw.rounded_rectangle([60, 78, OUT_W - 60, 188], radius=0, fill=(*COLOR_RED, 245))
    font = _fit_font(draw, text.upper(), OUT_W - 160, 76 if title else 68)
    draw.text((OUT_W // 2, 132), text.upper(), font=font, fill=COLOR_WHITE, anchor="mm")

    if subtext:
        sub_font = _fit_font(draw, subtext.upper(), OUT_W - 140, 54)
        draw.text((OUT_W // 2, OUT_H - 220), subtext.upper(), font=sub_font, fill=COLOR_WHITE, anchor="mm")

    handle_font = _font(42)
    draw.text((OUT_W // 2, OUT_H - 102), "@azvscars", font=handle_font, fill=(210, 210, 210), anchor="mm")
    bar_w = int((OUT_W - 120) * max(0.0, min(1.0, progress)))
    draw.rectangle([60, OUT_H - 54, 60 + bar_w, OUT_H - 42], fill=COLOR_RED)
    draw.rectangle([60 + bar_w, OUT_H - 54, OUT_W - 60, OUT_H - 42], fill=(80, 80, 80, 210))

    img = Image.alpha_composite(img, overlay).convert("RGB")
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def _frames_from_video(path, seconds, cue, progress_start, progress_span, subtext=None, show_divider=True):
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        return []
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    source_fps = cap.get(cv2.CAP_PROP_FPS) or 25
    # Keep picture and native engine audio on the same source timeline.
    start = 0

    frames_needed = int(seconds * FPS)
    frames = []
    for i in range(frames_needed):
        ok, frame = cap.read()
        if not ok:
            cap.set(cv2.CAP_PROP_POS_FRAMES, start)
            ok, frame = cap.read()
        if not ok:
            break
        frame = _cover_resize(frame)
        zoom = 1.0 + 0.035 * (i / max(1, frames_needed - 1))
        zw, zh = int(OUT_W / zoom), int(OUT_H / zoom)
        x, y = (OUT_W - zw) // 2, (OUT_H - zh) // 2
        frame = cv2.resize(frame[y:y + zh, x:x + zw], (OUT_W, OUT_H), interpolation=cv2.INTER_LINEAR)
        frames.append(_draw_overlay(
            frame, cue, subtext=subtext,
            progress=progress_start + progress_span * i / max(1, frames_needed),
            show_divider=show_divider,
        ))
    cap.release()
    return frames


def _frames_from_image(path, seconds, cue, progress_start, progress_span, subtext=None, show_divider=True):
    img = cv2.imread(path)
    if img is None:
        img = np.zeros((OUT_H, OUT_W, 3), dtype=np.uint8)
    img = _cover_resize(img)
    frames = []
    total = int(seconds * FPS)
    for i in range(total):
        frames.append(_draw_overlay(
            img.copy(), cue, subtext=subtext,
            progress=progress_start + progress_span * i / max(1, total),
            show_divider=show_divider,
        ))
    return frames


def _end_card_frames(end_slide_path, seconds):
    img = cv2.imread(end_slide_path)
    if img is None:
        img = np.zeros((1350, 1080, 3), dtype=np.uint8)
    canvas = np.zeros((OUT_H, OUT_W, 3), dtype=np.uint8)
    h, w = img.shape[:2]
    scale = min(OUT_W / w, OUT_H / h)
    nw, nh = int(w * scale), int(h * scale)
    resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
    x, y = (OUT_W - nw) // 2, (OUT_H - nh) // 2
    canvas[y:y + nh, x:x + nw] = resized
    return [canvas.copy() for _ in range(int(seconds * FPS))]


def render_cinematic_reel(video_paths, fallback_slide_paths, end_slide_path, output_path, script, sfx_paths=None, source_video_paths=None, duration_sec=13.5):
    if not video_paths and not fallback_slide_paths:
        raise ValueError("No video or fallback slide paths provided.")

    cues = script.get("cues") or [script.get("title", "AVTO DÖYÜŞÜ")]
    show_divider = bool(script.get("is_comparison", True))
    subtext = "SOL: ADI NƏDİR?  •  SAĞ: ADI NƏDİR?" if show_divider else "ADI NƏDİR?  •  SONDA AÇILIR"
    visual_sources = list(video_paths) or list(fallback_slide_paths)
    main_seconds = max(8.0, duration_sec - 2.0)
    segment_count = min(len(cues), max(3, len(visual_sources) * 2))
    segment_seconds = main_seconds / segment_count
    frames = []

    for idx in range(segment_count):
        source = visual_sources[idx % len(visual_sources)]
        cue = cues[idx % len(cues)]
        progress_start = idx / (segment_count + 1)
        progress_span = 1 / (segment_count + 1)
        if source.lower().endswith((".mp4", ".mov", ".webm", ".m4v")):
            segment = _frames_from_video(source, segment_seconds, cue, progress_start, progress_span, subtext, show_divider)
        else:
            segment = _frames_from_image(source, segment_seconds, cue, progress_start, progress_span, subtext, show_divider)
        frames.extend(segment)

    if end_slide_path:
        frames.extend(_end_card_frames(end_slide_path, 2.0))

    if not frames:
        raise ValueError("Could not render any cinematic frames.")

    with tempfile.TemporaryDirectory() as tmp:
        temp_video = os.path.join(tmp, "cinematic_noaudio.mp4")
        writer = cv2.VideoWriter(temp_video, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (OUT_W, OUT_H))
        for frame in frames:
            writer.write(frame)
        writer.release()
        _mux_audio(
            temp_video, output_path, len(frames) / FPS, sfx_paths or [],
            source_video_paths or video_paths, segment_seconds,
        )
    return output_path


def _has_audio(path):
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    result = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", path],
        capture_output=True, text=True,
    )
    return "Audio:" in result.stderr


def _mux_audio(video_path, output_path, duration, sfx_paths, source_video_paths, segment_seconds):
    audio_inputs = []
    music = reel_renderer.select_audio_file(output_path)
    if music:
        audio_inputs.append(("music", music, 0))
    for idx, sfx in enumerate(sfx_paths[:5]):
        audio_inputs.append(("sfx", sfx, int((0.35 + idx * segment_seconds) * 1000)))
    for idx, source in enumerate(source_video_paths[:3]):
        if _has_audio(source):
            audio_inputs.append(("source", source, int(idx * segment_seconds * 1000)))

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    if not audio_inputs:
        subprocess.run([ffmpeg, "-y", "-i", video_path, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", output_path], check=True)
        return

    cmd = [ffmpeg, "-y", "-i", video_path]
    for _, path, _ in audio_inputs:
        cmd.extend(["-i", path])

    filters = []
    labels = []
    for i, (kind, _, delay_ms) in enumerate(audio_inputs, start=1):
        label = f"a{i}"
        volume = "0.16" if kind == "music" else ("0.72" if kind == "source" else "0.82")
        trim = min(duration, segment_seconds + 0.4) if kind == "source" else duration
        chain = f"[{i}:a]atrim=0:{trim:.2f},asetpts=PTS-STARTPTS,volume={volume}"
        if delay_ms:
            chain += f",adelay={delay_ms}|{delay_ms}"
        chain += f"[{label}]"
        filters.append(chain)
        labels.append(f"[{label}]")
    filters.append(f"{''.join(labels)}amix=inputs={len(labels)}:duration=first:dropout_transition=0[aout]")

    cmd.extend([
        "-filter_complex", ";".join(filters),
        "-map", "0:v:0",
        "-map", "[aout]",
        "-t", f"{duration:.2f}",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-b:v", "3500k",
        "-b:a", "160k",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path,
    ])
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
