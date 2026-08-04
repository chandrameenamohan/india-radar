# Round 4 — verdict

**This round starts a new curve.** Rounds 1–3 graded a register on honesty and
craft; round 4 grades a product on PRODUCT-1 §6's rubric — ease (25),
curation-legibility (25), representation (20). These numbers are not
comparable to the register scores, and the anchor carried over in spirit: a
faultless implementation of the spec with no point of view is a 62.

| | Ease /25 | Curation /25 | Representation /20 | Judge /70 |
|---|---|---|---|---|
| r04-a The Dossier | 22 | 23 | 16.5 | 61.5 |
| r04-b The Instrument | 23 | 21.5 | 16 | 60.5 |
| **r04-c The Guide** | **22** | **23.5** | **17.5** | **63** |

Everything below was measured on the running pages with my own CDP harness —
private headless Chrome, the repo served gzipped on 8761, Fast 3G by protocol,
390px by device metrics, real key events for b's keyboard path — before any
NOTES.md was opened.

## The measures, across the three

All six pass on all three variants, and for the first time in this harness's
history the self-reports were *conservative*: my Fast-3G first-card times
(a 405 ms · b 194 ms · c 275 ms) beat every claim, my click counts matched
every claim (a 6 · b 10 keystrokes · c 5), and M4 audits found zero unevidenced
hype words on any page. The two deviations found ran the other way:

- **r04-b drops stated facts.** It reads `visa` and never `hire_from_abroad`;
  832 roles whose boards state they hire from abroad render as silence, and
  the how-sheet's "unstated on 25,674" is wrong by the same amount. a and c
  read both fields and print the correct 1,891 / 947. No role renders a lie —
  but the corpus's most distinctive column loses 44% of its yeses.
- **r04-a infers a keep.** Opening a role on an un-kept company creates the
  keep and prints *"kept Aug 4, 2026"* — the page's hand rendered as the
  reader's verb. Disclosed and reversible, but it is the exact move the
  two-hands doctrine forbids. b's "shortlist … open a role and it lands here"
  wording is honest; c's model (`kept_at` stays null on opens) is correct.

Lesser letter-misses: b's shortlist chips omit the kept dates M6 names; c's
second-visit question fires on the next pageload rather than the next day
(session is the only witness a pinned snapshot allows — disclosed, and it
still fires exactly once and dies on any answer).

## The founder's gate, run on all three

*Engineering + San Francisco, giants hidden* returns essentially the founder's
list on all three — Mercor, Baseten/Astranis, LangChain, Drata, Eight Sleep,
Together AI, Grow Therapy, Reducto, Candid Health, Wispr Flow — with roughly
one household name in ten and no Anthropic/OpenAI/Databricks anywhere above
the fold. PRODUCT-1 §2's prediction holds on live pages. The three yield
grammars all print what the cut costs. The ten-application weekend works on
any of them; the differences are in feel:

- **a** is the dossier: five credentialed cards on the fold, the sieve
  counted at the top, authority intact at card 400. It informs.
- **b** is the instrument: `f e ↵ c s ↵ o o o o` — ten keystrokes to three
  apply-tabs, keys live before the data is. It performs.
- **c** is the guide: *"I read 10,125 companies to build this"*, a caption
  under every credential saying what it does and does not prove, the giants
  set aside by name with the reason stated, and an ask that explains itself.
  It persuades — and this product's premise is a trust problem.

## Why c wins

The founder's stated moat is "the representation and solving the problem with
ease." On ease the three tie within a point — b fastest for hands, c shortest
in clicks and the only one whose role-expansion never blocks (it sharded
`companies.json` per company; a and b both still hang a throttled expand on a
9.8 MB fetch). On representation they do not tie. c is the only page where the
*interpretation* of every credential is on the card itself — "a tracker's call
on size, not a funding fact" · "a filing signed by their own counsel, not a
press release" · "YC lists 65 people, their own board lists 90 roles" — which
is the difference between citing the hard work and showing it. Its stance
risk (six sentences carrying 291 identical CB Insights cards) is real and
audited: the aside does wallpaper on a long scroll, softened by the
interpolated role count and the genuinely varying YC captions. The warmth
thins; it does not curdle, and it never invents.

