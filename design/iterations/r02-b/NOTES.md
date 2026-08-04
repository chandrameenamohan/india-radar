# r02-b — THE NIGHT DESK, SECOND NIGHT

## The idea, in one sentence

The register still asks its question as a sentence — but the sentence now has a
grammar per language instead of English word order wearing translations, and a
**second sentence underneath it that the reader writes about themselves**, from
which everything else falls out: a lens that dims only what a stated fact rules
out, a shortlist that is a word in the first sentence, and a diff that greets
you with what appeared since the night you were last here.

## What round 1 won on, and what is untouched

The judge named five things to keep. All five are still here and none of them
was rewritten for the sake of a second draft:

- the query as a sentence whose nouns are the controls;
- bands by the night we first saw each role, each with its own honesty note;
- the ask printing its own telemetry back to the reader;
- the URL as the session;
- "It is late, and somebody is hiring."

## 1 — The frontier: the locale owns the sentence, not just its words

This is the thing the lane was told to fix and the thing most of the diff went
into. Round 1 translated every WORD and left the English SYNTAX: label, then
value, nine times. So German read `Arbeitsform egal` and Japanese `分野は
問わず` — a form with translated labels, not prose.

Three mechanisms, all in the string table where a translator can reach them:

- **`sent.core`** is a template that names its own connectives and the position
  of every slot. Japanese puts the country first and the verb last; German
  keeps its relative clause; Hindi's postpositions follow the noun.
- **`cl.order`** names which narrow clauses a language wants and in what order,
  and each **`cl.*`** carries the case, preposition or particle its own syntax
  needs on either side of the value.
- **`inc` / `inc.<CODE>`** is the page's own preposition for a country, and it
  declines: *im Vereinigten Königreich*, *in den Niederlanden*, *aux Pays-Bas*,
  *au Japon*, *nos Países Baixos*, *日本から*. The fifteen NAMES still come from
  `Intl.DisplayNames`; only the preposition is a page string, which is exactly
  the difference between prose and a form field. English is in the table too —
  r01-b said "in United Kingdom".
- **`fmt.dept` / `fmt.city`** decorate the word as it stands IN the sentence
  while the dropdown stays bare, because 「エンジニアリング (2,431)の」 is
  debris inside a line of prose and 「エンジニアリングの」 is Japanese.

`grammar()` reads these without the English fallback every other key gets: a
missing translation should fall back to English prose, but a missing GRAMMAR
rule must fall back to its own language's generic form, or a Japanese sentence
quietly acquires an English preposition.

Read out loud, on the running page:

| | |
|---|---|
| en | Show me roles matching anything in all fifteen countries in any field — newest first. |
| de | Zeig mir Stellen in den Niederlanden aus jedem Bereich zum Thema irgendetwas, die aus der Ferne erledigt werden … |
| ja | 日本から、どの分野の、どんな言葉を含む職を、リモートで働けるもの、新しい順に見せて。 |
| fr | Montre-moi les postes qui parlent de n'importe quoi au Royaume-Uni en tout domaine, exercés à distance … |
| hi | सभी पंद्रह देशों में किसी भी क्षेत्र में कुछ भी से मेल खाती भूमिकाएँ — सबसे नई पहले दिखाओ। |

## 2 — Gap 1: the page reads the reader, and the reader wrote it

A second sentence under the first, in the same instrument, a size down:

> I am reading from **a country this register does not cover**. I read
> **日本語**. I **would need a visa sponsored**. `DIM WHAT THESE RULE OUT`

