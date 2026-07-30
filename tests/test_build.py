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
    carry_salary,
    country_counts,
    errors,
    integrity_errors,
    published,
    website_counts,
    write,
)
from src.countries import COUNTRIES
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

    The real Provider with only its fetching swapped: the field names it reads a
    title, a URL and a workplace from are part of what these tests are checking,
    so a hand-built stand-in would test a table nothing ships.

    Greenhouse's description pass is swapped too, and it answers with the same
    board — which is what the live API does, `content=true` being the same board
    with the prose in it. Without this a unit test would go to the network for
    every listed company.
    """
    def answer(slug):
        return boards[slug]

    provider = PROBES[ats]._replace(probe=answer)
    return {ats: provider._replace(describe=answer) if provider.describe else provider}


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
                    "countries": ["India"],
                    "workplace": None,
                    # T8.4/T8.3: the fixture's own description says "we do sponsor
                    # visas! However, we aren't able to..." — the both-polarity
                    # shape that is 76 real postings, and it reads as a yes. It
                    # says nothing about relocating anyone, so that stays unknown.
                    "visa": "yes",
                    "hire_from_abroad": "unknown",
                },
                {
                    "title": "Staff Engineer, Data",
                    "url": "https://job-boards.greenhouse.io/acme/jobs/5988684006",
                    "locations": ["Bengaluru, India; Mumbai, India"],
                    "countries": ["India"],
                    "workplace": None,
                    # "You must have the right to work in India" — one sentence
                    # refusing the visa and the relocation together.
                    "visa": "no",
                    "hire_from_abroad": "no",
                },
            ],
            "countries": ["India"],  # what the site's country tabs offer
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
    "countries": ["India"],
    "workplace": None,
    "visa": "unknown",
    "hire_from_abroad": "unknown",
}


@pytest.mark.parametrize(
    ("field", "value", "because"),
    [
        ("roles", [], "at least one target-country role"),  # the ambiguous zero
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
        # T8.4's own. A role's countries are what put it here, so an empty list
        # is the same contradiction an empty location list is — and a country
        # outside the fifteen is a matcher this site has no tab for.
        ("roles", [{**ROLE, "countries": []}], "not a non-empty list of target countries"),
        ("roles", [{**ROLE, "countries": ["Poland"]}], "not a non-empty list of target countries"),
        ("roles", [{**ROLE, "countries": "India"}], "not a non-empty list of target countries"),
        # SPEC feature 15: silence is `unknown`, and `unknown` is a word. A null
        # or a blank here would render as an absence the site cannot tell from
        # "we read the posting and it said nothing".
        ("roles", [{**ROLE, "visa": None}], "visa None is not one of"),
        ("roles", [{**ROLE, "visa": "maybe"}], "visa 'maybe' is not one of"),
        ("roles", [{**ROLE, "hire_from_abroad": ""}], "hire_from_abroad '' is not one of"),
        ("roles", [{k: v for k, v in ROLE.items() if k != "visa"}], "missing 'visa'"),
        # The company's country set is derived from its roles, so a row that
        # states a country none of its roles is in would put itself under a tab
        # that reveals nothing.
        ("countries", ["India", "Japan"], "is not its roles'"),
        ("countries", [], "is not its roles'"),
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
    # T8.4's three, for the country tabs and the openness badge T8.5 builds on.
    # A dataset of India-only companies would let a broken tab pass, and one
    # where every verdict is the same would let "unknown" render as "no".
    listed_countries = {c for row in shipped["companies"] for c in row["countries"]}
    assert len(listed_countries) > 1, "no country-tab case: every company is in one country"
    assert any(
        "India" not in row["countries"] for row in shipped["companies"]
    ), "no company outside India, so the India-only enrichments prove nothing"
    assert any(len(row["countries"]) > 1 for row in shipped["companies"]), "no two-country company"
    for field in ("visa", "hire_from_abroad"):
        assert {role[field] for role in roles} == {"yes", "no", "unknown"}, f"{field} lacks a case"
    # The India-only enrichments must be absent wherever India is (SPEC v2), or
    # the fixture would assert a shape the build cannot produce.
    assert not [
        row
        for row in shipped["companies"]
        if "India" not in row["countries"] and (row["salary"] or row["mca"])
    ], "an India enrichment on a company with no India role"
    # And T8.5's other half: the site renders those enrichments under the country
    # views that contain India and hides them under the ones that don't. Only a
    # company that HAS one and also hires outside India can prove that — without
    # it the e2e's "no India enrichment here" comes back green off a row that had
    # nothing to render in the first place.
    assert any(
        (row["salary"] or row["mca"]) and set(row["countries"]) - {"India"}
        for row in shipped["companies"]
    ), "no India-enriched company with a role outside India"


# --- T8.4, the description pass -----------------------------------------------

#: The cheap Greenhouse pass: the same board with `content` gone, which is
#: literally what `content=false` returns. Derived rather than committed as a
#: second fixture, so the two passes cannot drift apart in the fixtures.
CHEAP = [{k: v for k, v in role.items() if k != "content"} for role in BOARD]


def two_pass(cheap=CHEAP, rich=BOARD):
    """A Greenhouse that answers one board cheaply and another with the prose,
    recording which pass was asked for."""
    calls: list[str] = []

    def probe(slug):
        calls.append("probe")
        return cheap

    def describe(slug):
        calls.append("describe")
        return rich

    return {"greenhouse": PROBES["greenhouse"]._replace(probe=probe, describe=describe)}, calls


def test_the_description_pass_runs_only_for_a_board_that_matched():
    """T8.1's affordable strategy, which is an ordering: 259 of 422 Greenhouse
    boards have no posting in any target country, and the 13.7x-35.3x payload
    multiplier must not be paid on them. So the country filter runs on the cheap
    board, and only a board that will contribute a row is fetched again."""
    probes, calls = two_pass()
    build(CORPUS[:1], {"Acme": GREENHOUSE}, probes)
    assert calls == ["probe", "describe"]

    nowhere = json.loads(board("Warsaw, Poland"))["jobs"]
    probes, calls = two_pass(cheap=nowhere)
    rows, outcomes = build(CORPUS[:1], {"Acme": GREENHOUSE}, probes)

    assert outcomes == {"Acme": Outcome.NO_TARGET_ROLES}
    assert calls == ["probe"], "a board with nothing for us was fetched a second time"
    assert rows == []


def test_openness_comes_from_the_second_pass_not_the_first():
    """The cheap pass carries no prose at all, so a role read off it is `unknown`
    on both fields — which is the honest answer for a posting whose text we never
    fetched, and exactly what the site must not render as "no"."""
    probes, _ = two_pass()
    rows, _ = build(CORPUS[:1], {"Acme": GREENHOUSE}, probes)
    assert [(r["visa"], r["hire_from_abroad"]) for r in rows[0]["roles"]] == [
        ("yes", "unknown"),
        ("no", "no"),
    ]

    # The same build with the second pass returning the cheap board: same rows,
    # same roles, no verdicts.
    probes, _ = two_pass(rich=CHEAP)
    silent, _ = build(CORPUS[:1], {"Acme": GREENHOUSE}, probes)
    assert [(r["visa"], r["hire_from_abroad"]) for r in silent[0]["roles"]] == [
        ("unknown", "unknown"),
        ("unknown", "unknown"),
    ]


@pytest.mark.parametrize(
    "rich, because",
    [
        (Outcome.PROBE_FAILED, "the second call failed outright"),
        ([], "the second call answered with a board that lost the role"),
    ],
)
def test_a_failed_description_pass_costs_the_openness_never_the_company(rich, because):
    """We DID read this board — the company is listed and its roles are whole. A
    description pass that fails afterwards is a fact we could not learn about a
    posting, not a company we could not check, and collapsing the two would put
    `probe-failed` on a company whose board we are holding."""
    probes, _ = two_pass(rich=rich)

    rows, outcomes = build(CORPUS[:1], {"Acme": GREENHOUSE}, probes)

    assert outcomes == {"Acme": Outcome.LISTED}, because
    assert len(rows[0]["roles"]) == 2
    assert all(role["visa"] == "unknown" for role in rows[0]["roles"])
    assert errors(rows[0]) == []


def test_a_provider_that_ships_its_prose_is_never_asked_twice():
    """Ashby and Lever send the descriptions whether we want them or not (T8.1),
    so there is no second pass to make — and `describe` being None is what says
    so. A wrapper that "unified" the three would be a call this build cannot
    afford, made 315 times a night for nothing."""
    assert PROBES["ashby"].describe is None
    assert PROBES["lever"].describe is None
    assert PROBES["greenhouse"].describe is not None


def test_ashby_and_lever_openness_is_read_off_the_board_we_already_fetched():
    """The other half: prose that arrived unasked still has to reach the role.
    Lever's is the one that needs care — the sponsorship boilerplate lives in
    `additional`, which a `descriptionPlain`-only reader never sees."""
    postings = json.loads(ashby_board(("Bengaluru, India",)))["jobs"]
    postings[0]["descriptionPlain"] = "We are unable to offer visa sponsorship for this role."
    rows, _ = build(
        CORPUS[:1], {"Acme": Slug(ats="ashby", slug="acme", method="guess")},
        answering("ashby", acme=postings),
    )
    assert rows[0]["roles"][0]["visa"] == "no"

    postings = json.loads(lever_board(("Bengaluru, Karnataka",)))
    postings[0]["descriptionPlain"] = "Join us."
    postings[0]["additional"] = "<p>We do sponsor visas for this role.</p>"
    rows, _ = build(
        CORPUS[:1], {"Acme": Slug(ats="lever", slug="acme", method="careers-page")},
        answering("lever", acme=postings),
    )
    assert rows[0]["roles"][0]["visa"] == "yes"


def test_country_counts_name_every_country_including_the_empty_ones():
    """A zero is never ambiguous, in the build report as everywhere else: "no
    company listed with a role in Norway" is a finding, and a country missing
    from the mapping would read as one nobody looked for."""
    abroad = json.loads(board("London, United Kingdom", "Bengaluru, India"))["jobs"]
    rows, _ = build(CORPUS[:1], {"Acme": GREENHOUSE}, answering(acme=abroad))

    counted = country_counts(rows)

    assert set(counted) == set(COUNTRIES)
    assert counted["India"] == 1 and counted["United Kingdom"] == 1
    assert counted["Norway"] == 0
    # Companies, not roles, and a company in two countries is in both counts — so
    # these deliberately do not sum to the number listed.
    assert sum(counted.values()) == 2 and len(rows) == 1


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


def test_no_target_roles_is_a_finding_not_a_gap():
    """The one honest exclusion: we read their whole board and none of it was in
    a country we cover. Note what that board contains — `In-Office` must not
    rescue it, and neither must a place that merely sounds like one of ours
    (`Cambridge, MA` is not the UK, `Perth` is not Australia)."""
    empty = json.loads(
        board("Warsaw, Poland", "In-Office", "Indianapolis, Indiana", "Cambridge, MA", "Perth")
    )["jobs"]

    rows, outcomes = build(CORPUS[:1], {"Acme": GREENHOUSE}, answering(acme=empty))

    assert outcomes == {"Acme": Outcome.NO_TARGET_ROLES}
    assert rows == []


def test_a_company_hiring_only_outside_india_is_now_listed():
    """T8.4 is the widening, and this is what widened: a board with no India role
    on it at all used to leave as a finding, and now leaves as a row. The India
    behaviour is preserved as one country of fifteen rather than re-litigated —
    `no-target-roles` still means we read the whole board and found nothing."""
    abroad = json.loads(board("London, United Kingdom", "Tokyo, Japan", "Warsaw, Poland"))["jobs"]

    rows, outcomes = build(CORPUS[:1], {"Acme": GREENHOUSE}, answering(acme=abroad))

    assert outcomes == {"Acme": Outcome.LISTED}
    assert rows[0]["countries"] == ["United Kingdom", "Japan"]  # COUNTRIES order, not board order
    assert [role["locations"] for role in rows[0]["roles"]] == [
        ["London, United Kingdom"],
        ["Tokyo, Japan"],
    ], "the Warsaw role is not a role this site has anything to say about"
    # The India-only fields degrade to absence rather than to a guess: there are
    # no India cities to filter on, and the enrichments never run (SPEC v2 keeps
    # AmbitionBox and the MCA register India's).
    assert rows[0]["cities"] == []
    assert rows[0]["salary"] is None and rows[0]["mca"] is None
    assert errors(rows[0]) == []


def test_one_posting_open_in_two_countries_is_one_role_in_both():
    """The multi-country posting, which is real: "London, UK; Sydney, Australia"
    is one job you can take in either place. It is one role, it carries both
    countries, and the company shows up under both tabs."""
    postings = json.loads(
        ashby_board(("London, United Kingdom", "Sydney, Australia"), ("Bengaluru, India",))
    )["jobs"]

    rows, _ = build(
        CORPUS[:1], {"Acme": Slug(ats="ashby", slug="acme", method="guess")},
        answering("ashby", acme=postings),
    )

    assert len(rows[0]["roles"]) == 2
    assert rows[0]["roles"][0]["countries"] == ["United Kingdom", "Australia"]
    assert rows[0]["countries"] == ["India", "United Kingdom", "Australia"]
    assert rows[0]["cities"] == ["Bengaluru"], "London and Sydney are not India cities"
    assert errors(rows[0]) == []


# --- T6.4, fail-safe publish --------------------------------------------------

#: A corpus with room for a provider to go dark in the MIDDLE of, which is the
#: shape of the failure: the companies probed before it went are listed, the ones
#: after it are `probe-failed`, and the file that results is complete and valid.
PARTIAL = [{**CORPUS[0], "name": f"Co{i}"} for i in range(10)]
SLUGS = {c["name"]: Slug(ats="greenhouse", slug=c["name"], method="careers-page") for c in PARTIAL}

#: A published benchmark, in the shape the schema demands (T4.2).
BENCHMARK = {
    "avg_lpa": 21.2,
    "reports": 340,
    "observed": "2025-10-12",
    "source_url": "https://www.ambitionbox.com/salaries/acme-salaries",
}


#: A night where every board answered. Named because it is the default: most of
#: these tests need one good run before they can break the next one.
EVERY = len(PARTIAL)


def dark_after(answers=EVERY):
    """A Greenhouse that answers `answers` boards and then stops. The default
    answers every one of them, which is a good night.

    Not a hypothetical: `greenhouse.probe` returns `probe-failed` on any status
    that isn't 200 or 404, so a provider going down does not raise, does not stop
    the run and does not fail the nightly's `set -e`. It empties the site.
    """
    seen = []

    def probe(slug):
        seen.append(slug)
        return BOARD if len(seen) <= answers else Outcome.PROBE_FAILED

    # The description pass answers whatever the cheap one did, which is what
    # Greenhouse does: a board that is dark is dark for both calls.
    return {"greenhouse": PROBES["greenhouse"]._replace(probe=probe, describe=lambda _: BOARD)}


def publish(path, probes, corpus=PARTIAL, slugs=SLUGS):
    """One whole run against the real spine: build, report, write."""
    rows, outcomes = build(corpus, slugs, probes)
    write(path, rows, report([c["name"] for c in corpus], outcomes))


def test_a_provider_that_goes_dark_mid_run_never_reaches_the_site(tmp_path):
    """T6.4's own check: break a probe mid-run, and the site still serves the last
    good data rather than a file with most of the companies missing."""
    out = tmp_path / "companies.json"
    publish(out, dark_after())
    good = out.read_bytes()

    with pytest.raises(ValueError, match="collapse, nothing written"):
        publish(out, dark_after(3))

    assert out.read_bytes() == good


def test_a_credible_loss_still_publishes(tmp_path):
    """The floor is a floor, not a hair trigger. Companies do stop hiring in
    India, and a guard that refused every loss would either hold the site at its
    high-water mark forever or teach whoever reads the failing nightly to ignore
    it."""
    out = tmp_path / "companies.json"
    publish(out, dark_after())
    publish(out, dark_after(6))

    assert len(json.loads(out.read_text())["companies"]) == 6


def kill_mid_write(monkeypatch):
    """Make the next write leave half a file behind and die, which is what a
    signal at the timeout does. Nothing computes the bytes lazily, so this is the
    only way the destination can be found truncated."""
    whole = Path.write_text

    def killed(self, text, *args, **kwargs):
        whole(self, text[: len(text) // 2])
        raise OSError("killed at the timeout")

    monkeypatch.setattr(Path, "write_text", killed)


def test_a_write_killed_partway_leaves_the_published_file_whole(tmp_path, monkeypatch):
    """The other half of a partial run: not a build that decides not to publish,
    a build that is killed while publishing. `timeout` in the nightly is 90
    minutes and it does fire; a truncated companies.json is a site that renders
    nothing at all."""
    out = tmp_path / "companies.json"
    publish(out, dark_after())
    good = out.read_bytes()

    kill_mid_write(monkeypatch)
    with pytest.raises(OSError):
        publish(out, dark_after())

    assert out.read_bytes() == good


@pytest.mark.parametrize(
    "content, because",
    [
        ('{"companies": [{"name": "Co0", "sal', "truncated mid-write by an older build"),
        ("", "the file exists and is empty"),
        ('{"schema_version": 9, "rows": []}', "a shape this code does not know"),
        ('{"companies": ["Co0", 3]}', "companies that are not companies"),
    ],
)
def test_a_corrupt_published_file_never_blocks_its_own_replacement(tmp_path, content, because):
    """The guard reads the file it is about to replace, so a bad file must not be
    able to fail the build — otherwise the one state that needs a fresh build the
    most is the one state that can't get one."""
    out = tmp_path / "companies.json"
    out.write_text(content)

    assert published(out) == [], because

    publish(out, dark_after())
    assert len(json.loads(out.read_text())["companies"]) == len(PARTIAL)


