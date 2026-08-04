// The Python/JS invariant, pointed at markup. Six cards arrive as HTML in
// index.html and 783 arrive as JSON and are rendered by app.js; if the two
// renderers ever disagree, the fold is a different page from the scroll.
//
//   node qa/crosscheck.mjs        # needs the page served (URL=...)
import { execFileSync } from 'node:child_process';
import { launch, evalJs } from './cdp.mjs';

const URL = process.env.URL || 'http://127.0.0.1:8842/';
const PY = process.env.PY || '/Users/ralph/sennamind/next-rocket-ship/.venv/bin/python';

const py = JSON.parse(execFileSync(PY, ['build.py', '--cards'],
  { cwd: new globalThis.URL('..', import.meta.url).pathname, maxBuffer: 1 << 28 }));
const slugs = Object.keys(py);
console.log(`python rendered ${slugs.length} cards`);

const cdp = await launch({ width: 1280, height: 900 });
await cdp.send('Page.enable');
await cdp.send('Runtime.enable');
await cdp.send('Page.navigate', { url: URL });
for (let i = 0; i < 400; i++) {
  if (await evalJs(cdp, 'window.__allLoaded || 0').catch(() => 0)) break;
  await new Promise(r => setTimeout(r, 50));
}

// The JS renderer, driven over the same index in the same order.
await cdp.send('Runtime.evaluate', {
  expression: `window.__js = {}; window.__order = [];
    fetch('data/index.json').then(r=>r.json()).then(ix => {
      ix.companies.forEach((c,i) => { window.__js[c.s] = window.__cardHTML(c,'any',i+1);
                                      window.__order.push(c.s); });
      window.__jsDone = true; });`,
  awaitPromise: false,
});
for (let i = 0; i < 400; i++) {
  if (await evalJs(cdp, 'window.__jsDone || false')) break;
  await new Promise(r => setTimeout(r, 50));
}

const jsOrder = await evalJs(cdp, 'window.__order');
let mismatch = 0;
const shown = [];
for (let i = 0; i < jsOrder.length; i++) {
  const slug = jsOrder[i];
  const got = await evalJs(cdp, `window.__js[${JSON.stringify(slug)}]`);
  if (got !== py[slug]) {
    mismatch++;
    if (shown.length < 3) { let d = 0; while (d < got.length && got[d] === py[slug][d]) d++;
      shown.push({ slug, py: py[slug].slice(d - 60, d + 90), js: got.slice(d - 60, d + 90) }); }
  }
}
console.log(`js rendered   ${jsOrder.length} cards`);
console.log(`MISMATCHES    ${mismatch}`);
for (const m of shown) {
  console.log('\n' + m.slug + '\n  PY ' + m.py.slice(0, 400) + '\n  JS ' + m.js.slice(0, 400));
}
cdp.kill();
process.exit(mismatch ? 1 : 0);
