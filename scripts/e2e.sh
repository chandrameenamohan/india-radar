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

# Unique per run. The page is served with no Cache-Control, so the browser gives
# it a heuristic freshness lifetime and re-serves the copy it already has for
# this URL -- and the port is fixed, so "this URL" is the same one every run.
# Measured: an e2e run validated an index.html from BEFORE the edit under test,
# reporting "This page reads schema v3" while the file on disk said 4. Every
# behavioural check below still passed against it, which is the dangerous part:
# a green gate that proves nothing about the code just written.
# `fetch(..., {cache:'no-cache'})` in the page covers the JSON, not the document
# that fetches it (FINDINGS T1.2 is the same trap one level down).
RUN="$$-$(date +%s)"
bust() { case "$1" in *\?*) echo "$1&_=$RUN";; *) echo "$1?_=$RUN";; esac; }

open_page() {
  local url; url=$(bust "$1")
  $B network --clear >/dev/null 2>&1
  $B console --clear >/dev/null 2>&1
  $B goto "$url" >/dev/null 2>&1
  $B wait --networkidle >/dev/null 2>&1
  # Two browse daemons on one machine split these commands across two browsers,
  # and the symptom is row diffs that look like site bugs. Name it instead.
  local at; at=$(val 'location.href')
  if [ "$at" != "$url" ]; then
    echo "  FAIL  browser is on [$at], not [$url]"
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
from datetime import date
data = json.load(open('tests/fixtures/companies-e2e.json'))
rows, snapshot = data['companies'], date.fromisoformat(data['snapshot'])
# Days since the round was announced, or None where the source stated no date.
age = lambda r: None if r['date'] is None else (snapshot - date.fromisoformat(r['date'])).days
keep = [r for r in rows if $1]
print('|'.join(r['name'] for r in sorted(keep, key=lambda r: ${2:-(-len(r['roles']), r['name'])})))"; }

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
# Put the sort back, as every filter below puts its own control back. Left on
# `name`, it silently reorders the checks that follow, and `expect`'s default
# key stops describing the page -- which is a failing check for the wrong
# reason, the one kind that gets "fixed" by editing the expectation.
$B select '#sort' 'reqs' >/dev/null 2>&1
$B select '#bracket' 'large' >/dev/null 2>&1
check "filtering by funding bracket" \
  "$(expect "r['amount'] is not None and r['amount'] >= 50_000_000")" "$(rows)"
$B select '#bracket' 'any' >/dev/null 2>&1

# A row whose source stated no round date must not be swept into "funded
# recently" — that is a claim, and the data doesn't make it. Same shape as the
# ambiguous zero: an absent fact is not a convenient default.
$B select '#recency' '90' >/dev/null 2>&1
check "an undated company is not claimed as recently funded" \
  "$(expect "age(r) is not None and age(r) <= 90")" "$(rows)"
$B select '#recency' 'any' >/dev/null 2>&1

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

# T4.1. Every India role is named and linked -- the row is the site's answer to
# "who is hiring, for what, and where do I apply", and a count alone answers only
# the first third. Derived from the dataset, so it stays true as the data grows.
check "an opened row lists every India role, each linked to its own posting" \
  "$($PY -c "
import json
c = json.load(open('tests/fixtures/companies-e2e.json'))['companies']
first = sorted(c, key=lambda r: (-len(r['roles']), r['name']))[0]
print('|'.join(f\"{r['title']} {r['url']}\" for r in first['roles']))")" \
  "$(val '[...document.querySelector(".row[open] .roles").querySelectorAll("li")]
       .map((li)=>`${li.querySelector("a").textContent} ${li.querySelector("a").href}`).join("|")')"

# The ambiguous zero, in badge form. 822 of the 1,112 published India roles state
# no workplace at all -- Greenhouse states one nowhere -- so a site that defaulted
# the blank to "on-site" would be inventing the most common answer for the
# largest provider and showing it as though the company had said it.
check "a role whose board stated no workplace shows no badge" \
  "$($PY -c "
import json
c = json.load(open('tests/fixtures/companies-e2e.json'))['companies']
first = sorted(c, key=lambda r: (-len(r['roles']), r['name']))[0]
print(sum(1 for r in first['roles'] if r['workplace']), 'of', len(first['roles']))")" \
  "$(val '(() => { const ul = document.querySelector(".row[open] .roles");
       return `${ul.querySelectorAll(".tag").length} of ${ul.querySelectorAll("li").length}` })()')"

# No listed company renders an empty location. The dataset holds all three ways
# of being placeless: cities named, "Remote - India" (remote, no city), and a
# board stating only "India" -- which is neither a city nor a remote claim, and
# must still read as a place rather than as a blank cell.
check "no listed company renders an empty location" "0" \
  "$(val '[...document.querySelectorAll(".where")].filter(n=>!n.textContent.trim()).length')"
check "a company whose board states only \"India\" says so, rather than nothing" \
  "India" \
  "$(val '[...document.querySelectorAll(".row")].find((r)=>
       r.querySelector(".name").textContent === "Zeta Placeless").querySelector(".where").textContent')"

# T4.2. The benchmark renders as one line carrying all three things that make it
# readable -- the figure, the sample it averages, and the date the SOURCE last
# recomputed it. The date is the load-bearing one: live figures range from
# today's to nine months old, so a bare number would read as a claim about now.
check "a salary benchmark renders with its sample size and its observation date" \
  "$($PY -c "
