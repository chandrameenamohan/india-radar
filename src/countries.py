"""Country matcher for the 15 target countries — T8.2 (SPEC feature 14).

The same shape as india.py, fourteen countries wider: word-boundary term lists
and nothing else. India is not re-listed here — `countries()` delegates to
`india.is_india`, whose list was measured over 4,337 real postings and whose
fixture must keep passing untouched. Duplicating it would give this repo two
answers to "is this India?".

What makes the wider list honest is what is *missing* from it. A bare
"Cambridge", "Newcastle", "Perth", "Reading", "Nice", "Richmond", "Waterloo",
"Hamilton" or "Dublin" names a real hiring city in two or three of these
countries and in the US besides, so none of them appears in any list and a
string carrying only one of them classifies as **no country at all**. That is a
real answer, not a gap. The alternative is deciding that "Cambridge, MA" is
British, which is exactly the quiet wrongness this pipeline exists not to ship.
When such a string also names its country — "Perth, Scotland", "Perth,
Australia", "Cambridge, MA, USA" — the country term is what classifies it, and
nothing here reads the city at all. So there is no US-marker rule, no state-code
table, no geo parser: the ambiguity is handled by an absence.

The line between an included city and an excluded one: exclude when the
collision is with a comparable hiring hub (Cambridge MA vs UK, Perth Scotland vs
Australia, Newcastle UK vs AU, Dublin CA vs Ireland) or with an ordinary English
word ("nice", "reading"). Include when the namesake is a small town that does
not post software roles at volume — accepted on purpose: London (Ontario), Paris
(Texas), Berlin (Connecticut), Manchester (New Hampshire), Melbourne (Florida),
Hamburg (New York), Wellington (Florida). Add to that the US towns named after
whole countries, Denmark WI and Norway ME, which any country-name list accepts
and india.py already does. Those are the known false positives of this module,
priced and named here rather than discovered later.

The city lists are flagship hubs, not gazetteers. A missing city costs nothing
on a string that names its country, which most real location strings do; the
lists only decide the bare-city strings. And unlike india.py, **none of this is
measured yet** — the T8.1 probes have not sampled non-India boards. This is a
starting list; when FINDINGS.md gains real location strings from the new
countries, entries earn their place there or get deleted there.
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
#: cannot see them, because the words really are separate words.
_TERMS: dict[str, tuple[str, ...]] = {
    "United Kingdom": (
        "united kingdom", r"u\.k\.?", "uk", "great britain",
        r"(?<!new )england", "scotland", r"(?<!new south )wales",
        "northern ireland",
        "london", "manchester", "edinburgh", "glasgow", "leeds", "belfast",
    ),
    # Dublin is deliberately absent: Dublin CA (Bay Area) and Dublin OH are both
    # live tech-posting addresses, so a bare "Dublin" is a coin flip. Real Irish
    # postings say "Dublin, Ireland".
    "Ireland": (r"(?<!northern )ireland",),
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
    identify, and both come back empty. A caller that needs "is this worth
    keeping" asks whether the list is non-empty.

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
