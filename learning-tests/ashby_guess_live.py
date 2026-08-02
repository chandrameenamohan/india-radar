#!/usr/bin/env python3
"""Can Ashby slugs be guessed? — the measurement before the task.

2,201 of 2,915 companies are `slug-unresolved`, which is 76% of the corpus and
the largest single number in this project. `data/unresolved.json` says why:

    no-board-link     837   we read their careers page; it linked no board
    no-website        740   we never knew their site, so nothing could be read
    no-careers-page   619   we had a site and found no careers page on it

The middle bucket is a corpus problem. The other 1,456 are companies we HAVE A
NAME FOR and cannot find a board for — and for those, `src.slugs.guess` is the
method that bypasses the careers page entirely. It runs against GREENHOUSE ONLY,
and its docstring gives two reasons:

    "Lever cannot be guessed at all (a wrong slug returns 200 with an empty
     array — T3.3's trap), and guessing Ashby means paying its ~151s fixed
     latency per candidate."

THE SECOND REASON IS STALE. `.github/workflows/nightly.yml` already records the
re-measurement — "Ashby now answers in ~2s" — so the constraint that shaped
`guess` has not held for some time. This file asks whether the decision should
change with it, and refuses to assume the answer.

Run: .venv/bin/python learning-tests/ashby_guess_live.py [sample_size]

KILL CRITERION: under 2% of the sampled companies resolving to a VERIFIED Ashby
board and this is not worth a nightly minute — say so and leave `guess` alone.
2% of 1,456 is ~29 companies for a few minutes a night, which is the level where
it stops paying. Setting the bar before the run is the point; a threshold chosen
afterwards is a threshold chosen to be cleared.

WHAT WAS MEASURED (2026-08-02):

  MECHANICS — both halves of the method exist, and neither was obvious:

  A. A WRONG SLUG 404s, in 9 bytes and ~1.6s. So the T3.3 Lever trap does NOT
     apply to Ashby: existence is decidable. `api.ashbyhq.com/posting-api/
     job-board/<slug>` returned 200/2.0MB for ramp and 1password, 404/"Not
     Found" for a nonsense slug. Misses are nearly free; only hits cost.

  B. THE API DOES NOT NAME THE COMPANY — no organizationName, no company field,
     nothing but the slug echoed back inside jobUrl. So the API alone cannot
     answer the question `states_company` exists to ask, and a guess verified by
     existence alone would publish some other Valon's roles under ours. The
     BOARD PAGE does state it: jobs.ashbyhq.com/<slug> carries "<Name> Jobs" in
     its <title> ("Ramp Jobs", "1Password Jobs"), and an unknown slug renders a
     bare "Jobs" with a 200. That title is Ashby's `board_name`, and it is what
     makes this method safe rather than merely possible.

  RESULT — 21 of 120 sampled companies resolved to a VERIFIED Ashby board.
  17.5%, nearly nine times the kill criterion, at 1.1s per company. Projected
  over the 1,456 guessable: ~254 companies, ~26 minutes. Slug resolution is
  incremental (it runs for names the corpus GAINED), so that is a one-time cost,
  not a nightly one.

  WHAT THE HIT LIST IS HIDING, and the reason the task below is not just "call
  guess twice". Six of the 21 are single generic words — Boom, Catch, Castle,
  Formal, Meter, Fathom — and `states_company` only asks whether the board's
  title CONTAINS the company's name. It cannot tell two companies apart that
  share one. This is not hypothetical here: the corpus's own YC URL for Castle
  is `/companies/castle-2`, because YC HAS TWO COMPANIES CALLED CASTLE, and the
  other one is at `/companies/castle`. So 17.5% is a CEILING, not a yield, and
  the difference between them is published roles under the wrong company's name
  — the exact failure `greenhouse/brave` is remembered for.

  WHAT WAS CHECKED AND FOUND ALREADY DONE: the YC payload src/yc.py fetches
  carries `website` for 99.4% of 6,112 companies, and the obvious idea was that
  it was being discarded. It is not — 1,024 of the corpus's 1,027 YC companies
  already carry their website. The 763 unresolved YC companies fail with a
  website in hand: 405 have no careers page we can find, 355 have one that links
  no board. Which is precisely the population guessing exists to serve, and is
  why this method fits them rather than more website discovery.

  The `no-website` bucket is a different problem and this does not touch it: 650
  of its 740 are SEC Form D filings, which state a company name and no domain.
"""
from __future__ import annotations

