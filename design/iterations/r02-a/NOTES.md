# r02-a — THE OVERPRINT

## The idea, in one sentence

The register is one black sheet that is the same for everybody, and everything
about the reader — where they stand, what a posting's own words say is open to
them, what they folded, what has been surveyed since they last read — is a
second plate printed in magenta over it, laid only where a fact exists.

## The fork, and which way I took it

The verdict gave lane A a choice: make the atlas answer the four gaps, or admit
the metaphor has run out. I took a third position that is really the first one
honestly done: **the atlas stays, the Bound Volume goes.**

r01-a's problem was not that it was a book. It was that a book is a thing you
page through in the order somebody else bound it, and every one of round 2's
four gaps is about the reader, not the binding. So the metaphor moved one step
back up its own family tree: an atlas plate is *printed*, in plates, one per
colour, registered to each other. That gives the page a structural rule it can
be held to and that r01-a had no equivalent of:

> **The overprint may only be laid where a fact exists.**

A board that said nothing about hiring somebody who is not already there gets
no magenta, because there is nothing to print. 5,671 of the 6,423 roles here
are in exactly that state, and the sheet's honest appearance under a stated
standpoint is *mostly bare*. That is the finding, and it is the first time this
register has had a way to draw its own silence at true scale.

Magenta is not decoration either: it is the overprint colour on an Ordnance
Survey revision and on an aeronautical chart. The colour is used once and means
one thing — **you** — and it means it everywhere without exception: the
standpoint's rule, a reachable line's tick, a folded corner, the keyboard
cursor, the focus ring, the revision slip, the registration cross that appears
in the corner of the sheet only once there is a second plate to register.

**The nine-select filter bank is gone.** It is replaced by three first-person
statements (`design/iterations/r02-a/index.html`, "the standpoint"), because
the question this register could never answer was never *which department* — it
was *could I do any of this*.

## The four gaps

### 1 — a register that reads its reader

`WHERE YOU STAND` states three things, none of them inferred, all persisted and
all printed back on the bookplate:

- **I am in** — one of the fifteen, or *a country not surveyed here*, or not
  saying. The second option is the corrected São Paulo/Warsaw case, and it is
  the one that changes the page most.
- **I read** — the eight editions' languages, as chips.
- **I can work** — anywhere the board says, or only remotely.

Every role then has a **bearing**, and there are only three:

| | when |
|---|---|
| **within reach** | the reader stands in one of the role's own countries (no border to cross, no board has to say anything), or the posting itself said visa `yes` or hire-from-abroad `yes` |
| **stated closed** | the posting said `no`, or named a workplace the reader's stated constraint excludes |
| **the board did not say** | everything else — 5,671 lines — and it prints as **nothing at all** |

The rule that makes this honest rather than clever: **remote is not borderless.**
A board that says "Remote — United Kingdom" has named a country, and it is still
that country's job. Remote alone never opens a role to somebody outside it; only
the posting's own words can. Every job site on earth gets this wrong and the
page says so in the margin.

Stating *a country not surveyed here* and pressing **PRINT ONLY THE OVERPRINT**
collapses 6,423 lines to **543, from 47 companies** — the postings that
volunteered, newest first, every country mixed. That number is the single most
useful true thing this corpus can tell a reader outside its fifteen countries,
and no variant in round 1 could produce it.

The lens **dims, it does not delete**: a silent line stays legible, stays
countable and stays clickable at 58% opacity, and comes back to full on hover or
under the cursor. Silence is not exclusion.

### 2 — the return visit

`SINCE YOU LAST READ THIS` is tipped in above the sheet on the second visit and
never on the first. It states what the data carries and refuses what it does
not:

> You last read the sheet of 2 August 2026. **145** roles have appeared since,
> confirmed on two consecutive nights. *What vanished, this copy cannot tell
> you: the build keeps no ledger of departures, and a count it does not hold is
> a count this page will not invent.* **2** of your folded corners are no longer
> on a board.

Two decisions in there. First, only `confirmed` first-sightings are counted,
which is `first-seen.json`'s own note enforced. Second — and this is the part I
am most pleased with — **`build-report.json`'s `departed` ledger is empty, so
the register genuinely cannot report a disappearance. The reader's own folds
can.** A fold whose URL is no longer in the corpus prints struck through with
*gone from the board*. The one place this page can honestly report a departure
is the one place the reader put a pin in.

### 3 — the reader can keep something

Folded corners. `f` on a line, or *fold the corner* inside the evidence sheet, or
the dog-ear at the end of the row. Kept in `localStorage` with the title and the
company beside the URL — which is what makes the departure detection above
possible — listed in the margin, and downloadable as a plain text list.

