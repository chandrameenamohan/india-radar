"""Openness heuristic — T8.3 (SPEC feature 15).

Two facts per posting, each `yes` / `no` / `unknown`: will this company sponsor a
visa, and will it hire someone who is not already where the role is. `unknown` is
the default and the common answer — 3,980 of 4,311 measured postings (92.32%) say
nothing at all. Silence is `unknown` and NEVER `no`.

**A sponsorship phrase is not a polarity.** That one measurement is the whole
design. `visa sponsorship` is the corpus's most common phrase (132 postings) and
37 of them carry a negation cue within 70 characters, because the same sixteen
characters are both of these:

    anthropic  "visa sponsorship: we do sponsor visas! however, we aren't able to
                successfully sponsor visas for every role and every candidate."
    pleo       "we are unable to offer visa sponsorship for this role in any of
                the listed locations."

So nothing here asks whether a phrase is present. It finds every `sponsor*` that
sits near visa vocabulary and reads the 60 characters in front of it for a
negation cue. Counted that way over the whole corpus `no` is the *more common*
answer: 148 postings negative (3.43%), 107 positive (2.48%), 76 carrying both
polarities (1.76%), 3,980 silent.

Four phrases from the list T8.1 was handed are absent, each naming its zero:

  - `sponsorship available` — **0 postings**. The company that means it writes
    "visa sponsorship*s are* available" (spellbrush, 6 postings), which the
    proximity rule reads for free without the phrase being listed.
  - `remote worldwide` — **0 postings**.
  - `no visa sponsorship` — **0 postings**. Nobody writes a negative that way;
    what they write is measured in `_REQUIRES_EXISTING_RIGHT` below.
  - `we sponsor` — 58 postings on 2 boards, 27 of them physicsx sponsoring women
    from disadvantaged backgrounds through university degrees. Charity, not
    immigration. The visa-proximity requirement drops those 27 and keeps the 31
    genuine ones, so the phrase earns nothing by being listed.

A bare `sponsor` stem is refused in the other direction too: 48 postings say
"executive sponsor" or "customer sponsor" and mean a sales contact.

Every number above is from learning-tests/FINDINGS.md "Description text and
openness phrases", measured 2026-07-30 over 4,311 real postings in the 15 target
countries across 277 live boards — the whole of data/slugs.json, not a sample.
"""
from __future__ import annotations

import html
import re
from typing import NamedTuple


class Openness(NamedTuple):
    """What one posting says about hiring someone who is not already there.

    Both fields are `yes` / `no` / `unknown`. A NamedTuple so T8.4 can write
    `classify(text)._asdict()` straight into the role JSON, and so neither field
    can be read positionally by accident from the other's slot.
    """

    visa: str
    hire_from_abroad: str


#: Every answer either field can carry. Named here so that a schema checking a
#: role (src/build.py) checks against the vocabulary this module emits rather
#: than against a second copy of it that can drift.
VERDICTS = ("yes", "no", "unknown")

#: The answer for silence, for empty text, and for text we cannot read. One
#: object because it is one meaning: this module has nothing to say.
SILENT = Openness("unknown", "unknown")

#: Any word off the sponsor stem, matched only when the vocabulary below sits
#: beside it. On its own it is unusable in both directions — 48 "executive
#: sponsor" postings and physicsx's 27 university degrees.
_SPONSOR = re.compile(r"\bsponsor\w*")

#: What makes a `sponsor*` an immigration statement rather than a sales one.
#: These four terms are the ones openness_live.py counted with, so the 148/107/76
#: split quoted above is a measurement of this list and not of a similar one.
_VISA_CONTEXT = re.compile(r"\bvisas?\b|\bimmigration\b|\bwork permits?\b|\bright to work\b")

#: The cues that flip a sponsorship statement. Measured as this exact list; the
#: contractions are load-bearing because `\bnot\b` does not match "aren't", and
#: "aren't able to successfully sponsor" is 71 postings on its own.
_NEGATION = re.compile(
    r"\b(?:not|no|unable|unwilling|cannot|can't|aren't|isn't|won't|without|neither|nor)\b"
)

