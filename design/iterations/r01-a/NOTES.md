# r01-a — The Bound Volume

## The idea, in one sentence

The page inherited an atlas **plate** and stopped there, so this round gives it
the rest of the book: an edition imprint, a key to its marks, a running head, a
bookplate, signature marks where the quires are sewn, and — between its back
pages — a bound-in reply card, which is what each of the brief's three flows
turns out to want.

## Why that, and not something else

Lane A's bet is that the existing language is good and has only been applied to
half the page. It is, and it had. The masthead is an atlas plate; the register
under it is a well-set list. The gap is not *style*, it is **apparatus** — the
furniture a reference volume carries that a single loose sheet does not:

| A volume has | The page had | Now |
|---|---|---|
| an edition imprint | nothing | the language control **is** the imprint |
| a key to its marks | nothing — six meanings of one red, never stated | the key card |
| a running head | nothing; no answer to "where am I" at row 400 | sticky running head with a traverse bar |
| signature marks | 6,423 undifferentiated lines | a quire mark every 32 lines |
| a bookplate | a gate that measured invisibly | every byte it keeps, printed |
| a tipped-in reply card | — | the ask, bound in where the paper stops |

Each of the three flows is answered by one of those rather than by a mechanism
imported from somewhere else. That is the whole design argument.

## Flow 1 — the ask, as a bound-in card

**The abridged binding.** A signed-out reader gets 40 complete register lines —
real companies, real roles, real places, the receipt that says which board we
read and when, the absences printed as absences. Then the paper stops and the
next thing on the sheet is a card. No overlay, no dimming, no blur, no
countdown, nothing above it touched.

Two answers, and **both print the rest**:

- *Ask for the complete binding* → Clerk's modal, on this page.
- *Print the rest of this copy anyway* → prints it, asks nothing, records a no.

The card says why out loud: it exists to be counted, the count is the only
evidence that would justify ever moving the corpus behind the Worker, and we
would rather find out that it does not. That sentence is the design — an ask
that explains its own instrumentation cannot read as a toll booth.

**The invariant.** `entitled` is true when the reader signed in, when they
answered by printing, **or when we could not ask at all**. Clerk missing at
`load`, `Clerk.load()` throwing, or four seconds of silence all resolve to
*absent* → the copy prints in full, no control is shown that cannot work, and
the bookplate says the binding office did not answer. Verified with the provider
black-holed at DNS: 200 rows, no card, `ra.ask.shown` never incremented.
`clerk-blocked.html` beside this file is a generated fixture for driving that
state in a browser (`make-clerk-blocked.py`).

**Where the ask does not appear:** a filtered register that fits. Nine results
is an answer, and asking on top of an answer is a toll.

**The measurement** is five values in `localStorage` — first opened, edition,
shown, answered/how, could-not-ask — and the bookplate at the foot of the page
prints all five with a control that burns them. There is no analytics script on
the page to send them with, and the bookplate says so.

**Your place survives** sign-in, sign-out, reload, and a change of edition:
plate, unit, sort, search term and every filter are written to this browser and
restored. A `?view=` in the URL still beats the memory — a link is someone
sending you a register.

## Flow 2 — inside

- **Signature marks.** A book is printed in quires, and the binder's guide is a
  single letter at the foot of each quire's first leaf. Every 32 lines the
  register strikes one — A B C D E F G H I K L M N O P Q R S T V X Y Z, then
  doubling, the compositor's sequence that skips J, U and W. 6,423 lines is a
  wall; 6,423 lines sewn in quires is a volume, and the eye gets a foothold
  every 32 rows that no rule alone gave it.
- **The running head.** Sticky, and the only fixed thing on the page. Plate,
  quire, the span of lines under your eye, and a **traverse bar** drawn to
  scale: the whole register as a track, what this copy prints as a solid
  segment, the viewport as a red bracket. It is the only place the abridged
  binding is visible as a *proportion*, which is what makes the card's numbers
  checkable rather than assertable.
- **The company column, quieted.** The register sorts by open roles and
  Databricks holds 295 of them, so the roles view printed the same company name
  in ink on 295 consecutive lines. It now takes ink where the company *changes*
  (and at every quire head) and the margin's grey where it repeats — the exact
  discipline the gutter's coordinate already used, one column over. Nothing is
  dropped; the boundaries become the rhythm.
