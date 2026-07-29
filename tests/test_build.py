"""T5.1 — JSON schema and emit.

The spine's job is to lose no one: every company either becomes a row or leaves
with an outcome, and a row that doesn't conform never reaches the disk.
"""
import json
from pathlib import Path

import pytest

from src import lever
from src.build import (
    PROBES,
    SCHEMA_VERSION,
    build,
    errors,
    integrity_errors,
    website_counts,
    write,
)
from src.outcomes import Outcome, report
from src.slugs import Slug
from tests.test_ashby import board as ashby_board
from tests.test_greenhouse import board
from tests.test_lever import board as lever_board

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

#: A build report's footer counts (T5.3), for the tests that are about a row
#: rather than about the footer. The ones about the footer build a real report.
COUNTED = {"corpus_size": 2, "checked": 2, "unchecked": 0}


def answering(ats="greenhouse", **boards):
    """A probe map answering with the given roles-or-outcome per slug.

    The real Provider with only its probe swapped: the field names it reads a
    title, a URL and a workplace from are part of what these tests are checking,
    so a hand-built stand-in would test a table nothing ships.
    """
    return {ats: PROBES[ats]._replace(probe=lambda slug: boards[slug])}


def test_listed_row_carries_the_corpus_and_the_board():
    """A listed row is the funding facts plus what the board proved — and what it
    carries is the India roles themselves, not the board's size and not a count."""
    rows, outcomes = build(CORPUS[:1], {"Acme": GREENHOUSE}, answering(acme=BOARD))

    assert outcomes == {"Acme": Outcome.LISTED}
    assert rows == [
        {
            "name": "Acme",
            "ats": "greenhouse",
            "slug": "acme",
            # Two of the board's four roles; Warsaw and In-Office are not India.
            # Greenhouse states no workplace on any role, ever — so `None` here
            # is the measured normal case, not a fixture that forgot to say.
            "roles": [
                {
                    "title": "Senior Software Engineer, Platform",
                    "url": "https://job-boards.greenhouse.io/acme/jobs/5988684004",
                    "locations": ["Bengaluru, India"],
                    "workplace": None,
                },
                {
                    "title": "Staff Engineer, Data",
                    "url": "https://job-boards.greenhouse.io/acme/jobs/5988684006",
                    "locations": ["Bengaluru, India; Mumbai, India"],
                    "workplace": None,
                },
            ],
            "cities": ["Bengaluru", "Mumbai"],  # what the site's city filter offers
            "amount": 21000000,
            "currency": "USD",
            "round_letter": "A",
            "date": "2026-07-28",
            "source_url": "https://www.finsmes.com/2026/07/acme-raises-21m.html",
            "qualified_by": "letter",
            # The spine states the absence and the enrichments fill it in after
            # (T4.2, T4.4), so a row leaves `build` carrying both fields and
            # neither answer. A build that never reaches AmbitionBox, or one
            # running without an MCA snapshot, is complete rather than broken.
            "salary": None,
            "mca": None,
        }
    ]
    assert errors(rows[0]) == []


def test_an_ashby_row_counts_roles_not_places():
    """T3.2. One Ashby posting open in Bengaluru and Mumbai is one role in two
    cities. The unwrap is per-provider precisely so that the count doesn't
    quietly become "location strings that mention India" the moment a second
    ATS lands — Greenhouse gives one place per role and Ashby gives several.

    `errors()` passing is the other half: it rejects any `ats` without a probe,
    so a row reaching the site as `ashby` proves T3.2 is registered in PROBES."""
    postings = json.loads(
        ashby_board(("Bengaluru, India", "Mumbai, India"), ("Warsaw, Poland", "Remote - India"))
    )["jobs"]

    rows, outcomes = build(
        CORPUS[:1],
        {"Acme": Slug(ats="ashby", slug="acme", method="guess")},
        answering("ashby", acme=postings),
    )

    assert outcomes == {"Acme": Outcome.LISTED}
    assert len(rows[0]["roles"]) == 2  # two postings, not the three India strings
    assert rows[0]["cities"] == ["Bengaluru", "Mumbai"]  # the Warsaw role is also Remote - India
    # T4.1: the Warsaw posting is listed for its Remote - India half alone, and
    # its Warsaw location does not come along — this is a site about India roles.
    assert rows[0]["roles"][1]["locations"] == ["Remote - India"]
    assert rows[0]["roles"][1]["workplace"] == "remote"
    assert errors(rows[0]) == []


