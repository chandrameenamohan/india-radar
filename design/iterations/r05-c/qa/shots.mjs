// Viewport screenshots: the fold at 1280x900, the fold at 390px by device
// metrics (not --window-size, which clamps at 500), and the sitting with two
// companies in it.
import { launch, evalJs } from './cdp.mjs';
import { writeFileSync } from 'node:fs';

const URL = process.env.URL || 'http://127.0.0.1:8743/';
const OUT = process.env.OUT || '/tmp';

const cdp = await launch({ width: 1280, height: 900 });
await cdp.send('Page.enable');

async function ready() {
  for (let i = 0; i < 300; i++) {
    const ok = await evalJs(cdp, `document.querySelectorAll('.regrow').length>=789`).catch(() => false);
    if (ok) return;
    await new Promise(r => setTimeout(r, 50));
  }
}
async function shot(name) {
  const { data } = await cdp.send('Page.captureScreenshot', { format: 'png' });
  writeFileSync(`${OUT}/${name}.png`, Buffer.from(data, 'base64'));
  console.log(`${OUT}/${name}.png`);
}

await cdp.send('Page.navigate', { url: URL });
await ready();
await shot('r05c-fold-1280');

// two kept -> the comparison
await evalJs(cdp, `(()=>{const c=document.querySelectorAll('#cards .card');
  c[0].querySelector('.keep').click(); c[1].querySelector('.keep').click();})()`);
await new Promise(r => setTimeout(r, 300));
await evalJs(cdp, `window.scrollTo(0,0)`);
await shot('r05c-sitting-2');

// with a card expanded
await evalJs(cdp, `document.querySelectorAll('#cards .card')[1].querySelector('.open').click()`);
await new Promise(r => setTimeout(r, 800));
await evalJs(cdp, `document.querySelectorAll('#cards .card')[1].scrollIntoView({block:'start'})`);
await new Promise(r => setTimeout(r, 200));
await shot('r05c-expanded');

// the funnel sheet
await evalJs(cdp, `document.getElementById('fbtn').click()`);
await new Promise(r => setTimeout(r, 300));
await shot('r05c-sheet');
await evalJs(cdp, `document.getElementById('sheetClose').click()`);

// 390px, real device metrics
await cdp.send('Emulation.setDeviceMetricsOverride', {
  width: 390, height: 844, deviceScaleFactor: 2, mobile: true,
});
// the desktop pass already kept two companies in this profile, and .keep is a
// toggle — clicking the same cards again would un-keep them. Start clean.
await evalJs(cdp, `localStorage.clear()`);
await cdp.send('Page.navigate', { url: URL });
await ready();
await shot('r05c-fold-390');
await evalJs(cdp, `(()=>{const c=document.querySelectorAll('#cards .card');
  c[0].querySelector('.keep').click(); c[1].querySelector('.keep').click();})()`);
await new Promise(r => setTimeout(r, 300));
await evalJs(cdp, `window.scrollTo(0,0)`);
await shot('r05c-sitting-390');

// horizontal overflow check, both widths
const of390 = await evalJs(cdp, `document.documentElement.scrollWidth - window.innerWidth`);
console.log('390px horizontal overflow:', of390, 'px');
cdp.kill();
process.exit(0);
