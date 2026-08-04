// Screenshots: the fold, a narrowed cut, an expanded card, the sheets, a phone.
// Phone shots use CDP device metrics, not --window-size: a Chrome window below
// 500px is clamped and you get a cropped desktop instead of a phone.
import { launch, evalJs } from './cdp.mjs';
import { writeFileSync, mkdirSync } from 'node:fs';

import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const PAGE = process.env.URL || 'http://127.0.0.1:8842/';
const OUT = join(dirname(fileURLToPath(import.meta.url)), '..', 'shots') + '/';
mkdirSync(OUT, { recursive: true });

const cdp = await launch({ width: 1280, height: 900 });
await cdp.send('Page.enable');

async function ready() {
  for (let i = 0; i < 300; i++) {
    const n = await evalJs(cdp, `document.querySelectorAll('.card').length`).catch(() => 0);
    if (n > 100) break;
    await new Promise(r => setTimeout(r, 50));
  }
  await new Promise(r => setTimeout(r, 700));
}
async function shot(name, full = false) {
  const r = await cdp.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: full });
  writeFileSync(OUT + name + '.png', Buffer.from(r.data, 'base64'));
  console.log('  ' + name + '.png');
}

await cdp.send('Page.navigate', { url: PAGE });
await ready();
await shot('fold');
console.log('  first card top: ' + await evalJs(cdp,
  `Math.round(document.querySelector('.card').getBoundingClientRect().top)` ) + 'px');

// the cards themselves, at reading distance
await evalJs(cdp, `document.querySelector('.card').scrollIntoView({block:'start'})`);
await new Promise(r => setTimeout(r, 250));
await shot('cards');

// the founder's gate: engineering, San Francisco, giants hidden
await evalJs(cdp, `(()=>{const f=document.getElementById('field');f.value='eng';f.onchange({target:f});
  const p=document.getElementById('place');p.value='sf';p.onchange({target:p});})()`);
await new Promise(r => setTimeout(r, 900));
await shot('gate-eng-sf');
console.log('  top ten: ' + await evalJs(cdp, `[...document.querySelectorAll('.card')].slice(0,10)
  .map(c=>c.querySelector('.cname').innerText+' '+c.querySelector('.rno').innerText).join(' · ')`));

// an expanded card
await evalJs(cdp, `document.querySelector('.card .open').click()`);
await new Promise(r => setTimeout(r, 900));
await shot('expanded');

// order by hiring intensity
await evalJs(cdp, `(()=>{const o=document.getElementById('order');o.value='size';o.onchange({target:o});})()`);
await new Promise(r => setTimeout(r, 900));
await shot('by-size');

// order by "ones I have read"
await evalJs(cdp, `(()=>{const o=document.getElementById('order');o.value='read';o.onchange({target:o});})()`);
await new Promise(r => setTimeout(r, 900));
await shot('by-read');

// the shortlist, with a record
await evalJs(cdp, `(()=>{document.getElementById('order').value='match';
  document.getElementById('order').onchange({target:document.getElementById('order')});})()`);
await new Promise(r => setTimeout(r, 700));
await evalJs(cdp, `[...document.querySelectorAll('.card .keep')].slice(0,3).forEach(b=>b.click())`);
await evalJs(cdp, `document.querySelector('.card .open').click()`);
await new Promise(r => setTimeout(r, 800));
await evalJs(cdp, `[...document.querySelectorAll('.card a.role')].slice(0,3).forEach(a=>{
  a.dispatchEvent(new MouseEvent('click',{bubbles:true}));})`);
await new Promise(r => setTimeout(r, 400));
await evalJs(cdp, `document.getElementById('deliver').scrollIntoView({block:'start'})`);
await new Promise(r => setTimeout(r, 250));
await shot('shortlist');
console.log('  copied shortlist, first 5 lines:\n' + (await evalJs(cdp,
  `(()=>{document.getElementById('copyList').click();
    return new Promise(r=>setTimeout(()=>r((window.__lastCopy||'').split('\\n').slice(0,9)
      .map(l=>'    | '+l).join('\\n')),400));})()`)));

for (const [id, name] of [['funnel', 'sheet-funnel'], ['never', 'sheet-never']]) {
  await evalJs(cdp, `document.getElementById('${id}').showModal()`);
  await new Promise(r => setTimeout(r, 300));
  await shot(name);
  await evalJs(cdp, `document.getElementById('${id}').close()`);
}

// phone
await cdp.send('Emulation.setDeviceMetricsOverride', {
  width: 390, height: 844, deviceScaleFactor: 2, mobile: true,
});
await cdp.send('Page.navigate', { url: PAGE });
await ready();
await shot('phone');
const overflow = await evalJs(cdp, `document.documentElement.scrollWidth - document.documentElement.clientWidth`);
console.log('  first card top at 390px: ' + await evalJs(cdp, `Math.round(document.querySelector('.card').getBoundingClientRect().top)`) + 'px');
console.log('  horizontal overflow at 390px: ' + overflow + 'px');
await evalJs(cdp, `[...document.querySelectorAll('.card')].find(c=>!c.querySelector('.memo.absent'))
  .scrollIntoView({block:'start'})`);
await new Promise(r => setTimeout(r, 250));
await shot('phone-card');

cdp.kill();
process.exit(0);
