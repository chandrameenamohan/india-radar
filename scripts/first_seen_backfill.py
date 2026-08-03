#!/usr/bin/env python3
"""The one-time backfill of data/first-seen.json — T15.2. Run by hand, once.

**Nothing automatic may ever call this.** `.github/workflows/nightly.yml` checks
out at depth 1, so there is no history in CI to read: a nightly built on `git
show` works perfectly on a laptop and produces an empty artifact at midnight.
The nightly runs `python -m src.firstseen`, which reads only the committed
artifact and today's two data files. tests/test_nightly.py holds that boundary.

The backfill is that same function folded over the published history: every
commit that ever touched data/companies.json, oldest first, with the
build-report.json as it stood at that commit. So this script contains no rule of
its own — it contains a `git show` and a loop, and every judgement about what
counts as new is `src.firstseen.advance`'s.

**History order is ancestry, not the stamped dates, and they disagree.** Three
builds were made on a branch and merged after a nightly that carried a later
snapshot date (fc82aee is stamped 2026-07-29 and lands after the 07-30 refresh).
Ancestry is the order the site actually published in, so it is the order the
fold follows; the date each role is dated with is the one its own build stamped,
because that is the day the board was read.

    python3 scripts/first_seen_backfill.py [--write]

Without --write it prints the fold and touches nothing.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.firstseen import ARTIFACT, advance, write  # noqa: E402

DATA = "data/companies.json"
REPORT = "data/build-report.json"


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True
    ).stdout


def at(rev: str, path: str) -> dict[str, Any]:
    doc: dict[str, Any] = json.loads(git("show", f"{rev}:{path}"))
    return doc


def main(argv: list[str]) -> None:
    revs = git("rev-list", "--reverse", "HEAD", "--", DATA).split()
    art: dict[str, Any] | None = None
    for rev in revs:
        published = at(rev, DATA)
        art = advance(art, published, at(rev, REPORT))
        day = art["dates"].get(art["snapshot"], {})
        roles = sum(len(c.get("roles") or ()) for c in published["companies"])
        subject = git("log", "-1", "--format=%s", rev).strip()[:44]
        print(
            f"{rev[:7]}  {published['snapshot']}  {roles:>5} roles  "
            f"+{len(day.get('confirmed', ())):>4} confirmed  "
            f"+{len(day.get('unconfirmed', ())):>5} unconfirmed  {subject}"
        )
    if art is None:
        raise SystemExit(f"no commit in this history touches {DATA}")
    total = sum(len(u) for d in art["dates"].values() for u in d.values())
    conf = sum(len(d.get("confirmed", ())) for d in art["dates"].values())
    print(f"\n{total} role URLs dated, {conf} of which the both-sides rule would confirm")
    # THE BACKFILL CONFIRMS NOTHING, and the run above is the argument for it.
    # 1,604 roles land "confirmed" on 2026-07-31 — the night the radar widened
    # from India to fifteen countries (T8.4, built on a branch and merged in
    # between). Every one of those roles was open the day before; the build was
    # not looking at its country yet. A change in what the build LOOKS FOR is
    # indistinguishable, inside the artifact, from a company opening a job, and
    # this history contains two of them (T8.4 and T12.1's 135 new boards).
    #
    # So history gives dates, which are facts about us and always true, and
    # gives no badges. Confirmation starts with the first nightly after this
    # lands: one build definition, two consecutive observations, which is the
    # only shape the both-sides rule was ever measured against.
    for day in art["dates"].values():
        day["unconfirmed"] = sorted(day["unconfirmed"] + day["confirmed"])
        day["confirmed"] = []
    print(f"{total} unconfirmed after demotion — a backfill dates, it does not badge")
    if "--write" in argv:
        write(ARTIFACT, art)
        print(f"wrote {ARTIFACT}")
    else:
        print(f"dry run — pass --write to emit {ARTIFACT}")


if __name__ == "__main__":
    main(sys.argv[1:])
