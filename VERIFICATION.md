# VERIFICATION — INDIA·RADAR

The back-pressure harness. Designed before implementation, per Step 4.

**The gate is the brake. The Ralph loop is only as safe as the thing that stops it.**

---

## The single command

```
make check
```

Runs four layers, cheapest first, stopping at the first failure:

| # | Layer | Invoked by | Runs where | Typical cost |
|---|---|---|---|---|
| 1 | lint | `ruff check .` | local + CI | <1s |
| 2 | typecheck | `mypy src/` | local + CI | ~2s |
| 3 | unit | `pytest tests/ -q` | local + CI | seconds |
| 4 | e2e | `scripts/e2e.sh` (drives the running site) | **local only** | ~20s |

`make check` is the whole gate. The Stop hook calls it, the pre-commit hook calls
it, `ralph.sh` calls it. There is exactly one definition of "green" and everything
defers to it.

### Why e2e is local-only

E2E drives a real browser via `gstack browse`, which is already installed on this
machine and needs no project dependency. GitHub Actions has no such binary, so CI
runs layers 1–3 only.

This is a deliberate split, not an oversight. CI's job here is to run the **data
pipeline** (Greenhouse nightly, Ashby weekly) — it is not the correctness gate.
The correctness gate runs beside the Ralph loop, locally, which is where code is
actually being written.

`# ponytail: browse for e2e instead of a project-local Playwright install. Ceiling:`
`# e2e can't run in CI. Upgrade path: pip install playwright + a headless runner`
`# in the workflow, if CI-side e2e ever becomes necessary.`

---

## Layer 4 in detail — driving the running app

Push as much as possible into deterministic checks. Most of what feels
"subjective" about this site is not.

### 4a. console-clean
Load the site, assert **zero** console errors, zero unhandled rejections, zero
failed network requests. Catches "looks fine, secretly broken" — the most common
way a static site rots.

```
browse goto file://./site/index.html
browse console --errors      -> must be empty
browse network               -> no non-2xx
```

### 4b. behavioural
Drive the running app and assert on rendered state, not on the DOM in a vacuum.

- Filter to "Bengaluru" → every visible row has a Bengaluru role; a company whose
  only role is in Warsaw never appears.
- Click a row → roles, apply links and badges render.
- Ramping filter → only `ramping` companies; `insufficient-history` companies show
  **no sparkline** rather than a flat line.
- Snapshot date is visible on the page.

### 4c. visual regression
Screenshot key states, diff against committed baselines. First run establishes
baselines; a human approves them once.

States worth baselining: empty result set, a row with every badge present, a row
with **none** (no salary, no CIN, no trend — the degraded case that must still
look deliberate), mobile width.

### 4d. accessibility
Axe/a11y snapshot on the main view. Fail on violations. This is basics — keyboard
reachability of filters, contrast, labelled controls — not an audit.

---

## Deterministic code-quality signals

Folded into the gate so craft is enforceable without a human:

- **Dead code / unused exports** — `ruff` (F401 unused imports, F841 unused
  locals) plus a periodic `vulture` pass for unreachable functions. The Ralph loop
  generates a lot of code with no continuous human taste holding it coherent;
  scaffolding left behind is the predictable failure.
- **Duplication** — flag copy-pasted blocks above a threshold. Three near-identical
  ATS probes are the obvious risk, and the honest answer there may well be that the
  duplication is correct (the three APIs genuinely differ) — the check exists to
  force that judgment, not to auto-refactor.
- **Size / complexity threshold** — fail on functions past a line count or
  branch-complexity bound. A 200-line `build()` is how this project would actually
  degrade.

