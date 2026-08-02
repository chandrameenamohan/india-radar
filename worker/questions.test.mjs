// T14.4 — proving that "we could not look" never renders as "there is nothing to
// answer". Run: node --test worker/questions.test.mjs
//
// Every failure mode of the fetch gets its own test, because they all converge on
// one output shape and a single missing guard would let one of them return an
// empty question list instead of a silence. The tests therefore assert
// `questions === null` rather than falsiness — an assertion an empty array passes
// is not an assertion at all, which mutation testing showed on `auth.test.mjs`
// earlier today.
//
// NO NETWORK. `fetch` is injected everywhere, and the fixtures are hand-built to
// the shapes `learning-tests/apply_questions_live.py` measured on 2026-08-02. A
// test that reached boards-api would be measuring Greenhouse's uptime, not this
// module, and would go red on a plane.

import { strict as assert } from "node:assert";
import { test } from "node:test";

import {
  PROFILE_MATCHERS,
  REASONS,
  greenhouseQuestionsUrl,
  isStructural,
  matchProfileField,
  postingQuestions,
  questionKind,
  splitByProfile,
} from "./questions.mjs";

// --- fixtures, in Greenhouse's real payload shape ---------------------------

const field = (name, type) => ({ name, type, values: [] });

const question = (label, fields, required = false) => ({ label, required, fields });

/** The fields every board has. Present in every fixture, expected in no output. */
const STRUCTURAL = [
  question("First Name", [field("first_name", "input_text")], true),
  question("Last Name", [field("last_name", "input_text")], true),
  question("Email", [field("email", "input_text")], true),
  question("Phone", [field("phone", "input_text")]),
  question("Resume/CV", [field("resume", "input_file"), field("resume_text", "textarea")], true),
  question("Cover Letter", [field("cover_letter", "input_file"), field("cover_letter_text", "textarea")]),
  question("LinkedIn Profile", [field("question_1", "input_text")]),
  question("Website", [field("question_2", "input_text")]),
];

/** A posting that asks real things: six recurring facts and one genuine essay. */
const ASKS_THINGS = [
  ...STRUCTURAL,
  question("What are your salary expectations?", [field("question_3", "input_text")], true),
  question("What is your earliest start date?", [field("question_4", "input_text")], true),
  question("What address would you be working from?", [field("question_5", "input_text")]),
  question("What languages do you speak?", [field("question_6", "input_text")]),
  question("Will you now or in the future require visa sponsorship?", [
    field("question_7", "multi_value_single_select"),
  ], true),
  question("How did you hear about this job?", [field("question_8", "input_text")]),
  question("Why Anthropic?", [field("question_9", "textarea")], true),
];

/** The full profile, keyed as T14.2 stores it. Every recurring fact held. */
const FULL_PROFILE = {
  salary_expectation: "£95,000",
  earliest_start: "2026-09-01",
  work_address: "Bengaluru, India",
  languages: ["English", "Kannada"],
  work_authorization: false,
  relocation: true,
  onsite: "hybrid, two days",
  heard_about_role: "ROLE·ATLAS",
};

/** A fetch that answers once with this body, and records what it was asked for. */
function stubFetch(body, { status = 200, json } = {}) {
  const calls = [];
  const impl = async (url) => {
    calls.push(url);
    return { status, json: json ?? (async () => body) };
  };
  impl.calls = calls;
  return impl;
}

/** A fetch that must never be called. Any call is the failure. */
const forbiddenFetch = async (url) => {
  throw new Error(`fetched ${url} when it should not have`);
};

const greenhouse = (extra = {}) => ({ ats: "greenhouse", slug: "anthropic", jobId: "4020161008", ...extra });

const labelsOf = (list) => list.map((q) => q.label);

// --- the happy half of the register ----------------------------------------

