// T14.3 — attacks on `resume.mjs`. Run: node --test worker/resume.test.mjs
//
// The module makes three claims and this file tries to break each of them: that
// one user cannot touch another's object, that a replacement leaves no second
// copy behind, and that a delete is verified in the same request rather than
// hoped for. Assertions are made against the FAKE STORE'S OWN CONTENTS wherever
// possible, never against what the module reported doing -- a module that
// reports its own bookkeeping back to a test proves nothing about the bucket.
//
// The fake is here rather than in `_testing.mjs` because half of it exists to
// LIE: to ignore deletes, to keep listing what it deleted, and to paginate one
// object at a time. Those are the stores that turn "deleted" into a false
// claim, and there is no way to find out whether the verification steps in
// `deleteResume` do anything without a store that misbehaves on demand.

import { strict as assert } from "node:assert";
import { test } from "node:test";

import {
  ACCEPTED_TYPES,
  MAX_RESUME_BYTES,
  checkResume,
  deleteResume,
  getResume,
  putResume,
  resumeKey,
  resumePrefix,
} from "./resume.mjs";

/**
 * NOTHING IN THIS FAKE TAKES EFFECT IN THE CALLER'S TICK, AND A WRITE LANDS
 * STRICTLY AFTER A READ ISSUED BEHIND IT.
 *
 * A bucket in memory is synchronous, and a synchronous fake would prove less
 * than these tests appear to: a `store.delete` the module forgot to `await`
 * would still have landed before the verifying read, so "the object is gone"
 * would pass over code that never waited for the deletion at all.
 *
 * Deferring every method by one macrotask is NOT enough, and the first version
 * of this file made that mistake -- timers fire in order, so the unawaited
 * delete's tick still ran before the following read's tick and all three
 * missing-`await` mutations survived. Writes therefore take two ticks and reads
 * take one: an operation whose promise was never awaited completes after the
 * read that was issued behind it, which is the only arrangement in which "you
 * did not wait for this" is observable at all. All three mutations now fail.
 *
 * What this cannot do is make the fake behave like R2. It does not have to: the
 * claim SPEC v4 makes is not "R2 is synchronous", it is that we never report a
 * deletion we did not observe. The two liars below are how that is tested --
 * `ignoreDelete` is a store where the delete has not taken effect by the time we
 * look, and `staleList` is one whose index still lists what it deleted. Both are
 * what a store WITHOUT read-after-delete consistency looks like from in here,
 * and against both `deleteResume` must refuse to claim success.
 */
const tick = () => new Promise((resolve) => setTimeout(resolve, 0));
const settle = async () => {
  await tick();
  await tick();
};

/**
 * An R2-shaped bucket in memory.
 *
 * @param ignoreDelete  accepts `delete` and keeps the object. A store that
 *                      swallows deletes silently -- a wrong binding, a bucket
 *                      with an object lock, a delete that has simply not
 *                      happened yet -- is the failure that would let us tell a
 *                      user their resume is gone while it is not.
 * @param staleList     deletes the object but keeps listing the key, which is
 *                      what an eventually-consistent index looks like from here.
 * @param pageSize      forces `list` to paginate, so the cursor loop is exercised.
 */
function fakeStore({ ignoreDelete = false, staleList = false, pageSize = 1000 } = {}) {
  const objects = new Map();
  const ghosts = new Set();
  return {
    objects, // tests read this directly; the module never sees it
    async put(key, body, options = {}) {
      await settle();
      objects.set(key, {
        key,
        body: Uint8Array.from(body),
        httpMetadata: options.httpMetadata ?? {},
        customMetadata: options.customMetadata ?? {},
      });
      ghosts.delete(key);
    },
    async get(key) {
      await tick();
      const stored = objects.get(key);
      if (!stored) return null;
      return {
        key: stored.key,
        size: stored.body.byteLength,
        httpMetadata: stored.httpMetadata,
        customMetadata: stored.customMetadata,
        bytes: stored.body,
        async text() {
          return new TextDecoder().decode(stored.body);
        },
      };
    },
    async delete(key) {
      await settle();
      if (ignoreDelete) return;
      objects.delete(key);
      if (staleList) ghosts.add(key);
    },
    async list({ prefix = "", cursor } = {}) {
      await tick();
      const all = [...new Set([...objects.keys(), ...ghosts])].filter((k) => k.startsWith(prefix)).sort();
      const start = cursor ? Number(cursor) : 0;
      const page = all.slice(start, start + pageSize);
      const end = start + page.length;
      const truncated = end < all.length;
      return {
        objects: page.map((key) => ({ key, size: objects.get(key)?.body.byteLength ?? 0 })),
        truncated,
        cursor: truncated ? String(end) : undefined,
      };
    },
  };
}

