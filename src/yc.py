"""YC company directory corpus source — T1.2 (SPEC feature 1).

YC publishes every company it funded, and — unlike a funding wire — says nothing
about the rounds those companies raised afterwards. What it does state is a
`stage`: `Growth` for a company past Series A, `Early` for one still at seed. So
a YC record carries no amount, no round letter and **no round date**, because YC
states none and a batch date is not a funding date. It carries the stage instead,
and `src/corpus.py` qualifies on that (SPEC feature 2's rules judge evidence, and
this is the evidence YC gives).

The payload is the yc-oss mirror of YC's directory, not YC's own
`api.ycombinator.com/v0.1/companies`. Measured, not preferred: the official API
is 244 paged calls for the same 6,087 companies and **omits `stage` entirely**,
with no query parameter to recover it — so it cannot qualify a single company.
The mirror is one call and carries the field. See learning-tests/FINDINGS.md.
"""
from __future__ import annotations

import json

from src.record import Record
from src.websites import site

#: One GET, ~10MB, the whole directory. There is no per-stage bucket to fetch a
#: tenth of; `all.json` is the smallest URL that carries `stage`.
API = "https://yc-oss.github.io/api/companies/all.json"


def parse(payload: str) -> list[Record]:
    """Every company in the directory, at whatever stage YC put it.

    Deliberately unfiltered: which stages qualify is `corpus._qualified_by`'s
    call, and a source that pre-filtered would be deciding on its behalf — the
    early-stage companies are then excluded *and counted* like every other
    unqualified record, rather than never appearing.

    A missing `name` or `url` raises. Both are structural, and a directory that
    stopped supplying them has changed shape in a way that must fail loudly
    rather than yield a shorter corpus.
    """
    return [
        Record(
            name=company["name"],
            amount=None,
            currency=None,
            date=None,
            round_letter=None,
            source_url=company["url"],
            stage=(company.get("stage") or "").casefold() or None,
            # Stated on 6,056 of 6,093 companies, and the reason T1.6 exists:
            # no other source covers this many companies with an address.
            website=site(company["website"]) if company.get("website") else None,
        )
        for company in json.loads(payload)
    ]
