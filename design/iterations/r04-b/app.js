// app.js — r04-b, "the instrument".
//
// One screen. The loop is filter → scan → keep → open tabs, and every step of it
// is one key. Nothing here navigates; nothing here infers.

import { FIELD_LABEL, GIANT_FLOOR } from './taxonomy.js';
import { prepare, cardHTML, optionsHTML, esc, num } from './render.js';

const SEP = '\u0001';
const CARDS_URL = '../../fixture-v2/cards.json';
const ROLES_URL = '../../fixture-v2/companies.json';
const STORE = 'roleatlas.r04b.v1';

const $ = (s) => document.querySelector(s);
const params = new URLSearchParams(location.search);

/* ── the page's notion of today ─────────────────────────────────────────────
   The second-visit question needs a yesterday. `?day=+1` moves the page's
   clock forward one day so an evaluator can run M6 in one sitting without
   waiting for midnight. Nothing else reads it. */
const DAY_SHIFT = (() => {
  const raw = params.get('day') || (params.get('simulate') === 'next-day' ? '+1' : '0');
  const n = parseInt(raw, 10);
  return Number.isFinite(n) ? n : 0;
})();
const now = () => new Date(Date.now() + DAY_SHIFT * 864e5);
const dayOf = (d) => new Date(d).toISOString().slice(0, 10);
const today = () => dayOf(now());
const clock = (d) => new Date(d).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
const human = (iso) => {
  const [y, m, dd] = iso.split('-').map(Number);
  return ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][m - 1] + ' ' + dd;
};

/* ── state ────────────────────────────────────────────────────────────────── */
let CARDS = [];                 // prepared, all 789, never filtered away
let BY = new Map();
let JOINT = null;               // slug -> {"fieldplace": n}, from the worker
let ROWS = [];                  // current view order
let cur = 0;                    // card cursor
let openSlug = null;            // the one expanded card
let roleCur = 0;
let roleData = null;
let showAllRoles = false;
let worker = null, reqId = 0;
const pending = new Map();

const view = {
  field: params.get('field') || 'all',
  place: params.get('place') || 'all',
  giants: params.get('giants') !== 'off',
};

/* ── the shortlist, on disk ───────────────────────────────────────────────── */
if (params.has('reset')) localStorage.removeItem(STORE);

let SL = load();
function load() {
  try {
    const raw = JSON.parse(localStorage.getItem(STORE) || '{}');
    return raw && raw.v === 1 && raw.companies ? raw : { v: 1, companies: {} };
  } catch (e) { return { v: 1, companies: {} }; }
}
function save() { try { localStorage.setItem(STORE, JSON.stringify(SL)); } catch (e) {} }
function rec(slug) {
  return SL.companies[slug] || (SL.companies[slug] = {
    kept_at: null, open_at_keep: null, opens: [], applied: null, asked_at: null,
  });
}
const isKept = (slug) => !!(SL.companies[slug] && SL.companies[slug].kept_at);
const opensOf = (slug) => (SL.companies[slug] ? SL.companies[slug].opens : []) || [];

/* ── boot ─────────────────────────────────────────────────────────────────── */
// The keys and both menus are live before the data is. index.html already ships
// the full option lists and the first ten cards, so a reader who starts typing
// at 300ms is not typing into a dead page.
const t0 = performance.now();
let booted = false;
wire();
syncOptions();
boot();

async function boot() {
  const res = await fetch(CARDS_URL);
  const raw = await res.json();
  CARDS = raw.map(prepare);
  for (const c of CARDS) BY.set(c.slug, c);

  booted = true;
  syncOptions();
  render();
  status(`${num(CARDS.length)} companies in ${Math.round(performance.now() - t0)}ms · reading roles…`);

  startWorker();
  flushPending();

  // 376 hand-written one-liners live in the fixture. They are the one editorial
  // thing on this page; they appear only inside an opened card, labelled, with
  // their coverage stated. 413 companies have none and get no line at all.
  fetch('../../fixture-v2/descriptions.json')
    .then((r) => r.json())
    .then((d) => {
      for (const [k, v] of Object.entries(d)) if (v && v.what) DESCRIPTIONS[k] = v.what;
      if (openSlug) paintRoles();
    })
    .catch(() => {});
}

