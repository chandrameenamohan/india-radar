#!/usr/bin/env python3
"""T9.2 Phase 1 — do the boards state a department, and is it better than our guess?

T5.4 ships a DEPARTMENT filter derived from the role title by keyword map: 86.3%
of titles placed, the rest reachable as UNCLASSIFIED, and the page says on itself
that the label is derived. Its note also says "no board publishes one" — which was
read off our own request string, never measured. This measures it.

Run: .venv/bin/python learning-tests/departments_live.py

Three questions, in the order that can kill the task:
  COST      does the department arrive in a call the build already makes?
  COVERAGE  what share of postings state one at all?
  VOCABULARY are they words a filter can use, or whatever a team typed that day?

KILL CRITERION (T9.2, on T8.1's rule): if what the boards state would not beat
86.3% WHERE IT MATTERS — the titles the map cannot place, and the ones it places
wrongly — stop, record the numbers, and leave the heuristic standing.

The comparison map is not re-typed here: `site_map()` reads the DEPTS table out of
site/index.html, so a measurement can never quietly drift from the page it is
about.

WHAT WAS MEASURED — see FINDINGS §T9.2 (the numbers this run printed are pasted
there rather than here, so this docstring stays the question and not the answer).
"""
from __future__ import annotations

import collections
import json
import re
import sys
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import ashby, greenhouse, lever  # noqa: E402
from src.countries import countries  # noqa: E402
from src.net import get  # noqa: E402

GH_CHEAP = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=false"
GH_RICH = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
ASHBY = "https://api.ashbyhq.com/posting-api/job-board/{slug}"
LEVER = "https://api.lever.co/v0/postings/{slug}?mode=json"

WORKERS = 10

#: Bytes pulled, so "the department is free on this provider" is a number.
FETCHED = [0]


def fetch(url: str, timeout: int) -> tuple[int, str]:
    status, body = get(url, timeout)
    FETCHED[0] += len(body.encode())
    return status, body


# --------------------------- the site's own map -------------------------------

#: One row of site/index.html's DEPTS table: `['Name', /pattern/i],`. The table is
#: JS, so it is read rather than re-typed — a transliterated copy would agree with
#: the page on the day it was written and never again.
#: ponytail: a regex over a literal list, not a JS parser. Ceiling: it breaks the
#: day someone reformats that array, and it breaks LOUDLY (zero rows parsed).
_ROW = re.compile(r"^\s*\['([^']+)',\s*/(.*)/i\],\s*$", re.M)


def site_map() -> list[tuple[str, re.Pattern[str]]]:
    """The site's title -> department table, first match wins, as the page has it.

    The patterns are the same subset both engines read the same way — literals,
    alternation, `\\b`, `.?`, groups — so compiling them with `re` is the same
    classifier and not an approximation of it.
    """
    rows = _ROW.findall((ROOT / "site/index.html").read_text())
    if not rows:
        raise SystemExit("site/index.html: no DEPTS rows parsed — the table moved")
    return [(name, re.compile(pattern, re.I)) for name, pattern in rows]


def classify(title: str, table: list[tuple[str, re.Pattern[str]]]) -> str | None:
    """What the site would label this title, or None where it gives up."""
    return next((name for name, pattern in table if pattern.search(title)), None)


# --------------------------- what each board states ---------------------------

#: Where each provider keeps the department, and what else it says beside it.
#: Greenhouse nests a list (a job can sit under several); Ashby and Lever state a
#: department AND a team, which are different questions — "Engineering / Backend"
#: on Ashby, "Sales & Professional Services / Solutions Engineering" on Lever.
STATED: dict[str, Callable[[dict[str, Any]], tuple[list[Any], list[Any]]]] = {
    "greenhouse": lambda job: (
        [d.get("name") for d in job.get("departments") or [] if isinstance(d, dict)],
        [],
    ),
    "ashby": lambda job: ([job.get("department")], [job.get("team")]),
    "lever": lambda job: (
        [(job.get("categories") or {}).get("department")],
        [(job.get("categories") or {}).get("team")],
    ),
}

PLACES = {
    "greenhouse": greenhouse.locations,
    "ashby": ashby.locations,
    "lever": lever.locations,
}
TITLE = {"greenhouse": "title", "ashby": "title", "lever": "text"}


def clean(values: list[Any]) -> list[str]:
    return [v.strip() for v in values if isinstance(v, str) and v.strip()]


