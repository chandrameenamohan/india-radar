"""T4.2 — the India CTC benchmark.

An enrichment is judged on how it behaves when it finds nothing, because that is
its common case: 51 of the 116 listed companies have no benchmark at all. So
most of what follows is about absence being absence — never a zero, never a
figure without its date, and never a build that fails because somebody else's
site did.
"""
import json
from pathlib import Path

import pytest

from src import net, salary
from src.build import errors, salary_errors

RAZORPAY = Path("tests/fixtures/ambitionbox-razorpay.html").read_text()
#: A live page that answers 200 for the right company and states no figure —
#: measured on 5 of 116 companies. The trimmed shape is the real one.
CRESTA = Path("tests/fixtures/ambitionbox-cresta.html").read_text()

URL = "https://www.ambitionbox.com/salaries/razorpay-salaries"


def test_parses_the_figure_its_sample_and_its_date():
    """The three things a reader needs, from the page's own hydration payload."""
    found = salary.parse(RAZORPAY, "Razorpay", URL)
    assert found == {
        "avg_lpa": 21.2,
        "reports": 7060,
        "observed": "2026-07-28",  # the source's `lastUpdated`, not today
        "source_url": URL,
    }


def test_date_always_shown():
    """A benchmark ships with its observation date or it does not ship.

    The DoD names this check, and it is not cosmetic: the live figures were last
    recomputed anywhere between nine months ago and today, so an undated figure
    would read as a statement about now. Both halves are asserted — the parser
    refuses to produce one, and the schema refuses to publish one.
    """
    undated = RAZORPAY.replace('"lastUpdated":"2026-07-28 08:26:01.0"', '"lastUpdated":null')
    assert undated != RAZORPAY, "fixture changed shape; this test is no longer testing anything"
    assert salary.parse(undated, "Razorpay", URL) is None

    figure = salary.parse(RAZORPAY, "Razorpay", URL)
    assert figure is not None
    assert salary_errors({**figure, "observed": None})
    assert salary_errors({k: v for k, v in figure.items() if k != "observed"})
    assert not salary_errors(figure)


@pytest.mark.parametrize(
    "observed",
    ["2026-13-45", "20260728", "28-07-2026", "2026-07-28 08:26:01.0", "", "recently"],
)
def test_a_date_the_site_cannot_render_is_not_a_date(observed):
    """The site prints this string verbatim, so a real date in the wrong shape is
    still wrong here — and an impossible one is not saved by matching a pattern."""
    assert salary_errors({"avg_lpa": 21.2, "reports": 7060, "observed": observed,
                          "source_url": URL})


def test_absent_salary_renders_clean():
    """A row with no benchmark is complete and publishable.

    The DoD's other named check. `salary: None` is the majority case, so if the
    schema treated it as a gap the enrichment would take the site down on the day
    AmbitionBox went dark — the exact opposite of what SPEC asks an enrichment to
    do. Asserted against a row that is otherwise identical to one that has a
    figure, so this pins the absence and nothing else.
    """
    row = {
        "name": "Acme", "ats": "greenhouse", "slug": "acme",
        "roles": [{"title": "Staff Engineer", "url": "https://job-boards.greenhouse.io/acme/1",
                   "locations": ["Bengaluru, India"], "workplace": None}],
        "cities": ["Bengaluru"], "amount": 21_000_000, "currency": "USD",
        "round_letter": "A", "date": "2026-07-28",
        "source_url": "https://www.finsmes.com/2026/07/acme.html", "qualified_by": "letter",
        "salary": None, "mca": None,
    }
    assert errors(row) == []
    assert errors({**row, "salary": {"avg_lpa": 21.2, "reports": 7060,
                                     "observed": "2026-07-28", "source_url": URL}}) == []
    # ...and the field is not optional: a row that never states it is a row the
    # site would read `undefined` from.
    assert errors({k: v for k, v in row.items() if k != "salary"})


def test_a_page_that_answers_is_not_this_companys_page():
    """The T2.2 rule, reused rather than re-derived: a page must state a name
    CONTAINING the company's, and a shorter one is a different company whose
    salaries would otherwise be published under our row.

    The looser direction is load-bearing here rather than tolerated: measured
    over the listed set, the page for `Kaseya` states `Kaseya Software`, and an
    exact-match rule would drop it.
    """
    assert salary.parse(RAZORPAY.replace('"Razorpay"', '"Razor"'), "Razorpay", URL) is None
    assert salary.parse(RAZORPAY.replace('"Razorpay"', '""'), "Razorpay", URL) is None
    assert salary.parse(RAZORPAY.replace('"companyName":"Razorpay"', '"x":1'), "Razorpay", URL) \
        is None
    # The same company saying more of its name is still the same company.
    assert salary.parse(RAZORPAY.replace('"Razorpay"', '"Razorpay Software"'), "Razorpay", URL)


def test_a_figure_with_no_stated_sample_is_not_publishable():
    """The sample is half of what makes the figure readable — the live ones range
    from 1 salary to 9,502 — so a figure that arrives without it cannot be shown
    honestly, and defaulting the missing count to 1 (or to anything) would be
    inventing the very number the reader needs in order to discount it."""
    unsampled = RAZORPAY.replace('"totalSalaryDataPoints":"7060"', '"totalSalaryDataPoints":null')
    assert unsampled != RAZORPAY, "fixture changed shape; this test is no longer testing anything"
    assert salary.parse(unsampled, "Razorpay", URL) is None


