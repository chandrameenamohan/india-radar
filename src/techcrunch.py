"""TechCrunch venture coverage — T1.4 (SPEC feature 1).

TechCrunch runs on WordPress and leaves the REST API open, so its venture
category is 100 headlines per call rather than a page of markup to scrape. The
headline carries the round the same way a FinSMEs one does — company, money,
sometimes a letter — and `src/finsmes` already reads that grammar, so this reads
money and letters with the same regexes rather than a second copy of them.

**The names are the hard part, and the filters below are the source.** Measured
over 1,000 live venture posts: 77 headlines announce a round, and a naive
`^(name) raises` on them yields four VC firms raising their own funds (Accel,
Lightspeed, CRV, SignalFire), a company called `Edtech platform`, and one called
`Gen Zers`. TechCrunch writes sentence-case prose, not a wire format:

    Amazon fulfillment competitor Stord raises $250M at $3B valuation
    African defense tech Terra Industries, founded by two Gen Zers, raises $22M
    Enterprise AI startup Glean lands a $7.2B valuation

So the name is the *trailing* proper-noun run of what precedes the verb, a fund
raise is rejected outright, and a valuation is never read as a round. A headline
none of that can resolve yields no record, because a wrong company name here
becomes a wrong row on the site.
"""
from __future__ import annotations

import json
import re
from html import unescape

from src.finsmes import AMOUNT, CURRENCY, SERIES, to_units
from src.net import fetch
from src.record import Record

API = "https://techcrunch.com/wp-json/wp/v2/posts"

#: TechCrunch's "venture" AND "fundraising" categories, comma-joined — the API
#: reads that as OR. Numeric because slugs are not addressable here.
#:
#: `venture` alone was the source for a year and it is not where TechCrunch files
#: a startup's round: "Granola raises $125M, hits $1.5B valuation" (2026-03-25)
#: is tagged AI + Apps + Fundraising and nothing else, so the corpus never saw a
#: company with fifteen open roles and a UK office. Measured 2026-08-04 over the
#: same window: venture alone yields 71 funding records, venture+fundraising 217,
#: and 108 of the added names are companies venture never mentioned — Cursor,
#: Anthropic, Deepgram, Cerebras, Granola.
CATEGORY = "577030455,577234943"

#: 100 posts a call. Measured 2026-08-04: 1,400 posts of both categories ≈ 17
#: months, the horizon 1,000 venture-only posts used to buy and the same one
#: EDGAR's QUARTERS buys — recent enough to be news, long enough that last
#: spring's round is still in the corpus. Adding the second category doubled the
#: posts per month, so this went 10 -> 14 to hold the window still.
PAGES = 14

# The verbs a TechCrunch funding headline actually uses, sentence-case rather
# than title-case. `raising` is deliberately absent: "reportedly raising funding
# at a $20B valuation" is a rumour about a round that has not closed.
_HEADLINE = re.compile(
    r"^(?P<lead>.+?)\s+(?:raises|raised|nabs|lands|secures|snags|scores|banks)\s", re.I
)

# A VC firm raising its own fund is this source's version of EDGAR's pooled
# investment fund, and it is common: the venture category covers the industry,
# not only the companies in it. These are the phrasings observed on the four
# firms that got through the name rules — a fund, a firm, or money raised to
# deploy rather than to build.
_FUND = re.compile(
    r"\bfunds?\b|\bVC\b|\bventure (?:capital|firm)\b|\bLPs?\b|\bfresh capital\b"
    r"|\bto (?:back|invest in)\b",
    re.I,
)
_FIRM_SUFFIX = re.compile(r"\b(?:Ventures|Capital|Partners|Fund|Management)$")

# A valuation is not a round, and TechCrunch states both in the same sentence:
# "raises $250M at $3B valuation" is a $250M round. Reading the larger number
# would inflate the corpus and qualify companies that raised nothing.
_NOT_A_ROUND = re.compile(r"^\W*(?:valuation|valuing|ARR|revenue)\b", re.I)

_PROPER = re.compile(r"^[A-Z0-9][\w.&'’+-]*$")


def download() -> list[str]:
    """The newest PAGES pages of the funding categories.

    Failures are retried once and then skipped rather than ending the walk:
    measured, the API serves an isolated 403 roughly one page in ten and the
    next page succeeds, so stopping at the first would silently halve the
    source. Returning nothing at all is what "TechCrunch is down" looks like,
    and the caller decides what that means.
    """
    pages = []
    for page in range(1, PAGES + 1):
        url = (
            f"{API}?categories={CATEGORY}&per_page=100&page={page}"
            "&_fields=title,link,date"
        )
        payload = fetch(url, timeout=60) or fetch(url, timeout=60)
        if payload is not None:
            pages.append(payload)
    return pages


def parse(payload: str) -> list[Record]:
    """Funding records from one page of venture posts.

    Deliberately does not apply the $5M line: which amounts qualify is
    `corpus._qualified_by`'s call. What it does apply is whether the post is
    about a company raising a round at all — that is a question about the
    source, not about the corpus.
    """
    records = []
    for post in json.loads(payload):
        title = unescape(post["title"]["rendered"]).strip()
        headline = _HEADLINE.match(title)
        series = SERIES.search(title)
        amount = _round_amount(title)
        if headline is None or (amount is None and series is None):
            continue
        name = _company_name(headline["lead"])
        if not name or _FUND.search(title) or _FIRM_SUFFIX.search(name):
            continue
        records.append(
            Record(
                name=name,
                amount=to_units(amount) if amount else None,
                currency=CURRENCY[amount["symbol"]] if amount else None,
                # The post date. An article announces a round on the day it
                # closes, which is the same assumption T1.1 makes of a FinSMEs
                # listing and the reason both can feed a recency filter.
                date=post["date"][:10],
                round_letter=series["letter"] if series else None,
                source_url=post["link"],
                stage=None,  # a headline announces a round, never a stage
                website=None,  # stated in the article body — websites.fill reads it
            )
        )
    return records


def _company_name(lead: str) -> str:
    """"Amazon fulfillment competitor Stord" -> "Stord". "Edtech platform" -> "".

    The trailing run of proper nouns, because TechCrunch puts the descriptor
    first and the company last. Everything before the run is prose about the
    company rather than its name.

    ponytail: the first word of a headline is capitalised because it is first,
    so a one-word capitalised descriptor ("Fintech Ramp raises…") is absorbed
    into the name. Measured 1 such case in 77 ("How Lucra"); the row then fails
    slug resolution and is counted, rather than appearing wrongly on the site.
    Upgrade path: a leading-descriptor stop list, when the miss rate justifies one.
    """
    words = lead.split()
    # "…, founded by two Gen Zers, raises $22M" — a clause closing on a comma
    # right before the verb is grammar, not a company. The real name is earlier
    # in the sentence and cannot be located structurally, so we take none.
    if not words or words[-1].endswith(","):
        return ""

    name = []
    for word in reversed(words):
        word = word.strip(".;:—–")
        if not word or not _PROPER.match(word):
            break
        name.append(word)
    return " ".join(reversed(name))


def _round_amount(title: str) -> re.Match[str] | None:
    """The first money in the headline that is a round rather than a valuation,
    an ARR figure or revenue. None when the headline states only those — the
    round may still qualify on a stated letter."""
    for amount in AMOUNT.finditer(title):
        if not _NOT_A_ROUND.match(title[amount.end() :]):
            return amount
    return None
