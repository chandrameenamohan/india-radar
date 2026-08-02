// T14.1 — the handler around `verifySession`. Run: node --test 'worker/*.test.mjs'
//
// `auth.test.mjs` attacks the verification. This file attacks everything else:
// the CORS allowlist, whether a refusal leaks which refusal it was, and whether
// a broken JWKS fetch fails closed or waves everyone through.

import { strict as assert } from "node:assert";
import { test } from "node:test";

import worker, { _internals } from "./index.mjs";
import { ISSUER, makeKeypair, mint } from "./_testing.mjs";

const ENV = { CLERK_ISSUER: ISSUER };
const real = await makeKeypair("kid_real");

/** Stub the network so the JWKS is ours. Returns a restore function. */
function serveJwks(body, { ok = true } = {}) {
  const original = globalThis.fetch;
  globalThis.fetch = async () => ({ ok, json: async () => body });
  return () => {
    globalThis.fetch = original;
  };
}

const call = (path, { method = "GET", token = null, origin = null } = {}) => {
  const headers = {};
  if (token) headers.authorization = `Bearer ${token}`;
  if (origin) headers.origin = origin;
  return worker.fetch(new Request(`https://api.example.com${path}`, { method, headers }), ENV);
};

// The cache state is an explicit argument, and it defaults to COLD. The handler
// caches the JWKS per isolate, so a test that inherited a previous test's warm
// cache would never call the stub at all — and would pass on keys it did not set.
const withJwks = async (body, fn, { ok = true, cache = null } = {}) => {
  _internals.resetJwksCache(cache?.keys ?? null, cache?.fetchedAt ?? 0);
  const restore = serveJwks(body, { ok });
  try {
    return await fn();
  } finally {
    restore();
  }
};

test("a valid token is answered with that user's own id", async () => {
  const token = await mint(real, { now: Date.now() / 1000 });
  await withJwks({ keys: [real.jwk] }, async () => {
    const response = await call("/api/me", { token });
    assert.equal(response.status, 200);
    assert.deepEqual(await response.json(), { userId: "user_2abc" });
  });
});

test("no token, a forged token and an expired token are refused identically", async () => {
  // If these three differed by status, body or timing shape, the endpoint would
  // be an oracle: a stranger could learn which user ids exist by watching which
  // refusal came back. They must be indistinguishable.
  const forger = await makeKeypair("kid_real");
  const forged = await mint(forger, { now: Date.now() / 1000 });
  const expired = await mint(real, { now: Date.now() / 1000 - 7200 });

  await withJwks({ keys: [real.jwk] }, async () => {
    const seen = [];
    for (const token of [null, forged, expired, "garbage"]) {
      const response = await call("/api/me", { token });
      seen.push([response.status, JSON.stringify(await response.json())]);
    }
    assert.equal(seen.length, 4);
    for (const [status, body] of seen) {
      assert.equal(status, 401);
      assert.deepEqual([status, body], seen[0], "refusals differ and can be told apart");
    }
  });
});

test("a cold cache with an unusable JWKS fails closed", async () => {
  // The dangerous bug here would be treating an unreachable Clerk as "skip
  // verification". A VALID token is used deliberately: the point is that even a
  // good one gets 401 when there are no keys to check it against.
  const token = await mint(real, { now: Date.now() / 1000 });
  for (const [body, options] of [[null, { ok: false }], [{ keys: [] }, {}], [{}, {}]]) {
    await withJwks(body, async () => {
      assert.equal((await call("/api/me", { token })).status, 401, "failed OPEN on an unusable JWKS");
    }, options);
  }
});

