# FINDINGS — what three rounds bought, and what to do next

The harness ran three rounds of three and stopped on its own rule. Nine working
variants are on disk, none deleted, all openable:

```bash
bash design/serve.sh
open http://127.0.0.1:8732/design/gallery.html
```

| Round | A · atlas | B · depart | C · wildcard |
|---|---|---|---|
| 1 | 54 | **63** | 55.5 |
| 2 | 63 | **64.5** | 60 |
| 3 | 64.5 | **65.5** | 61 |

Judge's 70 subjective points — the ask, the feel of moving through it,
originality. A clean, complete, faultless page scores 62 by construction, so the
whole exercise moved the winner from *slightly better than faultless* to *3.5
points better than faultless*. The stopping threshold was 68 and it was not met.

## The five findings that outlived the exercise

**1. The register is worldwide for 8% of itself.** For a reader outside the
fifteen surveyed countries, 543 roles at 47 companies have a board that *says*
abroad or visa is open; 213 are stated closed; **5,671 — 88% — say nothing that
bears on it.** Derived from `data/companies.json` and confirmed independently
three times. Translating the chrome into eight languages was the easy half.

**2. `hire_from_abroad` is unknown on 93% of postings.** That single field is the
highest-value thing the build could learn to extract from boards it already
reads. Every worldwide feature any variant built is throttled by it.

**3. 6,413 of 6,423 role titles are Latin-script**, and the ten that are not are
Japanese. A Japanese reader searching in Japanese is not hitting a search bug;
they are hitting the corpus. Three rounds each hand-rolled a 12–24 concept
lexicon to bridge it and each said the same thing: **the fix is a bilingual
occupation vocabulary in the build**, which no renderer can reach.

**4. Signing in buys nothing, in all nine variants.** Declining prints
everything, so *yes* gives the reader nothing nameable that *no* does not. The
gate exists to measure whether anyone signs in — a hollow offer measures nothing.
r03-b is the only one that says so out loud: *"What signing in buys, exactly:
nothing yet… pressing it is a vote and nothing else."*

**5. A role in São Paulo is not absent from this register; it is deleted by it.**
Found from the reader's side by the round-1 judge and from the code's side
independently, in the same hours. `countries: []` meant "we did not look there"
and rendered identically to "we could not read the board" — the one place the
repo violated absence-stays-absence.

## What to build next, in order — all outside the renderer

**1. `PUT /keeps` on the Clerk session.** All nine variants' asks converged,
unprompted, on naming the same absent server. The gate's counts only become
decision-grade once *yes* buys something, and a cross-device shortlist is the
smallest thing identity can honestly buy. This is the one that unblocks the
measurement the whole ladder rests on.

**2. The referral loop's unit is company + person, not a posting.** r03-c
identified this against itself: its `applied` state holds a posting, which is the
wrong unit for a product whose purpose is getting someone referred. Keep its
interaction — having *witnessed* you open a posting on an earlier night, the page
asks once: *"On Aug 2 you opened X. Did you apply?"* It asks; it never infers.

**3. The bilingual occupation vocabulary in the build.** See finding 3.

## Ideas worth taking from the variants, whichever you ship

- **`applied` can never come out of a click handler** (r03-c). The click is the
  page's hand; the application is the reader's. Data the page holds *about the
  reader* gets its own ink, and what it merely witnessed gets none.
- **The lens adds, never dims** (r03-a). Dimming 90% of rows reads as *disabled*;
  tinting the reachable ones leaves silence as paper.
- **Print the yield before asking to be believed** (r02-b): *dims 209, lights
  543, and 5,671 say nothing that bears on it and are exactly as bright as they
  were.*
- **Bypass as a labelled door** (r02-a): SIGN IN · PRINT THE REST ANYWAY · NO
  THANK YOU, each counted separately.
- **The fold is the only honest departure ledger** (r02-a). The build records no
  departures, but a kept role whose URL has left the corpus can be struck
  through. The one place the register can truthfully say *gone*.
- **Only confirmed sightings may be called new** (r02-a's clause, which r02-b and
  r02-c both got wrong): *"a count it does not hold is a count this page will not
  invent."*
- **Keep the last good sheet, dated** (all of round 3). A page that diffs itself
  nightly must expect to be stale nightly.

## What the harness got wrong, and what that cost

- **The corpus was not pinned until round 3.** The nightly rewrote it mid-round —
  schema 10 → 11, 6,423 → 27,687 roles — and every variant went dark. A score is
  a claim about a page *and* the data under it. Fixed by `design/fixture/`.
- **The evaluators never ran after round 1.** A spend limit killed them, and
  craft and translation were graded for exactly one of nine variants. The judges'
  70 points are sound; the other 30 are largely unmeasured.
- **The gallery named the wrong winner for three rounds**, reading the score by
  position instead of by label. Checked once at the start and never again — the
  same bug class the harness kept finding in the variants.
- **A self-reported feature list is not evidence.** r02-c's keep notch never
  rendered on desktop and round 2's grading did not catch it; r03-c's ask printed
  *"holds 1 nights"* while its notes claimed that fixed. Grade the page, never
  the changelog.

## Why it stopped

Round 2 converged the variants' prose; round 3 converged their structure — the
same mechanism set in three skins. The harness still closed every named gap and
stopped finding unnamed ones, which is the ceiling. The remaining distance is not
design work.
