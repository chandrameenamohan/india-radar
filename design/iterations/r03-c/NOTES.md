# r03-c — THE DAYBOOK

Lane C · wildcard · **ACCRETION**. Port 8743. Built on `design/iterations/r02-c/index.html`.

## The idea, in one sentence

The page keeps a dated, append-only daybook of what the reader did about the
register — written in two hands, one for what it witnessed here and one for what
the reader told it happened elsewhere — so that visit seven is a different page
from visit two, and the morning the build changes shape, the daybook and the
last good sheet are both still there, dated.

## Why this base

r02-a's best things are *rules and prose* — the overprint rule, the three-door
ask, the fold-as-departure-ledger, the diff clause — and prose ports in an
afternoon. r02-c's best things are *machinery*: a chunked column that releases
its rows, a rail measured in role indices, URL state, an evidence sheet, the
distance column, the bridge. A virtualised 6,423-row column does not port. So I
took the machinery and carried the prose across.

The second reason is sharper. r02-c's judged wound was that its numbers lied on
a page where numbers are the prose. That is a thing I can *correct* rather than
inherit, and correcting it in place is worth more than starting somewhere the
error never happened. Every printed figure below was recomputed against
`design/fixture/` before it was printed.

## The two hands, which is the whole design

Round 2 converged all three variants on the same honesty mechanics. The thing
that has to stay un-converged here is the ink, so it carries an argument:

| | |
|---|---|
| **blue** `--stamp` | the register's own side: the posting's word (○ remote · ▮ hires from abroad · ⊠ says it does not) and the nights a board was genuinely read twice |
| **red** `--hand` | the reader's own word: kept · applied · answered. Stated, never inferred |
| **no ink at all** | what the page *witnessed*: you were here, you opened this posting |

The third row is the load-bearing one. The page watched the reader click through
to a posting; that is a fact it holds, and it writes it down. It is not a claim
about the world, so it gets no colour that says one was made — and `applied` can
therefore never be produced by a click handler. The click is the page's hand,
the application is the reader's, and the daybook never turns one into the other.
It says so in its own second sentence, and note 08 says it again.

Red is only 1.35:1 against blue in luminance, so neither ink ever carries alone:
the board's marks are a circle and a square, the reader's are a rising bar and a
check, and every one of them has a translated `aria-label`.

## What is new

**1. The daybook (gap 1 and gap 3).** A sheet that opens *in* the page and
pushes the register down — not a modal, not a drawer, because it is the reader's
half of the same document. Dated blocks, newest first, never rewritten: a keep
that was later dropped keeps both of its lines, on the nights they happened.
Four tallies (nights · kept · applied · answered), a span line, and one control
that burns the lot.

Verified across seven simulated nights on seven different dates: the daybook
grows from one line to seven blocks; the handle goes `1 NIGHT · 2 KEPT` →
`7 NIGHTS · 7 KEPT`; the tallies move to `7 · 7 · 2 · 1`.

**2. The ladder — kept → applied → answered.** Three rungs, each dated on the
night the reader said it, offered as a door in the evidence sheet and on `a`
from the keyboard. The keep notch on every row is now a gauge as well as a
switch: empty, a third, two thirds, full. Climbing down is allowed and gets its
own line ("you took back what you had said about X") because a daybook records a
withdrawal, it does not pretend the thing was never said.

`a` only ever climbs one rung and only on a row already kept. A key that could
invent *applied* on a row you were merely passing is the same inference by
another route.

**3. The follow-up, which is the only place the page asks about the world.** The
page witnessed an open on an *earlier* night; on a later one it asks, once,
about up to three of them: "On 2 August you opened X. Did you apply?" — with
**Yes, I applied** and **Don't ask about this one**. Never on the same night as
the click. Never after 21 days: an unanswered question asked nightly is nagging,
and silence is an answer too.

**4. The nights strip.** One column per night on which a build first saw one of
these URLs, plus every night the reader was here — both are sets of dates this
page holds, and a strip made of only one of them is a history with a side
missing. Drawn to **true scale**: 31 July is a spike because that is the night
most of these boards were first read, and note 07 says exactly that rather than
letting a tall bar imply an event. The solid cap is the confirmed part. The red
foot is the reader's, and appears on no other night. On the first visit it is
one foot under seven columns; by the seventh it is seven feet under thirteen.

