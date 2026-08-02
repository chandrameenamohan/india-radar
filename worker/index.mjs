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
import { loadProfile, saveProfile } from "./profile.mjs";
import { postingQuestions } from "./questions.mjs";
import { deleteResume, getResume, putResume } from "./resume.mjs";
import { profileStore, resumeStore } from "./stores.mjs";

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

    const url = new URL(request.url);
    const route = ROUTES[url.pathname];
    if (!route) return json({ error: "not found" }, 404, request);

    const handler = route[request.method];
    if (!handler) return json({ error: "method not allowed" }, 405, request);

    const issuer = env.CLERK_ISSUER;
    if (!issuer) return json({ error: "misconfigured" }, 500, request);

    // AUTHENTICATION RUNS BEFORE EVERY HANDLER, WITHOUT EXCEPTION. There is no
    // per-route opt-in, because an opt-in is a thing somebody forgets on the one
    // route that mattered. A public endpoint, if one is ever wanted, has to be
    // added here deliberately rather than by omitting a line further down.
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

    try {
      const result = await handler({ request, env, userId, url });

      // Handlers return DATA, not Responses, so that none of them can forget the
      // CORS headers -- the allowlist is a security control here and applying it
      // in one place is what stops a new route quietly skipping it. The two
      // escapes are explicit: `{status, body}` to choose a status, and `{raw}`
      // for a response whose body is bytes rather than JSON.
      if (result?.raw) {
        const headers = new Headers(result.raw.headers);
        for (const [k, v] of Object.entries(corsHeaders(request))) headers.set(k, v);
        return new Response(result.raw.body, { status: result.raw.status, headers });
      }
      if (result?.status) return json(result.body, result.status, request);
      return json(result, 200, request);
    } catch (error) {
      // Handlers throw only on conditions that cannot arise from user input --
      // `resume.mjs` throws on a malformed user id, which can only mean a caller
      // skipped verifySession, and `questions.mjs` throws when its transport is
      // missing, which is a broken deploy. Both are OURS, so both are 500. A 400
      // here would blame the reader for a bug on this side.
      return json({ error: "internal" }, 500, request);
    }
  },
};

/**
 * The whole surface, in one table.
 *
 * A table rather than a chain of ifs so that "what can be reached, and by what
 * method" is one thing to read. Every entry is authenticated by the dispatcher
 * above; nothing here can opt out.
 */
const ROUTES = {
  "/api/me": {
    GET: async ({ userId }) => ({ userId }),
  },

  "/api/profile": {
    GET: async ({ env, userId }) => ({
      profile: (await loadProfile(profileStore(env.DB), userId)) ?? null,
    }),

    PUT: async ({ request, env, userId }) => {
      const patch = await readJson(request);
      if (patch === undefined) return { status: 400, body: { error: "invalid_json" } };

      const saved = await saveProfile(profileStore(env.DB), userId, patch);
      // A refusal carries WHICH field and WHY, because the reader has to fix it.
      // The one refusal that is not a validation message is a demographic field:
      // `profile.mjs` throws for those rather than returning, so it lands in the
      // dispatcher's catch as a 500 -- correct, because a demographic field
      // reaching the server at all is our bug, not the reader's mistake.
      if (!saved.ok) return { status: 422, body: { error: "invalid_profile", fields: saved.errors } };
      return { profile: saved.value };
    },
  },

  "/api/resume": {
    GET: async ({ env, userId }) => {
      const object = await getResume(resumeStore(env.RESUMES), userId);
      if (!object) return { status: 404, body: { error: "no_resume" } };
      return {
        raw: new Response(object.body, {
          headers: {
            "content-type": object.httpMetadata?.contentType ?? "application/octet-stream",
            "content-disposition": "attachment",
          },
        }),
      };
    },

    // The upload is BUFFERED, not streamed. `resume.mjs` refuses a stream on
    // purpose: a size cap applied after the object is in the bucket is not a
    // cap, and a declared Content-Length is the uploader's claim about itself.
    // Affordable precisely because the cap is 2 MiB.
    PUT: async ({ request, env, userId }) => {
      const body = await request.arrayBuffer();
      const result = await putResume(resumeStore(env.RESUMES), userId, body, {
        contentType: request.headers.get("content-type"),
        filename: request.headers.get("x-resume-filename"),
      });
      if (!result.ok) return { status: 422, body: { error: result.reason } };
      return { resume: { size: result.size, contentType: result.contentType, replaced: result.replaced } };
    },

    DELETE: async ({ env, userId }) => deleteResume(resumeStore(env.RESUMES), userId),
  },

  "/api/questions": {
    GET: async ({ env, userId, url }) => {
      // `loadProfile` returns the fields FLAT, not wrapped in `{fields}`. Reading
      // `.fields` here silently passed an empty profile and nothing ever autofilled;
      // the isolation test caught it, which is the only reason it is not shipped.
      const profile = (await loadProfile(profileStore(env.DB), userId)) ?? {};
      // The injected fetch is the global one HERE and only here -- the module
      // takes it as an argument so its tests never reach the real boards-api.
      return postingQuestions(
        {
          ats: url.searchParams.get("ats"),
          slug: url.searchParams.get("slug"),
          jobId: url.searchParams.get("jobId"),
          profile,
        },
        { fetch: (...args) => fetch(...args) },
      );
    },
  },
};

/** A parsed body, or undefined when it is not JSON. Never throws at the caller. */
async function readJson(request) {
  try {
    return await request.json();
  } catch {
    return undefined;
  }
}

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
