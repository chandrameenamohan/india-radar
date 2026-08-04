# r01-b "The Night Desk" — judge's card

Driven at 127.0.0.1:8761, private headless instance, 1440×900 and 390×844.
Signed out, scrolled through the free 240, declined, filtered by sentence,
searched, opened entries, walked with the keyboard.

| Criterion | /10 | Weighted |
|---|---|---|
| The ask (25) | 9 | 22.5 |
| Inside (25) | 9 | 22.5 |
| Originality (20) | 9 | 18 |
| **Judge total (70)** | | **63** |

## The ask — 9

The best-composed free sample of the round: 240 roles across 79 companies,
newest first, every country mixed in — a reader anywhere sees something that
could be theirs within a screen or two. The ask arrives exactly where the free
reading ends, states what remains in numbers ("292 more companies and 6,183
more roles"), explains its own existence in the register's voice ("so we can
find out whether anybody actually wants an account, before putting a public
register behind one"), and then does the one thing I have not seen a gate do:
**prints its own telemetry back to the reader** — `ASKED 1 · SIGNED IN 0 ·
DECLINED 0` under the buttons. A page that shows you its counter cannot be
quietly counting you. I declined; the card vanished, the register continued
from row 0241 without moving my scroll, and `ra.ask` recorded `no: 1`.

Why not 10: the reason to say *yes* is still thin. Declining prints everything,
so signing in buys the reader nothing they can name except "you keep your
place" — which the page keeps anyway. That is the brief's own constraint, and
B communicates it more warmly than A or C, but "you would sign in, and you
know why" is not quite true of any variant this round.

## Inside — 9

The register has a rhythm no table has: bands by *the night we first saw each
role*, each with its own count and its own honesty note ("We had not read these
boards the night before, so this is the night we saw these roles — not the
night they opened"). "Tonight — 7 roles" is the single most emotionally
accurate control in the round: the question an anxious person actually re-asks
every day is *what's new*, and B makes it the page's first band — which also
means the page is different tomorrow, and worth returning to. Entries unfold in
place with zero scroll loss; the sticky rail answers "where am I" in roles, not
pixels; the sentence keeps the whole query legible at all times; the URL is the
session, so the page can be *sent to a friend* — alone among the three.
The empty state stays in character and recovers you: "Every word you set is up
in the sentence, in the lamp colour. Put one back and the register comes with
it," with one button that asks the widest question again.

Faults: `j` from row 16,000px deep warped me back to the top (the cursor is a
data structure, not the position of my eye — all three share this); the
company view is an admitted poor cousin; the "anything" input clips its last
glyph at rest.

## Originality — 9

The query as a sentence the reader edits — nine controls that are nine words,
with real `<select>`s and a real search input underneath them, discovered when
my click was intercepted by `aria-label="Choose a country"` — is a control
invented for this page, and it holds under load: choose Japan and the whole
sentence re-composes, the count re-answers, the ledger renumbers. The lamp
colour means one thing (a thing you did); mono means read, serif means said,
and that shape-level honesty survives translation. The night-desk voice is
carried from the headline ("It is late, and somebody is hiring.") through the
band notes to the empty state without once breaking register. This is the
variant I was still scrolling after I had finished testing it — and the one
whose builder's own weakness list (the sentence goes telegraphic in de/ja; the
ja searcher's dead end) reads as the frontier of the idea rather than its
failure.

## What round 2 should keep from B

- The sentence, and the fight to make it compose as prose per-locale rather
  than as translated labels.
- Bands by first-seen night, with per-band epistemic notes.
- The telemetry printed back to the reader.
- The URL as the session.
- The headline's premise: the page knows what time it is for its reader.
