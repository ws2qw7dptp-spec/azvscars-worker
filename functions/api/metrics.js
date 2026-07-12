const GB = 1024 * 1024 * 1024;

async function listUsage(bucket) {
  let cursor;
  let bytes = 0;
  let objects = 0;
  do {
    const page = await bucket.list({ limit: 1000, cursor });
    for (const object of page.objects) bytes += object.size || 0;
    objects += page.objects.length;
    cursor = page.truncated ? page.cursor : undefined;
  } while (cursor);
  return { bytes, objects };
}

export async function onRequestGet({ env }) {
  if (!env.AZVSCARS_R2 || !env.AZVSCARS_KV) {
    return new Response(JSON.stringify({ error: "R2/KV binding missing" }), { status: 500 });
  }
  const usage = await listUsage(env.AZVSCARS_R2);
  const sessions = await env.AZVSCARS_KV.get("sessions:index", "json");
  const index = Array.isArray(sessions) ? sessions : [];
  const published = index.filter(item => item.is_published || Object.keys(item.published || {}).length).length;
  return new Response(JSON.stringify({
    r2_bytes: usage.bytes,
    r2_gb: Number((usage.bytes / GB).toFixed(3)),
    r2_percent_of_free_10gb: Number((usage.bytes / (10 * GB) * 100).toFixed(1)),
    objects: usage.objects,
    sessions: index.length,
    published,
    cleanup_threshold_gb: 8.5,
    cleanup_target_gb: 5,
  }), { headers: { "Content-Type": "application/json" } });
}
