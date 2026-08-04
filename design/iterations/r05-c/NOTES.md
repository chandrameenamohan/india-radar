# r05-c — the comparison plate

**The idea, in one sentence:** the shortlist is the head of the page rather than
a tray at its edge, and the moment two companies are in it they stand in the
same rows — what they do, for whom, why them, who vouched, status, roles open,
staff listed, your record — so the page finally supports the decision the reader
is actually making, which is A or B.

Twelve prior variants shipped a list with a shortlist attached. This one ships a
comparison with a list attached to it.

---

## What was kept and what was rebuilt

A previous agent built this variant and lost the session before writing anything
down. Its data layer and behaviour were sound and are kept whole; its
representation predated Signal 4 and was rebuilt entirely.

**Kept, unchanged** — `build.py` (817 lines, r04-c's taxonomy taken whole per
PRODUCT-1 §7.1, one canon not a fifth), all 789 per-company role shards, the
`data/` outputs, `serve.py`, `qa/cdp.mjs`, and the whole JavaScript behaviour
layer: the two-hands doctrine (`kept_at` set only by the reader; `applied` set
only in `answer()`), the URL state, the copy-out, the day-gated ask, the
keyboard loop, the funnel sheet's prose, the giants set-aside, the yield
grammar. The predecessor's honest copy is better than anything I would have
rewritten for the sake of rewriting it, and it is kept nearly verbatim.

**Rebuilt** — every line of CSS and all the markup-emitting functions. The
predecessor's page was warm paper (`#f7f5ef`), Iowan Old Style serif, and a
mono body: a newspaper. Signal 4 says the founder likes `site/index.html` and
that round 4's cards were *less designed* than it. So the craft here is the live
register's, deliberately and closely:

| the live site | here |
|---|---|
| `#fff` / `#111` / `#8a8a8a` / `#d5d5d5` / `#E30613` | identical |
| Inter, 15px/1.45, `tabular-nums`, `-0.006em` | identical |
| 11px uppercase micro-labels at `.11em`, weight 600 | identical |
| twelve-column grid, 78rem measure, 2rem gutter | identical |
| hairline `1px` rules, structural `2px` ink rules | identical |
| crop marks registering the sheet | identical |
| a reference gutter carrying `001` in mono | the card index |

**Departure in structure, continuity in craft.** The one thing not carried over
is r04-a's serif/mono evidence split, which was on the graft list: the baseline
the founder named is a single sans with mono for apparatus only, and Signal 4
outranks a graft.

### The red

The live site spends red on the active plate and the counts. This page spends it
on exactly one thing: **the reader's own record.** The kept stamp, the A/B column
letters, the kept rule down a card's gutter, the reader's own numbers on the
hand rules. Everything the data says is ink.

That rule is what makes Signal 2 structural rather than a promise. A status word
*cannot* go red here, because red is not available to facts. `Public — per Y
Combinator, Summer 2017` sits in the same ink, at the same size, in the same row
as every other fact, next to a company whose source publishes no status at all.
No red chip, no "not a bet", no rocketship hype. The sheet says this in a
section of its own, *What the red means*.

---

## The measures

All measured on the running page at `127.0.0.1:8743`, served gzipped, by
`qa/measure.mjs` — private headless Chrome via `qa/cdp.mjs`, never the shared
browse daemon. Re-run it; it is written to be re-run rather than trusted.

| | measure | target | measured | |
|---|---|---|---|---|
| **M1** | time to first company card | < 1500 ms | **719 ms** | pass |
| **M2** | curation legible in five seconds | both questions from pixels | see below | judge's call |
| **M3** | time to three apply-tabs | < 60 s, ≤ 6 clicks, 0 navs | **3.7 s, 5 clicks, 0 navs** | pass |
| **M4** | zero unevidenced claims | 0 | **0** claims, 5 refusals | pass |
| **M5** | absence renders as absence | doctrine holds | holds | pass |
| **M6** | the shortlist survives | 3 kept, reload, ask once | holds | pass |

**M1 — 719 ms**, Fast 3G by protocol (1.6 Mbps / 562.5 ms RTT), cache disabled,
two requests before that paint. The number is the page's own
`window.__firstCardPainted` stamp, not the harness's guess. 14 cards are on
that first paint; the remaining 718 arrive with `index.json`. Served: index.html
**27 KB gzipped** (96 KB raw), index.json 117 KB gzipped, a role shard 4 KB.

**M2 —** the fold shot is `shots/r05c-fold-1280.png`. *How did these companies
get here?* — "We read 10,125 companies to get here. 6,895 did not qualify, 2,076
had no job board we could resolve. Every company below is on someone named's
list, and every count is read off the company's own board." *Who didn't make
it?* — the same sentence's two rejected counts, plus the set-aside line naming
57 companies with 100+ roles open and offering them back in one click. I am not
the judge of my own screenshot; those are the pixels available to answer it.

**M3 — 3.7 s, 5 clicks, 0 page navigations**, by real CDP mouse events on
element centres: *Engineering in San Francisco / Bay Area (201)* → the first
card's role button → three role rows. The three URLs land on
`job-boards.greenhouse.io/astranis/...` — the companies' own board, not an
aggregator. The three roles are witnessed into storage; none of them sets
`applied`.

