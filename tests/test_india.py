"""T3.4 — India role matcher.

The fixture is the test. Every string below was observed on a real Greenhouse or
Ashby board (FINDINGS §2) or is the exact trap that a previous rule fell into.
Both lists are imported by `test_location_fixture_exact`, the VERIFICATION
invariant, so shrinking either one to make something pass fails the build there.
"""
import pytest

from src.india import cities, is_india

#: Must ALL classify as India. The last three are the formats a naive matcher
#: gets wrong: the ISO prefix with no "India" in it, a two-city single posting,
#: and a bare city with no country.
INDIA = [
    "Bengaluru, India",
    "Remote - India",
    "India - Remote",
    "Hyderabad, Telangana, India",
    "Gurugram, Haryana, India",
    "Mumbai, Maharashtra, India",
    "IN-Pune",
    "Bengaluru, India; Mumbai, India",
    "New Delhi",
]

#: Must ALL classify as NOT India.
NOT_INDIA = [
    "In-Office",  # the 47 false positives: a case-insensitive `IN-` ate this
    "Hybrid; In-Office",
    "IN-Office",  # even case-SENSITIVE `IN-` ate this; the list rule doesn't
    "Indianapolis, Indiana",  # "india" is a substring of "Indiana"
    "Indiana, United States",
    "Thanet, United Kingdom",  # "thane" is a substring of "Thanet"
    "San Francisco, CA",
    "Remote - US",
    "Warsaw, Poland",
    "London, United Kingdom",
    "Remote",
    "",
]


@pytest.mark.parametrize("location", INDIA)
def test_india_locations_match(location):
    assert is_india(location), f"false negative: {location!r} is an India posting"


@pytest.mark.parametrize("location", NOT_INDIA)
def test_non_india_locations_do_not_match(location):
    """A false positive here is the worse failure: it puts a San Francisco role
    on a site whose entire claim is that these roles are in India."""
    assert not is_india(location), f"false positive: {location!r} is not India"


def test_missing_location_is_not_india():
    """A role with no location is unknown, and unknown is not a yes."""
    assert not is_india(None)


@pytest.mark.parametrize(
    ("location", "expected"),
    [
        ("Bengaluru, India", ["Bengaluru"]),
        ("IN-Pune", ["Pune"]),                                  # no "India" in the string
        ("Bengaluru, India; Mumbai, India", ["Bengaluru", "Mumbai"]),  # one posting, two cities
        ("New Delhi", ["Delhi"]),
        ("Remote - India", []),                                 # India, city not stated
        ("India - Remote", []),
        ("Indianapolis, Indiana", []),                          # not India at all
        (None, []),
    ],
)
def test_city_parsing(location, expected):
    """The site's city filter is only as good as this list: a city it never sees
    is a city a user cannot filter to."""
    assert cities(location) == expected


@pytest.mark.parametrize(
    ("variant", "canonical"),
    [
        ("Bangalore, Karnataka, India", "Bengaluru"),
        ("Gurgaon, India", "Gurugram"),
        ("Cochin, Kerala", "Kochi"),
        ("Trivandrum, India", "Thiruvananthapuram"),
        ("Mysore, India", "Mysuru"),
        ("Vizag, India", "Visakhapatnam"),
    ],
)
def test_city_spellings_collapse_to_one_place(variant, canonical):
    """Both spellings are live on real boards. Left alone they would split one
    city into two filter entries, each hiding the other's roles."""
    assert cities(variant) == [canonical]
