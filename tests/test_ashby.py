"""T3.2 — Ashby probe.

Payloads are shaped exactly like the live API's, captured from Ramp's board:
a `jobs` array of flat role objects, each with a `location` string and a
`secondaryLocations` array of objects wrapping their own `location`. There is no
`meta.total` — Ashby states no count of its own.
"""
import json

import pytest

from src.ashby import ATTEMPTS, BACKOFF, locations, parse, probe, probe_all, text
from src.outcomes import Outcome


def board(*roles: tuple[str, ...]) -> str:
    """A board response, one role per tuple: primary location, then secondaries."""
    return json.dumps(
        {
            "apiVersion": "1",
            "jobs": [
                {
                    "id": f"34413f8d-{i}",
                    "title": "Software Engineer",
                    "location": primary,
                    "secondaryLocations": [{"location": place} for place in rest],
                    "jobUrl": f"https://jobs.ashbyhq.com/acme/{i}",
                }
                for i, (primary, *rest) in enumerate(roles)
            ],
        }
    )


@pytest.fixture(autouse=True)
def slept(monkeypatch):
    """Backoff is real seconds in production and dead weight in a unit test, so
    it is recorded rather than served. Returns the list of delays asked for."""
    delays: list[float] = []
    monkeypatch.setattr("src.ashby.sleep", delays.append)
    return delays


def answering(*responses: tuple[int, str]):
    """Stub `get` with one (status, body) per call, and record the URLs."""
    calls: list[str] = []
    replies = iter(responses)

    def fake_get(url, timeout=240):
        calls.append(url)
        return next(replies)

    return fake_get, calls


def test_secondary_locations_parsed():
    """The DoD check. A role open in Bengaluru and Mumbai is ONE role in two
    cities; reading only `location` undercounts it, and counting the strings
    would over-count it as two jobs (FINDINGS §2)."""
    roles = parse(board(("Bengaluru, India", "Mumbai, India"), ("Remote (US)",)))

    assert isinstance(roles, list)
    assert locations(roles[0]) == ["Bengaluru, India", "Mumbai, India"]
    assert locations(roles[1]) == ["Remote (US)"]

    # A board that omits the field entirely, and one that puts a bare string
    # where the live API puts an object: neither may crash the build.
    assert locations({"location": "Pune, India"}) == ["Pune, India"]
    assert locations({"location": "Pune, India", "secondaryLocations": ["Chennai, India"]}) == [
        "Pune, India",
        "Chennai, India",
    ]
    assert locations({}) == []


def test_retry_exhaustion_maps_to_probe_failed(monkeypatch, slept):
    """The DoD check. Ashby throttles repeat callers (FINDINGS §1: 3 of 12
    concurrent requests failed), so a transient failure is retried — and a
    company that runs out of tries is one we could not read. Never an empty
    role list, which reads on the site as "checked, not hiring in India"."""
    fake_get, calls = answering(*[(503, "")] * ATTEMPTS)
    monkeypatch.setattr("src.ashby.get", fake_get)

    assert probe("acme") == Outcome.PROBE_FAILED
    assert len(calls) == ATTEMPTS

    # Backoff, not just retry: a throttle answers three rapid retries exactly as
    # it answered the first call. The waits grow, and the last try isn't
    # followed by one — that would be a wait for nothing.
    assert slept == [BACKOFF, BACKOFF * 2]


def test_a_transient_failure_is_retried_not_recorded(monkeypatch):
    """The other half of the same rule: two flaky answers followed by a good one
    is a board we read. A probe that gave up on the first 503 would lose a
    company to a hiccup and count it as if we'd checked."""
    fake_get, calls = answering((0, ""), (429, ""), (200, board(("Pune, India",))))
    monkeypatch.setattr("src.ashby.get", fake_get)

    roles = probe("acme")

    assert isinstance(roles, list) and len(roles) == 1
    assert len(calls) == 3
    assert calls[0] == "https://api.ashbyhq.com/posting-api/job-board/acme"


def test_a_404_is_the_slug_not_the_board(monkeypatch):
    """Measured live: an unregistered slug 404s with the plain text `Not Found`.
    That is definitive, so it neither retries nor becomes a failure to read —
    T2.1 gave us a slug that is not a board."""
    fake_get, calls = answering((404, "Not Found"))
    monkeypatch.setattr("src.ashby.get", fake_get)

    assert probe("no-such-company") == Outcome.SLUG_UNRESOLVED
    assert len(calls) == 1, "a 404 is not transient; retrying it only slows the run"


def test_an_empty_board_is_believed():
    """Unlike Lever (T3.3), a wrong Ashby slug 404s — so nothing can masquerade
    here as an honest zero, and an empty array is a company with no open roles."""
    assert parse(board()) == []


@pytest.mark.parametrize(
    "payload",
    [
        '{"apiVersion": "1"}',  # no jobs key at all
        '{"jobs": {"1": {}}}',  # not the array we expect
        "<html>502 Bad Gateway</html>",  # an error page served as the body
        '{"jobs": [{"title": "Engi',  # truncated mid-transfer
    ],
)
def test_a_malformed_body_is_probe_failed(payload):
    """Ashby ships no `meta.total`, so a short board is undetectable — all we can
    refuse is a body that isn't whole. Hence retrying anything that isn't clean
    JSON rather than accepting what arrived."""
    assert parse(payload) == Outcome.PROBE_FAILED


def test_a_malformed_200_is_retried(monkeypatch):
    """A truncated body is transient in exactly the way a 503 is, and the status
    line can't tell them apart. Retrying it is what keeps a half-received board
    from costing a company."""
    fake_get, calls = answering((200, '{"jobs": [{"tit'), (200, board(("Remote - India",))))
    monkeypatch.setattr("src.ashby.get", fake_get)

    assert isinstance(probe("acme"), list)
    assert len(calls) == 2


def test_probe_all_resolves_every_slug(monkeypatch):
    """The concurrency contract: whatever each board answers, every slug comes
    back holding either roles or an outcome. A slug that fell out of the map
    would be a company silently absent from the build report."""
    answers = {
        "good": (200, board(("Hyderabad, India",))),
        "gone": (404, "Not Found"),
        "flaky": (503, ""),
    }
    monkeypatch.setattr("src.ashby.get", lambda url, timeout=240: answers[url.rsplit("/", 1)[1]])

    results = probe_all(["good", "gone", "flaky", "good"], workers=4)

    assert set(results) == {"good", "gone", "flaky"}, "a duplicate slug is fetched once"
    assert isinstance(results["good"], list) and len(results["good"]) == 1
    assert results["gone"] == Outcome.SLUG_UNRESOLVED
    assert results["flaky"] == Outcome.PROBE_FAILED


def test_text_is_the_prose_ashby_was_already_sending():
    """T8.1: `descriptionPlain` and `descriptionHtml` ship unconditionally, with
    no way to decline them — so this module has been paying for descriptions
    since T3.2 and throwing them away. There is no second call to make."""
    assert text({"descriptionPlain": "We sponsor visas.\n\nApply here."}) == (
        "We sponsor visas. Apply here."
    )
    # The HTML is the fallback, for a posting that ships only that shape. The
    # `&nbsp;` becomes an ordinary space rather than a U+00A0 the phrase list
    # would then fail to match across.
    assert text({"descriptionHtml": "<p>We sponsor&nbsp;visas.</p>"}) == "We sponsor visas."
    assert text({"descriptionPlain": "   ", "descriptionHtml": "<p>Real text.</p>"}) == "Real text."
    # No description at all is silence, not a crash — and silence is `unknown`.
    assert text({"title": "Staff Engineer"}) == ""
