# HANDOFF — ROLE·ATLAS session continuation

> Paste this file as the first prompt of a new session:
> "Read HANDOFF.md and continue from where it says NEXT."

## What this project is

ROLE·ATLAS (repo `chandrameenamohan/india-radar`, local
`/Users/ralph/sennamind/next-rocket-ship`): a static site listing funded
software companies with verified open roles across 15 countries — "proven by
their own job board, not by a claim." Python pipeline (zero runtime deps)
builds `data/companies.json`; `site/index.html` renders it; GitHub Pages
serves it; a nightly GitHub Action rebuilds data. Core doctrine everywhere:
**absence stays absence** — an unchecked company is never "not hiring", a
missing fact renders as nothing, a derivation says it is derived.

**THE LIVE URL IS NOW https://roleatlas.sennamind.com** (2026-08-02). The old
`chandrameenamohan.github.io/india-radar/` 301s to it. DNS is a CNAME on the
sennamind.com Cloudflare zone, DNS-only (grey cloud) so GitHub could issue the
cert; the `CNAME` file at the repo root is what Pages reads. The repo is still
named india-radar — renaming it is a human action, still not done.

- Tasks live in `TASKS.md` (markdown, NOT beads — bd is broken here). House
  style: `### T<n> — Title \`status\`` headers, Acceptance/Checks/Out-of-scope
  DoD blocks, measured narrative notes. Never weaken a check to pass.
- Gate: `make check` (lint → mypy → pytest → `scripts/e2e.sh`). 556 unit tests,
  ~100 e2e checks. KNOWN SHARP EDGE: e2e binds fixed port 8731; back-to-back
  runs and stray `http.server` processes race it — check `lsof -ti :8731`
  before believing an e2e failure.
- Commit style: narrative prose that explains the finding and the why, not a
  changelog (read `git log --oneline -10`). Push to `main`.
- **Pushes are slow.** `data/companies.json` is ~2.4MB and a push can exceed
  two minutes; use `timeout 480 git push origin main`. `git config
  http.postBuffer 524288000` is already set.

## State as of 2026-08-02 (end of a long session)

**41 tasks done. The site is 371 companies and has accounts.**

- **v3 — ACCOUNTS SHIPPED (T11.1).** Clerk's browser SDK on the static page:
  a script tag, a publishable key, one div in the masthead. No backend, no
  database, no credential in the repo. The register is PUBLIC and stays public
  — registration gates nothing, and `tests/test_auth.py` holds that by
  refusing any `Clerk` reference inside the renderer. See SPEC.md "v3 —
  Accounts" for the reasoning, including the measurement that killed the alerts
  idea (one nightly diff: 0 new companies, 9 new roles, 179 roles gone — of
  which 176 were companies the build could not check and 3 had actually closed.
  Absence means "not observed", never "not there").
- **T12.1 — Ashby slug guessing, built AND realised.** `guess` now tries Ashby
  after Greenhouse, verified by the board page's `<title>` AND
  `organization.publicWebsite` matching the address the corpus already held.
  The hand-run over 1,445 companies resolved 135 in 12.8 min.
  **316 → 371 listed, 700 → 834 checked, 0 companies lost.** The
  address-verified yield projected 10.0% off a 240-company sample and came in
  at 9.3% over the full set; name-matching alone offered 17.5% and a quarter of
  that was the wrong company.
- **T9.1 — UK Companies House badge done.** 19 of 220 badged, zero false
  positives. A badge is earned only where the COMPANY states its own number on
  its own site and the register resolves it. Schema is now **v10** (`uk` field).
  `data/uk.json` is the cache; the nightly only ever reads it.
- **T10.4 / T10.5 done.** Six website corrections are real in `corpus.json`.
  Two derived website sources added (`from_board`, `from_ats`) — the ATS's own
  page states the company's address for 26 of 40. **Listed companies with no
  address: 45 → 14. Descriptions verified: 245 → 272 of 319.**
- **`python -m src.slugs --gained`** now exists (T10.4): resolves only the names
  the corpus gained plus names a human answered differently. 31 names in 20
  seconds against the 2.5 hours a full re-resolve costs.
- **T7.1/T7.2 (trend + sparklines): still blocked on calendar** — needs ~30
  nightly snapshots; first nightly ran 2026-07-30; earliest start ~2026-08-29.
  Do NOT unblock early; TASKS.md T7.1 has the re-check commands.

## Hard-won lessons (do not relearn these)

- **NAME MATCHING IS NOT IDENTITY.** Three independent sources said so in one
  day: 25% of name-verified Ashby boards were a different company; applying the
  India/MCA rule to Companies House would have published 141 UK companies of
  which 15 are provably somebody else; and the live site was publishing
  Langfuse's 7 roles under ClickHouse's name. Always corroborate a name match
  against an independent fact — an address, a number the company itself states,
  a registration the register can resolve. This is THE constraint of this
  codebase.
- **A good comment can outlive its measurement.** Three stale guards found in
  one day, each a reason recorded once, correct then, never revisited: Ashby's
  "~151s fixed latency per candidate" (actually 1.6s — it blocked slug guessing
  entirely), `verify_override`'s "ashby probes land with T3.2/T3.3" (they
  landed long ago, and it still refuses every non-Greenhouse override), and
  e2e's hardcoded "schema v9". **When a comment justifies NOT doing something,
  re-measure before believing it.**
