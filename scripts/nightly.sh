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

git add -- data/companies.json data/build-report.json
if git diff --cached --quiet; then
  echo "nightly: build produced no change; nothing to commit"
  exit 0
fi
git commit -q -m "nightly refresh $(date -u +%F)"
echo "nightly: committed $(git rev-parse --short HEAD)"
