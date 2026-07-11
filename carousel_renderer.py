import os
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

# ─── Canvas & Style Constants ──────────────────────────────────────────────────
CANVAS_W, CANVAS_H  = 1080, 1350
CANVAS_SIZE          = (CANVAS_W, CANVAS_H)
HALF_W               = CANVAS_W // 2

# Zones (vertical)
ZONE_TOP_BADGE  = 160          # y-center of the red title badge
ZONE_CAR_TOP    = 280          # top of the visible car area
ZONE_CAR_BOT    = 1100         # bottom of the visible car area
ZONE_STAT       = 1030         # y-center of stat badges (in dark gradient)
ZONE_NAME       = 1200         # y-top of car name text

# BarlowCondensed-Bold.ttf — local font file with full Azerbaijani support
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(BASE_DIR, "BarlowCondensed-Bold.ttf")

COLOR_WHITE    = (255, 255, 255)
COLOR_RED      = (229,   9,  20)
COLOR_DARK     = ( 15,  15,  15)
COLOR_BADGE_BG = ( 15,  15,  15, 235)

# ─── Font Helpers ──────────────────────────────────────────────────────────────

def get_font(size: int):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception:
        return ImageFont.load_default()

def font_height(font) -> int:
    _, top, _, bottom = font.getbbox("A")
    return bottom - top

def fit_font(draw, text: str, max_w: int, start: int, min_sz: int = 18):
    """Shrink font until text fits within max_w pixels."""
    sz = start
    f  = get_font(sz)
    while draw.textlength(text, font=f) > max_w and sz > min_sz:
        sz -= 2
        f   = get_font(sz)
    return f

# ─── Image Processing ──────────────────────────────────────────────────────────

def enhance(img: Image.Image) -> Image.Image:
    img = ImageEnhance.Color(img).enhance(1.3)
    img = ImageEnhance.Contrast(img).enhance(1.15)
    img = ImageEnhance.Sharpness(img).enhance(1.2)
    return img

