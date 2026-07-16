/**
 * POST /api/publish/[sid]
 * Publishes a post (carousel, reel or story) directly to Instagram via Meta Graph API.
 * This runs inside Cloudflare Functions — no Python server needed.
 */

const SLIDE_KEYS = [
  "slide1_cover.png", "slide2_power.png", "slide3_speed.png",
  "slide4_price.png", "slide5_outro.png",
];

const GRAPH_VERSION = "v25.0";
const MIN_FEED_GAP_MS = 4 * 60 * 60 * 1000;
const MAX_FEED_POSTS_PER_DAY = 2;
const DEFAULT_HASHTAGS = "#azvscars #azerbaycan #baku #avto #masin #avtomobil #avtobazar";

async function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

function proxiedUrl(baseUrl, sid, file) {
  return `${baseUrl}/api/image/${sid}/${file}`;
}

function normalizeSlideUrls(meta, baseUrl, sid) {
  // Publish via the stable Pages/R2 proxy. Worker-generated R2 presigned URLs
  // expire after a few days and break delayed publishing.
  return SLIDE_KEYS.map(k => proxiedUrl(baseUrl, sid, k));
}

function storyUrl(meta, baseUrl, sid, file) {
  const storyFile = file || "story1_brand.jpg";
  if (!/^[a-zA-Z0-9_.-]+$/.test(storyFile)) {
    throw new Error("Story fayl adı yanlışdır.");
  }
  const known = meta.story_urls || {};
  return known[storyFile] || proxiedUrl(baseUrl, sid, storyFile);
}

function parseSessionDate(value) {
  const raw = String(value || "").trim();
  if (!raw) return null;
  const isoLike = raw.includes("T") ? raw : raw.replace(" ", "T");
  const date = new Date(isoLike);
  return Number.isNaN(date.getTime()) ? null : date;
}

function bakuDateKey(date = new Date()) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Baku",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(date).reduce((acc, part) => {
    acc[part.type] = part.value;
    return acc;
  }, {});
  return `${parts.year}-${parts.month}-${parts.day}`;
}

function validateFeedCadence(index, sid, mediaType) {
  if (mediaType === "story") return null;
  const publishedFeed = (Array.isArray(index) ? index : [])
    .filter((item) => item.sid !== sid)
    .filter((item) => Boolean(item?.published?.carousel || item?.published?.reel));

  const now = new Date();
  const todayKey = bakuDateKey(now);
  const todayFeedCount = publishedFeed.filter((item) => {
    const created = parseSessionDate(item.created_at);
    return created && bakuDateKey(created) === todayKey;
  }).length;

  if (todayFeedCount >= MAX_FEED_POSTS_PER_DAY) {
    return `Bu gün üçün feed limiti dolub. Audit qaydasına görə maksimum ${MAX_FEED_POSTS_PER_DAY} feed post paylaşılır.`;
  }

  const latestPublishedAt = publishedFeed
    .flatMap((item) => [item?.published?.carousel?.published_at, item?.published?.reel?.published_at])
    .map((value) => parseSessionDate(value))
    .filter(Boolean)
    .sort((a, b) => b.getTime() - a.getTime())[0];

  if (!latestPublishedAt) return null;

  const diff = now.getTime() - latestPublishedAt.getTime();
  if (diff >= MIN_FEED_GAP_MS) return null;

  const waitMinutes = Math.ceil((MIN_FEED_GAP_MS - diff) / 60000);
  return `Son feed post çox yenidir. Yeni paylaşım üçün ən az 4 saat ara saxlanmalıdır. Təxminən ${waitMinutes} dəqiqə sonra yenidən cəhd et.`;
}