// A PDF the way a real one is shaped: the header, then the binary comment every
// generator writes on line two to stop a naive tool treating the file as text,
// then a stream with a NUL in it. An all-ASCII fixture would have made the
// "a PDF relabelled as text/plain" test below pass while proving nothing --
// such a file genuinely IS plain text, and the first draft of this file had it.
const PDF = Uint8Array.from([
  ...new TextEncoder().encode("%PDF-1.7\n%"),
  0xe2, 0xe3, 0xcf, 0xd3,
  ...new TextEncoder().encode("\n1 0 obj\n<< /Length 12 >>\nstream\nRalph"),
  0x00, 0x01,
  ...new TextEncoder().encode("Waldo\nendstream\n%%EOF\n"),
]);
const TEXT = "Ralph Waldo\nStaff Engineer\n2019-2026 Some Company\n";
const USER = "user_2abc";
const OTHER = "user_2xyz";

const keysUnder = (store, prefix) => [...store.objects.keys()].filter((k) => k.startsWith(prefix)).sort();
const upload = (store, userId = USER, body = PDF, options = {}) =>
  putResume(store, userId, body, { contentType: "application/pdf", ...options });

// --- the key is derived from the session, and from nothing else -------------

test("a hostile user id cannot reach the key at all", () => {
  // Every one of these is something a caller could pass if it read the id from
  // a header, a path segment or a JSON body instead of from `verifySession`.
  // None of them may produce a key -- not a sanitised one, not a null.
  const hostile = [
    "..",
    ".",
    "../other",
    "..\\other",
    "user_a/../user_b",
    "user_a/..",
    "%2e%2e%2fuser_b",
    "%2E%2E/user_b",
    "..%2fuser_b",
    "/etc/passwd",
    "/user_a",
    "user_a/",
    "resumes/user_b/resume",
    "user_a ",
    "user_a\u0000",
    "user_a\u0000/../user_b",
    "user_a%00.pdf",
    "user_a\n",
    "user_a\r\nx-injected: 1",
    "user_a b",
    "user_a?x=1",
    "user_a#frag",
    "user_a;",
    "usér_a",
    "user_‮",
    "user_／", // fullwidth solidus: a slash that is not a slash until something normalises it
    "",
    " ",
    "a".repeat(65),
    null,
    undefined,
    42,
    {},
    ["user_a"],
    new String("user_a"), // a non-primitive that stringifies to something perfectly valid
  ];
  for (const id of hostile) {
    assert.throws(() => resumeKey(id), TypeError, `derived a key from: ${JSON.stringify(id)}`);
    assert.throws(() => resumePrefix(id), TypeError, `derived a prefix from: ${JSON.stringify(id)}`);
  }
});

test("a genuine Clerk id yields a stable, scoped key", () => {
  assert.equal(resumeKey(USER), "resumes/user_2abc/resume");
  assert.equal(resumePrefix(USER), "resumes/user_2abc/");
  assert.equal(resumeKey(USER), resumeKey(USER));
  // No extension: replacing a PDF with a text file must not write a second key.
  assert.ok(!resumeKey(USER).includes("."));
});

test("every entry point refuses a hostile id, not just the key function", async () => {
  const store = fakeStore();
  await assert.rejects(() => upload(store, "../user_2xyz"), TypeError);
  await assert.rejects(() => getResume(store, "../user_2xyz"), TypeError);
  await assert.rejects(() => deleteResume(store, "../user_2xyz"), TypeError);
  assert.equal(store.objects.size, 0);
});

test("the filename is stored but never reaches the key", async () => {
  const store = fakeStore();
  const result = await upload(store, USER, PDF, { filename: "../../../etc/passwd.pdf" });
  assert.equal(result.key, "resumes/user_2abc/resume");
  assert.deepEqual(keysUnder(store, "resumes/"), ["resumes/user_2abc/resume"]);
  assert.equal(store.objects.get(result.key).customMetadata.filename, "passwd.pdf");
});

