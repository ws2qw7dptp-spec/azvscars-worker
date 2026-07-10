import os
import json
import tempfile
import cv2
from dotenv import load_dotenv

# Load local environment variables
load_dotenv()

from ai_comparison import generate_comparison
from image_fetcher import fetch_wikipedia_image
import reel_renderer
from PIL import Image, ImageDraw
import gc
from carousel_renderer import (
    enhance, make_half, gradient_overlay,
    build_cover_slide, build_stat_slide, build_outro_slide,
    CANVAS_SIZE, CANVAS_W, CANVAS_H, HALF_W, COLOR_DARK, COLOR_RED,
)

def local_render(data, img1_path, img2_path, flip1, flip2, tmp_dir):
    base = Image.new("RGBA", CANVAS_SIZE, COLOR_DARK)
    img1 = enhance(Image.open(img1_path).convert("RGBA"))
    img2 = enhance(Image.open(img2_path).convert("RGBA"))
    base.paste(make_half(img1, flip=flip1), (0, 0))
    base.paste(make_half(img2, flip=flip2), (HALF_W, 0))
    base.alpha_composite(gradient_overlay(CANVAS_W, CANVAS_H, "bottom", 0.58, 255))
    base.alpha_composite(gradient_overlay(CANVAS_W, CANVAS_H, "top",    0.20, 200))

    draw = ImageDraw.Draw(base)
    for x in range(60):
        a = int(200 * (1 - x / 60))
        draw.line([(HALF_W - x, 0), (HALF_W - x, CANVAS_H)], fill=(0, 0, 0, a))
        draw.line([(HALF_W + x, 0), (HALF_W + x, CANVAS_H)], fill=(0, 0, 0, a))
    draw.line([(HALF_W, 0), (HALF_W, CANVAS_H)], fill=COLOR_RED, width=6)

    d = data
    builders = {
        "slide1_cover.png": lambda p: build_cover_slide(base, d, p),
        "slide2_power.png": lambda p: build_stat_slide(
            base, d["slide2_title"],
            d["slide2_car1_stat"], d["slide2_car2_stat"],
            d["car1_name"], d["car2_name"], p),
        "slide3_speed.png": lambda p: build_stat_slide(
            base, d["slide3_title"],
            d["slide3_car1_stat"], d["slide3_car2_stat"],
            d["car1_name"], d["car2_name"], p),
        "slide4_price.png": lambda p: build_stat_slide(
            base, d["slide4_title"],
            d["slide4_car1_stat"], d["slide4_car2_stat"],
            d["car1_name"], d["car2_name"], p),
        "slide5_outro.png": lambda p: build_outro_slide(base, p),
    }

    for filename, builder in builders.items():
        local = os.path.join(tmp_dir, filename)
        builder(local)
        gc.collect()

def run_all_cases():
    base_output_dir = "output_tests"
    os.makedirs(base_output_dir, exist_ok=True)
    
    post_types = ["main"]
    
    for pt in post_types:
        print(f"\n=============================================")
        print(f"🔄 TEST CASE: {pt.upper()}")
        print(f"=============================================")
        
        case_dir = os.path.join(base_output_dir, pt)
        os.makedirs(case_dir, exist_ok=True)
        
        # 1. Generate AI Content
        print(f"[{pt}] Generating AI Content...")
        data = generate_comparison(post_type=pt)
        
        # Save JSON data to see the captions
        with open(os.path.join(case_dir, "data.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        print(f"[{pt}] Caption: {data.get('caption')}")
        
        # 2. Fetch Images
        print(f"[{pt}] Fetching images for {data['car1_name']} vs {data['car2_name']}...")
        img1_path = fetch_wikipedia_image(data["car1_search_query"], os.path.join(case_dir, "car1_orig.jpg"))
        img2_path = fetch_wikipedia_image(data["car2_search_query"], os.path.join(case_dir, "car2_orig.jpg"))
        
        if not img1_path or not img2_path:
            print(f"[{pt}] Failed to fetch images. Skipping rendering.")
            continue
            
        # 3. Render Carousel
        print(f"[{pt}] Rendering Carousel Slides...")
        flip1, flip2 = False, True
        local_render(data, img1_path, img2_path, flip1, flip2, case_dir)
        
        slide_paths = []
        for key in ["slide1_cover.png", "slide2_power.png", "slide3_speed.png", "slide4_price.png", "slide5_outro.png"]:
            sp = os.path.join(case_dir, key)
            if os.path.exists(sp):
                slide_paths.append(sp)
                
        # 4. Render Reel
        if slide_paths:
            print(f"[{pt}] Rendering Reel Video...")
            reel_path = os.path.join(case_dir, "reel.mp4")
            try:
                reel_renderer.render_reel(slide_paths, reel_path)
                print(f"[{pt}] ✅ Successfully created reel at {reel_path}")
            except Exception as e:
                print(f"[{pt}] ❌ Failed to create reel: {e}")
                
        print(f"[{pt}] Done. Check the '{case_dir}' folder.")

if __name__ == "__main__":
    run_all_cases()
