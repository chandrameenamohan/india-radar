// render.js — the company card, in one place, so the pre-painted seed in
// index.html and the live render from cards.json cannot drift apart.

import { fieldOf, placeOf, FIELDS, FIELD_LABEL, gateOf, gateLine, GATE_NAME, GIANT_FLOOR } from './taxonomy.js';

export const esc = (s) => String(s == null ? '' : s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

export const num = (n) => n.toLocaleString('en-US');

// One pass over cards.json. Everything the fold needs is here; nothing on the
// fold waits for the 9.8 MB roles file.
export function prepare(card) {
  const fields = {};
  for (const [d, n] of Object.entries(card.depts || {})) {
    const f = fieldOf(d);
    fields[f] = (fields[f] || 0) + n;
  }
  const places = {};
  for (const [p, n] of Object.entries(card.places || {})) {
    const c = placeOf(p);
    if (!c) continue;
    places[c] = (places[c] || 0) + n;
  }
  const gate = gateOf(card);
  return {
    slug: card.slug,
    name: card.name,
    ats: card.ats,
    open: card.roles_open,
    giant: card.roles_open >= GIANT_FLOOR,
    fields,
    places,
    fieldList: Object.entries(fields).sort((a, b) => b[1] - a[1]),
    placeList: Object.entries(places).sort((a, b) => b[1] - a[1]),
    gate,
    gateName: GATE_NAME[gate],
    gateText: gateLine(card),
    gateHref: card.source_url || '',
    yc: card.yc || null,
    amount: card.amount,
  };
}

function factLine(list, label, sel, cap) {
  const parts = [];
  let shown = 0, rest = 0, restRoles = 0;
  const ordered = sel ? [...list].sort((a, b) => (b[0] === sel) - (a[0] === sel)) : list;
  for (const [k, n] of ordered) {
    const name = label ? (FIELD_LABEL[k] || k) : k;
    if (shown < cap) {
      const on = sel && k === sel ? ' on' : '';
      // name and count in ONE node: a place called "New York" is never a claim
      // standing on its own, it is always a stated count of open roles.
      parts.push(`<span class="k${on}">${esc(name)} <span class="v">${num(n)}</span></span>`);
      shown++;
    } else { rest++; restRoles += n; }
  }
  let s = parts.join(' <span class="sep">·</span> ');
  if (rest) s += ` <span class="more">· ${rest} more ${label ? 'field' : 'place'}${rest > 1 ? 's' : ''}, ${num(restRoles)} role${restRoles === 1 ? '' : 's'}</span>`;
  return s;
}

// `matching` is the count of roles at this company that answer the current
// question. Exact from cards.json for one-axis questions; exact from the roles
// worker once it lands for two-axis ones.
export function actionLabel(matching, field, place) {
  const f = field !== 'all' ? ' ' + (FIELD_LABEL[field] || field).toLowerCase() : '';
  const p = place !== 'all' ? ' in ' + place : '';
  return `<span class="num">${num(matching)}</span>${esc(f)} role${matching === 1 ? '' : 's'}${esc(p)}`;
}

export function cardHTML(c, st) {
  const { field = 'all', place = 'all', matching = c.open, kept = false, rank = 0 } = st || {};

  const staff = c.yc && c.yc.team_size
    ? ` <em>· YC lists ${num(c.yc.team_size)} people</em>` : '';

  const badges = [];
  if (c.yc && c.yc.status && c.yc.status !== 'Active') {
    badges.push(`<a class="badge status" href="${esc(c.gateHref)}" target="_blank" rel="noopener">YC says ${esc(c.yc.status)} ↗</a>`);
  }
  if (c.yc && c.yc.top_company) {
    badges.push(`<a class="badge tc" href="${esc(c.gateHref)}" target="_blank" rel="noopener">YC top company ↗</a>`);
  }

  return `<article class="card${kept ? ' kept' : ''}" data-slug="${esc(c.slug)}">`
    + `<span class="rank">${rank}</span>`
    + `<h3 class="name"><span class="nm">${esc(c.name)}</span>`
    + `<span class="cnt">${num(c.open)} roles open${staff}</span></h3>`
    + `<div class="row2">`
      + `<a class="gate" href="${esc(c.gateHref)}" target="_blank" rel="noopener">${esc(c.gateText)} <span class="arw">↗</span></a>`
      + `<span class="slot"></span>${badges.join('')}`
    + `</div>`
    + `<div class="facts">${factLine(c.fieldList, true, field === 'all' ? null : field, 4)}</div>`
    + `<div class="row4">`
      + `<div class="facts">${factLine(c.placeList, false, place === 'all' ? null : place, 4)}</div>`
      + `<div class="act">`
        + `<button class="btn keep${kept ? ' on' : ''}" data-act="keep">${kept ? '◆ kept' : '◇ keep'} <kbd>x</kbd></button>`
        + `<button class="btn pri" data-act="expand">${actionLabel(matching, field, place)} <kbd>↵</kbd></button>`
      + `</div>`
    + `</div>`
    + `<div class="roles" hidden></div>`
    + `</article>`;
}

// The two menus are a pure function of cards.json, so they are generated at
// build time into index.html: both dropdowns work before app.js has run.
export function optionsHTML(prepared) {
  const ft = {}, pt = {};
  for (const c of prepared) {
    for (const [k, n] of Object.entries(c.fields)) ft[k] = (ft[k] || 0) + n;
    for (const [k, n] of Object.entries(c.places)) pt[k] = (pt[k] || 0) + n;
  }
  const field = `<option value="all">any field</option>` + FIELDS
    .filter(([k]) => ft[k])
    .sort((a, b) => ft[b[0]] - ft[a[0]])
    .map(([k, label]) => `<option value="${k}">${esc(label)} — ${num(ft[k])} roles</option>`)
    .join('');
  const place = `<option value="all">anywhere</option>` + Object.entries(pt)
    .filter(([, n]) => n >= 12)
    .sort((a, b) => b[1] - a[1])
    .map(([k, n]) => `<option value="${esc(k)}">${esc(k)} — ${num(n)} roles</option>`)
    .join('');
  return { field, place };
}
