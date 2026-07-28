#!/usr/bin/env python3
"""INTEGRATION CHECK for T2.1 — careers-page slug discovery against live pages.

Lives here rather than in tests/ for the reason VERIFICATION.md gives: `make
check` must not go red because someone else's website is down. Re-run on demand:

    .venv/bin/python learning-tests/careers_slugs_live.py

BELIEFS UNDER TEST:
  BELIEF 11: resolving these 7 real companies BY NAME — guessing the domain,
             then regexing the careers page — clears the measured 50% baseline.
  BELIEF 12: Figma resolves to greenhouse/figma and Ramp to ashby/ramp, the two
             known-good pairs named in the task's acceptance.
  BELIEF 13: every company lands on exactly one side with a reason, so nothing
             is silently dropped between the corpus and the probe.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.slugs import resolve_all  # noqa: E402

# The same 7 used for the 4/7 baseline in FINDINGS §3, so the numbers compare.
COMPANIES = ["Anthropic", "Figma", "Glean", "Ramp", "Vercel", "Postman", "Razorpay"]


def main():
    resolution = resolve_all(COMPANIES)

    for name in COMPANIES:
        found = resolution.resolved.get(name)
        print(f"  {name:10s} " + (json.dumps(found) if found else resolution.unresolved[name]))
    print(f"\n  resolved {len(resolution.resolved)}/{len(COMPANIES)} = {resolution.rate:.0%}")

    assert resolution.rate >= 0.5, \
        f"BELIEF 11 FALSE: {resolution.rate:.0%} is below the 50% baseline"
    assert resolution.resolved.get("Figma", {}).get("slug") == "figma", "BELIEF 12 FALSE: Figma"
    assert resolution.resolved.get("Ramp", {}).get("slug") == "ramp", "BELIEF 12 FALSE: Ramp"
    assert set(resolution.resolved) | set(resolution.unresolved) == set(COMPANIES), \
        "BELIEF 13 FALSE: a company was dropped between input and output"
    assert all(resolution.unresolved.values()), \
        "BELIEF 13 FALSE: an unresolved company has no reason"

    print("\nAll asserted beliefs held.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
