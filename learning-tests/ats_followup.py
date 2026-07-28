#!/usr/bin/env python3
"""
LEARNING TEST 2: the three things ats_boards.py exposed as unknown.

Run 1 produced these surprises, which this test exists to resolve:
  - Ashby took ~50s per request, and the time was FLAT regardless of payload
    size (114 jobs -> 50.68s, 750 jobs -> 50.96s). That is a fixed server-side
    delay, not bandwidth. Fatal if it is a GLOBAL rate limit; harmless if it is
    per-request and we can run requests concurrently.
  - Location strings are messier than assumed: Ashby emits "IN-Pune" (ISO
    prefix, no "India" substring), Greenhouse emits "Bengaluru, India; Mumbai,
    India" (two cities, one posting). A naive city list silently under-counts.
  - 3/5 guessed Lever slugs 404'd and 2 returned HTTP 200 with an EMPTY array.
    200-with-zero is indistinguishable from "company has no open roles" -- a
    silent failure mode that would quietly zero out rows in production.

BELIEFS UNDER TEST:
  BELIEF 5: Ashby's ~50s is per-request, so N concurrent requests still finish
            in roughly 50s total (pipeline stays feasible).
  BELIEF 6: An "IN-" prefix rule plus a wider city list materially increases
            India-role recall over the naive list used in run 1.
  BELIEF 7: The ATS slug for a company can be discovered automatically by
            fetching its careers page and regexing for board URLs -- so we do
            not have to hand-maintain thousands of slugs like the reference site.
"""

import concurrent.futures as cf
import json
import re
import sys
import time
import urllib.error
import urllib.request

UA = "unicorn-radar-learning-test/0.1 (+contact: chandra@hakimo.ai)"


def fetch(url, timeout=90):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), time.monotonic() - t0, None
    except urllib.error.HTTPError as e:
        return e.code, e.read(), time.monotonic() - t0, f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return None, b"", time.monotonic() - t0, f"{type(e).__name__}: {e}"


# --------------------------------------------------------------------------
# BELIEF 5: is Ashby's 50s per-request (parallelizable) or global (fatal)?
# --------------------------------------------------------------------------
ASHBY_SLUGS = ["openai", "snowflake", "decagon", "sierra", "ramp", "cursor"]


