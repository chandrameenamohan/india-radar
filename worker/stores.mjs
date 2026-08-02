// The adapters between Cloudflare's bindings and the shapes the feature modules
// were written against.
//
// The modules take their storage as an ARGUMENT and name no binding, which is
// what let three of them be built and mutation-tested in parallel with no
// infrastructure at all. This file is where that abstraction is paid for: it is
// the only place in the Worker that knows D1 and R2 exist, and it is deliberately
// the dullest file here. Anything clever belongs on the other side of it.

/** Where the profile row lives. One row per user, replaced wholesale. */
const PROFILE_TABLE = "profiles";

/**
 * A profile store over D1.
 *
 * The value is stored as one JSON column rather than a column per field. That is
 * not laziness about schema design — `profile.mjs` owns which fields exist and
 * validates them, so a column per field would put that decision in two places
 * and make every new field a migration. The row is small, always read whole and
 * always written whole, so nothing here wants a query the JSON blob prevents.
 * ponytail: revisit when something needs to FILTER users by a profile field —
 * that is the query this shape cannot serve, and the signal to normalise.
 */
export function profileStore(db) {
  return {
    async get(userId) {
      const row = await db
        .prepare(`SELECT value FROM ${PROFILE_TABLE} WHERE user_id = ?`)
        .bind(userId)
        .first();
      if (!row?.value) return null;
      try {
        return JSON.parse(row.value);
      } catch {
        // A row we cannot parse is not an empty profile. Returning null would
        // silently hand the reader a blank form and then overwrite whatever was
        // really there on the next save.
        throw new Error("profile: stored value is not readable JSON");
      }
    },

    async put(userId, value) {
      await db
        .prepare(
          `INSERT INTO ${PROFILE_TABLE} (user_id, value, updated_at)
           VALUES (?1, ?2, ?3)
           ON CONFLICT(user_id) DO UPDATE SET value = ?2, updated_at = ?3`,
        )
        .bind(userId, JSON.stringify(value), new Date().toISOString())
        .run();
    },

    async delete(userId) {
      await db.prepare(`DELETE FROM ${PROFILE_TABLE} WHERE user_id = ?`).bind(userId).run();
    },
  };
}

/**
 * A resume store over R2.
 *
 * `resume.mjs` verifies its own deletions by reading back and by listing, so this
 * adapter must not paper over either. In particular `list` returns the raw keys
 * and the truncation cursor rather than a convenience array: the module walks
 * pages deliberately, because a deletion sweep that stopped at the first page
 * would leave objects behind and still report success.
 */
export function resumeStore(bucket) {
  return {
    put: (key, body, options) => bucket.put(key, body, options),
    get: (key) => bucket.get(key),
    delete: (key) => bucket.delete(key),
    async list({ prefix, cursor } = {}) {
      const page = await bucket.list({ prefix, cursor });
      return {
        objects: (page.objects ?? []).map((o) => ({ key: o.key })),
        truncated: Boolean(page.truncated),
        cursor: page.cursor ?? null,
      };
    },
  };
}
