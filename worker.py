"""
worker.py — GitHub Actions Worker
Handles:
  - action=generate: AI comparison -> images -> slides render -> optional reel -> R2 + KV
  - action=flip:     flip a car image and re-render slides
  - action=stories:  render branded story cards -> R2/KV -> optional publish
Called by Cloudflare Functions via workflow_dispatch.
Reports status to Cloudflare KV so frontend can poll /api/status/[sid].
"""
import os, sys, json, uuid, time, tempfile, gc, argparse, base64, random
import requests as http_req
from dotenv import load_dotenv
load_dotenv()

import cloudflare_storage as cf
from publish_quality import apply_publish_quality
from posting_plan import metadata_fields

SLIDE_KEYS = [
    "slide1_cover.png", "slide2_power.png", "slide3_speed.png",
    "slide4_price.png", "slide5_outro.png",
]
MARKET_SLIDE_KEYS = SLIDE_KEYS[:3]

# ─── KV Status Helper ────────────────────────────────────────────────────────

def set_status(sid, status, message):
    """Write status to KV so Cloudflare Function can return it to frontend."""
    try:
        cf.kv_put(f"status_{sid}", json.dumps({"status": status, "message": message, "sid": sid}))
    except Exception as e:
        print(f"[status] KV write failed: {e}")

def pages_base_url():
    return (os.environ.get("PAGES_BASE_URL") or "https://azvscars.pages.dev").rstrip("/")


def _metadata(post_type, media_type="reel"):
    return metadata_fields(post_type, media_type)


def _asset_history():
    history = cf.kv_get("assets:recent")
    return history if isinstance(history, list) else []


def _used_audio_ids():
    values = cf.kv_get("audio:used_ids")
    if isinstance(values, list):
        return [str(value) for value in values]
    return _pages_asset_ids("audio")


def _used_video_ids():
    values = cf.kv_get("video:used_ids")
    if isinstance(values, list):
        return [str(value) for value in values]
    return _pages_asset_ids("video")


def _pages_asset_ids(kind):
    password = os.environ.get("ADMIN_PASS", "").strip()
    if not password:
        return []
    try:
        response = http_req.get(
            f"{pages_base_url()}/api/asset-history",
            headers={"X-Admin-Password": password},
            timeout=20,
        )
        response.raise_for_status()
        values = response.json().get(f"{kind}_ids", [])
        return [str(value) for value in values] if isinstance(values, list) else []
    except Exception as exc:
        print(f"[assets] Pages history read failed for {kind}: {exc}")
        return []


