"""The build spine — T5.1 (SPEC feature 12's emit half; the site reads this).

Corpus in, `data/companies.json` out, with every company that didn't make it
accounted for in `build-report.json` under exactly one outcome. This is the one
place the four existing modules meet, and it stays a spine rather than a
framework: no plugin registry, no pipeline abstraction, just the five steps the
architecture line in SPEC.md names.

The schema is versioned and *enforced on the way out*. A non-conforming row
raises instead of shipping, because a wrong row on a static site outlives the
build that made it — the JSON is served straight to the browser with nothing in
between to catch it. Validation belongs at the write, not at the read.
"""
from __future__ import annotations

import json
import re
import sys
from collections.abc import Callable, Iterable, Mapping
from datetime import date
from pathlib import Path
from typing import Any, NamedTuple

from src import ashby, greenhouse, lever, mca, salary
from src.greenhouse import Roles
from src.india import WORKPLACES, cities, is_india, workplace
from src.outcomes import Outcome, report, write_report
from src.slugs import Slug

#: Bump when a row's shape changes. The site reads this and refuses a version it
#: doesn't know, rather than silently rendering fields that moved.
#: v2 added `cities` — the site's city filter is the one thing it cannot fake.
#: v3 made `date` nullable and admitted `qualified_by: "stage"` — a directory
#: source (T1.2) can state that a company is past Series A without stating which
#: round or when, and the site has to render that absence rather than a guess.
#: v4 replaced the `india_roles` count with the `roles` themselves (T4.1): a
#: title, an apply URL, the places the board named and how it says the role is
#: worked. The count is `len(roles)` — carrying both invites them to disagree.
#: v5 added `salary` (T4.2), which is null for most rows and must be: it is the
#: first field the site renders only when the enrichment found something.
#: v6 added `mca` (T4.4) — a CIN, the name it is registered under, and how sure
#: the match is. Null for most rows by construction, not by failure: the register
#: slice covers subsidiaries of foreign-incorporated parents, so an India-founded
#: company can never carry one.
#: v7 added `integrity` (T5.3) — how many companies this build checked and how
#: many it could not. It is the only field that describes the companies NOT in
#: the file, and the site cannot derive it: a renderer counting its own rows can
#: only ever report "116 of 116".
SCHEMA_VERSION = 7

Probe = Callable[[str], Roles | Outcome]
Row = dict[str, Any]


class Provider(NamedTuple):
    """How to read one ATS: fetch a board, find the places in a role, and know
    which fields spell the rest of it.

    `locations` is a function because the providers disagree on the *shape* —
    Greenhouse nests a single `location.name`, Ashby has a flat `location` plus
    a `secondaryLocations` array, Lever an `allLocations` that already contains
    its primary. The three below are plain field names because there the
    providers disagree only on *spelling*: every one of 1,112 measured India
    roles carries a string title and a string URL at some flat key (T4.1). A
    function per provider to return `role["title"]` would be an abstraction over
    a difference that is just a word.

    `workplace` is None for Greenhouse because Greenhouse states this nowhere —
    not on the role, not in `metadata`. That absence is the field's real value.
    """

    probe: Probe
    locations: Callable[[Mapping[str, Any]], list[str]]
    title: str
    #: The posting's own page — the one a human opens to read the role and
    #: apply. Ashby and Lever also expose a deep link straight to the form
    #: (`applyUrl`), which Greenhouse has no counterpart for; the posting page
    #: is the link all three can give, and it carries the apply button anyway.
    url: str
    workplace: str | None


#: A row: what the corpus knew about the funding, plus what the board proved
#: about the hiring. Types only — the value rules that carry meaning are in
#: `errors`. `amount`, `round_letter` and `date` are all nullable because the
#: sources genuinely differ in what they state, and the site renders each
#: absence as an absence.
FIELDS: dict[str, type | tuple[type, ...]] = {
    "name": str,
    "ats": str,
    "slug": str,
    "roles": list,
    "cities": list,
    "amount": (int, type(None)),
    "currency": (str, type(None)),
    "round_letter": (str, type(None)),
    "date": (str, type(None)),
    "source_url": str,
    "qualified_by": str,
    "salary": (dict, type(None)),
    "mca": (dict, type(None)),
}

