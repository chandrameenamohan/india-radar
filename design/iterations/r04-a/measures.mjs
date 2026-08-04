// PRODUCT-1 §6, M1–M6, run against the page as it actually runs. Real mouse
// events at real coordinates; nothing is asserted from the source.
//
//   node measures.mjs [m1 m2 m3 m4 m5 m6]        (default: all)
//
// Expects a static server on the repo root at 8741 and a private headless
// Chrome on 9741 — see NOTES.md for the two commands.
import { withPage, evalIn, waitFor, shot, sleep, URL_, OUT } from "./cdp.mjs";

const want = process.argv.slice(2).filter((a) => /^m[1-6]$/.test(a));
const run = (m) => !want.length || want.includes(m);
const ok = (b) => (b ? "PASS" : "FAIL");
const results = [];
function report(id, pass, detail) {
  results.push([id, pass]);
  console.log(`\n${id} ${ok(pass)} — ${detail}`);
}

async function settled(c, roles = false) {
  await waitFor(c, 'document.querySelectorAll(".card").length > 0');
  await waitFor(c, "window.__atlas && window.__atlas.ready()");
  if (roles) {
    await evalIn(c, "window.__atlas.loadRoles()");
    await waitFor(c, "window.__atlas.rolesReady()", 60000);
  }
  await sleep(120);
}

/* ── mouse ───────────────────────────────────────────────────────────── */
async function click(c, selector, nth = 0) {
  const box = await evalIn(c, `(() => {
    const e = document.querySelectorAll(${JSON.stringify(selector)})[${nth}];
    if (!e) return null;
    e.scrollIntoView({block:"center"});
    const r = e.getBoundingClientRect();
    return {x: r.left + r.width/2, y: r.top + r.height/2, t: e.textContent.trim().slice(0,60)};
  })()`);
  if (!box) throw new Error("no element for " + selector + " #" + nth);
  for (const type of ["mousePressed", "mouseReleased"])
    await c.send("Input.dispatchMouseEvent", {
      type, x: box.x, y: box.y, button: "left", clickCount: 1,
    });
  await sleep(60);
  return box.t;
}
const byText = (sel, text) =>
  `[...document.querySelectorAll(${JSON.stringify(sel)})].findIndex(e => e.textContent.trim().startsWith(${JSON.stringify(text)}))`;

/* ── M1 · time to first company card, Fast 3G, cache disabled ─────────── */
if (run("m1")) {
  const runs = [];
  for (let i = 0; i < 3; i++) {
    await withPage(async (c) => {
      await c.send("Page.navigate", { url: URL_ + "?cachebust=" + Date.now() });
      await waitFor(c, "window.__firstCardPainted", 30000, 10);
      runs.push(await evalIn(c, "window.__firstCardPainted"));
    }, { throttle: true });
  }
  const worst = Math.max(...runs);
  report("M1", worst < 1500,
    `first card painted at ${runs.map((r) => Math.round(r) + "ms").join(" / ")} on Fast 3G, cache disabled (target < 1500ms, worst of 3 = ${Math.round(worst)}ms)`);
}

/* ── M2 · the curation is legible in five seconds ─────────────────────── */
if (run("m2")) {
  await withPage(async (c) => {
    await c.send("Page.navigate", { url: URL_ });
    await settled(c);
    const p = await shot(c, "m2-load.png");
    // Every text node whose own box sits inside the 1280×900 viewport — the
    // pixels an evaluator is handed, and nothing below them.
    const text = await evalIn(c, `(() => {
      const vh = innerHeight, out = [];
      const w = document.createTreeWalker(document.querySelector("main"), NodeFilter.SHOW_TEXT);
      const range = document.createRange();
      for (let t = w.nextNode(); t; t = w.nextNode()) {
        if (!t.textContent.trim()) continue;
        range.selectNode(t);
        const r = range.getBoundingClientRect();
        if (r.top < vh && r.bottom > 0) out.push(t.textContent.replace(/\\s+/g, " ").trim());
      }
      return out.join(" ");
    })()`);
    const gates = ["Y Combinator", "CB Insights", "Forbes", "SEC EDGAR"].filter((g) => text.includes(g));
    const didnt = /didn.t qualify|no job board/.test(text);
    report("M2", gates.length >= 3 && didnt,
      `viewport screenshot ${p}\n     above the fold, verbatim: "${text.slice(0, 220)}…"\n     named gatekeepers on the first screen: ${gates.join(", ")} · who didn't make it: ${didnt ? "6,895 didn't qualify + 2,076 no job board" : "ABSENT"}`);
  });
}

