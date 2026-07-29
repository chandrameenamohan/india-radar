"""T1.7 — the software/sector filter.

The labelled set below is 30 real names taken from the live corpus, and the
software half is deliberately stacked with the traps: `Grafana Labs` and
`Cockroach Labs` (a laboratory reading deletes them), `Circle Medical` and
`Surgical Safety Technologies` (health software, not devices), `Drip Capital`
(lending software, not a fund), `Fleet Device Management` (SaaS), and `0x` and
`N26`, whose names are mostly digits. A vocabulary that looks reasonable and was
never measured rejects every one of them.
"""
import pytest

from src.corpus import merge
from src.finsmes import Record
from src.software import AMBIGUOUS, NOT_SOFTWARE, Verdict, classify

#: Hand-labelled, all from data/corpus.json. Ambiguous means genuinely so: each
#: of these names carries real sector signal that a name alone cannot settle.
CLEAR_SOFTWARE = [
    "Stripe",
    "Figma",
    "Databricks",
    "Zepto",
    "DoorDash",
    "Grafana Labs",
    "Cockroach Labs",
    "Circle Medical",
    "Surgical Safety Technologies",
    "Drip Capital",
    "Fleet Device Management",
    "N26",
]
CLEAR_NOT_SOFTWARE = [
    "Spero Foods",
    "Nobell Foods",
    "Cirrus Therapeutics",
    "C16 Biosciences",
    "Verge Genomics",
    "Navitas Semiconductor",
    "XTI Aerospace",
    "Function of Beauty",
    "AYC Fund",
]
GENUINELY_AMBIGUOUS = [
    "Gecko Robotics",
    "Stoke Space",
    "Relativity Space",
    "Helion Energy",
    "Asher Bio",
    "Wearable Devices",
    "Quantum Surgical",
    "Ascent Solar Technologies",
    "Matic Robots",
]


def test_30_labelled_companies():
    """The DoD's line: zero clear-software rejections.

    Stated as "not excluded" rather than "verdict is SOFTWARE" because that is
    the error that matters — `Circle Medical` coming back AMBIGUOUS keeps it in
    the corpus and asks a human, which is the intended outcome. The other two
    groups are pinned exactly, so this cannot be satisfied by a classifier that
    excludes nothing.
    """
    assert len(CLEAR_SOFTWARE + CLEAR_NOT_SOFTWARE + GENUINELY_AMBIGUOUS) == 30

    for name in CLEAR_SOFTWARE:
        assert classify(name)[0] is not Verdict.NOT_SOFTWARE, f"rejected {name}"
    for name in CLEAR_NOT_SOFTWARE:
        assert classify(name)[0] is Verdict.NOT_SOFTWARE, f"kept {name}"
    for name in GENUINELY_AMBIGUOUS:
        assert classify(name)[0] is Verdict.AMBIGUOUS, f"not flagged: {name}"


def test_ambiguous_kept_and_flagged():
    """Kept AND flagged — both halves. A flag that drops the company is just an
    exclusion with a nicer name, and an unflagged keep is invisible."""
    corpus = _merge_names(["Stripe", "Gecko Robotics", "Spero Foods"])

    assert [c["name"] for c in corpus.companies] == ["Gecko Robotics", "Stripe"]
    assert corpus.ambiguous == {"Gecko Robotics": "robotics"}
    assert "Stripe" not in corpus.ambiguous


def test_exclusions_are_counted_not_dropped():
    """T1.5's rule, extended to sector: every distinct company leaves by exactly
    one door, and all the doors are counted. A corpus that shrinks silently is
    indistinguishable from a scraper that broke."""
    names = CLEAR_SOFTWARE + CLEAR_NOT_SOFTWARE + GENUINELY_AMBIGUOUS + ["011235813"]
    corpus = _merge_names(names)

    accounted = {c["name"] for c in corpus.companies} | set(corpus.unqualified)
    assert accounted.isdisjoint(corpus.not_software)
    assert accounted | set(corpus.not_software) == set(names)
    assert set(corpus.not_software) == {*CLEAR_NOT_SOFTWARE, "011235813"}
    # Every exclusion names the word that caused it, so it can be argued with.
    assert corpus.not_software["Spero Foods"] == "foods"
    assert corpus.not_software["011235813"] == "no letters in the name"


@pytest.mark.parametrize("name", ["011235813", "1910"])
def test_non_name_identifiers_are_unusable(name):
    """EDGAR files what the registrant typed. A number is not a company we can
    look up, so it is excluded — but by a rule narrow enough to keep `0x`."""
    assert classify(name) == (Verdict.NOT_SOFTWARE, "no letters in the name")


@pytest.mark.parametrize("name", ["0x", "N26", "G2", "R2", "01.AI"])
def test_mostly_digits_is_still_a_name(name):
    """The reason the rule above demands the absence of every letter: all five
    of these are real software companies in the live corpus."""
    assert classify(name)[0] is Verdict.SOFTWARE


def test_vocabularies_are_disjoint():
    """A term in both lists would make the verdict depend on which set is tried
    first, which is exactly the kind of silent ordering bug the corpus already
    learned to fear from `_strength`."""
    assert NOT_SOFTWARE.isdisjoint(AMBIGUOUS)


def _merge_names(names):
    """Run real names through the real merge — the filter is only correct where
    it actually runs, and that is inside the corpus, not beside it."""
    return merge(
        Record(
            name=name,
            amount=10_000_000,
            currency="USD",
            date="2026-07-29",
            round_letter=None,
            source_url="https://example.test/round",
            stage=None,
            website=None,
        )
        for name in names
    )
