import hashlib
import os
import random

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps


OUT_W = 1080
OUT_H = 1920
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_DISPLAY = os.path.join(BASE_DIR, "Anton-Regular.ttf")
FONT_BOLD = os.path.join(BASE_DIR, "Montserrat-Black.ttf")
FONT_CONDENSED = os.path.join(BASE_DIR, "BarlowCondensed-Bold.ttf")
FONT_REGULAR = FONT_CONDENSED

INK = (8, 11, 15)
PANEL = (16, 20, 26)
PANEL_2 = (25, 30, 38)
RED = (239, 50, 46)
ORANGE = (255, 120, 52)
IVORY = (247, 244, 237)
WHITE = (255, 255, 255)
MUTED = (154, 162, 174)
HAIRLINE = (255, 255, 255, 34)


def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _fit(draw, text, font_path, size, max_w, min_size=24):
    font = _font(font_path, size)
    while draw.textlength(str(text), font=font) > max_w and size > min_size:
        size -= 2
        font = _font(font_path, size)
    return font


def _linear_gradient(size, top, bottom):
    width, height = size
    gradient = Image.new("RGB", size, top)
    draw = ImageDraw.Draw(gradient)
    for y in range(height):
        t = y / max(1, height - 1)
        color = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
        draw.line((0, y, width, y), fill=color)
    return gradient


def _add_grain(image, seed, opacity=12):
    rng = random.Random(hashlib.sha256(seed.encode()).hexdigest())
    # A small tiled texture gives natural grain without allocating millions of Python ints.
    noise = Image.new("L", (270, 480))
    noise.putdata([rng.randrange(80, 176) for _ in range(noise.width * noise.height)])
    noise = noise.resize(image.size, Image.Resampling.BILINEAR).filter(ImageFilter.GaussianBlur(0.35))
    texture = Image.merge("RGBA", (noise, noise, noise, Image.new("L", image.size, opacity)))
    return Image.alpha_composite(image.convert("RGBA"), texture).convert("RGB")


def _rounded_paste(base, layer, box, radius):
    x1, y1, x2, y2 = box
    layer = layer.resize((x2 - x1, y2 - y1), Image.Resampling.LANCZOS)
    mask = Image.new("L", layer.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, layer.width, layer.height), radius=radius, fill=255)
    base.paste(layer, (x1, y1), mask)


