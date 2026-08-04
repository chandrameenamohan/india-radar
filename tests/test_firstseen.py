"""The both-sides rule — T15.2.

SPEC v3 "Not a wall", measured 2026-08-01: one nightly diff gave 0 new companies
and 9 new roles while 179 roles disappeared, 176 of them companies the build
could not check that night. A naive diff is ~98% noise, and the noise is one
shape: absence of knowledge read as a finding.

So the guard these tests exist for is a single line in `advance` — a role may be
called new ONLY where its company was `listed` in the previous snapshot and in
this one. Every test below that names both_sides fails if that line is removed;
the mutation sweep in the T15.2 note records which, and it is not one test but
four, because the rule has four sides (previous-observed, currently-observed,
already-known, and the baseline that has no previous at all).

T16.1 added the fifth: **both builds must have been looking for the same thing.**
That is the one the four cannot see. The night T16.1 lands, every role this
register used to delete for being in São Paulo appears as a brand-new URL under a
company that was `listed` on both sides — and the four sides above all say yes.
It is the 1,604-roles-in-one-night failure T15.2 measured in this project's own
history, arriving a second time through a door the guard does not cover. So the
build states what it counted as a role (`build.ROLE_DEFINITION`), the artifact
carries it, and a night where the two disagree confirms nothing at all.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src.firstseen import SCHEMA_VERSION, advance, load, write

E2E_ARTIFACT = Path("tests/fixtures/first-seen-e2e.json")
E2E_DATA = Path("tests/fixtures/companies-e2e.json")


def snapshot(day: str, roles: dict[str, list[str]]) -> dict[str, Any]:
    """A companies.json document: company name -> the role URLs it published."""
    return {
        "schema_version": 10,
        "snapshot": day,
        "companies": [
            {"name": name, "roles": [{"url": url} for url in urls]}
            for name, urls in roles.items()
        ],
    }


def report(*listed: str, definition: str | None = "v2-any-stated-location") -> dict[str, Any]:
    """A build-report.json: the companies whose board this build actually read,
    and what that build counted as a role.

    The default is a real `build.ROLE_DEFINITION` value rather than a token,
    because every report the pipeline writes now carries one — a fixture that
    omitted it would exercise the transition path in every test and never the
    ordinary night. `definition=None` is the report a pre-T16.1 build wrote.
    """
    return {"listed": sorted(listed), **({} if definition is None else {"definition": definition})}


def dates(art: dict[str, Any], day: str) -> dict[str, list[str]]:
    return art["dates"].get(day, {"confirmed": [], "unconfirmed": []})


def test_the_first_snapshot_confirms_nothing() -> None:
    """The baseline. Every URL is being seen for the first time because there is
    no previous snapshot — not because anything opened. `advance` derives that
    from the artifact rather than being told, so a caller cannot get it wrong by
    forgetting an argument.
    """
    art = advance(None, snapshot("2026-08-01", {"Acme": ["u1", "u2"]}), report("Acme"))

    assert dates(art, "2026-08-01") == {"confirmed": [], "unconfirmed": ["u1", "u2"]}


def test_a_role_appearing_under_a_company_observed_both_nights_is_confirmed() -> None:
    """The one transition this feature is allowed to speak about: the board was
    read last night and again tonight, and tonight it holds a URL it did not.
    """
    first = advance(None, snapshot("2026-08-01", {"Acme": ["u1"]}), report("Acme"))
    art = advance(first, snapshot("2026-08-02", {"Acme": ["u1", "u2"]}), report("Acme"))

    assert dates(art, "2026-08-02")["confirmed"] == ["u2"]
    assert dates(art, "2026-08-02")["unconfirmed"] == []


def test_a_company_unchecked_last_night_yields_a_date_but_no_badge() -> None:
    """The 176. Acme's board could not be read last night, so tonight's roles are
    roles we are seeing for the first time — which is a fact about us, not about
    Acme. They get the date. They must not get the badge.
    """
    first = advance(None, snapshot("2026-08-01", {"Beta": ["b1"]}), report("Beta"))
    art = advance(
        first,
        snapshot("2026-08-02", {"Beta": ["b1"], "Acme": ["u1", "u2"]}),
        report("Beta", "Acme"),
    )

    assert dates(art, "2026-08-02") == {"confirmed": [], "unconfirmed": ["u1", "u2"]}


def test_a_company_missing_from_tonights_report_is_not_confirmed_either() -> None:
    """The other side of the same rule, and it is not symmetrical decoration: a
    row can reach companies.json while the report does not list it only if the
    two files disagree, and a disagreement is not evidence of a new job.
    """
    first = advance(None, snapshot("2026-08-01", {"Acme": ["u1"]}), report("Acme"))
    art = advance(first, snapshot("2026-08-02", {"Acme": ["u1", "u2"]}), report())

    assert dates(art, "2026-08-02")["confirmed"] == []
    assert dates(art, "2026-08-02")["unconfirmed"] == ["u2"]


def test_a_role_that_disappears_and_returns_keeps_its_first_date() -> None:
    """Set once, never revised. Acme's board was unreadable on the 2nd, so u1
    vanished from the file and came back on the 3rd. It is the same posting, and
    re-dating it would be the disappearance inference this module refuses to make
    in the other direction — the exact fault the 176 measure.
    """
    art = advance(None, snapshot("2026-08-01", {"Acme": ["u1"]}), report("Acme"))
    art = advance(art, snapshot("2026-08-02", {}), report())
    art = advance(art, snapshot("2026-08-03", {"Acme": ["u1"]}), report("Acme"))

    assert dates(art, "2026-08-01")["unconfirmed"] == ["u1"]
    assert "2026-08-03" not in art["dates"]


def test_the_previous_nights_observations_survive_in_the_artifact() -> None:
    """The nightly's whole memory. CI checks out at depth 1, so the only thing
    that can tell tomorrow which companies were read tonight is this field —
    drop it and every tomorrow silently becomes a baseline that confirms nothing.
    """
    art = advance(None, snapshot("2026-08-01", {"Acme": ["u1"]}), report("Acme", "Beta"))

    assert art["observed"] == ["Acme", "Beta"]


def test_a_snapshot_that_changes_nothing_rewrites_the_same_artifact() -> None:
    """Idempotence, which is what makes the nightly's "no change, no commit"
    branch mean anything: rebuilding the same data twice must not produce a diff.
    """
    once = advance(None, snapshot("2026-08-01", {"Acme": ["u1"]}), report("Acme"))
    twice = advance(once, snapshot("2026-08-01", {"Acme": ["u1"]}), report("Acme"))

    assert twice == once


def test_a_snapshot_predating_roles_is_folded_without_dating_anything() -> None:
    """Schema v1-v3 published companies and no roles (T4.1 added them). The
    backfill folds over those three too, and they must contribute no URL rather
    than raise — and must not make the next snapshot look like a transition.
    """
    art = advance(None, {"snapshot": "2026-07-28", "companies": [{"name": "Acme"}]}, report("Acme"))
    art = advance(art, snapshot("2026-07-29", {"Acme": ["u1"]}), report("Acme"))

    assert art["dates"] == {"2026-07-29": {"confirmed": [], "unconfirmed": ["u1"]}}


# --- T16.1, the night the build changes what it is looking for ----------------


def test_the_night_the_definition_changes_confirms_nothing() -> None:
    """The landmine T16.1 walks onto, in miniature.

    Acme's board was read last night and again tonight, and tonight it publishes
    two URLs it did not publish yesterday. Every side of the both-sides rule says
    yes. They are still not new: last night's build was deleting every role
    outside the fifteen and tonight's is not, so u2 and u3 are roles that were
    open all along and that this register was refusing to look at.

    Zero confirmed is the whole acceptance. The site badges nothing that night.
    """
    yesterday = snapshot("2026-08-04", {"Acme": ["u1"]})
    before = advance(None, yesterday, report("Acme", definition="v1"))
    widened = advance(
        before,
        snapshot("2026-08-05", {"Acme": ["u1", "u2", "u3"]}),
        report("Acme", definition="v2-any-stated-location"),
    )

    assert dates(widened, "2026-08-05")["confirmed"] == []
    assert dates(widened, "2026-08-05")["unconfirmed"] == ["u2", "u3"]


def test_the_night_after_a_widening_confirms_normally_again() -> None:
    """One night, not forever. The guard is about a BOUNDARY between two
    definitions — once both sides were built the same way there is nothing wrong
    with the diff, and a rule that kept refusing would be a badge that never
    comes back.
    """
    yesterday = snapshot("2026-08-04", {"Acme": ["u1"]})
    before = advance(None, yesterday, report("Acme", definition="v1"))
    widened = advance(before, snapshot("2026-08-05", {"Acme": ["u1", "u2"]}), report("Acme"))
    after = advance(widened, snapshot("2026-08-06", {"Acme": ["u1", "u2", "u3"]}), report("Acme"))

    assert dates(after, "2026-08-06")["confirmed"] == ["u3"]


def test_an_artifact_that_states_no_definition_confirms_nothing() -> None:
    """The production path, exactly as it runs the night T16.1 lands: the
    committed artifact was written before this field existed. Absent is not a
    match — a build that never said what it was looking for cannot be shown to
    have been looking for the same thing, and this module refuses that inference
    everywhere else already.
    """
    old = advance(None, snapshot("2026-08-04", {"Acme": ["u1"]}), report("Acme", definition=None))
    assert old["definition"] is None, "a pre-T16.1 artifact states nothing here"

    tonight = advance(old, snapshot("2026-08-05", {"Acme": ["u1", "u2"]}), report("Acme"))

    assert dates(tonight, "2026-08-05")["confirmed"] == []
    assert dates(tonight, "2026-08-05")["unconfirmed"] == ["u2"]


def test_a_build_that_states_no_definition_confirms_nothing_either() -> None:
    """The other side of the same absence, and the one that matters for a change
    to the pipeline rather than to the artifact: a build that stopped stating its
    definition would otherwise silently resume confirming against an artifact
    that states one, which is the failure this whole field exists to prevent.
    """
    first = advance(None, snapshot("2026-08-04", {"Acme": ["u1"]}), report("Acme"))
    art = advance(
        first, snapshot("2026-08-05", {"Acme": ["u1", "u2"]}), report("Acme", definition=None)
    )

    assert dates(art, "2026-08-05")["confirmed"] == []


def test_the_definition_survives_in_the_artifact() -> None:
    """The nightly's only memory of it, for the same reason `observed` is there:
    CI checks out at depth 1, so tomorrow can compare against tonight only if
    tonight wrote it down.
    """
    art = advance(None, snapshot("2026-08-04", {"Acme": ["u1"]}), report("Acme"))

    assert art["definition"] == "v2-any-stated-location"


def test_the_real_committed_artifact_confirms_nothing_across_a_definition_change() -> None:
    """The same rule against the real files rather than a fixture, because at this
    scale the numbers are the argument: `data/first-seen.json` is the artifact
    production is holding and `data/companies.json` is the register as published.

    Both directions are asserted, and that is the point. The same fold, the same
    real files, the same URLs nobody has seen — changed in ONE respect, the
    definition the build states — must confirm every one of them and then none of
    them. Asserting only the zero would leave a test that passes just as well
    when nothing is being confirmed for some other reason entirely.

    **This test was wrong when it was written and the real corpus is what caught
    it.** The first version folded a report stating the definition of the day and
    asserted zero, which held only while the committed artifact happened to state
    none. The moment the artifact was advanced — which is to say, the moment the
    thing this test describes actually happened — the same call became an
    ordinary night, confirmed 789 roles, and the test failed for being right.
    A check that depends on which side of a migration its fixtures are on is
    measuring the ambient state, not the rule.
    """
    prev = load()
    if prev is None:
        pytest.skip("no data/first-seen.json committed yet")
    published = json.loads(Path("data/companies.json").read_text())
    listed = [company["name"] for company in published["companies"]]
    # Every listed company gains a role, which is what a widening looks like from
    # inside the artifact: URLs nobody has seen, under companies read both nights.
    widened = {
        **published,
        "snapshot": "2999-01-01",
        "companies": [
            {**company, "roles": [*company["roles"], {"url": f"https://widened/{company['name']}"}]}
            for company in published["companies"]
        ],
    }
    # Whatever the artifact states, this is a build that states something else.
    # Derived rather than hardcoded, so the test keeps naming a boundary however
    # many times the definition moves after this one.
    changed = f"{prev.get('definition')}-and-then-something-else"

    ordinary = advance(prev, widened, {"listed": listed, "definition": prev.get("definition")})
    boundary = advance(prev, widened, {"listed": listed, "definition": changed})

    if prev.get("definition"):
        assert len(dates(ordinary, "2999-01-01")["confirmed"]) == len(listed), (
            "a night with the definition unchanged confirms a genuinely new URL under "
            "every company read on both sides — without this the zero below proves nothing"
        )
    badged = len(dates(boundary, "2999-01-01")["confirmed"])
    assert dates(boundary, "2999-01-01")["confirmed"] == [], (
        f"{badged} of {len(listed)} roles badged by a definition change alone — this is "
        f"the front page calling a week-old register New, and it is the failure T15.2 "
        f"measured at 1,604 roles in one night"
    )
    assert len(dates(boundary, "2999-01-01")["unconfirmed"]) == len(listed), (
        "the dates are still facts about us and still recorded"
    )


def test_load_refuses_an_artifact_from_a_schema_it_does_not_know(tmp_path: Path) -> None:
    """A corrupt or future artifact read as "absent" would restart the baseline:
    every role on the site re-dated to today. Dying leaves yesterday's committed
    file exactly where it is, which is `build.write`'s rule.
    """
    file = tmp_path / "first-seen.json"
    file.write_text(json.dumps({"schema_version": SCHEMA_VERSION + 1, "dates": {}}))

    with pytest.raises(ValueError, match="delete it to re-backfill"):
        load(file)

    assert load(tmp_path / "absent.json") is None


def test_a_written_artifact_reads_back_identical(tmp_path: Path) -> None:
    file = tmp_path / "first-seen.json"
    art = advance(None, snapshot("2026-08-01", {"Acme": ["u1"]}), report("Acme"))
    write(file, art)

    assert load(file) == art


def test_the_published_artifact_covers_every_published_role() -> None:
    """Against the real corpus, not a fixture. A role with no first-seen date
    renders no badge and sorts last — absence stays absence — so a gap here is
    silent on the page rather than loud, which is exactly the shape of hole that
    needs a check rather than an eye.
    """
    art = load()
    if art is None:
        pytest.skip("no data/first-seen.json committed yet")
    dated = {url for day in art["dates"].values() for urls in day.values() for url in urls}
    published = {
        role["url"]
        for company in json.loads(Path("data/companies.json").read_text())["companies"]
        for role in company["roles"]
    }

    assert not published - dated, f"{len(published - dated)} published roles carry no date"


def test_the_e2e_artifact_is_a_file_this_module_could_have_written() -> None:
    """The e2e drives the badge and the Newest sort over a fixture, because the
    17-role dataset has no history and the real one has 6,505 dates and (today)
    no confirmed role at all — a check that passes by never running is the shape
    this repo has been bitten by. A hand-written fixture buys that only while it
    stays a file the real pipeline could produce.
    """
    art = json.loads(E2E_ARTIFACT.read_text())
    urls = {
        role["url"]
        for company in json.loads(E2E_DATA.read_text())["companies"]
        for role in company["roles"]
    }

    assert art["schema_version"] == SCHEMA_VERSION
    assert art["snapshot"] in art["dates"] or art["dates"], "an artifact dates something"
    # Every artifact `advance` writes states the definition it was folded under,
    # even when that is null (T16.1). A fixture without the key is a file this
    # module could not have written, which is the whole bar this test holds.
    assert "definition" in art, "no definition: the real module always states one"
    for day, buckets in art["dates"].items():
        assert sorted(buckets) == ["confirmed", "unconfirmed"], day
        for kind, listed in buckets.items():
            assert listed == sorted(listed), f"{day}/{kind} is unsorted"
            assert set(listed) <= urls, f"{day}/{kind} dates a role the fixture never published"
    seen = [url for b in art["dates"].values() for urls_ in b.values() for url in urls_]
    assert len(seen) == len(set(seen)), "a URL is dated twice; first seen is seen once"
