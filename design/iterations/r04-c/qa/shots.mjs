// Screenshots of the states that matter, including a real 375px phone via CDP
// device metrics (a --window-size below 500 is clamped and gives you a cropped
// desktop, not a phone).
import { launch, evalJs } from './cdp.mjs';
import { writeFileSync } from 'node:fs';

const URL = process.env.URL || 'http://127.0.0.1:8843/';
const OUT = process.env.OUT || '/tmp/r04c';
const cdp = await launch({ width: 1280, height: 900 });
await cdp.send('Page.enable');

async function load() {
  await cdp.send('Page.navigate', { url: URL });
  for (let i = 0; i < 200; i++) {
    if (await evalJs(cdp, `document.querySelectorAll('.regrow').length>=789`).catch(() => 0)) return;
    await new Promise(r => setTimeout(r, 50));
  }
}
async function shot(name, full = false) {
  const o = { format: 'png' };
  if (full) o.captureBeyondViewport = true;
  const s = await cdp.send('Page.captureScreenshot', o);
  writeFileSync(`${OUT}-${name}.png`, Buffer.from(s.data, 'base64'));
  console.log('->', `${OUT}-${name}.png`);
}
async function metrics(w, h, mobile) {
  await cdp.send('Emulation.setDeviceMetricsOverride', {
    width: w, height: h, deviceScaleFactor: 2, mobile,
    screenWidth: w, screenHeight: h,
  });
  if (mobile) await cdp.send('Emulation.setTouchEmulationEnabled', { enabled: true });
}

await metrics(1280, 900, false);
await load();

// funnel opened
await evalJs(cdp, `document.getElementById('fbtn').click();window.scrollTo(0,0)`);
await new Promise(r => setTimeout(r, 400));
await shot('funnel');

// a card expanded, with a company kept
await load();
await evalJs(cdp, `(()=>{const c=document.querySelectorAll('.card');
  c[0].querySelector('.keep').click();})()`);
await new Promise(r => setTimeout(r, 300));
await evalJs(cdp, `(()=>{const c=document.querySelectorAll('.card')[1];
  c.querySelector('.open').click();})()`);
await new Promise(r => setTimeout(r, 900));
await evalJs(cdp, `document.querySelectorAll('.card')[1].scrollIntoView({block:'start'})`);
await new Promise(r => setTimeout(r, 300));
await shot('expanded');

// narrowed: engineering in San Francisco
await load();
await evalJs(cdp, `document.querySelector('#starts .linkish').click()`);
await new Promise(r => setTimeout(r, 500));
await shot('narrowed');

// second visit: keeps + the question
await evalJs(cdp, `(()=>{
  document.querySelectorAll('.card').forEach((c,i)=>{if(i<3)c.querySelector('.keep').click();});
})()`);
await new Promise(r => setTimeout(r, 400));
await evalJs(cdp, `document.querySelector('.card .open').click()`);
await new Promise(r => setTimeout(r, 800));
await evalJs(cdp, `[...document.querySelectorAll('.card a.role')].slice(0,3)
  .forEach(a=>{a.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true}));})`);
await new Promise(r => setTimeout(r, 300));
await load();
await evalJs(cdp, `window.scrollTo(0,0)`);
await new Promise(r => setTimeout(r, 300));
await shot('secondvisit');

// phone
await evalJs(cdp, `localStorage.clear()`);
await metrics(390, 844, true);
await load();
await new Promise(r => setTimeout(r, 400));
await shot('phone');
await evalJs(cdp, `document.querySelector('#starts .linkish').click()`);
await new Promise(r => setTimeout(r, 500));
await evalJs(cdp, `document.querySelector('.card .open').click()`);
await new Promise(r => setTimeout(r, 900));
await evalJs(cdp, `document.querySelector('.card').scrollIntoView({block:'start'})`);
await new Promise(r => setTimeout(r, 300));
await shot('phone-expanded');
const overflow = await evalJs(cdp, `({scrollW:document.documentElement.scrollWidth,
  clientW:document.documentElement.clientWidth,
  offenders:[...document.querySelectorAll('*')].filter(e=>e.getBoundingClientRect().right>
    document.documentElement.clientWidth+1).slice(0,6).map(e=>e.className+'|'+
    e.innerText.slice(0,40))})`);
console.log('horizontal overflow check:', JSON.stringify(overflow));

cdp.kill();
process.exit(0);