def postings(ats: str, slug: str, url: str, timeout: int) -> list[dict[str, Any]] | None:
    """Every target-country posting on one board, as title + what it states.

    A board that will not answer is None and counted as unreadable — never as a
    board that states no department, which is the whole distinction this project
    keeps.
    """
    status, body = fetch(url.format(slug=slug), timeout)
    if status != 200:
        return None
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None
    jobs = payload if isinstance(payload, list) else payload.get("jobs")
    if not isinstance(jobs, list):
        return None

    rows = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        places = PLACES[ats](job)
        where = sorted({c for place in places for c in countries(place)})
        if not where:
            continue
        departments, teams = STATED[ats](job)
        rows.append(
            {
                "ats": ats,
                "slug": slug,
                "title": str(job.get(TITLE[ats]) or "").strip(),
                "departments": clean(departments),
                "teams": clean(teams),
            }
        )
    return rows


def harvest(ats: str, slugs: list[str], url: str, timeout: int) -> list[dict[str, Any]]:
    started = time.monotonic()
    before = FETCHED[0]
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(lambda slug: postings(ats, slug, url, timeout), slugs))
    got = [row for result in results if result for row in result]
    print(
        f"  {ats:11s} {len(slugs):4d} boards "
        f"({sum(1 for r in results if r is None)} unreadable) -> {len(got)} target-country "
        f"postings, {(FETCHED[0] - before) / 1e6:.0f}MB in {time.monotonic() - started:.0f}s"
    )
    return got


def corpus() -> list[dict[str, Any]]:
    """Every target-country posting on every board in data/slugs.json.

    Greenhouse is fetched twice for the reason build.py fetches it twice: the
    departments ride with `content=true`, and 259 of 422 boards have no posting in
    a country we cover, so the cheap pass keeps the 24x payload off them.
    """
    slugs = json.loads((ROOT / "data/slugs.json").read_text())
    by_ats: dict[str, list[str]] = {}
    for entry in slugs.values():
        by_ats.setdefault(entry["ats"], []).append(entry["slug"])

    def contributes(slug: str) -> bool:
        status, body = fetch(GH_CHEAP.format(slug=slug), 60)
        if status != 200:
            return False
        try:
            jobs = json.loads(body)["jobs"]
        except (json.JSONDecodeError, KeyError, TypeError):
            return False
        return any(countries(place) for j in jobs for place in greenhouse.locations(j))

    every = sorted(set(by_ats.get("greenhouse", [])))
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        keep = list(pool.map(contributes, every))
    rich = [slug for slug, wanted in zip(every, keep, strict=True) if wanted]
    print(f"  greenhouse: {len(rich)}/{len(every)} boards have a target-country posting")

    return (
        harvest("greenhouse", rich, GH_RICH, 240)
        + harvest("ashby", sorted(set(by_ats.get("ashby", []))), ASHBY, 240)
        + harvest("lever", sorted(set(by_ats.get("lever", []))), LEVER, 120)
    )


# --------------------------- the three questions ------------------------------


def cost() -> None:
    """Which call carries the department, per provider, on one real board each."""
    print("\n== COST: does it arrive in a call the build already makes? ==")
    for label, url, timeout in (
        ("greenhouse content=false", GH_CHEAP, 60),
        ("greenhouse content=true", GH_RICH, 240),
    ):
        started = time.monotonic()
        status, body = get(url.format(slug="grafanalabs"), timeout)
        jobs = json.loads(body)["jobs"] if status == 200 else []
        stated = sum(1 for job in jobs if job.get("departments"))
        print(
            f"  {label:26s} {len(body) / 1e6:6.2f}MB  {time.monotonic() - started:5.1f}s  "
            f"{stated}/{len(jobs)} jobs carry `departments`"
        )
    print("  ashby / lever: one call, and it is the call the build already makes")


def coverage(rows: list[dict[str, Any]]) -> None:
    print("\n== COVERAGE: what share of postings state one? ==")
    print(f"  {'ats':11s} {'posts':>6s} {'department':>16s} {'team':>16s} {'either':>16s}")
    for ats in ("greenhouse", "ashby", "lever", "ALL"):
        group = rows if ats == "ALL" else [r for r in rows if r["ats"] == ats]
        if not group:
            continue
        counts = [
            sum(1 for r in group if r[field])
            for field in ("departments", "teams")
        ]
        either = sum(1 for r in group if r["departments"] or r["teams"])
        cells = "".join(f"{n:10d} {100 * n / len(group):5.1f}%" for n in (*counts, either))
        print(f"  {ats:11s} {len(group):6d}{cells}")


