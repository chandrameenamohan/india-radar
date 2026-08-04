"""Country matcher for the 15 target countries — T8.2 (SPEC feature 14).

The same shape as india.py, fourteen countries wider: word-boundary term lists
and nothing else. India is not re-listed here — `countries()` delegates to
`india.is_india`, whose list was measured over 4,337 real postings and whose
fixture must keep passing untouched. Duplicating it would give this repo two
answers to "is this India?".

What makes the wider list honest is what is *missing* from it. A bare
"Cambridge", "Newcastle", "Perth", "Reading", "Nice", "Richmond", "Waterloo" or
"Hamilton" names a real hiring city in two or three of these countries and in
the US besides, so none of them appears in any list and a string carrying only
one of them classifies as **no country at all**. That is a real answer, not a
gap. The alternative is deciding that "Cambridge, MA" is British, which is
exactly the quiet wrongness this pipeline exists not to ship. When such a string
also names its country — "Perth, Scotland", "Perth, Australia", "Cambridge, MA,
USA" — the country term is what classifies it, and nothing here reads the city
at all. So there is no US-marker rule, no state-code table, no geo parser: the
ambiguity is handled by an absence.

These lists are measured now (FINDINGS "Bonus: T8.2's city lists, measured",
`learning-tests/locations_live.py`): 26,880 real location strings, 3,419
distinct, from every board in slugs.json. **Zero false positives** — not one
distinct string classified to a country it is not in — and every named trap
behaved as designed, including the 16 real "Cambridge, MA" postings. The
exclusions are cheap: "Cambridge" is 17 postings of which 16 are Massachusetts,
and "Perth", "Nice" and "Newcastle" are 1-2 postings each.

**Dublin is the one exclusion the data killed.** It was excluded here fearing
Dublin CA and Dublin OH; the corpus contains zero strings naming either, while
bare "Dublin" is 51 postings and "Dublin, IE" another 8 — 59 postings, 24% of
Ireland's volume, classifying as no country. So it is a city term now, carrying
the only lookahead in this module: a Dublin that names a US state is still
nothing. The collision is guarded where it would occur rather than paid for
everywhere, which is why the no-US-marker-rule paragraph above still holds.

The remaining namesake risks are named rather than guarded — London (Ontario),
Paris (Texas), Berlin (Connecticut), Manchester (New Hampshire), Melbourne
(Florida), Hamburg (New York), Wellington (Florida), and the US towns named
after whole countries, Denmark WI and Norway ME, which any country-name list
accepts and india.py already does. The measurement found **none of them** in
26,880 strings. They stay documented risks rather than observed failures, and a
guard each would be regex spent on strings that do not exist.

The city lists are flagship hubs, not gazetteers: 53 of the 124 terms measured
never fired on any real string (every Norwegian city but Oslo, every NZ city but
Auckland, six of Japan's nine, every native-language country name except
"deutschland"). "dublin" is the 125th, added after that count.
They are kept deliberately — they cost zero measured false positives, a board we
have not sampled may use them tomorrow, and deleting them is churn against a
list that is already right. Two counts are worth knowing rather than acting on:
New Zealand is 5 postings and Norway 3, which is under SPEC's "add a country
when probe data shows real volume" bar. Both stay because the country list is a
product decision, not this module's.
"""
from __future__ import annotations

import re

from src.india import is_india

