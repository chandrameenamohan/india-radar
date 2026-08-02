#!/usr/bin/env python3
"""Do Greenhouse and Ashby state a job's APPLICATION QUESTIONS? — the v4 feature 18 gate.

Run: .venv/bin/python learning-tests/apply_questions_live.py

SPEC v4 feature 18 opens a workspace showing "the company's own questions, each
with a draft against it". That sentence assumes we can LEARN the questions. If we
can, the workspace opens already drafted against what the form actually asks. If
we cannot, the user has to paste the questions in first, which is a materially
less magic feature and a different UI — so this is worth knowing before anything
is designed around it.

The build already reads both boards' job endpoints (`src/greenhouse.py`,
`src/ashby.py`) and neither asks for questions today, so nothing here is a repeat
of a measurement the project holds.

WHAT IS PROBED
  Greenhouse  boards-api .../jobs/{id}?questions=true   — documented to carry them
  Ashby       the posting API, then the hosted board page's embedded blob, which
              is where `src/ashby.identity()` already found `publicWebsite` when
              the API refused to say whose board it was (T12.1).

FINDINGS, measured 2026-08-02. The assumption was half right, and the half that
was wrong is the more useful half.

**Greenhouse states them. Ashby does not.** `?questions=true` returns a full
`questions` array on every board tried, one extra call per job. Ashby's posting
API carries no question key at all, and the hosted board page — the same blob
`src/ashby.identity()` reads `publicWebsite` out of — carries only FEATURE FLAG
names that happen to contain the word (`UseJobPostingFiltersOnGlobal
ApplicationQuestions`), never the questions themselves. **401 of the 880 resolved
slugs are Ashby**, so for very nearly half this register the workspace cannot
know what the form asks, and has to say so rather than imply the form is short.

**CORRECTED 2026-08-03. The 54% this file first reported is not a measurement,
and the fault is in `STRUCTURAL` below.** It matched boilerplate labels by
SUBSTRING, so `"location"` deleted "Which office location would you prefer?" — a
question a company chose to ask, removed from a form we would then have told a
reader was complete. Switching to exact matching swings the same 52 postings to
98%, because it then keeps "LinkedIn Profile" and "Preferred First Name" as
company questions; classifying by Greenhouse's stable field names gives 85%.
**Three defensible filters, forty-four points apart.** The count is therefore
withdrawn rather than restated: what varies is the definition, not the boards.
There IS real material here — the first four-board probe returning nothing but
"Resume/CV" and "Cover Letter" was a small sample on non-engineering roles — but
`--labels` prints a distribution, and only the distribution should be read off it.

**But most of those questions are FACTS, not essays, and that is the finding
that matters.** The recurring labels are salary expectations, earliest start
date, the address you would work from, languages spoken, sponsorship needs,
pronouns, interview accommodations, and "how did you hear about this job".
Genuine prose questions — "Why Anthropic?", "How are you using AI today in your
current role?" — are the minority. That inverts the emphasis SPEC v4 was written
with: **the profile does most of the work and the model does the smaller part.**
A profile holding those eight recurring fields removes more repeated typing than
the drafting does, costs no tokens, and cannot hallucinate. Note also that the
`questions` array is where the EEO demographic fields live, which is exactly what
v4's browser-only demographic store was built to fill.

(The 401 Ashby slugs and the per-label counts are measured. The share of
postings asking a question is not — see the correction above. The fact/essay
split is a characterisation of the distribution `--labels` prints, and it is the
part that held up under every filter tried.)
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.net import get  # noqa: E402

GH_JOBS = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=false"
GH_ONE = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{job}?questions=true"
ASHBY_BOARD = "https://api.ashbyhq.com/posting-api/job-board/{slug}"
ASHBY_PAGE = "https://jobs.ashbyhq.com/{slug}/{job}"


def greenhouse(slug: str) -> dict[str, object]:
    """One board: fetch a job list, then ask the first job for its questions."""
    code, body = get(GH_JOBS.format(slug=slug))
    if code != 200:
        return {"slug": slug, "note": f"job list {code}"}
    jobs = json.loads(body).get("jobs", [])
    if not jobs:
        return {"slug": slug, "note": "no open roles"}

    job = jobs[0]
    code, body = get(GH_ONE.format(slug=slug, job=job["id"]))
    if code != 200:
        return {"slug": slug, "note": f"single job {code}"}
    payload = json.loads(body)
    questions = payload.get("questions")
    if questions is None:
        return {"slug": slug, "note": "200 but no `questions` key", "keys": sorted(payload)}

    # Only the free-text ones need drafting; a file upload or a yes/no does not.
    text = [q for q in questions if any(f.get("type") == "textarea" for f in q.get("fields", []))]
    return {
        "slug": slug,
        "role": job.get("title", "")[:44],
        "questions": len(questions),
        "free_text": len(text),
        "labels": [q.get("label", "")[:58] for q in text],
        "required": sum(1 for q in questions if q.get("required")),
    }


def ashby(slug: str) -> dict[str, object]:
    """One board: the posting API first, then the page blob if the API is silent."""
    code, body = get(ASHBY_BOARD.format(slug=slug))
    if code != 200:
        return {"slug": slug, "note": f"board {code}"}
    jobs = json.loads(body).get("jobs", [])
    if not jobs:
        return {"slug": slug, "note": "no open roles"}

    job = jobs[0]
    api_says = [k for k in job if "question" in k.lower() or "applicationForm" in k]

    job_id = job.get("id") or (job.get("jobUrl", "").rstrip("/").rsplit("/", 1)[-1])
    code, page = get(ASHBY_PAGE.format(slug=slug, job=job_id))
    pattern = r'"(\w*(?:[Qq]uestion|applicationForm)\w*)"'
    hits = sorted(set(re.findall(pattern, page))) if code == 200 else []
    return {
        "slug": slug,
        "role": job.get("title", "")[:44],
        "api_question_keys": api_says,
        "page": code,
        "page_question_keys": hits[:8],
        "page_bytes": len(page) if code == 200 else 0,
    }


#: Labels every board asks and no company wrote — they identify the applicant or
#: upload a file, and none of them is a question in the sense feature 18 means.
STRUCTURAL = ("resume/cv", "cover letter", "first name", "last name", "email",
              "phone", "linkedin", "website", "location", "github", "portfolio")


def _custom(questions: list[dict[str, Any]]) -> list[str]:
    """The free-text labels a company chose to add, structural fields removed."""
    out = []
    for q in questions:
        label = q.get("label", "").strip()
        if any(k in label.lower() for k in STRUCTURAL):
            continue
        if any(f.get("type") in ("textarea", "input_text") for f in q.get("fields", [])):
            out.append(label)
    return out


def labels(boards: list[str], per_board: int = 3) -> None:
    """The distribution of labels companies ask. Read the labels, not the count.

    The percentage this prints is an artefact of `STRUCTURAL` and is withdrawn —
    see the correction in the module docstring. It is still printed because
    watching it MOVE when the filter changes is the point.
    """
    seen = asked = 0
    found: Counter[str] = Counter()
    boards_asking = set()
    for slug in boards:
        code, body = get(GH_JOBS.format(slug=slug))
        if code != 200:
            continue
        for job in json.loads(body).get("jobs", [])[:per_board]:
            code, body = get(GH_ONE.format(slug=slug, job=job["id"]))
            if code != 200:
                continue
            seen += 1
            custom = _custom(json.loads(body).get("questions") or [])
            if custom:
                asked += 1
                boards_asking.add(slug)
                found.update(label[:90] for label in custom)

    pct = 100 * asked / max(seen, 1)
    print(f"\njobs sampled: {seen}   asking something written: {asked} ({pct:.0f}%)"
          f"   boards: {len(boards_asking)}/{len(boards)}")
    for label, n in found.most_common(20):
        print(f"  {n:3}  {label}")


def main() -> None:
    slugs = json.loads(Path("data/slugs.json").read_text())
    by_ats: dict[str, list[str]] = {"greenhouse": [], "ashby": []}
    for entry in slugs.values():
        if isinstance(entry, dict) and entry["ats"] in by_ats:
            by_ats[entry["ats"]].append(entry["slug"])

    if "--labels" in sys.argv:
        labels(by_ats["greenhouse"][:20])
        return

    for ats, probe in (("greenhouse", greenhouse), ("ashby", ashby)):
        print(f"\n=== {ats} ===")
        for slug in by_ats[ats][:4]:
            print(json.dumps(probe(slug), ensure_ascii=False)[:600])


if __name__ == "__main__":
    main()
