"""
worker.py — GitHub Actions Worker
Handles:
  - action=generate: AI comparison -> images -> slides render -> optional reel -> R2 + KV
  - action=flip:     flip a car image and re-render slides
  - action=stories:  render branded story cards -> R2/KV -> optional publish
Called by Cloudflare Functions via workflow_dispatch.
Reports status to Cloudflare KV so frontend can poll /api/status/[sid].
"""
import os, sys, json, uuid, time, tempfile, gc, argparse, base64
import requests as http_req
from dotenv import load_dotenv
load_dotenv()

import cloudflare_storage as cf

SLIDE_KEYS = [
    "slide1_cover.png", "slide2_power.png", "slide3_speed.png",
    "slide4_price.png", "slide5_outro.png",
]

# ─── KV Status Helper ────────────────────────────────────────────────────────

def set_status(sid, status, message):
    """Write status to KV so Cloudflare Function can return it to frontend."""
    try:
        cf.kv_put(f"status_{sid}", json.dumps({"status": status, "message": message, "sid": sid}))
    except Exception as e:
        print(f"[status] KV write failed: {e}")

# ─── Render & Upload Slides ───────────────────────────────────────────────────

def render_and_upload(sid, data, img1_path, img2_path, flip1, flip2, tmp_dir):
    from PIL import Image, ImageDraw
    from carousel_renderer import (
        enhance, make_half, gradient_overlay,
        build_cover_slide, build_stat_slide, build_outro_slide,
        CANVAS_SIZE, CANVAS_W, CANVAS_H, HALF_W, COLOR_DARK, COLOR_RED,
    )

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
            base, d["slide2_title"], d["slide2_car1_stat"], d["slide2_car2_stat"],
            d["car1_name"], d["car2_name"], p),
        "slide3_speed.png": lambda p: build_stat_slide(
            base, d["slide3_title"], d["slide3_car1_stat"], d["slide3_car2_stat"],
            d["car1_name"], d["car2_name"], p),
        "slide4_price.png": lambda p: build_stat_slide(
            base, d["slide4_title"], d["slide4_car1_stat"], d["slide4_car2_stat"],
            d["car1_name"], d["car2_name"], p),
        "slide5_outro.png": lambda p: build_outro_slide(base, p),
    }

    slide_urls = {}
    for filename, builder in builders.items():
        local = os.path.join(tmp_dir, filename)
        builder(local)
        url = cf.r2_upload_file(local, f"{sid}/{filename}", "image/png")
        slide_urls[filename] = url
        gc.collect()

    return slide_urls

def render_local_slides(data, img1_path, img2_path, flip1, flip2, tmp_dir):
    from PIL import Image, ImageDraw
    from carousel_renderer import (
        enhance, make_half, gradient_overlay,
        build_cover_slide, build_stat_slide, build_outro_slide,
        CANVAS_SIZE, CANVAS_W, CANVAS_H, HALF_W, COLOR_DARK, COLOR_RED,
    )

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

    builders = {
        "slide1_cover.png": lambda p: build_cover_slide(base, data, p),
        "slide2_power.png": lambda p: build_stat_slide(
            base, data["slide2_title"], data["slide2_car1_stat"], data["slide2_car2_stat"],
            data["car1_name"], data["car2_name"], p),
        "slide3_speed.png": lambda p: build_stat_slide(
            base, data["slide3_title"], data["slide3_car1_stat"], data["slide3_car2_stat"],
            data["car1_name"], data["car2_name"], p),
        "slide4_price.png": lambda p: build_stat_slide(
            base, data["slide4_title"], data["slide4_car1_stat"], data["slide4_car2_stat"],
            data["car1_name"], data["car2_name"], p),
        "slide5_outro.png": lambda p: build_outro_slide(base, p),
    }

    paths = {}
    for filename, builder in builders.items():
        local = os.path.join(tmp_dir, filename)
        builder(local)
        paths[filename] = local
        gc.collect()
    return paths

def _file_payload(path, content_type):
    with open(path, "rb") as f:
        return {
            "content_type": content_type,
            "data_base64": base64.b64encode(f.read()).decode("ascii"),
        }

def ingest_to_pages(sid, meta, files):
    admin_pass = os.environ.get("ADMIN_PASS")
    pages_base_url = os.environ.get("PAGES_BASE_URL", "https://azvscars.pages.dev").rstrip("/")
    if not admin_pass:
        raise RuntimeError("ADMIN_PASS is required for Pages ingest.")
    payload = {"meta": meta, "files": files}
    res = http_req.post(
        f"{pages_base_url}/api/ingest/{sid}",
        json=payload,
        headers={"X-Admin-Password": admin_pass},
        timeout=180,
    )
    if not res.ok:
        raise RuntimeError(f"Pages ingest failed: {res.status_code} {res.text}")
    return res.json()

# ─── Generate Action ─────────────────────────────────────────────────────────

