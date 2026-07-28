#!/usr/bin/env bash
# E2E: drives the real site via gstack browse. See VERIFICATION.md layer 4.
set -uo pipefail
cd "$(dirname "$0")/.."

B="$HOME/.claude/skills/gstack/browse/dist/browse"
if [ ! -x "$B" ]; then
  echo "SKIP: browse not found; e2e cannot run here (expected in CI)"
  exit 0
fi
if [ ! -f site/index.html ]; then
  echo "FAIL: site/index.html does not exist yet (T5.2)"
  exit 1
fi

fail=0
$B goto "file://$(pwd)/site/index.html" >/dev/null 2>&1

# 4a console-clean: zero errors, zero failed requests.
errs=$($B console --errors 2>/dev/null | grep -vc '^---' || true)
if [ "${errs:-0}" -gt 0 ]; then echo "FAIL console-clean: $errs console errors"; fail=1; fi
if $B network 2>/dev/null | grep -qE '→ [45][0-9][0-9]'; then
  echo "FAIL console-clean: failed network requests"; fail=1
fi

# 4b behavioural / 4c visual / 4d a11y -- land with T5.2.
echo "FAIL: behavioural, visual-regression and a11y checks not implemented (T5.2)"
fail=1

exit $fail
