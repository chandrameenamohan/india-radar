"""ATS slug discovery — careers page first (T2.1), then guessing (T2.2).

A company's job board lives at an ATS slug we don't know. The cheapest honest way
to learn it is to read the company's own careers page and take the board URL it
already links to — no guessing, the company told us.

That method alone resolves 6 of the 8-company fixture, and the ones it misses
miss for three different reasons that must not be conflated:

  `no-careers-page`  we never reached a page, so we know nothing
  `no-board-link`    we read the page and it linked no board — almost always a
                     JS-rendered listing
  `ambiguous-board`  the page linked more than one board and we will not pick

Every unresolved company carries its reason. An unresolved company is a company
we could not check, and the build report must be able to say which kind of
not-knowing it was. A company guessing then fails as well keeps that reason
rather than a vaguer one: it is what tells T2.3 whether the override file owes
this company a careers URL or a slug.

Whatever careers-page discovery leaves, `guess` tries: build a Greenhouse slug
out of the name, then ask Greenhouse *whose board that is*. The second half is
the load-bearing one — guessing without it resolves more companies, and some of
them are a different company (`greenhouse/brave` is the browser, not Brave Care).
"""
from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import NamedTuple, TypedDict

from src.greenhouse import board_name
from src.net import fetch

#: Board URLs as the three providers actually emit them, captured verbatim from
#: live careers pages (see tests/fixtures/board-links.txt):
#:   https://boards.greenhouse.io/figma/jobs/5988684004
#:   https://job-boards.greenhouse.io/vercel/jobs/5999792004   (newer host)
#:   https://jobs.ashbyhq.com/ramp/09a9381c-677b-40a5-9ff1-027bd4302c13
#: The `embed/job_board/js?for=` branch is Greenhouse's script-tag include; the
#: lookahead stops the bare host + "embed" from being read as a company slug.
BOARDS = {
    "greenhouse": re.compile(
        r"(?:job-boards|boards)\.greenhouse\.io/"
        r"(?:embed/job_board(?:/js)?\?for=)?"
        r"(?!embed\b)([a-z0-9_-]+)",
        re.I,
    ),
    "lever": re.compile(r"jobs\.(?:eu\.)?lever\.co/([a-z0-9_-]+)", re.I),
    "ashby": re.compile(r"jobs\.ashbyhq\.com/([a-z0-9_.-]+)", re.I),
}

#: ponytail: the domain is guessed from the name, because nothing feeds one in
#: yet — FinSMEs headlines have no website link. Ceiling: this only finds
#: companies whose name maps cleanly onto their domain. Upgrade path: YC's
#: payload carries a real website on 1,072 of 1,075 Growth companies; feed it in
#: here and these two lines go away. EDGAR does NOT — measured in T1.3, Form D
#: gives a street address and a phone number and no URL. The tail is T2.3's
#: override file.
#: Both paths are load-bearing: corebiomedicine.com/careers 404s while /jobs is
#: the real listing, and anthropic.com/jobs redirects to the listing its
#: /careers landing page doesn't link.
_PATHS = ("careers", "jobs")
_NOT_ALNUM = re.compile(r"[^a-z0-9]+")

#: A parked domain answers 200 with a redirect stub — measured 114 bytes for
#: antareslabs.com/careers, against 130KB for the smallest real careers page in
#: the sample. Below this, we did not reach a careers page, and saying we did
#: would report "read their page, no board on it" about a domain squatter.
#: ponytail: a length floor rather than content sniffing. Three orders of
#: magnitude of headroom, so the exact number isn't delicate.
_MIN_PAGE = 2_000


#: Greenhouse slugs a company name is worth trying. Measured over 260 corpus
#: companies plus the 8-company fixture (learning-tests/slug_guess_live.py):
#: the bare normalised name is the workhorse at ~10% of companies, and each of
#: these five suffixes found one board the bare name missed — Glean files under
#: `gleanwork`, Automattic under `automatticcareers`. A hyphenated variant and
#: `hq`, `inc`, `io`, `team` found NOTHING across all 260 and are not tried.
#: ponytail: the suffixes are 5 of the 6 calls per unresolved company for ~1.5%
#: more companies — 34 min against the corpus where the bare name alone is 6.
#: Both are small beside careers-page discovery's 2.5 hours, so the recall wins.
#: Ceiling: one data point per suffix. Upgrade path is T2.3's override file,
#: which is where a tail belongs, rather than a longer list of guesses here.
_GUESS_SUFFIXES = ("", "work", "ai", "labs", "jobs", "careers")


class Slug(TypedDict):
    ats: str
    slug: str
    method: str  # "careers-page" (T2.1), "guess" (T2.2); "override" is T2.3


class Resolution(NamedTuple):
    resolved: dict[str, Slug]
    unresolved: dict[str, str]  # company -> reason it isn't resolved

    @property
    def rate(self) -> float:
        total = len(self.resolved) + len(self.unresolved)
        return len(self.resolved) / total if total else 0.0

    @property
    def methods(self) -> Counter[str]:
        """How many companies each method resolved. The combined rate is only
        meaningful next to this split — a rate that rose because guessing
        accepted anything is a different fact from one that rose because it
        found boards."""
        return Counter(slug["method"] for slug in self.resolved.values())


