"""T4.3 — MCA snapshot pull. T4.4 — the name match.

Three rules carry this module and all of them are about what a failure costs.
The pull either produces the whole universe or leaves the last snapshot alone,
because a silently short cache understates the enrichment by thousands of
companies. The build's side of it cannot fail at all: no snapshot, a truncated
one, or a file that isn't the shape it was are one absence, and the site ships
regardless. And the match publishes only what it is sure of, because a CIN is a
claim about a real legal entity and a wrong one is worse than none.
"""
import json
from datetime import date

import pytest

from src import build, mca

#: Comma-separated down to `city,district,state,pincode-country`. Kept whole in
#: the snapshot: which comma holds the registered city is T4.4's to settle, and a
#: lossy trim here would cost a re-pull against an API that 502s under load.
ADDRESS = "201 Creative Industrial Estate,Mumbai,Mumbai City,Maharashtra,400018-India"

#: One live row, fields and all, as api.data.gov.in returns it — including the
#: corrupt country column, which is here precisely so the trim is seen dropping it.
RAW = {
    "CIN": "U27310MH2013FTC239281",
    "CompanyName": "EVER CORE COMMODITIES PRIVATE LIMITED",
    "CompanyROCcode": "ROC Mumbai",
    "CompanyCategory": "Company limited by shares",
    "CompanySubCategory": mca.SUBCATEGORY,
    "CompanyClass": "Private",
    "AuthorizedCapital": "1000000.00",
    "PaidupCapital": "100000.00",
    "CompanyRegistrationdate_date": "2013-01-04",
    "Registered_Office_Address": ADDRESS,
    "Listingstatus": "Unlisted",
    "CompanyStatus": "Strike Off",
    "CompanyStateCode": "maharashtra",
    "CompanyIndian/Foreign Company": "India",
    "nic_code": "27310",
    "CompanyIndustrialClassification": "Manufacturing (Metals and Chemicals, and products thereof)",
}

COMPANY = mca.Company(
    cin="U16000KA2018FTC111111",
    name="STRIPE INDIA PRIVATE LIMITED",
    incorporated="2018-04-02",
    address="Bengaluru,Bangalore Urban,Karnataka,560001-India",
    status="Active",
)


def rows(n, offset=0, total=None):
    """An API answer carrying `n` synthetic records, numbered from `offset`."""
    return json.dumps(
        {
            "total": n if total is None else total,
            "count": n,
            "records": [{**RAW, "CIN": f"U000{offset + i:05d}", "CompanyName": f"CO {offset + i}"}
                        for i in range(n)],
        }
    )


def answering(*pages):
    """A `net.get` stand-in serving the given pages in order, then 502ing."""
    served = iter(pages)

    def get(url, timeout=45):
        return next(served, (502, "upstream is dark"))

    return get


# --- the two checks T4.3's DoD names ------------------------------------------


def test_build_reads_cache_not_api(tmp_path):
    """The MCA figure the build publishes comes off the disk.

    `tests/conftest.py` refuses every unstubbed network call, so a `counts` that
    reached for api.data.gov.in — which is what the nightly build must never do —
    fails here rather than buying a dependency on an upstream that 502s.
    """
    snapshot = tmp_path / "mca.json"
    mca.write(snapshot, [COMPANY], pulled="2026-07-22")

    assert mca.counts(snapshot) == {"records": 1, "pulled": "2026-07-22"}

    # The figure tracks the file, which is the half a hardcoded constant would fake.
    mca.write(snapshot, [COMPANY, {**COMPANY, "cin": "U16000KA2019FTC222222"}])
    assert mca.counts(snapshot) == {"records": 2, "pulled": date.today().isoformat()}


