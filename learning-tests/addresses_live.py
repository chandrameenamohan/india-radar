"""T10.5 — where else a listed company's address can honestly be found, measured live.

Run: .venv/bin/python learning-tests/addresses_live.py

45 of the 315 companies the site lists carry no website in the corpus, so all 45
descriptions rest on a check (T10.3's audit) that nobody can run for them. T1.6
already tried the funding article and these are the ones where it failed, so the
question is what is left. Three avenues, and only one of them was thought to
exist when the task was written:

  1. THE APPLY URL. Some boards apply on the company's own domain rather than on
     the ATS's — that is how Alloy, Slice and Symphony were settled by hand.
     Costs nothing: the URLs are already in companies.json.

  2. THE ATS's OWN PAGE about the board. Not the jobs endpoint the build reads —
     the page a human opens. Measured here for the first time.

  3. THE POSTING TEXT. `Super`'s 195 postings state no domain anywhere (T10.3),
     which is one measurement on one company and the wrong direction to
     generalise from either way.

THE EVIDENCE RULE, and it is the same one everywhere else in this project: a
candidate is accepted only when the company's name is inside the REGISTRABLE
domain (`slugs.states_company`'s containment, applied to a host), and only when
the avenue yields exactly one. `wayve.firststage.co` is why the registrable half
matters — the company's name is in the host and the domain belongs to an ATS
vendor. Absent is a fact; a wrong address is a wrong company, and this project
has shipped three of those.

KILL CRITERION (T10.5): under ~25% over the 40 and the honest answer is that
these companies have no address we can evidence.

WHAT IT MEASURED, 2026-08-02, over exactly those 40:

    apply-url        0/40   0%   spent already — it is what defines this set
    ats-profile     26/40  65%   <- and this was the source that "does not exist"
    posting-text    11/40  28%
    ANY             29/40  72%

    control, 20 listed companies whose address we already hold:
    19 answers, 0 disagreements, on every avenue.

So the criterion does not fire, and the premise it was written under is wrong:
the ATSes DO publish whose board a slug is. `from_profile` is in the pipeline as
`websites.from_ats`. The posting text is not — it clears the criterion and adds
three companies the ATS page does not already reach, which is a second class of
fetch for three addresses.

The other finding is a bug rather than an address. Ashby answers with one
address and answers it confidently, so where OUR SLUG is wrong the answer is
another company's, stated plainly: `ClickHouse` is listed here on
`ashby/langfuse`, and Ashby names `langfuse.com` for that board. The containment
rule is what refuses it. See `disowned`.
"""
from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import corrections
from src.build import PROBES
from src.net import fetch, get
from src.outcomes import Outcome
from src.slugs import key
from src.websites import _host, site

_ANCHOR = re.compile(r'href="(https?://[^"\s]+)"')
#: Ashby server-renders its whole board state into the page, and the company's
#: own address is a field in it. Nothing in the posting API says this.
_PUBLIC = re.compile(r'"publicWebsite"\s*:\s*"(https?://[^"]+)"')
#: Every host that belongs to somebody's tooling rather than to a company. The
#: three ATSes plus the social and code hosts every careers page links.
_NOT_A_COMPANY = (
    "greenhouse.io", "ashbyhq.com", "lever.co", "ashbyprd.com",
    "linkedin.com", "twitter.com", "x.com", "facebook.com", "instagram.com",
    "youtube.com", "github.com", "glassdoor.com", "google.com", "gstatic.com",
    "w3.org", "schema.org", "crunchbase.com", "medium.com", "bit.ly",
)


def registrable(host: str) -> str:
    """The host's last two labels — the domain a company registers.

    ponytail: two labels, no public-suffix list. `careers.airbnb.com` is
    `airbnb.com` and `wayve.firststage.co` is `firststage.co`, which is the whole
    reason this exists. Ceiling: a company under `example.co.uk` reads as
    `co.uk` and is then refused by the naming rule, which is the safe direction.
    Upgrade path: the PSL, if a `.co.uk` company ever needs one.
    """
    return ".".join(host.split(".")[-2:])