import json
import random
import re
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.net import get_bytes  # noqa: E402
from src.slugs import _GUESS_SUFFIXES, key, states_company  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

#: Existence. 404 on a wrong slug, 9 bytes — finding A.
EXISTS = "https://api.ashbyhq.com/posting-api/job-board/{slug}"
#: Identity. "<Name> Jobs" in the title — finding B.
BOARD = "https://jobs.ashbyhq.com/{slug}"

#: The two buckets this method can help. `no-website` is excluded on purpose:
#: those companies fail for a reason guessing does not touch, and folding them
#: into the denominator would understate the hit rate of the thing being tested.
GUESSABLE = ("no-board-link", "no-careers-page")

KILL = 0.02


def board_title(slug: str) -> str | None:
    """The company name Ashby's board page states, or None.

    A bare "Jobs" is Ashby answering 200 for a board that does not exist, which
    is why this returns None for it rather than the literal string: it is the
    same not-knowing as a 404, wearing a success code.
    """
    status, body = get_bytes(BOARD.format(slug=slug), timeout=30)
    if status != 200:
        return None
    found = re.search(r"<title>([^<]*)</title>", body.decode("utf-8", "replace"))
    title = found.group(1).strip() if found else ""
    return title if title and title.casefold() != "jobs" else None


def guess_ashby(name: str) -> tuple[str, str] | None:
    """An Ashby slug for this company, verified by the board's own name.

    Existence first, identity second, and in that order for cost: the 404 is
    9 bytes and settles most candidates, while the page fetch is only paid for
    slugs that turned out to exist.
    """
    for suffix in _GUESS_SUFFIXES:
        slug = key(name) + suffix
        status, _ = get_bytes(EXISTS.format(slug=slug), timeout=30)
        if status != 200:
            continue
        title = board_title(slug)
        if title and states_company(title, name):
            return slug, title
        if title:
            return None  # a real board, someone else's name — the failure that matters
    return None


def main() -> None:
    size = int(sys.argv[1]) if len(sys.argv) > 1 else 120

    unresolved = json.loads((ROOT / "data" / "unresolved.json").read_text())
    reasons = Counter(unresolved.values())
    print("the 2,201, by reason:")
    for reason, n in reasons.most_common(4):
        print(f"  {n:>6}  {reason}")

    pool = [n for n, r in unresolved.items() if r in GUESSABLE]
    print(f"\nguessable population: {len(pool)}  (excludes no-website: "
          f"{reasons.get('no-website', 0)}, which guessing cannot help)")

    # Seeded, so a re-run measures the same companies and two runs are comparable.
    random.seed(11)
    sample = random.sample(pool, min(size, len(pool)))
    print(f"sampling {len(sample)}\n")

    started = time.time()
    with ThreadPoolExecutor(max_workers=8) as pool_exec:
        found = list(pool_exec.map(guess_ashby, sample))
    elapsed = time.time() - started

    hits = [(n, s, t) for n, r in zip(sample, found, strict=True) if r for s, t in [r]]
    rate = len(hits) / len(sample)

    print(f"RESOLVED {len(hits)}/{len(sample)} = {rate:.1%}   ({elapsed:.0f}s, "
          f"{elapsed / len(sample):.1f}s per company)")
    for name, slug, title in hits[:25]:
        print(f"  {name:<34} -> ashby/{slug:<24} ({title})")

    projected = int(rate * len(pool))
    print(f"\nprojected over the whole guessable population: ~{projected} companies")
    print(f"projected nightly cost: ~{elapsed / len(sample) * len(pool) / 60:.0f} "
          f"minutes at this concurrency (nightly is 11m26s today)")

    verdict = "DOES NOT FIRE — the method pays. Write the task." if rate >= KILL else \
              "FIRES — not worth a nightly minute. Leave guess() alone."
    print(f"\nKILL CRITERION ({KILL:.0%}): {verdict}")


if __name__ == "__main__":
    main()