test("a Greenhouse posting returns its real questions, split by the profile", async () => {
  const fetchImpl = stubFetch({ id: 4020161008, questions: ASKS_THINGS });
  const result = await postingQuestions(greenhouse({ profile: FULL_PROFILE }), { fetch: fetchImpl });

  assert.equal(result.state, "read");
  assert.equal(result.reason, null);
  assert.deepEqual(fetchImpl.calls, [
    "https://boards-api.greenhouse.io/v1/boards/anthropic/jobs/4020161008?questions=true",
  ]);

  // Seven company questions, and not one of the eight structural fields.
  assert.equal(result.questions.length, 7);
  assert.deepEqual(labelsOf(result.structural), labelsOf(STRUCTURAL));

  assert.deepEqual(labelsOf(result.unanswered), ["Why Anthropic?"]);
  assert.deepEqual(
    result.answered.map((q) => q.profileField),
    ["salary_expectation", "earliest_start", "work_address", "languages", "work_authorization", "heard_about_role"],
  );

  // Every filled answer names the field it came from AND carries that value —
  // SPEC v4's honesty invariant is unprovable to a reader without both.
  const salary = result.answered.find((q) => q.profileField === "salary_expectation");
  assert.equal(salary.answer, "£95,000");
  assert.equal(salary.required, true);
  assert.equal(salary.kind, "free_text");
  assert.equal(result.answered.find((q) => q.profileField === "work_authorization").kind, "choice");
});

test("a posting whose only free-text fields are resume and cover letter asks zero questions", async () => {
  // Genuinely zero, and this is the one case where an empty list is the truth.
  // It must still be distinguishable from the unreadable results below.
  const fetchImpl = stubFetch({ questions: STRUCTURAL });
  const result = await postingQuestions(greenhouse({ profile: FULL_PROFILE }), { fetch: fetchImpl });

  assert.equal(result.state, "read");
  assert.deepEqual(result.questions, []);
  assert.deepEqual(result.answered, []);
  assert.deepEqual(result.unanswered, []);
  assert.equal(result.structural.length, 8, "the structural fields are reported, not discarded");
});

test("a question the profile has no fact for is a gap that names nothing it cannot", async () => {
  const fetchImpl = stubFetch({ questions: ASKS_THINGS });
  const bare = { salary_expectation: "   ", languages: [], earliest_start: null, work_authorization: false };
  const result = await postingQuestions(greenhouse({ profile: bare }), { fetch: fetchImpl });

  // A whitespace string, an empty array and a null are absences, not answers.
  assert.deepEqual(
    labelsOf(result.unanswered).sort(),
    [
      "How did you hear about this job?",
      "What address would you be working from?",
      "What are your salary expectations?",
      "What is your earliest start date?",
      "What languages do you speak?",
      "Why Anthropic?",
    ],
  );
  for (const gap of result.unanswered) {
    assert.equal("answer" in gap, false, `${gap.label} carried an answer it has no fact for`);
  }

  // ...but `false` IS a held fact. "Do you need sponsorship? No" is an answer.
  assert.deepEqual(result.answered.map((q) => [q.profileField, q.answer]), [["work_authorization", false]]);

  // A gap whose fact we know the NAME of keeps it, so the workspace can say which
  // profile field to fill; a gap we cannot map to any field says so with null.
  const salaryGap = result.unanswered.find((q) => q.label.startsWith("What are your salary"));
  assert.equal(salaryGap.profileField, "salary_expectation");
  assert.equal(result.unanswered.find((q) => q.label === "Why Anthropic?").profileField, null);
});

// --- the half of the register we cannot see --------------------------------

test("an Ashby role states that we cannot see the form, and never asks a board", async () => {
  const result = await postingQuestions({ ats: "ashby", slug: "ramp", jobId: "abc" }, { fetch: forbiddenFetch });

  assert.equal(result.state, "unreadable");
  assert.equal(result.reason, REASONS.ATS_STATES_NOTHING);
  assert.equal(result.questions, null, "an unreadable form must not present an empty question list");
  assert.equal(result.answered, null);
  assert.equal(result.unanswered, null);
  assert.equal(result.slug, "ramp", "the caller still needs to know which posting it asked about");
});

test("a Lever role is unreadable for the same reason rather than unknown", async () => {
  const result = await postingQuestions({ ats: "lever", slug: "matillion", jobId: "x" }, { fetch: forbiddenFetch });
  assert.equal(result.reason, REASONS.ATS_STATES_NOTHING);
  assert.equal(result.questions, null);
});

test("an ATS we do not recognise is unknown, not assumed to answer like Greenhouse", async () => {
  for (const ats of ["workday", "", undefined, null, "Greenhouse"]) {
    const result = await postingQuestions({ ats, slug: "s", jobId: "1" }, { fetch: forbiddenFetch });
    assert.equal(result.reason, REASONS.UNKNOWN_ATS, `treated ${JSON.stringify(ats)} as known`);
    assert.equal(result.questions, null);
  }
});

