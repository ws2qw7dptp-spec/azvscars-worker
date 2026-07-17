# AZVSCARS Posting System

## Daily Schedule

All feed posts are Reels. Times are Asia/Baku.

| Slot | Time | Type | Format | Goal |
| --- | --- | --- | --- | --- |
| `0900_quick` | 09:00 | `quick` | Clean comparison Reel | comments + shares |
| `1300_main` | 13:00 | `main` | Clean comparison Reel | saves + shares |
| `1930_war` | 19:30 | `war` | Clean comparison Reel | comments + replays |
| `2030_supercar` | 20:30 | `night_supercar` | Supercar sound Reel | follows + replays |
| `2230_supercar` | 22:30 | `night_supercar` | Supercar sound Reel | follows + replays |
| `0030_supercar` | 00:30 | `night_supercar` | Supercar sound Reel | follows + replays |

Manual-only type:

| Type | Format | Rule |
| --- | --- | --- |
| `market` | One-car price Reel | Show one car, AZN price, clean follow card |

## Creative Rules

- Every feed post is 1080x1920, 9:16, 30fps.
- Every Reel uses the clean AZVSCARS visual system: top-left logo, simple detail panel, final VS logo + `FOLLOW @azvscars`.
- No old bottom-card, carousel, Canva-style, or fake time overlays in Reels.
- One car per Reel unless the type is a comparison type: `quick`, `main`, `war`, or `night`.
- `night_supercar` uses real supercar/racing/exhibition clips and fresh car sounds.
- Market posts show AZN prices and are designed for save/share behavior.

## Metadata Contract

Every generated session should include:

- `post_type`
- `content_series`
- `posting_slot`
- `posting_time_azt`
- `posting_label`
- `metadata_version`
- `publish_strategy`
- `source_assets`
- `alt_text`
- `image_description`

The canonical source is `posting_plan.py`.