#: 60 characters before, 30 after — long enough to hold "we are not able to
#: provide visa", short enough that the previous sentence's "not" does not leak
#: in. The same two windows openness_live.py measured with.
_BEFORE, _AFTER = 60, 30

#: Explicit negatives that never say `sponsor`, so the proximity rule cannot see
#: them. `right to work in` is the highest-recall negative in the corpus by two
#: orders of magnitude — 117 postings over 15 boards, against 2 for the handed
#: `must have the right to work`. `authorized to work in` is 21 postings over 7
#: boards; the `s` spelling is unmeasured padding, kept because it costs one
#: character on a corpus that is 39% UK.
_REQUIRES_EXISTING_RIGHT = re.compile(r"\bright to work in\b|\bauthori[sz]ed to work in\b")

#: 170 postings (11 boards) say `relocation support`, 63 (2 boards) say
#: `relocation package`. Both are boilerplate — 113 of the 170 are helsing, 61 of
#: the 63 are n26 — and neither distinguishes a move from Berlin to Munich from a
#: move from Bengaluru to Munich. It is the best measured signal this field has
#: and it is weaker than its 233 postings look; `classify` says so out loud.
_RELOCATION = re.compile(r"\brelocation (?:support|package)\b")

#: 74 postings, and 42 of them are a holiday policy: "4 weeks work from anywhere
#: per year" (heidihealth 28, marshmallow 14, duffel 7). FINDINGS says to drop
#: the phrase; it is kept because SPEC names remote-from-anywhere as half of what
#: `hire_from_abroad` means, and because `_PERK` is the pattern that measured the
#: 42 — so the exclusion is the same rule that produced the number, not a guess.
_ANYWHERE = re.compile(r"\bwork from anywhere\b")
_PERK = re.compile(
    r"(?:weeks?|days?|months?)\s+(?:of\s+)?work from anywhere|work from anywhere\s+(?:for|per)\b"
)

#: Above this share of non-ASCII characters, the posting is not in English and
#: this module has nothing to say about it — SPEC's v2 non-goal, honestly, rather
#: than a phrase list guessing at a language it cannot read. Measured: 20 of 255
#: Japan postings (7.8%) are over 0.10, and 0 of 1,676 UK postings are over 0.05,
#: so nothing we *can* read comes near the line. It costs about 20 postings.
_NON_ASCII_LIMIT = 0.10

_SPACE = re.compile(r"\s+")

#: Markup, minimally. A tag becomes a space rather than nothing, because
#: `<li>Bengaluru</li><li>India</li>` glued into one word would hide both.
_TAG = re.compile(r"<[^>]+>")


def plain(markup: str | None) -> str:
    """The readable text inside a posting's markup — tags out, entities in.

    Lives here rather than in each provider because all three need it and none of
    them owns it: Greenhouse's `content` is escaped HTML, Lever's `lists[].content`
    is HTML, and Ashby's `descriptionPlain` is already flat but its
    `descriptionHtml` is not. `learning-tests/openness_live.py:plain` is the shape
    every measurement in this module's docstring was taken with, and this is it.

    **Greenhouse double-escapes**, so `&amp;lt;p&amp;gt;` needs two unescapes to
    become a tag and then be stripped. One unescape leaves `&lt;p&gt;` sitting in
    the text as literal angle brackets — visible junk that a phrase can hide
    inside. `html.unescape` on text with no entities is a no-op, so the second
    call costs the other two providers nothing.

    stdlib only: `html.unescape` and one regex. An HTML parser here would be a
    dependency bought to delete `<p>` — and `html.parser` in the stdlib would be
    thirty lines of subclass for the same result.
    """
    if not markup:
        return ""
    return _SPACE.sub(" ", _TAG.sub(" ", html.unescape(html.unescape(markup)))).strip()


def _readable(text: str) -> bool:
    """Is this text in a language whose phrases were measured, i.e. English?"""
    dense = "".join(ch for ch in text if not ch.isspace())
    if not dense:
        return False
    return sum(1 for ch in dense if ord(ch) > 127) / len(dense) <= _NON_ASCII_LIMIT


