# r02-c — PASSPORT

Lane C · wildcard · **TEXT-LIGHT**. Port 8743.

## The idea, in one sentence

The reader states one fact about themselves — where they are allowed to work —
and the register answers *what could I do?* in numbers, three marks, distance
and position, so that the part of the page that carries the meaning is the part
that cannot be stranded in an English dead end.

## The thesis, and how it is actually spent

Text-light is not "fewer words as a style". It is a claim about who can read the
page. So the rule I worked to was: **anything the page could say with a number,
a mark, a length or a position, it says that way** — and every sentence that
survived had to earn a place in eight locales.

The chrome carries **97 string keys** against r01-c's **168** — a 42% smaller
translation surface for a page that does strictly more. Every key exists in all
eight locales; a sweep of `en · es · pt-BR · fr · de · ja · zh-Hans · hi` found
no orphaned English anywhere in the chrome.

The vocabulary of marks is **three**, and it never grows:

| | |
|---|---|
| `○` | the posting's own word: **remote** |
| `▮` | the posting's own word: it **hires from abroad** / sponsors a visa |
| `⊠` | the posting's own word: it **does not** |
| *(nothing at all)* | the posting said nothing |

The fourth state is the absence of a mark. That is not a shortcut, it is the
doctrine drawn: 4,662 of 6,423 postings say nothing, so most of the register
carries no mark and *looks* the way the corpus actually is. The legend is the
mark strip at the top — each glyph printed once at full size with its own count
beside it, plus a bar drawn to true share. A legend made of the data, not of
sentences. `CRITERIA` scores emoji-as-an-icon-system at 2; there are no emoji
here, three glyphs total, each used once and meaning one thing, each with a
translated `aria-label`.

## What is new here

**1. The reader's own cell (gap 1).** Top right, a dashed frame containing a
small grid of dots — nothing chosen. Open it and you get the same fifteen
country codes as the strip, **plus a sixteenth: `↗`, somewhere else, `0`.**
Stated, never guessed: the page does not read your IP or your locale and infer
mobility from it.

Choosing a country does three things at once, all wordless:

- the third headline figure becomes `JP 292` — how much of this register is
  where you are;
- every row gains a **distance**, `≈9 559`, great-circle from your country's
  anchor to the role's, formatted through `Intl`, marked `≈` because it is
  derived (note 03 says so);
- a fourth ordering appears — nearest first — which turns the register into a
  staircase you can read with your eyes shut.

Choose `↗` and the figure reads **`↗ 0`**. That single integer is the corrected
brief: for a reader outside the fifteen, *nothing here is where you are*, every
role is remote-or-relocation by definition, and the only things that can help
are the 1,009 that say remote and the 543 that say they hire from abroad — both
of which are one tap away on the mark strip. No variant in round 1 said this;
this one says it in a zero, in every language, without a sentence.

**2. The cross-language bridge (gap 1, the measured dead end).** `SCORE.md` for
r01-c measured it: in `ja`, `ソフトウェアエンジニア` → **0**, byte-identical to
`zzzzqqq`, while `engineer` → 2,270. Here the same query returns:

```
engineer → 2,270      software engineer → 532        (one tap each)
6,423 件の職種名のうち:  Aa 6,412    あ漢 11
職種名は、それを掲載した求人サイトの言語のまま表示されます。…
```

A 24-concept term table maps the **reader's** word into the word the boards use
— never the reverse. No posting is ever rewritten; the page offers the English
term *with its count* so the choice and the evidence both stay the reader's.
The table is matched across all eight locales, not just the one on screen, so a
Japanese reader who left the page in English gets the same bridge. Under it, the
script census: two sample glyphs and two numbers, which is the shortest true
answer to "why did my language find nothing".

**3. One country after another.** The default order deals the register
round-robin from the fifteen: `IN GB IE DE NL FR ES SE DK NO FI JP SG AU NZ IN
GB…`. It is the register's own invented order, it is legible in the country
column without being described, and it makes the free three hundred a sample of
*everywhere* rather than a sample of Databricks. r01-c's free portion was the
twelve largest companies and its ask sat 75,000px down; this one is 300 mixed
roles and the ask is at row 300.

**4. Keeping (gap 3), and the ask's missing motive.** Every row carries a page
marker on its own edge — click, or `s`. Kept rows fill their notch; a counter
sits bottom-right and filters to them. The ask then has something honest to
offer: *what you keep lives in this browser and nowhere else; an account is what
would carry it to your phone.* That is the one thing signing in actually buys,
and it makes `roleatlas.p.gate` measure desire rather than politeness.

**5. The return visit (gap 2).** `+145` in the status line, in the signal
colour, one tap to see them. It is the count of roles whose first-seen date is
later than your last visit. Roles that **vanished** are not counted, because the
build does not record them — absence stays absence even when it would make a
better number.

## What I stole, and what I refused to inherit

**From r01-c — the evidence sheet.** Enter or click opens the row in place into
COMPANY / WHERE / DISTANCE / WORKPLACE / FROM ABROAD / VISA / FIRST SEEN / BOARD
READ / ON THIS BOARD / FUNDING / QUALIFIED / the three AI-written lines, footed
with its provenance. Rewritten to be mostly key-and-number rather than prose,
and every empty field renders as nothing at all.

**From r01-c — geometry that cannot lie.** A right-edge rail showing depth
**measured in roles**, exact.

**But not the way r01-c bought it.** Its gauge was exact because rows were
fixed-height, and that cost 43% of titles at 380px — six consecutive rows
reading "Lakebase Sales Specialist" separated only by a country code. Here
**nothing truncates**: titles wrap, the company keeps its own line on a phone,
and the needle reads the *index* of the row at the top of the viewport (binary
search over chunk offsets, then over rows inside the one chunk on screen). Same
honesty, no cost. Measured at 380px: 100 rows rendered, **0 clipped**.

