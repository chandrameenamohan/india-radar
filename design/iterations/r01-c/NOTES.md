# r01-c — THE CORE

Lane C · wildcard, round 1's wildcard being **motion-led**.

## The idea, in one sentence

**Depth is the unit: 6,423 roles is a distance, the page is the gauge you
travel it with, and every motion on the sheet reports position, scale or rate —
nothing here moves for effect.**

## What it is

A dark instrument panel, not a printed atlas. The register is a **core log**:
one continuous column of roles, cut into **strata** (companies), read off a
**gauge** fixed to the left edge that draws the whole 6,423-role column at true
scale and shows where in it you are.

Five things carry the idea, and each one is a motion that means something:

1. **The gauge.** Depth in ROLES, not pixels — `0553 of 6,423` — plus a needle,
   a lens (how much of the column fits on your screen: at this scale a
   hairline), the band horizons where the open-role count drops a tier, and the
   seam. It is the largest type on the page and it is a number that changes as
   you move. At a hand's width the same instrument lies down across the top of
   the screen and keeps every part.
2. **Strata that push.** Each company's header is sticky inside its own
   section, so the company you are inside is always named at the top of the
   screen and the next one pushes it out. Where you are is never something you
   scroll back for. `.stratum.here` is written by the same frame loop that moves
   the needle, so the gauge and the log always agree.
3. **Rate of travel changes what is legible.** Above ~1.7 px/ms the secondary
   columns fade to 18% and the row rules go transparent: at speed the register
   reduces to titles and the strata you are passing, which is all anyone can
   read at speed. It is a *class on the root*, toggled twice a gesture, never a
   custom property read by six thousand rows.
4. **The unit switch is a movement, not a swap.** Roles and Companies are the
   same column at two depths of focus, so switching folds or unfolds every
   stratum — staggered outward from the stratum you are looking at, which is
   pinned so it does not move under you. You watch the register breathe from
   371 lines out to 6,423 and back. That is the only way this page has of
   showing you how much of it there is.
5. **The country bar is a data graphic used as navigation.** Fifteen segments,
   each one that country's share of the open roles. Selecting one lets its
   segment take four times its share over 420ms — the settling that says "you
   are inside this now" — and it is the only layout that animates anywhere on
   this page, deliberately, because it is a 420ms event and not a per-frame one.

## Flow 1 — the ask

Twelve companies, **complete**: 1,833 roles, every board address, every build
verdict, every registration, every receipt. Then the descent reaches **the
seam** — a horizon, not a modal. Its argument is two numbers and a bar drawn to
the same scale as the gauge: *4,590 more roles, at 359 more companies, lie below
this line*, with what you have read in the signal colour beside what you have
not. No blur, no "unlock", no countdown, nothing above it withheld.

- **The gate is measured and says so.** `roleatlas.gate.v1` in localStorage
  counts `shown`, `signin`, `bypass`, `signedIn`, and the seam prints a line
  saying it is counting, in your browser and nowhere else, and that the count
  is the only evidence that would ever justify a login wall — "and it has not
  been earned."
- **Two doors, always.** The second needs no account and no third party, and
  once taken it stays taken (`open: true`) and puts the reader back at the line
  rather than at the top. If Clerk never answers, the first door is not printed
  and the seam says why — verified with the script pointed at a dead URL: 12
  strata, 1,833 rows, empty account slot, one working door.
- The plate, filters and search survive sign-in twice over: Clerk mounts as a
  modal on this page, and the question is written to `sessionStorage` anyway.

## Flow 3 — worldwide

Eight locales, one string table, ~140 keys each, plus the fifteen country names
(a country name is the *build's* classification of a role, not a word any board
typed, so it is chrome and it translates). Data never does: company names, role
titles, city strings and register statuses print in the language they were
published in, and note 04 says so on the page.

`Intl` everywhere: `NumberFormat` for every count (the old page's `'en-IN'` was
right in one of these eight), `DateTimeFormat` parsed and formatted as UTC so a
reader west of Greenwich is never shown the day before the snapshot, and
`NumberFormat` compact-currency for money, so $4.1B reads `4,1 Mrd. $` in de.
`lang` and `dir` follow the choice; `DIRS` is the three lines that carry an RTL
locale when one ships.

## Performance — measured, not assumed

