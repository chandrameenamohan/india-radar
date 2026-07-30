#!/usr/bin/env python3
"""T8.1 (bonus) — src/countries.py's term lists against every real location string.

T8.2's docstring says of its city lists: "none of this is measured yet — the T8.1
probes have not sampled non-India boards. This is a starting list; when FINDINGS.md
gains real location strings from the new countries, entries earn their place there
or get deleted there." This is that measurement. It changes no code — it reports
which terms earned their place, which never fire, and what the deliberate
exclusions actually cost.

Run: .venv/bin/python learning-tests/locations_live.py   (~1m, ~110MB)

WHAT WAS MEASURED (2026-07-30, 26,880 location strings / 3,419 distinct, from every
board in data/slugs.json — the cheap pass only, no descriptions):

  THE FALSE-POSITIVE CLAIM HOLDS. Not one string in 3,419 classifies to a country
  it is not in. Every trap the docstring names behaves as designed:
  "Cambridge, MA" (16 postings) -> none, "Perth" -> none, "Nice" -> none,
  "Victoria, British Columbia, Canada" -> none, "Richmond, CA" -> none,
  "Kitchener-Waterloo, ON" -> none, "Hamilton, NJ" -> none. The 58 postings that
  name both a target country and the US/Canada are genuinely multi-located
  ("London, UK; New York, NY"), which is what feature 14 wants.

  53 OF THE 124 TERMS NEVER FIRE ON ANY REAL STRING. Every Norwegian city but
  Oslo, every NZ city but Auckland, six of Japan's nine (kyoto, yokohama, fukuoka,
  sapporo, kobe, shibuya), most of Spain's and Sweden's, and every native-language
  country name except "deutschland" (great britain, españa, sverige, danmark,
  norge, suomi, aotearoa: all zero). Harmless, but unmeasured padding.

  THE DUBLIN EXCLUSION IS THE ONE THE DATA CONTRADICTS. It was excluded because
  "Dublin CA (Bay Area) and Dublin OH are both live tech-posting addresses".
  In this corpus: **zero** strings name Dublin CA or Dublin OH. Meanwhile bare
  "Dublin" spellings are 51 postings and "Dublin, IE" another 8 — 59 postings,
  **24% of Ireland's total volume**, classifying as no country. The collision it guards
  against does not occur here; the cost does. "Dublin, IE" is not even the bare-city
  case — it names its country in ISO form and nothing reads it.

  THE OTHER EXCLUSIONS ARE VINDICATED AND NOW COST NOTHING. "Cambridge" is 17
  postings of which 16 are Cambridge MA. "Perth", "Nice" and "Newcastle" are 1-2
  postings each. Excluding them is free; the docstring guessed right.

  NEW ZEALAND AND NORWAY BARELY EXIST HERE: 5 and 3 postings, against SPEC's rule
  that a country is added "when probe data shows real volume there, not before".
  Not a bug in this module — a question for whoever owns the country list.
"""
from __future__ import annotations

import collections
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.countries import _TERMS, countries  # noqa: E402
from src.net import get  # noqa: E402

GH = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=false"
ASHBY = "https://api.ashbyhq.com/posting-api/job-board/{slug}"
LEVER = "https://api.lever.co/v0/postings/{slug}?mode=json"
WORKERS = 10

#: A string naming one of these alongside a target country is a multi-located
#: posting, not a false positive — but it is where a false positive would hide.
ELSEWHERE = re.compile(
    r"(?<!\w)(usa|u\.s\.|united states|canada|ontario|texas|california|florida|"
    r"ma|ca|ny|tx|fl|oh|nh|wi|me|nj|il|wa|va|nc|ct|pa)(?!\w)", re.IGNORECASE
)

#: Every place name the T8.2 docstring argues about, so the argument gets numbers.
TRAPS = ["cambridge", "newcastle", "perth", "reading", "nice", "dublin", "victoria",
         "bergen", "valencia", "holland", "richmond", "waterloo", "hamilton"]


