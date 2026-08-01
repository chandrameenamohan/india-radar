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
# The readiness probe holds the whole page in a variable rather than piping it
# into `grep -q`, and that is measured rather than stylistic: `grep -q` exits the
# instant it matches, curl takes a SIGPIPE for the rest of the body, and under
# `set -o pipefail` the pipeline reports curl's death as the probe's answer. It
# only bites once the page outgrows curl's write buffer -- so the site's redesign
# tripped a probe that had been wrong since it was written, and the symptom was
# "could not serve the site" against a server that was serving it perfectly.
served() {
  case "$(curl -s "$ROOT" 2>/dev/null)" in *'ROLE·ATLAS'*) return 0;; esac
  return 1
}
for _ in $(seq 40); do
  served && break
  sleep 0.1
done
if ! served; then
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
# T5.3, and the assertion is deliberately against the OTHER file: two artifacts
# of one build, agreeing on how much of the corpus that build managed to check.
# A site counting its own rows would say "116 of 116" -- completeness it cannot
# back. Read back out of the rendered sentence because the sentence is what a
# reader gets; the en-IN grouping is the browser's, and is stripped here for the
# same reason the salary check strips it below.
report() { $PY -c "import json;d=json.load(open('data/build-report.json'));print($1)"; }
read -r checked corpus unchecked <<<"$(val '(() =>
     document.querySelector("#integrity").textContent
       .match(/[\d,]+/g).map((n) => n.replace(/,/g, "")).join(" "))()')"
check "the footer's counts are the build report's" \
  "$(report "d['checked'], d['corpus_size'], d['unchecked']")" \
  "$checked $corpus $unchecked"
check "the footer accounts for every company in the corpus" \
  "$(report "d['corpus_size']")" "$(( ${checked:-0} + ${unchecked:-0} ))"

# T8.5's per-country counts against the OTHER artifact, the same shape as the
# footer check above: the site counts the rows it was given, build.py's
# country_counts counted them at the build, and per country the two must be the
# same number. Every one of the fifteen, zeros included -- a country the site
# left out of its list would read as one nobody looked for, which is the one
# thing a zero must never be confusable with.
# The plate index is where the fifteen are listed now (the country <select> went
# with the tab bar): one line per country plate, each stating its count. Both
# sides are sorted because the index is set in the atlas's plate order and
# src.countries lists them in the build's -- the assertion is the SET of fifteen
# names and their counts, which no ordering changes.
check "the country counts are the build report's, zeros included" \
  "$($PY -c "
import json
from src.countries import COUNTRIES
listed = json.load(open('data/build-report.json'))['countries']
print('|'.join(sorted(f'{c} ({listed[c]})' for c in COUNTRIES)))")" \
  "$(val '[...document.querySelectorAll("#pindex .pirow")]
       .map((b) => `${b.querySelector(".pinm").textContent} `
                 + `(${b.querySelector(".pict").textContent.replace(/,/g, "")})`)
       .sort().join("|")')"

# The tally sits inside the status line`s plate stamp now, so it is read off the
# tally itself rather than off the whole line -- which also carries the plate
# number, the index control and the folio mark.
check "the empty snapshot says so instead of implying nothing is hiring" \
  "$($PY -c '
import json
n = len(json.load(open("data/companies.json"))["companies"])
print(f"{n} of {n} companies" if n else
      "This snapshot listed no companies. The build report says why for each one.")')" \
  "$(val '(() => { const scope = document.querySelector("#status .pscope");
       return scope ? scope.nextElementSibling.textContent
                    : document.querySelector("#status > span").textContent })()')"

