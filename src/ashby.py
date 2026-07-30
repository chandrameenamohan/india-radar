"""Ashby board probe — T3.2 (SPEC feature 4).

Ashby is the second-largest board in this corpus: 264 slugs against Greenhouse's
429, all of them already verified by T2.1/T2.2 and all of them `probe-failed`
until this module existed.

Three things differ from Greenhouse, and each changes the code:

**A wrong slug 404s.** Measured today against a deliberately unregisterable
slug: `404 Not Found`, as plain text rather than JSON. So Ashby is not Lever's
trap — an empty `jobs` array from a 200 is a company with no open roles, not a
slug we misread, and it can be believed.

**There is no `meta.total`.** The response is `{"jobs": [...], "apiVersion": …}`
and nothing else, so Greenhouse's agreement check has no counterpart here: a
truncated body is undetectable. What we can do is refuse anything that isn't
whole JSON, and retry rather than accept a short answer as an answer.

**A role can be in several places at once.** `secondaryLocations` sits beside
the flat `location` string (158 of them across Ramp's 120 roles), and reading
only the primary undercounts multi-location postings — FINDINGS §2. That makes
one role a *list* of locations here, where Greenhouse gives exactly one, which
is why `locations` is per-provider and India roles are counted by role rather
than by location string.

**On latency.** FINDINGS §1 measured a fixed ~151s per call, growing across
runs, with 3 of 12 concurrent requests failing — and sized the whole refresh
budget on it. Re-measured at the start of this task: **~2s, and 12/12 concurrent
succeeded in 2s wall.** That figure is a year of nobody's engineering, not a
mistake in the original measurement, and it may come back — it read as
progressive throttling of a repeat caller. So the retries and the backoff stay:
they cost nothing at 2s and they are the difference between a slow night and a
lost night if the throttle returns.
"""
from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from concurrent.futures import ThreadPoolExecutor
from time import sleep
from typing import Any

from src.net import get
from src.openness import plain
from src.outcomes import Outcome

#: Unauthenticated, one call, whole board. There is no `content=false` here —
#: Ashby ships every description inline (~2MB for a 120-role board) and offers
#: no way to decline them.
API = "https://api.ashbyhq.com/posting-api/job-board/{slug}"

#: Three tries, then the company is `probe-failed` and excluded. FINDINGS' 3-in-12
#: failure rate is a per-request coin flip; three of them is enough that a
#: company lost to it is a real outage rather than bad luck.
ATTEMPTS = 3

#: Seconds, multiplied by the attempt number. Backoff is for throttling, and a
#: throttle answers a fast retry the same way it answered the first call.
BACKOFF = 5

#: Ashby answered 12 concurrent callers in the same 2s it answered one, both in
#: FINDINGS' measurements and again today, so this is bounded by politeness
#: rather than by throughput. The whole Ashby corpus is 264 companies.
WORKERS = 12

Roles = list[dict[str, Any]]


def parse(payload: str) -> Roles | Outcome:
    """The board's roles, or the outcome saying why we don't trust the response.

    Ashby states no count of its own, so "did the whole board arrive" is not a
    question this can answer — only "is this whole JSON with a jobs array in it".
    An empty array passes, and means it: a slug that isn't a board 404s before
    ever reaching here.
    """
    try:
        roles = json.loads(payload)["jobs"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return Outcome.PROBE_FAILED
    return roles if isinstance(roles, list) else Outcome.PROBE_FAILED


def probe(slug: str, timeout: int = 240, attempts: int = ATTEMPTS) -> Roles | Outcome:
    """Every open role on an Ashby board, or the outcome that says why not.

    A 404 is definitive and returns immediately — retrying a slug that is not a
    board only makes the run longer. Everything else gets `attempts` tries with
    growing backoff, and exhausting them is `probe-failed`: a company we could
    not read, excluded and counted, never listed as hiring nobody.

    The timeout is 240s rather than Greenhouse's 30 because FINDINGS measured
    single calls at ~151s when Ashby was throttling. At today's 2s it never
    fires; it exists so that the throttled case fails slowly instead of failing
    everywhere.
    """
    for attempt in range(1, attempts + 1):
        status, body = get(API.format(slug=slug), timeout)
        if status == 404:
            return Outcome.SLUG_UNRESOLVED
        if status == 200 and not isinstance(roles := parse(body), Outcome):
            return roles
        if attempt < attempts:
            sleep(BACKOFF * attempt)
    return Outcome.PROBE_FAILED


def probe_all(slugs: Iterable[str], workers: int = WORKERS) -> dict[str, Roles | Outcome]:
    """Probe many boards concurrently — every slug resolves to roles or an outcome.

    Ashby's latency is a server-side delay rather than throughput, so concurrency
    converts it directly into wall time: FINDINGS measured 151s → 16.8s per
    company going from 1 caller to 12, which is what keeps 1,000 companies inside
    the 6h workflow cap even if the throttling returns. Today's 2s makes this
    ~35s for the whole 264-company Ashby corpus.

    Duplicate slugs collapse — two companies claiming one board is a slug
    problem, not a reason to fetch it twice.
    """
    unique = sorted(set(slugs))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return dict(zip(unique, pool.map(probe, unique), strict=True))


def locations(role: Mapping[str, Any]) -> list[str]:
    """Every place this role is open in — primary first, then secondaries.

    Ashby's `secondaryLocations` entries are objects wrapping their own
    `location` string (all 158 seen on a live board), but this is a trust
    boundary and a bare string there would otherwise crash the build, so both
    shapes are read.
    """
    secondary = (
        entry.get("location") if isinstance(entry, Mapping) else entry
        for entry in role.get("secondaryLocations") or ()
    )
    return [place for place in (role.get("location"), *secondary) if isinstance(place, str)]


def text(role: Mapping[str, Any]) -> str:
    """This posting's prose (T8.4). It is already in the payload and always was.

    Ashby ships `descriptionPlain` *and* `descriptionHtml` unconditionally — there
    is no `content=false` to pass and no second call to make, so the 2MB this
    module's docstring mentions has been mostly prose we discarded since T3.2. The
    plain form is one field and whole, unlike Lever's four; the HTML is the
    fallback for a posting that ships only that shape.
    """
    flat = role.get("descriptionPlain")
    return plain(flat if isinstance(flat, str) and flat.strip() else role.get("descriptionHtml"))
