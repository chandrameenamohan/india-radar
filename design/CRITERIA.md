# CRITERIA — how the evaluator grades a variant

You are the **evaluator**. You did not build this. Your job is to find where it
falls short, and the generator's job is to argue back with a better version.

Out of the box a model is a poor QA agent: it praises work it is shown. Read
that sentence again before you score. **Your default posture is unimpressed.**
A variant that is merely competent scores 5, not 8. Competence is the floor
here, not the achievement.

## How to grade

**Drive the running page. Do not grade source code.** Serve it, open it, click
it, scroll it, resize it, switch the language, block Clerk, use only the
keyboard. A score derived from reading HTML is void — say so and re-do it.

Score each criterion 0–10. Quote the specific thing you saw. "The spacing feels
off" is not a finding; "the role row's 8px gap collapses to 2px at 380px wide
because `.jrow` has no min-height — screenshot 3" is.

## The five criteria

| # | Criterion | Weight |
|---|---|---|
| 1 | The ask | 25% |
| 2 | Inside — the feel of moving through it | 25% |
| 3 | Originality | 20% |
| 4 | Craft | 15% |
| 5 | Worldwide | 15% |

### 1 — The ask (25%)

Does a signed-out reader get enough, freely, to believe the register is honest?
Does the ask arrive at the right moment — after value, not before it? Would a
real person read it and feel invited rather than taxed?

- 9–10: you would sign in, and you know why.
- 5–6: it works and it is polite, and it is a modal.
- 0–2: blur, "unlock", countdown, or an ask before anything of value was given.
- **Automatic 0** if the register does not render with Clerk blocked.

### 2 — Inside (25%)

Scroll through several hundred roles. Filter. Open a role. Change plate. Come
back. Does it feel *alive*, or does it feel like a table?

- 9–10: you kept scrolling after you had finished testing.
- 5–6: fast, correct, unmemorable.
- 0–2: jank, layout shift, lost scroll position, or a spinner you waited on.
- Check the keyboard path and `prefers-reduced-motion` explicitly. Both count.

### 3 — Originality (20%)

Evidence of decisions someone *made*. Weight this heavily and grade it hard —
this is the axis a model fails by default, because the pull toward generic is
strong and generic passes every other check.

Penalise on sight: centered hero + three feature cards, purple-to-blue
gradients, glassmorphic panels, a rounded-2xl card grid, an emoji as an icon
system, "Discover your next opportunity" copy, a floating pill nav. These are
template defaults wearing a costume.

Reward: a metaphor carried all the way through; type doing structural work;
a colour used once and meaning one thing; a control invented for this data.

### 4 — Craft (15%)

Hierarchy, spacing rhythm, contrast (check real ratios, WCAG AA), optical
alignment, tabular numerals in every column of numbers, focus states that are
visible, hit targets ≥44px on touch. No console errors. No layout shift.

### 5 — Worldwide (15%)

Switch to `de` and `ja` at minimum. Then look for English that did not move.

- Any orphaned English string in page chrome: name it, and cap this criterion
  at 4.
- `<html lang>` must follow the choice. `<title>` too.
- Numbers and dates through `Intl`, not hardcoded `'en-IN'`.
- Does the layout survive German compounds and Japanese line-breaking?
- Data left untranslated is **correct** — do not penalise a German role title.

## Hard gates — any one of these caps the total at 3

- The register does not render with Clerk blocked or offline.
- A console error on load.
- The page claims a fact the data does not carry (violates absence-stays-absence).
- A source claim (company name, role title, board text) was translated.
- `prefers-reduced-motion` ignored.

## What you write

`SCORE.md` next to the variant:

```
# <id> — <the variant's own name for itself>

TOTAL: NN/100

| Criterion | Score | Why |
|---|---|---|
| The ask (25) | n/10 | one line, specific |
| Inside (25) | n/10 | |
| Originality (20) | n/10 | |
| Craft (15) | n/10 | |
| Worldwide (15) | n/10 | |

## What is genuinely good
Two or three things. Be specific; the next round should keep them.

## What is wrong
Ranked. Each one: what you saw, where, and why it matters. Reproduction steps.

## The one change that would move this most
A single sentence. Not a list.
```

Then append one row to `design/SCORES.md`.

## Calibration

- A faithful, clean, well-spaced version of the page as it exists today, with a
  working modal gate and complete translations, is a **62**. It does everything
  asked and nothing more. Do not score it higher because it has no faults.
- A variant with one genuinely new idea, executed roughly, with two real bugs,
  is a **71**. The idea is worth more than the bugs cost.
- Below 50 means something in the hard-gate list fired, or it is generic.
- Above 85 means you would ship it today and you are slightly jealous.
