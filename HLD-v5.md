# HLD — v5: Searching

> Drafted 2026-08-03 for sign-off. **NOT SIGNED OFF, and deliberately so** — the
> plan below stacks a hosting migration, a private repo, a rewritten page loop and
> an SEO layer into one step, which is what made it hard to say yes to. The work
> was re-cut as a ladder instead, and its first rung shipped the same day as
> **T15.1 — Jobs are the page** (roles as the landing view, no gate, no migration,
> everything still static and public).
>
> **The remaining rungs, in order:** 2 · `first_seen` and a "new since" badge —
> useful with no gate at all, and the thing that makes signing in worth something.
> 3 · a soft client-side gate, whose real job is to MEASURE whether anyone signs
> in. 4 · this document — the Worker-served corpus, the private repo, the hosting
> move — which step 3 either justifies or kills.
>
> The `T15.x` numbering in the task table below is superseded: T15.1 is taken. The
> architecture, the measurements and the arguments all still stand; only the
> sequencing changed.

## In one line

The register stops being a list of companies you can search and becomes a list of
**roles** — 6,422 of them — served from the Worker rather than shipped to the
browser, with the full result set behind a sign-in.

## The keystone decision: the migration is the feature

You asked for a gate that genuinely withholds. Follow that one word and it
determines everything else:

1. Withholding is impossible while `data/companies.json` sits in a **public**
   repo — verified, `chandrameenamohan/india-radar` is `PUBLIC`.
2. So the repo goes private (T13.1).
3. GitHub Pages will not serve a private repo on the Free plan. So Pages dies.
4. So the site is served by the Worker, at `roleatlas.sennamind.com`.

Step 4 is where the chain stops costing and starts paying:

- **The open TLS problem is deleted, not solved.** `worker/index.mjs:4-10` already
  explains why the API had to live on its own hostname: the apex was a DNS-only
  CNAME to GitHub Pages *because that is what let GitHub issue the certificate*.
  Remove Pages and Cloudflare proxies the apex, Cloudflare issues the certificate,
  and `roleatlas.sennamind.com` is a **two-level** name Universal SSL already
  covers. The three-level `api.` hostname that has never completed a handshake is
  no longer needed by anything.
- **CORS is deleted too.** Same origin. `ALLOWED_ORIGINS`, `corsHeaders`, the
  `OPTIONS` branch and the "handlers return DATA so none can forget the headers"
  machinery all become dead. That comment block stops being a security control and
  becomes a paragraph of history.
- **T13.1's trade-off dissolves.** The task records "private may cost the live
  URL." Under this plan it does not — the URL moves to the Worker and survives.

The migration is not overhead attached to the feature. It is the only version of
the feature you actually asked for, and it retires two open problems on the way.

## What v5 reverses, and why the reversal is honest

`SPEC.md` has a section called **"Not a wall"** and a v3 non-goal reading *"No
gate, no paywall, no withheld field."* v5 contradicts both, so the SPEC must record
the reversal rather than quietly grow a wall next to a paragraph promising none.

The reversal is coherent, and the original text says why. v3's argument was never
that a gate is wrong — it was that *"a gate in front of it would be a curtain in
front of an open door."* The door was open because the corpus was one public file
on a CDN. The migration closes the door. The objection expires with the
architecture that produced it.

What does **not** expire is the sentence after it: *"Registration has to be worth
something on its own terms or not exist."* A wall is not worth. That is what the
change record below is for.

## Architecture

```
nightly Action ──> build ──> data/companies.json      (archive, in git, now private)
                     │
                     ├──> data/roles.json             (the query index — new)
                     └──> data/changes.json           (the change record — new)
                              │
                              └──> wrangler deploy ──> Worker bundle
                                                        │
                              roleatlas.sennamind.com ──┤ GET  /            the page
                                                        │ GET  /api/search  rows + facets
                                                        │ GET  /api/changes what's new
                                                        └ …existing /api/* (unchanged)
```

**The roles index ships inside the Worker bundle.** Measured: the roles-only
projection is 926 KB of JSON, **170 KB gzipped**, against a 3 MB compressed limit
on the free plan. So there is no D1 query, no R2 read, no KV, no new store, and no
per-request storage cost. Search is a linear scan over an in-memory array in a warm
isolate — at 6,422 rows that is microseconds, and it is the laziest thing that is
also the correct thing.

The nightly Action gains a `wrangler deploy` step. Data freshness becomes a deploy
rather than a commit, which is a change to how the pipeline finishes, not to the
pipeline.

