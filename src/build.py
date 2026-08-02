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

from src import ashby, corrections, greenhouse, lever, mca, salary, uk
from src.countries import COUNTRIES, countries
from src.greenhouse import Roles
from src.india import WORKPLACES, cities, workplace
from src.openness import VERDICTS, classify
from src.outcomes import Outcome, report, write_report
from src.slugs import Slug, key, states_company

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
#: v8 widened the radar from India to fifteen countries (T8.4): a role states the
#: `countries` it matched and what its posting said about hiring from abroad
#: (`visa`, `hire_from_abroad`), and a company states the set its roles add up to.
#: The India-only fields stay exactly what they were — `cities`, `salary` and
#: `mca` describe India roles and nothing else, by decision (SPEC v2).
#: v9 added `department` to a role (T9.2) — the board's OWN word for where the
#: role sits, or null. Not the site's label and not a derivation: the site keeps
#: reading the title first (86.1% of roles, and the two disagree 26% of the time
#: over a difference of question, not of fact), and reads this only where the title
#: places nothing. Free to carry: it rides in payloads all three probes already
#: fetch — Greenhouse's `content=true` second pass, Ashby's and Lever's only call.
#: v10 added `uk` (T9.1) — the Companies House registration, or null. The UK
#: sibling of `mca` and NOT its generalisation: the two registers answer
#: different questions (MCA's slice is subsidiaries of foreign-incorporated
#: parents; Companies House covers every UK company), so a row can carry one,
#: both or neither, and each is said in its own register's words.
SCHEMA_VERSION = 10

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
    #: The posting's prose, flattened, for `openness.classify` (T8.4). A function
    #: for the same reason `locations` is: Ashby holds it in one field, Lever
    #: splits it across four, and Greenhouse only sends it when asked.
    text: Callable[[Mapping[str, Any]], str]
    title: str
    #: The posting's own page — the one a human opens to read the role and
    #: apply. Ashby and Lever also expose a deep link straight to the form
    #: (`applyUrl`), which Greenhouse has no counterpart for; the posting page
    #: is the link all three can give, and it carries the apply button anyway.
    url: str
    workplace: str | None
    #: Fetch the same board again, with the descriptions in it. None for the two
    #: providers that ship prose whether we want it or not — only Greenhouse
    #: charges for it, and only in bytes (T8.1). See `described`.
    describe: Probe | None = None
    #: The board's own word for where this role sits (T9.2), or None. A function
    #: because the three disagree on shape as well as spelling: Greenhouse nests a
    #: LIST (a job can hang off a department and its parent), Ashby and Lever
    #: state one string each. Defaulted so a provider that states nothing needs no
    #: entry — and measured, all three state something, on 99.6% of postings.
    department: Callable[[Mapping[str, Any]], str | None] = lambda _: None


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
    #: The countries this company's kept roles are in (T8.4) — derived from the
    #: roles, never stated separately, so the site's country tabs and the roles
    #: they reveal cannot disagree. `errors` enforces the derivation.
    "countries": list,
    #: India cities, and only India's — this field feeds the India view's city
    #: filter, and SPEC v2 keeps the per-country enrichments out of scope.
    "cities": list,
    "amount": (int, type(None)),
    "currency": (str, type(None)),
    "round_letter": (str, type(None)),
    "date": (str, type(None)),
    "source_url": str,
    "qualified_by": str,
    "salary": (dict, type(None)),
    "mca": (dict, type(None)),
    #: The Companies House registration (T9.1). A UK-role field, the way `mca`
    #: and `cities` are India's — the register covers UK companies and says
    #: nothing about anybody else.
    "uk": (dict, type(None)),
}

def stated(value: Any) -> str | None:
    """A board's word for something, or None where it said nothing usable.

    Blank is silence, not a department: Lever states `categories.department` on
    94.4% of postings and omits it on the rest, and an empty string reaching the
    site would render as a department nobody can read (T9.2).
    """
    return value.strip() or None if isinstance(value, str) else None


