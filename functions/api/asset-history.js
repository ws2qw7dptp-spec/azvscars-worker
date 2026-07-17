export async function onRequestGet({ env }) {
  const [audioIds, videoIds] = await Promise.all([
    env.AZVSCARS_KV.get("audio:used_ids", "json"),
    env.AZVSCARS_KV.get("video:used_ids", "json"),
  ]);
  return Response.json({
    audio_ids: Array.isArray(audioIds) ? audioIds.map(String) : [],
    video_ids: Array.isArray(videoIds) ? videoIds.map(String) : [],
  });
}
