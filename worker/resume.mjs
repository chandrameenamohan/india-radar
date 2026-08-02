// T14.3 — one resume per user, and a deletion you can verify in the same request.
//
// This is the first personal document this project has ever held, and SPEC v4
// owns the retention decision v3 deferred to whichever feature needed it. Three
// claims are made there that this file either makes true or makes a lie:
//
//   ONE RESUME, NO HISTORY. Replacing deletes the previous file. Versioning is
//   Epic 1's job, and two resume systems to reconcile later is worse than none
//   now. So "one object per user" is not a convention here, it is checked
//   against the store after every write.
//
//   DELETION IS SYNCHRONOUS. "A deletion you cannot verify synchronously is a
//   deletion you cannot honestly claim." `deleteResume` therefore reads back
//   after it deletes and THROWS rather than report a success it did not observe.
//   A store that quietly ignores a delete must not be able to make us tell a
//   user their resume is gone.
//
//   USER SCOPING IS THE SECURITY BOUNDARY. The key is derived from the id
//   `verifySession` returned and from nothing else. No filename, no client
//   field, no path component the caller chose ever reaches a key.
//
// NO DEPENDENCIES, and storage is INJECTED rather than imported. Nothing here
// names R2, wrangler or a binding: every function takes a `store` shaped like
// an R2 bucket -- `{ put, get, delete, list }`. That is what lets
// `resume.test.mjs` run the real logic against an in-memory fake under
// `node --test`, on the machine where workerd will not start (T14.1), and it
// keeps the module honest about the fact that all it needs is four methods.

/**
 * The size cap, and why this number.
 *
 * A plain-text resume is a few kilobytes; a typeset one- or two-page PDF is
 * comfortably under 500 KB. 2 MiB is roughly four times the fat end of that, so
 * it clears a scanned or image-heavy PDF and still refuses anything that is not
 * plausibly a resume -- someone's portfolio, or a bucket used as free storage.
 *
 * It is also small enough to BUFFER, and that is the load-bearing half. The cap
 * is enforced on the bytes we actually hold (see `bytesOf`), never on a declared
 * Content-Length, because a cap you apply to a number the caller supplied is not
 * a cap. A limit large enough to force streaming would have to be enforced after
 * the object was already in storage, which is not enforcement.
 *
 * It is a product judgement rather than a platform limit, so it is revisable:
 * the trigger for raising it is a measured rejection rate, not an argument.
 */
export const MAX_RESUME_BYTES = 2 * 1024 * 1024;

/**
 * Exactly two. SPEC v4 puts "formats beyond PDF and plain text" out of scope,
 * and each of these has a cheap structural check below -- which is the actual
 * reason the list is short. A format we cannot verify is a format we would be
 * storing on the caller's word.
 */
export const ACCEPTED_TYPES = new Set(["application/pdf", "text/plain"]);

/**
 * A Clerk `sub` is `user_` plus base58-ish characters. This allowlist is
 * deliberately a CHARACTER SET rather than a Clerk-shaped pattern: it does not
 * couple the storage layer to one identity vendor's id format, and it is the
 * charset that does the security work anyway. `.`, `/`, `\`, `%`, NUL, spaces
 * and every non-ASCII byte are absent, so `..`, `%2e%2e%2f`, `/etc/passwd` and
 * a NUL-truncated id cannot be spelled at all -- there is nothing to normalise
 * and therefore nothing to get wrong when normalising. The 64 is Clerk's ids
 * being ~32 characters, doubled.
 */
const USER_ID = /^[A-Za-z0-9_-]{1,64}$/;

/** Everything this module owns lives under here, so a sweep can be prefix-scoped. */
const ROOT = "resumes/";

/** The one object name. Note it carries no extension -- see `resumeKey`. */
const OBJECT = "resume";

/**
 * The user's private corner of the bucket. THE TRAILING SLASH IS A SECURITY
 * CONTROL, not tidiness: without it the prefix for `user_a` is also a prefix of
 * `user_ab`, so a prefix sweep for one user would list and delete another's
 * object. There is a test for exactly that pair.
 *
 * Throws on anything that did not come out of `verifySession`. This is the one
 * place in the module that throws on bad INPUT rather than returning a result,
 * and the asymmetry is deliberate: a malformed user id is not a user error to
 * be reported back, it is a caller that skipped authentication. Returning null
 * would make that indistinguishable from "this user has no resume", which is
 * how a hole gets to look like an empty state.
 */
export function resumePrefix(userId) {
  if (typeof userId !== "string" || !USER_ID.test(userId)) {
    throw new TypeError("resume: refusing to derive a storage key from an untrusted user id");
  }
  return `${ROOT}${userId}/`;
}