test("a filename carrying a header injection is cleaned before storage", async () => {
  const store = fakeStore();
  await upload(store, USER, PDF, { filename: "cv\r\nX-Injected: yes.pdf" });
  const stored = store.objects.get(resumeKey(USER)).customMetadata.filename;
  assert.ok(!/[\r\n]/.test(stored), `stored a newline: ${JSON.stringify(stored)}`);
  assert.equal(stored, "cvX-Injected: yes.pdf");
});

// --- one user is not another user ------------------------------------------

test("one user cannot read or delete another user's resume", async () => {
  const store = fakeStore();
  await upload(store, USER);
  assert.equal(await getResume(store, OTHER), null);

  assert.deepEqual(await deleteResume(store, OTHER), { deleted: 0, verified: true });
  assert.equal(store.objects.size, 1, "deleting for another user removed the victim's object");
  assert.ok(await getResume(store, USER));
});

test("a user id that is a prefix of another user's id stays out of their bucket", async () => {
  // `user_a` and `user_ab`. Without the trailing slash in `resumePrefix`, the
  // sweep for the first would list and delete the second's object -- a data
  // loss AND a cross-user read, from a missing character.
  const store = fakeStore();
  await upload(store, "user_a");
  await upload(store, "user_ab");

  assert.deepEqual(await deleteResume(store, "user_a"), { deleted: 1, verified: true });
  assert.equal(await getResume(store, "user_a"), null);
  assert.ok(await getResume(store, "user_ab"), "deleting user_a took user_ab's resume with it");
});

// --- what may be stored -----------------------------------------------------

test("PDF and plain text are accepted and nothing else is", async () => {
  assert.deepEqual([...ACCEPTED_TYPES].sort(), ["application/pdf", "text/plain"]);

  assert.equal(checkResume(PDF, "application/pdf").ok, true);
  assert.equal(checkResume(TEXT, "text/plain").ok, true);
  assert.equal(checkResume(TEXT, "text/plain; charset=utf-8").ok, true);
  assert.equal(checkResume(TEXT, "TEXT/PLAIN").ok, true);

  for (const type of [
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/octet-stream",
    "image/png",
    "text/html",
    "application/pdf-x",
    "",
    undefined,
    null,
  ]) {
    assert.equal(checkResume(PDF, type).reason, "unsupported_type", `accepted type: ${type}`);
  }
});

test("a file declared as PDF has to actually be one", () => {
  // Otherwise the format allowlist is a label the caller writes for themselves,
  // and `application/pdf` means "whatever the uploader said it was".
  assert.equal(checkResume(new TextEncoder().encode("MZ\u0000"), "application/pdf").reason, "not_a_pdf");
  assert.equal(checkResume("<html>not a pdf</html>", "application/pdf").reason, "not_a_pdf");
  assert.equal(checkResume(new TextEncoder().encode("%PDF"), "application/pdf").reason, "not_a_pdf");
  assert.equal(checkResume(new TextEncoder().encode("\n%PDF-1.7"), "application/pdf").reason, "not_a_pdf");
});

test("plain text has to be text", () => {
  // Two different guards, and they need separate cases. MUTATION TESTING found
  // this: the invalid-UTF-8 fixture here was `[0xff, 0xfe, 0x00, 0x41]`, whose
  // NUL meant the control-character check refused it first, so removing
  // `{ fatal: true }` from the decoder left the whole suite green. The first
  // case below is now invalid UTF-8 -- a lone continuation byte -- and contains
  // nothing else wrong with it, so it fails if and only if the decode is strict.
  assert.equal(checkResume(Uint8Array.from([0x52, 0x61, 0x6c, 0x70, 0xbf]), "text/plain").reason, "not_text");
  assert.equal(checkResume(Uint8Array.from([0x41, 0x00, 0x42]), "text/plain").reason, "not_text");
  assert.equal(checkResume(PDF, "text/plain").reason, "not_text", "a PDF relabelled as text was stored as text");

  // ...and a page break survives, because that is what pasting out of a PDF
  // produces and refusing it would refuse a real resume.
  assert.equal(checkResume("page one\fpage two", "text/plain").ok, true);
  assert.equal(checkResume("tabs\tand\r\nnewlines\n", "text/plain").ok, true);
  assert.equal(checkResume("Ralph — Staff Engineer, München 🙂", "text/plain").ok, true);
});

test("an empty upload is refused rather than stored as a resume", () => {
  // It would report success and then be unretrievable-in-spirit: the user
  // believes they have a resume and every application attaches nothing.
  assert.equal(checkResume(new Uint8Array(0), "application/pdf").reason, "empty");
  assert.equal(checkResume("", "text/plain").reason, "empty");
});

