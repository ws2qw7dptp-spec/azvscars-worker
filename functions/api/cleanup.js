const DEFAULT_THRESHOLD_GB = 8.5;
const DEFAULT_TARGET_GB = 5.0;
const DEFAULT_MIN_KEEP_DAYS = 45;
const GB = 1024 * 1024 * 1024;

function numberParam(url, name, fallback, min, max) {
  const value = Number(url.searchParams.get(name));
  if (!Number.isFinite(value)) return fallback;
  return Math.min(max, Math.max(min, value));
}

function sessionIdFromKey(key) {
  const idx = key.indexOf("/");
  return idx > 0 ? key.slice(0, idx) : "";
}

function parseCreatedAt(value) {
  const text = String(value || "").trim();
  if (!text) return 0;
  const normalized = text.includes("T") ? text : text.replace(" ", "T");
  const parsed = Date.parse(`${normalized}+04:00`);
  return Number.isFinite(parsed) ? parsed : 0;
}

async function listAllObjects(bucket) {
  const objects = [];
  let cursor = undefined;
  do {
    const page = await bucket.list({ limit: 1000, cursor });
    objects.push(...page.objects);
    cursor = page.truncated ? page.cursor : undefined;
  } while (cursor);
  return objects;
}

async function deleteInBatches(bucket, keys) {
  const batchSize = 500;
  for (let i = 0; i < keys.length; i += batchSize) {
    await bucket.delete(keys.slice(i, i + batchSize));
  }
}

export async function onRequestPost({ request, env }) {
  const bucket = env.AZVSCARS_R2;
  const kv = env.AZVSCARS_KV;
  if (!bucket || !kv) {
    return new Response(JSON.stringify({ error: "R2/KV binding missing" }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }

  const url = new URL(request.url);
  const thresholdGb = numberParam(url, "threshold_gb", DEFAULT_THRESHOLD_GB, 1, 9.8);
  const targetGb = numberParam(url, "target_gb", DEFAULT_TARGET_GB, 0.5, thresholdGb);
  const minKeepDays = numberParam(url, "min_keep_days", DEFAULT_MIN_KEEP_DAYS, 1, 365);
  const dryRun = url.searchParams.get("dry_run") === "true";

  const objects = await listAllObjects(bucket);
  const totalBytes = objects.reduce((sum, object) => sum + (object.size || 0), 0);
  const thresholdBytes = thresholdGb * GB;
  const targetBytes = targetGb * GB;

  const index = await kv.get("sessions:index", "json");
  const sessions = Array.isArray(index) ? index : [];
  const sessionDates = new Map(sessions.map((session) => [session.sid, parseCreatedAt(session.created_at)]));
  const groups = new Map();

  for (const object of objects) {
    const sid = sessionIdFromKey(object.key);
    if (!sid) continue;
    if (!groups.has(sid)) {
      groups.set(sid, { sid, keys: [], bytes: 0, uploadedMs: 0, createdMs: sessionDates.get(sid) || 0 });
    }
    const group = groups.get(sid);
    group.keys.push(object.key);
    group.bytes += object.size || 0;
    const uploadedMs = object.uploaded ? new Date(object.uploaded).getTime() : 0;
    group.uploadedMs = Math.max(group.uploadedMs, Number.isFinite(uploadedMs) ? uploadedMs : 0);
  }

  if (totalBytes < thresholdBytes) {
    return new Response(JSON.stringify({
      ok: true,
      action: "none",
      total_bytes: totalBytes,
      total_gb: Number((totalBytes / GB).toFixed(3)),
      threshold_gb: thresholdGb,
      target_gb: targetGb,
      message: "R2 storage is below cleanup threshold.",
    }), { headers: { "Content-Type": "application/json" } });
  }

  const cutoffMs = Date.now() - minKeepDays * 24 * 60 * 60 * 1000;
  const candidates = [...groups.values()]
    .map((group) => ({ ...group, sortMs: group.createdMs || group.uploadedMs || 0 }))
    .filter((group) => group.sortMs < cutoffMs)
    .sort((a, b) => a.sortMs - b.sortMs);

  let projectedBytes = totalBytes;
  const selected = [];
  for (const group of candidates) {
    if (projectedBytes <= targetBytes) break;
    selected.push(group);
    projectedBytes -= group.bytes;
  }

  const deleteKeys = selected.flatMap((group) => group.keys);
  if (!dryRun && deleteKeys.length) {
    await deleteInBatches(bucket, deleteKeys);
    for (const group of selected) {
      await kv.delete(`session:${group.sid}`);
      await kv.delete(`status_${group.sid}`);
    }
    const deletedSids = new Set(selected.map((group) => group.sid));
    await kv.put("sessions:index", JSON.stringify(sessions.filter((session) => !deletedSids.has(session.sid))));
  }

  return new Response(JSON.stringify({
    ok: true,
    action: dryRun ? "dry_run" : "cleanup",
    total_bytes: totalBytes,
    total_gb: Number((totalBytes / GB).toFixed(3)),
    projected_bytes: projectedBytes,
    projected_gb: Number((projectedBytes / GB).toFixed(3)),
    threshold_gb: thresholdGb,
    target_gb: targetGb,
    min_keep_days: minKeepDays,
    deleted_sessions: selected.length,
    deleted_objects: deleteKeys.length,
    deleted_gb: Number(((totalBytes - projectedBytes) / GB).toFixed(3)),
  }), { headers: { "Content-Type": "application/json" } });
}