def test_ashby_concurrency():
    print("--- BELIEF 5: Ashby concurrency ---")

    def one(slug):
        st, body, dt, err = fetch(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
        n = len(json.loads(body).get("jobs", [])) if st == 200 else -1
        return {"slug": slug, "status": st, "secs": round(dt, 1), "jobs": n, "err": err}

    t0 = time.monotonic()
    with cf.ThreadPoolExecutor(max_workers=len(ASHBY_SLUGS)) as ex:
        rows = list(ex.map(one, ASHBY_SLUGS))
    wall = time.monotonic() - t0
    for r in rows:
        print(" ", json.dumps(r))
    serial_est = sum(r["secs"] for r in rows)
    print(f"  wall={wall:.1f}s  sum_of_individual={serial_est:.1f}s  "
          f"speedup={serial_est / wall:.1f}x")
    return wall, serial_est, rows


# --------------------------------------------------------------------------
# BELIEF 6: how much does a better India rule actually recover?
# --------------------------------------------------------------------------
NAIVE = ["india", "bengaluru", "bangalore", "hyderabad", "pune", "mumbai",
         "delhi", "gurgaon", "gurugram", "noida", "chennai", "kolkata",
         "ahmedabad", "jaipur"]

# Wider list: every metro/tier-2 city that shows up in tech postings.
CITIES = NAIVE + [
    "kochi", "cochin", "trivandrum", "thiruvananthapuram", "coimbatore",
    "indore", "chandigarh", "bhubaneswar", "nagpur", "vadodara", "surat",
    "lucknow", "vizag", "visakhapatnam", "mysuru", "mysore", "mohali",
    "thane", "navi mumbai", "faridabad", "goa", "vellore", "madurai",
]
# Structural rules that catch what city lists cannot.
IN_PREFIX = re.compile(r"(^|[;,|/•·])\s*IN[-–]", re.I)
IN_SUFFIX = re.compile(r",\s*IN\s*($|[;,|/])", re.I)


def match_naive(loc):
    return any(m in (loc or "").lower() for m in NAIVE)


def match_better(loc):
    lo = (loc or "").lower()
    if any(m in lo for m in CITIES):
        return True
    return bool(IN_PREFIX.search(loc or "") or IN_SUFFIX.search(loc or ""))


def collect_locations():
    """Pull locations from a mix of Greenhouse + Ashby boards."""
    locs = []
    for slug in ["databricks", "anthropic", "gleanwork", "figma", "stripe",
                 "airtable", "cloudflare"]:
        st, body, _, _ = fetch(
            f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=false")
        if st == 200:
            for j in json.loads(body).get("jobs", []):
                locs.append(("greenhouse", slug, (j.get("location") or {}).get("name", "")))

    def ashby_one(slug):
        st, body, _, _ = fetch(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
        out = []
        if st == 200:
            for j in json.loads(body).get("jobs", []):
                out.append(("ashby", slug, j.get("location", "")))
                for sec in (j.get("secondaryLocations") or []):
                    loc = sec.get("location") if isinstance(sec, dict) else str(sec)
                    out.append(("ashby-secondary", slug, loc or ""))
        return out

    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for chunk in ex.map(ashby_one, ["openai", "snowflake", "ramp", "sierra"]):
            locs.extend(chunk)
    return locs


def test_india_detection():
    print("\n--- BELIEF 6: India detection recall ---")
    locs = collect_locations()
    naive_hits = {loc for _, _, loc in locs if match_naive(loc)}
    better_hits = {loc for _, _, loc in locs if match_better(loc)}
    gained = better_hits - naive_hits
    n_naive = sum(1 for _, _, loc in locs if match_naive(loc))
    n_better = sum(1 for _, _, loc in locs if match_better(loc))
    print(f"  locations sampled: {len(locs)} ({len(set(loc for _,_,loc in locs))} distinct)")
    print(f"  naive rule:  {n_naive} postings")
    print(f"  better rule: {n_better} postings  (+{n_better - n_naive})")
    print(f"  newly caught distinct strings: {sorted(gained)[:15]}")
    multi = [loc for _, _, loc in locs
             if match_better(loc) and (";" in loc or "|" in loc or "•" in loc)]
    print(f"  multi-location strings among India hits: {len(multi)} e.g. {multi[:3]}")
    return n_naive, n_better, gained


# --------------------------------------------------------------------------
# BELIEF 7: can we auto-discover a company's ATS slug from its careers page?
# --------------------------------------------------------------------------
BOARD_RE = {
    "greenhouse": re.compile(
        r"(?:job-boards|boards)\.greenhouse\.io/(?:embed/job_board\?for=)?([a-z0-9_-]+)", re.I),
    "lever": re.compile(r"jobs\.(?:eu\.)?lever\.co/([a-z0-9_-]+)", re.I),
    "ashby": re.compile(r"jobs\.ashbyhq\.com/([a-z0-9_.-]+)", re.I),
}
# (company, url to try). Deliberately a mix of ATS vendors and page conventions.
CAREER_PAGES = [
    ("Anthropic", "https://www.anthropic.com/careers"),
    ("Figma", "https://www.figma.com/careers/"),
    ("Glean", "https://www.glean.com/careers"),
    ("Ramp", "https://ramp.com/careers"),
    ("Vercel", "https://vercel.com/careers"),
    ("Postman", "https://www.postman.com/company/careers/"),
    ("Razorpay", "https://razorpay.com/jobs/"),
]


def test_slug_discovery():
    print("\n--- BELIEF 7: ATS slug auto-discovery ---")

    def one(item):
        name, url = item
        st, body, dt, err = fetch(url, timeout=30)
        if st != 200:
            return {"company": name, "url": url, "status": st, "err": err, "found": None}
        html = body.decode("utf-8", "ignore")
        found = {}
        for ats, rx in BOARD_RE.items():
            m = rx.findall(html)
            if m:
                found[ats] = sorted(set(m))[:3]
        return {"company": name, "status": st, "secs": round(dt, 1), "found": found or None}

    with cf.ThreadPoolExecutor(max_workers=7) as ex:
        rows = list(ex.map(one, CAREER_PAGES))
    for r in rows:
        print(" ", json.dumps(r))
    hits = sum(1 for r in rows if r.get("found"))
    print(f"  discovered {hits}/{len(rows)} directly from the careers page")
    return hits, len(rows)


def main():
    wall, serial_est, ashby_rows = test_ashby_concurrency()
    n_naive, n_better, _gained = test_india_detection()
    hits, total = test_slug_discovery()

    print("\n=== VERDICT ===")
    ok_ashby = sum(1 for r in ashby_rows if r["status"] == 200)
    speedup = serial_est / wall if wall else 0
    print(f"BELIEF 5 (Ashby parallelizable): speedup {speedup:.1f}x over {ok_ashby} concurrent -> "
          f"{'HOLDS' if speedup > 2 else 'FALSE'}")
    print(f"BELIEF 6 (better India rule): {n_naive} -> {n_better} postings -> "
          f"{'HOLDS' if n_better > n_naive else 'FALSE (naive rule was already complete)'}")
    print(f"BELIEF 7 (slug auto-discovery): {hits}/{total} -> "
          f"{'HOLDS' if hits >= total * 0.5 else 'FALSE -- needs a fallback'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
