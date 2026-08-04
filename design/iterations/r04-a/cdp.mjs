// A dependency-free CDP client (Node 22 ships a global WebSocket) used to run
// PRODUCT-1 §6's six measures against the page as it actually runs. Nothing in
// here is loaded by index.html; it is the harness, not the product.
//
//   node cdp.mjs <m1|m2|m3|m4|m5|m6|all> [--port 9741] [--url ...]
const args = process.argv.slice(2);
const flag = (k, d) => { const i = args.indexOf(k); return i > -1 ? args[i + 1] : d; };
const PORT = flag("--port", "9741");
const URL_ = flag("--url", "http://127.0.0.1:8741/design/iterations/r04-a/index.html");
const OUT = flag("--out", "/tmp/r04a");

async function newTab() {
  const r = await fetch(`http://127.0.0.1:${PORT}/json/new?about:blank`, { method: "PUT" });
  return r.json();
}
async function closeTab(id) {
  await fetch(`http://127.0.0.1:${PORT}/json/close/${id}`);
}

class CDP {
  constructor(ws) { this.ws = ws; this.id = 0; this.pending = new Map(); this.handlers = []; }
  static async open(url) {
    const ws = new WebSocket(url);
    const c = new CDP(ws);
    await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
    ws.onmessage = (e) => {
      const m = JSON.parse(e.data);
      if (m.id && c.pending.has(m.id)) {
        const { res, rej } = c.pending.get(m.id); c.pending.delete(m.id);
        m.error ? rej(new Error(JSON.stringify(m.error))) : res(m.result);
      } else if (m.method) c.handlers.forEach((h) => h(m));
    };
    return c;
  }
  send(method, params = {}, sessionId) {
    const id = ++this.id;
    return new Promise((res, rej) => {
      this.pending.set(id, { res, rej });
      this.ws.send(JSON.stringify({ id, method, params, sessionId }));
    });
  }
  on(fn) { this.handlers.push(fn); }
  close() { this.ws.close(); }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export async function withPage(fn, { throttle = false, width = 1280, height = 900 } = {}) {
  const tab = await newTab();
  const c = await CDP.open(tab.webSocketDebuggerUrl);
  await c.send("Page.enable");
  await c.send("Runtime.enable");
  await c.send("Network.enable");
  await c.send("Network.setCacheDisabled", { cacheDisabled: true });
  await c.send("Emulation.setDeviceMetricsOverride", {
    width, height, deviceScaleFactor: 1, mobile: false,
  });
  if (throttle) {
    // Chrome DevTools "Fast 3G": 1.6 Mbit/s down, 750 kbit/s up, 150ms RTT.
    await c.send("Network.emulateNetworkConditions", {
      offline: false, latency: 150,
      downloadThroughput: (1.6 * 1024 * 1024) / 8,
      uploadThroughput: (750 * 1024) / 8,
    });
  }
  try { return await fn(c); } finally { c.close(); await closeTab(tab.id); }
}

export async function evalIn(c, expr, awaitPromise = false) {
  const r = await c.send("Runtime.evaluate", {
    expression: expr, returnByValue: true, awaitPromise,
  });
  if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
  return r.result.value;
}

export async function waitFor(c, expr, timeout = 20000, every = 25) {
  const t0 = Date.now();
  for (;;) {
    if (await evalIn(c, `!!(${expr})`)) return Date.now() - t0;
    if (Date.now() - t0 > timeout) throw new Error("timeout waiting for " + expr);
    await sleep(every);
  }
}

export async function shot(c, path) {
  const r = await c.send("Page.captureScreenshot", { format: "png" });
  const fs = await import("node:fs/promises");
  await fs.mkdir(OUT, { recursive: true });
  await fs.writeFile(`${OUT}/${path}`, Buffer.from(r.data, "base64"));
  return `${OUT}/${path}`;
}

export { CDP, URL_, OUT, sleep };
