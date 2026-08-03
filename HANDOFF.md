# HANDOFF — ROLE·ATLAS session continuation

> Paste this file as the first prompt of a new session:
> "Read HANDOFF.md and continue from where it says NEXT."

## HOW TO WORK THIS SESSION

**Use a team of agents.** The manager+subagent pattern is how Phase 9 was built and
it worked: three modules in parallel, each agent owning exactly two files, storage
INJECTED so no agent needed infrastructure and no agent touched `worker/index.mjs`.
Routing and reconciliation stayed with the manager. Read "Running a team" below
before spawning anything — the briefing rules there are not optional, they are
what stopped three agents colliding.

## What this project is

ROLE·ATLAS (repo `chandrameenamohan/india-radar`, local
`/Users/ralph/sennamind/next-rocket-ship`): a static site listing funded software
companies with verified open roles across 15 countries — "proven by their own job
board, not by a claim." Python pipeline (zero runtime deps) builds
`data/companies.json`; `site/index.html` renders it; GitHub Pages serves it; a
nightly Action rebuilds data. **Live at https://roleatlas.sennamind.com.**

Core doctrine everywhere: **absence stays absence** — an unchecked company is
never "not hiring", a missing fact renders as nothing, a derivation says it is
derived. v4 points this at application forms: a question we hold no fact for is a
marked GAP, and a board we cannot read says so rather than implying the form is
short.

- Tasks live in `TASKS.md` (markdown, NOT beads). House style:
  `### T<n> — Title \`status\` · *Phase N*`, then a `>` narrative note, then a
  fenced Acceptance/Checks/Out-of-scope block. Never weaken a check to pass.
- Gate: `make check` (lint → mypy → pytest → **worker** → e2e).
  `make check-fast` skips the site e2e.
- Commit style: narrative prose explaining the finding and the why, not a
  changelog. Read `git log --oneline -8`.
- **Pushes are slow** (`data/companies.json` is ~2.4MB). Use
  `timeout 480 git push origin main`.
- **PORTS: 8731 (site e2e) and 8788 (worker e2e).** Both are bound by
  `make check-fast`. Concurrent agents running the gate WILL collide — brief them
  to run `node --test 'worker/<their-file>.test.mjs'` and nothing else.

## State as of 2026-08-03

**44 tasks done. 5 unpushed commits. Working tree clean. Full gate green:
580 unit + 114 worker + 12 worker-e2e + site e2e.**

### The unpushed commits (oldest first)
```
eac16f6  v4 plans the applying version, and measures its way out of needing a model
3c952c4  T14.1: the security boundary, and two guards passing for the wrong reason
1c55a8a  The gate gets a machine that can run it, and the pipe eats the exit code twice
b707271  Phase 9 modules, built three-up, and the three bugs that only showed under review
71e6ec6  The 54% is withdrawn: three defensible filters, forty-four points apart
```

### SPEC v4 — "Applying" (the plan)
Three features: **18** the application workspace, **19** the application record,
**20** the inbox watcher. Read the `# v4 — Applying` section of `SPEC.md` in full
before touching Phase 9 — especially "The drafting slot".

**v4 CONTAINS NO LLM CALL ANYWHERE, and that is a decision rather than a gap.**
Drafting is deferred with its price on paper; resolving a pasted URL needs no
model because register-only scope means every board URL already maps to a company
in the corpus; mail classification shares the deferred slot. The consequence is
that v4 has **no per-user running cost**, which is what lets it ship before anyone
has decided how it earns.

**The human has ruled out Anthropic API spend** and wants to use the Claude Code
subscription. Measured 2026-08-02, that is not possible for serving, in all three
directions: `count_tokens` returns 200, `messages.create` returns 429, and Managed
Agents returns `403 OAuth token does not meet scope requirement`. It is a
credential for measuring, not for serving. Do not re-litigate this; the spec
already records the three funding options and that none is chosen.

### Phase 9 — what exists
`worker/` is the first backend this project has had. Zero dependencies, no
`package.json`, no bundler; Node's stdlib test runner.

| File | What | Tests |
|---|---|---|
| `auth.mjs` | Clerk session verification over WebCrypto | 16 |
| `index.mjs` | Route table, CORS allowlist, dispatcher | 13 |
| `profile.mjs` | The 8 operational fields; refuses EEO by name | 31 |
| `resume.mjs` | One resume, verified deletion | 27 |
| `questions.mjs` | Greenhouse questions, split answered/gap | 27 |
| `stores.mjs` | The only file that knows D1 and R2 exist | — |
| `serve.mjs` | Node HTTP wrapper so the e2e runs without workerd | — |
| `schema.sql` | D1 schema, no column that could hold a demographic field | — |

