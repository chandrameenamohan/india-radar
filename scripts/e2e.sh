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
FIXTURE="$ROOT?data=../tests/fixtures/companies-e2e.json&view=companies"
# The page now opens on the ROLES register, so every check below that speaks
# about companies pins the company one explicitly on $FIXTURE above. That is a
# statement of what each check is about, not a way around the change: the
# default itself is asserted in the roles section, on a URL that sets nothing.
ROLES="$ROOT?data=../tests/fixtures/companies-e2e.json&view=roles"
DEFAULT="$ROOT?data=../tests/fixtures/companies-e2e.json"

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
  #
  # DECODED on both sides, and that is a fix rather than a loosening. T11.1 put
  # Clerk on the page, Clerk normalises the URL through history.replaceState, and
  # the normalisation percent-encodes the slashes in `?data=../tests/...` — so
  # every `?data=` page started reporting itself as the wrong page while
  # rendering exactly the right rows. The question this guard asks is "is the
  # browser on the page I asked for", and two spellings of one URL are the same
  # page: `location.href` still parses to the same `data` param, and the register
  # still renders from it. A guard that cannot tell an encoding from a wrong page
  # answers a question nobody asked.
  local at; at=$(val 'decodeURIComponent(location.href)')
  url=$(printf '%s' "$url" | $PY -c 'import sys,urllib.parse;print(urllib.parse.unquote(sys.stdin.read()),end="")')
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
# The published page opens on the ROLES register, so the tally it states is a
# role count. The check is unchanged in what it is FOR -- a tally must state the
# truth, and an empty snapshot must say so in words rather than render a silent
# zero -- and follows the register's unit rather than pinning a view, because
# this is the number a reader actually meets. `count()` groups en-IN, so the
# commas come off both sides.
tally() { val '(() => { const scope = document.querySelector("#status .pscope");
       return (scope ? scope.nextElementSibling.textContent
                     : document.querySelector("#status > span").textContent)
                .replace(/,/g, "") })()'; }
check "the empty snapshot says so instead of implying nothing is hiring" \
  "$($PY -c '
import json
n = sum(len(c["roles"]) for c in json.load(open("data/companies.json"))["companies"])
print(f"{n} of {n} roles" if n else
      "This snapshot listed no companies. The build report says why for each one.")')" \
  "$(tally)"
# And the same tally under the other register, on the same real data: the switch
# has to change the UNIT, not just the rows. A view that reported roles under
# both labels would pass every row check above and still be lying here.
$B click '#vcompanies' >/dev/null 2>&1
check "switching the register switches the unit the tally counts" \
  "$($PY -c '
import json
n = len(json.load(open("data/companies.json"))["companies"])
print(f"{n} of {n} companies" if n else
      "This snapshot listed no companies. The build report says why for each one.")')" \
  "$(tally)"
$B click '#vroles' >/dev/null 2>&1

# The roles register PAGES: 6,422 lines is a download, not a page. Checked here
# against the real corpus rather than on the fixture, because the fixture holds
# seventeen roles and would never reach the fold at all -- a check that passes by
# never running is the shape of check this repo has been bitten by before. The
# numbers are read off the page's own tally so they stay true as the corpus grows.
printed=$(val 'document.querySelectorAll(".jrow").length')
matched=$(tally | sed 's/ of .*//')
check "the roles register prints one page, not the whole corpus" "true" \
  "$([ "$printed" -le 200 ] && echo true || echo false)"
# The tally counts what MATCHED, never what is printed -- the rule that keeps the
# fold's own count readable and the register the size of the snapshot it reports.
check "the tally states the matched total, not the printed page" "true" \
  "$([ "$matched" -ge "$printed" ] && echo true || echo false)"
if [ "$matched" -gt "$printed" ]; then
  $B click '.spreadfold' >/dev/null 2>&1
  check "the fold prints the next page" "$((printed + 200))" \
    "$(val 'document.querySelectorAll(".jrow").length')"
  # Nothing is dropped and nothing is hidden: the fold says how many are behind it.
  check "the fold says how many roles are behind it" "true" \
    "$(val 'String(/\d[\d,]* further roles/.test(
         (document.querySelector(".spreadfold") || {}).textContent || ""))')"
else
  echo "  --    the roles fold not exercised: this build lists $matched roles, under one page"
fi

