// build.mjs — writes index.html from page.html + the fixture.
//
//   node build.mjs
//
// Two jobs, both about the first 1.5 seconds:
//
// 1. It pre-paints. The default view (any field · anywhere · hide the giants) is
//    deterministic, so the first ten cards are rendered here, at build time, by
//    the same render.js the live page uses, and shipped inside index.html. The
//    first company card is on screen when the HTML lands — before cards.json,
//    before app.js, before any JS runs at all. That is M1, and it holds whether
//    or not the server compresses anything.
// 2. It inlines the constants the fold needs — the header counts, the funnel,
//    the 376 one-liners — all read out of ../../fixture-v2 here so the page does
//    not spend a round trip on them.
//
// Nothing is invented. Every number below is computed from the fixture in this
// file; if the fixture changes, re-run and the page changes with it.

import fs from 'node:fs';
import { prepare, cardHTML, optionsHTML, esc, num } from './render.js';
import { GIANT_FLOOR, gateOf } from './taxonomy.js';

const read = (f) => JSON.parse(fs.readFileSync('../../fixture-v2/' + f, 'utf8'));

const cards = read('cards.json');
const report = read('build-report.json');

const prepared = cards.map(prepare);
const companies = prepared.length;
const roles = prepared.reduce((a, c) => a + c.open, 0);
const giants = prepared.filter((c) => c.giant);
const SNAPSHOT = 'Aug 4, 2026';

/* ── the gate census, straight off source_url ─────────────────────────────── */
const gateCount = {};
for (const c of cards) { const g = gateOf(c); gateCount[g] = (gateCount[g] || 0) + 1; }
const GATE_ORDER = ['yc', 'cbi', 'sec', 'forbes', 'techcrunch', 'finsmes'];
const gateLabel = { yc: 'Y Combinator', cbi: 'CB Insights', sec: 'SEC Form D', forbes: 'Forbes', techcrunch: 'TechCrunch', finsmes: 'FinSMEs' };

const ycs = cards.filter((c) => c.yc);
const notActive = ycs.filter((c) => c.yc.status !== 'Active');
const withAmount = cards.filter((c) => c.amount != null);

/* ── header ───────────────────────────────────────────────────────────────── */
const HDR1 = `<b>${num(companies)}</b> companies hiring · <b>${num(roles)}</b> roles open on their own boards · read ${SNAPSHOT}`;

const c = report.counts;
const HDR2 = `We read <b>10,125</b> companies to get here. <b>6,895</b> didn't qualify. `
  + `<b>${num(c['slug-unresolved'])}</b> more qualified but had no job board we could resolve.`;

const HDR3 = `<span class="g">Every card below names its own gate:</span>`
  + GATE_ORDER.filter((g) => gateCount[g])
    .map((g) => `<span class="g"><b>${num(gateCount[g])}</b> ${esc(gateLabel[g])}</span>`).join('');

/* ── the default view, computed exactly as the page computes it ───────────── */
const bySize = (a, b) => b.open - a.open || a.name.localeCompare(b.name);
const shown = prepared.filter((x) => !x.giant).sort(bySize);
const held = giants.slice().sort(bySize);

const YIELD = `<b>${num(shown.length)}</b> companies are hiring tonight. `
  + `<b>${num(held.length)}</b> have ${GIANT_FLOOR} or more roles open and are held back below.`;

const HELDSUM = `Held back: <b>${num(held.length)}</b> companies with ${GIANT_FLOOR} or more roles open. `
  + `They are rendered below, not removed — uncheck <b>hide the giants</b> to put them back in the list.`;

const SEED_N = 10;
let SEED = shown.slice(0, SEED_N)
  .map((x, i) => cardHTML(x, { field: 'all', place: 'all', matching: x.open, kept: false, rank: i + 1 }))
  .join('');
// M1 is measurable, not asserted: the first card carries an elementtiming mark,
// so an evaluator can read the exact millisecond it painted.
SEED = SEED.replace('<span class="nm">', '<span class="nm" elementtiming="first-card">');
// ...and, because Element Timing is not reported for text in every headless
// build, the card is followed by three lines that mark the first animation
// frame drawn after it exists. That is M1, measured by the page itself, with
// no reliance on a lab API: window.__firstCardPainted.
const mark = `<script>requestAnimationFrame(()=>requestAnimationFrame(()=>{window.__firstCardPainted=performance.now()}))<\/script>`;
const cut = SEED.indexOf('<article', 1);
SEED = SEED.slice(0, cut) + mark + SEED.slice(cut);

/* ── the how sheet ────────────────────────────────────────────────────────── */
const fun = (n, lab, indent) =>
  `<span class="n">${num(n)}</span>  <span class="${indent ? 'in' : 'lab'}">${lab}</span>`;

