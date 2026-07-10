import os
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

CANVAS_SIZE = (1080, 1350)
FONT_PATH = "BebasNeue-Regular.ttf"

COLOR_WHITE = (255, 255, 255)
COLOR_RED = (229, 9, 20) # A strong, automotive red
COLOR_DARK = (15, 15, 15)

def get_font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception:
        print("Warning: BebasNeue-Regular.ttf not found. Falling back to default.")
        return ImageFont.load_default()

def create_gradient(width, height, start_opacity=255, end_opacity=0):
    """Creates a black gradient image for the bottom overlay."""
    base = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    top = int(height * 0.4) # Gradient starts halfway down
    for y in range(height):
        if y < top:
            alpha = end_opacity
        else:
            alpha = int(end_opacity + (start_opacity - end_opacity) * ((y - top) / (height - top)))
            # make it exponentially darker at the very bottom
            if y > height * 0.7:
                alpha = min(255, int(alpha * 1.2))
        
        for x in range(width):
            base.putpixel((x, y), (0, 0, 0, alpha))
    return base

def crop_center(pil_img, crop_width, crop_height):
    img_width, img_height = pil_img.size
    return pil_img.crop(((img_width - crop_width) // 2,
                         (img_height - crop_height) // 2,
                         (img_width + crop_width) // 2,
                         (img_height + crop_height) // 2))

def draw_multicolor_text_centered(draw, text, font, canvas_width, start_y, line_spacing=10):
    """
    Draws text wrapped to the canvas width, centering each line.
    Words wrapped in * are painted RED, otherwise WHITE.
    """
    words = text.split()
    
    # Process words to identify colors
    processed_words = []
    for w in words:
        if w.startswith('*') and w.endswith('*') and len(w) > 2:
            processed_words.append({"text": w[1:-1].upper(), "color": COLOR_RED})
        else:
            # handle cases where punctuation is outside the star
            clean_word = w.upper()
            color = COLOR_WHITE
            if '*' in clean_word:
                clean_word = clean_word.replace('*', '')
                color = COLOR_RED
            processed_words.append({"text": clean_word, "color": color})
            
    # Wrap lines
    lines = []
    current_line = []
    current_width = 0
    space_width = draw.textlength(" ", font=font)
    
    max_text_width = canvas_width - 100 # 50px margin on each side
    
    for item in processed_words:
        word_w = draw.textlength(item["text"], font=font)
        if current_width + word_w > max_text_width and current_line:
            lines.append(current_line)
            current_line = [item]
            current_width = word_w + space_width
        else:
            current_line.append(item)
            current_width += word_w + space_width
    
    if current_line:
        lines.append(current_line)
        
    # Draw lines
    y = start_y
    for line in lines:
        # Calculate total width of this line to center it
        line_w = sum([draw.textlength(item["text"], font=font) for item in line]) + space_width * (len(line) - 1)
        x = (canvas_width - line_w) / 2
        
        # Get line height
        _, top, _, bottom = font.getbbox("A")
        line_h = bottom - top
        
        for item in line:
            draw.text((x, y), item["text"], font=font, fill=item["color"])
            x += draw.textlength(item["text"], font=font) + space_width
            
        y += line_h + line_spacing

def render_post(image_path, headline_text, output_path="output/final_post.png"):
    print(f"Rendering image: {image_path}")
    
    # Load and process the hero image
    try:
        hero = Image.open(image_path).convert("RGBA")
    except Exception as e:
        print(f"Failed to open image: {e}")
        return None
        
    # Scale to fill canvas, then crop center
    img_ratio = hero.width / hero.height
    canvas_ratio = CANVAS_SIZE[0] / CANVAS_SIZE[1]
    
    if img_ratio > canvas_ratio:
        # Image is wider
        new_height = CANVAS_SIZE[1]
        new_width = int(new_height * img_ratio)
    else:
        # Image is taller
        new_width = CANVAS_SIZE[0]
        new_height = int(new_width / img_ratio)
        
    hero = hero.resize((new_width, new_height), Image.Resampling.LANCZOS)
    hero = crop_center(hero, CANVAS_SIZE[0], CANVAS_SIZE[1])
    
    # Create the dark gradient overlay at the bottom
    gradient = create_gradient(CANVAS_SIZE[0], CANVAS_SIZE[1], start_opacity=240, end_opacity=0)
    hero.alpha_composite(gradient)
    
    # Setup drawing
    draw = ImageDraw.Draw(hero)
    
    # Draw Author Logo placeholder
    # Let's draw a nice "C" logo for Cars
    logo_y = 800
    draw.ellipse([(CANVAS_SIZE[0]//2 - 30, logo_y), (CANVAS_SIZE[0]//2 + 30, logo_y+60)], outline=COLOR_RED, width=5)
    f_logo = get_font(40)
    draw.text((CANVAS_SIZE[0]//2 - 12, logo_y + 10), "C", font=f_logo, fill=COLOR_WHITE)
    
    f_handle = get_font(30)
    draw.text((CANVAS_SIZE[0]//2 - 15, logo_y + 70), "@Cars", font=f_handle, fill=COLOR_WHITE)
    
    # Draw Headline
    f_headline = get_font(110)
    draw_multicolor_text_centered(draw, headline_text, f_headline, CANVAS_SIZE[0], start_y=950, line_spacing=5)
    
    # Draw "SWIPE FOR MORE"
    f_swipe = get_font(35)
    swipe_text = "SWIPE FOR MORE \u2192"
    swipe_w = draw.textlength(swipe_text, font=f_swipe)
    draw.text(((CANVAS_SIZE[0] - swipe_w)/2, 1280), swipe_text, font=f_swipe, fill=COLOR_WHITE)
    
    # Save final
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    hero.convert("RGB").save(output_path)
    print(f"Post successfully generated at: {output_path}")
    return output_path

if __name__ == "__main__":
    if not os.path.exists("assets/latest_car.jpg"):
        # Make a dummy image
        img = Image.new('RGB', (1080, 1350), color=(40, 40, 40))
        os.makedirs("assets", exist_ok=True)
        img.save("assets/latest_car.jpg")
        
    render_post("assets/latest_car.jpg", "MCMURTRY'S *HYPERCAR* IS *FINALLY* HERE & COSTS *$1.3* *MILLION*")
