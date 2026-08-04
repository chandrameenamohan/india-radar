// PRODUCT-1 §6, M3–M6, run against the live page.
import { launch, evalJs } from './cdp.mjs';

const URL = process.env.URL || 'http://127.0.0.1:8843/';
const out = [];
function say(s) { console.log(s); out.push(s); }

const cdp = await launch({ width: 1280, height: 900 });
await cdp.send('Page.enable');
await cdp.send('Runtime.enable');
await cdp.send('Target.setDiscoverTargets', { discover: true });

const opened = [];
const navs = [];
cdp.on('Target.targetCreated', p => {
  if (p.targetInfo.type === 'page' && p.targetInfo.url && p.targetInfo.url !== 'about:blank')
    opened.push(p.targetInfo.url);
});
cdp.on('Page.frameNavigated', p => { if (!p.frame.parentId) navs.push(p.frame.url); });

async function goto(url = URL) {
  await cdp.send('Page.navigate', { url });
  for (let i = 0; i < 200; i++) {
    const ok = await evalJs(cdp, `document.querySelectorAll('.regrow').length>=789`).catch(() => false);
    if (ok) return;
    await new Promise(r => setTimeout(r, 50));
  }
  throw new Error('page never finished loading');
}

// a real mouse click at the element's centre
let clicks = 0;
async function click(sel, nth = 0) {
  const box = await evalJs(cdp, `(()=>{const e=document.querySelectorAll(${JSON.stringify(sel)})[${nth}];
    if(!e) return null; e.scrollIntoView({block:'center'});
    const r=e.getBoundingClientRect();
    return {x:r.left+r.width/2,y:r.top+r.height/2,t:e.innerText.slice(0,60)};})()`);
  if (!box) throw new Error('no element for ' + sel + ' #' + nth);
  for (const type of ['mousePressed', 'mouseReleased'])
    await cdp.send('Input.dispatchMouseEvent', { type, x: box.x, y: box.y, button: 'left', clickCount: 1 });
  clicks++;
  await new Promise(r => setTimeout(r, 260));
  return box.t;
}

// =============================================================== M3
say('\n=== M3 · time to three apply-tabs ===');
say('script: "you are a backend engineer who wants to work in San Francisco.');
say('         get three application URLs on companies\' own job boards."');
await cdp.send('Network.enable');
await cdp.send('Network.clearBrowserCache');
await cdp.send('Network.setCacheDisabled', { cacheDisabled: true });
await cdp.send('Page.navigate', { url: 'about:blank' });
await new Promise(r => setTimeout(r, 200));
await evalJs(cdp, `1`);
opened.length = 0; navs.length = 0; clicks = 0;

const t0 = Date.now();
await cdp.send('Page.navigate', { url: URL });
// wait only for the first card — that is when a human can start acting
for (let i = 0; i < 400; i++) {
  const ok = await evalJs(cdp, `!!document.querySelector('.card')`).catch(() => false);
  if (ok) break;
  await new Promise(r => setTimeout(r, 25));
}
const tCard = Date.now() - t0;
const c1 = await click('#starts .linkish', 0);           // "engineering in San Francisco"
const openLabel = await click('.card .open', 0);          // expand the top card
await new Promise(r => setTimeout(r, 500));
const company = await evalJs(cdp, `document.querySelector('.card .cname').innerText`);
const applies = [];
for (let i = 0; i < 3; i++) { applies.push(await click('.card a.role', i)); }
const tDone = Date.now() - t0;
await new Promise(r => setTimeout(r, 600));

say(`first card painted at ${tCard}ms (unthrottled)`);
say(`clicked: "${c1}" -> "${openLabel}" -> 3 role rows at ${company}`);
// count real browser tabs, not just CDP events
const tabs = await (await fetch(`http://127.0.0.1:${cdp.port}/json/list`)).json();
const applyTabs = tabs.filter(t => t.type === 'page' && !t.url.startsWith('http://127.0.0.1:'));
say(`three apply tabs at ${tDone}ms · clicks ${clicks} · main-frame navigations ${Math.max(0, navs.length - 1)}`);
say(`tabs now open on companies' own boards: ${applyTabs.length}`);
applyTabs.forEach(t => say('   ' + t.url));
const m3pass = tDone < 60000 && clicks <= 6 && navs.length <= 1 && applyTabs.length >= 3;
say(`M3: ${m3pass ? 'PASS' : 'FAIL'}`);
for (const t of applyTabs) { try { await fetch(`http://127.0.0.1:${cdp.port}/json/close/${t.id}`); } catch (e) {} }