And the honest repair of the hollow gate: **the ask now says exactly what
signing in buys and exactly what it does not.**

> Signing in prints them, and it is counted. That count is the only evidence
> anyone will ever have that readers want a copy which follows them between
> devices: the corners you fold here are kept in this browser and nowhere else,
> and carrying them would need a server this register does not have yet.

That is true today, it names the thing identity would genuinely buy, and it
makes the counter measure desire for something real. It also refuses to claim a
sync that does not exist — which would have been the easy version of gap 3 and a
lie.

### 4 — the cursor follows the eye

`moveCursor()` re-seats before it moves: if the cursor is not inside the visible
range it is discarded and the line at the top (or bottom) of the viewport is
taken instead. Measured: scroll to 24,000px, press `j`, cursor lands on line 782
at 18px from the top of the register. Jump to 60,000px, press `k`, cursor lands
on line 2,000, in view. Both directions.

The first version of this shipped **two cursors** — it mutated `cur` before
calling `focusRow`, which then cleared the wrong row. `focusRow` now clears by
query, not by remembered index, and says why in a comment.

## Stolen, as instructed

- **r01-c's evidence sheet.** A role opens in place: what the posting said about
  visa and about hiring from abroad (with *the board did not say* printed in
  words, the only place on the page where silence gets words, because that is
  the question the reader came with), workplace, the board's own placement, the
  board's own department verbatim, first seen with confirmed/unconfirmed, board
  read, funding with *round letter not stated*, listing rule, CIN, UK number,
  the salary observation with its source, the build's verdict, the machine-
  written description marked as machine-written, and one paragraph naming every
  derivation on the card.
- **r01-c's true-scale gauge**, carried one step further: the whole sheet at
  true scale *and* every reachable line struck at its own depth, so the shape of
  what is open to you across 195,000px is visible before you have scrolled to
  any of it. Click it to go there.
- **r01-a's suppressible, auditable ask.** It does not appear when the view
  already fits (search "Spellbrush", get 8 lines, get no card). The bookplate
  prints every byte this copy holds about the reader, with the control that
  burns it.
- **r01-b's instrumentation printed back**: `asked 1 · signed in 0 · printed
  anyway 0 · declined 0`, under the card.

## What I changed that nobody asked for

- **The deal.** The judge's sharpest mark against r01-a was that its free sample
  was forty lines of one American company's sales org. The sheet is no longer
  sorted, it is *dealt*: newest night first, then one line per company at a
  time, round the table. The first eight lines are now Halter (NZ), Heidi Health
  (AU), Neo4j (IN), Netskope (AU), Reflection AI (GB), Neo4j (IN), Reflection AI
  (GB), ARQ (GB). The rule is printed on the finder line rather than left
  implicit.
- **The department is no longer translated.** r01-a translated fourteen
  department names. The field holds ~900 free-text strings a board typed
  (`8548 Payins - Eng`, `Rohit Dosi (Bing and Etisalat)`), which makes it a
  source claim, and translating a source claim is the one thing forbidden here.
  It prints verbatim under a label that says whose word it is.
- **The cross-language dead end has a bridge.** Search デザイナー in the Japanese
  edition and the page does not shrug: it explains that boards print in their
  own language and this register never translates one, counts what *is* printed
  in your script (7 of 6,423), offers to show those, and offers **the page's own
  gloss** — デザイナー → `design`, which returns 161 roles — labelled twice as
  the page speaking and never as a board's translation.
- **`i18n-check.py`**, carried forward from r01-a and hardened twice, because it
  let two real bugs through on this page. Its reachability pass was desynced by
  apostrophes in prose comments (five false alarms); comments are stripped now.
  And its missing-key pass only understood `t('...')` calls, so when a sed ate
  `ev.k.seen` and `ev.k.board` out of *all eight editions at once* — a table line
  holding three pairs, and a regex that ran to end-of-line — the eight still
  agreed and the check passed while two labels rendered blank. It now checks
  every key-shaped string literal in the code against the table. Both faults are
  written into the script's own docstrings.

## Measured, on the running page

Private headless instance on 127.0.0.1:8741, 1440×900 and 380×780 via CDP device
metrics.

- **Clerk blocked** (`Network.setBlockedURLs '*clerk*'`): 6,423 rows render, no
  account control at all rather than a dead button, no ask, and the bookplate
  records `ra2.ask.noask 1`. The ask is now suppressed entirely while the
  provider has not answered — a card that flashed up for four seconds and was
  then withdrawn was counting an ask this page took back, which corrupts the one
  measurement the gate exists to take.
- **No console errors.** The only console output is Clerk's own development-key
  warning, which the incumbent has too.
- **`prefers-reduced-motion: reduce`**: zero transitions and zero animations on
  every element in the document, `scroll-behavior: auto`. Smooth scrolling was
  removed at every setting — every scroll this page makes is a jump to a place
  the reader asked for, and animating a 195,000px sheet is a wait, not motion
  that carries meaning.
- **Layout shift: 0.0008** (was 0.3378 — the loading line lived in its own block
  above the page and dropped 57px of document when it went; it now sits inside
  the register, on the first row's own line, and the margin is drawn at full
  height and empty before the corpus lands).
- **Scroll**, 60px/frame through the middle of the full 6,423-line sheet: p50
  17ms at 1×, 24ms at 2× (a mid-range phone), 54ms at 4×. Without
  `content-visibility` the same scroll is 49/140ms; the gauge redraw costs about
  1ms a frame after it stopped walking all 6,423 rows for their class every
  frame.
- **Contrast**: every distinct colour/size/weight combination on the page
  measured against its own computed background. All pass WCAG AA. `--ink-3` is
  `#656B72` because that is the lightest grey that clears AA at 10px on all
  three grounds this page has (paper 5.16, plate 4.57, wash 4.57); it shipped at
  `#7E848A`, which is 3.62 and a fail.