test("the size cap is enforced on the bytes, not on a number the caller supplied", () => {
  const atCap = new Uint8Array(MAX_RESUME_BYTES);
  atCap.set(PDF.slice(0, 5));
  assert.equal(checkResume(atCap, "application/pdf").ok, true);

  const overCap = new Uint8Array(MAX_RESUME_BYTES + 1);
  overCap.set(PDF.slice(0, 5));
  assert.equal(checkResume(overCap, "application/pdf").reason, "too_large");

  // A string is measured in UTF-8 BYTES, not UTF-16 code units. This one is
  // half the cap by `.length` and over it once encoded, which is how a naive
  // length check lets a 2 MiB file through the 2 MiB cap.
  const emoji = "\u{1f600}".repeat(Math.ceil(MAX_RESUME_BYTES / 4) + 1);
  assert.ok(emoji.length < MAX_RESUME_BYTES, "the test string is not actually testing the encoding");
  assert.equal(checkResume(emoji, "text/plain").reason, "too_large");
});

test("an ArrayBuffer body is accepted and stored byte for byte", async () => {
  // This is not a defensive branch, it is THE branch: `await request.arrayBuffer()`
  // in the Workers runtime hands back a bare ArrayBuffer, not a view, and a
  // bare ArrayBuffer fails `ArrayBuffer.isView`. Without this conversion every
  // real upload would be refused as unreadable while every test passed on the
  // Uint8Array the tests happened to build. A branch mutation found it unexercised.
  const buffer = PDF.buffer.slice(PDF.byteOffset, PDF.byteOffset + PDF.byteLength);
  assert.ok(buffer instanceof ArrayBuffer && !ArrayBuffer.isView(buffer));

  const checked = checkResume(buffer, "application/pdf");
  assert.equal(checked.ok, true);
  assert.equal(checked.bytes.byteLength, PDF.byteLength);

  const store = fakeStore();
  const result = await putResume(store, USER, buffer, { contentType: "application/pdf" });
  assert.equal(result.size, PDF.byteLength);
  assert.deepEqual((await getResume(store, USER)).bytes, PDF);
});

test("a typed-array view onto a larger buffer stores only its own bytes", async () => {
  // `subarray` shares the buffer with its parent. Converting a view by handing
  // `body.buffer` to the store without the offset and length would store the
  // WHOLE buffer -- here, another user's bytes sitting next to it in memory.
  const backing = new Uint8Array([...PDF, ...new TextEncoder().encode("SOMEONE ELSE'S BYTES")]);
  const view = backing.subarray(0, PDF.byteLength);

  const store = fakeStore();
  await putResume(store, USER, view, { contentType: "application/pdf" });
  const stored = (await getResume(store, USER)).bytes;
  assert.equal(stored.byteLength, PDF.byteLength);
  assert.ok(!new TextDecoder().decode(stored).includes("SOMEONE ELSE"));
});

test("a body whose length cannot be measured is refused rather than streamed past the cap", () => {
  // A cap enforced after the object is already in the bucket is not a cap. So a
  // stream is refused here instead of trusting a declared length.
  const stream = new ReadableStream({ start: (c) => c.close() });
  assert.equal(checkResume(stream, "application/pdf").reason, "unreadable_body");
  assert.equal(checkResume({ length: 10 }, "application/pdf").reason, "unreadable_body");
  assert.equal(checkResume(null, "application/pdf").reason, "unreadable_body");
  assert.equal(checkResume(12345, "text/plain").reason, "unreadable_body");
});

test("a refused upload writes nothing", async () => {
  const store = fakeStore();
  const result = await putResume(store, USER, PDF, { contentType: "application/msword" });
  assert.equal(result.ok, false);
  assert.equal(store.objects.size, 0);
});

// --- one resume, no history -------------------------------------------------

test("a second upload replaces the first, and the store holds exactly one object", async () => {
  const store = fakeStore();
  const first = await upload(store, USER);
  assert.equal(first.replaced, false);

  const second = await putResume(store, USER, TEXT, { contentType: "text/plain" });
  assert.equal(second.replaced, true);

  // Asserted against the store, not against what putResume said it did.
  assert.deepEqual(keysUnder(store, resumePrefix(USER)), [resumeKey(USER)]);
  assert.equal(await (await getResume(store, USER)).text(), TEXT);
  assert.equal(store.objects.get(resumeKey(USER)).httpMetadata.contentType, "text/plain");
});

