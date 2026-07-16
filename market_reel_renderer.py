import os

from PIL import Image, ImageDraw, ImageFont


OUT_W = 1080
OUT_H = 1350
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_HEAD = os.path.join(BASE_DIR, "Anton-Regular.ttf")
FONT_BOLD = os.path.join(BASE_DIR, "Montserrat-Black.ttf")
FONT_CONDENSED = os.path.join(BASE_DIR, "BarlowCondensed-Bold.ttf")
FONT_REGULAR = os.path.join(BASE_DIR, "DejaVuSans.ttf")
BG = (12, 16, 21)
CARD = (18, 22, 29)
CARD_ALT = (24, 29, 37)
RED = (212, 31, 38)
RED_BRIGHT = (255, 78, 66)
ORANGE = (255, 125, 38)
WHITE = (248, 249, 251)
TEXT = (18, 21, 28)
MUTED = (130, 139, 151)
SOFT = (220, 225, 232)


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
    scale = max(OUT_W / img.width, 870 / img.height)
    resized = img.resize((int(img.width * scale), int(img.height * scale)))
    left = max(0, (resized.width - OUT_W) // 2)
    top = max(0, (resized.height - 870) // 2)
    return resized.crop((left, top, left + OUT_W, top + 870))


def _base_card(image_path, idx, total):
    canvas = Image.new("RGB", (OUT_W, OUT_H), BG)
    cover = _cover(image_path)
    canvas.paste(cover, (0, 0))

    shade = Image.new("RGBA", (OUT_W, OUT_H), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shade)
    for y in range(870):
        alpha = int(210 * (y / 870))
        sdraw.line([(0, y), (OUT_W, y)], fill=(0, 0, 0, alpha))
    for y in range(870, OUT_H):
        alpha = int(95 + ((y - 870) / max(1, OUT_H - 870)) * 80)
        sdraw.line([(0, y), (OUT_W, y)], fill=(0, 0, 0, alpha))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), shade).convert("RGB")

    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((42, 40, 396, 112), radius=24, fill=(*RED, 240))
    tag_font = _font(FONT_CONDENSED, 42)
    draw.text((72, 78), "AZVSCARS MARKET", font=tag_font, fill=WHITE, anchor="lm")

    badge_font = _font(FONT_CONDENSED, 48)
    draw.rounded_rectangle((920, 40, 1038, 112), radius=32, fill=(24, 29, 37))
    draw.text((979, 76), f"{idx}/{total}", font=badge_font, fill=WHITE, anchor="mm")
    draw.rounded_rectangle((46, 1180, 1034, 1286), radius=34, outline=(255, 255, 255, 18), width=2)
    return canvas


def _draw_listing(canvas, car):
    draw = ImageDraw.Draw(canvas)
    panel_top = 810
    panel = (34, panel_top, 1046, 1288)
    draw.rounded_rectangle(panel, radius=42, fill=WHITE)
    draw.rounded_rectangle((34, panel_top, 1046, panel_top + 16), radius=42, fill=RED_BRIGHT)

    price_box = (722, 860, 1008, 980)
    draw.rounded_rectangle(price_box, radius=30, fill=RED)
    draw.rounded_rectangle((710, 848, 996, 968), radius=30, outline=(255, 255, 255, 22), width=2)

    title_font = _fit(draw, car["name"], FONT_HEAD, 68, 600, min_size=40)
    meta_font = _font(FONT_CONDENSED, 33)
    price_font = _fit(draw, car["price_label"], FONT_BOLD, 54, 238, min_size=32)
    label_font = _font(FONT_CONDENSED, 26)
    cta_font = _font(FONT_REGULAR, 28)

    draw.text((72, 866), car["name"].upper(), font=title_font, fill=TEXT, anchor="la")
    draw.text((742, 886), "BAKI QIYMETI", font=label_font, fill=(255, 220, 221), anchor="la")
    draw.text((865, 936), car["price_label"], font=price_font, fill=WHITE, anchor="mm")

    specs = [
        str(car["year"]) if car.get("year") else "",
        car.get("engine", ""),
        car.get("mileage", ""),
    ]
    chip_y = 1024
    chip_x = 72
    for spec in [item for item in specs if item]:
        font = _fit(draw, spec, FONT_CONDENSED, 31, 220, min_size=22)
        text_w = int(draw.textlength(spec, font=font))
        chip_w = max(146, text_w + 50)
        draw.rounded_rectangle((chip_x, chip_y, chip_x + chip_w, chip_y + 62), radius=22, fill=(239, 241, 245))
        draw.text((chip_x + chip_w / 2, chip_y + 31), spec, font=font, fill=(47, 52, 60), anchor="mm")
        chip_x += chip_w + 18

    note_font = _font(FONT_REGULAR, 28)
    draw.text((72, 1160), "Qiymeti yadda saxla.", font=cta_font, fill=(96, 104, 115), anchor="la")
    draw.text((72, 1206), "Masin axtaran dosta gonder.", font=cta_font, fill=(96, 104, 115), anchor="la")
    draw.text((834, 1206), "@azvscars", font=note_font, fill=(77, 83, 92), anchor="mm")
    return canvas


