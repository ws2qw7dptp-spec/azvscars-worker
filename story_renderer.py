import hashlib
import os
import random
from datetime import datetime, timedelta, timezone

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
BLACK = (4, 7, 10)
INK = (9, 13, 18)
CARD = (18, 24, 31)
CARD_2 = (25, 31, 40)
WHITE = (248, 250, 252)
MUTED = (168, 177, 189)
RED = (230, 20, 28)
ORANGE = (255, 105, 32)
LINE = (58, 69, 82)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def font(size):
    for name in ["Anton-Regular.ttf", "BarlowCondensed-Bold.ttf", "Oswald-Bold.ttf"]:
        try:
            return ImageFont.truetype(os.path.join(BASE_DIR, name), size)
        except Exception:
            pass
    return ImageFont.load_default()


def baku_day_key():
    return (datetime.now(timezone.utc) + timedelta(hours=4)).strftime("%Y-%m-%d")


def rng_for(suffix, data=None):
    title = (data or {}).get("battle_title") or ""
    seed = hashlib.sha256(f"{baku_day_key()}|{suffix}|{title}".encode("utf-8")).hexdigest()
    return random.Random(seed)


def pick(items, suffix, data=None):
    return rng_for(suffix, data).choice(items)


def text_width(draw, text, fnt):
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0]


def fit_font(draw, text, max_width, start_size, min_size=32):
    size = start_size
    while size > min_size and text_width(draw, text, font(size)) > max_width:
        size -= 2
    return font(size)