**Filtering moves server-side with the data, and that is the real frontend cost.**
`render()` currently filters ~250 lines' worth over the whole corpus in the
browser. It becomes: build query params → fetch → paint. Simpler in the end, but
it is a rewrite of the page's core loop, not a new view bolted beside it.

## Findable first, gated second

Decided 2026-08-03: the site must be indexable by search engines **and by LLM
crawlers**, and the sign-in ask lands when a reader arriving from one of those
links wants more.

That inverts the naive gate. A wall in front of everything is also a wall in front
of Googlebot, GPTBot and PerplexityBot, and an unfindable job site has no readers
to convert. So:

**Public, indexable, no sign-in:**

- `GET /role/<id>` — one page per role, rendered by the Worker **from the bundle
  it already holds in memory**. No file generation, no 6,422 committed pages.
  Carries JSON-LD `JobPosting` structured data, which is what puts a listing into
  Google Jobs and what LLM crawlers read most reliably.
- `GET /sitemap.xml` — generated from the same bundle. Same zero files.
- The atlas home page, its counts, its plates, and `/api/changes`.

**Behind sign-in — "more detail" means depth, not the facts:**

- Search past the staged cap.
- Every other role at that company.
- What's new since your last visit; save a role; alert me.

**One recommendation against the letter of the brief, with its reason.** The
board link on a role page stays **public**. The site's entire thesis is *"proven by
their own job board, not by a claim"* — the click-through is the proof, and a
register that hides its own evidence behind a login is asking to be trusted, which
is the one thing it has always refused to do. Gate the depth, not the verification.
Say the word and I will gate the link instead; it is one condition either way.

**The honest cost of being findable.** A public page per role means the corpus is
crawlable by anyone who reads our own sitemap. That is a real hole in "genuinely
withhold" — priced, not hidden. It is also the hole every job board on the
internet has, and crawling 6,422 pages is a materially different act from
downloading one 248 KB file. Recommended: publish the sitemap and accept it.

## The gate

**Staged, as you chose:**

| Reader | Gets |
|---|---|
| Anonymous, searches 1–3 | Every matching role |
| Anonymous, search 4+ | **5 rows**, plus the true total and a sign-in prompt |
| Signed in | Everything |
| Any crawler, any role page | The role's full facts, always — never counted, never capped |

**The principle that keeps this honest: the gate withholds rows, never counts.**
A capped response still says *"214 roles match — showing 5."* The site's whole
doctrine is that a number means what it says; a total secretly narrowed by the
paywall would be the first lie the register has told. It also happens to be the
better product — every capped search advertises the size of what is behind it.

**Counting an anonymous reader without a database.** A D1 write per search would
eat the 100k writes/day budget, and there is no user to key a row on. The answer is
a **signed stateless cookie**: `{n, since}`, HMAC'd with a Worker secret so the
count cannot be forged upward or downward. No storage, no lookup, no cost.

Its ceiling, written down rather than discovered later: **clearing cookies resets
the grace period.** No soft wall survives that, and the fix is a hard login, which
is not what you asked for. What this version buys over a client-side counter is
categorical anyway — the reader who clears cookies gets three more searches, not
the 6,422-row file.

**A search is a distinct query term**, as you chose: debounced, normalized, and
deduped against the terms already spent. Typing `react` slowly is one search;
searching `react` again next week is not a new one. The counter increments on the
term, not on the filters — picking a country never burns a search.

## The dangerous edit, named

`worker/index.mjs:104-107` says:

> AUTHENTICATION RUNS BEFORE EVERY HANDLER, WITHOUT EXCEPTION. There is no
> per-route opt-in… A public endpoint, if one is ever wanted, has to be added here
> deliberately rather than by omitting a line further down.

`/api/search` is that public endpoint, and it is the most security-sensitive line
in this plan. The dispatcher already prescribes the shape — an explicit `PUBLIC`
set checked at the top, never a handler that quietly skips auth. Two failure
directions, both bad and both cheap to test: a bug that leaves the whole corpus
ungated, and a bug that walls the readers who paid with their email.

This gets its own task, and it meets the repo's standard — **a guard counts as
covered only once deleting it has been shown to turn a test RED.**

## The change record — and the measurement that decides its shape

You asked to show when a new role or company appears, and to build the audit now
even though nothing notifies yet. The audit is the right instinct, because the
naive version of this feature is already known to be wrong.

**`SPEC.md` records a measurement from 2026-08-01:** one nightly diff of the whole
corpus produced **0 new companies and 9 new roles, while 179 roles disappeared — of
which 176 were companies the build could not check that night, and only 3 had
actually closed.**

