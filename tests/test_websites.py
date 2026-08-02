"""T1.6 — a website per company, or an honest absence.

The fixtures are every `<a>` on a real FinSMEs article and a real CB Insights
profile, verbatim and in order (`from_page` reads nothing else). So the traps are
in them: the publisher's own navigation, its social accounts, and — on the CB
Insights page — four third-party news outlets writing about the same company.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.corpus import merge
from src.finsmes import Record
from src.websites import (
    fill,
    fill_from_ats,
    fill_from_boards,
    from_ats,
    from_board,
    from_page,
    site,
)

FIXTURES = Path(__file__).parent / "fixtures"
ARTICLE = (FIXTURES / "article-finsmes.html").read_text()
PROFILE = (FIXTURES / "profile-cbinsights.html").read_text()


def _record(name: str, source_url: str, website: str | None = None) -> Record:
    return Record(
        name=name,
        amount=10_000_000,
        currency="USD",
        date="2026-07-29",
        round_letter="A",
        source_url=source_url,
        stage=None,
        website=website,
    )


def test_website_extracted_from_article_fixture():
    """FinSMEs links the company under its own name, CB Insights links it as the
    bare domain. Both shapes were measured over 33 live pages; nothing else was
    ever the company's site."""
    assert from_page(ARTICLE, "Weave", "finsmes.com") == "https://weaveos.com"
    assert from_page(PROFILE, "Anthropic", "cbinsights.com") == "https://anthropic.com"


@pytest.mark.parametrize(
    ("html", "name", "why"),
    [
        ("", "Weave", "an empty page states nothing"),
        (ARTICLE, "Procode", "the company this article covers is not linked in it"),
        (
            '<a href="https://weave.io">Weave</a><a href="https://weave.dev">Weave</a>',
            "Weave",
            "two sites under the same name is a coin flip, and a coin flip is a guess",
        ),
        (
            '<a href="https://www.finsmes.com/tag/weave">Weave</a>',
            "Weave",
            "the publisher's own tag page is not the company's website",
        ),
    ],
)
def test_website_absent_is_null_not_guessed(html, name, why):
    """The field this task adds exists so `slugs.py` can stop guessing domains.
    A page that doesn't state one plainly must therefore yield None — inventing
    an address here would be the same guess wearing a source's clothes."""
    assert from_page(html, name, "finsmes.com") is None, why


def test_fill_only_fetches_publishers_that_link_the_company(monkeypatch):
    """EDGAR states no URL of any kind, so its 989 filing indexes are not worth a
    fetch each; YC and Forbes state one in the payload, so theirs would be a
    second answer to a question already answered."""
    fetched = []

    def record(url, timeout=45):
        fetched.append(url)
        return ARTICLE

    monkeypatch.setattr("src.websites.fetch", record)
    companies = [
        _record("Weave", "https://www.finsmes.com/2026/07/weave-raises-13-5m.html"),
        _record("Legora", "https://www.sec.gov/Archives/edgar/data/1/1/1-index.htm"),
        _record("Stripe", "https://www.ycombinator.com/companies/stripe", "https://stripe.com"),
    ]

    assert fill(companies) == 1
    assert fetched == ["https://www.finsmes.com/2026/07/weave-raises-13-5m.html"]
    assert [c["website"] for c in companies] == [
        "https://weaveos.com",
        None,  # honestly absent: Form D gives a street address and a phone number
        "https://stripe.com",  # already stated, so not re-derived
    ]


def test_a_website_survives_its_record_losing_the_merge():
    """A website is a fact about the company, not about the round. The strongest
    round for a company is routinely the one from the source that states no
    address at all — EDGAR files a dollar figure and no URL — so the corpus must
    not lose the address it does have to a stronger record that lacks one."""
    stated = _record("Legora", "https://www.ycombinator.com/companies/legora", "https://legora.com")
    stated["round_letter"], stated["amount"] = None, None
    stated["stage"] = "growth"
    stronger = _record("Legora", "https://www.sec.gov/Archives/edgar/data/1/1/1-index.htm")

    for order in ([stated], [stronger]), ([stronger], [stated]):
        company, = merge(*order).companies
        assert company["qualified_by"] == "letter"  # the stronger record won
        assert company["website"] == "https://legora.com"  # and the address survived


