-- D1 schema for the Workers API. Apply with:
--   npx wrangler d1 execute roleatlas --file worker/schema.sql --remote
--
-- ONE TABLE, and only the operational half of a profile is ever in it. The EEO
-- demographic fields -- gender, sexual orientation, race, veteran and disability
-- status, pronouns, interview accommodations -- are Article 9 special-category
-- data in the EU and UK, they live in the reader's own browser, and there is
-- deliberately NO COLUMN HERE THAT COULD HOLD ONE. `profile.mjs` refuses them by
-- name on the way in; this schema is the second lock, and the reason it is worth
-- having two is that a schema is far harder to change by accident than a
-- validator is.

CREATE TABLE IF NOT EXISTS profiles (
  -- The Clerk subject, and the only identifier in the system. There is no
  -- surrogate key, because a surrogate key invites a route that takes one --
  -- and a route that takes a user id is a route that can be handed somebody
  -- else's. Every query is scoped by the id the session proved.
  user_id    TEXT PRIMARY KEY NOT NULL,

  -- The validated operational fields, as JSON. `profile.mjs` owns which fields
  -- exist and what each may contain; a column per field would put that decision
  -- in two places and make every new field a migration. The row is always read
  -- and written whole.
  value      TEXT NOT NULL,

  updated_at TEXT NOT NULL
);

-- The R2 free tier, made countable.
--
-- R2's free tier is 10 GB-month of storage and 1M Class A operations a month,
-- and Cloudflare does not stop at it -- it bills. The human has decided the
-- correct behaviour past the line is to REFUSE THE UPLOAD, so something has to
-- know the total before the write happens, and R2 itself cannot answer "how many
-- bytes am I holding" without listing every object (which is itself Class A ops).
-- So the total is counted here, on the write path that already exists.
--
-- One row per user, because a single global counter cannot do the arithmetic a
-- REPLACEMENT needs: the new resume displaces the old one rather than adding to
-- it, and only a per-user figure knows what to subtract.
--
-- `ops` is Class A only (writes and lists) and resets by `month` rather than by
-- a scheduled job -- a row whose month is not the current one simply counts zero.
-- Reads are Class B, 10M a month, and are deliberately NOT counted: counting them
-- would mean a D1 write per download, and D1's own free tier (100k writes a day)
-- is the tighter of the two. The 10x-larger read allowance is the headroom that
-- pays for that.
CREATE TABLE IF NOT EXISTS resume_usage (
  user_id TEXT PRIMARY KEY NOT NULL,
  bytes   INTEGER NOT NULL,
  ops     INTEGER NOT NULL,
  month   TEXT    NOT NULL  -- "YYYY-MM", UTC
);
