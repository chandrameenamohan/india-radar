"""T2.1 careers-page slug discovery, and T2.2 guessing what it missed.

Two fixtures, both real. `board-links.txt` carries board URLs exactly as live
careers pages emit them, framed in their real markup; `careers-anthropic.html` is
an unedited capture of a JS-rendered careers page that links no board at all —
177KB of real noise, which is what a false-positive regex would trip over.
"""
from pathlib import Path

import pytest

from src.outcomes import Outcome
from src.slugs import (
    OVERRIDES,
    Slug,
    careers_urls,
    find_boards,
    guess,
    load_overrides,
    parse_overrides,
    resolve,
    resolve_all,
    states_company,
    verify_override,
)

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


def only_figma_has_a_careers_page(monkeypatch):
    """Careers-page discovery resolving exactly one company, so that what
    guessing adds afterwards is visible next to what it started from."""
    monkeypatch.setattr(
        "src.slugs.fetch",
        lambda url, timeout=45: (
            page('<a href="https://boards.greenhouse.io/figma/jobs/1">Role</a>')
            if "figma" in url
            else None
        ),
    )


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
    ("company", "pages", "reason"),
    [
        ("Acme", {}, "no-website"),
        ({"name": "Acme", "website": "https://acme.example"}, {}, "no-careers-page"),
        ({"name": "Acme", "website": "https://acme.example"}, {"careers": ANTHROPIC},
         "no-board-link"),
        (
            "Acme",
            {"careers": page("boards.greenhouse.io/one jobs.ashbyhq.com/two")},
            "ambiguous-board: ashby/two, greenhouse/one",
        ),
    ],
)
def test_unresolved_has_reason(monkeypatch, boards, company, pages, reason):
    """Four different kinds of not-knowing, and they must not collapse into one.

    "we had no address for them at all", "we had one and never reached a page"
    and "we read the page and it linked no board" send a company down three
    different recovery paths — a better website source, a retry, and T2.2's
    guessing. T1.6 exists because the first two were one reason and the site
    could not say which of them was actually costing it companies.
    """
    monkeypatch.setattr(
        "src.slugs.fetch",
        lambda url, timeout=45: next((p for k, p in pages.items() if k in url), None),
    )

    resolution = resolve_all([company])

    assert resolution.resolved == {}
    assert resolution.unresolved == {"Acme": reason}
    assert resolution.rate == 0.0


def test_every_company_lands_on_exactly_one_side(monkeypatch, boards):
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

    assert resolve("Antares Labs", "https://antareslabs.com") == "no-careers-page"


def test_careers_urls_from_name():
    """The domain is guessed from the name; punctuation and spacing in a company
    name are not part of its domain."""
    assert careers_urls("Antares Labs") == [
        "https://antareslabs.com/careers",
        "https://antareslabs.com/jobs",
    ]


def test_a_stated_website_is_used_instead_of_the_guessed_domain():
    """T1.6's payoff: a company whose name doesn't map onto its domain was
    invisible to careers-page discovery, because the only address it had was one
    it made up. Mystery.org files under mystery.org, never mysteryorg.com."""
    assert careers_urls("Mystery.org", "https://mystery.org/") == [
        "https://mystery.org/careers",
        "https://mystery.org/jobs",
    ]


# --- T2.2: guessing, and the reason it must verify whose board answered -------

#: What Greenhouse actually answered for each of these slugs on 2026-07-28,
#: names verbatim from learning-tests/slug_guess_live.py — trailing space and
#: all. Everything below is measured; none of it is a plausible-looking example.
GREENHOUSE = {
    "anthropic": "Anthropic",
    "gleanwork": "Glean",  # bare `glean` 404s — this is what the suffix list is for
    "automatticcareers": "Automattic Careers",
    "tide": "Careers at Tide",
    "crossriverbank": "Cross River",
    "stokespacetechnologies": "Stoke Space ",
    "brave": "Brave",  # the browser
    "razorpaysoftwareprivatelimited": "Razorpay Software Private Limited",
}

#: Company -> the slug guessing must return, or None and the reason it must not.
GUESSES = {
    "Anthropic": "anthropic",
    "Glean": "gleanwork",
    "Automattic": "automatticcareers",
    "Tide": "tide",
    # A board answers, states a SHORTER name, and we refuse it. Both of these are
    # in fact the right company — and they are string-for-string the same shape
    # as Brave Care -> `brave`, which is the browser. Nothing in the response
    # tells them apart, so the conservative direction costs these two.
    "Cross River Bank": None,
    "Stoke Space Technologies": None,
    # Verifiable name, unguessable slug: no suffix builds a legal entity name.
    # This is the tail T2.3's override file exists for.
    "Razorpay": None,
    # `brave` is not reachable from "Brave Care" at all — the first-word variant
    # that reached it found three boards on 60 companies and all three were a
    # different company, which is why it is not in _GUESS_SUFFIXES.
    "Brave Care": None,
}


