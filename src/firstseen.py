"""When we first saw a role, and whether we can honestly call it new — T15.2.

One field per role: the snapshot date its URL first appeared in a build. That
date is a sort ("Newest"), a badge, and the substrate the weekly alert of SPEC
v3's "Not a wall" will eventually stand on.

**The measurement this module exists to respect.** SPEC records, 2026-08-01: one
nightly diff of the whole corpus gave 0 new companies and 9 new roles, while 179
roles disappeared — of which 176 were companies the build could not check that
night, and only 3 had actually closed. A naive diff is ~98% noise, and the noise
is all of one shape: absence of knowledge read as a finding.

So this module splits every first sighting in two, and the split is the whole
design:

  * **confirmed** — the role's company was `listed` in the PREVIOUS snapshot and
    in this one. Both sides were genuinely observed, so a URL that was not there
    and now is really did appear. This is the only thing the page may badge.
  * **unconfirmed** — everything else. A company whose board we could not read
    last night has roles we are seeing for the first time and cannot date: they
    may have been open for a month. They get a first-seen date, because the date
    we first saw something is a fact about us and is always true, and they get no
    badge, because "new" would be a claim about the company.

The first snapshot that carries roles at all is the baseline, and nothing in it
is confirmed: there is no previous side to have observed. `advance` derives that
from the artifact rather than being told — an empty artifact can confirm nothing.

**And a third state, which the both-sides rule is blind to on its own: a night
when the build changed what it was looking for.** T15.2 measured it in this
project's own history — folding this function over 26 commits confirms 1,728
roles, of which 1,604 land on the night T8.4's fifteen-country radar reached a
nightly and 1,032 on the night T12.1 added 135 boards. Every one of those roles
was open the day before. The company was `listed` on both sides, both sides were
genuinely observed, and the rule says "new" because inside this artifact **a
definitional change is indistinguishable from a real one**.

Nothing in the artifact can tell them apart, so the build states it instead: the
report carries `definition` (`build.ROLE_DEFINITION`), the artifact carries the
one it was folded under, and **a snapshot may confirm only against a previous
snapshot built to the same definition**. A definition that is absent on either
side is not a match — a build that did not say what it was looking for cannot be
shown to have been looking for the same thing, and this module's whole job is to
refuse exactly that inference. The cost of getting it wrong is asymmetric and the
default follows the asymmetry: a spurious unconfirmed night loses a badge on a
handful of genuinely new roles, and a spurious confirmed night badges thousands
of week-old roles `New` on the front page.

The rule needs no history and no table of which builds changed the definition —
one string in tonight's report, one carried in last night's artifact.

**Closures are not here, deliberately.** A role that disappears is where 98% of
that measurement's noise lives, and the honest version of it needs the same
both-sides rule plus a policy for the 176. Out of scope; see TASKS.md T15.2.

**The nightly must never read git history, and this module cannot.** The refresh
runs under `actions/checkout@v4`, which fetches depth 1 — there is no history in
CI to read. Everything `advance` needs about yesterday comes out of the committed
artifact: every URL ever seen, and the set of companies genuinely observed at the
last snapshot. `scripts/first_seen_backfill.py` is the one and only thing that
reads git, it is a one-time hand run, and it works by folding THIS function over
the published history — so the backfill exercises the nightly's code path rather
than a second implementation of it.
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

#: Bump when the artifact's shape changes. `load` refuses a version it does not
#: know rather than reading fields that may have moved — the same rule the site
#: keeps against companies.json, for the same reason: this file outlives the
#: build that wrote it.
#:
#: T16.1 added `definition` and did NOT bump this, which is a decision rather than
#: an oversight. No field moved; the new one is optional, and its absence has a
#: defined meaning that is the conservative one — a v1 artifact confirms nothing
#: on the night this lands, which is exactly what the widening night needs. A bump
#: would make `load` refuse the committed artifact, and the only way out of that
#: is deleting 6,650 dates and re-backfilling them, which this module's own `load`
#: docstring names as the disaster to avoid.
SCHEMA_VERSION = 1

ARTIFACT = "data/first-seen.json"

#: Said in the file itself, not only here. The artifact is served to the page and
#: linked from the footer, so the rule that makes half its rows unbadgeable
#: travels with it.
NOTE = (
    "first_seen is the snapshot date a role's URL first appeared in a build. A "
    "role is confirmed only where its company's board was read on the previous "
    "snapshot AND on this one — both sides genuinely observed — AND both builds "
    "were looking for the same thing, which is what `definition` records. "
    "Everything else is unconfirmed: we saw it for the first time, which is not "
    "the same as it being new. Only confirmed roles may be called new."
)


def advance(
    prev: Mapping[str, Any] | None,
    published: Mapping[str, Any],
    report: Mapping[str, Any],
) -> dict[str, Any]:
    """Fold one snapshot into the artifact and return the new one.

    `published` is a companies.json document and `report` its build-report.json.
    `prev` is the artifact as it was committed, or None for the first run.

    Set once, never revised: a URL already in the artifact keeps the date it
    first carried. A role that vanishes for a week and comes back is not new — it
    is the same posting, and re-dating it would be exactly the closure inference
    this module refuses to make in the other direction.
    """
    snapshot = published["snapshot"]
    # The build report's own list of companies it actually read a board for.
    # `listed` is the only outcome that means that (src/outcomes.py); the other
    # six are absences of knowledge wearing different names.
    observed = set(report.get("listed") or ())
    before = set(prev.get("observed") or ()) if prev else set()
    # What tonight's build counted as a role, and what last night's did. Equal is
    # the only readable case, and equal-and-stated at that: two builds that both
    # declined to say are not two builds we know agreed.
    definition = report.get("definition")
    unchanged = bool(definition) and (prev or {}).get("definition") == definition
    dates: dict[str, dict[str, list[str]]] = {
        day: {kind: list(urls) for kind, urls in buckets.items()}
        for day, buckets in ((prev or {}).get("dates") or {}).items()
    }
    known = {url for buckets in dates.values() for urls in buckets.values() for url in urls}
    # ponytail: the artifact only ever grows — a URL that stops being published
    # keeps its date, because that is what stops a posting that vanished for a
    # week from coming back badged as new. 6,505 URLs is 494 KB beside a 3 MB
    # companies.json. Ceiling: if it ever approaches that file's size, drop URLs
    # absent for N snapshots and accept that one returning after N reads as new.
    # Do not prune before then — the saving is bytes and the cost is a false
    # claim, which is the trade this whole module exists to refuse.
    # The baseline. An artifact holding no URL at all has no previous side, so
    # nothing this snapshot shows can be a transition — not even for a company
    # `listed` on both, because "both" is one snapshot here. Derived from the
    # artifact rather than passed in: a caller cannot get this wrong by omission.
    baseline = not known

    for company in published["companies"]:
        # Three questions, and a role is confirmed only on three yeses: was there
        # a previous snapshot at all, was it looking for the same thing, and did
        # we genuinely read THIS company's board on both sides of the gap.
        both_sides = (
            not baseline
            and unchanged
            and company["name"] in observed
            and company["name"] in before
        )
        # `.get` rather than `[...]`: the backfill folds over schema v1–v3 too,
        # and a role was not a thing this project published until v4 (T4.1). A
        # snapshot with no roles contributes no URLs and is not an error.
        for role in company.get("roles") or ():
            url = role["url"]
            if url in known:
                continue
            known.add(url)
            day = dates.setdefault(snapshot, {"confirmed": [], "unconfirmed": []})
            day["confirmed" if both_sides else "unconfirmed"].append(url)

    return {
        "schema_version": SCHEMA_VERSION,
        "snapshot": snapshot,
        "note": NOTE,
        # Carried forward because the nightly has no other way to know it. This
        # is the "previous side" of tomorrow's both-sides rule, and dropping it
        # would silently make every tomorrow a baseline.
        "observed": sorted(observed),
        # The other half of the previous side, and the one that survives a build
        # changing its mind about what a role is. Written even when it is None:
        # an artifact that states no definition is a real state, it is what every
        # artifact written before T16.1 says, and it confirms nothing.
        "definition": definition,
        "dates": {day: {k: sorted(v) for k, v in dates[day].items()} for day in sorted(dates)},
    }


def load(path: str | Path = ARTIFACT) -> dict[str, Any] | None:
    """Read the committed artifact, or None if there isn't one yet.

    A file that exists and cannot be read raises rather than resolving to None.
    Treating a corrupt artifact as absent would restart the baseline: every role
    on the site re-dated to today and the whole register unbadgeable. Dying
    leaves yesterday's file committed and untouched, which is the rule
    `build.write` already keeps.
    """
    file = Path(path)
    if not file.exists():
        return None
    art: dict[str, Any] = json.loads(file.read_text())
    if art.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(
            f"{file} is v{art.get('schema_version')}; this module writes "
            f"v{SCHEMA_VERSION}. Nothing written — delete it to re-backfill."
        )
    return art


def write(path: str | Path, art: Mapping[str, Any]) -> None:
    """Emit the artifact. indent=2 like every other file in data/: the nightly
    commits this, and a one-line JSON diff says nothing about what changed."""
    Path(path).write_text(json.dumps(art, indent=2) + "\n")


def main() -> None:
    """The nightly's step. Reads today's build off disk, folds it into the
    committed artifact, writes it back. No arguments and no git."""
    published = json.loads(Path("data/companies.json").read_text())
    report = json.loads(Path("data/build-report.json").read_text())
    # Held rather than re-read after the write, which would compare the new file
    # with itself and never print the one line this exists to print.
    prev = load()
    art = advance(prev, published, report)
    write(ARTIFACT, art)
    # The date's whole bucket, not this run's delta: two builds on one day are
    # one day's worth of first sightings, and the bucket is what the page reads.
    today = art["dates"].get(art["snapshot"], {})
    print(
        f"first-seen: roles first seen on {art['snapshot']} — "
        f"{len(today.get('confirmed', ()))} confirmed new, "
        f"{len(today.get('unconfirmed', ()))} unconfirmed"
    )
    # Said out loud on the night it happens, because a run that confirms nothing
    # looks identical to a quiet night in the numbers above and is not one.
    if prev is not None and art["definition"] != (was := prev.get("definition")):
        print(
            f"first-seen: this build counted roles as {art['definition']!r} and the "
            f"last one as {was!r} — nothing tonight can be confirmed, because a "
            f"change in what the build looks for is not anybody hiring"
        )


if __name__ == "__main__":
    main()