def _fresh_car_asset(sid, query, car_name, output_path, slot, history, selected_assets):
    from image_fetcher import fetch_unique_car_image

    excluded_urls = {
        item.get("url") for item in history + selected_assets
        if isinstance(item, dict) and item.get("url")
    }
    excluded_hashes = {
        item.get("fingerprint") for item in history + selected_assets
        if isinstance(item, dict) and item.get("fingerprint")
    }
    short_name = " ".join(str(car_name).split()[:2])
    variants = [
        query,
        f"{car_name} automobile exterior",
        f"{car_name} car",
        f"{short_name} exterior",
        f"{short_name} side view",
        f"{short_name} official car",
    ]
    for variant in variants:
        asset = fetch_unique_car_image(
            variant,
            output_path,
            seed=f"{sid}:{slot}:{variant}",
            excluded_urls=excluded_urls,
            excluded_hashes=excluded_hashes,
        )
        if asset:
            selected = {
                "car": car_name,
                "url": asset.get("url", ""),
                "fingerprint": asset.get("fingerprint", ""),
                "title": asset.get("title", ""),
                "sid": sid,
                "used_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            selected_assets.append(selected)
            return output_path

    for variant in variants:
        asset = fetch_unique_car_image(
            variant,
            output_path,
            seed=f"{sid}:fallback:{slot}:{variant}",
            excluded_urls=set(),
            excluded_hashes=set(),
        )
        if asset:
            selected_assets.append({
                "car": car_name,
                "url": asset.get("url", ""),
                "fingerprint": asset.get("fingerprint", ""),
                "title": asset.get("title", ""),
                "sid": sid,
                "used_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "reused_fallback": True,
                "quality_note": "Fresh image pool was exhausted; reused highest-ranked high-quality image to keep posting reliable.",
            })
            return output_path
    raise RuntimeError(f"No high-quality image found for {car_name}; post cancelled.")


def _save_asset_history(history, selected_assets):
    cf.kv_put("assets:recent", (selected_assets + history)[:160])

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
            d["car1_name"], d["car2_name"], p, d.get("hide_names_until_end", True)),
        "slide3_speed.png": lambda p: build_stat_slide(
            base, d["slide3_title"], d["slide3_car1_stat"], d["slide3_car2_stat"],
            d["car1_name"], d["car2_name"], p, d.get("hide_names_until_end", True)),
        "slide4_price.png": lambda p: build_stat_slide(
            base, d["slide4_title"], d["slide4_car1_stat"], d["slide4_car2_stat"],
            d["car1_name"], d["car2_name"], p, d.get("hide_names_until_end", True)),
        "slide5_outro.png": lambda p: build_outro_slide(base, p, d),
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
            data["car1_name"], data["car2_name"], p, data.get("hide_names_until_end", True)),
        "slide3_speed.png": lambda p: build_stat_slide(
            base, data["slide3_title"], data["slide3_car1_stat"], data["slide3_car2_stat"],
            data["car1_name"], data["car2_name"], p, data.get("hide_names_until_end", True)),
        "slide4_price.png": lambda p: build_stat_slide(
            base, data["slide4_title"], data["slide4_car1_stat"], data["slide4_car2_stat"],
            data["car1_name"], data["car2_name"], p, data.get("hide_names_until_end", True)),
        "slide5_outro.png": lambda p: build_outro_slide(base, p, data),
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
    if not admin_pass:
        raise RuntimeError("ADMIN_PASS is required for Pages ingest.")
    payload = {"meta": meta, "files": files}
    res = http_req.post(
        f"{pages_base_url()}/api/ingest/{sid}",
        json=payload,
        headers={"X-Admin-Password": admin_pass},
        timeout=180,
    )
    if not res.ok:
        raise RuntimeError(f"Pages ingest failed: {res.status_code} {res.text}")
    return res.json()


def maybe_publish_post_story_reminder(sid, admin_pass):
    try:
        if os.environ.get("POST_STORY_REMINDER", "true").lower() != "true":
            return
        session_res = http_req.get(
            f"{pages_base_url()}/api/session/{sid}",
            headers={"X-Admin-Password": admin_pass},
            timeout=30,
        )
        if not session_res.ok:
            print(f"[worker] story reminder skipped: session read failed {session_res.status_code}")
            return
        session = session_res.json()
        if "slide1_cover.png" not in (session.get("slide_urls") or {}):
            print("[worker] story reminder skipped: clean reel has no slide1_cover.png")
            return
        delay_raw = os.environ.get("POST_STORY_REMINDER_DELAY_SECONDS", "").strip()
        if delay_raw:
            delay = max(0, int(delay_raw))
        else:
            delay = random.randint(120, 240)
        print(f"[worker] story reminder waits {delay}s for sid={sid}")
        time.sleep(delay)
        res = http_req.post(
            f"{pages_base_url()}/api/publish/{sid}",
            json={"media_type": "story", "story_file": "slide1_cover.png"},
            headers={"X-Admin-Password": admin_pass},
            timeout=90,
        )
        print(f"[worker] post story reminder response: {res.status_code} {res.text}")
    except Exception as exc:
        print(f"[worker] story reminder skipped after error: {exc}")

# ─── Generate Action ─────────────────────────────────────────────────────────