**5. The morning after the build moves (gap 2).** Every night that renders
leaves a sheet behind. When a night does not — schema moved, or the fetch failed
— the page refuses it (correct) and then prints that sheet, banded, dated, with
every figure wearing `as read on 4 August`. The headline figures do not print at
all: there is no live number to put in them and a zero would read as a fact. The
reader's keeps print in full from the facts recorded the last night they were
seen, each still openable, each still climbable — because what the reader did is
theirs and does not depend on the register opening tonight.

**See it:** `index.html?data=tomorrow.json` (a three-line v11 stand-in shipped
next to this file). Read a normal night first, or you get the other honest
state: *"There is no kept sheet in this browser either."*

**6. The keep bands.** In the kept view the ordering is the reader's own — newest
night of keeping first, with the date printed on a red rule between the bands.
Their strata, not the register's.

**7. The departure ledger, stolen whole from r02-a.** A kept URL the corpus no
longer carries prints struck through, with the only sentence the page is
entitled to: *"Not in tonight's register. When it left, this page cannot say —
the build records no departures."* Its evidence still opens, from the copy.

**8. The third door.** SIGN IN · **READ THE REST ANYWAY** · NO THANK YOU, four
ledger lines: `asked · signed in · read on · no thank you`. Saying no collapses
the ask permanently into one line that still holds the door open. And the offer
is the true one, not the flattering one: *"Signing in tonight moves none of it:
this register stores nothing on its own side yet. It is the only way to say that
a daybook should outlive a browser."* All three of round 2 promised an account
would carry the keeps across devices; the Worker cannot honour any of it.

## Numbers corrected, and every one verified against the fixture

r02-c printed **4,662** roles carrying no mark. It computed it by subtracting
three overlapping counts from 6,423.

| | r02-c | here | checked against |
|---|---|---|---|
| no mark at all | 4,662 ✗ | **4,781** | counted, never subtracted |
| double-marked | not printed | **119** | 83 remote∧open, 36 remote∧closed |
| carries ≥1 mark | not printed | **1,642** | 1,642 + 4,781 = 6,423 |
| "93% carry no mark" | ✗ (that is visa-silence) | **"about three quarters"** | 4,781∕6,423 = 74.4% |
| new since your last visit | any first-sighting ✗ | **confirmed only** | 145 |

The four mark chips overlap, so the page now says so in numbers under the bar,
and the bar draws the only split that is real: marked, or not. The counts in
note 02 are interpolated from the corpus at render time — a number in a sentence
cannot drift away from the number in the chip above it if the sentence gets it
from the same place.

The diff carries r02-a's clause wherever it appears (the chip's title, the
daybook's night block): *"145 roles here were confirmed on two consecutive
nights since 28 July … What vanished, this copy cannot tell you: the build
records no departures, and a count it does not hold is a count this page will
not invent."* Plus the unconfirmed remainder, 6,278, named as the thing this
page will *not* call new. 145 + 6,278 = 6,423.

## Three bugs found by driving it, not by reading it

- **The keep notch did not exist on desktop.** r02-c hung it at `left: -1.65rem`
  and every chunk carries `content-visibility: auto`, which brings paint
  containment — so the notch was clipped away, and nobody caught it because a
  kept row also changes its background. The row now carries its own left channel.
- **`[hidden]` was losing to `display: flex`.** The morning-after band printed an
  empty country strip and an empty query line underneath itself. One global
  `[hidden] { display: none !important }`.
- **Clerk resolving mid-read threw away the reader's place.** `__onAuth` calls
  straight through `render()`, which renumbers every row. The cursor and the
  open sheet are now remembered *by URL* and re-seated — an index is only a
  place on a list that no longer exists, and "signing in must not cost the
  reader their place" is in the brief.

## Measured, on a private headless Chromium (Playwright, not the shared daemon)

- **Hard gates.** Clerk aborted at the network: register renders (100 rows on
  first paint, 300 free), no sign-in control printed at all, two working doors
  plus the translated line saying why the third is missing. **0 page errors and
  0 console errors** on every pass. `prefers-reduced-motion: reduce`: **0**
  elements with any transition or animation duration; `scroll-behavior: auto`.
- **CLS** cold, over four runs each: **0.0004** desktop fresh · **0.0015**
  desktop returning · **0.000** at 380px with real CDP device metrics (one run
  in four measured 0.0045 there, on the mark-chip row). Getting there needed a
  size-adjusted stand-in face — Inter arrives ~1s after first paint and sets
  8.2% wider than Helvetica (2,442px vs 2,258px for the same string, measured in
  this browser), and every wrapped paragraph moved when it landed.
