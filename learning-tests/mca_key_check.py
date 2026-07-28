#!/usr/bin/env python3
"""
Run this the moment you have a registered data.gov.in API key.

    python3 learning-tests/mca_key_check.py YOUR_KEY_HERE
    # or:  export DATA_GOV_IN_KEY=... && python3 learning-tests/mca_key_check.py

It answers the two questions left open in FINDINGS.md, which are the only things
blocking the MCA enrichment bead (SPEC.md feature 9):

  Q1. Does a registered key lift the 10-rows-per-call cap?
      The public sample key returns exactly 10 rows whether you ask for 100,
      1000 or 5000. At 10/call a full scan of the 3,674,314-row table needs
      367,431 calls, which is not viable. We need to know the real ceiling.

  Q2. What values does CompanySubCategory actually take?
      "Subsidiary of Foreign Company" returned total=0, while CompanyStatus=Active
      returned 2,597,823 -- so filtering works and that value looks absent. But
      the sample key throttled to timeouts before the vocabulary could be
      enumerated, and a THROTTLED CALL IS INDISTINGUISHABLE FROM A GENUINE ZERO.
      Until this runs green, treat that 0 as unproven.

  Q3. Is CompanyStateCode a REQUIRED filter?
      The resource metadata lists exactly one exposed field:
        field_exposed: [{'id': 'CompanyStateCode', 'mandatory': True}]
      If the API genuinely requires it, we cannot do one flat scan of the table
      and must pull in ~36 state-scoped chunks instead. That is not a problem --
      it shards naturally and matches the sharded GitHub Actions plan in SPEC.md
      feature 11 -- but it changes the pull strategy, so confirm before building.

Exit code is 0 if the questions got a clean answer, 1 if the key is rejected.
"""

import collections
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

INDEX = "4dbe5667-7b6b-41d7-82af-211562424d9a"  # RoC-wise Company Master Data
BASE = f"https://api.data.gov.in/resource/{INDEX}"
UA = "india-radar-key-check/0.1"


def api(key, **params):
    params.setdefault("api-key", key)
    params.setdefault("format", "json")
    url = f"{BASE}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read())


def q1_page_size(key):
    print("--- Q1: page-size cap ---")
    best = 0
    for lim in (10, 100, 1000, 5000, 10000):
        try:
            d = api(key, limit=lim, offset=0)
            got = len(d.get("records", []))
            best = max(best, got)
            flag = "" if got == lim else "  <-- CAPPED"
            print(f"  asked {lim:>6} -> got {got:>6}{flag}")
            if got < lim:
                break
        except urllib.error.HTTPError as e:
            print(f"  asked {lim:>6} -> HTTP {e.code} {e.read(200).decode('utf-8','ignore')[:80]}")
            break
        except Exception as e:  # noqa: BLE001
            print(f"  asked {lim:>6} -> {type(e).__name__}: {e}")
            break
    total = api(key, limit=1).get("total", 0)
    if best:
        print(f"  best page size: {best}  ->  full scan = {int(total) // best:,} calls")
    return best, total


def q2_subcategories(key, page):
    print("\n--- Q2: CompanySubCategory vocabulary ---")
    sub = collections.Counter()
    frn = collections.Counter()
    seen = 0
    # Sample across the whole table rather than the head, which is unrepresentative.
    for off in (0, 250_000, 750_000, 1_500_000, 2_500_000, 3_500_000):
        try:
            d = api(key, limit=min(page, 1000), offset=off)
        except Exception as e:  # noqa: BLE001
            print(f"  offset {off:,} failed: {type(e).__name__}")
            continue
        recs = d.get("records", [])
        seen += len(recs)
        for r in recs:
            sub[(r.get("CompanySubCategory") or "(empty)").strip()] += 1
            frn[(r.get("CompanyIndian/Foreign Company") or "(empty)").strip()] += 1
        time.sleep(0.5)

    print(f"  sampled {seen:,} rows")
    print("  CompanySubCategory values:")
    for k, v in sub.most_common(12):
        print(f"     {v:6,}  {k!r}")
    print("  CompanyIndian/Foreign Company values:")
    for k, v in frn.most_common(8):
        print(f"     {v:6,}  {k!r}")

    # Now confirm counts server-side for whichever values look foreign-related.
    print("\n  server-side totals for candidate filters:")
    candidates = [k for k in sub if "foreign" in k.lower() or "subsidiary" in k.lower()]
    candidates += [k for k in frn if k and k != "(empty)"]
    for val in dict.fromkeys(candidates):
        field = ("CompanySubCategory" if val in sub else "CompanyIndian/Foreign Company")
        try:
            d = api(key, limit=1, **{f"filters[{field}]": val})
            print(f"     {field}={val!r} -> total={d.get('total')}")
        except Exception as e:  # noqa: BLE001
            print(f"     {field}={val!r} -> {type(e).__name__}")
    return sub, frn