def draw_center(draw, text, y, size, fill=WHITE, max_width=900):
    fnt = fit_font(draw, text, max_width, size)
    draw.text((W // 2, y), text, font=fnt, fill=fill, anchor="mm")


def draw_center_at(draw, text, x, y, size, fill=WHITE, max_width=220):
    fnt = fit_font(draw, text, max_width, size)
    draw.text((x, y), text, font=fnt, fill=fill, anchor="mm")


def wrap_words(draw, text, max_width, size):
    words = str(text).split()
    lines, current = [], ""
    fnt = font(size)
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and text_width(draw, candidate, fnt) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines[:4]


def draw_wrapped_center(draw, text, y, size=74, fill=WHITE, max_width=860, line_gap=1.12):
    lines = wrap_words(draw, text, max_width, size)
    line_height = int(size * line_gap)
    start_y = y - (len(lines) - 1) * line_height // 2
    for index, line in enumerate(lines):
        draw_center(draw, line, start_y + index * line_height, size, fill, max_width)


def rounded_text(draw, xy, text, size=52, fill=WHITE, bg=CARD, pad_x=24, pad_y=16):
    x, y = xy
    fnt = font(size)
    box = draw.textbbox((0, 0), text, font=fnt)
    tw, th = box[2] - box[0], box[3] - box[1]
    draw.rounded_rectangle(
        [x, y, x + tw + pad_x * 2, y + th + pad_y * 2],
        radius=24,
        fill=bg,
        outline=(42, 52, 65),
        width=2,
    )
    draw.text((x + pad_x, y + pad_y - 2), text, font=fnt, fill=fill)


def base_card():
    img = Image.new("RGB", (W, H), BLACK)
    draw = ImageDraw.Draw(img)

    for y in range(H):
        alpha = y / H
        r = int(5 * (1 - alpha) + 14 * alpha)
        g = int(9 * (1 - alpha) + 16 * alpha)
        b = int(13 * (1 - alpha) + 21 * alpha)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    draw.ellipse([-260, -210, 430, 480], fill=(95, 12, 18))
    draw.ellipse([710, 1300, 1280, 2050], fill=(62, 8, 12))
    draw.rounded_rectangle([58, 70, W - 58, H - 86], radius=56, outline=(31, 41, 54), width=3)
    draw.rounded_rectangle([84, 96, 996, 1838], radius=42, outline=(16, 24, 33), width=1)

    # Subtle grid texture; low contrast so screenshots stay clean.
    for x in range(120, W, 180):
        draw.line([(x, 150), (x, H - 160)], fill=(9, 15, 22), width=1)
    for y in range(250, H - 150, 170):
        draw.line([(100, y), (W - 100, y)], fill=(9, 15, 22), width=1)

    return img, draw


def logo(draw):
    draw.ellipse([92, 94, 194, 196], outline=RED, width=5)
    draw.ellipse([102, 104, 184, 186], outline=ORANGE, width=3)
    draw_center_at(draw, "VS", 143, 146, 38, WHITE, max_width=70)
    draw.text((214, 104), "AZVSCARS", font=font(44), fill=WHITE)
    draw.text((216, 151), "Azerbaijan car media", font=font(26), fill=MUTED)


def footer(draw, line="Cavab ver, sonra reel-də davamını gör."):
    draw.rounded_rectangle([106, 1668, W - 106, 1796], radius=34, fill=(13, 18, 25), outline=(42, 52, 65), width=2)
    draw.text((138, 1692), "@azvscars", font=font(40), fill=WHITE)
    cta_font = fit_font(draw, line, 555, 28, min_size=22)
    draw.text((138, 1744), line, font=cta_font, fill=MUTED)
    draw.rounded_rectangle([752, 1710, 948, 1762], radius=26, fill=RED)
    draw_center_at(draw, "FOLLOW", 850, 1737, 34, WHITE, max_width=150)


def hero_title(draw, kicker, title, subtitle=None):
    rounded_text(draw, (108, 302), kicker, 36, WHITE, bg=(145, 14, 20), pad_x=22, pad_y=12)
    draw_wrapped_center(draw, title, 610, size=104, fill=WHITE, max_width=860, line_gap=1.0)
    if subtitle:
        draw_wrapped_center(draw, subtitle, 810, size=44, fill=MUTED, max_width=820, line_gap=1.22)


def option_card(draw, y, text, accent=RED):
    draw.rounded_rectangle([126, y, W - 126, y + 116], radius=26, fill=CARD, outline=(48, 58, 72), width=2)
    draw.rounded_rectangle([126, y, 148, y + 116], radius=12, fill=accent)
    draw_center(draw, text, y + 61, 52, WHITE, max_width=720)


def story_brand(path, data=None):
    data = data or {}
    img, draw = base_card()
    logo(draw)
    hooks = [
        "35 000 AZN OLSA, HANSI 10 IL GEDER?",
        "BAKIDA HANSI MAŞIN DAHA AĞILLI SEÇİMDİR?",
        "USTA SEÇDİYİ MAŞIN HƏMİŞƏ POPULYAR OLMUR.",
        "1 IL SONRA HANSI DAHA RAHAT SATILAR?",
        "BU DEAL REALDIR, YOXSA TUZAQ?",
    ]
    hook = pick(hooks, "brand", data)
    hero_title(draw, "BUGÜNÜN AVTO SUALI", hook, "Səs verən yox, səbəb yazan adamın cavabı növbəti reel-i dəyişir.")
    option_card(draw, 1030, "ALARDIM", RED)
    option_card(draw, 1180, "KEÇƏRDİM", ORANGE)
    footer(draw, "Story-də cavab ver, reel-də səbəbini yoxlayaq.")
    img.save(path, quality=96)


def story_schedule(path, data=None):
    img, draw = base_card()
    logo(draw)
    hero_title(draw, "REAL SISTEM", "POST PLANI", "Az paylaşım, daha güclü slotlar. Feed limiti: gündə maksimum 2 post.")
    rows = [
        "B.E. 15:10  Alıcı seçimi",
        "Ç.axş. 13:20 Market  +  19:10 Debat",
        "C. 12:40 Müqayisə  +  23:00 Supercar",
        "Cümə axş. 12:20 Market  +  20:30 Supercar",
        "C. 13:30 Debat  +  22:30 Supercar",
        "Story: 08:45 / 14:30 / 20:45",
    ]
    y = 930
    for index, row in enumerate(rows):
        option_card(draw, y + index * 118, row, RED if index < 5 else ORANGE)
    footer(draw, "Bakı vaxtı ilə. Hər slot ayrıca mövzu üçündür.")
    img.save(path, quality=96)


def story_topics(path, data=None):
    data = data or {}
    img, draw = base_card()
    logo(draw)
    topics = [
        "Qiymət ucuzdur, amma servis bahadır?",
        "Az yanacaq, yoxsa rahat satış?",
        "Kreditə almağa dəyər, yoxsa gözləmək lazımdır?",
        "Premium görünüş, yoxsa problem çıxarmayan motor?",
        "Bakı tıxacında hansı daha ağıllıdır?",
    ]
    topic = pick(topics, "topics", data)
    hero_title(draw, "REEL ÜÇÜN MÖVZU", topic, "Bir maşın yox, real sahiblik qərarı müzakirə olunur.")
    option_card(draw, 1040, "QİYMƏT", RED)
    option_card(draw, 1190, "SERVIS", ORANGE)
    option_card(draw, 1340, "SATIS", RED)
    footer(draw, "Sənin cavabın növbəti müqayisəni seçə bilər.")
    img.save(path, quality=96)


def story_contact(path, email="islammuradov1@icloud.com", data=None):
    img, draw = base_card()
    logo(draw)
    hero_title(draw, "COLLAB / GÖNDƏR", "MAŞININ VAR?", "Yaxşı görüntü, düzgün məlumat və real qiymət varsa AZVSCARS story/reel formatına düşə bilər.")
    rows = [
        "Model, il, motor, yürüş",
        "Real AZN qiymət və şəhər",
        "Full maşın görüntüsü, insan yox",
        "Salon / servis / event üçün DM",
    ]
    for index, row in enumerate(rows):
        option_card(draw, 990 + index * 132, row, RED if index % 2 == 0 else ORANGE)
    draw_center(draw, email, 1552, 38, MUTED, max_width=820)
    footer(draw, "DM açıqdır. Göndər, uyğun olsa paylaşaq.")
    img.save(path, quality=96)


def story_comment(path, data=None):
    img, draw = base_card()
    logo(draw)
    hero_title(draw, "ŞƏRH QAYDASI", "1 SÖZLÜK CAVAB YOX.", "BMW, Audi, BYD yazıb çıxmaq yox. Seçimini real səbəblə müdafiə et.")
    option_card(draw, 1030, "Niyə daha etibarlıdır?", RED)
    option_card(draw, 1180, "Niyə daha rahat satılar?", ORANGE)
    option_card(draw, 1330, "Niyə xərcə dəyər?", RED)
    footer(draw, "Ən güclü səbəb növbəti story-də paylaşılır.")
    img.save(path, quality=96)


def story_china_germany(path, data=None):
    img, draw = base_card()
    logo(draw)
    hero_title(draw, "ÇİN vs ALMAN", "BİRİ TEXNOLOGİYA, BİRİ ETİBAR İDDİASI.", "Bakı alıcısı üçün sual sadədir: 3 il sonra hansını daha rahat saxlayarsan?")
    option_card(draw, 1040, "ÇİN: yeni tech + zəmanət", RED)
    option_card(draw, 1190, "ALMAN: marka + ikinci əl", ORANGE)
    option_card(draw, 1340, "Sən hansına pul qoyardın?", RED)
    footer(draw, "Cavabı story-də ver, səbəbi şərhdə yaz.")
    img.save(path, quality=96)


def story_ev_v8(path, data=None):
    img, draw = base_card()
    logo(draw)
    hero_title(draw, "EV vs MOTOR SƏSİ", "SÜRƏT HƏR ŞEYDİR?", "Elektrik sakit və sürətlidir. Amma bəziləri üçün maşın hissi səsdən başlayır.")
    option_card(draw, 1040, "EV: sakit, sürətli, modern", RED)
    option_card(draw, 1190, "V8: səs, hiss, xarakter", ORANGE)
    option_card(draw, 1340, "Gündəlik sürüşdə hansını seçərdin?", RED)
    footer(draw, "Səs ver. Fanat cavabları növbəti reel-ə gedir.")
    img.save(path, quality=96)


def story_suv_war(path, data=None):
    img, draw = base_card()
    logo(draw)
    hero_title(draw, "SUV SEÇİMİ", "STATUS YOXSA BAŞ AĞRITMAYAN MAŞIN?", "Bakı yolları, ailə, servis və satış: real seçim bunların hamısıdır.")
    option_card(draw, 1040, "Land Cruiser / Lexus: rahat saxlanma", RED)
    option_card(draw, 1190, "G-Class / Range: status və risk", ORANGE)
    option_card(draw, 1340, "Sən pulunu hansına bağlayardın?", RED)
    footer(draw, "Dostuna göndər, cavabını soruş.")
    img.save(path, quality=96)


def story_daily_duel(path, data):
    data = data or {}
    img, draw = base_card()
    logo(draw)
    car1 = data.get("car1_name", "SOL TƏRƏF")
    car2 = data.get("car2_name", "SAĞ TƏRƏF")
    hero_title(draw, "BUGÜN REELDƏ", "İKİ SEÇİM, BİR REAL QƏRAR.", "Poll kimi cavabla. Sonra postda səbəbini yaz.")
    option_card(draw, 1010, f"SOL: {car1}", RED)
    option_card(draw, 1170, f"SAĞ: {car2}", ORANGE)
    draw_center(draw, "HANSI REAL HƏYATDA DAHA MƏNTİQLİDİR?", 1400, 52, WHITE, max_width=820)
    footer(draw, "Reel gələndə şərhdə 1 ciddi səbəb yaz.")
    img.save(path, quality=96)


def story_daily_question(path, data):
    data = data or {}
    img, draw = base_card()
    logo(draw)
    questions = [
        "Bu büdcə səndə olsa, hansı riskə girərdin?",
        "Hansı 1 il sonra daha rahat satılar?",
        "Hansı ailə üçün daha ağıllıdır?",
        "Hansı servis xərcində səni yormaz?",
        "Hansı real Bakı sürüşündə daha məntiqlidir?",
    ]
    question = pick(questions, "daily-question", data)
    title = data.get("battle_title", "AVTO SECIM")
    hero_title(draw, "SƏN QƏRAR VER", title, question)
    option_card(draw, 1050, "QİYMƏT", RED)
    option_card(draw, 1200, "ETİBAR", ORANGE)
    option_card(draw, 1350, "SATIŞ", RED)
    footer(draw, "Cavabını story-də ver, dostuna da göndər.")
    img.save(path, quality=96)


def render_story_campaign(output_dir, email="islammuradov1@icloud.com", daily_data=None):
    os.makedirs(output_dir, exist_ok=True)
    daily_data = daily_data or {}
    stories = {
        "story1_brand.jpg": lambda p: story_brand(p, daily_data),
        "story2_schedule.jpg": lambda p: story_schedule(p, daily_data),
        "story3_topics.jpg": lambda p: story_topics(p, daily_data),
        "story4_contact.jpg": lambda p: story_contact(p, email, daily_data),
        "story5_comment.jpg": lambda p: story_comment(p, daily_data),
        "story6_china_germany.jpg": lambda p: story_china_germany(p, daily_data),
        "story7_ev_v8.jpg": lambda p: story_ev_v8(p, daily_data),
        "story8_suv_war.jpg": lambda p: story_suv_war(p, daily_data),
        "story9_daily_duel.jpg": lambda p: story_daily_duel(p, daily_data),
        "story10_daily_question.jpg": lambda p: story_daily_question(p, daily_data),
    }
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
