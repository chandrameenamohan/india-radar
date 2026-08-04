// Minimal dependency-free CDP driver. Node 22 has a global WebSocket, so this
// needs no puppeteer. Launches its own private Chrome with its own profile —
// never the shared browse daemon.
import { spawn } from 'node:child_process';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const CHROME = process.env.CHROME ||
  '/Users/ralph/.cache/puppeteer/chrome/mac_arm-146.0.7680.31/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

// A random high port, because other agents on this machine are running their
// own headless Chromes and a fixed debugging port collides with them.
const randomPort = () => 9400 + Math.floor(Math.random() * 500);

export async function launch({ port = randomPort(), width = 1280, height = 900 } = {}) {
  const profile = mkdtempSync(join(process.env.SCRATCH || tmpdir(), 'r04c-'));
  const proc = spawn(CHROME, [
    '--headless=new',
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${profile}`,
    `--window-size=${width},${height}`,
    '--no-first-run', '--no-default-browser-check', '--disable-gpu',
    '--hide-scrollbars', '--force-device-scale-factor=1',
    '--disable-extensions', '--disable-background-networking',
    'about:blank',
  ], { stdio: ['ignore', 'ignore', 'pipe'] });
  proc.stderr.on('data', () => {});

  let list = null;
  for (let i = 0; i < 100; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${port}/json/list`);
      list = await r.json();
      if (list.length) break;
    } catch (e) { /* not up yet */ }
    await new Promise(r => setTimeout(r, 100));
  }
  if (!list || !list.length) throw new Error('chrome did not come up');
  const target = list.find(t => t.type === 'page') || list[0];
  const cdp = await connect(target.webSocketDebuggerUrl);
  cdp.kill = () => { try { proc.kill('SIGKILL'); } catch (e) {} };
  cdp.port = port;
  return cdp;
}

export function connect(url) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(url);
    let id = 0;
    const pending = new Map();
    const handlers = new Map();
    ws.onmessage = (ev) => {
      const m = JSON.parse(ev.data);
      if (m.id && pending.has(m.id)) {
        const { res, rej } = pending.get(m.id);
        pending.delete(m.id);
        m.error ? rej(new Error(m.error.message + ' ' + JSON.stringify(m.error))) : res(m.result);
      } else if (m.method) {
        (handlers.get(m.method) || []).forEach(h => h(m.params));
      }
    };
    ws.onerror = (e) => reject(e);
    ws.onopen = () => resolve({
      send(method, params = {}) {
        const i = ++id;
        return new Promise((res, rej) => {
          pending.set(i, { res, rej });
          ws.send(JSON.stringify({ id: i, method, params }));
        });
      },
      on(method, fn) {
        if (!handlers.has(method)) handlers.set(method, []);
        handlers.get(method).push(fn);
      },
      close() { ws.close(); },
    });
  });
}

export async function evalJs(cdp, expr, awaitPromise = true) {
  const r = await cdp.send('Runtime.evaluate', {
    expression: expr, returnByValue: true, awaitPromise,
  });
  if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails.exception));
  return r.result.value;
}