#: Every ATS this corpus holds a slug for. With Lever in, no company is
#: `probe-failed` for want of a probe — the outcome now means only what it says,
#: that we tried and could not read the board.
PROBES: dict[str, Provider] = {
    "greenhouse": Provider(greenhouse.probe, greenhouse.locations, "title", "absolute_url", None),
    "ashby": Provider(ashby.probe, ashby.locations, "title", "jobUrl", "workplaceType"),
    "lever": Provider(lever.probe, lever.locations, "text", "hostedUrl", "workplaceType"),
}

#: A role's fields, and the same refusal as the row's: the site renders these
#: straight into a link, so a role that can't state a title and a URL is not a
#: role this can publish. Measured 1,112/1,112 carry both — so a violation here
#: is a provider changing its payload, and the build failing loudly is the alarm.
ROLE_FIELDS = ("title", "url", "locations", "workplace")

#: A benchmark's fields (T4.2). `observed` is required rather than optional, and
#: that is SPEC feature 8's "renders the figure with its date" made deterministic:
#: the source's figures were last recomputed anywhere from nine months ago to
#: today, so a figure that arrives without its date is not publishable — it would
#: read as a statement about now. Absence of the whole benchmark is fine; a
#: benchmark that can't say when is not.
SALARY_FIELDS = ("avg_lpa", "reports", "observed", "source_url")

#: An MCA registration's fields (T4.4). A CIN names a real legal entity, so this
#: is the one enrichment whose mistake is a public claim about somebody else's
#: company — hence the shape check on the identifier itself and the refusal of
#: any confidence below the publish threshold.
MCA_FIELDS = ("cin", "name", "incorporated", "city", "status", "confidence")

#: The footer's counts (T5.3), lifted from the build report rather than derived
#: from the rows. `checked` is the companies whose board we actually read —
#: `outcomes.CHECKED`, listed or not — and `unchecked` is every absence of
#: knowledge. They are here, in the data file, so the site stays one fetch and so
#: the numbers it shows are the ones the report accounted for.
INTEGRITY_FIELDS = ("corpus_size", "checked", "unchecked")

#: A CIN as the register issues it: listing status, industry code, state, year of
#: incorporation, ownership class and the registration number. All 24,102 rows in
#: the snapshot conform, so a row that doesn't is a parse gone wrong rather than
#: an unusual company.
CIN = re.compile(r"[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}")


def _shape(found: Mapping[str, Any], names: Iterable[str]) -> list[str]:
    """Fields the schema names and this mapping doesn't, and the reverse.

    Unknown fields are a violation, not a courtesy: an enrichment that adds a
    field without bumping the version is exactly how the site starts rendering
    something the schema never promised.
    """
    problems = [f"missing {f!r}" for f in names if f not in found]
    if extra := sorted(set(found) - set(names)):
        problems.append(f"unknown field(s) {extra}")
    return problems


def role_errors(role: Any) -> list[str]:
    """Every way one role fails the schema. Empty means it may ship.

    The location list is required to be non-empty, and that is the deterministic
    form of SPEC feature 7's "no company displays an empty location": a role
    became an India role by naming a place in India, so a role here with nothing
    to render its location from is a contradiction, not a gap.
    """
    if not isinstance(role, Mapping):
        return [f"is {type(role).__name__}, not a role"]
    problems = _shape(role, ROLE_FIELDS)
    if not (isinstance(role.get("title"), str) and role.get("title", "").strip()):
        problems.append(f"title {role.get('title')!r} is not a non-empty string")
    # http(s) only: the site refuses to link anything else (a `javascript:` href
    # from a third-party payload is the one that matters), so a row carrying it
    # would render a dead label where a human expects to apply.
    if not (isinstance(url := role.get("url"), str) and url.startswith(("http://", "https://"))):
        problems.append(f"url {role.get('url')!r} is not an http(s) URL")
    places = role.get("locations")
    if not (isinstance(places, list) and places and all(isinstance(p, str) and p for p in places)):
        problems.append(f"locations {places!r} is not a non-empty list of place names")
    if role.get("workplace") not in (*WORKPLACES, None):
        problems.append(f"workplace {role.get('workplace')!r} is not one of {WORKPLACES} or None")
    return problems


