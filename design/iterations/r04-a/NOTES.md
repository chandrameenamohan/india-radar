# r04-a — THE DOSSIER

**The idea, in one sentence:** the card is a dossier entry someone typed after
doing the diligence — company name first and largest, its own named credential
underneath with the receipt one click away — and the first sentence on the page
is that diligence, counted.

Nothing on this page is chrome. There is no masthead, no edition, no plate, no
card border, no shadow, no icon that is not a link. What is left is type, a
hairline between entries, and two numbers per company: how many roles are open
on their own board tonight, and how many of them are yours. The typographic
discipline is r01-a's and r03-a's, inherited on purpose; the grammar is not. A
register opens with its own name. This opens with **what was thrown away**.

```
We read 10,125 companies to get here. 6,895 didn’t qualify; 2,076 more had no
job board we could find. These 789 are hiring tonight, and every one is here
because a named gatekeeper put it on a list — receipt on the card.
```

One typeface for what a person wrote (the sieve, the company's name, the
credential, in a text serif) and one for what a machine counted (roles, cities,
departments, dates, dollars, in mono). That split is the whole visual system,
and it is also an honesty device: nothing counted can be mistaken for something
claimed.

---

## How to run it

```bash
python3 -m http.server 8741 --bind 127.0.0.1        # from the repo root
open http://127.0.0.1:8741/design/iterations/r04-a/index.html
```

Rebuild the two derived shards after any change to `design/fixture-v2/`:

```bash
python3 design/iterations/r04-a/build.py
```

Re-run the six measures against a private headless Chrome (never the shared
`/browse` daemon):

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new \
  --remote-debugging-port=9741 --user-data-dir=/tmp/r04a-profile about:blank &
node design/iterations/r04-a/measures.mjs          # or: … measures.mjs m3
```

### Files

| file | what it is |
|---|---|
| `index.html` | the whole product — markup, CSS, JS, no dependencies, no fonts fetched |
| `build.py` | the fixture-side build: department families, city fold, the two shards |
| `seed.js` | **derived.** The first screen (24 cards) + the counts the first paint needs |
| `grid.json` | **derived.** Per company, role counts by department family × city |
| `measures.mjs` | M1–M6, run against the running page with real mouse events |
| `cdp.mjs` | a dependency-free CDP client (Node 22's global `WebSocket`) |

Data comes from `../../fixture-v2/` — `cards.json` for all 789 cards,
`companies.json` (9.8 MB) fetched last and only for role rows. Nothing outside
this directory is written.

---

## The six measures, as measured

Run 2026-08-04 against `http://127.0.0.1:8741/…/r04-a/index.html`, Chrome
150 headless, 1280×900. Full transcript reproducible with `node measures.mjs`.

**M1 · time to first company card — PASS.** 559 / 568 / 571 ms across three
cold loads, Fast 3G (1.6 Mbit/s, 150 ms RTT) with the cache disabled. Target
< 1500 ms. Read off the page (`performance.now()` in the frame after the first
card exists), not off a poll.

> How: PRODUCT-1 §7's shard, done honestly. `index.html` (46 KB, 13 KB
> gzipped) and `seed.js` (33 KB, 10 KB gzipped) are the entire first paint —
> two round trips, no fonts fetched, no CSS file, no framework. Measured
> against a plain `python3 -m http.server`, which does not gzip; on any server
> that does, it is a third of that on the wire.
> `cards.json` (470 KB), `grid.json` (382 KB) and `companies.json` (9.8 MB)
> follow in that order, each one only when the page needs it. Until they land,
> the page prints the totals it knows and says it is still reading; it never
> counts the 24 cards it happens to be holding.

**M2 · the curation is legible in five seconds — PASS.** Screenshot at
`/tmp/r04a/m2-load.png`. The first text node on the page is the funnel; the
second line names all six gatekeepers with counts (`Y Combinator 298 · CB
Insights 291 · SEC EDGAR 101 · Forbes 78 · TechCrunch 20 · FinSMEs 1`); and the
first five cards each carry their own credential — *Y Combinator, Summer 2017 ·
YC's directory lists 300 people ↗*, *On CB Insights' unicorn tracker ↗*, *An
editor at Forbes put it on a list ↗*. Both questions are answerable from the
pixels: how they got here, and that 6,895 didn't qualify and 2,076 more had no
board we could find.

