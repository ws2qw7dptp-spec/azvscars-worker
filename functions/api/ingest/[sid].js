/**
 * POST /api/ingest/[sid]
 * Accepts generated media from GitHub Actions and stores it in R2/KV.
 * Protected by the global X-Admin-Password middleware.
 */

const MAX_FILE_BYTES = 25 * 1024 * 1024;

function decodeBase64(value) {
  const binary = atob(value);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

function cleanFileName(name) {
  if (!/^[a-zA-Z0-9_.-]+$/.test(name)) {
    throw new Error(`Invalid file name: ${name}`);
  }
  return name;
}

export async function onRequestPost({ request, env, params }) {
  const sid = params.sid;
  const body = await request.json().catch(() => null);
  if (!body || !body.meta || !body.files || typeof body.files !== "object") {
    return new Response(JSON.stringify({ error: "Invalid ingest payload" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  const bucket = env.AZVSCARS_R2;
  const kv = env.AZVSCARS_KV;
  if (!bucket || !kv) {
    return new Response(JSON.stringify({ error: "R2/KV binding missing" }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }

  const uploaded = {};
  try {
    for (const [rawName, file] of Object.entries(body.files)) {
      const fileName = cleanFileName(rawName);
      if (!file || typeof file.data_base64 !== "string") {
        throw new Error(`Missing file data: ${fileName}`);
      }
      const bytes = decodeBase64(file.data_base64);
      if (bytes.byteLength > MAX_FILE_BYTES) {
        throw new Error(`File too large: ${fileName}`);
      }
      const contentType = file.content_type || "application/octet-stream";
      const key = `${sid}/${fileName}`;
      await bucket.put(key, bytes, {
        httpMetadata: { contentType },
      });
      uploaded[fileName] = `/api/image/${sid}/${fileName}`;
    }

    const url = new URL(request.url);
    const baseUrl = `${url.protocol}//${url.host}`;
    const meta = {
      ...body.meta,
      sid,
      slide_urls: body.meta.slide_urls || {},
      reel_url: body.meta.reel_url || null,
      is_published: Boolean(body.meta.is_published),
    };

    for (const name of Object.keys(uploaded)) {
      if (name.endsWith(".png")) {
        meta.slide_urls[name] = `${baseUrl}/api/image/${sid}/${name}`;
      }
      if (name === "reel.mp4") {
        meta.reel_url = `${baseUrl}/api/image/${sid}/reel.mp4`;
      }
    }

    await kv.put(`session:${sid}`, JSON.stringify(meta));

    let index = await kv.get("sessions:index", "json");
    if (!Array.isArray(index)) index = [];
    index = index.filter(s => s.sid !== sid);
    index.unshift({
      sid,
      post_type: meta.post_type || "",
      car1: meta.car1_name || "",
      car2: meta.car2_name || "",
      created_at: meta.created_at || "",
      is_published: Boolean(meta.is_published),
      published: meta.published || {},
    });
    await kv.put("sessions:index", JSON.stringify(index.slice(0, 500)));

    return new Response(JSON.stringify({ ok: true, sid, uploaded: Object.keys(uploaded) }), {
      headers: { "Content-Type": "application/json" },
    });
  } catch (e) {
    return new Response(JSON.stringify({ error: e.message }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
}
