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
from html import unescape
from typing import NamedTuple, TypedDict

BASE = "https://www.finsmes.com"


class Record(TypedDict):
    """What one corpus source found out about one company — the shared contract
    every E1 source emits, defined here with the first of them.

    Everything but the name and the source URL is optional, because the sources
    genuinely differ in what they state: a FinSMEs headline gives an amount and a
    date but never a stage, YC's directory gives a stage but never an amount or a
    round date. An absent field is absent, never guessed — T1.5 decides what each
    absence disqualifies."""

    name: str
    amount: int | None
    currency: str | None
    date: str | None  # ISO, YYYY-MM-DD; None when the source states no round date
    round_letter: str | None
    source_url: str
    stage: str | None  # a source's own funding-stage label, e.g. YC's "growth"
    website: str | None  # the company's own address; None until T1.6 finds one


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

# Public because a headline is a headline: TechCrunch (T1.4) writes money and
# round letters exactly the way a funding wire does, so it reads them with these
# rather than with a second copy that could drift out of step.
AMOUNT = re.compile(r"(?P<symbol>[$£€])(?P<value>\d+(?:\.\d+)?)(?P<scale>[KMB])\b", re.I)
SERIES = re.compile(r"\bSeries\s+(?P<letter>[A-Z])\b")

CURRENCY = {"$": "USD", "£": "GBP", "€": "EUR"}
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

        amount = AMOUNT.search(title)
        series = SERIES.search(title)
        records.append(
            Record(
                name=headline["name"].strip(),
                amount=to_units(amount) if amount else None,
                currency=CURRENCY[amount["symbol"]] if amount else None,
                date=entry["date"],
                round_letter=series["letter"] if series else None,
                source_url=entry["url"],
                stage=None,  # a headline announces a round, never a stage
                website=None,  # stated in the article, not the listing — websites.fill
            )
        )

    return ParseResult(records, unparsed)


def to_units(amount: re.Match[str]) -> int:
    """$7.25M -> 7250000. Currency units, not USD — no rate is applied here."""
    return round(float(amount["value"]) * _SCALE[amount["scale"].upper()])
