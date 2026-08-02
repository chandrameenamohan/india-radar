"""T9.1 — what Companies House actually answers for the names this corpus holds.

Run by hand, against the live API and live company websites, and NOT part of
`make check`: the gate must never depend on somebody else's uptime
(VERIFICATION.md).

    python -m learning-tests.companies_house_live           # the register, all 220
    python -m learning-tests.companies_house_live --sites   # what the companies say
    python -m learning-tests.companies_house_live monzo     # one name, verbosely

The question is not "can we fetch a company" — that is one authenticated GET. It
is whether anything short of the company's own word says WHICH company a name is,
and the first probe already says no: `q=monzo` ranks `BRAMAND LTD` (dissolved, a
sheep farm's postcode in Gwynedd, formerly named `MONZO LTD`) above `MONZO BANK
LIMITED`. Every figure this prints is in FINDINGS under "Companies House".
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from src import uk

#: Where the register's answers land, so the matcher can be changed and
#: re-measured without a second half-hour pull.
MEASURED = Path("learning-tests/companies_house_measured.json")


def uk_names() -> list[dict[str, str | None]]:
    """Every listed company with a UK role, its website and its round date.

    The date is here because it is the one fact about a company that comes from a
    source Companies House has never heard of (EDGAR, Forbes, FinSMEs), which
    makes it corroboration a name-matcher cannot fake.
    """
    listed = json.loads(uk.LISTED.read_text())["companies"]
    sites = {c["name"]: c.get("website") for c in json.loads(uk.CORPUS.read_text())["companies"]}
    return [
        {"name": row["name"], "date": row["date"], "website": sites.get(row["name"])}
        for row in listed
        if "United Kingdom" in row["countries"]
    ]


def one(name: str, key: str) -> None:
    """Everything the register says about one name, printed."""
    found = uk.search(key, name) or []
    print(f"{name}: {len(found)} search hits")
    for i, item in enumerate(found):
        print(f"  {i}. {item.get('title')!r} {item.get('company_number')} "
              f"{item.get('company_status')} | {item.get('address_snippet')}")
    tier, matched = uk.find(name, uk.candidates(found))
    print(f"  name rule: {tier or 'nothing'} -> {[m['name'] for m in matched]}")


def register(key: str) -> int:
    """Phase 1 — what the register offers for each name, and what a name-only
    rule would have published.

    The counterfactual is the point. This is the rule `src/mca.py` publishes on,
    run against Companies House, so the number it produces is the number that
    would have gone on the site if T4.4's doctrine had been carried over whole.
    """
    companies = uk_names()
    print(f"{len(companies)} listed companies have a UK role\n")

    tiers: Counter[str] = Counter()
    statuses: Counter[str] = Counter()
    sic: Counter[str] = Counter()
    hits: Counter[int] = Counter()
    ambiguous: list[str] = []
    refused: list[str] = []
    would_publish: list[tuple[str, str, str, str, list[str]]] = []
    rows = []

    for i, company in enumerate(companies, 1):
        name = str(company["name"])
        raw = uk.search(key, name) or []
        # Profiled only where the name rule can reach the hit at all: this is the
        # counterfactual run, so it spends calls exactly where a name-only matcher
        # would have, and nowhere else.
        reachable = [c for c in uk.candidates(raw) if uk.find(name, [c])[0]]
        found = [uk.profile(key, c["number"]) or c for c in reachable]
        hits[len(raw)] += 1
        tier, matched = uk.find(name, found)
        tiers[tier or "none"] += 1
        if tier == uk.EXACT and len(matched) > 1:
            ambiguous.append(f"{name} -> {[m['name'] for m in matched]}")
        alive = []
        for match in matched:
            statuses[match["status"] or "(blank)"] += 1
            for code in match["sic"]:
                sic[code] += 1
            if why := uk.disqualified(match, str(company["date"] or "") or None):
                refused.append(f"{name}: {match['name']} {match['number']} — {why}")
            else:
                alive.append(match)
        if tier == uk.EXACT and len(alive) == 1:
            would_publish.append((name, alive[0]["name"], alive[0]["number"],
                                  alive[0]["incorporated"], alive[0]["sic"]))
        rows.append({"name": name, "date": company["date"], "tier": tier, "candidates": found})
        print(f"  {i:3d}/{len(companies)}  {name:<28} {tier or '-':<8} "
              f"{[m['name'] for m in matched]}", flush=True)

    MEASURED.write_text(json.dumps(rows, indent=1) + "\n")

    print(f"\ntiers:        {dict(tiers)}")
    print(f"search hits:  {dict(sorted(hits.items()))}")
    print(f"status:       {dict(statuses)}")
    print(f"top SIC:      {sic.most_common(15)}")
    print(f"ambiguous at the exact tier ({len(ambiguous)}):")
    for line in ambiguous:
        print(f"  {line}")
    print(f"refused by corroboration ({len(refused)}):")
    for line in refused:
        print(f"  {line}")
    print(f"\nA NAME-ONLY RULE WOULD PUBLISH {len(would_publish)} of {len(companies)}:")
    for line in sorted(would_publish, key=lambda row: row[3]):
        print(f"  {line[0]:<24} {line[1]:<44} {line[2]}  {line[3]}  {line[4]}")
    print("\nSort that by incorporation date: the registrations from before the "
          "listed company existed are the false positives, and they are the "
          "reason nothing above this line is published.")
    return 0


def sites() -> int:
    """Phase 2 — does the company's OWN website state a number, and on what page?

    The Companies (Trading Disclosures) Regulations require a UK company to state
    its registered number on its websites, so where the corpus has an address for
    a company, the company itself is supposed to be answering this question. This
    measures how often it actually does, and which paths are worth fetching.
    """
    #: Every path worth trying once, so the four that survive into
    #: `uk.LEGAL_PAGES` are a measurement rather than a guess.
    paths = ["", "/terms", "/legal", "/privacy", "/imprint", "/terms-of-service",
             "/terms-and-conditions", "/privacy-policy", "/legal/terms", "/legal/privacy",
             "/about", "/contact", "/legal-notice", "/cookie-policy", "/terms-of-use",
             "/company", "/en/legal", "/legal/terms-of-service", "/policies/terms",
             "/privacy-notice"]

    companies = uk_names()
    paid: Counter[str] = Counter()
    stated, silent, unreachable, nowhere = 0, 0, 0, 0

    for company in companies:
        website = company["website"]
        if not website:
            nowhere += 1
            print(f"  {company['name']:<26} — no website in the corpus", flush=True)
            continue
        found, where = uk.declared(website, paths)
        for path in paths:
            got = uk.fetch(website.rstrip("/") + path)
            if got and uk.numbers(got):
                paid[path or "/"] += 1
        if found:
            stated += 1
        elif where == "unreachable":
            unreachable += 1
        else:
            silent += 1
        print(f"  {company['name']:<26} {sorted(found)} {where}", flush=True)

    print(f"\n{stated} of {len(companies)} state a company number "
          f"({silent} silent, {unreachable} unreachable, {nowhere} with no website)")
    print(f"pages that paid: {paid.most_common()}")
    return 0


def main(argv: list[str]) -> int:
    key = uk.api_key()
    if not key:
        print("no UK_COMPANY_HOUSE_KEY", file=sys.stderr)
        return 1
    if argv and argv[0] == "--sites":
        return sites()
    if argv:
        one(argv[0], key)
        return 0
    return register(key)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
