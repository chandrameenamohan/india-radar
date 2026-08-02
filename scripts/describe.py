#!/usr/bin/env python3
"""Write a description for every listed company that hasn't got one — T8.7's delta.

The descriptions on the site are read off each company's OWN website by an agent
with a fetch tool, and marked AI-SUMMARIZED where they render. This is the part
that was always missing: a company newly listed by a rebuild carries no
description, and nothing generated one.

Run: .venv/bin/python scripts/describe.py [--limit N] [--dry-run]

AUTH. `claude-agent-sdk` is the Claude Code harness as a library, so it takes the
same credential Claude Code does: `CLAUDE_CODE_OAUTH_TOKEN` in the environment,
no ANTHROPIC_API_KEY anywhere. Measured 2026-08-02, and the distinction is the
whole reason this is an agent rather than an API call: that token authenticates
against the raw Messages API too, but there it is throttled to Haiku (Opus and
Sonnet both answer 429). Through this path Opus answers.

WHY AN AGENT AND NOT A COMPLETION. The job is "open their site and see what they
say", which is a fetch and a judgement, not a generation. It is also the only
reason the omissions are honest: a model asked to describe `Insider` from its own
weights will describe SOMETHING, and be fluent about it.

ponytail: no cache and no resume. A run that dies re-describes what it had done,
which costs a fetch per company on a delta that is normally single digits.
Ceiling: the full-corpus regeneration (~300), where a resume file would earn its
keep — write the merge after each company rather than at the end.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import corrections  # noqa: E402 — after the path insert above

COMPANIES = ROOT / "data/companies.json"
CORPUS = ROOT / "data/corpus.json"
DESCRIPTIONS = ROOT / "data/descriptions.json"
#: The audit's verdicts, one json object per line, appended as they land. In
#: logs/ rather than data/ because it is a work list for a human, not something
#: the site reads — and because re-running is meant to resume from it.
AUDIT_LOG = ROOT / "logs/description-audit.jsonl"

#: Four at once. The previous hand-run pass used six writer agents and finished
#: comfortably; four is that with room for the fetch timeouts, and the delta is
#: normally small enough that the number never matters.
WORKERS = 4

#: The whole task, and every rule that makes an omission honest. Written at the
#: length it is because each sentence here is a failure that happened in the hand
#: pass: a description read off a trade publication that had written about the
#: company, marketing copy pasted back as fact, and a fluent paragraph about a
#: company whose site never loaded.
BRIEF = """\
Write a three-line description of the company below for a job-seeker's index of
funded companies that are hiring.

Company: {name}
Their website, as our sources state it: {website}
The job board we publish their roles from states: {board}
Roles open on it right now: {roles}

Open that website and read it. If the address 404s, is parked, is a holding page,
or belongs to somebody else (a trade publication that wrote about them, a
directory listing), say so and stop — do not describe the company from memory,
and do not go looking for another source. A missing description is fine. A
confident wrong one is not.

Then check the website against the board before you answer. The board is what
this site publishes, so a website that cannot be the same company as the board is
the website being wrong, not the board — omit, and say what each one was. This
is not a style test: a company can hire for anything, and a name can be a
coincidence. It is a contradiction test. A finance coaching programme whose board
is hiring a Business Reporter is two companies sharing a word.

Answer with ONE json object and nothing else:

  {{"what": "...", "for_whom": "...", "why_them": "..."}}

  what      what the product IS, 5-9 words, e.g. "A password manager for people
            and companies"
  for_whom  who buys or uses it, 5-9 words, e.g. "Individuals and company IT
            security teams"
  why_them  5-9 words, and the hard one. It must be a CONCRETE FACT THE SITE
            ITSELF STATES — a named customer, a number they publish, a capability
            they claim in those words. Not a superlative, a ranking, a market
            position or a comparison against competitors unless the site says it.
            "Tens of millions of developers use it" is only allowed if the site
            says so; "the default X of the internet" is never allowed. If the
            site gives you nothing concrete, write what it does say plainly —
            a thin true line beats an impressive invented one.

Or, if you could not verify it from their own site:

  {{"omit": "one line saying what you found instead"}}

Plain sentence case, no trailing full stop, no marketing language, no company
name repeated inside the lines. Their own words are evidence of what they sell,
never of whether it is good.
"""

#: The audit (T10.3). Same reading, opposite direction: the description already
#: exists and the question is whether it describes the company whose board we
#: publish. Deliberately does NOT ask for a better description — a pass that
#: rewrites 314 rows to fix 2 is a pass that churns 312 hand-checked ones.
AUDIT = """\
Check whether an existing description belongs to the company whose job board we
publish. This is a verification task. Do not write a replacement.

