"""The nightly refresh, dry-run — T6.2, and its tiering — T6.3.

VERIFICATION.md keeps full-corpus builds out of the gate: a real run is ~14
minutes against three live APIs. So these drive `scripts/nightly.sh` — the exact
thing `.github/workflows/nightly.yml` runs — over a throwaway git repo with the
build stubbed. The publish logic is what can break, and it is all here.

The two halves of "commits fresh JSON *on success*" get a test each: a build
that succeeds is published, and a build that fails or overruns leaves the
previously published JSON byte-for-byte intact.

The last two are T6.3's, and they pin a decision rather than a behaviour: every
provider is refreshed on the one schedule whose date the site stamps. See the
module docstring in `learning-tests/nightly_tiers_live.py` for the measurement
that ruled out the weekly Ashby tier T6.3 was named for.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from src.build import PROBES
from src.firstseen import SCHEMA_VERSION

SCRIPT = Path("scripts/nightly.sh")
BACKFILL = Path("scripts/first_seen_backfill.py")
FIRSTSEEN = Path("src/firstseen.py")
WORKFLOWS = Path(".github/workflows")
WORKFLOW = WORKFLOWS / "nightly.yml"
SLUGS = Path("data/slugs.json")
PUBLISHED = "the last good build\n"
#: A first-seen artifact that has never folded a snapshot — the state a repo is
#: in before the backfill, and the one the bootstrap has to survive.
EMPTY_ARTIFACT = json.dumps(
    {"schema_version": SCHEMA_VERSION, "snapshot": None, "note": "", "observed": [], "dates": {}}
)

#: The environment for a throwaway repo, which is the ambient one with git's own
#: variables taken out.
#:
#: Load-bearing, and it took a blocked commit to find: git exports GIT_DIR,
#: GIT_INDEX_FILE and the author identity into every hook it runs, and the
#: The environment with git's own variables taken out of it.
#:
#: Git exports GIT_DIR and GIT_INDEX_FILE to a hook, and this suite runs under
#: the pre-commit one. Inherited, `-C tmp_path` stops meaning anything: `git
#: init` re-inits the repository being committed to rather than the throwaway
#: one, and `git commit` re-enters the hook that started it. Isolation is the
#: whole point of the fixture, so git's environment is dropped, not trusted.
#:
#: Found independently by two agents, both working in git WORKTREES, which is
#: where it bites hardest — there GIT_DIR points somewhere other than the
#: checkout and the failure names a pytest tmp path rather than its cause. It
#: did NOT fail in the main checkout; commits went green through this same hook
#: all session. Recorded that way deliberately: "every commit was failing" was
#: the first telling and it is not what the evidence supports.
CLEAN_ENV = {name: value for name, value in os.environ.items() if not name.startswith("GIT_")}


def git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        env=CLEAN_ENV,
    )
    return done.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A repo with one commit holding a published data/, and the real script."""
    (tmp_path / "scripts").mkdir()
    script = tmp_path / SCRIPT
    script.write_bytes(SCRIPT.read_bytes())
    script.chmod(0o755)

    (tmp_path / "data").mkdir()
    (tmp_path / "data/companies.json").write_text(PUBLISHED)
    (tmp_path / "data/build-report.json").write_text(PUBLISHED)
    (tmp_path / "data/first-seen.json").write_text(EMPTY_ARTIFACT)

    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.name", "test")
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-qm", "published")
    return tmp_path


def nightly(
    repo: Path, build: str, seconds: str = "30", firstseen: str | None = "true"
) -> subprocess.CompletedProcess[str]:
    """Run the script with `build` standing in for the real build.

    A file rather than an inline command line because NIGHTLY_BUILD is
    word-split by the script — it has to be, to carry `python3 -m src.build`.

    `firstseen` stands in for T15.2's step the same way, and defaults to a no-op
    so the four publish tests below keep testing publishing. The one test that
    wants the real module passes it, and it is the one that proves the wiring.
    """
    stub = repo / "stub.sh"
    stub.write_text(f"#!/bin/sh\n{build}\n")
    stub.chmod(0o755)
    return subprocess.run(
        [str(repo / SCRIPT)],
        cwd=repo,
        env={
            **CLEAN_ENV,
            "NIGHTLY_BUILD": str(stub),
            "NIGHTLY_TIMEOUT": seconds,
            # None omits the variable, which is the only way to exercise the
            # script's own DEFAULT. Every other test here supplies both seams,
            # and that is exactly how a default naming .venv/bin/python reached
            # production unrun.
            **({} if firstseen is None else {"NIGHTLY_FIRSTSEEN": firstseen}),
            "PYTHONPATH": str(Path.cwd()),
        },
        capture_output=True,
        text=True,
    )


def commits(repo: Path) -> int:
    return int(git(repo, "rev-list", "--count", "HEAD"))


