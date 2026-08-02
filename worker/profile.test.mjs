// T14.2 — attacks on the profile store. Run: node --test worker/profile.test.mjs
//
// The happy path here is one test. The rest of this file is trying to get an EEO
// field into storage, because that is the half of T14.2 that cannot be undone: a
// wrong salary is an edit, and one stored `gender` column is a disclosure that
// exists from the moment it is written and is still true after it is dropped.
//
// So the tests below are written as the callers we are afraid of -- one that
// wraps the payload in an object, one that spells the field in camelCase, one
// that means well and sends the browser's whole form -- rather than as a
// demonstration that saving a start date works.
//
// The store is injected and lives in a Map, which is what lets this run with no
// D1, no wrangler and no Workers runtime; see the note at the top of profile.mjs
// for why that is a requirement here rather than a convenience.

import { strict as assert } from "node:assert";
import { test } from "node:test";

import {
  DEMOGRAPHIC_FIELDS,
  DemographicFieldError,
  OPERATIONAL_FIELDS,
  ProfileStoreError,
  assertNoDemographics,
  demographicMatch,
  loadProfile,
  saveProfile,
  serializeProfile,
} from "./profile.mjs";

const USER = "user_2abc";
const NOW = 1_800_000_000_000;

/**
 * Deliberately NOT copying on put. A store that serialised its input would hide
 * a module that passed the caller's own object straight through, and one of the
 * tests below exists specifically to catch that.
 */
function makeStore(seed = null) {
  const rows = new Map();
  if (seed) rows.set(USER, seed);
  return {
    rows,
    writes: 0,
    async get(userId) {
      return rows.has(userId) ? rows.get(userId) : null;
    },
    async put(userId, value) {
      this.writes += 1;
      rows.set(userId, value);
    },
  };
}

/** A complete, valid profile: every operational field the measurement found. */
const FULL = {
  work_authorization: "sponsorship_required",
  relocation: true,
  onsite: "hybrid",
  earliest_start: "2026-09-01",
  salary_expectation: "£120,000 base, flexible for the right role",
  languages: ["English", "Hindi"],
  heard_about_role: "A friend who works there sent me the posting.",
  work_address: "Flat 4, 27 Fictional Road, London NW1 2AB — I would relocate for the right role.",
};

test("a full profile round-trips, and comes back to a different session unchanged", async () => {
  const store = makeStore();
  const saved = await saveProfile(store, USER, FULL, { now: NOW });
  assert.equal(saved.ok, true);

  // A "second browser" is nothing more than a second read against the same
  // store with no memory of the first -- which is exactly what the acceptance
  // means by seeing the fields again on a later visit from another machine.
  assert.deepEqual(await loadProfile(store, USER), FULL);
  assert.equal(store.rows.get(USER).updated_at, NOW);
});

test("every EEO field is refused BY NAME, in every spelling, and nothing is written", async () => {
  // The list is what an application form, an ORM and a hand-written fetch would
  // each call these fields. If any single one of them ever gets through, the
  // decision SPEC v4 made is already broken and cannot be remade.
  const attempts = [
    "gender", "Gender", "gender_identity", "genderIdentity", "candidate_gender",
    "sex", "sexual_orientation", "sexualOrientation", "sexuality", "orientation",
    "lgbtq", "transgender", "nonbinary",
    "race", "Race", "ethnicity", "race_ethnicity", "raceEthnicity", "ethnicGroup",
    "veteran", "veteran_status", "veteranStatus", "protected_veteran",
    "disability", "disability_status", "disabilityStatus", "disabilities", "is_disabled",
    "pronouns", "eeo_gender", "demographics", "diversity_data",
    "religion", "political_affiliation", "health_conditions", "criminal_convictions",
    // An answer to "will you need accommodations to interview with us?" states
    // disability status even when it is a bare yes, so the question is one to
    // answer from the browser and never one to keep.
    "accommodations", "accommodation", "interview_accommodations",
    "interviewAccommodations", "accessibility_needs",
  ];

  for (const key of attempts) {
    const store = makeStore();
    await assert.rejects(
      () => saveProfile(store, USER, { [key]: "any value at all" }),
      (error) => {
        assert.equal(error.name, "DemographicFieldError", `not refused as demographic: ${key}`);
        assert.deepEqual(error.fields, [key], `refusal does not name the field: ${key}`);
        assert.match(error.message, new RegExp(key.replace(/[[\]]/g, "\\$&")));
        return true;
      },
      `accepted an EEO field: ${key}`,
    );
    assert.equal(store.writes, 0, `wrote to the store while refusing ${key}`);
  }
});

