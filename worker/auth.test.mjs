// T14.1 — attacks on `verifySession`. Run: node --test worker/
//
// These are the task. `auth.mjs` is the only thing standing between a stranger
// and another reader's resume, so this file is written to get PAST it, not to
// demonstrate that the happy path works. Every test below is a forgery someone
// would actually attempt.
//
// No test framework and no fixtures on disk: Node's WebCrypto mints the keys and
// signs the tokens, so the attacks are built with the same primitives the real
// tokens are, and nothing here can rot into agreeing with a stale fixture.

import { strict as assert } from "node:assert";
import { test } from "node:test";

import { bearerToken, verifySession } from "./auth.mjs";
import { ISSUER, NOW, encodeJson, b64url, makeKeypair, mint } from "./_testing.mjs";

const real = await makeKeypair("kid_real");
const attacker = await makeKeypair("kid_real"); // same kid, different key: key confusion
const jwks = { keys: [real.jwk] };
const verify = (token, over = {}) => verifySession(token, { jwks, issuer: ISSUER, now: NOW, ...over });

test("a genuine token yields its subject", async () => {
  assert.equal(await verify(await mint(real)), "user_2abc");
});

test("a token signed by a different key is refused", async () => {
  // The forger publishes nothing and guesses nothing -- they simply sign their
  // own token and claim the real key's kid. This is the whole threat model.
  assert.equal(await verify(await mint(attacker)), null);
});

test("a token signed with the real key but a tampered payload is refused", async () => {
  const token = await mint(real);
  const [head, , signature] = token.split(".");
  const swapped = encodeJson({ iss: ISSUER, sub: "user_SOMEONE_ELSE", exp: NOW + 60 });
  assert.equal(await verify(`${head}.${swapped}.${signature}`), null);
});

test("alg: none is refused", async () => {
  const head = encodeJson({ alg: "none", typ: "JWT", kid: "kid_real" });
  const body = encodeJson({ iss: ISSUER, sub: "user_2abc", exp: NOW + 60 });
  assert.equal(await verify(`${head}.${body}.`), null);
  assert.equal(await verify(`${head}.${body}.x`), null);
});

test("HS256 signed with the public key as the HMAC secret is refused", async () => {
  // The classic confusion attack: the verifier is tricked into treating a PUBLIC
  // value as a shared secret. It fails because alg is checked against RS256 and
  // never used to select the algorithm.
  const head = encodeJson({ alg: "HS256", typ: "JWT", kid: "kid_real" });
  const body = encodeJson({ iss: ISSUER, sub: "user_2abc", exp: NOW + 60 });
  const secret = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(JSON.stringify(real.jwk)),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const mac = await crypto.subtle.sign("HMAC", secret, new TextEncoder().encode(`${head}.${body}`));
  assert.equal(await verify(`${head}.${body}.${b64url(mac)}`), null);
});

test("an unknown kid is refused rather than tried against every key", async () => {
  const stranger = await makeKeypair("kid_not_published");
  assert.equal(await verify(await mint(stranger)), null);
});

// The two tests below exist because MUTATION TESTING said the ones around them
// were passing for the wrong reason. Deleting the `alg` check and deleting `kid`
// selection each left the whole file green: every attack was being stopped by
// signature verification one step later, so two guards were untested and would
// have rotted silently. Each test here fails if, and only if, its guard is gone.

test("a non-RS256 alg is refused even when the RSA signature is genuine", async () => {
  // Signed with the real key over these exact header bytes, so the signature
  // VERIFIES. The alg field is the only thing wrong with it -- which makes this
  // the one test that can tell whether the alg check runs at all.
  const token = await mint(real, { header: { alg: "RS384" } });
  assert.equal(await verify(token), null);
  assert.equal(await verify(await mint(real, { header: { alg: "PS256" } })), null);
});

test("kid selects the signing key rather than the set's first key", async () => {
  // Two published keys, and the token is signed by the SECOND. A verifier that
  // grabs keys[0] and ignores kid rejects a legitimate reader -- a failure that
  // arrives the day Clerk rotates its signing key, not on the day it ships.
  const second = await makeKeypair("kid_second");
  const both = { keys: [real.jwk, second.jwk] };
  assert.equal(await verify(await mint(second), { jwks: both }), "user_2abc");

  // ...and claiming another published key's kid is still refused.
  const liar = await mint(second, { header: { kid: "kid_real" } });
  assert.equal(await verify(liar, { jwks: both }), null);
});

test("an expired token is refused, and the leeway does not swallow a real expiry", async () => {
  assert.equal(await verify(await mint(real, { payload: { exp: NOW - 1 } })), "user_2abc",
    "a token one second past expiry is still inside the 5s clock-skew leeway");
  assert.equal(await verify(await mint(real, { payload: { exp: NOW - 3600 } })), null);
});

test("a token missing exp entirely is refused", async () => {
  const head = encodeJson({ alg: "RS256", typ: "JWT", kid: "kid_real" });
  const body = encodeJson({ iss: ISSUER, sub: "user_2abc" });
  const signature = await crypto.subtle.sign(
    { name: "RSASSA-PKCS1-v1_5" },
    real.privateKey,
    new TextEncoder().encode(`${head}.${body}`),
  );
  assert.equal(await verify(`${head}.${body}.${b64url(signature)}`), null);
});

test("a token not yet valid is refused", async () => {
  assert.equal(await verify(await mint(real, { payload: { nbf: NOW + 3600 } })), null);
});

test("a token from another issuer is refused", async () => {
  // A real, correctly signed token from somebody else's Clerk instance.
  assert.equal(await verify(await mint(real, { payload: { iss: "https://evil.clerk.accounts.dev" } })), null);
});

test("a token with no subject is refused", async () => {
  assert.equal(await verify(await mint(real, { payload: { sub: "" } })), null);
  assert.equal(await verify(await mint(real, { payload: { sub: 12345 } })), null);
});

test("malformed input is refused without throwing", async () => {
  for (const bad of ["", "a.b", "a.b.c.d", "....", "not a jwt", "!!!.???.###", null, undefined, 42, {}]) {
    assert.equal(await verify(bad), null, `threw or accepted: ${JSON.stringify(bad)}`);
  }
});

test("an empty or malformed JWKS refuses everything rather than failing open", async () => {
  const token = await mint(real);
  for (const broken of [{ keys: [] }, {}, null, undefined, { keys: [{ kid: "kid_real", kty: "oct" }] }]) {
    assert.equal(await verifySession(token, { jwks: broken, issuer: ISSUER, now: NOW }), null);
  }
});

test("bearerToken reads only a well-formed Authorization header", () => {
  const req = (value) => ({ headers: { get: () => value } });
  assert.equal(bearerToken(req("Bearer abc.def.ghi")), "abc.def.ghi");
  assert.equal(bearerToken(req("bearer abc.def.ghi")), "abc.def.ghi");
  for (const bad of [null, "", "abc.def.ghi", "Basic abc", "Bearer", "Bearer a b"]) {
    assert.equal(bearerToken(req(bad)), null, `accepted: ${JSON.stringify(bad)}`);
  }
});
