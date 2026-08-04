# PRODUCT-1 — "Finding the next rocketship startup," defined as behaviour

*2026-08-04. Every number below was recomputed from the world build
(`buildclone/data/companies.json` + `corpus.json` + `build-report.json`,
snapshot 2026-08-04). Every claim about a variant was checked against the page
running on port 8732 at 1280×900, not against its NOTES.md.*

---

## 0. The one-paragraph version

The nine variants are registers: they are organised around **what the corpus
contains**, and the founder wants something organised around **what he should do
next**. That is what "do not think that this is just a board" means. The fix is
not a new aesthetic — it is a change of unit. **The unit of this product is the
company, not the role**, because the founder's own sentence puts it first ("I
did the hard work to find the next rocketship *startup* and their role") and
every variant puts it fourth. And the curation — the actual differentiator — is
on screen in exactly zero of the nine pages. It is fully evidenced in the data
and nobody printed it.

One thing in the founder's framing is wrong and he needs to hear it before the
first line of code: **"recently funded" is not provable here.** Details in §2.
What *is* provable, at 100% coverage, is better than he thinks.

---

## 1. Why the nine variants failed the brief

They are careful, honest, and beautifully made. The failure is structural and
it is the same failure nine times, because the rubric that produced them graded
honesty and craft and never once graded whether a reader got closer to
applying. Nine agents optimised what was measured. They succeeded.

Here is what a user actually sees in the first five seconds.

### The tell: all nine open with a masthead

Stripped of markup, the first text node of every variant:

| | first words on the page |
|---|---|
| r01-a | `Role · Atlas` · `Edition` · `Snapshot` · `Plate 01` · `World — all countries` |
| r01-b | `Role·Atlas` · `Night desk` · `Reading the register…` |
| r01-c | `Depth` · `Role · Atlas` · `Language` · `Snapshot` |
| r02-a | `ROLE · ATLAS` |
| r02-b | `Role·Atlas` · `Night desk` |
| r02-c | `ROLE · ATLAS` |
| r03-a | `ROLE · ATLAS` |
| r03-b | `Role·Atlas` · `Night desk` |
| r03-c | `ROLE · ATLAS` |

A masthead, an edition, a plate, a snapshot, a night desk. That is the grammar
of a **reference work**. Reference works are consulted by someone who already
knows what they are looking for. This product's entire premise is that the
reader does *not* know — that finding is the thing being done for them.

### The five-second read, page by page

**r03-b** (`It is late, and somebody is hiring.`) — a serif headline the height
of a fist, then `6,423 open roles at 371 funded companies in 15 countries`, then
a sentence you complete: `Show me roles matching anything in all fifteen
countries in any field — newest first`. The first role does not appear until
~700px down, and it is `Lead Engineers - Platform · Halter · Auckland`,
followed by `Regional Sales Manager · Netskope · Melbourne` and `Social Media
Manager · Heidi Health`. The word **funded** appears once, as an adjective, with
nothing behind it. A job-hunting founder in the US scrolls three rows into a
social media job in Melbourne.

**r03-a** — the most information-dense first screen of the nine, and the column
order is the whole diagnosis: `IN · ROLE · COMPANY · WORKED · FIRST SEEN`. The
company is **fourth, grey, and smaller than the role title**. Row 1: `NZ · Lead
Engineers - Platform · Halter`. The left rail is `WHERE YOU STAND` — three
controls about the reader's visa situation, which is `unknown` on 93% of
postings. The most prominent coloured element on the page (magenta) encodes
`543 within reach / 5,671 the board did not say / 209 stated closed` — an
honest bar about the sparsest column in the corpus.

**r03-c** — opens on three enormous numerals: `6,423 ROLES · 371 COMPANIES · 15
COUNTRIES`. Those are the publisher's inventory stats. Nothing above the fold is
about the reader. Then a 15-cell country strip, then a four-symbol legend, then
a sentence explaining that the four counts overlap and do not add to 6,423 —
before the first job. Row 1: `Manager, Campaign Operations · 6Sense`.

**r01-a** — nine filter dropdowns in a row above the first result (`SEARCH ·
HIRING CITY · DEPARTMENT · WORKPLACE · FOREIGN HIRES · MCA REGISTER · RAISED ·
FUNDED · SORT BY`), under a world map with 16 numbered plates. Row 1 is
`ソリューションアーキテクト (プリセールス) · Databricks · Tokyo`. This is the only
variant that tried to surface funding at all — and it did it as **`RAISED: Any
amount` and `FUNDED: Any time`, two subtractive filters over a column that is
null on 667 of 789 companies.** Touch either and 85% of the register vanishes.
That is the exact inversion of the doctrine: absence rendered as exclusion.