def salary_errors(found: Any) -> list[str]:
    """Every way one salary benchmark fails the schema. Empty means it may ship.

    A row with no benchmark is normal — 51 of 116 measured — and `errors` never
    calls this for one. What this refuses is a benchmark that is present but
    can't be read honestly: no date, no sample size, or a figure the site would
    render as "₹0.0L".
    """
    if not isinstance(found, Mapping):
        return [f"is {type(found).__name__}, not a benchmark"]
    problems = _shape(found, SALARY_FIELDS)
    avg = found.get("avg_lpa")
    if not (isinstance(avg, int | float) and not isinstance(avg, bool) and avg > 0):
        problems.append(f"avg_lpa {avg!r} is not a positive number")
    if not (isinstance(n := found.get("reports"), int) and not isinstance(n, bool) and n > 0):
        problems.append(f"reports {n!r} is not a positive count")
    # The date the SOURCE stated, not the build's — see SALARY_FIELDS.
    if not salary.is_iso_date(found.get("observed")):
        problems.append(f"observed {found.get('observed')!r} is not an ISO date")
    if not (isinstance(url := found.get("source_url"), str) and url.startswith("https://")):
        problems.append(f"source_url {url!r} is not an https URL")
    return problems


def mca_errors(found: Any) -> list[str]:
    """Every way one MCA registration fails the schema. Empty means it may ship.

    A row with no registration is the normal case — 84 of 116 measured, and most
    of those can never have one — and `errors` never calls this for one. What
    this refuses is a registration the site would render as a fact about a
    company that may not be this one: a malformed CIN, or a match the matcher
    itself held below the publish threshold.
    """
    if not isinstance(found, Mapping):
        return [f"is {type(found).__name__}, not a registration"]
    problems = _shape(found, MCA_FIELDS)
    if not (isinstance(cin := found.get("cin"), str) and CIN.fullmatch(cin)):
        problems.append(f"cin {cin!r} is not a CIN")
    for field in ("name", "status"):
        if not (isinstance(value := found.get(field), str) and value.strip()):
            problems.append(f"{field} {value!r} is not a non-empty string")
    if not salary.is_iso_date(found.get("incorporated")):
        problems.append(f"incorporated {found.get('incorporated')!r} is not an ISO date")
    # Blank is legal: the register writes the city into an address field, and a
    # short address is an absence the site renders as one.
    if not isinstance(found.get("city"), str):
        problems.append(f"city {found.get('city')!r} is not a string")
    if found.get("confidence") != mca.EXACT:
        problems.append(f"confidence {found.get('confidence')!r} is below the publish threshold")
    return problems


