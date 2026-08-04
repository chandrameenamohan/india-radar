# ITERATIONS — how many rounds does the best version take?

Answering with the article's own numbers (re-fetched 2026-08-04) beside this
project's measured curve. Short version: **the article ran 5–15 micro-iterations
per artifact and saw plateau-with-headroom; we ran 3 macro-rounds × 3 variants
= 9 attempts on the register and hit the same plateau shape; the pivot to the
product restarts the curve, and the honest budget for the product phase is 2–3
rounds with a founder look after every one.**

## 1. What the article actually ran

Every concrete count in the piece, quoted:

- **Frontend/design experiments:** *"I ran 5 to 15 iterations per generation,
  with each iteration typically pushing the generator in a more distinctive
  direction."*
- **The plateau:** *"Across runs, the evaluator's assessments improved over
  iterations before plateauing, with headroom still remaining."* Plateau is the
  stopping signal — not perfection. They stopped with headroom left.
- **Non-linearity:** *"While scores generally improved over iterations, the
  pattern was not always cleanly linear… I regularly saw cases where I preferred
  a middle iteration over the last one."* And the museum page example: nine
  iterations of refinement, then *"on the tenth cycle, it scrapped the approach
  entirely."* More iterations do not monotonically approach "best" — which is
  why they kept intermediate outputs, and why we keep every variant.
- **App builds:** the game maker ran a *"16-feature spec spread across ten
  sprints"* (Sprint 3 alone had 27 evaluator criteria); the DAW ran **three**
  build+QA rounds in ~4 hours and $124.
- **Diminishing returns move with the model:** on newer models *"the boundary
  moved outward"* — tasks that needed evaluator iterations stopped needing them.
  The right count shrinks over time; it is not a constant.

## 2. What our own curve showed

Units first: the article's 5–15 are **micro-iterations of one artifact**. Our
rounds are **macro-iterations of three parallel variants** with a comparative
judge. 3 rounds × 3 variants = **9 independent attempts**, 12 after round 4 —
inside the article's 5–15 band once the units are reconciled. The comparison is
legitimate at the attempt level, not the round level.

| Round | Scores (a/b/c, /70) | Winner | Mean | What the round bought |
|---|---|---|---|---|
| 1 | 54 / 63 / 55.5 | 63 | 57.5 | Three genuinely different answers; the gaps named |
| 2 | 63 / 64.5 / 60 | 64.5 | 62.5 | Floor rose 5 pts to the old ceiling; winner +1.5 |
| 3 | 64.5 / 65.5 / 61 | 65.5 | 63.7 | Winner +1; mean nearly flat; wildcard fell back |

**The knee was round 2.** Round 1 → 2 bought five points of mean; round 2 → 3
bought one. The qualitative signals agreed with the numbers: the unbriefed
surplus per round shrank to one sentence, one grammar, one question; convergence
moved from prose (round 2: interchangeable honesty paragraphs) to structure
(round 3: the same mechanism set in three skins). The stopping rule at 68 fired
at 65.5. Stopping at three was right — a fourth register round buys decimal
points, exactly the article's plateau-with-headroom shape.

## 3. The distinction that governs the answer

**Iterations refine an objective; they cannot fix a wrong one.** Our three
rounds converged on the best *register* while the founder wanted a *product*.
No fourth, fifth, or tenth register round would have found the shortlist
builder, because the rubric never asked for it — nine agents optimised what was
measured, perfectly. The article's own tuning loop ("find where the evaluator's
judgment diverged from *mine*") is the mechanism we skipped: the founder saw no
intermediate output for three rounds, so their calibration signal — "this is
not just a board" — arrived three rounds late. **One founder look at round 1
would have been worth more than rounds 2 and 3 combined.** That is the most
expensive lesson in this project, and it reframes the question: the binding
constraint on finding the best version was never iteration count. It was
calibration frequency.

## 4. Recommendation for the product phase

Round 4 (three variants against PRODUCT-1) is **iteration 1 of a new
objective**, not iteration 4 of the old one. The curve restarts.

- **Plan for 2–3 product rounds, expect the knee at round 2.** The register
  curve and the article both say round-over-round gains halve fast. 3 rounds ×
  3 variants = 9 attempts on this objective; with round 4's three, the project
  total lands at 12–18 attempts, squarely in the article's band.
- **Founder look after every round — this is the rule that changed.** Not after
  three. The M1–M6 rubric plus the founder's ten-applications gate is the
  sprint contract; the founder running that gate on round 4's winner *is* the
  round-5 brief.
- **Watch three plateau signals, not just the score:** (1) winner delta < ~2
  points, (2) mechanisms converging across variants (the structural-convergence
  tell that ended the register phase), (3) unbriefed surplus approaching zero.
  Any two of the three → stop and ship the leader.
- **Keep middle iterations reachable.** The article preferred middle iterations
  over final ones "regularly"; our round-3 steal-list drew four of seven items
  from losing variants. Nothing gets deleted; the gallery stays the deliverable.
- **Budget is a real constraint here, not a footnote.** Two spend-limit deaths
  killed the evaluator layer for two rounds (30 of 100 points unmeasured). A
  product round with generators + evaluator + judge is ~7 agents; the evaluator
  is ~8% of the cost and is the loop — cut variants per round before cutting
  the evaluator. If budget forces a choice, 2 rounds × 3 variants with full
  grading beats 3 rounds × 3 with the loop broken.
