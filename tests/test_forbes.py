"""T1.4 — Forbes company lists.

The fixture is the live AI 50 payload with five of its fifty rows kept verbatim:
two heavily funded, one modestly funded, and the two Forbes reports as
bootstrapped — which are the rows that decide what this source is allowed to claim.
"""
from pathlib import Path

from src.corpus import merge
from src.finsmes import Record
from src.forbes import parse

FIXTURE = (Path(__file__).parent / "fixtures" / "forbes-ai50.json").read_text()


def test_fixture_parse():
    by_name = {r["name"]: r for r in parse(FIXTURE)}

    assert set(by_name) == {"Abridge", "Anthropic", "Gamma", "Midjourney", "Surge AI"}
    assert by_name["Anthropic"]["source_url"] == "https://www.forbes.com/companies/anthropic/"

    assert parse(FIXTURE) == parse(FIXTURE)  # a pure function of the payload


def test_schema_matches_corpus_contract():
    """T1.1's schema, field for field — a source that drifts from it would be
    special-cased downstream, and the DoD says these flow through unaided."""
    for record in parse(FIXTURE):
        assert set(record) == set(Record.__annotations__)
        assert isinstance(record["name"], str) and record["name"]
        assert record["source_url"].startswith("https://")


def test_a_lifetime_total_is_never_reported_as_a_round():
    """`funding: 830` is $830M across Abridge's whole life. In `amount` it would
    be a round nobody raised, and SPEC feature 2's $5M proxy would judge it as one."""
    for record in parse(FIXTURE):
        assert record["amount"] is None
        assert record["currency"] is None
        assert record["round_letter"] is None
        assert record["date"] is None  # a list has a publication month, not a round date


def test_a_bootstrapped_company_carries_no_fundedness_claim():
    """Forbes reports 0 for Midjourney and Surge AI, and it is right — they are
    on the list for what they built, not for what they raised. A stage label
    there would qualify a company that has never raised a Series A."""
    by_name = {r["name"]: r for r in parse(FIXTURE)}

    assert by_name["Anthropic"]["stage"] == "growth"
    assert by_name["Abridge"]["stage"] == "growth"
    assert by_name["Gamma"]["stage"] == "growth"
    assert by_name["Midjourney"]["stage"] is None
    assert by_name["Surge AI"]["stage"] is None


def test_records_flow_through_merge_without_special_casing():
    corpus = merge(parse(FIXTURE))

    assert [c["name"] for c in corpus.companies] == ["Abridge", "Anthropic", "Gamma"]
    assert {c["qualified_by"] for c in corpus.companies} == {"stage"}
    # Excluded and counted, the same door an undisclosed round leaves by.
    assert corpus.unqualified == ["Midjourney", "Surge AI"]
