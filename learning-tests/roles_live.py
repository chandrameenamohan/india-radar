"""T4.1 — where a role states its title, its apply URL, and whether it's remote.

Every previous probe task found the headline assumption stale, so nothing here is
inherited. Three questions, all of which change the code:

  1. Which field on each provider's role is an APPLY url — one a human can click
     and land on an application form? Several URL-shaped fields exist per role
     and they are not interchangeable.
  2. Do those URLs actually 200? That is T4.1's own DoD check, and it cannot run
     in `make check` (VERIFICATION: no live third-party contracts in the gate),
     so it runs here, against the 10 real listed companies the DoD asks for.
  3. What does an India role with NO named city say? `alpaca` is listed today
     with `cities: []`, and the DoD demands every listed company show a city or
     an explicit remote flag. The vocabulary for that flag has to be measured off
     real location strings, not imagined — T3.4 already lost `IN-` to
     `In-Office`, which is exactly this mistake made one task earlier.

Run: .venv/bin/python learning-tests/roles_live.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, ".")
from src import ashby, greenhouse, lever  # noqa: E402
from src.india import cities, is_india  # noqa: E402
from src.net import get  # noqa: E402

PROVIDERS = {"greenhouse": greenhouse, "ashby": ashby, "lever": lever}

listed = json.load(open("data/companies.json"))["companies"]
by_ats: dict[str, list[dict]] = {}
for company in listed:
    by_ats.setdefault(company["ats"], []).append(company)

print("== 1. role shape per provider — which field is an apply URL? ==")
boards: dict[str, list[dict]] = {}
for ats, module in PROVIDERS.items():
    sample = by_ats[ats][0]
    roles = module.probe(sample["slug"])
    if not isinstance(roles, list) or not roles:
        print(f"  {ats}: {roles}")
        continue
    boards[ats] = roles
    role = roles[0]
    urls = {k: v for k, v in role.items() if isinstance(v, str) and v.startswith("http")}
    print(f"\n  {ats}/{sample['slug']} — {len(roles)} roles, keys: {sorted(role)}")
    for key, value in sorted(urls.items()):
        print(f"    url  {key:20} {value}")
    for key in ("title", "text", "name"):
        if isinstance(role.get(key), str):
            print(f"    title{key:20} {role[key]!r}")

print("\n== 2. do the apply URLs 200? (the DoD's own check: 10 listed companies) ==")
# One India role from each of ten real listed companies, spread across all three
# providers so a provider-specific mistake cannot hide behind two that work.
FIELD = {"greenhouse": "absolute_url", "ashby": "jobUrl", "lever": "hostedUrl"}


def first_india_url(company: dict) -> tuple[str, str] | None:
    module = PROVIDERS[company["ats"]]
    roles = module.probe(company["slug"])
    if not isinstance(roles, list):
        return None
    for role in roles:
        if any(is_india(place) for place in module.locations(role)):
            url = role.get(FIELD[company["ats"]])
            return (company["name"], url) if isinstance(url, str) else (company["name"], "")
    return None


sample = by_ats["lever"][:3] + by_ats["ashby"][:3] + by_ats["greenhouse"][:4]
with ThreadPoolExecutor(max_workers=10) as pool:
    found = [r for r in pool.map(first_india_url, sample) if r]

with ThreadPoolExecutor(max_workers=10) as pool:
    statuses = list(pool.map(lambda pair: get(pair[1], 45)[0] if pair[1] else 0, found))

for (name, url), status in zip(found, statuses, strict=True):
    print(f"  {status}  {name:24} {url[:96]}")
print(f"\n  {sum(s == 200 for s in statuses)}/{len(statuses)} apply URLs returned 200")

print("\n== 3. India roles that name no city — what do they say? ==")
# Every India location string on every sampled board, split by whether `cities`
# found a name in it. The right-hand column is the vocabulary a remote flag can
# honestly be built from.
placeless: Counter[str] = Counter()
withcity = 0
for ats, roles in boards.items():
    for role in roles:
        for place in PROVIDERS[ats].locations(role):
            if not is_india(place):
                continue
            if cities(place):
                withcity += 1
            else:
                placeless[place] += 1

# A wider read: the listed corpus is 116 companies, and the three boards above
# are too few to name a vocabulary from. Pull every India location string across
# 30 listed companies.
def india_places(company: dict) -> list[str]:
    module = PROVIDERS[company["ats"]]
    roles = module.probe(company["slug"])
    if not isinstance(roles, list):
        return []
    return [p for role in roles for p in module.locations(role) if is_india(p)]


with ThreadPoolExecutor(max_workers=10) as pool:
    wide = [p for places in pool.map(india_places, listed[:30]) for p in places]

nocity = Counter(p for p in wide if not cities(p))
print(f"  {len(wide)} India location strings across 30 listed companies")
print(f"  {len(wide) - sum(nocity.values())} name a city, {sum(nocity.values())} do not")
print("\n  the ones naming no city:")
for place, count in nocity.most_common(30):
    print(f"    {count:4d}  {place!r}")

REMOTE = re.compile(r"\bremote\b|\bwork from home\b|\banywhere\b", re.IGNORECASE)
print("\n  how many of those a /remote|work from home|anywhere/ rule would flag:")
flagged = sum(count for place, count in nocity.items() if REMOTE.search(place))
print(f"    {flagged} of {sum(nocity.values())}")

print("\n  and the trap check — India strings WITH a city that also say remote:")
hybrid = Counter(p for p in wide if cities(p) and REMOTE.search(p))
for place, count in hybrid.most_common(12):
    print(f"    {count:4d}  {place!r}")