a is a very good page a newspaper would be proud of; its inferred keep and its
austere cards cost it the two points. b is the best engineering of the round
wrapped around the thinnest scroll-level argument, plus the round's only
factual counter error.

## Grafts — what the shipping version takes from the losers

From **b**:
1. The pre-rendered six-card fold and the key queue (c paints at 275 ms;
   b's 194 with six cards showing is better).
2. The whole keyboard loop — `j k ↵ o 1–9 x g` — layered on c's page.
3. `window.__firstCardPainted` self-stamping, so every future measurement
   reads the page's own number.
4. The how-sheet section *What this page will not say* — the best prose
   argument in the round; c's funnel should absorb it.
5. The board's own department string on every role row.

From **a**:
6. The evidence-split typography — serif for claims, mono for counts — as an
   honesty device on c's cards.
7. Per-option yield counts on the controls (a's chips price every narrowing
   before it is clicked; c's selects should too).
8. The sieve footnote separating counted-from-report from quoted-upstream
   numbers.
9. The on-page confession of the department cut's residue at query time
   (a prints its 4,852; c hides its 1,063 in NOTES).
10. The Python/JS cross-check invariant (29,982 combinations, 0 mismatches)
    as a permanent CI step.

Fixes to c itself: day-gate the question off `opened.at` once the clock is
real; put `Something else` in the field menu; one more per-company fact in the
CB Insights aside; a San-Francisco-proper answer under the Bay Area merge.

## What none of the three did

1. **The shortlist cannot leave the page.** No URL carries the narrowing, no
   button copies the kept list, nothing exports "my ten companies and the
   roles I opened." Third round running that nothing is built for the friend —
   and this round the deliverable itself is what evaporates. One "copy my
   shortlist" affordance is a line of code and the whole point of the session.
2. **Nobody says what an unheard-of company does on the collapsed card.** The
   product's success test is six-of-ten *unknown* companies; all three hand
   the seeker a stranger's name, a credential and counts. b renders
   `descriptions.json` one-liners for 376 companies — inside the opened card
   only. The single line that makes an unknown name feel like a find, not a
   risk, is in the fixture and on no fold.
3. **Nobody spends the record.** Three pages witness keeps and opens; none
   performs the honest arithmetic it already holds ("of the 141 companies in
   this cut, you have opened 2"). Same gap as round 3, now with better data.
4. **Nobody lets the reader act on hiring intensity.** c prints roles-vs-staff
   in a sentence; nobody offers it as an ordering ("hiring hardest for their
   size") — computable today from two stated numbers on 294 YC companies.

## Open decisions only the founder can settle

1. **Default 732 or 789.** All three ship `hide the giants` on. The gate
   argues for 732; the "cut nothing" decision argues the default view should
   show everything and offer the cut. c's set-aside strip is the best
   compromise shipped — hidden, but named, counted, and one click back.
2. **Should kept companies gather at the top of the list** (b's own weakness
   names it), or does the strip suffice as the deliverable?
3. **The department vocabulary is now written four times** — a's 14 families
   (engineering = 8,122 roles), b's taxonomy.js (6,971), c's build.py
   (9,063), and PRODUCT-1's ~8,104. Three pages give three different answers
   to "how many engineering roles are there." This must move into the build
   as one canon; PRODUCT-1 §7.1 said so before the round started, and all
   three NOTES say it again.
4. **May the ranking demote the 32 Acquired/Public/Inactive YC companies?**
   All three print the status loudly and refuse to sort on it, calling it an
   editorial judgement with no source URL. As long as the answer is no,
   BillionToOne — Public, per YC — is the first card of the default product.
5. **Bay Area merged or San Francisco proper** (c merged; a and b did not).

## Round 5

**Do not run round 5 yet.** The variants converged again — same default
toggle, same yield grammar, same founder's-gate list, same refusal on status
ranking — which is this harness's known signal that the brief's space is
exhausted. Every decision that would change the next build materially (the
default view, the vocabulary canon, status demotion, the fold budget) is a
founder's call, not a builder's, and per ITERATIONS.md the founder's look IS
the next brief. Ship c with the ten grafts, put it in front of the founder,
and let the ten-application weekend — six unheard-of, by his own gate — write
round 5's brief in his words. If he stalls before ten, the stall point is the
brief. Running another triple build before that gate would be building around
him again, which is what rounds 1–3 were for.