def test_a_throttled_night_keeps_the_figure_the_last_build_published(tmp_path):
    """T6.4, one field down. AmbitionBox rate-limits on cumulative volume (T4.2),
    and measured across two runs three hours apart it dropped 11 figures and
    added 11 — so a build that overwrites a real figure with `null` publishes a
    coverage regression that nothing in the world caused."""
    out = tmp_path / "companies.json"
    rows, outcomes = build(CORPUS[:1], {"Acme": GREENHOUSE}, answering(acme=BOARD))
    rows[0]["salary"] = BENCHMARK
    write(out, rows, report([c["name"] for c in CORPUS], outcomes))

    tonight, _ = build(CORPUS[:1], {"Acme": GREENHOUSE}, answering(acme=BOARD))

    assert tonight[0]["salary"] is None, "the enrichment found nothing tonight"
    assert carry_salary(tonight, out) == 1
    # Carried WITH its own observation date, which is the whole reason this is
    # honest: the figure states when it was sampled, so it claims nothing about
    # tonight. A board row has no date but the snapshot's — which is why T6.3
    # refused to republish one.
    assert tonight[0]["salary"] == BENCHMARK


def test_a_figure_observed_tonight_is_never_replaced_by_the_last_one(tmp_path):
    """Carrying forward is for an absence, never for a disagreement: the source
    recomputes, and the fresh figure is the one it recomputed."""
    out = tmp_path / "companies.json"
    rows, outcomes = build(CORPUS[:1], {"Acme": GREENHOUSE}, answering(acme=BOARD))
    rows[0]["salary"] = BENCHMARK
    write(out, rows, report([c["name"] for c in CORPUS], outcomes))

    tonight, _ = build(CORPUS[:1], {"Acme": GREENHOUSE}, answering(acme=BOARD))
    fresh = {**BENCHMARK, "avg_lpa": 24.8, "observed": "2026-07-29"}
    tonight[0]["salary"] = fresh

    assert carry_salary(tonight, out) == 0
    assert tonight[0]["salary"] == fresh


def test_a_carried_figure_that_no_longer_conforms_is_dropped_not_carried(tmp_path):
    """A schema bump would otherwise deadlock the build: it reads its own last
    output, carries a figure the new schema refuses, and then declines to write —
    every night, until a human deletes the file."""
    out = tmp_path / "companies.json"
    out.write_text(json.dumps({"companies": [{"name": "Acme", "salary": {"avg_lpa": 21.2}}]}))
    tonight, _ = build(CORPUS[:1], {"Acme": GREENHOUSE}, answering(acme=BOARD))

    assert carry_salary(tonight, out) == 0
    assert tonight[0]["salary"] is None