echo "-- behaviour, over the committed dataset"
open_page "$FIXTURE"
# A register line is `.irow`, and a long register continues in the spread below
# the board, so the rows are both together in document order. `.iname` carries
# the company name as its own text node with the places nested after it -- the
# first child is the name, and nothing else is.
rows() { val '[...document.querySelectorAll("#index .irow, #spreadrows .irow")]
     .map((n) => n.querySelector(".iname").firstChild.textContent).join("|")'; }

# The register renders ONE worked entry at a time (the index is the master, the
# gazetteer sheet the detail), so a claim about absence ACROSS the dataset has to
# walk it: open every entry in turn and count what each one renders. render() is
# synchronous, so the whole walk is one page's work. Returns:
#   <entries with a salary line> <with a registration> <badges: open, closed>
#   <entries rendering a null> <entries walked>
walk() { val '(() => {
     const n = document.querySelectorAll(".irow").length;
     let salary = 0, mca = 0, said = 0, denied = 0, nulls = 0;
     for (let i = 0; i < n; i++) {
       document.querySelectorAll(".irow")[i].click();
       const sheet = document.querySelector("#sheet");
       salary += sheet.querySelectorAll(".salary").length;
       mca += sheet.querySelectorAll(".mca").length;
       said += sheet.querySelectorAll(".tag.open").length;
       denied += sheet.querySelectorAll(".tag.closed").length;
       if (/\bnull\b|\bundefined\b|\bNaN\b/.test(sheet.textContent)) nulls++;
     }
     // Put the sheet back on the first entry, the way every filter check puts
     // its own control back: a walk that left the last entry open would silently
     // re-aim the checks after it at whichever company sorted last.
     if (n) document.querySelectorAll(".irow")[0].click();
     return `${salary} ${mca} ${said} ${denied} ${nulls} ${n}`;
   })()'; }
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

# Row detail. The disclosure is gone: the register is an index, and one worked
# gazetteer entry is filed on the sheet beside it. So the assertion is no longer
# "a row starts closed" -- nothing is collapsed -- but the same fact one level
# up: the entry on the sheet is the entry for the row the reader picked, and it
# carries the board we read and the funding source we cite. It is still about
# what is *visible*: checkVisibility(), not a querySelector.
sheeted() { val '(() => {
     const body = document.querySelector("#sheet .detail");
     if (!body) return "no entry";
     const shown = body.checkVisibility({contentVisibilityAuto: true, visibilityProperty: true});
     const hrefs = [...body.querySelectorAll("a")].map((a) => a.href).join(" ");
     return `${document.querySelector("#sheet h2").textContent} `
          + `${shown ? "shown" : "hidden"} `
          + (hrefs.includes("job-boards.greenhouse.io") ? "board" : "no-board")
          + (hrefs.includes("finsmes.com") ? "+source" : "+no-source");
   })()'; }
# On LOAD, and only here: a gazetteer never opens to a blank plate, so the sheet
# starts on the register's first entry. It is deliberately not re-checked after
# the filters below -- the sheet keeps the reader's PICK while that company is
# still on the board, so "the first entry" stops being the claim the moment a
# reader has chosen one, and a check that demanded it anyway would be demanding
# the page forget where the reader was.
check "the sheet opens on the register's first entry" \
  "$(expect True | cut -d'|' -f1) shown board+source" "$(sheeted)"

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

# A click moves the sheet. Third line rather than first, so a sheet that never
# moved could not pass by standing still.
$B js '(() => document.querySelectorAll(".irow")[2].click())()' >/dev/null 2>&1
check "clicking a row reveals that company's board and its funding source" \
  "$(expect True | cut -d'|' -f3) shown board+source" "$(sheeted)"
$B js '(() => document.querySelectorAll(".irow")[0].click())()' >/dev/null 2>&1

# T4.1. Every role is named and linked -- the entry is the site's answer to
# "who is hiring, for what, and where do I apply", and a count alone answers only
# the first third. Derived from the dataset, so it stays true as the data grows.
# A long board folds its tail behind a "+n more roles" button; the fold is
# pressed first, so this asserts every role is SHOWN and not merely present.
$B click '#sheet .morebtn' >/dev/null 2>&1
check "an opened entry lists every role, each linked to its own posting" \
  "$($PY -c "
import json
c = json.load(open('tests/fixtures/companies-e2e.json'))['companies']
first = sorted(c, key=lambda r: (-len(r['roles']), r['name']))[0]
print('|'.join(f\"{r['title']} {r['url']}\" for r in first['roles']))")" \
  "$(val '[...document.querySelectorAll("#sheet .roles li:not(.more)")]
       .map((li)=>`${li.querySelector("a").textContent} ${li.querySelector("a").href}`).join("|")')"

# The ambiguous zero, in badge form. 822 of the 1,112 published India roles state
# no workplace at all -- Greenhouse states one nowhere -- so a site that defaulted
# the blank to "on-site" would be inventing the most common answer for the
# largest provider and showing it as though the company had said it. Counts the
# workplace badges specifically: T8.5 put the openness badges in the same row and
# a bare `.tag` count would stop being about workplace at all.
check "a role whose board stated no workplace shows no badge" \
  "$($PY -c "
import json
c = json.load(open('tests/fixtures/companies-e2e.json'))['companies']
first = sorted(c, key=lambda r: (-len(r['roles']), r['name']))[0]
print(sum(1 for r in first['roles'] if r['workplace']), 'of', len(first['roles']))")" \
  "$(val '(() => { const ul = document.querySelector("#sheet .roles");
       return `${ul.querySelectorAll(".tag.workplace").length} of `
            + ul.querySelectorAll("li:not(.more)").length })()')"

