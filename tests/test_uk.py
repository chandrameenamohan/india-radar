"""T9.1 — the Companies House badge, and the reason it is not a name match.

Three rules carry this module. The pull either produces an answer for a name or
leaves the name out, because a throttled call cached as "the register knows
nobody by that name" silently unbadges a company whose registration is fine. The
build's side of it cannot fail at all: no snapshot, a truncated one, or a file
that isn't the shape it was are one absence, and the site ships regardless. And
the badge publishes only what the company itself stated, because the measurement
below says an exact name match on this register is not evidence.
"""
import json
from datetime import date

import pytest

from src import build, uk

#: One live search hit, spelled the way `/search/companies` spells it. This is
#: the one that made the module: `q=monzo` ranks `BRAMAND LTD` FIRST because it
#: was once called `MONZO LTD`, and it is a dissolved shell at a Gwynedd address.
HIT = {
    "title": "BRAMAND LTD",
    "company_number": "15296432",
    "company_status": "dissolved",
    "date_of_creation": "2023-11-20",
    "address_snippet": "Llwyn Helyg, Llangybi, Pwllheli, Wales, LL53 6TB",
}

#: One live profile, as `/company/{number}` returns it — Monzo's, the company
#: that search put fourth.
PROFILE = {
    "company_name": "MONZO BANK LIMITED",
    "company_number": "09446231",
    "company_status": "active",
    "date_of_creation": "2015-02-18",
    "jurisdiction": "england-wales",
    "type": "ltd",
    "sic_codes": ["64191", "64999"],
    "registered_office_address": {
        "address_line_1": "Broadwalk House",
        "address_line_2": "5 Appold Street",
        "locality": "London",
        "postal_code": "EC2A 2AG",
        "country": "England",
    },
    "previous_company_names": [{"name": "FOCUS FS LIMITED", "ceased_on": "2016-10-21"}],
    "has_insolvency_history": False,
}


def registered(number, name, status="active", incorporated="2015-02-18", sic=("62012",),
               kind="ltd", locality="London"):
    """One register record, the shape the snapshot holds."""
    return uk.Registered(
        number=number, name=name, status=status, incorporated=incorporated,
        locality=locality, postcode="EC2A 2AG", sic=list(sic), kind=kind,
    )


def snapshot(**companies):
    """A snapshot holding exactly these companies, pulled today."""
    return uk.Snapshot(pulled="2026-08-02", companies=dict(companies))


def known(stated="", source="silent", candidates=()):
    return uk.Known(stated=stated, source=source, candidates=list(candidates))


def answering(*pages):
    """A `net.get` stand-in serving the given pages in order, then 429ing."""
    served = iter(pages)

    def get(url, timeout=45, auth=None):
        return next(served, (429, "rate limit exceeded"))

    return get


# --- the hand-labelled set ----------------------------------------------------

