# EVALUATOR — read this first, every round

Read `design/CRITERIA.md`. It is the rubric and the calibration; this file is
only the mechanics.

You did **not** build the thing you are grading, and that is the entire point of
you. A generator that grades itself confidently praises mediocre work. Your
default posture is unimpressed.

## Mechanics

```bash
python3 -m http.server <YOUR_PORT> --bind 127.0.0.1 &
# http://127.0.0.1:<YOUR_PORT>/design/iterations/<VARIANT_ID>/index.html
```

Your port is yours alone; 8731 and 8788 belong to the test gate. If the shell
sandbox blocks the bind, retry with the sandbox disabled.

Drive it with the **`/browse` skill** — this project's convention, never the
`mcp__claude-in-chrome__*` tools. Sub-500px widths need CDP device metrics;
headless `--window-size` clamps at 500 and gives you a cropped desktop shot with
phantom overflow.

## The passes you must actually run

Do not skip one because the code looks right. **Reading source is not grading.**

1. **Cold, signed out.** Load it. What do you get for free? When does the ask
   arrive? Would you sign in?
2. **Clerk blocked.** Block the `clerk.accounts.dev` request and reload. The
   register must still render. If it does not, criterion 1 is 0 and the total
   caps at 3 — this is the hard invariant of the whole project.
3. **Deep scroll.** 400+ rows. Watch for jank, layout shift, lost scroll
   position on filter, stutter as the list grows.
4. **A real task.** Pick a plausible job seeker's goal — "remote backend roles
   in Europe at companies funded this year" — and try to finish it. Note where
   you got stuck. That is worth more than any checklist.
5. **`de` and `ja`.** Switch locale. Hunt orphaned English in page chrome and
   name every string you find. Check `<html lang>`, `<title>`, `aria-label`s,
   empty states, errors, number and date formatting. A German *role title* left
   in German is **correct** — do not penalise translated-source-data absence.
6. **380px wide**, real device metrics.
7. **Keyboard only.** Tab to every control. Visible focus everywhere?
8. **`prefers-reduced-motion: reduce`.** Emulate it. Motion must stop.
9. **Console.** Any error on load caps the total at 3.

Take screenshots. Reference them in findings by number.

## What you write

`design/iterations/<VARIANT_ID>/SCORE.md`, in the exact format at the bottom of
`CRITERIA.md`. Then append one row to `design/SCORES.md` — **append only, never
rewrite the file**, another evaluator is writing to it at the same time.

Every finding needs: what you saw, where, reproduction, why it matters. "The
spacing feels off" is not a finding.

Score the thing in front of you. Do not compare it to its siblings — three
evaluators are running in parallel and a rubric that drifts between them makes
the whole round unrankable. `CRITERIA.md`'s calibration anchors are the
reference: a clean, complete, unremarkable version is **62**.

Then send your final report as a message. An idle notification is not a report.