def make_half(pil_img: Image.Image, flip: bool) -> Image.Image:
    """
    Creates a 540×1350 panel:
      - Background = blurred + darkened stretch of the image (fills the panel)
      - Foreground = whole car scaled to fit width=540, vertically centred in
        the CAR ZONE so it sits above the stat/name area.

    flip=True  → car faces LEFT  (left panel,  front outward)
    flip=False → car faces RIGHT (right panel, front outward)
    """
    if flip:
        pil_img = pil_img.transpose(Image.FLIP_LEFT_RIGHT)

    img_w, img_h = pil_img.size
    img_ratio    = img_w / img_h

    # ── Background (blurred) ──────────────────────────────────────────────────
    target_ratio = HALF_W / CANVAS_H
    if img_ratio > target_ratio:
        bh = CANVAS_H
        bw = int(bh * img_ratio)
    else:
        bw = HALF_W
        bh = int(bw / img_ratio)

    bg = pil_img.resize((bw, bh), Image.Resampling.LANCZOS)
    lx = (bw - HALF_W) // 2
    ty = (bh - CANVAS_H) // 2
    bg = bg.crop((lx, ty, lx + HALF_W, ty + CANVAS_H))
    
    # PERFORMANCE OPTIMIZATION: Downscale before heavy Gaussian blur, then upscale
    blur_scale = 4
    bg_small = bg.resize((HALF_W // blur_scale, CANVAS_H // blur_scale), Image.Resampling.NEAREST)
    bg_small = bg_small.filter(ImageFilter.GaussianBlur(10)) # 40 / 4 = 10
    bg = bg_small.resize((HALF_W, CANVAS_H), Image.Resampling.LANCZOS)
    
    bg = ImageEnhance.Brightness(bg).enhance(0.35)

    # ── Foreground (whole car, fits width) ───────────────────────────────────
    fg_w = HALF_W
    fg_h = int(fg_w / img_ratio)

    # Car zone height (where the car should sit)
    car_zone_h = ZONE_CAR_BOT - ZONE_CAR_TOP
    # If car is taller than the zone, scale it down
    if fg_h > car_zone_h:
        fg_h = car_zone_h
        fg_w = int(fg_h * img_ratio)

    fg   = pil_img.resize((fg_w, fg_h), Image.Resampling.LANCZOS)

    # Centre the car in the car zone horizontally and vertically
    fg_x = (HALF_W - fg_w) // 2
    fg_y = ZONE_CAR_TOP + (car_zone_h - fg_h) // 2

    if fg.mode == "RGBA":
        bg.paste(fg, (fg_x, fg_y), fg)
    else:
        bg.paste(fg, (fg_x, fg_y))

    return bg

# ─── Gradient Overlay ──────────────────────────────────────────────────────────

def gradient_overlay(width: int, height: int, direction: str = "bottom",
                     start_pct: float = 0.55, max_alpha: int = 255) -> Image.Image:
    out  = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(out)
    if direction == "bottom":
        b = int(height * start_pct)
        for y in range(b, height):
            a = int(max_alpha * min(1.0, (y - b) / max(1, height - b) * 1.6))
            draw.line([(0, y), (width, y)], fill=(0, 0, 0, a))
    elif direction == "top":
        b = int(height * start_pct)
        for y in range(b):
            a = int(max_alpha * (1 - y / max(1, b)))
            draw.line([(0, y), (width, y)], fill=(0, 0, 0, min(255, a)))
    return out

# ─── Base Split-Screen Builder ─────────────────────────────────────────────────

def build_split_base(img_path1: str, img_path2: str) -> Image.Image:
    """
    Left  panel = car1, FLIPPED so its front faces LEFT  (outward)
    Right panel = car2, NOT flipped so its front faces RIGHT (outward)
    """
    base = Image.new("RGBA", CANVAS_SIZE, COLOR_DARK)
    try:
        img1 = Image.open(img_path1).convert("RGBA")
        img2 = Image.open(img_path2).convert("RGBA")
    except Exception as e:
        print(f"  ⚠️  Image load error: {e}")
        return base

    img1 = enhance(img1)
    img2 = enhance(img2)

    half1 = make_half(img1, flip=True)   # front faces LEFT  (outward)
    half2 = make_half(img2, flip=False)  # front faces RIGHT (outward)

    base.paste(half1, (0, 0))
    base.paste(half2, (HALF_W, 0))

    # Gradient: heavy bottom fade into dark (stat area), light top fade
    base.alpha_composite(gradient_overlay(CANVAS_W, CANVAS_H, "bottom", 0.58, 255))
    base.alpha_composite(gradient_overlay(CANVAS_W, CANVAS_H, "top",    0.20, 200))

    # Feathered center shadow + sharp red divider
    draw     = ImageDraw.Draw(base)
    # The black gradient in the middle
    for x in range(HALF_W - 40, HALF_W + 40):
        dist = abs(x - HALF_W)
        alpha = int(255 * (1 - dist / 40))
        draw.line([(x, 0), (x, CANVAS_H)], fill=(0, 0, 0, alpha))
    # Middle thin red line
    draw.rectangle([HALF_W - 2, 0, HALF_W + 2, CANVAS_H], fill=COLOR_RED)

    return base

# ─── Drawing Primitives ────────────────────────────────────────────────────────

def draw_badge(draw, text: str, cx: int, cy: int, max_w: int, sz: int,
               bg=COLOR_BADGE_BG, fg=COLOR_WHITE, pad=20):
    """Badge centred at (cx, cy). Auto-shrinks to stay within max_w."""
    f = fit_font(draw, text, max_w - pad * 2, sz)
    bbox = draw.textbbox((cx, cy), text, font=f, anchor="mm")
    
    # Optional multiline fallback if it's still way too wide? No, fit_font already shrinks it.
    draw.rectangle([bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad], fill=bg)
    draw.text((cx, cy), text, font=f, fill=fg, anchor="mm")

def draw_vs_circle(draw, cy: int, include_vs=True):
    """VS circle centred on the red divider at vertical position cy."""
    if include_vs:
        draw.ellipse([HALF_W - 32, cy - 32, HALF_W + 32, cy + 32], fill=(0,0,0), outline=COLOR_RED, width=3)
        vs_font = get_font(36)
        draw.text((HALF_W, cy), "VS", font=vs_font, fill=COLOR_WHITE, anchor="mm")

def draw_car_name(draw, name: str, panel: str):
    """Draw a car name label centred in its panel at the bottom."""
    safe_w = HALF_W - 60
    f      = fit_font(draw, name, safe_w, 54)
    tw     = draw.textlength(name, font=f)
    th     = font_height(f)
    y      = ZONE_NAME
    if panel == "left":
        x = (HALF_W - tw) / 2
    else:
        x = HALF_W + (HALF_W - tw) / 2
    # Subtle dark background behind name
    pad = 12
    draw.rectangle([x - pad, y - pad, x + tw + pad, y + th + pad],
                   fill=(0, 0, 0, 160))
    draw.text((x, y), name, font=f, fill=COLOR_WHITE)

def draw_centered(draw, text: str, f, y: int, color=COLOR_WHITE):
    tw = draw.textlength(text, font=f)
    draw.text(((CANVAS_W - tw) / 2, y), text, font=f, fill=color)

# ─── Slide Builders ────────────────────────────────────────────────────────────

def build_cover_slide(base: Image.Image, data: dict, out: str):
    """Slide 1 – title badge + VS circle + car names."""
    img = base.copy()
    img.alpha_composite(Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 70)))
    draw = ImageDraw.Draw(img)

    # Red title badge at top
    title = data.get("battle_title", "GÜNÜN MÜQAYİSƏSİ")
    draw_badge(draw, title, CANVAS_W // 2, ZONE_TOP_BADGE,
               max_w=940, sz=88, bg=COLOR_RED)

    # Small conversion cue: visible on the first slide without crowding the grid.
    f_hook = get_font(44)
    draw_centered(draw, "ŞƏRHDƏ TƏRƏFİNİ SEÇ", f_hook, ZONE_TOP_BADGE + 105, (230, 230, 230))

    # VS circle at vertical mid-point of car zone
    vs_y = (ZONE_CAR_TOP + ZONE_CAR_BOT) // 2
    draw_vs_circle(draw, vs_y)

    # Car names
    draw_car_name(draw, data["car1_name"], "left")
    draw_car_name(draw, data["car2_name"], "right")

    img.convert("RGB").save(out)


