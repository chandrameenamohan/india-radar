# ROLE·ATLAS

**Funded software companies that are hiring right now, proven by their own job
board — not by a claim.**

A static site: one `data/companies.json`, vanilla JS, no backend, no database,
published on GitHub Pages. A company appears only if it (a) is a software company
that has raised roughly Series A or more, and (b) had at least one open role in
one of fifteen target countries on its own ATS at build time. HQ may be anywhere.

Fifteen countries: India · United Kingdom · Ireland · Germany · Netherlands ·
France · Spain · Sweden · Denmark · Norway · Finland · Japan · Singapore ·
Australia · New Zealand.

The build is stateless — each run recomputes the whole site from live sources.
A company that stops hiring simply stops appearing. A company we could not check
is left off and counted as unchecked in the footer, never shown as not hiring.

> The site shipped as **INDIA·RADAR** while the radar was one country wide.
> Renaming the GitHub repo and the Pages URL to match ROLE·ATLAS is a human
> action, still to be done.

## Running it

```
./init.sh              # create .venv and install
make check             # the gate: lint, typecheck, unit, e2e
scripts/nightly.sh     # full build; commits on success, never pushes
.venv/bin/python -m src.build --smoke   # offline build against fixtures
```

`make check` is the only definition of green — the pre-commit hook, the Stop hook
and `ralph.sh` all call it and nothing else. See `VERIFICATION.md` for what each
layer is allowed to prove, `SPEC.md` for the features and their acceptances, and
`TASKS.md` for the build order.
