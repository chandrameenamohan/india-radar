"""T3.3 — Lever probe.

Payloads are shaped exactly like the live API's, captured from MindTickle's
board: a bare JSON array of postings, each with a `categories` object holding a
primary `location` string and an `allLocations` list. There is no envelope and
no count — the array is the whole response.
"""
import json

import pytest

from src.lever import API, locations, parse, probe
from src.outcomes import CHECKED, Outcome

#: What Lever answers for a slug that is not a board. Measured against ten wrong
#: slugs today; all ten got this, byte for byte.
NOT_FOUND = '{"ok":false,"error":"Document not found"}'


def board(*postings: tuple[str, ...]) -> str:
    """A board response, one posting per tuple of place names."""
    return json.dumps(
        [
            {
                "id": f"885113ea-{i}",
                "text": "Software Engineer",
                "categories": {
                    "commitment": "Full-Time",
                    "department": "Engineering",
                    "location": places[0],
                    "allLocations": list(places),
                },
                "workplaceType": "hybrid",
                "hostedUrl": f"https://jobs.lever.co/acme/885113ea-{i}",
            }
            for i, places in enumerate(postings)
        ]
    )


def answering(status: int, body: str):
    """Stub `get` with one (status, body), and record the URLs it was asked for."""
    calls: list[str] = []

    def fake_get(url, timeout=30):
        calls.append(url)
        return status, body

    return fake_get, calls


def test_empty_array_is_unverified_not_zero(monkeypatch):
    """The DoD check, and the reason this module is not a copy of Ashby's.

    Lever's empty array is the one answer we cannot read: an abandoned board, a
    renamed company and a firm that isn't hiring all produce it, and Lever has
    no name lookup to ask a second question of. `no-india-roles` would claim we
    checked — it counts as CHECKED and would let the site imply "not hiring".
    """
    fake_get, calls = answering(200, "[]")
    monkeypatch.setattr("src.lever.get", fake_get)

    assert probe("ramenvr") == Outcome.EMPTY_BOARD_UNVERIFIED
    assert Outcome.EMPTY_BOARD_UNVERIFIED not in CHECKED
    assert calls == [API.format(slug="ramenvr")]


def test_a_404_is_the_slug_not_the_board(monkeypatch):
    """Measured live: every wrong slug 404s with `Document not found`, so the
    trap above is narrower than FINDINGS §1 described — but a 404 is still a
    slug we misread, not a board we failed to reach, and it must not become the
    unverified-empty outcome either."""
    fake_get, _ = answering(404, NOT_FOUND)
    monkeypatch.setattr("src.lever.get", fake_get)

    assert probe("no-such-company") == Outcome.SLUG_UNRESOLVED


def test_a_populated_board_is_read(monkeypatch):
    """The ordinary case: a board with postings comes back as postings."""
    fake_get, _ = answering(200, board(("Bengaluru, Karnataka",), ("Remote (US)",)))
    monkeypatch.setattr("src.lever.get", fake_get)

    roles = probe("mindtickle")

    assert isinstance(roles, list) and len(roles) == 2


@pytest.mark.parametrize("status", [0, 429, 500, 502, 503])
def test_anything_else_is_probe_failed(monkeypatch, status):
    """A board we could not reach is not a board with no roles. Status 0 is
    curl's "the transfer never happened" — DNS, refused, timed out."""
    fake_get, _ = answering(status, "")
    monkeypatch.setattr("src.lever.get", fake_get)

    assert probe("acme") == Outcome.PROBE_FAILED


@pytest.mark.parametrize(
    "payload",
    [
        NOT_FOUND,  # the error object served with a 200 by some proxy
        '{"postings": []}',  # an envelope Lever does not use
        "<html>502 Bad Gateway</html>",  # an error page served as the body
        '[{"text": "Software Engi',  # truncated mid-transfer
    ],
)
def test_a_malformed_body_is_probe_failed(payload):
    """Lever ships no count, so a short board is undetectable and all `parse`
    can refuse is a body that isn't a whole JSON array. Note the first case: an
    error object is NOT an empty board, and must not borrow its outcome."""
    assert parse(payload) == Outcome.PROBE_FAILED


def test_all_locations_is_the_whole_answer():
    """One posting open in Bengaluru and Pune is one role in two cities.

    `allLocations` contains the primary already — 157 of 158 live postings, the
    exception being a null primary — so prepending `location` would double every
    city. That is invisible in the role count and visible in the row's cities.
    """
    roles = parse(board(("Bengaluru, Karnataka", "Pune, Maharashtra"), ("Warsaw, Poland",)))

    assert isinstance(roles, list)
    assert locations(roles[0]) == ["Bengaluru, Karnataka", "Pune, Maharashtra"]
    assert locations(roles[1]) == ["Warsaw, Poland"]


def test_a_posting_with_no_stated_place_is_not_an_error():
    """Measured on Kpler: `location: null` with `allLocations: []`. A role with
    nowhere stated is a role we can't place, never a crash on the way to the
    site — and never India by default."""
    assert locations({"categories": {"location": None, "allLocations": []}}) == []
    assert locations({"categories": {"location": "Pune, Maharashtra"}}) == ["Pune, Maharashtra"]
    assert locations({}) == []