def action_generate(sid, post_type, make_reel, mark_done=True):
    from ai_comparison import generate_comparison
    from image_fetcher   import fetch_wikipedia_image
    import reel_renderer

    try:
        set_status(sid, "running", "☁️ AI ilə müqayisə yaradılır…")
        data = generate_comparison(post_type=post_type)

        set_status(sid, "running", f"🖼 Şəkillər yüklənir: {data['car1_name']} / {data['car2_name']}")

        use_pages_ingest = os.environ.get("INGEST_VIA_PAGES", "").lower() == "true" or not os.environ.get("R2_ACCESS_KEY_ID")

        with tempfile.TemporaryDirectory() as tmp:
            img1_path = fetch_wikipedia_image(data["car1_search_query"], os.path.join(tmp, "car1_orig.jpg"))
            img2_path = fetch_wikipedia_image(data["car2_search_query"], os.path.join(tmp, "car2_orig.jpg"))

            set_status(sid, "running", "🎨 Karusel slayidlər render edilir…")
            flip1, flip2 = False, True
            if use_pages_ingest:
                slide_paths = render_local_slides(data, img1_path, img2_path, flip1, flip2, tmp)
                slide_urls = {
                    filename: f"{os.environ.get('PAGES_BASE_URL', 'https://azvscars.pages.dev').rstrip('/')}/api/image/{sid}/{filename}"
                    for filename in SLIDE_KEYS
                }
            else:
                cf.r2_upload_file(img1_path, f"{sid}/car1_orig.jpg", "image/jpeg")
                cf.r2_upload_file(img2_path, f"{sid}/car2_orig.jpg", "image/jpeg")
                slide_urls = render_and_upload(sid, data, img1_path, img2_path, flip1, flip2, tmp)

            reel_url = None
            if make_reel:
                set_status(sid, "running", "🎬 Reel video render edilir…")
                local_reel = os.path.join(tmp, "reel.mp4")
                local_slide_list = [os.path.join(tmp, k) for k in SLIDE_KEYS]
                reel_renderer.render_reel(local_slide_list, local_reel)
                if use_pages_ingest:
                    reel_url = f"{os.environ.get('PAGES_BASE_URL', 'https://azvscars.pages.dev').rstrip('/')}/api/image/{sid}/reel.mp4"
                else:
                    reel_url = cf.r2_upload_file(local_reel, f"{sid}/reel.mp4", "video/mp4")

            meta = {
                "sid":        sid,
                "post_type":  post_type,
                "car1_name":  data["car1_name"],
                "car2_name":  data["car2_name"],
                "flip1":      flip1,
                "flip2":      flip2,
                "caption":    data["caption"] + "\n\n" + data.get("hashtags", ""),
                "data":       data,
                "slide_urls": slide_urls,
                "reel_url":   reel_url,
                "created_at": time.strftime("%Y-%m-%d %H:%M"),
                "is_published": False,
            }
            if use_pages_ingest:
                files = {
                    "car1_orig.jpg": _file_payload(img1_path, "image/jpeg"),
                    "car2_orig.jpg": _file_payload(img2_path, "image/jpeg"),
                }
                for filename in SLIDE_KEYS:
                    files[filename] = _file_payload(os.path.join(tmp, filename), "image/png")
                if make_reel:
                    files["reel.mp4"] = _file_payload(local_reel, "video/mp4")
                set_status(sid, "running", "☁️ Media Cloudflare Pages-ə göndərilir…")
                ingest_to_pages(sid, meta, files)
            else:
                cf.session_save(sid, meta)
        if mark_done:
            set_status(sid, "done", "✅ Hazırdır!")
        print(f"[generate] Done. sid={sid}")

    except Exception as e:
        import traceback
        traceback.print_exc()
        set_status(sid, "error", f"❌ Xəta: {str(e)}")
        sys.exit(1)

# ─── Flip Action ─────────────────────────────────────────────────────────────

def action_flip(sid, car):
    try:
        set_status(sid, "running", "🔄 Maşın yenidən render edilir…")

        meta = cf.session_load(sid)
        if not meta:
            raise Exception(f"Session tapılmadı: {sid}")

        if car == 1:
            meta["flip1"] = not meta.get("flip1", False)
        else:
            meta["flip2"] = not meta.get("flip2", False)

        with tempfile.TemporaryDirectory() as tmp:
            img1 = os.path.join(tmp, "car1_orig.jpg")
            img2 = os.path.join(tmp, "car2_orig.jpg")
            cf.r2_download_to(f"{sid}/car1_orig.jpg", img1)
            cf.r2_download_to(f"{sid}/car2_orig.jpg", img2)

            slide_urls = render_and_upload(sid, meta["data"], img1, img2, meta["flip1"], meta["flip2"], tmp)
            meta["slide_urls"] = slide_urls

        cf.session_save(sid, meta)
        set_status(sid, "done", "✅ Çevrildi!")
        print(f"[flip] Done. sid={sid}, car={car}")

    except Exception as e:
        import traceback
        traceback.print_exc()
        set_status(sid, "error", f"❌ Flip xətası: {str(e)}")
        sys.exit(1)

