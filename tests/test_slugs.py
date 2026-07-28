"""T2.1 — careers-page slug discovery.

Two fixtures, both real. `board-links.txt` carries board URLs exactly as live
careers pages emit them, framed in their real markup; `careers-anthropic.html` is
an unedited capture of a JS-rendered careers page that links no board at all —
177KB of real noise, which is what a false-positive regex would trip over.
"""
from pathlib import Path

import pytest

from src.slugs import careers_urls, find_boards, resolve, resolve_all

FIXTURES = Path(__file__).parent / "fixtures"
BOARD_LINKS = (FIXTURES / "board-links.txt").read_text()
ANTHROPIC = (FIXTURES / "careers-anthropic.html").read_text()


def page(markup: str) -> str:
    """A careers page linking `markup`, on top of a real page's worth of noise.

    The noise is load-bearing twice over: resolve() ignores bodies too short to
    be a page (a parked domain's stub), and a link found in 177KB of real markup
    is a stronger claim than one found in a one-line string.
    """
    return ANTHROPIC + markup


def test_board_url_regexes_on_fixtures():
    """Both hosts, both Greenhouse URL shapes, JSON-escaped and attribute-framed
    links, and a slug that runs straight into a UUID."""
    assert find_boards(BOARD_LINKS) == [
        ("ashby", "ramp"),
        ("greenhouse", "examplecorp"),  # from the embed include's ?for=
        ("greenhouse", "figma"),
        ("greenhouse", "razorpaysoftwareprivatelimited"),
        ("greenhouse", "vercel"),
        ("lever", "voleon"),
    ]

    # The constructed hazards: "embed" is a URL path, not a company, and the
    # marketing site is not a board. A wrong slug is worse than no slug — it
    # probes someone else's board and reports the answer as this company's.
    slugs = [slug for _, slug in find_boards(BOARD_LINKS)]
    assert "embed" not in slugs
    assert "customers" not in slugs


def test_known_good_pages_resolve(monkeypatch):
    """The acceptance pair: Figma -> greenhouse/figma, Ramp -> ashby/ramp,
    end to end through resolve() rather than the regex alone."""
    pages = {
        "Figma": page('<a href="https://boards.greenhouse.io/figma/jobs/5988684004">Role</a>'),
        "Ramp": page('\\"jobUrl\\":\\"https://jobs.ashbyhq.com/ramp/09a9381c-677b-40a5\\"'),
    }
    monkeypatch.setattr(
        "src.slugs.fetch",
        lambda url, timeout=45: pages.get("Figma" if "figma" in url else "Ramp"),
    )

    assert resolve("Figma") == {"ats": "greenhouse", "slug": "figma", "method": "careers-page"}
    assert resolve("Ramp") == {"ats": "ashby", "slug": "ramp", "method": "careers-page"}


def test_real_js_rendered_page_finds_no_board():
    """Anthropic's careers page is genuinely on Greenhouse and genuinely links no
    board in its HTML. Finding anything here would be a false positive, and a
    false positive is a wrong company's roles under this company's name."""
    assert find_boards(ANTHROPIC) == []


@pytest.mark.parametrize(
    ("pages", "reason"),
    [
        ({}, "no-careers-page"),
        ({"careers": ANTHROPIC}, "no-board-link"),
        (
            {"careers": page("boards.greenhouse.io/one jobs.ashbyhq.com/two")},
            "ambiguous-board: ashby/two, greenhouse/one",
        ),
    ],
)
def test_unresolved_has_reason(monkeypatch, pages, reason):
    """Three different kinds of not-knowing, and they must not collapse into one.
    "we never reached a page" and "we read the page and it linked no board" send
    a company down different recovery paths — the second is T2.2's whole remit."""
    monkeypatch.setattr(
        "src.slugs.fetch",
        lambda url, timeout=45: next((p for k, p in pages.items() if k in url), None),
    )

    resolution = resolve_all(["Acme"])

    assert resolution.resolved == {}
    assert resolution.unresolved == {"Acme": reason}
    assert resolution.rate == 0.0


def test_every_company_lands_on_exactly_one_side(monkeypatch):
    """A company resolves or it is named with a reason. Never both, never
    neither — an unaccounted company is one T6.1 cannot report on."""
    monkeypatch.setattr(
        "src.slugs.fetch",
        lambda url, timeout=45: (
            page('<a href="https://jobs.lever.co/voleon">Jobs</a>') if "voleon" in url else None
        ),
    )

    resolution = resolve_all(["Voleon", "Nowhere Inc"])

    assert set(resolution.resolved) | set(resolution.unresolved) == {"Voleon", "Nowhere Inc"}
    assert not set(resolution.resolved) & set(resolution.unresolved)
    assert resolution.resolved["Voleon"]["method"] == "careers-page"
    assert resolution.rate == 0.5


def test_parked_domain_is_not_a_careers_page(monkeypatch):
    """Verbatim body of antareslabs.com/careers on 2026-07-28 — a squatter's
    redirect stub answering 200. Reporting "read their page, no board on it"
    here would claim we reached a company we never reached."""
    stub = (
        "<!DOCTYPE html><html><head><script>window.onload=function()"
        '{window.location.href="/lander"}</script></head></html>'
    )
    monkeypatch.setattr("src.slugs.fetch", lambda url, timeout=45: stub)

    assert resolve("Antares Labs") == "no-careers-page"


def test_careers_urls_from_name():
    """The domain is guessed from the name; punctuation and spacing in a company
    name are not part of its domain."""
    assert careers_urls("Antares Labs") == [
        "https://antareslabs.com/careers",
        "https://antareslabs.com/jobs",
    ]
