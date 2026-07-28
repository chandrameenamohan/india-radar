"""T1.4 — TechCrunch venture source.

The fixture is eleven real posts taken verbatim from the live venture category,
chosen for the shapes measured over 1,000 of them: the clean headline, the
descriptor prefix, the appositive clause, the two flavours of VC fund raise, the
valuation posing as a round, and two posts that are not funding news at all.
"""
from pathlib import Path

from src.corpus import merge
from src.finsmes import Record
from src.techcrunch import parse

FIXTURE = (Path(__file__).parent / "fixtures" / "techcrunch-venture.json").read_text()


def test_fixture_parse():
    by_name = {r["name"]: r for r in parse(FIXTURE)}

    assert set(by_name) == {"Cascade", "Nectar Social", "Stord"}

    assert by_name["Cascade"]["amount"] == 3_500_000
    assert by_name["Cascade"]["currency"] == "USD"
    assert by_name["Cascade"]["round_letter"] is None
    assert by_name["Cascade"]["date"] == "2026-07-22"
    assert by_name["Cascade"]["source_url"].startswith("https://techcrunch.com/2026/07/22/")

    # "Marketing operating system Nectar Social raises $30M Series A led by Menlo"
    # — the descriptor is prose, the letter is real.
    assert by_name["Nectar Social"]["round_letter"] == "A"
    assert by_name["Nectar Social"]["amount"] == 30_000_000

    assert parse(FIXTURE) == parse(FIXTURE)  # a pure function of the payload


def test_schema_matches_corpus_contract():
    """T1.1's schema, field for field — a source that drifts from it would be
    special-cased downstream, and the DoD says these flow through unaided."""
    for record in parse(FIXTURE):
        assert set(record) == set(Record.__annotations__)
        assert isinstance(record["name"], str) and record["name"]
        assert record["source_url"].startswith("https://")
        assert record["stage"] is None  # a headline announces a round, never a stage


def test_a_fund_raise_is_not_a_company():
    """The venture category covers the industry, not only the companies in it.
    Left in, these become rows on a site about who is hiring engineers."""
    names = {r["name"] for r in parse(FIXTURE)}

    assert "Seedcamp" not in names  # "raises $320M for its new fund"
    assert "Menlo Ventures" not in names  # a fund, and a firm-suffix name
    assert "Accel" not in names  # "raises $5B to back late-stage bets"


def test_a_headline_without_a_company_name_yields_nothing():
    """TechCrunch writes prose, and prose does not always name the company. A
    guessed name is worse than a missing row: it survives dedup as a new
    company and then fails every downstream check for the wrong reason."""
    names = {r["name"] for r in parse(FIXTURE)}

    assert "Edtech platform" not in names and "platform" not in names
    # "African defense tech Terra Industries, founded by two Gen Zers, raises…"
    assert not any("Gen Zers" in name for name in names)


def test_a_valuation_is_never_read_as_a_round():
    """Both numbers are in the same sentence and only one is money raised.
    Reading the larger would qualify companies on a round that never happened."""
    by_name = {r["name"]: r for r in parse(FIXTURE)}

    # "Amazon fulfillment competitor Stord raises $250M at $3B valuation"
    assert by_name["Stord"]["name"] == "Stord"  # not "Amazon fulfillment competitor"
    assert by_name["Stord"]["amount"] == 250_000_000

    # "Enterprise AI startup Glean lands a $7.2B valuation" states no round at
    # all, so it yields no record rather than a $7.2B one.
    assert "Glean" not in by_name


def test_an_unclosed_round_is_not_a_round():
    """"reportedly raising funding at a $20B valuation" is a rumour. The corpus
    records rounds that happened."""
    assert not any("Boring" in r["name"] for r in parse(FIXTURE))


def test_records_flow_through_merge_without_special_casing():
    corpus = merge(parse(FIXTURE))

    assert [c["name"] for c in corpus.companies] == ["Nectar Social", "Stord"]
    assert {c["qualified_by"] for c in corpus.companies} == {"letter", "amount"}
    # $3.5M clears no rule, so Cascade leaves by the counted door, not silently.
    assert corpus.unqualified == ["Cascade"]
