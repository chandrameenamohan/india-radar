// T14.2 — the application profile, and the one rule in it that cannot be taken back.
//
// SPEC v4 splits a user's constant facts BY PURPOSE, and this module is the
// server-side half of that split. The operational facts -- the ones
// `learning-tests/apply_questions_live.py` measured companies actually asking --
// live here because they will shape what we show the user. The EEO demographics
// live in the reader's own browser and never arrive here at all.
//
// THE NEGATIVE RULE IS THE FEATURE. Gender, sexual orientation, race, ethnicity,
// veteran status and disability status are Article 9 special-category data in the
// EU and the UK. They never needed to sync, so the cheapest correct handling of
// them is not to hold them. That decision is free today and irreversible the
// moment one row is written, which is why this file REFUSES such a key BY NAME
// and LOUDLY rather than dropping it quietly. A caller that silently loses a
// field believes the write worked; a caller that catches a thrown
// `DemographicFieldError` has been told, in the stack trace, that it is asking
// this project to hold something it has promised not to.
//
// WHY TWO FAILURE MODES, AND THE LINE BETWEEN THEM. A field the user typed badly
// -- a salary that is 10,000 characters long, a start date of 2026-02-30 -- is
// ordinary and expected, so it comes back as data: `{ ok: false, errors }`, one
// entry per field, so an interface can mark all of them at once. A demographic
// key is not user error. It is a caller wired against this module in a way SPEC
// v4 forbids, it cannot be fixed by the person at the keyboard, and it must not
// be representable as one of several field-level notes an interface might choose
// to ignore. So it throws. The two are deliberately not interchangeable, and a
// test asserts that they stay that way.
//
// ZERO DEPENDENCIES AND NO BINDINGS, for the same reason `auth.mjs` has none: the
// Workers runtime will not start on this machine (see T14.1), so anything that
// imports D1 or wrangler is untestable here. Storage arrives as an argument --
// any `{ get(userId), put(userId, value) }` -- which means the whole of this
// file's behaviour, including every refusal, is checkable under `node --test`
// with no infrastructure at all. The D1 adapter is the integrator's to write and
// is the only thing that needs to know a binding exists.

/**
 * How deep the demographic scan will look before giving up.
 *
 * A caller may reasonably nest -- `{ profile: {...} }`, an array of answers --
 * and a scan that only checked top-level keys would be defeated by a wrapper
 * object, which is not a threat model so much as an afternoon's refactor. Past
 * this depth we REFUSE rather than accept: "we could not look" and "there was
 * nothing there" are different facts, and this project renders them differently
 * everywhere else it appears. It also makes a self-referential input terminate
 * in a refusal instead of a stack overflow, which is why no cycle set is needed.
 */
const MAX_SCAN_DEPTH = 8;

/** Long enough for "£120k base, flexible for the right role"; short enough to be a form field. */
const MAX_TEXT = 200;

/**
 * The cap for the two fields a company asks in prose rather than as a value:
 * "how did you hear about this role" and "what address would you work from, and
 * say so if you would need to relocate". Both draw a sentence.
 */
const MAX_LONG_TEXT = 500;

/** A profile listing fifty languages is a paste accident, not a polyglot. */
const MAX_LANGUAGES = 20;

/** Clerk ids are ~32 characters. The cap exists so a bad id cannot become a key of any size. */
const MAX_USER_ID = 128;

/**
 * The stored shape's version.
 *
 * Not speculative schema astronomy: Workers deploys roll, so two versions of this
 * module run against the same D1 for a few minutes on every release. A row
 * written by a NEWER deploy must not be read by an older one and merged back
 * down, because that silently deletes whatever the new version added. Reads
 * refuse a version they do not recognise, and refusing a read also prevents the
 * overwrite, because every write here merges onto a read.
 */
const PROFILE_VERSION = 1;

