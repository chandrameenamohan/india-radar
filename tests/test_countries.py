"""T8.2 — country matcher for the 15 target countries.

The fixture is the test, as in test_india.py: every string below is the shape a
Greenhouse, Ashby or Lever board actually emits (city / region / country, an
ISO-ish "UK", a "Remote - <country>", a two-location posting), or it is one of
the named cross-country traps.

A false positive is the worse failure here, exactly as it is for India: it puts
a Massachusetts role under a British flag on a site whose whole claim is that it
knows where the job is. So NO_COUNTRY is longer than the positive fixture, and
every entry in it is a string a matcher with one more "helpful" city in its list
would get wrong.
"""
import pytest

from src.countries import COUNTRIES, countries

#: The 15, in SPEC order. Not derived from src.countries — a test that asks the
#: module what it supports cannot notice the module dropping one.
SPEC_COUNTRIES = [
    "India", "United Kingdom", "Ireland", "Germany", "Netherlands", "France",
    "Spain", "Sweden", "Denmark", "Norway", "Finland", "Japan", "Singapore",
    "Australia", "New Zealand",
]

#: (location string, the countries it names). Covers all 15 — enforced below by
#: test_fixture_covers_every_target_country, so adding a country to the module
#: without a fixture string for it fails.
LOCATIONS = [
    # India, delegated to india.py and unchanged by this module.
    ("Bengaluru, India", ["India"]),
    ("Remote - India", ["India"]),
    ("IN-Pune", ["India"]),
    # United Kingdom, including the forms that never spell the country out.
    ("London, United Kingdom", ["United Kingdom"]),
    ("London, UK", ["United Kingdom"]),
    ("Remote - U.K.", ["United Kingdom"]),
    ("London, England, United Kingdom", ["United Kingdom"]),
    ("Edinburgh, Scotland", ["United Kingdom"]),
    ("Cardiff, Wales", ["United Kingdom"]),
    ("Belfast, Northern Ireland", ["United Kingdom"]),  # UK, and NOT Ireland
    ("Manchester", ["United Kingdom"]),
    ("Leeds, England", ["United Kingdom"]),
    # Ireland. Bare "Dublin" is 51 real postings and "Dublin, IE" another 8 —
    # 24% of Ireland's volume, which the first cut of this module dropped on a
    # collision (Dublin CA / Dublin OH) that occurs zero times in 26,880 real
    # strings. FINDINGS, "Bonus: T8.2's city lists, measured".
    ("Dublin, Ireland", ["Ireland"]),
    ("Dublin", ["Ireland"]),
    ("Dublin, IE", ["Ireland"]),
    ("Remote - Ireland", ["Ireland"]),
    ("Galway, Republic of Ireland", ["Ireland"]),
    # Germany
    ("Berlin, Germany", ["Germany"]),
    ("Munich, Bavaria, Germany", ["Germany"]),
    ("München", ["Germany"]),
    ("Remote (Germany)", ["Germany"]),
    ("Hamburg", ["Germany"]),
    # Netherlands
    ("Amsterdam, Netherlands", ["Netherlands"]),
    ("Amsterdam, North Holland, Netherlands", ["Netherlands"]),
    ("Eindhoven", ["Netherlands"]),
    ("The Hague, Netherlands", ["Netherlands"]),
    # France
    ("Paris, France", ["France"]),
    ("Paris, Île-de-France, France", ["France"]),
    ("Lyon", ["France"]),
    ("Remote - France", ["France"]),
    # Spain
    ("Barcelona, Spain", ["Spain"]),
    ("Madrid, Community of Madrid, Spain", ["Spain"]),
    ("Málaga", ["Spain"]),
    # Sweden
    ("Stockholm, Sweden", ["Sweden"]),
    ("Göteborg", ["Sweden"]),
    ("Malmo, Sweden", ["Sweden"]),
    # Denmark
    ("Copenhagen, Denmark", ["Denmark"]),
    ("København", ["Denmark"]),
    ("Aarhus, Denmark", ["Denmark"]),
    # Norway
    ("Oslo, Norway", ["Norway"]),
    ("Trondheim", ["Norway"]),
    # Finland
    ("Helsinki, Finland", ["Finland"]),
    ("Espoo, Uusimaa, Finland", ["Finland"]),
    # Japan
    ("Tokyo, Japan", ["Japan"]),
    ("Shibuya City, Tokyo, Japan", ["Japan"]),
    ("Osaka", ["Japan"]),
    ("Remote - Japan", ["Japan"]),
    # Singapore — the one country whose name is also its only city.
    ("Singapore", ["Singapore"]),
    ("Singapore, Singapore", ["Singapore"]),
    # Australia
    ("Sydney, NSW, Australia", ["Australia"]),
    ("Melbourne, Victoria, Australia", ["Australia"]),
    ("Sydney, New South Wales", ["Australia"]),          # NOT Wales
    ("Perth, Australia", ["Australia"]),                  # the country decides
    ("Brisbane", ["Australia"]),
    # New Zealand
    ("Auckland, New Zealand", ["New Zealand"]),
    ("Wellington", ["New Zealand"]),
    ("Christchurch, New Zealand", ["New Zealand"]),
    # One posting, two countries — no splitting needed, and the order is
    # COUNTRIES order rather than the order the string happens to use.
    ("London, UK; Sydney, Australia", ["United Kingdom", "Australia"]),
    ("Bengaluru, India; London, United Kingdom", ["India", "United Kingdom"]),
    ("Remote - Germany, Netherlands, Sweden", ["Germany", "Netherlands", "Sweden"]),
    # A target country named alongside one we do not target: we report ours and
    # say nothing about theirs.
    ("Berlin, Germany; Zurich, Switzerland", ["Germany"]),
]

