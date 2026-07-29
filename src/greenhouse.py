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
from src.outcomes import Outcome

#: content=false drops the job descriptions — we need locations, not prose, and
#: the full payload is orders of magnitude larger for no gain.
API = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=false"

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


def probe(slug: str, timeout: int = 30) -> Roles | Outcome:
    """Every open role on a Greenhouse board, or the outcome that says why not.

    ponytail: one company, one call, and deliberately no batch wrapper — at
    0.35s a caller looping over a 1,000-company corpus spends ~6 minutes, well
    inside the nightly budget. Ceiling: if Greenhouse slows or the corpus grows
    an order of magnitude, wrap the loop in the ThreadPoolExecutor
    slugs.resolve_all already uses. Ashby (T3.2) is the one that needs it.
    """
    status, body = get(API.format(slug=slug), timeout)
    if status == 404:
        return Outcome.SLUG_UNRESOLVED
    if status != 200:
        return Outcome.PROBE_FAILED
    return parse(body)


def locations(role: Mapping[str, Any]) -> list[str]:
    """Where this role is open. Greenhouse nests exactly one place per role and
    has no second-location field, so this is a list of one — or of none, when
    the board left the location off entirely.

    A list because Ashby genuinely gives several (`secondaryLocations`), and the
    build counts India roles by role rather than by location string.
    """
    name = (role.get("location") or {}).get("name")
    return [name] if isinstance(name, str) else []


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