/**
 * Word segments that mean a key is carrying data this project will not hold.
 *
 * MATCHED PER SEGMENT, NOT PER SUBSTRING. `candidateGender`, `gender_identity`
 * and `eeo-race` all match; `trace_id` does not, because "trace" is one segment
 * and "race" never appears as its own. Substring matching would have refused
 * `trace_id` with a message about ethnicity, which is the kind of wrong error
 * that teaches a reader to distrust every other one.
 *
 * The first group is the five categories T14.2 names. The second is the rest of
 * GDPR Article 9 and its immediate neighbours, and it is here because the cost of
 * including them is bounded to nothing: a key not on the operational allowlist
 * below is refused either way, so this list only decides WHICH refusal a caller
 * gets. Given that, the wider list is free and the narrower one is a wager that
 * nobody will ever wire up a religion or health field. Anything that turns out to
 * be genuinely operational -- see the note on nationality below -- gets refused
 * loudly first and discussed second, which is the correct order for this rule.
 */
const DEMOGRAPHIC_SEGMENTS = new Set([
  // The five EEO categories, and the spellings a form or an ORM actually uses.
  "gender", "genders", "sex", "sexes", "sexual", "sexuality", "orientation",
  "lgbt", "lgbtq", "lgbtqia", "transgender", "trans", "nonbinary", "enby",
  "race", "races", "racial", "ethnicity", "ethnicities", "ethnic", "ethnicgroup",
  "veteran", "veterans", "disability", "disabilities", "disabled", "handicap",
  "pronoun", "pronouns",
  // "Will you need accommodations to interview with us?" is one of the recurring
  // measured questions, and any answer to it -- including a bare yes -- states
  // disability status, which is the same Article 9 class as `disability_status`
  // two lines up. It reaches us as a question to ANSWER, never as a fact to
  // KEEP. This was left out of an earlier draft on the grounds that
  // "accommodation" means housing in British English and could collide with a
  // relocation field; `work_address` is now that field, so the ambiguity has
  // somewhere else to live and the word can be refused outright.
  "accommodation", "accommodations", "accessibility",
  // The words that mark a payload as demographic even when the field is not.
  "eeo", "eeoc", "demographic", "demographics", "diversity", "protectedclass",
  // The rest of Article 9, plus criminal-conviction data from Article 10.
  "religion", "religious", "political", "politics", "tradeunion",
  "health", "medical", "pregnancy", "pregnant", "biometric", "genetic",
  "criminal", "conviction", "convictions",
]);

/**
 * The demographic fields by their canonical names, for the browser-side store to
 * own. Exported so the page and this module cannot drift into disagreeing about
 * what the split is; nothing here reads it.
 */
export const DEMOGRAPHIC_FIELDS = Object.freeze([
  "gender",
  "sexual_orientation",
  "race_ethnicity",
  "veteran_status",
  "disability_status",
]);

/** Thrown when a key would have put special-category data in our storage. */
export class DemographicFieldError extends Error {
  constructor(hits) {
    const described = hits.map((hit) => `${hit.path} (matches "${hit.matched}")`).join(", ");
    super(`profile storage refuses demographic fields: ${described}`);
    this.name = "DemographicFieldError";
    /** Every offending key, by path, so a caller learns all of them at once. */
    this.fields = hits.map((hit) => hit.path);
    /** The segment each one matched on, so the refusal explains itself. */
    this.matched = hits.map((hit) => hit.matched);
  }
}

/**
 * Thrown when the module refuses for a reason that is not the caller's field
 * values: an unreadable stored row, an unscannable input, a missing user id.
 * These are all "we will not proceed", never "the user typed something odd",
 * and `code` is the machine-readable half.
 */
export class ProfileStoreError extends Error {
  constructor(code, message) {
    super(message);
    this.name = "ProfileStoreError";
    this.code = code;
  }
}

/** `raceEthnicity` -> ["race","ethnicity"]; `trace_id` -> ["trace","id"]. */
function segmentsOf(key) {
  return key
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter(Boolean);
}

/**
 * The demographic word a key carries, or null.
 *
 * @param {unknown} key
 * @returns {string|null} the matched segment, which is what the refusal names
 */