def test_a_lever_empty_board_never_reaches_the_site():
    """T3.3. The two halves of the last probe, in the spine rather than in the
    module: a board with India roles becomes a row — which `errors()` only
    accepts because `lever` is registered in PROBES — and an empty board leaves
    as `empty-board-unverified`, with no row and no zero.
    """
    postings = json.loads(lever_board(("Bengaluru, Karnataka", "Pune, Maharashtra")))
    slugs = {"Acme": Slug(ats="lever", slug="acme", method="careers-page")}

    rows, outcomes = build(CORPUS[:1], slugs, answering("lever", acme=postings))
    assert outcomes == {"Acme": Outcome.LISTED}
    assert len(rows[0]["roles"]) == 1, "one posting open in two cities is one role"
    assert rows[0]["cities"] == ["Bengaluru", "Pune"]
    # T4.1: Lever states the workplace itself, in its own casing. The board's
    # word wins over anything read out of the location string.
    assert rows[0]["roles"][0]["workplace"] == "hybrid"
    assert errors(rows[0]) == []

    rows, outcomes = build(CORPUS[:1], slugs, answering("lever", acme=lever.parse("[]")))
    assert outcomes == {"Acme": Outcome.EMPTY_BOARD_UNVERIFIED}
    assert rows == []


def test_a_directory_sourced_company_ships_without_a_round():
    """T1.2's rows: YC states that a company is past Series A, never which round
    or when. The absent date has to survive validation as an absence — a schema
    that demanded a string here would force the build to invent one."""
    company = {
        "name": "Epsilon",
        "amount": None,
        "currency": None,
        "date": None,
        "round_letter": None,
        "source_url": "https://www.ycombinator.com/companies/epsilon",
        "qualified_by": "stage",
    }

    rows, outcomes = build([company], {"Epsilon": GREENHOUSE}, answering(acme=BOARD))

    assert outcomes == {"Epsilon": Outcome.LISTED}
    assert errors(rows[0]) == []
    assert rows[0]["date"] is None and rows[0]["qualified_by"] == "stage"


ROLE = {
    "title": "Staff Engineer",
    "url": "https://job-boards.greenhouse.io/acme/jobs/1",
    "locations": ["Bengaluru, India"],
    "workplace": None,
}