test("a demographic key is refused even when wrapped, nested or inside an array", async () => {
  // The caller we actually expect: someone who posts the whole browser form,
  // demographics in their own sub-object, and reasonably assumes the server
  // takes the part it recognises.
  const store = makeStore();
  const nested = [
    { profile: FULL, eeo: { gender: "female" } },
    { answers: [{ question: "Gender", value: "female" }, { race: "prefer not to say" }] },
    { a: { b: { c: { d: { veteranStatus: "no" } } } } },
  ];
  for (const payload of nested) {
    await assert.rejects(() => saveProfile(store, USER, payload), DemographicFieldError);
  }
  assert.equal(store.writes, 0);
});

test("the refusal gives the path to the offending key, indexed where it sits in an array", async () => {
  // "Refuse by name" is only useful if the name locates the field. A caller
  // posting an array of answers gets `answers[1].race`, which they can go and
  // find; `answers.1.race` is a path no property access reads back.
  await assert.rejects(
    () => saveProfile(makeStore(), USER, { answers: [{ onsite: "remote" }, { race: "prefer not to say" }] }),
    (error) => {
      assert.deepEqual(error.fields, ["answers[1].race"]);
      return true;
    },
  );
  await assert.rejects(
    () => saveProfile(makeStore(), USER, { candidate: { gender: "female" } }),
    (error) => {
      assert.deepEqual(error.fields, ["candidate.gender"]);
      return true;
    },
  );
  // A wrapper whose own name is a marker word is reported as well as its
  // contents, because `eeo` is the caller telling us what the object is.
  await assert.rejects(
    () => saveProfile(makeStore(), USER, { eeo: { gender: "female" } }),
    (error) => {
      assert.deepEqual(error.fields, ["eeo", "eeo.gender"]);
      return true;
    },
  );
});

test("one demographic key refuses the whole save, including the valid fields beside it", async () => {
  // Partial acceptance would be the worst of both: the user believes their EEO
  // answer synced, and it did not, and the difference is invisible to them.
  const store = makeStore();
  await assert.rejects(
    () => saveProfile(store, USER, { ...FULL, gender: "female" }),
    DemographicFieldError,
  );
  assert.equal(store.writes, 0);
  assert.deepEqual(await loadProfile(store, USER), {});
});

test("all offending keys are named at once, not one refusal at a time", async () => {
  await assert.rejects(
    () => saveProfile(makeStore(), USER, { gender: "f", race: "x", onsite: "remote" }),
    (error) => {
      assert.deepEqual(error.fields.sort(), ["gender", "race"]);
      assert.deepEqual(error.matched.sort(), ["gender", "race"]);
      return true;
    },
  );
});

test("a demographic key REFUSES where an unrecognised key merely reports", async () => {
  // This is the test that can tell whether the deny list runs at all. The
  // allowlist would reject `gender` on its own -- as an unknown field, returned
  // as data, indistinguishable from a typo, quietly ignorable by an interface.
  // Only the deny list makes it throw, and only this asymmetry proves it.
  const store = makeStore();
  const typo = await saveProfile(store, USER, { salery_expectation: "120k" });
  assert.equal(typo.ok, false);
  assert.deepEqual(typo.errors, [{ field: "salery_expectation", reason: "unknown_field" }]);

  await assert.rejects(() => saveProfile(store, USER, { gender: "female" }), DemographicFieldError);
  assert.equal(store.writes, 0, "an unknown field must not be written either");
});

test("a key that merely contains a demographic word as a substring is not refused", async () => {
  // `trace_id` must not be reported as ethnicity. A wrong refusal teaches the
  // reader of a stack trace to distrust the right ones.
  for (const innocent of ["trace_id", "unisex", "bracket", "embraces"]) {
    assert.equal(demographicMatch(innocent), null, `false positive on ${innocent}`);
  }
  for (const guilty of ["gender", "candidateRace", "eeo-veteran-status"]) {
    assert.notEqual(demographicMatch(guilty), null, `missed ${guilty}`);
  }
});

