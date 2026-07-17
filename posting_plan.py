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
        "label": "Sürücü Seçimi",
        "series": "daily_driver_choice",
        "pillar": "comment_debate",
        "format": "clean_comparison_reel",
        "cars_per_post": 2,
        "primary_goal": "comments",
        "secondary_goal": "shares",
        "cta": "Hansını öz pulunla alardın? Səbəbini yaz.",
        "hook_style": "daily choice with a clear buyer decision",
        "publish_window": "09:00 AZT",
        "hashtags": ["#azvscars", "#avto", "#masin", "#baku", "#azerbaycan", "#avtomobil"],
    },
    "main": {
        "label": "Real Avto Döyüş",
        "series": "real_buyer_battle",
        "pillar": "save_share_value",
        "format": "clean_comparison_reel",
        "cars_per_post": 2,
        "primary_goal": "saves",
        "secondary_goal": "shares",
        "cta": "Maşın axtaran dosta göndər və real seçim səbəbini yaz.",
        "hook_style": "Baku buyer logic: price, service, resale, daily use",
        "publish_window": "13:00 AZT",
        "hashtags": ["#azvscars", "#avtobazar", "#bakucars", "#masin", "#azerbaycan", "#avtomobil"],
    },
    "war": {
        "label": "Şərh Savaşı",
        "series": "comment_war",
        "pillar": "fanbase_argument",
        "format": "clean_comparison_reel",
        "cars_per_post": 2,
        "primary_goal": "comments",
        "secondary_goal": "replays",
        "cta": "Tərəfini seç və qısa yox, səbəb yaz.",
        "hook_style": "polarizing brand or engine argument",
        "publish_window": "19:30 AZT",
        "hashtags": ["#azvscars", "#carbattle", "#avto", "#masin", "#baku", "#azerbaycan"],
    },
    "night": {
        "label": "Gecə Döyüşü",
        "series": "night_driver_battle",
        "pillar": "emotion_sound_visuals",
        "format": "clean_comparison_reel",
        "cars_per_post": 2,
        "primary_goal": "likes",
        "secondary_goal": "shares",
        "cta": "Gecə açar səndə olsa hansını götürərdin?",
        "hook_style": "night-drive emotion and fan identity",
        "publish_window": "manual",
        "hashtags": ["#azvscars", "#nightdrive", "#avto", "#masin", "#baku", "#cars"],
    },
    "market": {
        "label": "Bakı Market",
        "series": "baku_market_price_check",
        "pillar": "save_share_utility",
        "format": "one_car_price_reel",
        "cars_per_post": 1,
        "primary_goal": "saves",
        "secondary_goal": "shares",
        "cta": "Bu qiymətə alınar, yoxsa pass? Maşın axtaran dosta göndər.",
        "hook_style": "one real market car with AZN price",
        "publish_window": "manual",
        "hashtags": ["#azvscars", "#avtobazar", "#masinqiymeti", "#turboaz", "#baku", "#azerbaycan"],
    },
    "night_supercar": {
        "label": "Night Supercar",
        "series": "night_supercar_special",
        "pillar": "replay_follow_growth",
        "format": "clean_supercar_reel",
        "cars_per_post": 1,
        "primary_goal": "follows",
        "secondary_goal": "replays",
        "cta": "FOLLOW @azvscars",
        "hook_style": "supercar/racing/exhibition visuals with unique engine sound",
        "publish_window": "20:30 / 22:30 / 00:30 AZT",
        "hashtags": ["#azvscars", "#supercar", "#racing", "#carshow", "#baku", "#azerbaijan", "#cars"],
    },
}


SCHEDULED_SLOTS = {
    "0900_quick": {
        "time_azt": "09:00",
        "cron_utc": "0 5 * * *",
        "post_type": "quick",
        "name": "Morning driver choice",
    },
    "1300_main": {
        "time_azt": "13:00",
        "cron_utc": "0 9 * * *",
        "post_type": "main",
        "name": "Midday buyer battle",
    },
    "1930_war": {
        "time_azt": "19:30",
        "cron_utc": "30 15 * * *",
        "post_type": "war",
        "name": "Evening comment war",
    },
    "2030_supercar": {
        "time_azt": "20:30",
        "cron_utc": "30 16 * * *",
        "post_type": "night_supercar",
        "name": "Night supercar first drop",
    },
    "2230_supercar": {
        "time_azt": "22:30",
        "cron_utc": "30 18 * * *",
        "post_type": "night_supercar",
        "name": "Night supercar second drop",
    },
    "0030_supercar": {
        "time_azt": "00:30",
        "cron_utc": "30 20 * * *",
        "post_type": "night_supercar",
        "name": "Night supercar late drop",
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
        "video_rules": VIDEO_RULES,
        "quality_rules": [
            "one_featured_car_per_reel_except_comparison",
            "fresh_media_assets",
            "fresh_audio_assets",
            "azn_price_when_price_is_shown",
            "no_old_slide_design_for_reels",
            "caption_has_comment_or_share_reason",
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
        "metadata_version": "2026-07-17-clean-reels-v2",
    }
