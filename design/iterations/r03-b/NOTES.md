# r03-b — THE NIGHT DESK, THIRD NIGHT

## The idea, in one sentence

The sentence conjugates: the unit word that was "the 12 roles I kept" grows two
more tenses — *the 3 I applied to*, *the 1 I heard back about* — so the page's
one organizing idea finally reaches past what the register holds to **what the
reader did about it**, and everything else this round follows from a page that
now has a past tense to keep: a log that gets longer instead of newer, and a
copy of itself for the morning the build moves.

## First, the error, because it was mine

Round 2's greeting counted unconfirmed first sightings. With a last-read date of
28 July it announced "6,423 roles appeared" — the whole register — because
tracking began on the 29th. The page's own footnote states the artifact's rule
("only confirmed roles may be called new") and its NEW badge obeyed it; the
greeting did not.

Fixed **at the source, not at the banner**: `seenSince()` now requires
`e.confirmed`, so the sentence's `first seen since …` clause and the greeting
can never disagree again. With last-read 28 July it now reads **145** — and
r02-a's clause is in there verbatim:

> *What vanished, this copy cannot tell you: the build keeps no ledger of
> departures, and a count it does not hold is a count this page will not
> invent.*

And the half that was being silently dropped is now printed rather than hidden:

> *6,278 more were first seen since then on boards we had not read the night
> before — so we saw them for the first time, which is not the same as their
> being new, and this page will not call them new.*

That number was the *whole* of the old overclaim. Printing it as what it is,
beside the 145, is the honest version of the sentence that was wrong.

`greet.head` also goes through `pluralKey` now: the confirmed diff is often a
single role (seven appeared on the night this was written), and "1 roles have
appeared" is the page failing at the one line it opens with.

## 1 — Gap 1: the verb (the lane question, answered)

**The model is one enum and two dates.** A kept row gains `applied` and
`answered`, each holding the *snapshot* on which the reader said it. That is
all. It inherits every rule the reader-profile already had: stated never
inferred, dated by the night it was stated, undoable one step at a time,
printed in the bookplate, burned with everything else. Note 08 says so on the
page, in the page's own voice:

> *Nothing about any of it was observed: no inbox was read, no board was told,
> no company was contacted, and the register does not know you exist. That is
> exactly why the page can print it back to you — and why the door beside each
> one undoes it.*

**Where it lives, in four places, each doing a different job:**