#: Twenty hand-labelled pairs: a corpus name, a name Companies House really
#: holds, and what the NAME RULE may conclude from the two. Every registered name
#: below is a live row in `data/uk.json` — pinned by
#: `test_the_labelled_pairs_are_rows_the_register_really_holds`, because a
#: hand-labelled set that drifts from the register is how this check goes green
#: while being wrong about the world.
#:
#: The three labels are the three answers the name rule has. NOTE that `exact`
#: here does NOT mean publishable — see `PUBLISH` below, which is the set that
#: measures false positives. `exact` means only "the register holds this name
#: and a legal form and nothing else", and the measurement is that this is true
#: of the wrong company often enough to be worthless as proof.
NAMES = [
    # EXACT — the register says the company's name and nothing that carries
    # information. `UK` and `(UK)` are the register saying which country's arm
    # this is, and every Companies House registration is a UK one, so they
    # distinguish nobody. Note what is in this tier: `ALLOY LTD` is a 1998
    # Guildford company, `AMPLITUDE LIMITED` a 1994 Devon estate manager,
    # `CURSOR LIMITED` a 2007 Lincoln firm, `STRIPE LTD` a dissolved Peckham
    # one, and `INTERCOM` a charity. Ten `exact` matches and half of them are
    # somebody else — which is the whole reason this tier does not publish.
    ("9fin", "9FIN LIMITED", uk.EXACT),
    ("Amperity", "AMPERITY UK LIMITED", uk.EXACT),
    ("Staffbase", "STAFFBASE UK LTD", uk.EXACT),
    ("Anthropic", "ANTHROPIC LIMITED", uk.EXACT),
    ("Applied Intuition", "APPLIED INTUITION UK LTD.", uk.EXACT),
    ("Alloy", "ALLOY LTD", uk.EXACT),
    ("Amplitude", "AMPLITUDE LIMITED", uk.EXACT),
    ("Cursor", "CURSOR LIMITED", uk.EXACT),
    ("Intercom", "INTERCOM", uk.EXACT),
    ("Stripe", "STRIPE LTD", uk.EXACT),
    ("Torq", "TORQ LIMITED", uk.EXACT),
    # PREFIX — the register says MORE. `MONZO BANK LIMITED` and `AMPLITUDE
    # ANALYTICS LTD.` are the right companies and sit BELOW the tier that holds
    # the wrong ones, which is the clearest statement of what a name is worth.
    ("Monzo", "MONZO BANK LIMITED", uk.PREFIX),
    ("Amplitude", "AMPLITUDE ANALYTICS LTD.", uk.PREFIX),
    ("Alloy", "ALLOY AUTOMATIONS LTD", uk.PREFIX),
    ("Torq", "TORQ TECHNOLOGIES UK LIMITED", uk.PREFIX),
    ("Cursor", "CURSOR SOFTWARE LIMITED", uk.PREFIX),
    # NOTHING — the word boundary. Each of these three came back in the top
    # twenty for `q=monzo` and each continues INSIDE the word, which is the one
    # cut the rule never makes.
    ("Monzo", "MONZOIMPEX LTD", ""),
    ("Monzo", "MONZONITE LIMITED", ""),
    ("Monzo", "MONZOO TRADERS LTD", ""),
    # NOTHING, and RIGHT. These two are the companies the site actually badges —
    # proven by Anima's and Trigger.dev's own websites — and the name rule
    # reaches neither at any tier. There is no string metric that closes this,
    # which is why the badge is not one.
    ("Anima", "CONTINUUM HEALTH LIMITED", ""),
    ("Trigger.dev", "API HERO LTD", ""),
]