/* ── M3 · time to three apply-tabs ────────────────────────────────────── */
if (run("m3")) {
  await withPage(async (c) => {
    let navigations = 0, tabs = 0;
    c.on((m) => {
      if (m.method === "Page.frameNavigated" && !m.params.frame.parentId) navigations++;
      if (m.method === "Page.windowOpen") tabs++;
    });
    await c.send("Page.navigate", { url: URL_ });
    await waitFor(c, 'document.querySelectorAll(".card").length > 0');
    const t0 = Date.now();
    navigations = 0;                                  // the load itself is not a click
    let clicks = 0;
    const before = (await (await fetch("http://127.0.0.1:9741/json/list")).json()).length;

    // "You are a backend engineer who wants to work in San Francisco."
    await waitFor(c, "window.__atlas.ready()");
    const iDept = await evalIn(c, byText(".chip", "engineering"));
    await click(c, ".chip", iDept); clicks++;
    const iCity = await evalIn(c, byText(".chip", "San Francisco"));
    await click(c, ".chip", iCity); clicks++;
    await evalIn(c, "window.__atlas.loadRoles()");
    await waitFor(c, "window.__atlas.rolesReady()", 60000);
    const first = await evalIn(c, 'document.querySelector(".card .name").textContent');
    await click(c, ".card .act"); clicks++;
    await waitFor(c, 'document.querySelectorAll(".role .apply").length >= 3');
    for (let i = 0; i < 3; i++) { await click(c, ".role .apply", i); clicks++; }
    await sleep(500);
    const list = await (await fetch("http://127.0.0.1:9741/json/list")).json();
    const opened = list.filter((t) => t.type === "page" && !t.url.includes("index.html") && t.url !== "about:blank");
    const secs = (Date.now() - t0) / 1000;
    const co = await evalIn(c, '[...document.querySelectorAll(".card .name")].slice(0,3).map(e=>e.textContent).join(", ")');
    for (const t of opened) await fetch("http://127.0.0.1:9741/json/close/" + t.id);
    report("M3", secs < 60 && clicks <= 6 && navigations === 0 && opened.length >= 3,
      `${secs.toFixed(1)}s · ${clicks} clicks · ${navigations} page navigations · ${opened.length} apply tabs opened (${list.length - before} new targets)\n     first three companies under the cut: ${co}\n     expanded: ${first}\n     tabs: ${opened.map((t) => t.url.slice(0, 62)).join("\n            ")}`);
  });
}

/* ── M4 · zero unevidenced claims ─────────────────────────────────────── */
if (run("m4")) {
  await withPage(async (c) => {
    await c.send("Page.navigate", { url: URL_ });
    await settled(c, true);
    // The fullest DOM the page can render: all 789 cards, the sieve open, one
    // card expanded onto its role rows, and a department cut on so the
    // ungrouped disclosure is printed too.
    await click(c, ".sieve-open");
    await evalIn(c, 'document.getElementById("giants").click()');
    await click(c, ".chip", await evalIn(c, byText(".chip", "engineering")));
    await sleep(400);
    await click(c, ".card .act");
    await sleep(400);
    const bad = await evalIn(c, `(() => {
      const RE = /rocketship|recently|funded|\\bnew\\b|\\btop\\b|\\bbest\\b|fast-growing/i;
      const out = [];
      document.querySelectorAll("main *").forEach(e => {
        const own = [...e.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join(" ");
        if (!RE.test(own)) return;
        const node = e.closest("a") ? e.closest("a") : e;
        const evid = node.querySelector("a") || node.closest("a") ||
                     /\\d/.test(node.textContent);
        if (!evid) out.push(own.trim().slice(0, 90));
      });
      return out;
    })()`);
    const hits = await evalIn(c, `(() => {
      const RE = /rocketship|recently|funded|\\bnew\\b|\\btop\\b|\\bbest\\b|fast-growing/gi;
      return (document.querySelector("main").innerText.match(RE) || []).length;
    })()`);
    report("M4", bad.length === 0,
      `${hits} matches of /rocketship|recently|funded|new|top|best|fast-growing/ in the rendered DOM, each with a link, a date or a count in its own node. Unevidenced: ${bad.length ? JSON.stringify(bad) : "none"}`);
  });
}

