"""T1.5 — merge, dedup, qualify.

The FinSMEs fixture supplies the real shapes (a stated letter, a seed round with
a big amount, an undisclosed round with neither); hand-built records supply the
duplicates, which one source's single page cannot.
"""
import random
from pathlib import Path

import pytest

from src import cbinsights, forbes, techcrunch
from src.corpus import MIN_AMOUNT, merge
from src.finsmes import Record, parse

FIXTURES = Path(__file__).parent / "fixtures"
FIXTURE = (FIXTURES / "finsmes-usa.html").read_text()


def _record(
    name: str,
    *,
    letter: str | None = None,
    amount: int | None = None,
    stage: str | None = None,
    website: str | None = None,
) -> Record:
    return Record(
        name=name,
        amount=amount,
        currency="USD" if amount else None,
        date="2026-07-28",
        round_letter=letter,
        source_url=f"https://www.finsmes.com/2026/07/{name.casefold()}-{letter}-{amount}.html",
        stage=stage,
        website=website,
    )


def test_dedup_order_independent():
    """Shuffling the sources must not change the corpus — including which round
    survives for a company seen more than once."""
    rounds = [
        _record("Acme", letter="A", amount=12_000_000),
        _record("Acme", letter="C", amount=60_000_000),  # strongest: must win
        _record("ACME", amount=6_000_000),  # same company, different casing
        _record("Beta Labs", amount=9_000_000),
        _record("Gamma", amount=1_000_000),  # unqualifiable, still accounted for
    ]

    expected = merge(rounds)
    assert [c["name"] for c in expected.companies] == ["Acme", "Beta Labs"]
    assert expected.companies[0]["round_letter"] == "C"

    shuffler = random.Random(0)
    for _ in range(20):
        shuffled = rounds[:]
        shuffler.shuffle(shuffled)
        # Split across two sources too: source order must not matter either.
        assert merge(shuffled[:2], shuffled[2:]) == expected


def test_qualified_by_exclusive():
    """Every corpus row carries exactly one rule, and it is the rule that fired."""
    corpus = merge(
        [
            _record("Lettered", letter="B", amount=1_000),  # letter wins over a tiny amount
            _record("Big Seed", amount=MIN_AMOUNT),  # threshold is inclusive
            _record("Small Seed", amount=MIN_AMOUNT - 1),
            _record("Grown", stage="growth"),  # a stage is the weakest evidence
            _record("Grown Up", letter="A", stage="growth"),  # ...and the last rule tried
            _record("Sprout", stage="early"),  # a stated stage that admits nothing
        ]
    )

    by_name = {c["name"]: c for c in corpus.companies}
    assert by_name["Lettered"]["qualified_by"] == "letter"
    assert by_name["Big Seed"]["qualified_by"] == "amount"
    assert by_name["Grown"]["qualified_by"] == "stage"
    assert by_name["Grown Up"]["qualified_by"] == "letter"
    assert corpus.unqualified == ["Small Seed", "Sprout"]

    for company in corpus.companies:
        assert company["qualified_by"] in {"letter", "amount", "stage"}


@pytest.mark.parametrize(
    "source, fixture",
    [
        (techcrunch.parse, "techcrunch-venture.json"),
        (forbes.parse, "forbes-ai50.json"),
        (cbinsights.parse, "cbinsights-unicorns.html"),
    ],
)
def test_adding_a_source_grows_the_corpus_and_demotes_nobody(source, fixture):
    """T1.4's DoD line, plus the invariant T1.3 learned the hard way: the thing
    to watch when a source lands is not whether the corpus grew but whether
    anything qualified left it. EDGAR's arrival demoted four companies by
    reporting a small round for them, and a bigger corpus hid it."""
    before = merge(parse(FIXTURE).records)
    after = merge(parse(FIXTURE).records, source((FIXTURES / fixture).read_text()))

    assert len(after.companies) > len(before.companies)
    assert {c["name"] for c in before.companies} <= {c["name"] for c in after.companies}


def test_unqualifiable_counted_not_dropped():
    """A round with neither letter nor amount is judged on nothing, so it is
    excluded — but it must still be named. Silent shrinkage looks exactly like a
    broken scraper, which is the failure this guards."""
    records = parse(FIXTURE).records
    corpus = merge(records)

    # PawPay's round is undisclosed: real company, no evidence, must be visible.
    assert "PawPay" in corpus.unqualified

    distinct = {r["name"].casefold() for r in records}
    accounted = {n.casefold() for n in corpus.unqualified} | {
        c["name"].casefold() for c in corpus.companies
    }
    assert accounted == distinct