#: The set that measures FALSE POSITIVES, which is a different question from the
#: one above: not "what does the name rule say", but "would the site publish a
#: company number that is not this company's".
#:
#: Each row is hand-checked, on 2026-08-02, against the company's own site and
#: the public register:
#:
#:   company     the corpus name
#:   truth       the company number that is really this company's, or None
#:               where no source proves one
#:   stated      what the company's own website states, if anything
#:   candidates  what the register's search offers for the NAME
#:
#: The two shapes that make this set worth having are both in it. `Amplitude`,
#: `Stripe`, `Alloy` and `Tide` are names the register answers with exactly one
#: `exact`-tier company that is SOMEBODY ELSE — the false positives a name-only
#: matcher publishes. `Anima` and `Caribou` are the reverse: the company's real
#: registration shares not one word with the name it trades under, so no string
#: rule could ever reach it and only the company's own statement does.
PUBLISH = [
    (
        "9fin", "10451957",
        ("10451957", "https://9fin.com/"),
        [registered("10451957", "9FIN LIMITED", incorporated="2016-10-28", sic=["63990"])],
    ),
    (
        # Trades as Anima; registered as CONTINUUM HEALTH LIMITED, which shares
        # not one word with it and has no previous name that does. The register
        # separately holds three companies literally called ANIMA and this is
        # none of them. animahealth.com: "Continuum Health Ltd, trading as Anima
        # Health. Registered in England and Wales, company number 12205370."
        "Anima", "12205370",
        ("12205370", "http://www.animahealth.com/"),
        [registered("12205370", "CONTINUUM HEALTH LIMITED", incorporated="2019-09-13",
                    sic=["86101", "86210"]),
         registered("12737409", "ANIMA LIMITED", incorporated="2020-07-13",
                    sic=[], kind="", locality="")],
    ),
    (
        # Trades as Trigger.dev; registered as API HERO LTD. Same shape, and the
        # register's search for `Trigger.dev` reaches it at no tier at all.
        "Trigger.dev", "14441978",
        ("14441978", "https://trigger.dev/terms"),
        [registered("14441978", "API HERO LTD", incorporated="2022-10-25",
                    locality="Altrincham")],
    ),
    (
        # THE FALSE POSITIVE THE LIVE PULL PRODUCED, and the rule that caught it.
        # veriff.com's privacy notice reads "Veriff is jointly a Data Controller
        # with Cifas, a company registered in England and Wales under company
        # number 02584687" — a real number, on the company's own site, in a
        # disclosure context, belonging to the UK fraud-prevention service.
        # Nothing about the NUMBER is wrong; what is wrong is whose it is, and
        # the register says so itself: CIFAS is limited by guarantee and has no
        # share capital, so it cannot be a company that raised a priced round.
        "Veriff", None,
        ("02584687", "https://veriff.com/privacy-policy"),
        [registered("02584687", "CIFAS", incorporated="1991-02-22",
                    sic=["63990", "82990"],
                    kind="private-limited-guarant-nsc-limited-exemption")],
    ),
    (
        # One exact-tier candidate, active, and a Devon estate manager
        # incorporated in 1994. Amplitude's UK company is AMPLITUDE ANALYTICS
        # LTD., which the name rule reads as `prefix`.
        "Amplitude", None, None,
        [registered("02962681", "AMPLITUDE LIMITED", incorporated="1994-08-26",
                    sic=[], kind="", locality="")],
    ),
    (
        # One exact-tier candidate, dissolved, at a Peckham house.
        "Stripe", None, None,
        [registered("09733676", "STRIPE LTD", status="dissolved",
                    incorporated="2015-08-14", sic=[], kind="", locality="")],
    ),
    (
        # 551 companies on the register carry the word `alloy`. One is called
        # exactly that: a Guildford company incorporated in 1998.
        "Alloy", None, None,
        [registered("03567784", "ALLOY LTD", incorporated="1998-05-20",
                    sic=[], kind="", locality="")],
    ),
    (
        # Three dissolved companies reach the exact tier and Tide is none of
        # them — and tide.co states TWO live numbers, so even its own site
        # settles nothing on its own.
        "Tide", None, None,
        [registered("SC753507", "TIDE LTD", status="dissolved",
                    incorporated="2022-12-20", sic=[], kind="", locality=""),
         registered("13447520", "TIDE LIMITED", status="dissolved",
                    incorporated="2021-06-09", sic=[], kind="", locality="")],
    ),
    (
        # The register answers `q=intercom` with a charitable incorporated
        # organisation that states no status and no incorporation date at all.
        "Intercom", None, None,
        [registered("CE010464", "INTERCOM", status="", incorporated="", sic=[],
                    kind="", locality="")],
    ),
    (
        # The search ranking, taken at its word, publishes this: first hit for
        # `q=monzo`, dissolved, and the name it exactly matches is one it dropped
        # in 2024. Monzo's own site is what settles it — and it settles it on the
        # company search ranked FOURTH.
        "Monzo", "09446231",
        ("09446231", "https://monzo.com/"),
        [registered("09446231", "MONZO BANK LIMITED", incorporated="2015-02-18",
                    sic=["64191", "64999"]),
         registered("15296432", "BRAMAND LTD", status="dissolved",
                    incorporated="2023-11-20", sic=[], kind="", locality="")],
    ),
    (
        # The register says nothing at all, which is the commonest answer and is
        # not an error.
        "Nobody At All", None, None, [],
    ),
]


def published(company, stated, candidates, funded=None):
    """What the site would render for one labelled pair — the number, or None."""
    row = {"name": company, "date": funded, "uk": None}
    uk.attach(
        [row],
        snapshot(**{company: known(
            stated=stated[0] if stated else "",
            source=stated[1] if stated else "silent",
            candidates=candidates,
        )}),
    )
    return row["uk"]["number"] if row["uk"] else None


