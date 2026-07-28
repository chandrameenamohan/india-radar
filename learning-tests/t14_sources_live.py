"""What TechCrunch, Forbes and CB Insights actually give us — measured for T1.4.

Run: .venv/bin/python learning-tests/t14_sources_live.py

One file for three sources because the questions are identical and the answer
that matters is the combined one: does each fetch live, is each non-empty, is
each schema-valid, and does adding all three to the real corpus grow it without
demoting anything that was already qualified.

This is T1.4's integration check. It is deliberately outside `make check` — the
gate must not depend on three third-party sites being up (see VERIFICATION.md).
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import cbinsights, corpus, edgar, finsmes, forbes, techcrunch, yc  # noqa: E402
from src.finsmes import Record  # noqa: E402
from src.net import fetch  # noqa: E402


def schema_valid(records: list[Record]) -> None:
    """T1.1's contract, asserted rather than eyeballed: a source that drifts from
    it gets special-cased downstream, which is what the DoD forbids."""
    for record in records:
        assert set(record) == set(Record.__annotations__), record
        assert isinstance(record["name"], str) and record["name"].strip(), record
        assert record["source_url"].startswith("https://"), record
        assert record["amount"] is None or isinstance(record["amount"], int), record


def techcrunch_live() -> list[Record]:
    print("== TechCrunch ==")
    pages = techcrunch.download()
    assert pages, "TechCrunch unreachable"
    records = [r for page in pages for r in techcrunch.parse(page)]
    schema_valid(records)
    assert records, "no funding headlines parsed — the grammar has moved"
    dates = sorted(r["date"] or "" for r in records)
    print(f"  pages fetched : {len(pages)}/{techcrunch.PAGES}")
    print(f"  records       : {len(records)} ({len({r['name'] for r in records})} distinct)")
    print(f"  span          : {dates[0]} .. {dates[-1]}")
    print(f"  with a letter : {sum(1 for r in records if r['round_letter'])}")
    print(f"  with an amount: {sum(1 for r in records if r['amount'])}")
    return records


def forbes_live() -> list[Record]:
    print("\n== Forbes ==")
    payloads = forbes.download()
    assert payloads, "Forbes unreachable"
    records = [r for payload in payloads for r in forbes.parse(payload)]
    schema_valid(records)
    assert records, "the lists came back empty"
    funded = [r for r in records if r["stage"]]
    print(f"  lists published: {len(payloads)}/{len(forbes.LISTS)}")
    print(f"  records        : {len(records)} ({len({r['name'] for r in records})} distinct)")
    print(f"  fundedness stated: {len(funded)}; unstated: {len(records) - len(funded)}")
    print(f"  bootstrapped   : {sorted(r['name'] for r in records if not r['stage'])[:8]}")
    return records


def cbinsights_live() -> list[Record]:
    print("\n== CB Insights ==")
    page = fetch(cbinsights.UNICORNS, timeout=60)
    assert page is not None, "CB Insights unreachable"
    records = cbinsights.parse(page)
    schema_valid(records)
    assert records, "the unicorn board parsed to nothing — the table has moved"
    # What the SPEC sector filter costs, so the trade stays visible.
    board = list(cbinsights._ROW.finditer(page))
    dropped = Counter(
        r["industry"] for r in board if r["industry"] not in cbinsights.SOFTWARE
    )
    print(f"  board rows : {len(board)}")
    print(f"  kept       : {len(records)}")
    print(f"  dropped    : {dropped.most_common()}")
    return records


def against_the_prior_corpus(new: dict[str, list[Record]]) -> None:
    """The DoD's line — 'adding the source strictly increases distinct company
    count' — plus the invariant T1.3 learned: what matters when a source lands is
    not that the corpus grew but that nothing qualified left it.

    The baseline is rebuilt live from T1.1–T1.3 rather than read from
    `data/corpus.json`, because once a build has run, that file already contains
    these three and the comparison would answer itself.
    """
    print("\n== against a corpus rebuilt from T1.1-T1.3 ==")
    baseline = _prior_sources()

    def qualified(*sources: list[Record]) -> set[str]:
        return {c["name"] for c in corpus.merge(*baseline, *sources).companies}

    before = qualified()
    after = qualified(*new.values())
    print(f"  qualified before: {len(before)}")
    print(f"  qualified after : {len(after)}  (+{len(after - before)} new)")
    print(f"  demoted         : {sorted(before - after) or 'none'}")
    assert len(after) > len(before), "the sources added no company the corpus did not have"
    assert not before - after, "a company that was qualified left the corpus"

    for name, records in new.items():
        added = qualified(records) - before
        print(f"  {name:<12} adds {len(added):>4} on its own")
        assert added, f"{name} added nothing"


def _prior_sources() -> list[list[Record]]:
    """FinSMEs, YC and EDGAR — the corpus as it stood before T1.4."""
    page = fetch(f"{finsmes.BASE}/category/usa")
    directory = fetch(yc.API, timeout=120)
    quarters = edgar.download()
    assert page and directory and quarters, "a pre-T1.4 source is down; no baseline to compare to"
    return [
        finsmes.parse(page).records,
        yc.parse(directory),
        *(edgar.parse(quarter) for quarter in quarters),
    ]


if __name__ == "__main__":
    against_the_prior_corpus(
        {
            "TechCrunch": techcrunch_live(),
            "Forbes": forbes_live(),
            "CB Insights": cbinsights_live(),
        }
    )
    print("\nT1.4 integration: all three live, non-empty and schema-valid.")