test("a warm cache rides out a Clerk outage, but only up to the staleness bound", async () => {
  // This is availability, and it is deliberate: cached keys are GENUINE keys, so
  // a forgery still fails signature verification, and refusing here would sign
  // every reader out because a third party had a bad minute.
  const token = await mint(real, { now: Date.now() / 1000 });
  const warm = (age) => ({ keys: { keys: [real.jwk] }, fetchedAt: Date.now() - age });

  await withJwks(null, async () => {
    assert.equal((await call("/api/me", { token })).status, 200);
  }, { ok: false, cache: warm(_internals.JWKS_MAX_STALE_MS - 60_000) });

  // ...and past the bound it stops, so a key revoked because it leaked cannot
  // keep working forever on the strength of a failing refetch.
  await withJwks(null, async () => {
    assert.equal((await call("/api/me", { token })).status, 401, "served keys past the staleness bound");
  }, { ok: false, cache: warm(_internals.JWKS_MAX_STALE_MS + 1) });
});

test("a missing issuer is a server error, never a pass", async () => {
  const response = await worker.fetch(new Request("https://api.example.com/api/me"), {});
  assert.equal(response.status, 500);
});

test("only exact allowlisted origins get a CORS header", async () => {
  for (const origin of [
    "https://roleatlas.sennamind.com.evil.com",
    "https://evil-roleatlas.sennamind.com",
    "http://roleatlas.sennamind.com",
    "https://sennamind.com",
    "null",
  ]) {
    const response = await call("/api/me", { origin });
    assert.equal(
      response.headers.get("access-control-allow-origin"),
      null,
      `allowed a look-alike origin: ${origin}`,
    );
  }

  const good = await call("/api/me", { origin: "https://roleatlas.sennamind.com" });
  assert.equal(good.headers.get("access-control-allow-origin"), "https://roleatlas.sennamind.com");
  assert.equal(good.headers.get("vary"), "origin");
});

test("preflight is answered without touching authentication", async () => {
  const response = await call("/api/me", { method: "OPTIONS", origin: "https://roleatlas.sennamind.com" });
  assert.equal(response.status, 204);
  assert.equal(response.headers.get("access-control-allow-origin"), "https://roleatlas.sennamind.com");
});

test("unknown paths and wrong methods are refused before any token work", async () => {
  assert.equal((await call("/")).status, 404);
  assert.equal((await call("/api/")).status, 404);
  assert.equal((await call("/api/me/../secrets")).status, 404);
  assert.equal((await call("/api/me", { method: "POST" })).status, 405);
});

// ---------------------------------------------------------------------------
// The feature routes. `profile.mjs`, `resume.mjs` and `questions.mjs` are each
// attacked thoroughly by their own suites; what is tested HERE is only what the
// dispatcher owns — that authentication cannot be skipped, that one reader
// cannot reach another's data through a route, and that CORS survives every
// return path including the one that returns bytes.

/** D1, minimally. Enough for `stores.mjs`, and no more. */
function fakeDb() {
  const rows = new Map();
  return {
    rows,
    prepare(sql) {
      let args = [];
      const api = {
        bind: (...a) => ((args = a), api),
        first: async () => (sql.includes("SELECT") ? (rows.get(args[0]) ?? null) : null),
        run: async () => {
          if (sql.includes("INSERT")) rows.set(args[0], { value: args[1] });
          if (sql.startsWith("DELETE")) rows.delete(args[0]);
          return { success: true };
        },
      };
      return api;
    },
  };
}

/** R2, minimally. */
function fakeBucket() {
  const objects = new Map();
  return {
    objects,
    async put(key, body, options) {
      objects.set(key, { body, httpMetadata: options?.httpMetadata ?? {} });
      return { key };
    },
    async get(key) {
      const o = objects.get(key);
      return o ? { body: o.body, httpMetadata: o.httpMetadata } : null;
    },
    async delete(key) {
      objects.delete(key);
    },
    async list({ prefix }) {
      return {
        objects: [...objects.keys()].filter((k) => k.startsWith(prefix)).map((key) => ({ key })),
        truncated: false,
        cursor: null,
      };
    },
  };
}

const PDF = new Uint8Array([
  ...new TextEncoder().encode("%PDF-1.7\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<< >>\nstream\nx\nendstream\n%%EOF\n"),
]);

const envWith = () => ({ CLERK_ISSUER: ISSUER, DB: fakeDb(), RESUMES: fakeBucket() });

