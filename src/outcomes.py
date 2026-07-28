"""Outcome vocabulary and build report — SPEC feature 12.

A zero is never ambiguous. Every company in the corpus leaves a build under
exactly one outcome, and only a company whose board we successfully read can be
listed. Absence of knowledge ("we never got an answer") and a finding ("they
have no India roles") are different outcomes and must never collapse into one.
"""
from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from enum import StrEnum
from pathlib import Path
from typing import Any


class Outcome(StrEnum):
    LISTED = "listed"
    NO_INDIA_ROLES = "no-india-roles"
    SLUG_UNRESOLVED = "slug-unresolved"
    PROBE_FAILED = "probe-failed"
    EMPTY_BOARD_UNVERIFIED = "empty-board-unverified"  # Lever's 200-with-empty-array
    NOT_QUALIFIED = "not-qualified"


#: The only outcomes that mean we actually read the company's board. Everything
#: else is an absence of knowledge, and the site must say so rather than imply
#: the company isn't hiring.
CHECKED = frozenset({Outcome.LISTED, Outcome.NO_INDIA_ROLES})


def report(corpus: Iterable[str], outcomes: Mapping[str, Outcome]) -> dict[str, Any]:
    """Account for every corpus company under exactly one outcome.

    A company with no recorded outcome was never successfully checked, so it is
    counted `probe-failed` and excluded — never rendered as "not hiring". That
    default is the whole point: a pipeline that drops a company on the floor
    produces an honest gap in the report instead of a silent lie on the site.

    Raises ValueError on an outcome for a company outside the corpus, which
    means the pipeline and the corpus have diverged.
    """
    assigned = {name: outcomes.get(name, Outcome.PROBE_FAILED) for name in corpus}
    if stray := set(outcomes) - set(assigned):
        raise ValueError(f"outcomes for companies not in the corpus: {sorted(stray)}")

    counts = dict.fromkeys((o.value for o in Outcome), 0)
    for outcome in assigned.values():
        counts[outcome.value] += 1
    checked = sum(1 for o in assigned.values() if o in CHECKED)

    return {
        "corpus_size": len(assigned),
        "checked": checked,
        "unchecked": len(assigned) - checked,
        "counts": counts,
        "listed": sorted(n for n, o in assigned.items() if o is Outcome.LISTED),
        "companies": {n: o.value for n, o in sorted(assigned.items())},
    }


def write_report(path: str | Path, built: dict[str, Any]) -> None:
    """Emit build-report.json."""
    Path(path).write_text(json.dumps(built, indent=2) + "\n")
