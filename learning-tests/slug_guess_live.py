#!/usr/bin/env python3
"""INTEGRATION CHECK for T2.2 — slug guessing against live Greenhouse.

Lives here rather than in tests/ for the reason VERIFICATION.md gives: `make
check` must not go red because somebody else's API is down. Re-run on demand:

    .venv/bin/python learning-tests/slug_guess_live.py

Two parts. The first is the DoD's check — combined resolution on the 8-company
fixture, strictly above careers-page alone, with Anthropic and Glean coming back
through guessing. The second is the measurement the implementation was sized on:
which name variants ever find a board, and how often a board that answers turns
out to belong to somebody else.
"""
from __future__ import annotations

import json
import random
import re
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.greenhouse import board_name  # noqa: E402
from src.slugs import guess, key, resolve, resolve_all, states_company  # noqa: E402

#: The 7 companies T2.1 measured, plus Notion. Anthropic and Glean are the two
#: the DoD names: both genuinely on Greenhouse, both invisible to a careers-page
#: regex — Anthropic's board lives a page deeper, Glean's listing is JS-rendered.
FIXTURE = ["Anthropic", "Figma", "Ramp", "Vercel", "Razorpay", "Glean", "Postman", "Notion"]


def section(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


section("1. the DoD: combined rate on the 8-company fixture > careers-page alone")

started = time.time()
careers_page = {name: slug for name in FIXTURE if not isinstance(slug := resolve(name), str)}
combined = resolve_all(FIXTURE)
elapsed = time.time() - started

for name in FIXTURE:
    slug = combined.resolved.get(name)
    got = f"{slug['ats']}/{slug['slug']} ({slug['method']})" if slug else combined.unresolved[name]
    print(f"  {name:12s} {got}")

print(f"\n  careers-page alone : {len(careers_page)}/{len(FIXTURE)}")
print(f"  combined           : {len(combined.resolved)}/{len(FIXTURE)}  {dict(combined.methods)}")
print(f"  {elapsed:.0f}s for {len(FIXTURE)} companies")

assert combined.rate > len(careers_page) / len(FIXTURE), "guessing added nothing"
assert set(careers_page) <= set(combined.resolved), "guessing lost a careers-page resolution"
for named in ("Anthropic", "Glean"):
    assert named in combined.resolved, f"{named} is on Greenhouse and must resolve"
print("  PASS")

section("2. what the candidate list and the name check were sized on")

#: Every variant considered, including the four dropped. `first-word` is the
#: dangerous one and the reason `states_company` exists.
VARIANTS = {
    "plain": lambda w: "".join(w),
    "hyphen": lambda w: "-".join(w),
    "first-word": lambda w: w[0],
    **{
        suffix: (lambda w, s=suffix: "".join(w) + s)
        for suffix in ("hq", "work", "ai", "inc", "labs", "io", "jobs", "careers")
    },
}

corpus = json.loads(Path("data/corpus.json").read_text())["companies"]
sample = random.Random(11).sample([c["name"] for c in corpus], 60)

found: Counter[str] = Counter()
verified: Counter[str] = Counter()
wrong: list[tuple[str, str, str]] = []
started = time.time()
for name in sample:
    words = re.sub(r"[^a-z0-9]+", " ", name.casefold()).split()
    for variant, build in VARIANTS.items():
        slug = build(words)
        if slug == key(name) and variant != "plain":
            continue  # one-word names collapse every variant onto `plain`
        if (board := board_name(slug)) is None:
            continue
        found[variant] += 1
        if states_company(board, name):
            verified[variant] += 1
        else:
            wrong.append((name, slug, board))

print(f"  {len(sample)} companies x {len(VARIANTS)} variants in {time.time() - started:.0f}s")
print(f"  boards found     : {dict(found)}")
print(f"  name-verified    : {dict(verified)}")
print("  a board that answered and named somebody else:")
for name, slug, board in wrong:
    print(f"    {name!r} -> greenhouse/{slug} board says {board!r}")

section("3. and what all that costs on the real corpus")

names = [c["name"] for c in corpus]
started = time.time()
guessed = [name for name in random.Random(3).sample(names, 20) if guess(name)]
per_company = (time.time() - started) / 20
print(f"  {per_company:.1f}s/company sequential; {len(guessed)}/20 of the corpus resolves by guess")
print(f"  {len(names)} companies -> ~{len(names) * per_company / 60 / 8:.0f} min at 8 workers")
