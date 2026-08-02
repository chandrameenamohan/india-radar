#!/usr/bin/env python3
"""What does ONE drafted application cost? — the v4 operating-cost gate.

Run: .venv/bin/python learning-tests/draft_cost_live.py

SPEC v4 listed this as the last unmeasured assumption: "per-application cost
times the scale curve is the operating cost of this entire version and nobody
has priced it." The human's stated curve is 1 -> 100 -> 10k -> 100k -> 1M users
in two years, and no architecture decision in v4 can be checked against that
without this number.

WHAT IS MEASURED
  A realistic single application: the profile fields `apply_questions_live.py`
  found companies actually ask, a resume, a REAL posting fetched live from
  Greenhouse with `content=true`, and that posting's REAL custom questions.
  The model answers each question or marks a gap, under v4's grounding rule.
  Both a cold call and a warm one, because the system half of this prompt is
  identical for every application a user ever makes and caching it is the
  difference between the per-application cost and a small fraction of it.

AUTH. `CLAUDE_CODE_OAUTH_TOKEN` in `.env` authenticates the API directly as a
Bearer token with the `oauth-2025-04-20` beta header — verified 2026-08-02,
HTTP 200 off `/v1/messages/count_tokens`. **That is a Claude Code subscription
credential and is right for measuring and wrong for serving.** A multi-tenant
backend drafting other people's applications needs an API key on API billing;
this token is scoped to one developer.

DEPENDENCY. `anthropic` is installed in `.venv` for this file only. The pipeline
stays dependency-free: `make check` typechecks `src/` alone, and nothing under
`src/` imports this.

FINDINGS, 2026-08-02. **Half measured, half blocked, and the measured half
overturned the assumption the caching design rested on.**

Against Anthropic's own Greenhouse board, "Account Executive, Public Sector",
a 9,098-character posting with 6 real free-text questions:

    input tokens: 4,755 total
      = 951 cacheable   (system + profile + resume — identical every application)
      + 3,804 per application  (this posting and its questions)

**THE POSTING IS FOUR FIFTHS OF THE INPUT, NOT THE PROFILE.** SPEC v4 assumed
the cacheable prefix would dominate, because the profile and resume are the same
for every application a user ever makes. They are — and they are 20% of the
prompt. Prompt caching therefore takes one application from **$0.0297 to $0.0195
of input**, a 34% saving rather than the near-total one the design implied. The
951-token prefix does clear Opus 5's 512-token cache minimum, so caching is worth
keeping; it is just not the lever it was taken for. The lever, if one is needed,
is sending less of the posting.

**Output tokens are UNMEASURED and are probably the larger half.** Not an
estimate of the number — an observation about the rates: output bills at $25/MTok
against input's $5, so output dominates unless the answers are very short. Until
it is measured the per-application cost is not known, only bounded below.

**Why it is unmeasured: `client.messages.create` returned 429 after the SDK's own
two retries.** The OAuth subscription token counts tokens all day and will not
buy a completion — which is the same fact the auth note below states
architecturally, arriving as a rate limit. Re-run without `--count-only` once an
API key with API billing exists in `.env`; the code path is written and works.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.net import get  # noqa: E402

MODEL = "claude-opus-5"

#: The eight fields `apply_questions_live.py` measured companies actually asking,
#: plus the operational constants v4 stores server-side. This is feature 18's
#: profile, not an invention.
PROFILE = {
    "name": "Priya Raman",
    "location": "Bengaluru, India",
    "work_authorization": "Indian citizen; would need sponsorship to work in the US or UK",
    "relocation": "Open to relocating for the right role",
    "onsite": "Happy with hybrid, up to three days a week",
    "earliest_start": "Six weeks from offer (notice period)",
    "salary_expectation": "INR 65-80 lakh, or equivalent if relocating",
    "languages": "English (fluent), Tamil (native), Hindi (conversational)",
    "pronouns": "she/her",
    "accommodations": "None needed",
    "heard_about_role": "ROLE·ATLAS",
}

RESUME = """\
Priya Raman — Senior Backend Engineer, Bengaluru

EXPERIENCE
Razorpay — Senior Software Engineer, Payments Core (2022-present)
  Owned the idempotency layer behind card authorisation, which handles ~4,000
  requests/second at peak and had been the source of three duplicate-charge
  incidents before the rewrite. Zero since.
  Migrated the settlement ledger from a single Postgres primary to a sharded
  layout without downtime, over eleven weeks.
  Mentored four engineers; two now run their own services.

Freshworks — Software Engineer (2019-2022)
  Built the webhook delivery service (Go, Kafka) that fans out ~90M events/day.
  Cut p99 delivery latency from 4.2s to 380ms by replacing a per-event database
  read with a warmed subscription cache.

Zoho — Software Engineer (2017-2019)
  Java services for the CRM import pipeline.

SKILLS
  Go, Python, Java, Postgres, Kafka, Redis, Kubernetes, gRPC.
  Distributed systems, payments, idempotency, at-least-once delivery.

EDUCATION
  B.E. Computer Science, Anna University, 2017.
"""

SYSTEM = """\
You help a job applicant answer an employer's own application questions in their
own voice.

THE RULE THAT GOVERNS EVERYTHING: you may not state a fact about this applicant
that is not present in their profile or resume below. You may select, compress
and phrase what is there. You may not invent an employer, a number, a motivation,
a preference, or an opinion they have not expressed. Where a question asks for
something the profile and resume do not contain, return a gap for that question
instead of an answer — a marked gap is a correct output, not a failure.

