#!/usr/bin/env bash
# E2E: drives the real site via gstack browse. See VERIFICATION.md layer 4.
#
# Over HTTP, not file://, and that is measured rather than stylistic: a file://
# page cannot fetch() a sibling JSON at all ("URL scheme file is not supported",
# FINDINGS T5.2). GitHub Pages serves over HTTP anyway, so this is also the
# deployment we actually ship.
set -uo pipefail
cd "$(dirname "$0")/.."

B="$HOME/.claude/skills/gstack/browse/dist/browse"
if [ ! -x "$B" ]; then
  echo "SKIP: browse not found; e2e cannot run here (expected in CI)"
  exit 0
fi
if [ ! -f site/index.html ]; then
  echo "FAIL: site/index.html is missing"
  exit 1
fi

PY=.venv/bin/python
[ -x "$PY" ] || PY=python3
PORT=8731
ROOT="http://127.0.0.1:$PORT/site/index.html"
# The site's own data is legitimately empty until slug resolution improves
# (T5.1), so behaviour is driven against a committed dataset instead. It is held
# to the shipped schema by test_the_e2e_dataset_is_a_file_this_build_could_have_written.
FIXTURE="$ROOT?data=../tests/fixtures/companies-e2e.json"

$PY -m http.server "$PORT" --bind 127.0.0.1 >/dev/null 2>&1 &
srv=$!
trap 'kill $srv 2>/dev/null' EXIT
for _ in $(seq 40); do
  curl -s "$ROOT" 2>/dev/null | grep -q 'INDIA·RADAR' && break
  sleep 0.1
done
if ! curl -s "$ROOT" 2>/dev/null | grep -q 'INDIA·RADAR'; then
  echo "FAIL: could not serve the site on port $PORT"
  exit 1
fi

fail=0
check() { # label expected actual
  if [ "$2" = "$3" ]; then echo "  ok    $1"; else echo "  FAIL  $1: expected [$2] got [$3]"; fail=1; fi
}
val() { $B js "$1" 2>/dev/null; }
open_page() {
  $B network --clear >/dev/null 2>&1
  $B console --clear >/dev/null 2>&1
  $B goto "$1" >/dev/null 2>&1
  $B wait --networkidle >/dev/null 2>&1
  # Two browse daemons on one machine split these commands across two browsers,
  # and the symptom is row diffs that look like site bugs. Name it instead.
  local at; at=$(val 'location.href')
  if [ "$at" != "$1" ]; then
    echo "  FAIL  browser is on [$at], not [$1]"
    echo "        a second browse daemon is likely serving these commands; try: browse stop"
    fail=1
  fi
}

# 4a console-clean. Zero console errors, zero non-2xx responses -- the "looks
# fine, secretly broken" case. `console --errors` prints "(no console errors)"
# when clean, so count the error lines rather than the output lines.
console_clean() { # label
  local errs
  errs=$($B console --errors 2>/dev/null | grep -c '\[error\]')
  check "$1 zero console errors" "0" "$errs"
  local bad
  bad=$($B network 2>/dev/null | grep -cE '→ [45][0-9][0-9]')
  check "$1 zero failed requests" "0" "$bad"
}

echo "-- the published site (its own data/companies.json)"
open_page "$ROOT"
console_clean "published"

# 4b behavioural. Assertions on rendered state, and every expectation is derived
# from the data rather than hardcoded, so the checks stay true as the data grows.
check "snapshot date is visible" \
  "$($PY -c 'import json;print(json.load(open("data/companies.json"))["snapshot"])')" \
  "$(val 'document.querySelector("#snapshot").textContent')"
check "the empty snapshot says so instead of implying nothing is hiring" \
  "$($PY -c '
import json
n = len(json.load(open("data/companies.json"))["companies"])
print(f"{n} of {n} companies" if n else
      "This snapshot listed no companies. The build report says why for each one.")')" \
  "$(val 'document.querySelector("#status").textContent')"