export function demographicMatch(key) {
  if (typeof key !== "string") return null;
  for (const segment of segmentsOf(key)) {
    if (DEMOGRAPHIC_SEGMENTS.has(segment)) return segment;
  }
  return null;
}

function scan(value, path, depth, hits) {
  if (value === null || typeof value !== "object") return;
  if (depth > MAX_SCAN_DEPTH) {
    throw new ProfileStoreError(
      "input_too_deep",
      `profile input nests deeper than ${MAX_SCAN_DEPTH} levels at ${path || "the root"}, so it cannot be checked for demographic fields and is refused`,
    );
  }
  if (Array.isArray(value)) {
    value.forEach((item, index) => scan(item, `${path}[${index}]`, depth + 1, hits));
    return;
  }
  for (const key of Object.keys(value)) {
    const here = path ? `${path}.${key}` : key;
    const matched = demographicMatch(key);
    if (matched) hits.push({ path: here, matched });
    scan(value[key], here, depth + 1, hits);
  }
}

/**
 * Refuse, by name, any input carrying a demographic key at any depth.
 *
 * Every hit is collected before throwing rather than throwing on the first,
 * because a caller wiring an EEO form up to the wrong endpoint should learn the
 * whole list in one run instead of one field per deploy.
 *
 * @param {unknown} input
 * @throws {DemographicFieldError} if any key is special-category data
 * @throws {ProfileStoreError} if the input is too deep to check
 */
export function assertNoDemographics(input) {
  const hits = [];
  scan(input, "", 0, hits);
  if (hits.length > 0) throw new DemographicFieldError(hits);
}

const invalid = (reason) => ({ ok: false, reason });

function textField(maxLength) {
  return (value) => {
    if (typeof value !== "string") return invalid("not_a_string");
    const trimmed = value.trim();
    // REFUSED, NOT TRUNCATED. Everything stored here is copied into a form the
    // user signs their name to, and a silently shortened salary or start date is
    // a fact they did not state. `absence stays absence` cuts both ways: we do
    // not invent, and we do not edit.
    if (trimmed.length > maxLength) return invalid("too_long");
    return { ok: true, value: trimmed };
  };
}

function enumField(allowed) {
  return (value) => {
    if (typeof value !== "string") return invalid("not_a_string");
    if (!allowed.includes(value)) return invalid("not_allowed");
    return { ok: true, value };
  };
}

function booleanField(value) {
  // Strings are refused rather than coerced, because "false" is truthy and that
  // is exactly how a reader who will not relocate ends up recorded as one who
  // will -- a wrong fact, on a form, with their name on it.
  if (typeof value !== "boolean") return invalid("not_a_boolean");
  return { ok: true, value };
}

function isoDateField(value) {
  if (typeof value !== "string") return invalid("not_a_string");
  // THE ROUND TRIP IS THE WHOLE CHECK, and it enforces the shape as well as the
  // calendar. A `^\d{4}-\d{2}-\d{2}$` test stood here and was DELETED rather
  // than kept as a documented survivor: it could not change the outcome for any
  // input, because the comparison below is against `toISOString`, which emits
  // nothing but YYYY-MM-DD -- so a value only passes if it is already exactly
  // that. That also holds under a more lenient `Date` parser than V8's, which
  // was the argument for keeping the regex and does not survive contact with
  // what the comparison actually compares.
  //
  // What the round trip catches that a shape test cannot: 2026-02-30 and
  // 2026-13-01 both LOOK like dates and JS rolls them forward into March and
  // January, so a value that does not come back identical was never a day on
  // anyone's calendar. Anything unparseable throws inside `toISOString` instead.
  let roundTripped;
  try {
    roundTripped = new Date(`${value}T00:00:00Z`).toISOString().slice(0, 10);
  } catch {
    return invalid("not_a_date");
  }
  if (roundTripped !== value) return invalid("not_a_date");
  return { ok: true, value };
}