@pytest.fixture
def boards(monkeypatch):
    """Greenhouse answering for the measured slugs and 404ing everything else."""
    monkeypatch.setattr("src.slugs.board_name", lambda slug, **kw: GREENHOUSE.get(slug))


@pytest.mark.parametrize("company", GUESSES)
def test_a_guess_is_only_kept_if_the_board_says_whose_it_is(boards, company):
    """The whole safety of this method. A board that answers proves a board
    exists, never that it is this company's, and a wrong slug publishes somebody
    else's roles under this company's name — worse than the unresolved row we
    would otherwise have."""
    slug = GUESSES[company]
    expected = {"ats": "greenhouse", "slug": slug, "method": "guess"} if slug else None

    assert guess(company) == expected


@pytest.mark.parametrize(("board", "company", "same"), [
    ("Automattic Careers", "Automattic", True),  # the company saying more
    ("Careers at Tide", "Tide", True),
    ("Razorpay Software Private Limited", "Razorpay", True),
    ("Cross River", "Cross River Bank", False),  # the company saying less
    ("Brave", "Brave Care", False),
    (None, "Nowhere Inc", False),  # no board at all is not a match
])
def test_a_board_states_a_company_only_by_containing_its_whole_name(board, company, same):
    """The rule, isolated from the fetching: the board may extend the company's
    name, never shorten it."""
    assert states_company(board, company) is same


def test_only_runs_on_unresolved(monkeypatch, boards):
    """A company whose own careers page named its board is never guessed at: it
    already told us the answer, and a guess could only disagree with it."""
    guessed = []
    only_figma_has_a_careers_page(monkeypatch)
    def record(name):
        guessed.append(name)
        return None

    monkeypatch.setattr("src.slugs.guess", record)

    resolve_all(["Figma", "Glean"])

    assert guessed == ["Glean"]


def test_method_recorded(boards, monkeypatch):
    """Two methods resolved this corpus and the report has to be able to say
    which did what — a combined rate that rose is a different fact from a
    combined rate that rose because guessing accepted anything."""
    only_figma_has_a_careers_page(monkeypatch)

    resolution = resolve_all(["Figma", "Glean", "Brave Care"])

    assert resolution.resolved["Figma"]["method"] == "careers-page"
    assert resolution.resolved["Glean"] == {
        "ats": "greenhouse",
        "slug": "gleanwork",
        "method": "guess",
    }
    assert resolution.methods == {"careers-page": 1, "guess": 1}
    # Brave Care stayed out, and kept the reason careers-page discovery gave it —
    # here the corpus knows no address for it, so nothing was ever read.
    assert resolution.unresolved == {"Brave Care": "no-website"}


def test_guessing_strictly_raises_the_combined_rate(boards, monkeypatch):
    """The DoD's headline, over a corpus careers-page discovery partly resolves.
    Anthropic and Glean are both genuinely on Greenhouse and both fail that
    method here — Anthropic's board link lives a page deeper than /careers,
    Glean's listing is JS-rendered — and both come back through guessing."""
    only_figma_has_a_careers_page(monkeypatch)
    companies = ["Figma", *GUESSES]

    careers_page_alone = [c for c in companies if not isinstance(resolve(c), str)]
    combined = resolve_all(companies)

    assert careers_page_alone == ["Figma"]
    assert combined.rate > len(careers_page_alone) / len(companies)
    assert set(combined.resolved) == {"Figma", "Anthropic", "Glean", "Automattic", "Tide"}
    assert {"Anthropic", "Glean"} <= set(combined.resolved)


# --- T2.3: the override file, where a human overrules the evidence ------------


