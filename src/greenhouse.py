"""Greenhouse board probe — T3.1 (SPEC feature 4).

Greenhouse is the good citizen of the three ATSes: one unauthenticated call,
0.35s median, and the response carries `meta.total` alongside the roles it
returns — so a short answer is *detectable* rather than silently short. There is
no pagination to walk (FINDINGS §1: meta.total matched the returned count on 5/5
real boards).

This module refuses to guess. A 404 means the slug is not a board — T2.1 read
the wrong link, or the company left Greenhouse — and that is `slug-unresolved`.
Anything else that is not a clean, self-consistent 200 is `probe-failed`.
Neither ever becomes an empty role list, because an empty role list reads on the
site as "we checked, they aren't hiring in India".
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from src.net import get
from src.openness import plain
from src.outcomes import Outcome

#: content=false drops the job descriptions. It is the pass every board gets: 259
#: of 422 Greenhouse boards have no posting in any target country (T8.1), and
#: those boards never need the prose.
API = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=false"

#: The same endpoint, with the descriptions in it — what T8.4 fetches for a board
#: that turned out to have a target-country posting. Measured (T8.1): 13.7x-35.3x
#: the bytes and under 2x the latency, on the same single call. Every role on all
#: three sampled boards carried non-empty content (803/803, 374/374, 128/128).
RICH = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"

#: The board itself, rather than its jobs — the one place Greenhouse states
#: *whose* board a slug belongs to. The jobs payload never says, so a guessed
#: slug (T2.2) has no way to tell "this company's board" from "a board".
BOARD = "https://boards-api.greenhouse.io/v1/boards/{slug}"

Roles = list[dict[str, Any]]


def parse(payload: str) -> Roles | Outcome:
    """The board's roles, or the outcome saying why we don't trust the response.

    meta.total is the board's own count of what it should have sent. If it
    disagrees with what arrived, the response is truncated or paginated, and the
    honest answer is that we failed to read this board — not the short list we
    happen to be holding.
    """
    try:
        board = json.loads(payload)
        roles = board["jobs"]
        total = board["meta"]["total"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return Outcome.PROBE_FAILED

    if not isinstance(roles, list) or len(roles) != total:
        return Outcome.PROBE_FAILED
    return roles


def _board(url: str, timeout: int) -> Roles | Outcome:
    """One board fetch, with the status rules both passes keep."""
    status, body = get(url, timeout)
    if status == 404:
        return Outcome.SLUG_UNRESOLVED
    if status != 200:
        return Outcome.PROBE_FAILED
    return parse(body)


def probe(slug: str, timeout: int = 30) -> Roles | Outcome:
    """Every open role on a Greenhouse board, or the outcome that says why not.

    ponytail: one company, one call, and deliberately no batch wrapper — at
    0.35s a caller looping over a 1,000-company corpus spends ~6 minutes, well
    inside the nightly budget. Ceiling: if Greenhouse slows or the corpus grows
    an order of magnitude, wrap the loop in the ThreadPoolExecutor
    slugs.resolve_all already uses. Ashby (T3.2) is the one that needs it.
    """
    return _board(API.format(slug=slug), timeout)


def describe(slug: str, timeout: int = 60) -> Roles | Outcome:
    """The same board again, with each role's description text in it (T8.4).

    Greenhouse is the only provider that charges for prose, and it charges in
    bytes rather than in calls — so this is the second half of the two-pass T8.1
    measured as affordable: the cheap `probe` over all 422 boards, this over the
    163 that turned out to have a target-country posting. Whole corpus, both
    passes: 1m55s and 270MB at 10 concurrent callers.

    The timeout is double `probe`'s because the payload is: a 803-role board goes
    0.69MB → 9.40MB. The latency multiplier stayed under 2x throughout, so 60s is
    slack rather than an expected wait.
    """
    return _board(RICH.format(slug=slug), timeout)


def locations(role: Mapping[str, Any]) -> list[str]:
    """Where this role is open. Greenhouse nests exactly one place per role and
    has no second-location field, so this is a list of one — or of none, when
    the board left the location off entirely.

    A list because Ashby genuinely gives several (`secondaryLocations`), and the
    build counts India roles by role rather than by location string.
    """
    name = (role.get("location") or {}).get("name")
    return [name] if isinstance(name, str) else []


def text(role: Mapping[str, Any]) -> str:
    """This role's description as readable prose, or "" if we never asked for it.

    Empty is the answer for every role that came off the cheap pass, and it is an
    honest one: `openness.classify("")` is `unknown`, which is what we know about
    a posting whose text we did not fetch. `content` is doubly HTML-escaped here,
    which `openness.plain` handles.
    """
    return plain(role.get("content"))


def department(role: Mapping[str, Any]) -> str | None:
    """The board's own word for where this role sits, or None (T9.2).

    A LIST here, unlike Ashby's and Lever's single string: Greenhouse hangs a job
    off a department and, often, that department's parent ("R&D: Platform" under
    "R&D"). The first is the specific one and the one the board leads with.

    None for every role off the cheap pass, and that is the same honest absence
    `text` returns: `departments` arrives only with `content=true` — measured
    0 of 142 jobs on `content=false`, 142 of 142 on `content=true` — so a board
    whose second pass failed says nothing here rather than saying nothing exists.
    """
    first = next(iter(role.get("departments") or []), None)
    name = first.get("name") if isinstance(first, Mapping) else None
    return name.strip() or None if isinstance(name, str) else None


def board_name(slug: str, timeout: int = 20) -> str | None:
    """The company name this board states it belongs to, or None if there is no
    such board.

    Anything short of a 200 carrying a string `name` is None: this answer only
    ever admits a slug, so an unreadable board must not become a claim about
    which company it is.
    """
    status, body = get(BOARD.format(slug=slug), timeout)
    if status != 200:
        return None
    try:
        name = json.loads(body).get("name")
    except (json.JSONDecodeError, AttributeError):
        return None
    return name if isinstance(name, str) else None
