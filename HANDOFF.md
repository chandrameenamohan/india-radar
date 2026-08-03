# HANDOFF — ROLE·ATLAS session continuation

> Paste this file as the first prompt of a new session:
> "Read HANDOFF.md and continue from where it says NEXT."

## HOW TO WORK THIS SESSION

**Steps 1–2 of NEXT are NOT team work — do them yourself.** A stuck TLS
certificate and one authenticated upload are a single thread of diagnosis each;
handing either to a subagent adds a briefing and removes the context that solves
it. The session that added T14.9 used no subagents at all and was right to.

**Step 4 (T14.5/T14.6) IS team work**, and the manager+subagent pattern is how
Phase 9 was built: three modules in parallel, each agent owning exactly two files,
storage INJECTED so no agent needed infrastructure and no agent touched
`worker/index.mjs`. Routing and reconciliation stayed with the manager. Read
"Running a team" below before spawning anything — the briefing rules there are not
optional, they are what stopped three agents colliding.

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
- **Pushes are slow** (`data/companies.json` is ~2.4MB) and the nightly Action
  commits to `main` while you sleep. Use
  `git pull --rebase origin main && timeout 480 git push origin main`.
  **The push itself is blocked by the permission classifier — the human has to
  run it** (`!` prefix in the prompt). See the classifier note below.
- **PORTS: 8731 (site e2e) and 8788 (worker e2e).** Both are bound by
  `make check-fast`. Concurrent agents running the gate WILL collide — brief them
  to run `node --test 'worker/<their-file>.test.mjs'` and nothing else.

## State as of 2026-08-03 (afternoon)

**45 tasks done. EVERYTHING IS PUSHED — `origin/main` is `5bf9f87`, working tree
clean. Full gate green: 580 unit + 128 worker + 12 worker-e2e + site e2e.**

**The Worker is DEPLOYED and CI IS GREEN**, which closes the two things the
previous handoff called unverified:

- **Real workerd has now executed this code.** CI run `30810998559`, step
  *worker e2e (real workerd)*: `WORKER E2E GREEN -- 12 checks`. `wrangler dev`
  boots fine with a real `database_id`, which was the standing suspect for a
  first red CI. It is not a risk any more.
- **`npx wrangler deploy` succeeded** with both bindings resolving at upload.

**The one thing still not working is TLS on the API hostname** — see PROVISIONING.

### THE PERMISSION CLASSIFIER IN THIS ENVIRONMENT BLOCKS THREE THINGS
Not opinions, measured three times each this session. Do not burn a session
rediscovering them — hand them to the human with `!` instead:
- **`git push`** — blocked. So is writing a `.claude/settings.local.json` that
  would allow it, which is correct behaviour and not a bug to route around.
- **`npx wrangler deploy`** — blocked on the first attempt, allowed on the
  second with no change in between. Assume it may need the human.
- **POSTing `CLERK_E2E_*` to Clerk's frontend API from a shell** — blocked, and
  it reads as credential exfiltration, which is a fair reading. Get a session
  token through the browser (`/browse`) instead of curl.

`wrangler r2 bucket create`, `wrangler d1 execute` and Cloudflare REST GETs all
ran without complaint.

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
| `resume.mjs` | One resume, verified deletion, **and the free-tier decision** | 31 |
| `questions.mjs` | Greenhouse questions, split answered/gap | 27 |
| `stores.mjs` | The only file that knows D1 and R2 exist; **the usage counters** | 7 |
| `serve.mjs` | Node HTTP wrapper so the e2e runs without workerd | — |
| `schema.sql` | D1 schema: `profiles`, `resume_usage`. No column that could hold a demographic field | — |

**`stores.test.mjs` is the only suite that runs SQL rather than a fake** — real
SQLite via `node:sqlite`, applying `schema.sql` verbatim. Every other suite
injects a fake that reimplements the query, which is exactly the blind spot a
feature made of SQL falls into. It is also the only thing that has ever executed
`schema.sql` outside a deploy.

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
  `worker/wrangler.toml`. `num_tables: 2` (`profiles`, `resume_usage`).
- ✅ **R2 enabled and the bucket exists.** The human enabled it in the dashboard
  2026-08-03 (it is not a token scope — R2 has to be switched on once, with a
  payment method attached); `roleatlas-resumes` created immediately after.
- ✅ **The free tier is enforced in code (T14.9), because R2 bills past it rather
  than stopping.** `resume_usage` in D1 counts stored bytes and Class A ops; an
  upload that would cross either line is refused with 507 or 429 and never
  reaches the bucket. Margins are 9 GB of 10 and 800k ops of 1M. Reads are
  deliberately uncounted — counting them costs a D1 write each, and D1's 100k
  writes/day is tighter than R2's 10M reads/month.
- ✅ **Worker deployed** 2026-08-03, version `6fb8927d`. Both bindings resolved
  at upload: `env.DB (roleatlas)`, `env.RESUMES (roleatlas-resumes)`.
- ✅ **`api.roleatlas.sennamind.com` is a Workers Custom Domain** in zone
  `sennamind.com` (`f054c1df5235c938cf2ac873d6d99c52`). Cloudflare created and
  proxied the DNS record itself; `roleatlas.sennamind.com` stays DNS-only so
  GitHub keeps issuing the register's certificate.
