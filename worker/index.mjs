// T14.1 — the Workers API. Thin on purpose: everything load-bearing is in
// `auth.mjs`, which is testable without the Workers runtime.
//
// WHY THIS NEEDS CORS AT ALL, since SPEC v4 says the app page is same-origin
// with the register: `roleatlas.sennamind.com` is a DNS-only (grey cloud) CNAME
// to GitHub Pages, because that is what let GitHub issue the certificate (see
// HANDOFF). A Worker route on that hostname would require proxying it through
// Cloudflare, which takes the certificate away from GitHub. So the API lives on
// its own hostname and the page reaches it cross-origin -- which makes the
// allowlist below a security control rather than boilerplate.

import { bearerToken, verifySession } from "./auth.mjs";

/** Exact origins, no wildcards, no suffix matching. `evil-roleatlas.com` must not pass. */
const ALLOWED_ORIGINS = new Set([
  "https://roleatlas.sennamind.com",
  "http://127.0.0.1:8731", // the e2e harness
]);

/** Clerk rotates signing keys; a day is short enough to follow and long enough to not matter. */
const JWKS_TTL_MS = 24 * 60 * 60 * 1000;

/**
 * How long a cached key set may outlive a failing refetch.
 *
 * This constant is the whole argument, so it is written down. Serving CACHED
 * keys through a Clerk outage is not a security hole — they are genuine Clerk
 * keys, so a forged token still fails signature verification, and refusing
 * instead would sign every reader out because a third party had a bad minute.
 * What it IS, unbounded, is a way for a key revoked because it leaked to keep
 * working forever. So staleness is bounded, and past the bound we refuse.
 */
const JWKS_MAX_STALE_MS = 2 * JWKS_TTL_MS;

let jwksCache = { keys: null, fetchedAt: 0 };

/**
 * Clerk's signing keys, cached per isolate. Null when there are none to be had.
 *
 * Every caller treats null as a refusal. FAILING OPEN HERE WOULD ACCEPT EVERY
 * FORGED TOKEN, so this must never return an empty or absent key set as if it
 * were a usable one — `index.test.mjs` attacks exactly that with a good token.
 */
async function signingKeys(issuer, now = Date.now()) {
  const age = now - jwksCache.fetchedAt;
  if (jwksCache.keys && age < JWKS_TTL_MS) return jwksCache.keys;

  const fallback = jwksCache.keys && age < JWKS_MAX_STALE_MS ? jwksCache.keys : null;
  try {
    const response = await fetch(`${issuer}/.well-known/jwks.json`);
    if (!response.ok) return fallback;
    const body = await response.json();
    if (!Array.isArray(body?.keys) || body.keys.length === 0) return fallback;
    jwksCache = { keys: body, fetchedAt: now };
    return body;
  } catch {
    return fallback;
  }
}

function corsHeaders(request) {
  const origin = request.headers.get("origin");
  if (!origin || !ALLOWED_ORIGINS.has(origin)) return {};
  return {
    "access-control-allow-origin": origin,
    "access-control-allow-headers": "authorization,content-type",
    "access-control-allow-methods": "GET,POST,DELETE,OPTIONS",
    "vary": "origin",
  };
}

const json = (body, status, request) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", ...corsHeaders(request) },
  });

/**
 * Identical for every refusal. A caller cannot learn from this whether a token
 * was expired, forged, or belonged to a user who does not exist.
 */
const refuse = (request) => json({ error: "unauthenticated" }, 401, request);

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(request) });
    }

    const { pathname } = new URL(request.url);
    if (pathname !== "/api/me") return json({ error: "not found" }, 404, request);
    if (request.method !== "GET") return json({ error: "method not allowed" }, 405, request);

    const issuer = env.CLERK_ISSUER;
    if (!issuer) return json({ error: "misconfigured" }, 500, request);

    const token = bearerToken(request);
    if (!token) return refuse(request);

    const jwks = await signingKeys(issuer);
    // Belt and braces, and measured as such: mutation testing showed deleting
    // this line changes no test, because `verifySession` refuses a null or empty
    // key set on its own and `auth.test.mjs` is what proves fail-closed. Kept so
    // a later refactor of verifySession cannot quietly make this the hole.
    if (!jwks) return refuse(request);

    const userId = await verifySession(token, { jwks, issuer });
    if (!userId) return refuse(request);

    return json({ userId }, 200, request);
  },
};

// Test seams. Not part of the request path. `resetJwksCache` exists because the
// cache is per-isolate module state, and a test that could not clear it would
// pass on the key a previous test had installed — which is how the fail-closed
// test first passed while the code was failing open.
export const _internals = {
  ALLOWED_ORIGINS,
  corsHeaders,
  signingKeys,
  JWKS_TTL_MS,
  JWKS_MAX_STALE_MS,
  resetJwksCache: (keys = null, fetchedAt = 0) => {
    jwksCache = { keys, fetchedAt };
  },
};
