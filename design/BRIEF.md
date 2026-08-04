# BRIEF — the loving portal

The one thing this page has to become: **the website a job seeker loves.**
Not "a good data site". Loved. Someone opens it at 11pm, anxious about their
next job, and stays.

**Where that someone actually is, corrected.** This brief first named readers in
São Paulo and Warsaw. The register covers fifteen countries and neither Brazil
nor Poland is one of them:

> Australia · Denmark · Finland · France · Germany · India · Ireland · Japan ·
> Netherlands · New Zealand · Norway · Singapore · Spain · Sweden · United Kingdom

So a Warsaw reader translating the page into Polish still finds no Polish job.
For everyone outside those fifteen, **every role here is remote-or-relocation by
definition** — and nothing on the page says so. That is the difference between
*multilingual* and *worldwide*, and it was a factual error in this brief rather
than a failing of the variants graded against it. Flow 3 is both: translate the
chrome, and tell a reader outside the register what is actually open to them.

Three flows, in order of importance.

## Flow 1 — the ask

A signed-out reader sees **a few companies, fully**. Not a blurred wall, not a
teaser card: real rows, real roles, real provenance, enough that they can tell
this register is honest. Then the page asks — warmly, once, in the reader's own
language — to sign in for the rest.

Rules:

- **The ask is an invitation, never a toll booth.** No blur-and-fade, no
  "unlock", no countdown, no dark pattern. If the reader says no, the page
  keeps working for what they already have.
- **The gate is client-side and bypassable on purpose.** Its real job is to
  MEASURE whether anyone signs in — that measurement is the only evidence that
  would justify moving the corpus behind the Worker later. Count the ask and the
  answer in `localStorage`; a gate nobody can measure is worse than no gate.
- **The register must still render when Clerk is blocked, slow, or broken.**
  This is a hard invariant, not a nicety. Auth is additive. A reader with a
  script blocker sees the free preview and no broken control — never a spinner
  that never resolves, never a "Sign in" button that cannot sign anybody in.
- Signing in must not cost the reader their place: the plate, the filters and
  the search term survive it.

## Flow 2 — inside

Once signed in, moving through 371 companies and 6,423 roles should feel like
something. Scrolling is the primary verb of this page; make it the thing that's
designed, not the thing that's left over.

This is where "mind-blowing" is earned or not. Some directions worth trying —
none mandatory, and a variant that finds a better one wins:

- The list has a *rhythm*, not just rows. Density that changes as you move.
- Where you are is always legible — the plate, the country, the depth.
- A role reveals itself without a page turn and without losing the scroll.
- Motion that carries meaning (a page turn, a filter settling) rather than
  decoration. `prefers-reduced-motion` is honoured everywhere, always.
- 6,423 roles is a *lot*. Make the scale feel like abundance rather than a wall.
- Keyboard-first. Someone who lives here for an hour should never touch a mouse.

Performance is part of the feel: no jank on a mid-range phone, no layout shift
as data lands, no scroll that stutters at row 400.

## Flow 3 — worldwide

**No orphaned English.** Every string the *page* owns is translated: labels,
buttons, empty states, the ask, errors, dates, counts, `aria-label`s, the
`<title>`, `lang` on `<html>`.

- Detect from `navigator.languages`, allow an explicit override, persist it.
- Ship: `en`, `es`, `pt-BR`, `fr`, `de`, `ja`, `zh-Hans`, `hi`.
- **Data stays in its own language.** A Berlin company's role title is German
  because that is what its board says. Translating a source claim would be
  exactly the lie this register exists not to tell. The chrome translates; the
  evidence does not.
- Numbers, dates and currency go through `Intl`. `count()` currently hardcodes
  `'en-IN'` — that is a bug in every other locale.
- The design must survive German (long) and Japanese (short, no spaces) without
  truncation or reflow damage. Test at least those two.
- Add `dir` handling now even without an RTL locale shipping — it is three lines
  today and a rewrite later.

## Doctrine you inherit (do not violate)

- **Absence stays absence.** A missing fact renders as nothing, never as a
  guess. A derivation says it is derived. A claim states its source. The gate
  must not imply data it does not have.
- The page is a **renderer**. It reads the JSON the build wrote; it never
  recomputes a fact.
- Dependency-free. No bundler, no npm, no framework. One HTML file, plus Clerk
  from its CDN. Fonts from Google Fonts are already accepted.
- Comments in this codebase explain *why*, in prose. Match that voice — a
  comment that says what the line does is noise here.
- Mark deliberate shortcuts with a `ponytail:` comment naming the ceiling.

## What you are handed

`site/index.html` — 3,384 lines, self-contained, currently a Swiss /
International Typographic "atlas plate": one twelve-column grid, hairline
rules, one red, tabular numerals, a plate-index chart for navigation. It is
good. It is also not the only answer.
