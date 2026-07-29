"""SEC Form D funding corpus source — T1.3 (SPEC feature 1).

Every US private placement files a Form D, so EDGAR states an *amount* the way a
press release never does: structurally, in a field, audited by the filer's own
lawyers. That makes it the one source whose records qualify on SPEC feature 2's
amount proxy rather than on prose.

The bulk route, not the filing route. SEC republishes each quarter's Form D
filings as a zip of TSVs (`ISSUERS`, `OFFERING`, joined on accession number), so
a quarter costs **one** call instead of ~16,000 fetches of `primary_doc.xml`.

**A naive Form D scrape builds a directory of venture funds, not of companies.**
Measured on 2026Q1: of 15,734 issuer rows, 5,757 are pooled investment funds
(Sequoia's own fund files a Form D too), 5,765 are amendments re-reporting an
offering already counted, and 3,360 are real estate, oil and gas, banking and
the rest. 852 are technology operating companies. Filtering is not tidying here;
it is the difference between this source and noise. See learning-tests/FINDINGS.md.
"""
from __future__ import annotations

import csv
import io
import re
import zipfile
from datetime import date

from src.finsmes import Record
from src.net import get_bytes

#: The DERA quarterly data set. Note `structureddata`, not `dera` — the latter
#: path 404s for these files.
DATASET = "https://www.sec.gov/files/structureddata/data/form-d-data-sets/{quarter}_d.zip"

#: SEC's automated-access policy wants a declared contact, and enforces it: the
#: browser UA in `net.UA` gets a blanket 403 here, this gets 200. Not decoration.
UA = "india-radar chandra@hakimo.ai"

#: A year of filings. Enough that a company which raised last spring is still in
#: the corpus, short enough that we aren't listing 2019's round as news.
QUARTERS = 4

#: Form D's industry taxonomy has no "Software" value; these three are its whole
#: technology branch. SPEC's non-goals rule out the other twenty-odd groups
#: (biotech, oil and gas, REITs, restaurants), so scope is applied here rather
#: than leaving the corpus to be mostly companies we would never list.
TECH = frozenset({"Computers", "Other Technology", "Telecommunications"})

#: Trailing legal-entity forms, stripped so a registry name becomes a company
#: name. EDGAR files "Legora, Inc."; YC's directory and FinSMEs' headlines both
#: say "Legora". Measured over 2026Q1: this merges 5 real cross-source duplicates
#: and collapses no two distinct companies in either source. Deliberately does
#: NOT touch descriptive words — "Signify Holdings" and "Garage Technologies"
#: keep theirs, because those are part of the name rather than its legal wrapper.
_LEGAL = re.compile(
    r"[\s,]+(?:inc|incorporated|corp|corporation|co|company|llc|l\.l\.c|ltd|limited"
    r"|lp|l\.p|llp|plc|pbc|gmbh|s\.a|s\.a\.r\.l|pte|pty|ag|nv|bv|ab|oy)\.?$",
    re.I,
)


def quarters(today: date | None = None) -> list[str]:
    """Candidate quarter labels, newest first — `download` takes the ones that exist.

    Computed rather than hardcoded, but never trusted: SEC publishes a quarter
    months after it closes, and *how many* months is not fixed. Measured on
    2026-07-28, Q2 was still 404 four weeks after it ended while Q1 had been up
    since 3 April. So this deliberately offers more candidates than it needs and
    lets the 404s pick.
    """
    day = today or date.today()
    year, quarter = day.year, (day.month - 1) // 3 + 1
    labels = []
    for _ in range(QUARTERS + 3):  # +3 of publication lag to walk past
        labels.append(f"{year}q{quarter}")
        year, quarter = (year - 1, 4) if quarter == 1 else (year, quarter - 1)
    return labels


def download(today: date | None = None) -> list[bytes]:
    """The newest QUARTERS data sets SEC has actually published.

    Stops as soon as it has enough. A 404 here is the normal way an unpublished
    quarter announces itself and is not an error; running out of candidates
    without a single success is, and the caller is left to say so.
    """
    blobs = []
    for quarter in quarters(today):
        status, blob = get_bytes(DATASET.format(quarter=quarter), timeout=120, ua=UA)
        if status == 200:
            blobs.append(blob)
            if len(blobs) == QUARTERS:
                break
    return blobs


def parse(blob: bytes) -> list[Record]:
    """Technology operating companies from one quarterly Form D data set.

    Deliberately does not apply the $5M line: which amounts qualify is
    `corpus._qualified_by`'s call, and a source that pre-filtered would decide on
    its behalf — the small rounds are then excluded *and counted* like every
    other unqualified record, rather than never appearing.
    """
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        offerings = {row["ACCESSIONNUMBER"]: row for row in _rows(archive, "OFFERING")}
        issuers = _rows(archive, "ISSUERS")

    records = []
    for issuer in issuers:
        offering = offerings.get(issuer["ACCESSIONNUMBER"])
        if (
            issuer["IS_PRIMARYISSUER_FLAG"] != "YES"  # a co-issuer on someone else's raise
            or offering is None
            or offering["ISAMENDMENT"] == "true"  # D/A restates a round already counted
            or offering["ISPOOLEDINVESTMENTFUNDTYPE"] == "true"  # a fund, not a company
            or offering["INDUSTRYGROUPTYPE"] not in TECH
        ):
            continue
        # Sold, not offered: TOTALOFFERINGAMOUNT is the ceiling the filer is
        # permitted to raise and is routinely open-ended, while this is the money
        # actually in the door. 0 is a real answer — the round was announced and
        # nothing has closed yet.
        amount = _to_int(offering["TOTALAMOUNTSOLD"])
        records.append(
            Record(
                name=_company_name(issuer["ENTITYNAME"]),
                amount=amount,
                currency="USD" if amount is not None else None,
                # Date of first sale — the round's own date, not the filing's.
                date=offering["SALE_DATE"] or None,
                round_letter=None,  # Form D states a dollar figure, never a letter
                source_url=_filing_url(issuer["CIK"], issuer["ACCESSIONNUMBER"]),
                stage=None,
                # Form D states a street address and a phone number and no URL of
                # any kind (measured, T1.3), so an EDGAR company legitimately ends
                # the build with no website rather than a guessed one.
                website=None,
            )
        )
    return records


def _rows(archive: zipfile.ZipFile, table: str) -> list[dict[str, str]]:
    """One TSV out of the quarterly zip. The directory inside is named for the
    quarter (`2026Q1_d/`), so members are matched by suffix rather than path."""
    name = next(n for n in archive.namelist() if n.endswith(f"{table}.tsv"))
    text = archive.read(name).decode("utf-8", errors="replace")
    return list(csv.DictReader(io.StringIO(text), delimiter="\t"))


def _company_name(entity: str) -> str:
    """"Legora, Inc." -> "Legora". Looping, because "Foo Corp., Inc." is real.

    Falls back to the filed name if stripping would empty it — a company that is
    genuinely called "Holdings Ltd" keeps its name over becoming anonymous.
    """
    name = entity.strip()
    while (shorter := _LEGAL.sub("", name).strip()) != name:
        name = shorter
    return name or entity.strip()


def _to_int(value: str) -> int | None:
    """Form D amounts are whole dollars. Anything else is a shape change, and an
    absent amount is absent rather than zero."""
    return int(value) if value.isdigit() else None


def _filing_url(cik: str, accession: str) -> str:
    """The filing's index page on EDGAR — the human-readable landing page for the
    Form D this record came from. CIK is zero-padded in the TSV and unpadded in
    the path."""
    return (
        f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
        f"{accession.replace('-', '')}/{accession}-index.htm"
    )
