"""The six project-specific invariants from VERIFICATION.md.

An invariant is expected to FAIL until its owning task lands — red is the correct
initial state, because a gate that passes an empty project teaches nothing. Five
have landed and assert for real; invariant 4 is still a `strict=True` xfail
because T7.1 is blocked on a human push.

Invariant 3 (`test_empty_array_is_unverified_not_zero`) lives in `test_lever.py`,
beside the probe it constrains and the fixtures it needs. VERIFICATION.md names
invariants by TEST NAME, not by file, so that satisfies it. This file carried a
placeholder of the same name until T3.3 landed; it was deleted rather than left
declaring "T3.3 not implemented" next to a task marked done.
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
    assert r["counts"]["no-located-roles"] == 0
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


def test_partial_run_leaves_published_json_intact(tmp_path, monkeypatch):
    """Invariant 6 (T6.4). A failed run never clobbers good data.

    The run that matters is the one that does NOT fail: every probe returns
    `probe-failed` on a bad status rather than raising, so a provider going down
    mid-run produces a complete, schema-valid file with most of the site missing,
    and the nightly's `set -e` sees a clean exit. Both halves are here — the run
    that publishes too little, and the run that is killed while publishing.
    """
    from src.build import COLLAPSE
    from tests.test_build import dark_after, kill_mid_write, publish

    out = tmp_path / "companies.json"
    publish(out, dark_after())
    good = out.read_bytes()

    with pytest.raises(ValueError, match="collapse, nothing written"):
        publish(out, dark_after(3))
    assert out.read_bytes() == good

    kill_mid_write(monkeypatch)
    with pytest.raises(OSError):
        publish(out, dark_after())
    assert out.read_bytes() == good

    # The floor has to leave room for a real loss. Satisfying this invariant by
    # refusing every loss would hold the site at its high-water mark and make the
    # nightly red on the days it is right — the way this comes back green with
    # the guarantee gone.
    assert 0 < COLLAPSE < 1
