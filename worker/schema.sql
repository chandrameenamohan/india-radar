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