def test_hand_labelled_pairs_zero_false_positives():
    """The check T9.1's DoD names. A wrong company number on a public site is a
    claim about somebody else's company — worse than no badge at all.

    Both directions are asserted: nothing false is published, and the true
    registrations ARE published, because a matcher that publishes nothing has a
    false-positive rate of zero and is not a matcher.
    """
    verdicts = [(c, published(c, stated, candidates)) for c, _, stated, candidates in PUBLISH]

    assert verdicts == [(c, truth) for c, truth, _, _ in PUBLISH]
    assert [v for _, v in verdicts if v] == [
        "10451957", "12205370", "14441978", "09446231"
    ], "the proven registrations stopped being published"

    # The traps must stay IN the fixture, the rule invariant 2 keeps for
    # locations. Each of these is a registered name that reaches a listed
    # company's name at the EXACT tier and belongs to somebody else, so deleting
    # one is how this comes back green with the doctrine gone.
    traps = {c: cs for c, truth, _, cs in PUBLISH if truth is None and cs}
    assert {"Amplitude", "Stripe", "Alloy", "Tide", "Intercom"} <= set(traps)
    for company in ("Amplitude", "Stripe", "Alloy", "Tide", "Intercom"):
        tier, matched = uk.find(company, traps[company])
        assert (tier, bool(matched)) == (uk.EXACT, True), f"{company} left the exact tier"

    # And Veriff is the trap that is not about names at all: a real UK company
    # number, stated on the company's own site, in a disclosure sentence — and
    # it is the fraud-prevention service they share data with.
    assert uk.disqualified(traps["Veriff"][0]).startswith("a private-limited-guarant")

    # And the schema is the second lock: nothing below the publish threshold can
    # reach a row even if the matcher one day hands it over.
    proven = uk.badge(registered("10451957", "9FIN LIMITED"))
    assert not build.uk_errors(proven)
    assert build.uk_errors({**proven, "confidence": uk.EXACT})

    # The third lock, and the one that keeps a bad badge from failing the whole
    # build: anything `disqualified` lets through must be something the write
    # accepts. An enrichment that hands `build.write` a row it refuses is an
    # enrichment that can take a nightly down.
    for _, _, _, candidates in PUBLISH:
        for company in candidates:
            assert uk.disqualified(company) or not build.uk_errors(uk.badge(company)), company


def test_the_labelled_pairs_are_rows_the_register_really_holds():
    """The labels in `NAMES` are claims about Companies House's data, so they are
    pinned to it.

    Without this the fixture is 20 strings somebody typed, and the obvious way to
    make a failing match go green is to edit the string it failed on.
    """
    holds = {
        company["name"]
        for found in uk.load()["companies"].values()
        for company in found["candidates"]
    }
    assert holds, "data/uk.json is missing; the labelled pairs cannot be checked"
    assert [name for _, name, _ in NAMES if name not in holds] == []


def test_the_name_rule_joins_words_but_never_splits_one():
    """The whole difference between a match and a wrong company number.

    The register writes `AMBIENTAI` for `Ambient.ai`, so the asked name's words
    are run together; it never writes one of a company's words as two, so a cut
    inside a registered word is not a match.
    """
    verdicts = [(c, uk.find(c, [registered("00000001", name)])[0]) for c, name, _ in NAMES]

    assert verdicts == [(company, label) for company, _, label in NAMES]

    # The traps must stay in: each opens with a listed company's letters and
    # continues inside the word, so deleting one is how this comes back green
    # with the boundary rule gone.
    assert {"MONZOIMPEX LTD", "MONZONITE LIMITED", "MONZOO TRADERS LTD"} <= {
        name for _, name, label in NAMES if label == ""
    }


def test_a_register_that_says_LESS_than_the_company_is_not_a_match():
    """The direction that cannot be settled from the strings, refused rather than
    judged — `slugs.states_company`'s rule, anchored at the front."""
    assert uk.find("Cohere Health", [registered("00000001", "COHERE LIMITED")]) == ("", [])


# --- the badge, and what is held ----------------------------------------------