def test_dead_upstream_degrades(tmp_path):
    """MCA down, or never pulled, or pulled into a file that got truncated: the
    build reports zero and keeps going. None of these is an error.
    """
    assert mca.counts(tmp_path / "never-pulled.json") == {"records": 0, "pulled": None}

    for broken in ('{"companies": [{"cin": "U1"}], "pull', "[]", '{"companies": 24102}'):
        half_written = tmp_path / "truncated.json"
        half_written.write_text(broken)
        assert mca.counts(half_written) == {"records": 0, "pulled": None}

    # And the whole build survives it — an enrichment that can fail a run is not
    # an enrichment. This is the assembly line `build.main` runs, without a site
    # to overwrite: rows are produced, and the report carries the honest zero.
    listed, outcomes = build.build(
        [{**c, "website": None} for c in _CORPUS], _SLUGS, _PROBES
    )
    assert [row["name"] for row in listed] == ["Acme"]
    assert mca.counts(tmp_path / "never-pulled.json")["records"] == 0
    assert outcomes["Acme"].value == "listed"


# --- the trim -----------------------------------------------------------------


def test_record_keeps_what_the_site_can_show_and_drops_the_corrupt_column():
    """The snapshot carries a CIN, a name, an incorporation date, the registered
    address and the entity status — and specifically NOT
    `CompanyIndian/Foreign Company`, which holds the literal string `91` (a phone
    country code) across ~670k rows and is why `CompanySubCategory` is the filter.
    """
    kept = mca.record(RAW)

    assert kept == {
        "cin": "U27310MH2013FTC239281",
        "name": "EVER CORE COMMODITIES PRIVATE LIMITED",
        "incorporated": "2013-01-04",
        "address": "201 Creative Industrial Estate,Mumbai,Mumbai City,Maharashtra,400018-India",
        "status": "Strike Off",
    }
    assert "91" not in json.dumps(kept), "the corrupt country column reached the snapshot"


def test_record_without_a_cin_or_a_name_is_dropped():
    """T4.4 matches on the name and displays the CIN, so a row missing either is
    unusable — dropped here rather than cached as a record with a hole in it."""
    assert mca.record({**RAW, "CIN": ""}) is None
    assert mca.record({**RAW, "CompanyName": None}) is None
    assert mca.record({**RAW, "CompanyStatus": None})["status"] == "", "a blank status is legal"


# --- the pull -----------------------------------------------------------------


def test_pull_walks_every_page_and_dedupes_by_cin(monkeypatch):
    """Pagination over a filtered query is not promised to be stable, so two
    pages may overlap. A company counted twice inflates the same universe figure
    a dropped page deflates."""
    monkeypatch.setattr(mca, "PAGE", 2)
    monkeypatch.setattr(mca, "EXPECTED", 0)  # the universe floor is its own test
    # Three companies over two pages, and the second page repeats the first's
    # last row — the overlap this dedup exists for.
    monkeypatch.setattr(
        mca, "get",
        answering((200, rows(2, offset=0, total=3)), (200, rows(2, offset=1, total=3))),
    )

    found = mca.pull("key")

    assert [c["cin"] for c in found] == ["U00000000", "U00000001", "U00000002"]


def test_pull_retries_a_dark_upstream_then_refuses_to_cache_a_short_answer(monkeypatch):
    """Measured: after ~20 calls the whole resource 502s, including requests that
    worked seconds earlier. Retries are what get a pull through that; refusing
    the short result is what stops a half-pull replacing a good snapshot."""
    monkeypatch.setattr(mca, "BACKOFF", 0)
    monkeypatch.setattr(mca, "EXPECTED", 1)
    calls = []

    def flaky(url, timeout=45):
        calls.append(url)
        return (200, rows(1, total=1)) if len(calls) == 3 else (502, "")

    monkeypatch.setattr(mca, "get", flaky)
    assert len(mca.pull("key", attempts=3)) == 1
    assert len(calls) == 3, "gave up before exhausting its retries"

    # A page that goes missing mid-walk: the API says 4 and two pages arrive.
    monkeypatch.setattr(mca, "PAGE", 2)
    monkeypatch.setattr(mca, "get", answering((200, rows(2, total=4)), (200, rows(0, total=4))))
    with pytest.raises(ValueError, match="short: 2 of 4"):
        mca.pull("key", attempts=1)


