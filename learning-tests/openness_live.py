#!/usr/bin/env python3
"""T8.1 (c, d) — how often do openness phrases actually occur, and is Japan English?

SPEC feature 15 bets that posting prose says whether a company will hire from
abroad. T8.1's kill criterion prices that bet: under ~2% of postings carrying any
phrase and feature 15 is a heuristic with nothing to be heuristic about.

Run: .venv/bin/python learning-tests/openness_live.py   (1m55s and 270MB, measured)

ponytail: no cache, so re-running refetches all 270MB. Ceiling: the day someone
wants to iterate on the phrase list rather than on the corpus, dump `corpus()` to
a file first — the analysis below is a second of CPU on two minutes of network.

WHAT WAS MEASURED (2026-07-30, 4,311 real postings in the 15 target countries,
across 277 live boards — the whole of data/slugs.json, not a sample):

  THE KILL CRITERION DID NOT FIRE, by a factor of five. 511 postings (11.85%)
  carry at least one phrase from the list T8.1 was handed; 44 boards of 277
  (15.88%). Every stricter recount below still clears 2%. Feature 15 proceeds.

  But three of the seven positive phrases are junk, and the negatives are worse:

  1. "work from anywhere" IS NOT AN OPENNESS SIGNAL. 74 postings, and 42 of them
     are the time-boxed holiday perk — "4 weeks work from anywhere per year".
     Wired into T8.3 as a positive it would report heidihealth and marshmallow as
     hiring from abroad on the strength of their PTO policy.

  2. "we sponsor" hits exactly 2 boards, and 27 of its 58 postings are physicsx's
     "we sponsor bright women ... through their university degrees". Charity, not
     immigration.

  3. A bare `sponsor` stem is unusable in the other direction too: 48 postings say
     "executive sponsor" or "customer sponsor" — sales vocabulary, in postings
     that say nothing about visas.

  4. "visa sponsorship" IS POLARITY-BLIND. 132 postings, of which anthropic is 71
     ("visa sponsorship: we do sponsor visas! however, we aren't able to
     successfully sponsor visas for every role") and pleo is 19 ("we are unable to
     offer visa sponsorship for this role"). The same 16 characters are a yes, a
     qualified yes and a flat no. The words around it decide, not the phrase.

  5. THE NEGATIVE LIST HAS ALMOST NO RECALL. The five negatives T8.1 was handed
     find 37 postings between them, and one finds zero. The negatives that are
     really out there, in the same corpus:
       117  "right to work in"      (15 boards)  vs 2 for "must have the right to work"
       119  okx's "...and do not require okx's sponsorship of a visa"
        71  anthropic's "aren't able to successfully sponsor"
        21  "unable to offer visa sponsorship"
     Counted by visa-context proximity instead of by fixed phrase, NEGATIVES
     OUTNUMBER POSITIVES: 148 postings negative-only (3.43%), 107 positive-only
     (2.48%), 76 carrying both (1.76%).

  6. THE SIGNAL IS A COMPANY ATTRIBUTE WEARING A ROLE'S CLOTHES. "relocation
     support" is 170 postings and 113 of them are helsing; "relocation package" is
     63 postings and 61 of them are n26; anthropic alone is 54% of "visa
     sponsorship". It is boilerplate stamped on every posting a company publishes,
     so a per-role field will show a company's whole board flipping together, and
     the honest headline number is the board one (15.88%), not the posting one.

  7. Japan is mostly English. 255 JP postings across 54 boards; 20 (7.8%) are over
     10% non-ASCII, spread over 12 boards, and 5 (2.0%) are over 50%. The UK
     control is 0 of 1,676 over 10% — nothing English-language scores above the
     threshold, so the ratio separates the two cleanly. 26 of the 255 JP postings
     match a listed phrase, so Japan is not a phrase desert either.

CONSEQUENCE FOR T8.3: keep "visa sponsorship" / "relocation support" / "relocation
package" / "sponsorship" but read the ~60 characters before them for a negation cue
rather than treating the phrase as a polarity. Drop "work from anywhere" and
"we sponsor". Add "right to work in" and "do not require ... sponsorship". And
`no` deserves the same care as `yes`: it is the more common answer.
"""
from __future__ import annotations