def code_only(path: Path) -> str:
    """The file with its comments and its module docstring taken out.

    The rule below is about what a file DOES, and all three of these files
    explain at length why they do not do it — a substring check over the whole
    text would be reading the explanation as the offence, and the fix for that
    failure would be deleting the explanation.
    """
    body = path.read_text()
    if path.suffix == ".py":
        body = body.split('"""', 2)[-1]
    return "\n".join(line for line in body.splitlines() if not line.lstrip().startswith("#"))


def test_successful_build_is_committed(repo: Path) -> None:
    done = nightly(repo, "echo fresh > data/companies.json")

    assert done.returncode == 0, done.stderr
    assert commits(repo) == 2
    assert git(repo, "log", "-1", "--format=%s").startswith("nightly refresh ")
    assert git(repo, "show", "HEAD:data/companies.json") == "fresh"


def test_unchanged_build_commits_nothing(repo: Path) -> None:
    """A night where nobody's board moved is not a night with no data."""
    done = nightly(repo, "true")

    assert done.returncode == 0, done.stderr
    assert commits(repo) == 1
    assert "nothing to commit" in done.stdout


def test_failed_build_leaves_published_json_intact(repo: Path) -> None:
    """The build writes, then dies. Nothing it wrote reaches the published tree."""
    done = nightly(repo, "echo truncated > data/companies.json\nexit 1")

    assert done.returncode != 0
    assert commits(repo) == 1
    assert git(repo, "show", "HEAD:data/companies.json") == PUBLISHED.strip()


def test_overrun_is_killed_and_publishes_nothing(repo: Path) -> None:
    """The wall-time bound is enforced, not hoped for: a build that hangs is
    killed at NIGHTLY_TIMEOUT and publishes nothing. Without the bound this test
    would take 30 seconds and then commit.
    """
    started = time.monotonic()
    done = nightly(repo, "echo half > data/companies.json\nsleep 30", seconds="1")
    elapsed = time.monotonic() - started

    assert elapsed < 10, f"the bound did not bite: {elapsed:.1f}s"
    assert done.returncode == 124, "124 is timeout's 'I killed it'"
    assert commits(repo) == 1
    assert git(repo, "show", "HEAD:data/companies.json") == PUBLISHED.strip()


def test_the_first_seen_artifact_is_folded_after_the_build_and_published(repo: Path) -> None:
    """T15.2's wiring, with the real module rather than a stub.

    Ordering is what this proves, and the fixture is what makes it prove it: the
    published data/ holds `the last good build`, which is not JSON. A first-seen
    step running BEFORE the build would read that and die. It succeeds only if it
    ran after, over the file the build had just written — and the artifact it
    wrote has to reach the commit, or tomorrow's nightly starts from nothing and
    re-dates the whole register to tomorrow.
    """
    (repo / "fresh.json").write_text(
        json.dumps(
            {
                "schema_version": 10,
                "snapshot": "2026-08-03",
                "companies": [{"name": "Acme", "roles": [{"url": "https://boards/1"}]}],
            }
        )
    )
    (repo / "fresh-report.json").write_text(json.dumps({"listed": ["Acme"]}))

    done = nightly(
        repo,
        "cp fresh.json data/companies.json\ncp fresh-report.json data/build-report.json",
        firstseen=f"{sys.executable} -m src.firstseen",
    )

    assert done.returncode == 0, done.stderr
    assert commits(repo) == 2
    art = json.loads(git(repo, "show", "HEAD:data/first-seen.json"))
    assert art["dates"] == {"2026-08-03": {"confirmed": [], "unconfirmed": ["https://boards/1"]}}
    assert art["observed"] == ["Acme"], "without this the next night confirms nothing"


def test_the_nightly_reads_no_git_history() -> None:
    """T15.2, and it is the one way this feature fails silently in production.

    `actions/checkout@v4` fetches depth 1. A first-seen step that diffed against
    the previous commit would work perfectly on a laptop with 26 commits of
    data/companies.json behind it and produce garbage at 20:00 UTC, where there
    is exactly one. So the nightly's whole memory is the committed artifact, and
    the only thing in this repo that reads git is the one-time backfill, which
    nothing automatic may call.

    Asserted against the files rather than trusted, because "we just don't do
    that" is the kind of fact that stays true until someone adds a convenient
    line — the same reason the slug rule above is a test.
    """
    for path in (SCRIPT, WORKFLOW, FIRSTSEEN):
        body = code_only(path)
        for reads_history in ("git show", "git log", "rev-list", "git diff HEAD"):
            assert reads_history not in body, (
                f"{path} reads git history: CI checks out at depth 1 and there is "
                f"none to read. The delta comes from the committed artifact."
            )
        assert BACKFILL.name not in body, f"{path} calls the one-time backfill"
    assert "git show" in BACKFILL.read_text(), (
        "the backfill is the one thing that may read history; if it no longer "
        "does, this test is guarding a rule nothing implements"
    )