def test_pull_refuses_a_universe_that_collapsed(monkeypatch):
    """The measured universe is 24,102, and a pull holding a handful of it has
    not watched them dissolve — it has stopped matching them.

    This is the failure that already happened once: the filter spelled
    "Subsidiary of Foreign Company" returned total=0, which reads exactly like a
    throttled call. The API's own total agrees with the answer in that case, so
    only the expected figure catches it.
    """
    monkeypatch.setattr(mca, "PAGE", 30_000)
    monkeypatch.setattr(mca, "get", answering((200, rows(1, total=1))))

    with pytest.raises(ValueError, match=f"1 of 1 reported, {mca.EXPECTED} expected"):
        mca.pull("key", attempts=1)


def test_pull_raises_rather_than_returning_a_page_it_never_got(monkeypatch):
    """The caller is assembling a count the site presents as the MCA universe. A
    page dropped out of it silently understates that by 10,000 companies."""
    monkeypatch.setattr(mca, "BACKOFF", 0)
    monkeypatch.setattr(mca, "EXPECTED", 0)
    monkeypatch.setattr(mca, "get", answering((200, rows(0, total=0))))
    monkeypatch.setattr(mca, "PAGE", 1)

    # An empty first page ends the walk cleanly; a page that never answers does not.
    assert mca.pull("key", attempts=1) == []

    monkeypatch.setattr(mca, "get", answering((200, rows(1, total=10)), (502, "")))
    with pytest.raises(ValueError, match="offset 1"):
        mca.pull("key", attempts=1)


def test_api_key_is_read_but_never_invented(monkeypatch, tmp_path):
    """No key is a real answer: the key refreshes the cache, so a machine without
    one still builds the site off the committed snapshot."""
    monkeypatch.setenv("DATA_GOV_IN_KEY", "  from-the-environment  ")
    assert mca.api_key() == "from-the-environment"

    monkeypatch.delenv("DATA_GOV_IN_KEY")
    monkeypatch.chdir(tmp_path)
    assert mca.api_key() is None

    (tmp_path / ".env").write_text("OTHER=x\nDATA_GOV_IN_KEY=from-dot-env\n")
    assert mca.api_key() == "from-dot-env"


def test_main_leaves_the_last_snapshot_alone_when_the_pull_fails(monkeypatch, tmp_path):
    """Stale-but-whole beats fresh-but-partial, the same rule `build.write` keeps
    for a non-conforming row."""
    snapshot = tmp_path / "mca.json"
    mca.write(snapshot, [COMPANY], pulled="2026-07-22")
    monkeypatch.setattr(mca, "BACKOFF", 0)
    monkeypatch.setattr(mca, "get", answering())  # everything 502s
    monkeypatch.setenv("DATA_GOV_IN_KEY", "key")

    assert mca.main([str(snapshot)]) == 1
    assert mca.counts(snapshot) == {"records": 1, "pulled": "2026-07-22"}

    monkeypatch.delenv("DATA_GOV_IN_KEY")
    monkeypatch.chdir(tmp_path)  # no .env here either
    assert mca.main([str(snapshot)]) == 1, "a missing key must not be a silent no-op"


# --- the name match (T4.4) ----------------------------------------------------

