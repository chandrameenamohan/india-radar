"""ATS slug discovery — overrides (T2.3), careers page (T2.1), guessing (T2.2).

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

Whatever careers-page discovery leaves, `guess` tries: build a slug out of the
name, then ask the ATS *whose board that is*. The second half is the
load-bearing one — guessing without it resolves more companies, and some of them
are a different company (`greenhouse/brave` is the browser, not Brave Care).

Greenhouse and Ashby, since T12.1, and the two are not verified alike. Greenhouse
states a board's name and 404s a slug that is not a board, so the name settles
it. Ashby answers 200 for every slug ever typed, and a quarter of the boards its
titles matched turned out to belong to a different company with the same one-word
name — so an Ashby guess must ALSO match the address the corpus already held
against the one the board states. Lever is still unguessable: a wrong slug there
returns 200 with an empty array (T3.3), so nothing can be found to verify.

Above both sits `data/overrides.yaml`. A human's answer does not merely win the
tie — the automatic methods do not run at all for a company listed there, since
they could only spend two fetches to produce an answer we would discard. It is
the one method that can resolve what `states_company` correctly refuses, and the
one whose mistakes belong to a person rather than to a source, which is why a
dead slug here stops the run instead of joining the counted failures.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from collections.abc import Iterable, Mapping
from concurrent.futures import ThreadPoolExecutor
from itertools import chain
from pathlib import Path
from typing import Any, NamedTuple, TypedDict
from urllib.parse import urlsplit

from src import corrections
from src.ashby import identity as ashby_identity
from src.greenhouse import board_name
from src.greenhouse import probe as greenhouse_probe
from src.net import fetch
from src.outcomes import Outcome

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

#: The two paths a careers page actually lives at, tried under the company's own
#: website (T1.6) or, for a company that states none, under a domain guessed from
#: its name. The guess stays because it earns its keep — measured over 30 corpus
#: companies it resolves 5, one short of what their real websites resolve — but a
#: company whose name doesn't map onto its domain was invisible without T1.6.
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

#: The same ladder, run against Ashby, earns nothing: **32 of 32 hits were the
#: bare name**, over 1,280 candidate slugs fetched (T12.1). And where a
#: Greenhouse miss is a 0.3s 404, an Ashby candidate is a 1.6s board page hit or
#: miss — so the five suffixes are five sixths of the pass for a yield the
#: measurement cannot see. Bare name only puts the whole 1,456-company guess at
#: ~4.5 minutes against ~26.
#: ponytail: a null result at n=1,248 rather than a proof there is no such
#: board. Ceiling: an Ashby org that files under `<name>careers` is invisible.
#: Upgrade path: this tuple, once one of them is measured finding a company.
_ASHBY_SUFFIXES = ("",)


#: The hand-maintained tail. YAML rather than JSON for one reason: a comment.
#: Every entry is a human overruling the evidence, and an override whose reason
#: went unrecorded is one nobody can safely delete a year later.
#: ponytail: one regex reads `<name>: <ats>/<slug>` rather than adding PyYAML —
#: this project carries no runtime dependency at all today, and buying its first
#: one for a flat mapping is a poor trade. Ceiling: everything else YAML can
#: express (nesting, lists, anchors, block scalars) is REJECTED, loudly, rather
#: than half-read. Upgrade path: if this file ever needs structure, `pip install
#: pyyaml` and delete `_ENTRY`.
OVERRIDES = Path("data/overrides.yaml")
_ENTRY = re.compile(r"^(.+?)\s*:\s*([a-z]+)/([a-z0-9_.-]+)$", re.I)


class Slug(TypedDict):
    ats: str
    slug: str
    method: str  # "careers-page" (T2.1), "guess" (T2.2), "override" (T2.3)


class Resolution(NamedTuple):
    resolved: dict[str, Slug]
    unresolved: dict[str, str]  # company -> reason it isn't resolved

    @property
    def rate(self) -> float:
        total = len(self.resolved) + len(self.unresolved)
        return len(self.resolved) / total if total else 0.0

    @property
    def methods(self) -> Counter[str]:
        """How many companies each `<ats>/<method>` pair resolved. The combined
        rate is only meaningful next to this split — a rate that rose because
        guessing accepted anything is a different fact from one that rose
        because it found boards.

        Keyed by ATS as well as method since T12.1, because the two guessable
        providers are verified by different evidence and can fail apart: a
        Greenhouse guess is one board name, an Ashby guess is a board name plus
        an address, and "guessing resolved 500" would hide which of those two
        claims the number rests on.
        """
        return Counter(f"{slug['ats']}/{slug['method']}" for slug in self.resolved.values())


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


def careers_urls(name: str, website: str | None = None) -> list[str]:
    """Candidate careers-page URLs: the company's own site when it stated one,
    and a domain guessed from its name when it didn't."""
    base = website.rstrip("/") if website else f"https://{key(name)}.com"
    return [f"{base}/{path}" for path in _PATHS]


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