function startWorker() {
  try {
    worker = new Worker('./roles-worker.js', { type: 'module' });
    worker.onmessage = onWorker;
    worker.onerror = () => { worker = null; mainThreadRoles(); };
    worker.postMessage({ t: 'init', url: ROLES_URL });
  } catch (e) { mainThreadRoles(); }
}

// If module workers are unavailable, do it here rather than lose the feature.
async function mainThreadRoles() {
  const { fieldOf, placesOf } = await import('./taxonomy.js');
  const doc = await (await fetch(ROLES_URL)).json();
  const joint = Object.create(null); const by = new Map(); const urls = new Set();
  let roles = 0;
  for (const c of doc.companies) {
    by.set(c.slug, c);
    const jc = Object.create(null);
    for (const r of c.roles) {
      roles++; urls.add(r.url);
      const f = fieldOf(r.dept_norm);
      for (const p of placesOf(r)) { const k = f + SEP + p; jc[k] = (jc[k] || 0) + 1; }
    }
    joint[c.slug] = jc;
  }
  worker = {
    _by: by, _urls: urls,
    postMessage(m) {
      if (m.t === 'roles') {
        const c = by.get(m.slug); const match = [], other = [];
        for (const r of (c ? c.roles : [])) {
          const okF = m.field === 'all' || fieldOf(r.dept_norm) === m.field;
          const okP = m.place === 'all' || placesOf(r).includes(m.place);
          (okF && okP ? match : other).push({ title: r.title, url: r.url, places: placesOf(r), dept: r.department || null,
            visa: r.visa === 'yes' || r.visa === 'no' ? r.visa : null, workplace: r.workplace || null });
        }
        onWorker({ data: { t: 'roles', id: m.id, slug: m.slug, match: match.slice(0, 400), match_n: match.length, other: other.slice(0, 400), other_n: other.length } });
      } else if (m.t === 'live') {
        onWorker({ data: { t: 'live', id: m.id, live: m.urls.map((u) => urls.has(u)) } });
      }
    },
  };
  onWorker({ data: { t: 'joint', joint, roles, snapshot: doc.snapshot, ms: 0 } });
}

let rolesPct = 0;
function onWorker(e) {
  const m = e.data;
  if (m.t === 'progress') {
    rolesPct = m.total ? Math.min(99, Math.round(m.got * 100 / m.total)) : 0;
    status(`${num(CARDS.length)} companies · reading 27,689 roles${rolesPct ? ` — ${rolesPct}%` : '…'}`);
    if (openSlug && !roleData) paintRoles();
    return;
  }
  if (m.t === 'joint') {
    JOINT = m.joint;
    status(`${num(CARDS.length)} companies · ${num(m.roles)} roles ready`);
    render();
    // a card opened while the roles were still in flight fills itself in
    if (openSlug && !roleData) { const s = openSlug; openSlug = null; expand(s); }
    checkLive();
    return;
  }
  const p = pending.get(m.id);
  if (p) { pending.delete(m.id); p(m); }
}

function askWorker(msg) {
  return new Promise((resolve) => {
    const id = ++reqId;
    pending.set(id, resolve);
    worker.postMessage({ ...msg, id });
  });
}

/* ── the two dropdowns ────────────────────────────────────────────────────── */
// index.html ships them complete. This only rebuilds them if that failed, and
// then applies whatever the reader (or the query string) has already chosen.
function syncOptions() {
  const fsel = $('#field'), psel = $('#place');
  if (fsel.options.length < 2 && CARDS.length) {
    const o = optionsHTML(CARDS);
    fsel.innerHTML = o.field; psel.innerHTML = o.place;
  }
  fsel.value = view.field; if (!fsel.value) fsel.value = 'all';
  psel.value = view.place; if (!psel.value) psel.value = 'all';
  view.field = fsel.value; view.place = psel.value;
  $('#giants').checked = view.giants;
}

/* ── counting ─────────────────────────────────────────────────────────────── */
// Exact from cards.json on one axis. Exact from the worker on two. Never a
// guess: while the roles file is still landing, a two-axis question is answered
// on the axis the fold can prove, and the yield line says so.
function matchOf(c) {
  const { field, place } = view;
  if (field === 'all' && place === 'all') return c.open;
  if (place === 'all') return c.fields[field] || 0;
  if (field === 'all') return c.places[place] || 0;
  if (JOINT && JOINT[c.slug]) return JOINT[c.slug][field + SEP + place] || 0;
  return Math.min(c.fields[field] || 0, c.places[place] || 0);
}