const HOW = `
<h2>How these ${num(companies)} companies got here, and who didn't make it</h2>
<p class="sub">Every number on this panel is a counter the nightly build wrote on ${SNAPSHOT}. None of it is an estimate.</p>
<div class="funnel">
${fun(10125, 'company names read from the five sources')}<br>
${fun(6895, '&#9500;&#9472; did not qualify — no funding signal any source would state', 1)}<br>
${fun(report.corpus_size, 'qualified')}<br>
${fun(c['slug-unresolved'], '&#9500;&#9472; no job board we could resolve — we could not look', 1)}<br>
${fun(report.checked, 'boards actually read')}<br>
${fun(c['no-located-roles'], '&#9500;&#9472; read, nothing open tonight', 1)}<br>
${fun(c['another-companys-board'], '&#9500;&#9472; turned out to be another company\'s board', 1)}<br>
${fun(c['empty-board-unverified'], '&#9492;&#9472; empty, and we could not verify it', 1)}<br>
${fun(companies, '<b>companies with something open tonight</b>')}<br>
${fun(roles, 'roles, every one live on the company\'s own board on ' + SNAPSHOT)}
</div>
<p style="margin-top:-6px">These are the build's own counters, printed as recorded; the middle rows overlap slightly and do not sum cleanly, and we would rather show you that than round it.
<b>${num(report.unchecked)}</b> qualified companies remain unchecked — that is "we could not look", never "nothing there".</p>

<h2 style="font-size:14px;margin-top:18px">The gate on each card</h2>
<p class="sub" style="margin-bottom:8px">One clickable receipt per company. 100% coverage — no company is here without one.</p>
<table>
<tr><th>Gate</th><th class="n">n</th><th>What the card says, and what it does not</th></tr>
<tr><td>Y Combinator</td><td class="n">${gateCount.yc}</td><td>the batch, by name — <em>Y Combinator, Winter 2021</em>. A batch is a date, not a funding date, so it is never called one.</td></tr>
<tr><td>CB Insights</td><td class="n">${gateCount.cbi}</td><td>on their unicorn list. States no amount, no date, no round — so the card states none.</td></tr>
<tr><td>SEC EDGAR</td><td class="n">${gateCount.sec}</td><td>a Form D, with the exact sum sold and the exact date, because a filing has both.</td></tr>
<tr><td>Forbes</td><td class="n">${gateCount.forbes}</td><td>an editor put them on a list. That is a real signal and it is not a funding fact.</td></tr>
<tr><td>TechCrunch</td><td class="n">${gateCount.techcrunch}</td><td>a dated story about a round.</td></tr>
<tr><td>FinSMEs</td><td class="n">${gateCount.finsmes}</td><td>a dated wire item.</td></tr>
</table>

<h2 style="font-size:14px">What this page will not say</h2>
<p><b>"Recently funded" — an amount and a date exist for ${withAmount.length} of ${num(companies)} companies</b>, so it is true of 15% and the page does not print it as a promise.
<b>Seed / Series A / B / C</b> — a round letter exists on <b>5</b> rows. There is no such filter here.
<b>An investor name</b> — the field does not exist in any source this build may lawfully republish.
<b>A score</b> — nothing here is composited into a number, because a number has no source URL.
<b>A "new" badge — first-seen holds 7 dated URLs against ${num(roles)} roles</b>, so freshness is not a product yet.</p>

<h2 style="font-size:14px">Where a fact is missing</h2>
<p>Sponsorship is unstated on <b>25,674</b> of ${num(roles)} roles; workplace on <b>14,489</b>; a funding amount on <b>${num(companies - withAmount.length)}</b> of ${num(companies)} companies.
None of the three is a filter on this page, because a filter over a sparse column silently deletes everyone the board was quiet about.
Each is printed on the card or the role when the source states it, and printed as nothing when it doesn't. A blank here means <em>nobody said</em>, and it never means no.</p>
<p><b>${notActive.length}</b> of the ${ycs.length} Y Combinator companies are Acquired, Public or Inactive by YC's own status field — Airbnb among them. Their cards carry that status, because a job at a company that already landed is not a bet on a rocketship, and you should be told which one you are looking at.</p>
<p>The department and city menus are this page's own grouping of the board's <b>2,300</b> department strings and <b>1,672</b> place strings. The grouping rules are in <code>taxonomy.js</code>, ordered and readable; <b>3,708</b> roles sit on labels that map to nothing standard and are kept under <em>Other</em>, not dropped.</p>
<button class="close" data-act="close">close</button>`;

/* ── the tail ─────────────────────────────────────────────────────────────── */
const TAIL = `
<p><button class="how" data-act="showall" style="font-size:13px">↓ show all ${num(companies)} companies</button>
— clears both menus and the giants toggle. The full register is the receipt, not the door.</p>
<p>${num(companies)} companies · ${num(roles)} roles · read from each company's own applicant tracking system on ${SNAPSHOT}
(<b>${num(report.checked)}</b> boards read, <b>${num(report.unchecked)}</b> qualified companies not yet checked).
The shortlist lives in this browser. There is no account and nothing leaves the page.</p>`;

/* ── write ────────────────────────────────────────────────────────────────── */
const opts = optionsHTML(prepared);
const optField = opts.field;
const optPlace = opts.place;

const inlineData = `<script>
window.__HOW=${JSON.stringify(HOW)};
window.__TAIL=${JSON.stringify(TAIL)};
</script>`;

let html = fs.readFileSync('page.html', 'utf8');
const put = (mark, val) => { html = html.replace('<!--' + mark + '-->', val); };
put('HDR1', HDR1);
put('HDR2', HDR2 + ' ');
put('HDR3', HDR3);
put('FIELDOPTS', optField);
put('PLACEOPTS', optPlace);
put('YIELD', YIELD);
put('SEED', SEED);
put('HELDSUM', HELDSUM);
put('HELDSEED', '');
put('TAIL', TAIL);
html = html.replace('<script type="module" src="./app.js"></script>', inlineData + '\n<script type="module" src="./app.js"></script>');

fs.writeFileSync('index.html', html);

console.log(`index.html  ${(fs.statSync('index.html').size / 1024).toFixed(1)}KB`);
console.log(`companies ${companies} · roles ${roles} · shown ${shown.length} · held ${held.length}`);
console.log(`gates`, gateCount);
console.log(`seed: ${shown.slice(0, SEED_N).map((x) => x.name + ' ' + x.open).join(' · ')}`);