**M3 · time to three apply-tabs — PASS.** **3.0 s · 6 clicks · 0 page
navigations · 3 tabs opened** on the company's own board. Script: *backend
engineer who wants San Francisco.* Clicks: `engineering` → `San Francisco` →
`40 engineering roles in San Francisco →` → three `Apply ↗`. The three tabs
were `jobs.ashbyhq.com/mercor/…`. First three companies under that cut: **Mercor
45→40, Baseten 36, LangChain 24** — the list PRODUCT-1 §2 predicted, not the
Anthropic/OpenAI/Databricks one.

**M4 · zero unevidenced claims — PASS.** 242 matches of
`/rocketship|recently|funded|new|top|best|fast-growing/i` in the fullest DOM the
page can render (all 789 cards, sieve open, a department cut on, one card
expanded onto its role rows) — **0 without a link, a date or a count in the same
node.** The words *rocketship* and *recently* appear nowhere; `funded` appears
once, inside `2,925 qualified as funded software companies`; `top` appears only
in *one of the companies YC itself flags as a top company*, inside the anchor
that links YC's page. Most of the 242 are the string "New" in `New York` — which
is why every city on this page is printed with its role count beside it.

**M5 · absence renders as absence — PASS.** Ten companies with `amount: null`,
sampled from `cards.json`: **0 excluded** from the default view, **0**
placeholder elements (`0`, `—`, `n/a`, `no`, `unknown`) anywhere in their cards,
**0** dimming. Their gate lines simply contain no number — *An editor at Forbes
put it on a list ↗*. For roles: AfterQuery, 30 of 31 roles say nothing about
hiring from abroad — all 31 rows render, none dimmed, 30 carry no mark at all,
and the expanded card closes with the stated silence: *"31 shown here: 1 state
they can hire from abroad, 0 state they cannot, and 30 say nothing that bears on
it and are exactly as open as the rest."*

**M6 · the shortlist survives — PASS.** Kept 3 → witnessed 3 opened role URLs →
hard reload with cache ignored → all 3 still pinned with their dates and the 3
witnessed opens. Same-day questions asked: **0**. On a simulated next visit
(`window.__atlas.simulateNextVisit()`): exactly **1** — *"On Aug 4, 2026 you
opened 3 roles at BillionToOne. Did you apply?"* `yes · no · not yet`. After
answering: 0, and 0 again after a reload plus two more simulated days.

**Beyond the checklist — the founder's gate.** Default first ten:
BillionToOne · LangChain · Pigment · Harness · Astranis · Horizon 3 AI ·
Justworks · Gusto · Socure · Kong. Engineering-in-San-Francisco first ten:
Mercor · Baseten · LangChain · Drata · Astranis · Eight Sleep · Together AI ·
Discord · Grow Therapy · Sigma Computing. One household name in twenty.
`hide the giants` is on by default and the yield line always prints what it
costs (57 companies with the cut open, 22 under engineering-in-SF).

**One invariant beyond the six, because two implementations of one rule is a bug
waiting to happen:** `build.py` counts the department × city index in Python and
`index.html` filters the role rows in JavaScript. Checked across **29,982
company × family × city combinations: 0 mismatches.**

---

## What is on the page and why

- **The gate line is the point.** One per company, different on every card,
  always a link to the receipt: `Y Combinator, Winter 2016 · YC's directory
  lists 500 people ↗` · `Filed a Form D with the SEC for $4,082,050,250 on Dec
  16, 2025 ↗` · `TechCrunch reported a $65,000,000 round on Oct 5, 2025 ↗` ·
  `On CB Insights' unicorn tracker — their list of companies valued at $1B or
  more ↗` · `An editor at Forbes put it on a list ↗` · `FinSMEs reported a
  $13,000,000 round on Jul 31, 2026 ↗`. All six shapes verified rendering.
- **YC's status has the chip slot right of the name**, on the 32 companies where
  it is not Active: `AIRBNB [PUBLIC — PER YC ↗]`, `BREX [ACQUIRED — PER YC ↗]`.
  Red, outlined, unmissable, and attributed. That slot is also §5.4's reserved
  slot for problem #2's status.
