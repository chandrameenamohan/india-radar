// T14.4 — what a posting actually asks, and the difference between a form with
// no questions and a form we could not look at.
//
// Measured 2026-08-02 (`learning-tests/apply_questions_live.py`): Greenhouse
// states a job's application questions on request; **Ashby states nothing**, and
// 401 of 880 resolved slugs are Ashby. So this module covers half the register
// with real questions and the other half with an honest silence, and the whole
// point of the file is that a caller can always tell which one it got.
//
// THE INVARIANT, AND IT IS THE REASON THIS MODULE EXISTS. "We could not look" and
// "this form asks nothing" are different facts and are never collapsed into an
// empty list. A workspace that rendered an Ashby role as a resume field and
// nothing else would be claiming the form is short when the truth is we could not
// look — the same error as an unchecked company rendering as "not hiring". So the
// unreadable result carries `questions: null`, never `[]`, and every branch that
// gives up goes through one constructor to make that impossible to forget.
//
// NO DEPENDENCIES, and `fetch` is a parameter rather than a global. Both for the
// same reason as `auth.mjs`: the module runs unchanged in the Worker and under
// `node --test` on a machine where the Workers runtime will not start, and the
// tests cannot accidentally reach the real boards-api.
//
// NO MODEL RUNS HERE. This file sorts questions against facts the user already
// stated; it never writes a sentence. SPEC v4 "The drafting slot" records why.

/** The posting's form was read. `questions` is then trustworthy, including when empty. */
export const READ = "read";

/** The form was not read. `questions` is null and `reason` says what stopped us. */
export const UNREADABLE = "unreadable";

/** Why we could not look. Distinct values because they call for distinct wording. */
export const REASONS = {
  /** Greenhouse-only capability. Ashby and Lever publish no questions at all. */
  ATS_STATES_NOTHING: "ats-does-not-state-questions",
  /** An ATS this register does not know — never assume a board answers like Greenhouse. */
  UNKNOWN_ATS: "unknown-ats",
  /** No slug or no job id. We did not ask, so we cannot claim to have looked. */
  INCOMPLETE_REFERENCE: "incomplete-reference",
  /** The injected fetch threw: DNS, TLS, abort, offline. */
  FETCH_FAILED: "fetch-failed",
  /** The board answered, but not with a success status. `status` carries which. */
  BOARD_ERROR: "board-error",
  /** 200 with a body that is not JSON. */
  UNREADABLE_BODY: "unreadable-body",
  /** 200, valid JSON, no `questions` array. UNKNOWN, and emphatically not zero. */
  NO_QUESTIONS_KEY: "no-questions-key",
};

/**
 * Boards we have measured to publish no questions, so we can say so specifically.
 *
 * Lever is out of scope for T14.4 rather than measured silent, but the fact a
 * caller needs is the same one — we cannot see this company's form — and telling
 * a reader "unknown ATS" about a board we plainly recognise would be a worse lie
 * than telling them we cannot read it.
 */
const SILENT_ATS = new Set(["ashby", "lever"]);

/** The one board that answers. Documented, and re-measured 2026-08-02. */
const GREENHOUSE = "greenhouse";

/**
 * The endpoint, with both path segments encoded.
 *
 * Encoding is a control, not tidiness: a slug arrives from `companies.json` and a
 * job id from a URL a reader pasted, and neither may be able to add a path
 * segment or a query parameter to a request we make on their behalf.
 */
export function greenhouseQuestionsUrl(slug, jobId) {
  const board = encodeURIComponent(slug);
  const job = encodeURIComponent(jobId);
  return `https://boards-api.greenhouse.io/v1/boards/${board}/jobs/${job}?questions=true`;
}

/** Greenhouse field types that need a person to write something. */
const FREE_TEXT_TYPES = new Set(["textarea", "input_text"]);

/** ...to pick from a published list. */
const CHOICE_TYPES = new Set(["multi_value_single_select", "multi_value_multi_select"]);

/** ...to attach a document. */
const FILE_TYPES = new Set(["input_file"]);

/**
 * Greenhouse's own names for the fields every board has. Matching on these first
 * is deliberate: they are stable identifiers, where a label is prose a company
 * can rewrite ("Attach your CV here" is still `resume`).
 */
const STRUCTURAL_FIELD_NAMES = new Set([
  "first_name",
  "last_name",
  "name",
  "email",
  "phone",
  "resume",
  "resume_text",
  "cover_letter",
  "cover_letter_text",
]);

