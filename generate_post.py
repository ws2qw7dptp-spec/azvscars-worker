"""
Auto Page Post Generator
-------------------------
Turns car data (in cars.json) into finished, branded 1080x1350 Instagram
graphics automatically. Run this weekly after you gather real data.

Usage:
    python3 generate_post.py

Edit BRAND settings below once, then just keep editing cars.json every week.
Output goes to the output/ folder, one PNG per car, ready to post.
"""

import json
import os
import textwrap
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# BRAND SETTINGS — set these once, keep them consistent forever
# ---------------------------------------------------------------------------
BRAND_NAME = "AVTO BAZAR"          # watermark text, change to your page name
BG_COLOR = (20, 22, 26)            # dark charcoal
ACCENT_COLOR = (255, 179, 0)       # amber accent — change to your brand color
TEXT_COLOR = (245, 245, 245)
MUTED_COLOR = (160, 160, 160)
CANVAS_SIZE = (1080, 1350)         # Instagram portrait post size

# Fonts: DejaVuSans ships with Pillow's default set on most systems.
# Replace these paths with real font files for a distinct brand look.
FONT_DIR = "/usr/share/fonts/truetype/dejavu"
FONT_BOLD = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")
FONT_REGULAR = os.path.join(FONT_DIR, "DejaVuSans.ttf")


def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines, current = [], ""
    for w in words:
        trial = (current + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines


def make_car_card(car, out_path):
    img = Image.new("RGB", CANVAS_SIZE, BG_COLOR)
    draw = ImageDraw.Draw(img)
    margin = 70

    f_watermark = load_font(FONT_BOLD, 30)
    f_headline = load_font(FONT_BOLD, 64)
    f_price = load_font(FONT_BOLD, 90)
    f_label = load_font(FONT_REGULAR, 32)
    f_spec = load_font(FONT_REGULAR, 34)

    # Watermark (top)
    draw.text((margin, 50), BRAND_NAME, font=f_watermark, fill=ACCENT_COLOR)

    # Accent bar
    draw.rectangle([margin, 110, margin + 90, 116], fill=ACCENT_COLOR)

    # Headline (car name) — wrapped
    headline_lines = wrap_text(draw, car["name"], f_headline, CANVAS_SIZE[0] - 2 * margin)
    y = 160
    for line in headline_lines:
        draw.text((margin, y), line, font=f_headline, fill=TEXT_COLOR)
        y += 74

    # Price — the hero number
    y += 20
    draw.text((margin, y), car["price"], font=f_price, fill=ACCENT_COLOR)
    y += 130

    # Divider
    draw.line([(margin, y), (CANVAS_SIZE[0] - margin, y)], fill=(60, 62, 66), width=2)
    y += 40

    # Spec rows
    for spec in car.get("specs", []):
        label, value = spec.get("label", ""), spec.get("value", "")
        draw.text((margin, y), label.upper(), font=f_label, fill=MUTED_COLOR)
        draw.text((margin, y + 38), value, font=f_spec, fill=TEXT_COLOR)
        y += 100

    # Footer note / source
    footer = car.get("note", "")
    if footer:
        wrapped = wrap_text(draw, footer, f_label, CANVAS_SIZE[0] - 2 * margin)
        fy = CANVAS_SIZE[1] - 60 - (len(wrapped) * 38)
        for line in wrapped:
            draw.text((margin, fy), line, font=f_label, fill=MUTED_COLOR)
            fy += 38

    img.save(out_path)
    print(f"Saved: {out_path}")


def main():
    data_path = os.path.join(os.path.dirname(__file__), "cars.json")
    out_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(out_dir, exist_ok=True)

    with open(data_path, "r", encoding="utf-8") as f:
        cars = json.load(f)

    for i, car in enumerate(cars, start=1):
        safe_name = car["name"].replace(" ", "_").replace("/", "-")
        out_path = os.path.join(out_dir, f"{i:02d}_{safe_name}.png")
        make_car_card(car, out_path)


if __name__ == "__main__":
    main()