#: Country -> the terms that name it, in SPEC order. Terms are regex fragments,
#: not literals: `u\.k\.?` escapes its dots, and three of them carry a negative
#: lookbehind because one country's name sits inside another country's place.
#: "Northern Ireland" is the UK and not Ireland, "New South Wales" is Australia
#: and not Wales, and "New England" is neither — it is the US north-east. Those
#: three are the only cross-country substring traps in these 15; `\b` alone
#: cannot see them, because the words really are separate words. One term also
#: carries a negative lookahead, for a different reason — see Ireland.
_TERMS: dict[str, tuple[str, ...]] = {
    "United Kingdom": (
        "united kingdom", r"u\.k\.?", "uk", "great britain",
        r"(?<!new )england", "scotland", r"(?<!new south )wales",
        "northern ireland",
        "london", "manchester", "edinburgh", "glasgow", "leeds", "belfast",
    ),
    # "dublin" carries the only lookahead here, and it is the shape of the trap
    # rather than a general rule: a Dublin that names a US state is a US Dublin,
    # and everything else is Irish. Measured — zero US-Dublin strings in 26,880,
    # against 59 postings (24% of Ireland's volume) that the exclusion was
    # dropping. "Dublin, IE" needs nothing further: this term matches it, so the
    # ISO form comes free rather than as a second rule. It guards the two US
    # Dublins that get named (CA, OH); "Dublin, GA" would still read as Irish.
    # Extending it state by state is the general marker rule in disguise, and
    # that rule would change how the other 123 measured terms behave — so this
    # stops where the evidence does.
    "Ireland": (r"(?<!northern )ireland", r"dublin(?!,\s*(?:ca|california|oh|ohio)\b)"),
    "Germany": (
        "germany", "deutschland",
        "berlin", "munich", "münchen", "munchen", "hamburg", "frankfurt",
        "cologne", "köln", "stuttgart", "düsseldorf", "dusseldorf", "leipzig",
        "dresden", "karlsruhe",
    ),
    # "holland" is out: Holland, Michigan. "North Holland" in a real Amsterdam
    # string is caught by "netherlands" or "amsterdam" anyway.
    "Netherlands": (
        "netherlands",
        "amsterdam", "rotterdam", "utrecht", "eindhoven", "the hague",
        "den haag", "delft", "groningen",
    ),
    # "nice" is out — it is an ordinary English word before it is a city.
    "France": (
        "france",
        "paris", "lyon", "marseille", "toulouse", "bordeaux", "lille", "nantes",
        "grenoble", "montpellier", "strasbourg",
    ),
    # "valencia" is out: Valencia CA and Valencia, Venezuela.
    "Spain": (
        "spain", "españa", "espana",
        "madrid", "barcelona", "bilbao", "málaga", "malaga", "sevilla",
        "seville", "zaragoza",
    ),
    "Sweden": (
        "sweden", "sverige",
        "stockholm", "gothenburg", "göteborg", "goteborg", "malmö", "malmo",
        "uppsala", "linköping", "linkoping", "lund",
    ),
    "Denmark": (
        "denmark", "danmark",
        "copenhagen", "københavn", "kobenhavn", "aarhus", "århus", "odense",
        "aalborg",
    ),
    # "bergen" is out: "Bergen County, NJ" is a common US location string.
    "Norway": (
        "norway", "norge",
        "oslo", "trondheim", "stavanger", "tromsø", "tromso",
    ),
    "Finland": (
        "finland", "suomi",
        "helsinki", "espoo", "tampere", "oulu", "turku", "vantaa",
    ),
    "Japan": (
        "japan",
        "tokyo", "osaka", "kyoto", "yokohama", "nagoya", "fukuoka", "sapporo",
        "kobe", "shibuya",
    ),
    "Singapore": ("singapore",),
    # "victoria" is out (Victoria BC, Victoria TX, and a given name); the state
    # is reached through "australia" in "Melbourne, Victoria, Australia".
    "Australia": (
        "australia", "new south wales", "nsw", "queensland",
        "sydney", "melbourne", "brisbane", "adelaide", "canberra",
    ),
    "New Zealand": (
        "new zealand", "aotearoa",
        "auckland", "wellington", "christchurch", "dunedin",
    ),
}

#: SPEC order, India first — the order `countries()` returns, so two builds of
#: the same board diff cleanly.
COUNTRIES: tuple[str, ...] = ("India", *_TERMS)

#: `(?<!\w)`/`(?!\w)` rather than `\b` for one reason: `\b` after the trailing
#: dot of "U.K." asks for a word boundary between "." and end-of-string, which
#: does not exist, so `\bu\.k\.\b` never matches the string it was written for.
#: On every term that ends in a letter the two are identical.
_PATTERNS: dict[str, re.Pattern[str]] = {
    country: re.compile(r"(?<!\w)(?:" + "|".join(terms) + r")(?!\w)", re.IGNORECASE)
    for country, terms in _TERMS.items()
}


def countries(location: str | None) -> list[str]:
    """The target countries this location string names, in COUNTRIES order.

    Zero or more, and zero is the common honest answer: "Warsaw, Poland" is a
    real posting in a country we do not target, "Newcastle" is a place we cannot
    identify, and both come back empty. The two zeros are different and this
    function cannot tell them apart, which is why T16.1 stopped letting it decide
    what gets published: no caller asks "is this worth keeping" any more. It
    answers "which of the fifteen, if any", and an empty answer keeps its role.

    More than one is real too — "London, UK; Sydney, Australia" is a single
    posting open in two of our countries, and (like india.cities) it needs no
    splitting: any term anywhere in the string counts.
    """
    if not location:
        return []
    found = {c for c, pattern in _PATTERNS.items() if pattern.search(location)}
    if is_india(location):
        found.add("India")
    return [c for c in COUNTRIES if c in found]
