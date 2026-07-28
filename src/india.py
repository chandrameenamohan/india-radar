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
    Which cities they are is T4.1's question.
    """
    return bool(location and _INDIA.search(location))
