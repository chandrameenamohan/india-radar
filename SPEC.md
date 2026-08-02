# SPEC — ROLE·ATLAS

*(Shipped as INDIA·RADAR through v1, when the radar was one country wide. T8.6
renamed it for the fifteen-country reality — see the Expansion section.)*

## Thesis

**Funded software companies that are hiring in India right now, proven by their own job board — not by a claim.**

## What it is

A static site: one `data/companies.json`, vanilla JS, no backend, no database,
published on GitHub Pages. Every company on it is (a) a software company that has
raised roughly Series A or more, and (b) showing at least one open India role on
its own ATS at build time. HQ may be anywhere — US, UK, Canada, Europe, Asia,
Australia.

The build is **stateless**. Each run recomputes the whole site from live sources.
There is no history store, no incremental state, no migrations. A company that
stops hiring in India simply stops appearing.

## Architecture in one line

```
funding corpus  ->  resolve ATS slug  ->  probe board  ->  keep India roles
                ->  enrich (roles/city/salary/MCA)  ->  emit companies.json
```

Enrichment hangs off the job-posting spine. Any enrichment may fail, degrade, or
arrive late without taking the site down.

---

## Features

Each carries an **observable acceptance**: what a user or caller can see when it works.

### 1. Funding corpus assembly
Scrape four free sources into a deduplicated company list with name, funding
amount, date, round letter (when stated), and source URL.
Sources: FinSMEs, YC company directory, SEC Form D (EDGAR), TechCrunch/Forbes/CBI lists.

**Acceptance:** `corpus.json` exists with ≥1,000 distinct companies; every record
carries a source URL that resolves; running the build twice produces the same
company set (dedup is deterministic, not order-dependent).

### 2. "Series A or more" filter — amount-based proxy
Qualify a company when a stated round letter is A or later, **or**, when no
letter is given, when a disclosed round is ≥ $5M. Record which rule fired.

**Acceptance:** every corpus record has `qualified_by` set to exactly one of
`letter` or `amount`; a record with neither a letter nor an amount is excluded and
counted in the build report, never silently dropped.

### 3. ATS slug resolution
For each company, find its job-board slug by (a) regexing its careers page for
board URLs, then (b) guessing the slug from the company name and probing
Greenhouse and Ashby directly, then (c) consulting a hand-maintained override file.

A guess is only kept if the board states whose it is. Greenhouse states a name
and 404s a slug that is not a board, so the name settles it. Ashby answers 200
for every slug ever typed and **25% of the boards its titles matched were a
different company with the same one-word name** (T12.1), so an Ashby guess must
also agree with the company's own address. Lever is not guessed at all: a wrong
slug returns 200 with an empty array, so there is nothing to verify.

**Acceptance:** `slugs.json` maps company → `{ats, slug, method}` where method is
one of `careers-page | guess | override`; unresolved companies land in
`unresolved.json` with a reason, and the build report prints the resolution rate.
Measured baseline to beat: ~50% from (a) and (b) alone.

### 4. Board probe
Fetch open roles per company from Greenhouse, Lever, or Ashby.

**Acceptance:** for a known-good slug the probe returns the same role count the
provider's own public board shows. For Greenhouse specifically, the returned count
equals `meta.total` in the same response.

### 5. India role filter
Keep a company when ≥1 open role matches India by city-name list. Handles
`Bengaluru, India`, `Remote - India`, `India - Remote`, `IN-Pune`, multi-city
strings like `Bengaluru, India; Mumbai, India`, and Ashby's `secondaryLocations`.

**Acceptance:** a fixture file of real location strings (including the known
false-positive traps `In-Office` and `Hybrid; In-Office`) classifies with zero
false positives and zero false negatives.

### 6. Enrichment — India roles and apply links
Attach each matching role's title and direct apply URL.

**Acceptance:** every listed company has ≥1 role with a URL that returns HTTP 200
and lands on that company's posting.

### 7. Enrichment — city and remote flag
Parse India cities and remote/hybrid/onsite from the same location strings.

**Acceptance:** each company shows ≥1 India city or is explicitly flagged remote;
no company displays an empty location.

### 8. Enrichment — salary benchmark
Attach an AmbitionBox-style India CTC figure with its source URL and observation date.

**Acceptance:** where present, the figure renders with its date and a working
source link; where absent, the row renders cleanly without it. Absence is never
an error.

### 9. Enrichment — MCA verification badge
Attach CIN, incorporation year, registered city and entity status from the
**RoC-wise Company Master Data** dataset
(`4dbe5667-7b6b-41d7-82af-211562424d9a`).

