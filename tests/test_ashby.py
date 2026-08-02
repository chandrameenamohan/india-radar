"""T3.2 — Ashby probe.

Payloads are shaped exactly like the live API's, captured from Ramp's board:
a `jobs` array of flat role objects, each with a `location` string and a
`secondaryLocations` array of objects wrapping their own `location`. There is no
`meta.total` — Ashby states no count of its own.
"""
import json

import pytest

from src.ashby import (
    ATTEMPTS,
    BACKOFF,
    Identity,
    identity,
    locations,
    parse,
    probe,
    probe_all,
    text,
)
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


# --- T12.1: who a board page says it belongs to -------------------------------

#: The `organization` objects verbatim off the live board pages on 2026-08-02,
#: fields and all — including the two absences the guess turns on. Ashby renders
#: its boards client-side, so the server ships a spinner and this blob, and the
#: blob is the only place the company's own address appears.
ORGANIZATIONS = {
    "ramp": {
        "organizationId": "7a158cac-9866-4881-95a8-bc946d3dca79",
        "name": "Ramp",
        "publicWebsite": "https://ramp.com",
        "customJobsPageUrl": None,
        "hostedJobsPageSlug": "ramp",
    },
    # Boom Supersonic is boomsupersonic.com. THIS Boom is not, and its board is
    # titled "Boom Jobs" all the same — one of the 8 collisions in 32 that made
    # T12.1 check addresses at all.
    "boom": {
        "organizationId": "4e682054-1b62-4cc5-af99-9c8026b4c85d",
        "name": "Boom",
        "publicWebsite": "https://www.boompay.app/",
        "customJobsPageUrl": None,
        "hostedJobsPageSlug": "Boom",
    },
    # A real board that states its name and NO address: 12 of the 264 known-good
    # Ashby boards are like this, and `customJobsPageUrl` is deliberately not
    # read as a substitute — over that whole control it would have rescued one
    # company, and it is a careers page rather than a claim about who they are.
    "envoy": {
        "organizationId": "5805a2a7-7eab-4de6-ba82-2697338a41a0",
        "name": "Envoy",
        "publicWebsite": None,
        "customJobsPageUrl": "https://www.envoy.com/jobs",
        "hostedJobsPageSlug": "Envoy",
    },
}


def board_page(title: str, organization: dict | None = None) -> str:
    """A board page shaped as Ashby serves one: a spinner, then the state blob.

    `organization=None` is the 7,128-byte shell Ashby answers 200 with for a
    slug it has never heard of — and, measured, for two slugs whose boards are
    very much alive (`cursor`, 1.04MB of jobs). Its title is a bare "Jobs".
    """
    data: dict[str, object] = {"environment": "production", "maintenanceMode": False}
    if organization is not None:
        data["organization"] = organization
    return (
        f"<!DOCTYPE html><html><head><title>{title}</title>"
        f'<meta name="title" content="{title}" /></head><body>'
        '<div class="center"><div class="fade-in"><div class="spinner"></div></div></div>'
        '<script nonce="mAOCDJNGw4B84B5K9CiLJZ6RTDwvbJaKHKgWJOC">\n'
        f"      window.__appData = {json.dumps(data)};\n    </script></body></html>"
    )


def serving(pages: dict[str, str]):
    """Stub `get` with a board page per slug; anything else is the empty shell,
    which is what Ashby really answers for a slug it has never heard of."""
    def fake_get(url, timeout=240):
        return 200, pages.get(url.rsplit("/", 1)[1], board_page("Jobs"))
    return fake_get


def test_identity_states_the_name_and_the_address(monkeypatch):
    """Both halves, out of one fetch. The name is the `<title>` minus Ashby's
    own " Jobs" suffix; the address is what the organisation calls its site."""
    monkeypatch.setattr(
        "src.ashby.get", serving({"ramp": board_page("Ramp Jobs", ORGANIZATIONS["ramp"])})
    )

    assert identity("ramp") == Identity("Ramp", "https://ramp.com")


def test_a_bare_jobs_title_is_not_knowing(monkeypatch):
    """Ashby answers 200 for every slug ever typed, so the status line proves
    nothing and this page has to read as silence rather than as a board named
    "Jobs" — otherwise every company ever guessed at resolves to something."""
    monkeypatch.setattr("src.ashby.get", serving({}))

    assert identity("zzzznotarealslugxyz") == Identity(None, None)
    assert identity("cursor") == Identity(None, None), (
        "cursor's board is LIVE — 1.04MB of jobs off the posting API — and its "
        "page serves this same shell. Unnameable is unresolvable either way."
    )


def test_a_board_that_states_no_address_states_only_its_name(monkeypatch):
    """Envoy, verbatim. Half an identity is what it is, and the caller decides
    what that half is worth — for a guessed slug, nothing."""
    monkeypatch.setattr(
        "src.ashby.get", serving({"envoy": board_page("Envoy Jobs", ORGANIZATIONS["envoy"])})
    )

    assert identity("envoy") == Identity("Envoy", None)


@pytest.mark.parametrize("body", [
    "<html><head></head><body>no title, no blob</body></html>",
    "<html><head><title>Ramp Jobs</title></head><body>no blob</body></html>",
    '<html><head><title>Ramp Jobs</title></head><body><script>window.__appData = {"or'
    "</script></body></html>",  # a blob that stops mid-object
])
def test_a_page_we_cannot_read_claims_no_address(monkeypatch, body):
    """A trust boundary. A blob that stops mid-object must not become an
    address, and a page with no blob at all must not either."""
    monkeypatch.setattr("src.ashby.get", lambda url, timeout=240: (200, body))

    assert identity("whatever").website is None


def test_a_page_that_did_not_answer_claims_nothing(monkeypatch):
    """Ashby being down is not evidence about whose board this is."""
    monkeypatch.setattr("src.ashby.get", lambda url, timeout=240: (503, ""))

    assert identity("ramp") == Identity(None, None)
