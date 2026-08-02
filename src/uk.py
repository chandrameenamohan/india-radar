"""Companies House registration badge — T9.1 (SPEC feature 9, UK).

The UK analogue of `src/mca.py`, and deliberately its sibling rather than its
copy: the doctrine is the same and the source is not.

**Where it differs from MCA.** MCA's usable slice is 24,102 rows and downloads
whole, so the snapshot is the universe and the join runs against all of it.
Companies House has ~5.6M companies and no bulk API — only a search endpoint —
so the snapshot is corpus-shaped: one search per listed UK name, the candidates
that search returned, cached. That difference is why `pull` takes the corpus as
an argument and MCA's does not.

**Search ranking is not evidence, and this is measured.** `q=monzo` answers, in
order: `BRAMAND LTD` (dissolved), `CAPIWISE LTD`, `12808379 LTD`, and only then
`MONZO BANK LIMITED`. Taking the top hit would have published a dissolved
sheep-farm-registered shell as Monzo's registration. Worse, BRAMAND ranks first
because it was ONCE CALLED `MONZO LTD` — an *exact* name match on a former name.
So former names are a trap rather than the recall win they look like, and this
module matches on the name the register holds today, never on a previous one.

**Two of T4.4's rules carry over unchanged**: the register may JOIN a company's
words but never SPLIT one, and a registered name that says MORE than the
company's own plus a legal form is held for a human rather than published.

**And then the measurement broke T4.4's third rule, which is why this module
does not publish a name match at all.** MCA's `exact` tier — the register saying
the company's name and a legal form and nothing else — is publishable in India
because the slice is 24,102 foreign subsidiaries and a collision inside it is
rare. Companies House is 5.6M companies, and measured over the 220 listed UK
names the same tier is wrong on real companies:

  `Amplitude` reaches exactly one exact-tier company, `AMPLITUDE LIMITED`.
  Amplitude's actual UK entity is `AMPLITUDE ANALYTICS LTD.` (11291165), which
  the tier below never publishes. One exact candidate, and it is the wrong one.

  `Anima` reaches `ANIMA LIMITED` and two `ANIMA LTD`s. Its own site states
  `12205370` — `CONTINUUM HEALTH LIMITED`, which shares not one word with the
  name the company trades under and has no previous name that does.

A trading name is routinely not the registered name, and the register holds 551
companies with `alloy` in the name. So the badge is earned by a fact the name
cannot fake: **the company's own website states its registered number**, which
UK trading-disclosure law requires it to. `declared` reads it, the register
resolves it, and `disqualified` refuses the ones the live board contradicts.
The name rule stays, and its whole job is now the held list — what a human
should look at, and never what the site publishes.

The nightly never calls this API and never fetches a website. `attach` reads
`data/uk.json` and cannot raise, for the reason `mca.attach` cannot: an
enrichment that can fail a build is not an enrichment.
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections.abc import Iterable, Mapping, MutableMapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from time import sleep
from typing import Any, TypedDict
from urllib.parse import urlencode

from src import corrections
from src.net import fetch, get

BASE = "https://api.company-information.service.gov.uk"

#: The public register page for a company number — where the badge links, so a
#: reader can check the claim instead of trusting it. Not the API host: this one
#: is a web page a person can read, and it needs no key.
PUBLIC = "https://find-and-update.company-information.service.gov.uk/company/"

SNAPSHOT = Path("data/uk.json")

#: Who is listed, and where to find them. `companies.json` is the site's own
#: output and says which companies have a UK role; only the corpus states a
#: company's website, and the badge needs both.
LISTED = Path("data/companies.json")
CORPUS = Path("data/corpus.json")

#: The documented limit is 600 requests per five minutes — two a second. Half
#: that, because the pull is run rarely and by hand and there is nothing to buy
#: with the other half: 220 searches and a profile each are four minutes at this
#: pace and two at the ceiling, and the ceiling is where a 429 costs half a
#: minute of backoff to learn nothing.
RATE = 1.0

#: Companies House answers 429 when the window is spent, and the wait is the
#: only thing that clears it. Five tries and a growing wait, `mca.page`'s shape,
#: because the failure is the same shape: an upstream saying "not now".
ATTEMPTS = 5
BACKOFF = 30

#: How many search hits to look at per name. Measured: `q=monzo` reports 39
#: results and puts `MONZO BANK LIMITED` fourth, behind three companies whose
#: current name does not contain the word at all — so the first hit is worth
#: nothing and a page of them is worth something. Twenty is one call, the same
#: as one, and it is the register's own default page size.
HITS = 20

#: How many candidates a held entry shows a human. `why` always states the full
#: count; this is how many are worth printing beside it.
SHOWN = 5


class Registered(TypedDict):
    """One company as the register holds it, trimmed to what a badge can use.

    `sic` and `kind` are here for `disqualified` rather than for the site: SIC
    99999 is a company stating on its own confirmation statement that it does no
    business, which is not the company whose live board we just read.

    What is NOT here, and never will be: officers and persons with significant
    control. Companies House publishes both; they are personal data and they help
    nobody looking for a job, which is T4.4's rule about DINs said again.
    """

    number: str
    name: str
    status: str
    incorporated: str
    locality: str
    postcode: str
    sic: list[str]
    kind: str


class Known(TypedDict):
    """Everything the pull learned about one corpus company.

    `stated` is the number the company published on its own site — the badge —
    and `source` is either the page that stated it or the reason there is none
    (`silent`, `unreachable`, `two numbers`, `no website`). The reason is kept
    rather than dropped because "we looked and the company says nothing" and "we
    could not reach the site" are different facts, and only the first is settled.

    `candidates` is the WHOLE search answer, unfiltered — see `candidates` for
    why the matcher is not applied before the evidence is stored. It is the held
    list's material and never the badge's.
    """

    stated: str
    source: str
    candidates: list[Registered]


class Snapshot(TypedDict):
    """The cache on disk: what the pull learned per corpus name, and the day it
    learned it.

    Keyed by the corpus name because the pull is corpus-shaped — there is no
    downloadable universe here to key by number. `pulled` ships for `mca`'s
    reason: a count with no date is a freshness claim nobody checked.
    """

    pulled: str | None
    companies: dict[str, Known]


def api_key() -> str | None:
    """The Companies House key, from the environment or `.env`, or None.

    None is a real answer: the key refreshes the cache, so a machine without one
    still builds the site off the snapshot in the repo. `pull` is the only caller
    that requires it.
    """
    if key := os.environ.get("UK_COMPANY_HOUSE_KEY"):
        return key.strip()
    env = Path(".env")
    if not env.exists():
        return None
    found = re.search(r"^UK_COMPANY_HOUSE_KEY=(.+)$", env.read_text(), re.M)
    return found.group(1).strip() if found else None


def call(key: str, path: str, attempts: int = ATTEMPTS, **params: Any) -> dict[str, Any] | None:
    """One authenticated GET, or None having spent every retry.

    None is "we do not know", never "there is no such company": the caller is
    deciding whether to publish a company number, and a throttled call that read
    as an empty register would quietly unbadge companies whose registration is
    fine. 404 is the one status that means an answer, and it means "no", so it
    comes back as an empty dict rather than None.

    The key is HTTP Basic's *username* with an empty password, which is Companies
    House's own spelling of an API key and the reason `net.get` learned `auth`.
    """
    url = f"{BASE}{path}" + (("?" + urlencode(params)) if params else "")
    for attempt in range(1, attempts + 1):
        sleep(RATE)
        status, body = get(url, timeout=45, auth=f"{key}:")
        if status == 404:
            return {}
        if status == 200:
            try:
                return dict(json.loads(body))
            except (json.JSONDecodeError, TypeError, ValueError):
                pass  # A half-received page is transient the way a 429 is.
        if attempt < attempts:
            sleep(BACKOFF * attempt)
    return None


def search(key: str, name: str, attempts: int = ATTEMPTS) -> list[dict[str, Any]] | None:
    """The register's search hits for a name, best-ranked first — and the ranking
    is not to be believed. See the module docstring: `monzo` ranks a dissolved
    shell above Monzo.

    None where the call never answered, which is NOT the same as a name the
    register has never heard of. `pull` must not cache the two alike.
    """
    found = call(key, "/search/companies", attempts, q=name, items_per_page=HITS)
    if found is None:
        return None
    return [item for item in (found.get("items") or []) if isinstance(item, dict)]


def profile(key: str, number: str, attempts: int = ATTEMPTS) -> Registered | None:
    """One company's own record, or None if the register would not say.

    The search hit already carries a name, a number, a status and a date. This
    call buys what search does not return — the SIC codes, the company type and
    the registered office split into fields — and it is spent on exactly one
    company per name: the one the company itself stated.
    """
    found = call(key, f"/company/{number}", attempts)
    if not found:
        return None
    where = found.get("registered_office_address") or {}
    kept = Registered(
        number=str(found.get("company_number") or "").strip(),
        name=str(found.get("company_name") or "").strip(),
        status=str(found.get("company_status") or "").strip(),
        incorporated=str(found.get("date_of_creation") or "").strip(),
        locality=str(where.get("locality") or "").strip(),
        postcode=str(where.get("postal_code") or "").strip(),
        sic=[str(code) for code in (found.get("sic_codes") or [])],
        kind=str(found.get("type") or "").strip(),
    )
    # A record with no number or no name cannot be shown or checked, and a badge
    # is both. Dropped here rather than cached with a hole in it (`mca.record`).
    return kept if kept["number"] and kept["name"] else None


# --- the name rule ------------------------------------------------------------

#: The words a UK registered name ends with to state what kind of company it is.
#: Dropped from the tail before matching: no source outside the register says
#: them, so `MONZO BANK LIMITED` and `Monzo Bank` are one name.
#:
#: Deliberately short. `COMPANY`, `PUBLIC`, `PARTNERSHIP` and `LIABILITY` are
#: NOT here even though they spell out longer legal forms, because stripping a
#: word makes the asked name reach MORE registered names, and a company really
#: called `<something> Company` would then reach `<something> Company Limited`
#: and `<something> Limited` alike. A legal form spelled out in full costs a
#: held match, which is the cheap side of this trade.
LEGAL_FORM = frozenset({"limited", "ltd", "plc", "llp", "lp", "cic", "cio", "unlimited"})

#: What a registered name may say AFTER the company's own name and still be the
#: same company. Every Companies House registration is a UK registration, so
#: these distinguish nobody from anybody — `DEEPGRAM UK LTD` is Deepgram.
#:
#: Spelled as whole suffixes rather than a set of ignorable words, because
#: membership would also swallow `<name> UNITED` — a different company with a
#: word that happens to be in the phrase.
COUNTRY: tuple[tuple[str, ...], ...] = ((), ("uk",), ("gb",), ("united", "kingdom"))

#: What a match is worth, and NEITHER name tier is worth a badge.
#:
#: `stated` is the company's own site publishing its registered number and the
#: register resolving it. It is the only thing published.
#:
#: `exact` is the register saying the company's name and nothing else that
#: carries information, and `prefix` is the register saying MORE. Both are held.
#: `exact` looks like proof and is not: `AMPLITUDE LIMITED` is the only exact
#: match for `Amplitude`, and Amplitude's UK company is `AMPLITUDE ANALYTICS
#: LTD.`. The tier is kept because it is what a human needs to settle the case,
#: and because a name the register cannot reach at all is a different fact from
#: one it reaches twelve ways.
STATED, EXACT, PREFIX = "stated", "exact", "prefix"

_WORD = re.compile(r"[^a-z0-9]+")


def words(name: str) -> list[str]:
    """A company name as lowercase alphanumeric words, its legal form dropped."""
    found = [word for word in _WORD.split(name.casefold()) if word]
    while found and found[-1] in LEGAL_FORM:
        found.pop()
    return found


def opens_with(asked: Sequence[str], registered: Sequence[str]) -> tuple[str, ...] | None:
    """What the registered name says AFTER the asked name, or None if it does not
    open with it. An empty tuple means it said exactly the asked name.

    The whole difference between a match and a wrong company number is that this
    only ever cuts BETWEEN the registered name's words: `CURSORIAL` does not open
    with `Cursor`, and `HIGH TOUCH` is two words where `Hightouch` is one. Joining
    is allowed in the other direction — the register writes `AMBIENTAI` for
    `Ambient.ai` — so the asked words are compared run together.
    """
    if not asked or not registered:
        return None
    wanted, key = "".join(asked), ""
    for i, word in enumerate(registered):
        key += word
        if key == wanted:
            return tuple(registered[i + 1:])
        if len(key) > len(wanted):
            break
    return None


def find(name: str, found: Iterable[Registered]) -> tuple[str, list[Registered]]:
    """The best tier of registered companies this name could be, and which tier —
    or `("", [])` where none of them is plausibly it.

    Several companies can share a tier and that is not a match: `Monzo` reaches
    `MONZO BANK LIMITED` and `MONZO BANK HOLDING GROUP LIMITED`, and answering
    "one of these" is the caller's to refuse (`attach`).
    """
    asked = words(name)
    if not asked:
        return "", []
    plausible = [
        (rest, company)
        for company in found
        if (rest := opens_with(asked, words(company["name"]))) is not None
    ]
    if exact := [company for rest, company in plausible if rest in COUNTRY]:
        return EXACT, exact
    return (PREFIX, [company for _, company in plausible]) if plausible else ("", [])


def hit(item: Mapping[str, Any]) -> Registered:
    """A search result read as a register record, with the two fields only the
    profile call carries left empty.

    Search states a name, a number, a status and an incorporation date, and its
    address arrives as one unsplit `address_snippet` — so `locality` and
    `postcode` are absent here rather than guessed out of a comma-separated
    string, and `sic` and `kind` are simply not in the payload.
    """
    return Registered(
        number=str(item.get("company_number") or "").strip(),
        name=str(item.get("title") or "").strip(),
        status=str(item.get("company_status") or "").strip(),
        incorporated=str(item.get("date_of_creation") or "").strip(),
        locality="",
        postcode="",
        sic=[],
        kind="",
    )


def candidates(hits: Iterable[Mapping[str, Any]]) -> list[Registered]:
    """The whole search answer, trimmed to what the register said about each hit.

    Deliberately UNFILTERED by the name rule, though `find` will filter it a
    moment later. The snapshot is the pull's evidence, and evidence that has
    already had the matcher applied to it cannot be used to check the matcher —
    the names the rule REFUSES (`ALLOYED LIMITED` for `Alloy`, `STRIPES ACADEMY`
    for `Stripe`) are exactly the ones a false-positive fixture is made of, and
    a snapshot that dropped them would let the fixture drift from the register
    with nothing to catch it.

    No profile call is spent here, and that is a decision the measurement made:
    a corpus name that is also an English word reaches twenty of twenty search
    hits — `Alloy`, and the register holds 551 companies carrying that word — so
    profiling them all would be thousands of calls against a 600-per-five-minutes
    limit for companies that can only ever be held. The one company that gets
    profiled is the one the company itself stated, because that is the one that
    can become a badge.
    """
    # Deduped by number because search repeats itself: `SumUp` comes back with
    # `SUMUP LIMITED` twice and `Tide` with `TIDE LTD` twice, and a held list
    # saying "three companies at this tier" when the register holds two is a work
    # item that argues with itself.
    found = {record["number"]: record for item in hits if (record := hit(item))["number"]}
    return list(found.values())


# --- corroboration: what the company says about itself ------------------------

#: Where a UK company states its own registered number. The Companies (Trading
#: Disclosures) Regulations 2015 require every UK company to state it on its
#: websites; they do not say where.
#:
#: MEASURED over twenty candidate paths on all 220 listed UK names: 22 companies
#: state a number, and these four reach every one of them — the home page 13,
#: `/privacy` five more, `/privacy-policy` three more, `/terms` the last one
#: (Trigger.dev). The sixteen paths that are not here — `/imprint`,
#: `/terms-of-service`, `/cookie-policy`, `/legal`, `/contact` and the rest —
#: each found only companies these four already had, so they are 3,500 fetches
#: for nothing.
LEGAL_PAGES = ("", "/privacy", "/privacy-policy", "/terms")

#: A company number as a company writes it on its own site: eight digits, or the
#: two-letter jurisdiction prefix and six. EXACTLY eight characters, and that is
#: measured rather than tidy — an earlier version also took seven digits and
#: padded the leading zero, on the theory that sites drop it. What it actually
#: found was `Capi Money Inc., a company incorporated in Delaware with
#: registration number 7262022`: a foreign register's number, padded into
#: `07262022`, which is a real and unrelated dissolved London company. A rule
#: that invents a digit invents a company.
#:
#: The letter prefix excludes `Z`, and that is measured too. `ZA283379`,
#: `ZA797592`, `ZB547039` and `ZA165305` turned up beside four companies' real
#: numbers on the same privacy pages: they are ICO **data-protection**
#: registrations, which are the same shape and a different register. Companies
#: House issues no `Z` prefix, and without this four companies that state
#: exactly one company number appear to state two and are held for nothing.
_NUMBER = re.compile(r"(?<![\w-])(\d{8}|[A-Y][A-Z]\d{6})(?![\w-])")

#: The words that have to come BEFORE the digits for them to be a company number
#: rather than a date, a price or an asset hash. Without this, an eight-digit
#: regex over a marketing page matches roughly anything: the context is what makes
#: the number a statement instead of a coincidence.
_SAYS = re.compile(r"regist|company (?:no|number)|incorporat|companies house", re.I)

_MARKUP = re.compile(r"<(script|style)[^>]*>.*?</\1>|<[^>]+>", re.S | re.I)


def numbers(html: str) -> set[str]:
    """Every company number this page STATES, as opposed to merely contains.

    The context rule is the whole function. `Registered in England and Wales
    No. 09446231` is a statement; `?v=20240115` is eight digits on the same page,
    and a matcher without the words in front of it cannot tell them apart.
    """
    text = _MARKUP.sub(" ", html)
    return {
        match.group(1)
        for match in _NUMBER.finditer(text)
        if _SAYS.search(text[max(0, match.start() - 160):match.start()])
    }


def declared(website: str, pages: Sequence[str] = LEGAL_PAGES) -> tuple[set[str], str]:
    """The company numbers a company's own site states, and the page that stated
    them — or an empty set and why it is empty.

    This is the corroboration a name cannot fake, and the reason it is worth the
    fetches: the register can be searched by anybody for any string, but only the
    company can put its own registration on its own domain. `ANIMA LIMITED` is an
    exact name match for `Anima`; animahealth.com saying `12205370` is Anima
    saying its registration is `CONTINUUM HEALTH LIMITED`, which no reading of
    the two names could have reached.
    """
    site, reached, found, where = website.rstrip("/"), False, set(), ""
    for page in pages:
        got = fetch(site + page)
        if got is None:
            continue
        reached = True
        # Every page is read, not just the first that answers. A company that
        # states one number on its home page and its parent's on its privacy
        # page has stated two, and stopping early would turn that into a
        # confident wrong answer — which is the whole failure this module is
        # built around.
        if said := numbers(got):
            where = where or site + (page or "/")
            found |= said
    return found, where or ("silent" if reached else "unreachable")


# --- corroboration: what the register says about itself -----------------------

#: Companies House's words for a company that is no longer on the register. A
#: listed company is one whose live job board we read minutes ago, so a
#: registration in any of these states is somebody else's company — which is
#: exactly what `BRAMAND LTD` (dissolved, formerly `MONZO LTD`) is, and what the
#: `removed` Dubai overseas entity called `CARIBOU LIMITED` is.
#:
#: Measured over the 220 listed UK names, the register answered with 156
#: dissolved companies, one removed, two converted-closed and one closed. What
#: is NOT here is as deliberate: `liquidation`, `administration` and
#: `voluntary-arrangement` are companies that still exist and can still be
#: hiring, and the badge states them verbatim rather than hiding them.
DEAD = frozenset({"dissolved", "removed", "closed", "converted-closed"})

#: SIC 99999 is "dormant company" and 74990 is "non-trading company". Both are
#: the register's own statement that this entity does no business, said by the
#: company on its own confirmation statement — which cannot be true of a company
#: running the job board we just read. `BRAMAND LTD` files 99999.
DORMANT = frozenset({"99999", "74990"})

#: The company types that can be one of these companies at all. Every row on this
#: site qualified by RAISING A PRICED EQUITY ROUND (`corpus._qualified_by`), and
#: a body with no share capital has no equity to price — so the register's own
#: `type` field, checked against the corpus's own admission rule, is a fact from
#: two sources that a page cannot fake.
#:
#: This is not theory. It is the rule that caught the one false positive the live
#: pull produced: veriff.com's privacy notice says "Veriff is jointly a Data
#: Controller with Cifas, a company registered in England and Wales under company
#: number 02584687" — and 02584687 is CIFAS, the UK fraud-prevention service, a
#: `private-limited-guarant-nsc-limited-exemption`. The number is stated on
#: Veriff's own page, in a disclosure context, and belongs to somebody else.
#:
#: An allow-list rather than a block-list, because the failure of a list that is
#: short by one entry has to be a held match and never a published one. Measured
#: across the 460 candidate registrations the searches returned, the types it
#: turns away are `registered-overseas-entity` (a land-registry entry, not a
#: company), `uk-establishment` (a branch), `oversea-company`, both guarantee
#: types, and `charitable-incorporated-organisation` — which is what the register
#: answers for `q=intercom`.
WITH_SHARE_CAPITAL = frozenset({
    "ltd", "plc", "llp", "private-unlimited", "private-unlimited-nsc",
    "private-limited-shares-section-30-exemption", "old-public-company",
})

_ISO = re.compile(r"\d{4}-\d{2}-\d{2}")


def disqualified(company: Registered, funded: str | None = None) -> str:
    """Why this registration cannot be the company we listed, or "" if nothing
    says it isn't.

    Every rule here is a REJECTION, never a score. That direction is the whole
    design: a corroboration that could raise a weak match into a published one
    would be a second way to be wrong, whereas a rule that can only subtract
    leaves the evidence carrying exactly what it carried before.

    The first three rules are facts the register states about itself, checked
    against facts from sources it has never seen — the live board we read, and
    the funding date the corpus got from EDGAR, Forbes or FinSMEs. The last is
    the register saying too little to render: `build.uk_errors` refuses a badge
    with no status or no incorporation date, and an enrichment that hands the
    write something it will refuse is an enrichment that fails the build.
    """
    if company["status"] in DEAD:
        return f"{company['status']}, and we read this company's live job board"
    if not (company["status"] and _ISO.fullmatch(company["incorporated"])):
        return (
            f"the register states status {company['status']!r} and incorporation "
            f"{company['incorporated']!r} — not enough to render"
        )
    if company["kind"] not in WITH_SHARE_CAPITAL:
        return (
            f"a {company['kind'] or 'company of no stated type'}, which has no equity"
            " to have raised a round with"
        )
    if set(company["sic"]) & DORMANT:
        return f"filed as dormant (SIC {'/'.join(sorted(set(company['sic']) & DORMANT))})"
    # A company cannot raise a round before it is incorporated. The dates come
    # from different worlds — the register's own filing, and a funding
    # announcement — so an inversion is two different companies, not a late
    # filing. Compared as ISO strings, which is what both of them are.
    if funded and company["incorporated"] and company["incorporated"] > funded:
        return (
            f"incorporated {company['incorporated']}, after the round stated {funded}"
        )
    return ""


# --- the snapshot -------------------------------------------------------------


#: How many company websites to read at once. Concurrent because this half of
#: the pull touches 220 hosts and not one of them is Companies House — the rate
#: limit this module respects is the register's, and a company's own site is not
#: it. `websites.py` fetches the same way for the same reason. Measured: ten of
#: the 220 are unreachable, and four paths at curl's timeout is eight sequential
#: minutes of waiting for nothing.
WORKERS = 8


def stated(names: Mapping[str, str | None]) -> dict[str, tuple[set[str], str]]:
    """What each company states on its own site, read in parallel."""
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        answers = pool.map(
            lambda site: declared(site) if site else (set(), "no website"), names.values()
        )
        return dict(zip(names, answers, strict=True))


def look_up(
    key: str, name: str, said: tuple[set[str], str], attempts: int = ATTEMPTS
) -> Known | None:
    """Everything the pull knows about one company, or None if the register would
    not answer at all.

    Two questions, in the order that matters: what does the company say its
    number is, and what does the register offer for its name. The first is the
    badge and the second is the held list, and they are gathered together so the
    snapshot on disk answers both without a second pull.

    A site stating TWO numbers is not a statement — a group's legal page can name
    a parent and a subsidiary — so it is recorded as such and settles nothing.
    """
    hits = search(key, name, attempts)
    if hits is None:
        return None
    numbers, where = said
    known = Known(stated="", source=where, candidates=candidates(hits))
    if len(numbers) > 1:
        known["source"] = f"two numbers stated: {', '.join(sorted(numbers))}"
    elif numbers:
        number = next(iter(numbers))
        # The register has the last word on a number the company published: a
        # typo'd digit is a different company, and an unresolvable one is not a
        # company at all. `profile` is also where SIC and the registered office
        # come from, which is what `disqualified` and the badge's city need.
        if found := profile(key, number, attempts):
            known["stated"] = found["number"]
            known["candidates"] = [
                found,
                *(c for c in known["candidates"] if c["number"] != found["number"]),
            ]
        else:
            known["source"] = f"stated {number}, which the register does not hold"
    return known


def pull(
    key: str, names: Mapping[str, str | None], attempts: int = ATTEMPTS
) -> dict[str, Known]:
    """Look up every corpus name: the websites together, the register in order.

    A name whose search call never answered is LEFT OUT of the result rather than
    stored empty, so a throttled pull cannot be cached as "the register knows
    nobody by that name". `write` refuses a pull that lost too many of them.
    """
    said = stated(names)
    found: dict[str, Known] = {}
    for name in names:
        if (known := look_up(key, name, said[name], attempts)) is not None:
            found[name] = known
    return found


def write(
    path: str | Path,
    companies: Mapping[str, Known],
    asked: int | None = None,
    pulled: str | None = None,
) -> None:
    """Replace the snapshot, or ValueError having written nothing.

    `asked` is how many names the pull set out to look up. A pull that came back
    with a fraction of them met a rate limit rather than a register that forgot
    the corpus, and caching that would silently unbadge every company it lost —
    `mca.pull`'s refusal, in the place this source can lose rows.
    """
    if asked and len(companies) < asked * 0.9:
        raise ValueError(
            f"UK pull is short: {len(companies)} of {asked} names answered"
            " — refusing to cache it"
        )
    payload = Snapshot(pulled=pulled or date.today().isoformat(), companies=dict(companies))
    Path(path).write_text(json.dumps(payload, indent=1) + "\n")


def load(path: str | Path = SNAPSHOT) -> Snapshot:
    """The cached snapshot, or an empty one. Never raises, never fetches.

    Every way this can fail — no snapshot committed, a truncated write, a file
    that isn't the shape it was — is the same absence, and the absence must cost
    the build nothing. There is no code path here that can fail a run.
    """
    try:
        found = json.loads(Path(path).read_text())
        companies = found["companies"]
        pulled = found["pulled"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return Snapshot(pulled=None, companies={})
    if not isinstance(companies, dict) or not (isinstance(pulled, str) or pulled is None):
        return Snapshot(pulled=None, companies={})
    return Snapshot(pulled=pulled, companies=companies)


def counts(path: str | Path = SNAPSHOT) -> dict[str, Any]:
    """What the build report says about Companies House: how many names the cache
    holds an answer for, how many of them stated a number, and when they were
    pulled.

    `stated` is in the report because it is the enrichment's real ceiling — every
    badge comes from a company that published its own number, so this number is
    the most a build can ever badge, and a drop in it is the pull breaking rather
    than the register changing.
    """
    found = load(path)
    return {
        "names": len(found["companies"]),
        "stated": sum(1 for known in found["companies"].values() if known.get("stated")),
        "pulled": found["pulled"],
    }


# --- the badge ----------------------------------------------------------------


class Registration(TypedDict):
    """What the site shows about a matched company, and how sure the match is.

    `url` ships resolved rather than built in the page, because the badge's whole
    claim is that a reader can check it: the link is part of the fact, not part
    of the styling. `status` is the register's own word, never normalised — a
    company in administration must not render as one that is fine.
    """

    number: str
    name: str
    status: str
    incorporated: str
    city: str
    url: str
    confidence: str


class Held(TypedDict):
    """A match that is plausible and not certain, kept for a human.

    These are NOT published. A wrong company number on a public site is a claim
    about somebody else's company, so everything below the threshold lands in the
    build report where a person can settle it, rather than on the site where
    nobody could tell it was ever in doubt.

    `why` says which rule held it — a tier that says more than the company's
    name, several companies at the same tier, or a corroboration that refused it.
    A work list nobody can act on is a work list nobody will.

    `candidates` is TRIMMED to `SHOWN`, and `why` carries the full count. The
    register answers `q=alloy` with nineteen companies whose names open with the
    word, and a report that printed all of them for all 186 held names would be
    a megabyte of the same non-answer — which is the same "a count nobody can
    check is not a claim" rule read the other way round.
    """

    name: str
    confidence: str
    why: str
    candidates: list[Registered]


def badge(company: Registered) -> Registration:
    """One proven registration, as the site renders it."""
    return Registration(
        number=company["number"],
        name=company["name"],
        status=company["status"],
        incorporated=company["incorporated"],
        city=company["locality"].title(),
        url=PUBLIC + company["number"],
        confidence=STATED,
    )


def attach(
    rows: Iterable[MutableMapping[str, Any]], snapshot: Snapshot | None = None
) -> list[Held]:
    """Fill in each row's `uk`, in place, and return everything held for review.

    Rows arrive from `build.build` with `uk: None` already set, so a register
    that was never pulled — or a snapshot that got truncated — leaves a build that
    is complete and honest rather than one that failed. Nothing here reaches the
    network or a website; `load` is a file read that cannot raise.

    A company is published only where IT stated its own number, the register
    resolved that number, and nothing about the resolved company contradicts the
    live board that listed the row. Every name match, at either tier, is held —
    which is the finding in the module docstring made structural rather than
    remembered.
    """
    found = (snapshot if snapshot is not None else load())["companies"]
    held: list[Held] = []
    for row in rows:
        known = found.get(row["name"])
        if not known:
            continue
        confidence, matches = find(row["name"], known.get("candidates") or [])
        proven = [c for c in (known.get("candidates") or []) if c["number"] == known.get("stated")]
        why = disqualified(proven[0], row.get("date")) if proven else ""
        if proven and not why:
            row["uk"] = badge(proven[0])
        elif proven:
            held.append(Held(name=row["name"], confidence=STATED, why=why, candidates=proven))
        elif matches:
            held.append(
                Held(
                    name=row["name"],
                    confidence=confidence,
                    why=f"{known.get('source') or 'silent'}; "
                        + (f"{len(matches)} companies reach the {confidence} tier"
                           if len(matches) > 1 else f"one {confidence}-tier name match"),
                    candidates=matches[:SHOWN],
                )
            )
    return held


def main(argv: list[str]) -> int:
    """Refresh the snapshot. Run rarely and by hand — never from the nightly
    build, which reads what this leaves behind.
    """
    key = api_key()
    if not key:
        print("no UK_COMPANY_HOUSE_KEY (environment or .env) — snapshot unchanged", file=sys.stderr)
        return 1

    out = Path(argv[0]) if argv else SNAPSHOT
    listed = json.loads(LISTED.read_text())["companies"]
    # The corpus is where a company's own address lives; `companies.json` says
    # who is listed. The badge needs both, because the number comes off the
    # company's site and the site comes off the corpus.
    #
    # T10.1's corrections beat the corpus, and here they are load-bearing rather
    # than tidy: Cresta's corpus website is `analyticsinsight.net`, a trade
    # publication that wrote about them, and Alloy's is `alloy.app` rather than
    # `alloy.com`. Reading a registered number off somebody else's site is
    # exactly the wrong company this module exists to refuse.
    sites = {c["name"]: c.get("website") for c in json.loads(CORPUS.read_text())["companies"]}
    sites |= corrections.load().websites
    names = {
        row["name"]: sites.get(row["name"])
        for row in listed
        if "United Kingdom" in row["countries"]
    }

    companies = pull(key, names)
    try:
        write(out, companies, asked=len(names))
    except ValueError as refused:
        # The old snapshot outlives a bad pull, for `mca.main`'s reason:
        # stale-but-whole beats fresh-but-partial.
        print(f"{refused} — {out} unchanged", file=sys.stderr)
        return 1

    stated = sum(1 for known in companies.values() if known["stated"])
    named = sum(1 for name, known in companies.items() if find(name, known["candidates"])[0])
    print(f"{out}: {len(companies)} of {len(names)} UK names answered, "
          f"{stated} state their own number, {named} reach a name on the register")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
