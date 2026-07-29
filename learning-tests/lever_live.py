"""T3.3 — what Lever actually answers, measured before writing the probe.

FINDINGS §1 measured Lever once, a year of nobody's engineering ago: 2/5 slugs
OK at ~1.1s, and the two that answered 200 returned zero postings. That last
observation is the whole task — a wrong slug returning 200-with-empty-array is
indistinguishable from a company with no open roles. T3.2 found Ashby's headline
number stale by two orders of magnitude, so nothing here is inherited.

Answers wanted:
  1. Does a nonsense slug still return 200 with an empty array, or a 404?
  2. What does a real board return, and how long does it take?
  3. Where does a posting state its location, and can one posting hold several?
  4. How many of our 51 real slugs answer at all?
  5. T3.3's integration check — the DoD's own, against the live API.

Run: .venv/bin/python learning-tests/lever_live.py
"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from time import monotonic

sys.path.insert(0, ".")
from src.india import is_india  # noqa: E402
from src.net import get  # noqa: E402

API = "https://api.lever.co/v0/postings/{slug}?mode=json"

REAL = ["mindtickle", "tala", "matillion", "immuta", "moonpay"]
NONSENSE = ["no-such-company-india-radar-xyz", "zzzz-not-a-board-99"]


def timed(slug: str) -> tuple[str, int, float, str]:
    start = monotonic()
    status, body = get(API.format(slug=slug), 60)
    return slug, status, monotonic() - start, body


def summarise(slug: str, status: int, secs: float, body: str) -> None:
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        print(f"  {slug:36} {status}  {secs:5.1f}s  NOT JSON: {body[:70]!r}")
        return
    kind = type(parsed).__name__
    count = len(parsed) if isinstance(parsed, list) else "-"
    print(f"  {slug:36} {status}  {secs:5.1f}s  {kind}, {count} postings")


print("== 1. nonsense slugs — is the trap still real? ==")
for slug in NONSENSE:
    summarise(*timed(slug))

print("\n== 2. real slugs from data/slugs.json ==")
for slug in REAL:
    summarise(*timed(slug))

print("\n== 3. posting shape ==")
_, status, _, body = timed("mindtickle")
postings = json.loads(body)
if postings:
    print(json.dumps({k: v for k, v in postings[0].items() if k != "description"}, indent=2)[:1400])
    keys: dict[str, int] = {}
    multi = 0
    for post in postings:
        for key in post.get("categories", {}):
            keys[key] = keys.get(key, 0) + 1
        if len(post.get("categories", {}).get("allLocations") or []) > 1:
            multi += 1
    print(f"\n  categories keys across {len(postings)} postings: {keys}")
    print(f"  postings with >1 allLocations: {multi}")

print("\n== 4. all 51 corpus slugs, concurrent ==")
slugs = sorted(
    s["slug"] for s in json.load(open("data/slugs.json")).values() if s["ats"] == "lever"
)
start = monotonic()
with ThreadPoolExecutor(max_workers=12) as pool:
    results = list(pool.map(timed, slugs))
wall = monotonic() - start

empty = nonempty = broken = 0
for slug, status, _secs, body in results:
    try:
        posts = json.loads(body)
    except json.JSONDecodeError:
        broken += 1
        print(f"  {slug:30} {status} NOT JSON {body[:50]!r}")
        continue
    if not isinstance(posts, list):
        broken += 1
        print(f"  {slug:30} {status} {type(posts).__name__}: {body[:80]!r}")
    elif posts:
        nonempty += 1
    else:
        empty += 1
        print(f"  {slug:30} {status} EMPTY ARRAY")

print(f"\n  {len(slugs)} slugs in {wall:.1f}s wall at 12 workers")
print(f"  {nonempty} with postings, {empty} empty (unverifiable), {broken} not a JSON array")
print(f"  statuses: {sorted({r[1] for r in results})}")
print(f"  slowest single call: {max(r[2] for r in results):.1f}s")

print("\n== 5. T3.3's integration check, against the live API ==")
# The DoD asks for "a known-bad slug -> empty-board-unverified", and a known-bad
# slug does not do that any more: all ten tried above 404. What the check is FOR
# — a 200-with-empty-array must never become an honest zero — is asserted here
# against boards that really do answer that way today, and the 404 case is
# pinned beside it so the divergence stays visible rather than assumed.
from src.lever import locations, probe  # noqa: E402
from src.outcomes import Outcome  # noqa: E402

for slug in ["ramenvr", "tesorio", "trela"]:
    outcome = probe(slug)
    print(f"  {slug:32} -> {outcome}")
    assert outcome is Outcome.EMPTY_BOARD_UNVERIFIED, f"{slug} must not become a zero"

for slug in NONSENSE:
    outcome = probe(slug)
    print(f"  {slug:32} -> {outcome}")
    assert outcome is Outcome.SLUG_UNRESOLVED, f"{slug} is a wrong slug, not an empty board"

roles = probe("mindtickle")
assert isinstance(roles, list) and roles, "a populated board must come back as postings"
india = [r for r in roles if any(is_india(p) for p in locations(r))]
print(f"  {'mindtickle':32} -> {len(roles)} postings, {len(india)} in India")
assert india, "MindTickle is an India-headquartered company; zero here means the unwrap is wrong"
print("\nOK — every assertion held.")