def test_workflow_runs_the_tested_script_nightly() -> None:
    """The tests above are worth something only if CI runs this script and not
    its own copy of the logic.
    """
    workflow = WORKFLOW.read_text()

    assert "scripts/nightly.sh" in workflow
    assert 'cron: "0 20 * * *"' in workflow
    assert "contents: write" in workflow, "the job commits; without this it 403s"


def test_the_nightly_probes_every_resolved_provider() -> None:
    """T6.3. The nightly runs the build, so the build's providers ARE the refresh
    tiering: an ATS the corpus holds slugs for but the build cannot probe is a
    slice of the site refreshed never, while the footer stamps tonight's date on
    it. That is how a weekly Ashby tier would have failed — 261 companies
    republished from last week under today's snapshot date.
    """
    resolved = {entry["ats"] for entry in json.loads(SLUGS.read_text()).values()}

    assert resolved <= set(PROBES), (
        f"{resolved - set(PROBES)} resolved but unprobeable: those companies are "
        "probe-failed for want of a probe, not for want of a readable board"
    )


def test_the_nightly_never_re_resolves_slugs() -> None:
    """T10.4's ruling, and T12.1 is what makes it bite. Slug discovery is ~2.5
    hours of careers pages, and T12.1 hangs another ~26 minutes of Ashby
    guessing off the same pass. A company that already has a slug learns nothing
    from being resolved again — data/slugs.json already says the answer — and a
    nightly that spent three hours re-deriving it would sit inside a 6h cap it
    currently uses 3% of.

    So the nightly runs the BUILD and only the build, and slug resolution is a
    hand-run for the names the corpus gained. Asserted against the workflow and
    the script it calls, because "we just don't run it" is the kind of fact that
    stays true only until someone adds a convenient line.
    """
    for path in (WORKFLOW, SCRIPT):
        assert "src.slugs" not in path.read_text(), (
            f"{path} resolves slugs: that is ~3h a night to re-derive what "
            "data/slugs.json already holds, and T10.4 ruled it out"
        )


def test_one_schedule_because_a_second_would_be_a_slower_tier() -> None:
    """T6.3. Measured 2026-07-29 (`learning-tests/nightly_tiers_live.py`): the
    whole Ashby corpus is 36.9s concurrently, 9% of the probe time and 5% of an
    11-minute build. A weekly tier buys back 37 seconds a night and pays six days
    of staleness for it.

    So a second scheduled workflow is not a free addition to this repo — it is
    the tiering decision being reversed. Whoever adds one is asserting a cost
    that this measurement says does not exist, and should have to say so here.
    """
    # `*.y*ml` because GitHub reads both spellings, and a weekly tier landing as
    # `weekly.yaml` would otherwise walk straight past this check.
    scheduled = [
        path.name for path in sorted(WORKFLOWS.glob("*.y*ml")) if "schedule:" in path.read_text()
    ]

    assert scheduled == ["nightly.yml"], (
        f"{scheduled}: a second schedule refreshes part of the corpus less often "
        "than the snapshot date the site publishes"
    )


def test_the_first_seen_step_runs_without_any_seam_set(repo: Path) -> None:
    """The DEFAULT interpreter, on a machine with no .venv — which is CI.

    This is the test that did not exist, and its absence cost a full nightly.
    `nightly.yml` supplies NIGHTLY_BUILD to give CI an interpreter, so the
    build's `.venv/bin/python` default never ran there; T15.2 copied that seam
    without the caller-side half, and every test overrode both. The result was a
    step that worked on every laptop and exited 127 at 03:26, after the build had
    already spent ten minutes and thrown the result away (run 30874273868).

    The fixture repo has no .venv, so omitting the override is the whole test:
    the script must resolve an interpreter that exists rather than name one.
    """
    (repo / "fresh.json").write_text(
        json.dumps(
            {
                "schema_version": 10,
                "snapshot": "2026-08-05",
                "companies": [{"name": "Acme", "roles": [{"url": "https://boards/9"}]}],
            }
        )
    )
    (repo / "fresh-report.json").write_text(json.dumps({"listed": ["Acme"]}))

    done = nightly(
        repo,
        "cp fresh.json data/companies.json\ncp fresh-report.json data/build-report.json",
        firstseen=None,
    )

    assert "No such file or directory" not in done.stderr, done.stderr
    assert done.returncode == 0, done.stderr
    # Not merely "it did not die": the artifact has to have been written, or a
    # step that silently no-opped would pass this too.
    art = json.loads(git(repo, "show", "HEAD:data/first-seen.json"))
    assert art["dates"]["2026-08-05"]["unconfirmed"] == ["https://boards/9"]