@pytest.mark.parametrize(
    ("stated", "expected"),
    [
        ("http://icracked.com", "http://icracked.com"),  # scheme kept as stated
        ("https://weaveos.com/", "https://weaveos.com"),
        ("https://mystery.org/careers/eng?ref=yc", "https://mystery.org"),
    ],
)
def test_site_keeps_the_address_and_drops_the_page(stated, expected):
    """YC files plenty of `http://`, and curl follows the redirect. Rewriting it
    would be inventing a fact about somebody's TLS to save a hop."""
    assert site(stated) == expected


# ---------------------------------------------------------------------- T10.5
# The third source, and the free one: a company hosting its own job board applies
# on its own domain, so the rows the last build published already state the
# address. Every case below is a real one, measured over the 315 listed boards.


def _roles(*urls: str) -> list[dict[str, str]]:
    return [{"title": "Engineer", "url": url} for url in urls]


@pytest.mark.parametrize(
    ("name", "url", "expected", "why"),
    [
        ("Workato", "https://workato.com/company/careers/x", "https://workato.com",
         "the plain case: 73 postings, all applying on the company's own domain"),
        ("Awardco", "https://award.co/careers/x", "https://award.co",
         "the domain need not spell the name the way the corpus does"),
        ("Cato Networks", "https://catonetworks.com/careers/x", "https://catonetworks.com",
         "a two-word name inside a one-word domain is the same containment T2.2 uses"),
        ("Airbnb", "https://careers.airbnb.com/positions/x", "https://airbnb.com",
         "the careers subdomain is where they hire, not the address they have"),
        ("Wayve", "https://wayve.firststage.co/jobs/x", None,
         "the company's name in the left label of an ATS VENDOR's domain — the "
         "exact shape a host check accepts and publishes as an address"),
        ("Cross River Bank", "https://crossriver.com/careers/x", None,
         "measured cost: a domain SHORTER than the corpus name is the direction "
         "`states_company` refuses, and six of the 58 are refused by it"),
        ("Notion", "https://jobs.ashbyhq.com/notion/x", None,
         "the ATS's own host names nobody — 257 of the 315 boards apply here"),
        ("Braze", "https://boards.greenhouse.io/braze/jobs/1", None,
         "and the containment would ADMIT this one, which is why the ATS hosts "
         "are refused before the name is even looked at"),
    ],
)
def test_an_apply_url_is_an_address_only_when_it_names_the_company(name, url, expected, why):
    assert from_board(name, _roles(url)) == expected, why


def test_a_board_applying_on_two_hosts_states_nothing():
    """`from_page`'s rule, for its reason: a coin flip between two hosts is a
    guess wearing a board's clothes. Measured, no listed board does this — which
    is what makes the rule cheap rather than what makes it unnecessary."""
    assert from_board("Acme", _roles("https://acme.com/x", "https://acmecorp.com/y")) is None


def test_a_role_with_no_link_is_not_a_host():
    """A posting whose URL never arrived must not narrow the board to one host by
    disappearing — it has to leave the count alone."""
    assert from_board("Acme", [{"title": "Engineer"}, *_roles("https://acme.com/x")]) == (
        "https://acme.com"
    )
    assert from_board("Acme", []) is None


def test_only_a_company_with_no_address_is_given_one(tmp_path):
    """A source that stated an address, or a human who corrected one, has
    answered a question this must not re-open."""
    out = tmp_path / "companies.json"
    out.write_text(json.dumps({"companies": [
        {"name": "Workato", "roles": _roles("https://workato.com/careers/x")},
        {"name": "Stripe", "roles": _roles("https://stripe.com/jobs/x")},
        {"name": "Notion", "roles": _roles("https://jobs.ashbyhq.com/notion/x")},
    ]}))
    companies = [
        _record("Workato", "https://www.sec.gov/x"),
        _record("Stripe", "https://www.ycombinator.com/companies/stripe", "https://stripe.com"),
        _record("Notion", "https://www.sec.gov/y"),
        _record("Unlisted", "https://www.sec.gov/z"),
    ]

    assert fill_from_boards(companies, out) == 1
    assert [c["website"] for c in companies] == [
        "https://workato.com",
        "https://stripe.com",  # already stated, and not re-derived
        None,  # applies on Ashby's host, which says nothing about anybody
        None,  # no board was published for this one at all
    ]


