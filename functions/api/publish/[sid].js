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

export async function onRequestPost({ request, env, params }) {
  const sid = params.sid;
  const kv = env.AZVSCARS_KV;

  const meta = await kv.get(`session:${sid}`, "json");
  if (!meta) {
    return new Response(JSON.stringify({ error: "Session tapılmadı" }), { status: 404, headers: { "Content-Type": "application/json" } });
  }

  const body = await request.json().catch(() => ({}));
  const caption = body.caption || meta.caption || "";
  const media_type = body.media_type || "carousel";

  const ig_token = env.META_ACCESS_TOKEN;
  const ig_user_id = env.INSTAGRAM_ACCOUNT_ID;
  const url = new URL(request.url);
  const base_url = `${url.protocol}//${url.host}`;
  const graphVersion = env.META_GRAPH_VERSION || GRAPH_VERSION;

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
    meta.published = meta.published || {};
    meta.published[media_type] = {
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
        index[idx].is_published = true;
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
