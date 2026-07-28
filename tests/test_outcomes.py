"""T6.1 — outcome vocabulary and build report.

The invariant that a never-checked company is never listed lives in
tests/test_invariants.py, where VERIFICATION.md expects to find it.
"""
import json

import pytest

from src.outcomes import CHECKED, Outcome, report, write_report

CORPUS = ["Acme", "Bolt", "Cog", "Dyne"]


def test_outcomes_are_exhaustive():
    """The vocabulary is exactly SPEC feature 12's — no more, no less.

    Extra outcomes mean the report can classify something the site doesn't know
    how to render; missing ones mean a real state gets forced into a wrong bucket.
    """
    assert {o.value for o in Outcome} == {
        "listed",
        "no-india-roles",
        "slug-unresolved",
        "probe-failed",
        "empty-board-unverified",
        "not-qualified",
    }
    assert CHECKED < set(Outcome)


def test_counts_sum_to_corpus():
    r = report(
        CORPUS,
        {
            "Acme": Outcome.LISTED,
            "Bolt": Outcome.NO_INDIA_ROLES,
            "Cog": Outcome.NOT_QUALIFIED,
        },
    )
    assert r["corpus_size"] == len(CORPUS)
    assert sum(r["counts"].values()) == len(CORPUS)
    assert set(r["companies"]) == set(CORPUS)
    # The footer's two numbers (T5.3) must also sum to the corpus.
    assert r["checked"] + r["unchecked"] == len(CORPUS)
    assert r["checked"] == 2  # not-qualified was never probed


def test_outcome_for_company_outside_corpus_is_an_error():
    with pytest.raises(ValueError, match="not in the corpus"):
        report(CORPUS, {"Ghost": Outcome.LISTED})


def test_write_report_emits_the_file(tmp_path):
    path = tmp_path / "build-report.json"
    write_report(path, report(CORPUS, {"Acme": Outcome.LISTED}))
    written = json.loads(path.read_text())
    assert written["counts"]["listed"] == 1
    assert written["counts"]["probe-failed"] == 3