test("a fetch that throws is unreadable, never zero questions", async () => {
  const result = await postingQuestions(greenhouse(), {
    fetch: async () => {
      throw new TypeError("network error");
    },
  });
  assert.equal(result.state, "unreadable");
  assert.equal(result.reason, REASONS.FETCH_FAILED);
  assert.equal(result.questions, null);
});

test("a board error is unreadable and carries the status", async () => {
  for (const status of [500, 404, 403, 429, 302]) {
    const result = await postingQuestions(greenhouse(), { fetch: stubFetch({ questions: ASKS_THINGS }, { status }) });
    assert.equal(result.state, "unreadable", `status ${status} was treated as readable`);
    assert.equal(result.reason, REASONS.BOARD_ERROR);
    assert.equal(result.status, status);
    assert.equal(result.questions, null);
  }
});

test("a response with no usable status fails closed", async () => {
  // A transport that answers with something we cannot recognise as a success is
  // not evidence that the form is empty.
  for (const response of [{}, null, { status: "200" }, { ok: true }]) {
    const result = await postingQuestions(greenhouse(), { fetch: async () => response });
    assert.equal(result.state, "unreadable", `${JSON.stringify(response)} was treated as a success`);
    assert.equal(result.questions, null);
  }
});

test("a 200 that is not JSON is unreadable", async () => {
  const fetchImpl = stubFetch(null, {
    json: async () => {
      throw new SyntaxError("Unexpected token < in JSON at position 0");
    },
  });
  const result = await postingQuestions(greenhouse(), { fetch: fetchImpl });
  assert.equal(result.reason, REASONS.UNREADABLE_BODY);
  assert.equal(result.questions, null);
});

test("a 200 with no questions key is UNKNOWN, and emphatically not zero questions", async () => {
  // The measured case: `learning-tests/apply_questions_live.py` prints exactly
  // this note for boards that answer without the array. Reporting it as an empty
  // form would tell a reader the company asks nothing, which we do not know.
  const payload = { id: 42, title: "Staff Engineer", location: { name: "London" } };
  const result = await postingQuestions(greenhouse(), { fetch: stubFetch(payload) });

  assert.equal(result.state, "unreadable");
  assert.equal(result.reason, REASONS.NO_QUESTIONS_KEY);
  assert.equal(result.questions, null);
  assert.notDeepEqual(result.questions, [], "an empty list here would claim the form asks nothing");
  assert.deepEqual(result.keys, ["id", "location", "title"], "what we did get, for whoever debugs this");
});

test("a questions key that is not an array is unknown too", async () => {
  for (const questions of [null, "none", {}, 0, undefined]) {
    const result = await postingQuestions(greenhouse(), { fetch: stubFetch({ questions }) });
    assert.equal(result.reason, REASONS.NO_QUESTIONS_KEY, `accepted questions: ${JSON.stringify(questions)}`);
    assert.equal(result.questions, null);
  }
});

test("an incomplete reference is refused without pretending to have looked", async () => {
  for (const bad of [{ slug: "", jobId: "1" }, { slug: "a", jobId: "" }, { slug: null, jobId: null }, {}]) {
    const result = await postingQuestions({ ats: "greenhouse", ...bad }, { fetch: forbiddenFetch });
    assert.equal(result.reason, REASONS.INCOMPLETE_REFERENCE, `fetched on ${JSON.stringify(bad)}`);
    assert.equal(result.questions, null);
  }
  // A numeric job id is a complete reference — Greenhouse's own payload uses one.
  const ok = await postingQuestions({ ats: "greenhouse", slug: "anthropic", jobId: 4020161008 }, {
    fetch: stubFetch({ questions: [] }),
  });
  assert.equal(ok.state, "read");
});

test("a missing transport throws rather than reporting an honest silence", async () => {
  // A broken deploy must not be indistinguishable from Ashby.
  await assert.rejects(() => postingQuestions(greenhouse(), {}), TypeError);
  await assert.rejects(() => postingQuestions(greenhouse()), TypeError);
  await assert.rejects(() => postingQuestions(greenhouse(), { fetch: "nope" }), TypeError);
});

// --- the pure parts, attacked directly -------------------------------------

