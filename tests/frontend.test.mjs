import { test } from "node:test";
import assert from "node:assert/strict";
import { starterTasks } from "../src/readiness.ts";
import { api, ApiError, money, quantity, submitEntry } from "../src/api.ts";

const owner = { id: "owner", role: "owner", stores: ["sausage", "health"] };
const source = (patch = {}) => ({
  id: "source-1",
  store: "sausage",
  category: "sales",
  status: "needs_review",
  author_id: "owner",
  ...patch,
});

test("one store or a shared report never fills the other store's first sales slot", () => {
  const tasks = starterTasks(
    [source(), source({ store: "both", status: "reviewed" })],
    owner,
    "both",
  );
  assert.equal(
    tasks.find((t) => t.store === "sausage" && t.category === "sales").state,
    "submitted",
  );
  assert.equal(
    tasks.find((t) => t.store === "health" && t.category === "sales").state,
    "missing",
  );
});

test("reviewed sources do not imply the other categories are complete", () => {
  const tasks = starterTasks(
    [source({ status: "reviewed" })],
    owner,
    "sausage",
  );
  assert.equal(tasks[0].state, "reviewed");
  assert.equal(tasks.filter((t) => t.state === "missing").length, 3);
  assert.ok(tasks.every((t) => t.store === "sausage"));
});

test("staff suggestions consider only their own accessible submissions", () => {
  const staff = { id: "staff", role: "staff", stores: ["health"] };
  const tasks = starterTasks(
    [
      source({ store: "health", status: "reviewed" }),
      source({ author_id: "staff" }),
    ],
    staff,
    "both",
  );
  assert.ok(tasks.every((t) => t.store === "health" && t.state === "missing"));
  const own = starterTasks(
    [source({ author_id: "staff", store: "health" })],
    staff,
    "health",
  );
  assert.equal(own[0].state, "submitted");
});

test("transport failure has unknown outcome, not a claim that a write failed", async (t) => {
  t.mock.method(globalThis, "fetch", async () => {
    throw new TypeError("Failed to fetch");
  });
  await assert.rejects(
    api("/entries", { method: "POST" }),
    (error) =>
      error instanceof ApiError &&
      error.status === undefined &&
      error.message.includes("could not confirm"),
  );
});

test("expired sessions preserve a structured 401 for draft reauthentication", async (t) => {
  t.mock.method(
    globalThis,
    "fetch",
    async () =>
      new Response(JSON.stringify({ detail: "Sign in to continue." }), {
        status: 401,
      }),
  );
  await assert.rejects(
    api("/entries"),
    (error) => error instanceof ApiError && error.status === 401,
  );
});

test("a truncated success response is also an unknown write outcome", async (t) => {
  t.mock.method(
    globalThis,
    "fetch",
    async () => new Response('{"id":', { status: 201 }),
  );
  await assert.rejects(
    api("/entries", { method: "POST" }),
    (error) => error instanceof ApiError && error.status === undefined,
  );
});

test("an existing private upload still uploads remaining files and requires final verification", async (t) => {
  const form = new FormData();
  for (const [key, value] of Object.entries({store:'both',category:'other',title:'Test',notes:'Synthetic',
    occurred_on:'2026-09-09',request_key:'test-key-1111111111'})) form.append(key, value);
  form.append('files', new File(['first original'], 'first.txt'));
  form.append('files', new File(['second original'], 'second.txt'));
  let uploads = 0;
  let finalized = false;
  t.mock.method(globalThis, 'fetch', async (url, init) => {
    if (url === '/api/system') return Response.json({ upload_mode: 'direct' });
    if (url === '/api/upload-intents') {
      const manifest = JSON.parse(init.body);
      assert.equal(manifest.request_key, 'test-key-1111111111');
      assert.equal(manifest.files.length, 2);
      assert.match(manifest.files[0].sha256, /^[a-f0-9]{64}$/);
      return Response.json({ id: 'intent', files: [{ grant: 'one' }, { grant: 'two' }] });
    }
    if (url === '/api/storage') return Response.json({ url: 'https://storage.example/upload' });
    if (url === 'https://storage.example/upload') {
      assert.equal(init.credentials, 'omit');
      uploads++;
      return uploads === 1 ? Response.json({ error: { code: 'bad_request' } }, { status: 400 }) : Response.json({});
    }
    assert.equal(url, '/api/upload-intents/intent/finalize');
    assert.equal(uploads, 2);
    finalized = true;
    return Response.json({ id: 'verified-record' }, { status: 201 });
  });
  assert.equal((await submitEntry(form)).id, 'verified-record');
  assert.equal(finalized, true);
});

test("a private upload is not reported saved when final checksum verification fails", async (t) => {
  const form = new FormData();
  form.append('files', new File(['test'], 'test.txt'));
  t.mock.method(globalThis, 'fetch', async url => {
    if (url === '/api/system') return Response.json({ upload_mode: 'direct' });
    if (url === '/api/upload-intents') return Response.json({ id: 'intent', files: [{ grant: 'one' }] });
    if (url === '/api/storage') return Response.json({ url: 'https://storage.example/upload' });
    if (url === 'https://storage.example/upload') return Response.json({}, { status: 400 });
    return Response.json({ detail: 'The original file could not be verified.' }, { status: 503 });
  });
  await assert.rejects(submitEntry(form), error => error instanceof ApiError && error.status === 503);
});

test("a missing quantity stays missing and an exact zero stays zero", () => {
  assert.equal(quantity(null), null);
  assert.equal(quantity("0"), "0");
  assert.equal(quantity("0.000"), "0");
  assert.equal(quantity("7.250"), "7.25");
  assert.equal(quantity("12"), "12");
  assert.equal(quantity("9999999.999"), "9999999.999");
});

test("money display pads to the account decimals but never shortens a value", () => {
  const php = { code: "PHP", decimal_places: 2 };
  assert.equal(money(null, php), null);
  assert.equal(money("250", php), "PHP 250.00");
  assert.equal(money("249.9", php), "PHP 249.90");
  // A longer fraction is preserved rather than rounded away.
  assert.equal(money("249.995", php), "PHP 249.995");
  assert.equal(money("250", { code: null, decimal_places: null }), "250");
  assert.equal(money("250", null), "250");
});