### The four structural faults, named

**1. The company is subordinate to the role.** Every variant's atom is a role
row; the company is a small grey right-hand column. The founder's product is
*"I found the companies."* Nine designs demoted the finding to metadata.

**2. The curation is invisible.** Nowhere on any first screen does a page say
*Y Combinator*, or *Form D*, or *$130,599,988 on 2025-11-19*, or *we read 10,125
companies and rejected 6,895*. All of that is in the data. All of it is
printable with a link to the receipt. **None of it is on any page.** The one
thing that separates this from Indeed is the one thing no variant renders.

**3. The default order serves the corpus, not the reader.** Alphabetical
(r03-c), or corpus-chronological "newest first" (r03-b/r03-a). Whoever the
reader is, row 1 is not for them. There is no ranking anywhere in any variant —
which is a design decision that hands the finding back to the user, in a
product whose promise is *"why should finding take time?"*

**4. The biggest verb on screen is *read* or *filter*, never *apply*.** r03-b's
largest interactive text is `Show me`. r01-a's first screen is nine dropdowns.
The apply affordance, where it exists, is a 10px `↗` glyph on a role row. The
founder's test is *"they just need to apply."* Nothing above any fold is that.

### What deserves to survive

Credit where it is due, because these are the parts worth carrying forward:

- **r02-b's yield line** — print what a filter costs *before* asking to be
  believed. This is the right answer to sparse columns and it is reused in §4.
- **r03-c's `applied` discipline** — *"`applied` can never be derived from a
  click-out: the click is the page's hand."* Correct, and load-bearing for
  problem #2.
- **r03-b's `Tonight · 7 roles` band**, which confines the `NEW` badge to
  genuinely twice-observed URLs and says why in-line. That is honest. It is also
  7 roles out of 6,423, which makes freshness a footnote, not a product.
- **r02-a's "bypass as a labelled door"** and the struck-through departure
  ledger.

---

## 2. Where the founder's framing is wrong, and what is true instead

> *"Show jobs from only those companies which are recently funded from highly
> credible individuals, angels, investors, VCs — YC/SPC/Thiel Fellowship/other
> respectful, seed, Series A, B, C, pre-IPO."*

Held against the build, that sentence has four clauses and the data supports
one and a half of them.

| Clause | Corpus reality | Verdict |
|---|---|---|
| "recently funded" | funding date on **122 of 789**. Within 12 months: **72**. Within 6 months: **22**. Within 90 days: **4**. | **Not shippable.** "Recently" describes at most 9% of the register and the median dated round is over a year old. |
| "seed, Series A, B, C, pre-IPO" | `round_letter` on **5 companies** — four `A`, one `B`. | **Not shippable.** 0.6% coverage. Do not build a round filter. |
| "from credible individuals, angels, VCs" | The field does not exist. The only investor names anywhere are inside 20 TechCrunch URL slugs (`...50m-from-benchmark...`, `...33-million-from-prosus...`). | **Not shippable as data.** Printable as a headline for 20 companies. |
| "YC / other respectful" | **298 YC companies**, each with a canonical `ycombinator.com/companies/<slug>` receipt. | **Shippable today, at scale, with a link.** |

If the page prints "recently funded startups" as a promise, the founder will
catch it himself on his first weekend of applying. He is the first user; that is
the whole point of building it for himself.

### What is true instead — and it is stronger

**Every one of the 789 companies is here because a named gatekeeper put it on a
list, and the build kept the receipt.** 100% coverage, one clickable URL each:

| Gate | n | What the card can say, verbatim |
|---|---|---|
| Y Combinator | 298 | `Y Combinator company ↗` → `ycombinator.com/companies/airbnb` |
| CB Insights | 291 | `Listed by CB Insights ↗` |
| SEC EDGAR | 101 | `Filed a Form D for $130,599,988 on 2025-11-19 ↗` → the EDGAR document |
| Forbes | 78 | `On a Forbes list ↗` |
| TechCrunch | 20 | `TechCrunch, 2026-03-12: raised $50M from Benchmark ↗` |