test("the URL encodes both segments so a slug cannot reshape the request", () => {
  assert.equal(
    greenhouseQuestionsUrl("../../admin", "1?x=2"),
    "https://boards-api.greenhouse.io/v1/boards/..%2F..%2Fadmin/jobs/1%3Fx%3D2?questions=true",
  );
  const url = new URL(greenhouseQuestionsUrl("a/b", "c&d"));
  assert.equal(url.pathname, "/v1/boards/a%2Fb/jobs/c%26d");
  assert.deepEqual([...url.searchParams.keys()], ["questions"]);
});

test("structural fields are recognised by Greenhouse's field name, whatever the label says", () => {
  assert.equal(isStructural(question("Attach your CV here", [field("resume", "input_file")])), true);
  assert.equal(isStructural(question("Tell us who you are", [field("first_name", "input_text")])), true);
  assert.equal(isStructural(question("Anything else?", [field("question_9", "textarea")])), false);
});

test("a company question containing a structural word survives", () => {
  // The substring matching a throwaway probe can get away with would delete these
  // from a form we are telling the user is complete.
  const survivors = [
    "Which office location would you prefer?",
    "What is the name of your current employer?",
    "What location would you like to be considered for?",
    "Describe a website you are proud of",
    "How do you feel about a phone-first support rota?",
    "Tell us the name you would give this feature",
  ];
  for (const label of survivors) {
    assert.equal(isStructural(question(label, [field("q", "textarea")])), false, `dropped: ${label}`);
  }
});

test("name variants and a bare Location are structural, and the office question still is not", () => {
  // BOTH DIRECTIONS IN ONE TEST, because they are one decision and a fix to
  // either can break the other. Measured over the same 52 live Greenhouse
  // postings on 2026-08-03: these labels were being handed to the reader as
  // questions their company chose to ask — "Preferred First Name" 22 times, the
  // legal/preferred variants 9 more, a bare "Location" 3. They arrive as ordinary
  // `question_NNN` custom fields, so only the label can give them away.
  const boilerplate = [
    "Preferred First Name",
    "What is your legal first name?",
    "What is your legal last name?",
    "What is your preferred first name?",
    "Preferred Name",
    "Legal Name",
    "Surname",
    "Location",
  ];
  for (const label of boilerplate) {
    assert.equal(isStructural(question(label, [field("question_12", "input_text")])), true, `shown as a question: ${label}`);
  }

  // ...and the case that made exact matching necessary in the first place must
  // survive the widening. A rule that catches the eight above by eating this one
  // has traded a visible annoyance for a silently incomplete form.
  assert.equal(isStructural(question("Which office location would you prefer?", [field("q", "textarea")])), false);
  assert.equal(isStructural(question("What is the name of your current employer?", [field("q", "input_text")])), false);
});

test("a boilerplate field re-asked as a custom question is still structural", () => {
  // Boards do this: the same field arrives with a `question_NNN` name, so the
  // stable identifier is not there to give it away and only the label can. This
  // test exists because MUTATION TESTING said the exact-label set was untested —
  // every other fixture that reaches it is caught one line earlier by its
  // Greenhouse field name, so deleting the set left the whole file green.
  for (const label of ["Email Address", "Phone Number", "Full Name", "Resume/CV", "Cover letter"]) {
    assert.equal(isStructural(question(label, [field("question_11", "input_text")])), true, `kept: ${label}`);
  }
});

test("link fields are structural however they are dressed up", () => {
  for (const label of ["LinkedIn Profile URL", "linkedin", "Website / Portfolio", "GitHub profile", "Portfolio"]) {
    assert.equal(isStructural(question(label, [field("q", "input_text")])), true, `kept: ${label}`);
  }
});

test("questionKind reports what answering takes, and refuses to guess", () => {
  assert.equal(questionKind(question("x", [field("q", "textarea")])), "free_text");
  assert.equal(questionKind(question("x", [field("q", "multi_value_single_select")])), "choice");
  assert.equal(questionKind(question("x", [field("q", "input_file")])), "file");
  // A file AND a textarea is free text: the harder half describes the work.
  assert.equal(questionKind(question("x", [field("a", "input_file"), field("b", "textarea")])), "free_text");
  // A type Greenhouse adds tomorrow must not render as a text box.
  assert.equal(questionKind(question("x", [field("q", "input_signature")])), "unknown");
  assert.equal(questionKind(question("x", [])), "unknown");
  assert.equal(questionKind(undefined), "unknown");
});

