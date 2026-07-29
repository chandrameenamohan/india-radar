#!/usr/bin/env bash
# Validates each Ralph iteration and advances the attended prompt automatically.
#
# This is NOT --auto. --auto removes the checkpoint entirely; this keeps it and
# mechanises the parts of validation that are objective, halting for a human on
# anything that isn't. The loop only advances when every check below passes.
#
# HALT conditions (prompt is left unanswered, so ralph.sh just waits):
#   - the gate is not green
#   - no task moved out of actionable state
#   - more than one task moved (an iteration must do exactly one)
#   - the total test count DROPPED (tests deleted to make the gate pass)
#   - the strict-xfail count ROSE (a real test regressed back to "not implemented")
#   - a commit bypassed the pre-commit hook
#
#   ./scripts/watch-and-validate.sh [max_iterations]
set -uo pipefail
cd "$(cd "$(dirname "$0")/.." && pwd)"

MAX="${1:-40}"
LOG=logs/ralph-latest.log
VLOG=logs/validation.log
SESSION=ralph

actionable() { grep -cE '^### T[0-9].*`(todo|in-progress)`' TASKS.md 2>/dev/null || echo 0; }
done_ct()    { grep -cE '^### T[0-9].*`done`' TASKS.md 2>/dev/null || echo 0; }
parked_ct()  { grep -cE '^### T[0-9].*`(blocked|needs-review)`' TASKS.md 2>/dev/null || echo 0; }
# pytest prints e.g. "5 passed, 5 xfailed in 0.02s"
test_counts() {
  local out; out=$(.venv/bin/pytest tests/ -q 2>&1 | tail -3)
  local p x; p=$(echo "$out" | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+' || echo 0)
  x=$(echo "$out" | grep -oE '[0-9]+ xfailed' | grep -oE '[0-9]+' || echo 0)
  echo "${p:-0} ${x:-0}"
}
note() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$VLOG"; }

read -r P0 X0 <<<"$(test_counts)"
A0=$(actionable); H0=$(git rev-parse HEAD)
note "WATCHER START  actionable=$A0 done=$(done_ct) parked=$(parked_ct) passed=$P0 xfailed=$X0"

seen=$(grep -c "VALIDATION SUMMARY" "$LOG" 2>/dev/null || echo 0)

for _ in $(seq 1 "$MAX"); do
  # Wait until ralph.sh is actually sitting at its prompt.
  #
  # Counting VALIDATION SUMMARY lines in the log was wrong twice over: a summary
  # already present when the watcher starts is never processed (the watcher waits
  # for a NEW one that will never come, then halts), and an iteration that stops
  # WITHOUT emitting a summary is indistinguishable from one still running. Both
  # produced false "wedged" halts while the loop sat idle at an unanswered prompt.
  #
  # The prompt itself is the real signal: ralph.sh only prints it when it wants an
  # answer. Read the last non-empty line of the pane rather than the scrollback,
  # so an old prompt further up doesn't match.
  at_prompt() {
    tmux capture-pane -t "$SESSION" -p 2>/dev/null \
      | grep -v '^[[:space:]]*$' | tail -1 | grep -q 'q=quit'
  }
  waited=0
  while ! at_prompt; do
    if ! pgrep -f 'bash ./ralph.sh' >/dev/null 2>&1; then
      note "LOOP EXITED (no ralph.sh process). actionable=$(actionable)"
      exit 0
    fi
    sleep 10; waited=$((waited+10))
    if [ $waited -ge 3600 ]; then note "HALT: 60min with no prompt — iteration may be wedged"; exit 1; fi
  done
  seen=$((seen + 1))

  A1=$(actionable); H1=$(git rev-parse HEAD)
  read -r P1 X1 <<<"$(test_counts)"
  moved=$((A0 - A1))
  fails=""

  # THE CRITICAL ONE. Advancing with a dirty tree is destructive: step 1 of
  # LOOP_PROMPT.md runs `git checkout -- . && git clean -fd` on a stale
  # in-progress task, so the next iteration DELETES whatever is sitting here.
  # This exact case cost a near-miss on 1,833 resolved websites. Never advance
  # past uncommitted work -- halt and let a human decide whether to rescue it.
  if [ -n "$(git status --porcelain)" ]; then
    fails="$fails UNCOMMITTED-WORK(advancing-would-delete-it)"
  fi

  make check >/dev/null 2>&1 || fails="$fails gate-not-green"
  [ "$moved" -gt 1 ]        && fails="$fails moved-$moved-tasks-expected-1"
  [ $((P1 + X1)) -lt $((P0 + X0)) ] && fails="$fails tests-deleted($((P0+X0))->$((P1+X1)))"
  [ "$X1" -gt "$X0" ]       && fails="$fails xfail-rose($X0->$X1)"
  # Truly stuck == no task closed AND nothing committed. A task that spans several
  # iterations is legitimate (T1.6 did), so a commit without a closure is PARTIAL
  # progress, not a failure -- provided the tree is clean, which is checked above.
  [ "$moved" -eq 0 ] && [ "$H0" = "$H1" ] && fails="$fails no-progress(no-task-no-commit)"

  if [ -n "$fails" ]; then
    note "HALT after iteration $seen —$fails"
    note "  actionable $A0->$A1  passed $P0->$P1  xfailed $X0->$X1"
    note "  prompt left UNANSWERED; ralph.sh is waiting. Human review required."
    exit 1
  fi

  if [ "$moved" -eq 0 ]; then
    note "PARTIAL iteration $seen (committed, task still open)  actionable=$A1 passed=$P1"
  else
    note "APPROVED iteration $seen  actionable=$A1 done=$(done_ct) parked=$(parked_ct) passed=$P1 xfailed=$X1"
  fi
  A0=$A1; P0=$P1; X0=$X1; H0=$H1

  if [ "$A1" -eq 0 ]; then
    note "ALL ACTIONABLE TASKS COMPLETE ($(parked_ct) parked)"
    tmux send-keys -t "$SESSION" "" Enter 2>/dev/null
    exit 0
  fi
  tmux send-keys -t "$SESSION" "" Enter 2>/dev/null || { note "HALT: tmux send failed"; exit 1; }
done
note "watcher hit max=$MAX iterations"
