"""The nightly refresh, dry-run — T6.2.

VERIFICATION.md keeps full-corpus builds out of the gate: a real run is ~14
minutes against three live APIs. So these drive `scripts/nightly.sh` — the exact
thing `.github/workflows/nightly.yml` runs — over a throwaway git repo with the
build stubbed. The publish logic is what can break, and it is all here.

The two halves of "commits fresh JSON *on success*" get a test each: a build
that succeeds is published, and a build that fails or overruns leaves the
previously published JSON byte-for-byte intact.
"""
from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import pytest

SCRIPT = Path("scripts/nightly.sh")
WORKFLOW = Path(".github/workflows/nightly.yml")
PUBLISHED = "the last good build\n"


def git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
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
    """
    stub = repo / "stub.sh"
    stub.write_text(f"#!/bin/sh\n{build}\n")
    stub.chmod(0o755)
    return subprocess.run(
        [str(repo / SCRIPT)],
        cwd=repo,
        env={**os.environ, "NIGHTLY_BUILD": str(stub), "NIGHTLY_TIMEOUT": seconds},
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