/**
 * The single object key for a user.
 *
 * NO EXTENSION, AND THAT IS THE "no history" GUARANTEE. If the key ended in
 * `.pdf` or `.txt`, replacing a PDF with a text resume would write a second key
 * and orphan the first -- the user would believe they had replaced their resume
 * while the old one sat in the bucket, retrievable, forever. One fixed name
 * makes replacement an overwrite. The content type travels as metadata instead.
 */
export function resumeKey(userId) {
  return `${resumePrefix(userId)}${OBJECT}`;
}

/** `text/plain; charset=utf-8` is `text/plain`. Parameters are not part of the type. */
function normalizeType(contentType) {
  return String(contentType ?? "").split(";")[0].trim().toLowerCase();
}

/**
 * The bytes of a body we are willing to measure, or null.
 *
 * A stream lands in the null branch on purpose. We cannot know a stream's
 * length without draining it, so accepting one would mean either trusting a
 * declared length or enforcing the cap after the object was written -- and
 * `MAX_RESUME_BYTES` explains why neither counts as a cap. Refusing here is the
 * honest version, and it is affordable precisely because the cap is 2 MiB.
 */
function bytesOf(body) {
  if (typeof body === "string") return new TextEncoder().encode(body);
  if (body instanceof ArrayBuffer) return new Uint8Array(body);
  if (ArrayBuffer.isView(body)) return new Uint8Array(body.buffer, body.byteOffset, body.byteLength);
  return null;
}

/**
 * A PDF states what it is in its first five bytes: `%PDF-`.
 *
 * The header must be at offset zero. Readers in the wild tolerate it appearing
 * anywhere in the first kilobyte, and this deliberately does not -- every
 * generator writes it first, and the tolerance exists to rescue damaged files
 * rather than to admit them. A short body needs no length check of its own:
 * `bytes[4]` is `undefined` on a four-byte array, so `every` already refuses it.
 * (A length check WAS here. Mutation testing could not make it fail a test,
 * because it could never be the reason for a refusal, so it went.)
 */
function looksLikePdf(bytes) {
  const header = [0x25, 0x50, 0x44, 0x46, 0x2d];
  return header.every((byte, i) => bytes[i] === byte);
}

/**
 * Plain text has to actually be text: valid UTF-8 and free of the control
 * characters that only appear in binary. Without this, `text/plain` is a label
 * anyone can put on anything and the format allowlist above means nothing.
 *
 * Tab, newline, carriage return and FORM FEED are allowed. The form feed is not
 * an oversight -- it is how a page break survives being pasted out of a PDF, so
 * refusing it would reject a real resume produced the most obvious way.
 */
function looksLikeText(bytes) {
  try {
    new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  } catch {
    return false;
  }
  const allowed = new Set([0x09, 0x0a, 0x0c, 0x0d]);
  return !bytes.some((byte) => byte < 0x20 && !allowed.has(byte));
}

/**
 * Whether this upload may be stored, and the exact bytes if so.
 *
 * Pure, so the whole accept/refuse decision is testable without a store. It
 * hands back the bytes it measured rather than a size, and that is a guard
 * rather than a convenience: `putResume` stores THOSE bytes, so there is no
 * window in which the thing we checked and the thing we wrote could differ.
 *
 * Reasons are distinguishable, unlike `auth.mjs` where every refusal is
 * identical. There is nothing to enumerate here -- the caller is already
 * authenticated and this is their own file -- and a user who is told only
 * "no" about their own upload cannot fix it.
 *
 * @returns {{ok: true, contentType: string, bytes: Uint8Array}
 *          |{ok: false, reason: string}}
 */
export function checkResume(body, contentType) {
  const type = normalizeType(contentType);
  if (!ACCEPTED_TYPES.has(type)) return { ok: false, reason: "unsupported_type" };

  const bytes = bytesOf(body);
  if (!bytes) return { ok: false, reason: "unreadable_body" };
  if (bytes.byteLength === 0) return { ok: false, reason: "empty" };
  if (bytes.byteLength > MAX_RESUME_BYTES) return { ok: false, reason: "too_large" };

  if (type === "application/pdf" && !looksLikePdf(bytes)) return { ok: false, reason: "not_a_pdf" };
  if (type === "text/plain" && !looksLikeText(bytes)) return { ok: false, reason: "not_text" };

  return { ok: true, contentType: type, bytes };
}

/**
 * A filename fit to be stored beside the object. Display only -- it never
 * touches the key, which is derived from the user id alone.
 *
 * It is still cleaned, because the caller that eventually renders it will put
 * it in a `Content-Disposition` header, and a name carrying a CR or LF is a
 * response-splitting bug waiting for that day. Directory components go too: a
 * stored `../../etc/passwd` is harmless here but is a trap for whatever reads
 * this metadata next.
 */
