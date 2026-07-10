import os
from PIL import Image, ImageDraw, ImageFont

CANVAS_SIZE = (1080, 1080)
COLOR_RED = (229, 9, 20)
COLOR_WHITE = (255, 255, 255)
COLOR_DARK = (15, 15, 15)
FONT_PATH = "/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf"

def get_font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except:
        return ImageFont.load_default()

def create_profile_picture():
    img = Image.new('RGB', CANVAS_SIZE, COLOR_DARK)
    draw = ImageDraw.Draw(img)
    
    center = 1080 // 2
    r = 350
    
    # Draw a thin red circle around the edge of the whole image (Instagram crops to circle anyway, but this is a nice touch)
    draw.ellipse([(center - 500, center - 500), (center + 500, center + 500)], outline=(30, 30, 30), width=10)
    
    # Draw the main VS circle
    draw.ellipse([(center - r, center - r), (center + r, center + r)], fill=(0,0,0), outline=COLOR_RED, width=25)
    
    # Draw VS text
    f_vs = get_font(450)
    w = draw.textlength("VS", font=f_vs)
    _, top, _, bottom = f_vs.getbbox("VS")
    h = bottom - top
    
    draw.text((center - w/2, center - h/2 - 20), "VS", font=f_vs, fill=COLOR_WHITE)
    
    # Draw small subtext
    f_sub = get_font(80)
    subtext = "AZVSCARS"
    w_sub = draw.textlength(subtext, font=f_sub)
    draw.text((center - w_sub/2, center + r + 30), subtext, font=f_sub, fill=COLOR_RED)
    
    os.makedirs("output", exist_ok=True)
    out_path = "output/profile_picture.png"
    img.save(out_path)
    print(out_path)

if __name__ == "__main__":
    create_profile_picture()