def _draw_compare_slide(out_path, cars):
    canvas = Image.new("RGB", (OUT_W, OUT_H), BG)
    draw = ImageDraw.Draw(canvas)
    draw.ellipse((-130, -40, 440, 500), fill=(76, 15, 18))
    draw.ellipse((792, 892, 1230, 1380), fill=(96, 19, 22))
    draw.rounded_rectangle((66, 64, OUT_W - 66, 212), radius=34, fill=RED)
    title = _font(FONT_CONDENSED, 78)
    draw.text((540, 139), "HANSI DEAL DAHA GUVENLIDIR?", font=title, fill=WHITE, anchor="mm")

    card_top = 320
    for car in cars:
        price_font = _fit(draw, car["price_label"], FONT_BOLD, 36, 250, min_size=24)
        name_font = _fit(draw, car["name"], FONT_CONDENSED, 42, 450, min_size=26)
        draw.rounded_rectangle((70, card_top, 1010, card_top + 122), radius=26, fill=CARD_ALT)
        draw.text((112, card_top + 50), car["name"].upper(), font=name_font, fill=WHITE, anchor="lm")
        draw.text((920, card_top + 52), car["price_label"], font=price_font, fill=WHITE, anchor="rm")
        card_top += 154

    body = _font(FONT_REGULAR, 33)
    draw.text((76, 1110), "Qerarin niye bele oldugunu serhde yaz.", font=body, fill=SOFT)
    draw.text((76, 1172), "Masin axtaran dosta gonder ve reel-i yadda saxla.", font=body, fill=SOFT)
    draw.text((76, 1260), "@azvscars", font=_font(FONT_CONDENSED, 44), fill=(184, 190, 198))
    canvas.save(out_path)


def _draw_outro_slide(out_path, cars):
    canvas = Image.new("RGB", (OUT_W, OUT_H), BG)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, OUT_W, OUT_H), fill=BG)
    draw.ellipse((758, -120, 1240, 360), fill=(80, 16, 18))
    draw.ellipse((-160, 852, 320, 1330), fill=(92, 22, 24))
    draw.rounded_rectangle((64, 86, OUT_W - 64, 266), radius=34, fill=WHITE)
    title = _font(FONT_HEAD, 70)
    sub = _font(FONT_REGULAR, 30)
    draw.text((78, 118), "BAKI DEAL CHECK", font=title, fill=TEXT, anchor="la")
    draw.text((78, 206), "Sabah yeni qiymetler, yeni reel, yeni mubahise.", font=sub, fill=MUTED, anchor="la")

    y = 400
    for idx, car in enumerate(cars[:3], start=1):
        draw.rounded_rectangle((72, y, OUT_W - 72, y + 138), radius=30, fill=CARD)
        idx_font = _font(FONT_CONDENSED, 36)
        name_font = _fit(draw, car["name"], FONT_CONDENSED, 44, 520, min_size=24)
        price_font = _fit(draw, car["price_label"], FONT_BOLD, 40, 260, min_size=24)
        draw.text((112, y + 34), f"{idx:02d}", font=idx_font, fill=ORANGE, anchor="la")
        draw.text((112, y + 88), car["name"].upper(), font=name_font, fill=WHITE, anchor="la")
        draw.text((960, y + 82), car["price_label"], font=price_font, fill=WHITE, anchor="rm")
        y += 162

    cta_font = _font(FONT_REGULAR, 30)
    draw.text((78, 1178), "Masin axtaran dosta gonder.", font=cta_font, fill=SOFT, anchor="la")
    draw.text((78, 1230), "Qiymeti saxla, fikrini serhde yaz.", font=cta_font, fill=SOFT, anchor="la")
    draw.text((78, 1290), "@azvscars", font=_font(FONT_CONDENSED, 42), fill=(195, 200, 207), anchor="la")
    canvas.save(out_path)


def render_market_slides(cars, image_paths, out_dir):
    total = max(1, len(cars))
    card_targets = [
        ("slide1_cover.png", 0),
        ("slide2_power.png", 1),
        ("slide3_speed.png", 2),
    ]
    for filename, idx in card_targets:
        car = cars[min(idx, total - 1)]
        image_path = image_paths[min(idx, total - 1)]
        canvas = _base_card(image_path, min(idx, total - 1) + 1, total)
        canvas = _draw_listing(canvas, car)
        canvas.save(os.path.join(out_dir, filename))

    _draw_compare_slide(os.path.join(out_dir, "slide4_price.png"), cars)
    _draw_outro_slide(os.path.join(out_dir, "slide5_outro.png"), cars)
