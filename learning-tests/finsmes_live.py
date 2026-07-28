#!/usr/bin/env python3
"""T1.1 integration check — scrape one REAL FinSMEs page.

Lives here, not in tests/, because `make check` must not depend on a third party
being up (VERIFICATION.md, "Deliberately NOT verified"). Run on demand to catch
the source changing shape:

    .venv/bin/python learning-tests/finsmes_live.py

Asserts the T1.1 DoD against live HTML: >=10 records with source URLs, and that
those URLs actually resolve 200.
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.finsmes import _UA, BASE, fetch, parse  # noqa: E402

SAMPLE_URLS = 3  # spot-check, not all 12: the source challenges bursts


def resolves(url: str) -> str:
    """HTTP status of the URL, via curl for the same TLS reason as fetch.

    A GET with the body discarded, not a HEAD: Cloudflare answers HEAD with 403
    on these article pages and GET with 200, so a HEAD check would report every
    perfectly good source URL as dead.
    """
    done = subprocess.run(
        ["curl", "--silent", "--max-time", "45", "-o", "/dev/null",
         "-w", "%{http_code}", "-A", _UA, url],
        capture_output=True,
        text=True,
    )
    return done.stdout.strip() or "no-response"


def main() -> int:
    url = f"{BASE}/category/usa"
    page = fetch(url)
    if page is None:
        print(f"FAIL  could not fetch {url} -- source down or challenging us")
        return 1

    records, unparsed = parse(page)
    print(f"records: {len(records)}   unparsed headlines: {len(unparsed)}")
    for record in records[:5]:
        print(f"  {record['date']}  {record['name']:<28} "
              f"{record['amount']} {record['currency']} series={record['round_letter']}")
    for title in unparsed:
        print(f"  UNPARSED: {title}")

    assert len(records) >= 10, f"expected >=10 records, got {len(records)}"
    assert all(r["source_url"].startswith("https://") for r in records)

    for record in records[:SAMPLE_URLS]:
        status = resolves(record["source_url"])
        print(f"  {status}  {record['source_url']}")
        assert status == "200", f"source URL did not resolve: {record['source_url']}"

    print(f"\nPASS  {len(records)} records, first {SAMPLE_URLS} source URLs resolve 200")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