def integrity_errors(found: Any, listed: int) -> list[str]:
    """Every way the footer's counts fail the schema. Empty means they may ship.

    On the real path these are three fields copied out of a report that computed
    `unchecked` as a subtraction, so the sum can only hold. What this catches is
    the counts and the rows describing different builds: a hand-written dataset
    (the e2e fixture), or a report from another run — `checked` below the number
    of rows shipped means the footer is accounting for a build that isn't this
    one. That is the failure the footer exists to make impossible, so it is
    refused at the write like every other claim the site renders.
    """
    if not isinstance(found, Mapping):
        return [f"is {type(found).__name__}, not a count of what was checked"]
    problems = _shape(found, INTEGRITY_FIELDS)
    for field in INTEGRITY_FIELDS:
        count = found.get(field)
        if not (isinstance(count, int) and not isinstance(count, bool) and count >= 0):
            problems.append(f"{field} {count!r} is not a count")
    if problems:
        return problems
    if found["checked"] + found["unchecked"] != found["corpus_size"]:
        problems.append(
            f"checked {found['checked']} + unchecked {found['unchecked']} is not the "
            f"{found['corpus_size']}-company corpus: the footer would not add up"
        )
    if found["checked"] < listed:
        problems.append(f"checked {found['checked']} is fewer than the {listed} companies listed")
    return problems


def errors(row: Mapping[str, Any]) -> list[str]:
    """Every way this row fails the current schema. Empty means it may ship.

    The fields it names are checked for type here; the value rules that carry
    meaning follow, and the nested shapes are `role_errors` and `salary_errors`.
    """
    problems = _shape(row, FIELDS)
    problems += [
        f"{field!r} is {type(row[field]).__name__}, not {types}"
        for field, types in FIELDS.items()
        if field in row and not isinstance(row[field], types)
    ]

    # A listed company is one whose board we read and found India roles on. An
    # empty list here would be a row saying "listed, hiring nobody" — the
    # ambiguous zero this project exists to refuse.
    if isinstance(roles := row.get("roles"), list):
        if not roles:
            problems.append("roles is empty: a listed company has at least one India role")
        problems += [f"roles[{i}]: {p}" for i, role in enumerate(roles) for p in role_errors(role)]
    # An empty city list is legal (a role can be "Remote - India"); a non-string
    # inside it is not, because the site renders these straight into the filter.
    if isinstance(row.get("cities"), list) and not all(isinstance(c, str) for c in row["cities"]):
        problems.append(f"cities {row['cities']!r} is not a list of strings")
    # Null is the common case and always legal. A benchmark that is *there* is
    # held to the same bar as everything else the site renders.
    if row.get("salary") is not None:
        problems += [f"salary: {p}" for p in salary_errors(row["salary"])]
    if row.get("mca") is not None:
        problems += [f"mca: {p}" for p in mca_errors(row["mca"])]
    # The three rules corpus._qualified_by can fire. A row qualified by anything
    # else was admitted by a rule the site has no wording for.
    if row.get("qualified_by") not in ("letter", "amount", "stage"):
        problems.append(f"qualified_by {row.get('qualified_by')!r} is not a corpus rule")
    if row.get("ats") not in PROBES:
        problems.append(f"ats {row.get('ats')!r} has no probe, so nothing verified this row")
    return problems


def posting(role: Mapping[str, Any], provider: Provider, places: list[str]) -> Row:
    """One India role as the site renders it: what it's called, where to apply,
    the places it names in India, and how it says it's worked.

    `places` is India-only, like the row's `cities`: this is a site about India
    roles, and a Bengaluru-and-Warsaw posting listed under "also Warsaw" would
    be answering a question nobody came here with.

    Where the board states a workplace it is believed over the location string,
    because it is the field that exists to answer this question — Ashby's
    `OnSite` and Lever's `onsite` join `india.workplace`'s vocabulary on a
    `.lower()`. The two disagreed on 2 of 173 measured roles (a role located
    `India - Remote` stating `OnSite`), which is the company contradicting
    itself; the string carries the other 939, where Greenhouse states nothing.
    """
    stated = role.get(provider.workplace) if provider.workplace else None
    title = role.get(provider.title)
    return {
        # Real titles arrive padded (` Software Engineer `, live on two boards).
        # Anything that isn't a string passes through to fail validation as what
        # it is, rather than crashing here.
        "title": title.strip() if isinstance(title, str) else title,
        "url": role.get(provider.url),
        "locations": places,
        "workplace": stated.lower() if isinstance(stated, str) else workplace("; ".join(places)),
    }


