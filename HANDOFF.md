# HANDOFF — ROLE·ATLAS · 2026-08-04

> Paste this file as the first prompt of a new session:
> "Read HANDOFF.md and continue from where it says NEXT."

## THE ONE THING THAT IS TIME-SENSITIVE

**T15.2 is built, green and UNPUSHED, on branch `t15.2-first-seen` @ `54736dd`.**
The nightly fires at **20:00 UTC daily**. Whether that branch is on `main` before
the next firing decides whether tonight is the first night this project can
honestly say a role is new.

Nothing breaks if it misses — the artifact simply keeps its backfilled state and
the first confirmation night slides a day. The only cost is that one cohort of
roles gets dated a day late, because the fold would compare a two-night gap.

```
git checkout main && git merge --ff-only t15.2-first-seen \
  && git pull --rebase origin main && timeout 480 git push origin main
```

**The push is blocked by the permission classifier — a human has to run it** with
the `!` prefix. See the classifier note below.

## HOW TO WORK THIS SESSION

**Match the harness to the work, and this repo has now done it both ways in one
day.** The roles register (T15.1) was one thread of reasoning through one file
and was rightly done with no subagent at all. T15.2 was a self-contained feature
with a decidable brief — data artifact, backfill, nightly step, two site
controls — and went to a single agent that returned it green.

**When you do delegate, the brief is the work.** The T15.2 brief pinned down two
things before the agent started, and both would otherwise have failed silently:
that the nightly may not read git history (`actions/checkout@v4` is depth 1 — in
CI there IS no history), and that the honesty rule is the design rather than a
caveat. Everything else was left to the agent, and it made better calls than the
brief would have.

**Verify what an agent reports. Re-run its mutation sweep yourself.** T15.2's
claims all held — and re-deriving its central finding from `git log` independently
made it *stronger* than the report claimed. That is the value: not catching a lie,
but finding the sharper version of the truth.

## What this project is

ROLE·ATLAS (repo `chandrameenamohan/india-radar`, local
`/Users/ralph/sennamind/next-rocket-ship`): a register of funded software
companies with verified open roles across 15 countries — "proven by their own job
board, not by a claim." Python pipeline (zero runtime deps) builds
`data/companies.json`; `site/index.html` renders it; GitHub Pages serves it from
`main` at root; a nightly Action rebuilds the data.
**Live at https://roleatlas.sennamind.com.**

**As of 2026-08-03 the page is a JOB search, not a company directory.** It opens
on 6,422 roles; the company register it grew out of is one switch away at
`?view=companies`, unchanged.

Core doctrine everywhere: **absence stays absence** — an unchecked company is
never "not hiring", a missing fact renders as nothing, a derivation says it is
derived. T15.2 is the sharpest test of it yet: a role we cannot prove is new does
not get a badge, even though we know the date we first saw it.

- Tasks live in `TASKS.md` (markdown, NOT beads). House style:
  `### T<n> — Title \`status\` · *Phase N*`, then a `>` narrative note, then a
  fenced Acceptance/Checks/Out-of-scope block. Never weaken a check to pass.
- Gate: `make check` (lint → mypy → pytest → **worker** → e2e).
  `make check-fast` skips the site e2e. **594 unit + 128 worker + 12 worker-e2e +
  ~120 site e2e checks.**
- Commit style: narrative prose explaining the finding and the why, not a
  changelog. Read `git log --oneline -8`.
- **Pushes are slow** (`data/companies.json` is ~2.9 MB) and the nightly commits
  to `main` while you sleep. `git pull --rebase origin main` first, always.
- **PORTS: 8731 (site e2e) and 8788 (worker e2e).** Concurrent agents running the
  gate WILL collide — brief them to run only their own tests, or to run the gate
  only if they are the sole agent.

## State as of 2026-08-04

**`origin/main` is `b06095f`. Working tree clean. Full gate green.**

Shipped and live today:

| | |
|---|---|
| `a76aa5b` | **T15.1 — Jobs are the page.** The register's unit is the role. |
| `b06095f` | **57 company descriptions backfilled**, 51 written and 6 refused. |

Built, green, **not pushed**:

| | |
|---|---|
| `54736dd` on `t15.2-first-seen` | **T15.2 — `first_seen` and "new since".** |