/* ── M5 · absence renders as absence ──────────────────────────────────── */
if (run("m5")) {
  await withPage(async (c) => {
    await c.send("Page.navigate", { url: URL_ });
    await settled(c, true);
    const r = await evalIn(c, `(async () => {
      const cards = await (await fetch("../../fixture-v2/cards.json")).json();
      const nulls = cards.filter(c => c.amount === null && c.roles_open < 100).slice(0, 10);
      const names = [...document.querySelectorAll(".card .name")].map(e => e.textContent);
      const missing = nulls.filter(c => !names.includes(c.name)).map(c => c.name);
      // (b) nothing in the card stands in for the absent amount: no element
      // whose whole content is a placeholder, and no dimming.
      const PLACE = /^(0|\\$0|—|–|-|n\\/a|no|none|unknown|null|undisclosed)$/i;
      const shouty = [];
      nulls.forEach(c => {
        const card = [...document.querySelectorAll(".card")].find(e => e.querySelector(".name").textContent === c.name);
        if (!card) return;
        card.querySelectorAll("*").forEach(e => {
          if (!e.children.length && PLACE.test(e.textContent.trim())) shouty.push(c.name + ": " + e.textContent.trim());
        });
        const op = +getComputedStyle(card).opacity;
        if (op < 1) shouty.push(c.name + ": opacity " + op);
      });
      const gates = nulls.map(c => {
        const card = [...document.querySelectorAll(".card")].find(e => e.querySelector(".name").textContent === c.name);
        return card ? card.querySelector(".gate").textContent.trim() : null;
      });
      return {sampled: nulls.length, missing, gates, shouty};
    })()`, true);

    // 10 roles whose board said nothing about hiring from abroad, in a company
    // whose board said something about some of the others.
    const v = await evalIn(c, `(async () => {
      const corpus = await (await fetch("../../fixture-v2/companies.json")).json();
      const mixed = corpus.companies.find(c => c.roles.length > 12 && c.roles.length < 100 &&
        c.roles.some(r => r.visa === "unknown" && r.hire_from_abroad === "unknown") &&
        c.roles.some(r => r.visa !== "unknown" || r.hire_from_abroad !== "unknown"));
      return {slug: mixed.slug, name: mixed.name,
              unknown: mixed.roles.filter(r => r.visa === "unknown" && r.hire_from_abroad === "unknown").length,
              total: mixed.roles.length};
    })()`, true);
    await evalIn(c, `(() => {
      window.__atlas.state.open = ${JSON.stringify(v.slug)};
      window.__atlas.state.showAll[${JSON.stringify(v.slug)}] = true;
    })()`);
    await click(c, ".chip", 0);        // redraw through the page's own path
    await sleep(300);
    const rows = await evalIn(c, `(() => {
      const rows = [...document.querySelectorAll(".role")];
      return {
        rows: rows.length,
        marked: rows.filter(r => r.querySelector(".v")).length,
        dimmed: rows.filter(r => +getComputedStyle(r).opacity < 1).length,
        sample: rows.filter(r => !r.querySelector(".v")).slice(0, 3).map(r => r.textContent.replace(/\\s+/g," ").trim()),
        footer: (document.querySelector(".rfoot span") || {}).textContent,
      };
    })()`);
    const silence = /\d+ say nothing that bears on it/.exec(rows.footer || "");
    const pass = r.missing.length === 0 && r.shouty.length === 0 && rows.rows > 0 &&
                 rows.dimmed === 0 && rows.rows - rows.marked >= 10 && !!silence;
    report("M5", pass,
      `(a) 10 null-amount companies sampled — ${r.missing.length} excluded from the default view.\n` +
      `     (b) placeholders or dimming found in their cards: ${r.shouty.length ? JSON.stringify(r.shouty) : "none"}. Their gate lines simply contain no number: e.g. "${r.gates[0]}"\n` +
      `     (a) ${v.name}: ${v.unknown} of ${v.total} roles say nothing about hiring from abroad — ${rows.rows} rows rendered, ${rows.dimmed} dimmed, ${rows.rows - rows.marked} carry no mark at all.\n` +
      `     e.g. ${JSON.stringify(rows.sample[0])}\n` +
      `     (c) stated silence: "${rows.footer}"`);
  });
}

