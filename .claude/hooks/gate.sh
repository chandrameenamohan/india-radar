#!/usr/bin/env bash
# THE GATE. One definition of "green" for the whole project.
# The Stop hook, the pre-commit hook and ralph.sh all call this and nothing else.
# Runs `make check` from the project root and exits with its code.
set -uo pipefail

# git rev-parse already returns the project ROOT -- do not append "/..".
# (An earlier version did, landing one directory too high. The gate then reported
# "No rule to make target 'check'" while STILL exiting non-zero, so it looked like
# a working brake and was not. Proving the brake is what surfaced it.)
if ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" && [ -n "$ROOT" ]; then
  cd "$ROOT" || exit 1
else
  cd "$(dirname "$0")/../.." || exit 1
fi

# Fail loudly if we landed somewhere without the Makefile, rather than letting
# make's own error masquerade as a genuine gate failure.
if [ ! -f Makefile ]; then
  echo "gate.sh: no Makefile in $(pwd) -- refusing to report a meaningful result" >&2
  exit 1
fi

exec make check
