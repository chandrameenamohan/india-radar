"""MCA foreign-subsidiary snapshot and name match — T4.3, T4.4 (SPEC feature 9).

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

**The join is by name, because no shared identifier exists** (T4.4). MCA knows
`STRIPE INDIA PRIVATE LIMITED`; the corpus knows `Stripe`. The rule is the one
`slugs.states_company` already uses on job boards — the other name may say MORE
than the company's and never less — anchored at the front, since a registered
name is the company's name followed by the register's own words. What it adds is
a word boundary, and that is the whole difference between a match and a wrong
CIN: `KONGSBERG`, `NOTIONEXT`, `STRIPES ACADEMY` and `SCALEFFICIENT` all start
with a listed company's letters and belong to somebody else.
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from collections.abc import Iterable, Mapping, MutableMapping
from datetime import date
from pathlib import Path
from time import sleep
from typing import Any, NamedTuple, TypedDict
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


# --- the name match (T4.4) ----------------------------------------------------

#: The words a registered name ends with to state what kind of company it is.
#: Dropped from the tail before matching, because no source outside the register
#: states them: `STRIPE INDIA PRIVATE LIMITED` and `Stripe` are one company.
LEGAL_FORM = frozenset({"private", "pvt", "public", "limited", "ltd", "llp"})

#: `INDIA` after the company's own name is the register saying which country's
#: subsidiary this is, not part of the name — and since every one of the 24,102
#: rows is an India registration, it distinguishes nobody from anybody.
COUNTRY = "india"

#: The two ways a registered name can start with a company's, best first.
#: `exact` is the register saying the company's name and nothing else that
#: carries information; `prefix` is the register saying MORE, which is `GLEAN
#: SEARCH TECHNOLOGIES INDIA` (right) and `FERN & ADE INDIA` (a different
#: company) in the same shape. Only `exact` is published — see `attach`.
EXACT, PREFIX = "exact", "prefix"

_WORD = re.compile(r"[^a-z0-9]+")


class Registration(TypedDict):
    """What the site shows about a matched company, and how sure the match is.

    `confidence` ships on the row rather than staying in the matcher because a
    CIN is a claim about a real legal entity, and a reader who can see the rule
    that produced it can check it. Every published row says `exact` today; that
    is the threshold doing its job, not a constant.
    """

    cin: str
    name: str
    incorporated: str
    city: str
    status: str
    confidence: str


class Held(TypedDict):
    """A match that is plausible and not certain, kept for a human.

    These are NOT published. A wrong CIN on a public site is a claim about
    somebody else's company, so the whole set below the threshold lands in the
    build report where a person can settle it, rather than on the site where
    nobody could tell it was ever in doubt.
    """

    name: str
    confidence: str
    candidates: list[Company]


class Candidate(NamedTuple):
    """One registered company whose name opens with the name we asked about."""

    #: Words of the registered name the asked-about name spent. The register may
    #: JOIN a company's words (`AMBIENTAI` for `Ambient.ai`) but never SPLIT
    #: them: `HIGH TOUCH HEALTH SOLUTIONS` spends two words on `Hightouch`'s one
    #: and is a healthcare company, not the data one.
    spent: int
    #: What the registered name says after them.
    rest: tuple[str, ...]
    company: Company


def words(name: str) -> list[str]:
    """A company name as lowercase alphanumeric words, its legal form dropped."""
    found = [word for word in _WORD.split(name.casefold()) if word]
    while found and found[-1] in LEGAL_FORM:
        found.pop()
    return found


def index(companies: Iterable[Company]) -> dict[str, list[Candidate]]:
    """Registered companies keyed by every word-boundary prefix of their name.

    Keyed on the words run together, so `AMBIENTAI` and `Ambient.ai` meet, and
    only ever cut between words, so nothing can match into the middle of one.
    Measured over the whole 2,915-company corpus against all 24,102 registered
    names: zero corpus names reach two different `exact` CINs.
    """
    found: dict[str, list[Candidate]] = defaultdict(list)
    for company in companies:
        registered = words(company["name"])
        key = ""
        for i, word in enumerate(registered):
            key += word
            found[key].append(Candidate(i + 1, tuple(registered[i + 1 :]), company))
    return found


def find(name: str, registered: Mapping[str, list[Candidate]]) -> tuple[str, list[Company]]:
    """The best tier of registered companies this name could be, and which tier —
    or `("", [])` where the register says nothing about it.

    Several companies can share a tier and that is not a match: `Scale` reaches
    both `SCALE AI INDIA` and `SCALE FACILITATION PARTNERS INDIA`, and the
    corpus holds `Scale AI` as a separate company. Answering "one of these" is
    the caller's to refuse.
    """
    asked = words(name)
    if not asked:
        return "", []
    plausible = [c for c in registered.get("".join(asked), ()) if c.spent <= len(asked)]
    if exact := [c.company for c in plausible if not c.rest or c.rest == (COUNTRY,)]:
        return EXACT, exact
    return (PREFIX, [c.company for c in plausible]) if plausible else ("", [])


def city(address: str) -> str:
    """The registered office's city, or "" — the register writes an address as
    `<street>,<locality>,<district>,<state>,<pincode>-India`.

    The district is the fourth field from the right and the locality the fifth,
    and the *locality* is what an earlier reading of one Mumbai row took for the
    city. Measured across all 24,102: the locality is blank on 252 rows, a
    street fragment on 349 (`Sector -45`, `NH-8`), and where it is a place it is
    a neighbourhood — `Kandivali West` for EBANX, `Shaikpet` for Workato. The
    district is never blank, holds 476 distinct values, and reads as the city a
    person would name. Case is the register's own noise (`NEW DELHI` beside
    `New Delhi` for the same place), so it is evened out; nothing else is.
    """
    parts = address.split(",")
    return parts[-3].strip().title() if len(parts) >= 3 else ""


def attach(
    rows: Iterable[MutableMapping[str, Any]], snapshot: Snapshot | None = None
) -> list[Held]:
    """Fill in each row's `mca`, in place, and return the matches held for review.

    Rows arrive from `build.build` with `mca: None` already set, so an MCA that
    was never pulled — or a snapshot that got truncated — leaves a build that is
    complete and honest rather than one that failed. Nothing here reaches the
    network; `load` is a file read that cannot raise.

    A company is published only where exactly one registered name is `exact`.
    Everything else is held: a wrong CIN is worse than no CIN, and this is a
    slice where being unmatched is the *normal* outcome anyway — the register
    lists subsidiaries of foreign-incorporated parents, so an India-founded
    company cannot appear in it at all.
    """
    registered = index((snapshot if snapshot is not None else load())["companies"])
    held: list[Held] = []
    for row in rows:
        confidence, companies = find(row["name"], registered)
        if confidence == EXACT and len(companies) == 1:
            company = companies[0]
            row["mca"] = Registration(
                cin=company["cin"],
                name=company["name"],
                incorporated=company["incorporated"],
                city=city(company["address"]),
                status=company["status"],
                confidence=confidence,
            )
        elif companies:
            held.append(Held(name=row["name"], confidence=confidence, candidates=companies))
    return held


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