**Acceptance:** a matched company displays a CIN that resolves on the MCA portal;
match confidence is recorded and anything below threshold is held for manual review
rather than published. Unmatched companies render normally without a badge.

> **UNBLOCKED** (2026-07-28). Registered key obtained; all three unknowns resolved.
>
> - Page size **10,000** → the full 3,674,314-row table is **367 calls**.
> - The foreign-subsidiary filter value is
>   `CompanySubCategory = "subsidiary of company incorporated outside India"`
>   → **24,102 companies**. (My earlier guess "Subsidiary of Foreign Company"
>   does not exist, which is why it returned 0.)
> - `CompanyStateCode` is optional; a flat scan works.
>
> **Never use the state-wise datasets — all 37 are frozen at 31 March 2021.**
> **Never use `CompanyIndian/Foreign Company`** — ~670k rows contain the literal
> string `91`, a phone country code leaked into a country field.
>
> The API 502s under sustained load (~20 calls in, everything goes dark including
> requests that worked seconds earlier). So the MCA pull is a **cached snapshot
> refreshed rarely**, with backoff and retries, never an inline dependency of the
> nightly build. A dead MCA upstream must degrade to "no badge", never fail the run.

### 10. The site
Search, sort and filter over the JSON; row click reveals roles, links and badges.
Filters: hiring city, remote-only, funding bracket, last-round recency, MCA-verified.

**Acceptance:** loads with zero console errors and zero failed network requests;
filtering to a city yields only companies with a role in that city; the snapshot
date is visible on the page.

### 11. Tiered refresh
GitHub Actions: **Greenhouse nightly** (0.35s/company), **Ashby weekly**
(~151s/company fixed, concurrency ~12 with backoff and retries).

**Acceptance:** both workflows complete inside the 6h job cap; a run that fails
leaves the previously published JSON intact rather than committing a truncated file.

### 12. Integrity reporting — the anti-silent-failure feature
A zero must never be ambiguous. Distinguish *no India roles*, *slug unresolved*,
*probe failed/throttled*, and *provider returned 200 with an empty array* (the
known Lever trap).

**Acceptance:** every build emits `build-report.json` with a count per outcome;
a company that was never successfully checked is **excluded** from the site and
counted as `unchecked`, never rendered as "not hiring". The site footer shows how
many companies were checked and how many could not be.

### 13. Hiring velocity — trend from git history
The nightly workflow already commits `data/companies.json` to a git repo, so the
repo **is** the time series. Derive per-company trend by walking `git log` on that
one file. No database, no new storage, no backfill.

Each company gains `reqs_30d_ago` and `trend` ∈ `ramping | flat | cooling | new |
insufficient-history`, rendered as a sparkline with a "ramping" filter.

**Acceptance:** a company whose India req count strictly increased across
snapshots shows `ramping` and appears under the ramping filter; a company with
fewer than the minimum number of usable snapshots shows `insufficient-history`
and **never** a fabricated trend.

**Hard constraint — trend is computed ONLY over snapshots where that company was
successfully checked.** A snapshot in which the company was `unchecked` (feature
12) contributes **no data point**, never a zero. Without this, every Ashby 502
manufactures a phantom collapse, and a confident wrong trend is materially worse
than no trend — it misdirects a real career decision.

**Depends on feature 12.** Velocity is only as honest as the snapshots beneath it,
so integrity reporting is a prerequisite, not a parallel nice-to-have.

> This was adopted from the out-of-the-box step and **reverses a deferral** made
> earlier in this spec. The original reasoning — "historical tracking needs the
> persisted state statelessness buys us out of" — rested on a false premise: git
> is already a persisted store, obtained free as a side effect of committing the
> nightly JSON. The deferral was priced wrong, not decided wrong. Statelessness
> of the *build* is preserved; only the *reader* looks backwards.

---

## Non-goals

- No backend, database, user accounts, or saved searches.
- No director/DIN data. MCA publishes it; it is personal data and helps no one here.
- No job-application features — we link out, we never proxy an application.
- No paid data sources (Crunchbase, Tracxn, Tofler) in v1.
- No non-software sectors, no hardware, no biotech, no services firms.
- No scraping of MCA21 itself; `mca.gov.in` returns 403 and we respect that.
- No claim of completeness. The site shows what it could verify, and says so.

## Deliberately not building yet

- ~~**Historical tracking / trend charts.**~~ **Promoted to feature 13** — the
  deferral assumed history needs a store we don't have; git already is one.
