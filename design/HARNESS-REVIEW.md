# HARNESS-REVIEW — our process against Anthropic's harness-design article

Written 2026-08-04, after three register rounds, the product pivot, and the
launch of round 4. The article is
https://www.anthropic.com/engineering/harness-design-long-running-apps — this
review re-fetched it and works from the source. Every claim about our process
below is a real event in this project's history; where the article is silent on
something we did, that is said rather than stretched.

---

## 1 · What the article prescribes, in one page

The article describes building complete applications over multi-hour autonomous
runs with a **three-agent harness**:

- **Planner** — expands a 1–4 sentence user prompt into a full product spec.
  Ambitious about scope, high-level about implementation.
- **Generator** — builds incrementally, self-checks at sprint completion, uses
  git.
- **Evaluator** — drives the *running* application the way a user would
  (Playwright), grades against criteria and discovered bugs.

It exists because two failure modes kill naive single-agent runs:

- **Context degradation and anxiety** — models lose coherence as the window
  fills and start "wrapping up prematurely." The fix is context resets: fresh
  agents with structured handoffs.
- **Self-evaluation bias** — "when asked to evaluate work they've produced,
  agents tend to respond by confidently praising the work — even when, to a
  human observer, the quality is obviously mediocre." Separating the evaluator
  matters because "tuning a standalone evaluator to be skeptical turns out to
  be far more tractable than making a generator critical of its own work."

For frontend work specifically, the author ran a **generator–evaluator loop**
(5–15 iterations per generation) and made subjective quality gradable with four
criteria — design quality, originality, craft, functionality — deliberately
weighting design and originality "because Claude already scored well on craft
and functionality by default," and calibrating the evaluator with "few-shot
examples with detailed score breakdowns."