- **In the sentence.** `units` gains `applied` and `answered` the moment there
  is one of each. This is the lane question and it is the whole reason to build
  it here: German declines the relative clause the verb needs (*die 3, auf die
  ich mich beworben habe*), Japanese puts the verb in front of the counter
  (*応募した3件*), French pronominalises at n=1 (*celui auquel j'ai postulé*).
  All three tenses go through `pluralKey`, because "les 1 qui m'ont répondu" is
  ungrammatical in five of the eight and the first application anybody states
  is exactly the case where n is 1.
- **On the row, everywhere in the register.** A line you applied to wears
  `applied`, and past four nights it wears `waiting 9` beside it. The marks are
  **dashed** — alone among the marks on a row — because everything else there
  was read off a board and these two were said by the reader, and a page that
  set its own reader's word in the same frame as a company's would be levelling
  the two kinds of claim it spends its whole length telling apart.
- **In the role's evidence sheet**, as the last block: what you did, in dates,
  and every door out of it including the undo. An undo is not politeness here —
  it is the thing that makes a stated fact safe to state.
- **On the shelf, as the one move per line.** In the three keep views the row's
  end control is not the keep (it is already kept) but the next thing the reader
  could truthfully say: `+ APPLIED`, then `+ ANSWERED`, then a mark. The shelf
  bands by **state** — *Heard back · Applied to · Kept, and nothing said yet* —
  so the second week reads forward, and the sort word offers *longest waiting
  first*, which is the order a person actually comes back for.

Keyboard: `a` states applied, and it keeps first if it has to. A reader who
applied to a line they never got round to keeping means both, and making them
press `x` then `a` would be the page insisting on its data model in front of
somebody who is telling it something.

**The tally head is the week in one line** in all three views — `kept 4 ·
applied to 3 · heard back 1` — so switching between them never costs sight of
the other two numbers.

## 2 — Gap 2: the morning after the build moves

Round 2's three variants all refused the v11 schema, each in its own voice, and
the refusal was right. What none of us designed is what the reader meets
*instead*, which was an apology with no register under it.

**The page now keeps the last sheet it read in full, in the Cache.** Not
localStorage: the sheet is 1.8 MB, Chrome counts localStorage in UTF-16 code
units (3.6 MB against a 5 MB quota), and it would cost a synchronous stringify
of the whole corpus on every load. The Cache stores the *response*, so the copy
is the bytes we actually read, byte for byte, with nothing to re-serialise
wrongly. All four files are kept together so the copy is internally consistent,
and only from a load that rendered.

**A dated copy is not a lie; a copy that presents itself as tonight is.** So:

- the masthead says its own date in its first line, and the letterhead's stamp
  reads `READ ON AUGUST 4, 2026 · A COPY`;
- and `STALE` switches off **every claim the page makes about tonight**: the
  NEW badge, the `Tonight` band head (it prints its date instead), the "no
  longer listed" strike on a departed keep, and the whole return diff. Verified
  on the running page: 0 `NEW` badges, empty `#greet`, dated bands.

The masthead says that out loud rather than leaving it to be noticed:

> *So nothing below is a claim about tonight … we did not read a board tonight,
> and a copy that spoke as though we had would be the one lie this register
> exists not to tell.*

**Test seam: `?stale=1`** makes tonight's file fail to arrive. A fallback nobody
can see is a fallback nobody has checked, and on a pinned corpus this path is
otherwise unreachable. `?data=../data/nope.json` reaches the no-copy case, and
`?data=../data/build-report.json` the schema-mismatch one; both print the
refusal *and* `stale.nocopy` so the reader knows why there is nothing to fall
back on.

The copy is printed in the bookplate as its own row — *a public file, and
nothing about you* — and **burn takes it too**. A control that said "all of it"
and left 1.8 MB behind would be the audit failing at the one line the reader
can check.

## 3 — Gap 3: visit seven

`ra.nights` is a list of the snapshots this browser has read, written by the
same rule as the visit stamp (on the way out, once the reader has actually
read). **The log** sits under the greeting and is the only thing on the page
that gets *longer* rather than newer:

```
NIGHTS READ  Jul 21  Jul 24  Jul 26  Jul 28  Jul 31  Aug 2  Aug 4
```

The nights you kept something take the lamp; nothing else is marked, so a glance
across it is a glance at the nights that turned into something. Then four lines
of prose built from nothing but what the reader did — nights read, nights that
produced a keep, applications, answers, and the one number a person actually
comes back for: *your oldest unanswered application was 11 nights ago.*

It is deliberately **not a chart**. A bar chart of somebody's job hunt is this
page having an opinion about their week, and it has no standing to.

Tonight counts while it is happening (`nights` = stored + tonight), so the log
appears from the second visit and visibly accretes; the stamp is still only
written on the way out, so a reload never costs anybody a night. And it survives
the greeting: once you have read tonight, the diff retires and the log does not.

## 4 — Stolen whole, as instructed

- **r02-a's three-door ask.** SIGN IN · **PRINT THE REST ANYWAY** · NO THANK
  YOU. Round 2's two doors made "no" mean two different things at once — *I do
  not want an account* and *print the rest* — so the counter could not tell them
  apart, and the counter is the entire reason the gate exists. `printed` is now
  its own ledger line. The third door is a real answer: it prints nothing more,
  and it stays silent for the rest of the page's life (`askOff`), because
  "nothing here will ask you again on this visit" has to survive the reader
  changing a word in the sentence and changing it back. What stands at the seam
  afterwards is one line saying where the printing stopped — a register that
  just ended would read as a bug.
- **r02-a's diff clause, verbatim** (above).
- **r02-a's fold-as-departure-ledger** was already here as `.gone`; it now meets
  the verb, which is where it hurts: *"And the posting you applied to is no
  longer on the board we read tonight. That is not an answer — it is only that
  it is no longer listed."*
- **r02-c's distance, derived, marked ≈, nearest-first.** Fifteen anchors, one
  per country, a haversine, and three rules that keep it honest: it is only
  offered once the reader has named a country (a distance from nowhere is a
  number with one end), it prints `≈` everywhere, and note 09 says what it was
  measured between. The sort reaches past the company blocks the way `newest`
  does, because a company hiring in Dublin and Tokyo is two different answers to
  a reader in London.

## 5 — The convergence warning, taken personally

The brief named the `asked · signed in · declined` counter as a convention
inherited rather than an idea. It is now a **sentence in the page's voice** with
the fourth term the third door earned, set the way the page sets every other
sentence (voice in the serif, numbers in the mono), and it says where the count
lives:

> *Counted here and nowhere else — asked `1` · signed in `0` · printed the rest
> anyway `1` · no thank you `1`. That row is four numbers in your own storage:
> the bookplate at the foot prints it, and offers to burn it.*

**And the offer is now the true one.** All three round-2 variants promised that
an account carries your keeps across devices, in three tenses, and the Worker
cannot honour any of them. This one says so:

> *What signing in buys, exactly: nothing yet. You have kept 4 roles and written
> down what you did about 3 of them, and every byte of that is in this browser
> alone. There is no server on the other side of that button that could carry it
> to your phone — there is a count of whether anybody pressed it. That count is
> the only argument for building the thing that would carry your list, so
> pressing it is a vote and nothing else, and we would rather say so than imply
> a sync we have not written.*

That is the scrupulous version and I think it is also the better pitch.

## Craft

- **Console errors: none**, across the whole flow, in all eight locales, with
  Clerk blocked, on the copy, and on both refusal paths.
- **CLS**: 0.0002 (en), 0.0006 (de), 0.0016 (hi) at 1440×1000 on a cold profile.
  `#log` reserves its berth from the first paint whenever this browser already
  holds a night, the same way `#greet` does.
- **`prefers-reduced-motion`**: entry animation `none`, row transition `0s`,
  `scroll-behavior: auto`. Measured with emulated media, not read off source.
- **380px** with CDP device metrics in de, hi and ja: no horizontal overflow
  (380 vs 380), verb button 88×44, doors 189×44.
- **Contrast**: log dates 5.1:1 (unmarked) and 9.4:1 (lamp), log prose 9.3:1,
  fine print 4.95:1.
- **One real bug found by looking**: `.did` as the doors container also matched
  `.mk.did` and `.nt.did` — the state marks on every row grew a stray solid top
  border and half a rem of padding nothing else on the line had. Renamed
  `.didbox`. It was invisible in the source and obvious in a screenshot.
- The keyboard's `x` and `a` repaint **one row in place** rather than resetting
  the register: rebuilding six thousand rows to change one mark would throw the
  reader back to the top of what they were reading. Verified at depth — `j` from
  scrollY 5,587 adopts row 73 and seats at 5,290.

## What I deliberately did not do

- **No outcome beyond "answered".** Offer, rejection, stages — all of it is one
  more thing the page would be modelling on somebody's behalf, and three states
  is where the honest floor is. `ponytail:` in the code.
- **No server-side counting**, unchanged: this measures browsers, not people.
- **No shortlist sync** — and now the ask says so in plain words rather than
  hinting at it.
- **The copy is not a service worker.** The ceiling is named in the code: a
  service worker would make the whole register readable with no network at all,
  which is a real thing to want and a much larger thing to own.
- **Distance is country-to-country and says so.** An office-level distance would
  need coordinates the corpus does not carry.

## Where I think it is weak

1. **Two blocks now sit between the sentence and the register** on a returning
   reader's second-plus night — the greeting and the log. Together they can run
   nine lines. They are about different subjects (what the register did, what
   the reader did) and the log retires nothing, but it is the densest the top of
   this page has ever been, and I did not find a compression that kept both
   legible.
2. **The log counts completed nights plus tonight.** That is honest, but it
   means the very first visit shows nothing and the second shows "2 nights",
   which is a beat behind what a reader might expect from a strip that is
   supposed to be about *them*.
3. **A role that answered you is counted under `applied to` as well**, because
   you did apply to it. The tally reads `applied to 3 · heard back 1` for three
   applications, one of which answered. I believe that is right and I can see
   somebody reading it as four events.
4. **Nothing prompts the verb in the register at large.** The doors are in the
   evidence sheet and on the shelf; a reader who never opens a row and never
   visits their shelf will never learn that `a` exists except from the rail
   hint. The shelf is the workbench and you have to walk to it.
5. **Distance is fifteen anchors.** ≈18,254 km from Germany to New Zealand is
   defensible; ≈0 km from Germany to Germany is a shrug, and it prints as `0`
   on every row of a country-scoped view where it adds nothing.
6. **The copy is only as good as the last full read.** A browser whose first
   ever visit lands on a broken build has no copy, and gets round 2's answer.
   The page says exactly that rather than pretending otherwise.
7. **`markup()`'s `*stars*` do not nest.** Passing a value that already carries
   stars produces `**7**` and renders a stray asterisk — I shipped that bug for
   an hour and caught it on the running page. It is a sharp edge for a
   translator and there is no guard on it.
8. Everything r02-b was weak at that this round did not touch is still true: the
   yield prose can stack, the company view has no lens, `display=optional` means
   a cold visitor may read the register in Georgia.

## Running it

```bash
python3 -m http.server 8742 --bind 127.0.0.1
# http://127.0.0.1:8742/design/iterations/r03-b/index.html
# ?lang=de|ja|zh-Hans|hi|es|pt-BR|fr   ?view=companies   ?wide=1   ?c=Germany
# ?stale=1                 — tonight's file does not arrive; the copy prints
# ?data=../data/nope.json  — nothing arrives and there is no copy
```

To see visit seven without waiting a week, seed the record a returning reader
would already have and reload:

```js
localStorage.setItem('ra.visit', JSON.stringify({ last: '2026-07-28' }));
localStorage.setItem('ra.nights', JSON.stringify(
  ['2026-07-21','2026-07-24','2026-07-26','2026-07-28','2026-07-31','2026-08-02']));
```

Driven throughout on a private headless instance (own binary, own
user-data-dir, CDP :9342, never the shared daemon), at 1440×950 and at 380px
with CDP device metrics.
