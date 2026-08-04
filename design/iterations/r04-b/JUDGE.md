# r04-b — The Instrument · judge

| | |
|---|---|
| Ease (25) | **23** |
| Curation-legibility (25) | **21.5** |
| Representation (20) | **16** |
| **Judge total (70)** | **60.5** |

**New curve.** First PRODUCT round; scored on ease · curation-legibility ·
representation, not comparable to rounds 1–3. Anchor: faultless-with-no-POV
is a 62.

Driven, not read: my own CDP harness (private headless Chrome 150, repo served
gzipped on 8761), the keyboard path exercised with real `Input.dispatchKeyEvent`
key events including native-select type-ahead, the `?reset` and `?day=+1` seams
used as shipped.

## The measures, verified

- **M1 — pass, the fastest first card of the round.** 193–194 ms from
  navigation start under my Fast 3G profile (150 ms RTT); the claim of 764 ms
  used DevTools' 562.5 ms RTT and is the conservative one. The pre-rendered
  fold means the first card is in the HTML itself. The self-stamping
  `window.__firstCardPainted` is the round's best measurement idea — the page
  offers the evaluator its own number instead of asking to be believed.
- **M2 — pass.** Header line 2 answers who didn't make it, line 3 is the gate
  census, every visible card names its gate. Compact and complete.
- **M3 — pass, and the keyboard path is real.** `f e ↵ c s ↵ o o o o` — ten
  keystrokes, zero clicks, zero navigations, three Mercor tabs on Ashby,
  driven end-to-end with trusted key events including type-ahead into the
  native selects. Keys pressed before boot are queued, not dropped; I verified
  the queue exists in the handler.
- **M4 — 0 failures** across 43 hits; `rocketship`, `recently`, `funded`
  appear only inside the how-sheet's *What this page will not say*, each
  beside the coverage number that makes the phrase unsayable — the best single
  section of prose in the round.
- **M5 — pass on the letter, with a real blemish on the spirit** (below).
- **M6 — pass with one letter-miss.** Keeps survive reload and the question
  fires exactly once on `?day=+1`, never after an answer. But the shortlist
  chips carry no kept dates — `LangChain ×`, not `kept Aug 4` — and M6's
  letter is "pinned with their dates." The date is stored; it is not rendered.

## The blemish my instrumentation found and NOTES did not

**b reads only `r.visa` and never `hire_from_abroad`.** The fixture states
openness in either field: the union is 1,891 stated-yes / 947 stated-no —
the numbers a and c print. b renders stated-yes on 1,059 roles and prints
nothing on the **832 roles whose only statement lives in `hire_from_abroad`**
— a stated fact rendered as silence, the inverse of M5. Its how-sheet's
"Sponsorship is unstated on 25,674" is wrong by the same 800-odd roles.
STRATEGY calls the openness signal, including the no's, the corpus's most
distinctive column; this variant drops 44% of the stated yeses. No single role
renders a lie, which is why M5 still passes as written — but a page this
scrupulous about counters printed a wrong one.

## Ease — 23

The best interactive loop of the round: pre-rendered fold (six cards, the only
variant to hit the spec's six), queued keys, `o` open-next, sticky shortlist,
a footer that teaches every key, giants genuinely *held back below* — rendered
at positions 732+ in the same scroll, the most honest treatment of the toggle.
The one real hazard: the 9.8 MB roles fetch — an early expand on a throttled
line waits ~55 s behind an honest progress line. The worker is the right
architecture; the shard (which r04-c actually built) is the right fix. Minor:
"1 roles open" on singular cards.

## Curation-legibility — 21.5

The how-sheet is the most complete honest document in the round, and the
board's-own-department string on every role row is the doctrine done right.
But on the scroll — where the founder's ten-application weekend actually
happens — the gate line is four words (`Listed by CB Insights ↗`) with no
interpretation, 291 times. The hard work is *cited* everywhere and *shown*
mostly in a panel behind a keystroke. Add the visa undercount above.

## Representation — 16

The instrument is fully realised and unmistakably itself; nobody who used the
keyboard loop would confuse it with the other two. But the stance's named risk
— that the gate lines read as data rather than diligence — is, by the NOTES'
own admission, only half answered: the warm work lives in the expanded card
and the how-panel, and 413 companies have no one-liner at all. At 11pm this is
the page for the seeker who already trusts the register; it does the least of
the three to *earn* that trust on the scroll.

## What the shipping version should take from this variant

The pre-rendered fold and the key queue; `window.__firstCardPainted`
self-stamping; the entire keyboard loop (`j k ↵ o 1–9 x g`); the how-sheet's
*What this page will not say*; giants held back below rather than removed; the
board's own department string on every role row.