A naive diff is **~98% noise**, and every one of those false disappearances would
be the site breaking its own central promise: *absence means "not observed," never
"not there."* The spec already states the precondition — a change feature must
record checked-vs-unchecked per company per night and may only speak about
transitions where both sides were genuinely observed.

**That precondition is already met, which is why this is cheap.**
`data/build-report.json` carries `companies: {name → status}` for all 2,925, with
`listed / no-target-roles / slug-unresolved / probe-failed / empty-board-unverified
/ not-qualified / another-companys-board`, plus `checked: 834, unchecked: 2091` —
and it is committed nightly beside `companies.json`. Git history is the snapshot
archive; 26 nightly commits exist already.

So `data/changes.json` is a build step over two commits, with one rule:

- A role is **new** when its URL is absent from the previous snapshot and its
  company was `listed` on both nights.
- A role is **closed** only when its company was `listed` on both nights. Otherwise
  it is **unobserved**, and the record says so in those words.
- A company is **new** on the same both-sides-observed rule.
- Counts of new / closed / unobserved are all published. Hiding the unobserved
  bucket would rebuild the exact lie the measurement caught.

**What it unlocks, which is why it belongs in v5 rather than after it:** each role
gains a `first_seen` date. That single field is simultaneously a **sort** ("newest
roles"), a **badge** ("new since Aug 2"), the substrate for the **notification**
you are deferring, and — the part that matters — *the reason to sign in that is not
a wall.* "Email me when a role like this appears" is worth an account. Nine new
roles a night also settles the cadence the spec already inferred: **weekly, not
daily.**

`/api/changes` is public and ungated. What is new is a fact about the corpus, and a
teaser only works if strangers can read it.

## Failure modes

- **Worker down = site down.** Today a broken Worker costs the app; after the
  migration it costs the register too. Mitigation is the gate we already run plus
  Cloudflare's own rollback; the honest note is that this is a real reduction in
  the static site's near-perfect availability, traded for the feature.
- **Bundle outgrows 3 MB.** At 170 KB there is 17× headroom, but the corpus grows.
  The build fails loudly on a size threshold rather than a deploy failing at
  midnight.
- **Nightly deploy fails.** The site keeps serving the previous bundle — stale but
  true, and the snapshot date on the page already says which night it is.
- **Cookie secret rotates.** Every anonymous reader's count resets. Acceptable, and
  it beats refusing to serve.

## What I would not build

- **No search backend.** No index, no Elastic, no D1 FTS. 6,422 rows in memory.
- **No per-user search history, no saved searches, no alerts table.** The record is
  corpus-wide; personalising it is v6's problem and needs the workspace first.
- **No notification delivery** — email, push, or otherwise. Your instruction, and
  correct: the spec's own v3 non-goal is "no email from this project," and a sender
  reputation is not something to acquire as a side effect.
- **No hard login.** The wall stays soft; cookie-clearing stays a known ceiling.

## Task shape (for TASKS.md on sign-off)

| | Task | Depends on |
|---|---|---|
| T15.1 | Site served by the Worker at the apex; Pages retired; TLS and CORS deleted | — |
| T15.2 | The roles index, built and bundled, with a size ceiling | — |
| T15.3 | `/api/search` — the public route, facets, and the auth-boundary guard | T15.2 |
| T15.4 | The staged gate: signed cookie, rows withheld, counts never | T15.3 |
| T15.5 | The job-first page: `render()` becomes fetch-driven | T15.3 |
| T15.6 | `data/changes.json` and `first_seen`, both-sides-observed only | T15.2 |
| T15.7 | `/api/changes` + "new" badge and "newest" sort | T15.6, T15.5 |
| T15.8 | Public role pages, JSON-LD `JobPosting`, sitemap | T15.2 |
| T13.1 | Repo private, org move | T15.1 |

T15.1 and T15.2 are independent and are the natural parallel pair.

## Decided 2026-08-03

- **Findable.** Search engines and LLM crawlers get full role pages; the sign-in
  ask is for depth. The crawlable-corpus hole is accepted and written down above.
- **The atlas stays.** The chart, the graticule and the fifteen plates keep
  working, driven by counts — which the gate never withholds. A plate is now a
  filter on roles rather than on companies, so "roles in Japan" is one click and
  the map still means what it always meant.
- **Phase 9 waits.** T14.5 and T14.6 land after v5, not beside it. They would be
  editing `worker/index.mjs` while T15.1 and T15.3 rewrite its dispatcher, and the
  workspace was designed against a company register that v5 replaces — worth
  re-reading its spec once roles are the page.

## Still open

Only one, and it is a preference rather than a blocker: **the board link on a role
page.** Recommended public, for the reason in "Findable first" above. Overrule and
it becomes the gate's best-converting moment instead.