Three merged branches are lying around (`roles-register`, `descriptions-backfill`,
`t15.2-first-seen`) plus three stale worktrees under `.claude/worktrees/`. All
prunable; `git worktree remove` for the latter.

### The shape of the plan changed today, and that is the important part

A session began by asking for job search plus a sign-in wall. Answering four
coupled questions at once produced `HLD-v5.md` — a hosting migration, a private
repo, a rewritten page loop and an SEO layer, all in one step. It was coherent and
it was **unbuildable as a single decision**, which is why it was never signed off.

**It was re-cut as a ladder, and the ladder is the plan now:**

1. **Roles are the page.** ✅ Shipped as T15.1. No gate, no migration, still
   static and public.
2. **`first_seen` and "new since".** ✅ Built as T15.2, awaiting a push. Useful
   with no gate at all, and it is the thing that later makes signing in worth
   something.
3. **A soft, client-side gate.** Not started. Its real job is to **MEASURE**
   whether anyone signs in.
4. **`HLD-v5.md`** — the Worker-served corpus, the private repo, the hosting move.
   Step 3 either justifies it or kills it.

**Do not skip to 4.** `HLD-v5.md` remains accurate on architecture, measurements
and arguments; only its sequencing and its `T15.x` numbering are superseded. Its
best finding is still live: **serving the site from the Worker would DELETE the
TLS problem below and the CORS allowlist with it**, because the apex is a
two-level name Universal SSL already covers.

## T15.1 — Jobs are the page

`site/index.html` only. The register lists roles; `?view=companies` deep-links to
the company index; role lines are `.jrow`, built by `roleRow(c, r)`; the list
pages at 200 behind a `.spreadfold`.

**The filters cut at the ROLE, and that is the whole difference between this and a
re-skin.** Under the company register a company with one remote job keeps every
on-site job it has — correct there, because the unit is the company, and wrong
here for the same reason `inScope` exists one level up. Workplace, foreign-hires
and city are re-applied per role on the flatten; plate and department were already
role-level. A role line cites its OWN countries, so Theta Global's London job
prints ·GB alone.

**Adding beside rather than replacing was the decision that made it an afternoon.**
Replacing the company register outright would have invalidated ~40 of the e2e's 87
checks, and this repo rewrites checks rather than weakening them — 40 rewrites
against a design nobody had used yet. Pinning them with one `&view=companies` on
`$FIXTURE` cost a line. **Deleting the company view later is cheap; doing that
rewrite twice is not.**

## T15.2 — first_seen, and why nothing is badged

Every one of the 6,422 published roles carries the date it was first seen.
**None of them may be called new**, and that is the finding rather than a bug.

- `src/firstseen.py` — `advance(prev, companies_doc, report)`. Reads no git.
- `scripts/first_seen_backfill.py` — the one-time hand run over 26 commits. Every
  judgement in it is `advance`'s, so the backfill exercises the nightly's code.
- `data/first-seen.json` — 494 KB, 6,505 URLs, grouped by date. `observed` is the
  nightly's entire memory of yesterday; drop it and every tomorrow silently
  becomes a baseline.
- `scripts/nightly.sh` runs it after the build, behind the same
  `NIGHTLY_FIRSTSEEN` seam as `NIGHTLY_BUILD`. `nightly.yml` is unchanged.

**THE RULE:** a role may be called new only when its company was `listed` in BOTH
the previous snapshot and this one. SPEC v3's measurement is why — one nightly
diff gave 9 new roles against 179 disappearances, **176 of which were companies
the build could not check that night.**

**AND THE RULE IS NOT ENOUGH, which is the new lesson.** Folding it over all 26
commits *confirms* 1,728 roles — but 4,340 of the artifact's dates land on
2026-07-31 and 1,032 on 2026-08-02. `src/countries.py` T8.2 (the fifteen-country
radar) landed 2026-07-30; `T12.1 realised: 135 boards found, the register grows
316 → 371` is dated 2026-08-02. **5,372 of 6,505 dates are the build changing what
it LOOKS FOR, not anybody hiring.** Those roles were open all along; we were not
looking at Germany yet. The both-sides rule is blind to it — the company was
`listed` on both nights.

So the backfill demotes everything to unconfirmed: **history gives dates, not
badges.** Confirmation starts with the first nightly after the branch lands, and
SPEC's own measurement says that night should badge about nine. **Nine true badges
beat 1,604 false ones.** The badge window is 7 days, from SPEC v3's "weekly, not
daily".

