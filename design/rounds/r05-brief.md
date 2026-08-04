# Round 5 — the founder's calibration, and a target

The founder looked at all three round-4 variants. The verdict: **"I do not like
any version."** Three concrete signals came with it, and they are this brief.
The target is **68–69 on the round-4 rubric** (same judge, same anchors:
faultless-with-no-POV = 62; round 4's winner sat at 63). Rounds continue until
a winner reaches it.

## Signal 1 — the card never says what the company IS

> "We missed to show these information: WHAT, FOR WHOM and WHY THEM."

The data exists and every round-4 variant left it off the collapsed card:
`fixture-v2/descriptions.json` — **371 of 789 companies** carry three
one-line fields with provenance flags:

```json
"Stripe": {"what": "Payment processing for internet businesses",
           "for_whom": "Any business that takes money online",
           "why_them": "The default payments layer of the internet",
           "ai": true, "checked": true}
```

This was also the judge's own "what none did" finding — *fatal-ish for a
product whose winning list is six-of-ten unknown companies* — and the founder
confirmed it independently. Strongest possible signal in the project.

Requirements:
- WHAT / FOR WHOM / WHY THEM on the **collapsed** card, readable while
  scanning, not hidden behind an expand.
- Provenance rendered: these lines are `AI-summarized`, most `checked against
  their own site`. A summary the page wrote is the page's voice, not a board's
  — say so once, well, without wallpapering every card with the same footnote.
- **418 companies have no description. Absence stays absence** — an absent
  description must read as "not yet read", never as a broken card, and never
  invented. Design the absent state deliberately; it is the majority of the
  newly-unlocked world companies. (The backfill is `scripts/describe.py` build
  work — name it, do not fake it.)

## Signal 2 — a young public company is attractive, not a warning

> "I prefer Airbnb as they are public company but very young public company."

This **overrules round 4's treatment and the judge's praise of it**. r04-a's
red `PUBLIC` chip and r04-c's caption ("A job at a public company, not a bet on
one") both editorialize *against* exited companies. The founder reads the same
fact the other way: a company that IPO'd recently is a rocketship that already
left the pad, and that is interesting.

Requirements:
- Status is a **fact, stated with its source, editorialized in neither
  direction.** "Public — per YC ↗" with the batch year. No red, no warning
  grammar, no "not a bet" — and equally no "rocket that made it" hype the data
  cannot source.
- Never demote or hide the 32 Acquired/Public/Inactive. (This settles open
  decision #2 from the round-4 verdict.)
- Lesson for every future round, recorded here: **the judge is calibrated by
  the founder, not the other way round.** Where a judge's praised sentence and
  the founder's stated preference conflict, the founder wins.

## Signal 3 — the target

68–69 on the round-4 product rubric: ease 25 · curation-legibility 25 ·
representation 20. The gap from 63 to 68 is five points, and round 4's verdict
says where they are NOT: not in speed (all three beat every measure by an order
of magnitude), not in more mechanism. They are in **representation** (no
variant scored above 17.5/20) and in the gaps every variant shared.

## Signal 4 — the baseline is the live site, and the founder likes it

Added mid-round, 2026-08-05:

> "My baseline is this: https://roleatlas.sennamind.com/site/index.html — I
> want better than this. This is not better but I like it so far."

Read it carefully: the founder LIKES the live register's design — the Swiss /
International Typographic identity, the hairline rules, the tabular numerals,
the printed-instrument confidence of `site/index.html`. The round-4 product
cards are more *useful* than the register and **less designed than it** — and
that is why none of them was liked. The bar is not "better than the other two
variants"; it is **better than the live site**, on the live site's own terms of
craft, while being the product the register never was.

What this does NOT mean: do not rebuild the register. The behaviours stand —
the shortlist loop, the six measures, the calibration items above. What it
means: the representation must carry the design DNA the founder already chose
once — a page that looks like it was set by someone who cared about type, not a
generic card list. `site/index.html` is in this repo; open it, study what makes
it feel authored (the grid, the micro-labels, one red, the crop marks, numerals
as columns), and bring that authority to the product. The judge will compare
against the live site directly.

From the round-4 verdict's "what none did":

1. **The shortlist cannot leave the page.** No URL state, no copy, no export —
   the friend gap, third round running. A shortlist you cannot send or reopen
   elsewhere is a session, not an asset. Minimum: the shortlist survives in the
   URL and a one-tap copy produces something a friend or a future self can use.
2. **Nothing spends the record.** Keeps, opens, and answers accumulate and buy
   no sentence. One honest line of arithmetic over the reader's own record is
   worth more than a feature.

## Grafts — the judge's list, take them

From r04-b: the pre-rendered fold and key queue; the full keyboard loop;
`__firstCardPainted` self-stamping; the "What this page will not say" sheet;
the board's own department words on role rows. From r04-a: the serif/mono
evidence-split typography; per-option yield counts on controls; the on-page
department-residue confession. From r04-c: per-company role shards (the only
solved roles-fetch); per-gate captions with interpolated counts; the day-gated
ask discipline (`applied` never from a click handler — permanent doctrine).

## Unchanged

M1–M6 still hold and the judge re-verifies them independently. All 789 render;
every card cites its credential; `hide the giants` stays (its default remains
the founder's open decision — ship it on, but make turning it off obvious).
Data: `../../fixture-v2/`. English-only. No sign-in. The department taxonomy
remains a renderer's stopgap — pick ONE of round 4's three (r04-c's had the
least residue) rather than writing a fifth.
