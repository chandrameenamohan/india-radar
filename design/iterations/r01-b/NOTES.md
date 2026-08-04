# r01-b — THE NIGHT DESK

## The idea, in one sentence

The page is a person on a night desk reading the register aloud to someone who
is still awake and worried, and **the query is a sentence they edit** — there is
no filter bank, only one line of English (or Hindi, or Japanese) whose nouns are
the controls.

## What departing meant here

The Swiss atlas answers this data as a printed plate: white paper, one twelve
column grid, hairline rules, one red, everything in the third person, navigation
drawn as a map. This is the opposite answer on every axis I could find one:

| | atlas | night desk |
|---|---|---|
| ground | white paper | warm dark, lit by one lamp pool at the top |
| voice | third person, captions | first and second person, sentences |
| type | Inter, one grid | Newsreader serif for the voice, mono for the evidence |
| navigation | an equirectangular chart with plate chips | a line of country names that wraps like a paragraph |
| controls | nine selects in a bank | nine words inside one sentence |
| the unit of reading | a row in a table | a band of roles under the night we first saw them |
| detail | a sticky gazetteer sheet in a second column | an entry that unfolds in place, under the line |

Two rules hold the whole thing together and are worth stating because every
decision below falls out of them:

- **One accent, one meaning.** `#F0A93B`, the lamp, means *this is live* and
  nothing else: a word in the sentence the reader departed from its default,
  the open row's spine, the roles first seen this week. There is no second
  accent, and nothing decorative is ever that colour, so a lamp-coloured thing
  at the edge of your eye is always something you did.
- **Every number is mono, every voice is serif.** Not one count, date, code or
  receipt line is set in the serif. That gets tabular figures in every column
  for free without a single table, and it means a reader can tell a thing we
  *read* from a thing we *said* by its shape alone, at a glance, in all eight
  languages.

## Flow 1 — the ask

A signed-out reader gets **240 roles across 79 companies**, in full, before
anything is asked, and every one of those companies opens completely: the three
AI lines with their provenance, the verification receipt, the funding, the
registrations, every role on the board. Then, at the exact line where the free
reading ends, a note in the register's own voice — not a modal, no blur, no
countdown, no "unlock".

The part I care about: **saying no prints everything anyway**, and the note says
so before you press either button.

> This is not a wall. The whole register is still searchable from the sentence
> at the top, the data file is linked at the foot of the page, and the button
> beside the sign-in prints everything anyway. The sign-in is here so we can
> find out whether anybody actually wants an account, before putting a public
> register behind one.

That is the brief's own reasoning said out loud to the reader. The gate's job is
to MEASURE, so both answers are counted in `localStorage` (`ra.ask`), and the
counter is **printed back to the reader** under the buttons — `asked 1 · signed
in 0 · declined 0`. A page that prints its own instrumentation cannot be
quietly instrumenting you.

Clerk-blocked behaviour, tested by serving a copy whose script tag points at a
dead host: the register renders 240 rows, the header shows **no account control
at all** (the slot holds its berth and stays invisible), and the ask drops its
sign-in half entirely and prints one extra line — "Sign-in is not answering
right now, so there is nothing here to sign into. The button below still prints
the rest." No dead button, no spinner.

Your place survives signing in because **the address bar is the session**: every
word you set is written to the query string on each render, `openSignIn()` is a
modal on our own sheet rather than a redirect, and `afterSignOutUrl` is
`location.href`.

## Flow 2 — inside

- **Bands, not rows.** Under the default sort the register is grouped by *the
  night we first saw each role* — Tonight, then 3 August, then 2 August — read
  straight off `first-seen.json`. Each band head carries its own count and its
  own honesty note, and the note is part of the band KEY rather than read off
  the first row, so a band can never print "these really did appear" over rows
  we cannot say that about. Under the other sorts the bands are the companies.
- **Milestones.** Every 250 roles a quiet mono rule: `750 read · 5,673 still
  ahead`. 6,423 reads as distance covered rather than as a wall.