**The canonical profile vocabulary is eight names, and both modules must agree:**
`work_authorization, relocation, onsite, earliest_start, salary_expectation,
languages, heard_about_role, work_address`. `questions.mjs` has a deliberately
brittle test asserting the sorted list literally — if it goes red, someone renamed
a field on one side only.

**Refused server-side as Article 9 special-category data:** gender, sexual
orientation, race, veteran status, disability status, **pronouns** (they imply
gender identity) and **accommodations** (they reveal disability status). These
live in the reader's browser. `profile.mjs` refuses them by name; `schema.sql` has
no column for them. Two locks on purpose.

## PROVISIONING — done, half done, and not started

**Cloudflare account: `5bb014e16f8cf5d16a6eb4e53245be81`**
(`Chandrameenamohan@gmail.com's Account`). `.env` holds a working
`CLOUDFLARE_API_TOKEN` scoped Workers Scripts / D1 / R2 / DNS / Workers Routes.
**It has a TTL — if calls start failing with 401, check expiry first.**

- ✅ **D1 created and schema applied.** `roleatlas`, region APAC,
  `database_id = 8383daaf-b15f-4813-804b-7c4c8419eb34`, already written into
  `worker/wrangler.toml`. `num_tables: 1`.
- ⛔ **R2 NOT ENABLED on the account.** The API says
  `Please enable R2 through the Cloudflare Dashboard.` This is not a token scope —
  R2 must be switched on once in the dashboard (R2 Object Storage → Purchase R2
  Plan → add a payment method; the free tier is real, 10 GB). **A human must do
  this.** Then: `npx wrangler r2 bucket create roleatlas-resumes`.
- ⛔ **Worker NOT deployed.** Deliberately: deploying with the R2 binding
  unresolved leaves `/api/resume` broken. Deploy once R2 exists.
- ⛔ **`api.roleatlas.sennamind.com` does not exist.** Add it as a Workers
  **Custom Domain** after deploy — that creates and proxies the DNS record itself.
  Then add the hostname to `ALLOWED_ORIGINS` in `worker/index.mjs` **with a test**.
  `roleatlas.sennamind.com` stays DNS-only so GitHub keeps issuing its cert; the
  API on a different, proxied hostname does not disturb that.

**Nothing is pushed.** `git log origin/main..HEAD` lists all five commits.

## NEXT (in order)

1. **Enable R2** (human, dashboard) → `wrangler r2 bucket create roleatlas-resumes`
   → `npx wrangler deploy --config worker/wrangler.toml` → bind the custom domain
   → add the hostname to `ALLOWED_ORIGINS` with a test → run
   `bash scripts/worker-e2e.sh` against the deployed URL. **That last step is the
   first time the real Workers runtime will ever have executed this code**, because
   workerd refuses to start on this Mac (13.4; needs 13.5+).
2. **Push.** CI (`.github/workflows/check.yml`, ubuntu-latest) is the only place
   workerd runs. One unverified risk: whether `wrangler dev` boots in CI now that
   `database_id` is real. If CI goes red on the first push, that is the first
   suspect.
3. **Close T14.1–T14.4.** All four are `blocked` on nothing but deployment; their
   code is done and mutation-verified. Read each task's note before closing —
   several record findings you would otherwise rediscover.
4. **Build T14.5 (the workspace) and T14.6 (the record).** These need NO
   provisioning — every module takes its store as an argument, which is exactly
   what let three be built in parallel with none. This is the natural team-of-agents
   task and can start immediately, in parallel with step 1.
5. **T13.1** — move the repo to the `sennamind` org and make it private. Still a
   human action. **Pages does not serve a private repo on the Free plan**, so
   private may cost the live URL; the task records the whole trade-off.
6. Late August: re-check T7.1's unblock condition (needs ~30 nightly snapshots,
   earliest 2026-08-29).

## Running a team

What worked, and the brief every worker got:
- **One agent owns exactly two files** (a module and its test). Say so explicitly
  and say that touching any other file is a failure of the task. All three
  respected it.
- **Storage/fetch INJECTED, never imported.** No agent needs D1, R2 or the
  network, so all of them are testable immediately and in parallel.
- **The manager keeps routing and reconciliation.** This is where the work is.
  Three agents independently invented different names for the same eight fields
  — four of eight disagreed — which would have surfaced as the workspace rendering
  a GAP for a fact the reader had already given us.
- **Brief them to SEND a final report.** An idle notification is not a report, and
  two of three went idle without one until asked.
- **Verify on disk. Re-run their mutation sweep yourself.** Two agents' claims held;
  the value was in checking.