def test_below_threshold_held_for_review():
    """A plausible-but-unproven match is published nowhere and reported to a
    human — the third state between "matched" and "no such company"."""
    rows = [{"name": "9fin", "date": None, "uk": None},
            {"name": "Amplitude", "date": None, "uk": None},
            {"name": "Nobody At All", "date": None, "uk": None}]

    held = uk.attach(rows, snapshot(
        **{
            "9fin": known("10451957", "https://9fin.com/",
                          [registered("10451957", "9FIN LIMITED")]),
            "Amplitude": known(candidates=[registered("11291165", "AMPLITUDE LIMITED")]),
            "Nobody At All": known(),
        }
    ))

    assert rows[0]["uk"]["number"] == "10451957"
    assert rows[0]["uk"]["confidence"] == uk.STATED
    assert rows[1]["uk"] is None, "an exact-tier name match reached the site"
    assert rows[2]["uk"] is None
    assert [(h["name"], h["confidence"]) for h in held] == [("Amplitude", uk.EXACT)]
    assert [c["name"] for c in held[0]["candidates"]] == ["AMPLITUDE LIMITED"]
    # The held entry has to say WHY, or it is a work list nobody can act on.
    assert "silent" in held[0]["why"] and "exact" in held[0]["why"]
    # A company the register says nothing about is not held: there is nothing for
    # a human to settle.
    assert "Nobody At All" not in {h["name"] for h in held}


def test_dissolved_status_verbatim():
    """The register's own word for a company's state reaches the site unchanged,
    and a dissolved company never renders a badge at all.

    Both halves matter and they are different rules. `liquidation` and
    `administration` are companies that still exist and can still be hiring, so
    they publish — saying so, in the register's spelling, never softened into a
    word that implies Active. `dissolved` is a company that has ceased to exist,
    which contradicts the live job board that put the row on the site, so it is
    refused: that is `BRAMAND LTD`, the top search hit for `monzo`.
    """
    for status in ("active", "liquidation", "administration", "voluntary-arrangement"):
        row = {"name": "Somebody", "date": None, "uk": None}
        uk.attach([row], snapshot(Somebody=known(
            "10451957", "https://x.test/", [registered("10451957", "SOMEBODY LTD", status)]
        )))
        assert row["uk"]["status"] == status, "the register's word was rewritten"
        assert not build.uk_errors(row["uk"])

    row = {"name": "Monzo", "date": None, "uk": None}
    held = uk.attach([row], snapshot(Monzo=known(
        "15296432", "https://x.test/",
        [registered("15296432", "BRAMAND LTD", status="dissolved")],
    )))
    assert row["uk"] is None
    assert held[0]["why"].startswith("dissolved")
    # And the schema refuses it a second time, whatever the matcher believed —
    # for every one of the four states that mean the company is off the register.
    for status in uk.DEAD:
        gone = uk.badge(registered("15296432", "BRAMAND LTD", status))
        assert build.uk_errors(gone) == [
            f"status {status!r}: this company's live board is what listed it"
        ]


def test_a_dormant_company_is_not_the_one_running_a_job_board():
    """SIC 99999 is the company's own statement, on its own confirmation
    statement, that it does no business — which cannot be true of the company
    whose live board we read minutes ago."""
    assert uk.disqualified(registered("1", "X", sic=["99999"])).startswith("filed as dormant")
    assert uk.disqualified(registered("1", "X", sic=["62012"])) == ""


def test_a_body_with_no_share_capital_never_raised_a_round():
    """The rule that caught the live pull's one false positive.

    Every company on this site is here because it raised a priced equity round
    (`corpus._qualified_by`), and a body limited by guarantee has no equity to
    price. So the register's own `type` field, checked against the corpus's own
    admission rule, refuses `CIFAS` — a real UK company number, stated on
    Veriff's own privacy page, belonging to the fraud-prevention service they
    share data with — and a charity, a branch and an overseas-entity entry with
    it.
    """
    for kind in ("private-limited-guarant-nsc-limited-exemption",
                 "private-limited-guarant-nsc", "charitable-incorporated-organisation",
                 "registered-overseas-entity", "uk-establishment", "oversea-company", ""):
        assert uk.disqualified(registered("1", "X", kind=kind)), kind
    for kind in ("ltd", "plc", "llp"):
        assert uk.disqualified(registered("1", "X", kind=kind)) == "", kind


def test_a_company_cannot_raise_a_round_before_it_is_incorporated():
    """Two facts from two worlds — the register's own filing and a funding
    announcement the register has never seen. An inversion is two different
    companies, not a late filing."""
    born_2023 = registered("1", "X", incorporated="2023-01-19")

    assert uk.disqualified(born_2023, funded="2019-06-01").startswith("incorporated 2023-01-19")
    assert uk.disqualified(born_2023, funded="2024-06-01") == ""
    # The corpus states no date for most companies, and an absent date refuses
    # nothing rather than everything.
    assert uk.disqualified(born_2023, funded=None) == ""


