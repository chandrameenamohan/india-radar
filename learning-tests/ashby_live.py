#!/usr/bin/env python3
"""INTEGRATION CHECK for T3.2 — the Ashby probe against live boards.

Lives here rather than in tests/ for the reason VERIFICATION.md gives: `make
check` must not go red because someone else's API is down. Re-run on demand:

    .venv/bin/python learning-tests/ashby_live.py

BELIEFS UNDER TEST:
  BELIEF 17: 12 real slugs probed CONCURRENTLY all resolve — to roles or to an
             outcome, never to nothing — and the wall time is bounded. This is
             the DoD's integration check, and it is the shape the 6h workflow
             cap depends on: Ashby's cost is a server-side delay, so 12 callers
             finish in about the time one does.
  BELIEF 18: a slug that is not a board 404s, and lands on `slug-unresolved`.
             Ashby is NOT Lever's 200-with-empty-array trap.
  BELIEF 19: FINDINGS §1's ~151s per call no longer holds. It was the number the
             whole refresh budget was sized on, and if it has come back the
             tiering in T6.3 has to change.

The per-slug role counts print so a human can compare one against the public
board; the board URL is printed beside it to make that a ten-second check.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ashby import WORKERS, probe, probe_all  # noqa: E402
from src.outcomes import Outcome  # noqa: E402

# Twelve real slugs from data/slugs.json — the corpus's own Ashby companies,
# not a hand-picked sample of famous boards.
SLUGS = [
    "1password", "sevenai", "9fin", "arq", "abacum", "abridge",
    "afterquery", "agentio", "alaro", "provable", "aleph", "anyscale",
]

# Nobody's board. Deliberately unregisterable-looking rather than merely unused.
NOT_A_BOARD = "no-such-company-india-radar-probe"

# FINDINGS §1's figure. Wall time for 12 concurrent callers should be nowhere
# near this; if it is, Ashby is throttling again and T6.3's weekly tiering is
# load-bearing rather than precautionary.
FINDINGS_LATENCY = 151


def main() -> int:
    failures = []

    print(f"BELIEF 17/19: {len(SLUGS)} live boards at concurrency {WORKERS}")
    started = time.monotonic()
    boards = probe_all(SLUGS)
    wall = time.monotonic() - started

    for slug in SLUGS:
        result = boards.get(slug)
        if result is None:
            failures.append(f"{slug}: resolved to nothing at all")
            continue
        answer = result if isinstance(result, Outcome) else f"{len(result):4d} roles"
        print(f"  {slug:14s} {answer:>12}   https://jobs.ashbyhq.com/{slug}")

    read = [s for s in SLUGS if not isinstance(boards.get(s), Outcome)]
    print(f"\n  {len(read)}/{len(SLUGS)} boards read, {wall:.1f}s wall "
          f"({wall / len(SLUGS):.1f}s per company)")

    if len(boards) != len(SLUGS):
        failures.append(f"{len(SLUGS) - len(boards)} slugs resolved to no outcome at all")
    if not read:
        failures.append("no board was readable — Ashby is down, or the API moved")
    if wall > FINDINGS_LATENCY * 2:
        failures.append(f"{wall:.0f}s wall for {len(SLUGS)} concurrent: not bounded")
    if wall < FINDINGS_LATENCY:
        print(f"  BELIEF 19 CONFIRMED: FINDINGS' ~{FINDINGS_LATENCY}s per call is stale — "
              f"{wall:.1f}s for all {len(SLUGS)}")

    print("\nBELIEF 18: a slug that is not a board")
    outcome = probe(NOT_A_BOARD)
    print(f"  {NOT_A_BOARD} -> {outcome}")
    if outcome is not Outcome.SLUG_UNRESOLVED:
        failures.append(f"bad slug returned {outcome}, expected {Outcome.SLUG_UNRESOLVED}")

    print()
    for failure in failures:
        print(f"FAILED: {failure}")
    print("BELIEF 17/18/19: " + ("HOLD" if not failures else "FALSE"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