- **Email / RSS alerts on trend changes.** The obvious sequel to feature 13
  ("tell me when a company starts ramping"). Deliberately held back until trend
  data is proven trustworthy over a real month of snapshots — alerting on a
  phantom trend is the worst version of this product.
- **More ATS providers** (Workday, SmartRecruiters, Lever EU, in-house boards).
  Add when the resolution rate plateaus and these are the measured gap.
- **Fuzzy-matching infrastructure.** Hand-maintained overrides until the override
  file gets painful. A matching framework before that is speculative.
- **Email alerts / RSS.** Real value, but it needs the history layer above.
- **Automated slug enumeration by crawling ATS namespaces.** Interesting, and a
  project of its own.

---

## End-to-end verification scenario

The single scenario that proves the whole thing works:

1. Run the full build from a clean checkout.
2. `data/companies.json` is produced, non-empty, and schema-valid.
3. Pick any company in it. It has ≥1 open India role, and that role's apply URL
   returns 200 on the company's real posting.
4. Pick a company NOT in it that has a resolved slug. `build-report.json` states
   why — `no-target-roles`, not `unchecked`.
5. Open the site. Zero console errors, zero failed requests.
6. Filter to "Bengaluru". Every result has a Bengaluru role; none has only, say,
   a Warsaw role.
7. The location fixture from Feature 5 passes: `In-Office` is not India.
8. The footer shows checked vs unchecked counts, and they sum to the corpus size.

If all eight hold, the site is telling the truth.

---

## Measured constraints (from `learning-tests/FINDINGS.md`, 2026-07-28)

| Fact | Value | Consequence |
|---|---|---|
| Greenhouse latency | 0.35s, one call, complete | nightly refresh is free |
| Ashby latency | ~151s fixed, payload-independent | weekly only |
| Ashby concurrency | flat wall at 1/4/12 → 16.8s/co at 12 | ~4.7h per 1,000 |
| Ashby throttling | 50s → 151s across three runs | backoff required |
| Ashby failures | 3/12 at concurrency 12 | retries required |
| Lever | 200 + empty array on bad slug | zero ≠ not hiring |
| India match | city list finds 167/4,337; ISO regex adds 0 real | no regex |
| MCA state-wise data | frozen at 2021-03-31 | never use |
| MCA RoC dataset | 3.67M rows, newest reg 2026-03-31 | the only usable source |
| Registered key page size | 10,000/call | full scan = 367 calls |
| Foreign subsidiaries on MCA | **24,102** | the enrichment universe |
| `CompanyIndian/Foreign Company` | ~670k rows contain `91` | field corrupt, unusable |
| MCA API under load | 502s after ~20 calls | cache the snapshot, degrade gracefully |

---

# Expansion — ROLE·ATLAS (v2, decided 2026-07-30)

**Compression:** The radar widens from one destination country to fifteen — same
stateless pipeline, same proof standard (a role on the company's own board, not
a claim) — with each kept role now tagged by the country it's in and, where the
posting says so, whether the company will hire from abroad (visa sponsorship or
remote-from-anywhere). The openness signal is the keystone: "funded companies in
Japan" is a list; "funded companies in Japan that will sponsor you" is a reason
to visit. It is also the hard part: no ATS has a structured field for it, so it
is a keyword heuristic over posting text with an honest `unknown` — and the
phrase list is frozen only after learning tests measure how often the phrases
actually occur in the wild. If they effectively don't, that finding kills or
reshapes feature 15 before anything is built on it. The site becomes
**ROLE·ATLAS**.

**Target countries (15):** India · United Kingdom · Ireland · Germany ·
Netherlands · France · Spain · Sweden · Denmark · Norway · Finland · Japan ·
Singapore · Australia · New Zealand.
"Europe" means these major hubs by decision, not all of the EEA — add a country
when probe data shows real volume there, not before.

**What stays India-only, deliberately:** the salary benchmark (feature 8,
AmbitionBox) and the MCA badge (feature 9). Per-country equivalents (Companies
House, Glassdoor-by-country, …) are six new integrations for a badge — out of
scope.

> **Superseded for the UK, 2026-08-02 (E9, T9.1).** "Out of scope" held while
> India was the largest plate; the UK is now 220 of 315 listed companies, which
> is a different trade. Companies House is built and India-only is now a
> statement about the OTHER thirteen countries. It also did not turn out to be
> "the MCA badge again with a different register": MCA's name match is
> publishable on a 24,102-row slice and is wrong about one company in ten on a
> 5.6M-company one, so the UK badge is earned by the company's own stated
> registration number rather than by its name. France, Japan and Australia are
> still out of scope, and now have a measured reason to be careful.

