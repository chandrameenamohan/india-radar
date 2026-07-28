"""T1.3 — SEC Form D (EDGAR) source.

The fixture is nine real issuer rows lifted verbatim from the 2026Q1 data set,
with every column SEC ships, chosen so that each thing the parser throws away is
represented by something that actually filed: a Bain credit fund, an amendment
restating a $71M round, a biotech, and a co-issuer on someone else's raise.

They live as two TSVs rather than a zip so the fixture stays readable in a diff;
the test zips them back into the shape `parse` is handed in production.
"""
import io
import zipfile
from datetime import date
from pathlib import Path

from src.corpus import merge
from src.edgar import QUARTERS, parse, quarters
from src.finsmes import Record
from src.yc import parse as yc_parse

FIXTURES = Path(__file__).parent / "fixtures"


def dataset() -> bytes:
    """The two TSVs as one quarterly zip, laid out the way SEC lays it out —
    including the `2026Q1_d/` directory the members hang under."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for table in ("ISSUERS", "OFFERING"):
            archive.writestr(
                f"2026Q1_d/{table}.tsv", (FIXTURES / f"edgar-{table.lower()}.tsv").read_bytes()
            )
    return buffer.getvalue()


def test_fixture_parse():
    by_name = {r["name"]: r for r in parse(dataset())}

    assert set(by_name) == {"Legora", "SOLIDROAD", "Core Foundry Labs", "Augmeta"}

    legora = by_name["Legora"]
    assert legora["amount"] == 441_525_860
    assert legora["currency"] == "USD"
    assert legora["date"] == "2026-03-09"  # date of first sale, not of filing
    assert legora["round_letter"] is None  # Form D states dollars, never a letter
    assert legora["stage"] is None
    # Verified 200 live. The CIK is zero-padded in the TSV and unpadded in the
    # path, and the accession appears twice in two different spellings.
    assert legora["source_url"] == (
        "https://www.sec.gov/Archives/edgar/data/2071663/"
        "000207166326000001/0002071663-26-000001-index.htm"
    )

    # An offering that has closed nothing yet reports a real zero, and one that
    # has named no sale date is undated rather than dated today.
    assert by_name["Core Foundry Labs"]["amount"] == 0
    assert by_name["Augmeta"]["date"] is None

    assert parse(dataset()) == parse(dataset())  # a pure function of the payload


def test_traps_are_excluded():
    """A naive Form D scrape is a directory of venture funds. Each exclusion here
    is a row that filed in the same quarter as the four we keep."""
    names = {r["name"] for r in parse(dataset())}

    assert not [n for n in names if "Bain" in n]  # pooled fund, and its co-issuer row
    assert not [n for n in names if "MIP HPC" in n]  # pooled fund
    assert "4C Medical Technologies" not in names  # D/A restating a counted round
    assert "Promaxo Holdings" not in names  # biotechnology — SPEC non-goal

    # ...and the amendment is not excluded merely for being small: it restates
    # $71M, more than two of the rows that survive.
    assert max(r["amount"] or 0 for r in parse(dataset())) > 71_608_160


def test_schema_matches_corpus_contract():
    """T1.1's schema, field for field — a source that drifts from it would be
    special-cased downstream, and the DoD says these flow through unaided."""
    for record in parse(dataset()):
        assert set(record) == set(Record.__annotations__)
        assert isinstance(record["name"], str) and record["name"]
        assert isinstance(record["source_url"], str)
        assert record["source_url"].startswith("https://www.sec.gov/")
        assert record["date"] is None or len(record["date"]) == len("YYYY-MM-DD")


def test_legal_suffix_is_stripped_but_the_name_is_not():
    """EDGAR files a registry name; the other sources publish a company name. The
    wrapper comes off so they dedup, and nothing else does — "Core Foundry Labs"
    keeps every word that is part of what the company is called."""
    names = {r["name"] for r in parse(dataset())}

    assert "Legora" in names  # "Legora, Inc."
    assert "SOLIDROAD" in names  # "SOLIDROAD INC." — casing is left alone
    assert "Core Foundry Labs" in names  # "Core Foundry Labs, LLC"
    assert "Augmeta" in names  # "Augmeta, Inc" — no trailing period


def test_dedups_against_another_source_without_special_casing():
    """The acceptance: EDGAR flows through T1.5's merge unaided. YC lists Legora
    with no amount; EDGAR states $441M for the same company. One row must come
    out, whichever order the sources arrive in, carrying the stronger evidence."""
    yc_row = yc_parse('[{"name": "Legora", "url": "https://www.ycombinator.com/companies/legora"}]')
    edgar_rows = parse(dataset())

    for order in (edgar_rows, yc_row), (yc_row, edgar_rows):
        corpus = merge(*order)
        legora = [c for c in corpus.companies if c["name"] == "Legora"]
        assert len(legora) == 1, "the same company must not be listed twice"
        assert legora[0]["qualified_by"] == "amount"
        assert legora[0]["amount"] == 441_525_860


def test_a_small_recent_round_never_disqualifies_a_company_another_source_qualifies():
    """A regression from wiring EDGAR in. YC calls Lob `Growth`; EDGAR reports it
    filing a $2M round. Both are true, and picking the record with the bigger
    number picked the one that then failed the $5M proxy — so a company past
    Series A dropped out of the corpus because a second source mentioned a small
    raise. Four real companies (Datafold, Legion Health, Lob, Overview) left the
    corpus this way before `_strength` learned to prefer qualifying evidence."""
    yc_row = yc_parse('[{"name": "Lob", "url": "https://www.ycombinator.com/companies/lob", '
                      '"stage": "Growth"}]')
    small = [Record(
        name="Lob",  # as edgar.parse emits it, the legal suffix already off
        amount=2_000_000,
        currency="USD",
        date="2026-03-01",
        round_letter=None,
        source_url="https://www.sec.gov/Archives/edgar/data/1/1/1-index.htm",
        stage=None,
    )]

    for order in (yc_row, small), (small, yc_row):
        corpus = merge(*order)
        assert corpus.unqualified == [], "a qualified company was demoted by a smaller round"
        company, = corpus.companies
        assert company["qualified_by"] == "stage"


def test_adding_the_source_strictly_increases_the_company_count():
    """The DoD's own line. Measured against a corpus that already holds the
    company EDGAR overlaps on, so the increase is net of a real dedup."""
    yc_row = yc_parse('[{"name": "Legora", "url": "https://www.ycombinator.com/companies/legora"}]')

    before = merge(yc_row)
    after = merge(yc_row, parse(dataset()))
    names = lambda c: {r["name"] for r in c.companies} | set(c.unqualified)  # noqa: E731

    assert names(before) < names(after)
    assert len(after.companies) > len(before.companies)


def test_quarter_candidates_outrun_the_publication_lag():
    """SEC publishes a quarter months after it closes, and how many months is not
    fixed — on 2026-07-28, Q2 was still 404 four weeks after it ended. So the
    candidate list must reach back past the newest quarters to find QUARTERS that
    exist, and must stay on the calendar while it does."""
    candidates = quarters(date(2026, 7, 28))

    assert candidates[:3] == ["2026q3", "2026q2", "2026q1"]
    assert len(candidates) > QUARTERS  # room to walk past the unpublished ones
    assert "2025q4" in candidates  # far enough back to reach a published one
    assert candidates == sorted(candidates, reverse=True)  # newest first
    assert all(q[-2] == "q" and q[-1] in "1234" for q in candidates)

    # Year rollover is arithmetic, not string munging.
    assert quarters(date(2026, 2, 1))[:3] == ["2026q1", "2025q4", "2025q3"]