test("the eight recurring labels the measurement found each map to a profile field", () => {
  // Taken from the FINDINGS header of learning-tests/apply_questions_live.py.
  const measured = {
    "What are your salary expectations?": "salary_expectation",
    "Desired compensation": "salary_expectation",
    "What is your earliest start date?": "earliest_start",
    "Notice period": "earliest_start",
    "What address would you be working from?": "work_address",
    "Where are you currently based?": "work_address",
    "What languages do you speak?": "languages",
    "Do you now or in the future require sponsorship?": "work_authorization",
    "Are you legally authorized to work in the UK?": "work_authorization",
    "Are you willing to relocate?": "relocation",
    "Are you able to work on-site three days a week?": "onsite",
    "How did you hear about this job?": "heard_about_role",
  };
  for (const [label, expected] of Object.entries(measured)) {
    assert.equal(matchProfileField(label), expected, `unmatched: ${label}`);
  }
});

test("matching is narrow: a question we cannot map becomes a gap rather than a wrong fact", () => {
  // Filling a form with the wrong fact under the user's own name is the failure
  // the honesty invariant forbids, so these must all come back null.
  const prose = [
    "Why Anthropic?",
    "How are you using AI today in your current role?",
    "Based on your experience, what would you change about our product?",
    "Tell us about a time you disagreed with a manager",
    "",
    "   ",
  ];
  for (const label of prose) {
    assert.equal(matchProfileField(label), null, `wrongly matched: ${label}`);
  }
  assert.equal(matchProfileField(undefined), null);
});

test("every matcher field is distinct, so an answer names exactly one profile field", () => {
  const fields = PROFILE_MATCHERS.map((m) => m.field);
  assert.equal(new Set(fields).size, fields.length);
});

test("the matcher table names exactly the eight fields profile.mjs stores", () => {
  // `profile.mjs` owns this vocabulary because it is the thing that holds the
  // value. A key that drifts from it renders a gap for a fact the user has
  // already given us, and nothing else in either module would notice.
  assert.deepEqual(PROFILE_MATCHERS.map((m) => m.field).sort(), [
    "earliest_start",
    "heard_about_role",
    "languages",
    "onsite",
    "relocation",
    "salary_expectation",
    "work_address",
    "work_authorization",
  ]);
});

test("pronouns and interview accommodations stay unmatched, and that is not an oversight", () => {
  // ARTICLE 9 SPECIAL-CATEGORY DATA. Pronouns imply gender identity and
  // accommodations reveal disability status, so `profile.mjs` refuses to store
  // either and they live in the reader's browser. A matcher here would be this
  // module asking the server for a fact the server must never hold — so these
  // questions are gaps by design, and this test exists so that the missing
  // matchers cannot be read as an omission and "fixed".
  const article9 = [
    "What are your pronouns?",
    "Pronouns",
    "Preferred pronouns",
    "Do you require any accommodations for the interview process?",
    "Interview accommodations",
    "Please let us know if you need any accommodations",
  ];
  for (const label of article9) {
    assert.equal(matchProfileField(label), null, `would send to the server: ${label}`);
  }

  // ...and end to end: asked by a posting, they come back as gaps naming no
  // profile field, even with every storable fact held.
  const asked = [
    question("What are your pronouns?", [field("question_20", "input_text")]),
    question("Do you require any accommodations for the interview process?", [field("question_21", "textarea")]),
  ];
  const { answered, unanswered } = splitByProfile(asked, FULL_PROFILE);
  assert.deepEqual(answered, []);
  assert.deepEqual(unanswered.map((q) => q.profileField), [null, null]);
});

test("splitByProfile survives a payload that is not the shape we expect", () => {
  for (const junk of [null, undefined, "questions", 7, {}]) {
    assert.deepEqual(splitByProfile(junk, FULL_PROFILE), {
      questions: [],
      answered: [],
      unanswered: [],
      structural: [],
    });
  }
  // A question object missing everything is still a question, not a crash.
  const odd = splitByProfile([{}, { label: 42 }, { label: "Salary?", fields: null }], {});
  assert.equal(odd.questions.length, 3);
  assert.equal(odd.questions[0].label, "");
  assert.equal(odd.unanswered.at(-1).profileField, "salary_expectation");
});
