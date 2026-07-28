#!/usr/bin/env python3
"""
LEARNING TEST 4: can we actually GET bulk MCA company master data?

This was the premise-killer flagged in the Challenge step.

FINDINGS, measured 2026-07-28. My FIRST reading of these results was WRONG and is
corrected here, because the correction is the whole lesson:

  WRONG FIRST CONCLUSION: "MCA bulk data is geo-blocked, project blocked."
  I got HTTP 403 from data.gov.in via headless Chromium AND via WebFetch, saw an
  Akamai edge-error body, and concluded the host blocks us. It does not.

  WHAT IS ACTUALLY TRUE:
    data.gov.in       -> HTTP 200 to plain curl with an ordinary browser UA.
                         The 403 is BOT fingerprinting (TLS/headless signals),
                         not geography. Real Chromium via the browse tool is
                         blocked; boring curl sails through. Do not trust a
                         headless browser to tell you a host is unreachable.
    mca.gov.in        -> HTTP 403, genuinely. Both paths tried. Assume no access.
    api.data.gov.in   -> WORKS. Returns {"error":"Authorization field missing"}
                         without a key, and real data with one. data.gov.in
                         publishes a sample key that is enough to evaluate.

WHAT THIS CHANGES:
  MCA is reachable after all, so the enrichment layer is viable -- see
  mca_roc_dataset.py, which finds the one dataset worth using and measures the
  real limits (the staleness fear was RIGHT about the obvious datasets and WRONG
  about the one that matters).

  The Challenge-step decision to demote MCA from gate to enrichment still stands
  on its own merits, but not for the reason argued during this test. It stands
  because MCA proves legal existence, not hireability.

METHOD NOTE worth keeping: probe a suspicious 403 with at least two different
clients before believing it. One client's block is not the host's policy.
"""

import json
import sys
import urllib.error
import urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 " \
     "(KHTML, like Gecko) Chrome/145.0 Safari/537.36"

TARGETS = [
    ("data.gov.in catalog", "https://www.data.gov.in/catalog/company-master-data"),
    ("mca.gov.in master data",
     "https://www.mca.gov.in/content/mca/global/en/data-and-reports/company-statistics/company-master-data.html"),
    ("mca.gov.in open dataset", "https://www.mca.gov.in/mcafoportal/showOpenDataSet.do"),
    ("api.data.gov.in", "https://api.data.gov.in/catalog/company-master-data?format=json"),
]


def probe(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.read(400).decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, e.read(400).decode("utf-8", "ignore")
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}: {e}"


def main():
    reachable = []
    for name, url in TARGETS:
        status, body = probe(url)
        blocked = status == 403 or "Access Denied" in body or "edgesuite" in body
        print(json.dumps({
            "target": name, "status": status,
            "edge_blocked": blocked,
            "body_head": " ".join(body.split())[:110],
        }))
        if status == 200:
            reachable.append(name)

    print("\n=== VERDICT ===")
    if reachable:
        print(f"MCA bulk access now WORKS for: {reachable}. "
              "Unblock the MCA enrichment bead and measure dump freshness.")
    else:
        print("MCA bulk access still BLOCKED from this network. "
              "MCA enrichment stays deferred; ship the ATS-first site without it.")
    # Deliberately not an assert-fail: a blocked network is the CURRENT known
    # state, not a regression. This test reports, and flips to green when the
    # situation changes.
    return 0


if __name__ == "__main__":
    sys.exit(main())