Three words, all optional, all **stated** — nothing is inferred from a header,
and the unstated default says its own silence out loud ("somewhere I have not
said"). The lens is a separate act from the statement, because a page that
started dimming the moment you named your country would be deciding for you.

**The lens uses exactly two kinds of fact**: what a posting states about itself,
and what the reader stated about themselves. A board that said nothing is never
dimmed — 5,974 of 6,423 postings say nothing about sponsorship, and a page that
read silence as refusal would be inventing five thousand rejections. The yield
is printed in numbers above the register before the lens is believed: *dims 209,
lights 543, 5,671 say nothing that bears on it and are exactly as bright as they
were.* Note 07 states the rule on the page.

**The brief's corrected reader is answered directly.** Say you are outside the
fifteen and the page tells you so, in its own voice, with numbers: *"This
register covers fifteen countries and yours is not one of them, so every role
below is remote work or relocation. 317 postings here say they hire from abroad
and 237 say they sponsor a visa. The rest say nothing at all about it, and
nothing is not a no."*

**The alphabet, not the language.** The corpus carries no language field and
inventing one would be a guess. What CAN be read off a title without guessing is
the alphabet it is written in — so that is what the second sentence works from,
and the finding is printed: *of 6,423 titles, 6,413 are in the Latin alphabet;
10 are not.* Note 06 says it is derived.

## 3 — The Japanese searcher's dead end, repaired

Type 「デザイナー」 in Japanese. Nothing matches, because the boards wrote in
Latin letters and this page does not translate what a board wrote. The empty
state says that with the two numbers, and then does the one thing available:

> These words are ours, though, and ours are in your language. Each one is
> already a filter: **デザイン — 147件**

The bridge is built out of the only words on the page that ARE in the reader's
language — our own field and country names, which are already filters. Matching
is containment either way plus, for a script with no spaces, a two-character
head, because 「デザイナー」 and our 「デザイン」 are not substrings of one
another and are obviously the same question. Where nothing of ours matches
either, the offer is the ten titles written in an alphabet the reader reads —
and pressing a button that says "an alphabet I read" IS the statement, so the
page still never guesses.

## 4 — Gap 3: what you keep, and what signing in finally buys

Every line carries a `+` at its end (`x` on the keyboard). Keeping writes the
board's own title and URL beside the night you kept it, and the shortlist is
**a word in the first sentence** — `Show me the 12 roles I kept matching …` —
not a panel bolted to the side. Its bands are the nights you kept things, which
is the same organizing idea one person along. It is never gated: asking somebody
to sign in to read what they wrote down themselves would be the toll booth this
page exists not to be.

That gives the ask the motive round 1 did not have. Declining still prints
everything, so "yes" had to buy something nameable that "no" does not:

> One thing signing in would actually buy: you have kept 12 roles, and they are
> in this browser alone. An account is the only thing here that could carry them
> to your phone.

And, stolen from r01-a and taken further: **the ask does not appear at all once
the reader has set a word in the sentence.** Nine results is an answer, and
asking on top of an answer is a toll; the ask is for the reader who is browsing,
which is the read the measurement is actually about.

## 5 — Gap 2: the return visit

`ra.visit` holds the night this browser last read. Come back and the page opens
with your diff, above the register:

> **Since you last read this, on 2 August: 1,151 roles appeared.**
> Where: United Kingdom 371, Germany 117, India 102.
> We cannot tell you what left. This record holds first sightings and nothing
> else, so a role that came down between the two nights leaves no trace in it.
> **1 of the roles you kept is no longer on any board we read tonight.**

The half we cannot know is stated rather than skipped — and the half we CAN
know about disappearance is the half that matters to a person: the roles they
kept. "Read only those 1,151" is another clause in the sentence (`first seen
since 2 August`), so the diff composes with everything else.

The stamp is written on the way OUT and only once the reader has actually read
— scrolled past the first screen, or left the page open half a minute. Opening
the page and reloading is not reading and must not cost somebody their diff.

## 6 — Gap 4: the cursor is where the eye is

`j` from sixteen thousand pixels down used to warp to row one in all three
round-1 variants. Here the cursor is adopted from the row the rail is already
reporting — the one under the reader's eye — whenever the focused row is off
screen, and if the reader has scrolled PAST the last row (into the ask, or the
footer) it takes the row nearest the top of the viewport. Verified on the
running page: rail at row 73, `j` lands on 73, scroll stays at 7,091.

`Enter` opens the evidence for the line you are on, `c` the company behind it,
`x` keeps it, `/` searches, `Esc` closes.

## 7 — Stolen outright, as instructed

- **r01-c's in-place evidence sheet, at the ROW.** The index is the handle: it
  opens what we hold on that one role — first seen with its confirmed/
  unconfirmed clause, the location exactly as the board typed it, workplace,
  visa and hiring-from-abroad each stated or explicitly *"the posting did not
  say"*, the field naming which of the two texts placed it, the board, the read
  date, the posting. The company is one control away, not a page turn away.
- **r01-a's suppressible ask** (above) and **the bookplate**: every byte this
  page has written about the reader, printed back with the key it lives under
  and a control that burns it — and any key in this origin that is NOT ours is
  printed too, labelled as the sign-in provider's, because a bookplate that
  printed only the rows it was proud of would be the audit failing at the one
  line that matters.

## 8 — Craft: the layout shift is gone

r01-b's cumulative layout shift measured 0.10–0.43 on a cold profile on this
harness. r02-b measures **≤0.0006 on desktop and 0.000 at 390px, in all eight
locales**. Four causes, all found by measurement rather than by inspection:

1. The Google Fonts sheet was render-blocking (first paint at 564ms) and then
   swapped, relaying the whole page. It is now non-blocking and `display=
   optional`: first paint at 60ms, and a visitor whose cache is cold reads the
   fallback rather than watching the page rearrange itself.
2. That is only safe because of a **metrics-matched fallback**, measured on the
   running page: Newsreader sets the same prose at 100.5% of Georgia and 110% of
   Times, with its own number for the italic — synthesising an oblique from
   Georgia roman sets ten per cent wide, and the headline and the search word
   are the two italic things on this page.
3. `.lede h1 { max-width: 22ch }` was measured in the FALLBACK's zero, so the
   headline broke in a different place once Newsreader arrived. Now `em`.
4. The lede's em-dash placeholders held their place but not their **berth**, so
   the paragraph relaid when the numbers landed. They are now sized by measuring
   a sample of the right shape in the reader's own locale — `ch` is the mono
   zero, and a Devanagari date inside a mono span is not set in the mono at all.
   And at 390px the account slot reserves its WIDTH as well as its height: the
   letterhead was one pixel from wrapping, so it grew a line when Clerk answered
   — in Spanish, Portuguese and French only.

Also fixed: r01-b's clipped final glyph on `anything` (the italic input sets
wider than the roman sizer; the sizer now carries slack), and a real bug where a
company beginning with C, D, K or L was given a first-seen band's head in the
alphabetical company view, because the band key and the date key shared a
prefix.