# --- what a company says about itself -----------------------------------------


def test_a_number_is_stated_not_merely_present():
    """Eight digits on a marketing page are a build id, a date or a phone
    number. The disclosure words in front of them are what make them a claim."""
    assert uk.numbers("Registered in England and Wales no. 09446231") == {"09446231"}
    assert uk.numbers("Company No: SC334532") == {"SC334532"}
    assert uk.numbers("<p>Registered office: 5 Appold Street</p>"
                      "<script>var build='20240115'</script>") == set()
    assert uk.numbers("Prices from 12345678 tokens") == set()


def test_an_ico_registration_is_not_a_company_number():
    """MEASURED on four companies' privacy pages, beside their real numbers.

    `ZA797592` is TrueLayer's ICO data-protection registration: the same eight
    characters, a different register. Companies House issues no `Z` prefix, and
    without this rule four companies that state exactly one company number appear
    to state two and are held for nothing.
    """
    said = "Registered in England and Wales 10278251. ICO registration ZA797592."

    assert uk.numbers(said) == {"10278251"}
    # The prefixes Companies House DOES issue still read.
    assert uk.numbers("Registered in Scotland number SC334532") == {"SC334532"}


def test_a_foreign_registration_number_is_not_a_uk_one():
    """MEASURED, and the reason the rule is exactly eight characters.

    capimoney.com states `Capi Money Inc., a company incorporated in Delaware
    with registration number 7262022`. Padded to eight, that is `07262022` — a
    real, dissolved, entirely unrelated London company. A rule that invents a
    digit invents a company.
    """
    delaware = ("Capi Money Inc., a company incorporated in Delaware"
                " with registration number 7262022")

    assert uk.numbers(delaware) == set()


def test_declared_stops_at_the_first_page_that_answers(monkeypatch):
    """The home page footer is where most of them say it, so the common case is
    one fetch — and a site nobody could reach is a different fact from a site
    that says nothing."""
    asked = []

    def fetching(pages):
        def fetch(url, timeout=45):
            asked.append(url)
            return pages.get(url)
        return fetch

    monkeypatch.setattr(uk, "fetch", fetching(
        {"https://x.test": "<p>nothing here</p>",
         "https://x.test/privacy": "Registered in England and Wales No. 09446231"}
    ))
    assert uk.declared("https://x.test") == ({"09446231"}, "https://x.test/privacy")
    # Every page is read: a home page stating one number and a privacy page
    # stating the parent's is a company that has stated two.
    assert asked == [f"https://x.test{page}" for page in uk.LEGAL_PAGES]

    monkeypatch.setattr(uk, "fetch", fetching({"https://x.test": "<p>nothing</p>"}))
    assert uk.declared("https://x.test") == (set(), "silent")

    monkeypatch.setattr(uk, "fetch", fetching({}))
    assert uk.declared("https://x.test") == (set(), "unreachable")


def test_a_site_stating_two_numbers_settles_nothing(monkeypatch):
    """A group's terms page can name a parent and a subsidiary, and "one of
    these two" is not a company number."""
    monkeypatch.setattr(uk, "fetch", lambda url, timeout=45:
                        "Registered no. 09446231 and registered no. 14785367")
    monkeypatch.setattr(uk, "search", lambda *a, **k: [])
    monkeypatch.setattr(uk, "profile", lambda *a, **k: pytest.fail("profiled an unsettled number"))

    said = uk.stated({"Monzo": "https://x.test"})
    found = uk.look_up("key", "Monzo", said["Monzo"])

    assert said["Monzo"][0] == {"09446231", "14785367"}
    assert found["stated"] == ""
    assert found["source"].startswith("two numbers stated")


def test_a_stated_number_the_register_does_not_hold_is_not_a_badge(monkeypatch):
    """The register has the last word on a number a company published: a typo'd
    digit is a different company, and an unresolvable one is not a company."""
    monkeypatch.setattr(uk, "sleep", lambda _: None)
    monkeypatch.setattr(uk, "fetch", lambda url, timeout=45: "Company number 99999999")
    monkeypatch.setattr(uk, "get", answering(
        (200, json.dumps({"items": []})),   # the name search
        (404, ""),                          # the profile: no such company
    ))

    said = uk.stated({"Whoever": "https://x.test"})
    found = uk.look_up("key", "Whoever", said["Whoever"], attempts=1)

    assert found["stated"] == ""
    assert "the register does not hold" in found["source"]


