// Does the page come up, and does anything throw?
import { launch, evalJs } from './cdp.mjs';

const URL = process.env.URL || 'http://127.0.0.1:8842/';
const cdp = await launch({ width: 1280, height: 900 });
await cdp.send('Page.enable');
await cdp.send('Runtime.enable');
await cdp.send('Log.enable');
const errs = [];
cdp.on('Runtime.exceptionThrown', p => errs.push('EXC ' + JSON.stringify(p.exceptionDetails.exception || p.exceptionDetails.text)));
cdp.on('Runtime.consoleAPICalled', p => { if (p.type === 'error') errs.push('CONSOLE ' + JSON.stringify(p.args.map(a => a.value || a.description))); });
cdp.on('Log.entryAdded', p => { if (p.entry.level === 'error') errs.push('LOG ' + p.entry.text); });

await cdp.send('Page.navigate', { url: URL });
for (let i = 0; i < 200; i++) {
  const n = await evalJs(cdp, `document.querySelectorAll('.card').length`).catch(() => 0);
  if (n > 100) break;
  await new Promise(r => setTimeout(r, 50));
}
await new Promise(r => setTimeout(r, 1200));

const state = await evalJs(cdp, `({
  cards: document.querySelectorAll('.card').length,
  reg: document.querySelectorAll('.regrow').length,
  memos: document.querySelectorAll('.memo').length,
  absent: document.querySelectorAll('.memo.absent').length,
  gates: document.querySelectorAll('.gate a').length,
  firstCard: window.__firstCardPainted,
  allLoaded: window.__allLoaded,
  h1: document.querySelector('h1').innerText,
  lede: document.querySelector('#lede2').innerText.slice(0, 400),
  yield: document.querySelector('#yield').innerText,
  residue: document.querySelector('#residue').innerText.slice(0,200),
  firstThree: [...document.querySelectorAll('.card')].slice(0,3).map(c=>c.innerText.replace(/\\n/g,' | ')),
})`);
console.log(JSON.stringify(state, null, 1));
console.log(errs.length ? '\nERRORS:\n' + errs.join('\n') : '\nno console errors');
cdp.kill();
process.exit(0);
