// Load the page, dump what is above the fold, screenshot it.
import { launch, evalJs } from './cdp.mjs';
import { writeFileSync } from 'node:fs';

const URL = process.env.URL || 'http://127.0.0.1:8843/';
const OUT = process.env.OUT || '/tmp/r04c';

const cdp = await launch({ width: 1280, height: 900 });
await cdp.send('Page.enable');
await cdp.send('Runtime.enable');
const errs = [];
cdp.on('Runtime.exceptionThrown', p => errs.push(p.exceptionDetails.text + ' ' +
  (p.exceptionDetails.exception && p.exceptionDetails.exception.description || '')));
cdp.on('Runtime.consoleAPICalled', p => {
  if (p.type === 'error' || p.type === 'warning')
    errs.push(p.type + ': ' + p.args.map(a => a.value || a.description).join(' '));
});

await cdp.send('Page.navigate', { url: URL });
await new Promise(r => setTimeout(r, 2500));

const info = await evalJs(cdp, `(()=>{
  const cards=[...document.querySelectorAll('.card')];
  const fold=cards.filter(c=>c.getBoundingClientRect().top<900).length;
  return {
    title: document.title,
    cards: cards.length,
    foldCards: fold,
    yield: document.getElementById('yield').innerText,
    setaside: document.getElementById('setaside').innerText.slice(0,220),
    h1: document.getElementById('h1').innerText,
    lede: document.getElementById('lede').innerText,
    first3: cards.slice(0,3).map(c=>c.innerText),
    registerRows: document.querySelectorAll('.regrow').length,
    docH: document.body.scrollHeight,
  };
})()`);
console.log(JSON.stringify(info, null, 1));
console.log('console errors:', errs.length ? errs : 'none');

const shot = await cdp.send('Page.captureScreenshot', { format: 'png' });
writeFileSync(OUT + '-fold.png', Buffer.from(shot.data, 'base64'));
console.log('screenshot ->', OUT + '-fold.png');
cdp.kill();
process.exit(0);