Closures are deliberately out of scope. That is where the remaining noise lives.

## PROVISIONING

**Cloudflare account `5bb014e16f8cf5d16a6eb4e53245be81`.** `.env` holds a working
`CLOUDFLARE_API_TOKEN` scoped Workers Scripts / D1 / R2 / DNS / Workers Routes.
**It has a TTL — if calls start failing with 401, check expiry first.**

- ✅ **D1** `roleatlas`, APAC, `database_id = 8383daaf-b15f-4813-804b-7c4c8419eb34`,
  already in `worker/wrangler.toml`. Two tables (`profiles`, `resume_usage`).
- ✅ **R2** enabled, bucket `roleatlas-resumes` exists.
- ✅ **The free tier is enforced in code (T14.9)**, because R2 bills past it
  rather than stopping. 9 GB of 10, 800k Class A ops of 1M, in `resume.mjs`.
  Reads are uncounted by design: counting one costs a D1 write, and D1's 100k
  writes/day is tighter than R2's 10M reads/month.
- ✅ **Worker deployed** 2026-08-03, version `6fb8927d`, both bindings resolving.
- ✅ **CI has run the worker e2e under real workerd** and it is green.
- ⛔ **NO TLS ON `api.roleatlas.sennamind.com`.** Still the one open infra
  problem. Every request fails `sslv3 alert handshake failure`, measured
  continuously for an hour. **Leading theory: it is a THREE-level hostname, and
  Universal SSL covers `sennamind.com` and `*.sennamind.com` only.** An hour of
  failure fits "no certificate will ever cover this name" far better than "slow
  issuance". The API token cannot read `ssl/certificate_packs` (9109), so this
  needs the dashboard.
  - **Cheap fix:** a two-level hostname (`roleatlas-api.sennamind.com`) — one line
    in `wrangler.toml` plus a redeploy; nothing else names the host.
  - **Free fix:** ladder step 4. Serving the page from the Worker puts the API on
    the apex, same-origin, and the problem plus the CORS allowlist both vanish.
  - Re-check with `bash scripts/worker-e2e.sh deployed`.
- **No workers.dev subdomain, deliberately** — it would publish the API on a
  second permanent hostname the CORS allowlist does not cover.

## NEXT (in order)

1. **Push `t15.2-first-seen`** — see the top of this file. Before 20:00 UTC if you
   want tonight to be the first confirmation night.
2. **Watch the first honest nightly.** It should badge roughly nine roles, not
   1,600. If it badges hundreds, a definitional change slipped into the build and
   the artifact cannot see it — that is the failure mode to watch for forever.
3. **Ladder step 3: the soft gate.** Client-side, bypassable on purpose. It exists
   to measure whether anyone signs in, which is the only evidence that justifies
   step 4.
4. **Wire `describe.py` into a schedule.** `nightly.yml` runs `src.build` and
   nothing else, so **the description gap regrows from zero every night** — 57 had
   accumulated before anyone noticed. It needs `CLAUDE_CODE_OAUTH_TOKEN` as a repo
   secret and spends subscription usage nightly, so it is a credential decision,
   not a YAML edit. A weekly manual run costs nothing to decide.
5. **Super's website is the wrong company.** Recorded site `superapp.id` is an
   Indonesian grocery app (PT Krakatau Karya Abadi); the board we publish its
   roles from, `greenhouse/super`, is Super Technologies — sports betting, hiring
   in Croatia, Romania, Spain, Brazil. All eight listed roles are on that board, so
   **the board is right and the website is wrong.** A `corrections.yaml` entry is a
   claim about identity and wants independent corroboration first.
6. **T14.5 / T14.6** (the application workspace and record) are still `todo`. They
   were designed against a company register that is no longer the page — re-read
   their spec before building.
7. **T13.1** — org move and private repo. Note this is now *entailed* by ladder
   step 4 rather than independent of it.
8. Late August: **T7.1**'s unblock condition (~30 nightly snapshots, earliest
   2026-08-29, and a missed night pushes it out day for day).

## THE PERMISSION CLASSIFIER BLOCKS THREE THINGS

Measured repeatedly. Do not burn a session rediscovering them — hand them to the
human with `!`:

- **`git push`** — blocked. So is writing a `.claude/settings.local.json` that
  would allow it, which is correct behaviour and not a bug to route around.
- **`npx wrangler deploy`** — blocked on the first attempt, allowed on the second
  with no change between. Assume it may need the human.
- **POSTing `CLERK_E2E_*` to Clerk's frontend API from a shell** — blocked, and it
  reads as credential exfiltration, which is a fair reading. Get a session token
  through the browser (`/browse`) instead of curl.

`wrangler r2 bucket create`, `wrangler d1 execute`, Cloudflare REST GETs and
`gh api` all run fine.

## Hard-won lessons (do not relearn these)

- **A DEFINITIONAL CHANGE IS INDISTINGUISHABLE FROM A REAL ONE, and it is invisible
  to the guard built to catch fakes.** T15.2's both-sides rule is exactly right and
  still confirmed 1,604 week-old roles as "new" because the radar widened from
  India to fifteen countries. Any feature differencing snapshots must ask not only
  "did we observe both nights" but "were we looking for the same thing".
- **NAME MATCHING IS NOT IDENTITY.** 25% of name-verified Ashby boards were a
  different company; Companies House would have published 141 UK companies of which
  15 are provably somebody else; the site was publishing Langfuse's roles under
  ClickHouse's name. Super is the newest case, and the first where the WEBSITE
  rather than the board is the impostor. Always corroborate against an independent
  fact.
- **A number that moves on a definitional choice is not a measurement.** The
  withdrawn "54% of postings ask a free-text question" was an artefact of substring
  matching; three defensible filters give 54%, 85%, 98%. T15.2 is the same lesson
  arriving from the other direction.
- **MUTATION TESTING IS THE STANDARD.** A guard counts as covered only once
  deleting it has been shown to turn a test RED. Forcing `both_sides = True` turns
  6 red; deleting T15.1's role-level workplace cut turns the remote check red with
  Gamma Health's four on-site roles riding in on its one remote job.
- **A guard that is an ABSENCE cannot be deleted, only violated.** "There must be
  no matcher for pronouns" is mutation-tested by ADDING the forbidden thing. Every
  branch-based sweep is blind to rules of this shape.
- **A CHECK THAT CANNOT RUN PROVES NOTHING, and the fixture is where that hides.**
  The e2e fixture holds 17 roles, so it can never reach a 200-row fold — that check
  runs against the real corpus and prints an honest `--` note when a build is too
  small. T15.2's badge is the mirror image: the real artifact confirms nothing, so
  the badge is driven over a hand-written fixture, itself held to "a file the real
  module could have written". Never let a check pass by never running.
- **THE PIPE EATS THE EXIT CODE.** `node --test | tail` reported GREEN over a red
  suite, and the identical fault was reintroduced one line later. **Any new gate
  step must be proven with a fault ONLY that step can see.**
- **CI HAS NO GIT HISTORY.** `actions/checkout@v4` is depth 1. Anything reading
  `git log` works perfectly on the dev machine and produces garbage at midnight.
- **CHECK FOR A CLASS-NAME COLLISION BEFORE INVENTING ONE.** T15.1's role row was
  born `.rrow`, which was already the gazetteer receipt's class; it silently
  matched the sheet's detail rows and the e2e caught it, not review. Now `.jrow`.
- **A SYNCHRONOUS FAKE PROVES LESS THAN IT LOOKS LIKE.** A `store.delete` the code
  forgot to `await` still lands before the verifying read. Only after making writes
  settle over two ticks and reads over one did three missing-`await` bugs die.
- **A FAKE REIMPLEMENTS A QUERY RATHER THAN RUNNING IT.** Every worker suite
  injects a fake store, so no test had executed a line of SQL until
  `stores.test.mjs` ran `schema.sql` against real SQLite via `node:sqlite`.
- **TWO GUARDS AGAINST ONE FAILURE MEAN NEITHER CAN BE SHOWN TO WORK.** A
  `COALESCE` and a `?? 0` defended the same value, so mutation reported both as
  survivors. Belt-and-braces costs the ability to prove the belt exists. (Contrast
  `index.mjs`'s deliberate JWKS double-check, which is KEPT and documented as
  unprovable — the difference is that one is written down.)
