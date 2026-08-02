#!/usr/bin/env bash
# E2E for the Worker: drives a RUNNING server over HTTP, not the handler in a
# vacuum. See VERIFICATION.md layer 5.
#
# Two runners, deliberately:
#   wrangler  -- real workerd, what actually ships. Needs macOS 13.5+ or Linux.
#   node      -- worker/serve.mjs, the same handler over node:http. Exists so
#                these assertions can be exercised on a machine where workerd
#                refuses to start, because a check whose first real run is in CI
#                is a check nobody has tested.
#
# Usage: scripts/worker-e2e.sh [wrangler|node]
set -uo pipefail
cd "$(dirname "$0")/.."

RUNNER="${1:-wrangler}"
PORT=8788
BASE="http://127.0.0.1:$PORT"
LOG=$(mktemp)
pass=0
fail=0

check() { # check <name> <expected> <actual>
  if [ "$2" = "$3" ]; then
    echo "  ok    $1"
    pass=$((pass + 1))
  else
    echo "  FAIL  $1 -- expected '$2', got '$3'"
    fail=$((fail + 1))
  fi
}

case "$RUNNER" in
  wrangler)
    if ! command -v npx >/dev/null 2>&1; then
      echo "SKIP: npx not found; worker e2e cannot run here"
      exit 0
    fi
    npx --yes wrangler@4 dev --config worker/wrangler.toml --port "$PORT" >"$LOG" 2>&1 &
    ;;
  node)
    PORT="$PORT" node worker/serve.mjs >"$LOG" 2>&1 &
    ;;
  *)
    echo "FAIL: unknown runner '$RUNNER'"
    exit 1
    ;;
esac
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null; wait $SERVER_PID 2>/dev/null' EXIT

# Wait for it, rather than sleeping a guessed interval.
ready=0
for _ in $(seq 1 40); do
  if curl -sf -o /dev/null --max-time 2 "$BASE/api/me" 2>/dev/null || \
     [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 2 "$BASE/api/me" 2>/dev/null)" != "000" ]; then
    ready=1
    break
  fi
  sleep 1
done

if [ "$ready" -eq 0 ]; then
  # workerd below macOS 13.5 lands here. A skip, not a pass -- and it names why.
  if grep -qi 'unsupported macos version' "$LOG"; then
    echo "SKIP: workerd cannot run on this macOS (needs 13.5+). Try: scripts/worker-e2e.sh node"
    exit 0
  fi
  echo "FAIL: server did not become ready"
  tail -20 "$LOG"
  exit 1
fi

echo "==> worker e2e ($RUNNER)"

status() { curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$@"; }
header() { curl -s -D- -o /dev/null --max-time 5 "$@" | tr -d '\r' | grep -i "^$1:" | cut -d' ' -f2-; }

# Refusals. Every one of these must be 401 and must be indistinguishable -- a
# different status per reason turns this endpoint into a user-id oracle.
check "no token is refused"        401 "$(status "$BASE/api/me")"
check "garbage token is refused"   401 "$(status -H 'Authorization: Bearer not.a.jwt' "$BASE/api/me")"
check "empty bearer is refused"    401 "$(status -H 'Authorization: Bearer ' "$BASE/api/me")"
check "wrong scheme is refused"    401 "$(status -H 'Authorization: Basic abc' "$BASE/api/me")"

bodies=$(for h in "" "Authorization: Bearer not.a.jwt" "Authorization: Basic abc"; do
  if [ -z "$h" ]; then curl -s --max-time 5 "$BASE/api/me"; else curl -s --max-time 5 -H "$h" "$BASE/api/me"; fi
  echo
done | sort -u | wc -l | tr -d ' ')
check "refusals are indistinguishable" 1 "$bodies"

# Routing.
check "unknown path is 404"        404 "$(status "$BASE/")"
check "nested path is 404"         404 "$(status "$BASE/api/me/secrets")"
check "POST is 405"                405 "$(status -X POST "$BASE/api/me")"

# CORS -- the allowlist is a security control here, because the API is on its own
# hostname (roleatlas.sennamind.com is a DNS-only CNAME to GitHub Pages).
check "look-alike origin gets no ACAO" "" \
  "$(header 'access-control-allow-origin' -H 'Origin: https://evil-roleatlas.sennamind.com' "$BASE/api/me")"
check "suffix-attack origin gets no ACAO" "" \
  "$(header 'access-control-allow-origin' -H 'Origin: https://roleatlas.sennamind.com.evil.com' "$BASE/api/me")"
check "allowlisted origin is echoed exactly" "https://roleatlas.sennamind.com" \
  "$(header 'access-control-allow-origin' -H 'Origin: https://roleatlas.sennamind.com' "$BASE/api/me")"
check "preflight is 204" 204 \
  "$(status -X OPTIONS -H 'Origin: https://roleatlas.sennamind.com' "$BASE/api/me")"

echo
if [ "$fail" -gt 0 ]; then
  echo "WORKER E2E RED -- $fail failed, $pass passed"
  exit 1
fi
echo "WORKER E2E GREEN -- $pass checks"
