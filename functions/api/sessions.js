export async function onRequestGet({ env }) {
  const kv = env.AZVSCARS_KV;
  if (!kv) {
    return new Response(JSON.stringify({ error: "AZVSCARS_KV binding tapılmadı" }), { status: 500 });
  }

  const index = await kv.get("sessions:index", "json") || [];
  
  return new Response(JSON.stringify(index), {
    headers: { "Content-Type": "application/json" }
  });
}
