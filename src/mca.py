"""MCA foreign-subsidiary snapshot — T4.3 (SPEC feature 9's cache half).

India's Ministry of Corporate Affairs publishes company master data through
data.gov.in. Two things about that source decide the shape of this module.

**The obvious datasets are a trap.** All 37 state-wise "Company Master Data of
<State>" tables are frozen at 2021-03-31, so a site built on them would be blind
to every company incorporated since — exactly the cohort this project is about.
The RoC-wise table below is the one usable source: 3.67M rows, newest
registration observed 2026-03-31. Never substitute a state-wise dataset for it.

**The API goes dark under sustained load.** Measured: after roughly twenty calls
every request 502s, including ones that answered seconds earlier. That is why
the pull is a *cache* — three calls, run rarely, by hand — and why the nightly
build reads a file instead. An enrichment that can take the build down with it
is not an enrichment, so `counts` and `load` have no path to the network and no
path to an exception: a missing snapshot is zero records and a build that ships.

`CompanyIndian/Foreign Company` would look like the obvious filter and is
unusable — ~670k rows hold the literal string `91`, a phone country code leaked
into a country field. `CompanySubCategory` carries the signal instead.
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections.abc import Iterable, Mapping
from datetime import date
from pathlib import Path
from time import sleep
from typing import Any, TypedDict
from urllib.parse import urlencode

from src.net import get

#: "Registrars of Companies (RoC)-wise Company Master Data" — company-level rows,
#: not aggregates, and the only MCA table on data.gov.in that is current.
INDEX = "4dbe5667-7b6b-41d7-82af-211562424d9a"
BASE = f"https://api.data.gov.in/resource/{INDEX}"

#: Spelled exactly as the data spells it. An earlier guess — "Subsidiary of
#: Foreign Company" — returned total=0, and a filter for a value that does not
#: exist is indistinguishable from a throttled call. Changing this string
#: silently empties the enrichment, so `pull` refuses a short answer.
SUBCATEGORY = "subsidiary of company incorporated outside India"

#: A registered key serves 10,000 rows a call (the published sample key is
#: capped at 10), so the whole 24,102-row slice is three calls.
PAGE = 10_000

SNAPSHOT = Path("data/mca.json")

#: The universe, measured. A pull that comes back far under this has not watched
#: the foreign subsidiaries disappear — it has stopped matching them, which is
#: exactly what happened when the filter was spelled "Subsidiary of Foreign
#: Company": total=0, indistinguishable from a throttled call. The floor catches
#: that; growth above it is a normal quarter's registrations and passes.
EXPECTED = 24_102

#: Five tries and a growing wait, because the failure this meets is a backend
#: that went dark for everyone rather than a rate limit aimed at us — the only
#: thing that helps is waiting, and there is no cheaper request to fall back to.
ATTEMPTS = 5
BACKOFF = 10

#: What the snapshot keeps, and what it drops at the door. SPEC feature 9 shows a
#: CIN, an incorporation year, a registered city and an entity status; the name
#: is what T4.4 matches on. The address is kept RAW rather than parsed down to
#: its city: the parse is T4.4's to get right, and a lossy trim here would cost a
#: re-pull against an API that 502s under load. Everything else — capital, NIC
#: code, the corrupt country column — is not something the site can honestly show.
FIELDS = {
    "cin": "CIN",
    "name": "CompanyName",
    "incorporated": "CompanyRegistrationdate_date",
    "address": "Registered_Office_Address",
    "status": "CompanyStatus",
}


class Company(TypedDict):
    """One foreign subsidiary as MCA registers it."""

    cin: str
    name: str
    incorporated: str
    address: str
    status: str


class Snapshot(TypedDict):
    """The cache on disk: the records, and the day they were pulled.

    `pulled` ships because MCA staleness is this source's known failure mode and
    a count with no date is a freshness claim nobody checked. It is None when
    there is no snapshot at all.
    """

    pulled: str | None
    companies: list[Company]


def api_key() -> str | None:
    """The data.gov.in key, from the environment or `.env`, or None.

    None is a real answer and not an error: the key is only needed to *refresh*
    the cache, so a machine without one still builds the site off the snapshot
    in the repo. `pull` is the only caller that requires it.
    """
    if key := os.environ.get("DATA_GOV_IN_KEY"):
        return key.strip()
    env = Path(".env")
    found = re.search(r"^DATA_GOV_IN_KEY=(.+)$", env.read_text(), re.M) if env.exists() else None
    return found.group(1).strip() if found else None


def record(raw: Mapping[str, Any]) -> Company | None:
    """One API row trimmed to what the site could show, or None if it is not a
    company we could ever name.

    A row with no CIN or no name is unusable downstream — T4.4 matches on the
    name and displays the CIN — so it is dropped here rather than carried as a
    record with a hole in it. The other three fields are allowed to be blank,
    because MCA genuinely leaves them blank and an absent status is an absence.
    """
    kept = {field: str(raw.get(source) or "").strip() for field, source in FIELDS.items()}
    if not (kept["cin"] and kept["name"]):
        return None
    return Company(**kept)  # type: ignore[typeddict-item]


def page(key: str, offset: int, attempts: int = ATTEMPTS) -> dict[str, Any]:
    """One page of foreign subsidiaries as the API returned it, or `{}` having
    proven nothing — every retry spent and no clean answer.

    An empty answer is never an empty page: the caller is assembling a count the
    site will present as the MCA universe, and a page that quietly became zero
    rows would understate it by 10,000 companies with nothing to show for it.
    """
    url = f"{BASE}?" + urlencode(
        {
            "api-key": key,
            "format": "json",
            "limit": PAGE,
            "offset": offset,
            "filters[CompanySubCategory]": SUBCATEGORY,
        }
    )
    for attempt in range(1, attempts + 1):
        status, body = get(url, timeout=180)
        if status == 200:
            try:
                return dict(json.loads(body))
            except (json.JSONDecodeError, TypeError, ValueError):
                pass  # A half-received page is transient in the way a 502 is.
        if attempt < attempts:
            sleep(BACKOFF * attempt)
    return {}


def pull(key: str, attempts: int = ATTEMPTS) -> list[Company]:
    """Every foreign subsidiary MCA lists, or ValueError having written nothing.

    Deduped by CIN because pagination over a filtered query is not promised to
    be stable — two pages may overlap — and a company counted twice inflates the
    same universe figure a dropped page deflates.
    """
    found: dict[str, Company] = {}
    total, offset = None, 0
    while total is None or offset < total:
        answer = page(key, offset, attempts)
        if not answer:
            raise ValueError(f"MCA gave no usable answer at offset {offset} after {attempts} tries")
        total = int(answer.get("total") or 0)
        rows = [kept for raw in answer.get("records", []) if (kept := record(raw))]
        if not rows:
            break  # An empty page ends the walk; without this a 0-row answer loops.
        found.update({row["cin"]: row for row in rows})
        offset += PAGE

    # Short against the API's own count means a page went missing; short against
    # the measured universe means the filter stopped matching. Either way the old
    # snapshot is the better answer, so neither is allowed to overwrite it.
    if len(found) < max(total or 0, EXPECTED) * 0.9:
        raise ValueError(
            f"MCA pull is short: {len(found)} of {total} reported, {EXPECTED} expected"
            " — refusing to cache it"
        )
    return list(found.values())


def write(path: str | Path, companies: Iterable[Company], pulled: str | None = None) -> None:
    """Replace the snapshot. Compact rather than indented: 24,102 records are a
    cache a program reads, and pretty-printing triples the file for nobody.
    """
    payload = Snapshot(pulled=pulled or date.today().isoformat(), companies=list(companies))
    Path(path).write_text(json.dumps(payload) + "\n")


def load(path: str | Path = SNAPSHOT) -> Snapshot:
    """The cached snapshot, or an empty one. Never raises, never fetches.

    Every way this can fail — no snapshot committed, a truncated write, a file
    that isn't the shape it was — is the same absence, and the absence must cost
    the build nothing. This is SPEC feature 9's "a dead MCA upstream degrades to
    no badge", made structural: there is no code path here that can fail a run.
    """
    try:
        found = json.loads(Path(path).read_text())
        companies = found["companies"]
        pulled = found["pulled"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return Snapshot(pulled=None, companies=[])
    if not isinstance(companies, list) or not (isinstance(pulled, str) or pulled is None):
        return Snapshot(pulled=None, companies=[])
    return Snapshot(pulled=pulled, companies=companies)


def counts(path: str | Path = SNAPSHOT) -> dict[str, Any]:
    """What the build report says about MCA: how many records the cache holds and
    when they were pulled.

    The date is half the answer. MCA's whole risk here is staleness, and a build
    reporting 24,102 records without saying they were fetched a year ago is
    making the freshness claim this project refuses to make everywhere else.
    """
    found = load(path)
    return {"records": len(found["companies"]), "pulled": found["pulled"]}


def main(argv: list[str]) -> int:
    """Refresh the snapshot. Run rarely and by hand — never from the nightly
    build, which reads what this leaves behind.
    """
    key = api_key()
    if not key:
        print("no DATA_GOV_IN_KEY (environment or .env) — snapshot unchanged", file=sys.stderr)
        return 1

    out = Path(argv[0]) if argv else SNAPSHOT
    try:
        companies = pull(key)
    except ValueError as refused:
        # The old snapshot outlives a bad pull, for the same reason build.write
        # refuses a non-conforming row: stale-but-whole beats fresh-but-partial.
        print(f"{refused} — {out} unchanged", file=sys.stderr)
        return 1

    write(out, companies)
    print(f"{out}: {len(companies)} foreign subsidiaries")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