# T15.2, against the real artifact. The badge itself is driven on the fixture
# below, because the corpus's own history cannot exercise it: the backfill dates
# 6,505 URLs off git and confirms none of them (a change in what the build LOOKS
# FOR is indistinguishable from a company opening a job, and the history holds
# two), so until a nightly runs there is nothing on this page to badge. What CAN
# be checked here is the rule that matters most, and it is the negative one: the
# page badges exactly as many roles as the artifact confirms, which today is
# none. A regression that badged on the date alone shows up here as 6,422.
badged=$(val 'document.querySelectorAll(".jrow .tag.fresh").length')
# Over the roles PRINTED, in the order the register prints them -- company rank
# first, board order within, one page at a time. Counting the whole corpus would
# compare a page against a file, and this check runs after the fold above has
# turned a page, so how many are printed is read off the page rather than assumed.
onpage=$(val 'document.querySelectorAll(".jrow").length')
confirmable=$($PY -c '
import datetime, json, pathlib, sys
art = pathlib.Path("data/first-seen.json")
if not art.exists():
    print(0); raise SystemExit
seen = json.loads(art.read_text())
data = json.load(open("data/companies.json"))
snap = datetime.date.fromisoformat(data["snapshot"])
fresh = {url for day, buckets in seen["dates"].items() for url in buckets["confirmed"]
         if 0 <= (snap - datetime.date.fromisoformat(day)).days <= 7}
cs = sorted(data["companies"], key=lambda c: (-len(c["roles"]), c["name"]))
roles = [r["url"] for c in cs for r in c["roles"]][: int(sys.argv[1])]
print(sum(1 for url in roles if url in fresh))' "$onpage")
check "the register badges exactly the roles the artifact confirms" \
  "$confirmable" "$badged"
if [ "$confirmable" = "0" ]; then
  echo "  --    the new badge not exercised on real data: the backfill confirms"
  echo "        nothing by design, so this corpus has no confirmed role until a"
  echo "        nightly has run. Driven on the fixture below instead."
fi
# The unconfirmed count is published rather than hidden -- it is the larger half
# of this feature and the reason most of the register carries no badge.
check "the footer states how many roles are dated but unconfirmed" "true" \
  "$(val 'String(/\d[\d,]* are dated but unconfirmed/.test(
       document.querySelector("#firstseen").textContent))')"

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
# T5.4 took the city filter off this list: it is every plate's now, built from
# the plate's own roles (checked in its own section below). The MCA control is
# still the India-only one -- it reads an enrichment the build attaches to India
# rows alone, so off India it has nothing to offer and must not be left holding
# a value nobody can see.
check "the India-only filter is hidden where India is not in view" "hidden" \
  "$(visibility '#mca')"
check "the city filter is not withdrawn off India" "shown" "$(visibility '#city')"
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

echo "-- departments, coverage notes, per-plate cities (T5.4)"
# The department is DERIVED from the role title, so what this holds is not the
# keyword map's taste but its arithmetic: every role in view lands in exactly one
# option, Unclassified included. A role the map lost, or counted twice, breaks
# the sum -- which is precisely what a bucket-by-bucket check would miss, and it
# is derived from the dataset rather than from the page's own totals.
check "the department options account for every role in view" \
  "$($PY -c "
import json
rows = json.load(open('tests/fixtures/companies-e2e.json'))['companies']
print(sum(len(r['roles']) for r in rows), 'roles')")" \
  "$(val '(() => { const o = [...document.querySelectorAll("#dept option")].slice(1);
       return o.reduce((n, x) => n + +x.textContent.match(/— ([\d,]+)/)[1]
         .replace(/,/g, ""), 0) + " roles" })()')"

# The filter cuts at ROLE level: a company stays while one of its roles is in the
# department, and its count then speaks about those roles alone.
# The expectation mirrors only what the FIXTURE's own titles say -- every
# engineering title in it literally reads "Engineer", and the one that also says
# "Support" is a support role under the map's stated precedence (the more
# specialised craft takes a title naming two). Mirroring the whole keyword map
# here would be marking the map's homework with a copy of the map.
eng="'engineer' in x['title'].lower() and 'support' not in x['title'].lower()"
$B select '#dept' 'Engineering' >/dev/null 2>&1
check "the department filter keeps only companies with a role in that department" \
  "$(expect "any($eng for x in r['roles'])" \
            "(-sum(1 for x in r['roles'] if $eng), r['name'])")" "$(rows)"
check "a filtered row counts its roles in that department, not the whole board" \
  "$($PY -c "
import json
rows = json.load(open('tests/fixtures/companies-e2e.json'))['companies']
eng = lambda r: [x for x in r['roles'] if $eng]
top = sorted([r for r in rows if eng(r)], key=lambda r: (-len(eng(r)), r['name']))[0]
n = len(eng(top))
print(f\"{top['name']} {n} {'role' if n == 1 else 'roles'}\")")" \
  "$(val '(() => { const r = document.querySelector(".irow");
       return r.querySelector(".iname").firstChild.textContent + " "
            + r.querySelector(".ireqs").firstChild.textContent })()')"

