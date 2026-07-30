"""T8.3 — the openness heuristic.

The fixture is the test. Every line marked *quoted* below is text T8.1 read off a
live board and wrote into `learning-tests/FINDINGS.md`; every line marked *shape*
is the sentence frame FINDINGS counted (117 postings of `right to work in`, 170
of `relocation support`) written out, because FINDINGS records the counts and the
boards for those but not a verbatim sentence. Nothing here is invented to make a
rule look good, and the traps are here because they are the rules that a phrase
list gets wrong: a charity, a holiday policy, a sales contact, and a Japanese
posting whose English footer would otherwise be read as a promise.

Phrases the module deliberately does NOT carry each keep their zero in a comment,
so a future reader adding one back has to argue with the measurement.
"""
import pytest

from src.openness import SILENT, Openness, classify

# --- the corpus quotes -------------------------------------------------------
# (text, visa, hire_from_abroad). Lowercased because that is the shape T8.1
# measured over and the shape `classify` normalises to anyway.

POSTINGS = [
    # quoted (anthropic, 71 postings — 54% of every `visa sponsorship` posting in
    # the corpus). A yes and its bound in one paragraph. The phrase is identical
    # to pleo's below; only the words in front of it differ.
    ("visa sponsorship: we do sponsor visas! however, we aren't able to successfully "
     "sponsor visas for every role and every candidate.", "yes", "unknown"),
    # quoted (pleo, 19 postings). The same sixteen characters, flatly refused.
    ("we are unable to offer visa sponsorship for this role in any of the listed "
     "locations.", "no", "unknown"),
    # quoted (okx, 119 postings over 4 boards). No negation phrase from the handed
    # list appears; `do not` five words upstream of `sponsorship` is the whole
    # signal, which is why the window is read rather than a phrase matched.
    ("and do not require okx's sponsorship of a visa.", "no", "unknown"),
    # quoted (spellbrush, 6 postings). `sponsorship available` measured ZERO in
    # 4,311 postings because the company that means it writes it like this; the
    # proximity rule reads it without the dead phrase being listed.
    ("visa sponsorships are available for this position.", "yes", "unknown"),
    # shape (`right to work in`: 117 postings over 15 boards, against 2 for the
    # handed `must have the right to work`). Answers both questions at once.
    ("you must have the right to work in the united kingdom.", "no", "no"),
    # shape (`authorized to work in`: 21 postings over 7 boards).
    ("candidates must be authorized to work in the united states.", "no", "no"),
    # shape (`relocation support`: 170 postings, 113 of them helsing).
    ("we offer relocation support to help you make the move.", "unknown", "yes"),
    # shape (`relocation package`: 63 postings, 61 of them n26).
    ("we provide a relocation package for you and your family.", "unknown", "yes"),
    # quoted fragment (oyster). The one `work from anywhere` posting FINDINGS
    # says means what feature 15 means.
    ("no borders or hq — work from anywhere in the world.", "unknown", "yes"),
    # shape (`work permit` as visa context, the third of the four context terms).
    ("we do not sponsor work permits for this role.", "no", "unknown"),
    # shape (`immigration` as visa context, the fourth).
    ("our immigration team will sponsor your move.", "yes", "unknown"),
    # A posting that says both. The fields are read independently: they will pay
    # to move you, and they will not get you the right to be moved.
    ("we offer relocation support for this role. you must have the right to work "
     "in germany.", "no", "yes"),
]

# --- the traps ---------------------------------------------------------------
# Every one of these carries vocabulary from the handed phrase list and means
# something else. All must come back silent.

TRAPS = [
    # quoted (physicsx, 27 of the 58 `we sponsor` postings). A university degree,
    # not a visa. `we sponsor` is not in the module for exactly this reason.
    "to help make a change, we sponsor bright women from disadvantaged backgrounds "
    "through their university degrees",
    # quoted fragment (heidihealth 28, marshmallow 14, duffel 7 — 42 of the 74
    # `work from anywhere` postings). A holiday policy read as a hiring policy
    # would report those three companies as hiring from abroad on their PTO.
    "enjoy 4 weeks work from anywhere per year, plus 25 days of holiday",
    "we offer 30 days work from anywhere for each calendar year",
    # 48 postings say this and mean a sales contact. A bare `sponsor` stem is
    # unusable in both directions, so it never matches without visa vocabulary.
    "you will partner with the executive sponsor to drive adoption across the account",
    "you will be the customer sponsor for two strategic accounts",
    # The common case: 3,980 of 4,311 postings (92.32%) say nothing at all.
    "we are looking for a senior backend engineer to join our platform team in "
    "london. you will work with go, kubernetes and postgres.",
    # `remote worldwide` measured ZERO postings, and `no visa sponsorship` measured
    # ZERO — neither is in the module. A posting that is merely remote says
    # nothing about who may hold the job.
    "this is a fully remote role within european time zones.",
]

