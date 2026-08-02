// Token forgery kit, shared by auth.test.mjs and index.test.mjs. Not shipped.
//
// Keys are minted per run rather than committed, so no test here can drift into
// agreeing with a stale fixture, and the attack tokens are built with the same
// primitives the real ones are.

export const ISSUER = "https://regular-troll-50.clerk.accounts.dev";
export const NOW = 1_800_000_000;

export const b64url = (bytes) =>
  btoa(String.fromCharCode(...new Uint8Array(bytes)))
    .replaceAll("+", "-")
    .replaceAll("/", "_")
    .replaceAll("=", "");

export const encodeJson = (value) => b64url(new TextEncoder().encode(JSON.stringify(value)));

export async function makeKeypair(kid) {
  const pair = await crypto.subtle.generateKey(
    {
      name: "RSASSA-PKCS1-v1_5",
      modulusLength: 2048,
      publicExponent: new Uint8Array([1, 0, 1]),
      hash: "SHA-256",
    },
    true,
    ["sign", "verify"],
  );
  const jwk = await crypto.subtle.exportKey("jwk", pair.publicKey);
  return { ...pair, jwk: { ...jwk, kid, alg: "RS256", use: "sig" } };
}

/** A signed token. Defaults are valid; every argument exists to be made invalid. */
export async function mint(keypair, { header = {}, payload = {}, now = NOW } = {}) {
  const head = encodeJson({ alg: "RS256", typ: "JWT", kid: keypair.jwk.kid, ...header });
  const body = encodeJson({ iss: ISSUER, sub: "user_2abc", exp: now + 60, ...payload });
  const signature = await crypto.subtle.sign(
    { name: "RSASSA-PKCS1-v1_5" },
    keypair.privateKey,
    new TextEncoder().encode(`${head}.${body}`),
  );
  return `${head}.${body}.${b64url(signature)}`;
}