#: Every ATS this corpus holds a slug for. With Lever in, no company is
#: `probe-failed` for want of a probe — the outcome now means only what it says,
#: that we tried and could not read the board.
PROBES: dict[str, Provider] = {
    "greenhouse": Provider(
        probe=greenhouse.probe,
        locations=greenhouse.locations,
        text=greenhouse.text,
        title="title",
        url="absolute_url",
        workplace=None,
        describe=greenhouse.describe,
        department=greenhouse.department,
    ),
    "ashby": Provider(
        probe=ashby.probe,
        locations=ashby.locations,
        text=ashby.text,
        title="title",
        url="jobUrl",
        workplace="workplaceType",
        department=lambda role: stated(role.get("department")),
    ),
    "lever": Provider(
        probe=lever.probe,
        locations=lever.locations,
        text=lever.text,
        title="text",
        url="hostedUrl",
        workplace="workplaceType",
        department=lambda role: stated((role.get("categories") or {}).get("department")),
    ),
}

#: A role's fields, and the same refusal as the row's: the site renders these
#: straight into a link, so a role that can't state a title and a URL is not a
#: role this can publish. Measured 1,112/1,112 carry both — so a violation here
#: is a provider changing its payload, and the build failing loudly is the alarm.
#: T8.4 added `countries` (which of the fifteen this role is in) and the two
#: openness verdicts, which are `unknown` far more often than not and must be.
#: T9.2 added `department` — the board's own word, or null. Null is legal and
#: common (the whole reason the site keeps deriving from the title); what is
#: refused is the empty string, which would render as a department nobody typed.
ROLE_FIELDS = (
    "title", "url", "locations", "countries", "workplace", "visa", "hire_from_abroad",
    "department",
)

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

#: A Companies House registration's fields (T9.1). `url` is a field rather than
#: something the page builds from `number`, because the badge's whole claim is
#: that a reader can go and check it — the link is part of the fact. `uk_errors`
#: refuses a link that points at a different company from the number beside it.
UK_FIELDS = ("number", "name", "status", "incorporated", "city", "url", "confidence")

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

#: A UK company number as Companies House issues it: eight characters, either
#: eight digits (England and Wales) or a two-letter jurisdiction prefix and six
#: (`SC` Scotland, `NI` Northern Ireland, `OC`/`SO`/`NC` the LLP series, `FC`
#: overseas). Leading zeros are part of it — `09446231` is Monzo and `9446231`
#: is not a company number at all — which is why this ships as a string and is
#: length-checked rather than parsed as a number.
COMPANY_NUMBER = re.compile(r"\d{8}|[A-Z]{2}\d{6}")

#: The share of the last published companies a build must still list to publish
#: (T6.4). A broken provider does not fail this build — every probe returns
#: `probe-failed` on a bad status, by design — so a night when Greenhouse is down
#: produces a complete, schema-valid file with 88 of 116 companies missing, and
#: `set -e` in the nightly cannot see it. This is what sees it.
#:
#: Half, because that is the gap between measured churn and an outage. The spine
#: is byte-stable across runs hours apart (FINDINGS: 116 rows both times, zero
#: non-salary differences), and today's listed set is 88 greenhouse + 22 ashby +
#: 6 lever — so the biggest provider going dark leaves 24%, and any two leave
#: under 20%.
#:
#: ponytail: one number over the whole file, not a floor per provider. Ceiling:
#: Lever going dark leaves 95% and publishes — those 6 companies leave counted as
#: `probe-failed` and the footer's `checked` drops, which is the honest
#: degradation this project already ships for one company. Upgrade path: a
#: per-provider floor once 30 nights of snapshots exist to say what real churn
#: looks like — the same history T7.1 is blocked on.
COLLAPSE = 0.5


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
    became a kept role by naming a place in a target country, so a role here with
    nothing to render its location from is a contradiction, not a gap. `countries`
    is refused empty for the same reason and one step further along — it is what
    put the role here.

    The two openness verdicts are refused unless they are one of the three words
    `openness` emits. A role that reached the site carrying `null` or `""` there
    would render as an absence the site cannot tell from `unknown` — and the whole
    of SPEC feature 15 is that silence renders as unknown rather than as "no".
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
    where = role.get("countries")
    if not (isinstance(where, list) and where and all(c in COUNTRIES for c in where)):
        problems.append(f"countries {where!r} is not a non-empty list of target countries")
    if role.get("workplace") not in (*WORKPLACES, None):
        problems.append(f"workplace {role.get('workplace')!r} is not one of {WORKPLACES} or None")
    said = role.get("department")
    if not (said is None or (isinstance(said, str) and said.strip())):
        problems.append(f"department {said!r} is neither a non-empty string nor absent")
    problems += [
        f"{field} {role.get(field)!r} is not one of {VERDICTS}"
        for field in ("visa", "hire_from_abroad")
        if role.get(field) not in VERDICTS
    ]
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