test("demographicMatch answers null for a non-string instead of throwing", () => {
  // It is exported, so the callers are not only `scan` -- and the one thing a
  // key check must never do is throw on the way to deciding, because a caller
  // that wraps it in a try/catch and swallows the error has just built the
  // silent drop this whole module exists to prevent.
  for (const bad of [42, null, undefined, {}, [], true, Symbol("gender")]) {
    assert.equal(demographicMatch(bad), null, `threw or matched on ${String(bad)}`);
  }
});

test("no operational field is itself caught by the demographic list", () => {
  // A collision here would make a field permanently unsavable and the failure
  // would look like a caller bug rather than a list that ate its own allowlist.
  for (const field of OPERATIONAL_FIELDS) {
    assert.equal(demographicMatch(field), null, `the deny list swallows ${field}`);
  }
  // The eight measured fields, and this list is the vocabulary the rest of the
  // worker aligns to -- storage names the fields, not the other way round.
  assert.deepEqual(OPERATIONAL_FIELDS, [
    "work_authorization",
    "relocation",
    "onsite",
    "earliest_start",
    "salary_expectation",
    "languages",
    "heard_about_role",
    "work_address",
  ]);
  // `work_address` is the one operational field whose name sits closest to the
  // deny list -- "accommodation" is refused, and in British English it means
  // housing. The assertion above that no operational field matches is what
  // stops the two from colliding as either list grows.
  assert.equal(demographicMatch("work_address"), null);
  // The browser owns these. Named here so the two halves of SPEC v4's split
  // cannot drift apart without a test noticing.
  assert.deepEqual(DEMOGRAPHIC_FIELDS, [
    "gender",
    "sexual_orientation",
    "race_ethnicity",
    "veteran_status",
    "disability_status",
  ]);
});

test("input too deep to scan is refused rather than accepted unchecked", async () => {
  // "We could not look" is not "there was nothing there" -- the same distinction
  // this register makes between an unchecked company and one that is not hiring.
  let deep = { gender: "hidden this far down" };
  for (let i = 0; i < 12; i += 1) deep = { wrap: deep };

  await assert.rejects(
    () => saveProfile(makeStore(), USER, deep),
    (error) => {
      assert.equal(error.name, "ProfileStoreError");
      assert.equal(error.code, "input_too_deep");
      return true;
    },
  );
});

test("a self-referential input refuses instead of hanging or overflowing the stack", () => {
  const loop = { onsite: "remote" };
  loop.self = loop;
  assert.throws(() => assertNoDemographics(loop), (error) => error.code === "input_too_deep");
});

test("relocation is a boolean, and the string \"false\" is refused rather than coerced", async () => {
  // "false" is truthy. A module that coerced it would record a reader who will
  // not move as one who will, on a form, under their own name. That is the
  // whole reason this field is not a string.
  const store = makeStore();
  for (const bad of ["false", "true", "yes", "no", 0, 1, {}]) {
    const result = await saveProfile(store, USER, { relocation: bad });
    assert.equal(result.ok, false, `accepted relocation: ${JSON.stringify(bad)}`);
    assert.equal(result.errors[0].reason, "not_a_boolean");
  }
  assert.equal((await saveProfile(store, USER, { relocation: false })).ok, true);
  assert.equal((await loadProfile(store, USER)).relocation, false, "false must survive as false");
});

test("an enum field refuses a value outside the enum", async () => {
  const store = makeStore();
  for (const [field, bad] of [
    ["work_authorization", "yes"],
    ["work_authorization", "needs sponsorship"],
    ["onsite", "hybrid-ish"],
    ["onsite", "REMOTE"],
  ]) {
    const result = await saveProfile(store, USER, { [field]: bad });
    assert.equal(result.ok, false, `accepted ${field}: ${bad}`);
    assert.equal(result.errors[0].reason, "not_allowed");
  }
  assert.equal(store.writes, 0);
});

test("earliest_start must be a day that exists on the calendar", async () => {
  const store = makeStore();
  for (const bad of ["2026-02-30", "2026-13-01", "2026-00-10", "next Tuesday", "2026-9-1", "01/09/2026", "2026-09-01T09:00:00Z"]) {
    const result = await saveProfile(store, USER, { earliest_start: bad });
    assert.equal(result.ok, false, `accepted a start date of ${bad}`);
    assert.equal(result.errors[0].reason, "not_a_date", `wrong reason for ${bad}`);
  }
  assert.equal((await saveProfile(store, USER, { earliest_start: "2028-02-29" })).ok, true,
    "a leap day is a real day and must be accepted");
});

