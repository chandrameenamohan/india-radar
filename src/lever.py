"""Lever board probe — T3.3 (SPEC feature 4).

Lever is the last 51 slugs, and the whole of what `probe-failed` still holds.

**The trap, re-measured.** FINDINGS §1 recorded that a wrong Lever slug can
answer HTTP 200 with an empty array — indistinguishable from a company with no
open roles, and the reason `empty-board-unverified` exists at all. Ten wrong
slugs of three shapes were tried today (nonsense, near-miss spellings, the
un-suffixed form of slugs we hold as `asapp-2`/`easypost-2`) and **every one
404s** with `{"ok":false,"error":"Document not found"}`. So the trap's mechanism
is narrower than it was written down as.

It is not gone. Three slugs in our own corpus — `ramenvr`, `tesorio`, `trela` —
answer 200 with `[]` right now, and nothing in that response says whether it is
an abandoned board, a renamed company or a firm that simply isn't hiring. Lever
has no counterpart to Greenhouse's `boards/{slug}` name lookup, so there is no
second question to ask. An empty board therefore stays `empty-board-unverified`:
excluded, counted as an absence of knowledge rather than as a finding, exactly
as the outcome vocabulary requires. Ashby's empty array is believed and Lever's
is not — the two look identical and mean different things.

**One posting can be open in several places.** `categories.allLocations` is a
list beside the primary `categories.location`, present on all 158 postings
measured across six boards and containing the primary in every case where the
primary exists at all. So `allLocations` is the answer when it has anything in
it, and the primary is the fallback — a Kpler posting states `location: null`
with `allLocations: []`, which is a role with no stated place, not a crash.
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from src.net import get
from src.outcomes import Outcome

#: `mode=json` is the documented public feed; without it the same URL 404s the
#: same way, so the parameter is the format rather than the door.
API = "https://api.lever.co/v0/postings/{slug}?mode=json"

Roles = list[dict[str, Any]]


def parse(payload: str) -> Roles | Outcome:
    """The board's postings, or the outcome saying why we don't trust the answer.

    Lever states no count of its own, so a truncated body is undetectable and
    all this can refuse is something that isn't a whole JSON array. An EMPTY
    array is refused too, and that is the point of the module: zero postings is
    the one answer Lever gives that we cannot tell apart from a mistake.
    """
    try:
        roles = json.loads(payload)
    except json.JSONDecodeError:
        return Outcome.PROBE_FAILED
    if not isinstance(roles, list):
        return Outcome.PROBE_FAILED
    return roles or Outcome.EMPTY_BOARD_UNVERIFIED


def probe(slug: str, timeout: int = 30) -> Roles | Outcome:
    """Every open role on a Lever board, or the outcome that says why not.

    ponytail: one company, one call, no retries and no batch wrapper — the same
    shape as `greenhouse.probe`, which carries 429 companies to this one's 51.
    Measured: all 51 answered first try, 2–5.4s each, no 5xx and no throttling
    at 12 concurrent. Ceiling: the full build went 5m12s → 9m38s with these 51
    sequential calls in it, against a 6h workflow cap. Upgrade path if Lever
    slows or the corpus grows — `ashby.probe_all` is the concurrent version of
    exactly this, and did all 51 in 15s.
    """
    status, body = get(API.format(slug=slug), timeout)
    if status == 404:
        return Outcome.SLUG_UNRESOLVED
    if status != 200:
        return Outcome.PROBE_FAILED
    return parse(body)


def locations(role: Mapping[str, Any]) -> list[str]:
    """Every place this posting is open in.

    `allLocations` already contains the primary, so it is used whole rather than
    prepended to — unlike Ashby, where `secondaryLocations` is genuinely the
    other places. An empty list falls back to the primary, and a posting that
    states neither is a role with no location, which the build treats as not
    India rather than as an error.
    """
    categories = role.get("categories") or {}
    places = categories.get("allLocations") or [categories.get("location")]
    return [place for place in places if isinstance(place, str)]