- **Never let them run `make check` / `check-fast`** — ports 8731 and 8788.

## Hard-won lessons (do not relearn these)

- **NAME MATCHING IS NOT IDENTITY.** 25% of name-verified Ashby boards were a
  different company; the India/MCA rule applied to Companies House would have
  published 141 UK companies of which 15 are provably somebody else; the live site
  was publishing Langfuse's roles under ClickHouse's name. Always corroborate a
  name match against an independent fact.
- **MUTATION TESTING IS THE STANDARD FOR `worker/`.** A guard counts as covered
  only once deleting it has been shown to turn a test RED. It found two guards in
  `auth.test.mjs` passing for the wrong reason on day one — every attack was being
  stopped by signature verification one step later.
- **A guard that is an ABSENCE cannot be deleted, only violated.** "There must be
  no matcher for pronouns" cannot be mutation-tested by deletion; the mutation has
  to ADD the forbidden thing. Every branch-based sweep is blind to rules of this
  shape.
- **Check your mutation tool before believing its findings.** An anchored regex
  meant single-line `if (C) return x;` guards were never mutated at all and scored
  as survivors — it reported **12 false findings** before a condition-balancing
  version reported the true zero.
- **THE PIPE EATS THE EXIT CODE.** `node --test | tail` reported GREEN over a red
  suite. Fixing it, the identical fault was reintroduced one line later with
  `worker-e2e.sh | tail | sed`. **Any new gate step must be proven with a fault
  ONLY that step can see** — every mutation that broke the e2e also broke a unit
  test, so the swallowed status stayed invisible until `exit 1` was appended to the
  script by hand.
- **A SYNCHRONOUS FAKE PROVES LESS THAN IT LOOKS LIKE.** A `store.delete` the code
  forgot to `await` still lands before the verifying read. A macrotask deferral was
  not enough — timers fire FIFO. Only after making writes settle over two ticks and
  reads over one did three missing-`await` bugs die.
- **A number that moves on a definitional choice is not a measurement.** The
  "54% of postings ask a free-text question" published in SPEC.md was an artefact
  of matching boilerplate labels by SUBSTRING — `"location"` deleted "Which office
  location would you prefer?". Three defensible filters give 54%, 85%, 98%. The
  figure is withdrawn; the qualitative claim (the recurring questions are FACTS,
  not essays) survives every filter and is what the design rests on.
- **A good comment can outlive its measurement.** When a comment justifies NOT
  doing something, re-measure before believing it.
- **workerd needs macOS 13.5+**; this machine is 13.4, so `wrangler dev` cannot
  run here. `wrangler deploy`, `d1`, `r2` are plain API calls and work fine.
  `worker/serve.mjs` exists so the e2e assertions are exercised locally anyway —
  a check whose first real run is in CI is a check nobody has tested.
- **AGENT WORKTREES ONCE RE-INITIALISED THE MAIN REPO** (`core.bare` flipped to
  true). Fixed, but check `git config core.bare` first if git starts failing.
  Three stale worktrees still exist under `.claude/worktrees/` — all merged, prune
  with `git worktree remove`.
- **Clerk specifics:** `@clerk/clerk-js@latest` serves v4 — pin `@5`. The frontend
  host is base64 inside the publishable key. Sign-UP cannot be automated
  (Turnstile); sign-IN can, which is why e2e uses one `+clerk_test` account.
  Clerk is still a **development** instance.

## Loose ends

- `.env` holds `CLAUDE_CODE_OAUTH_TOKEN`, `CLOUDFLARE_API_TOKEN` (new, scoped,
  with a TTL), `CLERK_*`, `UK_COMPANY_HOUSE_KEY`, `DATA_GOV_IN_KEY`. The OLD
  zone-only Cloudflare token was overwritten and can be revoked in the dashboard.
- `.venv` has `anthropic` installed for `learning-tests/draft_cost_live.py` only.
  The pipeline stays dependency-free — `make check` typechecks `src/` alone.
- `learning-tests/draft_cost_live.py` measured 4,755 input tokens per drafted
  application (951 cacheable, 3,804 the posting) but **output is unmeasured**: the
  subscription token 429s on completions. It needs an API key to finish, and the
  human has ruled that out.
- `FeatureBrainstorming.md` is the human's file, not project work.

## Billing

The monthly Anthropic cap was hit 2026-08-01 ($101.32/$100), usage credits blocked
until Sep 1. This session ran three concurrent subagents (~60k subagent tokens for
the modules, plus one ~60k analysis agent) — far smaller than the prior session's
~925k. Re-check the position before a large fan-out.