def uk_errors(found: Any) -> list[str]:
    """Every way one Companies House registration fails the schema. Empty means
    it may ship.

    A row with no registration is the normal case and `errors` never calls this
    for one. What this refuses is a registration the site would render as a fact
    about a company that may not be this one: a malformed company number, a link
    that points somewhere other than the number beside it, a match the matcher
    held below the publish threshold — or a company the register has struck off,
    which contradicts the live job board that put the row here at all.

    The status is checked and NEVER rewritten. `liquidation` and `administration`
    ship as the register spells them (T9.1's DoD: a company in difficulty must
    not render as one that is fine); only the four states that mean the company
    is off the register are refused.
    """
    if not isinstance(found, Mapping):
        return [f"is {type(found).__name__}, not a registration"]
    problems = _shape(found, UK_FIELDS)
    number = found.get("number")
    if not (isinstance(number, str) and COMPANY_NUMBER.fullmatch(number)):
        problems.append(f"number {number!r} is not a UK company number")
    for field in ("name", "status"):
        if not (isinstance(value := found.get(field), str) and value.strip()):
            problems.append(f"{field} {value!r} is not a non-empty string")
    if not salary.is_iso_date(found.get("incorporated")):
        problems.append(f"incorporated {found.get('incorporated')!r} is not an ISO date")
    # Blank is legal: the register leaves a registered office's locality out on
    # a real minority of records, and the site renders that absence as one.
    if not isinstance(found.get("city"), str):
        problems.append(f"city {found.get('city')!r} is not a string")
    if found.get("url") != uk.PUBLIC + str(number):
        problems.append(f"url {found.get('url')!r} does not lead to company {number!r}")
    if found.get("status") in uk.DEAD:
        problems.append(
            f"status {found.get('status')!r}: this company's live board is what listed it"
        )
    if found.get("confidence") != uk.STATED:
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

    # A listed company is one whose board we read and found target-country roles
    # on. An empty list here would be a row saying "listed, hiring nobody" — the
    # ambiguous zero this project exists to refuse.
    if isinstance(roles := row.get("roles"), list):
        if not roles:
            problems.append("roles is empty: a listed company has at least one target-country role")
        problems += [f"roles[{i}]: {p}" for i, role in enumerate(roles) for p in role_errors(role)]
        # The country set is derived, so the only thing to check is that it is
        # still the derivation. A row whose tabs and roles disagree would put a
        # company under a country tab that none of its roles is in — the site's
        # version of the ambiguous zero.
        stated = [
            role["countries"]
            for role in roles
            if isinstance(role, Mapping) and isinstance(role.get("countries"), list)
        ]
        derived = [c for c in COUNTRIES if any(c in where for where in stated)]
        if row.get("countries") != derived:
            problems.append(f"countries {row.get('countries')!r} is not its roles' {derived}")
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
    if row.get("uk") is not None:
        problems += [f"uk: {p}" for p in uk_errors(row["uk"])]
    # The three rules corpus._qualified_by can fire. A row qualified by anything
    # else was admitted by a rule the site has no wording for.
    if row.get("qualified_by") not in ("letter", "amount", "stage"):
        problems.append(f"qualified_by {row.get('qualified_by')!r} is not a corpus rule")
    if row.get("ats") not in PROBES:
        problems.append(f"ats {row.get('ats')!r} has no probe, so nothing verified this row")
    return problems