def _sponsorship(text: str) -> tuple[bool, bool]:
    """(said yes, said no) over every sponsorship statement in visa context.

    Both can be true. A posting that says it sponsors and then bounds the promise
    has said both things, and pretending otherwise is what a first-match-wins
    reader does; `classify` decides what the pair means.
    """
    yes = no = False
    for match in _SPONSOR.finditer(text):
        before = text[max(0, match.start() - _BEFORE):match.start()]
        after = text[match.end():match.end() + _AFTER]
        if not (_VISA_CONTEXT.search(before) or _VISA_CONTEXT.search(after)):
            continue  # "executive sponsor", "we sponsor bright women" — not immigration
        if _NEGATION.search(before):
            no = True
        else:
            yes = True
    return yes, no


def _verdict(yes: bool, no: bool) -> str:
    """A stated yes, else a stated no, else silence. The tie-break lives here."""
    return "yes" if yes else "no" if no else "unknown"


def classify(text: str | None) -> Openness:
    """Read one posting's prose for what it says about hiring from abroad.

    Takes the whole posting as one plain-text string. **The caller does the
    gluing**: a Lever posting splits its prose across `description`,
    `lists[].content` and `additional`, and the sponsorship boilerplate sits in
    `additional` — a `descriptionPlain`-only reader misses 62-77% of the text
    (measured, three boards). Greenhouse needs `?content=true`; Ashby already
    ships `descriptionPlain`. Tags and HTML entities are the caller's problem too,
    and `plain` above is the tool for it; whitespace and curly apostrophes are
    normalised here because the measurements were taken on flattened,
    straight-quoted text.

    **The tie-break, chosen deliberately and not by first match:** when a posting
    carries both polarities, the answer is `yes`. An unnegated sponsorship
    statement is a claim a company chose to make — nobody writes "we do sponsor
    visas" by accident — while the negated one beside it almost always *bounds*
    that claim rather than withdrawing it. The corpus agrees: 76 postings carry
    both, and 71 of them are one board (anthropic's "we do sponsor visas!
    however, we aren't able to successfully sponsor visas for every role"), which
    is a qualified yes. Reading those 71 as `no` would hide the corpus's largest
    genuine sponsor from the site's "open to foreign hires" filter, and `unknown`
    hides it just the same while sounding humbler about it. The cost of the
    choice, stated plainly: a posting whose benefits list offers sponsorship and
    whose small print excludes *this* role reads as `yes` here. T8.1 never
    counted that shape, so it is a risk taken with open eyes, not one measured
    away — and the 76 both-polarity postings are the population to recount if it
    ever looks wrong on the site.

    The two fields are read independently — a `visa: yes` does not imply
    `hire_from_abroad: yes`, and the site ORs them rather than one deriving the
    other. `right to work in` is the one signal that answers both questions: a
    company requiring the right you must already hold is refusing the visa and
    the relocation in one sentence.

    Non-English text and empty text both return `unknown` for both fields.
    """
    if not text:
        return SILENT
    body = _SPACE.sub(" ", text.replace("’", "'")).lower()
    if not _readable(body):
        return SILENT

    sponsors, refuses = _sponsorship(body)
    requires_existing = bool(_REQUIRES_EXISTING_RIGHT.search(body))
    anywhere = _ANYWHERE.search(body) and not _PERK.search(body)
    relocates = bool(_RELOCATION.search(body) or anywhere)

    # ponytail: a negated `sponsor*` with no visa word anywhere near it ("we
    # cannot sponsor candidates") is missed, because dropping the visa-context
    # requirement for negatives would re-admit the 48 "executive sponsor"
    # postings the moment one of them is phrased negatively. Ceiling: measure how
    # many such postings exist before widening — this one is unmeasured today.
    return Openness(
        visa=_verdict(sponsors, refuses or requires_existing),
        hire_from_abroad=_verdict(relocates, requires_existing),
    )
