# r05-a — the guide, set in the register's hand

**The idea in one sentence:** the round-4 winner's argument — somebody did the
diligence and is talking you through it — printed on the sheet the founder
already said he likes, so that under every unheard-of name there is what they
do, who it is for and why them, and the shortlist you build can leave the page.

---

## Run it

```bash
cd design/iterations/r05-a
python3 build.py                # regenerates data/ and index.html from ../../fixture-v2
python3 serve.py                # tries 8741, then 8841, then 8941 — gzip on, like Pages
open http://127.0.0.1:8841/
```

Port **8741 was already held by another process** on this machine every time I
tried it, so everything below was measured on **8841**, which `serve.py` falls
back to on its own. All QA scripts take `URL=…`.

```bash
node qa/perf.mjs        # M1 · Fast 3G, cache disabled   (NET= CPU= RUNS=)
node qa/measures.mjs    # M3 M4 M5 M6 + "the shortlist leaves the page"
node qa/crosscheck.mjs  # the Python fold and the JS render must agree, word for word
node qa/shots.mjs       # fold / funnel / expanded / narrowed / second visit / phone
node qa/smoke.mjs       # console errors, counts, the first three cards as text
```

`qa/cdp.mjs` launches its own private Chrome on a throwaway profile — never the
shared browse daemon, never `mcp__claude-in-chrome__*`. Phone shots use CDP
device metrics, not `--window-size`.

---

## What I kept from my predecessor, and what I rebuilt

A previous agent built r05-a's `build.py`, `page.html` and `qa/` and lost the
session before `index.html` existed. I inventoried it first. **The behaviour
layer was sound and I kept essentially all of it**; **the presentation layer was
answering a brief that no longer existed, and I rebuilt it whole.**

**Kept (theirs, and good):** the descriptions record and its provenance flags;
the neutral status treatment; San Francisco proper split out of the Bay Area
with the union kept as its own counted bucket; `Something else` in the field
menu; the day-gated ask off a real clock kept separate from the corpus date;
per-option yield counts on both menus; the per-company CB Insights aside; the
board's own department word on role rows; the quoted-vs-counted funnel; URL
state, copy-the-list and copy-the-link; the record line; the keyboard loop with
its pre-boot key queue; `window.__firstCardPainted`; the pre-rendered fold in
Python. That is most of the round-4 graft list and all four brief signals'
*mechanisms*, and re-deriving it would have been vandalism.

**Rebuilt:** the entire visual layer — every line of CSS, the body skeleton, and
the card markup both renderers emit. What I inherited was a warm dark dossier:
near-black paper, amber and teal accents, a serif for prose. Signal 4 arrived
mid-round and says the baseline is `site/index.html` and the founder likes it.
That page is white paper, one ink, one red, hairline rules under 2px structural
rules, 11px uppercase micro-labels at .11em tracking, tabular numerals, crop
marks, a twelve-column grid. A dark amber page is not a better version of that;
it is a different identity. So this page now uses the register's tokens
literally — the same six greys, the same `#E30613`, the same micro-label,
the same crop marks — and its own structures are built out of them.

**One graft I deliberately did not take.** r04-a's serif/mono "evidence split"
was praised by the judge. The founder's chosen page has no serif anywhere in it.
The brief's own recorded lesson is that the founder calibrates the judge, so the
split survives in the register's grammar instead: prose is sans, and every
number I counted is mono and tabular. You can still tell a sentence from a
figure at a glance; the page does not import a typeface the baseline never used.

**Also fixed while rebuilding, and both were real:** the masthead's `.aside`
class and the gate caption's `.aside` class collided, so every credential's
caption was inheriting `text-align: right` (visible in the first screenshots).
And `drawYield` still carried one `style="color:var(--dim)"` from the old
palette, pointing at a variable that no longer exists.

---

## What is on the screen, and why

**The masthead is a plate.** `I READ 10,125 COMPANIES TO BUILD THIS` in 800
uppercase with the count in the page's one red; the snapshot date and a red
hairline stamp — `789 / HIRING TONIGHT` — struck in the top right the way an
atlas sheet carries its number in the margin; the qualifier and the lede beneath
it, closed by a 2px rule. Crop marks register the sheet.

