"""What SEC Form D actually gives us — measured for T1.3.

Run: .venv/bin/python learning-tests/edgar_live.py

Four questions this answers, none of which are safe to guess:
  1. Does the browser UA the rest of the project uses work here? (No.)
  2. Which quarters are actually published today?
  3. What survives the filters, and what does a naive scrape get instead?
  4. Do EDGAR's legal names dedup against the YC corpus?
"""
from __future__ import annotations

import collections
import io
import json
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import corpus, edgar, net  # noqa: E402
from src.finsmes import Record  # noqa: E402

CORPUS = Path(__file__).resolve().parent.parent / "data" / "corpus.json"


def ua_matters() -> None:
    print("== 1. the User-Agent ==")
    url = edgar.DATASET.format(quarter=edgar.quarters()[-1])
    print(f"  project browser UA : {net.get(url, timeout=60)[0]}")
    print(f"  SEC contact UA     : {net.get_bytes(url, timeout=120, ua=edgar.UA)[0]}")


def published() -> bytes:
    print("\n== 2. which candidate quarters exist ==")
    for quarter in edgar.quarters():
        url = edgar.DATASET.format(quarter=quarter)
        status, blob = net.get_bytes(url, timeout=120, ua=edgar.UA)
        print(f"  {quarter}  {status}  {len(blob):,}b")
        if status == 200:
            return blob
    raise SystemExit("no published quarter found")


def yield_of(blob: bytes) -> list[Record]:
    print("\n== 3. what the newest published quarter contains ==")
    records = edgar.parse(blob)

    # The same file read WITHOUT the filters, to size what they remove.
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        offering = {o["ACCESSIONNUMBER"]: o for o in edgar._rows(archive, "OFFERING")}
        issuers = edgar._rows(archive, "ISSUERS")

    drop: collections.Counter[str] = collections.Counter()
    for i in issuers:
        o = offering.get(i["ACCESSIONNUMBER"])
        if i["IS_PRIMARYISSUER_FLAG"] != "YES":
            drop["secondary issuer"] += 1
        elif o is None:
            drop["no offering row"] += 1
        elif o["ISAMENDMENT"] == "true":
            drop["amendment (D/A)"] += 1
        elif o["ISPOOLEDINVESTMENTFUNDTYPE"] == "true":
            drop["pooled investment fund"] += 1
        elif o["INDUSTRYGROUPTYPE"] not in edgar.TECH:
            drop[f"not tech ({o['INDUSTRYGROUPTYPE']})"] += 1
    print(f"  {len(issuers):6} issuer rows")
    for reason, n in drop.most_common(8):
        print(f"  {-n:6} {reason}")
    print(f"  {len(records):6} records emitted")
    qualifying = [r for r in records if (r["amount"] or 0) >= corpus.MIN_AMOUNT]
    print(f"  {len(qualifying):6} of them clear the $5M proxy")
    print(f"  undated among those: {sum(1 for r in qualifying if not r['date'])}")
    for r in sorted(qualifying, key=lambda r: -(r["amount"] or 0))[:6]:
        print(f"     ${r['amount']:>15,}  {r['date']}  {r['name']}")
    return qualifying


def dedups(qualifying: list[Record]) -> None:
    print("\n== 4. dedup against the existing corpus ==")
    if not CORPUS.exists():
        print("  no data/corpus.json yet — skipped")
        return
    key = lambda n: re.sub(r"[^a-z0-9]+", "", n.casefold())  # corpus.py's key  # noqa: E731
    existing = {c["name"] for c in json.loads(CORPUS.read_text())["companies"]}
    by_key = {key(n): n for n in existing}
    merged = [(r["name"], by_key[key(r["name"])]) for r in qualifying if key(r["name"]) in by_key]
    print(f"  corpus {len(existing)}, EDGAR qualifying {len(qualifying)}, merging {len(merged)}")
    for edgar_name, other in merged[:8]:
        print(f"     {edgar_name!r} <- {other!r}")
    print("  (EDGAR strips the legal suffix at the source, so the plain key already matches;")
    print("   the raw ENTITYNAMEs are e.g. 'Legora, Inc.', 'SOLIDROAD INC.')")


def source_urls(qualifying: list[Record]) -> None:
    print("\n== 5. do the source URLs resolve? ==")
    for r in qualifying[:5]:
        status, _ = net.get_bytes(r["source_url"], timeout=30, ua=edgar.UA)
        print(f"  {status}  {r['source_url']}")


if __name__ == "__main__":
    ua_matters()
    qualifying = yield_of(published())
    dedups(qualifying)
    source_urls(qualifying)