# No listed company renders an empty location. The dataset holds all three ways
# of being placeless: cities named, "Remote - India" (remote, no city), and a
# board stating only "India" -- which is neither a city nor a remote claim, and
# must still read as a place rather than as a blank cell.
# Counted over the ROWS rather than over the place cells: the register omits the
# cell entirely for a row with nothing to put in it, so counting empty cells
# would score that row as a pass by leaving it out of the count.
check "no listed company renders an empty location" "0" \
  "$(val '[...document.querySelectorAll(".irow")]
       .filter((r) => !(r.querySelector(".iwhere") || {textContent: ""})
                        .textContent.trim()).length')"
check "a company whose board states only \"India\" says so, rather than nothing" \
  "India" \
  "$(val '[...document.querySelectorAll(".irow")].find((r)=>
       r.querySelector(".iname").firstChild.textContent === "Zeta Placeless")
         .querySelector(".iwhere").textContent')"

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
  "$(val '(() => { const p = document.querySelector("#sheet .salary"), t = p.textContent;
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
# One walk of every entry answers this, the registration below, and the null
# check after it -- the sheet shows one entry at a time, so "across the dataset"
# means across the dataset's entries, opened one by one.
read -r wsalary wmca wsaid wdenied wnulls wrows <<<"$(walk)"
check "a company with no benchmark renders no salary line at all" \
  "$($PY -c "
import json
c = json.load(open('tests/fixtures/companies-e2e.json'))['companies']
print(sum(1 for r in c if r['salary']), 'of', len(c))")" \
  "$wsalary of $wrows"

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
  "$(val '(() => { const p = document.querySelector("#sheet .mca"), t = p.textContent;
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
  "$wmca of $wrows"

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
# Both halves of the split sheet: the register lines here, and every gazetteer
# entry from the walk above ($wnulls).
check "an absent fact never renders as null in the register" "0" \
  "$(val '[...document.querySelectorAll(".irow")]
       .filter(n=>/\bnull\b|\bundefined\b|\bNaN\b/.test(n.textContent)).length')"
check "an absent fact never renders as null in an entry" "0" "$wnulls"

echo "-- country plates and openness badges (T8.5)"
# expect_in <countries, | separated, empty for all fifteen> [filter over `r` and
# its in-scope `roles`] -> the names the site should show under that country
# scope, in the order it should show them. A country view counts and sorts on the
# roles it is SHOWING, so the expectation has to as well: a company with four
# roles and one of them in the UK is a one-role row under the UK tab, and sorts
# as one.
#
# The countries arrive as a string and become a set HERE rather than being
# written as a python set literal in the call: bash brace-expands `{'a','b'}`
# straight through the quotes of a command substitution, which turned this check
# into eight failed subprocesses whose empty output matched an empty expectation.
# A vacuous green check is the failure mode worth naming.
expect_in() { $PY -c "
import json
from src.countries import COUNTRIES
named = '''$1'''
scope = set(named.split('|')) if named else set(COUNTRIES)
keep = []
for r in json.load(open('tests/fixtures/companies-e2e.json'))['companies']:
    roles = [role for role in r['roles'] if scope & set(role['countries'])]
    if roles and (${2:-True}):
        keep.append((r, roles))
print('|'.join(r['name'] for r, _ in sorted(keep, key=lambda k: (-len(k[1]), k[0]['name']))))"; }
# The tab strip is gone: the atlas binds sixteen plates, and the chart's own
# country chips are the whole navigation. `plate <Country>` turns to a country's
# plate, `plate` alone returns to Plate 01 -- the whole atlas, what the "All
# countries" tab used to be. The return trip is taken first every time because a
# chip is a TOGGLE: clicking the open plate's chip turns back to Plate 01, so a
# helper that only clicked the chip would flip rather than turn on every second
# call. Plate 01's strip clears the plate unconditionally, which is what makes
# the sequence deterministic.
plate() {
  $B click '#p01' >/dev/null 2>&1
  [ $# -eq 0 ] || $B click "#plate .mk[data-country=\"$1\"]" >/dev/null 2>&1
}
visibility() { val "(() => { const c = document.querySelector('$1')
     .checkVisibility({contentVisibilityAuto: true, visibilityProperty: true});
     return c ? 'shown' : 'hidden' })()"; }

# Every plate, in one pass: the count on a chip is a claim about the rows behind
# it, and a chip that says 6 and shows 4 is the site disagreeing with itself in
# public. All fifteen, zeros included.
# The pass states how many plates it walked rather than reporting an empty list
# of disagreements: a selector that matched nothing would produce that same empty
# list and read as green, which is the vacuous check this file names elsewhere.
check "each country plate shows as many companies as its chip claims" \
  "$($PY -c 'from src.countries import COUNTRIES; print(len(COUNTRIES), "plates agree")')" \
  "$(val '(() => {
       const chips = [...document.querySelectorAll("#plate .mk")];
       const bad = [];
       for (const chip of chips) {
         chip.click();
         const rows = document.querySelectorAll(".irow").length;
         const says = +chip.querySelector("b").textContent.replace(/,/g, "");
         if (rows !== says) bad.push(`${chip.dataset.country} says ${says}, shows ${rows}`);
       }
       document.querySelector("#p01").click();          // back to Plate 01
       return bad.length ? bad.join("; ") : `${chips.length} plates agree`;
     })()')"