def host(url: str) -> str:
    """The bare hostname a URL points at, as an address is compared.

    ponytail: `www.` stripped and nothing else — no public-suffix list, which
    would be this project's first runtime dependency for a comparison the data
    does not need. Measured over the 32 Ashby hits T12.1 sampled: all 24 genuine
    ones agree on host alone once `www.` is off, and it is needed in both
    directions (`realitydefender.com` against `www.realitydefender.com`,
    `www.catch.co` against `catch.co`). Ceiling: a company stating
    `blog.example.com` against a board stating `example.com` reads as a
    disagreement and stays unresolved, which is the safe direction. Upgrade
    path: a public-suffix list, if companies are ever measured lost to it.
    """
    split = urlsplit(url if "//" in url else "//" + url)
    return split.netloc.casefold().rpartition("@")[2].partition(":")[0].removeprefix("www.")


def same_site(stated: str | None, website: str | None) -> bool:
    """Whether a board's stated address and the corpus's are the same company's.

    This is the check `states_company` cannot make, and T12.1 measured the size
    of the gap: **8 of 32** verified-by-name Ashby hits were a different company
    — Boom Supersonic handed `boompay.app`, Castle handed `getcastle.com` (the
    corpus's own YC URL is `/companies/castle-2`, because YC has two), Zego
    Robotics handed `zego.com`, Fathom handed `fathomhealth.com`. 25%, against a
    10% kill criterion. Names cannot separate those; addresses can.

    It is not free of false negatives, and the cost was measured on boards known
    to be right rather than assumed away: over the 264 Ashby slugs careers-page
    discovery had already proved, **10 of the 192 that state an address on both
    sides disagree on host** — nine are one company on two domains (Rutter is
    `rutterapi.com`, Numeral is `numeralhq.com`) and one board states
    `jobs.ashbyhq.com` as its own website. About 1 right answer in 20, refused.
    Against 25% wrong that is the trade this module always makes.

    Both sides must state an address. A company the corpus holds none for cannot
    be checked, and an unchecked company is not a verified one.
    """
    return bool(stated and website and host(stated) == host(website))


def guess(name: str, website: str | None = None) -> Slug | None:
    """A Greenhouse or Ashby slug guessed from the company name and verified
    against the board's own account of itself — or None, having proven nothing.

    Greenhouse first, because it is the cheaper miss: ~0.3s and a clean 404 for
    a wrong slug. Ashby is second and costs ~1.6s a candidate hit or miss, which
    is a hundredfold less than the ~151s the docstring here used to cite as the
    reason not to guess it at all (T3.2 re-measured; `learning-tests/
    ashby_guess_live.py` re-measured again). It resolves ~10% of the companies
    careers-page discovery gave up on, verified — 24 of 240 sampled.

    **Ashby is verified twice and Greenhouse once, because Ashby is guessed on a
    weaker signal.** Greenhouse 404s a wrong slug, so a board that answers at
    least exists; Ashby answers 200 for every slug ever typed and only the
    page's title separates a board from a shell. Worse, the title alone is not
    identity: **8 of 32 name-verified hits were a different company** with the
    same one-word name — Boom Supersonic handed the other Boom, Castle handed
    YC's other Castle. 25%, against T12.1's 10% kill criterion. So this also
    requires the board's stated address to be the one the corpus already held,
    and that check is free: same page, same fetch, no second call.

    Lever is still not guessable at all: a wrong slug returns 200 with an empty
    array (T3.3's trap), so existence is undecidable there and no amount of
    verification helps something that cannot be found.
    """
    for suffix in _GUESS_SUFFIXES:
        slug = key(name) + suffix
        if states_company(board_name(slug), name):
            return Slug(ats="greenhouse", slug=slug, method="guess")

    # No address, no Ashby guess — and deliberately not a fallback to the name
    # alone. Structurally this costs nothing: every company guessing can help is
    # one whose careers page we reached or looked for, and a company with no
    # website never got that far (`resolve` returns `no-website` first).
    if not website:
        return None

    for suffix in _ASHBY_SUFFIXES:
        slug = key(name) + suffix
        board = ashby_identity(slug)
        if states_company(board.name, name) and same_site(board.website, website):
            return Slug(ats="ashby", slug=slug, method="guess")
    return None


