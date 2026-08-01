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

## State as of 2026-08-01 evening (all pushed through commit `14cbfdb`)

- **34 tasks done.** Live site has: the Swiss-atlas redesign (16 plates,
  world-map-as-navigation, per-company VERIFIED·BOARD READ stamp), 322 listed
  companies (UK 224 is the largest plate; India 118), WHAT/FOR WHOM/WHY THEM
  descriptions for 319 of 322 (`data/descriptions.json`, marked
  AI-SUMMARIZED; 3 honest omissions: Raintank, Insider, Fundamental), and
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
- **T9.2 (board-stated departments): specced, deferred** — Phase 1 is a
  T8.1-style learning test with a kill criterion; can run anytime, no key
  needed.

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

1. **Corpus data-bug cleanup** (no input needed): description writers found —
   Cresta's corpus website points at analyticsinsight.net (not theirs),
   Monzo's at pre-2016 mondo.com, Raintank duplicates Grafana Labs (rename),
   Next Caller acquired by Pindrop (may not be an independent employer).
   Fix in the pipeline/corpus the honest way (counted, not silently dropped),
   gate, push.
2. **T9.2 Phase 1 measurement** (no input needed): run the learning test in
   the T9.2 spec (TASKS.md ~line 1551) against real Greenhouse/Ashby/Lever
   boards; record in learning-tests/ + FINDINGS; apply the kill criterion;
   update T9.2's status/note with the numbers.
3. **T9.1 build** — only after the human supplies the Companies House API key.
4. **Descriptions nightly delta** — newly listed companies get no description
   until regenerated; wiring the delta into the nightly needs an
   ANTHROPIC_API_KEY repo secret (human step). Until then, a manual
   regeneration pass (6 parallel writer agents, website-verified, omit when
   unverifiable) is the pattern — see `data/descriptions.json` provenance.
5. Late August: re-check T7.1's unblock condition (snapshot count).

## Billing context (2026-08-01)

Monthly spend cap hit ($101.32/$100) — usage credits blocked until Sep 1.
$21.91 promotional credit expires Aug 9 and will be lost unless the human
raises the monthly limit. Plan (Max 5x) session/weekly limits still fine.
Prefer plan usage; keep agent fan-outs modest.
