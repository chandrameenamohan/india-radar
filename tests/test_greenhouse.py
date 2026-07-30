"""T3.1 — Greenhouse probe.

Payloads are shaped exactly like the live API's (FINDINGS §1): a `jobs` array of
role objects and a sibling `meta.total`.
"""
import json

import pytest

from src.greenhouse import describe, parse, probe, text
from src.outcomes import Outcome


def board(*locations: str, total: int | None = None) -> str:
    """A board response carrying one role per location."""
    jobs = [
        {
            "id": 4000 + i,
            "title": "Software Engineer",
            "location": {"name": location},
            "absolute_url": f"https://job-boards.greenhouse.io/acme/jobs/{4000 + i}",
        }
        for i, location in enumerate(locations)
    ]
    return json.dumps({"jobs": jobs, "meta": {"total": len(jobs) if total is None else total}})


def test_meta_total_agreement():
    """meta.total is the board's own count of what it should have sent. When it
    agrees, we have the whole board in one call and no pagination to walk."""
    roles = parse(board("Bengaluru, India", "Warsaw, Poland"))

    assert isinstance(roles, list)
    assert len(roles) == 2
    assert [r["location"]["name"] for r in roles] == ["Bengaluru, India", "Warsaw, Poland"]

    # An empty board that says it is empty is a real answer, not a failure:
    # unlike Lever, a wrong Greenhouse slug 404s (see test_404_maps_to_outcome),
    # so nothing else can masquerade as an honest zero here.
    assert parse(board()) == []


@pytest.mark.parametrize(
    "payload",
    [
        board("Pune, India", total=5),  # truncated: 1 role arrived, 5 promised
        board("Pune, India", total=0),  # nonsense the other way
        '{"jobs": [], "meta": {}}',  # no count to check against
        '{"jobs": {"1": {}}, "meta": {"total": 1}}',  # not the array we expect
        "<html>502 Bad Gateway</html>",  # an error page served as the body
    ],
)
def test_short_or_malformed_response_is_probe_failed(payload):
    """A response we can't fully account for is a board we FAILED TO READ. The
    tempting bug is returning the roles that did arrive — a company then ships
    with a partial board, and a missing India role reads as "not hiring"."""
    assert parse(payload) == Outcome.PROBE_FAILED


@pytest.mark.parametrize(
    ("status", "outcome"),
    [
        (404, Outcome.SLUG_UNRESOLVED),  # no such board: T2.1 gave us a wrong slug
        (500, Outcome.PROBE_FAILED),
        (429, Outcome.PROBE_FAILED),
        (0, Outcome.PROBE_FAILED),  # never answered at all
    ],
)
def test_404_maps_to_outcome(monkeypatch, status, outcome):
    """A 404 is a slug problem and a 502 is a reachability problem — they route a
    company to different fixes. Neither is an empty success: an empty role list
    renders as "checked, no target-country roles", a claim we haven't earned."""
    monkeypatch.setattr("src.greenhouse.get", lambda url, timeout=30: (status, ""))

    assert probe("acme") == outcome


def test_probe_returns_roles_on_a_clean_board(monkeypatch):
    """The happy path end to end, through the URL the pipeline actually calls."""
    called = []

    def fake_get(url, timeout=30):
        called.append(url)
        return 200, board("Remote - India")

    monkeypatch.setattr("src.greenhouse.get", fake_get)

    roles = probe("figma")

    assert isinstance(roles, list) and len(roles) == 1
    assert roles[0]["absolute_url"].startswith("https://job-boards.greenhouse.io/")
    assert called == ["https://boards-api.greenhouse.io/v1/boards/figma/jobs?content=false"]


def test_describe_asks_the_same_endpoint_with_the_prose_in_it(monkeypatch):
    """T8.4's second pass. It is the SAME call with one parameter flipped — no
    per-role fetch, which is what makes reading 4,311 descriptions affordable
    (T8.1: 13.7x-35.3x the bytes, under 2x the latency)."""
    called = []

    def fake_get(url, timeout=60):
        called.append(url)
        return 200, board("Bengaluru, India")

    monkeypatch.setattr("src.greenhouse.get", fake_get)

    assert isinstance(describe("figma"), list)
    assert called == ["https://boards-api.greenhouse.io/v1/boards/figma/jobs?content=true"]


def test_describe_keeps_the_status_rules_probe_keeps(monkeypatch):
    """A board that 404s on the second pass is the same slug problem it would be
    on the first. `build.described` treats every outcome here as "no prose", but
    the module must still say which one it was rather than inventing an empty
    board."""
    monkeypatch.setattr("src.greenhouse.get", lambda url, timeout=60: (404, ""))
    assert describe("acme") == Outcome.SLUG_UNRESOLVED
    monkeypatch.setattr("src.greenhouse.get", lambda url, timeout=60: (503, ""))
    assert describe("acme") == Outcome.PROBE_FAILED


def test_text_reads_the_doubly_escaped_description():
    """Greenhouse escapes its HTML twice, so one `html.unescape` leaves `&lt;p&gt;`
    sitting in the text as literal characters — a phrase can hide inside that.
    Measured on live boards; the fixture below is the shape they arrive in."""
    role = {"content": "&amp;lt;p&amp;gt;We do sponsor visas &amp;amp; relocate.&amp;lt;/p&amp;gt;"}

    assert text(role) == "We do sponsor visas & relocate."
    # The cheap pass carries no `content` at all, and that is an honest silence
    # rather than a missing field: `openness.classify("")` is `unknown`.
    assert text({"title": "Staff Engineer"}) == ""
