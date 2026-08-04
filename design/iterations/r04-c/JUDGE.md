# r04-c — The Guide · judge

| | |
|---|---|
| Ease (25) | **22** |
| Curation-legibility (25) | **23.5** |
| Representation (20) | **17.5** |
| **Judge total (70)** | **63** |

**New curve.** First PRODUCT round; scored on ease · curation-legibility ·
representation, not comparable to rounds 1–3. Anchor: faultless-with-no-POV
is a 62. **Winner of round 4.**

Driven, not read: my own CDP harness on a private headless Chrome (repo served
gzipped on 8761 — not this variant's own `serve.py`, which also works), Fast 3G
by CDP, 390px by device metrics, measures re-run with my own instrumentation
before NOTES was opened.

## The measures, verified

- **M1 — pass.** 275 ms to the first real card (the 185 ms skeleton
  "Pulling the cards up…" does not count and my first probe was corrected for
  it). The one-request first paint — fourteen cards, both menus, the funnel
  counts and all 57 giants inlined in `head-data` — is why. Claim of 725 ms is
  conservative against mine.
- **M2 — pass, the most human answer.** *"I read 10,125 companies to build
  this. 6,895 didn't qualify. These 789 are hiring right now."* First person,
  five named gatekeepers with counts in the second sentence, receipts on every
  visible card. "Who didn't make it" is answered in the headline number and
  fully in the funnel one click away — a's fold says slightly more (the 2,076
  clause is on-screen), but no cold viewer of this screenshot could fail
  either question.
- **M3 — pass, fewest clicks: 5.** One opener link (*engineering in San
  Francisco / Bay Area (201)* sets both menus), one expand, three role rows —
  three Astranis tabs on Greenhouse, 0 navigations, 1.8 s scripted. The
  openers are the round's best answer to the blank-page moment.
- **M4 — 0 failures** across 36 hits, and this is the variant that risks the
  most words per claim; every warm clause sits in the node with its link.
- **M5 — pass, and beyond the letter.** Null-amount cards state their silence
  (*"an editor's call. No funding number behind it"*); visa silence is a
  sentence, not a blank: *"Their board says nothing about visa sponsorship on
  90 of them — that is silence, not a no."* Openness read from both fields
  (1,891 / 947 — correct against my fixture count, where r04-b is not).
- **M6 — pass, once and never again, with one spirit-deviation.** Keeps
  survive with dates; the strip adds the one honest time-fact the pinned
  corpus supports (*"you opened 1 of them · it is still on their board on
  Aug 4, 2026"*). The question fires exactly once and dies on any answer —
  but it fires on the *next pageload*, same evening, because with a pinned
  snapshot "an earlier day" cannot exist and the variant chose session as the
  witness. Disclosed (weakness 7). In production, with a real clock and
  `opened.at` already stored, this must become day-gated like a and b. The
  ask's caption — *"I am asking because I cannot know. I watched this page
  hand you 3 links — that is the page's hand, not yours."* — is r03-c's
  mechanism finally wearing its reason on the outside.

## Ease — 22

Five clicks cold-to-three-tabs is the round's shortest path, and this is the
only variant that solved the roles-fetch problem instead of describing it:
`data/roles/<slug>.json`, ~6 KB per expand, so an expansion never waits behind
9.8 MB even throttled. Costs: three cards above the fold, not six — the opener
buys M2 and pays in scan rate (the founder's 20-second six-card skim is five
screens here); generic queries outside the three openers fall back to two
native selects; no keyboard path; the tall cards make the 789-card scroll the
longest of the three.

## Curation-legibility — 23.5

The gate captions are the round's centrepiece: six sentences that *interpret*
every credential without ever exceeding it — *"a tracker's call on size, not a
funding fact. $1B means the launch already happened; the 97 open roles are
what I would go on"* turns CB Insights' weakest-evidence rows into an argument
for the one 100%-coverage signal. The YC caption prints the two stated numbers
PRODUCT-1 asked for, verbatim shape: *"YC lists 65 people, their own board
lists 90 roles."* The set-aside strip is the best giants treatment of the
round — all 57 named with counts, each a click that puts it back: nothing
concealed, and the *reason* stated ("you have heard of those"). The funnel
panel — "Where the other 9,336 went" — carries the freshness confession and
the Airbnb warning. Deductions: the `Something else` department bucket (1,063
roles) is reachable through *any field* but absent from the menu, and nothing
on the page says so — the one silent exclusion here; the Bay-Area merge means
someone who means San Francisco proper cannot say so.

## Representation — 17.5

This is the founder's sentence — *"I did the hard work to find the next
rocketship startup"* — rendered as a page, in the first person, with receipts.
Of the three, it is the one a tired person at 11pm would *feel* did the work
for them, and the one they would quote to a friend. The stance's named risk —
six sentences carrying 291 identical CB Insights cards — is real: at card 400
the aside repeats, softened only by the interpolated role count, and the YC
cards (whose captions genuinely vary by batch, status and headcount) carry the
deep scroll. The warmth thins; it does not curdle. What it never does is
invent: every aside I checked terminates in a stated fact, and the strip, the
openers and the ask are all mechanisms, not decoration.

## What must be fixed before this ships

Day-gate the second-visit question off `opened.at` once the clock is real;
put `Something else` in the field menu; vary or tighten the CB Insights aside
(the interpolated count is the right instinct — one more per-company fact
would end the wallpaper); consider a San-Francisco-proper sub-answer under the
Bay Area merge.