### 14. Multi-country role filter
Keep a company when ≥1 open role matches **any** target country; each kept role
carries the country it matched. Location matching follows the india.py doctrine:
word-boundary lists measured against real boards, no cleverness.

**Acceptance:** a fixture of real location strings across all 15 countries
classifies with zero false positives, including the cross-country traps:
`Cambridge, MA` is not the UK, `Perth, Scotland` is not Australia, a bare
`Newcastle` or `Nice` or `Reading` classifies as *no country* rather than a
guess. The existing India fixture passes unchanged.

### 15. Openness signal — hire-from-abroad / visa
Per role, from posting description text: `visa` and `hire_from_abroad`, each
`yes | no | unknown`. Explicit negatives ("we are unable to sponsor") are a real
`no` and worth as much as a yes. Silence is `unknown`, rendered as unknown —
**never** as "no".

**Acceptance:** a fixture of real posting excerpts (positive, explicit-negative,
and silent) classifies correctly; the phrase list cites measured frequencies
from `learning-tests/FINDINGS.md`; the site can filter to "open to foreign
hires" (`visa: yes` OR `hire_from_abroad: yes`).

### 16. Country navigation
One site, one `companies.json`. Country tabs (grouping is the site's choice —
e.g. a single Europe tab with a country filter inside it); India-only
enrichments render only where they apply.

**Acceptance:** selecting a country shows only companies with ≥1 role in that
country; per-tab counts are consistent with `build-report.json`; the India view
preserves all current behavior (city filter, salary, MCA badge); zero console
errors.

### Outcome vocabulary change
`no-india-roles` generalizes to `no-target-roles`. Build report gains per-country
listed counts. Everything else in feature 12 stands.

### v2 non-goals
- No per-country corporate registries or salary benchmarks.
- No translation: non-English postings (likely some in Japan) get `unknown`
  openness, honestly, rather than a guessed classification.
- No LLM classification of postings — it would add the first runtime dependency
  and a nightly cost to a zero-dependency build. Revisit only if the measured
  heuristic recall is unacceptably low.
- No country-specific job-quality scoring, cost-of-living data, or visa-law
  guidance. We report what the posting says, nothing more.

---

# v3 — Accounts (decided 2026-08-02)

**Compression:** The register stops being read-only. A visitor can create an
account, and the site knows who they are on the next visit — nothing more in this
version. It matters because of what it is the first step of: ROLE·ATLAS is
becoming a product for **getting** the job, not browsing it, and every feature in
that direction (a resume matched to a role, a named person who can refer you, a
paid ex-employee who preps you) needs an identity to hang off. Registration
withholds nothing. The corpus stays fully public — that is a decision, not an
oversight, and the reasoning is in "Not a wall" below.

**The keystone decision: auth is bought, not built.** Clerk holds the users, the
sessions, the password resets, the OAuth handshakes and the emails that come with
them. The site keeps zero credentials, stores zero passwords, and adds zero
backend — Clerk's browser SDK runs on the static page exactly as it stands, and
the publishable key it needs is public by design. This is the only reason accounts
fit inside a project whose whole architecture is "one JSON file on a CDN."

### 17. Account creation and sign-in
A visitor can sign up (email or Google), sign in, sign out, and reset a password
without leaving the site. A returning visitor is recognized without signing in
again. The header states which of the two states the reader is in, always.

**Acceptance:** on a page served from the live origin, a signed-out reader sees a
sign-in control and a signed-in reader sees their own account control; a session
survives a full page reload; sign-out returns the page to the signed-out state.
Zero console errors in every one of those states. No secret key exists anywhere
in the repository or the built site — only the publishable key, and a check
proves it.

### Not a wall
Nothing on this site is hidden from anonymous readers, and nothing will be by
this feature. The corpus is one public file on a CDN — a gate in front of it would
be a curtain in front of an open door, and the site's own claim is that it proves
what it says rather than asking to be trusted. Registration has to be worth
something on its own terms or not exist.

**Measured, 2026-08-01:** one nightly diff of the whole 15-country corpus produced
**0 new companies and 9 new roles**, while 179 roles disappeared — of which **176
were companies the build could not check that night, and 3 had actually closed.**
Two consequences the next version must respect. Alert frequency follows the data,
so weekly, not daily. And *absence in this corpus means "not observed," never "not
there"* — the invariant that keeps the site honest becomes a lie the moment
something differences it naively and emails a reader that a job closed. Any
feature reading snapshot-to-snapshot change must first record checked-vs-unchecked
per company per night, and may only speak about transitions where both sides were
genuinely observed.