STATES = ["karnataka", "maharashtra", "delhi", "telangana", "tamil nadu"]


def q3_state_scoping(key):
    """Is CompanyStateCode actually mandatory, or merely 'exposed'?"""
    print("\n--- Q3: is CompanyStateCode a required filter? ---")
    try:
        unscoped = api(key, limit=5).get("total")
        print(f"  no state filter          -> total={unscoped}")
    except Exception as e:  # noqa: BLE001
        unscoped = None
        print(f"  no state filter          -> {type(e).__name__}: {e}")

    per_state = {}
    for st in STATES:
        try:
            d = api(key, limit=1, **{"filters[CompanyStateCode]": st})
            per_state[st] = d.get("total")
            print(f"  CompanyStateCode={st:<12} -> total={d.get('total')}")
        except Exception as e:  # noqa: BLE001
            per_state[st] = None
            print(f"  CompanyStateCode={st:<12} -> {type(e).__name__}")
        time.sleep(0.3)

    if unscoped and any(per_state.values()):
        print("  VERDICT: state filter is OPTIONAL -- a flat scan works, "
              "state-scoping is just a convenient way to shard.")
    elif any(per_state.values()):
        print("  VERDICT: state filter appears REQUIRED -- pull in ~36 "
              "state-scoped chunks, one shard per state.")
    else:
        print("  VERDICT: inconclusive -- neither form returned data.")
    return unscoped, per_state


def read_dotenv():
    """Tiny .env reader -- avoids a dependency for one variable."""
    try:
        for line in open(".env", encoding="utf-8"):
            line = line.strip()
            if line.startswith("DATA_GOV_IN_KEY=") and not line.startswith("#"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
    return ""


def main():
    key = (sys.argv[1] if len(sys.argv) > 1
           else os.environ.get("DATA_GOV_IN_KEY", "") or read_dotenv()).strip()
    if not key:
        print(__doc__)
        print("ERROR: no key given. Pass it as argv[1] or set DATA_GOV_IN_KEY.")
        return 1
    try:
        api(key, limit=1)
    except urllib.error.HTTPError as e:
        print(f"Key rejected: HTTP {e.code} {e.read(300).decode('utf-8','ignore')[:200]}")
        return 1

    page, total = q1_page_size(key)
    q2_subcategories(key, page or 10)
    q3_state_scoping(key)

    print("\n=== WHAT TO DO WITH THIS ===")
    if page > 10:
        hours = (int(total) / page) * 0.5 / 3600
        print(f"Q1 ANSWERED: page size {page}. Full scan ~{int(total)//page:,} calls "
              f"(~{hours:.1f}h at 0.5s/call). Bulk pull into SQLite is viable.")
    else:
        print("Q1 UNRESOLVED: still capped at 10/call. A full scan is NOT viable -- "
              "fall back to per-company name lookups for matched companies only.")
    print("Q2: read the vocabulary above. If no 'Subsidiary of Foreign Company' value "
          "exists, match foreign subsidiaries by NAME instead (e.g. '% INDIA PRIVATE "
          "LIMITED') and treat the subcategory field as unusable. Update "
          "learning-tests/FINDINGS.md and SPEC.md feature 9 with whatever is true.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