Note that all 101 SEC companies carry an exact dollar amount **and** an exact
date, because a Form D is a legal filing. That is stronger evidence than any
competitor's "funding" chip, and it is not on any page.

**And the hard work has a number.** `corpus.json` and `build-report.json`
already hold the whole funnel:

```
10,125  company names read from the sources
        ├── 6,895  did not qualify
        ├──   109  not software
        └──   196  ambiguous
 2,925  qualified as funded software companies
        └── 2,076  we could not resolve a job board
   832  boards actually read
        ├──    43  read, nothing open
        ├──    12  turned out to be another company's board
        └──     5  empty, unverified
   789  companies with something open tonight
27,689  roles, every one live on the company's own board on 2026-08-04
```

That block is *"I did the hard work to find the next rocketship startup"*, in
the build's own numbers, and it is 100% honest today. It appears on none of the
nine pages. It is the single highest-value thing to put on screen.

### The rocketship signal that actually has 100% coverage

It is not funding. **It is hiring.** Open-role count is a fact about the
company's own board tonight, present for all 789 (median 16, mean 35). A
company with 279 open roles is expanding; a company with 1 is not.

But volume alone fails the founder's own test, and this is worth showing.
Ranked purely by matching roles, "engineer, San Francisco" returns:

```
Anthropic 168 · OpenAI 118 · Databricks 69 · Scale AI 56 · Mercor 45 …
```

He already knows those. Nobody did any hard work for him. Add **one** cut — a
boolean over a 100%-coverage field, `total open roles < 100` (732 of 789
companies qualify, so it removes only the giants) — and the same query returns:

```
Mercor 45/78 · Chime 34/65 · Together AI 29/56 · Reflection AI 28/64 ·
Gusto 26/92 · Lambda Labs 26/64 · LangChain 24/97 · Eight Sleep 24/53 ·
Drata 23/54 · Sentry 20/48 · Grow Therapy 19/33 · Sigma Computing 18/72 …
```

That is the list the founder is describing. One toggle, one honest field, and
the product's promise becomes visible. **Do not compute a composite
"rocketship score."** Print the admission gate and the two role counts adjacent
and let the reader judge — that is what this repo's doctrine requires and it
also happens to be more persuasive.

---

## 3. The product, defined as behaviour

**It is a shortlist builder, not a board.** The output of a session is 5–15
companies the reader is going to apply to this weekend, with the role URLs open
in tabs. Everything below is judged against that.

### On load — 0 seconds

No masthead. No filter bank. No map. No language picker. The page opens on a
stack of **company cards, already ranked, already useful**, under one line:

```
789 companies hiring · 27,689 roles open on their own boards · read Aug 4, 2026
We read 10,125 companies to get here. 6,895 didn't qualify.  ↗ how
```

The second line is the differentiator and it belongs in the first paint. `↗ how`
opens the funnel from §2 — the receipt for the curation.

### First five seconds

Six company cards visible without scrolling. Each carries four things and
nothing else:

```
┌────────────────────────────────────────────────────────────────────┐
│  Mercor                                            78 roles open   │
│  On a Forbes list ↗                                                │
│  Engineering 48 · Operations 19 · Enterprise Agents 6 · 2 more     │
│  San Francisco · New York City · London                            │
│                                     [ 48 engineering roles → ]     │
└────────────────────────────────────────────────────────────────────┘
```

*(Every value in that card and in the fold below is read from
`companies.json`, not composed. Mercor really is a Forbes-list admission with 78
open roles and 48 of them in Engineering.)*

The second line is the curation, made visible, per company, always linked to a
receipt. It is different on every card — `Y Combinator company`, `Filed a Form D
for $130.6M on Nov 19, 2025`, `TechCrunch: raised $50M from Benchmark`. **That
line is the five-second answer to "why is this not Indeed."** A reader who
scrolls six cards has seen six different named gatekeepers vouching for six
companies. No board on earth shows that.

### First minute — the shortest honest path to applying

Four beats: **narrow once → skim companies → open roles → keep the company.**

**Narrow once.** One control, not nine. A sentence above the cards:

```
I'm in  [ engineering ▾ ]  looking in  [ San Francisco ▾ ]     ☑ hide the giants
```

Two dropdowns, both over near-total coverage (department known on 99% of roles,
locations on 100%), plus the one checkbox from §2. Nothing else, ever, above the
fold. The rule that produces this list is the important part:

