import os
import sys
import uuid
import time
import json
import argparse
import tempfile
import threading
import requests as http_req
from dotenv import load_dotenv

load_dotenv()

# Project imports
from ai_comparison import generate_comparison
from image_fetcher import fetch_wikipedia_image
import cloudflare_storage as cf
import reel_renderer
from carousel_renderer import (
    enhance, make_half, gradient_overlay,
    build_cover_slide, build_stat_slide, build_outro_slide,
    CANVAS_SIZE, CANVAS_W, CANVAS_H, HALF_W, COLOR_DARK, COLOR_RED,
)
from PIL import Image, ImageDraw
import gc

SLIDE_KEYS = [
    "slide1_cover.png", "slide2_power.png", "slide3_speed.png",
    "slide4_price.png", "slide5_outro.png",
]

def render_slides(data, img1_path, img2_path, flip1, flip2, tmp_dir):
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

    paths = []
    for filename, builder in builders.items():
        local = os.path.join(tmp_dir, filename)
        builder(local)
        paths.append(local)
        gc.collect()
    return paths

def is_duplicate(car1, car2):
    """Check KV storage to see if this battle was recently posted."""
    try:
        history = cf.kv_get("history:pairs") or []
        pair = sorted([car1.lower(), car2.lower()])
        if pair in history:
            return True
        return False
    except Exception as e:
        print(f"Warning: Could not check history: {e}")
        return False

def add_to_history(car1, car2):
    try:
        history = cf.kv_get("history:pairs") or []
        pair = sorted([car1.lower(), car2.lower()])
        history.insert(0, pair)
        # Keep last 50 pairs
        history = history[:50]
        cf.kv_put("history:pairs", history)
    except Exception as e:
        print(f"Warning: Could not save history: {e}")

def publish_to_instagram(sid, caption, media_type, reel_url, slide_urls):
    ig_token   = os.environ.get("META_ACCESS_TOKEN", "")
    ig_user_id = os.environ.get("INSTAGRAM_ACCOUNT_ID", "")
    
    if not ig_token or not ig_user_id:
        raise ValueError("Missing META credentials.")
        
    graph_version = os.environ.get("META_GRAPH_VERSION", "v25.0")
    api_base = f"https://graph.facebook.com/{graph_version}/{ig_user_id}"
    
    print(f"Publishing as {media_type} to Instagram...")
    if media_type == "reel":
        r = http_req.post(f"{api_base}/media", params={
            "media_type": "REELS",
            "video_url": reel_url,
            "caption": caption,
            "share_to_feed": "true",
            "access_token": ig_token,
        })
        r.raise_for_status()
        container_id = r.json()["id"]
        
        print("Waiting for Reel processing...")
        while True:
            time.sleep(5)
            status_res = http_req.get(f"https://graph.facebook.com/{graph_version}/{container_id}", params={
                "fields": "status_code",
                "access_token": ig_token
            })
            status_res.raise_for_status()
            status = status_res.json().get("status_code")
            if status == "FINISHED":
                break
            elif status == "ERROR":
                raise Exception("Instagram Reels processing failed (ERROR state).")
                
        r = http_req.post(f"{api_base}/media_publish", params={
            "creation_id": container_id,
            "access_token": ig_token,
        })
        r.raise_for_status()
        print(f"✅ Reel published successfully! Post ID: {r.json().get('id')}")
    else:
        container_ids = []
        for url in slide_urls:
            if not url: continue
            r = http_req.post(f"{api_base}/media", params={
                "image_url": url,
                "is_carousel_item": "true",
                "access_token": ig_token,
            })
            r.raise_for_status()
            container_ids.append(r.json()["id"])
            time.sleep(2)

        r = http_req.post(f"{api_base}/media", params={
            "media_type": "CAROUSEL",
            "children": ",".join(container_ids),
            "caption": caption,
            "access_token": ig_token,
        })
        r.raise_for_status()
        carousel_id = r.json()["id"]

        time.sleep(3)
        r = http_req.post(f"{api_base}/media_publish", params={
            "creation_id": carousel_id,
            "access_token": ig_token,
        })
        r.raise_for_status()
        print(f"✅ Carousel published successfully! Post ID: {r.json().get('id')}")

def run_post(post_type):
    print(f"🚀 Starting automated post pipeline. Type: {post_type.upper()}")
    
    # Intelligently decide media type
    if post_type in ["quick", "war"]:
        media_type = "reel"
        make_reel = True
    else:
        media_type = "carousel"
        make_reel = False
        
    print(f"Target Media Type: {media_type.upper()}")
    
    sid = str(uuid.uuid4())[:8]
    data = None
    
    # Try up to 3 times to get a non-duplicate pair
    for attempt in range(3):
        data = generate_comparison(post_type=post_type)
        if not is_duplicate(data["car1_name"], data["car2_name"]):
            break
        print(f"Duplicate detected ({data['car1_name']} vs {data['car2_name']}), retrying... ({attempt+1}/3)")
        time.sleep(2)
        
    print(f"Versus: {data['car1_name']} VS {data['car2_name']}")
    
    with tempfile.TemporaryDirectory() as tmp:
        # Download
        print("Downloading images...")
        img1_path = fetch_wikipedia_image(data["car1_search_query"], os.path.join(tmp, "car1_orig.jpg"))
        img2_path = fetch_wikipedia_image(data["car2_search_query"], os.path.join(tmp, "car2_orig.jpg"))
        
        if not img1_path or not img2_path:
            raise Exception("Failed to fetch car images. Aborting.")
            
        cf.r2_upload_file(img1_path, f"{sid}/car1_orig.jpg", "image/jpeg")
        cf.r2_upload_file(img2_path, f"{sid}/car2_orig.jpg", "image/jpeg")

        # Render
        print("Rendering slides...")
        flip1, flip2 = False, True
        local_slide_paths = render_slides(data, img1_path, img2_path, flip1, flip2, tmp)
        
        # Upload slides
        slide_urls = []
        for lp in local_slide_paths:
            fname = os.path.basename(lp)
            url = cf.r2_upload_file(lp, f"{sid}/{fname}", "image/png")
            slide_urls.append(url)
            
        reel_url = None
        if make_reel:
            print("Rendering reel...")
            local_reel = os.path.join(tmp, "reel.mp4")
            reel_renderer.render_reel(local_slide_paths, local_reel)
            print("Uploading reel to R2...")
            reel_url = cf.r2_upload_file(local_reel, f"{sid}/reel.mp4", "video/mp4")
            
        caption = data["caption"] + "\n\n" + data.get("hashtags", "")
        
        # Save metadata
        meta = {
            "sid": sid,
            "post_type": post_type,
            "car1_name": data["car1_name"],
            "car2_name": data["car2_name"],
            "flip1": flip1,
            "flip2": flip2,
            "caption": caption,
            "slide_urls": slide_urls,
            "reel_url": reel_url,
            "is_published": False,
            "created_at": time.strftime("%Y-%m-%d %H:%M"),
        }
        cf.session_save(sid, meta)
        
        # Add to history to prevent duplicates
        add_to_history(data["car1_name"], data["car2_name"])
        
        # Publish
        publish_to_instagram(sid, caption, media_type, reel_url, slide_urls)
        meta["is_published"] = True
        meta["published"] = {
            media_type: {
                "published_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
        }
        cf.session_save(sid, meta)
        
        print(f"🎉 Pipeline finished successfully for {sid}!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run automated Instagram post.")
    parser.add_argument("--type", choices=["quick", "main", "war", "night"], required=True, help="Type of post to generate")
    args = parser.parse_args()
    
    try:
        run_post(args.type)
    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