#: Twenty hand-labelled pairs: a corpus name, a name the register really holds,
#: and what the match may conclude from the two. Every registered name below is
#: a live row in `data/mca.json` — pinned by
#: `test_the_labelled_pairs_are_rows_the_register_really_holds`, because a
#: hand-labelled set that drifts from the register is how this check goes green
#: while being wrong about the world.
#:
#: The three labels are the three answers: `exact` publishes, `prefix` is held
#: for a human, and `""` is the register talking about somebody else.
PAIRS = [
    # The register says the company's name and nothing else that carries
    # information. Ten companies, and the spellings that make the rule non-trivial:
    # a joined name, a two-word name, a digit inside a name, no `INDIA` at all.
    ("Stripe", "STRIPE INDIA PRIVATE LIMITED", mca.EXACT),
    ("Databricks", "DATABRICKS INDIA PRIVATE LIMITED", mca.EXACT),
    ("Minio", "MINIO PRIVATE LIMITED", mca.EXACT),
    ("Ambient.ai", "AMBIENTAI INDIA PRIVATE LIMITED", mca.EXACT),
    ("Scale AI", "SCALE AI INDIA PRIVATE LIMITED", mca.EXACT),
    ("Neo4j", "NEO4J INDIA PRIVATE LIMITED", mca.EXACT),
    ("Cohere Health", "COHERE HEALTH INDIA PRIVATE LIMITED", mca.EXACT),
    ("Airbnb", "AIRBNB INDIA PRIVATE LIMITED", mca.EXACT),
    ("Imply Data", "IMPLY DATA INDIA PRIVATE LIMITED", mca.EXACT),
    ("YipitData", "YIPITDATA INDIA PRIVATE LIMITED", mca.EXACT),
    # The register says MORE. Four of these five are plainly the right company
    # and the fifth (`FERN & ADE`, below) is plainly not, in the same shape —
    # which is why the tier exists and why none of them is published.
    ("Glean", "GLEAN SEARCH TECHNOLOGIES INDIA PRIVATE LIMITED", mca.PREFIX),
    ("Kaseya", "KASEYA SOFTWARE INDIA PRIVATE LIMITED", mca.PREFIX),
    ("Netskope", "NETSKOPE SOFTWARE INDIA PRIVATE LIMITED", mca.PREFIX),
    ("Airbnb", "AIRBNB PAYMENTS INDIA PRIVATE LIMITED", mca.PREFIX),
    ("Fern", "FERN & ADE INDIA PRIVATE LIMITED", mca.PREFIX),
    # A different company whose registered name opens with the same letters.
    # These are the false positives, and the word boundary is what stops all of
    # them: KONGSBERG is a Norwegian maritime group, not the API gateway;
    # NOTIONEXT, STRIPES ACADEMY and SCALEFFICIENT are nobody the corpus knows.
    ("Kong", "KONGSBERG MARITIME INDIA PRIVATE LIMITED", ""),
    ("Notion", "NOTIONEXT INDIA PRIVATE LIMITED", ""),
    ("Stripe", "STRIPES ACADEMY LEARNING AND DEVELOPMENT INDIA PRIVATE LIMITED", ""),
    ("Scale", "SCALEFFICIENT OUTSOURCED SOLUTIONS PRIVATE LIMITED", ""),
    # The other half of the boundary rule: the register may JOIN a company's
    # words but never SPLIT one. `Hightouch` is one word; this is two, and a
    # healthcare company.
    ("Hightouch", "HIGH TOUCH HEALTH SOLUTIONS GLOBAL PRIVATE LIMITED", ""),
]


def register(*names):
    """A snapshot holding exactly these registered names, CINs invented per row."""
    return mca.Snapshot(
        pulled="2026-07-29",
        companies=[{**COMPANY, "cin": f"U16000KA2018FTC{i:06d}", "name": name}
                   for i, name in enumerate(names)],
    )


def registered(*names):
    """The same, indexed for `find`."""
    return mca.index(register(*names)["companies"])


def labelled_pairs_verdicts():
    """Each labelled pair matched against a register holding only its own row.

    One row at a time is the point: a pair labelled `""` must find nothing
    because the two names disagree, not because a better candidate outranked it.

    The assertion over this lives in `tests/test_invariants.py` under the name
    VERIFICATION.md gives it, `test_20_known_pairs_zero_false_positives`.
    """
    return [(company, mca.find(company, registered(name))[0]) for company, name, _ in PAIRS]


def test_the_labelled_pairs_are_rows_the_register_really_holds():
    """The labels above are claims about MCA's data, so they are pinned to it.

    Without this the fixture is 20 strings somebody typed, and the obvious way
    to make a failing match go green is to edit the string it failed on.
    """
    known = {c["name"] for c in mca.load()["companies"]}
    assert known, "data/mca.json is missing; the labelled pairs cannot be checked"
    assert [name for _, name, _ in PAIRS if name not in known] == []


def test_a_register_that_says_LESS_than_the_company_is_not_a_match():
    """The direction that cannot be settled from the strings, refused rather
    than judged — `slugs.states_company`'s rule, anchored at the front.

    `COCKROACH INDIA` for `Cockroach Labs` is the same shape as `brave` for
    `Brave Care`: possibly the company, possibly a different one, and nothing in
    the register tells them apart.
    """
    assert mca.find("Cockroach Labs", registered("COCKROACH INDIA PRIVATE LIMITED")) == ("", [])


