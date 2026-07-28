"""The six project-specific invariants from VERIFICATION.md.

All are expected to FAIL until their owning task lands. Red is the correct
initial state: a gate that passes an empty project teaches nothing.
"""
import pytest


@pytest.mark.xfail(reason="T6.1 not implemented", strict=True)
def test_unchecked_never_listed():
    from src import outcomes  # noqa: F401
    raise AssertionError("T6.1: outcome vocabulary not implemented")


@pytest.mark.xfail(reason="T3.4 not implemented", strict=True)
def test_location_fixture_exact():
    from src import india  # noqa: F401
    raise AssertionError("T3.4: India matcher not implemented")


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
