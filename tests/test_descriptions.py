"""T10.5 — a verified description and an unverified one are not the same claim.

The site publishes three AI-written lines about a company and marks them
AI-SUMMARIZED. Until now that was the whole of what it said about them, and it
covered two very different things: 245 descriptions the audit (T10.3) had read
against the company's own website and against the board we publish their roles
from, and 45 for companies the corpus held no address for, where that check has
never run and could not.

`checked: true` is the difference, and the invariants below are what stop it
from becoming decoration. The shipped files are the fixtures, deliberately —
`data/descriptions.json` is what the browser downloads, so a test agreeing with
anything else would be a test nobody is served by.
"""
from __future__ import annotations

import json
from pathlib import Path

from src import corrections

ROOT = Path(__file__).resolve().parent.parent
DESCRIPTIONS = json.loads((ROOT / "data/descriptions.json").read_text())
CORPUS = json.loads((ROOT / "data/corpus.json").read_text())["companies"]
LISTED = json.loads((ROOT / "data/companies.json").read_text())["companies"]
PAGE = (ROOT / "site/index.html").read_text()

#: Every company we hold an address for — the corpus's, with the corrections
#: file's on top, which is the same union `scripts/describe.py` reads.
ADDRESSED = {c["name"] for c in CORPUS if c["website"]} | set(corrections.load().websites)


def test_a_description_is_only_verified_where_we_hold_an_address_to_verify_it_against():
    """The invariant. The check is "read their own site against their board", so
    a company with no site to read cannot have passed it, and a flag that could
    appear without one would be a flag that means nothing."""
    unbacked = sorted(
        name
        for name, said in DESCRIPTIONS.items()
        if said.get("checked") and name not in ADDRESSED
    )

    assert not unbacked, f"marked verified with no address to verify against: {unbacked}"


def test_the_listed_companies_we_hold_no_address_for_are_all_unverified():
    """The other direction, over the rows a reader can actually reach. These are
    the ones T10.5 is about: their boards are read and their roles are real, and
    it is the description — nothing else — that nobody has stood behind."""
    blind = [row["name"] for row in LISTED if row["name"] not in ADDRESSED]

    assert blind, "if this is ever empty the check has stopped checking anything"
    assert not [name for name in blind if DESCRIPTIONS.get(name, {}).get("checked")]


def test_the_flag_is_true_or_absent_and_never_false():
    """Absence is the absence this file already renders — a missing line, a
    company with no entry at all. A `false` would be a third state the page has
    no rendering for, and it would read as a verdict rather than as a gap."""
    assert not [
        name
        for name, said in DESCRIPTIONS.items()
        if "checked" in said and said["checked"] is not True
    ]


def test_the_page_states_which_of_the_two_it_is_showing():
    """A distinction the data carries and the page does not render is a
    distinction the reader still cannot see, which is the state T10.5 found."""
    assert "d.checked" in PAGE, "the page never reads the flag"
    assert "AI-summarized · checked against their own site" in PAGE
    assert "AI-summarized · unverified" in PAGE


def test_the_split_is_real_in_the_file_that_ships():
    """Both states are populated. A file where everything is verified, or
    nothing is, would pass every check above and tell a reader nothing."""
    checked = sum(1 for said in DESCRIPTIONS.values() if said.get("checked"))

    assert 0 < checked < len(DESCRIPTIONS)