Structural practices: **sprint contracts** (generator and evaluator agree what
"done" looks like *before* code is written — Sprint 3 alone had 27 criteria);
**file-based communication** ("one agent would write a file, another agent
would read it and respond"); **evaluator tuning as load-bearing work** ("out of
the box, Claude is a poor QA agent… the tuning loop was to read the evaluator's
logs, find examples where its judgment diverged from mine, and update the QA's
prompt"); and **re-examining the harness at each model release**, because
"every component in a harness encodes an assumption about what the model can't
do on its own."

---

## 2 · Where we followed it, with receipts

| Article principle | What actually happened here |
|---|---|
| Generator ≠ evaluator | Nine variants built by generator agents; graded by separate agents that never saw the builder's reasoning. `EVALUATOR.md` opens with the article's own logic: "a generator that grades itself confidently praises mediocre work." |
| Skeptical evaluator, tuned | The instruction "your default posture is unimpressed" plus calibration anchors. It worked in the strongest sense: **r01-c's evaluator refuted its own builder** — "zero dropped frames" was measured as 30 of 265 (90 of 262 throttled); "18ms keystroke" was 48–88ms unthrottled, 369ms at 4× CPU. It also *upgraded* a builder claim: reduced-motion, self-flagged as unverified, was re-verified with real CDP emulation and found correct. |
| Grade the running page, not source | `EVALUATOR.md`: "a score derived from reading HTML is void." Enforced hard — and vindicated when r03-c found r02-c's keep notch had *never rendered on desktop* (clipped by paint containment) and r03-a found an English string that survived every key-parity check because the render was memoised. Our phrasing of the article's lesson: **grade the page, never the changelog.** |
| Weight originality over craft | The article weighted design/originality because craft comes free. Our split: ask 25 · inside 25 · originality 20 vs craft 15 · worldwide 15, with `CRITERIA.md` naming the generic tells ("centered hero, purple gradient, rounded-2xl…") that score 2/10 on sight. Zero of nine variants shipped a generic tell. |
| Calibration anchors against drift | `CRITERIA.md`: "a clean, complete, faultless page with a polite modal gate and complete translations is a **62**." That single sentence is why three rounds of scores stayed in the 54–65.5 band instead of clustering at 8/10. |
| File-based communication | The entire harness is files: `BRIEF.md` / `CRITERIA.md` / per-role standing instructions; per-variant `NOTES.md` → `JUDGE.md` / `SCORE.md`; per-round `rNN-brief.md` ← written *from* the previous `rNN-verdict.md`. Each round's brief is the previous round's evaluator output, which is exactly the article's loop at one-round granularity. |
| Context resets with structured handoff | Every generator, evaluator, and judge started fresh each round with only the files as inherited state. When the session itself switched accounts mid-project, work resumed from `design/README.md` + git log with nothing lost — the handoff pattern applied to the orchestrator itself. |
| Plateau detection / knowing when to stop | The article runs 5–15 iterations and watches scores plateau. We formalised it: round 3 carried a **stopping rule** (winner must clear 68 or the harness has found its ceiling), and the judge applied it against us — 65.5, stop, "the remaining distance belongs to the product, not another lap of the renderer." The diagnosis matched the article's plateau language: round 2 converged the variants' prose, round 3 converged their *structure*. |

One thing we did that the article practices implicitly: **the orchestrator
verified agent numbers instead of relaying them.** The 543 abroad-open roles,
the 6,413 Latin-script titles, the 4,781 no-mark count, the hide-the-giants
list — each was re-derived from the corpus before being believed. Twice that
caught something (r02-c's 4,662; my own first Latin-script count being wrong).

---

## 3 · Where we deviated deliberately, and whether it paid off

**No planner agent.** The article's planner exists to expand 1–4 sentences of
user input. We had the opposite problem — a rich repo, a 320-line `HANDOFF.md`,
an HLD — so the orchestrator planned directly. *Verdict: right call for the
input we had, with a caveat recorded in §4: the plan it produced encoded the
repo's worldview, and no agent was positioned to challenge it.*

**A single cross-variant judge for the subjective 70.** The article grades one
artifact per evaluator; comparative judging appears nowhere in it. We split the
rubric: per-variant evaluators for defects (a console error exists or it
doesn't), one judge holding all three variants for ask/inside/originality.
*Verdict: our best addition.* Every finding that changed the project's
direction required seeing variants side by side: all three keyboard cursors
warping identically; two lanes shipping the incumbent's filter bank verbatim;
round 3's structural convergence (same mechanism set, three skins) — "a tell
you cannot spot in one page is obvious when two pages share it." A per-variant
grader can never see convergence, and convergence turned out to be the ceiling
signal.

**Model diversity.** Fable for judge/strategy (ambiguous, wide-context
judgment), Opus for generators and evaluators. The article is silent on
multi-model harnesses. *Verdict: paid off on the evidence — the Fable judge's
first act was to find a factual error in the orchestrator's own brief (São
Paulo and Warsaw aren't in the corpus) and the hollow-sign-in finding — but the
planned A/B against an Opus judge died with the round-1 spend limit, so this is
a justified belief, not a measurement.*

**Persistent lanes + wildcard rotation + nothing deleted.** The article
iterates one artifact in place ("refine the current direction… or pivot"). We
ran three parallel lineages, kept all nine variants openable, and rotated the
wildcard's thesis each round. *Verdict: paid off repeatedly and measurably.*
Four of round 3's seven steal-whole items came from variants that *lost*; the
winner's only doctrine violation (calling 6,423 unconfirmed sightings "new")
was fixed by the third-place variant's clause, taken verbatim; r03-c closed
four of five measured flaws of its own lane's losing predecessor. Deleting
losers would have deleted the repairs.

**Generators self-verify before handoff.** Our `GENERATOR.md` demands the
builder drive its own page before reporting — the article's generator
"evaluates its own work at sprint completion" similarly, but ours produced a
distinctive artifact: builders' `NOTES.md` list their own weaknesses, and
r03-a *retracted its own performance claim* (20ms vs 22ms, withdrawn as noise
after interleaved re-measurement). Self-evaluation bias predicts builders
overclaim; making the self-report a falsifiable checklist for the evaluator
("the builder's self-reported weaknesses are a checklist to verify, not a
substitute") converted the bias into free test cases.

---

## 4 · Where we deviated by accident or failure, and what it cost

**The evaluator half of the loop was broken for budget — the article's core
mechanism, skipped for two rounds.** Round 1's evaluators were killed
mid-flight by a spend limit; rounds 2 and 3 skipped them to conserve. Result:
craft and worldwide — 30 of 100 points — were measured for exactly one variant
in nine. Cost: the "is 65.5 out of 70 or 100?" confusion with the founder; a
">90" target discussed on a scale that didn't exist; craft defects surfacing
late or never. For scale: in the article's updated harness, QA cost $10.39 of
a $124.70 run — **8% of budget**. We cut the 8% that closes the loop. The
belated fix (evaluating rounds retroactively) was then stopped by the pivot,
so it was never paid back.

**The environment was not pinned until it broke.** The nightly rewrote
`data/companies.json` mid-round-2 (schema 10 → 11, 6,423 → 27,689 roles) and
every variant went dark; only the judge's timing prevented three evaluators
from firing the render hard-gate against healthy pages. The article assumes a
stable environment and is silent on adversarial changes to it; the lesson we
paid for is now in `README.md`: *a score is a claim about a page AND the corpus
under it.* Relatedly, the harness shared a working tree with the ralph loop,
which switched branches at 18:41 and deleted every tracked `design/` file
mid-round-3 (restored from the object store by a generator; ~5 minutes lost, a
void measurement window, one near-miss on git-lock contention). The article's
implicit isolation assumption is real and worth making explicit in any
multi-process repo.

**The harness's own tooling had the exact bug class the harness kept finding.**
The gallery read "the first bold number" as the judge's total; round 3's judge
bolded every criterion, so the gallery named the wrong winner (r02-b at 64.5
over r03-b at 65.5) — and before that it had shown "0 scored" for three rounds
because it read a file the dead evaluators never wrote. Checked once at the
start, never again — precisely r02-c's keep-notch failure, in the
orchestrator's own deliverable.

**The biggest failure: the rubric graded the wrong product for three rounds,
and the human calibration signal arrived three rounds late.** The article's
evaluator-tuning loop is explicitly human-in-the-loop: "read the evaluator's
logs, find examples where its judgment diverged from *mine*." Our rubric was
tuned hard — against drift, against leniency, against generic output — but
never against *the founder*, who first saw output after round 3 and said: "I
am not happy with the design. Do not think that this is just a board."
`PRODUCT-1.md`'s post-mortem line is the cost stated exactly: **"the rubric
graded honesty and craft and never graded whether anyone got closer to
applying. Nine agents optimised what was measured, perfectly."** This is the
article's central warning realised — every harness component encodes an
assumption, the rubric encoded "this is a register," and no agent could
falsify it because every agent inherited it. Only the human could, and we
didn't show the human intermediate output until the harness had already
stopped itself. The article's **sprint contract** — agree what "done" looks
like *before* building — practiced with the founder rather than between
agents, would have surfaced the divergence in round 1.

**Budget discipline was warned about and ignored.** `HANDOFF.md` said "re-check
the position before a large fan-out." The orchestrator flagged it, then
launched ~11 agents; the limit killed the evaluators, and later killed two
strategy agents mid-run (relaunched after re-login). The article meters cost
per phase to the cent; we never metered at all.

---

## 5 · What the article would have us do differently, from round 4 on

1. **Never skip the evaluator again.** It is ~8% of spend and it is the loop.
   Round 4's M1–M6 are agent-runnable by design; run them on every variant,
   every round. (Round 4's briefs already require generator self-verification
   against M1–M6 — keep the independent pass on top, because self-checks are
   what the bias warning is about.)
2. **Make the founder's sign-off a sprint contract.** The pivot accidentally
   produced the right shape: `PRODUCT-1.md` proposed, the founder pushed back
   (kept all 789, rejected the cut), and `r04-brief.md` records the settled
   decisions as non-negotiable. Formalise that: no round launches until the
   human has seen the previous round's winner and the next round's "done"
   definition. The article's calibration loop, with the founder as "mine."
3. **Few-shot the new rubric.** M1–M6 replaced a three-round-old rubric with
   zero calibration examples. The article calibrated with "few-shot examples
   with detailed score breakdowns" — we now have nine register variants that
   *fail* M2/M3 in known ways; use them as the judge's negative examples.
4. **Consider inner iteration loops.** The article runs 5–15
   generator-evaluator iterations *within* a generation; our loop iterates
   once per round. For M3 (the 60-second apply loop), a tight inner loop —
   generator measures, adjusts, re-measures before handoff — is closer to the
   article's cadence than another full round.
5. **Meter the run.** Cost per round, per role, reported in the round verdict.
   The article's tables exist for a reason; two spend-limit deaths in one day
   is the reason.
6. **Re-examine the harness at the model boundary.** The session's default
   model changed mid-project (Opus 5 → Fable). Per the article, that is the
   moment to stress-test components: whether three representation stances are
   still needed for diversity, whether the judge/evaluator split still earns
   its cost against M1–M6 (which are objective enough that the comparative
   judge may matter less this round), and whether briefs this prescriptive
   still help or now hurt — the article removed its sprint construct when the
   model improved, and found the evaluator "worth the cost when the task sits
   beyond what the current model does reliably solo," not before.

---

## The one-paragraph summary

We ran the article's generator–evaluator separation, its skeptical-evaluator
discipline, its weighted-originality rubric with calibration anchors, its
file-based handoffs, and its plateau-detection — and we extended it with
comparative judging, persistent lanes, model diversity, and keep-everything,
each of which paid for itself in findings a faithful implementation could not
have produced. We broke it in two places that mattered: we cut the evaluator
half of the loop for budget, and — the expensive one — we tuned the evaluator
against everything except the human it existed to represent. The article's
deepest sentence turned out to be literal: every harness component encodes an
assumption. Ours encoded "this is a register," nine agents optimised it
perfectly, and the correction had to come from the only participant who had
never read the rubric.
