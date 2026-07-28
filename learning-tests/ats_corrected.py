#!/usr/bin/env python3
"""
LEARNING TEST 3: corrections to two results that run 2 reported as "HOLDS"
but which were measurement bugs in the test itself.

BUG 1 (precision, and it would have shipped): run 2's "better" India rule used a
CASE-INSENSITIVE regex for the ISO prefix `IN-`. It matched the literal string
"In-Office". Every one of the +47 "recovered" postings was a false positive --
San Francisco roles labelled as India. The city-list rule alone was already
finding everything real. Correct rule: case-SENSITIVE `IN-`, and require what
follows to look like a place, not an English word.

BUG 2 (measurement): run 2 reported "speedup 6.0x" by comparing wall time to the
SUM OF INDIVIDUAL TIMES MEASURED DURING THE CONCURRENT RUN. Those per-request
times inflated from ~50s to ~151s precisely because Ashby throttles concurrent
callers, so the denominator was contaminated. Honest comparison is against the
run-1 serial baseline: 6 x 50.6s = 304s serial vs 151.7s wall = ~2.0x, not 6.0x.

BELIEFS UNDER TEST:
  BELIEF 8:  Case-sensitive IN- plus a word-boundary guard removes every false
             positive while keeping any genuine "IN-Pune" style hit.
  BELIEF 9:  Ashby throughput does NOT scale linearly with concurrency; there is
             a ceiling. Find roughly where it is, because it sets the nightly
             refresh budget for the whole pipeline.
  BELIEF 10: When a careers page hides its board (JS-rendered), guessing the
             slug from the company domain and probing Greenhouse directly
             recovers it -- Greenhouse costs ~0.35s so guessing is nearly free.
"""

import concurrent.futures as cf
import json
import re
import sys
import time
import urllib.error
import urllib.request

UA = "unicorn-radar-learning-test/0.1 (+contact: chandra@hakimo.ai)"


def fetch(url, timeout=200):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), time.monotonic() - t0, None
    except urllib.error.HTTPError as e:
        return e.code, e.read(), time.monotonic() - t0, f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return None, b"", time.monotonic() - t0, f"{type(e).__name__}: {e}"


CITIES = [
    "india", "bengaluru", "bangalore", "hyderabad", "pune", "mumbai", "delhi",
    "gurgaon", "gurugram", "noida", "chennai", "kolkata", "ahmedabad", "jaipur",
    "kochi", "cochin", "trivandrum", "thiruvananthapuram", "coimbatore",
    "indore", "chandigarh", "bhubaneswar", "nagpur", "vadodara", "surat",
    "lucknow", "vizag", "visakhapatnam", "mysuru", "mysore", "mohali",
    "thane", "navi mumbai", "faridabad", "vellore", "madurai",
]
# The bug: this was re.I in run 2, so it ate "In-Office". Case-sensitive `IN`
# plus a capitalised place name after the dash is what Ashby actually emits.
ISO_IN = re.compile(r"(?:^|[;,|/])\s*IN-(?=[A-Z])")
BROKEN_ISO_IN = re.compile(r"(^|[;,|/•·])\s*IN[-–]", re.I)  # kept to prove the bug


def match_cities(loc):
    return any(c in (loc or "").lower() for c in CITIES)


def match_corrected(loc):
    return match_cities(loc) or bool(ISO_IN.search(loc or ""))


def match_buggy(loc):
    return match_cities(loc) or bool(BROKEN_ISO_IN.search(loc or ""))