def action_market_generate(sid, mark_done=True):
    from market_content import build_market_alt_text, build_market_caption, pick_market_batch
    from clean_reel_renderer import render_clean_single_car_reel
    from video_sound_fetcher import download_market_startup_sounds

    set_status(sid, "running", "💸 Bakı bazarı reel-i üçün maşınlar seçilir…")
    cars = pick_market_batch(sid, count=1)
    use_pages_ingest = os.environ.get("INGEST_VIA_PAGES", "").lower() == "true" or not os.environ.get("R2_ACCESS_KEY_ID")

    history = _asset_history()
    selected_assets = []

    with tempfile.TemporaryDirectory() as tmp:
        image_paths = []
        for idx, car in enumerate(cars, start=1):
            set_status(sid, "running", f"🖼 {car['name']} şəkli hazırlanır…")
            image_paths.append(_fresh_car_asset(
                sid, car["search_query"], car["name"],
                os.path.join(tmp, f"market_{idx}.jpg"), idx, history, selected_assets,
            ))

        set_status(sid, "running", "🔊 Bu maşın üçün fərqli startup səsi seçilir…")
        audio_paths, audio_assets = download_market_startup_sounds(
            cars,
            os.path.join(tmp, "market_audio"),
            sid,
            [{"media_type": "audio", "provider_id": value} for value in _used_audio_ids()],
        )
        if len(audio_paths) != len(cars):
            raise RuntimeError("Fresh startup sound was not found for every market card; publish cancelled to prevent audio repetition.")
        selected_assets.extend(audio_assets)

        set_status(sid, "running", "🎬 Clean market reel render edilir…")
        local_reel = os.path.join(tmp, "reel.mp4")
        render_clean_single_car_reel(cars[0], image_paths[0], local_reel, audio_paths=audio_paths)
        reel_url = f"{pages_base_url()}/api/image/{sid}/reel.mp4" if use_pages_ingest else None

        caption = build_market_caption(cars)
        alt_text = build_market_alt_text(cars)
        meta_fields = _metadata("market", "reel")
        meta = {
            "sid": sid,
            "post_type": "market",
            "content_series": meta_fields["content_series"],
            "posting_slot": meta_fields["posting_slot"],
            "posting_time_azt": meta_fields["posting_time_azt"],
            "posting_label": meta_fields["posting_label"],
            "metadata_version": meta_fields["metadata_version"],
            "car1_name": cars[0]["name"],
            "car2_name": cars[1]["name"] if len(cars) > 1 else "Baku bazarı",
            "caption": caption,
            "alt_text": alt_text,
            "image_description": alt_text,
            "data": {
                "market_cars": cars,
                "battle_title": "BAKI QİYMƏT CHECK",
                "slide2_car1_stat": cars[0]["price_label"],
                "slide2_car2_stat": cars[1]["price_label"] if len(cars) > 1 else "",
                "slide3_car1_stat": cars[0]["mileage"],
                "slide3_car2_stat": cars[1]["mileage"] if len(cars) > 1 else "",
                "audio_sources": audio_assets,
            },
            "publish_strategy": meta_fields["publish_strategy"],
            "source_assets": selected_assets,
            "slide_urls": {},
            "reel_url": reel_url or cf.r2_upload_file(local_reel, f"{sid}/reel.mp4", "video/mp4"),
            "created_at": time.strftime("%Y-%m-%d %H:%M"),
            "is_published": False,
        }

        if use_pages_ingest:
            files = {
                "reel.mp4": _file_payload(local_reel, "video/mp4"),
            }
            for idx, image_path in enumerate(image_paths, start=1):
                files[f"market_{idx}.jpg"] = _file_payload(image_path, "image/jpeg")
            set_status(sid, "running", "☁️ Market media Cloudflare Pages-ə göndərilir…")
            ingest_to_pages(sid, meta, files)
        else:
            cf.session_save(sid, meta)
            _save_asset_history(history, selected_assets)
            existing_audio_ids = _used_audio_ids()
            new_audio_ids = [item["provider_id"] for item in audio_assets]
            cf.kv_put("audio:used_ids", list(dict.fromkeys(new_audio_ids + existing_audio_ids)))

    if mark_done:
        set_status(sid, "done", "✅ Market reel hazırdır!")
    print(f"[market] Done. sid={sid}")


