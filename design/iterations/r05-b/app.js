/* r05-b — "the memo".
 *
 * One renderer, mirrored in build.py so the six cards that arrive as HTML and
 * the 783 that arrive as JSON are the same markup. qa/crosscheck.mjs asserts it
 * on all 789.
 */
'use strict';

const $ = (s, r) => (r || document).querySelector(s);
const $$ = (s, r) => [...(r || document).querySelectorAll(s)];
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
  .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#x27;');
const num = (n) => Number(n).toLocaleString('en-US');
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
const pretty = (s) => { const [y, m, d] = String(s).split('-'); return `${MONTHS[+m - 1]} ${+d}, ${y}`; };
const today = () => iso(new Date());

const GIANT = 100;
const PROV = {
  checked: 'checked against their own site',
  unchecked: 'not checked against their site',
  board: 'written from their job board, not their site',
};
const DL = HEAD.dept_labels, PL = HEAD.place_labels, META = HEAD.meta;

/* ======================================================= the card, once ==== */

/* Two of the place buckets are not places — they are what the board said when
 * it did not say a place. They stay in the count and stay in the menu; on the
 * rail's three-place line they simply go last, so the line leads with somewhere
 * a reader could actually go. */
/* a/b to one decimal, in integer arithmetic both languages agree on. Python's
 * format rounds half to even and toFixed rounds half away from zero, so
 * 810/40 = 20.25 printed 20.2 in the pre-rendered fold and 20.3 in the scrolled
 * list — seven of the 789 cards differed on one digit. Mirrors one_decimal()
 * in build.py. */
const oneDecimal = (a, b) => {
  const tenths = Math.floor((a / b) * 10 + 0.5);
  return `${Math.floor(tenths / 10)}.${tenths % 10}`;
};

const NONPLACE = new Set(['elsewhere', 'unstated']);
const placeCmp = (a, b) => (NONPLACE.has(a[0]) - NONPLACE.has(b[0])) || b[1] - a[1];

/* One line of the memo: a micro-label in the sheet's one gutter, and its value
 * set to the masthead thesis. `display:contents` puts both directly on the
 * card's grid, so every label on the page stands in the same column. */
const row = (k, v) => `<p class="ml"><span class="mk">${k}</span><span class="mv">${v}</span></p>`;

function memoHTML(c) {
  if (c.m) {
    const rows = [['what', c.m.w], ['for whom', c.m.f], ['why them', c.m.y]]
      .map(([k, v]) => row(k, esc(v))).join('');
    // Only the part that VARIES prints on the card. That these three lines are
    // mine and machine-written is said once, in the lede, where it can be
    // argued properly — 371 identical footnotes would be wallpaper.
    return `<div class="memo">${rows}<p class="ml"><span class="mk"></span>`
      + `<span class="prov">${esc(PROV[c.m.p])}</span></p></div>`;
  }
  const words = (c.bw || []).map(esc).join(' · ') || 'their board names no teams';
  return '<div class="memo absent">'
    + row('not yet read', 'I have their gate and their board. I have not read '
      + 'their own site, so this card does not say what they do.')
    + `<p class="ml"><span class="mk">their teams</span><span class="bwords">${words}</span></p>`
    + '<p class="ml"><span class="mk"></span><span class="prov">a backlog in '
    + 'scripts/describe.py — not a judgement about them</span></p></div>';
}

/* Who vouched, and the receipt. Same anatomy as a memo line, because it is one
 * — the difference is that this line is not mine. */
const gateHTML = (c) => '<p class="ml"><span class="mk">vouched</span><span class="mv gate">'
  + `<a href="${esc(c.g.url)}" target="_blank" rel="noopener">${esc(c.g.line)} ↗</a>`
  + `<span class="gcap">${esc(c.gc)}</span></span></p>`;

/* The YC status as a fact with its source and no adjective. Active, Public,
 * Acquired and Inactive share one frame, one ink and one sentence shape; the
 * difference between the four is the word inside and nothing else. */
const chipHTML = (c) => (c.g.kind !== 'yc' ? ''
  : `<span class="chip">${esc(c.g.status)} · per YC · ${esc(c.g.batch_short)}</span>`);

/* The rail: everything somebody else counted, stamped in the mono voice.
 * Nothing here is a claim, and nothing on the left is a number. */
