import os
import subprocess
import tempfile

import cv2
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

import night_supercar_renderer as night
import reel_renderer
from publish_quality import normalize_price_label


OUT_W = 1080
OUT_H = 1920
FPS = 30
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_DISPLAY = os.path.join(BASE_DIR, "Anton-Regular.ttf")
FONT_BOLD = os.path.join(BASE_DIR, "Montserrat-Black.ttf")
FONT_CONDENSED = os.path.join(BASE_DIR, "BarlowCondensed-Bold.ttf")
WHITE = (248, 248, 245)
RED = (244, 42, 38)
MUTED = (203, 209, 218)
PANEL = (5, 8, 12, 174)


def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _fit(draw, text, font_path, size, max_w, min_size=28):
    font = _font(font_path, size)
    while draw.textlength(str(text), font=font) > max_w and size > min_size:
        size -= 2
        font = _font(font_path, size)
    return font


def _cover_image(path):
    with Image.open(path) as source:
        source = source.convert("RGB")
        source = ImageEnhance.Color(source).enhance(1.08)
        source = ImageEnhance.Contrast(source).enhance(1.08)
        return ImageOps.fit(source, (OUT_W, OUT_H), method=Image.Resampling.LANCZOS)


def _image_frame(path, zoom):
    image = _cover_image(path)
    crop_w = int(OUT_W / zoom)
    crop_h = int(OUT_H / zoom)
    left = max(0, (OUT_W - crop_w) // 2)
    top = max(0, (OUT_H - crop_h) // 2)
    image = image.crop((left, top, left + crop_w, top + crop_h)).resize((OUT_W, OUT_H), Image.Resampling.LANCZOS)
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)


def _market_image_frame(path, progress):
    with Image.open(path) as source:
        source = source.convert("RGB")
        source = ImageEnhance.Color(source).enhance(1.08)
        source = ImageEnhance.Contrast(source).enhance(1.08)

        background = ImageOps.fit(source, (OUT_W, OUT_H), method=Image.Resampling.LANCZOS)
        background = background.filter(ImageFilter.GaussianBlur(26))
        background = ImageEnhance.Brightness(background).enhance(0.58)
        background = ImageEnhance.Contrast(background).enhance(1.12).convert("RGBA")

        max_w = 1008
        max_h = 1110
        subtle_zoom = 1.0 + 0.018 * progress
        foreground = ImageOps.contain(
            source,
            (int(max_w * subtle_zoom), int(max_h * subtle_zoom)),
            method=Image.Resampling.LANCZOS,
        ).convert("RGBA")

        shadow = Image.new("RGBA", foreground.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.rounded_rectangle(
            (8, 8, foreground.width - 8, foreground.height - 8),
            radius=34,
            fill=(0, 0, 0, 136),
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(28))

        canvas = background
        x = (OUT_W - foreground.width) // 2
        y = max(188, (1286 - foreground.height) // 2)
        canvas.alpha_composite(shadow, (x, y + 22))
        canvas.alpha_composite(foreground, (x, y))
        return cv2.cvtColor(np.array(canvas.convert("RGB")), cv2.COLOR_RGB2BGR)


def _bottom_fade(layer):
    draw = ImageDraw.Draw(layer)
    for y in range(1120, OUT_H):
        alpha = int(220 * ((y - 1120) / (OUT_H - 1120)) ** 1.25)
        draw.line((0, y, OUT_W, y), fill=(3, 5, 8, alpha))


def _text_overlay(frame, title, line1="", line2="", tag=""):
    image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    _bottom_fade(layer)
    draw = ImageDraw.Draw(layer)

    draw.rounded_rectangle((58, 1378, 1022, 1704), radius=46, fill=PANEL, outline=(255, 255, 255, 38), width=2)
    if tag:
        tag_font = _fit(draw, tag.upper(), FONT_BOLD, 25, 360, min_size=18)
        draw.rounded_rectangle((88, 1410, 88 + int(draw.textlength(tag.upper(), font=tag_font)) + 48, 1462), radius=26, fill=RED)
        draw.text((112, 1436), tag.upper(), font=tag_font, fill=WHITE, anchor="lm")

    title_font = _fit(draw, str(title).upper(), FONT_DISPLAY, 82, 870, min_size=46)
    draw.text((88, 1536), str(title).upper(), font=title_font, fill=WHITE, anchor="lm")
    if line1:
        line_font = _fit(draw, str(line1), FONT_BOLD, 40, 870, min_size=26)
        draw.text((88, 1604), str(line1), font=line_font, fill=MUTED, anchor="lm")
    if line2:
        line_font = _fit(draw, str(line2), FONT_CONDENSED, 35, 870, min_size=24)
        draw.text((88, 1660), str(line2), font=line_font, fill=(222, 226, 232), anchor="lm")

    return cv2.cvtColor(np.array(Image.alpha_composite(image, layer).convert("RGB")), cv2.COLOR_RGB2BGR)


def _floating_cta_overlay(frame, progress):
    image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    eased = 0.5 - 0.5 * np.cos(np.pi * max(0.0, min(1.0, progress)))
    pulse = 0.5 - 0.5 * np.cos(2 * np.pi * max(0.0, min(1.0, progress)))
    alpha = int(188 + 34 * pulse)
    y = int(1090 + 34 * np.sin(2 * np.pi * eased))

    text = "DOSTUNA GÖNDƏR"
    font = _fit(draw, text, FONT_DISPLAY, 86, 830, min_size=56)
    text_w = int(draw.textlength(text, font=font))
    x = int(OUT_W + 70 - (OUT_W + text_w + 140) * eased)
    x = max(70, min(x, OUT_W - text_w - 70))
    box = (x - 34, y - 66, x + text_w + 34, y + 52)
    draw.rounded_rectangle(box, radius=34, fill=(5, 8, 12, alpha), outline=(255, 255, 255, 44), width=2)
    draw.rectangle((box[0] + 24, box[3] - 10, box[2] - 24, box[3] - 4), fill=RED)
    draw.text((x, y), text, font=font, fill=WHITE, anchor="lm")

    small = "QIYMƏTİ SONRA MÜQAYİSƏ ET"
    small_font = _fit(draw, small, FONT_BOLD, 33, 770, min_size=24)
    small_w = int(draw.textlength(small, font=small_font))
    small_x = int(70 + (OUT_W - small_w - 140) * eased)
    small_y = y + 86
    draw.rounded_rectangle(
        (small_x - 24, small_y - 34, small_x + small_w + 24, small_y + 31),
        radius=24,
        fill=(244, 42, 38, int(168 + 22 * pulse)),
    )
    draw.text((small_x, small_y), small, font=small_font, fill=WHITE, anchor="lm")

    return cv2.cvtColor(np.array(Image.alpha_composite(image, layer).convert("RGB")), cv2.COLOR_RGB2BGR)


def _segment(path, seconds, seed, title, line1="", line2="", tag=""):
    frames = []
    total = int(seconds * FPS)
    for index in range(total):
        progress = index / max(1, total - 1)
        frame = _image_frame(path, 1.0 + 0.045 * progress)
        frame = night._watermark(frame)
        frame = _text_overlay(frame, title, line1, line2, tag)
        frames.append(frame)
    return frames


def _market_frames(img_path, car, details):
    frames = []
    total = int(6.5 * FPS)
    first_end = int(2.2 * FPS)
    cta_end = int(4.9 * FPS)
    title = car.get("name", "AZVSCARS")
    price = car.get("price_label", "")

    for index in range(total):
        progress = index / max(1, total - 1)
        frame = _market_image_frame(img_path, progress)
        frame = night._watermark(frame)
        frame = _text_overlay(frame, title, price, details, "BU PULA DƏYƏR?")
        if first_end <= index < cta_end:
            frame = _floating_cta_overlay(frame, (index - first_end) / max(1, cta_end - first_end - 1))
        frames.append(frame)
    return frames


def _mux_audio(video_path, audio_paths, output_path, segment_seconds, duration):
    valid_audio = [path for path in (audio_paths or []) if path and os.path.exists(path)]
    if valid_audio:
        night._mux_car_audio(video_path, valid_audio, output_path, segment_seconds, duration)
        return
    music = reel_renderer.select_audio_file(output_path)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    if music:
        subprocess.run([
            ffmpeg, "-y", "-i", video_path, "-i", music,
            "-filter:a", "volume=0.32", "-t", f"{duration:.3f}",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
            "-movflags", "+faststart", output_path,
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    else:
        subprocess.run([
            ffmpeg, "-y", "-i", video_path, "-c:v", "copy",
            "-movflags", "+faststart", output_path,
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def _write(frames, output_path, audio_paths=None, segment_seconds=2.55):
    if not frames:
        raise ValueError("No clean reel frames generated.")
    frames.extend(night._end_card_frames(frames[-1], seconds=1.6))
    with tempfile.TemporaryDirectory() as tmp:
        silent_path = os.path.join(tmp, "clean_silent.mp4")
        reel_renderer._encode_frames(iter(frames), silent_path, FPS, OUT_W, OUT_H)
        _mux_audio(silent_path, audio_paths, output_path, segment_seconds, len(frames) / FPS)
    return output_path


def render_clean_comparison_reel(data, img1_path, img2_path, output_path, audio_paths=None):
    car1 = data.get("car1_name", "Car 1")
    car2 = data.get("car2_name", "Car 2")
    price1 = normalize_price_label(data.get("slide4_car1_stat", ""))
    price2 = normalize_price_label(data.get("slide4_car2_stat", ""))
    power1 = data.get("slide2_car1_stat", "")
    power2 = data.get("slide2_car2_stat", "")
    speed1 = data.get("slide3_car1_stat", "")
    speed2 = data.get("slide3_car2_stat", "")
    frames = []
    frames.extend(_segment(img1_path, 2.55, "car1", car1, price1, f"{power1} / 0-100: {speed1}", "SOL SEÇİM"))
    frames.extend(_segment(img2_path, 2.55, "car2", car2, price2, f"{power2} / 0-100: {speed2}", "SAĞ SEÇİM"))
    return _write(night._join_with_dissolves([frames[:76], frames[76:]], transition_frames=7), output_path, audio_paths, 2.55)


def render_clean_single_car_reel(car, img_path, output_path, audio_paths=None):
    meta_bits = [str(car.get("year") or ""), car.get("engine", ""), car.get("mileage", "")]
    details = " / ".join(bit for bit in meta_bits if bit)
    return _write(_market_frames(img_path, car, details), output_path, audio_paths, 2.4)