def action_night_supercar_generate(sid, mark_done=True):
    from night_supercar_renderer import render_night_supercar_reel
    from video_sound_fetcher import download_market_startup_sounds, download_night_supercar_assets

    set_status(sid, "running", "🏁 Gecə supercar videoları seçilir…")
    use_pages_ingest = os.environ.get("INGEST_VIA_PAGES", "").lower() == "true" or not os.environ.get("R2_ACCESS_KEY_ID")

    with tempfile.TemporaryDirectory() as tmp:
        media = download_night_supercar_assets(
            os.path.join(tmp, "night_supercar_video"),
            sid,
            used_video_ids=_used_video_ids(),
            max_videos=3,
        )
        if len(media["videos"]) != 3:
            raise RuntimeError(f"Three fresh supercar clips were not found; publish cancelled. {media.get('errors')}")

        set_status(sid, "running", "🔊 Üç fərqli supercar səsi seçilir…")
        sound_profiles = [
            {"name": "V12 Supercar", "engine": "V12"},
            {"name": "V10 Race Car", "engine": "V10"},
            {"name": "V8 Exhibition Car", "engine": "V8"},
        ]
        audio_paths, audio_sources = download_market_startup_sounds(
            sound_profiles,
            os.path.join(tmp, "night_supercar_audio"),
            sid,
            [{"media_type": "audio", "provider_id": value} for value in _used_audio_ids()],
        )
        if len(audio_paths) != 3:
            raise RuntimeError("Three fresh supercar sounds were not found; publish cancelled to prevent repetition.")

        set_status(sid, "running", "🎬 Night Supercar Reel render edilir…")
        local_reel = os.path.join(tmp, "reel.mp4")
        render_night_supercar_reel(media["videos"], audio_paths, local_reel, sid)

        used_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        video_sources = []
        for source in media["sources"]:
            normalized = dict(source)
            normalized["url"] = normalized.get("source_url", "")
            normalized["used_at"] = used_at
            video_sources.append(normalized)
        source_assets = video_sources + audio_sources
        meta_fields = _metadata("night_supercar", "reel")
        caption = (
            "Gecə səsi açıq saxla. 🏁\n\n"
            "Supercar, yarış və sərgi kadrlarından hansını bir də izlədin? "
            "Maşın sevən dosta göndər və ən güclü səsi şərhdə yaz.\n\n"
            "FOLLOW @azvscars\n\n"
            "#azvscars #supercar #racing #carshow #baku #azerbaijan #cars"
        )
        meta = {
            "sid": sid,
            "post_type": "night_supercar",
            "content_series": meta_fields["content_series"],
            "posting_slot": meta_fields["posting_slot"],
            "posting_time_azt": meta_fields["posting_time_azt"],
            "posting_label": meta_fields["posting_label"],
            "metadata_version": meta_fields["metadata_version"],
            "car1_name": "Night Supercars",
            "car2_name": "Racing & Exhibition",
            "caption": caption,
            "alt_text": "Gecə supercar, yarış və avtomobil sərgisi kadrlarından hazırlanmış dinamik Reel.",
            "image_description": "Three unique supercar, racing and exhibition clips with unique engine sounds.",
            "data": {
                "video_sources": video_sources,
                "audio_sources": audio_sources,
                "has_time_overlay": False,
                "end_card": "FOLLOW @azvscars",
            },
            "publish_strategy": meta_fields["publish_strategy"],
            "source_assets": source_assets,
            "slide_urls": {},
            "reel_url": f"{pages_base_url()}/api/image/{sid}/reel.mp4" if use_pages_ingest else cf.r2_upload_file(local_reel, f"{sid}/reel.mp4", "video/mp4"),
            "created_at": time.strftime("%Y-%m-%d %H:%M"),
            "is_published": False,
        }

        if use_pages_ingest:
            set_status(sid, "running", "☁️ Night Supercar media Cloudflare-ə göndərilir…")
            ingest_to_pages(sid, meta, {"reel.mp4": _file_payload(local_reel, "video/mp4")})
        else:
            cf.session_save(sid, meta)
            current_audio = _used_audio_ids()
            current_video = _used_video_ids()
            cf.kv_put("audio:used_ids", list(dict.fromkeys([item["provider_id"] for item in audio_sources] + current_audio)))
            cf.kv_put("video:used_ids", list(dict.fromkeys([item["provider_id"] for item in video_sources] + current_video)))

    if mark_done:
        set_status(sid, "done", "✅ Night Supercar Reel hazırdır!")
    print(f"[night_supercar] Done. sid={sid}")

