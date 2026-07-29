"""Software/sector filter — T1.7 (SPEC's non-goals, applied to the corpus).

SPEC says "software companies" and rules out hardware, biotech and services. Two
of the four E1 sources already apply that at their own end — CB Insights filters
its industry column, Forbes picks four software lists — and this is what is left
over: the sources that state no usable sector at all.

**No source hands us a software/not-software label, and that is measured, not
assumed.** Form D's entire technology branch is `Computers`, `Other Technology`,
`Telecommunications`, with no finer value to ask for — Seegrid (warehouse robots)
and KYG Trade both file as technology operating companies. YC states a rich
`subindustry`, but it categorises by *market served* rather than by what the
company builds: `Consumer -> Food and Beverage` holds DoorDash, Instacart, Rappi
and **Zepto** beside Nobell Foods, and `Industrials -> Automotive` holds Cruise.
Excluding those buckets would drop exactly the companies this site exists to
list. So the only signal left is the company's own name.

A name is weak evidence, so this deliberately decides only what a name can
carry, in three verdicts rather than two. **Wrongly excluding a real company is
invisible and wrongly including one is visible and fixable**, so anything short
of conclusive is KEPT and flagged for a human instead of dropped.

The vocabulary is measured, not imagined: every term below was checked against
all 2,948 live corpus names and kept only where every single hit was genuinely
its category. That check is what moved `medical` and `surgical` out of the
exclusion list — `Circle Medical` is telehealth software and `Surgical Safety
Technologies` is an operating-room analytics product, and a plausible-looking
vocabulary would have deleted both.
"""
from __future__ import annotations

import re
from enum import StrEnum


class Verdict(StrEnum):
    SOFTWARE = "software"  # no sector signal against it; kept
    AMBIGUOUS = "ambiguous"  # could go either way; kept AND flagged
    NOT_SOFTWARE = "not-software"  # conclusive; excluded and counted


#: Conclusive: every live corpus name carrying one of these was a drug company,
#: a food brand, a chip maker, a rocket maker or an investment vehicle. Kept
#: narrow on purpose — `labs` is absent because it is overwhelmingly software
#: (Cockroach, Grafana, dbt, Modal, Mysten, Ripple, Protocol), and a vocabulary
#: that reads it as a laboratory deletes a tenth of the corpus.
NOT_SOFTWARE = frozenset(
    {
        "aerospace",
        "beauty",
        "beverage",
        "beverages",
        "bioscience",
        "biosciences",
        "farm",
        "farms",
        "food",
        "foods",
        "fund",
        "funds",
        "genomics",
        "pharma",
        "pharmaceutical",
        "pharmaceuticals",
        "semiconductor",
        "semiconductors",
        "therapeutic",
        "therapeutics",
    }
)

#: Real signal, not conclusive. A robotics company sells software with its
#: robots as often as instead of them, `Green Energy Exchange` is a trading
#: platform and `Fleet Device Management` is SaaS. These stay in the corpus and
#: get named in `corpus.json`, so a human reviews a list of ~40 rather than
#: hunting through 2,948.
AMBIGUOUS = frozenset(
    {
        "bio",
        "device",
        "devices",
        "energy",
        "materials",
        "medical",
        "nano",
        "robotics",
        "robots",
        "solar",
        "space",
        "surgical",
    }
)

_WORDS = re.compile(r"[a-z]+")


def classify(name: str) -> tuple[Verdict, str]:
    """A verdict on one company name, with the evidence that produced it.

    The evidence travels with the verdict because the corpus publishes both: an
    exclusion nobody can audit is the silent drop this project refuses
    everywhere else.
    """
    # EDGAR files whatever the registrant typed, and some of them typed a number
    # (`011235813`, `1910`). There is no company to look up and no board to
    # probe, so it leaves by the counted door. Deliberately requires the absence
    # of *every* letter: `0x`, `N26`, `G2` and `R2` are all real software
    # companies, and any looser rule takes them too.
    if not re.search(r"[a-z]", name, re.I):
        return Verdict.NOT_SOFTWARE, "no letters in the name"

    words = set(_WORDS.findall(name.casefold()))
    if hit := sorted(words & NOT_SOFTWARE):
        return Verdict.NOT_SOFTWARE, hit[0]
    if hit := sorted(words & AMBIGUOUS):
        return Verdict.AMBIGUOUS, hit[0]
    return Verdict.SOFTWARE, ""
