#!/usr/bin/env python3
"""How many guessed Ashby boards are the WRONG company? — the T12.1 gate.

`learning-tests/ashby_guess_live.py` measured that Ashby slugs can be guessed:
21 of 120 sampled companies resolved to a board whose `<title>` contained the
company's name. It said in the same breath that 17.5% is a **ceiling and not a
yield**, because six of the 21 are a single generic word — Boom, Catch, Castle,
Formal, Meter, Fathom — and `states_company` asks only whether the board's title
CONTAINS the company's name. It cannot separate two companies sharing one. The
corpus proves they exist: its own YC URL for Castle is `/companies/castle-2`,
because YC has two Castles.

This file turns that worry into a number, and then checks the fix it chose
against 264 boards the corpus already knows the answer for.

Run: .venv/bin/python learning-tests/ashby_collision_live.py [sample] [seed]

KILL CRITERION, set before the run and inherited from T12.1's DoD: if more than
**10%** of name-verified hits are a different company, name containment is not
enough verification for Ashby, and this ships without the cases it cannot tell
apart rather than shipping a corpus nobody can trust.

WHAT WAS MEASURED (2026-08-02; 240 sampled of the 1,456 guessable, seed 11):

  0. THE PREMISE WAS INCOMPLETE, IN OUR FAVOUR. `ashby_guess_live.py` concluded
     that "the API does not name the company ... the BOARD PAGE does state it"
     and stopped at the `<title>`. The same page carries a `window.__appData`
     blob holding an `organization` object that states `name`, `publicWebsite`
     and `customJobsPageUrl`. The board does not merely name the company — **it
     states the company's own address**, which is precisely the independent fact
     this file was written to go hunting elsewhere for, and it arrives in the
     bytes the title already came in. No extra fetch.

  1. THE COLLISION RATE: **8 of 32 name-verified hits, 25.0%.** The kill
     criterion FIRES, by two and a half times.

     Pesto      getpesto.com       vs board pesto.app
     Boom       boomsupersonic.com vs board boompay.app
     Castle     castle.io          vs board getcastle.com     (YC's castle-2)
     Zego       zegorobotics.com   vs board zego.com
     Fathom     fathom.ai          vs board fathomhealth.com
     Cohere     cohere.io          vs board cohere.com
     Universe   onuniverse.com     vs board uni.tech
     Recurrency recurrency.com     vs board recurrency.ai

     Seven of the eight are genuinely different companies, confirmed by curling
     both addresses: neither redirects to the other. The eighth, Recurrency, is
     one company that moved domain — `recurrency.ai` 301s to `recurrency.com`.
     So 21.9% wrong and 3.1% refused-but-right, and either reading fires.

  2. WHY "EXCLUDE THE GENERIC NAMES" IS NOT THE FIX. It is not implementable at
     the size the data has: 19 of the original 21 hits are single words,
     including Patreon, Miro, Snyk and BetterUp. A single-word rule spends
     almost the whole method to remove four wrong answers. Requiring the board's
     stated address to match the one the corpus already held spends the eight,
     and keeps Catch, Formal and Meter — three of the six names the ceiling
     warning was written about.

  3. WHAT THE FIX COSTS, measured on boards that are known-right rather than
     guessed. Every one of the 264 Ashby slugs in `data/slugs.json` was resolved
     by careers-page discovery, i.e. the company itself linked it, so a
     verification that rejects them is rejecting the truth. Running the T12.1
     check over all 264:

       10  board pages state no name at all — a bare "Jobs" title
       12  state no `publicWebsite`
       24  state a name that does not contain the corpus's ('7AI' is
           'Seven AI', 'Aleo' is 'Provable', 'Payward' is 'Kraken')
       10  of the 192 where both sides state an address disagree on host, 5.2%:
           nine are one company on two domains (Rutter/rutterapi.com,
           StackAI/stack-ai.com, Numeral/numeralhq.com, Nash/usenash.com), and
           one board states `jobs.ashbyhq.com` as its own website (Capi Money)

     So the address check refuses about 1 right answer in 20, on top of what
     name containment already refuses. Against a 25% collision rate that is the
     trade this project always makes, and `states_company` already makes it for
     Cross River Bank: unresolved beats wrong.

  4. A BARE "Jobs" IS NOT PROOF THE BOARD DOES NOT EXIST — correcting
     `ashby_guess_live.py` finding B, which read it that way. Of the 10
     known-good boards whose page states no name, **8 slugs are genuinely dead**
     (posting API 404s them: charta-health, edison, hitpayapp.com, jasper,
     paxos-technology-solutions, resolve, tools) — a stale-slug finding for
     `data/slugs.json`, not for this task — but **2 are live boards the page
     simply refuses to name**: `cursor` answers the API with 1.04MB of jobs and
     `elyos` with 47KB, and both serve the same 7,128-byte shell as the nonsense
     slug `zzzznotarealslugxyz`. Identical byte count.

     This does not change the method, and the reason is worth stating: a board
     that will not say whose it is cannot be verified, so it is unresolvable
     whether or not it exists. Existence was never the question. It does mean
     the posting-API call `ashby_guess_live.py` made first, to keep misses
     cheap, buys nothing here — the page must be fetched anyway, it costs the
     same 1.6s, and it answers the only question that decides the outcome.
     `guess` makes one call per candidate instead of two.

  5. THE SUFFIX LADDER EARNS NOTHING ON ASHBY. `_GUESS_SUFFIXES` was measured
     for Greenhouse, where each of `work ai labs jobs careers` found exactly one
     board across 260 companies. Run against Ashby: **32 of 32 hits are the bare
     normalised name**, over 1,280 candidate slugs fetched — so 1,248 suffixed
     candidates found nothing at all. That is not free here the way it is on
     Greenhouse, where a miss is a 0.3s 404: an Ashby candidate is a 1.6s page
     whether it hits or misses, so the ladder is five sixths of the pass. Bare
     name only puts the whole 1,456-company guess at ~4.5 minutes rather than
     the ~26 the task was scoped at, for a yield this sample cannot tell apart.
"""
from __future__ import annotations

