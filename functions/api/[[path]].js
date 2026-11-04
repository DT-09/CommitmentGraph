export async function onRequest({ request, env }) {
  const origin = String(env.COMMITMENTGRAPH_API_ORIGIN || "").trim().replace(/\/+$/, "");
  if (!origin) {
    return Response.json(
      { detail: "The CommitmentGraph API is not connected yet. Configure COMMITMENTGRAPH_API_ORIGIN in the Cloudflare Pages environment." },
      { status: 503, headers: { "Cache-Control": "no-store" } }
    );
  }

  let upstream;
  try {
    upstream = new URL(origin);
  } catch {
    return Response.json({ detail: "COMMITMENTGRAPH_API_ORIGIN is not a valid URL." }, { status: 500 });
  }
  if (upstream.protocol !== "https:" && upstream.hostname !== "localhost" && upstream.hostname !== "127.0.0.1") {
    return Response.json({ detail: "The API origin must use HTTPS." }, { status: 500 });
  }

  const apiKey = String(env.COMMITMENTGRAPH_API_KEY || "").trim();
  if (!apiKey) {
    return Response.json(
      { detail: "The API proxy secret is not configured. Set COMMITMENTGRAPH_API_KEY in the Cloudflare Pages environment." },
      { status: 503, headers: { "Cache-Control": "no-store" } }
    );
  }

  const incoming = new URL(request.url);
  const target = new URL(incoming.pathname + incoming.search, upstream.origin);
  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("cookie");
  headers.set("x-api-key", apiKey);

  const init = {
    method: request.method,
    headers,
    redirect: "manual"
  };
  if (request.method !== "GET" && request.method !== "HEAD") init.body = request.body;

  try {
    const response = await fetch(target.toString(), init);
    const responseHeaders = new Headers(response.headers);
    responseHeaders.set("Cache-Control", "no-store");
    responseHeaders.delete("set-cookie");
    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders
    });
  } catch {
    return Response.json(
      { detail: "The configured CommitmentGraph API could not be reached." },
      { status: 502, headers: { "Cache-Control": "no-store" } }
    );
  }
}