def test_below_threshold_held_for_review():
    """A plausible-but-unproven match is published nowhere and reported to a
    human — the third state between "matched" and "no such company"."""
    rows = [{"name": "Stripe", "mca": None}, {"name": "Glean", "mca": None},
            {"name": "Nobody At All", "mca": None}]

    held = mca.attach(rows, register(
        "STRIPE INDIA PRIVATE LIMITED", "GLEAN SEARCH TECHNOLOGIES INDIA PRIVATE LIMITED"
    ))

    assert rows[0]["mca"]["cin"] and rows[0]["mca"]["confidence"] == mca.EXACT
    assert rows[1]["mca"] is None, "a prefix match reached the site"
    assert rows[2]["mca"] is None
    assert [(h["name"], h["confidence"]) for h in held] == [("Glean", mca.PREFIX)]
    assert [c["name"] for c in held[0]["candidates"]] == [
        "GLEAN SEARCH TECHNOLOGIES INDIA PRIVATE LIMITED"
    ]
    # An unmatched company is not held: there is nothing for a human to settle.
    assert "Nobody At All" not in {h["name"] for h in held}


def test_two_registered_companies_at_the_same_tier_publish_neither():
    """`Scale` reaches `SCALE AI INDIA` and `SCALE FACILITATION PARTNERS INDIA`,
    and the corpus holds `Scale AI` as a separate company. Picking one would be
    inventing the answer; this is a question for a human."""
    rows = [{"name": "Scale", "mca": None}]

    held = mca.attach(rows, register("SCALE INDIA PRIVATE LIMITED", "SCALE PRIVATE LIMITED"))

    assert rows[0]["mca"] is None
    assert held[0]["confidence"] == mca.EXACT and len(held[0]["candidates"]) == 2


def test_city_is_the_district_field_not_the_locality():
    """The register writes `street,locality,district,state,pincode-India`.

    An earlier reading of one Mumbai row took the locality for the city, where
    both happened to say `Mumbai`. Measured over 24,102 rows the locality is a
    neighbourhood (`Kandivali West`), blank on 252 and a street fragment on 349;
    the district is never blank and reads as the city a person would name.
    """
    assert mca.city("Teleperformance Towers,Kandivali West,Mumbai,Maharashtra,400104-India") \
        == "Mumbai"
    # The register's own case noise: `NEW DELHI` and `New Delhi` are one place.
    assert mca.city("Plot 5,Vasant Kunj,NEW DELHI,Delhi,110070-India") == "New Delhi"
    # Absence, not a crash: a short address states no district.
    assert mca.city("Somewhere,411014-India") == ""


def test_attach_survives_a_register_that_was_never_pulled(tmp_path):
    """The enrichment reads a file that may not exist, and that costs the build
    nothing — the same guarantee `counts` gives the report. `load` turns every
    way of having no register into one empty snapshot, and an empty register
    matches nobody rather than raising."""
    rows = [{"name": "Stripe", "mca": None}]

    assert mca.attach(rows, mca.load(tmp_path / "never-pulled.json")) == []
    assert rows[0]["mca"] is None


#: The spine's own fixture, imported rather than rebuilt: this file asserts that
#: MCA's absence doesn't disturb it, which is only worth anything if it is the
#: build the project actually ships.
_CORPUS = [
    {
        "name": "Acme",
        "amount": 21000000,
        "currency": "USD",
        "date": "2026-07-28",
        "round_letter": "A",
        "source_url": "https://www.finsmes.com/2026/07/acme-raises-21m.html",
        "qualified_by": "letter",
    }
]
_SLUGS = {"Acme": {"ats": "greenhouse", "slug": "acme", "method": "careers-page"}}
def _board(slug):
    return [
        {"title": "Engineer", "absolute_url": "https://x.test/1",
         "location": {"name": "Bengaluru, India"}}
    ]


#: Both Greenhouse passes answer the same board, as the live API does. Left
#: unstubbed the description pass would be a live call from a unit test —
#: conftest refuses those, which is how this stub got written rather than
#: forgotten.
_PROBES = {"greenhouse": build.PROBES["greenhouse"]._replace(probe=_board, describe=_board)}