> **A filter over a sparse column silently deletes the unknown. A fact printed
> on a card cannot.**

`workplace` is unknown on 52%, `visa` on 93%, `amount` on 85%. Every one of those
was a filter in at least one variant. Every one of them moves onto the card as a
printed fact — or, where it is unknown, as nothing at all, which is what absence
looks like. This is the doctrine finally paying rent instead of costing space.

**Skim companies.** Default order is **matching roles, descending**, tie-broken
by total roles. It is 100%-coverage, it is a fact about tonight's board, and it
directly encodes *this company is hiring hard for people like you*. When a
narrowing removes companies, print the yield in r02-b's grammar before the
cards: `198 companies are hiring engineers in San Francisco. 21 of them have
more than 100 roles open and are hidden.`

**Open roles.** `[ 45 engineering roles → ]` expands the card **in place** into
its role list — title, location, first-seen date where the build genuinely has
one, and `Apply ↗` opening the company's own board in a new tab. No detail page.
No navigation. The shortlist you have built stays on screen behind you.

**Keep the company.** `Keep` pins it to a strip at the top of the page. That
strip is the deliverable of the session.

Budget: load 0s → two dropdowns 10s → skim six cards 20s → expand one 25s →
three apply-tabs open by 40s. Under a minute, six clicks, zero navigations.
That is *"they just need to apply."*

### Second visit

The keeps strip is on top and it is the only thing that changed:

```
KEPT · Mercor            Aug 4 · 78 → 81 roles open · your 3 roles still live
       Reflection AI     Aug 4 · 64 → 64 · one of your 3 is gone from their board
```

And **one question, asked once per kept company**, in r03-c's exact grammar:

> On Aug 4 you opened 3 roles at Mercor. Did you apply?    `yes` · `no` · `not yet`

It asks; it never infers. That single line is the whole seed of problem #2 and
it costs one row today.

Everything below the strip is identical to visit one. **No "new since you were
here" badge** — `first-seen.json` holds 7 dated URLs against 27,689 roles today.
Ship that badge when the snapshots exist (~2026-08-29 at the earliest per T7.1),
not before.

### Deliberately absent, and why

- **A search box.** A search box is an admission that the page cannot rank, and
  it hands the finding back to the user. *"Why should finding take time?"*
  — this is a direct disagreement with `STRATEGY.md` §5, which opens the page on
  one input with the cursor in it. That design answers *"is this specific
  company real and hiring?"*, which is a **verification** need (S1's ghost-job
  pain). Problem #1 is a **discovery** need. Two different products. The input
  also fails on today's corpus: 2,093 of 2,925 companies are unchecked and
  marquee names (Figma, Canva, Mistral, Revolut) are absent, so most first
  queries miss. **Condition for shipping the input: the unchecked count is
  under ~500, or a miss list exists to prove the top queries hit.** Until then
  it is a v2 feature, and problem #1 does not need it.
- **Sign-in.** FINDINGS #4: it buys nothing in all nine variants, so it measures
  nothing. Keeps go to `localStorage`. Add sign-in the day `PUT /keeps` exists
  and it buys a cross-device shortlist.
- **Countries, plates, eight languages.** ~48% of roles are US-located, the
  founder is job hunting in that market, and the corpus is 6,413/6,423
  Latin-script. Ship English.
- **The 27,689-row table.** It exists behind `see all 789 companies` at the
  bottom. The register becomes the receipt, not the door.

---

## 4. The one screen

