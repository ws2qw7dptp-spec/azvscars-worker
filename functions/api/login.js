export async function onRequestPost({ request, env }) {
  const body = await request.json().catch(() => ({}));
  
  if (body.email === env.ADMIN_EMAIL && body.password === env.ADMIN_PASS) {
    return new Response(JSON.stringify({ ok: true, token: env.ADMIN_PASS }), {
      headers: { "Content-Type": "application/json" }
    });
  }
  
  return new Response(JSON.stringify({ error: "Yanlış e-poçt və ya şifrə" }), {
    status: 403,
    headers: { "Content-Type": "application/json" }
  });
}