def build(
    corpus: Iterable[Mapping[str, Any]],
    slugs: Mapping[str, Slug],
    probes: Mapping[str, Provider] = PROBES,
) -> tuple[list[Row], dict[str, Outcome]]:
    """The spine: corpus → slug → board → India filter → rows.

    Returns the listed rows and one outcome per company. Every `continue` below
    is a company leaving with a reason attached; none of them can fall through
    into the site, and none of them becomes an empty role list.
    """
    rows: list[Row] = []
    outcomes: dict[str, Outcome] = {}

    for company in corpus:
        name = company["name"]
        slug = slugs.get(name)
        if slug is None:
            outcomes[name] = Outcome.SLUG_UNRESOLVED
            continue

        provider = probes.get(slug["ats"])
        if provider is None:
            outcomes[name] = Outcome.PROBE_FAILED
            continue

        result = provider.probe(slug["slug"])
        if isinstance(result, Outcome):
            outcomes[name] = result
            continue

        # A role, not a location string: one Ashby posting open in Bengaluru and
        # Mumbai is one role in two cities, and counting the strings would
        # report it as two jobs.
        india = [
            posting(role, provider, places)
            for role in result
            if (places := [p for p in provider.locations(role) if is_india(p)])
        ]
        if not india:
            outcomes[name] = Outcome.NO_INDIA_ROLES
            continue

        outcomes[name] = Outcome.LISTED
        rows.append(
            {
                "name": name,
                "ats": slug["ats"],
                "slug": slug["slug"],
                "roles": india,
                "cities": sorted(
                    {c for role in india for p in role["locations"] for c in cities(p)}
                ),
                "amount": company["amount"],
                "currency": company["currency"],
                "round_letter": company["round_letter"],
                "date": company["date"],
                "source_url": company["source_url"],
                "qualified_by": company["qualified_by"],
                # The spine states the absence; the enrichments fill in what they
                # can find afterwards. An enrichment inside the loop would put a
                # third-party site between a company and being listed at all.
                "salary": None,
                "mca": None,
            }
        )

    return rows, outcomes


def website_counts(
    corpus: Iterable[Mapping[str, Any]], outcomes: Mapping[str, Outcome]
) -> dict[str, int]:
    """How many companies we have an address for, and how the ones we found no
    board for split by whether we had one.

    Both halves land on `slug-unresolved`, and until T1.6 that hid which
    bottleneck the site was actually up against: a company whose own careers page
    named no board wants a better slug method, while a company we never had an
    address for wants a better website source. Counting them apart is what makes
    the next task's target visible rather than inferred.
    """
    unresolved = [c for c in corpus if outcomes.get(c["name"]) is Outcome.SLUG_UNRESOLVED]
    return {
        "with_website": sum(1 for c in corpus if c.get("website")),
        "slug_unresolved_with_website": sum(1 for c in unresolved if c.get("website")),
        "slug_unresolved_without_website": sum(1 for c in unresolved if not c.get("website")),
    }


def write(
    path: str | Path,
    rows: list[Row],
    built: Mapping[str, Any],
    snapshot: str | None = None,
) -> None:
    """Emit companies.json — or refuse to, loudly, and leave the last good file
    where it is. The snapshot date ships with the data because the site has to
    show it (SPEC feature 10) and a date computed at render time would claim a
    freshness the JSON doesn't have.

    `built` is this run's own build report, and the footer's counts are taken
    from it (T5.3). The site is a renderer: it can see the companies that made
    it, and only the report knows how many didn't.
    """
    counted = {field: built[field] for field in INTEGRITY_FIELDS if field in built}
    bad = {row.get("name"): problems for row in rows if (problems := errors(row))}
    if problems := integrity_errors(counted, len(rows)):
        bad["integrity"] = problems
    if bad:
        raise ValueError(f"schema v{SCHEMA_VERSION} violations, nothing written: {bad}")

    Path(path).write_text(
        json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "snapshot": snapshot or date.today().isoformat(),
                "integrity": counted,
                "companies": rows,
            },
            indent=2,
        )
        + "\n"
    )


