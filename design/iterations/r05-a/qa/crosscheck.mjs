// Two renderers write this page's cards: build.py inlines the first screenful
// as HTML so the fold costs no JavaScript, and page.html's makeCard() writes
// every card after that. Two renderers is two places a sentence can drift, so
// this asserts they do not: the Python-rendered card and the JS-rendered card
// for the same company must carry the same text, word for word.
//
// It is round 4's graft 10 — a's Python/JS cross-check invariant — made into a
// step you can run.
import { launch, evalJs } from './cdp.mjs';

const URL = process.env.URL || 'http://127.0.0.1:8841/';
const cdp = await launch({ width: 1280, height: 900 });
await cdp.send('Page.enable');
await cdp.send('Page.navigate', { url: URL });
for (let i = 0; i < 400; i++) {
  if (await evalJs(cdp, `document.querySelectorAll('.regrow').length>=789`).catch(() => 0)) break;
  await new Promise(r => setTimeout(r, 50));
}

// By now render() has replaced the inlined fold with JS-built cards, so the
// Python halves are re-fetched from the document as it was served.
const res = await evalJs(cdp, `(async()=>{
  const raw = await (await fetch(location.pathname, {cache:'reload'})).text();
  const box = document.createElement('div');
  box.innerHTML = raw.slice(raw.indexOf('<div class="cards"'), raw.indexOf('<footer'));
  const norm = e => (e.textContent||'').replace(/\\s+/g,' ').trim();
  const out = {checked:0, missing:[], diff:[]};
  for (const py of box.querySelectorAll('.card')) {
    const js = document.getElementById(py.id);
    if (!js) { out.missing.push(py.id); continue; }
    out.checked++;
    const a = norm(py), b = norm(js);
    if (a !== b) {
      let i = 0; while (i < a.length && a[i] === b[i]) i++;
      const at = Math.max(0, i - 40);
      out.diff.push(py.id + ' @' + i + ' :: py=' + JSON.stringify(a.slice(at, i + 90)) +
                    ' js=' + JSON.stringify(b.slice(at, i + 90)));
    }
  }
  return out;
})()`);

console.log(`cards cross-checked: ${res.checked}`);
console.log(`present in the JS render but not the Python one: ${res.missing.length}`);
res.missing.forEach(m => console.log('   ' + m));
console.log(`text mismatches: ${res.diff.length}`);
res.diff.slice(0, 6).forEach(d => console.log('   ' + d));
const pass = res.checked > 0 && res.missing.length === 0 && res.diff.length === 0;
console.log(`CROSS-CHECK: ${pass ? 'PASS' : 'FAIL'}`);
cdp.kill();
process.exit(pass ? 0 : 1);