- **A check can fail by reporting success.** The stale `schema v9` assertion
  reported "rendered" for a page that had refused correctly — green would have
  been the lie. Derive expectations from the artifact; do not hardcode them.
- **ClickHouse was a good read of a bad source.** Its own careers page links
  `jobs.ashbyhq.com/langfuse`. Discovery was correct; the company's page is
  wrong. No verification this project could write would have caught it, because
  the board it points at is real and really does state Langfuse.
- **AGENT WORKTREES RE-INITIALISED THE MAIN REPO.** Git exports `GIT_DIR` /
  `GIT_INDEX_FILE` into hooks; `tests/test_nightly.py` built throwaway repos
  with the ambient environment, so under the pre-commit hook `git init` hit the
  REAL repository. Symptoms: `core.bare` flips to `true` (every git command
  then fails "must be run in a work tree"), staged mass deletions, moved HEAD.
  **Fixed** (the fixture scrubs `GIT_*`), but if it recurs: `git config
  core.bare false`, then verify with `git rev-parse HEAD origin/main` and
  `git fsck`. Content was never lost either time.
- `.claude/worktrees/` is gitignored now — `git worktree add` puts them INSIDE
  the repo, so `ruff check .` walks into another agent's half-written code and
  fails the gate on a file this checkout does not own.
- **Headless Chrome clamps `--window-size` to 500px minimum.** Sub-500 "mobile"
  screenshots are cropped desktop layouts → phantom overflow bugs. True small
  viewports need CDP `Emulation.setDeviceMetricsOverride`. Also `overflow-x:
  clip` on html/body makes `scrollWidth` lie.
- **Clerk specifics** (all measured, `learning-tests/clerk_live.py`):
  `@clerk/clerk-js@latest` serves **v4**, not v5 — pin `@5`. The frontend host
  is base64 inside the publishable key. `/v1/environment` is readable with no
  key at all. The hosted portal is on a DIFFERENT host from the frontend API,
  so redirect flows walk the reader off the site — mount components locally,
  and pin `afterSignOutUrl` to the current URL or signing out drops the query
  string and the reader's filters. **Sign-UP cannot be automated** (Turnstile
  does not solve headless); sign-IN can, which is why the e2e signs in as one
  dedicated `+clerk_test` account.
- Verify agents' work on disk; idle notifications are not reports. Brief every
  subagent to SEND a final report, and to run `make check-fast` only — never
  the full gate, because concurrent agents collide on e2e's port 8731.
- A performance comparison across a behaviour change must hold work constant.

## NEXT (in order)

1. **Decide the product direction.** `TASKS.md` "The long picture" (F1–F7)
   records the human's stated goal and is deliberately NOT scheduled work — its
   headers do not match the `^### T<n>` pattern the loop counts. The product is
   becoming a referral marketplace: resume→job matching, finding a named human
   inside who can refer you, and paid ex-employee / ex-recruiter partners.
   **F1 is the one to read first**: the build already downloads every job
   description and throws the text away, and every matching feature is blocked
   on it. F3 carries the important judgment — the referrer wedge does NOT need
   LinkedIn's graph, because the partner side IS the graph.
2. **Small, specced, no decisions needed:**
   - `ClickHouse`'s override is `greenhouse/clickhouse` rather than
     `ashby/clickhouse` ONLY because `verify_override` still refuses
     non-Greenhouse slugs. Widening it is a real task and
     `src/ashby.identity()` already does the work.
   - 8 dead Ashby slugs in `data/slugs.json`: `charta-health`, `edison`,
     `hitpayapp.com`, `jasper` (×2 companies), `paxos-technology-solutions`,
     `resolve`, `tools`.
   - Three UK companies state two genuine numbers and are held rather than
     guessed: **Marshmallow**, **Pleo** (one is a Danish CVR, also eight
     digits), **Tide**. A human settles all three in minutes.
   - `MeltPlan` and `Niantic Spatial` came back `wrong_description` and are
     left standing as unverified rather than quietly regenerated.
3. **The 740 `no-website` companies are out of reach** and that is a sourcing
   problem, not a resolution one: 650 are SEC Form D filings that state a name
   and no domain. Do not spend a session guessing at them.
4. Late August: re-check T7.1's unblock condition (snapshot count).

## Loose ends from this session

- `FeatureBrainstorming.md` was swept into a commit by a `git add -A`. It is
  the human's file, not project work — untrack it if unwanted.
- `.env` now holds `CLERK_PUBLISHABLE_KEY`, `CLERK_E2E_EMAIL`,
  `CLERK_E2E_PASSWORD`, `UK_COMPANY_HOUSE_KEY`, `CLOUDFLARE_API_TOKEN`. The
  Cloudflare token's job (the CNAME) is done and it can be revoked.
  `.env.example` was NOT updated to document the Clerk e2e vars — the human
  declined that edit.
- Clerk is still a **development** instance. Production needs CNAMEs on
  sennamind.com; the DNS token is in `.env`.
- Three agent worktrees may still exist under `.claude/worktrees/`. All three
  branches are merged — prune with `git worktree list` / `git worktree remove`.

## Billing context (check before any large fan-out)

As of 2026-08-01 the monthly spend cap was hit ($101.32/$100), usage credits
blocked until Sep 1, and $21.91 promotional credit expires Aug 9 unless the
human raises the limit. Plan (Max 5x) session/weekly limits were fine. **This
session ran three concurrent subagents (~925k subagent tokens).** Re-check the
current position before doing that again.