# --- the pull -----------------------------------------------------------------


def test_pull_respects_the_rate_limit_with_backoff(monkeypatch):
    """600 requests per five minutes, and a 429 clears only by waiting.

    The pull sleeps before every call and again, longer, after every refusal, so
    a rate-limited window costs time rather than a truncated snapshot.
    """
    slept = []
    monkeypatch.setattr(uk, "sleep", slept.append)
    monkeypatch.setattr(uk, "get", answering((429, ""), (429, ""), (200, json.dumps({}))))

    assert uk.call("key", "/search/companies", attempts=3) == {}

    # Three calls paced, and a growing wait between the two that were refused.
    assert slept == [uk.RATE, uk.BACKOFF, uk.RATE, uk.BACKOFF * 2, uk.RATE]
    assert uk.RATE > 0 and uk.RATE >= 300 / 600, "faster than the documented limit"


def test_a_name_the_register_never_answered_is_left_out_not_cached_empty(monkeypatch):
    """A throttled call cached as "the register knows nobody by that name" is how
    a rate limit silently unbadges a company whose registration is fine."""
    monkeypatch.setattr(uk, "sleep", lambda _: None)
    monkeypatch.setattr(uk, "get", answering(
        (200, json.dumps({"items": [HIT]})),   # the first name answers
    ))                                          # the second 429s forever

    found = uk.pull("key", {"Monzo": None, "Nobody": None}, attempts=1)

    assert list(found) == ["Monzo"]
    assert found["Monzo"]["source"] == "no website"
    # The whole search answer is kept as evidence; the name rule refuses it here
    # rather than at the door, so the snapshot can still be used to check the rule.
    assert [c["name"] for c in found["Monzo"]["candidates"]] == ["BRAMAND LTD"]
    assert uk.find("Monzo", found["Monzo"]["candidates"]) == ("", [])


def test_write_refuses_a_pull_that_lost_most_of_the_corpus(tmp_path):
    """Stale-but-whole beats fresh-but-partial, `mca.pull`'s rule in the place
    this source can lose rows."""
    out = tmp_path / "uk.json"
    uk.write(out, {"9fin": known("10451957", "https://9fin.com/")}, pulled="2026-08-01")
    good = out.read_bytes()

    with pytest.raises(ValueError, match="short: 1 of 220"):
        uk.write(out, {"9fin": known()}, asked=220)
    assert out.read_bytes() == good


def test_search_ranking_is_never_taken_at_its_word(monkeypatch):
    """The finding this module exists for, held by a check.

    `q=monzo` answers `BRAMAND LTD` first — a dissolved shell whose only tie to
    the word is a name it dropped in 2024. Nothing here may read the top hit.
    """
    monkeypatch.setattr(uk, "sleep", lambda _: None)
    monkeypatch.setattr(uk, "get", answering((200, json.dumps({"items": [HIT, {
        "title": "MONZO BANK LIMITED", "company_number": "09446231",
        "company_status": "active", "date_of_creation": "2015-02-18",
    }]}))))

    found = uk.look_up("key", "Monzo", (set(), "no website"), attempts=1)

    # Both hits are kept as evidence, in the register's own order — and the name
    # rule reaches only the second, which is the one search ranked below it.
    assert [c["number"] for c in found["candidates"]] == ["15296432", "09446231"]
    assert [c["name"] for c in uk.find("Monzo", found["candidates"])[1]] == ["MONZO BANK LIMITED"]
    assert found["stated"] == ""


def test_profile_keeps_what_the_badge_can_show():
    """The trim: a name, a number, a status, a date, the registered office and
    the SIC codes corroboration reads. The officers are not here and never will
    be — personal data, T4.4's DIN rule."""
    kept = uk.hit(HIT)

    assert kept == {
        "number": "15296432", "name": "BRAMAND LTD", "status": "dissolved",
        "incorporated": "2023-11-20", "locality": "", "postcode": "", "sic": [], "kind": "",
    }
    assert "officers" not in json.dumps(kept) and "psc" not in json.dumps(kept)


