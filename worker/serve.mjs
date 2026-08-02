// A plain Node server around the real Worker handler. Run: node worker/serve.mjs
//
// NOT the Workers runtime, and not a substitute for it — `wrangler dev` is, and
// on CI that is what `scripts/worker-e2e.sh` drives. This exists because workerd
// refuses to start below macOS 13.5 and the development machine is on 13.4, so
// without it the e2e script's own assertions could not be exercised anywhere
// except CI, and a check whose first real run is in CI is a check nobody has
// tested.
//
// It imports the same `index.mjs` the deploy bundles. What it does not reproduce
// is the Workers runtime itself — isolate lifetime, the real fetch stack, actual
// bindings. Anything depending on those must be asserted against wrangler dev.

import { createServer } from "node:http";

import worker from "./index.mjs";

const PORT = Number(process.env.PORT || 8788);
const ENV = {
  CLERK_ISSUER: process.env.CLERK_ISSUER || "https://regular-troll-50.clerk.accounts.dev",
};

createServer(async (req, res) => {
  const body = ["GET", "HEAD"].includes(req.method)
    ? undefined
    : await new Promise((resolve) => {
        const chunks = [];
        req.on("data", (c) => chunks.push(c));
        req.on("end", () => resolve(Buffer.concat(chunks)));
      });

  const request = new Request(`http://127.0.0.1:${PORT}${req.url}`, {
    method: req.method,
    headers: req.headers,
    body,
  });

  try {
    const response = await worker.fetch(request, ENV);
    res.writeHead(response.status, Object.fromEntries(response.headers));
    res.end(Buffer.from(await response.arrayBuffer()));
  } catch (error) {
    // A throw here is a bug in the handler, and it must be visible rather than
    // arriving as a hung socket the e2e script reads as a timeout.
    res.writeHead(500, { "content-type": "application/json" });
    res.end(JSON.stringify({ error: "handler threw", detail: String(error) }));
  }
}).listen(PORT, "127.0.0.1", () => {
  console.log(`worker handler on http://127.0.0.1:${PORT} (node, not workerd)`);
});