- **380px**: no horizontal scroll, no element past the viewport, every control
  ≥44px. The margin dissolves (`display: contents`) and its sections take their
  own places in one column — standpoint and tally *in front of* the register
  because they are the invitation, gauge and folds *behind* it because they are
  instruments for a reader already inside.
- **Eight editions**: `<html lang>`, `<title>`, `dir`, dates, counts and country
  names all follow. Counts go through `Intl` — 6,423 / 6.423 / 6 423 / 6423 in
  en / de / fr / es, which is the `en-IN` bug fixed rather than moved. Swept
  every chrome zone in seven non-English editions for orphaned English; the one
  it found was the Clerk sign-in button, which is painted by the provider's own
  callback and went stale on an edition change. Fixed.

## Where it is weak

1. **The lens makes the sheet look switched off.** Under a stated standpoint,
   ~90% of rows sit at 58% opacity, and at a glance that reads as *disabled*
   rather than as *the board did not say*. The magenta ticks pull correctly and
   PRINT ONLY THE OVERPRINT is one press away, but the first half-second of that
   state is the weakest moment on the page.
2. **`stated closed` is doing two jobs.** A posting that said `visa: no` and a
   posting that said `onsite` under a reader who can only work remotely both
   print as *stated closed*. The second is true relative to the reader's stated
   constraint and the mechanism is explained in the key and in the margin note,
   but one label is carrying two different kinds of no.
3. **The printed-script derivation cannot separate Chinese from Japanese.** A
   title in Han characters alone (`Account Executive, 製薬`) is classified `zh`
   and tagged `ZH`, so a Japanese reader's script count says 7 when 8 titles are
   arguably theirs. The evidence sheet names the ambiguity outright rather than
   picking one quietly, and the gloss bridge does not depend on it — but a
   reader who counts will find the discrepancy before the page explains it.
   Marked `ponytail:` in the source.
4. **The gloss is twelve to eighteen words per language, hand-written.** It
   covers the role nouns a job seeker would actually type and nothing else. Type
   a Japanese *company* name and you get the dead-end explanation without a
   bridge.
5. **Rows are one line, and long titles are clipped with an ellipsis.** The
   evidence sheet has the whole title and the row carries it in `title=`, but the
   fixed row height that makes the gauge exact is paid for here.
6. **The country strip is fifteen bars, and on a phone it is two columns of
   eight before the register.** It is navigation and geometry in one control,
   which I think earns its place, but it is the largest thing between a phone
   reader and the first job.
7. **The finder is a substring match over title + company.** It has no stemming,
   no ranking and no fuzziness; "engineer" returns 2,270 lines in corpus deal
   order, and the reader has to narrow it themselves.
8. **`ra2.folds` grows without a cap.** The margin prints twelve and then a
   count, but nothing prunes the store.

## Deliberately not done

- **No shortlist sync, and no promise of one.** The ask says plainly that
  carrying folds between devices needs a server this register does not have.
  Ceiling: the Worker exists; this is a `PUT /folds` keyed on the Clerk session
  and a merge on load. `ponytail:` in the source.
- **No RTL edition ships**, but `dir` is set from the locale table and every
  edge uses logical properties, so adding one is a table row.
- **The keyboard's key names (`Enter`, `Esc`) are not translated**, because they
  are what is printed on the key.
