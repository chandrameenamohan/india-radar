#!/usr/bin/env python3
"""INTEGRATION CHECK for T3.1 — the Greenhouse probe against live boards.

Lives here rather than in tests/ for the reason VERIFICATION.md gives: `make
check` must not go red because someone else's API is down. Re-run on demand:

    .venv/bin/python learning-tests/greenhouse_live.py

BELIEFS UNDER TEST:
  BELIEF 14: probing 5 real slugs returns a role list for every one, each with
             at least one role — the probe's agreement rule does not reject
             live boards.
  BELIEF 15: meta.total still equals the number of roles returned, on a raw
             response this module didn't parse. This is FINDINGS §1's central
             claim and the reason there is no pagination to walk.
  BELIEF 16: a slug that is not a board 404s, and lands on `slug-unresolved`
             rather than an empty success.

The per-slug counts are printed so a human can compare one against the
provider's public board — that half of the acceptance is an eyeball check, and
the board URL is printed next to the count to make it a ten-second one.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.greenhouse import API, probe  # noqa: E402
from src.net import get  # noqa: E402
from src.outcomes import Outcome  # noqa: E402

# The same 5 boards FINDINGS §1 measured, so the numbers compare across runs.
SLUGS = ["databricks", "anthropic", "gleanwork", "togetherai", "figma"]

# Nobody's board. Deliberately unregisterable-looking rather than merely unused.
NOT_A_BOARD = "no-such-company-india-radar-probe"


def main() -> int:
    failures = []

    print("BELIEF 14/15: live boards, probe result vs raw meta.total")
    for slug in SLUGS:
        roles = probe(slug)
        if isinstance(roles, Outcome):
            failures.append(f"{slug}: probe returned {roles}, expected roles")
            print(f"  {slug:14s} {roles}")
            continue

        status, body = get(API.format(slug=slug))
        meta_total = json.loads(body)["meta"]["total"] if status == 200 else None

        ok = len(roles) > 0 and meta_total == len(roles)
        if not ok:
            failures.append(f"{slug}: {len(roles)} roles, meta.total={meta_total}")
        print(
            f"  {slug:14s} {len(roles):4d} roles  meta.total={meta_total}  "
            f"{'OK' if ok else 'MISMATCH'}   https://job-boards.greenhouse.io/{slug}"
        )

    print("\nBELIEF 16: a slug that is not a board")
    outcome = probe(NOT_A_BOARD)
    print(f"  {NOT_A_BOARD} -> {outcome}")
    if outcome is not Outcome.SLUG_UNRESOLVED:
        failures.append(f"bad slug returned {outcome}, expected {Outcome.SLUG_UNRESOLVED}")

    print()
    for failure in failures:
        print(f"FAILED: {failure}")
    print("BELIEF 14/15/16: " + ("HOLD" if not failures else "FALSE"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
