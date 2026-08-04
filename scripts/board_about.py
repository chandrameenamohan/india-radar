#!/usr/bin/env python3
"""Print what a company says about itself on its OWN job board.

WHY THIS EXISTS. `scripts/describe.py` reads a company's website, and six listed
companies serve none we can read: openai.com and blitzy.com answer 403 to every
path, getparker.com 404s, sorare.com serves a browser-compatibility gate whose
only readable text is a tagline, theathletic.com refuses the fetcher, and Super's
recorded website is a different company altogether. They were blank for it, and
OpenAI — 135 published roles, the largest board in the register — read as a
company nobody could describe.

Their boards describe them plainly, and the board is not a fallback to hearsay:
it is the source this whole register rests on ("proven by their own job board").
Every posting on it is the company's own copy.

WHAT IT IS NOT. This prints text; it does not write descriptions. The three lines
in data/descriptions.json were summarised from what this prints, and marked
`"source": "board"` so the page says `read from their own job board` rather than
claiming a website was checked. Run it to check those summaries against the
source — that is the entire point of it being a script rather than a session.

    python3 scripts/board_about.py OpenAI
    python3 scripts/board_about.py            # every board-sourced company

A posting describes a TEAM as readily as a company, so the company-level section
is what to read: "About <Company>" / "About us". Where a board carries none, the
opening paragraph is printed instead and is worth more scepticism — Parker and
Sorare are both in that state.
"""

from __future__ import annotations

import html
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPANIES = ROOT / "data/companies.json"
DESCRIPTIONS = ROOT / "data/descriptions.json"
UA = {"User-Agent": "roleatlas/1.0 (+https://roleatlas.sennamind.com)"}

# Six postings is plenty: boilerplate repeats, and a board with 737 of them
# (OpenAI) takes minutes to walk in full for text that is identical after the
# first. Measured 2026-08-04 — 6 of 6 carried the section on every board that
# has one at all.
SAMPLE = 6


def fetch(url: str, timeout: int = 45) -> str:
    return urllib.request.urlopen(
        urllib.request.Request(url, headers=UA), timeout=timeout
    ).read().decode()


def plain(markup: str | None) -> str:
    """Tags out, entities out, whitespace collapsed. Never innerHTML anywhere."""
    return re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", html.unescape(markup or ""))).strip()


def postings(ats: str, slug: str) -> list[str]:
    """A sample of posting bodies, as plain text, from the company's own board."""
    if ats == "ashby":
        board = json.loads(fetch(f"https://api.ashbyhq.com/posting-api/job-board/{slug}"))
        return [plain(j.get("descriptionHtml")) for j in board.get("jobs", [])[:SAMPLE]]
    if ats == "greenhouse":
        # The list endpoint takes `content=true`, but for an 80-role board that is
        # one very large response; per-job is slower to write and faster to run.
        listing = json.loads(
            fetch(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs")
        )["jobs"][:SAMPLE]
        out = []
        for job in listing:
            try:
                one = json.loads(
                    fetch(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{job['id']}")
                )
            except Exception:
                continue  # one unreadable posting is not a company we cannot read
            out.append(plain(one.get("content")))
        return out
    if ats == "lever":
        board = json.loads(fetch(f"https://api.lever.co/v0/postings/{slug}?mode=json"))[:SAMPLE]
        return [
            plain(
                (p.get("descriptionPlain") or "")
                + " "
                + " ".join(
                    (s.get("text") or "") + " " + plain(s.get("content"))
                    for s in p.get("lists", [])
                )
            )
            for p in board
        ]
    raise SystemExit(f"unknown ats: {ats}")


def about(name: str, bodies: list[str]) -> tuple[str, bool]:
    """The company-level section, and whether one was actually found."""
    first = re.escape(name.split()[0])
    pattern = re.compile(rf"(About (?:us|the company|{first})\b.{{120,1200}})", re.I | re.S)
    for body in bodies:
        found = pattern.search(body)
        if found:
            return found.group(1), True
    return (bodies[0][:900] if bodies else "(no postings on this board)"), False


def main(argv: list[str]) -> int:
    listed = {c["name"]: c for c in json.loads(COMPANIES.read_text())["companies"]}
    described = json.loads(DESCRIPTIONS.read_text())

    wanted = argv or [
        name
        for name, row in described.items()
        if row.get("source") == "board" and name in listed
    ]
    for name in wanted:
        company = listed.get(name)
        if not company:
            print(f"\n===== {name} — not listed in this build =====")
            continue
        print(f"\n===== {name}  ({company['ats']}/{company['slug']}) =====", flush=True)
        try:
            bodies = [b for b in postings(company["ats"], company["slug"]) if b]
        except Exception as error:  # a board that will not answer is a finding
            print(f"  board unreadable: {type(error).__name__}: {error}")
            continue
        text, company_level = about(name, bodies)
        mark = "About section" if company_level else "OPENING PARAGRAPH — no About section"
        print(f"  {len(bodies)} postings sampled · {mark}\n")
        print(f"  {text[:1100]}\n")
        row = described.get(name, {})
        if row:
            print(f"  published: what      — {row.get('what')}")
            print(f"             for whom  — {row.get('for_whom')}")
            print(f"             why them  — {row.get('why_them')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
