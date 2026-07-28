"""The build spine — T5.1 (SPEC feature 12's emit half; the site reads this).

Corpus in, `data/companies.json` out, with every company that didn't make it
accounted for in `build-report.json` under exactly one outcome. This is the one
place the four existing modules meet, and it stays a spine rather than a
framework: no plugin registry, no pipeline abstraction, just the five steps the
architecture line in SPEC.md names.

The schema is versioned and *enforced on the way out*. A non-conforming row
raises instead of shipping, because a wrong row on a static site outlives the
build that made it — the JSON is served straight to the browser with nothing in
between to catch it. Validation belongs at the write, not at the read.
"""
from __future__ import annotations

import json
import sys
from collections.abc import Callable, Iterable, Mapping
from datetime import date
from pathlib import Path
from typing import Any

from src.greenhouse import Roles
from src.greenhouse import parse as parse_board
from src.greenhouse import probe as greenhouse_probe
from src.india import is_india
from src.outcomes import Outcome, report, write_report
from src.slugs import Slug

#: Bump when a row's shape changes. The site reads this and refuses a version it
#: doesn't know, rather than silently rendering fields that moved.
SCHEMA_VERSION = 1

Probe = Callable[[str], Roles | Outcome]
Row = dict[str, Any]

#: A v1 row: what the corpus knew about the funding, plus what the board proved
#: about the hiring. Types only — the value rules that carry meaning are in
#: `errors`. Roles, cities and apply links are T4.1; they widen this, and the
#: version is how the site will know which shape it's holding.
FIELDS: dict[str, type | tuple[type, ...]] = {
    "name": str,
    "ats": str,
    "slug": str,
    "india_roles": int,
    "amount": (int, type(None)),
    "currency": (str, type(None)),
    "round_letter": (str, type(None)),
    "date": str,
    "source_url": str,
    "qualified_by": str,
}

#: The probes that exist. Ashby (T3.2) and Lever (T3.3) join by adding a line
#: here — and until they do, a company on either board is `probe-failed`, which
#: is the truth: we hold a slug we cannot read.
PROBES: dict[str, Probe] = {"greenhouse": greenhouse_probe}


def errors(row: Mapping[str, Any]) -> list[str]:
    """Every way this row fails schema v1. Empty means it may ship.

    Unknown fields are a violation, not a courtesy: an enrichment that adds a
    field without bumping the version is exactly how the site starts rendering
    something the schema never promised.
    """
    problems = []
    for field, types in FIELDS.items():
        if field not in row:
            problems.append(f"missing {field!r}")
        elif not isinstance(row[field], types):
            problems.append(f"{field!r} is {type(row[field]).__name__}, not {types}")
    if extra := sorted(set(row) - set(FIELDS)):
        problems.append(f"unknown field(s) {extra}")

    # A listed company is one whose board we read and found India roles on. Zero
    # here would be a row saying "listed, hiring nobody" — the ambiguous zero
    # this project exists to refuse.
    if isinstance(row.get("india_roles"), int) and row["india_roles"] < 1:
        problems.append("india_roles < 1: a listed company has at least one India role")
    if row.get("qualified_by") not in ("letter", "amount"):
        problems.append(f"qualified_by {row.get('qualified_by')!r} is not 'letter' or 'amount'")
    if row.get("ats") not in PROBES:
        problems.append(f"ats {row.get('ats')!r} has no probe, so nothing verified this row")
    return problems


def build(
    corpus: Iterable[Mapping[str, Any]],
    slugs: Mapping[str, Slug],
    probes: Mapping[str, Probe] = PROBES,
) -> tuple[list[Row], dict[str, Outcome]]:
    """The spine: corpus → slug → board → India filter → rows.

    Returns the listed rows and one outcome per company. Every `continue` below
    is a company leaving with a reason attached; none of them can fall through
    into the site, and none of them becomes an empty role list.
    """
    rows: list[Row] = []
    outcomes: dict[str, Outcome] = {}

    for company in corpus:
        name = company["name"]
        slug = slugs.get(name)
        if slug is None:
            outcomes[name] = Outcome.SLUG_UNRESOLVED
            continue

        probe = probes.get(slug["ats"])
        if probe is None:
            outcomes[name] = Outcome.PROBE_FAILED
            continue

        result = probe(slug["slug"])
        if isinstance(result, Outcome):
            outcomes[name] = result
            continue

        # Greenhouse nests the location; unwrapped here rather than in india.py
        # because the three ATSes genuinely disagree on a role's shape.
        india = [r for r in result if is_india((r.get("location") or {}).get("name"))]
        if not india:
            outcomes[name] = Outcome.NO_INDIA_ROLES
            continue

        outcomes[name] = Outcome.LISTED
        rows.append(
            {
                "name": name,
                "ats": slug["ats"],
                "slug": slug["slug"],
                "india_roles": len(india),
                "amount": company["amount"],
                "currency": company["currency"],
                "round_letter": company["round_letter"],
                "date": company["date"],
                "source_url": company["source_url"],
                "qualified_by": company["qualified_by"],
            }
        )

    return rows, outcomes


def write(path: str | Path, rows: list[Row], snapshot: str | None = None) -> None:
    """Emit companies.json — or refuse to, loudly, and leave the last good file
    where it is. The snapshot date ships with the data because the site has to
    show it (SPEC feature 10) and a date computed at render time would claim a
    freshness the JSON doesn't have.
    """
    if bad := {row.get("name"): problems for row in rows if (problems := errors(row))}:
        raise ValueError(f"schema v{SCHEMA_VERSION} violations, nothing written: {bad}")

    Path(path).write_text(
        json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "snapshot": snapshot or date.today().isoformat(),
                "companies": rows,
            },
            indent=2,
        )
        + "\n"
    )


#: init.sh's smoke test drives the whole emit path offline through a fixture
#: board — the same build/validate/write code the real run uses, in
#: milliseconds, with no live API. It writes its OWN file: a smoke test must
#: never overwrite the published artifact, and a fixture-derived
#: companies.json is precisely the lie T6.4 exists to prevent.
SMOKE_BOARD = Path("tests/fixtures/greenhouse-board.json")
SMOKE_OUT = "data/companies.smoke.json"


def main(argv: list[str]) -> None:
    corpus = json.loads(Path("data/corpus.json").read_text())["companies"]
    slugs: dict[str, Slug] = json.loads(Path("data/slugs.json").read_text())
    probes = PROBES
    out = "data/companies.json"

    if smoke := ("--smoke" in argv):
        corpus = corpus[:1]
        slugs = {c["name"]: Slug(ats="greenhouse", slug="smoke", method="smoke") for c in corpus}
        probes = {"greenhouse": lambda _: parse_board(SMOKE_BOARD.read_text())}
        out = SMOKE_OUT

    rows, outcomes = build(corpus, slugs, probes)
    write(out, rows)

    built = report([c["name"] for c in corpus], outcomes)
    if not smoke:
        write_report("data/build-report.json", built)

    print(f"{out}: {len(rows)} listed of {built['corpus_size']} in corpus")
    for outcome, count in sorted(built["counts"].items()):
        if count:
            print(f"  {count:4d}  {outcome}")


if __name__ == "__main__":
    main(sys.argv[1:])
