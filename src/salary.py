"""India CTC benchmark — T4.2 (SPEC feature 8).

AmbitionBox is the source: it publishes a per-company average India CTC in
lakhs, the number of self-reported salaries behind it, and — the field that
makes this publishable at all — **the date it last recomputed the figure**.
Measured across the 116 listed companies: 65 carry a figure, 46 are a clean 404
(nobody has reported a salary there), and 5 answer 200 with the figure null.
All three are absences, and none of them is an error.

**The observation date is not decoration.** The 65 figures were last updated
anywhere between 2025-10-14 and today, so "₹21.2L" without its date is a claim
about now made from a nine-month-old sample. SPEC feature 8 requires the date
beside the figure, and `build.salary_errors` refuses a figure that arrives
without one.

**A page that answers is not this company's page**, the same rule T2.2 measured
on job boards — so the page must state a name containing the company's, and
`slugs.states_company` is that rule, unchanged. A wrong slug 404s here (measured
on nonsense, and on real companies who simply aren't listed), so what remains is
a *different real company* sharing a normalised name. The residual is the one
`states_company` already carries everywhere else in this project, and the row
renders the source link so a reader can settle it in one click.

**The source rate-limits on cumulative volume, and it says 403 when it does.**
Two full sweeps of the listed set ran clean; the third came back 86-of-116
blocked and the fourth 116-of-116 — and a single call seconds later answered
normally. So it is a rolling request window, not a ban and not a concurrency
cap, and going slower does not buy anything: the worst run measured was the
one-worker one, because by then it was the third sweep inside a minute.

That the block is a 403 and a genuine absence is a 404 is what makes this
recoverable, and it is worth real coverage: a single pass found 65 of 116
figures, the same work with backoff found **82 of 115**.

Everything here degrades to None. An enrichment that can fail a build is not an
enrichment, and this one hangs off the spine rather than standing in it.
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterable, MutableMapping
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from time import sleep
from typing import Any, TypedDict

from src.net import get
from src.slugs import states_company

#: One call per company. A hyphenated name is the only candidate: over all 116
#: listed companies a concatenated variant (`ambientai`) won zero times that the
#: hyphenated one lost, so a second candidate would double the calls to find
#: nothing.
PAGE = "https://www.ambitionbox.com/salaries/{slug}-salaries"

#: The page is server-rendered Next.js: the figure sits in the hydration payload
#: as JSON, so this reads a documented shape rather than scraping formatted
#: markup that a redesign moves.
_NEXT_DATA = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)

_NOT_ALNUM = re.compile(r"[^a-z0-9]+")

#: A 403 is "you asked too often" and a 404 is "nobody has reported a salary
#: here" — the first is worth retrying and the second never is, and telling them
#: apart is the whole reason this module recovers anything. 4 workers rather
#: than 8 out of politeness rather than measurement: a rested burst at 8 is
#: clean too, and since the limit counts requests over a window, neither number
#: is what keeps the enrichment alive. Backoff is.
WORKERS = 4

#: Three tries then the benchmark is absent, and absent renders as nothing —
#: the reader is never told a figure doesn't exist, only shown one when it does.
ATTEMPTS = 3

#: Seconds, multiplied by the attempt. A rate limit answers an immediate retry
#: exactly as it answered the first call; waiting is the only thing that works.
BACKOFF = 5


class Salary(TypedDict):
    """What the site renders: the figure, how many salaries are behind it, when
    the source last recomputed it, and where to check it.

    `reports` ships because the sample sizes are genuinely uneven — measured
    min 1, median 91, max 9,502. An average over one self-reported salary is a
    real sourced figure and a poor benchmark, and the honest fix is to show the
    reader the sample rather than to invent a cutoff for it.
    """

    avg_lpa: float
    reports: int
    observed: str
    source_url: str


def slug(name: str) -> str:
    """A company name as AmbitionBox spells it in a URL."""
    return _NOT_ALNUM.sub("-", name.casefold()).strip("-")


def is_iso_date(value: Any) -> bool:
    """Whether this is exactly a `YYYY-MM-DD` string the site can render as-is.

    Round-tripped rather than pattern-matched, because the site prints this
    string verbatim: `2026-13-45` is impossible and `20260728` is a real date in
    a shape that would render as a number. `build.salary_errors` is the other
    caller — the parser refuses to produce an undated figure and the schema
    refuses to publish one, and they agree on what a date is by sharing this.
    """
    try:
        return date.fromisoformat(value).isoformat() == value
    except (TypeError, ValueError):
        return False


def parse(html: str, name: str, source_url: str) -> Salary | None:
    """The company's salary benchmark, or None having proven nothing.

    This is a trust boundary and it never raises: every shape that isn't the
    one measured — no hydration payload, another company's page, a null figure,
    a figure with no date — is an absence, and an absence renders as one.
    """
    found = _NEXT_DATA.search(html)
    if not found:
        return None
    try:
        page = json.loads(found.group(1))["props"]["pageProps"]
        if not states_company((page["companyHeaderData"] or {}).get("companyName"), name):
            return None
        data = (page["salaryData"] or {})["data"] or {}
        avg, reports, updated = (
            float(data["totalSalaryAverage"]),
            int(data["totalSalaryDataPoints"]),
            str(data["lastUpdated"])[:10],
        )
    except (json.JSONDecodeError, AttributeError, KeyError, TypeError, ValueError):
        return None
    if avg <= 0 or reports <= 0 or not is_iso_date(updated):
        return None
    return Salary(avg_lpa=avg, reports=reports, observed=updated, source_url=source_url)


def lookup(name: str, attempts: int = ATTEMPTS) -> Salary | None:
    """This company's India CTC benchmark, or None.

    A 404 returns immediately: 46 of 116 listed companies simply have no page,
    and retrying an absence only makes the build longer. A 403 is the rate limit
    and is worth waiting out — without that distinction a single burst would
    empty the whole enrichment, which is what a first sweep at 8 workers did
    (86 of 116 blocked, then 116 of 116).
    """
    url = PAGE.format(slug=slug(name))
    for attempt in range(1, attempts + 1):
        status, page = get(url, timeout=30)
        if status == 404:
            return None
        if status == 200:
            return parse(page, name, url)
        if attempt < attempts:
            sleep(BACKOFF * attempt)
    return None


def attach(rows: Iterable[MutableMapping[str, Any]], workers: int = WORKERS) -> None:
    """Fill in each row's `salary`, in place, for the rows that have one.

    Rows arrive from `build.build` with `salary: None` already set, so a dead
    AmbitionBox — or no network at all — leaves a build that is complete and
    honest rather than one that failed. That is SPEC's "any enrichment may fail,
    degrade, or arrive late without taking the site down", enforced by there
    being no path here that raises.
    """
    listed = list(rows)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for row, found in zip(listed, pool.map(lookup, (r["name"] for r in listed)), strict=True):
            if found:
                row["salary"] = found
