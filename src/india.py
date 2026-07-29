"""India role matcher — T3.4 (SPEC feature 5).

A city-name list, and nothing else. The obvious "improvement" — also matching
Ashby's ISO prefix `IN-` — was measured over 4,337 real postings and added
**zero** real hits while introducing 47 false positives, every one of them the
literal string `In-Office` (FINDINGS §2). `IN-Pune` is already caught here
because *pune* is in the list, so the regex bought nothing and cost precision.
It is not omitted by oversight; it was deleted on evidence.

The one thing a city list must not do is match substrings: `India` sits inside
`Indianapolis, Indiana`, which is a US posting. Hence word boundaries.
"""
from __future__ import annotations

import re

#: Every Indian city seen across the real Greenhouse and Ashby boards sampled in
#: FINDINGS §2, plus the spellings that coexist with them in the wild
#: (Bengaluru/Bangalore, Vizag/Visakhapatnam). Names a longer entry already
#: covers are left out — "mumbai" alone matches "Navi Mumbai".
CITIES = (
    "india",
    "bengaluru", "bangalore", "hyderabad", "pune", "mumbai", "delhi",
    "gurgaon", "gurugram", "noida", "chennai", "kolkata", "ahmedabad",
    "jaipur", "kochi", "cochin", "trivandrum", "thiruvananthapuram",
    "coimbatore", "indore", "chandigarh", "bhubaneswar", "nagpur", "vadodara",
    "surat", "lucknow", "vizag", "visakhapatnam", "mysuru", "mysore",
    "mohali", "thane", "faridabad", "vellore", "madurai",
)

#: Spellings of one city. The site's city filter offers the cities it finds in
#: the data, so without this "Bengaluru" and "Bangalore" become two places and a
#: filter on either hides half the roles. Both spellings are live on real boards.
ALIASES = {
    "bangalore": "bengaluru",
    "gurgaon": "gurugram",
    "cochin": "kochi",
    "trivandrum": "thiruvananthapuram",
    "mysore": "mysuru",
    "vizag": "visakhapatnam",
}

#: `\b` is load-bearing twice over: it keeps "india" out of "Indianapolis,
#: Indiana" and "thane" out of "Thanet, UK". Plain substring matching is what
#: makes a city list quietly wrong.
_INDIA = re.compile(r"\b(?:" + "|".join(CITIES) + r")\b", re.IGNORECASE)


def is_india(location: str | None) -> bool:
    """Does this location string name somewhere in India?

    Takes a location string rather than a role, because the three ATSes disagree
    on the shape of a role (Greenhouse nests `location.name`, Ashby has a flat
    `location` plus a `secondaryLocations` array). Callers unwrap their own
    provider in one line; a matcher that knew all three would be an abstraction
    over a difference that genuinely exists.

    Multi-city postings ("Bengaluru, India; Mumbai, India") need no splitting —
    one India city anywhere in the string makes the posting an India posting.
    Which cities they are is `cities` below.
    """
    return bool(location and _INDIA.search(location))


#: How a role is worked. The same three words the boards themselves use, so a
#: stated `workplaceType` needs only `.lower()` to join this vocabulary — Ashby
#: says `OnSite`/`Hybrid`/`Remote`, Lever says `onsite`/`hybrid` (T4.1 measured
#: 173 India roles across both). Greenhouse states nothing at all, ever, which is
#: why reading the location string has to work on its own.
WORKPLACES = ("remote", "hybrid", "onsite")

#: Ordered, and the order is the answer when a string says two things: `hybrid`
#: is the most specific claim a company makes, so "Hybrid; In-Office" is hybrid
#: rather than onsite. Measured vocabulary — `Remote - India`, `India (Remote)`,
#: `Hybrid - India`, `India Office` are all real strings on live boards.
_WORKPLACE = (
    ("hybrid", re.compile(r"\bhybrid\b", re.IGNORECASE)),
    ("remote", re.compile(r"\bremote\b|\bwork from home\b|\banywhere\b", re.IGNORECASE)),
    ("onsite", re.compile(r"\bon-?site\b|\bin-office\b|\boffice\b", re.IGNORECASE)),
)


def workplace(location: str | None) -> str | None:
    """How this location says the role is worked, or None if it doesn't say.

    None is a real answer and the common one: 939 of 1,112 measured India roles
    are Greenhouse's, and a Greenhouse board states the workplace nowhere — not
    in the role, not in `metadata`. Defaulting those to `onsite` would invent the
    most common answer for the largest provider, so absence stays absence.

    `In-Office` is matched here on purpose, and does NOT contradict T3.4: that
    trap was about the string being read as *India*, which it is not. Asked
    instead how a role is worked, `In-Office` answers.
    """
    for name, pattern in _WORKPLACE:
        if location and pattern.search(location):
            return name
    return None


def cities(location: str | None) -> list[str]:
    """The India cities this location names, deduplicated and canonically spelled.

    Empty for a location that is India without naming a city ("Remote - India",
    "India - Remote"). That is a real answer, not a gap: the company is hiring in
    India and hasn't said where, and the site renders it as such rather than as a
    blank. Multi-city postings yield every city they name.
    """
    matched = (m.lower() for m in _INDIA.findall(location or ""))
    found = {ALIASES.get(city, city) for city in matched}
    found.discard("india")
    return sorted(city.title() for city in found)
