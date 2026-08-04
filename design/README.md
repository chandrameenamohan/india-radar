# The design harness

Fifteen variants of the ROLE·ATLAS page, built and graded by separate agents,
none of them deleted. Structure follows Anthropic's harness-design writeup:
planner / generator / evaluator, with the generator never grading itself.

## Files

| | |
|---|---|
| `BRIEF.md` | what to build — the three flows and the doctrine |
| `CRITERIA.md` | how a variant is graded, and the calibration anchors |
| `GENERATOR.md` | the builder's standing instructions |
| `EVALUATOR.md` | the grader's standing instructions |
| `SCORES.md` | the ledger, append-only, one row per variant |
| `gallery.py` | rebuilds `gallery.html` by scanning the directory |
| `serve.sh` | static server on **8732** (8731 and 8788 are the test gate's) |
| `iterations/<id>/` | `index.html` · `NOTES.md` · `SCORE.md` |

## Look at them

```bash
bash design/serve.sh
open http://127.0.0.1:8732/design/gallery.html
```

The gallery links every variant, live and interactive, with its score. Rerun
`python3 design/gallery.py` after any round to pick up new work.

Each variant is a **complete self-contained page** reading the corpus through
`iterations/data`, a symlink that makes the original's `../data/…` paths resolve
one directory deeper.

**It points at `design/fixture/`, a pinned snapshot, and that is deliberate.**
It first pointed at the live `data/`, and during round 2 the nightly rewrote it —
schema 10 → 11, 371 → 789 companies, 6,423 → 27,687 roles. Every variant refused
to render, and any evaluator running after that moment would have fired the
render hard gate against six pages that were fine. A score is a claim about a
page *and* the corpus under it: a variant graded on 6,423 roles and re-opened on
27,687 is not the same artifact, and the round-over-round comparison this harness
exists to make would be measuring the data instead of the design.

So the fixture is `HEAD:data/*` at schema 10 — 371 companies, 6,423 roles — and
every variant in every round reads the same bytes. To grade against a newer
corpus, snapshot it into a new fixture directory deliberately rather than letting
it change underneath a round.

The live pipeline is untouched by any of this; `data/` is still `data/`.

## The rounds

Five rounds of three. Lanes persist so a lane can be read down the rounds, and
the wildcard rotates so the search does not collapse into one aesthetic.

| Lane | |
|---|---|
| **A · atlas** | evolve the Swiss / International Typographic identity |
| **B · depart** | a different visual language entirely |
| **C · wildcard** | R1 motion-led · R2 text-light · R3 editorial · R4 spatial · R5 synthesis |

IDs are `r<round>-<lane>`, e.g. `r03-b`.

Each round: three generators run in parallel, then three evaluators grade the
live pages. The next round's generators are handed their lane's previous
`SCORE.md` and the round's leader. **Nothing is deleted between rounds** — a
variant that scored badly is still on disk and still openable, because the
reason a direction failed is worth more than the score.

## Why it is built this way

- **The generator never grades itself.** Asked to evaluate its own work, a model
  praises it. Separating the roles is the load-bearing part of the harness.
- **The evaluator drives the running page**, not the source. A score derived
  from reading HTML is void.
- **Criteria are weighted toward design quality and originality** over craft and
  functionality, because craft is where a model is already strong and generic is
  where it fails by default.
- **Ports are assigned per agent.** Concurrent agents running servers collide,
  and 8731/8788 belong to the test gate.
