from PIL import Image, ImageDraw, ImageFont
import os
BASE_DIR = os.path.dirname(os.path.abspath('app.py'))
font = ImageFont.truetype(os.path.join(BASE_DIR, 'BarlowCondensed-Bold.ttf'), 60)
img = Image.new('RGB', (800, 200), (0,0,0))
draw = ImageDraw.Draw(img)
cx, cy = 400, 100
bbox = draw.textbbox((cx, cy), "MÜHƏRRİK VƏ GÜC", font=font, anchor="mm")
pad = 20
draw.rectangle([bbox[0]-pad, bbox[1]-pad, bbox[2]+pad, bbox[3]+pad], fill=(229,9,20))
draw.text((cx, cy), "MÜHƏRRİK VƏ GÜC", font=font, fill=(255,255,255), anchor="mm")
img.save('test_font.jpg')
print("Success")