# A classification that cannot place a title says so instead of guessing, and the
# roles it could not place stay reachable rather than falling off the page. The
# option's own claim is the thing under test: it promises N roles, and selecting
# it must produce exactly those N. Stated as "yes same" rather than as a count,
# so a missing option or an empty register cannot pass by matching a zero.
$B select '#dept' 'Unclassified' >/dev/null 2>&1
check "Unclassified is reachable and delivers every role it claims" "yes same" \
  "$(val '(() => {
       const o = [...document.querySelectorAll("#dept option")].find((x) => x.value === "Unclassified");
       if (!o) return "no option";
       const says = +o.textContent.match(/— ([\d,]+)/)[1].replace(/,/g, "");
       const rows = [...document.querySelectorAll(".irow")];
       const shown = rows.reduce((n, r) => n + +r.dataset.reqs, 0);
       return `${says > 0 && rows.length ? "yes" : "no"} `
            + `${says === shown ? "same" : says + " claimed, " + shown + " shown"}` })()')"
$B select '#dept' 'any' >/dev/null 2>&1
check "clearing the department filter restores every company" "$(expect True)" "$(rows)"

# T9.2. The board states a department for 99.6% of postings, and the site reads it
# ONLY where the title map places nothing — measured, the two disagree 26% of the
# time, over a difference of question rather than of fact. Both halves of that
# rule are asserted here, and the dataset carries the three cases by hand:
# `Clinical Data Lead` (board: Data Science) is the fill, `Clinical Trials
# Coordinator` (board: All Cost Center) is what neither can place, and `Product
# Designer` (board: Engineering) is the one the board must not move.
#
# The fill is asserted through a company the title map alone cannot put here:
# Gamma Health has no data-titled role, so its only way into Department=Data is
# the board's own word.
$B select '#dept' 'Data' >/dev/null 2>&1
check "a board's department fills a title the map cannot place" \
  "$($PY -c "
import json
rows = json.load(open('tests/fixtures/companies-e2e.json'))['companies']
named = sorted(r['name'] for r in rows
               if any(x['department'] == 'Data Science' for x in r['roles']))
print(' '.join(named))")" \
  "$(val '[...document.querySelectorAll(".irow .iname")]
       .map((n) => n.firstChild.textContent)
       .filter((n) => n === "Gamma Health").join(" ")')"

# And the other direction, which is the whole narrowing: every ENGINEERING role in
# view is one the TITLE says is engineering. The dataset holds a Product Designer
# whose board files it under Engineering; if the board's word overruled a placed
# title, this sum would be one too many and the Design option one too few.
$B select '#dept' 'Engineering' >/dev/null 2>&1
check "a stated department never moves a title the map placed" \
  "$($PY -c "
import json
rows = json.load(open('tests/fixtures/companies-e2e.json'))['companies']
print(sum(1 for r in rows for x in r['roles'] if $eng), 'roles')")" \
  "$(val '[...document.querySelectorAll(".irow")]
       .reduce((n, r) => n + +r.dataset.reqs, 0) + " roles"')"
$B select '#dept' 'Design' >/dev/null 2>&1
check "the designer the board calls an engineer is still under Design" \
  "$($PY -c "
import json
rows = json.load(open('tests/fixtures/companies-e2e.json'))['companies']
print(sum(1 for r in rows for x in r['roles'] if 'designer' in x['title'].lower()), 'roles')")" \
  "$(val '[...document.querySelectorAll(".irow")]
       .reduce((n, r) => n + +r.dataset.reqs, 0) + " roles"')"
$B select '#dept' 'any' >/dev/null 2>&1

# The sparse filters state their own coverage while they are set. RAISED and
# FUNDED read fields most of the register does not carry, so a reader who sets
# one watches most of the page leave with no way to know it left over a silence.
# Both numbers are read back out of the printed sentence and both are derived
# from the dataset -- a hardcoded pair would be a claim about a build that moved.
sparse() { $PY -c "
import json
rows = json.load(open('tests/fixtures/companies-e2e.json'))['companies']
print(sum(1 for r in rows if r[$1] is not None), 'of', len(rows))"; }
note() { val "(() => { const p = [...document.querySelectorAll('#fchip .fnote')]
     .find((x) => x.textContent.startsWith('$1'));
     if (!p) return 'no note';
     const m = p.textContent.match(/([\d,]+) of ([\d,]+)/);
     return m ? m[1].replace(/,/g, '') + ' of ' + m[2].replace(/,/g, '') : p.textContent })()"; }
check "the coverage note appears only while a sparse filter is set" "hidden" \
  "$(visibility '#fchip')"
$B select '#bracket' 'large' >/dev/null 2>&1
check "the raised filter states how many companies state an amount" \
  "$(sparse "'amount'")" "$(note Raised)"
$B select '#bracket' 'any' >/dev/null 2>&1
$B select '#recency' '365' >/dev/null 2>&1
check "the funded filter states how many companies state a date" \
  "$(sparse "'date'")" "$(note Funded)"
$B select '#recency' 'any' >/dev/null 2>&1
check "the coverage note leaves with the filter that raised it" "hidden" \
  "$(visibility '#fchip')"

# The city filter is every plate's now, and each plate's list is read off its own
# roles -- so a plate with no India in it offers the cities its own postings name
# and nobody else's. Both the list and the filtering are checked: a control that
# offered Berlin and then ignored it would pass half of this.
plate Germany
check "the city filter populates from a plate with no India in it" \
  "$($PY -c "