Touch targets at 380px: nothing under 44px anywhere, in en, de and ja, measured
with CDP device metrics. Dimmed rows: title 6.55:1, second line 6.55:1 — a lens
that pushed a job somebody might still want below AA would be a page deciding it
is no longer text.

## What I deliberately did not do

- **No server-side counting.** `ponytail:` in the code; this measures browsers,
  not people, which is still the right cost for "does anybody want an account".
- **No shortlist sync.** `ponytail:` — that is precisely what the account would
  buy, which is why the ask can finally name it. One row per user in the Worker.
- **No virtualised list.** `ponytail:` with the measured ceiling, unchanged.
- **The lens does not use `remote` as a border-crossing fact.** A posting that
  says "remote" has not said remote-from-your-country, and deriving that would
  be the guess this page exists not to make. It costs the lens some reach.
- **The reader's profile is not in the URL,** alone among the page's state. A
  find can be sent to a friend; a visa status is not part of a link. `since` and
  `script` are out for the same reason — they resolve against the reader.

## Where I think it is weak

1. **The yield can run to four paragraphs.** A reader who states all three facts
   and turns the lens on gets a lot of prose between the sentence and the
   register. It is all information they asked for by stating something, but it
   is the densest thing on the page and I did not find a way to compress it that
   kept the numbers legible.
2. **The lens's honesty is also its limit.** With `here` set and `move` set to
   "only where I already am", every row outside that country dims — 5,666 of
   them — and the dimming is doing very little work that the country word in the
   first sentence would not do better. The configuration where it earns its keep
   is sponsorship, where dim and lit are 209 and 543 against 5,671 silent.
3. **The dimmed index number sits at 4.24:1**, just under AA. The title and the
   location line clear it comfortably and any dimmed row returns to full on
   hover or focus, but I did not find a value that fixed the index without
   making a dimmed row's number brighter than an undimmed one's.
4. **The bridge is a two-character head for CJK.** It is a heuristic, and it can
   propose a field that is not what the reader meant. It is an offer with a
   count attached rather than a claim, which is why I let it stay loose.
5. **`display=optional` means a cold visitor may never see Newsreader.** I chose
   a page that does not move over a page that is always in its own type, and
   with the fallback matched to 0.5% that is a trade I would defend — but it IS
   a trade, and on a slow connection the register is set in Georgia.
6. **The company view is still the poor cousin.** It has no lens (the lens reads
   what a POSTING says, and it says so), no keep, and bands only under the
   alphabetical sort.
7. **`greet` counts what appeared, never what left.** That is the record's own
   limit, and the page says so — but a job seeker's real question at 11pm is
   sometimes "is the one I wanted still there", and only the shortlist can
   answer it.

## Running it

```bash
python3 -m http.server 8742 --bind 127.0.0.1
# http://127.0.0.1:8742/design/iterations/r02-b/index.html
# ?lang=de|ja|zh-Hans|hi|es|pt-BR|fr   ?view=companies   ?wide=1   ?c=Germany
```

Driven throughout on a private headless instance (own binary, own user-data-dir,
never the shared daemon), at 1440×900 and at 390/380px with CDP device metrics.
