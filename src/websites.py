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

Two more sources arrived with T10.5, both off the board rather than off the
funding article. A company that hosts its own job board applies on its own
domain, so the last build's rows already state the address (`from_board`, no
fetch at all) — and where they do not, the ATS itself publishes whose board a
slug is, on the page a human opens rather than on the jobs endpoint this project
reads (`from_ats`, 65% of the 40 that had nothing).
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from src import greenhouse
from src.net import fetch, get
from src.record import Record
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
    so this is deliberately not the 48 that slug resolution runs at, for the same
    reason `slugs._GUESS_WORKERS` isn't.
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


# ---------------------------------------------------------------------- T10.5
# The third source, and it costs no fetch at all: the board we already publish.
#
# 45 of the 315 listed companies carried no address here, so their descriptions
# rested on a check (T10.3's audit) that could not be run for them. The article
# read above is exactly what failed for those 45. What had not been looked at is
# the apply URL: some companies host their own job board on their own domain, and
# then every posting's link states the address outright. That is how Alloy,
# Slice and Symphony were settled by a human (T10.3) — this derives it instead,
# because a fact a run can re-derive does not belong in `corrections.yaml`.
# Measured: 5 of the 45. `from_ats` below is what reaches the other 40.

#: Hosts that belong to somebody's tooling rather than to a company: the three
#: ATSes, the CDN one of them serves its board assets from, and the social and
#: code hosts every careers page in the world links.
#:
#: The three ATSes alone would do for the apply URLs — measured over all 315
#: listed companies, 257 boards apply on one of them and the other 58 apply on
#: exactly one host each, zero split. The rest of the list is for `from_ats`,
#: which reads a whole page of links rather than one, and it is the same list the
#: measurement in learning-tests/addresses_live.py ran under.
NOT_A_COMPANY = (
    "greenhouse.io", "ashbyhq.com", "lever.co", "ashbyprd.com",
    "linkedin.com", "twitter.com", "x.com", "facebook.com", "instagram.com",
    "youtube.com", "github.com", "glassdoor.com", "google.com", "gstatic.com",
    "w3.org", "schema.org", "crunchbase.com", "medium.com", "bit.ly",
)

#: The last build's rows, which is where the apply URLs already are. Read rather
#: than fetched: the corpus runs before the build, so this is the same
#: carry-the-last-good-answer shape `build.carry_salary` has, and it makes the
#: derivation free.
BOARDS = Path("data/companies.json")


def registrable(host: str) -> str:
    """The host's last two labels — the domain a company registers, rather than
    whichever subdomain its hiring flow happens to live on.

    Load-bearing, and measured: `careers.airbnb.com` is `airbnb.com`, and
    `wayve.firststage.co` is `firststage.co` — a company's name in the leftmost
    label of somebody ELSE's domain, which is the exact shape a naive host check
    accepts and publishes as an address.

    ponytail: two labels, no public-suffix list. Ceiling: a company under
    `example.co.uk` reduces to `co.uk`, fails the naming rule below and is
    refused — the safe direction, and no listed company is in that shape today.
    Upgrade path: the PSL, if one ever is.
    """
    return ".".join(host.split(".")[-2:])


def _theirs(name: str, url: str) -> str | None:
    """This URL's registrable domain, if it can be this company's address.

    The domain must not be somebody's tooling, and it must STATE the company:
    `slugs.states_company`'s containment rule, pointed at a registrable domain
    instead of at a board's own name.
    """
    if not url.startswith(("http://", "https://")):
        return None
    domain = registrable(_host(url))
    if any(tool in domain for tool in NOT_A_COMPANY) or not key(name):
        return None
    return domain if key(name) in key(domain) else None


def _address(name: str, urls: Iterable[str]) -> str | None:
    """The one company address these URLs agree on, or None having guessed
    nothing — the evidence rule every derivation below is held to.

    The survivors must collapse to one, which is `from_page`'s rule: two
    addresses is a coin flip, and a coin flip is a guess wearing a source's
    clothes.
    """
    found = {domain for url in urls if (domain := _theirs(name, url))}
    return f"https://{found.pop()}" if len(found) == 1 else None


def from_board(name: str, roles: Iterable[Mapping[str, Any]]) -> str | None:
    """The company's own address as its own job board applies on it, or None
    having guessed nothing.

    Two conditions, and both are conditions this project already keeps. The
    board must apply on ONE host — `from_page` refuses a page offering two, for
    the same reason. And that host's registrable domain must state the company's
    name, which is `slugs.states_company`'s containment rule pointed at a domain
    instead of at a board's name.

    The containment is the expensive half and it is worth being exact about the
    price. Measured over the 58 listed boards that apply off-ATS, six are refused
    for naming a domain SHORTER than the corpus name — `Cross River Bank` at
    `crossriver.com`, `Vectra Networks` at `vectra.ai`, `SparkCognition` at
    `avathon.com` (a 2024 rename no source here states). Every one of the six is
    really that company, and nothing in the strings says so: it is the same
    direction `states_company` refuses for the same reason, and losing six
    addresses beats publishing one company's site under another's name.
    """
    hosts = {
        _host(url)
        for role in roles
        if isinstance(url := role.get("url"), str) and url.startswith(("http://", "https://"))
    }
    # One host for the whole board, checked before the rule below rather than
    # after: a board applying half on Greenhouse and half on its own domain is a
    # board we have not understood, and dropping the ATS half would hide that.
    return _address(name, [f"https://{hosts.pop()}"]) if len(hosts) == 1 else None


