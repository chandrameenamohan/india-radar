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
import time
from pathlib import Path

import pytest

from src.build import PROBES

SCRIPT = Path("scripts/nightly.sh")
WORKFLOWS = Path(".github/workflows")
WORKFLOW = WORKFLOWS / "nightly.yml"
SLUGS = Path("data/slugs.json")
PUBLISHED = "the last good build\n"


def git(repo: Path, *args: str) -> str:
    """Run git against the throwaway repo, and ONLY against it.

    The environment scrub is not hygiene, it is the whole safety of this file.
    `GIT_DIR` and `GIT_INDEX_FILE` are exported by git's own hooks, so when the
    pre-commit hook runs `make check-fast` these tests inherit them — and then
    `-C <tmp>` is ignored, `git add -A` stages the DELETION of every file in the
    real repo (they are all missing relative to `<tmp>`), and `git reset` moves
    the real HEAD. Measured, once, the hard way: a blocked commit left this
    worktree with 160 staged deletions and a reset HEAD.

    `subprocess` inherits `os.environ`, so the fix is to hand it a copy with
    every `GIT_*` removed. Nothing here needs one.
    """
    clean = {name: value for name, value in os.environ.items() if not name.startswith("GIT_")}
    done = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, check=True, env=clean,
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

    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.name", "test")
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-qm", "published")
    return tmp_path


def nightly(repo: Path, build: str, seconds: str = "30") -> subprocess.CompletedProcess[str]:
    """Run the script with `build` standing in for the real build.

    A file rather than an inline command line because NIGHTLY_BUILD is
    word-split by the script — it has to be, to carry `python3 -m src.build`.

    The environment is scrubbed of `GIT_*` for the reason `git` above is: the
    script commits, and under a pre-commit hook it would inherit the real repo's
    `GIT_DIR` and commit THERE.
    """
    stub = repo / "stub.sh"
    stub.write_text(f"#!/bin/sh\n{build}\n")
    stub.chmod(0o755)
    clean = {name: value for name, value in os.environ.items() if not name.startswith("GIT_")}
    return subprocess.run(
        [str(repo / SCRIPT)],
        cwd=repo,
        env={**clean, "NIGHTLY_BUILD": str(stub), "NIGHTLY_TIMEOUT": seconds},
        capture_output=True,
        text=True,
    )


def commits(repo: Path) -> int:
    return int(git(repo, "rev-list", "--count", "HEAD"))


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
