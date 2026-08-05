# REBUILD — prompt for the next session

> Paste as the first message: **"Read REBUILD.md and continue from NEXT."**
> Written 2026-08-05 at the end of the design-harness session, as its structured
> handoff. Everything below was verified in that session, with dates.

## The mission, in the founder's words

Rewrite the job-search product as a new app in **`sennamind/next-fastest-car`**,
in the language of the assistant's choice (decided: **TypeScript, Vite, zero
framework**), from the best judged design, hosted somewhere **better and safer**
than the current ungated GitHub Pages (decided: **Cloudflare Workers static
assets**, preview on workers.dev first). Ensure the flow of finding a job is
**faster than the live site** and prove it: compare every flow of
https://roleatlas.sennamind.com/site/index.html against the new app, timed.
Don't stop until done. The founder verifies at each stage via Claude Code.

The founder is **dogfooding** — they are a job seeker. Seven-problem roadmap,
built one at a time: (1) find the next rocketship ← ONLY this now; (2) track
applications; (3) fill forms; (4) tailor resume; (5) cover letters; (6) "why
this company"; (7) referrals/cold email/agent-applies-and-watches-inbox.

## What to build from — all committed on `harness/loving-portal` in THIS repo

The design was found by a 5-round, 15-variant generator/judge harness (article:
Anthropic harness-design). **Winner: `design/iterations/r05-a/` at 66/70.**
Target was 68–69; the judge ruled the missing points are not design:

1. **Descriptions backfill** (~1–1.5 pts): 418 of 789 companies lack
   WHAT/FOR WHOM/WHY THEM. Fix = `scripts/describe.py` (drives Claude Code
   agents — the API cannot serve on this subscription, measured 2026-08-02).
2. **Graft merge onto r05-a** (~0.5–1 pts), the judge's named list:
   - from r05-c: the **comparison plate** as the shortlist's expanded state
     (two kept companies align into A-or-B rows); the **link-arrival doctrine**
     verbatim ("Arrived in the link you opened — you have not kept it"); the
     **copy-preview** (textarea showing exactly what will be copied).
   - from r05-b: the **RATE row** (`300 ÷ 98 = one opening per 3.1 people`,
     printed as arithmetic, never a score); per-cut provenance line.
   - sticky controls.

Read in order: `design/rounds/r05-verdict.md` → `design/iterations/r05-a/`
(NOTES.md, JUDGE.md, build.py, page.html, qa/) → `design/PRODUCT-1.md` (spec +
measures M1–M6) → `design/rounds/r05-brief.md` (the founder's four calibration
signals) → `design/STRATEGY.md`, `design/ROCKETSHIP.md`, `design/FINDINGS.md`
→ `design/PLATFORM.md` (committed `2b4399c` — summary below, detail there).

## The founder's calibration — binds every future round; founder outranks judge

1. **WHAT / FOR WHOM / WHY THEM on the collapsed card.** Data:
   `design/fixture-v2/descriptions.json` (371/789, fields `what, for_whom,
   why_them, ai, checked`). The 418 absent get a designed honest state
   ("not yet read"), never invented prose.
2. **Status un-editorialized in either direction.** The founder LIKES a young
   public company (Airbnb). "Public — per YC ↗" in plain ink. No red chips, no
   "not a bet on one" (the judge praised that line; the founder overruled it).
   r05-c made this structural: **red belongs exclusively to the reader's own
   record**, so a fact cannot be red. Keep that rule.
3. **Target 68–69** on the product rubric (ease 25 · curation-legibility 25 ·
   representation 20; anchor: faultless-no-POV = 62).
4. **The baseline is the live site and the founder likes it.** Swiss grammar:
   `#fff/#111/#8a8a8a/#d5d5d5/#E30613`, Inter, tabular-nums, 11px/0.11em
   uppercase micro-labels, hairline vs 2px structural rules, crop marks,
   twelve columns at 78rem. The new app must read as MORE authored than
   roleatlas.sennamind.com, not less.