plate India
check "a country plate shows only companies with a role in that country" \
  "$(expect_in India)" "$(rows)"
# The signature invariant of the wider radar, in the form SPEC feature 16 states
# it: a company hiring only in Berlin is not a company hiring in Japan, and the
# Japan plate is where that is provable.
plate Japan
check "a company with only a Berlin role never appears under Japan" \
  "$(expect_in Japan)" "$(rows)"
# And the empty plate says WHICH country was empty. "No company matches these
# filters" would be the ambiguous zero: it reads as a filter to clear rather than
# as what it is -- we read the boards and none of them was hiring there. The
# bearing that follows ("Most of the register sits on Plate NN") is the plate's
# way onward and is checked below on its own.
check "an empty country says which country was empty" \
  "No company we could check had an open role in Japan on this snapshot — a plate we read, with nobody hiring." \
  "$(val 'document.querySelector("#status > span").textContent
       .split(" Most of the register")[0]')"
# The bearing itself: an empty plate points at where the register's mass actually
# is, and it must be the register's own biggest country and its own count -- a
# hardcoded "India" would stop being true the day the data moves.
check "an empty plate gives a bearing to where the register is" \
  "$($PY -c "
import json
from collections import Counter
rows = json.load(open('tests/fixtures/companies-e2e.json'))['companies']
seen = Counter(x for r in rows for x in r['countries'])
name, n = seen.most_common(1)[0]
print(f'{name} — {n} of its {len(rows)} companies.')")" \
  "$(val '(() => { const t = document.querySelector("#status > span").textContent;
       const m = t.match(/Most of the register sits on Plate \d+ · (.+)$/);
       return m ? m[1] : t })()')"

# A European plate. There is no Europe GROUP any more -- the atlas binds one
# plate per country and Plate 01 for all fifteen -- so the grouping check becomes
# what the group was there to prove in the first place: a plate shows exactly the
# companies with a role in its own country, for a country in the inset as much as
# for one on the band.
plate Germany
check "a European plate shows only companies with a role in that country" \
  "$(expect_in Germany)" "$(rows)"

# The India-only enrichments and the filters over them, off India (SPEC v2). An
# average India CTC beside a list of London roles is the site inventing a fact,
# and a city filter still holding "Bengaluru" while invisible is a tab that shows
# nothing for a reason the reader cannot see.
plate "United Kingdom"
check "the India-only filters are hidden where India is not in view" "hidden hidden" \
  "$(visibility '#city') $(visibility '#mca')"
# Every entry on the plate, not just the one on the sheet: an enrichment that
# only stayed away from the first company would still be the site inventing a
# fact about the second.
read -r ukwsalary ukwmca _ _ _ _ <<<"$(walk)"
check "no India enrichment renders on a country view without India in it" "0 salary 0 mca" \
  "$ukwsalary salary $ukwmca mca"