@pytest.mark.parametrize(
    "content", ["", "{}", '{"companies": null}', "not json at all"],
)
def test_no_build_to_read_derives_no_address(tmp_path, content):
    """A first-ever run has no companies.json, and a truncated one is the same
    absence — `build.published`'s rule, and it must cost the corpus nothing."""
    out = tmp_path / "companies.json"
    out.write_text(content)
    companies = [_record("Workato", "https://www.sec.gov/x")]

    assert fill_from_boards(companies, out) == 0
    assert fill_from_boards(companies, tmp_path / "absent.json") == 0
    assert companies[0]["website"] is None


# The fourth source, and the one T10.5 assumed did not exist: the ATS's own page
# ABOUT a board, rather than the jobs endpoint the build reads. Measured over the
# 40 listed companies nothing else reached — 26, 65%, against a kill criterion of
# ~25% (learning-tests/addresses_live.py).

ASHBY_PAGE = (
    '<script>window.__appData = {"organization":{"name":"Notion",'
    '"publicWebsite":"https://www.notion.com/","hostedJobsPageSlug":"notion"}}</script>'
)
LEVER_PAGE = (
    '<a href="https://jobs.lever.co/oleria-security/0597f93f">SDR</a>'
    '<a href="https://www.lever.co/job-seeker-support/">Help</a>'
    '<a href="https://www.oleria.com/">Oleria</a>'
)


@pytest.mark.parametrize(
    ("ats", "name", "page", "expected", "why"),
    [
        ("ashby", "Notion", ASHBY_PAGE, "https://notion.com",
         "Ashby server-renders the organisation record, `publicWebsite` and all"),
        ("lever", "Oleria", LEVER_PAGE, "https://oleria.com",
         "Lever's board links its own host and the company's home, nothing else"),
        ("ashby", "ClickHouse", ASHBY_PAGE, None,
         "the address Ashby states for `ashby/langfuse`, which this project "
         "lists under ClickHouse — a wrong SLUG, confidently answered, and the "
         "one failure mode this avenue has"),
        ("greenhouse", "Acme", '<a href="https://acme.com/about">Acme</a>',
         "https://acme.com", "Greenhouse's hosted page wears the company's own chrome"),
        ("greenhouse", "Acme",
         '<a href="https://acme.com/x">a</a><a href="https://acmehq.com/y">b</a>',
         None, "two domains that both name it is a coin flip, so neither is taken"),
        ("workday", "Acme", "", None, "an ATS we cannot read states nothing"),
    ],
)
def test_the_ats_states_an_address_only_when_it_names_the_company(
    monkeypatch, ats, name, page, expected, why
):
    monkeypatch.setattr("src.websites.fetch", lambda url, timeout=45: page)
    monkeypatch.setattr("src.websites.get", lambda url, timeout=45: (200, ""))

    assert from_ats(name, ats, "slug") == expected, why


def test_an_ashby_shell_is_retried_once_and_then_honestly_absent(monkeypatch):
    """Ashby answers the same slug with the full server-rendered state or with a
    7KB JS shell, minutes apart. One retry, then the absence is real."""
    pages = ["<html>shell</html>", ASHBY_PAGE]
    monkeypatch.setattr("src.websites.fetch", lambda url, timeout=45: pages.pop(0))

    assert from_ats("Notion", "ashby", "notion") == "https://notion.com"
    assert not pages, "the second attempt is what found it"

    monkeypatch.setattr("src.websites.fetch", lambda url, timeout=45: "<html>shell</html>")
    assert from_ats("Notion", "ashby", "notion") is None


def test_the_ats_is_only_asked_about_companies_with_a_board_and_no_address(
    monkeypatch, tmp_path
):
    """Two fetches per company, so the set matters: a company whose board we
    never read is a company no ATS has anything to say about, and one that
    already has an address has had the question answered."""
    asked: list[str] = []
    monkeypatch.setattr(
        "src.websites.fetch",
        lambda url, timeout=45: asked.append(url) or ASHBY_PAGE,
    )
    out = tmp_path / "companies.json"
    out.write_text(json.dumps({"companies": [
        {"name": "Notion", "ats": "ashby", "slug": "notion", "roles": []},
        {"name": "Stripe", "ats": "ashby", "slug": "stripe", "roles": []},
    ]}))
    companies = [
        _record("Notion", "https://www.sec.gov/x"),
        _record("Stripe", "https://www.ycombinator.com/x", "https://stripe.com"),
        _record("Unlisted", "https://www.sec.gov/z"),
    ]

    assert fill_from_ats(companies, out) == 1
    assert asked == ["https://jobs.ashbyhq.com/notion"]
    assert [c["website"] for c in companies] == ["https://notion.com", "https://stripe.com", None]
