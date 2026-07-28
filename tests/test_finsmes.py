"""T1.1 — FinSMEs corpus source.

The fixture is an unedited capture of https://www.finsmes.com/category/usa, ad
scripts and all. A hand-trimmed fixture would test the trimming, not the page.
"""
from pathlib import Path

from src.finsmes import parse

FIXTURE = (Path(__file__).parent / "fixtures" / "finsmes-usa.html").read_text()


def test_parses_fixture_page():
    records, unparsed = parse(FIXTURE)

    assert len(records) == 12
    assert not unparsed
    for record in records:
        assert record["name"]
        assert record["date"] == "2026-07-28"
        assert record["source_url"].startswith("https://www.finsmes.com/2026/07/")

    # Re-running yields the same set: the parse is a pure function of the page.
    assert parse(FIXTURE).records == records


def test_amount_and_letter_extraction():
    by_name = {r["name"]: r for r in parse(FIXTURE).records}

    # Decimals, and a K scale that must not be read as millions.
    assert by_name["Antares Labs"]["amount"] == 7_250_000
    assert by_name["Liquid Interactive"]["amount"] == 700_000
    assert by_name["CORE Biomedicine"]["amount"] == 21_000_000
    assert by_name["CORE Biomedicine"]["currency"] == "USD"

    # A stated letter is captured; a seed round genuinely has none, and guessing
    # one would qualify a company T1.5 must judge on amount alone.
    assert by_name["CORE Biomedicine"]["round_letter"] == "A"
    assert by_name["Dwelly"]["round_letter"] == "B"
    assert by_name["Antares Labs"]["round_letter"] is None
    assert by_name["Frenos"]["round_letter"] is None  # "Seed Extension"

    # An undisclosed round parses to a real company with no amount, rather than
    # vanishing. T1.5 excludes and counts it; dropping it here would hide it.
    assert by_name["PawPay"]["amount"] is None
    assert by_name["PawPay"]["currency"] is None


def test_unknown_headline_grammar_is_reported_not_dropped():
    """The source changing shape must be loud. This is how it shows up."""
    page = FIXTURE.replace(" Raises ", " Bamboozles ")

    records, unparsed = parse(page)

    assert len(unparsed) == 8
    assert any("Bamboozles" in title for title in unparsed)
    assert len(records) + len(unparsed) == 12