**The card is a register entry with three columns.** A mono reference in the
gutter (`01`, `02`, `03` — a CSS counter, so it is correct in both renderers and
stays correct through every re-narrowing without either being told), the entry
itself, and a right-hand count column carrying the roles figure at the size a
number gets when it is the thing you are choosing on, with the two verbs under
it. The open-their-roles button is the only filled block on the page.

**WHAT / FOR WHOM / WHY THEM sit on the collapsed card**, set in the slot the
baseline already uses for exactly this content: three ruled columns, keys in the
page's smallest voice, values beneath, and the provenance struck once along the
top edge of the slot rather than after each field. `371` of `789` carry them.

**The 418 without get a slot of the same shape.** Same rules, same footing, one
column: key `NOT YET READ`, value *"Not written up yet — below is only what Y
Combinator and their own board state"*, footing `THE BACKFILL JOB IS
SCRIPTS/DESCRIBE.PY`. Not a dash, not a blank, not an invention, and never a
card that looks broken. `BillionToOne` — card 01 of the default view — is one of
them, so the honest state is the first thing the page shows.

**Status is a fact in ink.** `PUBLIC, PER YC ↗` is a square hairline chip in
ink, linked to the directory that says it, with the batch year on the next line
(*"Y Combinator backed them, Summer 2017"*). No red, no warning grammar, no
"not a bet", and no "rocket that made it" either. Red on this page marks live
state — a set filter, a kept company, the count on the row under your hand —
and a company's status is not live state. The funnel says the position out loud:
*"What a company that already listed is worth to you is your call, and I do not
lean on it in either direction: they are neither hidden, nor demoted, nor sorted
differently from anyone else."*

**The shortlist leaves the page.** The narrowing and every kept company live in
the URL; `COPY THE LINK TO IT` hands you an address, `COPY MY SHORTLIST` hands
you ~1,000 characters of plain text carrying what each company does, who
vouched, the receipt URLs and every role you opened. A link that arrives
carrying companies says so rather than pretending they were always yours.

**One line spends the record**, and only once there is a record to spend: *"Of
the 732 companies in this cut you have kept 4 and opened 3 roles at 1 of them.
The other 728 you have not touched at all — that is the arithmetic, and it is
the only thing on this page that is about you."*

---

## The six measures, measured

Every number below is from the scripts in `qa/`, on a private headless Chrome,
against `serve.py` on 8841 with gzip on.

| | target | result |
|---|---|---|
| **M1** first card, cold, cache disabled, Fast 3G | < 1.5 s | **673 ms** median of 3 (692 / 671 / 673); the page's own `__firstCardPainted` stamp says **618 ms**. With 4× CPU throttling: **685 ms**. All 789 in the register at 2.1 s. **PASS** |
| **M2** curation legible from the load screenshot alone | both questions answerable | *How did these get here?* — five named gatekeepers with counts in the lede, and a linked receipt on every visible card. *Who didn't make it?* — `6,895 didn't qualify` in the subhead, the eleven-line ladder one click away. **PASS** (self-assessed; the screenshot is `qa/shots.mjs` → `-fold.png`) |
| **M3** three apply-tabs | < 60 s, ≤ 6 clicks, 0 navigations | **4.8 s · 5 clicks · 0 navigations**, three tabs on `job-boards.greenhouse.io/astranis/…`. Clicks: one opener, one `72 ENGINEERING ROLES IN SAN FRANCISCO AND THE WIDER BAY AREA`, three role rows. **PASS** |
| **M4** every hype word carries a link/date/count in the same node | 0 hits | **clean in five states**: default (732 cards), funnel open, register open (789 rows), giants shown (789 cards), a card expanded. **PASS** |
| **M5** absence renders as absence | not excluded, not a 0/—/no | 10 companies with no citable round: **0 excluded, 0 placeholder tokens, 0 dimmed or struck**. On Socure, 25 role rows, 1 with a stated visa answer, **0 dimmed**, and the header states the silence: *"Their board says nothing about visa sponsorship on 90 of them — that is silence, not a no."* **PASS** |
| **M6** shortlist survives; the question fires once | 3 pinned, 1 ask | 3 kept → hard reload → **3 pinned with their dates**. Same evening: **0 questions** — the day gate holds. Wind the stored `opened[].day` back one day: the question fires **once**, dies on any of `yes / no / not yet`, and does not return after another reload. **PASS** |

