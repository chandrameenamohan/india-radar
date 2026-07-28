"""FinSMEs funding corpus source — T1.1.

FinSMEs publishes one article per funding round, and the headline carries
everything the corpus needs: company name, amount and round. The listing page
supplies the date and the source URL, so a single category fetch yields complete
records without touching the article pages.

Headlines that don't match the known grammar are returned in `unparsed` rather
than dropped. A scraper's real failure mode is the source quietly changing shape
and the run reporting a confident zero; surfacing the misses makes that loud.
"""
from __future__ import annotations

import re
import subprocess
from html import unescape
from typing import NamedTuple, TypedDict

BASE = "https://www.finsmes.com"

#: Load-bearing: measured 403 with curl's default UA, 200 with this one.
_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)


class Record(TypedDict):
    """One funding round. `amount` and `round_letter` are absent when the
    headline doesn't state them — T1.5 decides what that disqualifies."""

    name: str
    amount: int | None
    currency: str | None
    date: str  # ISO, YYYY-MM-DD
    round_letter: str | None
    source_url: str


class ParseResult(NamedTuple):
    records: list[Record]
    unparsed: list[str]


# The listing repeats each article as an image link and a text link; requiring
# text-only anchor content ([^<]+) selects the headline and skips the image.
_ENTRY = re.compile(
    r'<a href="(?P<url>https?://[^"]+)"[^>]*rel="bookmark"[^>]*>(?P<title>[^<]+)</a>'
    r'.{0,2000}?<time[^>]*datetime="(?P<date>\d{4}-\d{2}-\d{2})',
    re.S,
)

# "Acme Raises $21M in Series A Funding" / "Acme Receives Investment From VANE".
# ponytail: five verbs, the two observed on a live page plus the common
# synonyms. Anything else lands in `unparsed`, which is the signal to add one.
_HEADLINE = re.compile(r"^(?P<name>.+?)\s+(?:Raises|Receives|Closes|Secures|Lands)\b")

_AMOUNT = re.compile(r"(?P<symbol>[$£€])(?P<value>\d+(?:\.\d+)?)(?P<scale>[KMB])\b", re.I)
_SERIES = re.compile(r"\bSeries\s+(?P<letter>[A-Z])\b")

_CURRENCY = {"$": "USD", "£": "GBP", "€": "EUR"}
_SCALE = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}


def parse(page: str) -> ParseResult:
    """Extract funding records from a FinSMEs category listing page."""
    records: list[Record] = []
    unparsed: list[str] = []

    for entry in _ENTRY.finditer(page):
        title = unescape(entry["title"]).strip()
        headline = _HEADLINE.match(title)
        if not headline:
            unparsed.append(title)
            continue

        amount = _AMOUNT.search(title)
        series = _SERIES.search(title)
        records.append(
            Record(
                name=headline["name"].strip(),
                amount=_to_units(amount) if amount else None,
                currency=_CURRENCY[amount["symbol"]] if amount else None,
                date=entry["date"],
                round_letter=series["letter"] if series else None,
                source_url=entry["url"],
            )
        )

    return ParseResult(records, unparsed)


def _to_units(amount: re.Match[str]) -> int:
    """$7.25M -> 7250000. Currency units, not USD — no rate is applied here."""
    return round(float(amount["value"]) * _SCALE[amount["scale"].upper()])


def fetch(url: str) -> str | None:
    """GET a page, or None if it isn't a clean 200. A blocked page is a gap in
    the corpus, never fabricated data.

    Uses curl, not urllib: Cloudflare fingerprints the TLS handshake, and
    Python's is tarpitted — the connection is accepted and then never answered,
    so even a socket timeout doesn't fire. curl's handshake gets through. See
    learning-tests/FINDINGS.md.
    """
    done = subprocess.run(
        ["curl", "--fail", "--silent", "--max-time", "45", "-A", _UA, url],
        capture_output=True,
    )
    if done.returncode != 0:
        return None
    return done.stdout.decode("utf-8", errors="replace")
