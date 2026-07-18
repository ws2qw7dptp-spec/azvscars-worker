# AZVSCARS Posting System

## Weekly Schedule

All feed posts are Reels. Times are Asia/Baku. The system now favors 5-7 higher-quality feed publications per week instead of repetitive daily spam.

| Slot | Time | Type | Format | Goal |
| --- | --- | --- | --- | --- |
| `mon_0900_buying` | Monday 09:00 | `quick` | Clean buyer-decision Reel | shares + comments |
| `tue_1300_market` | Tuesday 13:00 | `market` | One-car market Reel | saves + shares |
| `wed_1930_main` | Wednesday 19:30 | `main` | Clean buyer-comparison Reel | saves + shares |
| `fri_1930_war` | Friday 19:30 | `war` | Meaningful debate Reel | comments + shares |
| `sat_2030_supercar` | Saturday 20:30 | `night_supercar` | Supercar special Reel | follows + shares |
| `sat_2230_supercar` | Saturday 22:30 | `night_supercar` | Supercar special Reel | follows + shares |
| `sun_0030_supercar` | Sunday 00:30 | `night_supercar` | Supercar special Reel | follows + shares |

Manual-only type:

| Type | Format | Rule |
| --- | --- | --- |
| `market` | One-car price Reel | Show one car, AZN price, source, check date, and price type |

## Creative Rules

- Every feed post is 1080x1920, 9:16, 30fps.
- Every Reel uses the clean AZVSCARS visual system: top-left logo, simple detail panel, final VS logo + `FOLLOW @azvscars`.
- No old bottom-card, carousel, Canva-style, or fake time overlays in Reels.
- One car per Reel unless the type is a comparison type: `quick`, `main`, `war`, or `night`.
- `night_supercar` uses real supercar/racing/exhibition clips and fresh car sounds.
- Market posts show AZN prices, source labeling, and check dates.
- Captions use one primary CTA only.
- The worker checks the last 20 posts for model overuse and visual family repetition.
- Low-confidence market or rights cases must fail before auto-publish.

## Metadata Contract

Every generated session should include:

- `post_type`
- `content_series`
- `posting_slot`
- `posting_time_azt`
- `posting_label`
- `metadata_version`
- `publish_strategy`
- `analytics`
- `quality_report`
- `source_assets`
- `alt_text`
- `image_description`

The canonical source is `posting_plan.py`.
