import os
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
BLACK = (6, 8, 12)
WHITE = (248, 248, 248)
MUTED = (180, 180, 180)
RED = (238, 0, 20)
DARK_RED = (90, 0, 8)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def font(size):
    for name in ["Anton-Regular.ttf", "BarlowCondensed-Bold.ttf", "Oswald-Bold.ttf"]:
        try:
            return ImageFont.truetype(os.path.join(BASE_DIR, name), size)
        except Exception:
            pass
    return ImageFont.load_default()


def centered(draw, text, y, size, fill=WHITE):
    f = font(size)
    draw.text((W // 2, y), text, font=f, fill=fill, anchor="mm")


def rect_text(draw, text, y, size=78):
    f = font(size)
    box = draw.textbbox((0, 0), text, font=f)
    tw, th = box[2] - box[0], box[3] - box[1]
    pad_x, pad_y = 30, 18
    x1 = (W - tw) // 2 - pad_x
    y1 = y - th // 2 - pad_y
    x2 = (W + tw) // 2 + pad_x
    y2 = y + th // 2 + pad_y
    draw.rounded_rectangle([x1, y1, x2, y2], radius=0, fill=RED)
    draw.text((W // 2, y), text, font=f, fill=WHITE, anchor="mm")


def base_card():
    img = Image.new("RGB", (W, H), BLACK)
    draw = ImageDraw.Draw(img)
    for y in range(H):
        alpha = y / H
        r = int(BLACK[0] * (1 - alpha) + 18 * alpha)
        g = int(BLACK[1] * (1 - alpha) + 0 * alpha)
        b = int(BLACK[2] * (1 - alpha) + 3 * alpha)
        draw.line([(0, y), (W, y)], fill=(r, g, b))
    draw.line([(W // 2, 0), (W // 2, H)], fill=RED, width=6)
    draw.ellipse([W // 2 - 92, 120, W // 2 + 92, 304], outline=RED, width=8)
    centered(draw, "VS", 212, 92, WHITE)
    centered(draw, "AZVSCARS", 330, 34, RED)
    return img, draw


def footer(draw):
    draw.line([(140, 1650), (W - 140, 1650)], fill=DARK_RED, width=4)
    centered(draw, "@azvscars", 1715, 52, MUTED)
    centered(draw, "TƏRƏFİNİ SEÇ", 1790, 72, WHITE)


def story_brand(path):
    img, draw = base_card()
    rect_text(draw, "AVTO DÖYÜŞLƏR", 650, 86)
    centered(draw, "HƏR GÜN", 790, 128, WHITE)
    centered(draw, "ÇİN vs ALMAN", 980, 74, RED)
    centered(draw, "EV vs V8", 1080, 74, RED)
    centered(draw, "STATUS vs ETİBAR", 1180, 74, RED)
    footer(draw)
    img.save(path, quality=94)


def story_schedule(path):
    img, draw = base_card()
    rect_text(draw, "GÜNDƏ 4 POST", 610, 92)
    centered(draw, "09:00-09:25  SÜRÜCÜ SEÇİMİ", 820, 60, WHITE)
    centered(draw, "13:00-13:25  REAL AVTO DÖYÜŞ", 940, 60, WHITE)
    centered(draw, "19:30-19:55  ŞƏRH SAVAŞI", 1060, 60, WHITE)
    centered(draw, "22:45-23:10  GECƏ DÖYÜŞÜ", 1180, 60, WHITE)
    centered(draw, "BAKI VAXTI İLƏ", 1350, 54, MUTED)
    footer(draw)
    img.save(path, quality=94)


def story_topics(path):
    img, draw = base_card()
    rect_text(draw, "HANSI TƏRƏFDƏSƏN?", 610, 76)
    centered(draw, "TESLA vs BMW", 820, 76, WHITE)
    centered(draw, "BYD vs MERCEDES", 940, 76, WHITE)
    centered(draw, "LAND CRUISER vs G-CLASS", 1060, 64, WHITE)
    centered(draw, "LEXUS vs RANGE ROVER", 1180, 68, WHITE)
    footer(draw)
    img.save(path, quality=94)


def story_contact(path, email="islammuradov1@icloud.com"):
    img, draw = base_card()
    rect_text(draw, "SPONSORLUQ", 610, 96)
    centered(draw, "ƏMƏKDAŞLIQ ÜÇÜN", 790, 72, WHITE)
    centered(draw, "DM AÇIQDIR", 920, 92, RED)
    centered(draw, email, 1060, 54, WHITE)
    centered(draw, "AVTO BRANDLAR • SERVİSLƏR • SALONLAR", 1240, 44, MUTED)
    footer(draw)
    img.save(path, quality=94)


def story_comment(path):
    img, draw = base_card()
    rect_text(draw, "ŞƏRH SAVAŞI", 610, 94)
    centered(draw, "SOL YOXSA SAĞ?", 820, 118, WHITE)
    centered(draw, "FİKRİNİ KOMMENTƏ YAZ", 1010, 72, RED)
    centered(draw, "ƏN ÇOX SEÇİLƏN MAŞIN", 1160, 58, MUTED)
    centered(draw, "YENİ RƏQİBLƏ QAYIDIR", 1240, 58, MUTED)
    footer(draw)
    img.save(path, quality=94)


def story_china_germany(path):
    img, draw = base_card()
    rect_text(draw, "ÇİN vs ALMAN", 610, 92)
    centered(draw, "BYD • ZEEKR • LI AUTO", 820, 66, WHITE)
    centered(draw, "MERCEDES • BMW • AUDI", 940, 66, WHITE)
    centered(draw, "TEXNOLOGİYA", 1110, 84, RED)
    centered(draw, "YOXSA PRESTİJ?", 1210, 84, RED)
    footer(draw)
    img.save(path, quality=94)


def story_ev_v8(path):
    img, draw = base_card()
    rect_text(draw, "EV vs V8", 610, 98)
    centered(draw, "ANİ SÜRƏT", 820, 86, WHITE)
    centered(draw, "YOXSA MÜHƏRRİK SƏSİ?", 940, 76, WHITE)
    centered(draw, "TESLA • AMG • M", 1110, 72, RED)
    centered(draw, "SƏNİN TƏRƏFİN HANSIDIR?", 1280, 58, MUTED)
    footer(draw)
    img.save(path, quality=94)


def story_suv_war(path):
    img, draw = base_card()
    rect_text(draw, "SUV DÖYÜŞ", 610, 98)
    centered(draw, "LAND CRUISER", 820, 84, WHITE)
    centered(draw, "G-CLASS", 940, 84, WHITE)
    centered(draw, "LEXUS LX", 1060, 84, WHITE)
    centered(draw, "RANGE ROVER", 1180, 84, WHITE)
    centered(draw, "ETİBAR YOXSA STATUS?", 1350, 58, RED)
    footer(draw)
    img.save(path, quality=94)


def _fit_centered(draw, text, y, max_width=900, start_size=78, fill=WHITE):
    size = start_size
    while size > 34:
        f = font(size)
        if draw.textbbox((0, 0), text, font=f)[2] <= max_width:
            break
        size -= 2
    draw.text((W // 2, y), text, font=font(size), fill=fill, anchor="mm")


def story_daily_duel(path, data):
    img, draw = base_card()
    rect_text(draw, "BUGÜNÜN DUELİ", 610, 88)
    _fit_centered(draw, data.get("car1_name", "SOL TƏRƏF"), 820, fill=WHITE)
    centered(draw, "VS", 965, 82, RED)
    _fit_centered(draw, data.get("car2_name", "SAĞ TƏRƏF"), 1110, fill=WHITE)
    centered(draw, "POSTA BAX, TƏRƏFİNİ SEÇ", 1320, 54, MUTED)
    footer(draw)
    img.save(path, quality=94)


def story_daily_question(path, data):
    img, draw = base_card()
    rect_text(draw, "SƏN QƏRAR VER", 610, 88)
    centered(draw, data.get("battle_title", "AVTO DÖYÜŞÜ"), 810, 86, RED)
    centered(draw, "MARKA?", 990, 82, WHITE)
    centered(draw, "TEXNOLOGİYA?", 1100, 82, WHITE)
    centered(draw, "SÜRÜŞ HİSSİ?", 1210, 82, WHITE)
    centered(draw, "CAVABI ŞƏRHƏ YAZ", 1390, 58, MUTED)
    footer(draw)
    img.save(path, quality=94)


def render_story_campaign(output_dir, email="islammuradov1@icloud.com", daily_data=None):
    os.makedirs(output_dir, exist_ok=True)
    stories = {
        "story1_brand.jpg": story_brand,
        "story2_schedule.jpg": story_schedule,
        "story3_topics.jpg": story_topics,
        "story4_contact.jpg": lambda p: story_contact(p, email),
        "story5_comment.jpg": story_comment,
        "story6_china_germany.jpg": story_china_germany,
        "story7_ev_v8.jpg": story_ev_v8,
        "story8_suv_war.jpg": story_suv_war,
    }
    if daily_data:
        stories["story9_daily_duel.jpg"] = lambda p: story_daily_duel(p, daily_data)
        stories["story10_daily_question.jpg"] = lambda p: story_daily_question(p, daily_data)
    paths = {}
    for name, builder in stories.items():
        path = os.path.join(output_dir, name)
        builder(path)
        paths[name] = path
    return paths


if __name__ == "__main__":
    out = os.environ.get("STORY_OUTPUT_DIR", "output_tests/stories")
    for name, path in render_story_campaign(out).items():
        print(name, path)