def resolve(name: str, website: str | None = None) -> Slug | str:
    """Resolve one company to a Slug, or to the reason it stayed unresolved."""
    pages = [
        page
        for url in careers_urls(name, website)
        if (page := fetch(url, timeout=30)) and len(page) >= _MIN_PAGE
    ]
    if not pages:
        # Two different not-knowings, and T1.6 exists because they were one:
        # a company whose own site we read is a slug problem, a company we only
        # ever had a guessed domain for is a corpus problem, and only the second
        # is fixed by finding more websites.
        return "no-careers-page" if website else "no-website"

    boards = sorted({board for page in pages for board in find_boards(page)})
    if not boards:
        return "no-board-link"
    if len(boards) > 1:
        return "ambiguous-board: " + ", ".join(f"{ats}/{slug}" for ats, slug in boards)

    ats, slug = boards[0]
    return Slug(ats=ats, slug=slug, method="careers-page")


def parse_overrides(text: str) -> dict[str, Slug]:
    """The override file, or an error naming the line we could not read.

    Strict on purpose. A hand-edited file's failure mode is a line that parses
    into something subtly other than what was meant — a quoted key that then
    matches no company, a nested block silently flattened — and every one of
    those ends as a company quietly missing from the site. So anything this
    doesn't recognise stops the run and says which line it was.
    """
    overrides: dict[str, Slug] = {}
    for number, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        line = raw.split(" #")[0].strip()
        entry = _ENTRY.match(line)
        if not entry:
            raise ValueError(
                f"override file line {number}: expected '<company>: <ats>/<slug>', got {raw!r}"
            )
        name, ats, slug = entry.groups()
        overrides[name.strip("\"'")] = Slug(
            ats=ats.casefold(), slug=slug.casefold(), method="override"
        )
    return overrides


def verify_override(name: str, slug: Slug) -> None:
    """Raise unless this override names a board that is really there.

    A dead override is the one failure this project cannot absorb quietly. Every
    other unresolved company is *counted* as unresolved and left off the site;
    an override says a human already checked, so the same silence would read as
    "we looked, they aren't hiring" — and on Lever it literally is a 200 with an
    empty array (T3.3). It is also the only failure a person can simply fix.

    A probe that failed for any other reason is deliberately NOT an error: a
    Greenhouse outage is not a mistake in this file, and blaming the human for
    it teaches everyone to distrust the check. That company reaches the build
    holding a slug, fails there, and is counted `probe-failed` as it should be.
    """
    if slug["ats"] != "greenhouse":
        raise ValueError(
            f"override {name!r} -> {slug['ats']}/{slug['slug']}: only greenhouse boards can be "
            f"verified today, and this file must not hold an unchecked claim. {slug['ats']} "
            f"probes land with T3.2/T3.3, and until then a row on one is `probe-failed` anyway."
        )
    if greenhouse_probe(slug["slug"]) is Outcome.SLUG_UNRESOLVED:
        raise ValueError(
            f"override {name!r} -> greenhouse/{slug['slug']}: no such board. A hand-written "
            f"slug that has gone dead would list this company as hiring nobody."
        )


