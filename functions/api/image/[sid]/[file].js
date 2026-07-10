export async function onRequestGet({ env, params, request }) {
  const bucket = env.AZVSCARS_R2;
  
  if (!bucket) {
    return new Response(JSON.stringify({ error: "AZVSCARS_R2 binding tapılmadı" }), { status: 500 });
  }

  const sid = params.sid;
  const file = params.file;
  
  // Xüsusi xarakterləri təmizlə
  const objectName = `${sid}/${file}`;
  
  const object = await bucket.get(objectName);

  if (object === null) {
    return new Response(JSON.stringify({ error: "Fayl tapılmadı" }), { status: 404 });
  }

  const headers = new Headers();
  object.writeHttpMetadata(headers);
  headers.set('etag', object.httpEtag);
  
  // Cache for 1 hour to speed up UI
  headers.set('Cache-Control', 'public, max-age=3600');
  
  // CORS for Instagram/Meta API if needed
  headers.set('Access-Control-Allow-Origin', '*');

  return new Response(object.body, {
    headers,
  });
}