function compute() {
  const { field, place, giants } = view;
  const shown = [], held = [];
  for (const c of CARDS) {
    const m = matchOf(c);
    if (m <= 0) continue;
    (giants && c.giant ? held : shown).push([c, m]);
  }
  const bySize = (a, b) => b[1] - a[1] || b[0].open - a[0].open || a[0].name.localeCompare(b[0].name);
  shown.sort(bySize); held.sort(bySize);
  return { shown, held, giantsInList: shown.filter(([c]) => c.giant).length };
}

/* ── render ───────────────────────────────────────────────────────────────── */
function render() {
  if (!booted) return;   // the pre-painted seed stands until cards.json lands
  const { shown, held, giantsInList } = compute();
  ROWS = shown.map(([c]) => c);
  if (cur >= ROWS.length) cur = Math.max(0, ROWS.length - 1);

  const st = (c, m, i) => ({ field: view.field, place: view.place, matching: m, kept: isKept(c.slug), rank: i + 1 });
  $('#list').innerHTML = shown.map(([c, m], i) => cardHTML(c, st(c, m, i))).join('');
  $('#heldlist').innerHTML = held.map(([c, m], i) => cardHTML(c, st(c, m, i))).join('');
  $('#held').style.display = held.length ? '' : 'none';
  $('#held').querySelector('summary').innerHTML = heldSummary(held.length);

  $('#yield').innerHTML = yieldLine(shown.length, held.length, giantsInList);
  renderStrip();
  renderTail();
  paintCursor();
  if (openSlug && ROWS.some((c) => c.slug === openSlug)) paintRoles();
  else if (openSlug) { openSlug = null; roleData = null; }
}

function heldSummary(n) {
  return `Held back: <b>${num(n)}</b> compan${n === 1 ? 'y' : 'ies'} with ${GIANT_FLOOR} or more roles open. `
    + `They are rendered below, not removed — uncheck <b>hide the giants</b> to put them back in the list.`;
}

function yieldLine(shown, held, giantsInList) {
  const { field, place } = view;
  const f = field === 'all' ? '' : ` <b>${esc(FIELD_LABEL[field].toLowerCase())}</b>`;
  const p = place === 'all' ? '' : ` in <b>${esc(place)}</b>`;
  const pend = (field !== 'all' && place !== 'all' && !JOINT)
    ? ` <span class="pend">· counting the exact overlap, 27,689 roles still loading</span>` : '';
  if (!shown && !held) {
    return `No company in the register has${f || ' roles'}${p} open tonight. `
      + `Nothing was dropped for a fact a board did not state — all <b>${num(CARDS.length)}</b> companies were read and none matched.${pend}`;
  }
  const a = `<b>${num(shown)}</b> compan${shown === 1 ? 'y is' : 'ies are'} hiring${f || ''}${p} tonight.`;
  let b;
  if (!view.giants) {
    b = giantsInList
      ? ` <b>${num(giantsInList)}</b> of them ${giantsInList === 1 ? 'has' : 'have'} ${GIANT_FLOOR} or more roles open — the names you already know. <kbd>g</kbd> hides them.`
      : ` None of them has ${GIANT_FLOOR} or more roles open.`;
  } else {
    b = held
      ? ` <b>${num(held)}</b> ${held === 1 ? 'has' : 'have'} ${GIANT_FLOOR} or more roles open and ${held === 1 ? 'is' : 'are'} held back below.`
      : ` None of them has ${GIANT_FLOOR} or more roles open.`;
  }
  return a + b + pend;
}

function paintCursor() {
  const cards = $('#list').children;
  for (let i = 0; i < cards.length; i++) cards[i].classList.toggle('cur', i === cur);
}

function focusCard(i, scroll) {
  cur = Math.max(0, Math.min(ROWS.length - 1, i));
  paintCursor();
  if (scroll !== false) {
    const el = $('#list').children[cur];
    if (el) el.scrollIntoView({ block: 'nearest' });
  }
}

const cardEl = (slug) => document.querySelector(`.card[data-slug="${CSS.escape(slug)}"]`);