Company as we list it: {name}
Their website, as our sources state it: {website}
The job board we publish their roles from states: {board}
Roles open on it right now: {roles}

The description we currently publish:
  what      {what}
  for_whom  {for_whom}
  why_them  {why_them}

Open the website and read it. Then answer with ONE json object and nothing else:

  {{"verdict": "ok"}}
      the site is this company, and the description matches what the site says

  {{"verdict": "wrong_company", "why": "..."}}
      the website and the board cannot be the same company — a name collision, an
      acquirer, a trade publication, a parked domain. Say what each one was.

  {{"verdict": "wrong_description", "why": "..."}}
      the site IS the right company, but the description says something the site
      does not support

  {{"verdict": "unreadable", "why": "..."}}
      the site would not load, so you are not able to judge either way

Two things are NOT faults. A company can hire for anything, so a role title that
merely looks unrelated to the product is not a contradiction — only an
impossibility is. And a description that is thinner or blander than the site is
still accurate; you are checking truth, not quality.
"""

OPTIONS = ClaudeAgentOptions(
    model="opus",
    # The fetch, and nothing else. No file tools: this agent reads the web and
    # returns text, and the merge into descriptions.json is this script's job —
    # an agent that could write the file could write it wrong.
    allowed_tools=["WebFetch"],
    # Not the claude_code preset: that one is briefed to be a coding agent in a
    # repository, which is the wrong instincts entirely for reading a homepage.
    system_prompt=(
        "You read a company's own website and say plainly what they do. "
        "You would rather return nothing than return something you cannot see on "
        "their site."
    ),
    # Reproducible in CI: no CLAUDE.md, no user settings, no project permissions
    # leaking into what this agent believes it is doing.
    setting_sources=[],
    # Measured: 6 was too few and the SDK raises rather than returning what it
    # had, so a company whose site redirects twice killed the whole run. The
    # audit is the expensive direction — fetch, then compare against a board —
    # and 12 covers it. The bound stays because an agent that cannot answer in a
    # dozen turns is one whose answer we would not trust anyway.
    max_turns=12,
)


def websites() -> dict[str, str]:
    """Every corpus company's address, which is where the reading starts.

    companies.json carries no website — it carries the funding source_url, and
    handing an agent a FinSMEs article about a funding round is how the hand pass
    produced a description of the wrong company.

    `data/corrections.yaml` wins, and reading it HERE rather than trusting
    corpus.json matters: those corrections are applied by `src.corpus`, which the
    nightly does not run, so a hand-corrected address does not reach corpus.json
    until somebody rebuilds it. Without this the audit would keep re-reading the
    very address a human has already written down as wrong.
    """
    corpus = json.loads(CORPUS.read_text())["companies"]
    stated = {c["name"]: c["website"] for c in corpus if c.get("website")}
    return {**stated, **corrections.load().websites}


def answer(text: str) -> dict[str, str] | None:
    """The json object out of the agent's reply, or None if it wrote prose.

    Tolerant of a fenced block because that is what a model does when asked for
    json, and strict about nothing else: a reply this cannot read is a company
    left undescribed, which is a state the site already renders.
    """
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        found = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return found if isinstance(found, dict) else None


async def describe(name: str, row: dict) -> tuple[str, dict[str, str] | None]:
    """One company, read off its own site and checked against its board.

    Both halves are load-bearing, and the second one is what the hand pass had a
    human doing implicitly. Measured on the first run of this script: `Insider`'s
    corpus website is a finance coaching programme and its board is Business
    Insider's, hiring a Business Reporter. The site had been publishing one
    company's role under another's name, and the website alone reads clean.
    """
    said = []
    brief = BRIEF.format(
        name=name,
        website=row["website"],
        board=f"{row['ats']}/{row['slug']}",
        roles=", ".join(r["title"] for r in row["roles"][:8]) or "none",
    )
    async for message in query(prompt=brief, options=OPTIONS):
        if isinstance(message, AssistantMessage):
            said += [b.text for b in message.content if isinstance(b, TextBlock)]

    found = answer("\n".join(said))
    if not found or "omit" in found:
        print(f"  OMIT   {name}: {(found or {}).get('omit', 'no readable answer')}")
        return name, None
    lines = ("what", "for_whom", "why_them")
    if not all(isinstance(found.get(f), str) and found[f] for f in lines):
        print(f"  OMIT   {name}: answered without all three lines")
        return name, None
    print(f"  WROTE  {name}: {found['what']}")
    # `ai: true` is the flag the site renders AI-SUMMARIZED from. Set here, for
    # every row this writes, because there is no other kind of row it can write.
    return name, {
        "what": found["what"],
        "for_whom": found["for_whom"],
        "why_them": found["why_them"],
        "ai": True,
    }


async def audit(name: str, row: dict, said: dict[str, str]) -> dict[str, str]:
    """One published description, checked against the site and the board."""
    replies = []
    brief = AUDIT.format(
        name=name,
        website=row["website"],
        board=f"{row['ats']}/{row['slug']}",
        roles=", ".join(r["title"] for r in row["roles"][:8]) or "none",
        **{f: said.get(f, "") for f in ("what", "for_whom", "why_them")},
    )
    async for message in query(prompt=brief, options=OPTIONS):
        if isinstance(message, AssistantMessage):
            replies += [b.text for b in message.content if isinstance(b, TextBlock)]

    found = answer("\n".join(replies)) or {}
    verdict = found.get("verdict", "unreadable")
    if verdict not in ("ok", "wrong_company", "wrong_description", "unreadable"):
        verdict = "unreadable"
    return {"name": name, "verdict": verdict, "why": str(found.get("why", ""))[:400]}


async def run_audit(rows: dict[str, dict], described: dict, workers: int) -> None:
    """Audit every row, writing each verdict as it lands.

    Appended per company rather than collected and written at the end, because at
    314 companies a run that dies at 300 would otherwise have cost an hour and
    produced nothing. Re-running skips what the file already holds.
    """
    limit = asyncio.Semaphore(workers)
    done = 0

    async def one(name: str, row: dict) -> None:
        nonlocal done
        async with limit:
            try:
                found = await audit(name, row, described[name])
            except Exception as broke:  # noqa: BLE001 — one company, not the run
                # 270 companies is long enough that one failure must not cost the
                # other 269. Recorded as `error`, NOT as `unreadable`: the two
                # look alike in a log and mean opposite things. `unreadable` is
                # the agent's judgement about a site; `error` is our harness
                # falling over — measured, six concurrent CLIs alongside a full
                # build produce a handful. Only `error` rows are retried on a
                # re-run, so a transient never hardens into a verdict.
                found = {"name": name, "verdict": "error", "why": f"{broke}"[:200]}
        done += 1
        with AUDIT_LOG.open("a") as log:
            log.write(json.dumps(found) + "\n")
        mark = "ok   " if found["verdict"] == "ok" else found["verdict"].upper()
        print(f"  [{done:3d}/{len(rows)}] {mark:18s} {name}"
              + (f" — {found['why'][:100]}" if found["verdict"] != "ok" else ""), flush=True)

    await asyncio.gather(*(one(n, r) for n, r in rows.items()))


async def run(delta: dict[str, dict], workers: int) -> dict[str, dict[str, str]]:
    limit = asyncio.Semaphore(workers)

    async def one(name: str, row: dict) -> tuple[str, dict[str, str] | None]:
        async with limit:
            return await describe(name, row)

    done = await asyncio.gather(*(one(n, r) for n, r in delta.items()))
    return {name: found for name, found in done if found}


def verdicts() -> dict[str, str]:
    """The audit's latest verdict per company. Last row wins, for `report`'s
    reason: the log is append-only, so a company retried after a harness `error`
    carries two rows and only the second one happened."""
    if not AUDIT_LOG.exists():
        return {}
    rows = [json.loads(line) for line in AUDIT_LOG.read_text().splitlines() if line.strip()]
    return {row["name"]: row["verdict"] for row in rows}


def mark(described: dict[str, dict], latest: dict[str, str]) -> dict[str, dict]:
    """descriptions.json with the audit's verdicts folded in as one field — T10.5.

    `checked: true` is the site's licence to say a description was verified, and
    it means exactly one thing: the audit opened this company's own website, read
    it against the board we publish their roles from, and found no contradiction.
    Nothing weaker qualifies. A description regenerated after a
    `wrong_description` verdict was written under the same check but never
    re-audited, and an `unreadable` site is a site nobody has read — both stay
    unverified, which is a work list rather than a claim.

    A company the corpus holds no address for cannot be audited at all, and 45
    listed rows were in that state when this field was added — 45 descriptions
    the site published in exactly the same voice as the 245 somebody had read.
    T10.5's two new sources took that to 14, and the audit then ran over the 32
    it had freed. The field is what tells the rest apart from them.

    Removed, not set false, where the verdict does not qualify: absence is the
    absence this file already renders, and a stale `checked: true` surviving a
    re-audit is the one failure this cannot have.
    """
    return {
        name: {**said, "checked": True}
        if latest.get(name) == "ok"
        else {field: value for field, value in said.items() if field != "checked"}
        for name, said in described.items()
    }


def audited() -> set[str]:
    """Companies the audit log already holds a real verdict for.

    An `error` row is not a verdict — it is our harness having fallen over — so
    a re-run picks those companies up again. Every other row is skipped, which is
    what makes a 270-company run resumable rather than restartable.
    """
    if not AUDIT_LOG.exists():
        return set()
    rows = [json.loads(line) for line in AUDIT_LOG.read_text().splitlines() if line.strip()]
    return {row["name"] for row in rows if row["verdict"] != "error"}


def report() -> int:
    """The audit's findings, worst first. Prints nothing reassuring about `ok`
    beyond its count — the point of the file is the rows that are not."""
    # Last row per company wins. The log is append-only, so a company retried
    # after a harness `error` has two rows, and counting both would report a
    # failure that has since been resolved.
    latest = {
        json.loads(line)["name"]: json.loads(line)
        for line in AUDIT_LOG.read_text().splitlines()
        if line.strip()
    }
    verdicts = list(latest.values())
    counts: dict[str, int] = {}
    for found in verdicts:
        counts[found["verdict"]] = counts.get(found["verdict"], 0) + 1
    print(f"\n{len(verdicts)} audited: " + ", ".join(f"{n} {v}" for v, n in sorted(counts.items())))
    for kind in ("wrong_company", "wrong_description", "unreadable", "error"):
        flagged = [f for f in verdicts if f["verdict"] == kind]
        for found in sorted(flagged, key=lambda f: f["name"]):
            print(f"\n  {kind.upper()}  {found['name']}\n    {found['why']}")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, help="handle at most N companies")
    parser.add_argument("--dry-run", action="store_true", help="print the delta and stop")
    parser.add_argument("--audit", action="store_true", help="check the descriptions we publish")
    parser.add_argument("--report", action="store_true", help="summarise the audit log and stop")
    parser.add_argument("--workers", type=int, default=WORKERS, help="concurrent agents")
    args = parser.parse_args(argv)

    if args.report:
        return report()

    listed = {c["name"]: c for c in json.loads(COMPANIES.read_text())["companies"]}
    described = json.loads(DESCRIPTIONS.read_text())
    addresses = websites()

    if args.audit:
        # Only rows the site actually publishes, and only ones with an address to
        # read: a description we cannot check is not a description we can fault.
        done = audited()
        rows = {
            name: {**row, "website": addresses[name]}
            for name, row in listed.items()
            if name in described and name in addresses and name not in done
        }
        if args.limit:
            rows = dict(list(rows.items())[: args.limit])
        print(f"{len(listed)} listed, {len(done)} already audited, {len(rows)} to check")
        if rows and not args.dry_run:
            asyncio.run(run_audit(rows, described, args.workers))
        if not AUDIT_LOG.exists():
            return 0
        # The verdicts, written back into the file the site reads (T10.5). Done
        # on every audit invocation rather than only on one that ran agents:
        # marking is a fold over the log, so a completed audit can refresh the
        # flags without spending a single fetch to do it.
        marked = mark(json.loads(DESCRIPTIONS.read_text()), verdicts())
        DESCRIPTIONS.write_text(json.dumps(marked, indent=1) + "\n")
        checked = sum(1 for said in marked.values() if said.get("checked"))
        print(f"{checked} of {len(marked)} descriptions verified against their own site "
              f"and their board -> {DESCRIPTIONS}")
        return report()

    # A company with no address is not a company we can read, so it is not part
    # of the delta — it is counted and named, the way every other absence here is.
    delta = {
        name: {**row, "website": addresses[name]}
        for name, row in listed.items()
        if name not in described and name in addresses
    }
    if blind := [n for n in listed if n not in described and n not in addresses]:
        print(f"{len(blind)} listed with no website to read: {', '.join(sorted(blind))}")
    if args.limit:
        delta = dict(list(delta.items())[: args.limit])

    print(f"{len(listed)} listed, {len(described)} described, {len(delta)} to write")
    if not delta or args.dry_run:
        return 0

    written = asyncio.run(run(delta, args.workers))
    # Merged, never replaced: the file holds hand-checked entries and entries for
    # companies this build did not list, and a regeneration is not a reason to
    # drop either.
    DESCRIPTIONS.write_text(json.dumps({**described, **written}, indent=1) + "\n")
    print(f"{len(written)} written, {len(delta) - len(written)} omitted -> {DESCRIPTIONS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