#: Must ALL classify as no country. The first block is the named traps: each of
#: these cities exists in two or three of our target countries, or in the US, so
#: the honest answer to a bare one is that we do not know.
NO_COUNTRY = [
    "Cambridge, MA",              # not the UK
    "Cambridge, MA, USA",
    "Cambridge",
    "Newcastle",                  # UK or Australia
    "Nice",                       # France, or an ordinary English word
    "Reading",                    # UK, or an ordinary English word
    "Perth",                      # Scotland or Australia
    "Hamilton",                   # New Zealand, Canada, Scotland
    "Richmond",                   # UK, Australia, Virginia
    "Waterloo",                   # Belgium, Canada, Australia, London station
    "Dublin, CA",                 # Bay Area, not Ireland
    "Dublin, CA, USA",
    "Dublin, California",
    "Dublin, OH",
    "Dublin, Ohio",
    "New England",                # the US north-east, not England
    "Remote - New England",
    "Birmingham, AL",             # a comparable hub in both countries
    # Countries we deliberately do not target. "Europe" is 15 named hubs, not
    # the EEA, and a Warsaw role must not be quietly filed under one of them.
    "Warsaw, Poland",
    "Zurich, Switzerland",
    "Vienna, Austria",            # not Australia
    "Brussels, Belgium",
    "Lisbon, Portugal",
    "Milan, Italy",
    "Toronto, Canada",
    "Seoul, South Korea",
    "Tel Aviv, Israel",
    # US strings, the largest source of false positives on any board.
    "San Francisco, CA",
    "New York, NY",
    "Boston, MA",
    "Remote - US",
    "Indianapolis, Indiana",
    # No location, or one that says only how the role is worked.
    "Remote",
    "Remote - EMEA",
    "In-Office",
    "Hybrid",
    "",
]


@pytest.mark.parametrize(("location", "expected"), LOCATIONS)
def test_locations_classify(location, expected):
    assert countries(location) == expected


@pytest.mark.parametrize("location", NO_COUNTRY)
def test_ambiguous_and_untargeted_locations_name_no_country(location):
    """No country is a real answer. Guessing that "Cambridge, MA" is British
    would be a claim about where a job is, made from a name two countries
    share."""
    assert countries(location) == [], f"false positive: {location!r}"


def test_missing_location_names_no_country():
    assert countries(None) == []


def test_module_supports_exactly_the_fifteen_target_countries():
    """SPEC lists 15. A sixteenth is a decision ("add a country when probe data
    shows real volume"), not a drive-by edit."""
    assert list(COUNTRIES) == SPEC_COUNTRIES


def test_fixture_covers_every_target_country():
    covered = {country for _, expected in LOCATIONS for country in expected}
    assert covered == set(COUNTRIES), f"uncovered: {sorted(set(COUNTRIES) - covered)}"


@pytest.mark.parametrize("location", ["Perth, Scotland", "Perth, Australia", "Perth"])
def test_the_same_city_follows_whatever_country_the_string_names(location):
    """Perth is the trap in one line: two real cities, one name. The city is in
    no list, so the country term decides, and a string with no country term gets
    no country rather than the more famous guess."""
    expected = {
        "Perth, Scotland": ["United Kingdom"],
        "Perth, Australia": ["Australia"],
        "Perth": [],
    }[location]
    assert countries(location) == expected


@pytest.mark.parametrize(
    ("location", "expected"),
    [
        ("Dublin", ["Ireland"]),
        ("Dublin, IE", ["Ireland"]),
        ("Dublin, Ireland", ["Ireland"]),
        ("Dublin, CA", []),
        ("Dublin, CA, USA", []),
        ("Dublin, Ohio", []),
    ],
)
def test_dublin_is_irish_unless_it_names_a_us_state(location, expected):
    """The one term in this module that is guarded rather than absent, and the
    only one the measurement forced. Excluding Dublin outright cost 24% of
    Ireland's postings to a collision that never occurred in 26,880 strings;
    including it outright would call the Bay Area Irish. So the guard is the
    exact shape of the trap — the US Dublins name their state, and nothing else
    called Dublin does."""
    assert countries(location) == expected


def test_india_fixture_classifies_identically_through_this_module():
    """india.py is delegated to, not re-litigated: every string in its fixture
    must answer the same question the same way through the wider matcher."""
    from tests.test_india import INDIA, NOT_INDIA

    assert [loc for loc in INDIA if "India" not in countries(loc)] == [], "false negatives"
    assert [loc for loc in NOT_INDIA if "India" in countries(loc)] == [], "false positives"
