const SLIDE_KEYS = [
    "slide1_cover.png", "slide2_power.png", "slide3_speed.png",
    "slide4_price.png", "slide5_outro.png",
];

function normalizeSlideUrls(meta, baseUrl, sid) {
  // Prefer the stable Pages/R2 proxy. Worker-generated R2 presigned URLs expire.
  return SLIDE_KEYS.map(k => `${baseUrl}/api/image/${sid}/${k}`);
}

export async function onRequestGet({ request, env, params }) {
  const kv = env.AZVSCARS_KV;
  const sid = params.sid;
  
  const meta = await kv.get(`session:${sid}`, "json");
  if (!meta) {
    return new Response(JSON.stringify({ error: "Session tapılmadı" }), { status: 404 });
  }

  const url = new URL(request.url);
  const base_url = `${url.protocol}//${url.host}`;
  const slides = normalizeSlideUrls(meta, base_url, sid);
  
  let reel_url = meta.reel_url;
  if (!reel_url && meta.data) {
      // Fallback
      reel_url = `${base_url}/api/image/${sid}/reel.mp4`;
  } else if (reel_url) {
      reel_url = `${base_url}/api/image/${sid}/reel.mp4`;
  }

  const published = meta.published || {};
  const hasTypedPublishState = Object.keys(published).length > 0;
  const carousel_published = hasTypedPublishState ? Boolean(published.carousel) : Boolean(meta.is_published);
  const reel_published = Boolean(published.reel);

  return new Response(JSON.stringify({
    sid: sid,
    car1_name: meta.car1_name || "Avtomobil 1",
    car2_name: meta.car2_name || "Avtomobil 2",
    flip1: meta.flip1 || false,
    flip2: meta.flip2 || false,
    caption: meta.caption || "",
    slides: slides,
    reel_url: reel_url,
    is_published: Boolean(carousel_published || reel_published),
    carousel_published,
    reel_published,
  }), { headers: { "Content-Type": "application/json" } });
}

export async function onRequestDelete({ env, params }) {
  const kv = env.AZVSCARS_KV;
  const sid = params.sid;
  
  // Delete session data
  await kv.delete(`session:${sid}`);
  
  // Update index
  let index = await kv.get("sessions:index", "json");
  if (index && Array.isArray(index)) {
    index = index.filter(s => s.sid !== sid);
    await kv.put("sessions:index", JSON.stringify(index));
  }
  
  return new Response(JSON.stringify({ ok: true }), { headers: { "Content-Type": "application/json" } });
}