import json
rows = json.load(open('tests/fixtures/companies-e2e.json'))['companies']
seen = []
for r in rows:
    for x in r['roles']:
        if x['countries'] == ['Germany']:
            for place in x['locations']:
                city = place.split(',')[0].strip()
                if city not in seen: seen.append(city)
print('|'.join(sorted(seen)))")" \
  "$(val '[...document.querySelectorAll("#city option")].slice(1)
       .map((o) => o.value).sort().join("|")')"
$B select '#city' 'Berlin' >/dev/null 2>&1
check "filtering a country plate by city returns that plate's companies" \
  "$(expect_in Germany)" "$(rows)"
# ...and a city the next plate does not offer is CLEARED by the page turn. Left
# set and invisible it would be a plate showing nothing for a reason the reader
# cannot see -- the same rule the MCA control follows off India.
plate "United Kingdom"
check "a city the turned-to plate does not offer is cleared, not silently kept" "any" \
  "$(val 'document.querySelector("#city").value')"
plate

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

# T5.4: the box reads role titles too. The guard first -- no company NAME in the
# dataset carries this term, so whatever the next check surfaces was surfaced by
# a title and by nothing else. Without the guard the check could pass on a name
# match and prove nothing about roles at all.
$B fill '#q' 'designer' >/dev/null 2>&1
check "no company name carries the role-title term" "" \
  "$(expect "'designer' in r['name'].lower()")"
check "search surfaces a company by its role titles, not only by its name" \
  "$(expect "any('designer' in x['title'].lower() for x in r['roles'])")" "$(rows)"
# And the register says WHY that row is there: a company whose name says nothing
# about the term would otherwise read as a stranger the search let in.
check "the register says how many roles a title match was" \
  "$($PY -c "
import json
rows = json.load(open('tests/fixtures/companies-e2e.json'))['companies']
hit = [r for r in rows if any('designer' in x['title'].lower() for x in r['roles'])][0]
n = sum(1 for x in hit['roles'] if 'designer' in x['title'].lower())
print(f\"{hit['name']} matches {n} {'role' if n == 1 else 'roles'} {n} marked\")")" \
  "$(val '(() => { const r = document.querySelector(".irow");
       return [r.querySelector(".iname").firstChild.textContent,
               r.querySelector(".ihit").textContent,
               document.querySelectorAll("#sheet .roles li.hit").length,
               "marked"].join(" ") })()')"
$B fill '#q' 'no-such-company' >/dev/null 2>&1
check "a filter that matches nothing says so" "No company matches these filters." \
  "$(val 'document.querySelector("#status > span").textContent')"

console_clean "after interaction"

# A file whose schema the page doesn't know must not be rendered field-by-field
# and hoped over. build-report.json stands in for it: real, committed, and
# carrying no schema_version at all.
echo "-- a dataset this page doesn't know how to read"
open_page "$ROOT?data=../data/build-report.json"
# The version is read off the page rather than written here. It was hardcoded as
# v9 and went stale the moment T9.1 bumped the schema to v10 -- and the way it
# failed is the point: the check reported "rendered" for a page that had refused
# correctly, so a GREEN check would have been the lie, not the red one.
schema=$(grep -ao 'const SCHEMA = [0-9]*' site/index.html | grep -o '[0-9]*')
check "an unknown schema is refused, not rendered" "refused 0 rows" \
  "$(val "(document.querySelector('#status').textContent.startsWith('This page reads schema v$schema')
       ? 'refused ' : 'rendered ') + document.querySelectorAll('.irow').length + ' rows'")"
# And the footer goes with it. A count left over from the last dataset, sitting
# under a refusal to render this one, is the site stating a coverage figure for a
# build it just declined to read.
check "a refused dataset leaves the footer's counts blank rather than stale" "" \
  "$(val 'document.querySelector("#integrity").textContent')"
console_clean "unknown schema"

# 4e the account control (T11.1). Three things, in the state every reader arrives
# in: it mounts, it gates nothing, and it costs the page no errors.
#
# The AUTHENTICATED half of the round trip -- sign up, reload, still signed in,
# sign out -- is NOT here, and not because nobody tried. It CANNOT run in this
# harness: the instance has bot protection on, and Cloudflare Turnstile does not
# solve in the headless browser. Measured both ways (learning-tests/clerk_live.py
# finding 7) -- the programmatic path returns `captcha_invalid`, and the real
# modal leaves Continue disabled forever waiting for a token that never arrives.
# Turning bot protection off for the DEVELOPMENT instance is the unblock, and it
# is a dashboard toggle nobody has been asked for yet. Until then session
# persistence is verified by a human, once, and T11.1 says so rather than
# pretending the gate covers it.
echo "-- the account control"
open_page "$ROOT"
check "the account control mounts" "true" \
  "$(val 'document.querySelector("#account").hasAttribute("data-ready")')"
