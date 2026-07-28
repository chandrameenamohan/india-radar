"""CB Insights unicorn list — T1.4 (SPEC feature 1).

The one page CB Insights leaves outside its paywall is the complete unicorn
board, and it is server-rendered HTML: 1,404 companies with a valuation, a
country and an industry in a plain `<table>`. No key, no pagination, one call.

**A unicorn valuation is not a funding round**, so this source states no amount,
no letter and no date — the "Date Joined" column is the day the company first
crossed $1B, which is neither its latest round nor a date the site could honestly
rank recency by. What the list *is* evidence of is fundedness at scale: a company
valued at $1B or more is past Series A by any reading. That is the same claim
YC's `Growth` label makes, so it is recorded the same way and
`src/corpus.py` judges it under the same rule.

Industry is the source's own column and SPEC's non-goals are applied to it here,
for the reason EDGAR's technology filter exists: unfiltered, the biggest single
contribution this source would make to a site about software jobs is 213
industrial manufacturers and 128 biotechs.
"""
from __future__ import annotations

import re
from html import unescape

from src.finsmes import Record

UNICORNS = "https://www.cbinsights.com/research-unicorn-companies"

#: CB Insights' seven industry buckets, minus the three SPEC rules out:
#: Healthcare & Life Sciences (biotech), Industrials (hardware) and
#: Consumer & Retail (brands and services). Measured on the live board, keeping
#: these four is 851 of 1,404 companies.
SOFTWARE = frozenset(
    {"Enterprise Tech", "Financial Services", "Media & Entertainment", "Insurance"}
)

# One board row. The company cell is a link to its CB Insights profile, which is
# the source URL; the remaining cells are positional and unlabelled, so the
# industry is matched in place rather than by header.
_ROW = re.compile(
    r'<td><a href="(?P<url>https://www\.cbinsights\.com/company/[^"]+)">(?P<name>[^<]+)</a></td>\s*'
    r'<td data-value="[^"]*">[^<]*</td>\s*'  # valuation, $B — not a round, so unread
    r"<td>[^<]*</td>\s*"  # date joined the unicorn club — not a round date
    r"<td>[^<]*</td>\s*<td>[^<]*</td>\s*"  # country, city
    r"<td>(?P<industry>[^<]*)</td>",
    re.S,
)


def parse(page: str) -> list[Record]:
    """Software unicorns from the board.

    Deliberately does not decide whether $1B qualifies — that is
    `corpus._qualified_by`'s call. It decides only what the row says, and a row
    outside SPEC's sectors says nothing this site can use.
    """
    return [
        Record(
            name=unescape(row["name"]).strip(),
            amount=None,  # the board states a valuation; a valuation is not money raised
            currency=None,
            date=None,  # "date joined" is when it first hit $1B, not its latest round
            round_letter=None,
            source_url=row["url"],
            stage="growth",  # a $1B valuation is past Series A by any reading
        )
        for row in _ROW.finditer(page)
        if row["industry"] in SOFTWARE
    ]