def find_boards(html: str) -> list[tuple[str, str]]:
    """Every distinct (ats, slug) the page links to, sorted.

    Distinct rather than first-match: a page linking two different boards is a
    real signal that we don't know which is the company's, and the caller has to
    see that instead of silently taking whichever appeared first.
    """
    return sorted(
        {(ats, m.group(1).casefold()) for ats, rx in BOARDS.items() for m in rx.finditer(html)}
    )


def key(name: str) -> str:
    """A company name reduced to what a domain or a board slug is made of."""
    return _NOT_ALNUM.sub("", name.casefold())


def careers_urls(name: str) -> list[str]:
    """Candidate careers-page URLs for a company name."""
    return [f"https://{key(name)}.com/{path}" for path in _PATHS]


def states_company(board: str | None, name: str) -> bool:
    """Whether a board that answered is plausibly *this* company's.

    A guessed slug only proves some board exists. Measured, that is not the same
    question: `greenhouse/brave` is a real board belonging to the browser, not
    to the corpus company Brave Care, and `greenhouse/doc` is Marshall Wace's.
    Publishing those roles under the wrong company's name is the failure mode
    this whole method risks.

    So the board must state a name that CONTAINS the company's: "Automattic
    Careers", "Careers at Tide" and "Razorpay Software Private Limited" are the
    same company saying more, while a SHORTER name is a different company.

    The shorter direction is the one that cannot be settled from the strings,
    and that is precisely why it is refused rather than judged: "A24" for "A24
    Films" and "Cross River" for "Cross River Bank" are the same company;
    "Brave" for "Brave Care" and "Foundry" for "Foundry Robotics" are not.
    Nothing in the response tells the two apart, so we lose the first pair. That
    is the measured cost, and unresolved beats wrong.
    """
    return board is not None and key(name) in key(board)


def guess(name: str) -> Slug | None:
    """A Greenhouse slug guessed from the company name, verified against the
    board's own name — or None, having proven nothing.

    Greenhouse only, per the DoD: it 404s a wrong slug cleanly and answers in
    ~0.3s. Lever cannot be guessed at all (a wrong slug returns 200 with an
    empty array — T3.3's trap), and guessing Ashby means paying its ~151s fixed
    latency per candidate.
    """
    for suffix in _GUESS_SUFFIXES:
        slug = key(name) + suffix
        if states_company(board_name(slug), name):
            return Slug(ats="greenhouse", slug=slug, method="guess")
    return None


def resolve(name: str) -> Slug | str:
    """Resolve one company to a Slug, or to the reason it stayed unresolved."""
    pages = [
        page
        for url in careers_urls(name)
        if (page := fetch(url, timeout=30)) and len(page) >= _MIN_PAGE
    ]
    if not pages:
        return "no-careers-page"

    boards = sorted({board for page in pages for board in find_boards(page)})
    if not boards:
        return "no-board-link"
    if len(boards) > 1:
        return "ambiguous-board: " + ", ".join(f"{ats}/{slug}" for ats, slug in boards)

    ats, slug = boards[0]
    return Slug(ats=ats, slug=slug, method="careers-page")


def resolve_all(names: Iterable[str], workers: int = 8) -> Resolution:
    """Resolve a corpus: read their careers page, then guess what that missed.

    Concurrent because it is entirely network wait — two sequential fetches per
    company would put a 1,000-company corpus in hours.

    ponytail: 8 workers, each hitting a different company's own domain, so
    there is no single host to be rude to. Raise it if this ever dominates a run.
    """
    names = list(names)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        outcomes = pool.map(resolve, names)

    resolved: dict[str, Slug] = {}
    unresolved: dict[str, str] = {}
    for name, outcome in zip(names, outcomes, strict=True):
        if isinstance(outcome, str):
            unresolved[name] = outcome
        else:
            resolved[name] = outcome

    # Guessing runs on the failures and nowhere else, structurally: a company
    # whose own careers page named its board has already told us the answer, and
    # a guess could only disagree with it.
    missed = list(unresolved)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        guesses = pool.map(guess, missed)
    for name, slug in zip(missed, guesses, strict=True):
        if slug is not None:
            resolved[name] = slug
            del unresolved[name]

    return Resolution(resolved, unresolved)


def write(directory: str | Path, resolution: Resolution) -> None:
    """Emit slugs.json and unresolved.json side by side. They are two halves of
    one answer, and shipping one without the other invites reading a short
    slugs.json as "these are all the companies"."""
    out = Path(directory)
    for name, part in (("slugs", resolution.resolved), ("unresolved", resolution.unresolved)):
        (out / f"{name}.json").write_text(json.dumps(part, indent=2, sort_keys=True) + "\n")


def main() -> None:
    corpus = json.loads(Path("data/corpus.json").read_text())
    names = [company["name"] for company in corpus["companies"]]

    resolution = resolve_all(names)
    write("data", resolution)
    print(f"slugs.json: {len(resolution.resolved)}/{len(names)} resolved ({resolution.rate:.0%})")
    for method, count in sorted(resolution.methods.items()):
        print(f"  resolved   {count:3d}  by {method}")
    reasons = Counter(resolution.unresolved.values())
    for reason, count in sorted(reasons.items()):
        print(f"  unresolved {count:3d}  {reason}")


if __name__ == "__main__":
    main()