# ─── Story Campaign Action ──────────────────────────────────────────────────

def action_stories(sid, mark_done=True):
    from story_renderer import render_story_campaign

    try:
        set_status(sid, "running", "📲 Story kartları hazırlanır…")
        with tempfile.TemporaryDirectory() as tmp:
            story_paths = render_story_campaign(tmp)
            pages_base_url = os.environ.get("PAGES_BASE_URL", "https://azvscars.pages.dev").rstrip("/")
            story_urls = {
                filename: f"{pages_base_url}/api/image/{sid}/{filename}"
                for filename in story_paths
            }
            meta = {
                "sid": sid,
                "post_type": "stories",
                "car1_name": "AZvsCars",
                "car2_name": "Story Campaign",
                "caption": "AZvsCars story campaign",
                "story_urls": story_urls,
                "story_files": list(story_paths.keys()),
                "created_at": time.strftime("%Y-%m-%d %H:%M"),
                "is_published": False,
            }
            files = {
                filename: _file_payload(path, "image/jpeg")
                for filename, path in story_paths.items()
            }
            set_status(sid, "running", "☁️ Story kartları Cloudflare-ə göndərilir…")
            ingest_to_pages(sid, meta, files)
        if mark_done:
            set_status(sid, "done", "✅ Story kartları hazırdır!")
        print(f"[stories] Done. sid={sid}")

    except Exception as e:
        import traceback
        traceback.print_exc()
        set_status(sid, "error", f"❌ Story xətası: {str(e)}")
        sys.exit(1)

# ─── Entrypoint ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--action",       required=True, choices=["generate", "flip", "stories"])
    parser.add_argument("--sid",          required=True)
    parser.add_argument("--post_type",    default="main")
    parser.add_argument("--make_reel",    default="false")
    parser.add_argument("--car",          default="1", type=int)
    parser.add_argument("--auto_publish", default="false")
    args = parser.parse_args()

    print(f"[worker] action={args.action} sid={args.sid}")

    if args.action == "generate":
        auto_publish = args.auto_publish.lower() == "true"
        action_generate(args.sid, args.post_type, args.make_reel.lower() == "true", mark_done=not auto_publish)
        
        # Callback for autopilot
        if auto_publish:
            print(f"[worker] auto_publish triggered for sid={args.sid}")
            try:
                import requests
                import os
                
                admin_pass = os.environ.get("ADMIN_PASS")
                pages_base_url = os.environ.get("PAGES_BASE_URL", "https://azvscars.pages.dev").rstrip("/")
                if not admin_pass:
                    raise RuntimeError("ADMIN_PASS is required for auto_publish.")

                set_status(args.sid, "running", "🚀 Instagram-a avtomatik paylaşılır…")
                url = f"{pages_base_url}/api/publish/{args.sid}"
                
                media_type = "reel" if args.make_reel.lower() == "true" else "carousel"
                
                res = requests.post(
                    url,
                    json={"media_type": media_type},
                    headers={"X-Admin-Password": admin_pass}
                )
                print(f"[worker] auto_publish response: {res.status_code} {res.text}")
                res.raise_for_status()
                set_status(args.sid, "done", "✅ Hazırlandı və Instagram-a paylaşıldı!")
            except Exception as e:
                print(f"[worker] auto_publish error: {e}")
                set_status(args.sid, "error", f"❌ Auto-publish xətası: {e}")
                sys.exit(1)
                
    elif args.action == "flip":
        action_flip(args.sid, args.car)
    elif args.action == "stories":
        auto_publish = args.auto_publish.lower() == "true"
        action_stories(args.sid, mark_done=not auto_publish)
        if auto_publish:
            try:
                import requests

                admin_pass = os.environ.get("ADMIN_PASS")
                pages_base_url = os.environ.get("PAGES_BASE_URL", "https://azvscars.pages.dev").rstrip("/")
                if not admin_pass:
                    raise RuntimeError("ADMIN_PASS is required for story auto_publish.")
                set_status(args.sid, "running", "📲 Story-lər Instagram-a paylaşılır…")
                for story_file in [
                    "story1_brand.jpg",
                    "story2_schedule.jpg",
                    "story3_topics.jpg",
                    "story4_contact.jpg",
                    "story5_comment.jpg",
                    "story6_china_germany.jpg",
                    "story7_ev_v8.jpg",
                    "story8_suv_war.jpg",
                ]:
                    res = requests.post(
                        f"{pages_base_url}/api/publish/{args.sid}",
                        json={"media_type": "story", "story_file": story_file},
                        headers={"X-Admin-Password": admin_pass},
                        timeout=60,
                    )
                    print(f"[worker] story publish {story_file}: {res.status_code} {res.text}")
                    res.raise_for_status()
                    time.sleep(2)
                set_status(args.sid, "done", "✅ Story-lər hazırlandı və paylaşıldı!")
            except Exception as e:
                print(f"[worker] story auto_publish error: {e}")
                set_status(args.sid, "error", f"❌ Story publish xətası: {e}")
                sys.exit(1)
