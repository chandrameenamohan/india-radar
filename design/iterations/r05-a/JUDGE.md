# r05-a — judge's verdict

*Measured before NOTES.md was opened: private headless Chrome (CDP, own harness,
never the shared daemon), repo and variant served gzipped, Fast 3G by protocol
(562.5 ms RTT / 1.6 Mbps), 390 px by device metrics, real key events. The live
baseline was loaded from https://roleatlas.sennamind.com/site/index.html and
held next to this page for every call below — the local `site/index.html` copy
refuses the repo's v10 data and renders empty.*

| | score |
|---|---|
| Ease (25) | **24** |
| Curation-legibility (25) | **24** |
| Representation (20) | **18** |
| **Judge total (70)** | **66** |

**The round's winner.** Not at the 68 target — see the verdict for where the
missing two points live.

## Measures, re-run

- **M1 — pass, and the claim was conservative.** First card in DOM at
  **621 ms** median of 3 (my MutationObserver witness; claim 673). DCL 772 ms.
  One caveat the page should know: `__firstCardPainted` is stamped by a double
  rAF, and in idle headless frames rAF starves — the stamp never fired in my
  harness. b's and c's stamps fired; a's number I had to take myself.
- **M2 — pass from the pixels.** *How did these get here?* — five named
  gatekeepers with counts in the lede, a linked receipt on every visible card.
  *Who didn't make it?* — `6,895 didn't qualify` in the subhead. Both answerable
  cold.
- **M3 — pass.** Preset `engineering in San Francisco and the wider Bay Area
  (201)` → Astranis card → three role rows: **5 clicks, ~4.3 s wall, 0
  navigations**, three tabs on `job-boards.greenhouse.io/astranis/…`.
- **M4 — pass.** 32 raw hits; every one either carries its receipt in the same
  block, sits in the will-not-say sheet's own quoted refusals, or is an ordinary
  adjective inside a description line whose provenance ("in my words, checked…")
  is printed on the card. No page-voice hype anywhere.
- **M5 — pass.** Forbes cards with `amount: null` render no `$`, no dash, no
  zero — "an editor's call. No funding number behind it, and I will not invent
  one" is the best absence sentence in the round.
- **M6 — pass, and the only correct day-gate of the three.** 2 kept → reload →
  pinned with dates. Same-day reload: **no ask** (c fires here). Stored day
  wound back: the ask fires **once**, with "I am asking because I cannot know,"
  dies on the answer, `you said: applied` witnessed. `applied` never touched by
  a click handler.

## The four signals

1. **WHAT / FOR WHOM / WHY THEM** — on the collapsed card, three ruled columns
   with micro-label keys, set in the register's own slot grammar. Readable at
   scan speed. Provenance is per-card and *state-varying* ("checked against
   their own site" vs "not yet checked") — which is information, but it repeats
   as a micro-line on all 371 described cards, and "THE BACKFILL JOB IS
   SCRIPTS/DESCRIBE.PY" is stamped in the header of all 418 unread cards. The
   brief said name the backfill; naming it 418 times in the reader's eyeline is
   the wallpaper the brief warned about, relocated.
2. **Status** — "PUBLIC, PER YC ↗" as a hairline ink chip with the batch year
   beneath; Airbnb reads "Public, per YC ↗ · Winter 2009 · YC's own status field
   for them reads Public." No red, no warning, no hype, never demoted —
   BillionToOne is card 01 of the default product. The funnel states the
   position out loud. Clean pass.
3. **The target** — 66. The three points over round 4's 63 were earned in
   representation and the closed gaps; the last two are not on this page to
   take (verdict).
4. **The baseline** — the strongest cold-fold kinship of the three. The
   masthead-as-plate (`I READ 10,125 COMPANIES TO BUILD THIS`, the red
   hairline stamp `789 / HIRING TONIGHT`), crop marks, micro-labels, underlined
   selects, tabular numerals, mono counts: side by side with the live site it
   reads as the same hand setting a second sheet. Red = counts + the state
   under your hand, which is precisely the register's own declared meaning.

## The shared gaps, closed

- **The shortlist leaves the page.** URL carries narrowing + keeps; `COPY MY
  SHORTLIST` yields a ~1 KB plain-text brief with provenance, receipts and
  every opened role URL; `COPY THE LINK` explains what the link carries. A
  link-opened list *discloses itself*: "2 of these arrived in the link you
  opened, not from this device. I dated them Aug 4, 2026 because I do not know
  when whoever sent it kept them." That sentence is honest — but the page still
  writes `kept_at` into the visitor's storage for companies they never kept.
  c's stricter answer (no keep until the reader presses keep) is the right
  doctrine; graft it.
- **The record is spent**, with the round's best-scoped sentence: "…that is the
  arithmetic, and it is the only thing on this page that is about you."

## The fold, judged

First card tops at **573 px and finishes at 792**; the second is cut at 900.
Against the live baseline — whose own first data row sits near 690 px under a
masthead, a chart and nine controls — this is the best fold of the round and a
better spend than the baseline's own. The six-card ideal of PRODUCT-1 predates
Signal 4; one *finished*, authored card with the whole curation argument above
it is the baseline's grammar, and this page has it.

## Where the points went

Ease −1: one finished card on the fold, controls not sticky over a 732-card
scroll, no plate-head for the return visit. Curation −1: the CB Insights aside
still shares one voice across 291 cards at depth (self-confessed), and b's
per-cut provenance recomputation shows what this page's static lede is missing.
Representation −2: the backfill-stamp and provenance-line wallpaper; and the
page *matches* the register's authority more than it advances it — the one new
representational idea of the round (the comparison plate) is on c.
