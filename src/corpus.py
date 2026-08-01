"""Merge, dedup and qualify the funding corpus — T1.5 (SPEC features 1 and 2).

Sources emit one record per funding round; the corpus wants one row per company,
chosen the same way no matter what order the sources arrive in. So duplicates
collapse to the *strongest* round rather than the first one seen: a company that
raised Seed and later Series B qualifies on the B, whichever record the scraper
happened to yield first.

A company no qualifying rule admits is excluded and named in `unqualified` —
never silently dropped, because a corpus that shrinks quietly is
indistinguishable from a scraper that broke. Both kinds land there: the company
whose round was undisclosed, and the one a directory calls early-stage.
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from itertools import chain
from pathlib import Path
from typing import NamedTuple

from src import cbinsights, corrections, edgar, forbes, software, techcrunch, websites, yc
from src.finsmes import BASE, parse
from src.net import fetch
from src.record import Record

#: SPEC feature 2's proxy: with no stated letter, a disclosed round this size
#: stands in for "Series A or more".
#: ponytail: compared in the record's own currency. Every currency FinSMEs states
#: (USD/GBP/EUR) is within ~20% of USD, so an FX table would change no verdict.
#: Upgrade path: convert at the round's date if a weak currency ever appears.
MIN_AMOUNT = 5_000_000

#: ponytail: casefold + drop non-alphanumerics. Deliberately does NOT strip legal
#: suffixes, so "Acme" and "Acme Inc" stay distinct. With one source there are no
#: cross-source name variants to measure; add suffix stripping when T1.2–T1.4
#: produce a duplicate this misses. Registry-grade normalisation is T4.4's job.
_NOT_ALNUM = re.compile(r"[^a-z0-9]+")


class Company(Record):
    """A corpus row: the company's strongest known round, plus which rule
    qualified it. `qualified_by` is exactly one of `letter` or `amount`."""

    qualified_by: str


class Corpus(NamedTuple):
    companies: list[Company]
    unqualified: list[str]  # no rule admits them, so excluded and counted
    not_software: dict[str, str]  # outside SPEC's sectors — name -> the evidence
    ambiguous: dict[str, str]  # kept, but flagged for a human — name -> the evidence


def merge(*sources: Iterable[Record], corrected: Mapping[str, str] | None = None) -> Corpus:
    """Collapse funding records into one qualified row per distinct company.

    Deterministic in both directions: the surviving record for a company is the
    maximum under `_strength`, and the output is sorted, so shuffling the sources
    (or the records within them) yields an identical corpus.

    `corrected` is `corrections.load().websites` — the addresses a human found
    the sources stating wrongly. It wins over every source, because it is the
    only one of them that looked at the company's own site. Nothing else about a
    record is correctable here: the funding a source states is that source's
    claim, and the site renders it as one.
    """
    best: dict[str, Record] = {}
    addresses: dict[str, str] = {}
    for record in chain.from_iterable(sources):
        key = _NOT_ALNUM.sub("", record["name"].casefold())
        if key not in best or _strength(record) > _strength(best[key]):
            best[key] = record
        # A website belongs to the company, not to the round, so it survives its
        # record losing on strength: YC states an address for a company whose
        # strongest round came from EDGAR, which states none at all. Two sources
        # stating different addresses resolve by max() — arbitrary, but the same
        # arbitrary answer whatever order the sources arrive in.
        if website := record["website"]:
            addresses[key] = max(addresses.get(key, ""), website)

    companies: list[Company] = []
    unqualified: list[str] = []
    not_software: dict[str, str] = {}
    ambiguous: dict[str, str] = {}
    for key in sorted(best):
        record = best[key].copy()
        record["website"] = (corrected or {}).get(record["name"]) or addresses.get(key)
        # Sector before funding, because it is the more fundamental question: a
        # biotech's Series B is a real round we would still never list, so
        # judging its funding first would file it under the wrong reason. Both
        # doors are counted, so the totals hold either way.
        verdict, evidence = software.classify(record["name"])
        if verdict is software.Verdict.NOT_SOFTWARE:
            not_software[record["name"]] = evidence
            continue
        if verdict is software.Verdict.AMBIGUOUS:
            ambiguous[record["name"]] = evidence
        if rule := _qualified_by(record):
            companies.append(Company(**record, qualified_by=rule))
        else:
            unqualified.append(record["name"])

    return Corpus(companies, sorted(unqualified), not_software, ambiguous)


def _strength(record: Record) -> tuple[bool, str, int, str, str, str]:
    """Total order over rounds for the same company, independent of input order.

    **Qualifying evidence outranks a bigger number.** Two sources describing one
    company are complementary, not contradictory: YC calls Lob `Growth` and EDGAR
    reports it filing a $2M round, and both are true. Ranking on the amount alone
    let the $2M record win and then fail the $5M proxy, so a company three sources
    agree is past Series A left the corpus because one of them mentioned a small
    round. Measured when EDGAR landed: 4 companies demoted that way.

    After that, letter first (a later letter is a bigger round), then amount, then
    a stated stage. Date and URL are not signal — they are there so two
    equally-strong rounds still resolve to the same winner every run.
    """
    return (
        _qualified_by(record) is not None,
        record["round_letter"] or "",
        record["amount"] or 0,
        record["stage"] or "",
        record["date"] or "",
        record["source_url"],
    )


def _qualified_by(record: Record) -> str | None:
    """Which rule admits this company, or None if nothing does.

    Any stated letter qualifies: the parser only reads `Series <A-Z>`, and every
    such letter is A or later. Seed and pre-seed carry no letter and fall through
    to the amount proxy, which is exactly the case that proxy exists for.

    `stage` is the third rule and the weakest, so it is tried last. It exists
    because a directory can say *that* a company is past Series A without saying
    which letter or how much — YC labels Stripe, Razorpay and Groww `Growth` and
    a three-person current-batch company `Early`. Reading that as `letter="A"`
    would invent a round; excluding it would throw away the only qualifying
    evidence a whole source has. So the label qualifies as itself and the site
    says so.
    """
    if record["round_letter"]:
        return "letter"
    if record["amount"] is not None and record["amount"] >= MIN_AMOUNT:
        return "amount"
    if record["stage"] == "growth":
        return "stage"
    return None


def write(path: str | Path, corpus: Corpus) -> None:
    """Emit corpus.json. The excluded names ship with it — the count of what we
    couldn't judge, and of what we judged out of scope, is part of the corpus
    rather than a build-time aside. `ambiguous` is the read-me list: those
    companies ARE in the corpus, named so a human can overrule the machine."""
    Path(path).write_text(
        json.dumps(
            {
                "companies": corpus.companies,
                "unqualified": corpus.unqualified,
                "not_software": corpus.not_software,
                "ambiguous": corpus.ambiguous,
            },
            indent=2,
        )
        + "\n"
    )


def main() -> None:
    page = fetch(f"{BASE}/category/usa")
    # 10MB in one call, so it wants more than net.get's page-sized default.
    directory = fetch(yc.API, timeout=120)
    unicorns = fetch(cbinsights.UNICORNS, timeout=60)
    quarters = edgar.download()
    articles = techcrunch.download()
    lists = forbes.download()
    reachable = quarters and articles and lists
    if page is None or directory is None or unicorns is None or not reachable:
        # All or nothing: a corpus missing a source is a corpus that shrank, and
        # a company that silently left it is indistinguishable from one that
        # stopped hiring. Better to keep yesterday's file and say why.
        dead = ", ".join(
            name
            for name, got in (
                ("FinSMEs", page),
                ("the YC directory", directory),
                ("CB Insights", unicorns),
                ("EDGAR", quarters),
                ("TechCrunch", articles),
                ("Forbes", lists),
            )
            if not got
        )
        raise SystemExit(f"{dead} unreachable — corpus.json left as it was, never truncated")

    records, unparsed = parse(page)
    fixed = corrections.load().websites
    corpus = merge(
        records,
        yc.parse(directory),
        cbinsights.parse(unicorns),
        *(edgar.parse(quarter) for quarter in quarters),
        *(techcrunch.parse(article) for article in articles),
        *(forbes.parse(payload) for payload in lists),
        corrected=fixed,
    )
    corrections.check([c["name"] for c in corpus.companies], fixed, "website")
    # After the merge, not before: only ~3,000 companies survive dedup, and the
    # article read is a fetch each. Doing it per record would pay for every
    # duplicate round and every company no rule qualifies.
    stated = sum(1 for company in corpus.companies if company["website"])
    found = websites.fill(corpus.companies)

    write("data/corpus.json", corpus)
    print(
        f"corpus.json: {len(corpus.companies)} qualified, "
        f"{len(corpus.unqualified)} unqualified, "
        f"{len(corpus.not_software)} not software, "
        f"{len(corpus.ambiguous)} ambiguous (kept), "
        f"{len(unparsed)} unparsed headlines"
    )
    print(
        f"  websites: {stated + found} of {len(corpus.companies)} "
        f"({stated} stated by a source, {found} read off an article; "
        f"{len(fixed)} of the stated ones corrected by hand)"
    )


if __name__ == "__main__":
    main()