- **Scroll**, 160 real gestures down the open 6,423-row column: p50 **16.7ms**,
  p95 **17.5ms**, ~12.5k nodes at depth 3,000.
- **380px** with CDP device metrics: horizontal overflow **0**, with the daybook
  open **0**, **no interactive target under 44px**.
- **Keyboard**: 35 tab stops for the whole page (the register is one). At scroll
  depth 9,000px, `j` seats the cursor at row **249** — the row being looked at,
  not a warp. `s` keeps, `a` climbs, `Enter` opens, `d` opens the daybook,
  `Escape` closes it and leaves the register where it was.
- **Locales**: **159 keys**, all eight complete. A DOM sweep of every locale
  found **zero** orphaned English in the chrome — the only Latin text in `ja`,
  `zh-Hans` and `hi` is role titles and company names, which is correct. `<html
  lang>`, `dir` and `<title>` follow. Zero horizontal overflow in any locale.
- **Seven nights simulated across seven dates** with a shifted `Date` and
  carried `localStorage`, screenshots at each.

## Syntax, not just strings

The daybook's entry lines are whole sentences per locale with the role sitting
where that language puts it, built by a `frag()` that substitutes DOM nodes
rather than string-concatenating a label and a value:

```
en   you kept Acquisition Manager · Airbnb
ja   Acquisition Manager · Airbnb を保存しました
de   Sie haben angegeben, sich auf X beworben zu haben
```

Same call site, three word orders. And `1 nights` is gone: the four count labels
that inflect carry a singular and go through `Intl.PluralRules`; ja, zh and hi
simply have no singular key and are never asked.

## Deliberate ceilings

- **`ponytail:` the daybook caps at 4,000 entries.** The ceiling is a browser
  quota, not a design decision. A reader who fills it loses their oldest lines
  silently, which is the one place this page's append-only promise has a floor
  under it. A real fix is server-side and the Worker stores nothing.
- **`ponytail:` the hand lexicon is 24 concepts** (inherited). It covers what a
  job seeker types first; a miss falls back to the census plus the explanation.
  A real bilingual occupation vocabulary belongs in the *build*.
- **`ponytail:` Clerk's own modal is not localised.** Everything this page owns
  translates; the modal is Clerk's.
- **The three AI-written company lines stay English**, marked `lang="en"` and
  footed with their provenance. Translating a claim the build made is closer to
  the forbidden move than leaving it.
- **Distance is a country-to-country anchor measure** (inherited). Berlin to
  Munich is 0. Note 03 says so and every value wears `≈`.
- No companies view. The register's unit is the role.

## Where it is weak

1. **The daybook is a lot of page for a reader who has done one thing.** On
   night two it is a 300-word lede over four lines. The lede earns its length
   only once there are two hands visibly disagreeing in it, and that is night
   three at the earliest. I would cut the lede to one sentence and print the
   rest as a note if I had another pass.
2. **A departed keep still wears its old marks in the live kept view** without a
   date qualifier. The `goneNote` in its sheet says the row is gone, but the ○
   beside the title is a fact from a night that is over and does not say so.
   Only the morning-after view labels its facts with their date.
3. **`applied` and `answered` are one bit each and hold no company.** A reader
   applying to three roles at one company sees three unrelated rungs. The
   product this serves is a referral into a *company*, and the daybook is still
   organised by posting.
4. **The nights strip is honest at true scale and nearly unreadable because of
   it.** Six of seven columns are within two pixels of the floor. Note 07 tells
   you why, and a note is a worse instrument than a chart that could be read.
5. **The follow-up asks about opens, and an open is a weak signal.** A reader who
   opens ten postings to skim them gets asked about three of them. "Don't ask
   about this one" is the escape and it is one press, but the first night it
   fires may read as presumptuous.
6. **Burning is irreversible with a six-second arming window and no undo.** That
   is the correct shape for the promise, and it will eat someone's six weeks.
7. **`?data=tomorrow.json` is the only way to reach the morning-after band**
   without waiting for a real schema bump. The stub is shipped and labelled, but
   a state this important being one query parameter away from invisible is not
   ideal.
8. **The masthead still makes no claim** (inherited from r02-c). The honesty is
   demonstrated everywhere and stated in nine footnotes; a reader who opens
   nothing never meets the argument.
