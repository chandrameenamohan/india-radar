"""A website per corpus company — T1.6.

The pipeline listed zero companies for five iterations, and this is why: a corpus
record carried a name and no address, so slug discovery guessed `<name>.com` and
half its failures never reached a page at all. A company that states its own
website is a company we can at least look at.

Two sources state one outright — YC's directory and some Forbes rows — and those
cost nothing. For everyone else the funding article is the cheapest honest source,
because a publisher writing about a company links it. Measured live over 33 pages
(learning-tests/websites_live.py), that link is identifiable structurally in two
shapes and no others:

  the company's name is the link text   FinSMEs 11/12, TechCrunch 5/9
  the domain is its own link text       CB Insights 11/12 (`anthropic.com`)

Both are read, name first, and **a page offering two different hosts yields
None**. Zero of the 33 did — but the whole point of this field is that
`slugs.py` stops guessing, so a coin-flip between two domains would be the same
guess wearing a source's clothes. Absent is a fact; wrong is a wrong company.

EDGAR states no URL of any kind (measured in T1.3 — Form D gives a street address
and a phone number), so a Form D company legitimately ends here with `None`.
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor

from src.finsmes import Record
from src.net import fetch
from src.slugs import key

#: Publishers measured to link the company they write about. Deliberately a list
#: rather than "fetch every source_url": YC's and Forbes' pages are redundant
#: (both state the website in the payload) and EDGAR's 989 filing indexes carry no
#: URL at all, so fetching them would buy nothing and cost the longest run.
LINKS_THE_COMPANY = ("finsmes.com", "techcrunch.com", "cbinsights.com")

_ANCHOR = re.compile(r'<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>', re.S)
_TAGS = re.compile(r"<[^>]+>")


def site(url: str) -> str:
    """A stated URL reduced to the address of the company — scheme and host.

    The scheme is kept as stated rather than upgraded: YC files plenty of
    `http://` and curl follows the redirect, so rewriting it would be inventing a
    fact about someone's TLS to save a hop.
    """
    scheme, _, rest = url.partition("//")
    return f"{scheme}//{rest.split('/')[0]}"


def _host(url: str) -> str:
    return site(url).partition("//")[2].removeprefix("www.").casefold()


def from_page(html: str, name: str, publisher: str) -> str | None:
    """The company's own site as this page states it, or None having guessed
    nothing. `publisher` is the host doing the writing, whose own links are not
    evidence about anybody."""
    by_name: set[str] = set()
    by_self: set[str] = set()
    for match in _ANCHOR.finditer(html):
        url, text = match.group(1), _TAGS.sub("", match.group(2)).strip()
        if publisher in _host(url) or not key(text):
            continue
        if key(text) == key(name):
            by_name.add(site(url))
        elif key(text) == key(_host(url)):
            by_self.add(site(url))

    found = by_name or by_self
    return found.pop() if len(found) == 1 else None


def read(company: Record) -> str | None:
    """Fetch the page this company's record came from and read its website off
    it. None when the page is unreachable or names no single site."""
    page = fetch(company["source_url"], timeout=45)
    return from_page(page, company["name"], _host(company["source_url"])) if page else None


def fill(companies: Iterable[Record], workers: int = 8) -> int:
    """Give a website to every company that hasn't got one and whose source is a
    publisher that links what it covers. Returns how many were filled.

    ponytail: 8 workers. Most of these are CB Insights profile pages — one host,
    so this is deliberately not the 16 that slug resolution runs at.
    """
    wanted = [
        company
        for company in companies
        if not company["website"]
        and any(host in _host(company["source_url"]) for host in LINKS_THE_COMPANY)
    ]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        found = list(pool.map(read, wanted))

    for company, website in zip(wanted, found, strict=True):
        if website:
            company["website"] = website
    return sum(1 for website in found if website)
