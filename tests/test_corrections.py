"""T10.1 — the human's answer about a corpus row.

The file itself is the fixture wherever it can be: these are the four real
corrections, and a test that stopped agreeing with `data/corrections.yaml` would
be a test passing against a file nobody reads.
"""
import pytest

from src.corrections import check, load, parse


def test_the_committed_file_reads_as_what_it_says_it_is():
    """Every line in the real file parses, and lands under the directive it
    spells. A file this small is only worth having if it is exact."""
    fixed = load()
    assert fixed.websites["Cresta"].startswith("https://cresta.com")
    assert fixed.websites["Monzo"].startswith("https://monzo.com")
    assert fixed.boards["Next Caller"] == "Pindrop"
    assert set(fixed.websites) & set(fixed.boards) == set()


def test_comments_and_blank_lines_are_not_entries():
    fixed = parse("# Cresta: website https://wrong.example\n\nAcme: board Beta\n")
    assert fixed.websites == {}
    assert fixed.boards == {"Acme": "Beta"}


def test_a_trailing_comment_is_not_part_of_the_value():
    fixed = parse("Acme: website https://acme.example # their own site, checked today\n")
    assert fixed.websites == {"Acme": "https://acme.example"}


@pytest.mark.parametrize(
    "line, because",
    [
        ("Acme: greenhouse/acme", "a slug override belongs in overrides.yaml, not here"),
        ("Acme: website acme.example", "a website with no scheme is not a URL we can fetch"),
        ("Acme: website", "a directive with no value states nothing"),
        ("Acme: renamed Beta", "an unknown directive would be silently ignored"),
        ("  nested:\n    website: https://acme.example", "YAML this file does not read"),
    ],
)
def test_a_line_we_cannot_read_stops_the_run(line, because):
    """Strict for `slugs.parse_overrides`' reason: a hand-edited file fails by
    parsing into something subtly other than what was meant, and every one of
    those ends as a wrong fact on the site rather than as a crash."""
    with pytest.raises(ValueError, match="corrections file line"):
        parse(line + "\n")


def test_a_correction_for_a_company_that_left_the_corpus_stops_the_run():
    """A correction nothing applies to is the rot this file cannot absorb: it
    reads as maintained, in a file whose only value is that a human checked it."""
    with pytest.raises(ValueError, match="Gone"):
        check(["Acme"], {"Acme": "https://acme.example", "Gone": "https://gone.example"}, "website")


def test_a_correction_that_still_applies_passes_quietly():
    check(["Acme", "Beta"], {"Acme": "https://acme.example"}, "website")