# ...and the same company under a view that does include India keeps both, so the
# check above is about the view and not about a company with nothing to render.
plate India
check "the same company renders its India enrichments where India is in view" "1 salary 1 mca" \
  "$(val '(() => { [...document.querySelectorAll(".irow")].find((n) =>
         n.querySelector(".iname").firstChild.textContent === "Theta Global").click();
       const sheet = document.querySelector("#sheet");
       return `${sheet.querySelectorAll(".salary").length} salary `
            + `${sheet.querySelectorAll(".mca").length} mca` })()')"

# Why this row is here, visibly: under a country view the row counts, locates and
# lists the roles in that country. A UK row that said "2 roles" and "Bengaluru"
# would be the site answering a question nobody asked.
# The register line names places the way a register does -- "London", not
# "London, United Kingdom" -- and the gazetteer entry below prints them in full,
# so the expectation is shortened here the same way the line is.
plate "United Kingdom"
check "a country view counts and locates a company by the roles it is showing" \
  "$($PY -c "
import json
rows = json.load(open('tests/fixtures/companies-e2e.json'))['companies']
row = [r for r in rows if 'United Kingdom' in r['countries']][0]
roles = [x for x in row['roles'] if 'United Kingdom' in x['countries']]
short = lambda p: p if '—' in p else p.split(',')[0].strip()
where = list(dict.fromkeys(short(place) for x in roles for place in x['locations']))
print('|'.join([row['name'], f\"{len(roles)} {'role' if len(roles) == 1 else 'roles'}\",
                ' · '.join(where)]))")" \
  "$(val '(() => { const r = document.querySelector(".irow");
       return [r.querySelector(".iname").firstChild.textContent,
               r.querySelector(".ireqs").textContent,
               r.querySelector(".iwhere").textContent].join("|") })()')"
$B js '(() => document.querySelectorAll(".irow")[0].click())()' >/dev/null 2>&1
check "a country view says how many of the board's roles it is showing" \
  "$($PY -c "
import json
rows = json.load(open('tests/fixtures/companies-e2e.json'))['companies']
row = [r for r in rows if 'United Kingdom' in r['countries']][0]
print(sum(1 for x in row['roles'] if 'United Kingdom' in x['countries']), len(row['roles']))")" \
  "$(val '(() => { const t = [...document.querySelectorAll("#sheet .detail p")]
         .find((p) => /open roles?\b/.test(p.textContent)).textContent;
       return [t.match(/(\d+) open roles?\b/)[1],
               t.match(/of (\d+) on this board\b/)[1]].join(" ") })()')"

plate
# The openness badges, counted across the whole dataset: exactly as many badges
# as there are stated verdicts, in each direction. This is where "unknown is
# never rendered as no" is provable rather than asserted -- a silence rendered as
# a badge of either colour breaks one of these two numbers, and the fixture holds
# all three verdicts for both fields.
check "a badge renders for every stated verdict and for no silence" \
  "$($PY -c "
import json
roles = [x for r in json.load(open('tests/fixtures/companies-e2e.json'))['companies']
         for x in r['roles']]
said = lambda verdict: sum(1 for x in roles for f in ('visa', 'hire_from_abroad')
                           if x[f] == verdict)
print(f\"{said('yes')} open {said('no')} closed\")")" \
  "$(read -r _ _ said denied _ _ <<<"$(walk)"; echo "$said open $denied closed")"
# And the site says what a missing badge means, for the same reason it says what
# a missing CIN means: 92% of postings state nothing, so silence is the majority
# case and a reader who reads it as "no" reads the site wrong.
check "the site explains that a missing openness badge is not a no" "1" \
  "$(val '[...document.querySelectorAll("footer p")]
       .filter((p) => /did not say/.test(p.textContent)).length')"

# SPEC feature 15's filter: visa yes OR hire_from_abroad yes.
$B select '#openness' 'open' >/dev/null 2>&1
check "the open-to-foreign-hires filter returns only companies whose postings said yes" \
  "$(expect_in '' "any(x['visa'] == 'yes' or x['hire_from_abroad'] == 'yes' for x in roles)")" \
  "$(rows)"
# Per country, like everything else in a country view: a company that sponsors in
# London has said nothing about its Bengaluru role, and must not appear under the
# India plate as though it had.
plate India
check "openness is read off the roles in view, not off the whole company" \
  "$(expect_in India "any(x['visa'] == 'yes' or x['hire_from_abroad'] == 'yes' for x in roles)")" \
  "$(rows)"