- **Scrolling turns the page.** The sentinel *is* the fold button, so the
  automatic path and the pressed path are one line of code and cannot disagree.
  The button stays, because it is the thing that states what is behind it and
  because a reader who never scrolls must still be able to turn the page. Both
  stop at the binding — a page that auto-loaded past its own ask would be a gate
  that never asked. It is bounded at five automatic turns, then the reader
  presses (see *Two bugs the running found*, below).
- **Typing is no longer a stutter.** A render over 6,423 roles is a 270–360ms
  blocking task — measured, and the same on the original page as on this one —
  so answering every keystroke synchronously meant typing "engineer" cost eight
  of them. The search box alone is debounced at 120ms. Measured end to end,
  typing that word at fourteen characters a second: **0ms blocked per keystroke
  and 502ms to settle, against 250–300ms blocked per keystroke and 2,444ms to
  settle on `site/index.html`.** Same eight keystrokes, same 2,270 results.
  Selects are one decision and still answer instantly; a blur answers instantly.
- **Keyboard.** `J`/`K` walk the register by line with a red cursor spine,
  `Enter` opens the entry, `←`/`→` turn plates, `/` jumps to search, `?` opens
  the key, `Esc` closes. All six are printed in the key, because a convention a
  page invents and does not state is folklore.
- **Reduced motion** is one rule at the end of the sheet that kills every
  animation and transition, and `scrollIntoView` reads the same query before it
  chooses a behaviour. Verified with `--force-prefers-reduced-motion`: sweep
  `display: none`, transitions at 1µs, plate still turns.

## Flow 3 — the edition

The language control is the **imprint**, in the margin where a volume states its
own identity, and footnote 08 states what an edition does and does not
translate. 236 keys × 8 editions, all written, none machine-defaulted.

- **`i18n-check.py`** holds the eight key sets to each other, to their
  `{placeholders}`, and to the code paths that ask for them. It exits non-zero.
  "I read it carefully" is not a translation strategy.
- `count()`'s hardcoded `'en-IN'` is gone. Numbers, dates, currency and
  collation all go through `Intl`, built once per edition. Money uses compact
  currency notation, because `B`/`M` are English abbreviations of scale words
  that are not shared (`Mrd.`, `億`, `करोड़`).
- **Country names are apparatus, not evidence** — the fifteen come from
  `src/countries.py`, not from any board — so they are set by
  `Intl.DisplayNames`. Company names, role titles, cities, board departments
  and every registrar's own wording stay exactly as their sources wrote them: a
  Berlin board's role title is German in the Japanese edition too.
- `dir` is set from the table and every edition declares one; RTL is three lines
  away rather than a rewrite.
- Swept at 380px and 1440px in all eight: the only Latin left in page chrome is
  `ROLE·ATLAS`, `Clerk`, the `Enter` keycap, and the edition names in their own
  languages. Zero horizontal overflow anywhere.

## Craft, measured rather than eyeballed

- `--ink-3` was `#8a8a8a` — **3.0:1**, and every micro-label on this page is
  11px. The page's smallest voice was failing AA everywhere it spoke.
  `--ink-3` and `--wash` were re-solved *together* against each other, because
  the real failures were on selected and hovered rows: now grey-on-paper 5.10,
  grey-on-wash 4.76, red-on-paper 4.88, red-on-wash 4.56. A full-page contrast
  sweep (including the key and the card) returns **zero** failures.
- The repeated gutter coordinate was `#c6c6c6` — **1.8:1** live text. The
  discipline was right and the mechanism was wrong: the *change* is now struck
  in ink and bold, and the repeat sits at the margin's own legible weight.
- `pointer: coarse` alone matched in headless and blew every plate chip to 44px
  on a 1440px sheet; it is now `and (hover: none)`. Under it the filter selects
  grew from 33px to 44px — the bank was the one control that failed the thumb.
- Footnote cross-references pointed at the wrong paragraph. The openness note is
  **04** and the derivation note is **06**; the page shipped saying "note 03".
  On a page whose argument is that its claims are checkable, a citation that
  resolves to the wrong note is worse than none.
- Zero console errors and zero exceptions on load, in every edition, at both
  widths.

## Two bugs the running found — worth writing down, because neither was visible in the source

