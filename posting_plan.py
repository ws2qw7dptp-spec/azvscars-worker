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
        "secondary_goal": "shares",
        "cta": "Hansını alardın və niyə?",
        "hook_style": "specific AZN budget or ownership decision",
        "publish_window": "Bazar ertəsi 09:00 AZT",
        "visual_family": "buyer_guide",
        "cover_family": "buyer_guide",
        "target_duration_seconds": "12-22",
        "review_required": False,
        "hashtags": ["#azvscars", "#masin", "#avtomobil", "#azerbaycan", "#baku", "#masinsecimi"],
    },
    "main": {
        "label": "Real Alıcı Müqayisəsi",
        "series": "real_buyer_comparison",
        "pillar": "buying_decision",
        "format": "clean_comparison_reel",
        "cars_per_post": 2,
        "primary_goal": "saves",
        "secondary_goal": "shares",
        "cta": "Maşın baxırsansa bunu yadda saxla.",
        "hook_style": "Baku buyer logic: price, service, resale and daily comfort",
        "publish_window": "Çərşənbə 19:30 AZT",
        "visual_family": "buyer_guide",
        "cover_family": "buyer_guide",
        "target_duration_seconds": "14-26",
        "review_required": False,
        "hashtags": ["#azvscars", "#masin", "#avtomobil", "#azerbaycan", "#bakucars", "#masinqiymetleri"],
    },
    "war": {
        "label": "Mənalı Avto Debat",
        "series": "meaningful_comment_battle",
        "pillar": "car_battle",
        "format": "clean_comparison_reel",
        "cars_per_post": 2,
        "primary_goal": "comments",
        "secondary_goal": "shares",
        "cta": "Səbəbini yaz: niyə biri o birindən daha məntiqlidir?",
        "hook_style": "meaningful decision with budget, family or ownership stakes",
        "publish_window": "Cümə 19:30 AZT",
        "visual_family": "battle",
        "cover_family": "battle",
        "target_duration_seconds": "10-18",
        "review_required": False,
        "hashtags": ["#azvscars", "#masin", "#avtomobil", "#azerbaycan", "#bakucars", "#avtodebat"],
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
        "publish_window": "Çərşənbə axşamı 13:00 AZT",
        "visual_family": "price",
        "cover_family": "price",
        "target_duration_seconds": "10-18",
        "review_required": False,
        "hashtags": ["#azvscars", "#masinqiymeti", "#avtobazar", "#turboaz", "#baku", "#azerbaycan"],
    },
    "night_supercar": {
        "label": "Night Supercar",
        "series": "night_supercar_special",
        "pillar": "baku_spotting_entertainment",
        "format": "clean_supercar_reel",
        "cars_per_post": 1,
        "primary_goal": "follows",
        "secondary_goal": "shares",
        "cta": "Dostuna göndər, ən yaxşı səsi seçsin.",
        "hook_style": "licensed supercar, racing or exhibition visual with unique engine sound",
        "publish_window": "Şənbə gecəsi 20:30 / 22:30 / 00:30 AZT",
        "visual_family": "car_spotting",
        "cover_family": "car_spotting",
        "target_duration_seconds": "7-12",
        "review_required": False,
        "hashtags": ["#azvscars", "#supercar", "#racing", "#carshow", "#baku", "#azerbaijan", "#cars"],
    },
}


SCHEDULED_SLOTS = {
    "mon_0900_buying": {
        "time_azt": "09:00",
        "cron_utc": "0 5 * * 1",
        "post_type": "quick",
        "name": "Monday buyer decision",
    },
    "tue_1300_market": {
        "time_azt": "13:00",
        "cron_utc": "0 9 * * 2",
        "post_type": "market",
        "name": "Tuesday market price check",
    },
    "wed_1930_main": {
        "time_azt": "19:30",
        "cron_utc": "30 15 * * 3",
        "post_type": "main",
        "name": "Wednesday buyer comparison",
    },
    "fri_1930_war": {
        "time_azt": "19:30",
        "cron_utc": "30 15 * * 5",
        "post_type": "war",
        "name": "Friday debate reel",
    },
    "sat_2030_supercar": {
        "time_azt": "20:30",
        "cron_utc": "30 16 * * 6",
        "post_type": "night_supercar",
        "name": "Saturday night supercar first drop",
    },
    "sat_2230_supercar": {
        "time_azt": "22:30",
        "cron_utc": "30 18 * * 6",
        "post_type": "night_supercar",
        "name": "Saturday night supercar second drop",
    },
    "sun_0030_supercar": {
        "time_azt": "00:30",
        "cron_utc": "30 20 * * 6",
        "post_type": "night_supercar",
        "name": "Saturday late-night supercar third drop",
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