check "a reader who is not signed in is offered a sign-in" "Sign in" \
  "$(val 'document.querySelector("#account").textContent.trim()')"
# The register must be blind to who is reading it. Counting rows before and after
# the sign-in modal opens is the cheapest form that assertion takes: a page that
# started gating rows on a session would differ here first.
before=$(val 'document.querySelectorAll(".irow").length')
$B js 'document.querySelector("#account button").click()' >/dev/null 2>&1
$B wait --networkidle >/dev/null 2>&1
# Poll rather than assert straight after networkidle. Clerk mounts the modal from
# its own bundle AFTER the network settles, so a single read races it -- measured
# once as a red gate that a re-run turned green, which is the worst kind of check:
# one that teaches people their failures are noise. It still has to appear; this
# only stops the test asking before Clerk has answered.
for _ in $(seq 20); do
  case "$(val 'String(!!document.querySelector("[data-clerk-component], .cl-modalContent"))')" in
    true) break;;
  esac
  sleep 0.5
done
check "the sign-in modal opens on our own page, not Clerk's" "true" \
  "$(val 'String(!!document.querySelector("[data-clerk-component], .cl-modalContent"))')"
check "opening it leaves the register untouched" "$before" \
  "$(val 'document.querySelectorAll(".irow").length')"
console_clean "account control"

# 4f the signed-in round trip (T11.1). The one thing a static page genuinely has
# to prove about accounts: a session survives a reload, and signing out ends it.
#
# SIGNS IN, NEVER SIGNS UP, and that is the whole design of this section. Sign-up
# is bot-protected -- Turnstile does not solve headless (clerk_live.py finding 7)
# -- and even with it off, a gate that signs up on every commit would deposit a
# permanent user in a real Clerk instance every time anyone runs `make check`.
# One dedicated account, reused forever, costs nothing and accumulates nothing.
#
# Through Clerk's API rather than its modal DOM: what needs proving is OUR
# session handling, and Clerk's own form is Clerk's to test. Driving their React
# inputs was tried and is a trap -- `fill` sets .value without React seeing it,
# so the form reports an empty password while the DOM shows a full one.
CLERK_EMAIL=$(grep -s '^CLERK_E2E_EMAIL=' .env | cut -d= -f2- | tr -d '[:space:]')
CLERK_PASS=$(grep -s '^CLERK_E2E_PASSWORD=' .env | cut -d= -f2- | tr -d '[:space:]')
if [ -z "${CLERK_EMAIL:-}" ] || [ -z "${CLERK_PASS:-}" ]; then
  echo "-- the signed-in round trip"
  echo "  SKIP  CLERK_E2E_EMAIL / CLERK_E2E_PASSWORD not in .env"
  echo "        (expected on a fresh clone and in CI; see VERIFICATION.md 4f)"
else
  echo "-- the signed-in round trip"
  # JSON-quoted so a password containing quotes or backslashes reaches the page
  # as itself rather than as a syntax error in the middle of a script.
  jsq() { printf '%s' "$1" | $PY -c 'import sys,json;print(json.dumps(sys.stdin.read()),end="")'; }
  # browse's `js` does not await, so the flow parks its answer on window and we
  # poll for it. Same reason the second factor is handled inline: a test account
  # on a `+clerk_test` address takes the fixed code 424242 and no inbox exists.
  settle() { # var
    local v; for _ in $(seq 15); do
      v=$($B js "window.$1" 2>/dev/null)
      [ "$v" != "pending" ] && { echo "$v"; return; }
      sleep 1
    done
    echo "timeout"
  }
  open_page "$FIXTURE"
  anon_rows=$(val 'document.querySelectorAll(".irow").length')
  $B js "window.__in='pending'; (async () => { try {
    let a = await window.Clerk.client.signIn.create({ identifier: $(jsq "$CLERK_EMAIL"), password: $(jsq "$CLERK_PASS") });
    if (a.status === 'needs_second_factor') {
      await a.prepareSecondFactor({ strategy: 'email_code' });
      a = await a.attemptSecondFactor({ strategy: 'email_code', code: '424242' });
    }
    await window.Clerk.setActive({ session: a.createdSessionId });
    window.__in = a.status;
  } catch (e) { window.__in = 'ERR ' + (e.errors ? e.errors.map((x) => x.code).join(',') : e.message); } })()" >/dev/null 2>&1
  check "a reader can sign in" "complete" "$(settle __in)"
  sleep 2
  check "the header stops offering a sign-in" "false" \
    "$(val 'String(document.querySelector("#account").textContent.trim() === "Sign in")')"

  # THE FEATURE. Everything above this line is setup for it: "recognized on
  # return" is the whole of T11.1, and a reload is what return means.
  open_page "$FIXTURE"
  sleep 2
  check "the session survives a full page reload" "true" \
    "$(val 'String(!!window.Clerk.user)')"
  check "and it is the same reader" "$CLERK_EMAIL" \
    "$(val 'window.Clerk.user ? window.Clerk.user.primaryEmailAddress.emailAddress : "(none)"')"
  # SPEC v3's promise from the other side: the signed-out register and the
  # signed-in one are the same register. Signing in must buy a name, not rows.
  check "signing in changes nothing about what the register shows" "$anon_rows" \
    "$(val 'document.querySelectorAll(".irow").length')"

  # signOut NAVIGATES -- so nothing parked on `window` survives it, and this is
  # asserted on the page that comes back rather than polled for. Measured: with
  # Clerk's default afterSignOutUrl the reader lands on `/` with the query string
  # gone, which threw away the plate and the filters. The page pins it to the
  # current URL, and the row count below is what catches a regression: if signing
  # out ever bounces the reader off their fixture page again, this reads 315
  # against the 8 the fixture holds.
  $B js 'window.Clerk.signOut()' >/dev/null 2>&1
  $B wait --networkidle >/dev/null 2>&1
  sleep 3
  check "signing out ends the session" "false" "$(val 'String(!!window.Clerk.user)')"
  check "the header offers a sign-in again" "Sign in" \
    "$(val 'document.querySelector("#account").textContent.trim()')"
  check "signing out leaves the reader on the page they were reading" "$anon_rows" \
    "$(val 'document.querySelectorAll(".irow").length')"
  console_clean "signed-in round trip"
