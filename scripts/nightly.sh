#!/usr/bin/env bash
# The nightly refresh, whole — T6.2.
#
# .github/workflows/nightly.yml runs exactly this, and so can a human:
# `scripts/nightly.sh`. It builds and commits; it never pushes, because a hand
# run should not publish and the workflow is the only thing that should.
#
# It commits ONLY on success. `set -e` plus the build's own refusal to write a
# schema-invalid file (src/build.write validates, then writes) means a run that
# DIES leaves the published JSON exactly as it was.
#
# That was claimed here as T6.4's whole guarantee, and it is only half of it: a
# broken provider does not make this run die. Every probe returns `probe-failed`
# on a bad status, by design (a company we could not read is excluded and
# counted, never listed as hiring nobody) — so a night when Greenhouse is down
# exits 0 with a complete, schema-valid file missing 88 of 116 companies, and
# nothing in this script can tell that from a quiet week. The half `set -e`
# cannot see is `build.COLLAPSE`, in the build.
set -euo pipefail
cd "$(dirname "$0")/.."

# The bound. Measured full build: 11m26s, of which ~8.6 is Greenhouse's 429
# sequential calls at 1.2s each (re-measured 2026-07-29 — FINDINGS §1's 0.35s no
# longer holds). 90 minutes is eight times the measured run and a quarter of
# GitHub's 6h job cap, so a night that overruns it is a hung provider rather than
# a slow one, and killing it is the right answer.
#
# Unquoted on purpose: the override is a command line, not a filename. It exists
# so the dry-run test can substitute a stub for the real build — the gate does
# not do full-corpus builds (VERIFICATION.md).
# shellcheck disable=SC2086
timeout "${NIGHTLY_TIMEOUT:-5400}" ${NIGHTLY_BUILD:-.venv/bin/python -m src.build}

# T15.2. Dates every role URL the build just published that the artifact has not
# seen before, and marks it new ONLY where the company's board was read on the
# previous snapshot as well as this one.
#
# READS NO GIT HISTORY, and that is the whole reason it is a separate step
# rather than a diff. nightly.yml checks out with actions/checkout@v4, which
# fetches depth 1 — there is no previous commit here to diff against. Everything
# it knows about yesterday comes out of data/first-seen.json, which the last run
# committed. `scripts/first_seen_backfill.py` is the only thing in this repo
# that reads git, it is a hand run, and nothing automatic may call it.
#
# After the build, deliberately: it reads the two files the build has just
# written. `set -e` means a build that died never reaches this line, and a
# failure here reaches no commit.
#
# Same seam as NIGHTLY_BUILD above, for the same reason and unquoted for the
# same reason: it is a command line, and the dry-run test substitutes one.
# shellcheck disable=SC2086
${NIGHTLY_FIRSTSEEN:-.venv/bin/python -m src.firstseen}

git add -- data/companies.json data/build-report.json data/first-seen.json
if git diff --cached --quiet; then
  echo "nightly: build produced no change; nothing to commit"
  exit 0
fi
git commit -q -m "nightly refresh $(date -u +%F)"
echo "nightly: committed $(git rev-parse --short HEAD)"
