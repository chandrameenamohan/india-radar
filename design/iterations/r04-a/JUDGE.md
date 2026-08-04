# r04-a — The Dossier · judge

| | |
|---|---|
| Ease (25) | **22** |
| Curation-legibility (25) | **23** |
| Representation (20) | **16.5** |
| **Judge total (70)** | **61.5** |

**New curve.** Round 4 is the first PRODUCT round; these scores grade the
PRODUCT-1 rubric (ease · curation-legibility · representation) and are not
comparable to rounds 1–3's register scores. The calibration anchor: a faultless
implementation of the spec with no point of view is a 62.

Driven, not read: my own CDP harness on a private headless Chrome (150), the
repo served gzipped on 8761, Fast 3G by `Network.emulateNetworkConditions`,
390px by device metrics, all six measures re-run with my own instrumentation
before NOTES was opened.

## The measures, verified

- **M1 — pass, better than claimed.** 402–405 ms to first painted card from
  navigation start, Fast 3G, cache disabled, gzip serving (claim: 559 ms
  against an ungzipped server — the claim is the conservative one).
- **M2 — pass, the strongest opening argument of the three.** The first text
  node is the sieve, with the clause the other two shorten: *"6,895 didn't
  qualify; 2,076 more had no job board we could find."* Both questions
  answerable from pixels; the gate census names all six gatekeepers; five
  cards each carry a different credential.
- **M3 — pass, 6 clicks, 0 navigations, three Mercor tabs on Ashby.** My
  scripted run: 2.3 s wall. The primary button restates the query — `40
  engineering roles in San Francisco →` — which is the best single ease detail
  on the page.
- **M4 — 0 failures** across 42 hype-word hits in the default DOM.
- **M5 — pass.** Ten null-amount companies sampled: all render, no dash, no
  zero, no dimming. Stated visa yes/no from *both* fields (`visa` and
  `hire_from_abroad`), silence prints nothing — correct where r04-b is not.
- **M6 — pass, cleanly day-gated.** Keeps survive reload with dates; the
  question fires 0 times same-day, exactly once on `?today=2026-08-05`, and
  never again after an answer ("you said: applied — yes" remains).

## Ease — 22

The chip rail is the round's best control idea: every option prints its yield
before you press it (r02-b's rule moved onto the control), so narrowing is one
click per answer and never a gamble. The dossier's authority survives the deep
scroll — at card 400 the page is as composed as at card 1, and the tail closes
with the honest sentence about the 57. Costs: five cards above the fold, not
six; no keyboard path; the 9.8 MB roles fetch is a shared hazard with r04-b (a
throttled early expand waits); the 390px control rail is ~1,700px tall before
the first card.

## Curation-legibility — 23

The two-typeface split — serif for what a person wrote, mono for what a machine
counted — is a genuine honesty *device*, not a style: nothing counted can be
mistaken for something claimed. The sieve ledger's footnote distinguishing
counted-from-report from quoted-upstream numbers is the most scrupulous
receipt in the round. The department cut prints its own failure — *"4,852 of
27,689 roles carry a department … they are in no department cut, including
this one"* — at query time, on the page, not in a NOTES file. Deductions: the
card's department mix is the board's raw strings (`Field Sales, Oncology 34`),
honest but hard to scan against the normalised chips above; and two TechCrunch
amounts disagree with the headlines they link (disclosed; the receipt lets a
reader catch it, which is the doctrine working and a build bug staying open).

## Representation — 16.5

The stance is executed: it reads like a dossier someone typed after doing the
diligence, and it holds at 789 cards. What costs it here is one inference the
repo's own doctrine forbids: **pressing Apply on an un-kept company creates the
keep and prints "kept Aug 4, 2026."** The reader did not keep it; the page
did. NOTES discloses this (weakness 4) and it is reversible, but "kept" is a
reader's verb rendered from the page's hand — exactly the class of move r03-c's
two-hands rule exists to prevent. r04-b's wording for the same behaviour
("shortlist … open a role and it lands here") is honest; r04-c's model
(`kept_at` stays null on opens) is correct. Beyond that, the austerity that
gives the page its authority also caps its warmth: an unheard-of company gets a
name, a credential and numbers, and nothing that says what it does.

## What the shipping version should take from this variant

The evidence-split typography; the per-option yield counts on controls; the
sieve's quoted-vs-counted footnote; the on-page confession of the department
cut's residue; the 29,982-combination Python/JS cross-check invariant.
