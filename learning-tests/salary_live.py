"""What AmbitionBox actually does — T4.2 (SPEC feature 8).

Re-runnable on demand, never from `make check`: VERIFICATION.md keeps live
third-party contracts out of the gate. Run it when the enrichment's coverage
drops and you need to know whether the source moved or is merely throttling.

    .venv/bin/python -m learning-tests.salary_live      # or: python learning-tests/salary_live.py

Four claims, each the reason a design decision in src/salary.py is what it is.
"""
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import salary  # noqa: E402
from src.net import get  # noqa: E402
from src.slugs import key  # noqa: E402

LISTED = [c["name"] for c in json.loads(Path("data/companies.json").read_text())["companies"]]


def status(name: str) -> int:
    return get(salary.PAGE.format(slug=salary.slug(name)), 30)[0]


def main() -> None:
    print("§1 a wrong slug 404s, so an absence is never a silent empty page")
    for slug in ("zzznotacompanyxyz", "not-a-real-company-at-all"):
        code, _ = get(salary.PAGE.format(slug=slug), 30)
        print(f"   {slug:28} -> {code}   (expect 404)")

    print("\n§2 the figure, its sample and — the load-bearing one — its own date")
    for name in ("Razorpay", "Databricks", "Coinbase"):
        print(f"   {name:12} {salary.lookup(name)}")

    print("\n§3 the rate limit is a 403 on a rolling window, not a concurrency cap")
    print("   (a burst at 8 workers is what emptied the first sweep: 86 of 116 blocked)")
    sample = LISTED[:24]
    for workers in (8, 4):
        started = time.time()
        with ThreadPoolExecutor(workers) as pool:
            codes = list(pool.map(status, sample))
        blocked = sum(1 for c in codes if c == 403)
        print(f"   workers={workers}  {time.time() - started:5.1f}s  "
              f"200={codes.count(200)} 404={codes.count(404)} 403={blocked}")
        time.sleep(20)   # let the window drain, or the second measurement measures the first

    print("\n§4 the page must state a name CONTAINING the company's, and the loose")
    print("   direction is load-bearing: an exact-match rule drops Kaseya.")
    for name in LISTED:
        page = salary.lookup(name)
        if not page:
            continue
        payload = salary._NEXT_DATA.search(get(page["source_url"], 30)[1])
        if not payload:      # throttled on the re-fetch; not this claim's business
            continue
        header = json.loads(payload.group(1))["props"]["pageProps"]["companyHeaderData"]
        found = header["companyName"]
        if key(found) != key(name):
            print(f"   containment-only: corpus {name!r} page {found!r}")


if __name__ == "__main__":
    main()
