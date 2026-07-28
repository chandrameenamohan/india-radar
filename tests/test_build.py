"""T5.1 — JSON schema and emit.

The spine's job is to lose no one: every company either becomes a row or leaves
with an outcome, and a row that doesn't conform never reaches the disk.
"""
import json
from pathlib import Path

import pytest

from src.build import SCHEMA_VERSION, build, errors, write
from src.outcomes import Outcome
from src.slugs import Slug
from tests.test_greenhouse import board

#: The same fixture board init.sh's smoke build runs on: four roles, of which
#: two are India — and one of the other two is the `In-Office` trap.
BOARD = json.loads(Path("tests/fixtures/greenhouse-board.json").read_text())["jobs"]

CORPUS = [
    {
        "name": "Acme",
        "amount": 21000000,
        "currency": "USD",
        "date": "2026-07-28",
        "round_letter": "A",
        "source_url": "https://www.finsmes.com/2026/07/acme-raises-21m.html",
        "qualified_by": "letter",
    },
    {
        "name": "Beta",
        "amount": 7250000,
        "currency": "USD",
        "date": "2026-07-28",
        "round_letter": None,
        "source_url": "https://www.finsmes.com/2026/07/beta-raises-7-25m.html",
        "qualified_by": "amount",
    },
]

GREENHOUSE = Slug(ats="greenhouse", slug="acme", method="careers-page")


def answering(**boards):
    """A probe map answering with the given roles-or-outcome per slug."""
    return {"greenhouse": lambda slug: boards[slug]}


def test_listed_row_carries_the_corpus_and_the_board():
    """A listed row is the funding facts plus what the board proved — and the
    count is India roles, not the board's size."""
    rows, outcomes = build(CORPUS[:1], {"Acme": GREENHOUSE}, answering(acme=BOARD))

    assert outcomes == {"Acme": Outcome.LISTED}
    assert rows == [
        {
            "name": "Acme",
            "ats": "greenhouse",
            "slug": "acme",
            "india_roles": 2,  # of four roles; Warsaw and In-Office are not India
            "amount": 21000000,
            "currency": "USD",
            "round_letter": "A",
            "date": "2026-07-28",
            "source_url": "https://www.finsmes.com/2026/07/acme-raises-21m.html",
            "qualified_by": "letter",
        }
    ]
    assert errors(rows[0]) == []


@pytest.mark.parametrize(
    ("field", "value", "because"),
    [
        ("india_roles", 0, "at least one India role"),  # the ambiguous zero
        ("india_roles", "two", "not"),
        ("name", None, "not"),
        ("qualified_by", "vibes", "qualified_by"),
        ("ats", "workday", "no probe"),
    ],
)
def test_schema_validation_rejects_bad_row(field, value, because):
    """The DoD check: every way a row can be wrong is caught before it ships."""
    good, = build(CORPUS[:1], {"Acme": GREENHOUSE}, answering(acme=BOARD))[0]

    assert any(because in problem for problem in errors({**good, field: value}))


def test_schema_validation_rejects_missing_and_unversioned_fields():
    """A dropped field and an extra one are the same failure: the row is not the
    shape the site was told to expect. An enrichment that adds a field without
    bumping the version has to fail here, or it ships unannounced."""
    good, = build(CORPUS[:1], {"Acme": GREENHOUSE}, answering(acme=BOARD))[0]

    assert errors({k: v for k, v in good.items() if k != "source_url"})
    assert errors({**good, "salary": "20 LPA"})


def test_a_bad_row_fails_the_build_and_writes_nothing(tmp_path):
    """Refusing to write beats writing a truncated file: the last good
    companies.json is still on disk and still true."""
    good, = build(CORPUS[:1], {"Acme": GREENHOUSE}, answering(acme=BOARD))[0]
    out = tmp_path / "companies.json"

    with pytest.raises(ValueError, match="nothing written"):
        write(out, [good, {**good, "name": "Zero", "india_roles": 0}])

    assert not out.exists()


def test_written_file_is_versioned_and_revalidates(tmp_path):
    """Build → write → read back → every row still conforms."""
    rows, _ = build(CORPUS[:1], {"Acme": GREENHOUSE}, answering(acme=BOARD))
    out = tmp_path / "companies.json"
    write(out, rows, snapshot="2026-07-28")

    shipped = json.loads(out.read_text())

    assert shipped["schema_version"] == SCHEMA_VERSION
    assert shipped["snapshot"] == "2026-07-28"  # the site shows this, so it ships with the data
    assert [errors(row) for row in shipped["companies"]] == [[]]


def test_a_company_never_checked_is_never_listed():
    """Three ways to not know, none of which is "not hiring". The site's whole
    claim rests on the difference between a finding and a gap."""
    corpus = CORPUS + [{**CORPUS[0], "name": name} for name in ("Gone", "OnAshby", "Broken")]
    slugs = {
        "Acme": GREENHOUSE,
        "Beta": GREENHOUSE,
        "OnAshby": Slug(ats="ashby", slug="onashby", method="careers-page"),
        "Broken": Slug(ats="greenhouse", slug="broken", method="careers-page"),
    }

    rows, outcomes = build(
        corpus, slugs, answering(acme=BOARD, broken=Outcome.SLUG_UNRESOLVED)
    )

    assert outcomes == {
        "Acme": Outcome.LISTED,
        "Beta": Outcome.LISTED,
        "Gone": Outcome.SLUG_UNRESOLVED,  # no slug was ever found
        "OnAshby": Outcome.PROBE_FAILED,  # a slug we hold but cannot read until T3.2
        "Broken": Outcome.SLUG_UNRESOLVED,  # the board 404'd
    }
    assert {row["name"] for row in rows} == {"Acme", "Beta"}


def test_no_india_roles_is_a_finding_not_a_gap():
    """The one honest exclusion: we read their whole board and none of it was
    India. Note what that board contains — `In-Office` must not rescue it."""
    empty = json.loads(board("Warsaw, Poland", "In-Office", "Indianapolis, Indiana"))["jobs"]

    rows, outcomes = build(CORPUS[:1], {"Acme": GREENHOUSE}, answering(acme=empty))

    assert outcomes == {"Acme": Outcome.NO_INDIA_ROLES}
    assert rows == []
