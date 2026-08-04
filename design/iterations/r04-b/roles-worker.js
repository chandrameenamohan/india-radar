// roles-worker.js — the 9.8 MB roles file never touches the main thread.
//
// It is fetched and parsed here, after first paint, and the only things that
// cross back are (a) a compact field×place count per company, so the fold can
// answer a two-axis question exactly, and (b) the role rows for one company at
// a time, on expand. The card list stays at 60fps while 27,689 roles are read.

import { fieldOf, placesOf } from './taxonomy.js';

const SEP = '\u0001';

let BY = new Map();
let URLS = new Set();

// A card can be opened before the roles file has landed. The request waits here
// rather than being answered with an empty list.
let markReady;
const ready = new Promise((r) => { markReady = r; });

const trim = (r) => ({
  title: r.title, url: r.url, places: placesOf(r), dept: r.department || null,
  visa: r.visa === 'yes' || r.visa === 'no' ? r.visa : null,
  workplace: r.workplace || null,
});

self.onmessage = async (e) => {
  const m = e.data;

  if (m.t === 'init') {
    const t0 = performance.now();
    const res = await fetch(m.url);
    // Read it as a stream so the page can state how far along it is instead of
    // showing a spinner that means nothing. On a fast link this is one tick; on
    // Fast 3G the 9.8 MB take the best part of a minute and the reader is told.
    const total = Number(res.headers.get('content-length')) || 0;
    let doc;
    if (res.body && typeof TextDecoder !== 'undefined') {
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let text = '', got = 0, lastPost = 0;
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        got += value.byteLength;
        text += dec.decode(value, { stream: true });
        const now = performance.now();
        if (now - lastPost > 120) { lastPost = now; self.postMessage({ t: 'progress', got, total }); }
      }
      text += dec.decode();
      doc = JSON.parse(text);
    } else {
      doc = await res.json();
    }
    const joint = Object.create(null);
    let roles = 0;
    for (const c of doc.companies) {
      BY.set(c.slug, c);
      const jc = Object.create(null);
      for (const r of c.roles) {
        roles++;
        URLS.add(r.url);
        const f = fieldOf(r.dept_norm);
        for (const p of placesOf(r)) {
          const k = f + SEP + p;
          jc[k] = (jc[k] || 0) + 1;
        }
      }
      joint[c.slug] = jc;
    }
    markReady();
    self.postMessage({ t: 'joint', joint, roles, snapshot: doc.snapshot, ms: Math.round(performance.now() - t0) });
    return;
  }

  if (m.t === 'roles') {
    await ready;
    const c = BY.get(m.slug);
    if (!c) { self.postMessage({ t: 'roles', id: m.id, slug: m.slug, match: [], other: [], other_n: 0 }); return; }
    const match = [], other = [];
    for (const r of c.roles) {
      const okF = m.field === 'all' || fieldOf(r.dept_norm) === m.field;
      const okP = m.place === 'all' || placesOf(r).includes(m.place);
      (okF && okP ? match : other).push(r);
    }
    self.postMessage({
      t: 'roles', id: m.id, slug: m.slug,
      match: match.slice(0, 400).map(trim), match_n: match.length,
      other: other.slice(0, 400).map(trim), other_n: other.length,
    });
    return;
  }

  // Is a role a reader opened on an earlier night still on the company's board?
  // The only thing this register can truthfully say "gone" about.
  if (m.t === 'live') {
    await ready;
    self.postMessage({ t: 'live', id: m.id, live: m.urls.map((u) => URLS.has(u)) });
  }
};
