"""Merge, dedup and qualify the funding corpus — T1.5 (SPEC features 1 and 2).

Sources emit one record per funding round; the corpus wants one row per company,
chosen the same way no matter what order the sources arrive in. So duplicates
collapse to the *strongest* round rather than the first one seen: a company that
raised Seed and later Series B qualifies on the B, whichever record the scraper
happened to yield first.

A company that states neither a round letter nor an amount cannot be judged
either way. It is excluded and named in `unqualified` — never silently dropped,
because a corpus that shrinks quietly is indistinguishable from a scraper that
broke.
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterable
from itertools import chain
from pathlib import Path
from typing import NamedTuple

from src.finsmes import BASE, Record, parse
from src.net import fetch

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
    unqualified: list[str]  # judged on no evidence, so excluded and counted


def merge(*sources: Iterable[Record]) -> Corpus:
    """Collapse funding records into one qualified row per distinct company.

    Deterministic in both directions: the surviving record for a company is the
    maximum under `_strength`, and the output is sorted, so shuffling the sources
    (or the records within them) yields an identical corpus.
    """
    best: dict[str, Record] = {}
    for record in chain.from_iterable(sources):
        key = _NOT_ALNUM.sub("", record["name"].casefold())
        if key not in best or _strength(record) > _strength(best[key]):
            best[key] = record

    companies: list[Company] = []
    unqualified: list[str] = []
    for key in sorted(best):
        record = best[key]
        if rule := _qualified_by(record):
            companies.append(Company(**record, qualified_by=rule))
        else:
            unqualified.append(record["name"])

    return Corpus(companies, sorted(unqualified))


def _strength(record: Record) -> tuple[str, int, str, str]:
    """Total order over rounds for the same company, independent of input order.

    Letter first (a later letter is a bigger round), then amount. Date and URL
    are not signal — they are there so two equally-strong rounds still resolve to
    the same winner every run.
    """
    return (
        record["round_letter"] or "",
        record["amount"] or 0,
        record["date"],
        record["source_url"],
    )


def _qualified_by(record: Record) -> str | None:
    """Which rule admits this company, or None if nothing does.

    Any stated letter qualifies: the parser only reads `Series <A-Z>`, and every
    such letter is A or later. Seed and pre-seed carry no letter and fall through
    to the amount proxy, which is exactly the case that proxy exists for.
    """
    if record["round_letter"]:
        return "letter"
    if record["amount"] is not None and record["amount"] >= MIN_AMOUNT:
        return "amount"
    return None


def write(path: str | Path, corpus: Corpus) -> None:
    """Emit corpus.json. The unqualified names ship with it — the count of what
    we couldn't judge is part of the corpus, not a build-time aside."""
    Path(path).write_text(
        json.dumps({"companies": corpus.companies, "unqualified": corpus.unqualified}, indent=2)
        + "\n"
    )


def main() -> None:
    page = fetch(f"{BASE}/category/usa")
    if page is None:
        raise SystemExit("FinSMEs unreachable — corpus.json left as it was, never fabricated")

    records, unparsed = parse(page)
    corpus = merge(records)
    write("data/corpus.json", corpus)
    print(
        f"corpus.json: {len(corpus.companies)} qualified, "
        f"{len(corpus.unqualified)} unqualified, {len(unparsed)} unparsed headlines"
    )


if __name__ == "__main__":
    main()