function languagesField(value) {
  if (!Array.isArray(value)) return invalid("not_an_array");
  if (value.length > MAX_LANGUAGES) return invalid("too_many");
  const seen = new Set();
  const languages = [];
  for (const entry of value) {
    if (typeof entry !== "string") return invalid("not_a_string");
    const trimmed = entry.trim();
    if (trimmed === "") continue;
    if (trimmed.length > MAX_TEXT) return invalid("too_long");
    const key = trimmed.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    languages.push(trimmed);
  }
  if (languages.length === 0) return { ok: true, clear: true };
  return { ok: true, value: languages };
}

/**
 * The operational half of the split: the fields companies were measured asking.
 *
 * `work_authorization` is an enum rather than free text because it is the one
 * field here meant to shape what we SHOW the user -- a role that cannot sponsor
 * is a different thing to a reader who needs sponsorship -- and free text cannot
 * do that. Its three values are the two questions Greenhouse actually asks
 * ("are you authorized to work" and "will you now or in the future require
 * sponsorship") collapsed into the three combinations that exist.
 *
 * `salary_expectation` is free text and stays free text: T14.2 puts validating a
 * salary figure against anything explicitly out of scope, because it is the
 * user's number. We hold what they typed and hand back what they typed.
 *
 * `work_address` is the measured question "what is the address from which you
 * plan on working -- if you would need to relocate, please specify". It is free
 * text and is deliberately NOT parsed into a structured address, for the same
 * reason: a normalised address is a fact we assembled rather than one the user
 * stated. It is operational rather than demographic because it shapes what we
 * show the reader, exactly as `relocation` and `onsite` do.
 */
const FIELDS = {
  work_authorization: enumField([
    "authorized",
    "authorized_needs_future_sponsorship",
    "sponsorship_required",
  ]),
  relocation: booleanField,
  onsite: enumField(["onsite", "hybrid", "remote"]),
  earliest_start: isoDateField,
  salary_expectation: textField(MAX_TEXT),
  languages: languagesField,
  heard_about_role: textField(MAX_LONG_TEXT),
  work_address: textField(MAX_LONG_TEXT),
};

/** The seven fields this project stores server-side. Nothing else is storable. */
export const OPERATIONAL_FIELDS = Object.freeze(Object.keys(FIELDS));

/**
 * Blank means CLEAR, and clearing means the key is absent afterwards.
 *
 * This is the honesty invariant reaching down into storage. T14.5 renders a fact
 * we hold as an answer and a fact we lack as a marked gap, and it tells them
 * apart by the key being there. An empty string stored for `salary_expectation`
 * would render as an answer of "", which is a claim we never had -- so a blank
 * never reaches the store, and the field goes back to being a gap instead.
 */
function isBlank(value) {
  if (value === null || value === undefined) return true;
  if (typeof value === "string") return value.trim() === "";
  return false;
}

/**
 * Validate a patch of operational fields.
 *
 * This is the serializer T14.2's acceptance names: the one place an EEO key is
 * refused before anything can be written.
 *
 * @param {object} patch  the fields the user is setting; absent keys are untouched
 * @returns {{ok: true, value: object, cleared: string[]}|{ok: false, errors: {field: string, reason: string}[]}}
 * @throws {DemographicFieldError} if the patch carries special-category data
 * @throws {ProfileStoreError} if the patch is too deeply nested to check
 */
export function serializeProfile(patch) {
  // FIRST, BEFORE ANYTHING ELSE. Not after shape checks and not per field: a
  // demographic key must be refused even when the rest of the payload is
  // rubbish, because the interesting caller is the one still under construction.
  assertNoDemographics(patch);

  if (patch === null || typeof patch !== "object" || Array.isArray(patch)) {
    return { ok: false, errors: [{ field: "", reason: "not_an_object" }] };
  }

  const value = {};
  const cleared = [];
  const errors = [];

  for (const key of Object.keys(patch)) {
    const validate = Object.hasOwn(FIELDS, key) ? FIELDS[key] : null;
    if (!validate) {
      // The allowlist is the actual guarantee, and the deny list above only
      // improves the error. An unknown key is reported rather than dropped
      // because a typo that vanishes silently looks exactly like a save that
      // worked, and the user finds out when a form comes back empty.
      errors.push({ field: key, reason: "unknown_field" });
      continue;
    }
    if (isBlank(patch[key])) {
      cleared.push(key);
      continue;
    }
    const result = validate(patch[key]);
    if (!result.ok) {
      errors.push({ field: key, reason: result.reason });
    } else if (result.clear) {
      cleared.push(key);
    } else {
      value[key] = result.value;
    }
  }

  if (errors.length > 0) return { ok: false, errors };
  return { ok: true, value, cleared };
}