echo "-- behaviour, over the committed dataset"
open_page "$FIXTURE"
rows() { val '[...document.querySelectorAll(".name")].map(n=>n.textContent).join("|")'; }
# expect <python-row-filter> [python-sort-key] -> the names the site should show,
# in the order it should show them. Default order is the site's: India roles
# descending, ties by name. Every expectation below is derived from the dataset,
# so a check states an invariant rather than freezing today's answer.
expect() { $PY -c "
import json
rows = json.load(open('tests/fixtures/companies-e2e.json'))['companies']
keep = [r for r in rows if $1]
print('|'.join(r['name'] for r in sorted(keep, key=lambda r: ${2:-(-r['india_roles'], r['name'])})))"; }

check "every company renders" "$(expect True)" "$(rows)"

# The signature invariant, in the one form this schema can express it: a company
# hiring only in Pune must vanish under Bengaluru. (SPEC's Warsaw example can't
# arise -- a company with no India role never becomes a row at all.)
$B select '#city' 'Bengaluru' >/dev/null 2>&1
check "filtering to a city returns only companies with a role in that city" \
  "$(expect "'Bengaluru' in r['cities']")" "$(rows)"
$B select '#city' 'any' >/dev/null 2>&1
check "clearing the city filter restores every company" "$(expect True)" "$(rows)"

$B select '#sort' 'name' >/dev/null 2>&1
check "sorting by name" "$(expect True "r['name']")" "$(rows)"
$B select '#bracket' 'large' >/dev/null 2>&1
check "filtering by funding bracket" "$(expect "r['amount'] >= 50_000_000")" "$(rows)"
$B select '#bracket' 'any' >/dev/null 2>&1

# Row detail. A closed row's children are in the DOM, so the assertion has to be
# about what is *visible* -- checkVisibility() sees through the collapse, a
# height or a querySelector does not.
detail() { val '(() => {
     const row = document.querySelector(".row"), body = row.querySelector(".detail");
     const shown = body.checkVisibility({contentVisibilityAuto: true, visibilityProperty: true});
     const hrefs = [...body.querySelectorAll("a")].map((a) => a.href).join(" ");
     return `${row.open ? "open" : "closed"} ${shown ? "shown" : "hidden"} `
          + (hrefs.includes("job-boards.greenhouse.io") ? "board" : "no-board")
          + (hrefs.includes("finsmes.com") ? "+source" : "+no-source");
   })()'; }
check "a row starts closed" "closed hidden board+source" "$(detail)"
$B click '.row:first-of-type summary' >/dev/null 2>&1
check "clicking a row reveals its board and its funding source" "open shown board+source" "$(detail)"
# T4.1 will add per-role links; what must hold already is that no listed company
# renders an empty location. "Remote - India" names no city and must still read
# as a place.
check "no listed company renders an empty location" "0" \
  "$(val '[...document.querySelectorAll(".where")].filter(n=>!n.textContent.trim()).length')"

# 4d accessibility basics: every control reachable and named. Not an audit.
check "every control has an accessible name" "" \
  "$(val '[...document.querySelectorAll("input,select")].filter(c=>!c.labels.length
       && !c.getAttribute("aria-label")).map(c=>c.id).join(",")')"
check "rows are native disclosures, so keyboard-reachable without JS" \
  "$(expect True | awk -F'|' '{print NF}')" \
  "$(val 'document.querySelectorAll(".row > summary").length')"

# Search runs last of the interactions: `browse fill` cannot pass an empty value,
# so a page load is the only way back from "matches nothing" -- and a reload here
# would throw away the console history the next check is about to read.
$B fill '#q' 'beta' >/dev/null 2>&1
check "search narrows by name" "$(expect "'beta' in r['name'].lower()")" "$(rows)"
$B fill '#q' 'no-such-company' >/dev/null 2>&1
check "a filter that matches nothing says so" "No company matches these filters." \
  "$(val 'document.querySelector("#status").textContent')"

console_clean "after interaction"

# A file whose schema the page doesn't know must not be rendered field-by-field
# and hoped over. build-report.json stands in for it: real, committed, and
# carrying no schema_version at all.
echo "-- a dataset this page doesn't know how to read"
open_page "$ROOT?data=../data/build-report.json"
check "an unknown schema is refused, not rendered" "refused 0 rows" \
  "$(val '(document.querySelector("#status").textContent.startsWith("This page reads schema v2")
       ? "refused " : "rendered ") + document.querySelectorAll(".row").length + " rows"')"
console_clean "unknown schema"

# 4c visual regression is NOT here. It needs baseline screenshots a human
# approves once (VERIFICATION.md 4c), and an agent approving its own baselines
# would assert nothing. Deliberately outside the gate rather than faked inside it.

[ "$fail" -eq 0 ] && echo "E2E GREEN"
exit $fail