/* ── the shortlist strip ──────────────────────────────────────────────────── */
function renderStrip() {
  const entries = Object.entries(SL.companies)
    .filter(([, r]) => r.kept_at || (r.opens && r.opens.length))
    .sort((a, b) => (b[1].kept_at || '').localeCompare(a[1].kept_at || ''));

  const strip = $('#strip');
  strip.classList.toggle('empty', entries.length === 0);
  const chips = entries.map(([slug, r]) => {
    const c = BY.get(slug);
    const name = c ? c.name : slug;
    const n = (r.opens || []).length;
    const live = (r.opens || []).filter((o) => o.live !== false).length;
    const kept = !!r.kept_at;
    const day = (r.kept_at || (r.opens[0] && r.opens[0].at) || '').slice(0, 10);
    const tip = kept
      ? `kept ${human(day)}${c ? ` · ${num(c.open)} roles open` : ''}${n ? ` · ${live} of ${n} opened roles still on their board` : ''}`
      : `you opened ${n} role${n === 1 ? '' : 's'} here on ${human(day)} — not kept`;
    return `<span class="chip${kept ? '' : ' witness'}" title="${esc(tip)}" data-slug="${esc(slug)}">`
      + `${esc(name)}${n ? ` <span class="n">${n}↗</span>` : ''}`
      + `<button data-act="unkeep" title="remove">×</button></span>`;
  }).join('');

  $('#chips').innerHTML = `<span class="striplabel">shortlist</span>`
    + (chips || `<span id="chipsempty">empty — press <kbd>x</kbd> on any company, or open a role and it lands here</span>`);

  // The one question, asked once, never inferred.
  const asks = entries.filter(([, r]) => {
    if (r.applied !== null || r.asked_at) return false;
    const opens = r.opens || [];
    return opens.length > 0 && opens.some((o) => dayOf(o.at) < today());
  });
  $('#asks').innerHTML = asks.map(([slug, r]) => {
    const c = BY.get(slug); const n = r.opens.length;
    const day = human(dayOf(r.opens[0].at));
    return `<div class="ask" data-slug="${esc(slug)}">`
      + `<span>On <b>${day}</b> you opened <b>${n}</b> role${n === 1 ? '' : 's'} at <b>${esc(c ? c.name : slug)}</b>. Did you apply?</span>`
      + `<span class="btns">`
        + `<button data-ans="yes">yes</button><button data-ans="no">no</button><button data-ans="not_yet">not yet</button>`
      + `</span></div>`;
  }).join('');
}

// A kept role that has left the corpus is the one thing this page may call gone.
async function checkLive() {
  const all = [];
  for (const [slug, r] of Object.entries(SL.companies)) for (const o of (r.opens || [])) all.push([slug, o]);
  if (!all.length || !worker) return;
  const { live } = await askWorker({ t: 'live', urls: all.map(([, o]) => o.url) });
  let changed = false;
  all.forEach(([, o], i) => { if (o.live !== live[i]) { o.live = live[i]; changed = true; } });
  if (changed) { save(); renderStrip(); }
}

/* ── expand ───────────────────────────────────────────────────────────────── */
async function expand(slug) {
  if (openSlug === slug) { collapse(); return; }
  openSlug = slug; roleCur = 0; showAllRoles = false; roleData = null;
  paintRoles();
  if (!worker) return;
  const r = await askWorker({ t: 'roles', slug, field: view.field, place: view.place });
  if (openSlug !== slug) return;
  roleData = r;
  paintRoles();
}

function collapse() { const s = openSlug; openSlug = null; roleData = null; if (s) paintRoles(s); }