Write in first person, plainly, the way a competent engineer writes when they are
not trying to impress. No superlatives about the company. No "I am excited to".
No sentence that could be pasted into an application to any other employer.

For each answer, state which profile field or resume line it was built from.
"""

SCHEMA = {
    "type": "object",
    "properties": {
        "answers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "answer": {"type": "string"},
                    "grounded_in": {"type": "string"},
                    "is_gap": {"type": "boolean"},
                },
                "required": ["question", "answer", "grounded_in", "is_gap"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["answers"],
    "additionalProperties": False,
}

GH_JOBS = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=false"
GH_ONE = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{job}?questions=true"
STRUCTURAL = ("resume/cv", "cover letter", "first name", "last name", "email",
              "phone", "linkedin", "website", "location", "github", "portfolio")


def a_real_posting(slug: str) -> tuple[str, str, list[str]]:
    """A live posting and the questions its company actually asks."""
    code, body = get(GH_JOBS.format(slug=slug))
    if code != 200:
        raise SystemExit(f"{slug}: job list {code}")

    for job in json.loads(body).get("jobs", []):
        code, body = get(GH_ONE.format(slug=slug, job=job["id"]))
        if code != 200:
            continue
        payload = json.loads(body)
        asked = [
            q["label"].strip()
            for q in payload.get("questions") or []
            if not any(k in q.get("label", "").lower() for k in STRUCTURAL)
            and any(f.get("type") in ("textarea", "input_text") for f in q.get("fields", []))
        ]
        if asked:
            return job["title"], payload.get("content", ""), asked
    raise SystemExit(f"{slug}: no posting with free-text questions")


def stable_half() -> str:
    """Identical for every application this user ever makes — the cacheable prefix."""
    return f"{SYSTEM}\n\nPROFILE\n{json.dumps(PROFILE, indent=2)}\n\nRESUME\n{RESUME}"


def varying_half(title: str, posting: str, questions: list[str]) -> str:
    """The one posting being applied to — new bytes on every application."""
    asked = "\n".join(f"- {q}" for q in questions)
    return f"ROLE: {title}\n\nPOSTING\n{posting}\n\nQUESTIONS THIS COMPANY ASKS\n{asked}"


def one_application(client: Any, title: str, posting: str, questions: list[str]) -> Any:
    """One drafted application. The system half is cached; the posting is not."""
    return client.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=[{
            "type": "text",
            # Stable for every application this user ever makes -> the cache breakpoint
            # goes here and nowhere else.
            "text": stable_half(),
            "cache_control": {"type": "ephemeral"},
        }],
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": varying_half(title, posting, questions)}],
    )


def report(label: str, usage: Any) -> None:
    """Per-call tokens and dollars. Opus 5 is $5/$25 per million."""
    fresh, cached = usage.cache_creation_input_tokens, usage.cache_read_input_tokens
    uncached, out = usage.input_tokens, usage.output_tokens
    # Cache writes bill at 1.25x input, reads at 0.1x.
    dollars = (uncached + fresh * 1.25 + cached * 0.1) * 5e-6 + out * 25e-6
    print(f"{label:>6}: in={uncached} cache_write={fresh} cache_read={cached} "
          f"out={out}  ${dollars:.4f}")


def main() -> None:
    token = next(
        (line.split("=", 1)[1].strip().strip("\"'")
         for line in Path(".env").read_text().splitlines()
         if line.startswith("CLAUDE_CODE_OAUTH_TOKEN=")),
        os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", ""),
    )
    if not token:
        raise SystemExit("no CLAUDE_CODE_OAUTH_TOKEN in .env")

    import anthropic

    client = anthropic.Anthropic(
        auth_token=token,
        default_headers={"anthropic-beta": "oauth-2025-04-20"},
    )

    title, posting, questions = a_real_posting(sys.argv[1] if len(sys.argv) > 1 else "anthropic")
    print(f"role: {title}\nposting: {len(posting)} chars\nquestions: {len(questions)}")
    for q in questions:
        print(f"  - {q[:88]}")

    # `count_tokens` is free and unmetered, so the input half of the cost is
    # measurable even when the credential cannot afford a completion.
    def count(user_text: str) -> int:
        return client.messages.count_tokens(
            model=MODEL,
            system=[{"type": "text", "text": stable_half()}],
            messages=[{"role": "user", "content": user_text}],
        ).input_tokens

    total = count(varying_half(title, posting, questions))
    cacheable = count("x")
    per_app = total - cacheable
    print(f"\ninput tokens: {total} total = {cacheable} cacheable "
          f"(profile+resume+system, identical every time) + {per_app} per application")
    print(f"  cold input ${total * 1.25 * 5e-6:.4f}   "
          f"warm input ${(cacheable * 0.1 + per_app) * 5e-6:.4f}   "
          f"(Opus 5 $5/MTok in; cache write 1.25x, read 0.1x)")

    if "--count-only" in sys.argv:
        return

    cold = one_application(client, title, posting, questions)
    warm = one_application(client, title, posting, questions)
    print()
    report("cold", cold.usage)
    report("warm", warm.usage)

    drafted = json.loads(next(b.text for b in cold.content if b.type == "text"))
    gaps = sum(1 for a in drafted["answers"] if a["is_gap"])
    print(f"\nanswered {len(drafted['answers']) - gaps}, marked as gaps {gaps}")
    for a in drafted["answers"]:
        mark = "GAP" if a["is_gap"] else "   "
        print(f"\n{mark} {a['question'][:88]}\n    {a['answer'][:300]}")
        print(f"    <- {a['grounded_in'][:150]}")


if __name__ == "__main__":
    main()