Above the fold at 1280×900. Everything on it is justified underneath.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  789 companies hiring · 27,689 roles open on their own boards · read Aug 4   │
│  We read 10,125 companies to get here. 6,895 didn't qualify.  ↗ how          │
│                                                                              │
│  I'm in [ engineering ▾ ]  looking in [ San Francisco ▾ ]   ☑ hide the giants│
│                                                                              │
│  198 companies are hiring engineers in San Francisco.                        │
│  21 have more than 100 roles open and are hidden.                            │
│  ──────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│   Mercor                                                    78 roles open    │
│   On a Forbes list ↗                                                         │
│   Engineering 48 · Operations 19 · Enterprise Agents 6 · 2 more              │
│   San Francisco · New York City · London                                     │
│                                    ♢ keep      [ 48 engineering roles → ]    │
│  ──────────────────────────────────────────────────────────────────────────  │
│   Together AI                                               56 roles open    │
│   On a Forbes list ↗                                                         │
│   Engineering 26 · Research 10 · Business Operations 5 · 8 more              │
│   San Francisco · Amsterdam · Bangalore                                      │
│                                    ♢ keep      [ 26 engineering roles → ]    │
│  ──────────────────────────────────────────────────────────────────────────  │
│   Reflection AI                                             64 roles open    │
│   Listed by CB Insights ↗                                                    │
│   Engineering 15 · Research 10 · Operations 8 · 12 more                      │
│   San Francisco · New York · London · Washington DC · Seoul                  │
│                                    ♢ keep      [ 15 engineering roles → ]    │
│  ──────────────────────────────────────────────────────────────────────────  │
│   Eight Sleep                                               53 roles open    │
│   Y Combinator company ↗                                                     │
│  ──────────────────────────────────────────────────────────────────────────  │
│   Lightning AI                                              41 roles open    │
│   Filed a Form D for $435,454,301 on 2025-12-24 ↗                            │
│   …                                                                          │
└──────────────────────────────────────────────────────────────────────────────┘
```

Expanded (in place, no navigation) — real Mercor rows from the build:

```
│   Mercor                                                    78 roles open    │
│   On a Forbes list ↗                                                         │
│   ──────────────────────────────────────────────────────────────────────     │
│   Software Engineer, Platform            San Francisco or NYC                │
│                                                              Apply ↗         │
│   Infrastructure Engineer                San Francisco · New York City       │
│                                                              Apply ↗         │
│   Fullstack Engineer, RL Environments    San Francisco · New York City       │
│                                                              Apply ↗         │
│   Software Engineer, Backend             San Francisco                       │
│                                                              Apply ↗         │
│   … 44 more            ▲ collapse                                            │
```

**Every element, justified.**

| Element | Why it earns its place |
|---|---|
| `789 · 27,689 · read Aug 4` | The provenance promise in nine words. One line, not a masthead. |
| `We read 10,125. 6,895 didn't qualify.` | The hard work, quantified. This is the sentence the founder wrote the product to say. It is true today. |
| Two dropdowns | 99%/100% coverage. The only two questions with answers for nearly every role. |
| `hide the giants` | Converts a list of household names into the founder's list (§2), using one boolean over a field with no nulls. |
| The yield line | r02-b's rule: say what the narrowing cost before asking to be believed. |
| Company name, large | The unit of the product. First, largest, black. |
| The gate line | The differentiator, per company, always a link to a receipt. The single most important line on the page. |
| `78 roles open` | The hiring signal, 100% coverage, a fact about tonight's board. |
| Department breakdown | Tells the reader in one glance whether this company hires people like them, without a click. |
| Cities | Tells them whether it is reachable, from `locations`, which is never null. |
| `keep` | Builds the deliverable. Local, no account. |
| `[ N engineering roles → ]` | The single primary action. Expands in place. |
| `Apply ↗` | The founder's test, one click from the primary action. |

**Deliberately absent from the fold:** the word *rocketship* (unevidenced), the
word *recently* (9% true), any visa control (93% unknown), any workplace control
(52% unknown), any raised-amount control (85% unknown), a search box, a sign-in
button, a country strip, a language picker, a snapshot/edition/plate masthead.

**What the build must add for this screen to exist** — one dependency, and it
is real:

- `locations` has **3,632 distinct raw strings** (`San Francisco` 1,935 ·
  `San Francisco, CA` 945 · `San Francisco, California` 255 · `San Francisco,
  California, United States` 217 — all one place). `department` has **2,318
  distinct strings** (`Engineering` 3,483 · `Software Engineering` 209;
  `GTM` 261 · `Go To Market` 206). Both dropdowns are impossible until the build
  normalises them into ~30 cities and ~10 departments. Normalised: SF 4,997 ·
  New York 3,125 · London 1,498 · Bengaluru 651 · Seoul 606; engineering-ish
  8,104 roles.
- `companies.json` is **11.9 MB**. A single-file fetch will not paint a card in
  1.5s. Shard by department or by city.

Those two are the entire build cost of problem #1. Everything else is rendering
data that already exists.

---

## 5. How problem #2 attaches without a rewrite

Problem #2 is tracking which companies you applied to. Four things problem #1
must leave room for, all cheap, all justified on their own today:

