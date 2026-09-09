import { test } from "node:test";
import assert from "node:assert/strict";
import { starterTasks } from "../src/readiness.ts";
import { api, ApiError } from "../src/api.ts";

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