fi

# ---------------------------------------------------------------------------
# THE ROLES REGISTER. Everything above drives the company register, pinned by
# `&view=companies`; this section is the new unit. The checks that matter are
# the ones proving it cuts at the ROLE where the other cuts at the company --
# a view that merely relabelled the same eight rows would pass none of them.
echo "-- the roles register"

# The fixture's roles in the order this register prints them: company rank
# first (open roles, then name -- the default sort), board order within.
xroles() { $PY -c "
import json
data = json.load(open('tests/fixtures/companies-e2e.json'))
cs = sorted(data['companies'], key=lambda c: (-len(c['roles']), c['name']))
print('|'.join(r['title'] for c in cs for r in c['roles'] if $1))"; }

# Asserted where a reader meets it: no parameter, no click, no preference --
# the page a stranger lands on lists jobs.
open_page "$DEFAULT"
check "the page opens on the roles register" "roles" \
  "$(val 'document.querySelector("#viewsw").dataset.unit')"
console_clean "roles register"

open_page "$ROLES"
check "the roles register prints one line per role" "$(xroles True)" "$(rows)"
# Eight companies, seventeen roles. A tally still counting companies would be
# the header describing the other register.
check "the tally counts roles" "17 of 17 roles" \
  "$(val '(document.querySelector("#status").textContent.match(/\d+ of \d+ roles/) || [""])[0]')"

# THE role-level cut. Under the company register a company with one remote job
# keeps every on-site job it has -- correct there, wrong here.
$B select '#remote' 'remote' >/dev/null 2>&1
check "the remote filter returns only remote ROLES" \
  "$(xroles "r['workplace'] == 'remote'")" "$(rows)"
$B select '#remote' 'any' >/dev/null 2>&1
check "clearing the remote filter restores every role" "$(xroles True)" "$(rows)"

# Read off the ROLE's own posting the same way: three roles across three
# companies said yes, and their silent siblings must not ride in on them.
$B select '#openness' 'open' >/dev/null 2>&1
check "the foreign-hires filter reads the role's own posting" \
  "$(xroles "r['visa'] == 'yes' or r['hire_from_abroad'] == 'yes'")" "$(rows)"
$B select '#openness' 'any' >/dev/null 2>&1

# The gutter cites the ROLE's countries, never its company's: Theta Global hires
# in India and the UK, so built off c.countries both its rows would say both.
check "a role line cites its own country, not its company's" "true" \
  "$(val '[...document.querySelectorAll(".jrow")]
       .every((n) => n.dataset.countries.split("|").length === 1) + ""')"

# A plate cuts roles now. Theta keeps its London job here and its Bengaluru one
# on India's plate -- the same rule inScope follows, one level down.
plate 'United Kingdom'
check "a country plate shows only the roles in that country" \
  "$(xroles "'United Kingdom' in r['countries']")" "$(rows)"
plate

# The title IS the apply link, the rule the gazetteer entry already follows, so
# the register reaches the posting without a detour through the company.
check "every role line links to its own posting" "17" \
  "$(val 'document.querySelectorAll(".jrow .iname a[href^=\"http\"]").length')"
# The second affordance, and why the line is not a button: a job has two
# destinations. Both halves are read off the page rather than off the fixture,
# so the check is about the MECHANISM and not about which company sorts sixth --
# and the guard is what makes it mean anything: the sheet always shows some
# company (the plate walk above left one open), so without proving it was not
# already this one, the assertion would pass on a click that did nothing.
target=$(val 'document.querySelectorAll(".jrow .cobtn")[5].textContent.trim()')
before=$(val 'document.querySelector("#sheet h2").textContent.trim()')
check "the sheet is not already open on the company that row names" "true" \
  "$([ "$before" != "$target" ] && echo true || echo false)"
$B js 'document.querySelectorAll(".jrow .cobtn")[5].click()' >/dev/null 2>&1
check "the company cell opens THAT role's company" "$target" \
  "$(val 'document.querySelector("#sheet h2").textContent.trim()')"
check "every role line's company control has an accessible name" "true" \
  "$(val '[...document.querySelectorAll(".jrow .cobtn")]
       .every((b) => (b.getAttribute("aria-label") || "").trim().length > 0) + ""')"

# ---- T15.2: first seen, the badge and the Newest sort -----------------------
#
# Driven over a first-seen fixture, and it needs one: the real artifact holds
# 6,505 URLs, none of which this dataset publishes, and confirms none of them
# (see the run against real data above). A check that can never reach its own
# branch is the shape this repo has been bitten by before, so the history the
# corpus cannot express is written down instead -- held to a file the real
# module could have produced by test_the_e2e_artifact_is_a_file_this_module_
# could_have_written, which is what stops it drifting into wishful data.
#
# The fixture's snapshot is 2026-07-28 and its dates are placed against it:
# two confirmed that day, two UNCONFIRMED that day, one confirmed at seven days
# and one at eight, nine older, and one role with no date at all.
SEEN="$ROLES&seen=../tests/fixtures/first-seen-e2e.json"
open_page "$SEEN"
console_clean "roles register with first-seen dates"

badges() { val '[...document.querySelectorAll(".jrow")]
     .filter((n) => n.querySelector(".tag.fresh"))
     .map((n) => n.querySelector(".iname").firstChild.textContent).join("|")'; }

# Derived from the two fixtures rather than hardcoded, the way every other
# expectation here is -- and in Python against JavaScript, so the rule is
# implemented twice and has to agree with itself.
check "the badge marks the confirmed roles first seen inside the week" \
  "$($PY -c '
import datetime, json
data = json.load(open("tests/fixtures/companies-e2e.json"))
art = json.load(open("tests/fixtures/first-seen-e2e.json"))
snap = datetime.date.fromisoformat(data["snapshot"])
fresh = {url for day, buckets in art["dates"].items() for url in buckets["confirmed"]
         if 0 <= (snap - datetime.date.fromisoformat(day)).days <= 7}
cs = sorted(data["companies"], key=lambda c: (-len(c["roles"]), c["name"]))
print("|".join(r["title"] for c in cs for r in c["roles"] if r["url"] in fresh))')" \
  "$(badges)"

# THE CHECK THIS FEATURE EXISTS FOR, and it is named rather than derived: these
# two roles were first seen on the snapshot date itself -- as new as a role can
# be -- under companies whose board we could not read on the previous snapshot.
# SPEC measured that case at 176 of 179 changes on 2026-08-01. They carry the
# date, because when we first saw something is a fact about us and always true.
# They must not carry the badge, because "new" is a claim about the company.
#
# Counted as well as asserted: "none of these rows is badged" passes trivially
# when the rows are not there, and that is the failure this check would miss.
check "a role we saw first today but could not compare is dated, never badged" "2 0" \
  "$(val '(() => {
     const names = ["Product Designer", "Warehouse Systems Engineer"];
     const rows = [...document.querySelectorAll(".jrow")]
       .filter((n) => names.includes(n.querySelector(".iname").firstChild.textContent));
     return `${rows.length} ${rows.filter((n) => n.querySelector(".tag.fresh")).length}`;
   })()')"
