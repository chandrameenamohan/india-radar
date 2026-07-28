"""T1.4 — CB Insights unicorn board.

The fixture is eight rows of the live board, kept as the markup they arrive in:
the four industries SPEC admits, the three it rules out, and a company whose
profile slug is not its name (SingleStore files under `memsql`) so the source URL
cannot be reconstructed from the name.
"""
from pathlib import Path

from src.cbinsights import parse
from src.corpus import merge
from src.finsmes import Record

FIXTURE = (Path(__file__).parent / "fixtures" / "cbinsights-unicorns.html").read_text()


def test_fixture_parse():
    by_name = {r["name"]: r for r in parse(FIXTURE)}

    assert set(by_name) == {"Anthropic", "OpenAI", "SingleStore", "Revolut", "Next Insurance"}
    assert by_name["SingleStore"]["source_url"] == "https://www.cbinsights.com/company/memsql"

    assert parse(FIXTURE) == parse(FIXTURE)  # a pure function of the page


def test_schema_matches_corpus_contract():
    """T1.1's schema, field for field — a source that drifts from it would be
    special-cased downstream, and the DoD says these flow through unaided."""
    for record in parse(FIXTURE):
        assert set(record) == set(Record.__annotations__)
        assert isinstance(record["name"], str) and record["name"]
        assert record["source_url"].startswith("https://")


def test_a_valuation_is_never_reported_as_a_round():
    """$1B is what the company is worth, not what it raised, and the date is
    when it first crossed that line rather than when it last raised."""
    for record in parse(FIXTURE):
        assert record["amount"] is None
        assert record["currency"] is None
        assert record["round_letter"] is None
        assert record["date"] is None
        assert record["stage"] == "growth"  # $1B is past Series A by any reading


def test_sectors_spec_rules_out_never_enter_the_corpus():
    """Unfiltered, this source's largest contribution to a site about software
    jobs is manufacturers and biotechs — SPEC's non-goals, by the board's own
    industry column."""
    names = {r["name"] for r in parse(FIXTURE)}

    assert "Devoted Health" not in names  # Healthcare & Life Sciences
    assert "Figure" not in names  # Industrials
    assert "SHEIN" not in names  # Consumer & Retail


def test_records_flow_through_merge_without_special_casing():
    corpus = merge(parse(FIXTURE))

    assert [c["name"] for c in corpus.companies] == [
        "Anthropic",
        "Next Insurance",
        "OpenAI",
        "Revolut",
        "SingleStore",
    ]
    assert {c["qualified_by"] for c in corpus.companies} == {"stage"}
    assert corpus.unqualified == []
