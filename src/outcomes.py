"""Outcome vocabulary and build report — SPEC feature 12.

A zero is never ambiguous. Every company in the corpus leaves a build under
exactly one outcome, and only a company whose board we successfully read can be
listed. Absence of knowledge ("we never got an answer") and a finding ("they
have no roles in any country we cover") are different outcomes and must never
collapse into one.

`no-india-roles` became `no-target-roles` in T8.4, when the radar widened from
India to fifteen countries (SPEC "Expansion — ROLE·ATLAS"). The meaning was
unchanged and so was its place in `CHECKED`: we read the whole board and none of
it was anywhere we cover. Only the name got wider, because the old one would now
say "no India roles" about a company excluded for having no Berlin role either.

`no-target-roles` became `no-located-roles` in T16.1, and this time the MEANING
moved, which is why the name had to move with it. A role is now published for
naming a place at all — the fifteen enrich a role rather than admit it — so the
only board that leaves under this outcome is one where not a single posting
stated a location we could read. The old name would now say "no target roles"
about a company whose whole board is in São Paulo, which is a claim about São
Paulo that this register never made and cannot support. Same argument as T8.4's,
one ring out.
"""
from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from enum import StrEnum
from pathlib import Path
from typing import Any


class Outcome(StrEnum):
    LISTED = "listed"
    #: We read the whole board and no posting on it stated a place we could read
    #: (T16.1). NOT "no roles in the fifteen" — that stopped being a reason to
    #: exclude anybody when a matched country became an enrichment.
    NO_LOCATED_ROLES = "no-located-roles"
    SLUG_UNRESOLVED = "slug-unresolved"
    PROBE_FAILED = "probe-failed"
    EMPTY_BOARD_UNVERIFIED = "empty-board-unverified"  # Lever's 200-with-empty-array
    NOT_QUALIFIED = "not-qualified"
    #: The board we found for this name is another company's, so its roles are
    #: already listed under the company that owns it — or belong to a company
    #: that isn't in the corpus at all (T10.1). NOT `checked`: we read a board,
    #: but not this company's, so we still know nothing about whether it hires.
    ANOTHER_COMPANYS_BOARD = "another-companys-board"


#: The only outcomes that mean we actually read the company's board. Everything
#: else is an absence of knowledge, and the site must say so rather than imply
#: the company isn't hiring.
CHECKED = frozenset({Outcome.LISTED, Outcome.NO_LOCATED_ROLES})


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