def action_cinematic_generate(sid, mark_done=True, mode="crazy"):
    from ai_comparison import generate_comparison
    from video_sound_fetcher import choose_reel_type, cinematic_script, download_cinematic_assets
    import cinematic_reel_renderer

    set_status(sid, "running", "🎬 Cinematic reel üçün mövzu hazırlanır…")
    data = generate_comparison(post_type="night")
    reel_type = choose_reel_type(sid, mode=mode)
    script = cinematic_script(reel_type, data["car1_name"], data["car2_name"])
    data = apply_publish_quality(data, post_type="cinematic", media_type="reel")
    use_pages_ingest = os.environ.get("INGEST_VIA_PAGES", "").lower() == "true" or not os.environ.get("R2_ACCESS_KEY_ID")
    history = _asset_history()
    selected_assets = []

    with tempfile.TemporaryDirectory() as tmp:
        img1_path = _fresh_car_asset(
            sid, data["car1_search_query"], data["car1_name"],
            os.path.join(tmp, "car1_orig.jpg"), 1, history, selected_assets,
        )
        img2_path = _fresh_car_asset(
            sid, data["car2_search_query"], data["car2_name"],
            os.path.join(tmp, "car2_orig.jpg"), 2, history, selected_assets,
        )

        set_status(sid, "running", "🎨 Brend slaydlar hazırlanır…")
        flip1, flip2 = False, True
        slide_paths = render_local_slides(data, img1_path, img2_path, flip1, flip2, tmp)
        slide_urls = {
            filename: f"{pages_base_url()}/api/image/{sid}/{filename}"
            for filename in SLIDE_KEYS
        }

        set_status(sid, "running", "🏎 Video və real səs effektləri axtarılır…")
        media = download_cinematic_assets(
            reel_type,
            os.path.join(tmp, "cinematic_assets"),
            car1=data["car1_name"],
            car2=data["car2_name"],
        )
        if not media["videos"]:
            raise RuntimeError(f"Cinematic video tapılmadı. Fallback lazımdır. Errors: {media.get('errors')}")

        set_status(sid, "running", "🎞 Cinematic reel render edilir…")
        local_reel = os.path.join(tmp, "reel.mp4")
        fallback_slides = [slide_paths[k] for k in SLIDE_KEYS[:-1]]
        cinematic_reel_renderer.render_cinematic_reel(
            media["videos"],
            fallback_slides,
            slide_paths["slide5_outro.png"],
            local_reel,
            script,
            sfx_paths=media["sfx"],
            source_video_paths=media["videos"],
        )
        reel_url = f"{pages_base_url()}/api/image/{sid}/reel.mp4" if use_pages_ingest else None

        caption = data["caption"]
        meta = {
            "sid": sid,
            "post_type": "cinematic",
            "content_series": "crazy_cars" if mode == "crazy" else "cinematic",
            "cinematic_type": reel_type,
            "car1_name": data["car1_name"],
            "car2_name": data["car2_name"],
            "flip1": flip1,
            "flip2": flip2,
            "caption": caption,
            "alt_text": data.get("alt_text", ""),
            "image_description": data.get("image_description", ""),
            "data": {
                **data,
                "cinematic_script": script,
                "cinematic_sources": media.get("sources", []),
                "cinematic_media_errors": media.get("errors", []),
            },
            "source_assets": selected_assets,
            "slide_urls": slide_urls,
            "reel_url": reel_url or cf.r2_upload_file(local_reel, f"{sid}/reel.mp4", "video/mp4"),
            "created_at": time.strftime("%Y-%m-%d %H:%M"),
            "is_published": False,
        }

        if use_pages_ingest:
            files = {
                "car1_orig.jpg": _file_payload(img1_path, "image/jpeg"),
                "car2_orig.jpg": _file_payload(img2_path, "image/jpeg"),
                "reel.mp4": _file_payload(local_reel, "video/mp4"),
            }
            for filename in SLIDE_KEYS:
                files[filename] = _file_payload(os.path.join(tmp, filename), "image/png")
            set_status(sid, "running", "☁️ Cinematic media Cloudflare Pages-ə göndərilir…")
            ingest_to_pages(sid, meta, files)
        else:
            cf.session_save(sid, meta)
            _save_asset_history(history, selected_assets)

    if mark_done:
        set_status(sid, "done", "✅ Cinematic reel hazırdır!")
    print(f"[cinematic] Done. sid={sid} type={reel_type}")

