"""T1.6 — a website per company, or an honest absence.

The fixtures are every `<a>` on a real FinSMEs article and a real CB Insights
profile, verbatim and in order (`from_page` reads nothing else). So the traps are
in them: the publisher's own navigation, its social accounts, and — on the CB
Insights page — four third-party news outlets writing about the same company.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.corpus import merge
from src.finsmes import Record
from src.websites import fill, from_page, site

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
