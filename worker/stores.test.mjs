// The SQL, against real SQLite. Run: node --test worker/stores.test.mjs
//
// Every other suite here injects a fake, which is what let the modules be built
// with no infrastructure -- but a fake reimplements the query rather than running
// it, so the one thing none of them can catch is the SQL being wrong. The
// free-tier counters are arithmetic expressed entirely in SQL: two aggregates
// with deliberately different scopes, and an upsert that has to add within a
// month and reset outside one. A typo in either is a wrong bill, not a red test.
//
// D1 is SQLite, and Node ships one. So `schema.sql` is applied verbatim here and
// the queries run for real. This does NOT make it a D1 test -- it says nothing
// about bindings, replication or D1's own limits -- it says the statements mean
// what the comments above them claim.

import { strict as assert } from "node:assert";
import { readFileSync } from "node:fs";
import { DatabaseSync } from "node:sqlite";
import { test } from "node:test";

import { usageMonth, usageStore } from "./stores.mjs";

/** The D1 surface `stores.mjs` uses, over a real in-memory SQLite. */
function d1(schemaPath = new URL("./schema.sql", import.meta.url)) {
  const db = new DatabaseSync(":memory:");
  db.exec(readFileSync(schemaPath, "utf8"));
  return {
    prepare(sql) {
      const statement = db.prepare(sql);
      let args = [];
      const api = {
        bind: (...a) => ((args = a), api),
        first: async () => statement.get(...args) ?? null,
        run: async () => statement.run(...args),
      };
      return api;
    },
  };
}

const MONTH = "2026-08";

test("schema.sql is applied verbatim and creates both tables", () => {
  // It has never been executed by a test before, so a syntax error in it was
  // discoverable only by deploying. This is that check, and it costs one line.
  const db = new DatabaseSync(":memory:");
  db.exec(readFileSync(new URL("./schema.sql", import.meta.url), "utf8"));
  const names = db
    .prepare("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")
    .all()
    .map((row) => row.name);
  assert.deepEqual(names, ["profiles", "resume_usage"]);
});

test("the month key is a month", async () => {
  // Not decoration: slice one character short and the key is a YEAR, the Class A
  // counter resets in January instead of monthly, and eleven months of the free
  // tier are spent before anything refuses. Nothing else notices, because every
  // other test asks for the same key it recorded under.
  assert.equal(usageMonth(Date.UTC(2026, 7, 3, 12)), "2026-08");
  assert.equal(usageMonth(Date.UTC(2026, 11, 31, 23, 59)), "2026-12");
});

test("a driver that answers an aggregate with no row at all still totals zero", async () => {
  // `SUM` over an empty table is NULL, which `Number` makes 0 -- so the empty
  // table is not the interesting case. This is: a `first()` that returns null
  // leaves `undefined`, `Number(undefined)` is NaN, and every free-tier
  // comparison is a `>`, which NaN fails. The limits would all silently pass.
  const usage = usageStore({ prepare: () => ({ bind: () => ({ first: async () => null }) }) });
  assert.deepEqual(await usage.load("user_a", MONTH), { otherBytes: 0, ops: 0 });
});

test("an empty table totals zero rather than null", async () => {
  // The state on the day this ships: nobody has uploaded anything, and the first
  // reader's upload must be compared against 0 and not against NULL.
  const usage = usageStore(d1());
  assert.deepEqual(await usage.load("user_a", MONTH), { otherBytes: 0, ops: 0 });
});

test("bytes exclude the caller and operations include everyone", async () => {
  // The two scopes are the whole design and they are opposite: a replacement
  // displaces the caller's own bytes, so counting them would refuse an upload
  // that frees as much as it takes -- while ops that excluded the caller would
  // let one account in a loop spend the month without ever seeing the bill.
  const usage = usageStore(d1());
  await usage.record("user_a", 100, 4, MONTH);
  await usage.record("user_b", 250, 7, MONTH);

  assert.deepEqual(await usage.load("user_a", MONTH), { otherBytes: 250, ops: 11 });
  assert.deepEqual(await usage.load("user_b", MONTH), { otherBytes: 100, ops: 11 });
  assert.deepEqual(await usage.load("user_nobody", MONTH), { otherBytes: 350, ops: 11 });
});

test("operations add within a month and start over outside one", async () => {
  // The monthly reset with no scheduled job: a row whose month is not the one
  // being asked about contributes nothing, and the next write in a new month
  // replaces the count rather than continuing it.
  const usage = usageStore(d1());
  await usage.record("user_a", 100, 4, "2026-07");
  await usage.record("user_a", 100, 4, "2026-07");
  assert.equal((await usage.load("user_x", "2026-07")).ops, 8);
  assert.equal((await usage.load("user_x", MONTH)).ops, 0, "last month is still being counted");

  await usage.record("user_a", 100, 4, MONTH);
  assert.equal((await usage.load("user_x", MONTH)).ops, 4);
  assert.equal((await usage.load("user_x", "2026-07")).ops, 0, "the row kept a stale month");
});

test("a replacement overwrites the size and a deletion returns it to the pool", async () => {
  const usage = usageStore(d1());
  await usage.record("user_a", 1000, 4, MONTH);
  await usage.record("user_a", 300, 4, MONTH);
  assert.equal((await usage.load("user_x", MONTH)).otherBytes, 300, "sizes accumulated");

  await usage.record("user_a", 0, 4, MONTH);
  assert.deepEqual(await usage.load("user_x", MONTH), { otherBytes: 0, ops: 12 });
});
