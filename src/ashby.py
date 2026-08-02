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

**The board says who it is; the API does not.** No organizationName, no company
field — nothing in the posting payload but the slug echoed back inside jobUrl.
That was harmless while every Ashby slug came off the company's own careers
page, and became load-bearing the moment T12.1 started guessing them, which is
why `identity` reads the hosted board PAGE instead.

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
import re
from collections.abc import Iterable, Mapping
from concurrent.futures import ThreadPoolExecutor
from time import sleep
from typing import Any, NamedTuple

from src.net import get
from src.openness import plain
from src.outcomes import Outcome

#: Unauthenticated, one call, whole board. There is no `content=false` here —
#: Ashby ships every description inline (~2MB for a 120-role board) and offers
#: no way to decline them.
API = "https://api.ashbyhq.com/posting-api/job-board/{slug}"

#: The board PAGE rather than the posting API, and the only place Ashby states
#: *whose* board a slug is. The API names nobody — no organizationName, no
#: company field, only the slug echoed back inside jobUrl — so a guessed slug
#: (T12.1) either comes here or stays unverified.
BOARD = "https://jobs.ashbyhq.com/{slug}"

#: The board page is rendered client-side: the server ships a spinner and one
#: `window.__appData` blob, and the organisation sits inside it stating both its
#: name and its own website. Sliced out with the JSON decoder rather than a
#: regex because the blob is 7KB-2MB of nested objects and a regex that walks
#: into one is a regex that eventually reads the wrong string as a company's
#: address. `raw_decode` stops itself at the value's closing brace.
_APP_DATA = "window.__appData = "

#: "Ramp Jobs", "1Password Jobs" — and a bare "Jobs" when the page states no
#: company at all. Measured over the 264 known-good Ashby boards
#: (learning-tests/ashby_collision_live.py, CONTROL): 254 titled themselves
#: "<something> Jobs" and the other 10 are the bare form. Nothing else. So the
#: suffix is Ashby's template rather than a coincidence, and stripping it leaves
#: the name — which is why it is stripped rather than matched around: a company
#: literally named "Jobs" would otherwise be contained in every board on the
#: platform, and `states_company` asks only about containment.
_TITLE = re.compile(r"<title>([^<]*)</title>")
_JOBS = " Jobs"

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


class Identity(NamedTuple):
    """What a board page says about the company behind it.

    Two fields because one of them is not enough, which T12.1 measured rather
    than assumed: verifying a guessed slug by the stated NAME alone was a
    different company **8 times in 32**, because so many of these companies are
    one generic word and Ashby will hand you the other Boom without hesitating.
    """

    name: str | None
    website: str | None


def identity(slug: str, timeout: int = 30) -> Identity:
    """Who this board says it belongs to — or `Identity(None, None)`, meaning it
    said nothing and this company cannot be resolved to it.

    Ashby answers **200 for every slug ever typed**: `jobs.ashbyhq.com/<nonsense>`
    returns a 7,128-byte shell titled a bare "Jobs" (measured against
    `zzzznotarealslugxyz`, 1.56s, beside 77KB for `ramp`). So the status line
    decides nothing and the stated name decides everything.

    **A silent page is not proof there is no board**, and this returns the same
    nothing either way on purpose. Measured over the 264 Ashby boards
    careers-page discovery had already proved: 10 serve that same shell, of
    which 8 slugs are genuinely dead and **2 are live boards Ashby will not name
    on their hosted page** — `cursor` answers the posting API with 1.04MB of
    jobs and still renders the nonsense-slug shell, byte for byte. Existence was
    never the question a guess has to answer: a board that will not say whose it
    is cannot be verified, so it is unresolvable whether or not it is there.

    The website comes from `organization.publicWebsite`. If Ashby ever stops
    shipping it, every guess stops verifying and every guessed company stays
    unresolved, which is the direction this whole module fails in on purpose.
    """
    status, body = get(BOARD.format(slug=slug), timeout)
    if status != 200:
        return Identity(None, None)

    found = _TITLE.search(body)
    title = found.group(1).strip() if found else ""
    name = title[: -len(_JOBS)].strip() if title.endswith(_JOBS) else None
    return Identity(name or None, _public_website(body))


def _public_website(html: str) -> str | None:
    """The address the organisation states as its own, out of the board page's
    state blob."""
    start = html.find(_APP_DATA)
    if start < 0:
        return None
    try:
        data, _ = json.JSONDecoder().raw_decode(html, start + len(_APP_DATA))
    except (json.JSONDecodeError, ValueError):
        return None
    organization = data.get("organization") if isinstance(data, dict) else None
    site = organization.get("publicWebsite") if isinstance(organization, Mapping) else None
    return site if isinstance(site, str) and site.strip() else None


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
