export async function onRequest(context) {
  const { request, env } = context;
  
  // Allow OPTIONS (CORS preflight) unconditionally
  if (request.method === "OPTIONS") {
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, X-Admin-Password"
      }
    });
  }

  // Skip auth for login and public media. Instagram/Meta must be able to fetch
  // these image/video URLs during publish, so they cannot require admin headers.
  const url = new URL(request.url);
  if (url.pathname === "/api/login" || url.pathname.startsWith("/api/image/")) {
    return await context.next();
  }

  // Check auth
  const token = request.headers.get("X-Admin-Password");
  if (!env.ADMIN_PASS || token !== env.ADMIN_PASS) {
    return new Response(JSON.stringify({ error: "Unauthorized" }), {
      status: 401,
      headers: { "Content-Type": "application/json" }
    });
  }

  // Proceed
  const response = await context.next();
  // Add CORS headers to all responses
  const newResponse = new Response(response.body, response);
  newResponse.headers.set("Access-Control-Allow-Origin", "*");
  return newResponse;
}