@pytest.mark.parametrize(
    ("field", "value", "because"),
    [
        ("roles", [], "at least one India role"),  # the ambiguous zero
        ("roles", "two", "not"),
        ("name", None, "not"),
        ("qualified_by", "vibes", "qualified_by"),
        ("ats", "workday", "no probe"),
        # T4.1's own, one per way a role can be unpublishable. The location list
        # is the one that carries SPEC feature 7: a role that reached the site
        # by naming a place in India cannot then have nowhere to render.
        ("roles", [{**ROLE, "title": "  "}], "not a non-empty string"),
        ("roles", [{**ROLE, "url": None}], "not an http(s) URL"),
        ("roles", [{**ROLE, "url": "javascript:alert(1)"}], "not an http(s) URL"),
        ("roles", [{**ROLE, "locations": []}], "not a non-empty list of place names"),
        ("roles", [{**ROLE, "locations": "Bengaluru"}], "not a non-empty list of place names"),
        ("roles", [{**ROLE, "workplace": "wfh"}], "workplace"),
        ("roles", [{k: v for k, v in ROLE.items() if k != "url"}], "missing 'url'"),
        ("roles", [{**ROLE, "salary": "20 LPA"}], "unknown field"),
        ("roles", ["Staff Engineer"], "not a role"),
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
        write(out, [good, {**good, "name": "Zero", "roles": []}], COUNTED)

    assert not out.exists()


def test_written_file_is_versioned_and_revalidates(tmp_path):
    """Build → write → read back → every row still conforms."""
    rows, outcomes = build(CORPUS[:1], {"Acme": GREENHOUSE}, answering(acme=BOARD))
    out = tmp_path / "companies.json"
    write(out, rows, report([c["name"] for c in CORPUS], outcomes), snapshot="2026-07-28")

    shipped = json.loads(out.read_text())

    assert shipped["schema_version"] == SCHEMA_VERSION
    assert shipped["snapshot"] == "2026-07-28"  # the site shows this, so it ships with the data
    assert [errors(row) for row in shipped["companies"]] == [[]]
    # T5.3: the file also says who ISN'T in it. Acme was checked and listed; Beta
    # never reached a board, so the footer has one company to account for.
    assert shipped["integrity"] == {"corpus_size": 2, "checked": 1, "unchecked": 1}


def test_the_footer_counts_the_companies_the_site_cannot_show(tmp_path):
    """T5.3. The site's whole claim is that a company it can't check is left off
    rather than shown as not hiring — so the file carries how many those were.
    The numbers are the report's own, because a second count of the same thing is
    a second chance to disagree with it."""
    rows, outcomes = build(CORPUS, {"Acme": GREENHOUSE}, answering(acme=BOARD))
    built = report([c["name"] for c in CORPUS], outcomes)
    out = tmp_path / "companies.json"
    write(out, rows, built)

    shipped = json.loads(out.read_text())["integrity"]

    assert shipped == {field: built[field] for field in shipped}
    assert shipped["checked"] + shipped["unchecked"] == shipped["corpus_size"]
    assert shipped["corpus_size"] == len(CORPUS)


@pytest.mark.parametrize(
    "counted, because",
    [
        ({"corpus_size": 9, "checked": 1, "unchecked": 1}, "footer would not add up"),
        ({"corpus_size": 2, "checked": 0, "unchecked": 2}, "fewer than the 1 companies listed"),
        ({"corpus_size": 2, "checked": 1}, "missing 'unchecked'"),
        ({"corpus_size": 2, "checked": 1, "unchecked": None}, "unchecked None is not a count"),
        ({"corpus_size": 2, "checked": 1, "unchecked": 1, "listed": 1}, "unknown field"),
    ],
)
def test_footer_counts_that_do_not_account_for_the_corpus_are_refused(counted, because):
    """A footer that doesn't add up is worse than no footer: it states a number
    for the companies nobody checked, which is the one thing on this site a
    reader cannot check for themselves."""
    rows, _ = build(CORPUS[:1], {"Acme": GREENHOUSE}, answering(acme=BOARD))

    assert any(because in problem for problem in integrity_errors(counted, len(rows)))


def test_a_footer_that_does_not_add_up_fails_the_build_and_writes_nothing(tmp_path):
    """The same refusal a bad row gets, for the same reason: the site renders
    this straight. In practice it arrives as a report from a different run than
    the rows — `write` takes the whole report, so its OTHER keys are its own
    business and are filtered, but the three it publishes must describe these
    rows and this corpus."""
    rows, _ = build(CORPUS[:1], {"Acme": GREENHOUSE}, answering(acme=BOARD))
    out = tmp_path / "companies.json"

    with pytest.raises(ValueError, match="nothing written"):
        write(out, rows, {"corpus_size": 9, "checked": 1, "unchecked": 1})

    assert not out.exists()


def test_a_company_never_checked_is_never_listed():
    """Three ways to not know, none of which is "not hiring". The site's whole
    claim rests on the difference between a finding and a gap."""
    corpus = CORPUS + [{**CORPUS[0], "name": name} for name in ("Gone", "OnLever", "Broken")]
    slugs = {
        "Acme": GREENHOUSE,
        "Beta": GREENHOUSE,
        "OnLever": Slug(ats="lever", slug="onlever", method="careers-page"),
        "Broken": Slug(ats="greenhouse", slug="broken", method="careers-page"),
    }

    rows, outcomes = build(
        corpus, slugs, answering(acme=BOARD, broken=Outcome.SLUG_UNRESOLVED)
    )

    assert outcomes == {
        "Acme": Outcome.LISTED,
        "Beta": Outcome.LISTED,
        "Gone": Outcome.SLUG_UNRESOLVED,  # no slug was ever found
        "OnLever": Outcome.PROBE_FAILED,  # a slug we hold but cannot read until T3.3
        "Broken": Outcome.SLUG_UNRESOLVED,  # the board 404'd
    }
    assert {row["name"] for row in rows} == {"Acme", "Beta"}


def test_the_e2e_dataset_is_a_file_this_build_could_have_written():
    """The site's e2e drives a committed fixture dataset, because a real build's
    output is legitimately empty today (T5.1). A fixture the emitter could never
    produce would test the site against a shape that doesn't exist — so it is
    held to the same schema, and a version bump breaks it here rather than
    silently leaving the e2e testing last year's site."""
    shipped = json.loads(Path("tests/fixtures/companies-e2e.json").read_text())

    assert shipped["schema_version"] == SCHEMA_VERSION
    assert [errors(row) for row in shipped["companies"]] == [[]] * len(shipped["companies"])
    # T5.3's footer, which is about the companies that are NOT in this file — so
    # a fixture where everything was checked would render the one sentence the
    # footer exists to avoid, and prove nothing.
    assert integrity_errors(shipped["integrity"], len(shipped["companies"])) == []
    assert shipped["integrity"]["unchecked"], "no unchecked-companies case for the footer"
    # The city filter's negative case: filtering to Bengaluru must drop a company
    # whose only India city is Pune. Both have to be in the fixture for the e2e
    # assertion to mean anything.
    listed = [row["cities"] for row in shipped["companies"]]
    assert ["Pune"] in listed, "no city-filter negative case"
    assert any("Bengaluru" in cities for cities in listed), "no city-filter positive case"
    assert [] in listed, "no India-without-a-city case"
    # And the fully-degraded row a directory source produces (T1.2): no amount,
    # no letter, no date. Deleting it is how the site's null handling would come
    # back green with nothing exercising it.
    assert any(
        row["date"] is None and row["amount"] is None and row["qualified_by"] == "stage"
        for row in shipped["companies"]
    ), "no undated stage-qualified case"
    # T4.1's three, all measured on live boards and all rendered differently by
    # the site: a role stating remote, a role stating nothing, and a company with
    # no city AND no remote claim, whose location can only be what the board
    # literally said. Losing the last one is how the e2e's "never an empty
    # location" check would come back green with the blank cell restored.
    roles = [role for row in shipped["companies"] for role in row["roles"]]
    assert any(role["workplace"] == "remote" for role in roles), "no remote-filter positive case"
    assert any(role["workplace"] is None for role in roles), "no workplace-unstated case"
    assert any(
        not row["cities"] and not any(role["workplace"] == "remote" for role in row["roles"])
        for row in shipped["companies"]
    ), "no placeless-and-not-remote case"


def test_the_two_halves_of_slug_unresolved_are_counted_apart():
    """T1.6: "we read their careers page and found no board" and "we never had an
    address to read" both land on `slug-unresolved`, and they have different
    fixes — a better slug method against one, a better website source against the
    other. The build report has to say which is costing the site companies, or
    the next task is chosen by guesswork."""
    corpus = [
        {**CORPUS[0], "name": "Acme", "website": "https://acme.example"},
        {**CORPUS[0], "name": "Addressed", "website": "https://addressed.example"},
        {**CORPUS[0], "name": "Nameless Inc", "website": None},
    ]

    _, outcomes = build(corpus, {"Acme": GREENHOUSE}, answering(acme=BOARD))

    assert website_counts(corpus, outcomes) == {
        "with_website": 2,
        "slug_unresolved_with_website": 1,  # Addressed: a board we couldn't find
        "slug_unresolved_without_website": 1,  # Nameless Inc: nowhere to look
    }


def test_no_india_roles_is_a_finding_not_a_gap():
    """The one honest exclusion: we read their whole board and none of it was
    India. Note what that board contains — `In-Office` must not rescue it."""
    empty = json.loads(board("Warsaw, Poland", "In-Office", "Indianapolis, Indiana"))["jobs"]

    rows, outcomes = build(CORPUS[:1], {"Acme": GREENHOUSE}, answering(acme=empty))

    assert outcomes == {"Acme": Outcome.NO_INDIA_ROLES}
    assert rows == []
