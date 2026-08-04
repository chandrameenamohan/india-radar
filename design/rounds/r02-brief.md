# Round 2 — the brief

`design/BRIEF.md` still stands; this is what round 1 proved it was missing.
Read `design/rounds/r01-verdict.md` first — it is where these came from.

**The bar is 63** (r01-b, judge's 70 points). The calibration that matters more
than the number: *none of round 1's variants would make a job seeker tell a
friend about it unprompted.*

## What round 1 established

Three complete, working, non-generic answers. Nothing to un-learn — the losers
are on disk and openable, and two of their ideas are load-bearing below.

| | Judge /70 | |
|---|---|---|
| r01-a The Bound Volume | 54 | the most finished object |
| **r01-b The Night Desk** | **63** | composed its free sample for the reader |
| r01-c The Core | 55.5 | the best engineered |

## The four gaps — round 2's actual work

### 1. No page reads the reader

All three organise the corpus by the data's structure — company, country, night
— and none by the reader's question: **what could I do?** Nothing asks, infers,
or lets a reader state what languages they read, whether they need visa
sponsorship, whether they can relocate. The corpus already carries the facts to
answer: posting language, foreign-hires marks, remote scope.

Build a register that knows who is reading it: a **stated** (never guessed)
reader profile of languages-read plus mobility, and a lens that dims to the
roles whose own facts say *possible for you*.

**Absence stays absence — the lens may only use what a posting actually says.**
A role whose board is silent on sponsorship is not "no"; it is silent, and the
lens must render that as silence rather than as exclusion.

This is also where the Japanese searcher's dead end gets fixed. Type a Japanese
word, get zero results, and no variant explains that titles are in their own
boards' languages or offers a way through. An empty state that bridges the
language boundary is worth more than another translated string.

### 2. Nobody designed the return visit

The corpus diffs itself nightly — `first-seen.json` is real, 6,650 URLs dated —
and r01-b's Tonight band proves the material is there. Yet no variant remembers
what the reader saw last time and opens with **their** diff: *since you last
read: 212 appeared, 179 vanished, 2 in Japan.*

Greeting a returning reader with what changed for them is the loved-website
move, and it needs nothing but `localStorage`.

### 3. The reader can keep nothing

Three read-only registers. No shortlist, no saved rows, no *mark this for
tomorrow*. At 11pm, anxious, **you collect.**

This is also the honest repair for something all three got wrong identically:
**signing in buys nothing.** Declining prints everything, so "yes" gives the
reader nothing nameable that "no" does not. A gate that is honest and pointless
is still pointless — and `HANDOFF.md` says the gate exists to *measure* whether
anyone signs in, so a hollow offer measures nothing.

A client-side shortlist gives the ask its missing motive: identity is the one
thing that would carry a shortlist across devices. Make signing in buy that, and
the counter finally measures desire for something real rather than politeness.

### 4. The keyboard cursor is a data structure, not attention

Press `j` after scrolling deep and every variant warps back to a cursor that
never followed the eye. Small, shared, and exactly the tell that is invisible in
any single page.

Also for the record: **r01-a and r01-c both ship the incumbent's nine-select
filter bank essentially verbatim.** Only r01-b escaped it. A control you
inherited without deciding to is a template default wearing your own codebase.

## Steal these outright

Round 1's losers earned these. Do not reinvent them worse.

- **From r01-c — provenance at the row.** The only variant where a role opens
  *in place* into a full evidence sheet: first seen, board read, build verdict,
  funding with "round letter not stated", a derivation that names itself, the
  CIN. Take it.
- **From r01-c — geometry that cannot lie.** The true-scale depth gauge and the
  fold that breathes the register between 371 and 6,423 lines: the round's only
  honest answer to *make 6,423 feel like abundance, not a wall*.
- **From r01-a — the ask as a suppressible, auditable instrument.** Two parts,
  precisely: the ask does not appear when a filtered register already fits
  ("nine results is an answer, and asking on top of an answer is a toll"); and
  the bookplate prints every byte the page keeps about the reader, with a
  control that burns it.
- **From r01-b — the page showing you its instrumentation.** The ask printing
  its own counter back to the reader (`asked 1 · signed in 0 · declined 0`) was
  the round's best idea about trust.

## Lanes

| | |
|---|---|
| **A · atlas** | r01-a scored lowest on originality (14) — the volume is beautiful and its filter bank is the incumbent's. Either make the atlas answer the four gaps or admit the metaphor has run out. |
| **B · depart** | r01-b won and its frontier is known: the sentence goes telegraphic in German and Japanese, because label-then-value is English word order. Per-locale clause ordering is the fix nobody built. |
| **C · wildcard — TEXT-LIGHT** | Least translatable text wins. Icons, numbers, geometry and layout carrying meaning that prose currently carries. This lane is where gap 1 is most naturally solved, because a page that barely uses words does not strand a Japanese reader in an English dead end. |