def greenhouse(slug: str) -> list[str]:
    status, body = get(GH.format(slug=slug), 60)
    if status != 200:
        return []
    try:
        jobs = json.loads(body)["jobs"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return []
    return [(j.get("location") or {}).get("name") or "" for j in jobs]


def ashby(slug: str) -> list[str]:
    status, body = get(ASHBY.format(slug=slug), 240)
    if status != 200:
        return []
    try:
        jobs = json.loads(body)["jobs"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return []
    out = []
    for job in jobs:
        out.append(job.get("location") or "")
        out += [(e.get("location") if isinstance(e, dict) else e) or ""
                for e in job.get("secondaryLocations") or []]
    return out


def lever(slug: str) -> list[str]:
    status, body = get(LEVER.format(slug=slug), 120)
    if status != 200:
        return []
    try:
        posts = json.loads(body)
    except json.JSONDecodeError:
        return []
    if not isinstance(posts, list):
        return []
    out = []
    for post in posts:
        categories = post.get("categories") or {}
        places = categories.get("allLocations") or [categories.get("location")]
        out += [p for p in places if isinstance(p, str)]
    return out


def every_location() -> collections.Counter[str]:
    """Every location string on every board, with how many postings carry it."""
    slugs = json.loads((Path(__file__).resolve().parent.parent / "data/slugs.json").read_text())
    by_ats: dict[str, set[str]] = {}
    for entry in slugs.values():
        by_ats.setdefault(entry["ats"], set()).add(entry["slug"])

    seen: collections.Counter[str] = collections.Counter()
    for label, harvest in (("greenhouse", greenhouse), ("ashby", ashby), ("lever", lever)):
        boards = sorted(by_ats.get(label, ()))
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            for got in pool.map(harvest, boards):
                seen.update(place for place in got if place.strip())
        print(f"  {label:11s} {len(boards):4d} boards -> {sum(seen.values())} strings so far")
    return seen


def main() -> int:
    print("== every location string on every board ==")
    seen = every_location()
    if not seen:
        print("\nNO LOCATIONS FETCHED — nothing measured.")
        return 1
    print(f"\n{sum(seen.values())} location strings, {len(seen)} distinct.")
    matched = {place: countries(place) for place in seen}

    print("\n== does each term earn its place? ==")
    dead = []
    for country, terms in _TERMS.items():
        for term in terms:
            pattern = re.compile(r"(?<!\w)(?:" + term + r")(?!\w)", re.IGNORECASE)
            postings = sum(n for place, n in seen.items() if pattern.search(place))
            if postings:
                print(f"  {country:16s} {term:24s} {postings:6d}")
            else:
                dead.append(f"{country}/{term}")
    print(f"\n  NEVER FIRES ({len(dead)} of "
          f"{sum(len(t) for t in _TERMS.values())} terms): {', '.join(dead)}")

    print("\n== postings per country, by src/countries.py ==")
    per_country: collections.Counter[str] = collections.Counter()
    for place, n in seen.items():
        for country in matched[place]:
            per_country[country] += n
    for country, n in per_country.most_common():
        print(f"  {country:16s} {n:6d}")

    print("\n== false-positive hunt: classified AND naming the US/Canada ==")
    suspects = [(n, place) for place, n in seen.items()
                if matched[place] and ELSEWHERE.search(place)]
    for n, place in sorted(suspects, reverse=True)[:15]:
        print(f"  {n:5d}  {place[:64]:64s} -> {','.join(matched[place])}")
    print(f"  ({len(suspects)} distinct, {sum(n for n, _ in suspects)} postings — "
          f"read them: a genuine multi-located posting is not a false positive)")

    traps(seen, matched)
    return 0


def traps(seen: collections.Counter[str], matched: dict[str, list[str]]) -> None:
    """What each deliberate exclusion actually costs, in postings."""
    print("\n== the traps the T8.2 docstring argues about, with numbers ==")
    for trap in TRAPS:
        pattern = re.compile(rf"(?<!\w){trap}(?!\w)", re.IGNORECASE)
        found = [(n, place) for place, n in seen.items() if pattern.search(place)]
        if not found:
            print(f"  {trap:11s} never appears in any real string")
            continue
        total = sum(n for n, _ in found)
        kept = sum(n for n, place in found if matched[place])
        print(f"  {trap:11s} {total:5d} postings, {len(found):3d} distinct; "
              f"{kept} classified, {total - kept} left as no country")
        for n, place in sorted(found, reverse=True)[:3]:
            print(f"                {n:5d}  {place[:56]:56s} -> "
                  f"{','.join(matched[place]) or '(none)'}")


if __name__ == "__main__":
    raise SystemExit(main())
