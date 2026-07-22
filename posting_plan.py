import os
from copy import deepcopy


VIDEO_RULES = {
    "format": "reel",
    "aspect_ratio": "9:16",
    "resolution": "1080x1920",
    "fps": 30,
    "safe_zones": {
        "top_px": 180,
        "bottom_px": 300,
        "left_right_px": 42,
    },
    "brand_lockup": "top_left_azvscars",
    "end_card": "VS logo + FOLLOW @azvscars",
    "no_time_overlay": True,
    "no_old_slide_design": True,
}


POST_TYPE_PROFILES = {
    "quick": {
        "label": "Alıcı Seçimi",
        "series": "buyer_decision_daily",
        "pillar": "buying_decision",
        "format": "clean_comparison_reel",
        "cars_per_post": 2,
        "primary_goal": "shares",
        "secondary_goal": "comments",
        "cta": "Öz pulunla hansını alardın? 1 səbəb yaz.",
        "hook_style": "specific AZN budget or ownership decision",
        "publish_window": "Bazar ertəsi 15:10 AZT",
        "visual_family": "buyer_guide",
        "cover_family": "buyer_guide",
        "target_duration_seconds": "12-22",
        "review_required": False,
        "hashtags": ["#azvscars", "#bakimasin", "#avtobazar", "#masinsecimi", "#azerbaycan"],
    },
    "main": {
        "label": "Real Alıcı Müqayisəsi",
        "series": "real_buyer_comparison",
        "pillar": "buying_decision",
        "format": "clean_comparison_reel",
        "cars_per_post": 2,
        "primary_goal": "saves",
        "secondary_goal": "shares",
        "cta": "Bakı reallığında hansına güvənərdin? Səbəb yaz.",
        "hook_style": "Baku buyer logic: price, service, resale and daily comfort",
        "publish_window": "Çərşənbə 12:40 AZT",
        "visual_family": "buyer_guide",
        "cover_family": "buyer_guide",
        "target_duration_seconds": "14-26",
        "review_required": False,
        "hashtags": ["#azvscars", "#bakimasin", "#avtobazar", "#masinqiymeti", "#azerbaycan"],
    },
    "war": {
        "label": "Mənalı Avto Debat",
        "series": "meaningful_comment_battle",
        "pillar": "car_battle",
        "format": "clean_comparison_reel",
        "cars_per_post": 2,
        "primary_goal": "comments",
        "secondary_goal": "shares",
        "cta": "Qısa cavab yox: hansını seçərdin və niyə?",
        "hook_style": "meaningful decision with budget, family or ownership stakes",
        "publish_window": "Çərşənbə axşamı 19:10 / Cümə 13:30 AZT",
        "visual_family": "battle",
        "cover_family": "battle",
        "target_duration_seconds": "10-18",
        "review_required": False,
        "hashtags": ["#azvscars", "#bakimasin", "#avtodebat", "#avtobazar", "#azerbaycan"],
    },
    "night": {
        "label": "Gecə Döyüşü",
        "series": "night_driver_battle",
        "pillar": "experimental",
        "format": "clean_comparison_reel",
        "cars_per_post": 2,
        "primary_goal": "watch_time",
        "secondary_goal": "comments",
        "cta": "Gecə sürüşü üçün hansını seçərdin?",
        "hook_style": "emotion-led night-driving experiment",
        "publish_window": "manual",
        "visual_family": "battle",
        "cover_family": "battle",
        "target_duration_seconds": "8-16",
        "review_required": True,
        "hashtags": ["#azvscars", "#nightdrive", "#masin", "#baku", "#avtomobil", "#azerbaycan"],
    },
    "market": {
        "label": "Bu Pula Dəyər?",
        "series": "baku_market_price_check",
        "pillar": "real_prices_market",
        "format": "one_car_price_reel",
        "cars_per_post": 1,
        "primary_goal": "saves",
        "secondary_goal": "shares",
        "cta": "Bu qiymətə alardın, yoxsa keçərdin?",
        "hook_style": "one real Azerbaijan market listing with AZN price and source date",
        "publish_window": "Çərşənbə axşamı 13:20 / Cümə axşamı 12:20 AZT",
        "visual_family": "price",
        "cover_family": "price",
        "target_duration_seconds": "10-18",
        "review_required": False,
        "hashtags": ["#azvscars", "#masinqiymeti", "#avtobazar", "#bakimasin", "#azerbaycan"],
    },
    "night_supercar": {
        "label": "Night Supercar",
        "series": "night_supercar_special",
        "pillar": "baku_spotting_entertainment",
        "format": "clean_supercar_reel",
        "cars_per_post": 1,
        "primary_goal": "follows",
        "secondary_goal": "shares",
        "cta": "Car-only supercar seriyası üçün səhifəni izlə.",
        "hook_style": "licensed car-only supercar visual with harsh engine or fallback brand soundtrack",
        "publish_window": "Çərşənbə 23:00 / Cümə axşamı 20:30 / Cümə 22:30 AZT",
        "visual_family": "car_spotting",
        "cover_family": "car_spotting",
        "target_duration_seconds": "7-12",
        "review_required": False,
        "hashtags": ["#azvscars", "#supercar", "#bakucars", "#avtomobil", "#azerbaycan"],
    },
}