#: init.sh's smoke test drives the whole emit path offline through a fixture
#: board — the same build/validate/write code the real run uses, in
#: milliseconds, with no live API. It writes its OWN file: a smoke test must
#: never overwrite the published artifact, and a fixture-derived
#: companies.json is precisely the lie T6.4 exists to prevent.
SMOKE_BOARD = Path("tests/fixtures/greenhouse-board.json")
SMOKE_OUT = "data/companies.smoke.json"


def main(argv: list[str]) -> None:
    corpus = json.loads(Path("data/corpus.json").read_text())["companies"]
    slugs: dict[str, Slug] = json.loads(Path("data/slugs.json").read_text())
    out = "data/companies.json"

    if smoke := ("--smoke" in argv):
        corpus = corpus[:1]
        slugs = {c["name"]: Slug(ats="greenhouse", slug="smoke", method="smoke") for c in corpus}
        board = greenhouse.parse(SMOKE_BOARD.read_text())
        probes = {"greenhouse": PROBES["greenhouse"]._replace(probe=lambda _: board)}
        out = SMOKE_OUT
    else:
        # Ashby's cost is a server-side delay, not throughput, so its boards are
        # fetched together up front and the spine reads the answers. Sequentially
        # this is the one provider that could put a real run outside the nightly
        # budget if its throttling returns (src/ashby.py).
        boards = ashby.probe_all(s["slug"] for s in slugs.values() if s["ats"] == "ashby")
        probes = {
            **PROBES,
            "ashby": PROBES["ashby"]._replace(
                probe=lambda slug: boards.get(slug, Outcome.PROBE_FAILED)
            ),
        }

    rows, outcomes = build(corpus, slugs, probes)
    # Enrichment, after the spine and outside it: it runs on the listed rows
    # only, it cannot change who is listed, and every failure inside it is an
    # absent field rather than a failed build. `salary` is skipped in smoke for
    # the same reason the probes are — the smoke path touches no network. The
    # MCA match reads a local file, so it runs there too and init.sh proves the
    # whole enrichment offline rather than only the report line.
    if not smoke:
        salary.attach(rows)
    held = mca.attach(rows)

    # The report comes first now: the site's footer counts what this build could
    # not check (T5.3), and those numbers are the report's, copied rather than
    # counted twice.
    built = report([c["name"] for c in corpus], outcomes)
    write(out, rows, built)

    built["websites"] = website_counts(corpus, outcomes)
    # Off the disk, never off the API: data.gov.in 502s under sustained load, and
    # a nightly build that called it inline would be a site that goes down when
    # somebody else's Elasticsearch does. `src/mca.py` refreshes the cache by
    # hand; this only ever reads it, and reads nothing as zero.
    #
    # `held` is the honest half of the match: names the register plausibly knows
    # under a longer spelling, published nowhere and listed here so a human can
    # settle them. It is a work list, not a failure.
    built["mca"] = {
        **mca.counts(),
        "matched": sum(1 for row in rows if row["mca"]),
        "held": held,
    }
    if not smoke:
        write_report("data/build-report.json", built)

    print(f"{out}: {len(rows)} listed of {built['corpus_size']} in corpus")
    for outcome, count in sorted(built["counts"].items()):
        if count:
            print(f"  {count:4d}  {outcome}")
    for label, count in built["websites"].items():
        print(f"  {count:4d}  {label}")
    print(f"  {built['mca']['records']:4d}  MCA foreign subsidiaries cached "
          f"(pulled {built['mca']['pulled'] or 'never'})")
    print(f"  {built['mca']['matched']:4d}  matched to a CIN, "
          f"{len(built['mca']['held'])} held for review")


if __name__ == "__main__":
    main(sys.argv[1:])
