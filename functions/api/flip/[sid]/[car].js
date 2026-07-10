/**
 * POST /api/flip/[sid]/[car]
 * Triggers GitHub Actions to re-render a car's image flipped.
 */
export async function onRequestPost({ request, env, params }) {
  const sid = params.sid;
  const car = params.car;

  // Set status to running
  await env.AZVSCARS_KV.put(`status_${sid}`, JSON.stringify({
    status: "running",
    message: "🔄 Maşın yenidən render edilir…"
  }));

  const ghToken = env.GH_PAT;
  const ghOwner = env.GH_OWNER || "islammuradov1";
  const ghRepo = env.GH_REPO || "azvscars";
  const ghWorkflow = env.GH_WORKFLOW || "worker.yml";
  const ghRef = env.GH_REF || "main";

  if (!ghToken) {
    await env.AZVSCARS_KV.put(`status_${sid}`, JSON.stringify({
      status: "error",
      message: "❌ GH_PAT ayarlanmayıb. Flip işə salına bilmir."
    }));
    return new Response(JSON.stringify({ error: "GH_PAT environment variable is missing." }), {
      status: 500,
      headers: { "Content-Type": "application/json" }
    });
  }

  const triggerRes = await fetch(
    `https://api.github.com/repos/${ghOwner}/${ghRepo}/actions/workflows/${ghWorkflow}/dispatches`,
    {
      method: "POST",
      headers: {
        "Authorization": `token ${ghToken}`,
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "AZvsCars-CloudflareFunction"
      },
      body: JSON.stringify({
        ref: ghRef,
        inputs: {
          action: "flip",
          sid: sid,
          car: String(car),
          post_type: "main",
          make_reel: "false"
        }
      })
    }
  );

  if (!triggerRes.ok) {
    const errText = await triggerRes.text();
    await env.AZVSCARS_KV.put(`status_${sid}`, JSON.stringify({
      status: "error",
      message: `❌ GitHub Actions trigger xətası: ${errText}`
    }));
    return new Response(JSON.stringify({ error: `GitHub Actions trigger xətası: ${errText}` }), {
      status: 500,
      headers: { "Content-Type": "application/json" }
    });
  }

  return new Response(JSON.stringify({ ok: true, message: "Flip başladıldı, zəhmət olmasa gözləyin…" }), {
    headers: { "Content-Type": "application/json" }
  });
}