def load_overrides(path: str | Path = OVERRIDES) -> dict[str, Slug]:
    """The override file, parsed and checked against the live boards.

    Not guarded against a missing file: it is committed, the pipeline reads it
    every run, and resolving a whole corpus without the overrides nobody noticed
    had vanished is exactly the quiet wrong answer this module keeps refusing.
    """
    overrides = parse_overrides(Path(path).read_text())
    for name, slug in overrides.items():
        verify_override(name, slug)
    return overrides


#: Guessing is 48 threads against ONE host — boards-api.greenhouse.io — where
#: careers-page discovery is 48 threads against 48 different companies' domains.
#: The politeness argument for a high worker count does not survive that change
#: of target, so the guess pool keeps the old number.
_GUESS_WORKERS = 16


def resolve_all(
    companies: Iterable[str | Mapping[str, Any]],
    workers: int = 48,
    overrides: Mapping[str, Slug] | None = None,
) -> Resolution:
    """Resolve a corpus: take the human's answer, read careers pages for the
    rest, then guess what that missed.

    Takes corpus records, or bare names for a caller that has nothing else to
    say about a company — a name alone still resolves, on a guessed domain.

    Concurrent because it is entirely network wait — two sequential fetches per
    company would put a 1,000-company corpus in hours.

    ponytail: 48 workers, each hitting a different company's own domain, so
    there is no single host to be rude to. On a 64-company sample it is
    0.96s/company at 16 and 0.28s at 48 — the work is pure network wait, so the
    threads cost sockets and nothing else. The full corpus took ~30 minutes,
    against the sample's ~14: a random 64 under-represents the domains that hang
    to the 30s timeout, so trust the 30 and not the extrapolation.
    """
    sites = dict(_named(company) for company in companies)
    overrides = overrides or {}

    # Precedence is structural rather than a comparison: an overridden company
    # never enters the automatic pass at all, so there is no answer to prefer.
    resolved: dict[str, Slug] = {name: overrides[name] for name in sites if name in overrides}
    automatic = [name for name in sites if name not in resolved]

    with ThreadPoolExecutor(max_workers=workers) as pool:
        outcomes = pool.map(lambda name: resolve(name, sites[name]), automatic)

    unresolved: dict[str, str] = {}
    for name, outcome in zip(automatic, outcomes, strict=True):
        if isinstance(outcome, str):
            unresolved[name] = outcome
        else:
            resolved[name] = outcome

    # Guessing runs on the failures and nowhere else, structurally: a company
    # whose own careers page named its board has already told us the answer, and
    # a guess could only disagree with it.
    missed = list(unresolved)
    with ThreadPoolExecutor(max_workers=min(workers, _GUESS_WORKERS)) as pool:
        # The website travels with the name because the Ashby half of `guess` is
        # verified against it. A guess that only knew the name would have to
        # trust a board title, and T12.1 measured that at 25% wrong.
        guesses = pool.map(lambda name: guess(name, sites[name]), missed)
    for name, slug in zip(missed, guesses, strict=True):
        if slug is not None:
            resolved[name] = slug
            del unresolved[name]

    return Resolution(resolved, unresolved)


def _named(company: str | Mapping[str, Any]) -> tuple[str, str | None]:
    """(name, website) from either a corpus record or a bare name."""
    if isinstance(company, str):
        return company, None
    return company["name"], company.get("website")


def write(directory: str | Path, resolution: Resolution) -> None:
    """Emit slugs.json and unresolved.json side by side. They are two halves of
    one answer, and shipping one without the other invites reading a short
    slugs.json as "these are all the companies"."""
    out = Path(directory)
    for name, part in (("slugs", resolution.resolved), ("unresolved", resolution.unresolved)):
        (out / f"{name}.json").write_text(json.dumps(part, indent=2, sort_keys=True) + "\n")