### v3 non-goals
- **No gate, no paywall, no withheld field.** See above.
- **No profile page, no preferences UI.** Clerk ships its own; a second one is a
  second thing to maintain for no reader benefit.
- **No backend, no database, no session server.** The moment one exists, this
  project stops being a static site and starts being an application to operate.
  It will happen — feature 18 and beyond need it — but it does not happen for
  login, and doing it early buys nothing.
- **No storing of resumes, LinkedIn profiles, or any personal document.** The
  first PII this project holds should arrive with a decided retention policy, and
  that decision belongs to the feature that needs it, not to login.
- **No email from this project.** Clerk sends the verification and reset mail it
  needs. Anything we send ourselves is a sender reputation to manage.

---

# v4 — Applying (decided 2026-08-02)

**Compression:** The register stops being a place to read about an opening and
becomes the place a person gets the application *done* — for the 371 verified
companies and nowhere else. A signed-in user holds one profile of the constant
facts every application form asks for and one uploaded resume, and from any
verified role produces a complete package: drafted answers to that company's own
questions, a cover letter where one is asked for. They review it, edit it, and
submit it themselves on the company's board. Every application becomes a record,
and the record is completed by a model reading the user's mail rather than by the
user typing into a form.

**The keystone decision: the backend arrives, and the public register does not
change.** v3 said it out loud — *"no backend, no database, no session server. It
will happen — feature 18 and beyond need it."* This is that version. The
logged-in app is a client-rendered page on the same Pages site, talking to a
Cloudflare Workers API that holds the LLM key, D1 for records and R2 for
documents. The register stays the static artifact it is today: same nightly, same
`companies.json`, same CDN, zero runtime dependencies, no build step, no second
stack. Clerk continues to run browser-side exactly as T11.1 proved it does.

**The honesty invariant of this version: nothing we put in a form is a fact the
user has not given us.** Every filled field traces to a profile field or a line
of the uploaded resume. Where the company asks something we hold no fact for, the
workspace leaves a marked gap for the user to fill — it does not invent, infer or
flatter. This is `absence stays absence` pointed at an application form instead
of at a job board, and it is the whole reason this feature is defensible: the
user signs their name to what we hand them, so it has to be true.

## Architecture in one line (v4)

`static register (unchanged) + app page (client-rendered, same origin) -> Workers API -> D1 (records) + R2 (documents)`

**No model runs in this version, and that is a decision rather than a gap** — see
"The drafting slot" below. It is why the line above ends where it does.

### 18. The application workspace
A signed-in user records their constant facts once and uploads one resume. From
any role in the register they open a workspace: the posting on one side, the
company's own questions on the other, each already answered from their profile
where we hold the fact and marked as a gap where we do not. Every filled answer
names the profile field it came from. Nothing is ever submitted by us — the user
copies their answers and sends them on the company's board, and the interface
says so where they can see it.

**This feature writes prose for nobody.** It fills in facts the user stated once,
against questions the company published, and it is honest about the rest. That is
not a reduced version of the feature — it is the larger half of it, and the
measurement below is why.

**Measured 2026-08-02, and it moved the weight of this feature**
(`learning-tests/apply_questions_live.py`). Greenhouse states a job's application
questions on request; **Ashby states nothing, and 401 of 880 resolved slugs are
Ashby**. Of 52 Greenhouse jobs across 20 boards, 28 — **54%** — ask at least one
free-text question beyond the resume and cover letter. But the recurring ones are
*facts*: salary expectations, earliest start date, the address you would work
from, languages spoken, sponsorship needs, pronouns, interview accommodations,
how you heard about the job. Genuine prose — "Why Anthropic?", "How are you using
AI today in your current role?" — is the minority.

So **the profile carries this feature and no model is needed to do it.** A
profile holding those eight recurring fields removes more repeated typing than
drafting does, costs nothing per use, and cannot invent. Drafting answers the
minority question — "Why Anthropic?" — and is deferred with its price on paper.

And the doctrine applies to the form itself: for the Ashby half of the register
**we cannot see what the company asks, so we say we cannot**. A workspace that
showed only the resume field for an Ashby role would be claiming the form is
short when the truth is that we could not look — the same error as an unchecked
company rendering as "not hiring".

