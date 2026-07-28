"""The six project-specific invariants from VERIFICATION.md.

All are expected to FAIL until their owning task lands. Red is the correct
initial state: a gate that passes an empty project teaches nothing.
"""
import pytest


def test_unchecked_never_listed():
    """Invariant 1 (T6.1). A company that was never successfully checked is
    excluded from the site and counted, never rendered as "not hiring"."""
    from src.outcomes import Outcome, report

    r = report(["Checked", "Never"], {"Checked": Outcome.LISTED})

    assert r["companies"]["Never"] == "probe-failed"
    assert "Never" not in r["listed"]
    # The failure mode this guards: a missing answer quietly becoming a finding.
    assert r["counts"]["no-india-roles"] == 0
    assert r["checked"] == 1 and r["unchecked"] == 1


def test_location_fixture_exact():
    """Invariant 2 (T3.4). `In-Office` is not India. The fixture of real location
    strings classifies with zero false positives AND zero false negatives."""
    from src.india import is_india
    from tests.test_india import INDIA, NOT_INDIA

    assert [loc for loc in INDIA if not is_india(loc)] == [], "false negatives"
    assert [loc for loc in NOT_INDIA if is_india(loc)] == [], "false positives"

    # The traps must stay IN the fixture. Deleting one is how this invariant
    # would come back green while the bug it was written for is back.
    assert {"In-Office", "Hybrid; In-Office"} <= set(NOT_INDIA)
    assert "IN-Pune" in INDIA and "Bengaluru, India; Mumbai, India" in INDIA


@pytest.mark.xfail(reason="T3.3 not implemented", strict=True)
def test_empty_array_is_unverified_not_zero():
    raise AssertionError("T3.3: Lever probe not implemented")


@pytest.mark.xfail(reason="T7.1 not implemented", strict=True)
def test_probe_failed_snapshot_contributes_no_point():
    raise AssertionError("T7.1: trend derivation not implemented")


@pytest.mark.xfail(reason="T4.4 not implemented", strict=True)
def test_20_known_pairs_zero_false_positives():
    raise AssertionError("T4.4: MCA name matching not implemented")


@pytest.mark.xfail(reason="T6.4 not implemented", strict=True)
def test_partial_run_leaves_published_json_intact():
    raise AssertionError("T6.4: fail-safe publish not implemented")
