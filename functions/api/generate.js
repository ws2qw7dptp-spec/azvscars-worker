/**
 * POST /api/generate
 * Triggers a GitHub Actions workflow to generate a new post.
 * Returns the session ID immediately; status is polled via /api/status/[sid]
 */
export async function onRequestPost({ request, env }) {
  const body = await request.json().catch(() => ({}));
  const post_type = body.post_type || "main";
  const isStories = post_type === "stories";
  const make_reel = post_type === "cinematic" || body.make_reel ? "true" : "false";
  const auto_publish = body.auto_publish ? "true" : "false";

  // Generate a unique session ID
  const sid = Math.random().toString(36).substring(2, 10);

  // Write initial "running" status to KV so frontend can poll
  await env.AZVSCARS_KV.put(`status_${sid}`, JSON.stringify({
    status: "running",
    message: "☁️ GitHub Actions-da iş başladılır…"
  }));

  // Trigger GitHub Actions workflow
  const ghToken = env.GH_PAT;
  const ghOwner = env.GH_TARGET_OWNER || env.GH_OWNER || "islammuradov1";
  const ghRepo = env.GH_TARGET_REPO || env.GH_REPO || "azvscars";
  const ghWorkflow = env.GH_TARGET_WORKFLOW || env.GH_WORKFLOW || "worker.yml";
  const ghRef = env.GH_TARGET_REF || env.GH_REF || "main";

  if (!ghToken) {
    await env.AZVSCARS_KV.put(`status_${sid}`, JSON.stringify({
      status: "error",
      message: "❌ GH_PAT ayarlanmayıb. GitHub Actions işə salına bilmir."
    }));
    return new Response(JSON.stringify({ error: "GH_PAT environment variable is missing." }), {
      status: 500,
      headers: { "Content-Type": "application/json" }
    });
  }

  const inputs = {
    action: isStories ? "stories" : "generate",
    sid,
    post_type: isStories ? "stories" : post_type,
    make_reel,
    auto_publish,
  };
  if (isStories) {
    inputs.story_slot = body.story_slot || "all";
    inputs.story_files = body.story_files || "";
  }

  const dispatchUrl = `https://api.github.com/repos/${ghOwner}/${ghRepo}/actions/workflows/${ghWorkflow}/dispatches`;
  const dispatchOptions = {
      method: "POST",
      headers: {
        "Authorization": `token ${ghToken}`,
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "AZvsCars-CloudflareFunction"
      },
      body: JSON.stringify({
        ref: ghRef,
        inputs
      })
    };
  let triggerRes = await fetch(dispatchUrl, dispatchOptions);

  // During rolling deploys the worker workflow may not know story_slot yet.
  // Retry with the older compatible input shape instead of breaking autopilot.
  if (!triggerRes.ok && isStories && triggerRes.status === 422) {
    delete inputs.story_slot;
    dispatchOptions.body = JSON.stringify({ ref: ghRef, inputs });
    triggerRes = await fetch(dispatchUrl, dispatchOptions);
  }

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

  return new Response(JSON.stringify({ sid: sid }), {
    headers: { "Content-Type": "application/json" }
  });
}
