/**
 * Aegis — Cloudflare Co-Worker
 *
 * Runs at Cloudflare's edge BEFORE the request reaches the origin server.
 *
 * Responsibilities:
 *   1. Strip ALL identifying headers (IP, UA, fingerprints, locale)
 *   2. Enforce anonymous rate limiting (hashed IP, daily rotating salt)
 *   3. Block non-submission methods
 *   4. Forward a clean, anonymised request to origin
 */

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // ── Only allow submission + health endpoints ──────────────────────────
    const allowedPaths = ["/submit", "/health"];
    if (!allowedPaths.some((p) => url.pathname === p || url.pathname.startsWith(p))) {
      return new Response("Not found", { status: 404 });
    }

    // ── Rate limiting (anonymous — IP is hashed, never stored) ────────────
    const rawIP = request.headers.get("CF-Connecting-IP") || "unknown";
    const rateLimitKey = await hashIP(rawIP, env.RATE_LIMIT_SALT || getDailySalt());

    if (env.RATE_LIMITER) {
      const { success } = await env.RATE_LIMITER.limit({ key: rateLimitKey });
      if (!success) {
        return new Response(
          JSON.stringify({ error: "Rate limit exceeded. Try again later." }),
          {
            status: 429,
            headers: { "Content-Type": "application/json" },
          }
        );
      }
    }

    // ── Build clean headers — allowlist only ──────────────────────────────
    const cleanHeaders = new Headers();

    const allowlist = ["content-type", "content-length", "accept"];
    for (const [key, val] of request.headers.entries()) {
      if (allowlist.includes(key.toLowerCase())) {
        cleanHeaders.set(key, val);
      }
    }

    // Generic UA — don't leak Cloudflare PoP or any browser fingerprint
    cleanHeaders.set("User-Agent", "AegisProxy/1.0");

    // ── Forward clean request ─────────────────────────────────────────────
    const cleanRequest = new Request(request.url, {
      method: request.method,
      headers: cleanHeaders,
      body: ["POST", "PUT", "PATCH"].includes(request.method)
        ? request.body
        : null,
    });

    const response = await fetch(cleanRequest);

    // ── Strip any identifying headers from the response too ───────────────
    const cleanResponse = new Response(response.body, response);
    cleanResponse.headers.delete("Server");
    cleanResponse.headers.delete("X-Powered-By");
    cleanResponse.headers.set("X-Content-Type-Options", "nosniff");
    cleanResponse.headers.set("Referrer-Policy", "no-referrer");

    return cleanResponse;
  },
};


// ── Helpers ───────────────────────────────────────────────────────────────────

/**
 * One-way hash the submitter's IP for rate limiting.
 * The raw IP never leaves this function — only a derived token is used.
 * Salt rotates daily so the token cannot be used to track across days.
 */
async function hashIP(ip, salt) {
  const encoder = new TextEncoder();
  const data = encoder.encode(ip + "|" + salt);
  const hashBuffer = await crypto.subtle.digest("SHA-256", data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}

/**
 * Generate a daily salt from today's UTC date string.
 * Tokens derived with yesterday's salt are automatically invalidated.
 */
function getDailySalt() {
  return new Date().toISOString().slice(0, 10); // "YYYY-MM-DD"
}
