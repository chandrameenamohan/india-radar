"""Does Ashby deserve its own weekly tier? — T6.3, measured live.

T6.3 exists because FINDINGS §1 measured Ashby at ~151s/company and concluded
the corpus could not be refreshed nightly. T3.2 re-measured it at ~2s and T6.2
built ONE nightly covering every provider. This re-measures the tiering decision
itself — per T6.3's own DoD, which says the split must be justified by a cost
that is true today, not inherited.

The question is not "how fast is Ashby". It is "what does keeping Ashby in the
nightly COST", because that is what a weekly tier would buy back, and it is paid
for in staleness: six days of it, on a site whose whole claim is that a role was
open on the day it says.

Run:  .venv/bin/python -m learning-tests.nightly_tiers_live
      (or: .venv/bin/python learning-tests/nightly_tiers_live.py)
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from time import monotonic

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import ashby, greenhouse, lever  # noqa: E402

SLUGS = Path("data/slugs.json")

#: Greenhouse and Lever are probed sequentially by the build, so their corpus
#: cost is per-call latency times the slug count. Sampling beats waiting 8.6
#: minutes to re-derive a number the nightly already prints.
SAMPLE = 12


def by_ats(slugs: dict[str, dict[str, str]]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for entry in slugs.values():
        out.setdefault(entry["ats"], []).append(entry["slug"])
    return {ats: sorted(set(found)) for ats, found in out.items()}


def sequential_cost(probe, slugs: list[str], sample: int) -> tuple[float, float]:
    """Median-ish per-call seconds and the projected whole-corpus cost."""
    picked = random.Random(63).sample(slugs, min(sample, len(slugs)))
    started = monotonic()
    for slug in picked:
        probe(slug)
    each = (monotonic() - started) / len(picked)
    return each, each * len(slugs)


def main() -> None:
    corpus = by_ats(json.loads(SLUGS.read_text()))
    for ats, slugs in sorted(corpus.items()):
        print(f"{ats:<12} {len(slugs)} slugs")
    print()

    # Ashby whole, because it is concurrent and 264 slugs is under a minute —
    # the number the decision turns on gets measured, not projected.
    started = monotonic()
    probed = ashby.probe_all(corpus["ashby"])
    ashby_wall = monotonic() - started
    print(f"ashby        WHOLE CORPUS {len(probed)} slugs, concurrent: {ashby_wall:.1f}s")

    gh_each, gh_total = sequential_cost(greenhouse.probe, corpus["greenhouse"], SAMPLE)
    print(f"greenhouse   {gh_each:.2f}s/call x {len(corpus['greenhouse'])} sequential"
          f" -> {gh_total / 60:.1f} min")

    lv_each, lv_total = sequential_cost(lever.probe, corpus["lever"], SAMPLE)
    print(f"lever        {lv_each:.2f}s/call x {len(corpus['lever'])} sequential"
          f" -> {lv_total / 60:.1f} min")

    probes = ashby_wall + gh_total + lv_total
    print()
    print(f"all three probes: {probes / 60:.1f} min")
    print(f"ashby's share of that: {100 * ashby_wall / probes:.1f}%")
    print(f"a weekly tier would save {ashby_wall:.0f}s/night and cost 6 days of staleness")


if __name__ == "__main__":
    main()
