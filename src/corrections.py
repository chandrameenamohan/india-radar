"""The human's answer about a corpus row — T10.1.

A source can be wrong about a company in a way no other source contradicts, so
nothing in the pipeline can find it: CB Insights links a trade publication as
Cresta's website, and files Monzo under the name they dropped in 2016. Both were
found the only way they can be — a person reading the company's own site.

This is where that reading lands, for the same reason `data/overrides.yaml`
exists: a correction applied in code is a correction with no room for the reason
it was made, and an unexplained one is undeletable a year later.

Deliberately NOT a place to hide a derivation. Two companies whose careers pages
lead to one board are found by the build itself (`build.shared_boards`), and a
hand-written list of those would rot the night one of them moves. What belongs
here is only what no run can observe: an acquisition, a rename, an address a
publisher got wrong.
"""
from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import NamedTuple

#: ponytail: the same one-regex read as `slugs.OVERRIDES`, and the same ceiling —
#: everything else YAML can express is REJECTED, loudly, rather than half-read.
#: Upgrade path is that file's: `pip install pyyaml`, delete both regexes.
CORRECTIONS = Path("data/corrections.yaml")
_ENTRY = re.compile(r"^(.+?)\s*:\s*(website|board)\s+(\S.*)$")


class Corrections(NamedTuple):
    websites: dict[str, str]  # name -> the address the corpus should carry
    boards: dict[str, str]  # name -> the company whose board this name's page links


def parse(text: str) -> Corrections:
    """The corrections file, or an error naming the line we could not read.

    Strict for the reason `slugs.parse_overrides` is: a hand-edited file fails by
    parsing into something subtly other than what was meant, and every one of
    those ends as a wrong fact on the site rather than as a crash.
    """
    websites: dict[str, str] = {}
    boards: dict[str, str] = {}
    for number, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        entry = _ENTRY.match(raw.split(" #")[0].strip())
        if not entry:
            raise ValueError(
                f"corrections file line {number}: expected "
                f"'<company>: website <url>' or '<company>: board <company>', got {raw!r}"
            )
        name, directive, value = entry.groups()
        if directive == "website":
            if not value.startswith(("http://", "https://")):
                raise ValueError(
                    f"corrections file line {number}: website {value!r} is not an http(s) URL"
                )
            websites[name] = value
        else:
            boards[name] = value
    return Corrections(websites, boards)


def load(path: str | Path = CORRECTIONS) -> Corrections:
    """The corrections file, parsed. Not guarded against a missing file: it is
    committed, and a run that quietly proceeded without it would republish the
    wrong facts it exists to correct."""
    return parse(Path(path).read_text())


def check(names: Iterable[str], corrections: Mapping[str, str], directive: str) -> None:
    """Raise unless every correction here still names a company in the corpus.

    The corpus is rebuilt from live sources, so a company can leave it — and a
    correction for a company that has gone is not harmless. It is a line that
    reads as maintained, in a file whose whole value is that a human checked
    each entry. The same rule as a dead slug override, for the same reason.
    """
    if stale := sorted(set(corrections) - set(names)):
        raise ValueError(
            f"{CORRECTIONS}: {directive} correction(s) for {stale}, who are not in the corpus. "
            f"A correction nothing applies to is a claim nobody is checking any more — "
            f"delete the line, or find out what the company is called now."
        )
