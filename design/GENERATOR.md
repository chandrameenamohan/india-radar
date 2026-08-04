# GENERATOR — read this first, every round

You are building one variant of the ROLE·ATLAS page. Read `design/BRIEF.md`
(what to build) and `design/CRITERIA.md` (how you will be graded) before you
touch anything. You are graded by a separate agent that did not build this and
is instructed to be unimpressed.

## Your working area — and nothing else

```
design/iterations/<YOUR_ID>/index.html      the variant
design/iterations/<YOUR_ID>/NOTES.md        what you decided and why
```

**Do not touch `site/index.html`.** Do not touch any other iteration. Do not
touch `src/`, `worker/`, `tests/`, `data/`, `TASKS.md`, or `HANDOFF.md`. Do not
commit; do not run `git push`. The orchestrator commits.

Start:

```bash
mkdir -p design/iterations/<YOUR_ID>
cp site/index.html design/iterations/<YOUR_ID>/index.html
```

The variant is a **single self-contained HTML file**, exactly like the original.
No build step, no npm, no framework. It reads the real corpus through the
`../data/` paths already in the file — a symlink at `design/iterations/data`
makes those resolve from your directory, so leave them alone.

## Run it. Actually run it.

```bash
python3 -m http.server <YOUR_PORT> --bind 127.0.0.1 &
# http://127.0.0.1:<YOUR_PORT>/design/iterations/<YOUR_ID>/index.html
```

Your port is yours alone — other agents are running concurrently and **8731 and
8788 belong to the test gate**. If the shell sandbox blocks the bind, retry with
the sandbox disabled.

Use the **`/browse` skill** to drive it (this project's convention — never the
`mcp__claude-in-chrome__*` tools). Look at it. Scroll 400 rows. Open a role.
Switch to German and Japanese. Resize to 380px. Block Clerk. Tab through it with
the keyboard. **A variant you have not watched running is not finished** — and
the evaluator drives the live page, so anything you did not check, it will find.

Headless Chrome clamps `--window-size` to a 500px minimum; a sub-500 screenshot
is a cropped desktop shot showing phantom overflow. Use CDP device metrics for
real mobile widths.

## The three flows, and where the work actually is

`design/BRIEF.md` is the spec. Practically, most of your diff lands in:

1. **The gate** — a preview limit, the ask, the localStorage counters, and the
   guard that keeps the register rendering when Clerk never loads.
2. **The i18n layer** — a string table, `t()`, locale detection, a picker, and
   then the grind of routing every hardcoded string through it. `count()`'s
   hardcoded `'en-IN'` is a bug in seven of your eight locales.
3. **The feel of scrolling** — this is the part that is worth points and the
   part most likely to be skipped because the first two are concrete. Do not
   skip it. Competence scores 5.

## Ship-quality, not sketch-quality

Every variant must be *usable*, not a mockup. The filters work, the plates turn,
the search returns, the sheet opens. You are changing how it feels, not
replacing it with a picture of itself.

Break anything the brief tells you to break, and nothing else.

## What the grader punishes hardest

Generic. Centered hero, three feature cards, purple gradient, glass panels,
rounded-2xl grid, emoji icons, "Discover your next opportunity". These read as
default and score 2 on a 20-point axis. **Originality is where this is won.**
The pull toward the template is strong and you will not feel it happening.

## When you are done

Write `NOTES.md`:

- **The idea, in one sentence.** If you cannot, you do not have one.
- What you changed, and the reasoning — this codebase's comments explain *why*.
- What you deliberately did not do, and the ceiling on it (`ponytail:` comments
  in the code for the same).
- Where you think it is weak. The evaluator will find it anyway; saying it first
  costs nothing and makes the next round faster.

Then send your final report as a message. An idle notification is not a report.
