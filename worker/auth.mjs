// T14.1 — verifying a Clerk session, and the only security boundary in Phase 9.
//
// Every endpoint after this one reads a user id from `verifySession`. A forged
// token here is not a bug, it is one reader holding another reader's resume. So
// this file is written to be read by someone looking for a way through it.
//
// NO DEPENDENCIES, AND THAT IS A DECISION. The cryptography is WebCrypto's --
// `crypto.subtle.verify` is the same primitive a JWT library would call. What is
// written here is claim checking against RFC 7519, which is the part a library
// also merely checks. Keeping it dependency-free means it runs unchanged in the
// Worker and under `node --test` on a machine where the Workers runtime will not
// start, which is how `auth.test.mjs` can attack it at all.
//
// ponytail: hand-rolled claim validation, adversarially tested. The upgrade path
// is `@clerk/backend`'s verifyToken, and the trigger for taking it is Clerk
// changing claim SEMANTICS -- the claims checked below (iss, exp, nbf, sub, kid)
// are RFC-standard, not Clerk inventions, which is why this is not tracking a
// vendor. Revisit if we need networkless verification or multi-instance keys.
//
// Every rejection returns null. None of them says why, and none of them says
// whether the user exists -- a caller cannot use this to enumerate accounts.

/** Clock skew allowance. Clerk session tokens live ~60s, so this stays small. */
const LEEWAY_SECONDS = 5;

/** Hardcoded. The token's own `alg` is checked AGAINST this, never used to pick it. */
const ALGORITHM = { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" };

function bytesFromBase64Url(value) {
  // atob exists in Workers and in Node 18+; Buffer does not exist in Workers.
  const padded = value.replaceAll("-", "+").replaceAll("_", "/");
  const binary = atob(padded + "=".repeat((4 - (padded.length % 4)) % 4));
  return Uint8Array.from(binary, (c) => c.charCodeAt(0));
}

function jsonFromBase64Url(value) {
  return JSON.parse(new TextDecoder().decode(bytesFromBase64Url(value)));
}

/**
 * The user id inside a Clerk session token, or null.
 *
 * @param {string} token        the raw JWT
 * @param {object} options
 * @param {{keys: object[]}} options.jwks    Clerk's published signing keys
 * @param {string} options.issuer            the exact expected `iss`
 * @param {number} [options.now]             seconds since epoch; injected for tests
 * @returns {Promise<string|null>} the `sub` claim, or null for ANY failure
 */
export async function verifySession(token, { jwks, issuer, now = Date.now() / 1000 }) {
  if (typeof token !== "string") return null;

  const parts = token.split(".");
  if (parts.length !== 3) return null;
  const [encodedHeader, encodedPayload, encodedSignature] = parts;

  let header, payload, signature;
  try {
    header = jsonFromBase64Url(encodedHeader);
    payload = jsonFromBase64Url(encodedPayload);
    signature = bytesFromBase64Url(encodedSignature);
  } catch {
    return null;
  }

  // THE ALGORITHM CONFUSION DEFENCE. The token declares an algorithm and we
  // refuse anything that is not RS256 -- we never let the token choose which
  // verification runs. `alg: "none"` and an HS256 token signed with the public
  // key as an HMAC secret both die on this line, and both have a test.
  if (header?.alg !== "RS256") return null;
  if (typeof header.kid !== "string") return null;

  const jwk = jwks?.keys?.find((k) => k.kid === header.kid);
  if (!jwk || jwk.kty !== "RSA" || (jwk.alg && jwk.alg !== "RS256")) return null;

  let key;
  try {
    // Rebuilt from named fields rather than passed through: a JWKS we did not
    // author cannot smuggle `key_ops`, `alg` or `use` into importKey this way.
    key = await crypto.subtle.importKey(
      "jwk",
      { kty: "RSA", n: jwk.n, e: jwk.e, alg: "RS256", ext: true },
      ALGORITHM,
      false,
      ["verify"],
    );
  } catch {
    return null;
  }

  const signed = new TextEncoder().encode(`${encodedHeader}.${encodedPayload}`);
  let ok = false;
  try {
    ok = await crypto.subtle.verify(ALGORITHM, key, signature, signed);
  } catch {
    return null;
  }
  if (!ok) return null;

  // Signature is good, so the claims are authentic. They still have to be VALID.
  if (payload?.iss !== issuer) return null;
  if (typeof payload.exp !== "number" || payload.exp + LEEWAY_SECONDS <= now) return null;
  if (typeof payload.nbf === "number" && payload.nbf - LEEWAY_SECONDS > now) return null;
  if (typeof payload.sub !== "string" || payload.sub === "") return null;

  return payload.sub;
}

/** The bearer token on a request, or null. Never throws on a malformed header. */
export function bearerToken(request) {
  const header = request.headers.get("authorization");
  if (!header) return null;
  const [scheme, ...rest] = header.split(" ");
  if (scheme.toLowerCase() !== "bearer" || rest.length !== 1) return null;
  return rest[0] || null;
}