import collections
import html
import json
import re
import statistics
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.net import get  # noqa: E402

GH_CHEAP = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=false"
GH_RICH = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
ASHBY = "https://api.ashbyhq.com/posting-api/job-board/{slug}"
LEVER = "https://api.lever.co/v0/postings/{slug}?mode=json"

WORKERS = 10

#: Every byte this script pulls, so the "payload cost, not call cost" claim in
#: FINDINGS is a number rather than an impression. Written from pool threads, and
#: `+=` on an int is not atomic — but the loss is a few boards' bytes off a total
#: reported to one decimal place in megabytes.
#: ponytail: no lock. Ceiling: put one in the day a byte total decides anything.
FETCHED = [0]


def fetch(url: str, timeout: int) -> tuple[int, str]:
    """`net.get`, with the response size added to the running total."""
    status, body = get(url, timeout)
    FETCHED[0] += len(body.encode())
    return status, body

#: The phrase list T8.1 was handed, measured as given so the numbers answer the
#: question that was asked. What it gets wrong is in the docstring, not in here.
POSITIVE = [
    "visa sponsorship", "sponsorship available", "work from anywhere",
    "remote worldwide", "relocation support", "relocation package", "we sponsor",
]
NEGATIVE = [
    "unable to sponsor", "cannot sponsor", "no visa sponsorship",
    "must have the right to work", "authorized to work in",
]

#: Phrasings found by reading the corpus rather than by guessing at it — reported
#: beside the handed list so T8.3 can see what the handed list is missing.
IN_THE_WILD = [
    "right to work in", "do not require", "aren't able to successfully sponsor",
    "unable to offer visa sponsor", "not able to provide visa sponsor",
    "not currently able to sponsor", "sponsorships are available",
]

#: Deliberately rough — T8.2 owns the real matcher and its false-positive fixture.
#: This one only has to bucket a corpus for counting, and it is allowed to miss a
#: city; what it must not do is put a UK posting in the Japan bucket.
#: ponytail: no word boundaries, no ISO codes. Ceiling: the moment a number from
#: this script is quoted per-country rather than in aggregate, use src/countries.py.
COUNTRY = {
    "UK": ["united kingdom", ", uk", "(uk)", "england", "london", "manchester", "edinburgh",
           "scotland", "cambridge, uk", "bristol", "leeds", "glasgow", "belfast", "wales"],
    "IE": ["ireland", "dublin", "cork, ireland", "galway"],
    "DE": ["germany", "berlin", "munich", "münchen", "hamburg", "frankfurt", "cologne",
           "köln", "stuttgart"],
    "NL": ["netherlands", "amsterdam", "rotterdam", "utrecht", "eindhoven", "the hague"],
    "FR": ["france", "paris", "lyon", "toulouse", "marseille", "bordeaux"],
    "ES": ["spain", "madrid", "barcelona", "valencia, spain", "malaga", "málaga", "seville"],
    "SE": ["sweden", "stockholm", "gothenburg", "göteborg", "malmö"],
    "DK": ["denmark", "copenhagen", "københavn", "aarhus"],
    "NO": ["norway", "oslo", "bergen, norway", "trondheim"],
    "FI": ["finland", "helsinki", "espoo", "tampere"],
    "JP": ["japan", "tokyo", "osaka", "kyoto", "yokohama", "日本", "東京"],
    "SG": ["singapore"],
    "AU": ["australia", "sydney", "melbourne", "brisbane", "perth, austral", "canberra",
           "adelaide"],
    "NZ": ["new zealand", "auckland", "wellington, new zealand", "christchurch"],
}

TAG = re.compile(r"<[^>]+>")
SPACE = re.compile(r"\s+")

#: The 60 characters before a `sponsor*` — long enough to hold "we are not able to
#: provide visa", short enough that the previous sentence's "not" does not leak in.
NEAR_SPONSOR = re.compile(r"(.{0,60})\bsponsor")
NEGATION = re.compile(
    r"\b(not|no|unable|unwilling|cannot|can't|aren't|isn't|won't|without|neither|nor)\b"
)
VISA_CONTEXT = re.compile(r"visa|immigration|work permit|right to work")