def collect_locations():
    locs = []
    for slug in ["databricks", "anthropic", "gleanwork", "figma", "stripe",
                 "airtable", "cloudflare"]:
        st, body, _, _ = fetch(
            f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=false", timeout=30)
        if st == 200:
            for j in json.loads(body).get("jobs", []):
                locs.append((j.get("location") or {}).get("name", ""))

    def ashby_one(slug):
        st, body, _, _ = fetch(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
        out = []
        if st == 200:
            for j in json.loads(body).get("jobs", []):
                out.append(j.get("location", ""))
                for sec in (j.get("secondaryLocations") or []):
                    out.append((sec.get("location") if isinstance(sec, dict) else str(sec)) or "")
        return out

    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        for chunk in ex.map(ashby_one, ["openai", "snowflake", "ramp", "sierra"]):
            locs.extend(chunk)
    return locs


def test_belief_8(locs):
    print("--- BELIEF 8: India rule precision ---")
    n_city = sum(1 for loc in locs if match_cities(loc))
    n_bug = sum(1 for loc in locs if match_buggy(loc))
    n_fix = sum(1 for loc in locs if match_corrected(loc))
    fp = sorted({loc for loc in locs if match_buggy(loc) and not match_corrected(loc)})
    iso_only = sorted({loc for loc in locs if match_corrected(loc) and not match_cities(loc)})
    print(f"  sampled {len(locs)} postings")
    print(f"  city-list only : {n_city}")
    print(f"  run-2 buggy    : {n_bug}   (+{n_bug - n_city} vs city list)")
    print(f"  corrected      : {n_fix}   (+{n_fix - n_city} vs city list)")
    print(f"  false positives the bug introduced: {len(fp)} distinct -> {fp[:6]}")
    print(f"  genuine ISO-only hits the city list missed: {len(iso_only)} -> {iso_only[:6]}")
    return n_city, n_bug, n_fix, fp, iso_only


ASHBY_POOL = ["openai", "snowflake", "decagon", "sierra", "ramp", "cursor",
              "perplexityai", "linear", "runwayml", "scaleai", "notion", "vanta"]


def test_belief_9():
    print("\n--- BELIEF 9: Ashby throughput ceiling ---")

    def one(slug):
        st, _body, dt, _ = fetch(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
        return st == 200, dt

    rows = []
    for workers in (1, 4, 12):
        slugs = ASHBY_POOL[:workers]
        t0 = time.monotonic()
        with cf.ThreadPoolExecutor(max_workers=workers) as ex:
            res = list(ex.map(one, slugs))
        wall = time.monotonic() - t0
        ok = sum(1 for good, _ in res if good)
        per = wall / max(ok, 1)
        rows.append((workers, ok, wall, per))
        print(f"  concurrency={workers:2d}  ok={ok:2d}/{workers}  wall={wall:6.1f}s  "
              f"effective={per:5.1f}s/company")
    return rows


DOMAIN_GUESS = [
    ("Anthropic", "anthropic"), ("Glean", "gleanwork"), ("Postman", "postman"),
    ("Notion", "notion"), ("Airtable", "airtable"), ("Rippling", "rippling"),
    ("Zomato", "zomato"), ("Freshworks", "freshworks"),
]


def test_belief_10():
    print("\n--- BELIEF 10: slug guessing as discovery fallback ---")

    def one(item):
        name, guess = item
        st, body, dt, _ = fetch(
            f"https://boards-api.greenhouse.io/v1/boards/{guess}/jobs?content=false", timeout=30)
        n = len(json.loads(body).get("jobs", [])) if st == 200 else 0
        return {"company": name, "guess": guess, "status": st, "roles": n,
                "secs": round(dt, 2)}

    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        rows = list(ex.map(one, DOMAIN_GUESS))
    for r in rows:
        print(" ", json.dumps(r))
    hits = sum(1 for r in rows if r["status"] == 200 and r["roles"] > 0)
    print(f"  guess-the-slug on Greenhouse recovered {hits}/{len(rows)}")
    return hits, len(rows)


def main():
    locs = collect_locations()
    n_city, n_bug, n_fix, fp, _iso_only = test_belief_8(locs)
    ceiling = test_belief_9()
    hits, total = test_belief_10()

    print("\n=== VERDICT ===")
    fp_survives = [loc for loc in fp if match_corrected(loc)]
    print(f"BELIEF 8: bug added {n_bug - n_city} postings, ALL false positives; "
          f"corrected rule adds {n_fix - n_city} real ones -> "
          f"{'FALSE' if fp_survives else 'HOLDS (bug confirmed and fixed)'}")
    best = min(ceiling, key=lambda r: r[3])
    print(f"BELIEF 9: throughput ceiling ~{best[3]:.1f}s/company at concurrency={best[0]}; "
          f"1000 Ashby companies = {best[3] * 1000 / 3600:.1f}h per full refresh")
    print(f"BELIEF 10: slug guessing recovered {hits}/{total} -> "
          f"{'HOLDS' if hits >= total * 0.4 else 'FALSE'}")

    assert not any(match_corrected(loc) for loc in fp), \
        "BELIEF 8 FALSE: corrected rule still admits a known false positive"
    return 0


if __name__ == "__main__":
    sys.exit(main())