**Acceptance:** a signed-in user uploads a resume and it is retrievable on a
later visit from a different browser. Opening a Greenhouse role shows that
posting's real questions, each either answered from a named profile field or
marked as a gap. A question we hold no fact for renders a marked gap, never a
sentence — and a check proves it, against a profile deliberately missing the fact
the question needs. An Ashby role states that we cannot see this company's form,
and a check proves it does not instead render a short one. There is no control
anywhere in the interface that submits to a third-party board, and a check proves
that too. Zero console errors throughout.

### The drafting slot — deferred, priced, and not a gap

*"Why Anthropic?"* is the minority question, and answering it is the one thing in
this version that needs a model. It is deliberately not built, and the reason is
that **nobody has decided who pays for it.**

Measured 2026-08-02 (`learning-tests/draft_cost_live.py`), one real application:
**4,755 input tokens — $0.0195 warm, $0.0297 cold** — with output unmeasured and
billing at five times the input rate. Call it a few cents each. Twenty
applications for a hundred users is tens of dollars a month; the same behaviour
at ten thousand users is thousands. **Drafting cost scales linearly with users,
forever**, and that is a product decision rather than an engineering one.

Three answers, all defensible, none of them chosen yet:
- **The user's own key.** They supply it, drafting runs on it, it costs this
  project nothing. Suits an audience that mostly has one; costs signup friction
  and key custody.
- **We pay, funded by the partner side.** `F4` is where money enters this
  product. Drafting becomes something people pay for rather than something they
  are given.
- **It never gets built.** The measurement says the profile does the larger half
  for free. That is a real option, not a failure state.

**A Claude Code subscription is not one of the three** — verified 2026-08-02, all
three ways: `count_tokens` returns 200, `messages.create` returns 429, and
Managed Agents returns `403 OAuth token does not meet scope requirement`. It is a
credential for measuring, and it is licensed for its holder rather than for a
backend answering other people's requests.

**Feature 20 shares this slot.** Classifying a message as an acknowledgement, a
human reply or a rejection needs a model too — on the OAuth path and on the
auto-forward fallback alike. That feature was already third behind Google's
security assessment; this is the second thing it waits on, and the two are
independent.

### 19. The application record
Every application the user makes is a row they did not type. Applications built
in the workspace record themselves. Applications we had nothing to do with are
found by feature 20. The manual path is a box the user pastes a posting URL into
— there is no form to fill, because a product that makes people do data entry has
failed the brief it was written for.

**Register-only scope pays for itself here.** A pasted URL is a Greenhouse, Ashby
or Lever board address, and the corpus already maps every one of those to a
company, a role and a posting. Resolving the paste is a lookup in
`companies.json`, not an extraction — no model, no parsing of somebody's HTML, no
chance of getting the company wrong. A URL that resolves to nothing is a URL for
a company this register does not cover, and the box says exactly that.

The record obeys the doctrine the register runs on. **"No reply yet" and "we
could not look" are different facts and always render differently.** When a mail
connection lapses, expires or is revoked, every record it was feeding says so and
names the date we last genuinely saw the mailbox. A record never ages into
"rejected" through silence.

**The user sees their own numbers, and nobody else's** — how many applications,
how many drew a human reply, the median days to one, and which are still silent
past their own average. It is the calibration a person applying to thirty
companies has no way to get, and it is worth having on its own: most silence is
normal, and a candidate who cannot see that reads every quiet week as a verdict
on themselves.

**Acceptance:** an application completed in the workspace appears in the record
without the user entering anything. Pasting a board URL creates a record with
company, role and date resolved from the corpus, and the user is asked to confirm
rather than to type; a URL for a company the register does not cover is refused
by name rather than guessed at. A record whose mail source has stopped reporting renders as unobserved with
the last-observed date, and a check proves it does not render as "no response".
The personal counts are computed only over applications whose outcome was
genuinely observed, and a check proves an unobservable application is excluded
from the denominator rather than counted as a non-reply.

### 20. The inbox watcher
With the user's permission, a model reads their mail, recognizes the messages
that concern applications, and keeps the record current — shortlisted, rejected,
interview scheduled, or nothing yet. It is what makes the record complete rather
than a partial diary of what happened to start on our site, and it is the only
part of this version that works whether or not the user came through our funnel.

**We keep extractions, never contents.** The model reads a message in flight and
we store what it concluded — company, role, status, the date observed, the
message id — and nothing else. No body, no subject line, no attachment ever lands
in our storage. This is the single decision that keeps the liability of this
feature proportional to its value.

Four fields carry the timing, and they exist from the first row rather than being
added later: `applied_at`, `first_reply_at`, `reply_kind` — automated
acknowledgement, human, or rejection — and the outcome. **`reply_kind` is what
makes the timestamps mean anything and is the reason it cannot be retrofitted:
without it, an old row cannot say whether a two-day reply was a recruiter reading
the application or a robot confirming receipt, and every row written before the
distinction existed is uninterpretable forever.** No consent question attaches to
any of this — it is the user's own record of their own applications, shown back
only to them.