**1. The scroll-pager ran away.** With the viewport pinned at the foot of the
page — End held down, a trackpad flung, a test scrolling to `scrollHeight` in a
loop — the fold never leaves the observer's margin, so it re-fired the instant
its cooldown cleared and the register chased itself toward six thousand rows,
each render heavier than the last. The page stopped answering. Fixed by making
the automatic path a *courtesy with a bound*: five turns of two hundred, then
the reader presses, and a press re-arms the next five (`ev.isTrusted` keeps the
observer's synthetic click from topping up its own allowance).

**2. And then it turned exactly one page.** The bound revealed a second bug
underneath it. An `IntersectionObserver` reports *changes*: the fold that
`render()` built during the cooldown announced itself visible once, was refused
because the cooldown was running, and — its state never changing again — went
silent for good. The cooldown now re-observes rather than just clearing a flag.
Measured before: 200 → 400 → 400 → 400 → 400. After: 200 → 600 → 800 → 1000 →
1200, then it stops and says what is left.

Neither of these is findable by reading the diff, and both would have read as
"the scroll is a bit odd" rather than as a defect.

## What I deliberately did not do

- **`ponytail:` the keyboard cursor is a cursor, not a roving-tabindex listbox.**
  The full pattern wants `aria-activedescendant` and a container that owns the
  arrow keys; the container here is two DOM subtrees whose row order is visual,
  not linear. The tab order is left alone on purpose — a role title *is* its
  apply link, and taking those out of the tab order to make the register one
  stop would trade a real affordance for a tidy number. Ceiling: correct on a
  keyboard today, one step short of what a screen-reader user gets from a real
  listbox.
- **`ponytail:` the binding is 40 lines, hardcoded.** It should be a measure of
  *reading*, not of rows — three screens, or one quire and a bit. Ceiling: one
  constant, and the day it wants to be adaptive it wants a scroll-depth
  measurement the page does not take.
- **No RTL edition ships.** `dir` handling is in, per the brief; Arabic and
  Hebrew would need the plate's own east-west orientation thought about, which
  is a design question, not a translation one.
- **The gazetteer descriptions are not translated**, and that is on purpose:
  they are a machine's prose about a company, marked as such, and translating
  them would put a second machine between the reader and a claim that already
  carries one.

## Where it is weak — the evaluator will find these anyway

1. **The Europe inset is still crowded at 380px.** GB's 263-company dot and its
   chip sit hard against France's. I scaled the phone dots by a constant (which
   preserves the area encoding a cap would destroy) and it is better, not
   solved. The honest fix is hand-placing four more labels at that measure.
2. **Blocking Clerk produces one console line** — `net::ERR_CONNECTION_REFUSED`,
   the browser reporting a `<script src>` that did not arrive. It is not from
   this page's code and nothing can suppress it, but if you block the provider
   and read the console, it is there. Unblocked: zero.
3. **The running head's quire letter reads off the *first* visible line**, so on
   a tall desktop screen spanning five quires it says `A` while `B`–`F` marks
   are visible below. Correct by the letter of what a running head is; briefly
   confusing at 1000px tall.
4. **The traverse bar is nearly invisible on an abridged copy** — 40 of 6,423 is
   0.6% of the track, floored at 3px. That is the honest drawing and it is the
   point of the mark, but it reads as a speck before it reads as a scale.
5. **The register still opens on 295 Databricks roles.** Quieting the repeated
   company name gives the block a rhythm; it does not change the fact that the
   canonical sort front-loads one company. A per-company cap in the roles view
   would be a different, and possibly better, register.
6. **`?` is a poor discovery affordance.** The key is reachable from a labelled
   `KEY` button in the running head, so it is not hidden — but the *keyboard*
   is only discoverable by opening the key, which is a small circle.
7. **The place is restored from `localStorage` without ceremony.** Reload with a
   filter set and the filter is still set. The bookplate says so and `Forget
   this copy` clears it, but a reader who expects a fresh page gets a
   remembered one.

## Files

| | |
|---|---|
| `index.html` | the variant |
| `i18n-check.py` | holds the eight editions to each other; exits non-zero |
| `make-clerk-blocked.py` | regenerates the fixture below from `index.html` |
| `clerk-blocked.html` | generated: the page with Clerk pointed at a dead host |

```bash
python3 -m http.server 8741 --bind 127.0.0.1
# http://127.0.0.1:8741/design/iterations/r01-a/index.html
# http://127.0.0.1:8741/design/iterations/r01-a/clerk-blocked.html
python3 design/iterations/r01-a/i18n-check.py
```
