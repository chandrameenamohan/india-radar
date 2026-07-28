#!/usr/bin/env bash
# Boots the dev environment and runs a smoke test. Safe to re-run.
set -uo pipefail
cd "$(dirname "$0")"

VENV=.venv
ok=0; warn=0

say()  { printf "%-42s %s\n" "$1" "$2"; }
good() { say "$1" "OK";   ok=$((ok+1)); }
bad()  { say "$1" "WARN -- $2"; warn=$((warn+1)); }

echo "=== init: environment ==="

# 1. venv + tooling
if [ ! -d "$VENV" ]; then
  echo "creating $VENV ..."
  python3 -m venv "$VENV" || { echo "FATAL: could not create venv"; exit 1; }
fi
"$VENV/bin/pip" install --quiet --upgrade pip >/dev/null 2>&1
"$VENV/bin/pip" install --quiet ruff mypy pytest >/dev/null 2>&1
for t in ruff mypy pytest; do
  if [ -x "$VENV/bin/$t" ]; then good "$t"; else bad "$t" "install failed"; fi
done

# 2. MCA key -- warn only. MCA is enrichment and MUST degrade to "no badge".
if [ -f .env ] && grep -qE '^DATA_GOV_IN_KEY=.+' .env; then
  good "DATA_GOV_IN_KEY"
else
  bad "DATA_GOV_IN_KEY" "MCA badge disabled; everything else still works"
fi

# 3. browse -- warn only. Without it, e2e skips; lint/typecheck/unit still gate.
BROWSE="$HOME/.claude/skills/gstack/browse/dist/browse"
if [ -x "$BROWSE" ]; then good "browse (e2e driver)"; else bad "browse" "e2e will skip"; fi

# 4. layout
mkdir -p src tests scripts data site logs
[ -f tests/__init__.py ] || touch tests/__init__.py

echo ""
echo "=== init: smoke test ==="
# --smoke drives the whole spine (build -> validate -> write) over a fixture
# board, offline, in milliseconds. It writes data/companies.smoke.json, NOT the
# published data/companies.json: a smoke test that overwrites the shipped
# artifact with fixture-derived rows is the exact failure T6.4 exists to prevent.
if "$VENV/bin/python" -m src.build --smoke >/dev/null 2>&1; then
  if [ -s data/companies.smoke.json ]; then
    good "smoke build -> data/companies.smoke.json"
  else
    bad "smoke build" "ran but produced no data/companies.smoke.json"
  fi
else
  bad "smoke build" "src/build.py --smoke failed"
fi

echo ""
echo "ready: $ok   warnings: $warn"
echo "next:  make check    (expected RED until tasks land -- see VERIFICATION.md)"
