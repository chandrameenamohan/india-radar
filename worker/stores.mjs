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

/** Where the free-tier counters live. See `schema.sql` for why they exist at all. */
const USAGE_TABLE = "resume_usage";

/** The month key the counter resets on. UTC, so it does not turn over twice. */
export const usageMonth = (now = Date.now()) => new Date(now).toISOString().slice(0, 7);

/**
 * The R2 usage counters over D1.
 *
 * `load` is ONE query returning both totals, because it sits in front of every
 * upload and the whole feature is only worth having if it is cheaper than the
 * thing it protects. The two aggregates have different scopes -- bytes exclude
 * the caller (their old resume is replaced), ops include everyone (see
 * `withinFreeTier`) -- which is why they are two CASE expressions over one scan
 * rather than two statements.
 *
 * A missing row and an empty table both have to read as zero. `SUM` over no rows
 * is NULL, which `Number` already makes 0, but a driver that answers `SELECT
 * SUM(...)` with NO ROW leaves `undefined` -- and `Number(undefined)` is NaN,
 * which is false for `>`, so every limit would silently pass. Hence `?? 0`, and
 * hence no `COALESCE` beside it: two guards against one failure mean neither can
 * be shown to be doing anything, and a mutation sweep proved exactly that.
 * ponytail: counted on the write path only, so a crash between the R2 put and
 * this row undercounts by one resume. Move to a scheduled reconcile against
 * `bucket.list()` if the drift ever matters -- it costs Class A ops to fix.
 */
export function usageStore(db) {
  return {
    async load(userId, month = usageMonth()) {
      const row = await db
        .prepare(
          `SELECT SUM(CASE WHEN user_id <> ?1 THEN bytes ELSE 0 END) AS other_bytes,
                  SUM(CASE WHEN month = ?2 THEN ops ELSE 0 END) AS ops
             FROM ${USAGE_TABLE}`,
        )
        .bind(userId, month)
        .first();
      return { otherBytes: Number(row?.other_bytes ?? 0), ops: Number(row?.ops ?? 0) };
    },

    /**
     * Record what a write cost. `bytes` is what the user is now storing (0 after
     * a deletion); ops ACCUMULATE within a month and start again outside one,
     * which is the whole of the monthly reset -- there is no job to forget to run.
     */
    async record(userId, bytes, ops, month = usageMonth()) {
      await db
        .prepare(
          `INSERT INTO ${USAGE_TABLE} (user_id, bytes, ops, month)
           VALUES (?1, ?2, ?3, ?4)
           ON CONFLICT(user_id) DO UPDATE SET
             bytes = ?2,
             ops   = CASE WHEN month = ?4 THEN ops + ?3 ELSE ?3 END,
             month = ?4`,
        )
        .bind(userId, bytes, ops, month)
        .run();
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
