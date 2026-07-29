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


def test_20_known_pairs_zero_false_positives():
    """Invariant 5 (T4.4). A wrong CIN is worse than no CIN: publishing somebody
    else's company registration is a real-world error, not a cosmetic one."""
    from src import build, mca
    from tests.test_mca import PAIRS, labelled_pairs_verdicts, register

    assert len(PAIRS) >= 20
    assert labelled_pairs_verdicts() == [(company, label) for company, _, label in PAIRS]

    # The traps must stay IN the fixture, the same rule invariant 2 keeps. Each
    # is a registered name that OPENS with a listed company's letters and belongs
    # to somebody else, so deleting one is how this comes back green with the
    # boundary rule gone.
    traps = {name for _, name, label in PAIRS if label == ""}
    assert {"KONGSBERG MARITIME INDIA PRIVATE LIMITED", "NOTIONEXT INDIA PRIVATE LIMITED",
            "HIGH TOUCH HEALTH SOLUTIONS GLOBAL PRIVATE LIMITED"} <= traps
    # And the schema is the second lock: nothing below the publish threshold can
    # reach a row even if the matcher one day hands it over.
    rows = [{"name": "Stripe", "mca": None}]
    mca.attach(rows, register("STRIPE INDIA PRIVATE LIMITED"))
    assert not build.mca_errors(rows[0]["mca"])
    assert build.mca_errors({**rows[0]["mca"], "confidence": mca.PREFIX})


@pytest.mark.xfail(reason="T6.4 not implemented", strict=True)
def test_partial_run_leaves_published_json_intact():
    raise AssertionError("T6.4: fail-safe publish not implemented")