# The window, at its edge and one day past it: both roles are confirmed, so the
# only thing separating them is the week. A badge with no window would show both
# and a badge with an off-by-one would show neither.
check "seven days is inside the week and eight is outside" "Backend Engineer, Payments" \
  "$(val '[...document.querySelectorAll(".jrow")]
       .filter((n) => ["Backend Engineer, Payments", "Founding Engineer"]
         .includes(n.querySelector(".iname").firstChild.textContent))
       .filter((n) => n.querySelector(".tag.fresh"))
       .map((n) => n.querySelector(".iname").firstChild.textContent).join("|")')"

# The first sort in this register that is a fact about a ROLE. The other four
# order the company blocks the roles sit in; this one has to reach past them and
# order the flattened list, so it is checked against an order no company sort
# can produce -- and the undated role sorts LAST rather than being dated to
# force it, because an absence given a date would be the register inventing the
# fact it exists to avoid.
$B select '#sort' 'newest' >/dev/null 2>&1
check "Newest orders the roles themselves, and undated roles sort last" \
  "$($PY -c '
import json
data = json.load(open("tests/fixtures/companies-e2e.json"))
art = json.load(open("tests/fixtures/first-seen-e2e.json"))
when = {url: day for day, buckets in art["dates"].items()
        for urls in buckets.values() for url in urls}