// =============================================================== M4
say('\n=== M4 · zero unevidenced claims ===');
const audit = `(()=>{
  const RX=/\\b(rocketship|recently|funded|new|top|best|fast[- ]growing)\\b/i;
  const bad=[];
  const nodes=[...document.querySelectorAll('*'),...document.querySelectorAll('option')];
  nodes.forEach(e=>{
    const t=e.textContent||'';
    if(!RX.test(t)) return;
    if([...e.children].some(ch=>RX.test(ch.textContent||''))) return;   // not innermost
    const scope=[e, e.parentElement].filter(Boolean);
    const link=scope.some(s=>s.tagName==='A'||s.querySelector&&s.querySelector('a'));
    const num=scope.some(s=>/\\d/.test(s.textContent||''));
    if(!link&&!num) bad.push(e.tagName+' :: '+t.trim().slice(0,110));
  });
  if(RX.test(document.title)&&!/\\d/.test(document.title)) bad.push('TITLE :: '+document.title);
  return bad;
})()`;
async function m4(label) {
  const bad = await evalJs(cdp, audit);
  say(`  ${label}: ${bad.length ? 'FAIL (' + bad.length + ')' : 'clean'}`);
  bad.slice(0, 8).forEach(b => say('      ' + b));
  return bad.length;
}
await goto();
let m4bad = 0;
m4bad += await m4('default view (732 cards, register open below)');
await evalJs(cdp, `document.querySelector('#fbtn').click()`);
m4bad += await m4('funnel open');
await evalJs(cdp, `document.querySelector('details.reg').open=true`);
m4bad += await m4('register open (789 rows)');
await evalJs(cdp, `document.getElementById('giants').checked=false;
  document.getElementById('giants').dispatchEvent(new Event('change'))`);
await new Promise(r => setTimeout(r, 700));
m4bad += await m4('giants shown (789 cards)');
await click('.card .open', 0);
await new Promise(r => setTimeout(r, 500));
m4bad += await m4('a card expanded into its roles');
say(`M4: ${m4bad === 0 ? 'PASS' : 'FAIL'}`);

// =============================================================== M5
say('\n=== M5 · absence renders as absence ===');
await goto();
const m5 = await evalJs(cdp, `(async()=>{
  const ix=await (await fetch('data/index.json')).json();
  // 10 companies with no citable amount: no SEC/TechCrunch dollar figure at all
  const nulls=ix.companies.filter(c=>!(c.g.amount)).slice(0,10);
  document.getElementById('giants').checked=false;
  document.getElementById('giants').dispatchEvent(new Event('change'));
  await new Promise(r=>setTimeout(r,400));
  const res={excluded:[],rendered_as_no:[],dimmed:[],sample:[],visaCo:null};
  // a placeholder is a text node that IS the placeholder, not prose that
  // happens to contain a dash: "—", "-", "0", "n/a", "no", "none", "unknown"
  const PLACE=/^\\s*(—|-|–|0|\\$0|n\\/a|na|no|none|unknown|not available|not disclosed)\\s*$/i;
  for(const c of nulls){
    const card=document.getElementById('c-'+c.s);
    if(!card){res.excluded.push(c.n);continue;}
    const st=getComputedStyle(card);
    const w=document.createTreeWalker(card,NodeFilter.SHOW_TEXT);
    let node,hits=[];
    while((node=w.nextNode())) if(PLACE.test(node.nodeValue)) hits.push(JSON.stringify(node.nodeValue));
    // and: nothing on the card claims a round amount for a company with none
    if(/\\braised\\b|\\bForm D\\b|\\breported a round\\b/i.test(card.innerText))
      hits.push('claims a round it has no filing for');
    if(hits.length) res.rendered_as_no.push(c.n+' :: '+hits.join(', '));
    if(+st.opacity<1||st.textDecorationLine==='line-through') res.dimmed.push(c.n);
    res.sample.push(c.n);
  }
  // pick a company that has BOTH stated and unstated visa answers, so the
  // silent rows can be compared against the ones that speak
  const mix=ix.companies.find(c=>c.vy>0 && c.r-c.vy-c.vn>3 && c.r<100);
  res.visaCo=mix?mix.s:ix.companies[0].s;
  res.visaCoName=mix?mix.n:ix.companies[0].n;
  return res;
})()`);
say(`  sampled 10 companies with no citable round: ${m5.sample.join(', ')}`);
say(`  excluded from the default view: ${m5.excluded.length ? m5.excluded.join(', ') : 'none'}`);
say(`  rendered as 0 / — / no / n/a: ${m5.rendered_as_no.length ? m5.rendered_as_no.join(' | ') : 'none'}`);
say(`  greyed out or struck through: ${m5.dimmed.length ? m5.dimmed.join(', ') : 'none'}`);