- **Two controls, as words, not dropdowns.** `I'm in engineering 8,122 · sales
  4,979 …` / `looking in San Francisco 4,257 · New York 2,719 …`, and every
  option prints what it holds before you press it — r02-b's yield rule applied
  to the control instead of the result.
- **`hide the giants`** on by default, at 100 or more open roles, with the cost
  printed every time.
- **Keeps** are keyed on the company, carry `kept_at`, `roles_open_at_keep`,
  `opened_role_urls[{url,title,opened_at}]` and `applied: null`, and live in
  `localStorage`. `applied` is written by exactly one code path: the reader
  pressing `yes`/`no`/`not yet`. The `Apply ↗` handler writes only a witness.
- **141 role rows carry a first-seen date**, across 78 companies — the only
  dates `first-seen.json` calls *confirmed* (board read on both nights). The
  other 6,505 dated URLs mean "we looked for the first time", which is not a
  fact about the role, and are not carried. No badge is built on any of it.

---

## Where it is weak

1. **Five company cards above the fold at 1280×900, not six.** The lede, the
   gate census, the two control rows and the yield line cost ~300 px before the
   first card. Every line of that is load-bearing and I would not trade any of
   it for a sixth card, but the spec said six and it is five.
2. **The department families are this page's one judgement call, and they are a
   keyword rule.** 2,300 board-typed department strings do not group themselves.
   14 families cover 22,837 roles; **4,852 (17.5%) match nothing** — `토스코어`,
   `Professional Services`, `G&A`, `Applied AI`, and 746 others — and a
   department cut excludes them. The page prints that number and those names
   whenever a department cut is on, which is the doctrine's minimum, but it is
   still the one filter on this page that deletes something. The honest fix is
   a department vocabulary in the build, exactly like FINDINGS #3's bilingual
   occupation vocabulary, and no renderer can reach it.
3. **The controls are a chip rail, not the two dropdowns PRODUCT-1 §4 drew.**
   A native `<select>` costs two clicks to answer; two of them plus an expand
   plus three applies is 8, and M3's budget is 6. The chip rail makes every
   common answer one click and pushes the tail of 39 cities into a popover.
   Deliberate deviation, bought with the click budget.
4. **Pressing `Apply ↗` on a company you have not kept creates the keep.**
   Witnessing an opened URL needs a company-keyed record to hang it on, and
   problem #2 cannot reconstruct that later. It is visible (the strip appears,
   the button flips to `◆ kept`) and reversible (`drop`), but it is the page
   deciding something on your behalf.
5. **Ranking does not demote the 32 Acquired/Public/Inactive companies.** Their
   status is printed loudly, but BillionToOne (Public, per YC) is still the
   first card in the default order because it has the most open roles under 100.
   Whether a "next rocketship" list should rank on status is a founder's call,
   not a renderer's, so it prints and does not sort.
6. **Two derived files with no staleness check.** If `design/fixture-v2/`
   changes and `build.py` is not re-run, the first paint shows 24 stale cards
   for ~300 ms before `cards.json` corrects them. That reflow is the only
   warning; a content hash would be better.
7. **The TechCrunch amounts are the build's, and two of the twenty disagree with
   the headline they link to** (Fundamental Research Labs: the record says
   $30,000,000, the article slug says 33 million; Harper: $47M vs 45m). The page
   prints what the record holds and links the receipt, so a reader can catch it
   — which is the doctrine working and an extraction bug staying open.
8. **The role rows depend on a 9.8 MB fetch.** It starts after first paint and
   lands in ~1 s locally, well before anyone's first click; on a genuinely
   throttled connection expanding a card would wait, and M3 was not run under
   throttling (M1 was). A per-department shard would fix it.
9. **The sieve's first four numbers are quoted, not recomputed here** — the
   corpus step's 10,125 / 6,895 / 109 / 196 are upstream of `build-report.json`
   and `corpus.json` is not in the fixture. The panel says so in its own
   footnote. The other seven lines are counted from the build's own report.
10. **English only, one theme, no dark mode, no sign-in** — as the round
    directed. 390 px works (no horizontal overflow, checked with CDP device
    metrics) but the control rail is tall there; the layout is designed for a
    desk.