function safeFilename(filename) {
  if (typeof filename !== "string") return "";
  const base = filename.split(/[\\/]/).pop() ?? "";
  return base.replace(/[\u0000-\u001f\u007f]/g, "").trim().slice(0, 100);
}

/** Every key under a prefix, following the cursor. See `deleteResume` for why the loop matters. */
async function listKeys(store, prefix) {
  const keys = [];
  let cursor;
  do {
    const page = await store.list({ prefix, cursor });
    for (const object of page?.objects ?? []) keys.push(object.key);
    cursor = page?.truncated ? page.cursor : undefined;
  } while (cursor);
  return keys;
}

/**
 * Store this user's resume, replacing any resume they already had.
 *
 * ORDER MATTERS. The new object is written BEFORE the old ones are swept, so an
 * interrupted request leaves the user with a resume rather than with none. The
 * reverse order trades a real risk of losing the only copy for a cosmetic one.
 *
 * The sweep exists even though a fixed key makes replacement an overwrite,
 * because "one resume" is then true only for as long as the key derivation
 * never changes. Any object a previous scheme left under this user's prefix is
 * a resume they cannot see and we cannot honestly say we deleted, so the invariant
 * is enforced against the store on every write instead of being assumed.
 *
 * Throws if the store does not end up holding exactly one object for this user.
 * Throwing after a successful write is uncomfortable and is still right: at that
 * point we cannot claim "one resume, no history", and reporting success would be
 * claiming it.
 *
 * @returns {Promise<{ok: true, key: string, size: number, contentType: string, replaced: boolean}
 *                  |{ok: false, reason: string}>}
 */
export async function putResume(store, userId, body, { contentType, filename, now = Date.now() } = {}) {
  const prefix = resumePrefix(userId); // before any work: an untrusted id gets none
  const key = `${prefix}${OBJECT}`;

  const checked = checkResume(body, contentType);
  if (!checked.ok) return checked;

  const priorKeys = await listKeys(store, prefix);

  await store.put(key, checked.bytes, {
    httpMetadata: { contentType: checked.contentType },
    customMetadata: { filename: safeFilename(filename), uploadedAt: new Date(now).toISOString() },
  });

  for (const stale of priorKeys) {
    if (stale !== key) await store.delete(stale);
  }

  const remaining = await listKeys(store, prefix);
  if (remaining.length !== 1 || remaining[0] !== key) {
    throw new Error("resume: store holds more than one resume for this user after a replace");
  }

  return {
    ok: true,
    key,
    size: checked.bytes.byteLength,
    contentType: checked.contentType,
    replaced: priorKeys.length > 0,
  };
}

/**
 * This user's resume object, or null. The store's own object is returned rather
 * than a copy of it, so a caller can stream the body straight into a Response
 * without this module ever holding the file in memory on the read path.
 */
export async function getResume(store, userId) {
  return (await store.get(resumeKey(userId))) ?? null;
}

/**
 * Delete this user's resume and PROVE IT, in this request.
 *
 * The proof is two reads after the deletes, and they catch different lies. The
 * `get` is the user's own claim made literal -- "a read issued after the delete
 * returns nothing" -- and it fails if a store accepted a delete and kept serving
 * the object. The `list` catches an object under this user's prefix that the
 * canonical key does not name, which a `get` on that key cannot see. A store
 * that satisfies neither is a store we cannot honestly report a deletion from,
 * so this throws instead of returning.
 *
 * The pagination in `listKeys` is load-bearing here rather than defensive: a
 * sweep that stops at the first page deletes some of a user's data and reports
 * that it deleted all of it, which is the exact failure this whole task exists
 * to prevent.
 *
 * Deleting when there is nothing to delete is a success with `deleted: 0`.
 * Account deletion calls this for every user, and most of them never uploaded
 * anything; making that path throw would turn "no resume" into a failed account
 * deletion.
 *
 * @returns {Promise<{deleted: number, verified: true}>}
 */
export async function deleteResume(store, userId) {
  const prefix = resumePrefix(userId);
  const key = `${prefix}${OBJECT}`;

  const keys = await listKeys(store, prefix);
  for (const stored of keys) await store.delete(stored);

  if (await store.get(key)) {
    throw new Error("resume: object still readable after delete; deletion cannot be claimed");
  }
  const left = await listKeys(store, prefix);
  if (left.length > 0) {
    throw new Error("resume: objects remain under the user's prefix after delete");
  }

  return { deleted: keys.length, verified: true };
}
