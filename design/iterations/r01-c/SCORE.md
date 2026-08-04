# r01-c — THE CORE

TOTAL: — /100 · **evaluator half: 21/30** (craft 9/15 · worldwide 12/15). The ask,
inside and originality are left for the judge, who sees all three variants.

| Criterion | Score | Why |
|---|---|---|
| The ask (25) | —/10 | judge |
| Inside (25) | —/10 | judge |
| Originality (20) | —/10 | judge |
| Craft (15) | 6/10 | Tabular numerals and focus rings are flawless and every contrast ratio passes AA at rest — but CLS is 0.57, eight control classes are under 44px, and Tab is trapped in a 6,423-button list. |
| Worldwide (15) | 8/10 | Eight complete locales with real `Intl` (`$40.8億`, `4,1 Md $US`, `2 925`), translated `aria-label`s and country names; costs two composed-phrase errors and three English summary fields. |

## Hard gates — all five pass

| Gate | Result |
|---|---|
| Register renders with Clerk blocked | **PASS** — aborted `clerk.accounts.dev`, reloaded: 12 strata, 1,833 rows, docH 75,601. No sign-in button is printed at all (`signinBtns: []`) and the seam explains why: *"Sign-in is not reachable from this browser right now — a blocker, or Clerk itself. The door below needs neither."* One working door. Screenshot 05. |
| Console error on load | **PASS** — 0 errors across every pass. The only console output is Clerk's development-keys warning. |
| Absence stays absence | **PASS** — one flag, below (India CTC on a Japan role). |
| A source claim translated | **PASS** — company names, role titles, cities and register statuses print in their source language in all 8 locales, and footnote 06 says so *on the page*, translated. `Active` stays `Active` in German. Correct. |
| `prefers-reduced-motion` | **PASS, verified properly** — this is the one the builder flagged as unverified (NOTES #7), so I tested it with real `Emulation.setEmulatedMedia`, not a patched copy. `matchMedia('(prefers-reduced-motion: reduce)').matches === true`; animated/transitioned elements go **3,572 → 0**; `scroll-behavior` is `auto`; `scrollIntoView` lands in a single frame. Crucially the *JS* path is honoured too: the scroll de-emphasis (finding 3) is **suppressed entirely** rather than made instant — `.rp` opacity stays 1.0 across 75/75 samples during a sustained wheel scroll. That is the correct implementation and it is better than most. |

## What is genuinely good

**The seam is the best answer to "the ask" I can imagine testing.** Two doors of
equal weight, side by side, both 44px tall: `SIGN IN AND KEEP READING` in the
signal colour and `KEEP READING WITHOUT AN ACCOUNT` outlined beside it. Above
them, two numbers and a bar drawn to the gauge's own scale — *"4,590 more roles,
at 359 more companies, lie below this line. You have read 1,833 of them without
an account, and nothing above was withheld."* Beneath them, unprompted: *"This
page counts, in your browser and nowhere else, that you were shown this and what
you chose... and it has not been earned."* No blur, no countdown, no
"unlock". `roleatlas.gate.v1` records `shown`/`signin`/`bypass`/`open`, so the
measurement the brief asks for actually exists. Taking the second door opens the
full column (docH 75,584 → 275,181, 12 → 371 strata) and **it stays open across
reload**. And the seam recomputes per filter rather than reciting a constant —
under the DE plate it reads *"329 more roles, at 97 more companies"* against 428
read. Screenshots 05, 13.

**Reduced motion is a designed second state, not a kill switch.** See the gate
table. The distinction between "disable the effect" and "make the effect
instant" is one almost nobody gets right, and this gets it right.

**The receipt.** Enter on a row expands it in place — no page turn, no modal, no
lost scroll — into WHERE / FIRST SEEN / BOARD READ (the literal
`job-boards.greenhouse.io/databricks`) / READ ON / BUILD VERDICT / ON THIS BOARD
/ CORPUS / FUNDING / QUALIFIED / INDIA CTC / INDIA REGISTRATION, footed with
`AI-SUMMARIZED · CHECKED AGAINST THEIR OWN SITE`. Every label translates; every
number goes through `Intl`. This is the most honest thing on the page.
Screenshot 33.

**Worldwide is real, not string-swapped.** Compact currency renders `$40.8億` in
`ja` (myriad grouping), `4,1 Md $US` in `fr` with narrow-no-break grouping
`2 925`, `4,1 Mrd. $` in `de`, `$4.1 अ॰` in `hi`. `es` correctly *drops* the
thousands separator below 10,000 — jarring next to the other seven, and it is
`Intl` being right. Country names translate in visible text *and* `aria-label`
(`Vereinigtes Königreich`, `ニュージーランド`). Plurals are correct
(`1 Stelle` / `31 Stellen`). Switching locale mid-session preserves the search
term, the plate and the scroll position (y 4000 → 4023).

## What is wrong

Ranked. Findings 1–4 are mine to score; 5–10 land in the judge's territory and I
report them per the coverage rule.

**1. CLS = 0.5705 on every cold load — 5.7× the "poor" threshold.** Reproduce:
load the page with a `layout-shift` PerformanceObserver. Two shifts, both
reproducible across three runs. At **t≈131ms**, 0.5347: the country bar
materialises and pushes `#controls`, `#status` and `#barnote` down 44px. At
**t≈1375ms**, 0.0358: Clerk resolves, injects `SIGN IN` into `.mast-r`, and
pushes the entire page down another 40px — `MAIN#log` moves 564→604. Compare
`film-00-500ms.png` (no SIGN IN, list starts at y=575) with
`film-03-2000ms.png` (SIGN IN present, identical list starts at y=615). Why it
matters: the reader is 1.4 seconds into reading row 3 when the whole register
jumps under their eye, and the masthead slot Clerk fills has no reserved height.
For a variant whose thesis is *"nothing here moves for effect"*, the largest
motion on the page is an unintended one.

**2. Tab is trapped in the row list — a keyboard-only reader can never reach the
seam.** Every `.rrow` is `<button tabindex="0">`; there are 889 in the DOM at
load and 1,833 in the free column (6,423 opened). Reproduce: load, press Tab
repeatedly. Stops 0–29 walk the masthead, the 15 country segments, the search
box and the 8 selects — all correct, all with a visible ring. Stop ~31 enters
the list, and **140 further presses never leave it** (last stop reached: row
0108). To reach `SIGN IN AND KEEP READING`, `KEEP READING WITHOUT AN ACCOUNT`,
or the footer's `BUILD REPORT / THE DATA / FIRST SEEN`, the count is 1,833 Tabs
signed out and 6,423 opened. `j`/`k`/`J`/`K`/`?`/`/` all work well, but they are
the page's keys, not the browser's — a reader who only knows Tab is stuck in the
list and cannot answer the ask. Worse: **`[` and `]` drop focus to `BODY`
entirely** (verified: `active: "BODY"` after two BracketRight presses), so
changing country strands a keyboard user with no focus at all. The variant
advertises keyboard-first; this is the gap.

**3. The place column sits at 1.30:1 contrast for the entire duration of every
scroll.** This is the `.moving` behaviour from NOTES #3, and it is the
variant's signature idea, so I measured rather than judged it. Reproduce:
scroll continuously and sample `getComputedStyle(.rp).opacity` — it drops to
**0.18** within ~250ms and holds there for as long as you keep moving
(72/75 samples below 0.95), returning to 1.0 about 900ms after you stop. At 0.18
the blend is rgb(36,39,41) on rgb(10,12,14): **1.30:1, from 7.42:1 at rest.**
Effectively invisible. Screenshots 50, 52. The idea is coherent — at speed you
can only read titles anyway — but the column it hides is the one that answers
*can I take this job*, and "scrolling is the primary verb of this page." A
reader scanning for Berlin has to stop, wait ~900ms, read, and scroll again. The
row rules go transparent at the same time, so the list also loses its ruling
exactly when the eye needs the most help tracking across. Not a gate (it is
correctly suppressed under reduced motion) but the largest single cost in the
design.

**4. Eight interactive control classes are under the 44px touch minimum, three
of them severely** — measured at both 1440×900 and 380×780 with real device
metrics:

| Control | 1440px | 380px |
|---|---|---|
| `#keyhint` "? KEYS" | 45×**12** | 45×**12** |
| `footer a` "BUILD REPORT" | 90×**13** | 90×**13** |
| `#allbtn` "ALL COUNTRIES" | 102×**16** | 92×**30** |
| `.vsw button` ROLES / COMPANIES | 41×**30** | 41×**30** |
| `header button` SIGN IN | 72×**32** | 72×**32** |
| `#lang` | 219×**32** | 219×**32** |
| `.she` EVIDENCE | 71×**32** | 71×**32** |
| `#q` and all 8 selects | 142×**35** | 326×**35** |

`.seg` (44), `.shb` (44) and `.rrow` (40 desktop / 46 mobile) are fine. The
misses matter most on the phone the brief names: the primary SIGN IN affordance
is a 72×32 target, and the footer links are 13px tall. Related: `#q` is 142px
wide and cannot display its own placeholder in any locale — English shows
`company or role titl`, Japanese `ソフトウェアエンジ` mid-word.

**5. The zero-results state loses the count and the gauge, and offers no way
out.** Reproduce: type `zzzzqqq`. `#status` drops its `.tally` span entirely —
the orange "6,423 of 6,423 roles" does not become "0 of 6,423", it **vanishes**,
leaving the ROLES/COMPANIES tabs floating alone on an empty rule. `#depthtot`
becomes `—` while `#depth` still reads `0000`, so the gauge reads "DEPTH 0000
—". The body is one unframed line of 15px text stranded in ~200px of dead space,
and there are **no actions in the log at all** (`actions: []`) — no "clear
search", no "clear filters". Screenshots 22, 23.

**6. Two filters are written to `sessionStorage` and silently not restored,
changing the result count without saying so.** NOTES claims state survives
sign-in via `sessionStorage`; six of eight filters do. Reproduce: click the DE
segment, set DEPARTMENT = Engineering, type `backend` → tally "23 of 6,423".
Navigate away and back in the same tab. `roleatlas.place.v1` still holds
`{"country":"Germany", "f":{"dept":"Engineering","city":"Aarhus",...}}` — but
`#dept` reads `any` and the tally now reads **"24 of 6,423"**. Isolating it:
of `city, dept, remote, openness, mca, bracket, recency, sort`, exactly
**`city` and `dept`** fail to restore. Those are the two selects whose options
are built from the data at runtime, so the restore assigns a value before the
options exist and falls back to `any`. The reader comes back to a different
result set, one role larger, with no chip or notice. Scroll position is not
stored at all (y 1622 → 0), so *the place*, in the sense the state key is named
for, does not survive either.

**7. Fixed row height costs exactly what the assignment predicted, and worst on
a phone.** At 1440px the cost is nil — 0 of 400 titles truncate. At **380px, 130
of 300 truncate (43%)**: the title column is 250px and
`AI Engineer - FDE (Forward Deployed Engineer)` needs 313px,
`APJ Manufacturing & Automotive Industry GTM Leader` needs 357px. The real
damage is that the mobile row drops the city entirely — it becomes
`index | title | 2-letter country code` — so the truncated tail is the *only*
distinguishing token left. Screenshot 41 shows six consecutive rows (0078–0083)
all reading **"Lakebase Sales Specialist"**, separated only by DE/FR/NL/JP/SE/ES
at 10px, followed by `(Central)` DE, `(Enterpris…` GB, `- MEA` GB, `(UKI)` GB.
Rows 0078 and 0084 are both Databricks, both Germany, and differ only in a word
one of them does not show. A reader trying to tell two similar roles apart
cannot, and must open each one. **Contra NOTES weakness #1, the mitigation did
ship** — `.rt` carries a `title` attribute on 300/300 rows with the full string
— but a native tooltip needs hover, so it does nothing for the touch reader who
suffers all 43% of the truncation, and nothing for a keyboard reader either.

**8. Two of the three headline performance claims do not reproduce; the third
does.** Measured with `Input.dispatchMouseEvent` wheel gestures and rAF frame
sampling, two runs each, headless at 1440×900 over the full 275,181px column:

| | claimed | measured (unthrottled) | measured (4× CPU) |
|---|---|---|---|
| p50, rows 400–550 | 16.7ms | **16.7ms ✓** | 17.0ms |
| dropped frames, rows 400–550 | **zero** | **30–31 of ~265 (≈11%)**, max 34.1ms, one 55ms long task | **90 of 262 (34%)**, p75 66ms |
| deep column (y=120k / 250k) | 16.7ms p50 | 16.7ms, 2–4 dropped ✓ | p50 **49.2ms**, 147/208 dropped |
| keystroke re-render, 371 strata | **18ms** | **48–88ms** end-to-end (Event Timing), 21–50ms synchronous handler | **130–369ms** |

The p50 claim is exactly right and the deep-column behaviour is genuinely clean
— but "zero dropped frames" is not true even on a fast machine, and it fails
worst in the precise band the note singles out (rows 400–550). The 18ms
keystroke figure is 3–5× optimistic; the first character of a query costs 88ms
unthrottled. At a 4× CPU throttle — standard mobile emulation, and the brief
says *"no jank on a mid-range phone"* — the median frame deep in the column is
49ms, i.e. three frames long, and the first keystroke takes 369ms.

**9. The row DOM grows monotonically and never releases.** Reproduce: open the
full column, scroll 0 → 274,000, then return to the top. `.rrow` count goes
889 → 1,040 → 1,169 → 1,274 → **1,297**, and **stays at 1,297** back at the top
and on a second pass. Total nodes 9,053 → 11,821 (+31%) in one traversal. Heap
only reached 6MB so nothing is on fire today, but it is progressive reveal
rather than recycling, the ceiling is 6,423 rows, and it is the likeliest cause
of the depth-dependent throttled degradation in finding 8 (p50 17.0 → 17.7 →
49.2ms as you go deeper). "Someone who lives here for an hour" is the reader
this compounds on.

**10. Smaller things, reported not weighted:**

- **Filtering resets scroll to 0 and undoing the filter does not bring you
  back.** At y=18,000, typing in `#q` puts you at y=0; clearing it leaves you at
  y=0. Reproduce: scroll to 18,000, type `engineer`, delete it.
- **Switching ROLES → COMPANIES → ROLES lands you somewhere arbitrary.** From
  y=4,063 in ROLES, switch to COMPANIES (docH 2,381), scroll, switch back:
  y=**9,001**. Neither where you were nor the top.
- **No URL state whatsoever.** `location.search` and `location.hash` stay empty
  through every filter, plate and view change. NOTES #4 owns this as a
  deliberate ceiling, and it is the right thing to own — but it means no reader
  can bookmark, share or link "remote backend roles in Germany", and Back/
  Forward do nothing on a page built for long sessions.
- **The tally counts the matched register while twelve strata print** ("6,423 of
  6,423 roles" above 1,833 rows). NOTES #4 predicts this reads as a miscount and
  it does; the seam discloses the split honestly, but it is 75,000px below.
- **`INDIA CTC ₹35.6L average` prints on a Tokyo, Japan role.** It is labelled
  by country so it is not a false claim about the role, and I am not firing the
  absence gate on it — but nothing says the figure does not describe *this*
  posting, and a reader in Tokyo could reasonably read it as one.
- **Three fields render English in all eight locales**: `WHAT` → "One platform
  for data and AI workloads", `FOR WHOM` → "Companies with big data and AI
  ambitions", `WHY THEM` → "Created Spark, now a data-platform giant". I am
  **not capping worldwide at 4** for these and want the reasoning on the record:
  the panel foots them `AI-SUMMARIZED · CHECKED AGAINST THEIR OWN SITE`, so they
  are build-authored prose carried in the corpus JSON, and translating a claim
  the build made about a company is closer to the doctrine's forbidden move than
  leaving it. It is genuinely a grey zone and the judge may weigh it differently
  — but a Japanese reader gets three lines of English in an otherwise complete
  panel, and either translating them or marking them as untranslatable evidence
  would resolve it.
- **Composed-phrase syntax**, per CRITERIA §5: `fr` renders **"au 1 août 2026"**
  (French requires *1er*), and `pt-BR` renders **"Série A ou posterior, por o
  tamanho de uma rodada divulgada"** — *por o* is never valid, it contracts to
  *pelo*. Both are label-then-value assembly showing through as non-prose.
- `.sgn`/`.sgc` (country bar) are 9.5px at 4.79:1 — passes AA by 6%, at a size
  where it reads as decoration. `.tag`/`.she` are 9px, `.rk-foot` 8.5px.
- At 380px, "ALL COUNTRIES" and the "COUNTRIES — SHARE OF OPEN ROLES" label both
  wrap to two lines on the same row and visually collide. Screenshot 40.
- `? KEYS` renders on a 380px touch viewport, where it is unusable furniture —
  NOTES #3 predicts this.

## Round-2 brief: the cross-language dead end (reported, not deducted)

Per CRITERIA §5's round-1 rule. **A Japanese reader searching in Japanese hits a
wall and the page says nothing.** In `ja`: `エンジニア` → **2 of 6,423 roles**.
`ソフトウェアエンジニア` → **zero**. `東京` → 1. Meanwhile `engineer` returns
**2,270**. The reader is eight keystrokes from everything and the entire response
is 「この条件に合う求人はありません。」 — *byte-identical to what `zzzzqqq`
returns*. The page knows the titles are in their source language (footnote 06
says exactly that, in Japanese, 75,000px below). Nothing at the point of failure
says so, offers the English term, or hints that the corpus is largely
English-titled. It is correct behaviour and a complete dead end, and it lands on
the reader the brief opens with. The fix is small and nobody built it: an empty
state that names *why* it is empty and offers a way through.

## The one change that would move this most

Reserve the masthead's height so Clerk cannot shove the register 40px down the
page 1.4 seconds after it renders, and give the row list a roving tabindex so
Tab reaches the seam — the two unintended motions on a page whose whole argument
is that every motion means something.
