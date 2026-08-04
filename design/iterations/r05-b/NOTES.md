# r05-b — the memo, set on the register's own grid

**The idea, in one sentence:** every company is a one-paragraph investment memo
— what they do, who it's for, why them, who vouched with the receipt, and how
hard they are hiring — and the whole thing is set in the live register's Swiss
grammar, so the page the founder already likes and the product it never was are
the same page.

Serve it and look:

```
python3 serve.py 8742          # gzip, because M1 is a transfer measurement
python3 build.py               # rebuilds data/ + index.html from ../../fixture-v2
URL=http://127.0.0.1:8742/ node qa/measure.mjs      # M1–M6, all numbers below
URL=http://127.0.0.1:8742/ node qa/crosscheck.mjs   # Python == JS on all 789
URL=http://127.0.0.1:8742/ node qa/shots.mjs        # shots/
```

**Port note:** 8742 was held for this whole session by an orphaned
`python -m http.server 8742` (PID 73356, started 18:49, cwd = repo root, parent
already dead) that predates round 5 — not mine to kill, so every number below
was measured on **8842**, the same `serve.py` serving the same directory. Once
8742 frees up `python3 serve.py 8742` takes it with no other change.

---

## What I kept, and what I rebuilt

My predecessor's session died before writing anything up. The inheritance was
in two very different states.

**Kept, essentially whole — it was good work and it answers signals 1–3:**

- `build.py`'s data pipeline: the gate/credential resolution, `descriptions.json`
  → memo with provenance, r04-c's per-company role shards (789 files, 4.4 KB
  gzipped each — still the only solved roles-fetch), the funnel ladder, the
  priced menus, the intensity stats.
- `taxonomy.py` — r04-c's vocabulary, the one with the least residue. I did not
  write a fifth.
- `app.js`'s whole behaviour layer: URL state, the two copy buttons, the record
  arithmetic, the day-gated ask, the keyboard loop, the key queue, the
  incremental render, `__firstCardPainted`.
- `qa/cdp.mjs` — the dependency-free private-Chrome driver.

**Rebuilt, because it predated Signal 4:** the entire visual layer. The
inherited page was warm cream paper, Iowan Old Style, a brown accent and rounded
cards — a handsome newspaper, and nothing whatever to do with `site/index.html`.
Signal 4 says the judge compares against the live site directly, so `page.html`
is new from the first line: white paper, `#111` ink, Inter, one red `#E30613`,
11px/0.11em uppercase micro-labels, hairline and 2px structural rules, tabular
numerals, crop marks on the sheet corners, zero border-radius anywhere.

Both card renderers (`build.py:card_html`, `app.js:cardHTML`) were rewritten in
lockstep to the new anatomy.

**Written from scratch:** `qa/measure.mjs` (M1–M6), `qa/crosscheck.mjs` (the
Python/JS invariant, which the old comments promised and no file provided),
`build.py --cards` and `hype_audit()`.

## The one structural idea

**One gutter runs down the whole sheet and every micro-label lives in it.** The
card's index, WHAT, FOR WHOM, WHY THEM, VOUCHED — all in the same column, at the
same 11px, in the same margin gray. `.memo` and `.ml` are `display:contents`, so
a label and its value are grid siblings on the card's own grid rather than a
nested table; auto-placement does the aligning with no explicit columns.

A memo is a form, and a form has a label column. That is the register's own
anatomy pointed at prose, and it is what makes 789 paragraphs read as a
document instead of a card list.

The second idea follows from it: **left column, no numbers; right rail, no
claims.** The rail is the register's verification stamp re-cut for hiring —
open roles, the department split, `+N more fields`, `TEAM 300 people, per YC`,
`RATE 300 ÷ 98 = one opening per 3.1 people`, `WHERE`. That is r04-a's
evidence-split typography done in a one-family page: the split is mono-vs-Inter
and framed-vs-open, not serif-vs-sans.

## Signal by signal

**1 — WHAT / FOR WHOM / WHY THEM on the collapsed card.** All three, on the
collapsed card, at the masthead thesis's exact setting (1.0625rem/1.35,
-0.017em, 500) — the most authored type on the live site, spent on the memo.
371 of 789 carry them. Provenance prints as the varying fact only
(`CHECKED AGAINST THEIR OWN SITE` / `NOT CHECKED…` / `FROM THEIR JOB BOARD…`);
that the three lines are mine and machine-written is said once, in the lede,
where it can be argued. 371 identical `AI-summarised ·` prefixes was the first
draft and it was wallpaper — I cut it.

