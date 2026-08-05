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
signals) → `design/STRATEGY.md`, `design/ROCKETSHIP.md`, `design/FINDINGS.md`.
`design/PLATFORM.md` may exist (a platform-scout agent was researching agentic
hosting when the session ended — check; if absent, its brief is reproducible
from the git log).

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

## NEXT, in order

1. Confirm the push rule exists (try a trivial push to next-fastest-car; if
   blocked, ask the founder — options above).
2. Clone `sennamind/next-fastest-car` to `/Users/ralph/sennamind/next-fastest-car`.
3. Scaffold: TypeScript + Vite, zero framework; port r05-a (build → static
   HTML + vanilla TS, per-company shards) and apply the graft list; vendor
   fixture-v2 + its regeneration recipe; own lint/test gate; `qa/` harness
   with M1–M6.
4. CI: run the measures on every push; claude-code-action once the secret
   lands; wrangler preview deploy per version once that secret lands.
5. Deploy to workers.dev preview (`npx wrangler deploy` may prompt once);
   custom domain (suggest `next.sennamind.com`, two-level = Universal SSL
   covers it) only on the founder's word. **roleatlas.sennamind.com stays
   untouched.**
6. Write `FLOWS.md` (old vs new, timed). Judge the result against 68–69 with a
   fresh judge agent if useful — same rubric, same anchors.
7. Descriptions backfill (418 companies) via `scripts/describe.py` — needs the
   founder's OK to spend subscription usage.
8. Put it in front of the founder for the **ten-application weekend** — their
   stall points are the next brief. Decisions still open for them: default
   732 vs 789 · plate-as-head vs expanded strip · Bay Area vs SF proper ·
   whether the live site's chart band gets a descendant.

Memory files exist for the sharpest traps (`pages-deploy-is-ungated`,
`ralph-loop-switches-branches`, `headless-chrome-min-width-500`). The full
story is in this repo's `design/` directory and the git log of
`harness/loving-portal` — commit messages are narrative and were written to be
read.