#: quoted shape (Japan: 20 of 255 postings are over 0.10 non-ASCII, spread over 12
#: boards; 0 of 1,676 UK postings are over 0.05). The English footer is the trap —
#: read on its own it is a promise, and this module cannot read the Japanese in
#: front of it that might withdraw it.
JAPANESE = "東京オフィス勤務。日本語必須。visa sponsorship available."


@pytest.mark.parametrize(("text", "visa", "abroad"), POSTINGS)
def test_real_excerpts_classify(text, visa, abroad):
    assert classify(text) == Openness(visa=visa, hire_from_abroad=abroad)


@pytest.mark.parametrize("text", TRAPS)
def test_silence_and_traps_are_unknown_never_no(text):
    """SPEC feature 15, the line the whole field hangs on: silence is rendered as
    unknown, NEVER as no. A trap is silence wearing the vocabulary of a signal."""
    assert classify(text) == SILENT


@pytest.mark.parametrize("text", [None, "", "   ", "\n\n"])
def test_absent_text_is_unknown(text):
    """T8.4 will hand this whatever the board gave it, including nothing."""
    assert classify(text) == SILENT


def test_non_english_is_unknown_and_the_ratio_is_what_stops_it():
    """SPEC's v2 non-goal, honestly: no translation, so a posting we cannot read
    gets unknown rather than a guess. The pairing is the point — the English
    footer classifies on its own, so it is the non-ASCII ratio that stops the
    Japanese posting and not an absence of phrases in it."""
    assert classify(JAPANESE) == SILENT
    assert classify("visa sponsorship available.") == Openness("yes", "unknown")


@pytest.mark.parametrize(
    "text",
    [
        "we are unable to offer visa sponsorship for this role",   # quoted (pleo)
        "we aren't able to successfully sponsor visas",            # quoted (anthropic)
        "and do not require okx's sponsorship of a visa",          # quoted (okx)
        "we are not currently able to sponsor visas",              # shape (6 postings)
        "no visa sponsorship is offered for this position",        # `no`
        "we cannot sponsor visas at this time",                    # `cannot`
        "we can't sponsor a visa for this role",                   # `can't`
        "the company isn't able to sponsor visas",                 # `isn't`
        "we won't sponsor a visa for this position",               # `won't`
        "we are unwilling to sponsor visas",                       # `unwilling`
        "candidates without a visa cannot be sponsored",           # `without`
        "neither visas nor work permits are sponsored",            # `neither` / `nor`
    ],
)
def test_every_negation_cue_flips_a_sponsorship_statement(text):
    """The twelve cues that came with the measured instrument, one line each. The
    first four are corpus quotes; the rest are the shortest grammatical frame for
    a cue, because a cue in the list that no test exercises is a cue nobody knows
    is spelled right."""
    assert classify(text).visa == "no"


def test_curly_apostrophes_do_not_silently_flip_a_no_into_a_yes():
    """`aren't able to successfully sponsor` is 71 postings on one board, and it
    is a contraction: `\\bnot\\b` cannot see it, so the negation list carries
    `aren't` and `classify` straightens the quote first. Without that line this
    text reads as an unqualified yes."""
    assert classify("we aren’t able to sponsor visas for this role").visa == "no"


def test_whitespace_is_flattened_before_matching():
    """Descriptions arrive as paragraphs, and the measurements were taken on
    flattened text. A phrase split by the line break it happens to fall on is a
    phrase that silently stops matching."""
    assert classify("we offer\nrelocation\nsupport.").hire_from_abroad == "yes"


def test_a_stated_yes_beats_a_stated_no_in_the_same_posting():
    """The tie-break, pinned. 76 postings carry both polarities and 71 of them are
    anthropic's qualified yes — a company that sponsors and then bounds the
    promise. Flipping this to `no` (or to `unknown`, which hides it just the same)
    drops the corpus's largest genuine sponsor out of the site's filter."""
    both = ("we do sponsor visas! however, we aren't able to successfully sponsor "
            "visas for every role.")
    assert classify(both).visa == "yes"
    # ... and the bound on its own, with nothing affirmative anywhere, is a no.
    assert classify("we aren't able to successfully sponsor visas.").visa == "no"


def test_post_phrase_negation_is_a_known_miss():
    """A decision not to build, pinned so it has a diff.

    The window is the 60 characters BEFORE a `sponsor*`, because that is the
    window that measured 148 negative / 107 positive / 76 both. Every negative
    FINDINGS read out of the corpus puts its cue in front — "unable to offer visa
    sponsorship", "do not require ... sponsorship", "aren't able to sponsor". A
    cue placed after the phrase is therefore unread, and this is what that costs.
    Widening the window is not free in the other direction: "we sponsor visas" is
    routinely followed by equal-opportunity boilerplate full of `not`. Measure
    before changing this, and change this test with it."""
    assert classify("visa sponsorship is not available for this role.").visa == "yes"
