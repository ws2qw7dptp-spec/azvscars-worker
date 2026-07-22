const GRAPH_VERSION = "v25.0";

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export async function onRequestPost({ request, env }) {
  const body = await request.json().catch(() => ({}));
  const admin = request.headers.get("X-Admin-Password") || request.headers.get("x-admin-pass") || body.admin_pass || "";
  if (!env.ADMIN_PASS || admin !== env.ADMIN_PASS) {
    return json({ ok: false, error: "Unauthorized" }, 401);
  }

  const postId = String(body.post_id || "").trim();
  if (!/^\d{8,}$/.test(postId)) {
    return json({ ok: false, error: "Valid post_id is required." }, 400);
  }

  const token = env.META_ACCESS_TOKEN;
  if (!token) {
    return json({ ok: false, error: "META_ACCESS_TOKEN is not configured." }, 400);
  }

  const graphVersion = env.META_GRAPH_VERSION || GRAPH_VERSION;
  const url = `https://graph.facebook.com/${graphVersion}/${postId}`;
  const response = await fetch(url, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ access_token: token }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    return json({ ok: false, post_id: postId, graph_response: data }, response.status);
  }
  return json({ ok: true, post_id: postId, graph_response: data });
}