Permanent doctrine: absence stays absence; every claim cites its source;
**`applied` never comes from a click handler** (two-hands: the page's hand vs
the reader's word); all 789 render; every card states its credential with a
receipt link; `hide the giants` (<100 open roles) ships ON with off obvious.
Founder's gate: ten applications in one sitting, ≥6 to companies they'd never
heard of (eng+SF top ten should read Astranis · Replit · Mercor · MatX …).

## Data — exact state

- **`design/fixture-v2/`** (committed): schema-11 world build, **789 companies,
  27,689 roles**, all countries. `cards.json` (459KB, first paint),
  `companies.json` (12MB), per-company role shards pattern in r05-a's build,
  `descriptions.json`, `first-seen.json`. Enrichment (`stage`, `yc` block with
  batch/status/team_size/top_company) added by `design/fixture2.py` — source
  dir is argv[1]; regeneration recipe in its header comment.
- **Live site data is DIFFERENT**: schema 10, 15 countries, ~380 companies /
  6,529 roles. Main's `src/build.py` is still `SCHEMA_VERSION = 10`; schema 11
  exists on `harness/loving-portal` AND duplicated on `t16.1-rest-of-world`
  (the ralph loop's branch — same work, different SHAs; merging both
  conflicts). The nightly (20:00 UTC) writes only
  `data/{companies,build-report,first-seen}.json` and never touches `design/`.
- Known data bugs to carry: department taxonomy is a renderer's stopgap (use
  r04-c's, do NOT write a sixth); 2 of 20 TechCrunch amounts disagree with
  their linked headlines; `hire_from_abroad` unknown on 93%.

## Access — verified 2026-08-05

| Thing | State |
|---|---|
| `sennamind/next-fastest-car` | exists, PRIVATE, **gh account has ADMIN**, empty (README only) |
| gh CLI | authed as `chandrameenamohan`, scopes incl. `repo, workflow`; can read/trigger runs |
| Cloudflare | token in `.env` LIVE (`npx wrangler whoami` works); zone `sennamind.com` ACTIVE; D1 `roleatlas`, R2 `roleatlas-resumes`, worker `roleatlas-api` deployed |
| `git push` | **blocked by permission classifier** — the founder grants a scoped rule (below) or runs pushes with `!` |
| Pages | LEGACY mode: **a push to india-radar `main` IS a production deploy, ungated by CI** — never push that repo's main |
| Claude API | subscription cannot serve (`messages.create` 429) — agent-driving only |

**The push plan the founder approved discussing:** clone to
`/Users/ralph/sennamind/next-fastest-car` (separate tree — the ralph loop
switches branches in india-radar and once wiped `design/` mid-round), always
push via `git -C /Users/ralph/sennamind/next-fastest-car push`, and the founder
adds allow rule `Bash(git -C /Users/ralph/sennamind/next-fastest-car push:*)`
via `/permissions`. **If the rule isn't there yet, ask the founder to add it
(or push with `!`) — do not weaken anything, do not use gh-api writes to route
around the block.** Repo secrets (founder's call, not yet set):
`CLOUDFLARE_API_TOKEN` (CI preview deploys) and `CLAUDE_CODE_OAUTH_TOKEN`
(claude-code-action reviews every PR = "founder's Claude verifies each stage").

## Platform — decided, with the numbers (full detail: `design/PLATFORM.md`)

**Stay all-in on Cloudflare.** At 10k users the whole Cloudflare footprint is
~\$2,400/mo against ~\$210,000/mo of Claude tokens — infrastructure is ~1% of
variable cost, so the host is chosen on what is already built and provisioned
(Worker, D1, R2, live token, active zone). Everything problems 3–7 need is GA
after Agents Week 2026 **except the Agents SDK (preview — v1 must not touch
it)**; Workflows + a plain Durable Object does the same job at GA. Vercel's
sandbox measured 60% more on the same workload; eve would import Next.js into
a project that has refused every dependency. Managed Agents is a runtime a
Worker could call later, not a competing host — and is 403 on this account.

What v1 must not foreclose — **~100 lines, build them into the scaffold**:
- `llm` module doing plain `fetch` against `/v1/messages`, no vendor SDK;
- ONE tool-function array that the future MCP server, the Claude `tools`
  parameter, a Managed Agents custom tool, and the page's own filters all
  read from;
- user state keyed on the **company**, not the posting (already doctrine);
- **meter token spend from the first line of code** — the cost wall is real:
  "apply to 100 companies" ≈ \$21 of tokens per user per weekend at Sonnet
  rates vs \$15–30/**month** willingness to pay. Negative gross margin on the
  flagship feature; the structural answer is charge for the referral.

Roadmap-changing findings:
- **Problem 3 is two products.** Ashby + Lever (about half the register)
  publish no application API; Greenhouse's sanctioned submit endpoint uses the
  **employer's** key. Sanctioned auto-apply therefore runs through registered
  employer partners — the same shape as referrals — and browser-assist with a
  human pressing submit covers the rest. "Nothing auto-submitted" is the
  ToS-safe path, the cheap path, and the brand at once.
- **MCP inverts the economics.** The corpus as a remote MCP server on a Worker
  is ~\$0 marginal and the caller's subscription pays for the reasoning — the
  only roadmap item whose unit economics improve with scale. Build after
  feature 1 and after the hosting move.
- **Problem 7's email watching: never full inbox OAuth.** A dedicated `+tag`
  alias via Cloudflare Email Routing (free, GA) sees replies to our own
  applications and nothing else — the only version consistent with a schema
  that has no column for Article 9 data.
- Unproven and wants a half-day experiment before problem 3 is scheduled:
  whether Browser Run can drive a Greenhouse form end-to-end past CAPTCHA and
  file upload. Greenhouse ToS pages 404'd — exposure lives in per-employer
  career-page terms, not a quotable clause.
- `api.roleatlas.sennamind.com` TLS still failed 2026-08-05 — HLD-v5's
  hosting-move finding now has a day of evidence; the new app's two-level
  domain (e.g. `next.sennamind.com`) is covered by Universal SSL.

## Verification — how this project knows things

The harness's QA pattern is proven; reuse it: **private headless Chrome over
CDP** (never the shared /browse daemon — agents steal each other's tabs; never
mcp__claude-in-chrome__*), real input events, Fast-3G by protocol, **CDP device
metrics for <500px** (headless --window-size clamps at 500 → phantom overflow),
reproducible `qa/measure.mjs` scripts per variant. Measures **M1–M6** are in
`design/PRODUCT-1.md` §6. Round-4/5 lesson: self-reports ran conservative but
the judge caught real bugs by re-measuring (r05-b writes keeps into a
stranger's storage from a shared link — do not inherit that; r05-a is the
reference for the day-gated ask). Two dual-renderer drift bugs were caught by
a Python↔JS byte-cross-check — in the TS rewrite, ONE renderer, so the class
dies. The deliverable comparison: **`FLOWS.md`** — every ROLE·ATLAS flow vs the
new app, timed on both running sites (first role visible · search · filter →
shortlist · evidence check · keep · share · return visit); where the old site
lacks a flow, record "absent", not a time.

## Operational traps (each cost real time once)

- Spend/session limits killed agents mid-flight 3×: **commit early and often**,
  back up `design/` equivalents outside the repo, write briefs so a successor
  can resume ("inventory partial work, keep what's sound, say which").
- Check `git branch --show-current` **immediately before every commit** in
  india-radar (loop switches branches); the new repo's separate clone avoids
  this entirely.
- india-radar's pre-commit gate lints the WHOLE tree (`.venv/bin/python -m
  ruff check`, C901≤10, E501≤100) — in-flight agent files block everyone's
  commits; keep helpers lint-clean as they go. Give next-fastest-car its own
  gate from day one.
- Ports: 8731/8788 = india-radar test gates; 8732 = gallery; rounds used
  8741-3/8841-3; judge 8761. Variants' serve.py falls back if held.
- An idle notification is not a report — brief every agent to SEND its final
  report, and prod it if it goes idle silent.

## NEXT, in order — items 1–6 DONE 2026-08-05 (session after this file was written)

1. ~~Push rule~~ — CONFIRMED working (`git -C /Users/ralph/sennamind/next-fastest-car push`).
2. ~~Clone~~ — exists at `/Users/ralph/sennamind/next-fastest-car`, on `main`.
3. ~~Scaffold~~ — DONE, commit `6f91e58`: TS + Vite, zero framework (deps:
   typescript/vite/tsx only). ONE renderer (`src/render.ts` shared by the
   build-time fold inliner and the browser — the Python/JS drift class is
   dead). `src/fold.ts` verified **byte-identical** to r05-a's committed
   data/index.json (meta + all 789 records) except the judge's requested CB
   caption variation (89 cards, cbi & <20 roles). Whole graft list applied
   and measured green: plate at 2+ keeps, link-arrival (storage EMPTY after
   opening a 3-keep link), copy-preview, RATE row, per-cut provenance, sticky
   controls, paint-safe `__firstCardPainted` (harness reads 647ms now), no
   per-card backfill stamp. M1 649ms median local / 1,406ms on live
   workers.dev (Fast 3G); M3 4.2s/5 clicks; M4–M6 PASS (`qa/measures.mjs`).
4. ~~CI~~ — DONE, green on first run: build + tsc + node:test gate + measures
   + perf on ubuntu Chrome. Deploy job guarded on `CLOUDFLARE_API_TOKEN`
   secret (not yet set — founder's call, along with
   `CLAUDE_CODE_OAUTH_TOKEN` for claude-code-action; neither is added yet).
5. ~~Deploy~~ — LIVE: **https://next-fastest-car.sennamind.workers.dev**
   (assets-only Worker). Had to register the account's workers.dev subdomain
   (`sennamind`) via API — none existed. roleatlas.sennamind.com untouched.
   Custom domain still awaits the founder's word.
6. ~~FLOWS.md~~ — DONE, in the new repo (`qa/flows.mjs` reproduces it): first
   actionable thing 5,699ms (old) vs 1,406ms (new) on Fast 3G; keep/share/
   return-visit are sign-in-gated or absent on old, 295ms / URL-carried /
   139ms on new. No fresh judge round run — the verdict already said 66→68 is
   backfill + grafts, not another generation round; the grafts now ship.
7. Descriptions backfill (418 companies) via `scripts/describe.py` — needs the
   founder's OK to spend subscription usage.
8. Put it in front of the founder for the **ten-application weekend** — their
   stall points are the next brief. Decisions still open for them: default
   732 vs 789 · plate-as-head vs expanded strip · Bay Area vs SF proper ·
   whether the live site's chart band gets a descendant · whether the new
   app ever grows the old site's name search (FLOWS.md names the refusal) ·
   repo secrets (step 4) · custom domain (step 5).

Memory files exist for the sharpest traps (`pages-deploy-is-ungated`,
`ralph-loop-switches-branches`, `headless-chrome-min-width-500`). The full
story is in this repo's `design/` directory and the git log of
`harness/loving-portal` — commit messages are narrative and were written to be
read.