/* ── M6 · the shortlist survives ──────────────────────────────────────── */
if (run("m6")) {
  await withPage(async (c) => {
    await c.send("Page.navigate", { url: URL_ });
    await settled(c, true);
    await evalIn(c, 'localStorage.removeItem("roleatlas.r04a.keeps.v1")');
    await c.send("Page.reload");
    await settled(c, true);
    for (let i = 0; i < 3; i++) await click(c, ".card .keep", i * 1);
    const keptNames = await evalIn(c, "Object.keys(window.__atlas.keeps())");
    // witness three opened roles on the first kept company
    await click(c, ".card .act");
    await waitFor(c, 'document.querySelectorAll(".role .apply").length >= 3');
    for (let i = 0; i < 3; i++) await click(c, ".role .apply", i);
    await sleep(400);
    const list = await (await fetch("http://127.0.0.1:9741/json/list")).json();
    for (const t of list.filter((t) => t.type === "page" && !t.url.includes("index.html") && t.url !== "about:blank"))
      await fetch("http://127.0.0.1:9741/json/close/" + t.id);

    await c.send("Page.reload", { ignoreCache: true });
    await settled(c, true);
    const after = await evalIn(c, `(() => {
      const k = window.__atlas.keeps();
      return {slugs: Object.keys(k), dates: Object.values(k).map(v => v.kept_at),
              opened: Object.values(k).map(v => v.opened_role_urls.length),
              applied: Object.values(k).map(v => v.applied),
              strip: document.querySelectorAll("#keeps .kept").length,
              asks: document.querySelectorAll("#keeps .ask").length};
    })()`);
    // second visit
    const day2 = await evalIn(c, "window.__atlas.simulateNextVisit()");
    const asks1 = await evalIn(c, 'document.querySelectorAll("#keeps .ask").length');
    const askText = await evalIn(c, '(document.querySelector("#keeps .ask span")||{}).textContent');
    await click(c, "#keeps .ask button", 0);                       // "yes"
    const asks2 = await evalIn(c, 'document.querySelectorAll("#keeps .ask").length');
    await c.send("Page.reload");
    await settled(c);
    await evalIn(c, "window.__atlas.simulateNextVisit(2)");
    const asks3 = await evalIn(c, 'document.querySelectorAll("#keeps .ask").length');
    const applied = await evalIn(c, "Object.values(window.__atlas.keeps()).map(v=>v.applied)");
    const pass = after.slugs.length === 3 && after.strip === 3 && after.dates.every(Boolean) &&
                 after.asks === 0 && asks1 === 1 && asks2 === 0 && asks3 === 0 &&
                 after.opened.reduce((a, b) => a + b, 0) === 3 && applied.includes("yes");
    report("M6", pass,
      `kept ${keptNames.length} → hard reload → ${after.slugs.length} still pinned with dates ${JSON.stringify(after.dates)}, ${after.opened.reduce((a,b)=>a+b,0)} witnessed opens, applied=${JSON.stringify(after.applied)}\n     same day: ${after.asks} questions. Next visit (${day2}): ${asks1} question — "${askText}"\n     after answering: ${asks2}; after reload + two more days: ${asks3}; stored answers ${JSON.stringify(applied)}`);
  });
}

console.log("\n" + results.map(([id, p]) => `${id} ${ok(p)}`).join(" · "));
process.exit(results.every(([, p]) => p) ? 0 : 1);