import json
c = json.load(open('tests/fixtures/companies-e2e.json'))['companies']
first = sorted(c, key=lambda r: (-len(r['roles']), r['name']))[0]
s = first['salary']
print(s['avg_lpa'], s['reports'], s['observed'], s['source_url'])")" \
  "$(val '(() => { const p = document.querySelector(".row[open] .salary"), t = p.textContent;
       // Read the three facts back out of the rendered line rather than
       // rebuilding it here: the grouping is the browser`s (en-IN groups by
       // lakh), and a check that hardcodes that is testing Intl, not the site.
       return [t.match(/₹([\d.]+)L/)[1],
               t.match(/([\d,]+) reports?\b/)[1].replace(/,/g, ""),
               t.match(/as of (\d{4}-\d{2}-\d{2})\b/)[1],
               p.querySelector("a").href].join(" ") })()')"

# The degraded row, across the whole dataset: absence renders as NOTHING, not as
# "salary unknown". 51 of 116 listed companies have no benchmark, so a row that
# announced its own gap would put that line on half the site.
check "a company with no benchmark renders no salary line at all" \
  "$($PY -c "
import json
c = json.load(open('tests/fixtures/companies-e2e.json'))['companies']
print(sum(1 for r in c if r['salary']), 'of', len(c))")" \
  "$(val '`${document.querySelectorAll(".salary").length} of `
       + document.querySelectorAll(".row").length')"

# T4.4. The registration renders the CIN and the name it was matched to, because
# the name IS the claim: a reader who can see "GAMMA HEALTH INDIA PRIVATE
# LIMITED" under "Gamma Health" can check the join, and one shown a bare CIN
# cannot. The status ships too, and is not always "Active".
check "a matched company renders its CIN, its registered name and its status" \
  "$($PY -c "
import json
c = json.load(open('tests/fixtures/companies-e2e.json'))['companies']
first = sorted(c, key=lambda r: (-len(r['roles']), r['name']))[0]
m = first['mca']
print(m['cin'], m['name'], m['incorporated'][:4], m['city'], m['status'])")" \
  "$(val '(() => { const p = document.querySelector(".row[open] .mca"), t = p.textContent;
       return [p.querySelector(".cin").textContent,
               t.match(/· (.+?) · incorporated/)[1],
               t.match(/incorporated (\d{4})/)[1],
               t.split(" · ").slice(-3)[0],
               t.split(" · ").slice(-2)[0]].join(" ") })()')"

# The degraded row again, for the enrichment where absence is the MAJORITY:
# 84 of 116 listed companies carry no CIN, and most never can -- the register
# slice holds subsidiaries of foreign parents only. So a row without one says
# nothing at all rather than announcing a gap it cannot close.
check "a company with no MCA registration renders no registration line at all" \
  "$($PY -c "
import json
c = json.load(open('tests/fixtures/companies-e2e.json'))['companies']
print(sum(1 for r in c if r['mca']), 'of', len(c))")" \
  "$(val '`${document.querySelectorAll(".mca").length} of `
       + document.querySelectorAll(".row").length')"

# SPEC feature 10's MCA filter, now that a row can carry a CIN.
$B select '#mca' 'matched' >/dev/null 2>&1
check "the MCA filter returns only companies with a registration" \
  "$(expect "r['mca'] is not None")" "$(rows)"
$B select '#mca' 'any' >/dev/null 2>&1
check "clearing the MCA filter restores every company" "$(expect True)" "$(rows)"

# And the site says what the absence means. Without this the badge reads as a
# quality mark, and its absence as a mark against every India-founded company on
# the page -- which is exactly backwards, since they are excluded by the filter
# that built the register slice rather than by anything about them.
check "the site explains that a missing CIN is not a verdict" "1" \
  "$(val '[...document.querySelectorAll("footer p")]
       .filter(p=>/incorporated abroad/.test(p.textContent)).length')"

# SPEC feature 10's remote-only filter, now that a row carries the field. A
# company hiring only on-site in Pune must vanish from it.
$B select '#remote' 'remote' >/dev/null 2>&1
check "the remote filter returns only companies with a remote India role" \
  "$(expect "any(role['workplace'] == 'remote' for role in r['roles'])")" "$(rows)"
$B select '#remote' 'any' >/dev/null 2>&1
check "clearing the remote filter restores every company" "$(expect True)" "$(rows)"
# The absences a directory source ships with (no amount, no letter, no date) must
# read as English. A row that renders "announced null" is the degraded case
# looking broken rather than deliberate.
check "an absent fact never renders as null" "0" \
  "$(val '[...document.querySelectorAll(".row")]
       .filter(n=>/\bnull\b|\bundefined\b|\bNaN\b/.test(n.textContent)).length')"

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
  "$(val '(document.querySelector("#status").textContent.startsWith("This page reads schema v6")
       ? "refused " : "rendered ") + document.querySelectorAll(".row").length + " rows"')"
console_clean "unknown schema"

# 4c visual regression is NOT here. It needs baseline screenshots a human
# approves once (VERIFICATION.md 4c), and an agent approving its own baselines
# would assert nothing. Deliberately outside the gate rather than faked inside it.

[ "$fail" -eq 0 ] && echo "E2E GREEN"
exit $fail
