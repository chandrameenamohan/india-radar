#!/usr/bin/env python3
"""r04-a's two build artifacts. Reads design/fixture-v2, writes into this
directory only.

PRODUCT-1 §7 names two build costs before anything on the page is possible:
normalise the department and location strings, and shard the corpus so a card
paints in under 1.5s. This script is both, done as a fixture-side step so the
renderer stays a renderer.

  seed.js    the first screen, inlined as a script so the first card paints
             from the second round trip and never waits on 470KB of cards.
  grid.json  per company, role counts by (department family × city). The two
             controls need joint counts — a company with 48 engineering roles
             and 20 San Francisco roles may have none in both — and joining
             them client-side means holding 9.8MB before the first click.

Both are derived, never authored: every number below is counted out of
../../fixture-v2/, and the page re-renders from cards.json the moment it
lands, so a stale seed shows up as a visible reflow rather than a quiet lie.

The department families are the one judgement call in here. 2,300 board-typed
department strings do not group themselves; the regexes below group 23,044 of
27,689 roles and the remaining 4,645 match no family and are counted, named,
and printed on the page rather than dropped. `?` is that bucket. It is not an
"other" family — you cannot select it — it is the number the yield line owes
the reader when a department filter is on.
"""
import collections
import json
import pathlib
import re

HERE = pathlib.Path(__file__).parent
FIX = HERE / ".." / ".." / "fixture-v2"

# Ordered: first match wins, so the narrower families come before `sales`,
# whose "account"/"growth" would otherwise swallow Account Security and
# Growth Engineering.
FAMILIES = [
    ("engineering", r"engineer|software|infrastructure|platform|devops|sre|"
                    r"technolog|technical|developer|backend|frontend|full ?stack|"
                    r"mobile|ios|android|architec|\bqa\b|quality assurance|"
                    r"firmware|hardware|robotic|machine learning|applied ai|"
                    r"\btech\b|\bit\b|\bepd\b|r&d"),
    ("research", r"research|scientist|\bscience"),
    ("data", r"\bdata\b|analytic|analyst|business intelligence"),
    ("design", r"design|\bux\b|\bui\b|creative|brand"),
    ("product", r"product"),
    ("security", r"security|infosec"),
    ("clinical", r"clinic|medical|health|nurse|physician|pharma"),
    ("finance", r"financ|accounting|treasur|\btax\b|audit"),
    ("legal", r"legal|complian|policy|regulat|trust & safety|\brisk\b"),
    ("people", r"people|talent|recruit|human resource|\bhr\b|workplace"),
    ("support", r"customer|support|success|experience|community"),
    ("marketing", r"marketing|communications|content|demand gen"),
    ("operations", r"operation|\bops\b|supply|logistic|program|project|"
                   r"strateg|manufactur"),
    ("sales", r"sales|revenue|account|go ?to ?market|\bgtm\b|"
              r"business development|commercial|partnership|growth|field"),
]
FAM = [(n, re.compile(p, re.I)) for n, p in FAMILIES]

GATE_NAME = {
    "ycombinator.com": "Y Combinator",
    "cbinsights.com": "CB Insights",
    "sec.gov": "SEC EDGAR",
    "forbes.com": "Forbes",
    "techcrunch.com": "TechCrunch",
    "finsmes.com": "FinSMEs",
}

# `place()` in fixture2.py already took 'San Francisco, California, United
# States' down to a head. These are the two shapes that survived it: a
# workplace word glued to the front, and an office suffix on the back.
PREFIX = re.compile(r"^(hybrid|onsite|remote|on-site|in-office|in office)\s*[-–—:]\s*", re.I)
SUFFIX = re.compile(r"\s+(HQ|Office|Area)$", re.I)


def family(dept: str | None) -> str | None:
    if not dept:
        return None
    for name, pat in FAM:
        if pat.search(dept):
            return name
    return None


def city(p: str, known: set[str]) -> str:
    """Two passes, because one is not safe. 'San Francisco HQ' and 'San
    Francisco' are one place; 'Mercor HQ' is not a place called Mercor. The
    office suffix only comes off when what is left is a place the corpus
    already names on its own — `known`, counted in the first pass."""
    s = PREFIX.sub("", p).strip()
    t = SUFFIX.sub("", s).strip()
    return t if (t != s and t in known) else (s or p)