Two extra checks, because two of the brief's requirements are not in M1–M6:

- **The shortlist leaves the page — PASS.** Kept three, narrowed, then cleared
  `localStorage` and cold-opened the address in the same browser:
  `#field=eng&place=sfbay&keep=billiontoone,langchain,pigment` restored all
  three companies *and* both menus, and the page said *"3 of these arrived in
  the link you opened, not from this device. I dated them Aug 4, 2026 because I
  do not know when whoever sent it kept them."* `COPY MY SHORTLIST` put 1,054
  characters on the clipboard.
- **Python/JS cross-check — PASS.** 14 fold cards, 0 missing, 0 text
  mismatches. It found a real one on the first run: `build.py` wrote `YC's`
  where `page.html` wrote `YC’s`, so one card in fourteen carried a straight
  apostrophe on a page whose whole argument is typographic care.

Transfer: `index.html` **34.2 KB gzipped** (one request, fourteen cards, both
menus, funnel counts and all 57 giants inlined), `data/index.json` 119 KB
gzipped after first paint, one role shard 2–5 KB on expand.

### The founder's gate, which no script runs

`engineering in San Francisco and the wider Bay Area`, giants hidden, returns
**Astranis 72/95 · Replit 48/90 · Mercor 47/78 · MatX · Illumio · Lambda Labs ·
PsiQuantum · Hark · Abridge · LangChain**. `San Francisco proper` is now its own
answer in the menu (274 companies, 4,488 roles) and the Bay Area outside the
city is another (87 / 1,411); the union stays as a third, counted once and never
as a sum of the two.

---

## Where it is weak

1. **Two cards start above the fold at 1280×900, and only one finishes.** The
   first card's top is at **573 px**. r04-c started three. I spent the
   difference on the description slot, which is the round's first requirement,
   and on a masthead that carries the baseline's authority. I measured this
   rather than guessing at it (`qa/shots.mjs` prints it every run), and I still
   think it is the wrong trade to reverse — but it is a real cost against
   PRODUCT-1's six-card skim, and it is the first thing I would take back to the
   founder.
2. **Six sentences still carry 789 cards.** The CB Insights aside now varies by
   the company's own top field, place count or role count, which is better than
   round 4's single clause — but the *voice* is still per gate class. At card
   400 the shape of the sentence repeats even when its facts do not.
3. **418 of 789 have no description**, which is the majority of the newly
   unlocked world companies, and card 01 of the default view is one of them.
   The absent state is deliberate and named; it is still absence.
4. **The department buckets are mine**, and 1,063 roles (3.8%) land in
   `Something else`. That bucket is now in the menu and the residue is confessed
   on screen when you pick it, and every role row prints the board's own word —
   but a mis-bucketed role is still silently misrouted. The fix is normalisation
   in the build, not a renderer's regex, and this is a renderer's regex.
   PRODUCT-1 §7.1 has said so for two rounds.
5. **2,874 roles at 272 companies land in `Somewhere not in this list`.** In the
   menu, honestly labelled, still a big shrug.
6. **The default view is 732, not 789.** `hide the giants` ships on; all 57 are
   named with counts in the strip and one click puts any of them back, and the
   register at the foot always renders all 789. Still the founder's open
   decision #1.
7. **No freshness anywhere**, by choice: 7 dated URLs against 27,689 roles. The
   funnel names Aug 29 as the date that becomes a real number.
8. **The typeface is a stack, not a webfont.** The baseline loads Inter from
   Google Fonts; a font fetch is exactly the request M1 forbids, so this page
   asks for `Inter` first and falls back to the system grotesque. On a machine
   with Inter installed it is the baseline's type; on one without, it is close
   but not identical.
9. **Accessibility is not audited** beyond `aria-label` on both selects, real
   `<a>` role rows, `<h2>` company names, visible focus rings in the page's red,
   and a checked horizontal-overflow test at 390 px (the page does not scroll
   sideways; the giants strip does, on purpose).
10. **No sign-in, no i18n, no plates** — as briefed. Keeps are `localStorage`
    and the strip header says so.