function receiptHTML(c, verb) {
  const top = Object.entries(c.d).sort((a, b) => b[1] - a[1]).slice(0, 4);
  const more = Object.keys(c.d).length - top.length;
  let rows = top.map(([k, n]) => `<p class="rrow"><span class="rk">${esc(DL[k] || k)}</span>`
    + `<span class="rv">${n}</span></p>`).join('');
  if (more > 0) rows += `<p class="rmore">+${more} more field${more !== 1 ? 's' : ''}</p>`;
  let wide = '';
  if (c.t) {
    // The division is printed, not just its answer: two numbers somebody else
    // stated, and the arithmetic between them in the open.
    wide += '<p class="rrow wide"><span class="rk">team</span>'
      + `<span class="rv">${num(c.t)} people, per YC</span></p>`
      + '<p class="rrow wide"><span class="rk">rate</span>'
      + `<span class="rv">${num(c.t)} ÷ ${c.r} = one opening per ${oneDecimal(c.t, c.r)} people</span></p>`;
  }
  const where = Object.entries(c.p).sort(placeCmp).slice(0, 3)
    .map(([k]) => esc(PL[k] || k)).join(' · ');
  if (where) {
    wide += `<p class="rrow wide"><span class="rk">where</span><span class="rv">${where}</span></p>`;
  }
  return '<div class="crail"><aside class="receipt">'
    + `<p class="rhead"><span>open roles</span><span class="rno">${c.r}</span></p>`
    + `${rows}${wide}</aside>`
    + '<div class="act"><button class="keep" type="button">keep</button>'
    + `<button class="open" type="button">${verb} →</button></div></div>`;
}

function cardHTML(c, field, i) {
  const n = field === 'any' ? c.r : (c.d[field] || 0);
  const label = String(DL[field] || field).toLowerCase();
  const verb = (field === 'any' || !n) ? `all ${c.r} roles`
    : `${n} ${esc(label)} role${n !== 1 ? 's' : ''}`;
  return `<article class="card" id="c-${esc(c.s)}" data-s="${esc(c.s)}">`
    + `<div class="cmain"><span class="cref">${String(i).padStart(3, '0')}</span>`
    + `<div class="chead"><h2 class="cname">${esc(c.n)}</h2>${chipHTML(c)}</div>`
    + `${memoHTML(c)}${gateHTML(c)}</div>`
    + receiptHTML(c, verb)
    + '<div class="roles" hidden></div></article>';
}
window.__cardHTML = cardHTML;

/* ============================================================== the state == */

const S = { field: 'any', place: 'any', order: 'match', giants: true };
let ALL = HEAD.companies.slice();   // the 18 inlined, until index.json lands
let FULL = false;                   // ...then all 789
let CUT = [];                       // the current narrowing, ordered
let cursor = -1;
const shards = new Map();
const KEY = 'roleatlas.r05b.v1';

function loadRec() {
  try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch (e) { return {}; }
}
function saveRec() { try { localStorage.setItem(KEY, JSON.stringify(REC)); } catch (e) { /* private mode */ } }
let REC = loadRec();
const kept = () => Object.entries(REC).filter(([, v]) => v.kept_at);