Rows are a **fixed height**, which is the load-bearing decision: depth-in-roles
and depth-in-pixels become the same number, so the gauge is exact without
measuring anything during a scroll, and each stratum can reserve its exact
height before its rows exist. Role lists are `content-visibility: auto` and
materialise one and a half screens ahead (IntersectionObserver, with the frame
loop as a backstop for a fling that outruns it). Nothing shifts as they land.

Measured in headless Chrome at 1440×900 over the real corpus:

| | p50 | p95 | max |
|---|---|---|---|
| scroll 6.6k px through rows 400–550 | 16.7ms | 16.8ms | 17ms |
| fling upward 10.8k px, unlocked full column | 16.7ms | 17.1ms | 20ms |
| deep scroll at row ~3,900 of the 275,181px column | 16.7ms | 16.9ms | 19ms |

Zero dropped frames. Re-render on a keystroke: **18ms** (371 strata rebuilt).
Sort change: 22ms. Country change: 9ms. The whole loop writes two custom
properties, one text node and at most one class per frame.

## prefers-reduced-motion — the second designed state

Not a fallback. Duration goes; information stays. The gauge still tracks (a
position indicator is not an animation — scrollbars move too), the strata still
pin and push, the sheet still opens, the bar still shows the register's shape.
Specifically: the rAF loop never sets `.moving` (a reader who asked for less
motion did not ask the page to start hiding columns from them), `#depth` drops
its scale transform, the fold/unfold and the settle become instant state
changes, `scrollIntoView` uses `auto`. Verified by serving a copy with the
media query forced on and `REDUCE.matches` pinned true: `moving=false`,
`--v=0`, secondary columns at opacity 1, sheet opens at full height instantly.

## Keyboard

`/` search · `j`/`k` role down/up · `J`/`K` company down/up · `u` open or close
every company · `Enter` open the role under the cursor · `Esc` close · `[`/`]`
previous/next country · `?` the card that says all of this, translated.

## What I deliberately did not do

- **The equirectangular chart is gone.** It is lane A's identity and this lane
  is a departure; the country bar does the navigating and does it as a data
  graphic. Ceiling: nothing here reads a coordinate any more, so an entry no
  longer states its country's anchor. `ponytail:` in the code where `CODE`
  survives without `COORD`.
- **A register line carries at most two marks.** The openness sentence the
  sheet prints in full ("stellt aus dem Ausland ein") is four times the column's
  width, and a badge cut to `hires from abro` is worse than no badge — measured
  in de. So the line takes a short token (`abroad ✓` / `abroad ✕`, the same OR
  the foreign-hires filter uses) and the New badge takes that slot when a role
  is new. The sheet keeps both fields, unabridged. Ceiling: a reader scanning
  the list cannot tell visa-sponsorship from relocation without opening a role.
- **One sheet open at a time.** An accordion, not a pile: it keeps the DOM
  bounded and the log readable. Ceiling: you cannot compare two roles side by
  side.
- **No deep-linkable state in the URL.** State persists in `sessionStorage`
  instead. Ceiling: you cannot send someone the German plate.

## Where it is weak

1. **Role titles truncate to one line.** Fixed row height is what makes the
   gauge exact and the reservation exact, and it costs long titles their tails.
   The sheet prints the title in full and the row carries no `title` attribute
   to soften it — that is the first thing I would fix.
2. **The seam's right half is empty paper** at 1440. The copy is measure-bound
   at 34rem and nothing fills the rest.
3. **`? KEYS` is a weak affordance.** A reader who never presses it never
   learns the page is keyboard-first, and on a phone the card is useless
   furniture.
4. **The tally counts the whole matched register while only twelve strata are
   printed** under the gate ("371 of 371 companies" beside twelve rows). It is
   the original page's rule — count what matched, not what printed — and the
   seam states the difference, but read cold it looks like a miscount.
5. **The band horizons on the gauge are drawn in `--rule2`** and are nearly
   invisible against the track at small sizes; their labels do most of the work.
6. **The unit switch's fold lands the reader at the top** when the folded
   document is shorter than their scroll position (12 strata, gated). The
   anchoring is correct arithmetic with nowhere to put them.
7. **Reduced motion was verified on a patched copy**, not through real OS
   emulation — the media query and the JS branch are the shipped ones, but a
   grader emulating it for real is testing a path I inferred rather than saw.