function assertUserId(userId) {
  if (typeof userId !== "string" || userId.trim() === "" || userId.length > MAX_USER_ID) {
    // An absent or empty user id is not a nuisance, it is every reader sharing
    // one row. `auth.mjs` exists so that a stranger cannot hold another reader's
    // application; a blank key here would achieve the same thing by accident.
    throw new ProfileStoreError("invalid_user_id", "profile access requires a non-empty user id");
  }
}

/**
 * Read a stored row and rebuild it from named fields.
 *
 * A row is not trusted because it came out of our own store -- the same reason
 * `auth.mjs` rebuilds a JWK from named fields rather than passing the published
 * one to `importKey`. Unknown keys are dropped, because a shape written by some
 * other path is not something to hand onward. A DEMOGRAPHIC key is not dropped,
 * it throws: its presence means the promise has already been broken somewhere
 * upstream, and quietly serving around the evidence is worse than failing.
 */
async function readRow(store, userId) {
  const row = await store.get(userId);
  if (row === null || row === undefined) return {};
  if (typeof row !== "object" || Array.isArray(row)) {
    throw new ProfileStoreError("corrupt_row", `stored profile for ${userId} is not an object`);
  }
  if (row.version !== PROFILE_VERSION) {
    throw new ProfileStoreError(
      "unknown_version",
      `stored profile for ${userId} is version ${row.version}, and this deploy writes version ${PROFILE_VERSION}`,
    );
  }

  const stored = row.fields ?? {};
  assertNoDemographics(stored);

  const fields = {};
  for (const key of OPERATIONAL_FIELDS) {
    if (Object.hasOwn(stored, key)) fields[key] = stored[key];
  }
  return fields;
}

/**
 * The user's operational profile. `{}` when they have never saved one, so an
 * absent fact and an absent profile are the same shape to a caller: a gap.
 *
 * @param {{get: Function, put: Function}} store
 * @param {string} userId
 * @returns {Promise<object>}
 */
export async function loadProfile(store, userId) {
  assertUserId(userId);
  return await readRow(store, userId);
}

/**
 * Merge a patch into the user's stored profile.
 *
 * The order below is the point of this function. Validation runs BEFORE the
 * store is touched at all, so a rejected patch performs no read and no write:
 * there is no state in which half a bad save landed, and a demographic key is
 * refused without the store ever having seen it.
 *
 * @param {{get: Function, put: Function}} store
 * @param {string} userId
 * @param {object} patch
 * @param {{now?: number}} [options]  `now` is injected so tests can assert the stamp
 * @returns {Promise<{ok: true, value: object}|{ok: false, errors: object[]}>}
 * @throws {DemographicFieldError|ProfileStoreError}
 */
export async function saveProfile(store, userId, patch, { now = Date.now() } = {}) {
  assertUserId(userId);
  const serialized = serializeProfile(patch);
  if (!serialized.ok) return serialized;

  const current = await readRow(store, userId);
  // Rebuilt, never passed through: the object handed to `put` is ours, so a
  // caller that keeps a reference to its patch and mutates it afterwards cannot
  // reach into stored state, and nothing the caller attached can ride along.
  const fields = { ...current, ...serialized.value };
  for (const key of serialized.cleared) delete fields[key];

  await store.put(userId, { version: PROFILE_VERSION, updated_at: now, fields });
  return { ok: true, value: fields };
}