test("the previous resume is unretrievable, including by the key it used to have", async () => {
  const store = fakeStore();
  await upload(store, USER);
  const before = store.objects.get(resumeKey(USER)).body;

  await putResume(store, USER, TEXT, { contentType: "text/plain" });
  for (const stored of store.objects.values()) {
    assert.notDeepEqual(stored.body, before, `the old resume is still in the bucket at ${stored.key}`);
  }
});

test("an object left under the user's prefix by an older key scheme is swept on upload", async () => {
  // The invariant is "one object per user", enforced against the store. A fixed
  // key gives that for free only while the derivation never changes; this is
  // what makes it true across a change to it.
  const store = fakeStore();
  await store.put(`${resumePrefix(USER)}resume.pdf`, PDF);
  await store.put(`${resumePrefix(USER)}2026-01-01-resume.pdf`, PDF);

  await upload(store, USER);
  assert.deepEqual(keysUnder(store, resumePrefix(USER)), [resumeKey(USER)]);
});

test("a store that keeps a second copy after a replace is not reported as a success", async () => {
  const store = fakeStore({ ignoreDelete: true });
  await store.put(`${resumePrefix(USER)}resume.pdf`, PDF);
  await assert.rejects(() => upload(store, USER), /more than one resume/);
});

// --- deletion you can verify ------------------------------------------------

test("a read issued after the delete returns nothing, in the same call", async () => {
  const store = fakeStore();
  await upload(store, USER);

  assert.deepEqual(await deleteResume(store, USER), { deleted: 1, verified: true });
  assert.equal(await getResume(store, USER), null);
  assert.equal(store.objects.size, 0);
});

test("deleting a user who never uploaded is a success, not a failure", async () => {
  // Account deletion runs this for every user and most never uploaded. If this
  // threw, "no resume" would become a failed account deletion.
  const store = fakeStore();
  assert.deepEqual(await deleteResume(store, USER), { deleted: 0, verified: true });
});

test("a store that ignores the delete cannot make us claim the resume is gone", async () => {
  const store = fakeStore({ ignoreDelete: true });
  await upload(store, USER);
  await assert.rejects(() => deleteResume(store, USER), /still readable after delete/);
  assert.equal(store.objects.size, 1, "the fake was supposed to keep the object");
});

test("a store whose listing still shows the object after the delete is not trusted either", async () => {
  // `get` says gone, `list` says present. One of them is wrong and we do not
  // know which, so this is not a deletion anyone may claim.
  const store = fakeStore({ staleList: true });
  await upload(store, USER);
  await assert.rejects(() => deleteResume(store, USER), /objects remain under the user's prefix/);
});

test("deletion sweeps every object for the user, across pages of the listing", async () => {
  // A sweep that stops at the first page deletes some of a user's data and
  // reports that it deleted all of it -- the exact false claim this task exists
  // to prevent.
  const store = fakeStore({ pageSize: 1 });
  await upload(store, USER);
  await store.put(`${resumePrefix(USER)}resume.pdf`, PDF);
  await store.put(`${resumePrefix(USER)}old.txt`, PDF);
  await upload(store, OTHER);

  assert.deepEqual(await deleteResume(store, USER), { deleted: 3, verified: true });
  assert.deepEqual(keysUnder(store, "resumes/"), [resumeKey(OTHER)]);
});

// --- the round trip ---------------------------------------------------------

test("what was uploaded is what comes back, on a later request with no shared state", async () => {
  // The acceptance criterion is "retrievable on a later visit from a different
  // browser", which in this module means: nothing but the store carries it.
  const store = fakeStore();
  const result = await upload(store, USER, PDF, { filename: "ralph.pdf", now: 1_800_000_000_000 });
  assert.equal(result.size, PDF.byteLength);
  assert.equal(result.contentType, "application/pdf");

  const object = await getResume(store, USER);
  assert.deepEqual(object.bytes, PDF);
  assert.equal(object.httpMetadata.contentType, "application/pdf");
  assert.equal(object.customMetadata.filename, "ralph.pdf");
  assert.equal(object.customMetadata.uploadedAt, "2027-01-15T08:00:00.000Z");
});

test("the stored bytes are the bytes that were checked", async () => {
  // No window between "this passed the cap and the format check" and "this was
  // written", which is why `checkResume` hands back bytes rather than a size.
  const store = fakeStore();
  await upload(store, USER);
  assert.deepEqual(store.objects.get(resumeKey(USER)).body, PDF);
});
