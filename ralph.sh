#!/usr/bin/env bash
# Ralph loop driver. Spawns a FRESH headless Claude per iteration; each reads
# LOOP_PROMPT.md, implements ONE task from TASKS.md, and stops.
#
# Runs in its own shell / tmux session -- never inside an interactive Claude
# session. Monitor from elsewhere with:  tail -f logs/ralph-latest.log
#
#   ./ralph.sh           attended  -- pauses for your validation after each task
#   ./ralph.sh --auto    unattended -- only after the gate has caught a real failure
#   ./ralph.sh --max 5   cap iterations
set -uo pipefail
cd "$(cd "$(dirname "$0")" && pwd)"

AUTO=0
MAX=100
while [ $# -gt 0 ]; do
  case "$1" in
    --auto) AUTO=1 ;;
    --max)  MAX="$2"; shift ;;
    *) echo "unknown flag: $1"; exit 1 ;;
  esac
  shift
done

# Activates the Stop hook. Without this the hook is a silent no-op, which is what
# keeps interactive sessions from running the full gate on every turn.
export PW_LOOP=1

mkdir -p logs
STAMP="$(date +%Y%m%d-%H%M%S)"
LOG="logs/ralph-$STAMP.log"
ln -sf "$(basename "$LOG")" logs/ralph-latest.log

command -v claude >/dev/null || { echo "FATAL: claude CLI not found"; exit 1; }

banner() { echo "" | tee -a "$LOG"; echo "===== $* =====" | tee -a "$LOG"; }

# Count ACTIONABLE tasks. Anchored to '### T<n>' headers so prose mentioning
# `todo` (e.g. the status-vocabulary line) cannot inflate the count.
# Deliberately excludes `blocked` and `needs-review`: those are not actionable by
# the loop and are reported separately, so a fully-blocked backlog does not look
# like a finished one.
remaining()   { grep -cE '^### T[0-9].*`(todo|in-progress)`' TASKS.md 2>/dev/null || echo 0; }
parked()      { grep -cE '^### T[0-9].*`(blocked|needs-review)`' TASKS.md 2>/dev/null || echo 0; }

banner "RALPH START $(date)  mode=$([ $AUTO = 1 ] && echo auto || echo attended)  log=$LOG"
echo "tasks remaining: $(remaining)" | tee -a "$LOG"

for i in $(seq 1 "$MAX"); do
  REM_BEFORE=$(remaining)
  HEAD_BEFORE=$(git rev-parse HEAD)

  if [ "$REM_BEFORE" -eq 0 ]; then
    banner "NO ACTIONABLE TASKS LEFT — stopping ($(parked) parked as blocked/needs-review)"
    break
  fi

  banner "ITERATION $i / $MAX   (tasks remaining: $REM_BEFORE)"
  claude -p --permission-mode auto < LOOP_PROMPT.md 2>&1 | tee -a "$LOG"

  REM_AFTER=$(remaining)
  HEAD_AFTER=$(git rev-parse HEAD)

  # PROGRESS DETECTION: an iteration that closed no task AND made no commit is
  # stuck. Spinning on that burns tokens and produces nothing.
  if [ "$REM_AFTER" -eq "$REM_BEFORE" ] && [ "$HEAD_BEFORE" = "$HEAD_AFTER" ]; then
    banner "NO PROGRESS: no task closed and no commit made"
    if [ $AUTO = 1 ]; then
      echo "stopping rather than spinning. See $LOG" | tee -a "$LOG"
      exit 1
    fi
  fi

  if [ $AUTO = 0 ]; then
    echo "" | tee -a "$LOG"
    read -r -p "Validate the summary above. [enter]=continue  q=quit > " ans
    [ "$ans" = "q" ] && { banner "STOPPED BY USER"; break; }
  fi
done

banner "RALPH END $(date)   actionable: $(remaining)   parked: $(parked)"
echo "log: $LOG"