def _photo_stage(image_path):
    with Image.open(image_path) as source:
        source = source.convert("RGB")
        source = ImageEnhance.Color(source).enhance(1.06)
        source = ImageEnhance.Contrast(source).enhance(1.07)

    canvas = _linear_gradient((OUT_W, OUT_H), (17, 21, 27), INK)
    backdrop = ImageOps.fit(source, (OUT_W, 1320), method=Image.Resampling.LANCZOS)
    backdrop = backdrop.filter(ImageFilter.GaussianBlur(32))
    backdrop = ImageEnhance.Brightness(backdrop).enhance(0.38)
    canvas.paste(backdrop, (0, 0))

    # Keep the entire car visible even when Commons returns a wide landscape photo.
    stage_box = (38, 214, 1042, 1180)
    stage_w = stage_box[2] - stage_box[0]
    stage_h = stage_box[3] - stage_box[1]
    contained = ImageOps.contain(source, (stage_w, stage_h), method=Image.Resampling.LANCZOS)
    plate = Image.new("RGB", (stage_w, stage_h), (11, 14, 18))
    plate_bg = ImageOps.fit(source, (stage_w, stage_h), method=Image.Resampling.LANCZOS)
    plate_bg = plate_bg.filter(ImageFilter.GaussianBlur(26))
    plate_bg = ImageEnhance.Brightness(plate_bg).enhance(0.52)
    plate.paste(plate_bg, (0, 0))
    plate.paste(contained, ((stage_w - contained.width) // 2, (stage_h - contained.height) // 2))
    _rounded_paste(canvas, plate, stage_box, 42)

    overlay = Image.new("RGBA", (OUT_W, OUT_H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    odraw.rounded_rectangle(stage_box, radius=42, outline=(255, 255, 255, 42), width=2)
    for y in range(930, 1330):
        alpha = int(215 * ((y - 930) / 400) ** 1.6)
        odraw.line((0, y, OUT_W, y), fill=(8, 11, 15, alpha))
    return Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")


def _brand_header(draw, index, total):
    draw.rounded_rectangle((42, 76, 338, 150), radius=37, fill=(239, 50, 46))
    draw.text((190, 113), "AZVSCARS", font=_font(FONT_BOLD, 34), fill=WHITE, anchor="mm")
    draw.text((374, 113), "BAKI MARKET", font=_font(FONT_CONDENSED, 31), fill=(218, 223, 230), anchor="lm")
    draw.text((1008, 113), f"0{index} / 0{total}", font=_font(FONT_BOLD, 31), fill=IVORY, anchor="rm")


def _draw_listing(canvas, car, index, total):
    draw = ImageDraw.Draw(canvas)
    _brand_header(draw, index, total)

    draw.rounded_rectangle((38, 1060, 1042, 1712), radius=52, fill=PANEL)
    draw.rounded_rectangle((38, 1060, 1042, 1712), radius=52, outline=HAIRLINE, width=2)
    draw.rounded_rectangle((76, 1100, 316, 1156), radius=28, fill=(45, 51, 61))
    draw.ellipse((98, 1118, 112, 1132), fill=ORANGE)
    draw.text((132, 1128), "REAL BAZAR QİYMƏTİ", font=_font(FONT_CONDENSED, 24), fill=(226, 229, 234), anchor="lm")

    name = car["name"].upper()
    name_font = _fit(draw, name, FONT_DISPLAY, 88, 900, min_size=52)
    draw.text((76, 1190), name, font=name_font, fill=IVORY, anchor="la")

    draw.line((76, 1312, 1004, 1312), fill=(255, 255, 255, 28), width=2)
    draw.text((76, 1362), "BAKI ÜZRƏ TƏXMİNİ QİYMƏT", font=_font(FONT_CONDENSED, 28), fill=MUTED, anchor="la")
    price_font = _fit(draw, car["price_label"], FONT_BOLD, 78, 870, min_size=52)
    draw.text((76, 1418), car["price_label"], font=price_font, fill=WHITE, anchor="la")
    draw.rounded_rectangle((76, 1510, 1004, 1658), radius=32, fill=PANEL_2)

    specs = [
        str(car.get("year") or ""),
        car.get("engine", ""),
        car.get("mileage", ""),
    ]
    x_positions = (114, 430, 728)
    labels = ("İL", "MÜHƏRRİK", "YÜRÜŞ")
    for x, label, value in zip(x_positions, labels, specs):
        draw.text((x, 1542), label, font=_font(FONT_CONDENSED, 21), fill=MUTED, anchor="la")
        value_font = _fit(draw, value, FONT_BOLD, 29, 250, min_size=20)
        draw.text((x, 1603), value, font=value_font, fill=IVORY, anchor="la")

    draw.text((76, 1774), "SAXLA", font=_font(FONT_BOLD, 27), fill=RED, anchor="la")
    draw.text((196, 1774), "real bazarda müqayisə et", font=_font(FONT_REGULAR, 27), fill=(208, 213, 221), anchor="la")
    draw.text((1004, 1774), "@azvscars", font=_font(FONT_CONDENSED, 30), fill=MUTED, anchor="ra")
    return _add_grain(canvas, f"{car['name']}:{index}", opacity=7)


def _draw_compare_slide(out_path, cars):
    canvas = _linear_gradient((OUT_W, OUT_H), (20, 25, 32), INK)
    canvas = _add_grain(canvas, "market-decision", opacity=8)
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((42, 76, 338, 150), radius=37, fill=RED)
    draw.text((190, 113), "AZVSCARS", font=_font(FONT_BOLD, 34), fill=WHITE, anchor="mm")
    draw.text((998, 113), "DEAL CHECK / 04", font=_font(FONT_CONDENSED, 28), fill=MUTED, anchor="ra")

    draw.text((64, 270), "SƏNİN PULUN", font=_font(FONT_DISPLAY, 88), fill=IVORY, anchor="la")
    draw.text((64, 370), "HANSI BİRİNƏ GEDƏR?", font=_font(FONT_DISPLAY, 88), fill=IVORY, anchor="la")
    draw.rounded_rectangle((64, 510, 640, 576), radius=33, fill=RED)
    draw.text((352, 543), "ŞƏRHDƏ SƏBƏBİNİ YAZ", font=_font(FONT_CONDENSED, 31), fill=WHITE, anchor="mm")

    y = 650
    for idx, car in enumerate(cars[:3], start=1):
        draw.rounded_rectangle((64, y, 1016, y + 242), radius=38, fill=PANEL)
        draw.rounded_rectangle((64, y, 76, y + 242), radius=6, fill=RED if idx == 1 else ORANGE)
        draw.text((106, y + 49), f"0{idx}", font=_font(FONT_CONDENSED, 28), fill=MUTED, anchor="la")
        name_font = _fit(draw, car["name"].upper(), FONT_DISPLAY, 55, 610, min_size=34)
        draw.text((106, y + 92), car["name"].upper(), font=name_font, fill=IVORY, anchor="la")
        price_font = _fit(draw, car["price_label"], FONT_BOLD, 40, 330, min_size=27)
        draw.text((970, y + 125), car["price_label"], font=price_font, fill=WHITE, anchor="ra")
        detail = "  •  ".join(filter(None, [str(car.get("year") or ""), car.get("engine", ""), car.get("mileage", "")]))
        detail_font = _fit(draw, detail, FONT_CONDENSED, 27, 820, min_size=20)
        draw.text((106, y + 192), detail, font=detail_font, fill=MUTED, anchor="la")
        y += 278

    social_cta = "DOSTUNA GÖNDƏR: İKİNİZ DƏ EYNİ MAŞINI SEÇİRSİNİZ?"
    social_font = _fit(draw, social_cta, FONT_BOLD, 31, 940, min_size=23)
    draw.text((64, 1582), social_cta, font=social_font, fill=RED, anchor="la")
    draw.text((64, 1730), "@azvscars", font=_font(FONT_CONDENSED, 34), fill=MUTED, anchor="la")
    canvas.save(out_path, quality=96)


def _draw_outro_slide(out_path, cars):
    canvas = _linear_gradient((OUT_W, OUT_H), (24, 28, 35), INK)
    canvas = _add_grain(canvas, "market-outro", opacity=9)
    draw = ImageDraw.Draw(canvas)
    draw.ellipse((716, -120, 1240, 404), fill=(86, 20, 20))
    draw.ellipse((-240, 1450, 300, 1990), fill=(71, 25, 19))
    draw.rounded_rectangle((72, 106, 350, 180), radius=37, fill=RED)
    draw.text((211, 143), "AZVSCARS", font=_font(FONT_BOLD, 34), fill=WHITE, anchor="mm")

    draw.text((72, 430), "SABAH", font=_font(FONT_DISPLAY, 112), fill=IVORY, anchor="la")
    draw.text((72, 560), "YENİ DEAL.", font=_font(FONT_DISPLAY, 112), fill=IVORY, anchor="la")
    draw.rounded_rectangle((72, 740, 1008, 932), radius=42, fill=PANEL)
    draw.text((116, 796), "İZLƏ", font=_font(FONT_BOLD, 29), fill=RED, anchor="la")
    draw.text((116, 858), "real Bakı qiymətləri və fərqli maşınlar", font=_font(FONT_REGULAR, 31), fill=(218, 222, 228), anchor="la")

    draw.line((72, 1070, 1008, 1070), fill=(255, 255, 255, 42), width=2)
    draw.text((72, 1142), "BU GÜNÜN SƏNƏ FAYDASI OLDUSA:", font=_font(FONT_CONDENSED, 32), fill=MUTED, anchor="la")
    actions = (("01", "BİRİNİ SEÇ"), ("02", "DOSTUNA GÖNDƏR"), ("03", "CAVABI MÜQAYİSƏ ET"))
    y = 1244
    for number, label in actions:
        draw.text((76, y), number, font=_font(FONT_BOLD, 29), fill=ORANGE, anchor="la")
        action_font = _fit(draw, label, FONT_DISPLAY, 58, 790, min_size=38)
        draw.text((178, y), label, font=action_font, fill=IVORY, anchor="la")
        y += 112
    draw.text((72, 1732), "@azvscars", font=_font(FONT_CONDENSED, 42), fill=MUTED, anchor="la")
    canvas.save(out_path, quality=96)


def render_market_slides(cars, image_paths, out_dir):
    total = min(3, len(cars), len(image_paths))
    if total < 1:
        raise ValueError("Market reel requires at least one car image.")
    targets = ("slide1_cover.png", "slide2_power.png", "slide3_speed.png")
    for idx in range(total):
        canvas = _photo_stage(image_paths[idx])
        canvas = _draw_listing(canvas, cars[idx], idx + 1, total)
        canvas.save(os.path.join(out_dir, targets[idx]), optimize=True)

    # Keep three car cards; market Reels intentionally have no template outro screens.
    for idx in range(total, 3):
        canvas = _photo_stage(image_paths[idx % total])
        canvas = _draw_listing(canvas, cars[idx % total], idx + 1, total)
        canvas.save(os.path.join(out_dir, targets[idx]), optimize=True)