def published(path: str | Path = BOARDS) -> list[dict[str, Any]]:
    """The rows the last build put on the site, or none if there aren't any.

    Never raises, `build.published`'s rule and for its reason: a missing or
    truncated file is an absence, and an absence must cost the corpus nothing.
    A first-ever run has no build to read, and derives no address from one.
    """
    try:
        found = json.loads(Path(path).read_text())["companies"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return []
    return [row for row in found if isinstance(row, dict)] if isinstance(found, list) else []


def fill_from_boards(companies: Iterable[Record], path: str | Path = BOARDS) -> int:
    """Give a website to every company that hasn't got one and whose own board
    applies on its own domain. Returns how many were filled.

    Only companies with no address: a source that stated one, or a human who
    corrected one, has answered a question this cannot re-open.
    """
    rows = {
        row["name"]: row.get("roles") or []
        for row in published(path)
        if isinstance(row.get("name"), str)
    }
    filled = 0
    for company in companies:
        if company["website"] or company["name"] not in rows:
            continue
        if address := from_board(company["name"], rows[company["name"]]):
            company["website"] = address
            filled += 1
    return filled


# ---------------------------------------------------------------------- T10.5
# The fourth source, and the one nobody expected to exist. The task assumed the
# apply URL was the end of it — "the other 40 need a source that does not exist
# yet" — and it is wrong: the ATSes publish, on the page a human opens rather
# than on the jobs endpoint this project reads, whose board a slug is.
#
# Measured over the 40 listed companies the apply URL does not reach
# (learning-tests/addresses_live.py, 2026-08-02): 26 of 40, 65%, against T10.5's
# kill criterion of ~25%. On a 20-company control whose addresses are already
# known, 12 answers and 12 agreements — zero disagreements, on any avenue.
#
# Deliberately NOT built beside it: the posting text, measured at 11 of 40 (28%),
# which also clears the criterion and adds THREE companies this does not already
# reach. That is a second class of fetch — the rich board, per company, in the
# corpus run that today fetches no board at all — for three addresses.

#: Ashby states it outright and the other two have to be read off a page. Ashby
#: server-renders its whole organisation record into the board's HTML, and
#: `publicWebsite` is a field in it; the posting API this project already calls
#: says nothing about the company at all.
ASHBY_BOARD = "https://jobs.ashbyhq.com/{slug}"
#: Lever's board page carries exactly one link off its own host, and it is the
#: company's home.
LEVER_BOARD = "https://jobs.lever.co/{slug}"
#: Greenhouse says it in two weaker places, so both are read and `_address` is
#: what refuses them when they disagree: the board object's "About us" blurb
#: (`greenhouse.BOARD`, often empty) and the hosted page's own navigation, which
#: is the company's site chrome wrapped around the list.
GREENHOUSE_BOARD = "https://job-boards.greenhouse.io/{slug}"

_HREF = re.compile(r'href="(https?://[^"\s]+)"')
_PUBLIC_WEBSITE = re.compile(r'"publicWebsite"\s*:\s*"(https?://[^"]+)"')


def stated_by_ats(ats: str, slug: str) -> list[str]:
    """Every URL the ATS's own page about this board offers, before any rule is
    applied to it. Empty for an ATS we cannot read, which is an absence."""
    if ats == "ashby":
        # A short body is the JS shell without the server-rendered state — 7KB
        # against 40KB, measured on the same slug within a minute of a full one.
        # So one retry, and then it is honestly absent.
        for _ in range(2):
            page = fetch(ASHBY_BOARD.format(slug=slug), timeout=30) or ""
            if stated := _PUBLIC_WEBSITE.search(page):
                return [stated.group(1)]
        return []
    if ats == "lever":
        return _HREF.findall(fetch(LEVER_BOARD.format(slug=slug), timeout=45) or "")
    if ats == "greenhouse":
        _, about = get(greenhouse.BOARD.format(slug=slug), timeout=20)
        hosted = fetch(GREENHOUSE_BOARD.format(slug=slug), timeout=45) or ""
        return _HREF.findall(about) + _HREF.findall(hosted)
    return []


def from_ats(name: str, ats: str, slug: str) -> str | None:
    """The company's address as its ATS states it, or None having guessed
    nothing.

    Held to `_address` like everything else, and the containment is what this
    avenue needs MOST rather than least. Ashby answers with one address and
    answers it confidently, so where our slug is wrong the address is confidently
    another company's: measured, `ashby/langfuse` is listed here under
    "ClickHouse" and Ashby names langfuse.com for it. Three of the 45 are refused
    that way — ClickHouse, which is a wrong listing this found, and Lambda Labs
    (`lambda.ai`) and Payward (`kraken.com`), which are the same company under a
    name no source here states. Losing two beats publishing the first.
    """
    return _address(name, stated_by_ats(ats, slug))


def fill_from_ats(
    companies: Iterable[Record], path: str | Path = BOARDS, workers: int = 8
) -> int:
    """Give a website to every company that hasn't got one and whose ATS states
    one for its board. Returns how many were filled.

    Bounded by the last build's rows, so it costs two fetches for each of the
    ~40 listed companies nothing else reached — not one per corpus row. A company
    whose board we never read is a company no ATS has anything to say about.

    ponytail: 8 workers, `fill`'s number and for the same reason — this is three
    hosts rather than 2,900, so it is bounded by politeness, not throughput.
    """
    rows: dict[str, tuple[str, str]] = {
        row["name"]: (row["ats"], row["slug"])
        for row in published(path)
        if isinstance(row.get("name"), str)
        and isinstance(row.get("ats"), str)
        and isinstance(row.get("slug"), str)
    }
    wanted = [c for c in companies if not c["website"] and c["name"] in rows]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        found = list(
            pool.map(lambda c: from_ats(c["name"], *rows[c["name"]]), wanted)
        )

    for company, address in zip(wanted, found, strict=True):
        if address:
            company["website"] = address
    return sum(1 for address in found if address)