function paintRoles(forSlug) {
  document.querySelectorAll('.roles').forEach((el) => {
    if (el.closest('.card').dataset.slug !== openSlug) { el.hidden = true; el.innerHTML = ''; }
  });
  const slug = openSlug || forSlug;
  if (!openSlug) return;
  const card = cardEl(slug); if (!card) return;
  const box = card.querySelector('.roles');
  box.hidden = false;

  const c = BY.get(slug);
  const what = DESCRIPTIONS[c.name];
  const head = what
    ? `<p class="what"><a href="#how" data-act="how">what they do <sup>376/789</sup></a>${esc(what)}</p>` : '';

  if (!roleData) {
    box.innerHTML = head + `<p class="what">reading ${esc(c.name)}'s ${num(c.open)} roles`
      + (rolesPct ? ` — the roles file is ${rolesPct}% here` : '…') + `</p>`;
    return;
  }

  const opened = new Set(opensOf(slug).map((o) => o.url));
  const list = showAllRoles ? roleData.match.concat(roleData.other) : roleData.match;
  const cap = showAllRoles ? list.length : Math.min(list.length, 9);
  const rows = list.slice(0, cap).map((r, i) => roleRow(r, i, opened, i === roleCur)).join('');

  const bits = [];
  if (!showAllRoles && roleData.match_n > cap) bits.push(`<button data-act="allroles">show all ${num(roleData.match_n)} that match</button>`);
  if (roleData.other_n) bits.push(`<button data-act="allroles">${num(roleData.other_n)} more roles at ${esc(c.name)} that do not match</button>`);
  bits.push(`<span>grouped by the department ${esc(c.name)}'s own ${esc(c.ats)} board states, not by job title · every row links to that board · read Aug 4, 2026</span>`);

  box.innerHTML = head + rows + `<div class="rest">${bits.join('')}</div>`;
}

function roleRow(r, i, opened, isCur) {
  const was = opened.has(r.url);
  const o = was ? opensOf(openSlug).find((x) => x.url === r.url) : null;
  const visa = r.visa === 'yes' ? `<span class="visa">the posting states it hires from abroad</span>`
    : r.visa === 'no' ? `<span class="visa" style="color:var(--warn)">the posting states it cannot sponsor</span>` : '';
  const place = r.places.length ? r.places.join(' · ') : '';
  // "Remote · remote" helps nobody: if the board already said it in the place,
  // the workplace field adds nothing.
  const lower = r.places.map((x) => x.toLowerCase());
  const wp = r.workplace && !lower.includes(r.workplace) ? r.workplace : '';
  return `<a class="role${was ? ' opened' : ''}${isCur ? ' rcur' : ''}" href="${esc(r.url)}" target="_blank" rel="noopener"`
    + ` data-url="${esc(r.url)}" data-title="${esc(r.title)}" data-i="${i}">`
    + `<span class="k">${i < 9 ? i + 1 : '·'}</span>`
    + `<span class="t">${esc(r.title)}</span>`
    + visa
    + (r.dept ? `<span class="d">${esc(r.dept)}</span>` : '')
    + `<span class="p">${esc([place, wp].filter(Boolean).join(' · '))}</span>`
    + `<span class="go">${was ? `✓ opened ${clock(o.at)}` : 'Apply ↗'}</span>`
    + `</a>`;
}

/* ── acts ─────────────────────────────────────────────────────────────────── */
function toggleKeep(slug) {
  const r = rec(slug);
  if (r.kept_at) {
    r.kept_at = null; r.open_at_keep = null;
    if (!r.opens.length) delete SL.companies[slug];
  } else {
    r.kept_at = now().toISOString();
    r.open_at_keep = (BY.get(slug) || {}).open ?? null;
  }
  save();
  const el = cardEl(slug);
  if (el) {
    const on = isKept(slug);
    el.classList.toggle('kept', on);
    const b = el.querySelector('.btn.keep');
    b.classList.toggle('on', on);
    b.innerHTML = (on ? '◆ kept' : '◇ keep') + ' <kbd>x</kbd>';
  }
  renderStrip();
}

// The page witnesses that it handed you a URL. It never concludes you applied.
function witness(slug, url, title) {
  const r = rec(slug);
  if (!r.opens.some((o) => o.url === url)) {
    r.opens.push({ url, title, at: now().toISOString(), live: true });
    save();
  }
  renderStrip();
  paintRoles();
}

// A keystroke opens a real tab the same way a click does: by activating the
// anchor that is already on screen. window.open() is the fallback, not the path
// — a synthetic anchor click keeps the browser's own "this was a user gesture"
// bookkeeping intact, and pop-up blockers leave it alone.
function openRole(slug, r) {
  const a = document.querySelector(`.card[data-slug="${CSS.escape(slug)}"] a.role[data-url="${CSS.escape(r.url)}"]`);
  if (a) a.click(); else window.open(r.url, '_blank', 'noopener');
  // Repainting the row now would pull the anchor out of the document before the
  // browser has acted on the click, and the tab would never open. Witness — and
  // repaint — one tick later.
  setTimeout(() => witness(slug, r.url, r.title), 0);
}