function readHash() {
  const h = new URLSearchParams(location.hash.replace(/^#/, ''));
  if (h.get('f')) S.field = h.get('f');
  if (h.get('p')) S.place = h.get('p');
  if (h.get('o')) S.order = h.get('o');
  if (h.get('g') !== null) S.giants = h.get('g') !== '0';
  for (const slug of (h.get('k') || '').split(',').filter(Boolean)) {
    if (!REC[slug]) REC[slug] = { kept_at: h.get('kd') || today(), opened: [], applied: null, answered_at: null };
    else if (!REC[slug].kept_at) REC[slug].kept_at = h.get('kd') || today();
  }
  if (h.get('k')) saveRec();
}

function hashFor() {
  const p = new URLSearchParams();
  if (S.field !== 'any') p.set('f', S.field);
  if (S.place !== 'any') p.set('p', S.place);
  if (S.order !== 'match') p.set('o', S.order);
  if (!S.giants) p.set('g', '0');
  const ks = kept().map(([s]) => s);
  if (ks.length) p.set('k', ks.join(','));
  return '#' + p.toString();
}
function syncHash() { history.replaceState(null, '', hashFor()); }

/* ============================================================= the menus === */

function fillMenus() {
  const f = $('#field');
  f.innerHTML = `<option value="any">any field — ${num(META.roles)} roles at ${META.companies} companies</option>`
    + HEAD.depts.filter((d) => d.k !== 'other')
      .map((d) => `<option value="${d.k}">${esc(d.l)} — ${num(d.r)} roles at ${d.c} companies</option>`).join('');
  const groups = {};
  for (const p of HEAD.places) (groups[p.g] = groups[p.g] || []).push(p);
  const pl = $('#place');
  pl.innerHTML = `<option value="any">anywhere — all ${META.companies} companies</option>`
    + Object.entries(groups).map(([g, ps]) => `<optgroup label="${esc(g)}">`
      + ps.map((p) => `<option value="${p.k}">${esc(p.l)} — ${p.c} companies, ${num(p.r)} roles</option>`).join('')
      + '</optgroup>').join('');
  f.value = S.field; pl.value = S.place;
  $('#order').value = S.order;
  paintControls();
}

/* A control that has left its default prints red — the register's own rule, so
 * a narrowing is visible from across the sheet. The giants switch is not a
 * filter but a change of unit, so it sets as the register's struck-word pair
 * rather than as a checkbox: both states are readable words, always. */
function paintControls() {
  $('#field').classList.toggle('set', S.field !== 'any');
  $('#place').classList.toggle('set', S.place !== 'any');
  $('#ghide').setAttribute('aria-pressed', String(S.giants));
  $('#gshow').setAttribute('aria-pressed', String(!S.giants));
  $('#gnote').textContent = S.giants
    ? `— ${META.giants} boards with ${GIANT}+ roles open are set aside, and named below`
    : `— all ${META.companies}, giants included`;
}

/* ============================================================== filtering == */

const matches = (c) => {
  if (S.field === 'any' && S.place === 'any') return true;
  if (S.place === 'any') return (c.d[S.field] || 0) > 0;
  if (S.field === 'any') return (c.p[S.place] || 0) > 0;
  return c.x.some((x) => x[0] === S.field && x[1] === S.place);
};
const matchCount = (c) => {
  if (S.field === 'any' && S.place === 'any') return c.r;
  if (S.place === 'any') return c.d[S.field] || 0;
  if (S.field === 'any') return c.p[S.place] || 0;
  return c.x.filter((x) => x[0] === S.field && x[1] === S.place)
    .reduce((a, x) => a + x[2], 0);
};

const byMatch = (a, b) => matchCount(b) - matchCount(a) || b.r - a.r || a.n.localeCompare(b.n);

function order(list) {
  if (S.order === 'all') return list.slice().sort((a, b) => b.r - a.r || a.n.localeCompare(b.n));
  if (S.order === 'read') {
    const yes = list.filter((c) => c.m).sort(byMatch);
    return yes.concat(list.filter((c) => !c.m).sort(byMatch));
  }
  if (S.order === 'size') {
    const has = list.filter((c) => c.t), no = list.filter((c) => !c.t);
    has.sort((a, b) => (b.r / b.t) - (a.r / a.t) || b.r - a.r);
    no.sort(byMatch);
    return has.concat(no);
  }
  return list.slice().sort(byMatch);
}

function recompute() {
  const hit = ALL.filter(matches);
  const shown = S.giants ? hit.filter((c) => c.r < GIANT) : hit;
  CUT = order(shown);
  return { hit, shown };
}

/* ================================================================ the copy = */

const fieldWord = () => (S.field === 'any' ? '' : ` ${String(DL[S.field]).toLowerCase()}`);
const placeWord = () => (S.place === 'any' ? '' : ` in ${PL[S.place]}`);

/* Before index.json lands the page holds 18 of the 789. It may still state the
 * true unnarrowed totals, because those come from the build's own counts — but
 * it may not answer a *narrowed* question out of an eighteenth of the register.
 */
function provisional() {
  if (FULL) return '';
  if (S.field === 'any' && S.place === 'any') return '';
  return `<span class="second">One moment — I am still reading in the other `
    + `${META.companies - ALL.length} companies, so this count is not final yet.</span>`;
}

function yieldLine(hit) {
  const partial = !FULL && S.field === 'any' && S.place === 'any';
  const shownN = partial ? META.companies - (S.giants ? META.giants : 0) : CUT.length;
  const giantN = partial ? META.giants : hit.length - CUT.length;
  const read = CUT.filter((c) => c.m).length;
  const one = `<span class="n">${shownN}</span> compan${shownN === 1 ? 'y is' : 'ies are'} `
    + `hiring${fieldWord() ? fieldWord() : ''}${placeWord()}${fieldWord() ? '' : ' right now'}.`;
  let two = '';
  if (S.giants && giantN) {
    two = ` <span class="n">${giantN}</span> more have ${GIANT}+ roles open and are set aside`
      + ' — every one of them is named below, and one click brings it back.';
  } else if (!S.giants && META.giants) {
    two = ` The ${META.giants} giants are in this list; tick the box to set them aside.`;
  }
  if (partial) return one + two + provisional();
  const unread = shownN - read;
  const three = shownN
    ? `<span class="second">I have read the sites of <span class="n">${read}</span> of these `
      + `${shownN}. The other <span class="n">${unread}</span> say <em>not yet read</em> where the memo goes — `
      + 'that means I have their gate and their board and have not read them, nothing worse.</span>'
    : '';
  return one + two + three + provisional();
}

function orderNote() {
  if (S.order === 'read') {
    const read = CUT.filter((c) => c.m).length;
    return `The ${read} companies I have read are first, the other ${CUT.length - read} after them `
      + 'in the default order. This is a ranking of my backlog, not of the companies: a card '
      + 'that says "not yet read" is a job I have not done, and it says nothing at all about them.';
  }
  if (S.order !== 'size') return '';
  const it = META.intensity;
  const has = CUT.filter((c) => c.t).length;
  return `Ordered by open roles per person on the payroll. ${has} of these ${CUT.length} `
    + `state both numbers; the rest have no headcount to divide by and follow underneath, `
    + `in the default order. YC's headcount is YC's number and it can be stale — `
    + `${it.tiny} of the ${it.n} companies that give one list under ten people.`;
}

/* ========================================================== rendering ====== */

let renderToken = 0;
function renderList() {
  const list = $('#list');
  const token = ++renderToken;
  list.innerHTML = '';
  if (!CUT.length) {
    list.innerHTML = '<p class="yield">Nothing is open in that combination tonight. '
      + 'Widen one of the two menus — nothing has been deleted, only narrowed.</p>';
    return;
  }
  let i = 0;
  const step = () => {
    if (token !== renderToken) return;
    const frag = document.createDocumentFragment(), end = Math.min(i + 40, CUT.length);
    for (; i < end; i++) {
      const div = document.createElement('div');
      div.innerHTML = cardHTML(CUT[i], S.field, i + 1);
      frag.appendChild(div.firstChild);
    }
    list.appendChild(frag);
    paintKeeps();
    if (i < CUT.length) requestAnimationFrame(step);
    else if (S.order === 'size') markSizeSplit();
  };
  step();
}

function markSizeSplit() {
  const first = CUT.findIndex((c) => !c.t);
  if (first <= 0 || first >= CUT.length) return;
  const el = $(`#c-${CSS.escape(CUT[first].s)}`);
  if (!el || el.previousElementSibling?.classList.contains('splitnote')) return;
  const p = document.createElement('p');
  p.className = 'yield splitnote';
  p.innerHTML = `<span class="second">From here down, ${CUT.length - first} companies that `
    + 'no source gives a headcount for. They are not ranked by this ordering because '
    + 'there is nothing to rank them with — they are in the default order instead.</span>';
  el.parentNode.insertBefore(p, el);
}

function paintKeeps() {
  for (const el of $$('.card')) {
    const rec = REC[el.dataset.s];
    const on = !!(rec && rec.kept_at);
    el.classList.toggle('kept', on);
    const b = $('.keep', el);
    if (b) b.textContent = on ? 'kept' : 'keep';
  }
}

function giantStrip(hit) {
  const box = $('#gstrip');
  if (!S.giants) { box.innerHTML = ''; return; }
  const gs = hit.filter((c) => c.r >= GIANT);
  box.innerHTML = gs.length
    ? '<span class="gk">set aside</span>'
      + gs.map((c) => `<button type="button" data-g="${esc(c.s)}">${esc(c.n)} ${c.r}</button>`).join('')
    : '';
}

function paint() {
  const { hit } = recompute();
  paintControls();
  $('#yield').innerHTML = yieldLine(hit);
  const note = orderNote();
  $('#residue').innerHTML = note
    ? esc(note)
    : `The eleven fields in that first menu are mine, not the boards' — ${num(META.residue.roles)} `
      + `roles (${META.residue.pct}% of ${num(META.roles)}) match none of them and sit in a bucket `
      + 'called "something else"; every role row prints its board\'s own word for the team, so you '
      + 'can see when I have put one in the wrong drawer.';
  giantStrip(hit);
  renderList();
  paintDeliver();
  syncHash();
}

/* ============================================== the shortlist and the record */

function openedAll() {
  return Object.entries(REC).flatMap(([s, v]) => (v.opened || []).map((o) => ({ s, ...o })));
}

function slRow(slug, rec, i) {
  const c = ALL.find((x) => x.s === slug);
  const name = c ? c.n : slug;
  const n = (rec.opened || []).length;
  const bits = [`kept ${pretty(rec.kept_at)}`];
  if (c) bits.push(`${c.r} roles open`);
  if (n) bits.push(`you opened ${n} of them`);
  if (rec.applied) bits.push(`applied: ${rec.applied}`);
  return `<div class="slrow" data-s="${esc(slug)}">`
    + `<span class="sn">${String(i + 1).padStart(2, '0')}</span>`
    + `<span class="nm">${esc(name)}</span>`
    + `<span class="meta">${esc(bits.join(' · '))}</span>`
    + '<button class="drop" type="button" data-drop>drop</button></div>';
}

function recordLine() {
  const ks = kept(), opens = openedAll();
  if (!ks.length && !opens.length) return '';
  const cos = new Set(opens.map((o) => o.s));
  const answered = ks.filter(([, v]) => v.answered_at).length;
  const inCut = CUT.filter((c) => cos.has(c.s)).length;
  let s = `Your record here: <span class="n">${ks.length}</span> kept · `
    + `<span class="n">${opens.length}</span> role${opens.length === 1 ? '' : 's'} opened at `
    + `<span class="n">${cos.size}</span> compan${cos.size === 1 ? 'y' : 'ies'}`
    + (answered ? ` · <span class="n">${answered}</span> answered` : '') + '. ';
  s += `Of the <span class="n">${CUT.length}</span> companies in this cut you have opened a role at `
    + `<span class="n">${inCut}</span>.`;
  const third = gateSentence(opens);
  return s + (third ? ' ' + third : '');
}

const GATE_VERB = {
  'Y Combinator': 'Y Combinator backed',
  'SEC EDGAR': 'the SEC holds a Form D from',
  'CB Insights': 'CB Insights tracks',
  Forbes: 'a Forbes editor listed',
  TechCrunch: 'TechCrunch reported a round at',
};

function gateSentence(opens) {
  if (!opens.length) return '';
  const by = {};
  for (const o of opens) {
    const c = ALL.find((x) => x.s === o.s);
    if (c) by[c.g.who] = (by[c.g.who] || 0) + 1;
  }
  const ranked = Object.entries(by).sort((a, b) => b[1] - a[1]);
  if (!ranked.length) return '';
  const [who, n] = ranked[0];
  const touched = new Set(Object.keys(by));
  const untouched = {};
  for (const c of CUT) if (!touched.has(c.g.who)) untouched[c.g.who] = (untouched[c.g.who] || 0) + 1;
  const cold = Object.entries(untouched).sort((a, b) => b[1] - a[1])[0];
  let s = `${esc(who)} vouched for <span class="n">${n}</span> of the `
    + `<span class="n">${opens.length}</span> role${opens.length === 1 ? '' : 's'} you opened`;
  if (cold) {
    s += `; you have opened nothing at the <span class="n">${cold[1]}</span> compan`
      + `${cold[1] === 1 ? 'y' : 'ies'} here that ${GATE_VERB[cold[0]] || 'were listed by ' + esc(cold[0])}.`;
  } else s += '.';
  return s;
}

function askBox() {
  const t = today();
  const due = kept().filter(([, v]) => !v.answered_at && (v.opened || [])
    .some((o) => o.at < t));
  if (!due.length) return '';
  const [slug, rec] = due[0];
  const c = ALL.find((x) => x.s === slug);
  const when = rec.opened.filter((o) => o.at < t);
  const n = when.length;
  return `<div class="ask" data-s="${esc(slug)}"><p class="q">On ${pretty(when[0].at)} you opened `
    + `${n} role${n === 1 ? '' : 's'} at ${esc(c ? c.n : slug)}. Did you apply?</p>`
    + '<p class="why">I am asking because I cannot know. Opening a link is my hand; '
    + 'applying is yours, and nothing on this page may write that down for you.</p>'
    + '<div class="btns"><button type="button" data-a="yes">yes</button>'
    + '<button type="button" data-a="no">no</button>'
    + '<button type="button" data-a="not yet">not yet</button></div></div>';
}

function paintDeliver() {
  const ks = kept();
  const box = $('#deliver');
  box.hidden = !ks.length && !openedAll().length;
  $('#slrows').innerHTML = ks.map(([s, v], i) => slRow(s, v, i)).join('')
    || '<p class="slempty">Nothing kept yet — <em>keep</em> on any card pins it here, '
      + 'and the two buttons below turn it into something you can send.</p>';
  $('#askbox').innerHTML = askBox();
  $('#record').innerHTML = recordLine();
}

/* ================================================================== copying */

function shortlistText() {
  const ks = kept();
  const lines = [`${ks.length} compan${ks.length === 1 ? 'y' : 'ies'} I am applying to — ${pretty(today())}`,
    `found with ROLE·ATLAS, which read 10,125 companies and kept ${META.companies}`, ''];
  ks.forEach(([slug, rec], i) => {
    const c = ALL.find((x) => x.s === slug);
    if (!c) { lines.push(`${i + 1}. ${slug}`, ''); return; }
    lines.push(`${i + 1}. ${c.n} — ${c.r} roles open on their own board`);
    if (c.m) {
      lines.push(`   WHAT      ${c.m.w}`, `   FOR       ${c.m.f}`, `   WHY THEM  ${c.m.y}`,
        `   (${PROV[c.m.p]})`);
    } else {
      lines.push('   NOT YET READ — I have their gate and their board, not their site.',
        `   Their board's own words for its teams: ${(c.bw || []).join(' / ')}`);
    }
    lines.push(`   VOUCHED   ${c.g.line} — ${c.gc}`, `             ${c.g.url}`);
    const op = rec.opened || [];
    if (op.length) {
      lines.push(`   ROLES I OPENED (${op.length}, on ${pretty(op[0].at)}):`);
      for (const o of op) lines.push(`     ${o.title}`, `       ${o.url}`);
    }
    lines.push('');
  });
  lines.push(`Reopen this shortlist: ${location.origin}${location.pathname}${hashFor()}`);
  return lines.join('\n');
}

async function copy(text, said) {
  try {
    await navigator.clipboard.writeText(text);
  } catch (e) {
    const ta = document.createElement('textarea');
    ta.value = text; document.body.appendChild(ta); ta.select();
    document.execCommand('copy'); ta.remove();
  }
  window.__lastCopy = text;
  $('#said').textContent = said;
  setTimeout(() => { if ($('#said').textContent === said) $('#said').textContent = ''; }, 4000);
}

/* ============================================================ role shards == */

async function shard(slug) {
  if (shards.has(slug)) return shards.get(slug);
  const p = fetch(`data/roles/${slug}.json`).then((r) => r.json())
    .catch(() => ({ roles: [] }));
  shards.set(slug, p);
  return p;
}

function roleRow(r, i) {
  const chip = r.v ? `<span class="vchip">visa: ${r.v}</span>` : '';
  return `<a class="role" href="${esc(r.u)}" target="_blank" rel="noopener" data-i="${i}">`
    + `<span class="rn">${String(i + 1).padStart(2, '0')}</span>`
    + `<span class="rt">${esc(r.t)}${chip}</span>`
    + `<span class="rl">${esc(r.l || 'their board did not say where')}</span>`
    + '<span class="ra">apply ↗</span>'
    + `<span class="rb">${esc(r.b || 'their board gave this role no team')}</span></a>`;
}

async function expand(card) {
  const slug = card.dataset.s, box = $('.roles', card);
  if (!box.hidden) { box.hidden = true; return; }
  box.hidden = false;
  box.innerHTML = '<p class="rnote">reading their board…</p>';
  const data = await shard(slug);
  const c = ALL.find((x) => x.s === slug);
  let rows = data.roles;
  if (S.field !== 'any') rows = rows.filter((r) => r.d === S.field);
  if (S.place !== 'any') rows = rows.filter((r) => r.p.includes(S.place));
  if (!rows.length) rows = data.roles;
  const silent = rows.filter((r) => !r.v).length;
  const note = `${rows.length} of ${data.roles.length} roles on ${esc(c ? c.n : slug)}'s own board`
    + (silent ? `. Their board says nothing about visa sponsorship on ${silent} of them — `
      + 'that is silence, not a no.' : '.');
  box.innerHTML = `<p class="rnote">${note}</p>`
    + rows.slice(0, 12).map(roleRow).join('')
    + (rows.length > 12
      ? `<p class="rmore"><span>${rows.length - 12} more on their board — `
        + `<a href="${esc(data.roles[0] ? data.roles[0].u : '#')}" target="_blank" rel="noopener">open it ↗</a>`
        + '</span></p>' : '');
}

function witness(slug, title, url) {
  const r = REC[slug] || (REC[slug] = { kept_at: null, opened: [], applied: null, answered_at: null });
  if (!r.opened.some((o) => o.url === url)) r.opened.push({ url, title, at: today() });
  saveRec(); paintDeliver(); syncHash();
}

/* ================================================================ handlers = */

function toggleKeep(slug) {
  const r = REC[slug] || (REC[slug] = { kept_at: null, opened: [], applied: null, answered_at: null });
  r.kept_at = r.kept_at ? null : today();
  saveRec(); paintKeeps(); paintDeliver(); syncHash();
}

function onClick(e) {
  const g = e.target.closest('#gstrip button');
  if (g) { S.giants = false; paint();
    setTimeout(() => $(`#c-${CSS.escape(g.dataset.g)}`)?.scrollIntoView({ block: 'center' }), 60); return; }
  const drop = e.target.closest('[data-drop]');
  if (drop) { toggleKeep(drop.closest('.slrow').dataset.s); return; }
  const a = e.target.closest('.ask [data-a]');
  if (a) {
    const slug = a.closest('.ask').dataset.s, ans = a.dataset.a;
    REC[slug].applied = ans === 'not yet' ? null : ans;
    REC[slug].answered_at = today();
    saveRec(); paintDeliver(); return;
  }
  const card = e.target.closest('.card');
  if (!card) return;
  cursor = CUT.findIndex((c) => c.s === card.dataset.s);
  if (e.target.closest('.keep')) { toggleKeep(card.dataset.s); return; }
  if (e.target.closest('.open')) { expand(card); return; }
  const role = e.target.closest('a.role');
  if (role) witness(card.dataset.s, $('.rt', role).textContent, role.href);
}

/* the key queue: keys pressed before index.json lands are replayed, not dropped */
const queue = [];
const QUEUED = ['j', 'k', 'o', 'x', 'g', 'Enter', '1', '2', '3', '4', '5', '6', '7', '8', '9'];
function onKey(e) {
  if (/^(INPUT|SELECT|TEXTAREA)$/.test(e.target.tagName)) return;
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  if (!FULL && QUEUED.includes(e.key)) { queue.push(e.key); return; }
  runKey(e.key);
}

function runKey(k) {
  const move = (d) => {
    cursor = Math.max(0, Math.min(CUT.length - 1, cursor + d));
    const el = $(`#c-${CSS.escape(CUT[cursor].s)}`);
    $$('.card.on').forEach((c) => c.classList.remove('on'));
    if (el) { el.classList.add('on'); el.scrollIntoView({ block: 'center', behavior: 'instant' }); }
  };
  const cur = () => (cursor >= 0 && CUT[cursor] ? $(`#c-${CSS.escape(CUT[cursor].s)}`) : null);
  if (k === 'j') return move(cursor < 0 ? 0 : 1);
  if (k === 'k') return move(cursor < 0 ? 0 : -1);
  if (k === 'o' || k === 'Enter') { const c = cur(); if (c) expand(c); return; }
  if (k === 'x') { if (CUT[cursor]) toggleKeep(CUT[cursor].s); return; }
  if (k === 'g') { S.giants = !S.giants; paint(); return; }
  if (k === 'f') { $('#field').focus(); return; }
  if (k === 'p') { $('#place').focus(); return; }
  if (k === 'c') { copy(shortlistText(), 'copied — paste it anywhere'); return; }
  if (k === '?') { $('#keysheet').showModal(); return; }
  if (k === 'Escape') { $$('dialog[open]').forEach((d) => d.close()); return; }
  if (/^[1-9]$/.test(k)) {
    const card = cur(); if (!card) return;
    const row = $$('a.role', card)[+k - 1];
    if (row) { window.open(row.href, '_blank', 'noopener'); witness(card.dataset.s, $('.rt', row).textContent, row.href); }
  }
}

/* ================================================================== sheets = */

function fillSheets() {
  const f = META.funnel;
  $('#snapshot').textContent = pretty(META.snapshot);
  $('#rolecount').textContent = num(META.roles);
  $('#ladder').textContent = [
    `${num(f.read).padStart(6)}  company names read from the sources`,
    `        ├── ${num(f.not_qualified).padStart(5)}  did not qualify`,
    `        ├── ${num(f.not_software).padStart(5)}  not software`,
    `        └── ${num(f.ambiguous).padStart(5)}  ambiguous`,
    `${num(f.qualified).padStart(6)}  qualified as funded software companies`,
    `        └── ${num(f.no_board).padStart(5)}  no job board I could resolve`,
    `${num(f.boards_read).padStart(6)}  boards actually read`,
    `        ├── ${num(f.nothing_open).padStart(5)}  read, nothing open`,
    `        ├── ${num(f.wrong_board).padStart(5)}  another company's board`,
    `        └── ${num(f.empty).padStart(5)}  empty, unverified`,
    `${num(f.listed).padStart(6)}  companies with something open on ${pretty(META.snapshot)}`,
    `${num(META.roles).padStart(6)}  roles, every one live on the company's own board that day`,
  ].join('\n');
  $('#ladderNotes').innerHTML = [
    `The <span class="n">${num(f.no_board)}</span> I could not resolve a board for are "I could not look",`
    + ' not "not hiring". They are the largest number on this page and the least informative.',
    `<span class="n">${META.memo.absent}</span> of the ${META.companies} have no memo yet. That is a`
    + ' backlog in <span class="n">scripts/describe.py</span>, not a judgement about the company.',
    `<span class="n">${num(META.no_amount)}</span> of the ${META.companies} have no citable round, so their`
    + ' cards say nothing about money rather than a zero.',
  ].map((s) => `<li>${s}</li>`).join('');

  $('#neverBody').innerHTML = `
    <p>Six sentences I could write that would make this page more persuasive, and
       the reason each one is not here.</p>
    <h3>"Recently funded"</h3>
    <p>A funding date exists for <span class="n">122</span> of <span class="n">${META.companies}</span>
       companies, and only <span class="n">4</span> of those are inside 90 days. "Recently" would be
       true of about one company in two hundred, so the word is not on this page.</p>
    <h3>"Rocketship", "fast-growing", "hot"</h3>
    <p>There is no growth column in this corpus. What exists is a number of roles open on
       a board on one day. That number is printed; the adjective is not.</p>
    <h3>"New"</h3>
    <p>I have <span class="n">${META.first_seen.dated}</span> dated role URLs against
       <span class="n">${num(META.roles)}</span> roles. Nothing here may be called new until there are
       two snapshots to compare, which is a build job, not a copy job.</p>
    <p>The build greps its own memos for that word and the five like it, and finds
       <span class="n">${META.hype.n}</span> — ${esc(META.hype.examples.join(', '))} — every one of them
       the ordinary adjective inside a sentence about what a company sells, not a claim
       that the company or the role is new. They are counted here rather than edited
       away, because an audit you can run yourself is worth more than a promise:
       <span class="n">build.py hype_audit()</span>.</p>
    <h3>"You applied"</h3>
    <p>Opening a link is my hand. Applying is yours. The only way <span class="n">applied</span>
       is written down here is that you told me, in the one question this page asks.</p>
    <h3>"This company is better than that one"</h3>
    <p>Ordering is by counts you can see and check. A company that YC now lists as Public,
       Acquired or Inactive is neither promoted nor demoted for it — the status is printed with
       its source, and what it means to you is yours to decide.</p>
    <h3>"Not hiring"</h3>
    <p>Absence of a board is absence of a reading, not absence of a job. Every silence on this
       page is written as a silence.</p>`;

  const m = META.memo, g = META.gates, st = META.yc.status;
  const statuses = Object.entries(st).map(([k, v]) => `${v} ${k}`).join(' · ');
  $('#lede2').innerHTML =
    `Each card carries three lines — <em>what</em>, <em>for whom</em>, <em>why them</em>. Those `
    + `three are mine: I wrote them from the company's own site and checked <span class="n">${m.checked}</span> `
    + `of them against it, wrote <span class="n">${m.unchecked}</span> without checking, and took `
    + `<span class="n">${m.board}</span> off the company's own job board. `
    + `<span class="n">${m.absent}</span> companies I have not read at all, and those cards say `
    + `<em>not yet read</em> instead of guessing. The line under the memo is not mine at all: it is `
    + `who put this company on a list — Y Combinator <span class="n">${g['Y Combinator'] || 0}</span> · `
    + `CB Insights <span class="n">${g['CB Insights'] || 0}</span> · the SEC `
    + `<span class="n">${g['SEC EDGAR'] || 0}</span> · Forbes <span class="n">${g.Forbes || 0}</span> · `
    + `TechCrunch <span class="n">${g.TechCrunch || 0}</span> — and it is a link to the receipt. `
    + `<span class="n">${num(META.roles)}</span> roles, every one read off the company's own board on `
    + `${pretty(META.snapshot)}. Of the ${META.yc.n} Y Combinator companies, YC lists ${statuses}; `
    + 'all four are printed the same way, because a company that already went public is a fact, not a warning.';

  $('#foot').innerHTML =
    `Keeps live in this browser's localStorage and nowhere else — there is no account and no server. `
    + `The two buttons in the shortlist are how it leaves: one copies a memo you can paste into a message, `
    + `the other copies a link that reopens the same shortlist and the same narrowing on any device. `
    + `Departments and cities are bucketed by a vocabulary I wrote for this page, not by the boards; `
    + `<span class="n">${num(META.residue.roles)}</span> roles match none of my eleven fields.`;
}

function fillRegister() {
  $('#regsum').textContent = `the register — all ${META.companies} companies, in one list`;
  if (!FULL) {
    $('#reglist').innerHTML = '<div class="regrow">reading in all '
      + `${META.companies}…</div>`;
    return;
  }
  $('#reglist').innerHTML = ALL.slice().sort((a, b) => a.n.localeCompare(b.n))
    .map((c, i) => `<div class="regrow"><span>${String(i + 1).padStart(3, '0')}</span>`
      + `<span class="rgn">${esc(c.n)}</span><span>${c.r} roles</span>`
      + `<span class="rgg">${esc(c.g.who)}</span>`
      + `<span class="rgm">${c.m ? 'memo' : 'not yet read'}</span></div>`).join('');
}

/* ==================================================================== boot = */

function wire() {
  $('#field').onchange = (e) => { S.field = e.target.value; cursor = -1; paint(); };
  $('#place').onchange = (e) => { S.place = e.target.value; cursor = -1; paint(); };
  $('#order').onchange = (e) => { S.order = e.target.value; cursor = -1; paint(); };
  $('#ghide').onclick = () => { if (!S.giants) { S.giants = true; cursor = -1; paint(); } };
  $('#gshow').onclick = () => { if (S.giants) { S.giants = false; cursor = -1; paint(); } };
  $('#fbtn').onclick = () => $('#funnel').showModal();
  $('#nbtn').onclick = () => $('#never').showModal();
  $('#kbtn').onclick = () => $('#keysheet').showModal();
  $$('[data-close]').forEach((b) => { b.onclick = () => b.closest('dialog').close(); });
  $('#copyList').onclick = () => copy(shortlistText(), 'copied — paste it into a message');
  $('#copyLink').onclick = () => copy(location.origin + location.pathname + hashFor(),
    'link copied — it reopens this shortlist and this narrowing');
  document.addEventListener('click', onClick);
  document.addEventListener('keydown', onKey);
}

async function boot() {
  // The provenance paragraph is the page's argument and it stays open on any
  // sheet with room for it. At a hand's width it is 400px of small type between
  // the reader and the first company, so it opens folded — named, one tap away,
  // never removed.
  if (window.matchMedia('(max-width:62rem)').matches) $('#ledefold').open = false;
  readHash();
  fillMenus();
  fillSheets();
  wire();
  paint();
  fillRegister();
  const ix = await fetch('data/index.json').then((r) => r.json());
  ALL = ix.companies;
  FULL = true;
  window.__allLoaded = performance.now();
  paint();
  fillRegister();
  while (queue.length) runKey(queue.shift());
}

boot();