def matched(role: Mapping[str, Any], provider: Provider) -> tuple[list[str], list[str]]:
    """The places this role names in a target country, and the countries they name.

    Both lists are empty for a role we do not keep, so `if matched(...)[0]` is the
    filter. A role can genuinely be in two of the fifteen — "London, UK; Sydney,
    Australia" is one posting — and both countries come back, in COUNTRIES order.

    The places a role names OUTSIDE the fifteen are dropped here and never reach
    the row, which is T4.1's rule widened rather than changed: a Bengaluru-and-
    Warsaw posting is listed for its Bengaluru half, because "also Warsaw" answers
    a question nobody came here with. Poland is not on the map; it is not a place
    this site has anything to say about.

    Called twice per kept role — once to decide whether to keep it, once to build
    it — because a pure function called twice reads better here than its result
    threaded through the spine's loop. It is a regex over a handful of short
    strings, and the roles it runs on twice are the few that reach a row.
    """
    found = [(place, countries(place)) for place in provider.locations(role)]
    keep = [(place, where) for place, where in found if where]
    return (
        [place for place, _ in keep],
        [c for c in COUNTRIES if any(c in where for _, where in keep)],
    )


def described(provider: Provider, slug: str, roles: Roles) -> Roles:
    """The same roles, with their description text in them (T8.4).

    Two of the three providers ship prose whether we ask or not, so for them this
    is the identity and the whole function is one branch. Greenhouse charges for
    it — 13.7x-35.3x the bytes, under 2x the latency, on the same single call —
    so it is fetched here, AFTER the country filter has proved the board can
    contribute a row. T8.1 measured that ordering: 259 of 422 Greenhouse boards
    have no posting in any target country, and paying the multiplier on those is
    the whole avoidable cost.

    Roles are re-identified by their apply URL, which every one of 1,112 measured
    roles carries and which is unique per posting. A role the second pass does not
    return keeps the cheap version and classifies as `unknown` — a board that
    changed between two calls seconds apart costs us the openness of one posting,
    never the posting itself. A second pass that fails entirely costs the same,
    for every role on the board: `probe-failed` is for a company we could not
    read, and we did read this one.

    ponytail: sequential, one extra call per contributing board, inside the
    provider loop. Measured ceiling — the whole corpus, both passes, is 1m55s and
    270MB at 10 concurrent callers (T8.1) against a 90-minute nightly timeout;
    sequentially the second pass adds roughly the first pass's Greenhouse time
    again, on 163 of 422 boards. Upgrade path when that stops fitting:
    `ashby.probe_all` is the concurrent version of exactly this loop.
    """
    if provider.describe is None:
        return list(roles)
    rich = provider.describe(slug)
    if isinstance(rich, Outcome):
        return list(roles)
    prose = {role.get(provider.url): role for role in rich}
    return [prose.get(role.get(provider.url), role) for role in roles]


def posting(role: Mapping[str, Any], provider: Provider) -> Row:
    """One kept role as the site renders it: what it's called, where to apply, the
    places it names in countries we cover, how it says it's worked, and what its
    description says about hiring someone who is not already there.

    The openness pair is `unknown`/`unknown` for the large majority of roles and
    that is the measured normal case (92.32% of 4,311 postings say nothing at
    all), not a gap. It is also what a role gets when the description never
    arrived — `openness.classify` reads "" as silence, which is exactly what we
    know about a posting we did not fetch the text of.

    Where the board states a workplace it is believed over the location string,
    because it is the field that exists to answer this question — Ashby's
    `OnSite` and Lever's `onsite` join `india.workplace`'s vocabulary on a
    `.lower()`. The two disagreed on 2 of 173 measured roles (a role located
    `India - Remote` stating `OnSite`), which is the company contradicting
    itself; the string carries the other 939, where Greenhouse states nothing.
    """
    places, where = matched(role, provider)
    said = role.get(provider.workplace) if provider.workplace else None
    title = role.get(provider.title)
    return {
        # Real titles arrive padded (` Software Engineer `, live on two boards).
        # Anything that isn't a string passes through to fail validation as what
        # it is, rather than crashing here.
        "title": title.strip() if isinstance(title, str) else title,
        "url": role.get(provider.url),
        "locations": places,
        "countries": where,
        "workplace": said.lower() if isinstance(said, str) else workplace("; ".join(places)),
        # The board's word, carried verbatim and never mapped here (T9.2). The
        # site owns the department vocabulary — it derives one from the title for
        # 86.1% of roles — and a build that pre-mapped this would be two
        # classifiers disagreeing in two languages.
        "department": provider.department(role),
        **classify(provider.text(role))._asdict(),
    }