def names(company: str, url: str) -> bool:
    """Whether this URL's registrable domain states this company — T2.2's rule,
    applied to a host instead of to a board's name."""
    return bool(key(company)) and key(company) in key(registrable(_host(url)))


def candidates(company: str, urls: Iterable[str]) -> str | None:
    """The one address these URLs agree on, or None having guessed nothing."""
    found = {
        f"https://{registrable(_host(url))}"
        for url in urls
        if not any(host in _host(url) for host in _NOT_A_COMPANY) and names(company, url)
    }
    return found.pop() if len(found) == 1 else None


# --------------------------------------------------------------- the avenues


def from_apply_urls(company: str, roles: list[dict]) -> str | None:
    """Avenue 1: the host the board's own apply links sit on."""
    hosts = {_host(role["url"]) for role in roles if role.get("url")}
    if len(hosts) != 1:  # a board applying on two hosts states nothing
        return None
    return candidates(company, [f"https://{hosts.pop()}"])


def stated_by_ats(ats: str, slug: str) -> list[str]:
    """Every URL the ATS's own page about this board offers — before any rule is
    applied to it. Not the jobs endpoint the build reads: the page a human opens.

    Three different answers, because the three ATSes are three different products
    and only one of them was ever asked this question before.
    """
    if ats == "ashby":
        # Ashby answers outright: the board page server-renders the whole
        # organisation record into the HTML, and `publicWebsite` is a field in
        # it. Nothing in the posting API says this. Sometimes the response is
        # the JS shell without the state (7KB against 40KB), which is worth one
        # retry — measured, the same slug answers both ways within a minute.
        for _ in range(2):
            page = fetch(f"https://jobs.ashbyhq.com/{slug}", timeout=30) or ""
            if stated := _PUBLIC.search(page):
                return [stated.group(1)]
        return []
    if ats == "lever":
        # Lever's board page carries one link off its own host, and it is the
        # company's home.
        return _ANCHOR.findall(fetch(f"https://jobs.lever.co/{slug}", timeout=45) or "")
    # Greenhouse says it in two weaker places: the board object's "About us"
    # blurb, and the hosted page's own navigation, which is the company's site
    # chrome wrapped around the list.
    _, about = get(f"https://boards-api.greenhouse.io/v1/boards/{slug}", timeout=20)
    hosted = fetch(f"https://job-boards.greenhouse.io/{slug}", timeout=45) or ""
    return _ANCHOR.findall(about) + _ANCHOR.findall(hosted)


def from_profile(company: str, ats: str, slug: str) -> str | None:
    """Avenue 2, under the evidence rule the pipeline would have to keep."""
    return candidates(company, stated_by_ats(ats, slug))


def disowned(company: str, ats: str, slug: str) -> str | None:
    """The address the ATS states for this board when it does NOT name the
    company we list it under — the same read, with the rule taken off.

    Only Ashby can answer this, because only Ashby states one address rather than
    a page full of links. It is not a relaxation to consider shipping: it is the
    ATS's own record of whose board this is, so where it disagrees with our name
    the thing that is wrong is more likely the SLUG than the address. Measured
    here precisely so the disagreements can be read one by one.
    """
    if ats != "ashby":
        return None
    stated = stated_by_ats(ats, slug)
    return site(stated[0]) if stated and not candidates(company, stated) else None


def from_postings(company: str, ats: str, slug: str) -> str | None:
    """Avenue 3: a domain stated in the board's own posting prose."""
    provider = PROBES[ats]
    roles = (provider.describe or provider.probe)(slug)
    if isinstance(roles, Outcome):
        return None
    urls: list[str] = []
    for role in roles:
        urls += re.findall(r"https?://[^\s\"'<>)\]]+", provider.text(role))
    return candidates(company, urls)


# ---------------------------------------------------------------- the sample


