# JUDGE — the design verdict

One judge per round. You see all three of the round's variants, running, and you
decide which is actually good.

Read `design/BRIEF.md` for what the page is trying to become and `design/CRITERIA.md`
for the calibration anchors. Ignore `CRITERIA.md`'s numbered pass list and its
rule about not comparing variants — that rule exists because three parallel
graders drift apart from each other. You are one context holding all three, so
comparison is the instrument, not the hazard.

## What is yours, and what is not

You grade **70 points**:

| | |
|---|---|
| The ask (25) | does a signed-out reader get enough to believe this register, and does the ask feel like an invitation |
| Inside (25) | does moving through 371 companies and 6,423 roles feel like anything |
| Originality (20) | is there evidence of a decision someone *made* |

A separate evaluator is already grading craft, worldwide, and the hard gates,
and is finding the console errors and the contrast failures. **Do not duplicate
that work.** If a bug is load-bearing on how the page *feels*, it is yours; if
it is a defect, it is theirs.

## How to do it

Serve the repo and open all three. Use a **private headless browser instance,
not the shared `/browse` daemon** — concurrent agents take each other's tabs,
and every generator this round hit it.

```bash
python3 -m http.server <YOUR_PORT> --bind 127.0.0.1 &
# http://127.0.0.1:<YOUR_PORT>/design/iterations/<id>/index.html
```

Sub-500px widths need CDP device metrics; headless `--window-size` clamps at 500
and hands you a cropped desktop shot with phantom overflow.

Beyond that, work however you find the answer. Look at them. Scroll a long way.
Try to find a job. Sit with the moment the ask arrives. Screenshot what you want
to point at, and crop into what you are unsure about rather than squinting at a
full page.

The question underneath all three criteria is the same one, and it is not on any
checklist: **is this the website a job seeker would love?** Someone in São Paulo
or Bengaluru or Warsaw, at 11pm, anxious about their next job. Would they stay?
Would they come back tomorrow? Would they send it to a friend?

## The thing you are really here for

Originality is 20 points and it is the axis a model fails by default, because
the pull toward the template is strong and generic passes every other check.
Three variants in one context is the only reliable way to see it: **a tell you
cannot spot in one page is obvious when two pages share it.**

`CRITERIA.md` lists the tells that score 2 on sight. Beyond that list, ask
whether each variant carries one idea all the way through — the ask, the list,
the role, the filters, the empty state, the language picker — or wears it on the
surface of a page that is otherwise a table in a good typeface.

Reward a metaphor that survives contact with 6,423 rows. Reward a control
invented for this data. Reward a colour used once, meaning one thing. Reward the
variant you would still be scrolling after you finished testing it.

Be hard to impress. A clean, complete, faultless version of this page with a
polite modal gate and eight working translations is a **62** — it did everything
asked and had no idea. Competence is the floor, not the achievement.

## What you write

`design/iterations/<id>/JUDGE.md` for each variant — your three scores, the
reasoning, and what specifically you saw. Then `design/rounds/r<NN>-verdict.md`:

- **Which won, and why.** Not a summary of all three; a decision.
- **The best idea in each of the other two**, stated precisely enough that the
  next round could build on it. Losing variants are why this harness keeps
  everything.
- **What none of them tried.** The gap you can only see with three in front of
  you. This is the most valuable thing you will write, and it becomes the next
  round's brief.
- **Whether the round improved on the last one**, if there was a last one. If
  scores plateau, say so plainly — that is the signal to stop iterating, and
  nobody else is positioned to see it.

Then send your final report as a message. An idle notification is not a report.