test("every field that wants a string refuses a number, an array or an object BY TYPE", async () => {
  // A JSON body is not a form: `salary_expectation: 120000` and
  // `onsite: ["remote"]` are what a hand-written fetch or a half-migrated client
  // actually sends. Each must come back as `not_a_string` rather than throwing
  // on `.trim()`, and rather than being reported as some vaguer failure that
  // sends the caller looking at the wrong thing.
  const store = makeStore();
  const stringFields = [
    "salary_expectation", "heard_about_role", "work_address",
    "onsite", "work_authorization", "earliest_start",
  ];
  for (const field of stringFields) {
    for (const bad of [120000, 0, true, ["remote"], [], { value: "remote" }]) {
      const result = await saveProfile(store, USER, { [field]: bad });
      assert.equal(result.ok, false, `${field} accepted ${JSON.stringify(bad)}`);
      assert.equal(result.errors[0].reason, "not_a_string",
        `${field} refused ${JSON.stringify(bad)} for the wrong reason: ${result.errors[0].reason}`);
    }
  }
  assert.equal(store.writes, 0);
});

test("one overlong entry refuses the whole language list", async () => {
  // The cap is per entry, not just on the array: a single 10,000-character
  // "language" is the same paste accident as forty of them, and truncating it
  // would put a word the user never typed into somebody's form.
  const result = await saveProfile(makeStore(), USER, { languages: ["English", "x".repeat(300)] });
  assert.equal(result.ok, false);
  assert.equal(result.errors[0].reason, "too_long");
});

test("an overlong value is refused, never truncated", async () => {
  // Truncation would store a fact the user did not state, in a field they are
  // about to put their name to. Refusing is the only honest option.
  const store = makeStore();
  const huge = "9".repeat(10_000);
  const result = await saveProfile(store, USER, { salary_expectation: huge });
  assert.equal(result.ok, false);
  assert.equal(result.errors[0].reason, "too_long");
  assert.equal(store.writes, 0);
  assert.equal((await loadProfile(store, USER)).salary_expectation, undefined);
});

test("the prose fields take a sentence and the value fields do not", async () => {
  // Two different caps, and without this nothing tells them apart -- a swap
  // would pass every other test in the file while quietly refusing a legitimate
  // address or accepting a salary field the size of a paragraph.
  const store = makeStore();
  const sentence = "x".repeat(300);
  for (const field of ["heard_about_role", "work_address"]) {
    assert.equal((await saveProfile(store, USER, { [field]: sentence })).ok, true, `${field} refused a sentence`);
    const tooLong = await saveProfile(store, USER, { [field]: "x".repeat(600) });
    assert.equal(tooLong.ok, false, `${field} accepted 600 characters`);
    assert.equal(tooLong.errors[0].reason, "too_long");
  }
  const salary = await saveProfile(store, USER, { salary_expectation: sentence });
  assert.equal(salary.ok, false, "salary_expectation is a value, not a paragraph");
  assert.equal(salary.errors[0].reason, "too_long");
});

test("languages take a list of strings, deduplicated, and refuse anything else", async () => {
  const store = makeStore();
  assert.equal((await saveProfile(store, USER, { languages: "English, Hindi" })).ok, false);
  assert.equal((await saveProfile(store, USER, { languages: ["English", 42] })).ok, false);
  assert.equal(
    (await saveProfile(store, USER, { languages: Array.from({ length: 40 }, (_, i) => `lang${i}`) })).ok,
    false,
  );

  await saveProfile(store, USER, { languages: [" English ", "english", "Hindi", ""] });
  assert.deepEqual((await loadProfile(store, USER)).languages, ["English", "Hindi"]);
});

test("a blank clears the field entirely, so the workspace renders a gap and not an empty answer", async () => {
  // T14.5 tells "we hold this fact" from "we do not" by the key being present.
  // An empty string stored here would render as an answer of "", which is a
  // claim the user never made.
  const store = makeStore();
  await saveProfile(store, USER, FULL);

  for (const blank of ["", "   ", null, undefined]) {
    await saveProfile(store, USER, { salary_expectation: blank });
    const loaded = await loadProfile(store, USER);
    assert.equal("salary_expectation" in loaded, false, `blank ${JSON.stringify(blank)} left a key behind`);
    assert.equal(loaded.onsite, "hybrid", "clearing one field disturbed another");
    await saveProfile(store, USER, { salary_expectation: "£120,000" });
  }

  await saveProfile(store, USER, { languages: [] });
  assert.equal("languages" in (await loadProfile(store, USER)), false);
});