Reserve subjective craft review (abstraction fit, naming, "reads like the
codebase") for the on-demand reviewer in Step 7.5. Not every commit.

---

## Project-specific invariants the gate MUST enforce

These are this project's real failure modes, learned the hard way. A generic gate
would miss every one.

**1. A zero is never ambiguous.**
`test_unchecked_never_listed` — a company that was never successfully checked must
be excluded and counted, never rendered as "not hiring". This is the single most
important assertion in the suite; violating it makes the site quietly lie.

**2. `In-Office` is not India.**
`test_location_fixture_exact` — the location fixture contains the real traps
(`In-Office`, `Hybrid; In-Office`, `IN-Pune`, `Bengaluru, India; Mumbai, India`)
and demands zero false positives *and* zero false negatives. A case-insensitive
regex once flagged San Francisco roles as India and reported success.

**3. A 200-with-empty-array is not zero roles.**
`test_empty_array_is_unverified_not_zero` — Lever's silent failure mode.

**4. A probe-failed snapshot contributes no trend point.**
`test_probe_failed_snapshot_contributes_no_point` — otherwise every Ashby 502
manufactures a phantom hiring collapse.

**5. A wrong CIN is worse than no CIN.**
`test_20_known_pairs_zero_false_positives` — publishing someone else's company
registration is a real-world error, not a cosmetic one.

**6. A failed run never clobbers good data.**
`test_partial_run_leaves_published_json_intact`.

---

## init.sh

Boots the dev environment and runs a smoke test:

1. Create `.venv` if absent; install `ruff`, `mypy`, `pytest`.
2. Verify `.env` has `DATA_GOV_IN_KEY` (warn, don't fail — MCA is enrichment and
   must degrade).
3. Verify `browse` is available (warn if not; e2e will skip).
4. **Smoke test:** run the pipeline in `--smoke` mode over a handful of fixture
   companies and assert `data/companies.json` is produced and schema-valid.
5. Print what's ready and what's missing.

`./init.sh` must be safe to run repeatedly.

---

## Deterministic vs LLM evaluator

**Deterministic (everything above).** All six invariants, all four e2e layers,
all code-quality signals. This is the overwhelming majority and it is where effort
belongs.

**Genuinely needs an LLM evaluator (Step 7, only if reached):** exactly one thing
— *"does this site feel trustworthy and worth returning to?"* Visual hierarchy,
whether the degraded row (no salary, no CIN, no trend) reads as deliberate rather
than broken, whether the trend sparkline communicates what it claims. No
deterministic check can judge that, and no deterministic check should try.

---

## Deliberately NOT verified at this stage

Naming these so the gaps are decisions, not accidents:

- **Live third-party API contracts in the gate.** `make check` must not depend on
  Greenhouse/Ashby/data.gov.in being up — we watched data.gov.in 502 mid-session.
  Contract drift is covered by `learning-tests/`, re-run on demand, not on every commit.
- **Full-corpus builds in the gate.** The gate runs against fixtures. A real build
  is hours (Ashby alone is ~4.7h/1,000). Gating on that would make the loop useless.
- **Cross-browser testing.** One engine. It's a static table.
- **Load/performance testing.** It's a static JSON file on GitHub Pages.
- **Scraper resilience to source redesigns.** They will break; they'll break loudly
  in the nightly run and get fixed then. Pre-verifying against hypothetical
  redesigns is unbuildable.

Adding any of these now would be over-engineering for where we are.

---

## Order of enforcement

1. `make check` exists and runs today and is **GREEN**, because nothing is broken
   yet. Green means "everything that exists, works" — it does **not** mean the
   project is done. Completion is tracked by `TASKS.md`, never by holding the gate
   red.

   This was a corrected mistake. The gate was originally left permanently red
   (e2e failed because `site/index.html` doesn't exist until T5.2, the eighth
   task). Since the Stop hook enforces the full gate, that would have made every
   Ralph iteration unable to stop — and the obvious "fix" available to a stuck
   agent is to weaken the e2e check, which is exactly what the gate exists to
   prevent. A gate that cannot go green does not create back-pressure; it creates
   an incentive to defeat it. e2e now SKIPS when there is no site to verify.
2. Each task in `TASKS.md` turns its own checks green as it lands. The honesty
   guarantee is `strict=True` xfail in `tests/test_invariants.py`: an invariant
   that starts passing by accident **fails the build**, so nobody can quietly
   satisfy a check they didn't implement.
3. Only once the gate has **caught at least one real failure** does the loop earn
   the right to run unattended (`ralph.sh --auto`).

The loop runs in a **separate shell / tmux**, never in the interactive session,
teeing to `logs/` so progress is monitored from here by tailing the log.
