#!/usr/bin/env python3
"""
LEARNING TEST 5: the ONE usable MCA dataset, and whether we can pull the slice
we need out of it.

CORRECTS LEARNING TEST 4. That test concluded "MCA bulk access is blocked". That
was wrong, and wrong in two separate ways:
  - data.gov.in returns 200 to plain curl. The 403s came from headless Chromium
    (Akamai fingerprints TLS/bot signals, not just User-Agent) and from WebFetch.
    Only mca.gov.in itself is genuinely 403 to us.
  - api.data.gov.in works with data.gov.in's PUBLISHED SAMPLE KEY, no
    registration needed to evaluate.

CORRECTS THE CHALLENGE-STEP WORRY TOO, but only halfway. The staleness fear was
justified for the OBVIOUS source: all 37 state-wise "Company Master Data of
<State>" datasets are capped at "upto 31st March 2021" -- 5+ years stale today.
Building on those would have produced a site blind to every company incorporated
since 2021, which is exactly the cohort that matters. They are a trap.

The exception, and the only reason MCA enrichment is viable at all:
  Title : "Registrars of Companies (RoC)-wise Company Master Data"
  Index : 4dbe5667-7b6b-41d7-82af-211562424d9a
  Rows  : 3,674,314 -- company level, not aggregates
  Fields: CIN, CompanyName, CompanySubCategory, CompanyRegistrationdate_date,
          Registered_Office_Address, CompanyStatus, CompanyIndian/Foreign
          Company, nic_code, CompanyIndustrialClassification
  Updated: 2026-07-22 (six days before this test ran)

BELIEFS UNDER TEST -- and what the run actually returned:

  BELIEF 11: The RoC dataset is genuinely current.
             -> HOLDS. Newest registration date observed: 2026-03-31, sampled
                across five offsets spanning the whole table. ~4 months' lag,
                not 5 years. This is the dataset the project should use.

  BELIEF 12: We can filter server-side to CompanySubCategory="Subsidiary of
             Foreign Company", yielding a few tens of thousands of rows.
             -> UNRESOLVED, leaning FALSE. That filter returned total=0 while
                filters[CompanyStatus]=Active returned 2,597,823 and
                filters[CompanyROCcode]=ROC Delhi returned 561,757. So filtering
                WORKS; that specific value appears absent. BUT by the time I
                tried to enumerate the real CompanySubCategory values, the
                sample key had throttled to timeouts, and a throttled call is
                indistinguishable from a genuine zero. Treat the 0 as UNPROVEN.
                Resolve with a registered key before any spec depends on it.

  BELIEF 13: The API paginates far enough to retrieve the whole slice.
             -> FALSE on the sample key. limit=100, limit=1000 and limit=5000 ALL
                returned exactly 10 rows. The sample key is hard-capped at 10
                rows/call, which is 367,431 calls for a full scan -- not viable.
                Deep offset (3,000,000) does work, so pagination itself is fine;
                the page size is the wall. A free registered key is documented to
                lift this, but that is UNVERIFIED and is the next thing to test.

NET: MCA enrichment is viable but NOT free of unknowns. Two specific things must
be settled with a registered API key before the enrichment bead is scheduled:
the real page-size cap, and the true CompanySubCategory vocabulary.
"""

import json
import sys
import time
import urllib.parse
import urllib.request

KEY = "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b"  # published sample key
INDEX = "4dbe5667-7b6b-41d7-82af-211562424d9a"
BASE = f"https://api.data.gov.in/resource/{INDEX}"
UA = "unicorn-radar-learning-test/0.1"


def api(**params):
    params.setdefault("api-key", KEY)
    params.setdefault("format", "json")
    url = f"{BASE}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    t0 = time.monotonic()
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read()), time.monotonic() - t0


def test_belief_11():
    print("--- BELIEF 11: is the RoC dataset actually current? ---")
    d, dt = api(limit=1)
    total = d.get("total")
    print(f"  total rows: {total:,}  ({dt:.1f}s)")
    # Sample across the table and look at the newest registration dates seen.
    newest = []
    for off in (0, 500_000, 1_500_000, 3_000_000, 3_600_000):
        d, _ = api(limit=100, offset=off)
        dates = [r.get("CompanyRegistrationdate_date", "") for r in d.get("records", [])]
        dates = [x for x in dates if x and x[:2] == "20"]
        if dates:
            newest.append(max(dates))
        print(f"  offset {off:>9,}: max reg date in sample = {max(dates) if dates else '-'}")
    overall = max(newest) if newest else ""
    print(f"  newest registration date observed: {overall}")
    return total, overall


SUBCAT = "Subsidiary of Foreign Company"


def test_belief_12():
    print("\n--- BELIEF 12: can we filter to foreign subsidiaries? ---")
    out = {}
    for label, params in [
        ("subsidiary-of-foreign", {"filters[CompanySubCategory]": SUBCAT}),
        ("foreign-company-flag", {"filters[CompanyIndian/Foreign Company]": "Foreign"}),
    ]:
        try:
            d, dt = api(limit=3, **params)
            n = d.get("total")
            print(f"  {label:24s} total={n!s:>10}  ({dt:.1f}s)")
            for r in d.get("records", [])[:2]:
                print(f"      {r.get('CIN','')} | {r.get('CompanyName','')[:46]} | "
                      f"{r.get('CompanySubCategory','')} | {r.get('CompanyStatus','')}")
            out[label] = n
        except Exception as e:  # noqa: BLE001
            print(f"  {label:24s} FAILED: {type(e).__name__}: {e}")
            out[label] = None
    return out


def test_belief_13():
    print("\n--- BELIEF 13: pagination depth and page size ---")
    results = {}
    for lim in (100, 1000, 5000):
        try:
            d, dt = api(limit=lim, offset=0)
            got = len(d.get("records", []))
            print(f"  limit={lim:<5} -> returned {got:<5} rows in {dt:.1f}s")
            results[lim] = got
        except Exception as e:  # noqa: BLE001
            print(f"  limit={lim:<5} -> FAILED {type(e).__name__}: {e}")
            results[lim] = 0
    # Does a deep offset still work?
    try:
        d, dt = api(limit=5, offset=3_000_000)
        print(f"  deep offset 3,000,000 -> {len(d.get('records', []))} rows in {dt:.1f}s")
        results["deep"] = len(d.get("records", []))
    except Exception as e:  # noqa: BLE001
        print(f"  deep offset FAILED: {type(e).__name__}: {e}")
        results["deep"] = 0
    return results


def main():
    total, newest = test_belief_11()
    counts = test_belief_12()
    page = test_belief_13()

    print("\n=== VERDICT ===")
    fresh = newest >= "2024-01-01"
    print(f"BELIEF 11 (current): newest reg date {newest} -> "
          f"{'HOLDS' if fresh else 'FALSE -- dataset is stale after all'}")
    sub = counts.get("subsidiary-of-foreign")
    print(f"BELIEF 12 (filterable): subsidiary-of-foreign total={sub} -> "
          f"{'HOLDS' if sub else 'FALSE -- server-side filter unusable, must bulk-scan'}")
    best = max((k for k in page if isinstance(k, int) and page[k]), default=0)
    print(f"BELIEF 13 (paginates): best page size {best}, deep offset "
          f"{'ok' if page.get('deep') else 'FAILED'}")
    if best:
        print(f"  -> full 3.67M scan at {best}/call = {total // best:,} calls")
    return 0


if __name__ == "__main__":
    sys.exit(main())