def test_a_page_with_no_figure_is_an_absence_not_a_zero():
    """Measured on 5 of 116: the page is real, the company is right, and the
    figure is null. A zero rendered as "₹0.0L" would be this site's own kind of
    lie — the ambiguous zero it was built to refuse, in rupees."""
    assert salary.parse(CRESTA, "Cresta", URL) is None


@pytest.mark.parametrize(
    "html",
    [
        "",
        "<html><body>no hydration payload here</body></html>",
        '<script id="__NEXT_DATA__" type="application/json">{not json</script>',
        '<script id="__NEXT_DATA__" type="application/json">{"props":{}}</script>',
        '<script id="__NEXT_DATA__" type="application/json">null</script>',
    ],
)
def test_a_page_it_cannot_read_is_an_absence_not_a_crash(html):
    """A trust boundary that raises is a trust boundary that fails the build, and
    this enrichment is not allowed to fail a build."""
    assert salary.parse(html, "Razorpay", URL) is None


def test_a_negative_or_empty_sample_is_not_a_benchmark():
    """Both are figures the page could state and neither is publishable: an
    average of nothing has no meaning, and a negative CTC is a parse gone wrong
    wearing a number."""
    assert salary_errors({"avg_lpa": 0, "reports": 7060, "observed": "2026-07-28",
                          "source_url": URL})
    assert salary_errors({"avg_lpa": 21.2, "reports": 0, "observed": "2026-07-28",
                          "source_url": URL})
    # `True` is an int and would sail through an isinstance check as one report.
    assert salary_errors({"avg_lpa": 21.2, "reports": True, "observed": "2026-07-28",
                          "source_url": URL})


@pytest.fixture
def instant(monkeypatch):
    """Backoff, without the waiting. The retry COUNT is what these tests are
    about; sleeping 15s to prove it would just be a slow gate."""
    monkeypatch.setattr(salary, "sleep", lambda _: None)


def test_a_rate_limit_is_waited_out_and_an_absence_is_not(monkeypatch, instant):
    """The distinction the whole enrichment survives on.

    Measured: a burst returns 403 on a rolling window while a real absence is a
    404, and a first sweep at 8 workers came back 86-of-116 blocked. Retrying
    the 404s too would triple the run to re-learn 46 companies still aren't
    listed; not retrying the 403s empties the feature.
    """
    calls = []

    def answer(url, *a, **k):
        calls.append(url)
        return (404, b"") if "acme" in url else (403, b"")

    monkeypatch.setattr(net, "get_bytes", answer)
    assert salary.lookup("Acme") is None
    assert len(calls) == 1, "a 404 is final; retrying it only makes the build longer"

    calls.clear()
    assert salary.lookup("Razorpay") is None
    assert len(calls) == salary.ATTEMPTS


def test_a_rate_limit_that_lifts_yields_the_figure(monkeypatch, instant):
    """The point of retrying at all: the second try is a normal page."""
    answers = iter([(403, b""), (200, RAZORPAY.encode())])
    monkeypatch.setattr(net, "get_bytes", lambda *a, **k: next(answers))
    found = salary.lookup("Razorpay")
    assert found is not None and found["avg_lpa"] == 21.2


def test_an_unreachable_source_leaves_every_row_untouched(monkeypatch, instant):
    """AmbitionBox down, the whole site still ships. `attach` starts from rows
    that already say `salary: None`, so there is no path where a failed lookup
    leaves a row it cannot validate."""
    monkeypatch.setattr(net, "get_bytes", lambda *a, **k: (503, b""))
    rows = [{"name": "Razorpay", "salary": None}, {"name": "Acme", "salary": None}]
    salary.attach(rows, workers=2)
    assert [r["salary"] for r in rows] == [None, None]


def test_attach_fills_the_rows_it_found_and_only_those(monkeypatch):
    """Enrichment is per-row: one company's page answering says nothing about the
    next one's, and a mismatched zip would attach Razorpay's pay to Acme."""
    pages = {"razorpay": (200, RAZORPAY.encode()), "acme": (404, b"")}
    monkeypatch.setattr(
        net, "get_bytes", lambda url, *a, **k: pages[url.split("/")[-1].removesuffix("-salaries")]
    )
    rows = [{"name": "Acme", "salary": None}, {"name": "Razorpay", "salary": None}]
    salary.attach(rows, workers=2)
    assert rows[0]["salary"] is None
    assert rows[1]["salary"]["avg_lpa"] == 21.2


def test_the_url_slug_is_how_ambitionbox_spells_a_name():
    """Measured over all 116 listed companies: the hyphenated form is the only
    candidate that ever won, so this is the whole of the guessing."""
    assert salary.slug("Applied Intuition") == "applied-intuition"
    assert salary.slug("Ambient.ai") == "ambient-ai"
    assert salary.slug("6Sense") == "6sense"
    assert salary.slug("  Cockroach  Labs ") == "cockroach-labs"


def test_the_e2e_dataset_carries_both_a_benchmark_and_its_absence():
    """The e2e fixture has to hold the degraded row, or the site's handling of the
    majority case is never actually driven."""
    rows = json.loads(Path("tests/fixtures/companies-e2e.json").read_text())["companies"]
    assert any(r["salary"] for r in rows)
    assert any(r["salary"] is None for r in rows)
    assert any(r["salary"] and r["salary"]["reports"] == 1 for r in rows)