1. **State is keyed on the company, not the posting.** `keeps[slug] =
   { kept_at, opened_role_urls: [{url, title, opened_at}], applied: null }`.
   FINDINGS #2 identified this against r03-c: its `applied` state holds a
   posting, which is the wrong unit for a product whose endgame is a referral,
   where the unit is company + person. Getting this key right today costs
   nothing; getting it wrong costs a migration.
2. **Opened roles are witnessed at click time.** Which URLs the reader opened,
   and when. This is the *only* input #2 needs that cannot be reconstructed
   later — and it is what lets #2 ask a specific question instead of showing an
   empty form.
3. **The question already ships in #1.** *"On Aug 4 you opened 3 roles at
   Mercor. Did you apply?"* — one row on the second visit. #2 does not build a
   new interaction; it gives that answer somewhere to go.
4. **A reserved chip slot on the card**, right of the company name, where a
   status can appear later without reflowing the card.

And the discipline that must hold from day one, because it is r03-c's best
finding: **`applied` can never come out of a click handler.** The click is the
page's hand; the application is the reader's. The page may witness; it may never
infer.

**What #1 must NOT build:** a status pipeline (kept → applied → screening →
onsite → offer), a notes field, reminders, an email/ATS parser, a separate "my
applications" page, or a dashboard. Every one of those is a guess about a
workflow the founder has not run yet. #2 starts the weekend he says *"I've lost
track of who I applied to"* — and by then his own keeps data will tell him what
the columns should be. That is the feedback loop he said he wanted; do not
short-circuit it with a schema.

---

## 6. What to measure

The old rubric graded whether the page was honest and beautiful. These grade
whether anyone got closer to applying. All six are runnable by an evaluator
agent against a live page.

**M1 · Time to first company card.** Cold load, cache disabled, throttled to
Fast 3G. First card painted. **Target < 1.5s.** (Fails today at 11.9 MB — this
is the metric that forces the shard.)

**M2 · The curation is legible in five seconds.** Screenshot the viewport at
load. Hand it to an evaluator with **no other context** and ask two questions:
*How did these companies get here? Who didn't make it?* **Pass = both answerable
from the pixels alone.** Today: 0 of 9 variants pass — the word "funded" is the
entire answer available.

**M3 · Time to three apply-tabs.** Script: *"You are a backend engineer who
wants to work in San Francisco. Get three application URLs on companies' own job
boards."* Stopwatch from cold load. **Target: < 60s, ≤ 6 clicks, 0 page
navigations.** Log the three companies.

**M4 · Zero unevidenced claims.** Grep the rendered DOM for `rocketship`,
`recently`, `funded`, `new`, `top`, `best`, `fast-growing`. Every hit must have
an adjacent link, date, or count in the same DOM node. **Today `funded` fails on
all nine variants.** Automatable; run it in CI.

**M5 · Absence renders as absence.** Sample 10 companies with `amount: null`
and 10 roles with `visa: "unknown"`. Assert: (a) none is excluded from any
default view; (b) none renders as `0`, `—`, `no`, or a greyed-out row; (c) each
either renders as a stated silence or does not render. This is the doctrine, as
a test.

**M6 · The shortlist survives.** Keep 3 companies → hard reload → all 3 still
pinned with their dates. Simulate a second visit → the *"did you apply?"* row
fires **once per kept company** and never again after an answer.

**And the one no agent can run, which is the real gate:** the founder opens the
page cold, applies to ten companies in one sitting, and **at least six of the
ten are companies he had not heard of.** If they are all Anthropic, OpenAI, and
Databricks, the hard work was not done for him — it was done *around* him — and
§2's `hide the giants` cut is the difference between those two outcomes.

---

## 7. What to build first

In order, and it is short:

1. **Normalise `locations` and `department` in the build.** 3,632 → ~30 cities;
   2,318 → ~10 departments. Nothing else in this document is possible first.
2. **Shard the corpus** so a card paints in under 1.5s.
3. **The company card**, with the gate line and the receipt link. If only one
   thing gets built this week, build this: it is the differentiator and it is
   the thing zero of the nine pages has.
4. **The funnel line** — `We read 10,125 companies. 6,895 didn't qualify.` One
   line of copy over numbers `build-report.json` already computes.
5. **The two dropdowns, the giants toggle, and the yield line.**
6. **Expand-in-place + `Apply ↗`.**
7. **Keeps in `localStorage`, keyed on company, witnessing opened role URLs.**
8. **The second-visit question.** One row. That is problem #2's foundation and
   the end of problem #1.