**M4 — 0 unevidenced claims.** Every hit on `rocketship · recently · funded ·
fast-growing · best · top · new` is sorted by rule, not by hand, into three
buckets that all print in full: **5 refusals** (the containing block disclaims
the word — "It will not compute a rocketship score"), **11 evidenced** (the
block carries a link or a count — "New York (287 companies, 3,064 roles)",
"Support operations leaders at fast-growing companies" on a card with a receipt
link), and **0 claims**. The first version of this audit read `<script>` text
and counted the page's own refusals as violations; both were auditor bugs and
are fixed in the script, not papered over in the prose.

**M5 —** 418 companies carry no description; all 418 are in the 789, none is
demoted, and every one states its own condition: *"Not read yet. Their own board
files 98 open roles under these headings: Field Sales, Oncology 34 · …"* — the
board's own words, with nothing composed to fill the gap. 13 have no headings
either and say exactly that. On the sampled shard, 98 roles carry `visa:
unknown` and **0** rendered rows show a chip: silence renders as nothing, never
as a no. The absent cells on the comparison plate are a hairline, not an em-dash
— a dash reads as a value that failed to load.

**M6 —** three kept → hard reload → three still on the plate with *"Kept Aug 5,
2026"*, three cards still marked, stamp still `3 KEPT`, and the hash carrying
`k=billiontoone,langchain,pigment`. The ask fires **0** times in the session
that opened the roles, **1** on the next load, **0** after any answer, and **0**
after a further reload.

**Also verified:** all **789** render when the giants go back in, and **789 of
789** cards carry a credential link in their own evidence line. The keyboard
loop (`j j x`) keeps a company and writes it into the URL. 390 px by real device
metrics: **0 px** horizontal overflow. `ruff check` passes on the whole tree.
Console errors on load: none.

---

## The two gaps round 4 shared, closed

**The shortlist leaves the page.** The hash carries the narrowing *and* the
keeps (`#f=eng&p=sf&g=1&o=roles&k=…`), so the link is the shortlist. `copy the
link` copies it; `copy as text` produces a plain-text brief — each company's
WHAT / FOR WHOM / WHY THEM with its provenance stated, who vouched, the receipt
URL, the status with its source, and every role URL the reader opened. Both
print the result into a textarea on the page, so the reader sees exactly what
they are sending before they send it. A shortlist that arrives in someone else's
link is *not* a keep: it renders with no date and says "arrived in the link you
opened — you have not kept it" until the reader presses keep themselves.

**Something spends the record.** A rule between every hand of ten:
`70 DEALT · YOU KEPT 3 AND OPENED 7 ROLES · 662 STILL AHEAD`, the reader's own
numbers in red, arithmetic over their own record and nothing else. The plate's
own header does the same at the top of the page.

---

## Where this is weak

1. **The plate costs the fold.** The head of the page is the shortlist, so the
   first company card sits at roughly y=700 at 1280×900 — one card visible,
   where r04-b put six on the fold and was praised for it. I spent three
   rounds of edits buying that back (the empty plate became a one-line legend
   band rather than eight drawn rows; the masthead went to one line; the
   provenance note went from four lines to two) and it is still the single
   biggest cost of the stance. If the judge weights the fold the way round 4
   did, this is where the points go.

2. **The comparison is only as good as the descriptions, and 53% are missing.**
   Keep two unread companies and the plate's three best rows are a hairline, a
   hairline, and "Not read yet". The absent state is honest and deliberate, but
   the departure's whole argument is weakest on exactly the companies the
   product exists to surface. `scripts/describe.py` is the fix and it is build
   work, not page work.

3. **Beyond four columns the plate scrolls sideways.** The label rail is sticky
   and the rows move together, so it works, but a ten-company shortlist is a
   horizontal scroll on desktop and the comparison stops being one glance. The
   honest answer is that a ten-way comparison is not a comparison; I did not
   build a column-picker to say so.

4. **`Roles open` and `Staff listed` sit adjacent and invite a ratio.** That is
   deliberate — the footnote says "two numbers, two sources, never divided into
   a score… you can do the arithmetic this page refuses to do for you" — but
   putting them in adjacent aligned rows makes the division very easy, and a
   reader who does it on a stale YC headcount will get a wrong answer that the
   page's own layout encouraged. The order menu's explanation names the 12
   companies where this bites hardest; it is still a real risk the design takes.

5. **Inter is not loaded.** The live site fetches it from Google Fonts; a remote
   font is a network request M1 pays for, so this page names Inter first and
   falls back to Helvetica Neue. On a machine without Inter the type is very
   slightly wider than the baseline's. A self-hosted subset would close it.

6. **The department taxonomy is still a renderer's stopgap** — eleven buckets
   over 2,318 board-written strings, 1,063 roles (3.8%) unbucketed. It is
   r04-c's, unchanged, per the verdict; the sheet confesses it by name. It still
   belongs in the build as one canon.

7. **The ask still fires on the next page load**, not the next day, because a
   pinned snapshot gives the page no other clock. Disclosed in the sheet, fires
   once per company, dies on any answer including "not yet".

---

## Files

- `page.html` — the source; `index.html` is `page.html` with the first
  screenful inlined, so first paint costs one request. Never edit `index.html`.
- `build.py` — `python3 build.py` rebuilds `data/` and `index.html`.
- `serve.py` — gzipped static server (Pages serves gzipped; M1 is a transfer
  measurement). `python3 serve.py 8743`.
- `qa/measure.mjs` — M1, M3, M4, M5, M6.
- `qa/smoke.mjs` — does it render, does anything throw.
- `qa/shots.mjs` — the fold, the plate with two kept, an expanded card, the
  sheet, and both at 390 px by device metrics; prints the overflow check.
- `shots/` — the six PNGs those produce.