def shared_boards(
    slugs: Mapping[str, Slug], stated: Callable[[str], str | None] = greenhouse.board_name
) -> dict[str, str]:
    """Names that must not be listed because the board they resolved to is
    another corpus company's, each mapped to the company whose board it is (T10.1).

    Two corpus rows can be one employer, and the corpus cannot see it: EDGAR
    files Grafana Labs' round under `Raintank Inc`, its legal name, so the corpus
    holds both — and both careers pages lead to `greenhouse/grafanalabs`. Listed
    as two, they publish one board's 75 roles twice and count one company twice.
    The board is what settles it: two names reading one board are one employer,
    whatever the sources call them. Measured over the 708 resolved slugs, 10
    boards were shared by exactly 2 names each.

    Which name survives is the board's answer, not ours: it states one (Greenhouse
    does; `states_company` is T2.2's rule for whether it is this company's), and
    the longest corpus name that board confirms wins — "Scale AI" over "Scale"
    for a board called `Scale AI`, "Grafana Labs" over "Raintank" for one called
    `Grafana Labs`. Where the board names nobody — Ashby and Lever publish no
    company name at all, and one Greenhouse board answered `null` — the first
    name alphabetically wins, which is arbitrary but identical every run.
    ponytail: no second source consulted for those. Ceiling: 3 of the 10 pick a
    name a human might spell differently ("Fireworks" for "Fireworks AI"); both
    names are the same employer either way, which is the wrong this fixes.
    """
    by_board: dict[tuple[str, str], list[str]] = {}
    for name, slug in sorted(slugs.items()):
        by_board.setdefault((slug["ats"], slug["slug"]), []).append(name)

    shared: dict[str, str] = {}
    for (ats, slug_), names in by_board.items():
        if len(names) == 1:
            continue
        board = stated(slug_) if ats == "greenhouse" else None
        confirmed = [name for name in names if states_company(board, name)]
        owner = max(confirmed, key=lambda name: len(key(name))) if confirmed else names[0]
        shared.update({name: owner for name in names if name != owner})
    return shared


