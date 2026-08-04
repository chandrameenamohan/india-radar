# Round 5 — verdict

**Round 4's rubric, the founder's four signals as the contract, the live site
as the baseline.** Everything below was measured on the running pages with my
own CDP harness — private headless Chrome, gzip serving, Fast 3G by protocol,
390 px by device metrics, real key events — before any NOTES.md was opened.
The live baseline was judged from https://roleatlas.sennamind.com/site/index.html
loaded in the same browser (the local `site/index.html` refuses the repo's v10
data and renders its refusal, correctly, instead of a page).

| | Ease /25 | Curation /25 | Representation /20 | Judge /70 |
|---|---|---|---|---|
| **r05-a the register's guide** | **24** | **24** | **18** | **66** |
| r05-b the memo | 22.5 | 23.5 | 17 | 63 |
| r05-c the comparison plate | 23.5 | 23.5 | 18.5 | 65.5 |

**Winner: r05-a at 66. The 68–69 target is not met** — held to honestly in
both directions. The three points over round 4's 63 are real and verified; the
last two are mostly not points a generation round can print (below).

## The measures, across the three

All six pass on all three, and the self-reports were honest to conservative
for the second round running: my first-card times (a **621 ms** · b **630** ·
c **745**, Fast 3G, cache disabled) bracket every claim; my click counts match
every claim (a 5 · b 6 · c 5); three greenhouse apply-tabs on every variant in
under 5 s wall. M4 audits found zero page-voice hype on any page — every
residual hit is an ordinary adjective inside a description line whose
authorship is declared (b's own "11 hits, judgement call" self-report holds at
block granularity; I accept it). M5 holds everywhere, with c's absent states
the most careful ("their own board files 95 open roles under these headings…";
plate absences as hairlines, never dashes).

The deviations found, in doctrine order:

- **r05-b infers keeps from a link.** Open b's shortlist URL in a clean
  browser: it writes `kept_at: today` into the visitor's storage for companies
  they never kept and shows "MY SHORTLIST … kept Aug 5, 2026." The page's hand
  rendered as the reader's verb — r04-a's sin, one degree removed, and
  undisclosed (the NOTES' "no localStorage needed" claim is wrong; storage is
  written). c is doctrine-perfect here ("Arrived in the link you opened — you
  have not kept it," nothing hydrated, keep offered); a hydrates but discloses
  and explains its dating in a sentence.
- **r05-c's ask fires on a same-day reload.** `askDue` triggers on day-change
  *or* pageload-change, justified by a comment ("a pinned snapshot gives the
  page no other clock") that its own epoch timestamps refute — and that r05-a
  disproves by shipping the strict day-gate off the same clock: no same-day
  fire, fires once on a later day, dies on any answer. a's ask discipline is
  the reference implementation now.
- **r05-a's `__firstCardPainted` never fired in my harness** (double-rAF
  starves in idle headless frames); its M1 was mine to witness. Not a page bug
  for a human viewer, but the self-stamping graft exists so the harness can
  read the page's own number, and on a it couldn't.

## The founder's four signals, verified as a reader

**Signal 1 — the card says what the company is.** All three put WHAT / FOR
WHOM / WHY THEM on the collapsed card, legible while scanning; all three
design the absent state deliberately and name `scripts/describe.py` instead of
faking it. b's absent state is the most informative (the board's own team
words in the mono voice reserved for quoted text); c's quotes the board's
filing headings with counts; a's is honest but stamps the backfill script's
name on all 418 unread card headers — the wallpaper the brief warned about,
relocated. Provenance: b and c argue authorship once in the lede/aside (the
brief's letter); a prints a state-varying micro-line per card (more
information, more repetition).

**Signal 2 — status un-editorialized.** Clean pass on all three, checked on
BillionToOne (card 001 of every default view — never demoted) and on Airbnb
itself: "Public, per YC ↗ · Winter 2009" in ink on a; one hairline frame, four
possible words, no rule keyed off the value on b, plus the lede's "a company
that already went public is a fact, not a warning"; on c the enforcement is
structural — red is not available to facts at all. No red, no warning grammar,
no "not a bet," and no rocket-that-made-it hype anywhere.

**Signal 4 — against the live site.** All three carry the tokens faithfully
(I checked the values: same six greys, same #E30613, same 11px/.11em
micro-labels, same #d5d5d5/#111 rule pair, crop marks, tabular numerals,
Inter-first stacks; two variants declined the serif graft and were right to).
Side by side: **a** is the one a stranger would call the same designer's next
sheet — the masthead-as-plate and the red count-stamp have the baseline's
energy cold. **c** is the quietest cold (deliberately: no red until the reader
acts) and the strongest in use — the comparison plate with two kept companies
is the most live-site artifact any round has produced. **b** reads as the
report about the register: authored, but the memo crowds its own showpiece and
its first card doesn't finish above the fold. None of the three is a downgrade
against the baseline; none of the three carried the chart band's energy — the
one live-site element with no descendant anywhere in round 5.