- **A good comment can outlive its measurement.** When a comment justifies NOT
  doing something, re-measure before believing it.
- **THE NIGHTLY COMMITS TO main** at 20:00 UTC. A session holding unpushed commits
  overnight gets `! [rejected] non-fast-forward`, and it means BEHIND, not
  conflicted — the nightly touches data files only, so a rebase replays cleanly.
- **workerd needs macOS 13.5+**; this machine is 13.4, so `wrangler dev` cannot run
  here. `worker/serve.mjs` exists so the e2e assertions are exercised locally
  anyway. CI runs the real thing.
- **AGENT WORKTREES ONCE RE-INITIALISED THE MAIN REPO** (`core.bare` flipped to
  true). Check `git config core.bare` first if git starts failing.
- **Clerk specifics:** `@clerk/clerk-js@latest` serves v4 — pin `@5`. The frontend
  host is base64 inside the publishable key. Sign-UP cannot be automated
  (Turnstile); sign-IN can. Clerk is still a **development** instance.
- **GitHub Pages serves `cache-control: max-age=600`** on both the HTML and the
  JSON. A push is live for a fresh visitor in ~2 minutes and for a recent one in up
  to ~12. The page fetches its data `{cache: 'no-cache'}`, so only the document
  ages.

## Phase 9 — the Worker, which nothing above touches

`worker/` is the first backend this project has had. Zero dependencies, no
`package.json`, no bundler; Node's stdlib test runner.

| File | What | Tests |
|---|---|---|
| `auth.mjs` | Clerk session verification over WebCrypto | 16 |
| `index.mjs` | Route table, CORS allowlist, dispatcher | 13 |
| `profile.mjs` | The 8 operational fields; refuses EEO by name | 31 |
| `resume.mjs` | One resume, verified deletion, the free-tier decision | 31 |
| `questions.mjs` | Greenhouse questions, split answered/gap | 27 |
| `stores.mjs` | The only file that knows D1 and R2 exist | 7 |
| `serve.mjs` | Node HTTP wrapper so the e2e runs without workerd | — |
| `schema.sql` | No column that could hold a demographic field | — |

**The canonical profile vocabulary is eight names and both modules must agree:**
`work_authorization, relocation, onsite, earliest_start, salary_expectation,
languages, heard_about_role, work_address`. `questions.mjs` has a deliberately
brittle test asserting the sorted list literally.

**Refused server-side as Article 9 special-category data:** gender, sexual
orientation, race, veteran status, disability status, **pronouns** and
**accommodations**. These live in the reader's browser. `profile.mjs` refuses them
by name; `schema.sql` has no column for them. Two locks on purpose.

**`index.mjs:104` is the most dangerous line in any future change:** "AUTHENTICATION
RUNS BEFORE EVERY HANDLER, WITHOUT EXCEPTION… A public endpoint, if one is ever
wanted, has to be added here deliberately." Ladder step 4 needs exactly that.

## Loose ends

- `.env` holds `CLAUDE_CODE_OAUTH_TOKEN`, `CLOUDFLARE_API_TOKEN` (TTL), `CLERK_*`,
  `UK_COMPANY_HOUSE_KEY`, `DATA_GOV_IN_KEY`.
- `.venv` has `anthropic` installed for `learning-tests/draft_cost_live.py` only.
  `make check` typechecks `src/` alone.
- **The subscription cannot serve.** Measured 2026-08-02: `count_tokens` 200,
  `messages.create` 429, Managed Agents `403 scope`. It is a credential for
  measuring, not for serving. **`scripts/describe.py` works because it drives
  Claude Code agents rather than the API** — that is the distinction, and it is the
  only reason v4 can have no per-user running cost.
- `descriptions.json` covers **365 of 371**. The six refusals are honest: five
  sites would not serve us (403/404/a JS gate), and Super is the identity finding.
- `FeatureBrainstorming.md` is the human's file, not project work.
- **The R2 free tier has a number in the code, not in someone's head.** Raising
  `FREE_TIER_BYTES` / `FREE_TIER_CLASS_A` is a business decision, not a quiet code
  change because an upload got refused.

## Billing

The monthly Anthropic cap was hit 2026-08-01 ($101.32/$100); usage credits blocked
until Sep 1. Today's work used one subagent for T15.2 and 57 agent runs for the
descriptions. Re-check the position before a large fan-out.