def build_stat_slide(base: Image.Image, title: str,
                     stat1: str, stat2: str,
                     name1: str, name2: str, out: str):
    """Slides 2-4 – title badge + stat badges below cars + VS circle + names."""
    img = base.copy()
    img.alpha_composite(Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 110)))
    draw = ImageDraw.Draw(img)

    # Red title badge at top
    draw_badge(draw, title, CANVAS_W // 2, ZONE_TOP_BADGE,
               max_w=940, sz=80, bg=COLOR_RED)

    # VS circle between the two stat badges (below the cars)
    draw_vs_circle(draw, ZONE_STAT)

    # Stat badges — each constrained to their half, horizontally centred
    half_max_w = HALF_W - 50
    draw_badge(draw, stat1, HALF_W // 2, ZONE_STAT,
               max_w=half_max_w, sz=78)
    draw_badge(draw, stat2, HALF_W + HALF_W // 2, ZONE_STAT,
               max_w=half_max_w, sz=78)

    # Car names
    draw_car_name(draw, name1, "left")
    draw_car_name(draw, name2, "right")

    img.convert("RGB").save(out)


def build_outro_slide(base: Image.Image, out: str):
    """Slide 5 – CTA with the current four-post daily schedule."""
    img = base.copy()
    img.alpha_composite(Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 215)))
    draw = ImageDraw.Draw(img)

    # @azvscars account label
    f_handle = get_font(60)
    draw_centered(draw, "@azvscars", f_handle, 320, (200, 200, 200))

    # Big CTA
    f_cta = get_font(122)
    draw_centered(draw, "TƏRƏFİNİ SEÇ!", f_cta, 430, COLOR_WHITE)

    # Divider line
    draw.line([(120, 585), (CANVAS_W - 120, 585)], fill=COLOR_RED, width=3)

    # Schedule
    f_label = get_font(58)
    draw_centered(draw, "HƏR GÜN 4 AVTO DÖYÜŞ", f_label, 625, (210, 210, 210))

    f_time = get_font(82)
    draw_centered(draw, "09:00  /  13:00", f_time, 720, COLOR_RED)
    draw_centered(draw, "19:30  /  22:45", f_time, 810, COLOR_RED)

    f_zone = get_font(44)
    draw_centered(draw, "BAKI VAXTI İLƏ", f_zone, 910, (160, 160, 160))

    img.convert("RGB").save(out)

# ─── Main Orchestrator ─────────────────────────────────────────────────────────

def render_carousel(data: dict, img_path1: str, img_path2: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    print("  Building split-screen base…")
    base = build_split_base(img_path1, img_path2)

    build_cover_slide(base, data, os.path.join(output_dir, "slide1_cover.png"))
    print("  ✅ Slide 1: Cover")

    build_stat_slide(base,
                     data["slide2_title"],
                     data["slide2_car1_stat"], data["slide2_car2_stat"],
                     data["car1_name"],        data["car2_name"],
                     os.path.join(output_dir, "slide2_power.png"))
    print("  ✅ Slide 2: Engine / Power")

    build_stat_slide(base,
                     data["slide3_title"],
                     data["slide3_car1_stat"], data["slide3_car2_stat"],
                     data["car1_name"],        data["car2_name"],
                     os.path.join(output_dir, "slide3_speed.png"))
    print("  ✅ Slide 3: Speed")

    build_stat_slide(base,
                     data["slide4_title"],
                     data["slide4_car1_stat"], data["slide4_car2_stat"],
                     data["car1_name"],        data["car2_name"],
                     os.path.join(output_dir, "slide4_price.png"))
    print("  ✅ Slide 4: Price")

    build_outro_slide(base, os.path.join(output_dir, "slide5_outro.png"))
    print("  ✅ Slide 5: Outro / CTA")