The 418 absent get a three-line designed state, not a blank:

```
NOT YET READ   I have their gate and their board. I have not read their own
               site, so this card does not say what they do.
THEIR TEAMS    Field Sales, Oncology · Lab Operations · IT · Service Engineering
               A BACKLOG IN SCRIPTS/DESCRIBE.PY — NOT A JUDGEMENT ABOUT THEM
```

The board's own unedited words are set in the mono voice this page reserves for
things somebody else wrote. It is the closest honest thing to "what they do"
that exists without reading their site, it is useful, and it names the backfill
script rather than faking it.

**2 — status editorialized in neither direction.** `PUBLIC · PER YC · S17` in a
hairline frame in ink, in the card head. Active, Public, Acquired and Inactive
share one frame, one ink, one sentence shape; the difference between the four is
the word inside and nothing else — no rule in `page.html` keys off a status
value, and the ranking never reads one. The batch rides with it, the full batch
and the receipt link sit on the `VOUCHED` line directly below. The YC caption
was rewritten so it no longer repeats the status: *"YC's own directory entry —
the batch, the status and the 300 people it lists are YC's numbers, not mine."*
`BillionToOne — Public, per YC` is still card 001 of the default product.

**3 — the target.** Not mine to score. Where I spent the five points:
representation (the memo, the stamp, the absent state, the register's authority)
and both shared gaps — the shortlist leaves the page, and the record buys a
sentence.

**4 — better than the live site, on its own terms.** Taken wholesale: the
twelve-column masthead grid, the crop marks, the micro-label voice, the
hairline/2px rule pair, the priced controls with no boxes and a hand-drawn
chevron, `select.set` going red the moment it leaves its default, tabular
numerals, the platestamp (here: `27,689 / ROLES, ON THE COMPANIES' OWN BOARDS`),
the receipt block, the register row as the role row.

Taken *and corrected*: the live register's round-10 lesson that **at rest a
count is ink**. My first draft had a red rule and a red total on all 789
stamps and the accent turned into texture within one screen. Red now marks the
masthead's one number, the snapshot stamp, a control that has left its default,
and the **live** card — hovered, keyboard-cursored, or kept. Nothing else.

Deliberately *not* taken: the live receipt's -1.5° hand-stamp tilt. One tilted
stamp per plate is wit; 789 of them is a texture.

## Measured — every number below is `qa/measure.mjs` output, on 8842

| | |
|---|---|
| **M1** | first card **625 ms** on the page's own clock (700 ms wall), **Fast 3G by protocol** (562.5 ms RTT, 1.6 Mbps down). 6 cards are in the HTML with their memos already set — no JS ran. The other 783 land at 2,483 ms; 732 cards in the DOM when the incremental render finishes. |
| **M2** | the load screenshot carries `I READ 10,125 COMPANIES TO FIND THESE 789`, the snapshot date, `27,689 ROLES, ON THE COMPANIES' OWN BOARDS`, the two-column provenance paragraph with the five gate counts, and `the whole funnel, 10,125 → 789`. `shots/fold.png`. |
| **M3** | **6 clicks, 4.2 s, 0 navigations**, 3 new tabs, 3 opens witnessed — real `Input.dispatchMouseEvent` at real coordinates, not synthetic `.click()`. |
| **M4** | 233 raw matches of `/rocketship\|recently\|funded\|new\|top\|best/i`. **203 are the proper noun in a place a board named** (New York, New Delhi). Of the remaining 30, 11 have no link/date/count in the same `<p>` and **0 have none in the surrounding block**. Every one of the 11 is either the ordinary adjective in a memo (`Uses AI models to design new medicines`) or one of the sheet's own headings for a word it refuses to use. The build greps its own memos independently: `hype_audit()` finds **8**, all `new`, and the how-sheet prints that count with three of them quoted. |
| **M5** | **667 of 789** companies have no citable round; all 789 are in the register on the page and **0 cards render a missing amount as a zero**. Across the first 40 shards, **8,871 of 9,938** roles have no visa answer and 294 are a stated no; the unknowns print as *"their board says nothing about visa sponsorship on 98 of them — that is silence, not a no."* |
| **M6** | 3 keeps → 3 cards marked and 3 shortlist rows **survive a reload through the URL alone** (no localStorage needed — the `#k=` fragment carries them). The question **fired exactly once**, died on the answer, and did not return on the next reload. |

Other measurements I ran:

- **Python/JS markup invariant: 789 rendered by each, 0 mismatches**
  (`qa/crosscheck.mjs`). It earned its keep immediately — it caught 7 cards
  where Python's round-half-even and JS's `toFixed` disagreed on one digit
  (810 ÷ 40 = 20.25 → 20.2 in the pre-rendered fold, 20.3 in the scrolled
  list). Both now floor an explicit tenths integer.
- **The founder's gate** (engineering · San Francisco · giants hidden), top ten:
  Astranis · Replit · Mercor · MatX · Illumio · Lambda Labs · PsiQuantum · Hark ·
  Abridge · LangChain. One household name in ten, no Anthropic/OpenAI/Databricks.
- **The stance's own test** — of the first ten cards, how many can you describe
  to a friend: **7/10** default, **6/10** engineering+SF, **9/10**
  engineering+remote.
- **Keyboard**: `j j j` → cursor on Pigment, `x` keeps it, `o` opens 12 role
  rows, `g` swaps to all 789, `c` copies. The pre-data key queue exists and did
  not fire on localhost, because the data beat the keystrokes.
- **390px**: 0 px horizontal overflow (CDP device metrics, not `--window-size`).
- **Transfer, gzipped**: index.html 18.9 KB · app.js 12.1 KB · index.json
  119.2 KB · one role shard 4.4 KB.
- `ruff check` passes on the whole repo tree.

The shortlist copy is a real artifact, not a list of names:

```
3 companies I am applying to — Aug 5, 2026
found with ROLE·ATLAS, which read 10,125 companies and kept 789

1. Astranis — 95 roles open on their own board
   NOT YET READ — I have their gate and their board, not their site.
   Their board's own words for its teams: Production & Manufacturing …
   VOUCHED   Y Combinator backed them, Winter 2016 — YC's own directory entry …
             https://www.ycombinator.com/companies/astranis
   ROLES I OPENED (3, on Aug 5, 2026):
     …title…
       …url…
…
Reopen this shortlist: http://…/#f=eng&p=sf&k=astranis,replit,mercor
```

And the record buys a sentence:

> Your record here: **3** kept · **1** role opened at **1** company. Of the
> **732** companies in this cut you have opened a role at **1**. Y Combinator
> vouched for **1** of the **1** role you opened; you have opened nothing at the
> **272** companies here that CB Insights tracks.

## Where it is weak

1. **The phone header is 1,459 px deep.** Desktop puts the first card at 641 px,
   which is right; 390px does not, and everything above it is doing real work
   (masthead, thesis, three sheets, three controls, the switch, the yield). I
   folded the 400px provenance paragraph into a named `<details>` below 62rem,
   which bought 200 px. The remaining fix is the live site's `#ffold` — folding
   the control bank itself — and I did not build it. This is the biggest single
   thing between this page and a better ease score.
2. **Card 001 of the default view is an absent memo.** The default order is by
   role count and BillionToOne (98 roles) has no description, so the first thing
   a reader meets on the stance's own page is `NOT YET READ`. I measured before
   deciding: 7 of the first 10 carry memos, so the ten-card test passes
   comfortably, and putting the absent state on the fold unhidden is the honest
   reading of "design the absent state deliberately". But it is a real cost to
   the first impression and a reasonable judge could call it the wrong call.
3. **An absent-memo card leaves white space under the gate line**, because the
   rail is taller than three lines of prose. The live site's spread explicitly
   accepts a ragged foot; I accepted it too rather than padding the memo out
   with something I do not know.
4. **The M4 residue is a judgement call I made, not a clean pass.** Eleven
   matches have no evidence inside their own `<p>`. I believe every one is the
   English adjective and not a claim, the build counts them, and the how-sheet
   quotes three of them by name — but a judge running the regex strictly will
   count 11 and be within their rights.
5. **The pre-data key queue is untested in practice.** It exists, and localhost
   is too fast to exercise it. Under real throttling it should replay; I did not
   prove it.
6. **`hide the giants` still ships on**, per the brief. It is now a two-word
   switch — `HIDING THE GIANTS` / `SHOWING ALL 789`, the off state a readable
   word rather than an unticked box — with the count and the reason on the same
   line, and all 57 named on a scrolling rule underneath, each one a door back.
   Whether the *default* is 732 or 789 is still the founder's call and I did not
   presume it.
7. **Inter loads from Google Fonts non-blocking** (`media="print" onload`), with
   Helvetica Neue holding the page. The live site loads it render-blocking; I
   would not spend a third-party round trip on M1. If the network is unavailable
   the page sets in Helvetica Neue, which on a Swiss sheet is the ancestor, not
   a degradation — but it is not byte-identical to the baseline.
