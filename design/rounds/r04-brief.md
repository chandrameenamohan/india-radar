# Round 4 — the product, not the register

**This round supersedes `BRIEF.md` and `CRITERIA.md`.** Those briefed a register
and were graded on honesty and craft; nine variants optimised them perfectly and
the founder rejected all nine: *"I am not happy with the design. Do not think
that this is just a board."* The spec for this round is **`design/PRODUCT-1.md`**
and the strategy behind it is `design/STRATEGY.md` + `design/ROCKETSHIP.md`.
Read all three before writing a line.

## The founder's decisions, which are settled — do not re-litigate

1. **All 789 companies stay. Cut nothing.** A CB Insights row is not a company
   missing funding data; it is a company whose credential is "on a third party's
   tracker", sourced and linkable, beside "YC Winter 2021" and "Filed a Form D".
   Every card states its own gate. A seeker's preferred signal is unknown —
   stage, city, founder profile, backers — so the product surfaces every
   attribute it can evidence and lets the person decide.
2. **The unit is the company, not the role.** The product is a shortlist
   builder; the session's output is a handful of companies with role tabs open.
3. **The seven-problem roadmap is sequential.** This round builds problem #1
   (find the next rocketship) and leaves attachment points for #2 (tracking) —
   company-keyed keeps, witnessed opens, the "did you apply?" row. Nothing more.

## The data — fixture-v2, and it is richer than anything a prior round had

`design/fixture-v2/` — built 2026-08-04 from the world corpus plus the payloads
the pipeline fetches and previously discarded:

- **`cards.json` (459KB)** — one record per company: name, slug, ats,
  `roles_open`, role counts by normalised dept and place, amount/currency/
  round_letter/date, `stage` (667 of 789), `source_url`, `qualified_by`, and
  `yc: {batch, status, team_size, top_company}` on all 298 YC companies.
  **Load this first; it is the whole first paint.**
- **`companies.json` (~12MB)** — the full corpus with roles; every role carries
  `places` (canonical) and `dept_norm` beside the board's own strings. Fetch it
  lazily, after first paint.
- `first-seen.json`, `build-report.json`, `descriptions.json`.

Facts worth knowing: 32 YC companies are Acquired/Public/Inactive (Airbnb is
`Public`) — say so, never present them as live bets. 35 carry YC's own
`top_company` flag. Roles÷headcount is computable for the 298 (Replit: 90 open,
65 staff) — render as two stated numbers, never as a ratio-claim. The funnel is
real and belongs on the page: **10,125 read → 6,895 didn't qualify → 2,925
qualified → 789 hiring tonight.**

## The rubric — PRODUCT-1 §6, verbatim

M1 first card < 1.5s throttled · M2 a context-free viewer of a load screenshot
can answer "how did these companies get here, and who didn't make it?" · M3
three apply-tabs < 60s, ≤6 clicks, 0 navigations · M4 every hype word
(`rocketship|recently|funded|new|top|best`) has a link/date/count in the same
node · M5 null-amount companies and unknown-visa roles are neither excluded nor
rendered as no · M6 keeps survive reload; the apply question fires once.

Plus the founder's gate, which no checklist reaches: **they apply to ten
companies in one sitting, and at least six are ones they had not heard of.**
`hide the giants` is the difference.

## What is deliberately dead this round

The eight-locale i18n layer, the plates, the register-as-front-door, sign-in.
Keep the doctrine (absence stays absence; a claim states its source; `applied`
never comes from a click handler) — drop the furniture. English-only is fine
this round; the i18n architecture from r02-b is on file when it is time.