def blind() -> list[dict]:
    """The listed companies the corpus holds no address for."""
    corpus = {c["name"]: c for c in json.loads(Path("data/corpus.json").read_text())["companies"]}
    listed = json.loads(Path("data/companies.json").read_text())["companies"]
    fixed = corrections.load().websites
    return [
        row
        for row in listed
        if not (corpus.get(row["name"], {}).get("website") or fixed.get(row["name"]))
    ]


def known(limit: int) -> list[tuple[dict, str]]:
    """Listed companies whose address we already hold — the control.

    A method that produces answers is not a method that produces RIGHT answers,
    and the only way to tell here is to run it where the answer is already known.
    """
    corpus = {c["name"]: c for c in json.loads(Path("data/corpus.json").read_text())["companies"]}
    listed = json.loads(Path("data/companies.json").read_text())["companies"]
    fixed = corrections.load().websites
    pairs = [
        (row, fixed.get(row["name"]) or corpus[row["name"]]["website"])
        for row in listed
        if row["name"] in corpus and (fixed.get(row["name"]) or corpus[row["name"]]["website"])
    ]
    return pairs[:limit]


def measure(rows: list[dict], label: str, workers: int = 8) -> dict[str, dict[str, str]]:
    """Run all three avenues over these companies and print what each found."""
    print(f"\n== {label}: {len(rows)} companies")

    def one(row: dict) -> tuple[str, dict[str, str]]:
        name, ats, slug = row["name"], row["ats"], row["slug"]
        return name, {
            "apply-url": from_apply_urls(name, row["roles"]) or "",
            "ats-profile": from_profile(name, ats, slug) or "",
            "posting-text": from_postings(name, ats, slug) or "",
            "ats-disowns": disowned(name, ats, slug) or "",
        }

    with ThreadPoolExecutor(max_workers=workers) as pool:
        found = dict(pool.map(one, rows))

    for row in rows:
        got = found[row["name"]]
        print(f"  {row['name']:22s} {row['ats']:11s} "
              + "  ".join(f"{a}={got[a] or '-':30s}" for a in AVENUES)
              + (f"  ATS-DISOWNS={got['ats-disowns']}" if got["ats-disowns"] else ""))
    return found


AVENUES = ("apply-url", "ats-profile", "posting-text")


def rates(found: dict[str, dict[str, str]], over: list[str], label: str) -> None:
    print(f"\n-- {label}, over {len(over)} companies")
    for avenue in AVENUES:
        hit = sum(1 for name in over if found[name][avenue])
        print(f"   {avenue:14s} {hit:3d}/{len(over)}  {hit / len(over):.0%}")
    any_hit = sum(1 for name in over if any(found[name][a] for a in AVENUES))
    print(f"   {'ANY':14s} {any_hit:3d}/{len(over)}  {any_hit / len(over):.0%}")


def main() -> None:
    rows = blind()
    found = measure(rows, "listed companies with no address in the corpus")

    everyone = [row["name"] for row in rows]
    rates(found, everyone, "all of them")
    forty = [name for name in everyone if not found[name]["apply-url"]]
    rates(found, forty, "the ones the apply URL does not reach — the KILL CRITERION set")

    print("\n-- where the ATS states an address that does NOT name the company we "
          "list the board under")
    for name in everyone:
        if got := found[name]["ats-disowns"]:
            print(f"   {name:22s} {got}")

    control = known(20)
    verified = measure([row for row, _ in control], "control: addresses we already hold")
    print(f"\n-- control: does an avenue that answers, answer RIGHT? ({len(control)} companies)")
    for avenue in AVENUES:
        agree = wrong = 0
        for row, address in control:
            got = verified[row["name"]][avenue]
            if not got:
                continue
            if registrable(_host(got)) == registrable(_host(address)):
                agree += 1
            else:
                wrong += 1
                print(f"   DISAGREES  {avenue:14s} {row['name']:22s} {got} vs {address}")
        print(f"   {avenue:14s} {agree} agree, {wrong} disagree")


if __name__ == "__main__":
    main()