def test_override_precedence(boards, monkeypatch):
    """The DoD's headline. Figma's own careers page names greenhouse/figma and
    Glean is reachable by guessing — and an override beats both, because it is
    the only method that knows something the boards cannot say.

    Precedence is asserted as *silence*, not as a winning value: neither
    automatic method may even be consulted for an overridden company. Anything
    else spends two fetches per company on an answer it then throws away, and
    2,953 of those is an hour.
    """
    only_figma_has_a_careers_page(monkeypatch)
    guessed: list[str] = []
    monkeypatch.setattr("src.slugs.guess", lambda name: guessed.append(name) or guess(name))

    resolution = resolve_all(
        ["Figma", "Glean", "Brave Care"],
        overrides={
            "Figma": Slug(ats="greenhouse", slug="figma-holdings", method="override"),
            "Brave Care": Slug(ats="greenhouse", slug="bravecare", method="override"),
        },
    )

    assert resolution.resolved["Figma"] == {
        "ats": "greenhouse",
        "slug": "figma-holdings",  # NOT greenhouse/figma, which its careers page linked
        "method": "override",
    }
    # `brave` is the browser; only a human can say Brave Care is `bravecare`.
    assert resolution.resolved["Brave Care"]["slug"] == "bravecare"
    assert resolution.methods == {"override": 2, "guess": 1}
    assert guessed == ["Glean"]  # the overridden two were never guessed at


def test_dead_override_fails_loudly(monkeypatch):
    """A hand-written slug that has gone dead must stop the run. Every other
    unresolved company is counted and left off the site; this one claims a human
    already checked, so the same silence reads as "they aren't hiring"."""
    monkeypatch.setattr(
        "src.slugs.greenhouse_probe", lambda slug: Outcome.SLUG_UNRESOLVED
    )

    with pytest.raises(ValueError, match=r"Ghost Corp.*greenhouse/gone.*no such board"):
        verify_override("Ghost Corp", Slug(ats="greenhouse", slug="gone", method="override"))


def test_a_probe_that_merely_failed_is_not_the_humans_mistake(monkeypatch):
    """The other side of the same check, and the reason it can be trusted.
    Greenhouse being down is not an error in this file. Failing the run on it
    would make a green run depend on somebody else's uptime and teach everyone
    to reach for --no-verify."""
    monkeypatch.setattr("src.slugs.greenhouse_probe", lambda slug: Outcome.PROBE_FAILED)

    verify_override("Flaky Corp", Slug(ats="greenhouse", slug="flaky", method="override"))


def test_an_unverifiable_ats_is_refused(monkeypatch):
    """Only Greenhouse can be asked whether a board exists today. An Ashby or
    Lever override would be an unchecked human claim — and Lever's dead slug
    answers 200 with an empty array, which is precisely the silent zero."""
    with pytest.raises(ValueError, match=r"only greenhouse boards can be verified"):
        verify_override("Ramp", Slug(ats="ashby", slug="ramp", method="override"))


@pytest.mark.parametrize(
    "line",
    [
        "Acme: greenhouse",  # no slug
        "Acme greenhouse/acme",  # no colon
        "  nested:\n    ats: greenhouse",  # YAML this parser does not speak
        'Acme: "greenhouse/acme"',  # quoted value
    ],
)
def test_the_override_file_refuses_what_it_cannot_read(line):
    """A partial YAML parser's real danger is reading a line into something
    other than what was meant, so it rejects instead of interpreting. The line
    number is in the message because that is what makes it a 10-second fix."""
    with pytest.raises(ValueError, match=r"line \d+: expected '<company>: <ats>/<slug>'"):
        parse_overrides(line)


def test_comments_and_quoted_names_parse():
    """Comments are the entire reason this file is YAML and not JSON. A quoted
    key parses to the same company as an unquoted one — otherwise the override
    silently matches nobody, which is the failure this task exists to prevent.
    """
    assert parse_overrides(
        '# why this exists\n\n"A24 Films": greenhouse/a24  # board states "A24"\n'
    ) == {"A24 Films": {"ats": "greenhouse", "slug": "a24", "method": "override"}}


def test_the_shipped_override_file_is_readable_and_justified():
    """The committed file itself, held to the format and to its own house rule:
    every entry carries a comment saying why a human overruled the machine. An
    unexplained override is one nobody dares delete later."""
    text = OVERRIDES.read_text()
    overrides = parse_overrides(text)

    assert overrides, "the file ships four measured companies; an empty one is a regression"
    assert all(slug["method"] == "override" for slug in overrides.values())
    assert overrides["A24 Films"] == {"ats": "greenhouse", "slug": "a24", "method": "override"}

    lines = [line for line in text.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        if not line.lstrip().startswith("#"):
            assert lines[index - 1].lstrip().startswith("#"), f"unexplained override: {line!r}"


def test_load_overrides_verifies_every_entry(monkeypatch):
    """Loading is parse *and* check. A file read without verification is how a
    dead slug reaches slugs.json in the first place."""
    checked: list[str] = []
    monkeypatch.setattr("src.slugs.greenhouse_probe", lambda slug: checked.append(slug) or [])

    overrides = load_overrides()

    assert sorted(checked) == sorted(slug["slug"] for slug in overrides.values())