/**
 * Labels for the same fields when they arrive as ordinary custom questions,
 * which is how LinkedIn and website usually do.
 *
 * MATCHED EXACTLY, never as substrings. The learning test's throwaway probe used
 * substrings and would have swallowed "Which office location would you prefer?"
 * on the word "location" — a question the company chose to ask, silently deleted
 * from a form we are telling the user is complete. Exact matching fails the other
 * way, showing a boilerplate field as a question, which is visible and harmless.
 *
 * A bare "Location" is Greenhouse's own field and belongs here; anything with
 * more words in it is the company asking something and belongs to the reader.
 */
const STRUCTURAL_LABELS = new Set([
  "first name",
  "last name",
  "full name",
  "name",
  "email",
  "email address",
  "phone",
  "phone number",
  "mobile number",
  "telephone",
  "location",
  "resume",
  "resume cv",
  "cv",
  "cv resume",
  "cover letter",
  "cover letter or note",
]);

/**
 * The name field in all the ways boards phrase it.
 *
 * VALIDATED AGAINST THE LIVE 52 POSTINGS, 2026-08-03, and it is why exact
 * matching alone was not enough: "Preferred First Name" (22 occurrences), "What
 * is your legal first name?", "What is your preferred first name?" and "What is
 * your legal last name?" — 34 occurrences in all — were being handed to the
 * reader as questions their company chose to ask, sitting next to "Why
 * Anthropic?". They arrive as ordinary `question_NNN` custom fields, so no stable
 * field name gives them away.
 *
 * ANCHORED, and ending in the word itself, which is the whole reason it is safe:
 * "What is the name of your current employer?" does not end in "name" and stays a
 * company question. A substring rule on "name" would have eaten it.
 */