cs = sorted(data["companies"], key=lambda c: (-len(c["roles"]), c["name"]))
flat = [r for c in cs for r in c["roles"]]
flat.sort(key=lambda r: when.get(r["url"], ""), reverse=True)
print("|".join(r["title"] for r in flat))')" \
  "$(rows)"

# The company register has nothing role-shaped to order, so the control leaves
# the row -- the openness filter's rule at zero yield, and the MCA filter's off
# an India-less plate. It clears itself on the way out for the same reason they
# do: a sort holding a value while invisible orders the register by something
# nobody can see or change.
$B click '#vcompanies' >/dev/null 2>&1
check "Newest leaves the row where the register counts companies" "true" \
  "$(val 'String(document.querySelector("#sort option[value=newest]").hidden)')"
check "and clears itself rather than ordering by an invisible control" "reqs" \
  "$(val 'document.querySelector("#sort").value')"

# The artifact is enrichment and never a dependency -- the descriptions' rule,
# and the register is a public document that has to render without it. A missing
# file costs the badge and the sort, and costs the register nothing.
#
# console_clean is deliberately NOT called here: the 404 this check is ABOUT is
# a failed request, and a page that asked for a file that is not there is what
# is being proved. Every other page in this run is held to zero.
open_page "$ROLES&seen=../tests/fixtures/no-such-artifact.json"
check "a missing artifact costs the badge and nothing else" "17 0" \
  "$(val '`${document.querySelectorAll(".jrow").length} `
        + `${document.querySelectorAll(".jrow .tag.fresh").length}`')"
check "and takes the Newest sort off the bank with it" "true" \
  "$(val 'String(document.querySelector("#sort option[value=newest]").hidden)')"
check "and the footer claims no dates it does not hold" "" \
  "$(val 'document.querySelector("#firstseen").textContent')"

open_page "$ROLES"

# Search at the ROLE scale: the company register answers "which companies hold a
# matching title", this one answers "which jobs match". Last of the interactions
# -- `browse fill` cannot pass an empty value, so only a reload clears the box.
$B fill '#q' 'engineer' >/dev/null 2>&1
check "search returns the matching roles themselves" \
  "$(xroles "'engineer' in r['title'].lower()")" "$(rows)"
# A company NAME match still brings that company's jobs: a reader typing a
# company is asking for its roles, not for roles named after it.
$B fill '#q' 'gamma' >/dev/null 2>&1
check "a company name returns that company's roles" \
  "$(xroles "'gamma' in c['name'].lower()")" "$(rows)"
$B fill '#q' 'no-such-role' >/dev/null 2>&1
check "a roles filter that matches nothing says so" "No role matches these filters." \
  "$(val 'document.querySelector("#status > span").textContent')"

# THE TRAP CHECK, and the reason the switch is built by both of render()'s
# branches rather than only the one that has rows. A reader whose filters met in
# an empty corner is the one who most needs the other register; an empty page
# that also withdrew the way out of it would be a dead end wearing a message.
# The box still reads 'no-such-role' here -- that is the point.
check "the unit switch survives a register showing nothing" "true" \
  "$(val 'String(!!document.querySelector("#status #vcompanies"))')"
$B click '#vcompanies' >/dev/null 2>&1
check "and it still works from there" "companies" \
  "$(val 'document.querySelector("#viewsw").dataset.unit')"
# The same dead search under the other unit: the reader escaped the empty roles
# register into an empty company one, which is honest, and can still get back.
check "the way back is offered too" "true" \
  "$(val 'String(!!document.querySelector("#status #vroles"))')"
$B click '#vroles' >/dev/null 2>&1
check "the register returns to roles" "roles" \
  "$(val 'document.querySelector("#viewsw").dataset.unit')"
console_clean "roles register after interaction"

# The switch is navigation, not a filter, and it says so to a screen reader: the
# open unit is pressed and is not a control, because pressing the register you
# are already reading announces a state change that did not happen.
open_page "$ROLES"
check "the open unit is marked pressed" "true|false" \
  "$(val '[...document.querySelectorAll("#viewsw button")]
       .map((b) => b.getAttribute("aria-pressed")).join("|")')"
check "the switch names itself for a screen reader" "Register unit" \
  "$(val 'document.querySelector("#viewsw").getAttribute("aria-label")')"
# It lives on the status line and NOT in the filter bank -- a control that
# changes what a line IS among nine that change which lines show is how the
# first version shipped, and a reader asked for a view the page already had.
check "the unit switch is not in the filter bank" "true" \
  "$(val 'String(!document.querySelector("#controls #viewsw, #controls #view"))')"
check "the fold's tally does not count it as a filter" "" \
  "$(val 'document.querySelector("#fcount").textContent')"

# 4c visual regression is NOT here. It needs baseline screenshots a human
# approves once (VERIFICATION.md 4c), and an agent approving its own baselines
# would assert nothing. Deliberately outside the gate rather than faked inside it.

[ "$fail" -eq 0 ] && echo "E2E GREEN"
exit $fail