// now the visa half, on a card that has both stated and unstated answers
say(`  visa sample company: ${m5.visaCoName}`);
await evalJs(cdp, `(()=>{const c=document.getElementById('c-${m5.visaCo}');
  c.scrollIntoView({block:'center'}); c.querySelector('.open').click();})()`);
await new Promise(r => setTimeout(r, 900));
const m5b = await evalJs(cdp, `(()=>{
  const box=document.getElementById('c-${m5.visaCo}').querySelector('.roles');
  const rows=[...box.querySelectorAll('a.role')];
  const chips=rows.filter(r=>r.querySelector('.vchip'));
  return {
    note: box.querySelector('.rnote').innerText,
    rows: rows.length,
    withChip: chips.length,
    silentRowsDimmed: rows.filter(r=>+getComputedStyle(r).opacity<1).length,
    silentRowText: (rows.find(r=>!r.querySelector('.vchip'))||{innerText:''}).innerText.replace(/\\n/g,' | '),
  };
})()`);
say(`  expanded card note: "${m5b.note}"`);
say(`  ${m5b.rows} rows · ${m5b.withChip} carry a stated visa answer · ${m5b.silentRowsDimmed} rows dimmed`);
say(`  a silent role renders as: ${m5b.silentRowText}`);
const m5pass = m5.excluded.length === 0 && m5.rendered_as_no.length === 0 &&
  m5.dimmed.length === 0 && m5b.silentRowsDimmed === 0 && /silence, not a no/.test(m5b.note);
say(`M5: ${m5pass ? 'PASS' : 'FAIL'}`);

// =============================================================== M6
say('\n=== M6 · the shortlist survives ===');
await evalJs(cdp, `localStorage.clear()`);
await goto();
const kept = [];
for (let i = 0; i < 3; i++) {
  const nm = await evalJs(cdp, `document.querySelectorAll('.card .cname')[${i}].innerText`);
  await click('.card .keep', i);
  kept.push(nm);
}
say(`  kept: ${kept.join(', ')}`);
// open 3 roles at the first kept company, so there is something to ask about
await click('.card .open', 0);
await new Promise(r => setTimeout(r, 600));
for (let i = 0; i < 3; i++) await click('.card a.role', i);

await cdp.send('Page.reload', { ignoreCache: true });
await new Promise(r => setTimeout(r, 100));
await goto();
const after = await evalJs(cdp, `(()=>({
  strip: document.querySelectorAll('.slrow').length,
  text: [...document.querySelectorAll('.slrow')].map(r=>r.innerText.replace(/\\n/g,' · ')),
  asks: [...document.querySelectorAll('.ask .q')].map(q=>q.innerText),
}))()`);
say(`  after a hard reload: ${after.strip} companies pinned`);
after.text.forEach(t => say('      ' + t));
say(`  the question fired ${after.asks.length} time(s):`);
after.asks.forEach(t => say('      ' + t));
await click('.ask button', 0);   // "yes"
await new Promise(r => setTimeout(r, 300));
const afterAnswer = await evalJs(cdp, `document.querySelectorAll('.ask').length`);
await cdp.send('Page.reload', { ignoreCache: true });
await goto();
const after2 = await evalJs(cdp, `(()=>({
  asks: document.querySelectorAll('.ask').length,
  strip: document.querySelectorAll('.slrow').length,
  text: [...document.querySelectorAll('.slrow')].map(r=>r.innerText.replace(/\\n/g,' · ')),
  raw: localStorage.getItem('roleatlas.r04c.v1'),
}))()`);
say(`  after answering: ${afterAnswer} question(s) on screen; after another reload: ${after2.asks}`);
after2.text.forEach(t => say('      ' + t));
say('  stored state: ' + (after2.raw || '').slice(0, 320));
const m6pass = after.strip === 3 && after.asks.length === 1 && afterAnswer === 0 &&
  after2.asks === 0 && after2.strip === 3;
say(`M6: ${m6pass ? 'PASS' : 'FAIL'}`);

cdp.kill();
process.exit(0);
