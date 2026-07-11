# AZvsCars — Complete Content System

Avtomobil sahiblərini tərəf seçməyə çağıran Azərbaycan dilli Instagram sistemi: gündə dörd avtomatik post, mübahisəli müqayisələr, təmiz vizual stil və şərh gətirən caption-lar.

---

## 1. The 5 Content Pillars

Rotate through these. Never post randomly — every post should belong to one of these five buckets, so followers know what they're getting and keep coming back.

| # | Pillar | What it is | Why people follow for it |
|---|--------|-----------|---------------------------|
| 1 | **Market Pulse** | "This week in the AZ car market" — price moves, which brand is rising/falling, import trends | Feels like insider knowledge, keeps people checking back |
| 2 | **Budget Breakdown** | "What $X gets you" — comparing 3-4 real cars at a price point | Directly useful to anyone car-shopping, highly saveable |
| 3 | **Spec Showdown** | Head-to-head: 2 models compared on price/engine/fuel/features | Sparks comments and arguments = engagement |
| 4 | **Buyer Survival Tips** | Import scams to avoid, inspection checklist, real cost of ownership (insurance/fuel/service) | Builds trust — you're protecting people, not just showing cars |
| 5 | **Culture/Reaction** | Trending car spotted in Baku, funny/relatable driving moments, local car culture | Pure engagement/reach driver, humanizes the page |

**Cari autopilot ritmi:** hər gün 4 post, Bakı vaxtı ilə:

| Saat | Format | Məqsəd |
|---|---|---|
| 09:00 | Sürücü Seçimi | Sürətli “hansını sürərdin?” mübahisəsi |
| 13:00 | Real Avto Döyüş | Əsas karusel müqayisəsi |
| 19:30 | Şərh Savaşı | Ən güclü tərəf seçdirən duel |
| 22:45 | Gecə Döyüşü | Emosional/performance yönümlü reel |

---

## 2. Exact Post Formats

### A. Carousel (main automated format)
- **Slide 1 (cover):** Two cars, one clear debate. The hook must make owners choose a side.
- **Slides 2-4:** Engine/power, 0-100 km/s, starting price.
- **Last slide:** Brand CTA with the current 4-post daily schedule: 09:00 / 13:00 / 19:30 / 22:45 Baku time.

### B. Controversial Matchups
Prioritize “owner tribes” rather than neutral spec-sheet pairs:
- China premium EV vs Mercedes/BMW
- Tesla tech vs German luxury
- Toyota/Lexus reliability vs German/Range Rover status
- Old V8 vs new hybrid
- American muscle vs European precision
- Korean value vs Japanese reliability

### C. Reels
- **Hook (0-2 sec):** Text on screen + spoken hook, no slow intro. Example: *"Bu maşın 3 ayda 40% ucuzlaşdı."*
- **Body (3-20 sec):** AI voiceover over a sequence of manufacturer photos/B-roll with Ken Burns (slow zoom) motion, synced text captions burned in (most people watch muted).
- **Close (last 2 sec):** One-line takeaway + "Follow" text overlay.
- Use trending audio at low volume under your voiceover when the format allows — this significantly helps reach.

---

## 3. Quality Standards (non-negotiable — this is what makes it look like a real brand, not a spam page)

**Visual identity — build once, reuse forever:**
- 1 logo/watermark, small, same corner, every single post
- 2 brand colors max (e.g., a dark charcoal + one accent color) + white/black text
- 2 fonts max: one bold display font for headlines, one clean font for data/body text
- Same template grid every time — same margins, same logo position, same layout skeleton. Recognizability is what makes someone stop scrolling and think "oh, this page again" — that's the follow trigger.

**Data integrity:**
- Never invent a number. Pull from real listings, manufacturer spec sheets, or published market reports, and keep a running note of where each figure came from.
- If you're not sure a number is right, don't post it — a wrong price/spec destroys trust in this niche fast, and trust is the entire product.

**Caption formula (every post):**
1. Hook line (repeats or sharpens the cover headline)
2. 2-3 sentences of real value/context
3. One question to drive comments
4. 5-8 hashtags: mix broad (#Azerbaijan #avtomobil) + specific (#avtobazar #maşınelanları)

---

## 4. Daily Autopilot Rhythm

GitHub Actions runs the posting pipeline automatically.

- 09:00 Bakı — Sürücü Seçimi
- 13:00 Bakı — Real Avto Döyüş
- 19:30 Bakı — Şərh Savaşı
- 22:45 Bakı — Gecə Döyüşü

Manual triggering from the dashboard should use the same four formats. The post generator should not advertise old times or older weekly rhythm.

---

## 5. What's Safe to Automate vs. What Needs a Human Touch

| Task | Automate? |
|---|---|
| Writing captions/scripts from data you provide | Yes — AI does this well |
| Generating the data-card/carousel graphics | Yes — script below does this |
| Voiceover for reels | Yes — AI voice tools |
| Scheduling/posting | Yes — GitHub Actions + Cloudflare Pages |
| Sourcing accurate car data/prices | **No** — pull from real public listings/manufacturer sites yourself, don't let AI invent numbers |
| Final read-through before posting | **No** — always eyeball each post for accuracy before it goes out; a factual mistake in this niche is the fastest way to lose trust |

---

## 6. Growth Mechanics Specific to This Niche
- **Saves > likes** for the algorithm — Budget Breakdown and Spec Showdown posts get saved because people reference them later when actually shopping. Lean into these formats.
- **Comments-bait works honestly here** — "Which one would you buy?" under a Spec Showdown genuinely drives replies without feeling forced.
- **Repost-ability** — people share Budget Breakdown posts to friends who are car shopping. Make slide 1 work even as a screenshot shared out of context.