test("a patch merges and leaves the fields it does not mention alone", async () => {
  const store = makeStore();
  await saveProfile(store, USER, FULL);
  await saveProfile(store, USER, { onsite: "remote" });
  assert.deepEqual(await loadProfile(store, USER), { ...FULL, onsite: "remote" });
});

test("the stored row is ours: mutating the caller's object afterwards changes nothing", async () => {
  const store = makeStore();
  const patch = { onsite: "remote", languages: ["English"] };
  await saveProfile(store, USER, patch);

  patch.onsite = "onsite";
  patch.gender = "female";
  assert.deepEqual(await loadProfile(store, USER), { onsite: "remote", languages: ["English"] });
});

test("one user's profile is never another's", async () => {
  const store = makeStore();
  await saveProfile(store, USER, FULL);
  assert.deepEqual(await loadProfile(store, "user_someone_else"), {});

  for (const bad of ["", "   ", null, undefined, 42, {}, "x".repeat(200)]) {
    await assert.rejects(() => loadProfile(store, bad), (error) => error.code === "invalid_user_id",
      `accepted a user id of ${JSON.stringify(bad)}`);
    await assert.rejects(() => saveProfile(store, bad, FULL), (error) => error.code === "invalid_user_id");
  }
});

test("a stored row carrying a demographic field refuses on READ rather than laundering it", async () => {
  // If a row like this ever exists, something upstream has already broken the
  // promise. Serving around it quietly would make the breach invisible for as
  // long as it lasts, so the read fails and someone has to look.
  const store = makeStore({ version: 1, fields: { onsite: "remote", gender: "female" } });
  await assert.rejects(() => loadProfile(store, USER), DemographicFieldError);
  await assert.rejects(() => saveProfile(store, USER, { onsite: "hybrid" }), DemographicFieldError);
});

test("a row written by a newer deploy is refused, and never merged back down", async () => {
  // Workers deploys roll. An older isolate that read a version it does not
  // understand and wrote its own shape back would silently delete whatever the
  // newer one added, and nothing would report it.
  const store = makeStore({ version: 2, fields: { onsite: "remote" } });
  await assert.rejects(() => loadProfile(store, USER), (error) => error.code === "unknown_version");
  await assert.rejects(() => saveProfile(store, USER, { onsite: "hybrid" }), (error) => error.code === "unknown_version");
  assert.equal(store.writes, 0);
  assert.equal(store.rows.get(USER).fields.onsite, "remote");
});

test("a stored row is rebuilt from named fields, so an unrecognised key is not handed onward", async () => {
  const store = makeStore({ version: 1, fields: { onsite: "remote", favourite_colour: "blue" } });
  assert.deepEqual(await loadProfile(store, USER), { onsite: "remote" });
});

test("a corrupt or absent row is refused or empty, never guessed at", async () => {
  assert.deepEqual(await loadProfile(makeStore(), USER), {});
  for (const row of ["a string", [1, 2, 3], 42]) {
    await assert.rejects(() => loadProfile(makeStore(row), USER), (error) => error.code === "corrupt_row");
  }
});

test("a prototype-pollution payload is refused and pollutes nothing", async () => {
  const store = makeStore();
  const payload = JSON.parse('{"__proto__": {"polluted": true}, "onsite": "remote"}');
  const result = await saveProfile(store, USER, payload);
  assert.equal(result.ok, false);
  assert.equal(result.errors[0].field, "__proto__");
  assert.equal({}.polluted, undefined);
  assert.equal(store.writes, 0);
});

test("serializeProfile refuses anything that is not an object", () => {
  for (const bad of ["a string", 42, null, [FULL], true]) {
    const result = serializeProfile(bad);
    assert.equal(result.ok, false, `accepted ${JSON.stringify(bad)}`);
    assert.equal(result.errors[0].reason, "not_an_object");
  }
});

test("every bad field in one patch is reported together", async () => {
  // An interface that can only show one error per round trip makes the user
  // discover their form one failure at a time.
  const result = await saveProfile(makeStore(), USER, {
    relocation: "yes",
    onsite: "wherever",
    earliest_start: "2026-02-30",
  });
  assert.equal(result.ok, false);
  assert.deepEqual(result.errors.map((e) => e.field).sort(), ["earliest_start", "onsite", "relocation"]);
});
