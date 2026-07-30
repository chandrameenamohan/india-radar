"""The corpus record — the contract every E1 funding source emits.

Moved out of src/finsmes.py during the craft review (workflow step 7.5).
It lived there because FinSMEs was the first source built, and its own
docstring said so: "defined here with the first of them". Five other sources
then imported it, so `from src.finsmes import Record` in yc.py read as though
YC depended on FinSMEs. It does not. A shared contract should not be named
after whichever implementation happened to arrive first.

Behaviour is unchanged; this is a move and a re-export.
"""

from __future__ import annotations

from typing import TypedDict


class Record(TypedDict):
    """What one corpus source found out about one company — the shared contract
    every E1 source emits, defined here with the first of them.

    Everything but the name and the source URL is optional, because the sources
    genuinely differ in what they state: a FinSMEs headline gives an amount and a
    date but never a stage, YC's directory gives a stage but never an amount or a
    round date. An absent field is absent, never guessed — T1.5 decides what each
    absence disqualifies."""

    name: str
    amount: int | None
    currency: str | None
    date: str | None  # ISO, YYYY-MM-DD; None when the source states no round date
    round_letter: str | None
    source_url: str
    stage: str | None  # a source's own funding-stage label, e.g. YC's "growth"
    website: str | None  # the company's own address; None until T1.6 finds one
