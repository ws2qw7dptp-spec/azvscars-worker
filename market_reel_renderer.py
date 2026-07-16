import os

from PIL import Image, ImageDraw, ImageFont


OUT_W = 1080
OUT_H = 1350
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_BOLD = os.path.join(BASE_DIR, "BarlowCondensed-Bold.ttf")
FONT_REGULAR = os.path.join(BASE_DIR, "DejaVuSans.ttf")
BG = (15, 18, 22)
RED = (191, 12, 25)
RED_BRIGHT = (231, 38, 54)
WHITE = (250, 250, 250)
TEXT = (22, 24, 28)
MUTED = (108, 112, 119)


def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _fit(draw, text, font_path, size, max_w, min_size=24):
    font = _font(font_path, size)
    while draw.textlength(text, font=font) > max_w and size > min_size:
        size -= 2
        font = _font(font_path, size)
    return font


def _cover(image_path):
    img = Image.open(image_path).convert("RGB")
    scale = max(OUT_W / img.width, 900 / img.height)
    resized = img.resize((int(img.width * scale), int(img.height * scale)))
    left = max(0, (resized.width - OUT_W) // 2)
    top = max(0, (resized.height - 900) // 2)
    return resized.crop((left, top, left + OUT_W, top + 900))


def _base_card(image_path, idx, total):
    canvas = Image.new("RGB", (OUT_W, OUT_H), BG)
    cover = _cover(image_path)
    canvas.paste(cover, (0, 0))

    shade = Image.new("RGBA", (OUT_W, OUT_H), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shade)
    for y in range(900):
        alpha = int(220 * (y / 900))
        sdraw.line([(0, y), (OUT_W, y)], fill=(0, 0, 0, alpha))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), shade).convert("RGB")

    draw = ImageDraw.Draw(canvas)
    draw.polygon([(0, 0), (330, 0), (260, 100), (0, 100)], fill=RED)
    tag_font = _font(FONT_BOLD, 44)
    draw.text((36, 49), "AZVSCARS MARKET", font=tag_font, fill=WHITE, anchor="lm")

    badge_font = _font(FONT_BOLD, 52)
    draw.rounded_rectangle((920, 40, 1038, 116), radius=34, fill=(35, 39, 45))
    draw.text((979, 78), f"{idx}/{total}", font=badge_font, fill=WHITE, anchor="mm")
    return canvas


def _draw_listing(canvas, car):
    draw = ImageDraw.Draw(canvas)
    panel_top = 900
    draw.rectangle((0, panel_top, OUT_W, OUT_H), fill=WHITE)
    draw.polygon([(730, OUT_H), (1080, OUT_H), (1080, panel_top), (845, panel_top)], fill=RED)
    draw.line((0, panel_top, 835, panel_top), fill=RED_BRIGHT, width=8)

    title_font = _fit(draw, car["name"], FONT_BOLD, 68, 620)
    meta_font = _font(FONT_REGULAR, 34)
    price_font = _fit(draw, car["price_label"], FONT_BOLD, 74, 250)
    cta_font = _font(FONT_REGULAR, 28)

    draw.text((76, 1014), car["name"], font=title_font, fill=TEXT)
    meta_parts = [str(car["year"]) if car.get("year") else "", car.get("engine", ""), car.get("mileage", "")]
    meta = ", ".join(part for part in meta_parts if part)
    draw.text((76, 1094), meta, font=meta_font, fill=TEXT)
    draw.text((908, 1086), car["price_label"], font=price_font, fill=WHITE, anchor="mm")
    draw.text((76, 1238), "Qiyməti yadda saxla • Maşın axtaran dosta göndər", font=cta_font, fill=MUTED)
    return canvas


def _draw_title_slide(out_path):
    canvas = Image.new("RGB", (OUT_W, OUT_H), BG)
    draw = ImageDraw.Draw(canvas)
    draw.ellipse((-80, -40, 520, 560), fill=(130, 16, 24))
    draw.ellipse((720, 760, 1210, 1430), fill=(90, 10, 20))
    draw.rectangle((74, 120, 500, 138), fill=RED_BRIGHT)
    eyebrow = _font(FONT_BOLD, 42)
    title = _font(FONT_BOLD, 130)
    sub = _font(FONT_REGULAR, 36)
    draw.text((74, 92), "AZVSCARS", font=eyebrow, fill=(255, 210, 214))
    draw.text((74, 214), "BAKI", font=title, fill=WHITE)
    draw.text((74, 340), "QIYMET CHECK", font=title, fill=WHITE)
    draw.text((74, 474), "Reel formatinda real bazar istiqameti", font=sub, fill=(218, 220, 225))
    draw.text((74, 538), "Saxla, paylas, sabah yenisini gozle", font=sub, fill=(218, 220, 225))
    canvas.save(out_path)


def _draw_outro_slide(out_path, cars):
    canvas = Image.new("RGB", (OUT_W, OUT_H), BG)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, OUT_W, OUT_H), fill=(16, 18, 22))
    draw.rounded_rectangle((64, 80, OUT_W - 64, 224), radius=30, fill=RED)
    title = _font(FONT_BOLD, 82)
    body = _font(FONT_REGULAR, 38)
    list_font = _font(FONT_BOLD, 44)
    draw.text((540, 152), "HANSI DEAL DAHA GUVENLIDIR?", font=title, fill=WHITE, anchor="mm")
    y = 330
    for car in cars:
        draw.rounded_rectangle((72, y - 18, OUT_W - 72, y + 74), radius=20, fill=(28, 31, 37))
        draw.text((104, y + 26), f"{car['name']}  •  {car['price_label']}", font=list_font, fill=WHITE, anchor="lm")
        y += 126
    draw.text((84, 1098), "Qerarin niye bele oldugunu serhde yaz.", font=body, fill=(223, 226, 231))
    draw.text((84, 1158), "Masin axtaran dosta gonder ve reel-i yadda saxla.", font=body, fill=(223, 226, 231))
    draw.text((84, 1262), "@azvscars", font=_font(FONT_BOLD, 42), fill=(172, 176, 184))
    canvas.save(out_path)


def render_market_slides(cars, image_paths, out_dir):
    total = max(1, len(cars))
    _draw_title_slide(os.path.join(out_dir, "slide1_cover.png"))

    card_targets = [
        ("slide2_power.png", 0),
        ("slide3_speed.png", 1),
        ("slide4_price.png", 2),
    ]
    for filename, idx in card_targets:
        car = cars[min(idx, total - 1)]
        image_path = image_paths[min(idx, total - 1)]
        canvas = _base_card(image_path, min(idx, total - 1) + 1, total)
        canvas = _draw_listing(canvas, car)
        canvas.save(os.path.join(out_dir, filename))

    _draw_outro_slide(os.path.join(out_dir, "slide5_outro.png"), cars)