**This feature is third, and the reason is not engineering — measured
2026-08-02.** `gmail.readonly`, `gmail.metadata` and `gmail.modify` are all on
Google's *restricted* list, so reading only headers buys user trust and no
compliance relief. Restricted-scope apps must submit to **an annual security
assessment from a Google empanelled assessor**; until verification completes an
app is **capped at 100 users**, and in testing mode refresh tokens die after
**7 days** — which means the cap cannot even be used as a soft launch. That is a
process with a lead time this project does not control, so 18 and 19 ship first
and this ships behind either a completed assessment or the fallback: a Gmail
filter the user sets up themselves, auto-forwarding matching mail to an address
we own, which touches no OAuth scope at all. **The fallback is therefore the
design, not the contingency**, and the OAuth path is what replaces it once an
assessment is worth paying for.

**Acceptance:** a connected mailbox produces status changes on existing records
without the user acting, and produces new records for applications the user never
told us about. No message body, subject or attachment is present in D1 or R2, and
a check proves it by inspecting stored rows after a run over fixture mail. A
revoked or expired connection surfaces on every record it fed, with a date.

## Personal data, and the retention decision v3 deferred here

v3 refused to make this call and said the feature that needs it should own it.
It does.

- **Facts split by purpose.** Operational constants — visa need, relocation,
  on-site tolerance — live server-side, because they will shape what we show the
  user. The EEO demographics — gender, sexuality, race, veteran status — stay in
  the user's own browser, autofilled into other people's forms and never
  persisted by us. They are Article 9 special-category data in the EU and UK,
  they never needed to sync, and the cheapest correct handling of data you do not
  need is not to hold it.
- **One resume, no history.** Replacing it deletes the previous file. Versioning
  is Epic 1's job and is out of scope here.
- **Mail: extractions only.** See feature 20.
- **Deleting the account deletes the data in the same request** — R2 objects and
  D1 rows, not a queue, not a nightly sweep. A deletion you cannot verify
  synchronously is a deletion you cannot honestly claim.

## Measured before this froze (2026-08-02)

1. **The Gmail scope assumption holds, and it is worse than assumed.** Google
   classifies `gmail.readonly`, `gmail.metadata` AND `gmail.modify` as
   *restricted* — so header-only buys trust but no relief, exactly as feared —
   and restricted-scope apps "must meet the additional requirement of secure
   data handling by submitting to an annual security assessment from a Google
   empanelled group of security assessors." Unverified apps are **capped at 100
   users**, and refresh tokens for apps in testing mode are invalidated after
   **7 days**, which makes the cap useless for anything but a pilot. Feature 20
   is third, and the auto-forward fallback is not a curiosity — it is the design
   until an assessment completes.
2. **Greenhouse states its application questions; Ashby does not.** See the
   measurement folded into feature 18 above. This moved the weight of the
   feature from the drafting to the profile, and gave the Ashby half of the
   register an honesty requirement it would not otherwise have had.
3. **One drafted application: input priced, output still owed** — and the reason
   drafting is now deferred rather than built
   (`learning-tests/draft_cost_live.py`). Against a real 9,098-character posting
   with 6 real questions: **4,755 input tokens, of which only 951 are cacheable**
   — system, profile and resume together — and **3,804 are the posting**. The
   posting is four fifths of the prompt, so prompt caching takes one application
   from $0.0297 to $0.0195 of input rather than to nearly nothing. Output tokens
   are unmeasured and bill at five times the input rate, so the per-application
   figure is bounded below and not yet known. The completion returned **429 on
   the Claude Code subscription token** — it counts tokens freely and will not
   buy a completion — so finishing this needs an API key on API billing.

**The model calls in this version are single completions, not an agent loop.**
Drafting an answer, extracting a record from a pasted URL and classifying a
message are each one request with a JSON schema on the response; none of them
explores, uses tools or iterates. That matters architecturally: the Claude Agent
SDK is Claude Code as a library and needs a filesystem and subprocesses, which
Workers does not have — so reaching for it would cost this version its keystone
decision to buy a harness nothing here uses. The Anthropic SDK on Workers keeps
both. If a genuinely agentic feature arrives later — an agent that reads the
resume, opens the board and assembles the package unattended — that is the point
to revisit the runtime, and it is a real reason rather than this one.

## v4 non-goals