import json
import random
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ashby import API, identity  # noqa: E402
from src.net import get  # noqa: E402
from src.slugs import _GUESS_SUFFIXES, host, key, same_site, states_company  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

#: The two buckets guessing can help, exactly as ashby_guess_live.py defined
#: them so the two runs measure one population. `no-website` is excluded: those
#: companies fail for a reason guessing does not touch — and, since T12.1, for a
#: reason that would leave the address check with nothing to check.
GUESSABLE = ("no-board-link", "no-careers-page")

KILL = 0.10
WORKERS = 8


def hit(name: str) -> tuple[str, str, str | None, str] | None:
    """The first candidate slug whose board TITLE names this company, ignoring
    the address entirely.

    Deliberately ignoring it: reproducing the unverified method is the only way
    to measure what it would have shipped. Returns (slug, stated name, stated
    website, the suffix that found it).
    """
    for suffix in _GUESS_SUFFIXES:
        slug = key(name) + suffix
        board = identity(slug)
        if states_company(board.name, name):
            return slug, board.name or "", board.website, suffix
    return None


def collisions(sample: list[str], sites: dict[str, str | None]) -> None:
    """Section 1 — of the boards a NAME resolves to, how many are someone else's."""
    started = time.time()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        found = list(pool.map(hit, sample))
    elapsed = time.time() - started

    hits = [(n, *r) for n, r in zip(sample, found, strict=True) if r]
    print(f"NAME-VERIFIED HITS {len(hits)}/{len(sample)} = {len(hits) / len(sample):.1%}"
          f"   ({elapsed:.0f}s, {elapsed / len(sample):.1f}s per company)\n")

    verdicts: Counter[str] = Counter()
    for name, slug, stated, site, _ in hits:
        ours = sites.get(name)
        if not site or not ours:
            verdict = "UNVERIFIABLE"  # one side stated no address; nothing to check
        elif same_site(site, ours):
            verdict = "same"
        else:
            verdict = "WRONG COMPANY"
        verdicts[verdict] += 1
        print(f"{'  ' if verdict == 'same' else '**'} {name:<30} "
              f"ashby/{slug:<24} {verdict}")
        if verdict != "same":
            print(f"     corpus {host(ours) if ours else None!r:<26} "
                  f"board {host(site) if site else None!r}   (titled {stated!r})")

    wrong = verdicts["WRONG COMPANY"]
    rate = wrong / len(hits) if hits else 0.0
    print(f"\nCOLLISION RATE {wrong}/{len(hits)} = {rate:.1%}"
          f"   [same {verdicts['same']}, wrong {wrong}, "
          f"unverifiable {verdicts['UNVERIFIABLE']}]")
    print(f"KILL CRITERION ({KILL:.0%}): " + (
        "FIRES — a board title is not identity. The address must be checked too."
        if rate > KILL else "does not fire — name containment alone would do."))
    print(f"YIELD once the address is required: {verdicts['same']}/{len(sample)} = "
          f"{verdicts['same'] / len(sample):.1%}, against {len(hits) / len(sample):.1%} "
          f"on the name alone")

    # What each of the six `_GUESS_SUFFIXES` earned on Ashby, which is a cost
    # question rather than a recall one: five sixths of the fetches are suffixed
    # candidates, and on Ashby a candidate is a 1.6s page rather than a 0.3s 404.
    suffixes = Counter(suffix or "(bare name)" for *_, suffix in hits)
    tried = sum(len(_GUESS_SUFFIXES) if not r else _GUESS_SUFFIXES.index(r[3]) + 1
                for r in found)
    print(f"\nHITS BY SUFFIX over {tried} candidate slugs fetched: {dict(suffixes)}")


