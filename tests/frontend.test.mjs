import { test } from "node:test";
import assert from "node:assert/strict";
import { starterTasks } from "../src/readiness.ts";
import { api, ApiError, grouped, money, quantity, submitEntry } from "../src/api.ts";
import {
  groupMargin,
  hasCeiling,
  orderMessage,
  percentLabel,
} from "../src/ordering.ts";

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

test("money keeps every digit while adding separators", () => {
  const php = { code: "PHP", decimal_places: 2 };
  assert.equal(money("1814258.70", php), "PHP 1,814,258.70");
  assert.equal(money("999", php), "PHP 999.00");
  assert.equal(money("1000", php), "PHP 1,000.00");
  assert.equal(money("-1234.5", php), "PHP -1,234.50");
  // A longer fraction is still never rounded away.
  assert.equal(money("1234.567", php), "PHP 1,234.567");
});

const reorder = (patch = {}) => ({
  supplier_id: "market",
  supplier_name: "Marketplace",
  supplier_note: null,
  buffer_days: 2,
  cycle: false,
  lead_days: { min: 8, max: 8 },
  next_order_day: null,
  arrives: null,
  order_by: null,
  status: "order_now",
  days_of_cover: 1,
  suggested_order: 6,
  contact: { whatsapp: null, viber: null, messenger: null, person: "Ana" },
  buy_url: "https://shopee.ph/search?keyword=mustard",
  buy_kind: "search",
  buy_note: null,
  other_sources: [],
  target_buy_price: "206.50",
  target_state: "ok",
  target_margin: "0.30",
  sell_price: "295",
  recorded_cost: "192",
  implied_price: null,
  ...patch,
});
const due = (patch = {}) => ({
  key: "v1:store-a",
  name: "Mustard Dijon 185g",
  sku: "10437",
  inStock: "1",
  reorder: reorder(patch),
});
const group = (...items) => ({
  supplierId: "market",
  supplierName: "Marketplace",
  reorder: items[0].reorder,
  items,
});

test("the buying ceiling never reaches the message a supplier is sent", () => {
  // The text goes out over WhatsApp. The ceiling is our margin, and a supplier
  // who reads it knows the top of every negotiation after it.
  const text = orderMessage(
    group(due(), due({ target_state: "over", implied_price: "239" })),
    "Panglao",
  );
  for (const secret of ["206.50", "0.30", "30%", "192", "295", "239"])
    assert.ok(!text.includes(secret), `message leaked ${secret}: ${text}`);
});

test("the message a supplier is sent still carries the order itself", () => {
  const text = orderMessage(group(due()), "Panglao");
  assert.ok(text.includes("Hi Ana"));
  assert.ok(text.includes("- Mustard Dijon 185g: 6 (10437)"));
  assert.ok(text.includes("The Sausage Guy Panglao"));
});

test("a share is shown as a percentage without a floating point tail", () => {
  // 0.3 * 100 is 30.000000000000004 in binary floating point.
  assert.equal(percentLabel("0.30"), "30%");
  assert.equal(percentLabel("0.35"), "35%");
  assert.equal(percentLabel("0.325"), "32.5%");
  assert.equal(percentLabel(null), null);
});

test("a card explains the ceiling only when something on it has one", () => {
  assert.equal(hasCeiling(group(due())), true);
  assert.equal(hasCeiling(group(due({ target_state: "not_shopee" }))), false);
  // One Shopee line among quoted ones is still worth explaining.
  assert.equal(
    hasCeiling(group(due({ target_state: "not_shopee" }), due())),
    true,
  );
});

test("the margin shown on a card comes from the figures, not from a constant", () => {
  assert.equal(groupMargin(group(due({ target_margin: "0.35" }))), "0.35");
  // A card of quoted suppliers carries no margin to show at all.
  assert.equal(
    groupMargin(
      group(due({ target_state: "not_shopee", target_margin: null })),
    ),
    null,
  );
});

test("a catalogue stored before the ceiling shipped explains no ceiling", () => {
  // This crashed the order view in production: the stored snapshot carried no
  // target_state, every check fell through, and money(undefined) hit .split.
  const old = due();
  delete old.reorder.target_state;
  delete old.reorder.target_buy_price;
  delete old.reorder.target_margin;
  assert.equal(hasCeiling(group(old)), false);
  assert.equal(groupMargin(group(old)), null);
});

test("money and grouped refuse an absent value rather than reading it", () => {
  const php = { code: "PHP", decimal_places: 2 };
  assert.equal(money(undefined, php), null);
  assert.equal(money(null, php), null);
  assert.equal(grouped(undefined), null);
  // A real value is still untouched.
  assert.equal(money("206.5", php), "PHP 206.50");
});
