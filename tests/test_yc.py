"""T1.2 — YC directory source.

The fixture is five real records taken verbatim from the live directory, chosen
for the shapes that matter: both stages, an acquired company, and one whose
`website` is the empty string rather than absent.
"""
from pathlib import Path

from src.corpus import merge
from src.finsmes import Record
from src.yc import parse

FIXTURE = (Path(__file__).parent / "fixtures" / "yc-companies.json").read_text()


def test_fixture_parse():
    by_name = {r["name"]: r for r in parse(FIXTURE)}

    assert set(by_name) == {"Stripe", "Razorpay", "Conifer", "Brex", "Assembled"}
    assert by_name["Stripe"]["stage"] == "growth"
    assert by_name["Conifer"]["stage"] == "early"  # a current batch, pre-Series-A
    assert by_name["Stripe"]["source_url"] == "https://www.ycombinator.com/companies/stripe"

    # The directory states no round, so the record states none. A batch date is
    # not a funding date and would rank Stripe by 2009 under "recently funded".
    for record in by_name.values():
        assert record["amount"] is None
        assert record["currency"] is None
        assert record["round_letter"] is None
        assert record["date"] is None

    assert parse(FIXTURE) == parse(FIXTURE)  # a pure function of the payload


def test_schema_matches_corpus_contract():
    """T1.1's schema, field for field — a source that drifts from it would be
    special-cased downstream, and the DoD says these flow through unaided."""
    for record in parse(FIXTURE):
        assert set(record) == set(Record.__annotations__)
        assert isinstance(record["name"], str) and record["name"]
        assert isinstance(record["source_url"], str)
        assert record["source_url"].startswith("https://")


def test_growth_qualifies_and_early_is_excluded_not_dropped():
    """The stage rule is the only evidence YC gives, so it is what merge judges
    on — and the early-stage companies leave by the same counted door as an
    undisclosed round, never silently."""
    corpus = merge(parse(FIXTURE))

    assert [c["name"] for c in corpus.companies] == ["Assembled", "Brex", "Razorpay", "Stripe"]
    assert {c["qualified_by"] for c in corpus.companies} == {"stage"}
    assert corpus.unqualified == ["Conifer"]


def test_a_stated_round_outranks_a_stage_label():
    """A company both sources name keeps the round that was actually announced.
    The stage label says "past Series A" and no more, so it must never displace
    a record that says which letter and how much."""
    yc_row, = (r for r in parse(FIXTURE) if r["name"] == "Razorpay")
    announced = Record(
        name="Razorpay",
        amount=375_000_000,
        currency="USD",
        date="2026-07-28",
        round_letter="F",
        source_url="https://www.finsmes.com/2026/07/razorpay-raises-375m.html",
        stage=None,
        website=None,  # a FinSMEs headline states no address
    )

    for order in ([yc_row], [announced]), ([announced], [yc_row]):
        company, = merge(*order).companies
        assert company["qualified_by"] == "letter"
        assert company["round_letter"] == "F" and company["date"] == "2026-07-28"
        # The round that lost still knew where the company lives (T1.6). A
        # website is a fact about the company, not about the round, so losing
        # on strength must not take the only address in the corpus with it.
        assert company["website"] == "https://razorpay.com"
