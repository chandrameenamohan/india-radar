"""T3.4 — India role matcher.

The fixture is the test. Every string below was observed on a real Greenhouse or
Ashby board (FINDINGS §2) or is the exact trap that a previous rule fell into.
Both lists are imported by `test_location_fixture_exact`, the VERIFICATION
invariant, so shrinking either one to make something pass fails the build there.
"""
import pytest

from src.india import cities, is_india, workplace

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
    ("location", "expected", "how"),
    [
        ("Bengaluru, India", ["Bengaluru"], None),
        ("IN-Pune", ["Pune"], None),                            # no "India" in the string
        ("Bengaluru, India; Mumbai, India", ["Bengaluru", "Mumbai"], None),  # one posting, two
        ("New Delhi", ["Delhi"], None),
        ("Indianapolis, Indiana", [], None),                    # not India at all
        (None, [], None),
        # T4.1. Every string below is live on a board today, and the pairing is
        # the point: a city and a workplace are separate facts read from one
        # string, and a role can state either, both or neither.
        ("Remote - India", [], "remote"),                       # India, city not stated
        ("India - Remote", [], "remote"),
        ("India (Remote)", [], "remote"),
        ("India Remote", [], "remote"),
        ("Remote - Anywhere, Remote - India", [], "remote"),
        ("Remote - Bangalore, India", ["Bengaluru"], "remote"),  # a city AND remote
        ("Hybrid - India", [], "hybrid"),
        ("India Office", [], "onsite"),
        ("Pune, India", ["Pune"], None),                        # a city and no claim
        # The absence that must stay an absence: 939 of 1,112 measured India
        # roles are Greenhouse's, which states a workplace nowhere. Defaulting
        # these to `onsite` would invent the most common answer for the largest
        # provider — the ambiguous zero, wearing a different hat.
        ("India", [], None),
    ],
)
def test_city_and_remote_parsing(location, expected, how):
    """T4.1's DoD check. The site's city filter is only as good as this list — a
    city it never sees is a city a user cannot filter to — and its remote filter
    is only as honest as the second column."""
    assert cities(location) == expected
    assert workplace(location) == how


def test_in_office_answers_the_workplace_question_it_refuses_the_india_one():
    """T3.4's trap, asked the other way round. `In-Office` cost 47 false
    positives when it was read as *India*, and none of that makes it a bad
    answer to "how is this role worked" — the two rules read the same string for
    different facts, and only one of them is a claim about where."""
    from src.india import is_india

    assert not is_india("Hybrid; In-Office")
    assert workplace("Hybrid; In-Office") == "hybrid"     # the more specific claim wins
    assert workplace("In-Office") == "onsite"


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
