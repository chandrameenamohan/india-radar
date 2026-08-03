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


def report(*listed: str) -> dict[str, Any]:
    """A build-report.json: the companies whose board this build actually read."""
    return {"listed": sorted(listed)}


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
    for day, buckets in art["dates"].items():
        assert sorted(buckets) == ["confirmed", "unconfirmed"], day
        for kind, listed in buckets.items():
            assert listed == sorted(listed), f"{day}/{kind} is unsorted"
            assert set(listed) <= urls, f"{day}/{kind} dates a role the fixture never published"
    seen = [url for b in art["dates"].values() for urls_ in b.values() for url in urls_]
    assert len(seen) == len(set(seen)), "a URL is dated twice; first seen is seen once"
