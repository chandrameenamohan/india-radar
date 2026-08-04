#!/usr/bin/env python3
"""Build design/fixture-v2: the world corpus plus the attributes we already had.

ROCKETSHIP.md's finding was that the funding story is not missing from the
world, it is missing from companies.json because the pipeline fetches it and
discards it. This script is the render-what-we-download step, done as a fixture
so the product round can build against it without touching src/ or data/ —
both of which belong to the loop.

The founder's decision (2026-08-04) governs the shape: keep all 789, cut
nothing, and give every company its own stated credential. A CB Insights row is
not a company missing funding data; it is a company whose credential is "on a
third party's tracker", sourced and linkable, beside "YC W21" and "Form D".

Three merges, all from payloads the nightly already fetches:
  - YC directory (one GET, all.json): batch, status, team_size, top_company
  - corpus.json: stage — present on 1,881 rows, dropped by build.py's copy list
  - normalised places and departments, added BESIDE the source strings, never
    replacing them: the board's own words stay renderable as evidence.

ponytail: name-keyed merges and a hand alias table. Ceiling: a company whose YC
directory name differs from its corpus name silently gets no YC block (measured
below and printed); promote to slug-matching if the miss list grows.
"""
import json
import pathlib
import re
import urllib.request

HERE = pathlib.Path(__file__).parent
CLONE = pathlib.Path(
    "/private/tmp/claude-505/-Users-ralph-sennamind-next-rocket-ship/"
    "60ce8322-0ae6-42f9-94e7-e4244f7b3e1e/scratchpad/buildclone/data"
)
OUT = HERE / "fixture-v2"
YC_API = "https://yc-oss.github.io/api/companies/all.json"

# The top collisions among 2,318 department strings, measured. Everything else
# passes through as itself — an alias table that guessed would be a claim.
DEPT = {
    "software engineering": "Engineering",
    "engineering": "Engineering",
    "eng": "Engineering",
    "gtm": "Go To Market",
    "go to market": "Go To Market",
    "go-to-market": "Go To Market",
    "sales": "Sales",
    "marketing": "Marketing",
    "people": "People",
    "people & talent": "People",
    "recruiting": "People",
    "talent": "People",
    "design": "Design",
    "product": "Product",
    "product management": "Product",
    "operations": "Operations",
    "ops": "Operations",
    "finance": "Finance",
    "legal": "Legal",
    "data": "Data",
    "data science": "Data",
    "security": "Security",
    "customer success": "Customer Success",
    "support": "Customer Success",
    "customer support": "Customer Success",
}

CITY = {
    "sf": "San Francisco",
    "san francisco bay area": "San Francisco",
    "nyc": "New York",
    "new york city": "New York",
    "ny": "New York",
    "london, uk": "London",
    "bengaluru": "Bengaluru",
    "bangalore": "Bengaluru",
}


def place(loc: str) -> str:
    """One canonical place name from one board-typed location string.

    'San Francisco, California, United States' → 'San Francisco'. Remote
    variants collapse to 'Remote' — the workplace field, not this, is the
    authority on remoteness; this is only a grouping key.
    """
    s = loc.strip()
    if re.search(r"\bremote\b", s, re.I):
        return "Remote"
    head = s.split(",")[0].strip()
    head = re.sub(r"\s+", " ", head)
    return CITY.get(head.lower(), head)


def dept(d: str | None) -> str | None:
    if not d:
        return None
    return DEPT.get(d.strip().lower(), d.strip())


def enrich(companies: list[dict], stage: dict, yc: dict) -> tuple[int, int]:
    """Merge stage and the YC block onto each company; returns (hit, miss)."""
    yc_hit = yc_miss = 0
    for c in companies:
        c["stage"] = stage.get(c["name"])
        from_yc = "ycombinator" in (c.get("source_url") or "")
        entry = yc.get(c["name"]) if from_yc else None
        if from_yc:
            yc_hit, yc_miss = yc_hit + bool(entry), yc_miss + (not entry)
        c["yc"] = (
            {
                "batch": entry.get("batch"),
                "status": entry.get("status"),
                "team_size": entry.get("team_size"),
                "top_company": bool(entry.get("top_company")),
            }
            if entry
            else None
        )
        for role in c.get("roles", []):
            role["places"] = sorted({place(loc) for loc in (role.get("locations") or [])})
            role["dept_norm"] = dept(role.get("department"))
    return yc_hit, yc_miss


def main() -> None:
    doc = json.loads((CLONE / "companies.json").read_text())
    companies = doc["companies"] if isinstance(doc, dict) else doc
    corpus = json.loads((CLONE / "corpus.json").read_text())["companies"]
    stage = {c["name"]: c.get("stage") for c in corpus if c.get("stage")}

    req = urllib.request.Request(YC_API, headers={"User-Agent": "roleatlas-fixture"})
    with urllib.request.urlopen(req) as r:
        yc = {c["name"]: c for c in json.load(r)}

    yc_hit, yc_miss = enrich(companies, stage, yc)

    OUT.mkdir(exist_ok=True)
    (OUT / "companies.json").write_text(json.dumps(doc, ensure_ascii=False))

    # The card shard: everything a company card needs, none of the role rows.
    # PRODUCT-1's M1 is first card under 1.5s; 12MB of roles is not that.
    cards = []
    for c in companies:
        roles = c.get("roles", [])
        by_dept: dict[str, int] = {}
        by_place: dict[str, int] = {}
        for r in roles:
            if r.get("dept_norm"):
                by_dept[r["dept_norm"]] = by_dept.get(r["dept_norm"], 0) + 1
            for p in r.get("places", []):
                by_place[p] = by_place.get(p, 0) + 1
        cards.append(
            {
                "name": c["name"],
                "slug": c.get("slug"),
                "ats": c.get("ats"),
                "roles_open": len(roles),
                "depts": dict(sorted(by_dept.items(), key=lambda kv: -kv[1])),
                "places": dict(sorted(by_place.items(), key=lambda kv: -kv[1])),
                "amount": c.get("amount"),
                "currency": c.get("currency"),
                "round_letter": c.get("round_letter"),
                "date": c.get("date"),
                "stage": c.get("stage"),
                "source_url": c.get("source_url"),
                "qualified_by": c.get("qualified_by"),
                "yc": c.get("yc"),
            }
        )
    (OUT / "cards.json").write_text(json.dumps(cards, ensure_ascii=False))

    for f in ("first-seen.json", "descriptions.json", "build-report.json"):
        if (CLONE / f).exists():
            (OUT / f).write_text((CLONE / f).read_text())

    places = {p for c in companies for r in c.get("roles", []) for p in r["places"]}
    print(f"{len(companies)} companies · YC merged {yc_hit}, missed {yc_miss}")
    print(f"stage present on {sum(1 for c in companies if c.get('stage'))}")
    print(f"places: 3632 strings → {len(places)} canonical")
    print(f"cards.json: {len(cards)} cards, {(OUT/'cards.json').stat().st_size//1024}KB")


if __name__ == "__main__":
    main()