- ⛔ **NO TLS ON THE API HOSTNAME. This is the one open problem.** DNS resolves
  to Cloudflare and the route is live, but every request fails the handshake with
  `sslv3 alert handshake failure` — measured continuously for **an hour** after
  the deploy, not the couple of minutes a new certificate normally takes.
  **The leading theory, and where to start: `api.roleatlas.sennamind.com` is a
  THREE-level hostname, and Universal SSL covers `sennamind.com` and
  `*.sennamind.com` only — not `*.roleatlas.sennamind.com`.** An hour of failure
  fits "no certificate will ever cover this name" much better than it fits
  "issuance is slow".
  - Check first: dashboard → SSL/TLS → Edge Certificates for `sennamind.com`, and
    whether one exists for this hostname at all. The API token in `.env` CANNOT
    read `ssl/certificate_packs` (9109 Unauthorized), so this needs the dashboard
    or a wider token.
  - **The cheap fix is a two-level hostname** — `roleatlas-api.sennamind.com`,
    which Universal SSL already covers. It is one line in `worker/wrangler.toml`
    (`routes`) plus a redeploy, and nothing else in the codebase names the host.
    The alternative is paying for Total TLS / Advanced Certificate Manager, which
    is a business decision nobody has taken.
  - Re-check any time with `bash scripts/worker-e2e.sh deployed`. That runner
    exists now and takes an optional URL as its second argument.
- **No workers.dev subdomain, deliberately.** The first deploy failed asking for
  one; registering it would publish the API on a second permanent hostname the
  CORS allowlist does not cover. `workers_dev = false` and one route instead.
- **The API hostname is NOT in `ALLOWED_ORIGINS`, contrary to the older plan
  above.** An `Origin` is the page making the request, and nothing is served from
  that hostname — it answers `/api/*` with JSON and nothing else. Adding it would
  widen a security allowlist by an entry that cannot legitimately appear. It
  belongs there the day a page is served from it.

**Everything is pushed.** `origin/main` is `5bf9f87` and `git log
origin/main..HEAD` is empty.

## NEXT (in order)

1. **Get TLS working on the API** — the certificate above. Everything else about
   the deploy is done and proven; this is the only thing standing between the
   Worker and being usable from a browser. If the two-level hostname is the
   answer, it is one line in `wrangler.toml` and a redeploy.
2. **An AUTHENTICATED upload against the live API** — the check nothing has done
   yet, and the reason it matters: `resume_usage` has been proven against real
   SQLite and against a fake, but **D1, R2 and the free-tier counter have never
   been observed agreeing in production**. Sign in as the `+clerk_test` account
   through `/browse` (NOT curl — see the classifier note above), upload a resume,
   then confirm the row:
   `npx wrangler d1 execute roleatlas --remote --command "SELECT * FROM resume_usage"`
3. **Close T14.1–T14.4.** All four are `blocked` on nothing but deployment, which
   has now happened. Read each task's note before closing — several record
   findings you would otherwise rediscover.
4. **Build T14.5 (the workspace) and T14.6 (the record).** These need NO
   provisioning — every module takes its store as an argument, which is exactly
   what let three be built in parallel with none. This is the natural team-of-agents
   task and does not wait on the certificate.
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
- **A FAKE REIMPLEMENTS A QUERY RATHER THAN RUNNING IT.** Every worker suite
  injects a fake store, which is what let the modules be built with no
  infrastructure — and it means no test had ever executed a line of SQL or
  `schema.sql`. A feature whose logic lives in SQL is invisible to that whole
  arrangement. `node:sqlite` closes it in about forty lines: D1 is SQLite, and
  Node ships one.
- **TWO GUARDS AGAINST ONE FAILURE MEAN NEITHER CAN BE SHOWN TO WORK.** A
  `COALESCE` in SQL and a `?? 0` in JS both defended the same value, so the
  mutation sweep reported both as survivors — deleting either changed nothing.
  Belt-and-braces is not free: it costs the ability to prove the belt exists.
  (Contrast `index.mjs`'s deliberate JWKS double-check, which is KEPT and
  documented as unprovable. The difference is that one is written down.)
- **THE NIGHTLY ACTION COMMITS TO main.** A session that holds unpushed commits
  overnight gets `! [rejected] non-fast-forward` and it means BEHIND, not
  conflicted — the nightly touches `data/companies.json` and nothing else, so
  `git rebase origin/main` replays cleanly. Pull before pushing.
- **workerd needs macOS 13.5+**; this machine is 13.4, so `wrangler dev` cannot
  run here. `wrangler deploy`, `d1`, `r2` are plain API calls and work fine.
  `worker/serve.mjs` exists so the e2e assertions are exercised locally anyway —
  a check whose first real run is in CI is a check nobody has tested. **As of
  2026-08-03 CI has run it under real workerd and it is green**, so the local
  wrapper is now a convenience rather than the only coverage.
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
- **The R2 free tier now has a number attached to it and it is in the code**, not
  in someone's head: 9 GB of 10, 800k Class A ops of 1M, in `resume.mjs` as
  `FREE_TIER_BYTES` / `FREE_TIER_CLASS_A`. Raising them is a business decision —
  the day someone chooses to pay for R2 — and not a code change to be made
  quietly because an upload got refused.
- **Reads are uncounted by design.** If a per-user read cap is ever wanted, the
  reason it is not there is arithmetic: counting a download means a D1 write per
  read, and D1's 100k writes/day is tighter than R2's 10M reads/month.

## Billing

The monthly Anthropic cap was hit 2026-08-01 ($101.32/$100), usage credits blocked
until Sep 1. The session that built Phase 9 ran three concurrent subagents (~60k
subagent tokens) — far smaller than the prior session's ~925k. **The session that
added T14.9 and deployed used NO subagents at all**, which was right for the size
of the work: one module, one route, one table. Re-check the position before a
large fan-out; T14.5/T14.6 are the next thing that genuinely wants a team.