def build(
    corpus: Iterable[Mapping[str, Any]],
    slugs: Mapping[str, Slug],
    probes: Mapping[str, Provider] = PROBES,
    shared: Mapping[str, str] | None = None,
) -> tuple[list[Row], dict[str, Outcome]]:
    """The spine: corpus → slug → board → country filter → descriptions → rows.

    Returns the listed rows and one outcome per company. Every `continue` below
    is a company leaving with a reason attached; none of them can fall through
    into the site, and none of them becomes an empty role list.

    `shared` is `shared_boards` plus the corrections file's `board` lines — the
    names whose board belongs to somebody else. They leave first, before the
    board is read at all: a name that cannot be listed under any outcome should
    not spend a fetch to find that out.
    """
    rows: list[Row] = []
    outcomes: dict[str, Outcome] = {}
    shared = shared or {}

    for company in corpus:
        name = company["name"]
        if name in shared:
            outcomes[name] = Outcome.ANOTHER_COMPANYS_BOARD
            continue

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
        kept = [role for role in result if matched(role, provider)[0]]
        if not kept:
            outcomes[name] = Outcome.NO_TARGET_ROLES
            continue

        # The descriptions are fetched only now, for a board that has already
        # proved it contributes a row (T8.4). Nothing below can change who is
        # listed — a role's openness is a fact about the posting, never a filter.
        roles = [posting(role, provider) for role in described(provider, slug["slug"], kept)]
        outcomes[name] = Outcome.LISTED
        rows.append(
            {
                "name": name,
                "ats": slug["ats"],
                "slug": slug["slug"],
                "roles": roles,
                "countries": [c for c in COUNTRIES if any(c in r["countries"] for r in roles)],
                # India cities only, because `india.cities` names only India's:
                # a London role contributes nothing here and the site's city
                # filter stays the India view's, exactly as it was.
                "cities": sorted(
                    {c for role in roles for p in role["locations"] for c in cities(p)}
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
                "uk": None,
            }
        )

    return rows, outcomes


def country_counts(rows: Iterable[Row]) -> dict[str, int]:
    """How many listed companies have at least one role in each target country.

    All fifteen are present, zeros included, because a zero here is a finding
    like every other zero in this project: we read the boards and none of them
    was hiring in Norway. A country left out of the mapping would read as one we
    never looked at, and the site's tabs would have no way to tell the two apart.

    Companies, not roles, and a company in two countries is counted in both — so
    these do NOT sum to the number listed. That is the honest shape: a role in
    London and Sydney is one job you can take in either place.
    """
    listed = list(rows)
    return {
        country: sum(1 for row in listed if country in row["countries"])
        for country in COUNTRIES
    }


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


#: The one reason a departure has no outcome: the report accounts for the corpus,
#: and a company the sources have dropped is not in it to account for.
LEFT_THE_CORPUS = "left-the-corpus"


def departures(previous: Iterable[Row], assigned: Mapping[str, str]) -> dict[str, str]:
    """Every company the last published build listed and this one does not,
    mapped to the reason it went — T10.4.

    `report` already accounts for every company IN the corpus under exactly one
    outcome, which covers a company that stopped hiring or whose board stopped
    answering. It cannot cover the other direction: a corpus rebuild can drop a
    name outright (FinSMEs re-paginates, a directory delists), and that company
    is then in no outcome at all because there is nothing left to assign one to.
    So a listed set can shrink for a reason nothing states, which is the one
    shape of loss this project has no other check for.

    Named rather than counted, like `shared_boards`: "4 companies left" is a
    number nobody can act on, and the names are what tells a human whether a
    source broke or a company really went away.
    """
    # `published` is deliberately forgiving about what it reads back, so a row
    # that cannot say what it is called is skipped here rather than crashing the
    # report that exists to explain the loss.
    names = [row["name"] for row in previous if isinstance(row.get("name"), str)]
    return {
        name: assigned.get(name, LEFT_THE_CORPUS)
        for name in names
        if assigned.get(name) != Outcome.LISTED.value
    }


def published(path: str | Path) -> list[Row]:
    """The rows the last good build put on the site, or none if there aren't any.

    Never raises, the same rule `mca.load` keeps: no snapshot yet, a version this
    code doesn't know, a truncated file — all of it is the same absence, and the
    absence must cost the build nothing. A corrupt published file that could
    fail a run would be a corrupt published file that blocks its own replacement.
    """
    try:
        found = json.loads(Path(path).read_text())["companies"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return []
    return [row for row in found if isinstance(row, dict)] if isinstance(found, list) else []


def carry_salary(rows: list[Row], path: str | Path) -> int:
    """Keep a benchmark the last build published where this one found none, and
    say how many were carried (T6.4).

    Measured (FINDINGS, two runs three hours apart): 11 figures lost and 11
    gained between runs, all of it AmbitionBox's rolling request window rather
    than companies changing what they pay. Without this the site oscillates
    between 82 and 71 salaries for no real-world reason, and a throttled night
    publishes a coverage regression — the enrichment overwriting a real figure
    with `null` is a failed fetch deleting good published data.

    This is NOT the staleness T6.3 refused. A republished board row would carry
    no date but the snapshot's, so it would claim to be today; a benchmark states
    its own `observed` date beside the figure, which is why T4.2 made that field
    mandatory. A carried figure makes no claim about tonight.

    ponytail: carried indefinitely, so a company AmbitionBox drops keeps its last
    figure and the `observed` date ages in plain sight. Ceiling: a page that goes
    away for good. Upgrade path: expire past some age, once anything here has an
    age worth expiring — the oldest figure measured is nine months.
    """
    known = {
        row["name"]: row["salary"]
        # A figure that no longer conforms is not carried: on a schema bump it
        # would fail the write, and a build that cannot publish because of what
        # it read from its own last output has no way out.
        for row in published(path)
        if row.get("salary") and not salary_errors(row["salary"])
    }
    carried = [row for row in rows if row["salary"] is None and row["name"] in known]
    for row in carried:
        row["salary"] = known[row["name"]]
    return len(carried)


def _by_board(rows: Iterable[Row]) -> dict[str, list[str]]:
    """The companies each `<ats>/<slug>` board is listed under. More than one is
    the violation `write` refuses."""
    boards: dict[str, list[str]] = {}
    for row in rows:
        # A row that can't say what it is called fails `errors` anyway; this only
        # has to not crash on the way there.
        boards.setdefault(f"{row.get('ats')}/{row.get('slug')}", []).append(str(row.get("name")))
    return boards


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

    Three refusals, one rule (T6.4): a run that could not read something must not
    delete what the last run could. A row that doesn't conform, a footer that
    doesn't add up, and a build that lost half the site all leave the previous
    file exactly where it is — and the write itself is atomic, so a run killed at
    the timeout leaves the whole last file rather than half of a new one.
    """
    counted = {field: built[field] for field in INTEGRITY_FIELDS if field in built}
    bad = {row.get("name"): problems for row in rows if (problems := errors(row))}
    if problems := integrity_errors(counted, len(rows)):
        bad["integrity"] = problems
    # One board, one company (T10.1) — enforced here rather than trusted upstream,
    # for the reason every other rule is: two rows reading one board publish its
    # roles twice under two names, and on a static site that outlives the build
    # that made it. `shared_boards` is what prevents it; this is what proves it.
    for board, names in sorted(_by_board(rows).items()):
        if len(names) > 1:
            bad[board] = [f"one board, {len(names)} companies: {names}"]
    if bad:
        raise ValueError(f"schema v{SCHEMA_VERSION} violations, nothing written: {bad}")

    if len(rows) < COLLAPSE * len(last := published(path)):
        raise ValueError(
            f"collapse, nothing written: {len(rows)} companies against the {len(last)} "
            f"published, under the {COLLAPSE:.0%} floor. A provider that stops answering "
            f"does not fail this build — it empties it. Rerun; if the loss is real "
            f"(a smaller corpus, a deliberate change), delete {path} and build again."
        )

    # Written whole or not at all: `write_text` truncates its target the moment it
    # opens it, so a build killed mid-write — `timeout` in the nightly is 90
    # minutes and a real hang would hit it — would leave the site serving half a
    # JSON document. os.replace is atomic within a filesystem.
    out = Path(path)
    tmp = out.with_name(out.name + ".tmp")
    tmp.write_text(
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
    tmp.replace(out)


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

    shared: dict[str, str] = {}

    if smoke := ("--smoke" in argv):
        corpus = corpus[:1]
        slugs = {c["name"]: Slug(ats="greenhouse", slug="smoke", method="smoke") for c in corpus}
        board = greenhouse.parse(SMOKE_BOARD.read_text())
        # Both passes answer with the same fixture, which is what Greenhouse does
        # too: `content=true` is the same board with the prose in it. The fixture
        # carries `content`, so the smoke run proves the openness wiring offline
        # rather than only the shape of the fields.
        probes = {
            "greenhouse": PROBES["greenhouse"]._replace(
                probe=lambda _: board, describe=lambda _: board
            )
        }
        out = SMOKE_OUT
    else:
        # The names that cannot be listed under themselves: the ones whose board
        # already belongs to another corpus company (derived, every run), and the
        # ones a human found belong to an acquirer that is not in the corpus at
        # all (T10.1). The human's answer is merged second because it is the one
        # nothing here can re-derive. Skipped in smoke, which touches no network:
        # `shared_boards` asks Greenhouse whose board a shared slug is.
        fixed = corrections.load().boards
        corrections.check([c["name"] for c in corpus], fixed, "board")
        shared = shared_boards(slugs) | fixed

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

    rows, outcomes = build(corpus, slugs, probes, shared)
    # Enrichment, after the spine and outside it: it runs on the listed rows
    # only, it cannot change who is listed, and every failure inside it is an
    # absent field rather than a failed build. `salary` is skipped in smoke for
    # the same reason the probes are — the smoke path touches no network. The
    # MCA match reads a local file, so it runs there too and init.sh proves the
    # whole enrichment offline rather than only the report line.
    #
    # Both enrichments are India's and stay India's (SPEC v2): an AmbitionBox
    # figure is an India CTC, and the MCA register slice is India subsidiaries of
    # foreign parents. A Berlin-only company is not a company they know nothing
    # about — it is a company they are not about, and rendering "average India
    # CTC" on its row would be this site inventing a fact. So they run on the rows
    # with an India role, and the rest carry the absence the schema already allows.
    local = [row for row in rows if "India" in row["countries"]]
    carried = 0
    if not smoke:
        salary.attach(local)
        # Before the write, off the file the write is about to replace.
        carried = carry_salary(local, out)
    held = mca.attach(local)
    # The UK register, on the rows with a UK role, for the same reason: Companies
    # House knows every UK company and nobody else, so a badge on a Tokyo-only
    # row would be this site inventing a fact. It reads a local file too, so it
    # runs in smoke as well and init.sh proves the whole enrichment offline.
    british = [row for row in rows if "United Kingdom" in row["countries"]]
    held_uk = uk.attach(british)

    # The report comes first now: the site's footer counts what this build could
    # not check (T5.3), and those numbers are the report's, copied rather than
    # counted twice.
    built = report([c["name"] for c in corpus], outcomes)
    # Read off the file the write is about to replace, so it is the set the site
    # is serving right now rather than the set some earlier run listed.
    left = departures(published(out), built["companies"])
    write(out, rows, built)

    # Why the listed set is smaller than the one on the site, name by name
    # (T10.4). The outcome counts explain a company that stopped hiring; only
    # this explains one the sources stopped carrying, because a name that left
    # the corpus is in no outcome at all.
    built["departed"] = left
    built["websites"] = website_counts(corpus, outcomes)
    # Named, not just counted (T10.1): "10 companies read somebody else's board"
    # is a number nobody can check, and the pair it collapsed is the whole claim.
    built["shared_boards"] = shared
    # Per-country listed counts (T8.4), for the site's country tabs to agree with.
    # In the report rather than in companies.json because it is a fact about the
    # build, like every other count here — the site can already count the rows it
    # was given.
    built["countries"] = country_counts(rows)
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
    # Off the disk for the same reason, and for one more: Companies House has no
    # bulk endpoint, so a nightly reaching for it would be 220 searches and 300
    # profile calls against a 600-per-five-minutes limit, every night, to learn
    # what changed for almost nobody. `src/uk.py` refreshes the cache by hand.
    built["uk"] = {
        **uk.counts(),
        "matched": sum(1 for row in rows if row["uk"]),
        "held": held_uk,
    }
    if not smoke:
        write_report("data/build-report.json", built)

    print(f"{out}: {len(rows)} listed of {built['corpus_size']} in corpus")
    for outcome, count in sorted(built["counts"].items()):
        if count:
            print(f"  {count:4d}  {outcome}")
    for label, count in built["websites"].items():
        print(f"  {count:4d}  {label}")
    collapsed = ", ".join(f"{name} -> {owner}" for name, owner in sorted(shared.items()))
    print(f"  {len(shared):4d}  names reading another company's board [{collapsed}]")
    gone = ", ".join(f"{name} -> {why}" for name, why in sorted(left.items()))
    print(f"  {len(left):4d}  listed by the last build and not by this one [{gone}]")
    # Only the countries with something in them, the same rule the outcome counts
    # above print by. The zeros are in the report, where the site reads them.
    for country, count in built["countries"].items():
        if count:
            print(f"  {count:4d}  listed with a role in {country}")
    posted = sum(len(row["roles"]) for row in rows)
    for field in ("visa", "hire_from_abroad"):
        said = sum(1 for row in rows for role in row["roles"] if role[field] != "unknown")
        print(f"  {said:4d}  of {posted} roles state {field}")
    # T9.2 measured 99.6% on the whole corpus. Printed every run because the one
    # way this quietly dies is Greenhouse's second pass failing wholesale — the
    # department rides with the descriptions, so this number falls with them.
    filed = sum(1 for row in rows for role in row["roles"] if role["department"])
    print(f"  {filed:4d}  of {posted} roles state a department on their board")
    print(f"  {built['mca']['records']:4d}  MCA foreign subsidiaries cached "
          f"(pulled {built['mca']['pulled'] or 'never'})")
    print(f"  {built['mca']['matched']:4d}  matched to a CIN, "
          f"{len(built['mca']['held'])} held for review")
    print(f"  {built['uk']['names']:4d}  UK names looked up on Companies House "
          f"(pulled {built['uk']['pulled'] or 'never'})")
    print(f"  {built['uk']['stated']:4d}  state their own company number, "
          f"{built['uk']['matched']} badged, {len(built['uk']['held'])} held for review")
    print(f"  {sum(1 for row in rows if row['salary']):4d}  salary benchmarks "
          f"({carried} carried from the last build)")


if __name__ == "__main__":
    main(sys.argv[1:])