plate
$B select '#openness' 'any' >/dev/null 2>&1
check "clearing the open-to-foreign-hires filter restores every company" "$(expect True)" "$(rows)"

# 4d accessibility basics: every control reachable and named. Not an audit.
check "every control has an accessible name" "" \
  "$(val '[...document.querySelectorAll("input,select")].filter(c=>!c.labels.length
       && !c.getAttribute("aria-label")).map(c=>c.id).join(",")')"
# The plate chips and the plate index rows are <button>s, so they are
# keyboard-reachable by construction; what has to be checked is that a chip whose
# visible label is a dot and a count still NAMES its country, and that the
# pressed state a sighted reader sees is the one a screen reader gets. Both
# navigations are checked, because either one alone is a way to every plate.
# Named the same way: the count is stated, so a mistyped selector cannot pass by
# finding no controls to fault. Two ways to every plate, fifteen plates each.
check "every plate control has an accessible name" \
  "$($PY -c 'from src.countries import COUNTRIES; print(2 * len(COUNTRIES), "named")')" \
  "$(val '(() => { const c = [...document.querySelectorAll("#plate .mk, #pindex .pirow")];
       const unnamed = c.filter((b) => !(b.getAttribute("aria-label") || b.textContent).trim());
       return unnamed.length
         ? unnamed.map((b) => b.dataset.country || b.textContent).join(",")
         : `${c.length} named` })()')"
# One plate is open at a time and the chart says which: on a country plate its
# chip is pressed, on Plate 01 the index strip is. Never both, never neither --
# the red chip is the whole navigation's only state, and a reader who cannot see
# red must still be told which page the atlas is open at.
check "exactly one plate control is pressed on Plate 01" "1" \
  "$(val 'document.querySelectorAll("#plate [aria-pressed=true]").length')"
plate Japan
check "exactly one plate control is pressed on a country plate" "1 Japan" \
  "$(val '(() => { const on = document.querySelectorAll("#plate [aria-pressed=true]");
       return `${on.length} ${on.length === 1 ? on[0].dataset.country : ""}` })()')"
plate
# The disclosure rows are gone with the tab strip: the register is an index of
# <button>s into the gazetteer sheet. Buttons are focusable by construction, so
# what this holds is that EVERY listed company has one -- a register line that
# rendered as a plain div would be a company no keyboard could reach.
check "every register line is a keyboard-reachable button" \
  "$(expect True | awk -F'|' '{print NF}') buttons" \
  "$(val '(() => { const rows = [...document.querySelectorAll(".irow")];
       return `${rows.filter((r) => r.tagName === "BUTTON" && !r.disabled).length} `
            + "buttons" })()')"

# Search runs last of the interactions: `browse fill` cannot pass an empty value,
# so a page load is the only way back from "matches nothing" -- and a reload here
# would throw away the console history the next check is about to read.
$B fill '#q' 'beta' >/dev/null 2>&1
check "search narrows by name" "$(expect "'beta' in r['name'].lower()")" "$(rows)"
$B fill '#q' 'no-such-company' >/dev/null 2>&1
check "a filter that matches nothing says so" "No company matches these filters." \
  "$(val 'document.querySelector("#status > span").textContent')"

console_clean "after interaction"

# A file whose schema the page doesn't know must not be rendered field-by-field
# and hoped over. build-report.json stands in for it: real, committed, and
# carrying no schema_version at all.
echo "-- a dataset this page doesn't know how to read"
open_page "$ROOT?data=../data/build-report.json"
check "an unknown schema is refused, not rendered" "refused 0 rows" \
  "$(val '(document.querySelector("#status").textContent.startsWith("This page reads schema v8")
       ? "refused " : "rendered ") + document.querySelectorAll(".irow").length + " rows"')"
# And the footer goes with it. A count left over from the last dataset, sitting
# under a refusal to render this one, is the site stating a coverage figure for a
# build it just declined to read.
check "a refused dataset leaves the footer's counts blank rather than stale" "" \
  "$(val 'document.querySelector("#integrity").textContent')"
console_clean "unknown schema"

# 4c visual regression is NOT here. It needs baseline screenshots a human
# approves once (VERIFICATION.md 4c), and an agent approving its own baselines
# would assert nothing. Deliberately outside the gate rather than faked inside it.

[ "$fail" -eq 0 ] && echo "E2E GREEN"
exit $fail