def action_generate(sid, post_type, make_reel, mark_done=True):
    from ai_comparison import generate_comparison
    from clean_reel_renderer import render_clean_comparison_reel
    from video_sound_fetcher import download_market_startup_sounds
    import reel_renderer

    try:
        if post_type == "market":
            return action_market_generate(sid, mark_done=mark_done)

        if post_type == "night_supercar":
            return action_night_supercar_generate(sid, mark_done=mark_done)

        if post_type == "cinematic":
            return action_night_supercar_generate(sid, mark_done=mark_done)

        set_status(sid, "running", "☁️ AI ilə müqayisə yaradılır…")
        data = generate_comparison(post_type=post_type)
        media_type_for_quality = "reel" if make_reel else "carousel"
        data = apply_publish_quality(data, post_type=post_type, media_type=media_type_for_quality)

        set_status(sid, "running", f"🖼 Şəkillər yüklənir: {data['car1_name']} / {data['car2_name']}")

        use_pages_ingest = os.environ.get("INGEST_VIA_PAGES", "").lower() == "true" or not os.environ.get("R2_ACCESS_KEY_ID")
        history = _asset_history()
        selected_assets = []

        with tempfile.TemporaryDirectory() as tmp:
            img1_path = _fresh_car_asset(
                sid, data["car1_search_query"], data["car1_name"],
                os.path.join(tmp, "car1_orig.jpg"), 1, history, selected_assets,
            )
            img2_path = _fresh_car_asset(
                sid, data["car2_search_query"], data["car2_name"],
                os.path.join(tmp, "car2_orig.jpg"), 2, history, selected_assets,
            )

            flip1, flip2 = False, True
            slide_paths = {}
            slide_urls = {}
            if not make_reel:
                set_status(sid, "running", "🎨 Karusel slayidlər render edilir…")
                if use_pages_ingest:
                    slide_paths = render_local_slides(data, img1_path, img2_path, flip1, flip2, tmp)
                    slide_urls = {
                        filename: f"{pages_base_url()}/api/image/{sid}/{filename}"
                        for filename in SLIDE_KEYS
                    }
                else:
                    cf.r2_upload_file(img1_path, f"{sid}/car1_orig.jpg", "image/jpeg")
                    cf.r2_upload_file(img2_path, f"{sid}/car2_orig.jpg", "image/jpeg")
                    slide_urls = render_and_upload(sid, data, img1_path, img2_path, flip1, flip2, tmp)

            reel_url = None
            if make_reel:
                set_status(sid, "running", "🔊 Hər maşın üçün fərqli car sound seçilir…")
                audio_profiles = [
                    {"name": data["car1_name"], "engine": data.get("slide2_car1_stat", "")},
                    {"name": data["car2_name"], "engine": data.get("slide2_car2_stat", "")},
                ]
                audio_paths, audio_assets = download_market_startup_sounds(
                    audio_profiles,
                    os.path.join(tmp, "comparison_audio"),
                    sid,
                    [{"media_type": "audio", "provider_id": value} for value in _used_audio_ids()],
                )
                if len(audio_paths) != 2:
                    raise RuntimeError("Two fresh car sounds were not found; publish cancelled to prevent repeated or weak audio.")
                selected_assets.extend(audio_assets)

                set_status(sid, "running", "🎬 Clean comparison reel render edilir…")
                local_reel = os.path.join(tmp, "reel.mp4")
                render_clean_comparison_reel(data, img1_path, img2_path, local_reel, audio_paths=audio_paths)
                if use_pages_ingest:
                    reel_url = f"{pages_base_url()}/api/image/{sid}/reel.mp4"
                else:
                    reel_url = cf.r2_upload_file(local_reel, f"{sid}/reel.mp4", "video/mp4")

            meta_fields = _metadata(post_type, "reel" if make_reel else "carousel")
            meta = {
                "sid":        sid,
                "post_type":  post_type,
                "content_series": meta_fields["content_series"],
                "posting_slot": meta_fields["posting_slot"],
                "posting_time_azt": meta_fields["posting_time_azt"],
                "posting_label": meta_fields["posting_label"],
                "metadata_version": meta_fields["metadata_version"],
                "car1_name":  data["car1_name"],
                "car2_name":  data["car2_name"],
                "flip1":      flip1,
                "flip2":      flip2,
                "caption":    data["caption"],
                "alt_text":   data.get("alt_text", ""),
                "image_description": data.get("image_description", ""),
                "data":       data,
                "publish_strategy": meta_fields["publish_strategy"],
                "source_assets": selected_assets,
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
                    if filename in slide_paths:
                        files[filename] = _file_payload(os.path.join(tmp, filename), "image/png")
                if make_reel:
                    files["reel.mp4"] = _file_payload(local_reel, "video/mp4")
                set_status(sid, "running", "☁️ Media Cloudflare Pages-ə göndərilir…")
                ingest_to_pages(sid, meta, files)
            else:
                cf.session_save(sid, meta)
                _save_asset_history(history, selected_assets)
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

def action_stories(sid, story_slot="all", mark_done=True):
    from story_renderer import render_story_campaign
    from ai_comparison import generate_comparison

    try:
        set_status(sid, "running", "📲 Story kartları hazırlanır…")
        with tempfile.TemporaryDirectory() as tmp:
            daily_data = generate_comparison(post_type="main")
            story_paths = render_story_campaign(tmp, daily_data=daily_data)
            story_urls = {
                filename: f"{pages_base_url()}/api/image/{sid}/{filename}"
                for filename in story_paths
            }
            meta = {
                "sid": sid,
                "post_type": "stories",
                "story_slot": story_slot,
                "car1_name": "AZvsCars",
                "car2_name": "Story Campaign",
                "caption": "AZvsCars gündəlik story axını",
                "data": {"daily_comparison": daily_data},
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
    parser.add_argument("--story_files",   default="")
    parser.add_argument("--story_slot",    default="all", choices=["morning", "noon", "evening", "all"])
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
                if not admin_pass:
                    raise RuntimeError("ADMIN_PASS is required for auto_publish.")

                set_status(args.sid, "running", "🚀 Instagram-a avtomatik paylaşılır…")
                url = f"{pages_base_url()}/api/publish/{args.sid}"
                
                media_type = "reel" if args.make_reel.lower() == "true" else "carousel"
                
                res = requests.post(
                    url,
                    json={"media_type": media_type, "force": True},
                    headers={"X-Admin-Password": admin_pass}
                )
                print(f"[worker] auto_publish response: {res.status_code} {res.text}")
                res.raise_for_status()
                maybe_publish_post_story_reminder(args.sid, admin_pass)
                set_status(args.sid, "done", "✅ Hazırlandı və Instagram-a paylaşıldı!")
            except Exception as e:
                print(f"[worker] auto_publish error: {e}")
                set_status(args.sid, "error", f"❌ Auto-publish xətası: {e}")
                sys.exit(1)
                
    elif args.action == "flip":
        action_flip(args.sid, args.car)
    elif args.action == "stories":
        auto_publish = args.auto_publish.lower() == "true"
        action_stories(args.sid, story_slot=args.story_slot, mark_done=not auto_publish)
        if auto_publish:
            try:
                import requests

                admin_pass = os.environ.get("ADMIN_PASS")
                if not admin_pass:
                    raise RuntimeError("ADMIN_PASS is required for story auto_publish.")
                default_story_files = [
                    "story1_brand.jpg",
                    "story2_schedule.jpg",
                    "story3_topics.jpg",
                    "story4_contact.jpg",
                    "story5_comment.jpg",
                    "story6_china_germany.jpg",
                    "story7_ev_v8.jpg",
                    "story8_suv_war.jpg",
                    "story9_daily_duel.jpg",
                    "story10_daily_question.jpg",
                ]
                selected_story_files = [
                    item.strip()
                    for item in args.story_files.split(",")
                    if item.strip()
                ] or default_story_files
                allowed_story_files = set(default_story_files)
                invalid = [name for name in selected_story_files if name not in allowed_story_files]
                if invalid:
                    raise RuntimeError(f"Invalid story_files: {', '.join(invalid)}")

                set_status(args.sid, "running", "📲 Story-lər Instagram-a paylaşılır…")
                for story_file in selected_story_files:
                    res = requests.post(
                        f"{pages_base_url()}/api/publish/{args.sid}",
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