function currentList() {
  if (!roleData) return [];
  return showAllRoles ? roleData.match.concat(roleData.other) : roleData.match;
}

function openNext() {
  if (!openSlug || !roleData) return;
  const list = currentList();
  const opened = new Set(opensOf(openSlug).map((o) => o.url));
  let i = roleCur;
  while (i < list.length && opened.has(list[i].url)) i++;
  if (i >= list.length) return;
  openRole(openSlug, list[i]);
  roleCur = Math.min(i + 1, list.length - 1);
}

/* ── wiring ───────────────────────────────────────────────────────────────── */
function wire() {
  $('#field').addEventListener('change', (e) => { view.field = e.target.value; cur = 0; collapse(); render(); });
  $('#place').addEventListener('change', (e) => { view.place = e.target.value; cur = 0; collapse(); render(); });
  $('#giants').addEventListener('change', (e) => { view.giants = e.target.checked; cur = 0; render(); });

  document.addEventListener('click', (e) => {
    const roleA = e.target.closest('a.role');
    if (roleA) {
      const slug = roleA.closest('.card').dataset.slug;
      // let the anchor open its own tab first; witness on the next tick
      setTimeout(() => witness(slug, roleA.dataset.url, roleA.dataset.title), 0);
      return; // no navigation here, ever
    }
    const btn = e.target.closest('[data-act],[data-ans],.chip');
    if (!btn) return;
    const act = btn.dataset.act;

    if (act === 'how') { e.preventDefault(); sheet('how'); return; }
    if (act === 'allroles') { showAllRoles = true; paintRoles(); return; }
    if (act === 'showall') {
      view.field = 'all'; view.place = 'all'; view.giants = false;
      $('#field').value = 'all'; $('#place').value = 'all'; $('#giants').checked = false;
      cur = 0; collapse(); render(); window.scrollTo({ top: 0 }); return;
    }
    if (btn.dataset.ans) {
      const slug = btn.closest('.ask').dataset.slug;
      const r = rec(slug);
      r.applied = btn.dataset.ans; r.asked_at = now().toISOString();
      save(); renderStrip(); return;
    }
    if (btn.classList && btn.classList.contains('chip') && !act) {
      const slug = btn.dataset.slug;
      const i = ROWS.findIndex((c) => c.slug === slug);
      if (i >= 0) focusCard(i);
      return;
    }
    if (act === 'unkeep') {
      const slug = btn.closest('.chip').dataset.slug;
      delete SL.companies[slug]; save(); render(); return;
    }
    const card = e.target.closest('.card');
    if (!card) return;
    const slug = card.dataset.slug;
    const i = ROWS.findIndex((c) => c.slug === slug);
    if (i >= 0) focusCard(i, false);
    if (act === 'keep') toggleKeep(slug);
    else if (act === 'expand') expand(slug);
  });

  $('#veil').addEventListener('click', (e) => { if (e.target.id === 'veil' || e.target.dataset.act === 'close') $('#veil').hidden = true; });
  $('#how').addEventListener('click', () => sheet('how'));

  document.addEventListener('keydown', onKey);
}