def vocabulary(rows: list[dict[str, Any]], table: list[tuple[str, re.Pattern[str]]]) -> None:
    """What the stated values ARE, and how many land on a name the site already
    uses. A department nothing can map is a label, not a filter."""
    print("\n== VOCABULARY: canonical, or whatever somebody typed? ==")
    for ats in ("greenhouse", "ashby", "lever"):
        said = [d for r in rows if r["ats"] == ats for d in r["departments"]]
        if not said:
            continue
        tally = collections.Counter(said)
        once = sum(1 for value in tally.values() if value == 1)
        placeable = sum(n for value, n in tally.items() if classify(value, table))
        print(
            f"\n  {ats}: {len(said)} statements, {len(tally)} distinct "
            f"({once} said once), {100 * placeable / len(said):.1f}% of statements land "
            f"on a name the site's own map recognises"
        )
        for value, n in tally.most_common(12):
            print(f"    {n:5d}  {classify(value, table) or '-':28s}  {value[:60]}")


def decide(rows: list[dict[str, Any]], table: list[tuple[str, re.Pattern[str]]]) -> None:
    """The kill criterion, on the only postings that can move it: the ones the
    title map cannot place."""
    print("\n== THE DECIDER: what the board states where the title map gives up ==")
    ours = [(r, classify(r["title"], table)) for r in rows]
    placed = [r for r, name in ours if name]
    unplaced = [r for r, name in ours if not name]
    print(f"  the site's map places {len(placed)}/{len(rows)} "
          f"({100 * len(placed) / len(rows):.1f}%) of these postings, "
          f"{len(unplaced)} unclassified")

    if not unplaced:
        return
    stated = [r for r in unplaced if r["departments"]]
    usable = [r for r in stated if classify(r["departments"][0], table)]
    print(f"  of the {len(unplaced)} unclassified, {len(stated)} "
          f"({100 * len(stated) / len(unplaced):.1f}%) carry a board-stated department, "
          f"and {len(usable)} of those state a name the site's map recognises")
    gain = 100 * len(usable) / len(rows)
    print(f"  BEST CASE GAIN over the whole set: +{gain:.1f} percentage points "
          f"({100 * len(placed) / len(rows):.1f}% -> "
          f"{100 * (len(placed) + len(usable)) / len(rows):.1f}%)")

    print("\n  what the boards call the titles we cannot place (top 15):")
    for value, n in collections.Counter(
        r["departments"][0] for r in stated
    ).most_common(15):
        print(f"    {n:5d}  {classify(value, table) or '-':28s}  {value[:60]}")

    print("\n  a sample of the titles themselves, with what their board says:")
    for row in unplaced[:12]:
        said = row["departments"][0] if row["departments"] else "(states none)"
        print(f"    {row['title'][:48]:50s} -> {said[:40]}")

    agreement(ours, table)


def agreement(
    ours: list[tuple[dict[str, Any], str | None]],
    table: list[tuple[str, re.Pattern[str]]],
) -> None:
    """Where the title map and the board BOTH answer, how often they answer the
    same thing — the other half of the criterion, since a stated department that
    contradicts the title is the wrong the derivation is accused of."""
    print("\n== where both speak, do they agree? ==")
    both = [
        (row["title"], name, row["departments"][0], theirs)
        for row, name in ours
        if name and row["departments"]
        and (theirs := classify(row["departments"][0], table)) is not None
    ]
    if not both:
        return
    differ = [x for x in both if x[1] != x[3]]
    print(f"  {len(both) - len(differ)}/{len(both)} agree "
          f"({100 * (len(both) - len(differ)) / len(both):.1f}%), {len(differ)} differ")
    for title, name, said, theirs in differ[:12]:
        print(f"    {title[:42]:44s} we:{name:26s} board:{said[:22]:24s} ->{theirs}")


def main() -> int:
    table = site_map()
    print(f"== the site's map, read from site/index.html: {len(table)} rules ==")
    cost()

    print("\n== building the corpus ==")
    rows = corpus()
    if not rows:
        print("\nNO POSTINGS FETCHED — nothing measured.")
        return 1
    print(f"\n{len(rows)} target-country postings across "
          f"{len({(r['ats'], r['slug']) for r in rows})} boards. "
          f"{FETCHED[0] / 1e6:.0f}MB fetched.")

    coverage(rows)
    vocabulary(rows, table)
    decide(rows, table)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