def test_api_key_is_read_but_never_invented(monkeypatch, tmp_path):
    """No key is a real answer: the key refreshes the cache, so a machine without
    one still builds the site off the committed snapshot."""
    monkeypatch.setenv("UK_COMPANY_HOUSE_KEY", "  from-the-environment  ")
    assert uk.api_key() == "from-the-environment"

    monkeypatch.delenv("UK_COMPANY_HOUSE_KEY")
    monkeypatch.chdir(tmp_path)
    assert uk.api_key() is None

    (tmp_path / ".env").write_text("OTHER=x\nUK_COMPANY_HOUSE_KEY=from-dot-env\n")
    assert uk.api_key() == "from-dot-env"


# --- the two checks E4 doctrine names -----------------------------------------


def test_build_reads_cache_not_api(tmp_path):
    """The UK figure the build publishes comes off the disk.

    `tests/conftest.py` refuses every unstubbed network call, so a `counts` that
    reached for Companies House — which is what the nightly must never do — fails
    here rather than buying a dependency on a rate-limited upstream.
    """
    out = tmp_path / "uk.json"
    uk.write(out, {"9fin": known("10451957", "https://9fin.com/")}, pulled="2026-07-31")

    assert uk.counts(out) == {"names": 1, "stated": 1, "pulled": "2026-07-31"}

    # The figures track the file, which is the half a hardcoded constant fakes.
    uk.write(out, {"9fin": known("10451957", "x"), "Alloy": known()})
    assert uk.counts(out) == {"names": 2, "stated": 1, "pulled": date.today().isoformat()}


def test_absent_key_degrades(monkeypatch, tmp_path):
    """A missing key, a dead upstream, or a snapshot that was never pulled: the
    build reports zero and keeps going. None of these is an error.
    """
    monkeypatch.delenv("UK_COMPANY_HOUSE_KEY", raising=False)
    monkeypatch.chdir(tmp_path)   # no .env here either

    assert uk.api_key() is None
    assert uk.main([str(tmp_path / "uk.json")]) == 1, "a missing key must not be a silent no-op"
    assert not (tmp_path / "uk.json").exists(), "wrote a snapshot with no key"

    assert uk.counts(tmp_path / "never-pulled.json") == {
        "names": 0, "stated": 0, "pulled": None
    }
    for broken in ('{"companies": {"9fin": {}}, "pull', "[]", '{"companies": 220}'):
        half_written = tmp_path / "truncated.json"
        half_written.write_text(broken)
        assert uk.counts(half_written) == {"names": 0, "stated": 0, "pulled": None}

    # And the enrichment survives it: an empty register badges nobody rather
    # than raising, which is what keeps a build from failing on somebody else's
    # rate limit.
    row = {"name": "9fin", "date": None, "uk": None}
    assert uk.attach([row], uk.load(tmp_path / "never-pulled.json")) == []
    assert row["uk"] is None


def test_main_leaves_the_last_snapshot_alone_when_the_pull_fails(monkeypatch, tmp_path):
    """Stale-but-whole beats fresh-but-partial, the same rule `build.write` keeps
    for a non-conforming row."""
    out = tmp_path / "uk.json"
    uk.write(out, {"9fin": known("10451957", "https://9fin.com/")}, pulled="2026-07-31")
    monkeypatch.setattr(uk, "sleep", lambda _: None)
    monkeypatch.setattr(uk, "get", answering())        # everything 429s
    monkeypatch.setenv("UK_COMPANY_HOUSE_KEY", "key")
    monkeypatch.setattr(uk, "CORPUS", tmp_path / "corpus.json")
    monkeypatch.setattr(uk, "LISTED", tmp_path / "companies.json")
    monkeypatch.setattr(uk, "ATTEMPTS", 1)
    (tmp_path / "corpus.json").write_text(json.dumps({"companies": [{"name": "9fin"}]}))
    (tmp_path / "companies.json").write_text(json.dumps(
        {"companies": [{"name": "9fin", "countries": ["United Kingdom"]}]}
    ))

    assert uk.main([str(out)]) == 1
    assert uk.counts(out) == {"names": 1, "stated": 1, "pulled": "2026-07-31"}
