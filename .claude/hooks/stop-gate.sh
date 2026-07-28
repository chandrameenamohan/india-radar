#!/usr/bin/env bash
# Stop hook: refuses to let the turn end while the gate is RED.
#
# CRITICAL: gated on PW_LOOP=1 so it enforces ONLY inside the Ralph loop and is a
# silent no-op in normal interactive sessions. Without this, every interactive
# turn would run the full gate -- including e2e -- which is intolerable.
#
# Exit codes are the contract with Claude Code:
#   2 -> block the stop, feed stderr back into context
#   0 -> allow the stop
set -uo pipefail

if [ "${PW_LOOP:-0}" != "1" ]; then
  exit 0   # not in the loop: silent no-op
fi

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$("$ROOT/.claude/hooks/gate.sh" 2>&1)"
CODE=$?

if [ $CODE -ne 0 ]; then
  {
    echo "GATE IS RED -- you may not stop yet. Fix this, then re-run 'make check'."
    echo "Do NOT weaken, delete, or skip a check to make this pass."
    echo ""
    echo "$OUT" | tail -40
  } >&2
  exit 2
fi
exit 0