def read(directory: str | Path = "data") -> Resolution:
    """The answers the last resolution wrote. Both halves or neither: an
    unresolved.json without its slugs.json is a resolution that lost the
    companies it succeeded on, and merging into that would silently re-resolve
    them from scratch."""
    out = Path(directory)
    return Resolution(
        json.loads((out / "slugs.json").read_text()),
        json.loads((out / "unresolved.json").read_text()),
    )


def pending(
    corpus: Iterable[str], answered: Iterable[str], changed: Iterable[str] = ()
) -> set[str]:
    """The names a rebuild has to resolve — T10.4.

    Everything else already has an answer, and re-asking costs two fetches per
    company: over the whole corpus that is ~2.5 hours to reproduce what
    data/slugs.json and data/unresolved.json already say. So a corpus rebuild
    resolves what the corpus GAINED, and nothing it already knows.

    `changed` is the exception, and it is the one that makes this task worth
    doing: an address a human corrected and a slug a human wrote down are INPUTS
    to `resolve` that have moved since the answer was derived. Six of those
    addresses were a different company's (T10.3), and the answers standing on
    them were derived from a fact this project now holds to be wrong. They are
    also free — an override never reaches the network at all, and six corrected
    websites are twelve fetches.
    """
    answered, changed = set(answered), set(changed)
    return {name for name in corpus if name not in answered or name in changed}


def merge(held: Resolution, found: Resolution, corpus: Iterable[str]) -> Resolution:
    """Last run's answers, updated by this run's, narrowed to today's corpus.

    Narrowed rather than accumulated: a name the sources have dropped keeps an
    answer here forever otherwise, and `build.shared_boards` reads this file
    whole — so a dead name sharing a board would collapse a live company into one
    that is no longer in the corpus at all.
    """
    names = list(corpus)
    resolved = {n: held.resolved[n] for n in names if n in held.resolved}
    unresolved = {n: held.unresolved[n] for n in names if n in held.unresolved}
    # A name re-asked leaves its old answer behind whichever half it lands in:
    # a company that resolved last time and is unresolved now must not keep the
    # slug as well as the reason.
    for name in chain(found.resolved, found.unresolved):
        resolved.pop(name, None)
        unresolved.pop(name, None)
    return Resolution(resolved | found.resolved, unresolved | found.unresolved)


def main(argv: Iterable[str] = ()) -> None:
    argv = list(argv)
    companies = json.loads(Path("data/corpus.json").read_text())["companies"]
    stated = sum(1 for company in companies if company.get("website"))
    overrides = load_overrides()

    if "--gained" in argv:
        held = read()
        wanted = pending(
            (c["name"] for c in companies),
            set(held.resolved) | set(held.unresolved),
            set(corrections.load().websites) | set(overrides),
        )
        print(f"--gained: {len(wanted)} of {len(companies)} to resolve "
              f"({len(companies) - len(wanted)} already answered)")
        found = resolve_all(
            [c for c in companies if c["name"] in wanted], overrides=overrides
        )
        resolution = merge(held, found, (c["name"] for c in companies))
    else:
        resolution = resolve_all(companies, overrides=overrides)

    # Read before write() replaces it. T12.1's whole claim is that this number
    # moves, and --gained means the run that moves it touches only the names the
    # corpus gained -- so the count has to come off the file, not off this run.
    previous = Path("data/unresolved.json")
    before = len(json.loads(previous.read_text())) if previous.exists() else None

    write("data", resolution)
    print(f"slugs.json: {len(resolution.resolved)}/{len(companies)} resolved "
          f"({resolution.rate:.0%}), {stated} with a stated website")
    for method, count in sorted(resolution.methods.items()):
        print(f"  resolved   {count:3d}  by {method}")
    reasons = Counter(resolution.unresolved.values())
    for reason, count in sorted(reasons.items()):
        print(f"  unresolved {count:3d}  {reason}")
    # Stated out loud rather than left to be diffed out of two JSON files: the
    # whole of T12.1 is a claim that this number moves, and a run that resolves
    # nothing new must be as visible as one that resolves 250.
    if before is not None:
        print(f"  slug-unresolved {before} -> {len(resolution.unresolved)} "
              f"({len(resolution.unresolved) - before:+d})")


if __name__ == "__main__":
    main(sys.argv[1:])
