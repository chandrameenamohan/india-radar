# HANDOFF — ROLE·ATLAS session continuation

> Paste this file as the first prompt of a new session:
> "Read HANDOFF.md and continue from where it says NEXT."

## What this project is

ROLE·ATLAS (repo `chandrameenamohan/india-radar`, local
`/Users/ralph/sennamind/next-rocket-ship`): a static site listing funded
software companies with verified open roles across 15 countries — "proven by
their own job board, not by a claim." Python pipeline (zero runtime deps)
builds `data/companies.json`; `site/index.html` renders it; GitHub Pages
serves it at https://chandrameenamohan.github.io/india-radar/ ; a nightly
GitHub Action rebuilds data. Core doctrine everywhere: **absence stays
absence** — an unchecked company is never "not hiring", a missing fact renders
as nothing, a derivation says it is derived.

- Tasks live in `TASKS.md` (markdown, NOT beads — bd is broken here). House
  style: `### T<n> — Title \`status\`` headers, Acceptance/Checks/Out-of-scope
  DoD blocks, measured narrative notes. Never weaken a check to pass.
- Gate: `make check` (lint → mypy → pytest → `scripts/e2e.sh`, 75 e2e checks).
  KNOWN SHARP EDGE: e2e binds fixed port 8731; back-to-back runs race the
  port — re-run on "could not serve the site".
- Commit style: short narrative sentences (read `git log --oneline -10`).
  Push goes to `main`; nightly commits may land remotely — rebase, and for
  `data/*.json` conflicts prefer whichever side matches the CURRENT schema.

## State as of 2026-08-02

- **36 tasks done.** Live site has: the Swiss-atlas redesign (16 plates,
  world-map-as-navigation, per-company VERIFIED·BOARD READ stamp), 316 listed
  companies (UK 220 is the largest plate; India 115), WHAT/FOR WHOM/WHY THEM
  descriptions (`data/descriptions.json`, marked
  AI-SUMMARIZED; 2 honest omissions now that Raintank has collapsed into
  Grafana Labs: Insider and Fundamental), and
  T5.4's filter upgrades (role-title search with "MATCHES N ROLES", computed
  coverage notes on sparse RAISED/FUNDED filters, per-plate city filter,
  title-derived DEPARTMENT filter — 86.3% classified, 763 UNCLASSIFIED
  reachable, labelled "derived").
- The redesign came from a 2-run generate–evaluate harness (16 rounds total,
  judge panel of 3 structural bets, weighted score 5.5 → ~8.5). Design
  snapshots live in the session scratchpad (temp; the shipped page is the
  artifact that matters).
- **T7.1/T7.2 (trend + sparklines): blocked on calendar** — needs ~30 nightly
  snapshots; first nightly ran 2026-07-30; earliest start ~2026-08-29. Do NOT
  unblock early; TASKS.md T7.1 note has the re-check commands.
- **T9.1 (UK Companies House badge): specced, deferred** — blocked on the
  human registering a free API key at
  developer.company-information.service.gov.uk and adding it as a repo secret
  + local env.
- **T9.2 (board-stated departments) done 2026-08-02, both phases.** Phase 1
  measured 5,409 postings on 317 live boards: "no board publishes one" was wrong
  (99.6% state one, free in calls the build already makes), but the vocabulary is
  an org chart and where both speak they agree only 74% of the time. So Phase 2
  shipped narrowed — schema v9 carries the board's word per role, and the site
  reads the title first and the board ONLY where the title places nothing,
  through the same table. Live: 86.1% -> 93.8% placed, 335 still Unclassified.
- **T10.1 (one board, one company) done 2026-08-01.** 11 names left the site:
  10 pairs that read one board (the site was publishing Grafana Labs' 75 roles
  twice, under `Raintank` as well) and Next Caller, whose careers page links
  Pindrop's board since the 2021 acquisition. The collapse is derived every
  build (`build.shared_boards`, the board's own stated name picks the survivor)
  and refused again at the write; what no run can observe lives in
  `data/corrections.yaml` with its reason. 322 -> 316 listed.

## Hard-won lessons (do not relearn these)

- **Headless Chrome clamps `--window-size` to 500px minimum.** Sub-500
  "mobile" screenshots are cropped desktop layouts → phantom overflow bugs
  (this wasted ~a third of design run 1). True small viewports need CDP
  `Emulation.setDeviceMetricsOverride`. Also: `overflow-x: clip` on html/body
  makes `scrollWidth` lie. (Saved in auto-memory too.)
- Verify agents' work on disk; idle notifications are not reports. Brief every
  subagent to SEND a final report.
- A performance comparison across a behaviour change must hold work constant.

## NEXT (in order)

1. **T9.1 build** — only after the human supplies the Companies House API key.
2. **Descriptions nightly delta** — newly listed companies get no description
   until regenerated; wiring the delta into the nightly needs an
   ANTHROPIC_API_KEY repo secret (human step). Until then, a manual
   regeneration pass (6 parallel writer agents, website-verified, omit when
   unverifiable) is the pattern — see `data/descriptions.json` provenance.
   The 316-company set has churned since the last pass — new names carry no
   description, and 11 collapsed names (T10.1) now carry one nothing reads.
3. **Corpus rebuild, when something wants one** — `python -m src.corpus` is a
   manual step the nightly never runs, and it is what makes T10.1's two website
   corrections bite. Nothing is wrong on the site while it waits (both companies
   already resolve to their own boards); a rebuild also picks up companies the
   sources have added since 2026-07-29, which then need `python -m src.slugs`
   (~2.5h) before they can be checked.
4. Late August: re-check T7.1's unblock condition (snapshot count).

## Billing context (2026-08-01)

Monthly spend cap hit ($101.32/$100) — usage credits blocked until Sep 1.
$21.91 promotional credit expires Aug 9 and will be lost unless the human
raises the monthly limit. Plan (Max 5x) session/weekly limits still fine.
Prefer plan usage; keep agent fan-outs modest.
