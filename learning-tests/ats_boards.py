#!/usr/bin/env python3
"""
LEARNING TEST: public ATS job-board APIs (Greenhouse / Lever / Ashby).

This is now the PRIMARY pipeline: an open India job posting is direct evidence of
India presence, which is what a job seeker actually needs. MCA is enrichment.

FINDINGS (updated after each real run -- see bottom of file for the verdict):
  BELIEF 1: All three expose a public, unauthenticated JSON endpoint.
  BELIEF 2: Location is free text, not a structured country code, so India
            detection must be string matching over city names + "India".
  BELIEF 3: A single unauthenticated request per company is enough to get every
            open role with its location (no pagination).
  BELIEF 4: No API key, no rate-limit error at a handful of sequential requests.
"""

import json
import sys
import time
import urllib.error
import urllib.request

UA = "unicorn-radar-learning-test/0.1 (+contact: chandra@hakimo.ai)"

# Slugs observed on the reference site (unicorn-radar) or widely known.
GREENHOUSE = ["databricks", "anthropic", "gleanwork", "togetherai", "figma"]
LEVER = ["netflix", "eventbrite", "shopify", "kayak", "voleon"]
ASHBY = ["openai", "snowflake", "decagon", "sierra", "ramp"]

# India markers to test BELIEF 2. Deliberately includes cities, because plenty of
# postings say "Bengaluru" with no country suffix at all.
INDIA_MARKERS = [
    "india", "bengaluru", "bangalore", "hyderabad", "pune", "mumbai", "delhi",
    "gurgaon", "gurugram", "noida", "chennai", "kolkata", "ahmedabad", "jaipur",
]


def fetch(url, timeout=25):
    """Return (status, body_bytes, elapsed_s, error_str)."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), time.monotonic() - t0, None
    except urllib.error.HTTPError as e:
        return e.code, e.read(), time.monotonic() - t0, f"HTTPError {e.code}"
    except Exception as e:  # noqa: BLE001 -- learning test, log whatever happens
        return None, b"", time.monotonic() - t0, f"{type(e).__name__}: {e}"


def is_india(location):
    lo = (location or "").lower()
    return any(m in lo for m in INDIA_MARKERS)


def probe_greenhouse(slug):
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=false"
    status, body, dt, err = fetch(url)
    if err or status != 200:
        return {"ats": "greenhouse", "slug": slug, "ok": False, "status": status,
                "err": err, "secs": round(dt, 2)}
    d = json.loads(body)
    jobs = d.get("jobs", [])
    locs = [(j.get("location") or {}).get("name", "") for j in jobs]
    return {
        "ats": "greenhouse", "slug": slug, "ok": True, "status": status,
        "secs": round(dt, 2), "total_roles": len(jobs),
        "meta_total": d.get("meta", {}).get("total"),
        "india_roles": sum(1 for loc in locs if is_india(loc)),
        "sample_india": [loc for loc in locs if is_india(loc)][:3],
        "sample_any": locs[:3],
        "job_keys": sorted(jobs[0].keys()) if jobs else [],
    }


def probe_lever(slug):
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    status, body, dt, err = fetch(url)
    if err or status != 200:
        return {"ats": "lever", "slug": slug, "ok": False, "status": status,
                "err": err, "secs": round(dt, 2)}
    jobs = json.loads(body)
    locs = [(j.get("categories") or {}).get("location", "") for j in jobs]
    return {
        "ats": "lever", "slug": slug, "ok": True, "status": status,
        "secs": round(dt, 2), "total_roles": len(jobs), "meta_total": None,
        "india_roles": sum(1 for loc in locs if is_india(loc)),
        "sample_india": [loc for loc in locs if is_india(loc)][:3],
        "sample_any": locs[:3],
        "job_keys": sorted(jobs[0].keys()) if jobs else [],
    }


def probe_ashby(slug):
    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
    status, body, dt, err = fetch(url)
    if err or status != 200:
        return {"ats": "ashby", "slug": slug, "ok": False, "status": status,
                "err": err, "secs": round(dt, 2)}
    d = json.loads(body)
    jobs = d.get("jobs", [])
    locs = [j.get("location", "") for j in jobs]
    return {
        "ats": "ashby", "slug": slug, "ok": True, "status": status,
        "secs": round(dt, 2), "total_roles": len(jobs), "meta_total": None,
        "india_roles": sum(1 for loc in locs if is_india(loc)),
        "sample_india": [loc for loc in locs if is_india(loc)][:3],
        "sample_any": locs[:3],
        "job_keys": sorted(jobs[0].keys()) if jobs else [],
    }


def main():
    results = []
    for fn, slugs in ((probe_greenhouse, GREENHOUSE),
                      (probe_lever, LEVER),
                      (probe_ashby, ASHBY)):
        for s in slugs:
            r = fn(s)
            results.append(r)
            print(json.dumps(r), flush=True)

    ok = [r for r in results if r.get("ok")]
    print("\n=== SUMMARY ===")
    for ats in ("greenhouse", "lever", "ashby"):
        sub = [r for r in results if r["ats"] == ats]
        good = [r for r in sub if r.get("ok")]
        print(f"{ats:11s} {len(good)}/{len(sub)} slugs OK  "
              f"roles={sum(r['total_roles'] for r in good)}  "
              f"india={sum(r['india_roles'] for r in good)}  "
              f"median_secs={sorted(r['secs'] for r in good)[len(good)//2] if good else '-'}")

    # BELIEF 1: every provider answers unauthenticated for at least one slug.
    for ats in ("greenhouse", "lever", "ashby"):
        assert any(r.get("ok") for r in results if r["ats"] == ats), \
            f"BELIEF 1 FALSE: no {ats} slug returned 200 unauthenticated"
    # BELIEF 2: India roles are findable by string match somewhere in the sample.
    assert sum(r["india_roles"] for r in ok) > 0, \
        "BELIEF 2 FALSE: string matching found zero India roles across all boards"
    # BELIEF 3: single request returns the full set (Greenhouse meta.total agrees).
    for r in ok:
        if r["ats"] == "greenhouse" and r["meta_total"] is not None:
            assert r["meta_total"] == r["total_roles"], (
                f"BELIEF 3 FALSE: {r['slug']} meta.total={r['meta_total']} "
                f"!= {r['total_roles']} returned")
    # BELIEF 4: no 429s.
    assert not any(r.get("status") == 429 for r in results), \
        "BELIEF 4 FALSE: got a 429 rate-limit at low request volume"
    print("\nAll asserted beliefs held.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