function onKey(e) {
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  const tag = (e.target.tagName || '').toLowerCase();
  const inField = tag === 'select' || tag === 'input';

  if (e.key === 'Escape') {
    if (!$('#veil').hidden) { $('#veil').hidden = true; return; }
    if (inField) { e.target.blur(); return; }
    if (openSlug) { collapse(); return; }
    return;
  }
  if (inField) {
    if (e.key === 'Enter') { e.preventDefault(); e.target.blur(); }
    return;
  }
  if (!$('#veil').hidden) { if (e.key === '?' || e.key === 'h') $('#veil').hidden = true; return; }

  const k = e.key;
  // A key pressed in the first few hundred milliseconds is not a key thrown
  // away. It waits for the register and then happens.
  if (!booted && 'jkxG'.includes(k) || (!booted && k === 'Enter')) {
    e.preventDefault(); pendingKeys.push(k); return;
  }
  if (k === 'j' || k === 'ArrowDown') { e.preventDefault(); moveDown(); return; }
  if (k === 'k' || k === 'ArrowUp') { e.preventDefault(); moveUp(); return; }
  if (k === 'Enter') { e.preventDefault(); if (ROWS[cur]) expand(ROWS[cur].slug); return; }
  if (k === 'x') { e.preventDefault(); if (ROWS[cur]) toggleKeep(ROWS[cur].slug); return; }
  if (k === 'o') { e.preventDefault(); if (!openSlug && ROWS[cur]) expand(ROWS[cur].slug); else openNext(); return; }
  if (k >= '1' && k <= '9') {
    if (!openSlug || !roleData) return;
    e.preventDefault();
    const r = currentList()[+k - 1];
    if (r) { openRole(openSlug, r); roleCur = Math.min(+k, currentList().length - 1); }
    return;
  }
  if (k === 'f') { e.preventDefault(); $('#field').focus(); return; }
  if (k === 'c') { e.preventDefault(); $('#place').focus(); return; }
  if (k === 'g') { e.preventDefault(); const b = $('#giants'); b.checked = !b.checked; view.giants = b.checked; cur = 0; render(); return; }
  if (k === '?' || k === 'h') { e.preventDefault(); sheet(k === 'h' ? 'how' : 'keys'); return; }
  if (k === 'G') { e.preventDefault(); focusCard(ROWS.length - 1); return; }
}

const pendingKeys = [];
function flushPending() {
  const q = pendingKeys.splice(0);
  for (const k of q) {
    if (k === 'j') moveDown();
    else if (k === 'k') moveUp();
    else if (k === 'G') focusCard(ROWS.length - 1);
    else if (k === 'x' && ROWS[cur]) toggleKeep(ROWS[cur].slug);
    else if (k === 'Enter' && ROWS[cur]) expand(ROWS[cur].slug);
  }
}

function moveDown() {
  if (openSlug && roleData) {
    const list = currentList();
    if (roleCur < Math.min(list.length, showAllRoles ? list.length : 9) - 1) { roleCur++; paintRoles(); scrollRole(); return; }
    collapse();
  }
  focusCard(cur + 1);
}
function moveUp() {
  if (openSlug && roleData) {
    if (roleCur > 0) { roleCur--; paintRoles(); scrollRole(); return; }
    collapse();
  }
  focusCard(cur - 1);
}
function scrollRole() {
  const el = document.querySelector('.role.rcur');
  if (el) el.scrollIntoView({ block: 'nearest' });
}

function status(s) { $('#st').textContent = s; }

/* ── the how sheet ────────────────────────────────────────────────────────── */
function sheet(which) {
  $('#sheet').innerHTML = which === 'keys' ? KEYS_HTML : HOW_HTML;
  $('#veil').hidden = false;
}

function renderTail() {
  $('#tail').innerHTML = TAIL_HTML;
}

// filled in by build.mjs, from the fixture
const DESCRIPTIONS = {};
const HOW_HTML = window.__HOW || '';
const TAIL_HTML = window.__TAIL || '';
const KEYS_HTML = `
<h2>Every key on this page</h2>
<p class="sub">The loop is: narrow, scan, keep, open. Nothing here needs the mouse.</p>
<div class="keys">
  <div><kbd>j</kbd><span>next company — or, inside an open card, the next role</span></div>
  <div><kbd>k</kbd><span>previous</span></div>
  <div><kbd>↵</kbd><span>open this company's matching roles, in place</span></div>
  <div><kbd>o</kbd><span>open the next role you have not opened, in a new tab</span></div>
  <div><kbd>1</kbd>–<kbd>9</kbd><span>open that numbered role in a new tab</span></div>
  <div><kbd>x</kbd><span>keep this company on the shortlist</span></div>
  <div><kbd>f</kbd><span>the field dropdown · <kbd>↵</kbd> returns you to the list</span></div>
  <div><kbd>c</kbd><span>the city dropdown</span></div>
  <div><kbd>g</kbd><span>hide the giants — companies with 100+ roles open</span></div>
  <div><kbd>h</kbd><span>how these 789 companies got here</span></div>
  <div><kbd>esc</kbd><span>close the open card</span></div>
  <div><kbd>?</kbd><span>this list</span></div>
</div>
<p>The shortlist lives in this browser only — there is no account, and nothing about you leaves the page. Opening a role is recorded as <em>opened</em>, with the time. Whether you applied is a question this page asks you once; it will never decide it for you.</p>
<button class="close" data-act="close">close</button>`;
