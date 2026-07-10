export async function onRequestGet({ env, params }) {
  const kv = env.AZVSCARS_KV;
  const sid = params.sid;
  
  const statusRaw = await kv.get(`status_${sid}`, "json");
  if (statusRaw) {
    return new Response(JSON.stringify(statusRaw), { headers: { "Content-Type": "application/json" } });
  }

  // Fallback: check if session exists
  const meta = await kv.get(`session:${sid}`, "json");
  if (meta) {
    return new Response(JSON.stringify({ status: "done", message: "✅ Hazırdır!", sid: sid }), { headers: { "Content-Type": "application/json" } });
  }

  return new Response(JSON.stringify({ status: "unknown", message: "Bilinmir" }), { headers: { "Content-Type": "application/json" } });
}