def control(sites: dict[str, str | None]) -> None:
    """Section 2 — what the check costs on boards the companies themselves named.

    Every Ashby slug in data/slugs.json came off the company's own careers page,
    so this is the one population where a rejection is known to be a mistake.
    """
    slugs = json.loads((ROOT / "data" / "slugs.json").read_text())
    known = sorted((n, s["slug"]) for n, s in slugs.items() if s["ats"] == "ashby")
    print(f"\n\nCONTROL — the {len(known)} Ashby boards careers-page discovery proved\n")

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        boards = list(pool.map(lambda pair: identity(pair[1]), known))

    counts: Counter[str] = Counter()
    unnamed: list[tuple[str, str]] = []
    for (name, slug), board in zip(known, boards, strict=True):
        ours = sites.get(name)
        if board.name is None:
            counts["no name stated (bare 'Jobs')"] += 1
            unnamed.append((name, slug))
        elif not states_company(board.name, name):
            counts["name stated, does not contain ours"] += 1
            print(f"  NAME   {name:<28} ashby/{slug:<26} states {board.name!r}")
        if board.website is None:
            counts["no publicWebsite stated"] += 1
        if ours is None:
            counts["corpus holds no address"] += 1
        elif board.website and not same_site(board.website, ours):
            counts["both state an address, hosts differ"] += 1
            print(f"  SITE   {name:<28} ashby/{slug:<26} "
                  f"{host(board.website)} vs {host(ours)}")
        if ours and board.website:
            counts["both state an address"] += 1

    # A page that will not name the board is not proof there is no board — the
    # correction to ashby_guess_live.py finding B. The posting API is the oracle
    # for existence, and it disagrees with the page here.
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        live = list(pool.map(lambda pair: get(API.format(slug=pair[1]), 60), unnamed))
    for (name, slug), (status, body) in zip(unnamed, live, strict=True):
        verdict = "DEAD slug" if status == 404 else f"LIVE board, {len(body) / 1e6:.2f}MB"
        print(f"  UNNAMED {name:<27} ashby/{slug:<26} api {status}  {verdict}")

    print()
    for label, count in counts.most_common():
        print(f"  {count:>4}/{len(known)}  {label}")


def main() -> None:
    size = int(sys.argv[1]) if len(sys.argv) > 1 else 240
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 11

    unresolved = json.loads((ROOT / "data" / "unresolved.json").read_text())
    corpus = json.loads((ROOT / "data" / "corpus.json").read_text())["companies"]
    sites = {company["name"]: company.get("website") for company in corpus}

    pool = [n for n, r in unresolved.items() if r in GUESSABLE]
    # Seeded, so a re-run measures the same companies and two runs compare.
    random.seed(seed)
    sample = random.sample(pool, min(size, len(pool)))
    print(f"guessable population {len(pool)}, sampling {len(sample)} (seed {seed})\n")

    collisions(sample, sites)
    control(sites)


if __name__ == "__main__":
    main()
