"""T1.2's integration check: fetch the real YC directory and assert it is
non-empty, schema-valid, and adds companies the existing corpus does not have.

Deliberately outside `make check` (VERIFICATION.md: the gate must not depend on
a third party being up). Run it on demand:

    .venv/bin/python learning-tests/yc_live.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import yc  # noqa: E402
from src.corpus import merge  # noqa: E402
from src.finsmes import BASE, Record, parse  # noqa: E402
from src.net import get  # noqa: E402

status, payload = get(yc.API, timeout=120)
print(f"GET {yc.API} -> {status}, {len(payload) / 1e6:.1f}MB")
if status != 200:
    raise SystemExit(f"YC directory unreachable ({status}) — nothing to assert")

records = yc.parse(payload)
stages: dict[str | None, int] = {}
for record in records:
    stages[record["stage"]] = stages.get(record["stage"], 0) + 1
print(f"{len(records)} records, stages: {stages}")

assert records, "empty directory"
for record in records:
    assert set(record) == set(Record.__annotations__), f"schema drift: {sorted(record)}"
    assert record["name"] and record["source_url"].startswith("https://")

status, page = get(f"{BASE}/category/usa")
finsmes = parse(page).records if status == 200 else []
print(f"FinSMEs: {len(finsmes)} records ({'live' if finsmes else 'unreachable, skipping'})")

before = merge(finsmes)
after = merge(finsmes, records)
print(
    f"corpus: {len(before.companies)} -> {len(after.companies)} qualified, "
    f"{len(before.unqualified)} -> {len(after.unqualified)} unqualified"
)
assert len(after.companies) > len(before.companies), "the source added no distinct company"

by_rule: dict[str, int] = {}
for company in after.companies:
    by_rule[company["qualified_by"]] = by_rule.get(company["qualified_by"], 0) + 1
print(f"qualified_by: {by_rule}")

# A source URL that doesn't resolve is a citation we can't stand behind.
sample = [c for c in after.companies if "ycombinator.com" in c["source_url"]][:5]
for company in sample:
    code, _ = get(company["source_url"])
    print(f"  {code}  {company['name']}  {company['source_url']}")
    assert code == 200, f"{company['name']}'s source URL does not resolve"

# The full pipeline reads corpus.json, so prove the merged corpus round-trips.
json.dumps({"companies": after.companies, "unqualified": after.unqualified})
print(f"\nHOLDS: {len(after.companies)} qualified companies, all schema-valid")
