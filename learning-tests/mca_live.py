#!/usr/bin/env python3
"""T4.3's integration check, live: pull with retries and assert the record count
lands within 10% of the measured 24,102 foreign subsidiaries.

    .venv/bin/python learning-tests/mca_live.py

Three calls. That is the whole point of the module — a registered key serves
10,000 rows a call, so the enrichment universe is a rare three-call pull into a
file rather than an inline dependency on an API that goes dark after ~20 calls.

§2 is the check that would have caught the mistake this source has already made
once: `filters[CompanySubCategory]=Subsidiary of Foreign Company` returns
total=0, and a genuine zero is indistinguishable from a throttled call. The
spelling in `src/mca.py` is the one the data uses; the wrong one is here beside
it so the difference is visible rather than remembered.
"""
from __future__ import annotations

import json
import sys
import time
from urllib.parse import urlencode

sys.path.insert(0, ".")

from src import mca  # noqa: E402
from src.net import get  # noqa: E402


def total_for(key: str, subcategory: str) -> object:
    """What the API says the universe is for one spelling of the filter."""
    url = f"{mca.BASE}?" + urlencode(
        {
            "api-key": key, "format": "json", "limit": 1,
            "filters[CompanySubCategory]": subcategory,
        }
    )
    status, body = get(url, timeout=90)
    if status != 200:
        return f"HTTP {status}"
    return json.loads(body).get("total")


def main() -> int:
    key = mca.api_key()
    if not key:
        print("no DATA_GOV_IN_KEY — see .env.example")
        return 1

    print("§1 the pull, with retries, against the measured universe")
    started = time.time()
    companies = mca.pull(key)
    found, drift = len(companies), abs(len(companies) - mca.EXPECTED) / mca.EXPECTED
    print(f"   {found:,} records in {time.time() - started:.1f}s "
          f"({found * 100 // mca.EXPECTED}% of the expected {mca.EXPECTED:,})")
    assert drift <= 0.10, f"{found:,} is more than 10% off {mca.EXPECTED:,}"

    print("\n§2 the filter value is the one the data spells, not the obvious one")
    for label, subcategory in (
        ("as the data spells it", mca.SUBCATEGORY),
        ("the plausible guess  ", "Subsidiary of Foreign Company"),
    ):
        print(f"   {label}  total={total_for(key, subcategory)}")

    print("\n§3 every cached record can be named and shown")
    blank = {
        field: sum(1 for c in companies if not c[field])  # type: ignore[literal-required]
        for field in mca.FIELDS
    }
    print(f"   blank fields across {found:,} records: {blank}")
    assert not blank["cin"] and not blank["name"], "a record the site could not identify"

    print("\n§4 currency — the reason the 37 state-wise datasets are a trap")
    newest = max(c["incorporated"] for c in companies)
    print(f"   newest incorporation in the slice: {newest}  (state-wise data stops at 2021-03-31)")
    assert newest > "2021-03-31", "this looks like a frozen dataset, not the RoC one"

    print("\nOK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
