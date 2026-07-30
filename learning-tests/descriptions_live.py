#!/usr/bin/env python3
"""T8.1 (a, b) — does posting DESCRIPTION text cost extra calls, and what does it cost?

Feature 15 reads posting prose, and none of the three probes fetches prose today:
`greenhouse.API` pins `content=false` on purpose, and `ashby`/`lever` were written
against the fields the build needed. The question T8.1 exists to answer is whether
that prose is a flag on the call we already make or a second call per role — the
difference between a nightly that grows by a factor and one that grows by 4,442.

Run: .venv/bin/python learning-tests/descriptions_live.py

WHAT WAS MEASURED (2026-07-30, live boards):

  My assumption going in was that at least one provider would make descriptions a
  per-role fetch. WRONG on all three — nobody charges an extra call:

    Greenhouse  `?content=true` on the SAME jobs endpoint. Zero extra calls.
                databricks/803 roles: 0.69MB & 0.71s -> 9.40MB & 1.23s. The byte
                multiplier is 13.7x-35.3x across three boards (it rises as the board
                shrinks, because the non-description fields amortise worse); the
                latency multiplier is under 2x and sometimes under 1x, which is to
                say the extra megabytes are lost in the noise of the round trip.
    Ashby       descriptionHtml AND descriptionPlain ship unconditionally. There is
                no content=false. We have been paying for descriptions since T3.2
                and throwing them away.
    Lever       description/descriptionPlain/lists[].content/additional all ship
                unconditionally, same as Ashby.

  The Lever catch, which is not free: `descriptionPlain` is only the OPENING
  paragraphs. The requirements, the benefits and the legal boilerplate live in
  `lists[].content` and `additional` — and the legal boilerplate is exactly where a
  "we cannot sponsor" sentence sits. A descriptionPlain-only reader never sees
  **62-77%** of the posting (measured on pigment, kpler, patsnap below).

CONSEQUENCE FOR T8.4: description text is a payload cost, never a call-count cost.
"""
from __future__ import annotations

import html
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.net import get  # noqa: E402

GH = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content={content}"
ASHBY = "https://api.ashbyhq.com/posting-api/job-board/{slug}"
LEVER = "https://api.lever.co/v0/postings/{slug}?mode=json"

# Boards picked for size spread, all of them already in data/slugs.json.
GH_SLUGS = ["databricks", "sumup", "helsing"]
ASHBY_SLUGS = ["ramp", "pennylane", "deepl"]
LEVER_SLUGS = ["pigment", "kpler", "patsnap"]

TAG = re.compile(r"<[^>]+>")


def timed(url: str, timeout: int = 240) -> tuple[int, str, int, float]:
    """(status, body, bytes, seconds) — the four numbers every row below needs."""
    start = time.time()
    status, body = get(url, timeout)
    return status, body, len(body.encode()), time.time() - start


def plain(markup: str) -> str:
    """Tags out, entities in. Greenhouse double-escapes: the JSON string holds
    `&lt;p&gt;`, so one unescape yields HTML and the second yields the text."""
    return TAG.sub(" ", html.unescape(markup or "")).strip()


def main() -> int:
    print("== Greenhouse: content=false (what we fetch today) vs content=true ==")
    print(f"  {'slug':14s} {'roles':>5s} {'false MB':>9s} {'false s':>8s} "
          f"{'true MB':>8s} {'true s':>7s} {'x bytes':>8s} {'chars/role':>11s}")
    for slug in GH_SLUGS:
        _, _, cheap_bytes, cheap_secs = timed(GH.format(slug=slug, content="false"))
        status, body, rich_bytes, rich_secs = timed(GH.format(slug=slug, content="true"))
        if status != 200:
            print(f"  {slug:14s} HTTP {status} — not measured")
            continue
        jobs = json.loads(body)["jobs"]
        described = [j for j in jobs if (j.get("content") or "").strip()]
        chars = sum(len(plain(j.get("content") or "")) for j in jobs) // max(len(jobs), 1)
        print(f"  {slug:14s} {len(jobs):5d} {cheap_bytes / 1e6:9.2f} {cheap_secs:8.2f} "
              f"{rich_bytes / 1e6:8.2f} {rich_secs:7.2f} {rich_bytes / cheap_bytes:7.1f}x "
              f"{chars:11d}   {len(described)}/{len(jobs)} non-empty")

    print("\n== Ashby: descriptions ship unconditionally — no way to decline ==")
    print(f"  {'slug':14s} {'roles':>5s} {'MB':>6s} {'s':>6s} {'Html':>6s} {'Plain':>6s} "
          f"{'chars/role':>11s}")
    for slug in ASHBY_SLUGS:
        status, body, nbytes, secs = timed(ASHBY.format(slug=slug))
        if status != 200:
            print(f"  {slug:14s} HTTP {status} — not measured")
            continue
        jobs = json.loads(body)["jobs"]
        has_html = sum(1 for j in jobs if (j.get("descriptionHtml") or "").strip())
        has_plain = sum(1 for j in jobs if (j.get("descriptionPlain") or "").strip())
        chars = sum(len(j.get("descriptionPlain") or "") for j in jobs) // max(len(jobs), 1)
        print(f"  {slug:14s} {len(jobs):5d} {nbytes / 1e6:6.2f} {secs:6.2f} "
              f"{has_html:6d} {has_plain:6d} {chars:11d}")

    print("\n== Lever: descriptionPlain is the OPENING only — the rest is elsewhere ==")
    print(f"  {'slug':14s} {'posts':>5s} {'MB':>6s} {'s':>6s} {'Plain':>7s} {'+lists':>7s} "
          f"{'+additional':>12s} {'% lost':>7s}")
    for slug in LEVER_SLUGS:
        status, body, nbytes, secs = timed(LEVER.format(slug=slug))
        if status != 200:
            print(f"  {slug:14s} HTTP {status} — not measured")
            continue
        posts = json.loads(body)
        opening = lists = extra = 0
        for post in posts:
            opening += len(post.get("descriptionPlain") or "")
            lists += sum(len(plain(x.get("content") or "")) for x in post.get("lists") or [])
            extra += len(post.get("additionalPlain") or "")
        whole = opening + lists + extra
        lost = 100 * (1 - opening / whole) if whole else 0.0
        n = max(len(posts), 1)
        print(f"  {slug:14s} {len(posts):5d} {nbytes / 1e6:6.2f} {secs:6.2f} {opening // n:7d} "
              f"{lists // n:7d} {extra // n:12d} {lost:6.1f}%")
    print("  (chars per posting. '% lost' = share of the posting a descriptionPlain-only")
    print("   reader never sees — and 'we cannot sponsor' lives in `additional`.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