def main() -> None:
    cards = json.loads((FIX / "cards.json").read_text())
    corpus = json.loads((FIX / "companies.json").read_text())
    report = json.loads((FIX / "build-report.json").read_text())
    seen = json.loads((FIX / "first-seen.json").read_text())
    companies = {c["slug"]: c for c in corpus["companies"]}

    heads = collections.Counter()
    for c in corpus["companies"]:
        for role in c["roles"]:
            for p in role["places"]:
                heads[PREFIX.sub("", p).strip()] += 1
    known = {name for name, _ in heads.most_common(60)}

    grid: dict[str, dict[str, int]] = {}
    cities = collections.Counter()
    fams = collections.Counter()
    ungrouped = 0
    ungrouped_names = collections.Counter()

    for card in cards:
        c = companies[card["slug"]]
        g: collections.Counter = collections.Counter()
        for role in c["roles"]:
            f = family(role.get("dept_norm")) or "?"
            if f == "?":
                ungrouped += 1
                if role.get("dept_norm"):
                    ungrouped_names[role["dept_norm"]] += 1
            else:
                fams[f] += 1
            g[f"{f}|*"] += 1
            for place in {city(p, known) for p in role["places"]}:
                cities[place] += 1
                g[f"{f}|{place}"] += 1
                g[f"*|{place}"] += 1
        grid[card["slug"]] = dict(g)

    (HERE / "grid.json").write_text(json.dumps(grid, ensure_ascii=False, separators=(",", ":")))

    # The seed is the default view, in the default order: the giants hidden,
    # most roles open first. Whatever the page would have painted anyway.
    order = sorted(
        (c for c in cards if c["roles_open"] < 100),
        key=lambda c: (-c["roles_open"], c["name"]),
    )[:24]
    gates = collections.Counter()
    for c in cards:
        host = re.sub(r"^https?://(www\.)?([^/]+).*", r"\2", c["source_url"] or "")
        gates[GATE_NAME.get(host, host)] += 1

    seed = {
        "slugs": [c["slug"] for c in order],
        "cards": {c["slug"]: c for c in order},
        # Who admitted them, counted over all 789 — the answer to "how did
        # these companies get here" has to be on the first paint, not behind
        # the fetch of the other 765 cards.
        "gates": gates.most_common(),
        "with_amount": sum(1 for c in cards if c["amount"] is not None),
        # The corpus step's own counts. build-report.json starts at the 2,925
        # that qualified; these four are upstream of it and this fixture does
        # not carry corpus.json, so they are quoted (PRODUCT-1 §2, recomputed
        # 2026-08-04) and the sieve panel says so on the page.
        "corpus": {"read": 10125, "not_qualified": 6895, "not_software": 109, "ambiguous": 196},
        "report": {"corpus_size": report["corpus_size"], **report["counts"]},
        # first-seen.json's own note: a role is confirmed only where the
        # board was read on the previous snapshot AND on this one. The
        # unconfirmed 6,505 URLs mean "we looked for the first time", which
        # is not a fact about the role, so they are not carried. The 145
        # confirmed ones are, and they print as a date on a role row — never
        # as a badge, never as the word this page refuses to use.
        "first_seen": {
            url: day
            for day, s in seen.get("dates", {}).items()
            for url in s.get("confirmed", [])
        },
        # Counted here so the chip rail can print what each option holds
        # before it is clicked, on the first paint, without grid.json.
        "cities": cities.most_common(48),
        # The exact set the office-suffix fold is allowed to land on, so the
        # page filters role rows by the same rule the index was counted with.
        "fold_known": sorted(known),
        "families": fams.most_common(),
        "ungrouped": ungrouped,
        "ungrouped_top": ungrouped_names.most_common(6),
        "snapshot": corpus["snapshot"],
        "companies": len(cards),
        "roles": sum(c["roles_open"] for c in cards),
        "giants": sum(1 for c in cards if c["roles_open"] >= 100),
    }
    (HERE / "seed.js").write_text(
        "// Generated by build.py from ../../fixture-v2 — do not hand-edit.\n"
        "window.SEED = " + json.dumps(seed, ensure_ascii=False, separators=(",", ":")) + ";\n"
    )

    print(f"grid.json  {len(grid)} companies, {(HERE/'grid.json').stat().st_size//1024}KB")
    print(f"seed.js    {len(order)} cards, {(HERE/'seed.js').stat().st_size//1024}KB")
    print(f"families   {dict(fams)}")
    print(f"ungrouped  {ungrouped} roles across {len(ungrouped_names)} department names")
    print(f"cities     {len(cities)} canonical, top: {cities.most_common(6)}")


if __name__ == "__main__":
    main()