- **Nothing is ever auto-submitted, and nothing is ever submitted in bulk.** Not
  behind a flag, not for power users. A bot posting into Greenhouse and Ashby at
  volume is against their terms, is how a domain gets blocked, and is directly
  corrosive to a register whose entire claim is that it respects what those
  boards say.
- **No company outside the register.** A paste-any-URL applier makes the register
  decorative and puts this project head-to-head with a dozen tools on ground
  where it has no advantage.
- **No resume editing, tailoring or generation.** One uploaded file. Epic 1 owns
  this and is not built; pretending otherwise here would produce a second resume
  system to reconcile later.
- **No LinkedIn, of any kind.** Epic 3 owns the referral path and its whole
  premise is that partners are the graph. Nothing here scrapes.
- **No payments, no partner side.** F4's problems — employers forbidding paid
  referrals, payouts, identity checks, tax — are a different kind of software and
  none of them are solved by shipping this.
- **No email sent by this project.** Unchanged from v3, and now load-bearing: we
  are about to hold a mailbox connection, which makes our sender reputation worth
  more, not less.
- **No optimizing a draft to evade AI-detection.** Moot while drafting is
  deferred, and recorded because it must not creep back in with the feature. The
  goal is prose that is true, specific and in the user's voice. Writing to beat a
  detector is a different goal, it does not work reliably, and being caught at it
  would make a company distrust every candidate this site ever sends.
- **No LLM call anywhere in v4.** Not for drafting, not for resolving a pasted
  URL, not for classifying mail. Each one has a stated reason above, and the
  cumulative effect is that this version has no per-user running cost at all —
  which is what lets it ship before anyone has decided how it earns.

## Deliberately not building yet (v4)

- **Ranking roles against the resume.** It is the obvious next thing and it is
  `F2`, not this. It needs job description text at corpus scale, which is `F1`,
  which this version specifically avoided needing — the workspace fetches one
  posting on demand rather than storing 5,400 every night.
- **Interview preparation.** The natural sequel to a shortlist notification, and
  the thing that makes feature 20's output actionable. It should wait until
  feature 20 has produced real shortlists, because the shape of that help depends
  on what the mail actually says.
- **Multi-resume, per-role variants.** Epic 1.
- **Any cross-user or public statistic about a company's responsiveness.**
  Proposed as the one genuine leap of this version and demoted by its own
  challenge, kept here because the reasoning is worth more than the idea. The
  register already proves a company is hiring; aggregating feature 20's outcomes
  would prove whether it is worth applying to, which nobody else can publish
  because nobody else sees what happens after you apply. Three things stop it,
  none of them a schedule. **The metric as conceived rewards the wrong
  behaviour** — a company that auto-rejects in 48 hours scores as more responsive
  than one that takes three weeks to send a considered human note, which is the
  kind of flaw that is obvious in retrospect and humiliating on a site whose
  brand is that its numbers are honest. **The sample is structurally biased** —
  only applicants who use us and connected a mailbox — and unlike every other
  claim on this site we could not source it. **And most companies' numbers would
  rest on one or two applications**, which is publishing a rumour with a number
  attached. The unblock is three conditions, not a date: a reply classifier
  proven stable across ATS templates that change without notice, a metric that
  does not reward speed of refusal, and enough users that one company's figure is
  not one person's story. Consent is deliberately NOT taken at mailbox-connection
  time — asking permission for a hypothetical public statistic at the most
  trust-sensitive moment in the product taxes the feature that least can afford
  friction. Ask later, from users who already hold twenty outcomes, where the ask
  is concrete. The timestamps that would feed it are stored anyway, because
  feature 19 needs them for the user's own numbers.
- **Sharding D1 or moving to Postgres.** D1 is comfortable past 100k users and
  has a ~10GB ceiling that 1M would cross. All data access sits behind one
  module so the move is a swap; building for it now is building for a user count
  we do not have.

## End-to-end verification scenario (v4)

A new user signs in, fills the operational half of their profile and uploads a
resume. They open a role in the register, and the workspace shows that company's
own questions with a draft against each — every draft naming what it was built
from, and one question, for which the profile holds no fact, showing a marked gap
instead of a sentence. They edit a draft, copy the set, and follow the link to
the company's own board, which this site never posts to. The record now shows one
application they never typed. A message arrives in their connected mailbox; the
record moves to shortlisted, with the date. The connection is then revoked, and
every record it fed says so and states the date it was last genuinely observed —
not one of them says "no response". They delete their account, and the resume in
R2 and every row in D1 are gone when the same request returns.