- **The rail.** Sticky, left, desktop: the scope, your depth as a mono counter,
  a filled bar, and the name of the band you are inside. Updated from one
  `elementFromPoint` hit-test per animation frame, which is cheaper than
  observing a thousand rows and is exactly the question "what is the reader
  looking at".
- **The entry unfolds in place**, under the line that opened it, so nothing is
  replaced and the scroll never moves. `grid-template-rows: 0fr → 1fr`, 220ms,
  off under reduced motion.
- **Keyboard.** `/` search · `j`/`k` or arrows move · `Enter` opens · `Esc`
  closes and returns focus to the row. All verified on the running page.
- Measured: 1,080 rows mount in **118 ms**, cumulative layout shift **0** while
  extending; page-load CLS **0.03** desktop / **0.03** mobile.

## Flow 3 — worldwide

166 keys × 8 locales, checked programmatically for key parity *and* placeholder
parity. `Intl` everywhere: `NumberFormat` (the old `'en-IN'` hardcode is gone),
`DateTimeFormat`, compact `currency` for the raised brackets, `PluralRules` for
every count, `ListFormat`, and **`DisplayNames` for the fifteen country names** —
a hand table of fifteen countries in eight languages is a hundred and twenty
chances to be wrong.

`lang` and `dir` follow the choice, the `<title>` too. `dir` ships now although
all eight locales are ltr, because the CSS is written in logical properties
throughout (`margin-inline`, `border-inline-start`, `text-align: start`) — an
RTL locale is a row in the table rather than a rewrite.

Data stays in its source language and note 07 says so on the page.

## What I deliberately did not do

- **No virtualised list.** `ponytail:` in the code with the measured ceiling.
- **No server-side counting.** `ponytail:` likewise: this measures browsers, not
  people, which is the right cost for "does anybody want an account at all".
- **No map.** The atlas's chart is genuinely good and reproducing it here would
  have been half a departure. The country band is type doing the same job.
- **Company view is the poor cousin.** It works, it filters, it sorts, its rows
  open — but it has no band system except under the alphabetical sort, so it
  gets milestones and little else. Roles is the default and got the attention,
  because a job seeker at 11pm is looking for a job, not for a company.

## Where I think it is weak

1. **The sentence is telegraphic in the non-Latin locales.** Label-then-value is
   an English word order. I fixed the outright-wrong German (`im Bereich egal
   welchem` → `in jedem Bereich`) and re-cut the Japanese labels to work in
   prefix position, but `Arbeitsform egal` and `分野は 問わず` read as a form,
   not as prose. A per-locale clause ORDER is the real fix and I did not build
   it.
2. **`worked any way` / `having raised any amount`.** Even in English, the
   narrow clauses read more like a query language than like a person talking.
   The four core clauses are the ones that sound human.
3. **The country band scrolls horizontally on a phone** and the fifteenth name
   is behind a swipe. I chose that over eight wrapped rows of 44px targets
   pushing the register most of a screen down; there is a mask fade at the
   trailing edge saying there is more, but it is still a compromise.
4. **The remaining 0.03 CLS** is the sentence settling when the field and city
   option labels arrive and change a word's width. Small, but not zero.
5. **The lamp is used for the fresh mark as well as for reader state.** I argued
   myself into it (a role that appeared this week IS live state) but it is the
   one place the colour rule is doing two jobs.
6. **Search matches raw substrings**, so a Japanese reader searching in Japanese
   finds nothing — the titles are in their source language, correctly, and this
   page has no way to bridge that. Honest, and still a dead end for some readers.

## Running it

```bash
python3 -m http.server 8742 --bind 127.0.0.1
# http://127.0.0.1:8742/design/iterations/r01-b/index.html
# ?lang=de|ja|zh-Hans|hi|es|pt-BR|fr   ?view=companies   ?wide=1   ?c=Germany
```