SCHEDULED_SLOTS = {
    "mon_1510_buying": {
        "time_azt": "15:10",
        "cron_utc": "10 11 * * 1",
        "post_type": "quick",
        "name": "Monday buyer decision test",
    },
    "tue_1320_market": {
        "time_azt": "13:20",
        "cron_utc": "20 9 * * 2",
        "post_type": "market",
        "name": "Tuesday lunch market price check",
    },
    "tue_1910_debate": {
        "time_azt": "19:10",
        "cron_utc": "10 15 * * 2",
        "post_type": "war",
        "name": "Tuesday evening debate reel",
    },
    "wed_1240_main": {
        "time_azt": "12:40",
        "cron_utc": "40 8 * * 3",
        "post_type": "main",
        "name": "Wednesday lunch buyer comparison",
    },
    "wed_2300_supercar": {
        "time_azt": "23:00",
        "cron_utc": "0 19 * * 3",
        "post_type": "night_supercar",
        "name": "Wednesday late car-only supercar",
    },
    "thu_1220_market": {
        "time_azt": "12:20",
        "cron_utc": "20 8 * * 4",
        "post_type": "market",
        "name": "Thursday lunch market price check",
    },
    "thu_2030_supercar": {
        "time_azt": "20:30",
        "cron_utc": "30 16 * * 4",
        "post_type": "night_supercar",
        "name": "Thursday night car-only supercar",
    },
    "fri_1330_war": {
        "time_azt": "13:30",
        "cron_utc": "30 9 * * 5",
        "post_type": "war",
        "name": "Friday lunch debate reel",
    },
    "fri_2230_supercar": {
        "time_azt": "22:30",
        "cron_utc": "30 18 * * 5",
        "post_type": "night_supercar",
        "name": "Friday late car-only supercar",
    },
}


def profile_for(post_type):
    normalized = "night_supercar" if post_type == "cinematic" else post_type
    return deepcopy(POST_TYPE_PROFILES.get(normalized, POST_TYPE_PROFILES["main"]))


def slot_for_env(post_type):
    slot_id = os.environ.get("POSTING_SLOT", "").strip()
    slot = deepcopy(SCHEDULED_SLOTS.get(slot_id, {}))
    if slot:
        return slot_id, slot
    profile = profile_for(post_type)
    return "manual", {
        "time_azt": profile.get("publish_window", "manual"),
        "cron_utc": "",
        "post_type": post_type,
        "name": "Manual generation",
    }


def build_publish_strategy(post_type, media_type="reel"):
    profile = profile_for(post_type)
    slot_id, slot = slot_for_env(post_type)
    strategy = {
        "profile": profile,
        "posting_slot": slot_id,
        "posting_time_azt": slot.get("time_azt", "manual"),
        "slot_name": slot.get("name", "Manual generation"),
        "media_type": media_type,
        "pillar": profile["pillar"],
        "content_series": profile["series"],
        "format": profile["format"],
        "cars_per_post": profile["cars_per_post"],
        "primary_goal": profile["primary_goal"],
        "secondary_goal": profile["secondary_goal"],
        "cta_focus": profile["cta"],
        "hook_style": profile["hook_style"],
        "visual_family": profile.get("visual_family", ""),
        "cover_family": profile.get("cover_family", ""),
        "target_duration_seconds": profile.get("target_duration_seconds", ""),
        "review_required": profile.get("review_required", False),
        "video_rules": VIDEO_RULES,
        "quality_rules": [
            "one_featured_car_per_reel_except_comparison",
            "fresh_media_assets",
            "fresh_audio_assets",
            "azn_price_when_price_is_shown",
            "no_old_slide_design_for_reels",
            "single_primary_cta",
            "market_posts_need_source_and_check_date",
            "check_last_20_posts_for_model_overuse",
            "rotate_visual_families",
            "alt_text_present",
            "no_people_or_hands_in_car_only_reels",
            "track_profile_visits_per_reach_and_follows_per_profile_visit",
        ],
    }
    return strategy


def metadata_fields(post_type, media_type="reel"):
    strategy = build_publish_strategy(post_type, media_type)
    profile = strategy["profile"]
    return {
        "content_series": profile["series"],
        "posting_slot": strategy["posting_slot"],
        "posting_time_azt": strategy["posting_time_azt"],
        "posting_label": profile["label"],
        "publish_strategy": strategy,
        "analytics_template": {
            "content_id": "",
            "publish_date": "",
            "publish_time": "",
            "pillar": profile["pillar"],
            "series": profile["series"],
            "hook_type": profile["hook_style"],
            "hook_text": "",
            "cta_type": profile["primary_goal"],
            "duration_seconds": "",
            "video_style": profile.get("visual_family", ""),
            "voice_type": "",
            "source_type": "",
            "rights_status": "",
            "model_1": "",
            "model_2": "",
            "price_if_applicable": "",
            "location": "Azerbaijan",
            "experimental_variable": "",
            "snapshots": {
                "24h": {},
                "72h": {},
                "7d": {},
            },
        },
        "metadata_version": "2026-07-18-growth-system-v3",
    }
