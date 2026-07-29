"""Forbes company lists — T1.4 (SPEC feature 1).

The editorial lists (AI 50, Cloud 100, Fintech 50, Next Billion-Dollar Startups)
are rendered from a JSON API the page itself calls, so a list is one request and
a structured record rather than a scrape of a Next.js payload.

**Forbes states a cumulative funding total, never a round.** `funding: 830` is
$830M raised across Abridge's whole life; there is no letter, no round size and
no round date anywhere in the payload. Putting that number in `amount` would
report a round nobody raised and hand SPEC feature 2's $5M proxy a figure it was
not written for. So a Forbes record carries `stage` instead, exactly as a YC one
does: list membership plus a disclosed total is the source saying *this company
is venture-funded at scale*, which is what YC's `Growth` label says and no more.

The zeroes are the reason that is a judgement and not a formality. Forbes reports
`funding: 0` for Midjourney, Surge AI, Hyperliquid and Increase, and no funding
field at all for Zoho — the bootstrapped companies, correctly. A total Forbes
does not state is not evidence of a Series A, so those records carry no stage and
`src/corpus.py` excludes and counts them like any other unqualifiable row.
"""
from __future__ import annotations

import json
from datetime import date
from typing import Any

from src.finsmes import Record
from src.net import fetch
from src.websites import site

API = "https://www.forbes.com/forbesapi/org/{name}/{year}/position/true.json?limit=200"

#: The four lists that are software companies rather than people or public
#: corporations — Forbes also publishes the Midas List and the Global 2000, and
#: neither is a corpus of privately funded startups.
LISTS = ("ai50", "cloud100", "fintech50", "next-billion-dollar-startups")


def download(today: date | None = None) -> list[str]:
    """The newest published edition of each list.

    An unpublished year answers 200 with an empty list rather than 404, so the
    payload has to be opened to know it exists — measured 2026-07-28, the 2026
    Cloud 100 was still empty while the other three had landed. One year of
    fallback is enough: these are annual lists, so a list two years stale means
    Forbes retired it, and a retired list should leave the corpus.
    """
    year = (today or date.today()).year
    payloads = []
    for name in LISTS:
        for candidate in (year, year - 1):
            payload = fetch(API.format(name=name, year=candidate), timeout=60)
            if payload and _rows(payload):
                payloads.append(payload)
                break
    return payloads


def parse(payload: str) -> list[Record]:
    """Every company on one list, at whatever fundedness Forbes states.

    Deliberately unfiltered on amount: which evidence qualifies is
    `corpus._qualified_by`'s call, so the bootstrapped entries stay in and are
    excluded *and counted* rather than never appearing.
    """
    return [
        Record(
            name=row["organizationName"].strip(),
            amount=None,  # the payload's `funding` is a lifetime total, not a round
            currency=None,
            date=None,  # a list is published in a month; a round happened on a day
            round_letter=None,
            source_url=f"https://www.forbes.com/companies/{row['uri']}/",
            stage="growth" if row.get("funding") else None,
            # Stated on 79 of 220 rows and absent on the rest — a Forbes list
            # entry is editorial, so the field is optional in a way YC's isn't.
            website=site(row["webSite"]) if row.get("webSite") else None,
        )
        for row in _rows(payload)
    ]


def _rows(payload: str) -> list[dict[str, Any]]:
    """The list's companies. A missing `organizationName` or `uri` raises where
    it is read: both are structural, and a list that stopped supplying them has
    changed shape in a way that must fail loudly rather than shorten the corpus."""
    return list(json.loads(payload)["organizationList"]["organizationsLists"])