const NAME_LABEL =
  /^(?:what(?:'s| is) )?(?:your )?(?:legal |preferred |chosen )*(?:first |last |full |middle |maiden |family |given |sur)?names?$/;

/**
 * Link fields, matched on their FIRST word.
 *
 * These four are nouns no genuine question opens with — a company asking about
 * your work asks "Tell us about...", not "GitHub, and why?" — so a first-word
 * rule catches the long tail ("LinkedIn Profile URL", "Website / Portfolio")
 * without the substring hazard the exact set above exists to avoid. `github` and
 * `portfolio` are here because the learning test's STRUCTURAL list has them and
 * they are the same kind of thing, even though SPEC's sentence names only eight.
 */
const STRUCTURAL_LINK_WORDS = new Set(["linkedin", "website", "portfolio", "github"]);

/**
 * A label reduced to comparable words: lowercase, no decoration, single spaces.
 * "Resume/CV*" and "Cover Letter (optional)" are the same field as their plain
 * forms and must normalise onto them.
 */
function normalize(label) {
  return String(label ?? "")
    .toLowerCase()
    .replace(/\((?:optional|required)\)/g, " ")
    .replace(/[*?:.,/\\|()[\]{}]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * Is this one of the fields every board asks, rather than a question this company
 * chose to ask?
 *
 * Presenting "Email" as one of a company's questions would misstate what the
 * company wants to know, and it would drown the two questions that matter in
 * eight that do not. T14.4's checks name this one specifically.
 */
export function isStructural(question) {
  const fields = Array.isArray(question?.fields) ? question.fields : [];
  if (fields.some((field) => STRUCTURAL_FIELD_NAMES.has(field?.name))) return true;

  const label = normalize(question?.label);
  if (STRUCTURAL_LABELS.has(label)) return true;
  if (NAME_LABEL.test(label)) return true;
  return STRUCTURAL_LINK_WORDS.has(label.split(" ")[0]);
}

/**
 * What answering this question takes: `free_text`, `choice`, `file`, `unknown`.
 *
 * Free text wins when a question offers several field types, because Greenhouse's
 * resume question is a file AND a textarea, and the harder of the two is the one
 * that describes the work. `unknown` is returned rather than guessed at — a field
 * type Greenhouse adds tomorrow must not silently render as a text box.
 */
export function questionKind(question) {
  const types = (Array.isArray(question?.fields) ? question.fields : []).map((f) => f?.type);
  if (types.some((type) => FREE_TEXT_TYPES.has(type))) return "free_text";
  if (types.some((type) => CHOICE_TYPES.has(type))) return "choice";
  if (types.some((type) => FILE_TYPES.has(type))) return "file";
  return "unknown";
}

/**
 * The profile fields measured to recur, and the labels that ask for them.
 *
 * The finding that moved this feature is that the recurring questions are FACTS —
 * salary, start date, work address, languages, work authorisation, how you heard
 * — and genuine essays are the minority. That claim held under every filter tried
 * (the share of postings asking one did not, and is withdrawn: see the correction
 * in `learning-tests/apply_questions_live.py`). So the profile carries this
 * feature and no model is needed to do it.
 *
 * FIELD KEYS ARE `profile.mjs`'S, NOT THIS FILE'S. The storage module defines the
 * vocabulary because it is the thing that has to hold the value; four of these
 * were renamed on 2026-08-03 to match it. This table is exported so there is one
 * place the two agree, rather than a mapping that drifts until the workspace
 * renders a gap for a fact the user already gave us.
 *
 * NOT HERE, DELIBERATELY: pronouns and interview accommodations. Both recur in
 * the measured labels, and both are Article 9 special-category data — pronouns
 * imply gender identity, accommodations reveal disability status — so
 * `profile.mjs` refuses them and they live in the reader's browser. A matcher for
 * either would be this module asking the server for a fact the server must never
 * hold. They must come back as GAPS, and a test pins that so it cannot be
 * "fixed" later by someone who reads the omission as an oversight.
 *
 * Patterns run against a normalised label, first match wins, and they are
 * deliberately narrow: a wrong match fills a form with the wrong fact under the
 * user's own name, which is the exact failure the honesty invariant forbids. A
 * question we fail to match becomes a gap, and a gap is a correct output.
 */
export const PROFILE_MATCHERS = [
  {
    field: "salary_expectation",
    patterns: [/salary/, /compensation expectation/, /expected (?:pay|compensation)/, /desired (?:pay|compensation)/],
  },
  {
    field: "earliest_start",
    patterns: [/start date/, /earliest (?:start|availability|available)/, /when (?:could|can|would) you (?:be able to )?start/, /notice period/],
  },
  {
    field: "work_authorization",
    patterns: [/sponsorship/, /\bvisa\b/, /work authorization/, /work authorisation/, /right to work/, /legally (?:authorized|authorised|entitled)/],
  },
  {
    field: "relocation",
    patterns: [/relocat/],
  },
  {
    field: "onsite",
    patterns: [/on-?site/, /in[- ]office/, /\bhybrid\b/, /commut/],
  },
  {
    field: "work_address",
    patterns: [/work(?:ing)? from/, /work(?:ing)? (?:location|address)/, /where are you (?:currently )?(?:based|located)/, /city and (?:state|country)/],
  },
  {
    field: "languages",
    patterns: [/languages? (?:do )?you speak/, /what languages/, /language proficiency/, /spoken languages/],
  },
  {
    field: "heard_about_role",
    patterns: [/how did you hear/, /how (?:did|were) you (?:find|referred)/, /where did you (?:hear|find)/],
  },
];

/** The profile field a label asks for, or null when we hold no fact for it. */
export function matchProfileField(label) {
  const text = normalize(label);
  for (const { field, patterns } of PROFILE_MATCHERS) {
    if (patterns.some((pattern) => pattern.test(text))) return field;
  }
  return null;
}

/**
 * Do we actually hold this fact?
 *
 * An empty string is NOT an answer, and this is the honesty invariant in one
 * function: a profile row that exists but was never filled must render as a gap
 * rather than as a blank answer the user signs their name to. `false` and `0` are
 * held facts — "do you require sponsorship? no" is an answer, not an absence.
 */
function held(value) {
  if (value === undefined || value === null) return false;
  if (typeof value === "string") return value.trim() !== "";
  if (Array.isArray(value)) return value.length > 0;
  return true;
}

/** The caller-facing shape of one question. The raw board payload never escapes. */
function describe(question) {
  return {
    label: typeof question?.label === "string" ? question.label : "",
    required: question?.required === true,
    kind: questionKind(question),
  };
}

/**
 * Split a board's questions into what the profile answers and what it does not.
 *
 * Pure, and separate from the fetch so the sorting can be tested without a
 * transport. `structural` is returned rather than discarded so a caller can prove
 * nothing was hidden — the fields are removed from the company's questions, not
 * from the record of what the form contains.
 *
 * @param {object[]} rawQuestions  a Greenhouse `questions` array
 * @param {object} profile         the user's stored operational facts, keyed as PROFILE_MATCHERS
 */
export function splitByProfile(rawQuestions, profile = {}) {
  const questions = [];
  const structural = [];
  for (const raw of Array.isArray(rawQuestions) ? rawQuestions : []) {
    (isStructural(raw) ? structural : questions).push(describe(raw));
  }

  const answered = [];
  const unanswered = [];
  for (const question of questions) {
    const profileField = matchProfileField(question.label);
    const value = profileField ? profile?.[profileField] : undefined;
    if (profileField && held(value)) {
      answered.push({ ...question, profileField, answer: value });
    } else {
      // The matched-but-empty case keeps its field name: the workspace can then
      // say WHICH fact is missing instead of only that something is.
      unanswered.push({ ...question, profileField: profileField ?? null });
    }
  }

  return { questions, answered, unanswered, structural };
}

/**
 * The one constructor for "we could not look".
 *
 * `detail` is spread FIRST so that no caller can ever set `questions` to
 * something other than null. That ordering is the invariant made structural.
 */
function cannotSee(reason, detail = {}) {
  return {
    ...detail,
    state: UNREADABLE,
    reason,
    questions: null,
    answered: null,
    unanswered: null,
    structural: null,
  };
}

/** A usable path segment, or null. Job ids arrive as numbers about as often as strings. */
function segment(value) {
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  return typeof value === "string" && value.trim() !== "" ? value.trim() : null;
}

/**
 * A posting's application questions, split by what the profile can answer.
 *
 * @param {object} reference
 * @param {"greenhouse"|"ashby"|"lever"} reference.ats
 * @param {string} reference.slug          the board slug
 * @param {string|number} reference.jobId  the posting's id on that board
 * @param {object} [reference.profile]     the user's stored operational facts
 * @param {object} transport
 * @param {Function} transport.fetch       a fetch-like function; INJECTED, never global
 * @returns {Promise<object>} `state: "read"` with questions, or `state: "unreadable"`
 *   with a reason and `questions: null`. A caller distinguishes a form with no
 *   questions from a form we could not read by the state, never by the length.
 */
export async function postingQuestions({ ats, slug, jobId, profile = {} }, { fetch: fetchImpl } = {}) {
  // THROWS rather than returning unreadable, and that is deliberate. A missing
  // transport is a wiring bug, and reporting it as "we could not see the form"
  // would dress a broken deploy up as an honest silence — which is the one
  // failure this module exists to prevent. It must be loud.
  if (typeof fetchImpl !== "function") {
    throw new TypeError("postingQuestions requires an injected fetch");
  }

  const reference = { ats: ats ?? null, slug: slug ?? null, jobId: jobId ?? null };

  // Checked BEFORE any request. Asking boards-api about an Ashby slug would be a
  // fetch we cannot learn anything from, and a 404 from it would be reported as a
  // board error rather than as the measured fact that Ashby states nothing.
  if (ats !== GREENHOUSE) {
    return cannotSee(SILENT_ATS.has(ats) ? REASONS.ATS_STATES_NOTHING : REASONS.UNKNOWN_ATS, reference);
  }

  const board = segment(slug);
  const job = segment(jobId);
  if (!board || !job) return cannotSee(REASONS.INCOMPLETE_REFERENCE, reference);

  let response;
  try {
    response = await fetchImpl(greenhouseQuestionsUrl(board, job));
  } catch (error) {
    return cannotSee(REASONS.FETCH_FAILED, { ...reference, detail: String(error?.message ?? error) });
  }

  // Read as a NUMBER rather than trusting `response.ok`, so that anything which
  // is not recognisably a successful response — including a stub that forgot to
  // say — fails closed into unreadable instead of into "this form asks nothing".
  const status = Number(response?.status);
  if (!(status >= 200 && status < 300)) {
    return cannotSee(REASONS.BOARD_ERROR, { ...reference, status: Number.isFinite(status) ? status : null });
  }

  let payload;
  try {
    payload = await response.json();
  } catch (error) {
    return cannotSee(REASONS.UNREADABLE_BODY, { ...reference, detail: String(error?.message ?? error) });
  }

  // THE GUARD THIS TASK IS ABOUT. A board that answers 200 with no `questions`
  // array has told us nothing about its form; treating that as zero questions
  // would put a confident empty list in front of a reader. The keys we did get
  // ride along, because the next person to debug this will want them.
  if (!Array.isArray(payload?.questions)) {
    const keys = payload && typeof payload === "object" ? Object.keys(payload).sort() : [];
    return cannotSee(REASONS.NO_QUESTIONS_KEY, { ...reference, keys });
  }

  return { ...reference, state: READ, reason: null, ...splitByProfile(payload.questions, profile) };
}