/** A signed request for `who`, against a shared env. */
async function as(who, path, { method = "GET", body, headers = {}, env } = {}) {
  const keypair = who === "a" ? real : real;
  const token = await mint(keypair, { now: Date.now() / 1000, payload: { sub: `user_${who}` } });
  return worker.fetch(
    new Request(`https://api.example.com${path}`, {
      method,
      headers: { authorization: `Bearer ${token}`, ...headers },
      body,
    }),
    env,
  );
}

test("every feature route refuses an unauthenticated caller", async () => {
  await withJwks({ keys: [real.jwk] }, async () => {
    const env = envWith();
    for (const [path, method] of [
      ["/api/profile", "GET"], ["/api/profile", "PUT"],
      ["/api/resume", "GET"], ["/api/resume", "PUT"], ["/api/resume", "DELETE"],
      ["/api/questions", "GET"],
    ]) {
      const response = await worker.fetch(
        new Request(`https://api.example.com${path}`, { method }), env,
      );
      assert.equal(response.status, 401, `${method} ${path} was reachable without a token`);
    }
  });
});

test("one reader cannot reach another reader's profile or resume", async () => {
  // The dispatcher derives the user id from the verified token and nothing else.
  // There is deliberately no id in any path or query, so this test is really
  // asserting that no route ever grew one.
  await withJwks({ keys: [real.jwk] }, async () => {
    const env = envWith();
    await as("a", "/api/profile", {
      method: "PUT", env,
      body: JSON.stringify({ salary_expectation: "a's number" }),
      headers: { "content-type": "application/json" },
    });
    await as("a", "/api/resume", {
      method: "PUT", env, body: PDF, headers: { "content-type": "application/pdf" },
    });

    // Asserted on the CONTENT, not on the empty shape: `loadProfile` answers a
    // user with no row with an empty profile rather than null, and a test that
    // pinned the shape would pass for the wrong reason the day that changed.
    // What must never happen is a's value appearing under b's token.
    const theirProfile = await (await as("b", "/api/profile", { env })).json();
    assert.equal(
      JSON.stringify(theirProfile).includes("a's number"),
      false,
      "b read a's profile",
    );
    assert.equal((await as("b", "/api/resume", { env })).status, 404, "b read a's resume");

    // ...and a still has both, so the isolation is not just an empty database.
    const own = await (await as("a", "/api/profile", { env })).json();
    assert.equal(own.profile.salary_expectation, "a's number");
    assert.equal((await as("a", "/api/resume", { env })).status, 200);
  });
});

test("a demographic field is a 500, because it reaching us at all is our bug", async () => {
  await withJwks({ keys: [real.jwk] }, async () => {
    const response = await as("a", "/api/profile", {
      method: "PUT", env: envWith(),
      body: JSON.stringify({ salary_expectation: "x", gender: "prefer not to say" }),
      headers: { "content-type": "application/json" },
    });
    assert.equal(response.status, 500);
    // And nothing about the field is echoed back — not even its name.
    assert.equal(JSON.stringify(await response.json()).includes("gender"), false);
  });
});

test("a malformed body is the reader's 400, not a 500", async () => {
  await withJwks({ keys: [real.jwk] }, async () => {
    const response = await as("a", "/api/profile", {
      method: "PUT", env: envWith(), body: "{not json",
      headers: { "content-type": "application/json" },
    });
    assert.equal(response.status, 400);
  });
});

test("the bytes route still carries the CORS header", async () => {
  // The `{raw}` escape returns a Response the dispatcher did not build, which is
  // exactly the path on which a route could quietly lose the allowlist.
  await withJwks({ keys: [real.jwk] }, async () => {
    const env = envWith();
    await as("a", "/api/resume", {
      method: "PUT", env, body: PDF, headers: { "content-type": "application/pdf" },
    });
    const response = await as("a", "/api/resume", {
      env, headers: { origin: "https://roleatlas.sennamind.com" },
    });
    assert.equal(response.status, 200);
    assert.equal(
      response.headers.get("access-control-allow-origin"),
      "https://roleatlas.sennamind.com",
    );
  });
});
