// M1: time to first company card, cold, cache disabled, Fast 3G.
import { launch, evalJs } from './cdp.mjs';

const URL = process.env.URL || 'http://127.0.0.1:8843/';
const RUNS = +(process.env.RUNS || 3);

// Chrome DevTools "Fast 3G" preset.
const FAST3G = { offline: false, latency: 562.5, downloadThroughput: 1.6 * 1024 * 1024 / 8, uploadThroughput: 750 * 1024 / 8 };
const SLOW4G = { offline: false, latency: 150, downloadThroughput: 4 * 1024 * 1024 / 8, uploadThroughput: 3 * 1024 * 1024 / 8 };
const NONE = { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1 };

const profiles = { fast3g: FAST3G, slow4g: SLOW4G, none: NONE };
const which = process.env.NET || 'fast3g';

const cdp = await launch({ width: 1280, height: 900 });
await cdp.send('Page.enable');
await cdp.send('Network.enable');

const times = [];
for (let i = 0; i < RUNS; i++) {
  await cdp.send('Page.navigate', { url: 'about:blank' });
  await new Promise(r => setTimeout(r, 200));
  await cdp.send('Network.clearBrowserCache');
  await cdp.send('Network.setCacheDisabled', { cacheDisabled: true });
  await cdp.send('Emulation.setCPUThrottlingRate', { rate: +(process.env.CPU || 1) });
  await cdp.send('Network.emulateNetworkConditions', profiles[which]);

  const t0 = Date.now();
  await cdp.send('Page.navigate', { url: URL });
  // poll for the first .card actually laid out with a non-zero box
  let t = null;
  for (let k = 0; k < 400; k++) {
    const ok = await evalJs(cdp, `(()=>{const c=document.querySelector('.card');
      return !!(c && c.getBoundingClientRect().height>0);})()`).catch(() => false);
    if (ok) { t = Date.now() - t0; break; }
    await new Promise(r => setTimeout(r, 25));
  }
  // also wait for the full 789 to land, for the record
  let tFull = null;
  for (let k = 0; k < 800; k++) {
    const nCards = await evalJs(cdp, `document.querySelectorAll('.regrow').length`).catch(() => 0);
    if (nCards >= 789) { tFull = Date.now() - t0; break; }
    await new Promise(r => setTimeout(r, 50));
  }
  times.push([t, tFull]);
  console.log(`run ${i + 1}: first card ${t}ms · all 789 ${tFull}ms`);
}
const firsts = times.map(t => t[0]).sort((a, b) => a - b);
console.log(`\nnet=${which} cpu=${process.env.CPU || 1}x  median first card: ${firsts[Math.floor(firsts.length / 2)]}ms`);
cdp.kill();
process.exit(0);