function cleanText(value) {
  return String(value || "")
    .replace(/\r/g, "")
    .replace(/\s+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .replace(/[ \t]{2,}/g, " ")
    .replace(/komment/gi, "şərh")
    .trim();
}

function engagementLine(postType) {
  if (postType === "quick") return "Bu reel sürətli şərh və tag almaq üçün optimizasiya olunub.";
  if (postType === "war") return "Bu reel paylaşım və alovlu şərh üçün optimizasiya olunub.";
  if (postType === "night") return "Bu reel bəyənmə, paylaşım və fanat reaksiyası üçün optimizasiya olunub.";
  if (postType === "cinematic") return "Bu reel bəyənmə, paylaşım və saxlanma üçün optimizasiya olunub.";
  if (postType === "market") return "Bu reel saxlanma, paylaşım və real bazar müzakirəsi üçün optimizasiya olunub.";
  return "Bu post şərh, paylaşım və saxlanma balansı üçün optimizasiya olunub.";
}

function nonQuestionCta(postType, meta) {
  const car1 = meta.car1_name || "sol maşın";
  const car2 = meta.car2_name || "sağ maşın";
  if (postType === "quick") return `${car1} seçən dostu tag et.`;
  if (postType === "war") return `${car2} tərəfdarı tanıyırsansa bu postu paylaş.`;
  if (postType === "night") return "Gecə sürüşünü sevən dosta bunu göndər.";
  if (postType === "cinematic") return "Video xoşuna gəldisə paylaş və yadda saxla.";
  if (postType === "market") return "Maşın axtaran dosta göndər və reel-i yadda saxla.";
  return "Qiymət müqayisəsi lazım olarsa postu yadda saxla.";
}

function ensureHashtags(text) {
  return /#azvscars/i.test(text) ? text : `${text}\n\n${DEFAULT_HASHTAGS}`.trim();
}

function buildAltText(meta, mediaType) {
  const data = meta.data || {};
  const title = data.battle_title || "AZvsCars müqayisəsi";
  const kind = mediaType === "reel" ? "Reel video" : "Karusel post";
  return cleanText(
    `${kind}: ${title}. Sol tərəfdə ${meta.car1_name || "birinci avtomobil"}, sağ tərəfdə ${meta.car2_name || "ikinci avtomobil"}. ` +
    `Güc: ${data.slide2_car1_stat || ""} və ${data.slide2_car2_stat || ""}. ` +
    `Sürət: ${data.slide3_car1_stat || ""} və ${data.slide3_car2_stat || ""}. ` +
    `Qiymət: ${data.slide4_car1_stat || ""} və ${data.slide4_car2_stat || ""}.`
  );
}

function finalizePublishPayload(meta, rawCaption, mediaType) {
  const postType = meta.post_type || "main";
  const lines = cleanText(rawCaption).split("\n").map((line) => line.trim()).filter(Boolean);
  const textBody = lines.filter((line) => !line.startsWith("#")).join("\n");
  const requiredLines = [engagementLine(postType), nonQuestionCta(postType, meta)];
  let caption = textBody;
  for (const line of requiredLines) {
    if (!caption.toLowerCase().includes(line.toLowerCase())) {
      caption = `${caption}\n${line}`.trim();
    }
  }
  caption = ensureHashtags(cleanText(caption));
  const altText = cleanText(meta.alt_text || meta.image_description || buildAltText(meta, mediaType));
  return {
    caption,
    alt_text: altText,
    image_description: altText,
    publish_strategy: {
      optimized_at: new Date().toISOString(),
      media_type: mediaType,
      engagement_focus: engagementLine(postType),
      cta_focus: nonQuestionCta(postType, meta),
    },
  };
}

export async function onRequestPost({ request, env, params }) {
  const sid = params.sid;
  const kv = env.AZVSCARS_KV;

  const meta = await kv.get(`session:${sid}`, "json");
  if (!meta) {
    return new Response(JSON.stringify({ error: "Session tapılmadı" }), { status: 404, headers: { "Content-Type": "application/json" } });
  }

  const body = await request.json().catch(() => ({}));
  const media_type = body.media_type || "carousel";
  const publishKey = media_type === "story" ? `story:${body.story_file || "story1_brand.jpg"}` : media_type;
  const index = await kv.get("sessions:index", "json");
  const cadenceError = validateFeedCadence(index, sid, media_type);
  if (cadenceError) {
    return new Response(JSON.stringify({ error: cadenceError }), {
      status: 409,
      headers: { "Content-Type": "application/json" },
    });
  }

  if (meta.published?.[publishKey]) {
    return new Response(JSON.stringify({
      ok: true,
      already_published: true,
      post_id: meta.published[publishKey].post_id,
      message: "Bu media artıq paylaşılıb. Təkrar paylaşım dayandırıldı.",
    }), { headers: { "Content-Type": "application/json" } });
  }

  const ig_token = env.META_ACCESS_TOKEN;
  const ig_user_id = env.INSTAGRAM_ACCOUNT_ID;
  const url = new URL(request.url);
  const base_url = `${url.protocol}//${url.host}`;
  const graphVersion = env.META_GRAPH_VERSION || GRAPH_VERSION;
  const optimized = finalizePublishPayload(meta, body.caption || meta.caption || "", media_type);
  const caption = optimized.caption;

  if (!ig_token || !ig_user_id) {
    return new Response(JSON.stringify({ error: "META_ACCESS_TOKEN veya INSTAGRAM_ACCOUNT_ID ayarlanmayıb." }), { status: 400, headers: { "Content-Type": "application/json" } });
  }

  const api_base = `https://graph.facebook.com/${graphVersion}/${ig_user_id}`;

  try {
    let post_id;

    if (media_type === "story") {
      const image_url = storyUrl(meta, base_url, sid, body.story_file);

      // Step 1: Create STORIES container
      const r1 = await fetch(`${api_base}/media`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          media_type: "STORIES",
          image_url,
          access_token: ig_token,
        })
      });
      const d1 = await r1.json();
      if (!r1.ok) throw new Error(JSON.stringify(d1));
      const container_id = d1.id;

      // Step 2: Publish
      await sleep(2000);
      const r2 = await fetch(`${api_base}/media_publish`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ creation_id: container_id, access_token: ig_token })
      });
      const d2 = await r2.json();
      if (!r2.ok) throw new Error(JSON.stringify(d2));
      post_id = d2.id || "?";

    } else if (media_type === "reel") {
      const reel_url = proxiedUrl(base_url, sid, "reel.mp4");

      // Step 1: Create REELS container
      const r1 = await fetch(`${api_base}/media`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          media_type: "REELS",
          video_url: reel_url,
          caption: caption,
          share_to_feed: "true",
          access_token: ig_token,
        })
      });
      const d1 = await r1.json();
      if (!r1.ok) throw new Error(JSON.stringify(d1));
      const container_id = d1.id;

      // Step 2: Poll until FINISHED (max 120s)
      let tries = 0;
      while (tries < 40) {
        await sleep(3000);
        const status_res = await fetch(
          `https://graph.facebook.com/${graphVersion}/${container_id}?fields=status_code&access_token=${ig_token}`
        );
        const sd = await status_res.json();
        if (sd.status_code === "FINISHED") break;
        if (sd.status_code === "ERROR") throw new Error("Instagram Reels processing xətası.");
        tries++;
      }

      // Step 3: Publish
      const r3 = await fetch(`${api_base}/media_publish`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ creation_id: container_id, access_token: ig_token })
      });
      const d3 = await r3.json();
      if (!r3.ok) throw new Error(JSON.stringify(d3));
      post_id = d3.id || "?";

    } else {
      // CAROUSEL
      const slide_urls = normalizeSlideUrls(meta, base_url, sid);
      if (slide_urls.length < 2) {
        throw new Error("Carousel üçün ən az 2 slayd lazımdır.");
      }

      // Step 1: Create container for each slide
      const container_ids = [];
      for (const url of slide_urls) {
        const r = await fetch(`${api_base}/media`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            image_url: url,
            is_carousel_item: "true",
            access_token: ig_token,
          })
        });
        const d = await r.json();
        if (!r.ok) throw new Error(JSON.stringify(d));
        container_ids.push(d.id);
        await sleep(1000);
      }

      // Step 2: Create carousel container
      const r2 = await fetch(`${api_base}/media`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          media_type: "CAROUSEL",
          children: container_ids.join(","),
          caption: caption,
          access_token: ig_token,
        })
      });
      const d2 = await r2.json();
      if (!r2.ok) throw new Error(JSON.stringify(d2));
      const carousel_id = d2.id;

      // Step 3: Publish
      await sleep(2000);
      const r3 = await fetch(`${api_base}/media_publish`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ creation_id: carousel_id, access_token: ig_token })
      });
      const d3 = await r3.json();
      if (!r3.ok) throw new Error(JSON.stringify(d3));
      post_id = d3.id || "?";
    }

    // Mark this media type as published in KV.
    meta.caption = caption;
    meta.alt_text = optimized.alt_text;
    meta.image_description = optimized.image_description;
    meta.publish_strategy = optimized.publish_strategy;
    meta.published = meta.published || {};
    meta.published[publishKey] = {
      post_id,
      published_at: new Date().toISOString(),
    };
    meta.is_published = Boolean(meta.published.carousel || meta.published.reel);
    await kv.put(`session:${sid}`, JSON.stringify(meta));
    
    // Also update index
    let index = await kv.get("sessions:index", "json");
    if (index && Array.isArray(index)) {
      const idx = index.findIndex(s => s.sid === sid);
      if (idx !== -1) {
        index[idx].is_published = Boolean(meta.is_published || media_type === "story");
        index[idx].published = meta.published;
        index[idx].story_slot = meta.story_slot || index[idx].story_slot || "";
        index[idx].publish_strategy = meta.publish_strategy || index[idx].publish_strategy || {};
        await kv.put("sessions:index", JSON.stringify(index));
      }
    }

    return new Response(JSON.stringify({
      ok: true,
      post_id: post_id,
      message: `✅ Post uğurla paylaşıldı! ID: ${post_id}`
    }), { headers: { "Content-Type": "application/json" } });

  } catch (e) {
    return new Response(JSON.stringify({ error: `Meta API xətası: ${e.message}` }), {
      status: 500,
      headers: { "Content-Type": "application/json" }
    });
  }
}