#: "4 weeks work from anywhere per year" — the holiday perk, not a hiring policy.
PERK = re.compile(
    r"(weeks?|days?|months?)\s+(of\s+)?work from anywhere|work from anywhere\s+(for|per)\b"
)


def plain(markup: str) -> str:
    """Tags out, entities in, whitespace flattened, lowercased — the one text shape
    every count below is taken over. Greenhouse double-escapes, hence two unescapes.
    """
    return SPACE.sub(" ", TAG.sub(" ", html.unescape(html.unescape(markup or "")))).lower()


def countries(locations: list[Any]) -> list[str]:
    blob = " ; ".join(place.lower() for place in locations if isinstance(place, str))
    return sorted(code for code, keys in COUNTRY.items() if any(k in blob for k in keys))


def _row(ats: str, slug: str, location: str, found: list[str], text: str) -> dict[str, Any]:
    return {"ats": ats, "slug": slug, "loc": location, "countries": found, "text": text}


def greenhouse(slug: str) -> list[dict[str, Any]] | None:
    status, body = fetch(GH_RICH.format(slug=slug), 240)
    if status != 200:
        return None
    try:
        jobs = json.loads(body)["jobs"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return None
    rows = []
    for job in jobs:
        where = (job.get("location") or {}).get("name") or ""
        if found := countries([where]):
            rows.append(_row("greenhouse", slug, where, found, plain(job.get("content"))))
    return rows


def ashby(slug: str) -> list[dict[str, Any]] | None:
    status, body = fetch(ASHBY.format(slug=slug), 240)
    if status != 200:
        return None
    try:
        jobs = json.loads(body)["jobs"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return None
    rows = []
    for job in jobs:
        secondary = [e.get("location") if isinstance(e, dict) else e
                     for e in job.get("secondaryLocations") or []]
        where = job.get("location") or ""
        if found := countries([where, *secondary]):
            rows.append(_row("ashby", slug, where, found, plain(job.get("descriptionPlain"))))
    return rows


def lever(slug: str) -> list[dict[str, Any]] | None:
    """Lever's posting is four fields glued together — see descriptions_live.py, where
    reading `descriptionPlain` alone was measured to lose 62-77% of the text."""
    status, body = fetch(LEVER.format(slug=slug), 120)
    if status != 200:
        return None
    try:
        posts = json.loads(body)
    except json.JSONDecodeError:
        return None
    if not isinstance(posts, list):
        return None
    rows = []
    for post in posts:
        categories = post.get("categories") or {}
        places = categories.get("allLocations") or [categories.get("location")]
        if found := countries(places):
            whole = " ".join([post.get("description") or ""]
                             + [x.get("content") or "" for x in post.get("lists") or []]
                             + [post.get("additional") or ""])
            where = next((p for p in places if isinstance(p, str)), "")
            rows.append(_row("lever", slug, where, found, plain(whole)))
    return rows


def corpus() -> list[dict[str, Any]]:
    """Every posting in a target country, on every board in data/slugs.json.

    Greenhouse is fetched twice — once at content=false to find which boards have a
    target-country posting at all, then at content=true for only those. 163 of 422
    boards qualified, so the cheap pass avoids the 13-35x payload measured in
    descriptions_live.py on 259 boards that were never going to contribute a row.
    Ashby and Lever ship prose unconditionally, so there is nothing to skip and no
    first pass to make.

    A board that will not answer is counted and dropped, never counted as a board
    with no openness language — the same rule the probes follow.
    """
    slugs = json.loads((Path(__file__).resolve().parent.parent / "data/slugs.json").read_text())
    by_ats: dict[str, list[str]] = {}
    for entry in slugs.values():
        by_ats.setdefault(entry["ats"], []).append(entry["slug"])

    def interesting(slug: str) -> bool:
        status, body = fetch(GH_CHEAP.format(slug=slug), 60)
        if status != 200:
            return False
        try:
            jobs = json.loads(body)["jobs"]
        except (json.JSONDecodeError, KeyError, TypeError):
            return False
        return any(countries([(j.get("location") or {}).get("name") or ""]) for j in jobs)

    gh_all = sorted(set(by_ats.get("greenhouse", [])))
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        keeps = pool.map(interesting, gh_all)
        gh_slugs = [s for s, keep in zip(gh_all, keeps, strict=True) if keep]
    print(f"  greenhouse: {len(gh_slugs)}/{len(gh_all)} boards have a target-country posting")

    rows: list[dict[str, Any]] = []
    for label, harvest, board_slugs in (
        ("greenhouse", greenhouse, gh_slugs),
        ("ashby", ashby, sorted(set(by_ats.get("ashby", [])))),
        ("lever", lever, sorted(set(by_ats.get("lever", [])))),
    ):
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            results = list(pool.map(harvest, board_slugs))
        unreadable = sum(1 for r in results if r is None)
        got = [row for r in results if r for row in r]
        rows += got
        print(f"  {label:11s} {len(board_slugs):4d} boards ({unreadable} unreadable) "
              f"-> {len(got)} target-country postings")
    return rows


def table(rows: list[dict[str, Any]], phrases: list[str], boards: int) -> None:
    for phrase in phrases:
        hit = [r for r in rows if phrase in r["text"]]
        seen = {r["slug"] for r in hit}
        print(f"  {phrase:38s} {len(hit):5d} {100 * len(hit) / len(rows):6.2f}%  "
              f"{len(seen):4d} {100 * len(seen) / boards:6.2f}%")


def main() -> int:
    print("== building the corpus (two passes for Greenhouse, one for the others) ==")
    rows = corpus()
    if not rows:
        print("\nNO POSTINGS FETCHED — every board was unreadable. Nothing measured.")
        return 1
    boards = len({r["slug"] for r in rows})
    print(f"\n{len(rows)} postings across {boards} boards. "
          f"{FETCHED[0] / 1e6:.0f}MB fetched to get here.")

    tally: collections.Counter[str] = collections.Counter()
    for row in rows:
        tally.update(row["countries"])
    print("  by country:", "  ".join(f"{c}={n}" for c, n in tally.most_common()))
    print("  by ats:    ", dict(collections.Counter(r["ats"] for r in rows)))

    head = f"  {'phrase':38s} {'posts':>5s} {'post%':>7s}  {'brds':>4s} {'board%':>7s}"
    print(f"\n== the handed phrase list, counted by POSTING and by BOARD ==\n{head}")
    print("  -- positive --")
    table(rows, POSITIVE, boards)
    print("  -- negative --")
    table(rows, NEGATIVE, boards)

    positive = [r for r in rows if any(p in r["text"] for p in POSITIVE)]
    negative = [r for r in rows if any(p in r["text"] for p in NEGATIVE)]
    either = [r for r in rows if any(p in r["text"] for p in POSITIVE + NEGATIVE)]
    both = [r for r in positive if r in negative]
    for label, group in (("ANY positive", positive), ("ANY negative", negative),
                         ("EITHER (kill criterion)", either), ("both polarities", both)):
        seen = {r["slug"] for r in group}
        print(f"  {label:38s} {len(group):5d} {100 * len(group) / len(rows):6.2f}%  "
              f"{len(seen):4d} {100 * len(seen) / boards:6.2f}%")

    verdict = 100 * len(either) / len(rows)
    fires = "FIRES — T8.3 must be re-decided" if verdict < 2 else "does not fire"
    print(f"\n  KILL CRITERION (<~2% of postings carry any phrase): {verdict:.2f}% — {fires}")

    print("\n== how much of that is junk ==")
    wfa = [r for r in rows if "work from anywhere" in r["text"]]
    print(f"  'work from anywhere': {len(wfa)} postings, "
          f"{sum(1 for r in wfa if PERK.search(r['text']))} of them the time-boxed holiday perk")
    for phrase in ("we sponsor", "relocation support", "relocation package", "visa sponsorship"):
        per_board = collections.Counter(r["slug"] for r in rows if phrase in r["text"])
        top = per_board.most_common(3)
        print(f"  {phrase:20s} {sum(per_board.values()):4d} postings over {len(per_board)} boards; "
              f"top: {', '.join(f'{s}={n}' for s, n in top)}")
    stem = sum(1 for r in rows if re.search(r"executive sponsor|customer sponsor", r["text"]))
    print(f"  'executive/customer sponsor' (sales vocabulary): {stem} postings — "
          f"a bare `sponsor` stem is unusable")
    blind = [r for r in rows if "visa sponsorship" in r["text"]]
    flipped = sum(1 for r in blind if any(
        NEGATION.search(r["text"][max(0, m.start() - 70):m.start()])
        for m in re.finditer("visa sponsorship", r["text"])))
    print(f"  'visa sponsorship' with a negation cue in the 70 chars before it: "
          f"{flipped}/{len(blind)} — the phrase is not a polarity")

    print(f"\n== phrasings found by reading the corpus, not by guessing ==\n{head}")
    table(rows, IN_THE_WILD, boards)

    polarity(rows)
    japan(rows)
    return 0


def polarity(rows: list[dict[str, Any]]) -> None:
    """Every `sponsor*` that sits near visa vocabulary, split by whether the words
    just before it negate. This is the measurement the fixed-phrase tables cannot
    make, and it is the one that says `no` is the more common answer."""
    print("\n== polarity by proximity instead of by fixed phrase ==")
    counts: collections.Counter[str] = collections.Counter()
    for row in rows:
        text = row["text"]
        near = [m.group(1) for m in NEAR_SPONSOR.finditer(text)
                if VISA_CONTEXT.search(m.group(1))
                or VISA_CONTEXT.search(text[m.end():m.end() + 30])]
        if not near:
            counts["silent"] += 1
            continue
        negated = [bool(NEGATION.search(window)) for window in near]
        counts["negative only" if all(negated) else
               "positive only" if not any(negated) else "both in one posting"] += 1
    for label, n in counts.most_common():
        print(f"  {label:38s} {n:5d} {100 * n / len(rows):6.2f}%")


def japan(rows: list[dict[str, Any]]) -> None:
    """Non-ASCII density in Japan-located postings, against the UK as the control —
    a threshold is only meaningful if the language we can read scores near zero."""
    print("\n== Japan: how often is the posting not in English? ==")
    postings = [r for r in rows if "JP" in r["countries"]]
    britain = [r for r in rows if "UK" in r["countries"]]

    def non_ascii(text: str) -> float:
        dense = "".join(ch for ch in text if not ch.isspace())
        return sum(1 for ch in dense if ord(ch) > 127) / len(dense) if dense else 0.0

    jp_ratios = [non_ascii(r["text"]) for r in postings]
    uk_ratios = [non_ascii(r["text"]) for r in britain] or [0.0]
    if not jp_ratios:
        print("  no Japan postings in this run — not measured")
        return
    print(f"  {len(postings)} JP postings over {len({r['slug'] for r in postings})} boards; "
          f"median non-ASCII {statistics.median(jp_ratios):.3f} "
          f"(UK baseline {statistics.median(uk_ratios):.3f} over {len(britain)})")
    for cut in (0.05, 0.10, 0.20, 0.50):
        n = sum(1 for v in jp_ratios if v > cut)
        u = sum(1 for v in uk_ratios if v > cut)
        print(f"    over {cut:.2f}: JP {n:4d} ({100 * n / len(jp_ratios):5.1f}%)   "
              f"UK {u:4d} ({100 * u / len(uk_ratios):5.1f}%)")
    matched = sum(1 for r in postings if any(p in r["text"] for p in POSITIVE + NEGATIVE))
    print(f"  JP postings matching any handed phrase: {matched}/{len(postings)}")
    boards = collections.Counter(r["slug"] for r, v in zip(postings, jp_ratios, strict=True)
                                 if v > 0.10)
    print(f"  boards carrying the >0.10 postings: {dict(boards)}")


if __name__ == "__main__":
    raise SystemExit(main())
