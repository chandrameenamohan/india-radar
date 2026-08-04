// Does it render at all, and does anything throw?
import { launch, evalJs } from './cdp.mjs';

const URL = process.env.URL || 'http://127.0.0.1:8743/';
const cdp = await launch({ width: 1280, height: 900 });
await cdp.send('Page.enable');
await cdp.send('Runtime.enable');
const errs = [];
cdp.on('Runtime.exceptionThrown', p =>
  errs.push(p.exceptionDetails.exception?.description || p.exceptionDetails.text));
cdp.on('Runtime.consoleAPICalled', p => {
  if (p.type === 'error') errs.push(p.args.map(a => a.value || a.description).join(' '));
});

await cdp.send('Page.navigate', { url: URL });
for (let i = 0; i < 300; i++) {
  const ok = await evalJs(cdp, `document.querySelectorAll('.regrow').length>=789`).catch(() => false);
  if (ok) break;
  await new Promise(r => setTimeout(r, 50));
}
const st = await evalJs(cdp, `(()=>({
  cards: document.querySelectorAll('#cards .card').length,
  hands: document.querySelectorAll('#cards .hand').length,
  reg: document.querySelectorAll('.regrow').length,
  firstCard: document.querySelector('.card .cname')?.innerText,
  firstHand: document.querySelector('.hand .hs')?.innerText,
  lastHand: document.querySelector('.hand.last .hs')?.innerText,
  yield: document.getElementById('yield').innerText,
  starts: [...document.querySelectorAll('#starts button')].map(b=>b.innerText),
  sitting: document.getElementById('sitting').innerText.replace(/\\n/g,' | '),
  say: [...document.querySelectorAll('#cards .card')].slice(0,4).map(c=>c.innerText.replace(/\\n/g,' | ')),
  unread: [...document.querySelectorAll('#cards .card .say.unread')].length,
  plateRows: [...document.querySelectorAll('#sitting .crow .clab')].map(l=>l.innerText).filter(Boolean),
  stamp: window.__firstCardPainted,
}))()`);
console.log(JSON.stringify(st, null, 1));
console.log('\nerrors:', errs.length ? errs : 'none');
cdp.kill();
process.exit(0);