**The shared gaps of rounds 2–4 are closed.** On all three: the shortlist
survives in the URL, one tap copies a real artifact (per-company provenance,
receipts, opened-role URLs, the reopen link), and the record buys sentences —
a's "the only thing on this page that is about you," b's four-clause
arithmetic, c's hand rule every ten cards ("10 dealt · nothing kept yet · 191
still ahead," verified live). The friend gap, three rounds open, is closed —
best by c, adequately by a, wrongly by b.

## The fold trade, judged explicitly

The right yardstick is the baseline's own fold, which spends ~690 px on
masthead, chart and controls before its first data row — and the founder likes
it. Six cards above the fold (r04-b) was a register value, not the baseline's
grammar. Judged so: **a spends best** — first card tops at 573 px and
*finishes* at 792 with the full curation argument above it; **c spends fairly**
— one finished plate-card by ~913, the difference buying the shortlist head,
which on the second visit makes the fold the deliverable itself; **b
misjudges** — 643→965 means the memo's first card is cut by the fold its own
prose set, and its phone header is 1,459 px deep by its own count.

## Why a wins, and what c owns

a is the best *product page in the register's hand*: fastest, best fold, the
only correct ask discipline, receipts interpreted on every card, and cold —
which is how the founder will meet it — it is the page most likely to read as
"better than the live site, on the live site's own terms." c owns the round's
one new idea: the shortlist as the head of the page, two kept companies
standing in the same rows, red meaning *you*, the friend view, the
copy-preview. a wins the rubric; c's plate is the thing round 5 will be
remembered for, and it ships as a graft.

## The grafts — what the shipping page takes

From **c** (the big one first):
1. **The comparison plate as the shortlist's expanded state.** a keeps its
   strip; at two-plus keeps the strip unfolds into c's plate — same rows, same
   YOUR RECORD line, same footnote ("the arithmetic this page refuses to do
   for you").
2. **The link-arrival doctrine, verbatim:** nothing hydrates; "Arrived in the
   link you opened — you have not kept it"; keep offered. Replaces a's
   disclosed hydration and b's silent one.
3. **The copy-preview textarea** — "and here it is, so you can see exactly
   what you are sending."
4. Role rows as full-row links; the em-dash prohibition on absent cells.

From **b**:
5. **Per-cut provenance recomputation** ("I have read the sites of 90 of these
   201…") on a's yield line.
6. **The RATE row** ("300 ÷ 98 = one opening per 3.1 people") on a's card
   rail — stated division, never an ordering, until the founder asks for one.
7. Sticky controls; the two-word giants switch; kept dates on shortlist rows
   (already in a).

Kept from **a** (the chassis): the fold, the masthead-plate, the day-gated
ask, the per-gate interpretive captions, the will-not-say sheet, the
Python/JS cross-check, the priced presets.

Fixes to a itself: drop the per-card backfill stamp to one line in the aside
(keep the absent state's sentence); vary the CB aside by one more per-company
fact; make `__firstCardPainted` stamp off a paint-safe path so the harness can
read it.

## Where the missing two points live

66 → 68 is not another generation round. The variants converged again — same
canon (all three ship r04-c's eleven buckets + `Something else`; b and c print
identical 9,063-role engineering counts; the department canon question is
settled at the variant level and still belongs in the build per PRODUCT-1
§7.1), same URL grammar, same copy shapes, same founder's-gate top ten
(Astranis · Replit · Mercor · MatX · …, one household name in ten). That is
the harness's known exhaustion signal. The remaining points are:

1. **The descriptions backfill** (build work, ~1–1.5 pts). 418 of 789 — 53% —
   have no WHAT/FOR WHOM/WHY THEM, and card 001 of every default view is one
   of them. The founder's strongest signal cannot be fully answered by pages
   that refuse to invent (correctly). Run `scripts/describe.py`; the pages are
   already built to receive the words.
2. **The graft merge above** (integration work, ~0.5–1 pt): a's chassis with
   c's plate and friend doctrine and b's per-cut provenance and RATE.
3. **Founder decisions** (no points, but they gate shipping): default 732 or
   789; whether the plate is the page's head (c's stance) or its expanded
   strip (the graft's stance); whether hiring-intensity may ever order the
   list; whether the register's chart band deserves a descendant on the
   product page.

**Recommendation: do not run round 6 as a generation round.** Ship the graft
merge on a's chassis, run the backfill, and put the result in front of the
founder for the ten-application weekend — six-of-ten unheard-of, by his own
gate. His stall points, if any, are round 6's brief. That was round 4's
recommendation too; round 5 existed because Signal 4 arrived and it has now
been answered on the page: the founder's register and the founder's product
are, for the first time, set by the same hand.