**From r01-a — the suppressible ask.** The seam does not appear when the
filtered register already fits: 65 results for `engineer` under the DE plate,
no ask. Nine results is an answer, and asking on top of an answer is a toll.

**From r01-b — the page showing its instrumentation.** `asked 1 · signed in 0 ·
declined 0`, printed under the doors, translated.

**Four things r01-c's evaluator found, closed here:**

| r01-c | r02-c |
|---|---|
| CLS **0.57**, the register shoved 40px when Clerk resolved | **CLS 0.000** — measured cold at 1440×900 and 380×780, fresh reader and returning reader. The account slot, the figures, the strip, the marks and the status are all reserved in CSS, and the register reserves a screen of paper until the corpus lands |
| Tab trapped in a 6,423-button list | **32 tab stops for the whole page.** The register is one stop (`role="listbox"` + `aria-activedescendant`, roving cursor); the seam doors are reachable in three more |
| `[` `]` dropped focus to `BODY` | `[` `]` move the plate and land focus on the country cell they opened |
| Row DOM grew 889 → 1,297 and never released | Chunks release their rows once the reader is twelve chunks away, pinned to their measured height first so nothing moves. Full traversal of the open column: **11.3k nodes peak, not 60k**; p50 frame 16.7ms |
| Empty state offered no way out | Every live constraint prints as the chip that removes it |
| No URL state at all | The session is in the URL (`#c=DE&m=a&q=engineer`), Back and Forward work, a find can be sent to a friend. Home is deliberately **not** in it: a shared link must not impose the sender's mobility on whoever opens it |

## Measured

- **Hard gates.** Clerk blocked (`*clerk.accounts.dev*` aborted): register
  renders, no sign-in control is printed at all, the seam prints one working
  door plus a translated line saying why the other is missing, bypass opens the
  full column and persists. **0 console errors** on every pass.
  `prefers-reduced-motion: reduce`: **0** elements with any transition or
  animation duration, `scroll-behavior: auto`, every programmatic scroll is
  `behavior: 'auto'`.
- **CLS 0.000** in all four cold-load configurations tested.
- **Scroll**, real wheel gestures over the 271,000px open column: p50 **16.7ms**,
  p95 17.6ms.
- **Contrast**, computed not eyeballed: ink 15.0:1, ink-2 7.8:1, ink-3 5.1:1 on
  the bone paper; the signal colour 8.3:1 on paper and 10.1:1 reversed. Every
  text pair passes AA, including the 10px apparatus voice.
- **Touch**, 380×780 with real device metrics: no horizontal overflow, and no
  interactive target under 44px.
- **Locales**: all eight complete; `<html lang>` and `dir` follow; `<title>` is
  a proper noun in all eight; every count and date through `Intl` (`6.423` de,
  `6 423` fr, `6423` es, `2026年8月4日` ja).

## Deliberate ceilings

- **`ponytail:` no per-locale clause ordering.** Composed phrases here are
  short and few (the seam's two sentences, the mark labels), and each locale
  writes its own whole sentence rather than assembling label-then-value. That
  dodges r01-b's telegraphic-German problem rather than solving it. Ceiling: a
  phrase longer than a clause would need a real message formatter.
- **`ponytail:` Clerk's own modal is not localised.** `openSignIn()` renders
  Clerk's UI in English. Passing `localization` needs a locale bundle per
  language and this page is dependency-free. Everything this page owns
  translates; the modal is Clerk's.
- **`ponytail:` the term table is 24 concepts.** It covers the words a job
  seeker types first. A miss falls back to the census plus the explanation,
  which is still better than silence. Ceiling: a real bilingual occupation
  vocabulary belongs in the build, not in the renderer.
- **The three AI-written company lines stay English**, marked `lang="en"` and
  footed with their provenance. They are prose the *build* wrote about a
  company; translating a claim the build made is closer to the forbidden move
  than leaving it. Marked rather than moved, and I would take the argument.
- No companies view. The register's unit is the role, because the reader's
  question is about a role.

## Where it is weak

1. **The masthead makes no claim.** There is no tagline — no "proven by the
   board, not by a claim". The honesty is *demonstrated* (every row opens into
   its board, its read date, its funding, its holes named) and stated in note
   01, but a reader who never opens a row never meets the argument. The
   disclosure chevron on every row is my answer and it may not be enough. This
   is the sharpest place the thesis could be costing me.
2. **The tail of the deal degrades to one country.** Round-robin exhausts the
   small countries first, so the last ~900 rows under the default order are all
   GB. It is honest — GB has 2,003 of the 6,423 — and the country column shows
   it plainly, but the rhythm the ordering buys is gone by then.
3. **`↗ 0` is a strong statement carried by a glyph.** It has a `title` and an
   `aria-label`, but a reader who does not stop on it may read the third figure
   as a broken number rather than as the answer to their question.
4. **Distance is a country-to-country anchor measure.** Berlin to Munich is 0
   here. Note 03 says so and every value carries `≈`, but it is a coarse
   instrument dressed in a precise-looking number.
5. **Keeping is per-URL and never expires.** A role that leaves the corpus stays
   in `localStorage` and simply stops appearing, with nothing said about it.
6. **The keep notch is 24×36 on desktop** — over WCAG 2.2's 24×24 pointer
   minimum, under 44. It is 44px wide on touch, where 44 is the rule.
7. **The chunk-release heights are pinned at the width they were measured at.**
   A resize clears them and re-measures, but a resize *during* a deep scroll
   will re-lay-out the column under the reader.
