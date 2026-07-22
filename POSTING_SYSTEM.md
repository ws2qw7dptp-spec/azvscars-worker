# AZVSCARS Posting System

## Weekly Schedule

All feed posts are Reels. Times are Asia/Baku. The system now favors 9 testable feed publications per week, capped at 2 feed posts per day, mostly in Monday-Friday high-probability Instagram windows.

| Slot | Time | Type | Format | Goal |
| --- | --- | --- | --- | --- |
| `mon_1510_buying` | Monday 15:10 | `quick` | Clean buyer-decision Reel | shares + comments |
| `tue_1320_market` | Tuesday 13:20 | `market` | One-car market Reel | saves + shares |
| `tue_1910_debate` | Tuesday 19:10 | `war` | Meaningful debate Reel | comments + shares |
| `wed_1240_main` | Wednesday 12:40 | `main` | Clean buyer-comparison Reel | saves + shares |
| `wed_2300_supercar` | Wednesday 23:00 | `night_supercar` | Car-only supercar Reel | follows + shares |
| `thu_1220_market` | Thursday 12:20 | `market` | One-car market Reel | saves + shares |
| `thu_2030_supercar` | Thursday 20:30 | `night_supercar` | Car-only supercar Reel | follows + shares |
| `fri_1330_war` | Friday 13:30 | `war` | Meaningful debate Reel | comments + shares |
| `fri_2230_supercar` | Friday 22:30 | `night_supercar` | Car-only supercar Reel | follows + shares |

Manual-only type:

| Type | Format | Rule |
| --- | --- | --- |
| `market` | One-car price Reel | Show one car, AZN price, source, check date, and price type |

## Story Schedule

Stories are support content, not repeated filler. The generator renders 10 rotating cards every run and scheduled workflows publish only the useful subset for that time of day.

| Time | Files | Goal |
| --- | --- | --- |
| 08:45 | `story1_brand`, `story9_daily_duel`, `story2_schedule` | daily hook, poll-style choice, accurate plan |
| 14:30 | `story10_daily_question`, `story3_topics`, `story6_china_germany` | buyer question, topic seed, debate prompt |
| 20:45 | `story5_comment`, `story8_suv_war`, `story4_contact` | serious comments, share prompt, collaboration/DM |

Story rules:

- No repeated "generic reminder" cards without a question, poll, topic, or collaboration purpose.
- Collaboration story must ask for full-car media, model/year/engine/mileage, AZN price, city, and no people in frame.
- Story text should point viewers back to the next Reel or invite them to send a car/topic.

## Creative Rules

- Every feed post is 1080x1920, 9:16, 30fps.
- Every Reel uses the clean AZVSCARS visual system: top-left logo, simple detail panel, final VS logo + `FOLLOW @azvscars`.
- No old bottom-card, carousel, Canva-style, or fake time overlays in Reels.
- One car per Reel unless the type is a comparison type: `quick`, `main`, `war`, or `night`.
- `night_supercar` uses car-only licensed clips. No people, women, hands, crowds, detailing, or event/spectator footage.
- Market posts show AZN prices, source labeling, and check dates.
- Captions use one primary CTA only.
- Captions must include one clear reason to follow, not just a voting question.
- The worker checks the last 20 posts for model overuse and visual family repetition.
- Low-confidence market or rights cases must fail before auto-publish.
- Track growth using `profile_visits / reach`, `follows / profile_visits`, `sends`, `saves`, and 3-second retention. Likes alone are not a success metric.

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
