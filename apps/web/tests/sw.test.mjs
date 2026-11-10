// Runs the real public/sw.js inside a simulated service-worker environment (node --test).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";

const src = readFileSync(new URL("../public/sw.js", import.meta.url), "utf8");
const WS = "e5e39909-dc87-4ce2-ab60-77d6802b898e";

function boot({ online = true } = {}) {
  const stores = new Map();
  const listeners = {};
  const store = (name) => {
    if (!stores.has(name)) stores.set(name, new Map());
    const m = stores.get(name);
    return { put: async (k, v) => void m.set(typeof k === "string" ? k : new URL(k.url).pathname, v), match: async (k) => m.get(typeof k === "string" ? k : new URL(k.url).pathname), keys: async () => [...m.keys()] };
  };
  const caches = { open: async (n) => store(n), match: async (k) => { for (const n of stores.keys()) { const h = await store(n).match(k); if (h) return h; } }, keys: async () => [...stores.keys()], delete: async (n) => stores.delete(n) };
  const calls = [];
  const env = {
    self: { addEventListener: (t, f) => (listeners[t] = f), location: new URL("http://localhost:3000"), skipWaiting: () => {}, clients: { claim: async () => {} } },
    caches, URL, Response, Headers, Promise, JSON,
    fetch: async (req) => { calls.push(req.url); if (!online) throw new Error("offline"); return new Response(JSON.stringify({ ok: true }), { status: 200, headers: { "content-type": "application/json" } }); },
  };
  vm.createContext(env);
  vm.runInContext(src, env);
  const fire = async (req) => { let p; listeners.fetch({ request: req, respondWith: (x) => (p = x) }); return p ? await p : undefined; };
  return { fire, listeners, stores, calls, env };
}
const get = (path, extra = {}) => ({ method: "GET", url: `http://localhost:3000${path}`, mode: "cors", ...extra });

test("a readable page is fetched live and the last good answer is kept", async () => {
  const w = boot();
  const res = await w.fire(get(`/api/v1/workspaces/${WS}/udhaar/summary`));
  assert.equal(res.status, 200);
  assert.deepEqual([...w.stores.get("vyapar-data-v1").keys()], [`/api/v1/workspaces/${WS}/udhaar/summary`]);
});

test("offline, the saved answer is served and marked, and unsaved pages fail clearly", async () => {
  const live = boot();
  await live.fire(get(`/api/v1/workspaces/${WS}/alerts/summary`));
  const off = boot({ online: false });
  off.stores.set("vyapar-data-v1", live.stores.get("vyapar-data-v1"));
  const saved = await off.fire(get(`/api/v1/workspaces/${WS}/alerts/summary`));
  assert.equal(saved.headers.get("x-vyapar-offline"), "1");
  const missing = await off.fire(get(`/api/v1/workspaces/${WS}/analytics/overview`));
  assert.equal(missing.status, 503);
  assert.equal((await missing.json()).error.code, "offline");
});

test("sessions, writes, uploads, streams and downloads are never touched or saved", async () => {
  const w = boot();
  assert.equal(await w.fire({ method: "POST", url: `http://localhost:3000/api/v1/auth/refresh`, mode: "cors" }), undefined);
  for (const path of ["/api/v1/auth/me", `/api/v1/workspaces/${WS}/assistant/stream`, `/api/v1/workspaces/${WS}/reports/x/pdf`, `/api/v1/workspaces/${WS}/documents/search`, `/api/v1/workspaces/${WS}/bills`]) {
    assert.equal(await w.fire(get(path)), undefined, path);
  }
  assert.equal(w.stores.get("vyapar-data-v1"), undefined);
});

test("responses marked no-store are not kept", async () => {
  const w = boot();
  w.env.fetch = async () => new Response("{}", { status: 200, headers: { "cache-control": "no-store" } });
  await w.fire(get(`/api/v1/workspaces/${WS}/alerts`));
  assert.equal(w.stores.get("vyapar-data-v1"), undefined);
});

test("the clear message deletes every saved number", async () => {
  const w = boot();
  await w.fire(get(`/api/v1/workspaces/${WS}/udhaar/summary`));
  assert.ok(w.stores.has("vyapar-data-v1"));
  let p;
  w.listeners.message({ data: "clear", waitUntil: (x) => (p = x) });
  await p;
  assert.equal(w.stores.has("vyapar-data-v1"), false);
});

test("a page navigation falls back to the offline page", async () => {
  const w = boot({ online: false });
  await (await w.env.caches.open("vyapar-static-v1")).put("/offline", new Response("offline page"));
  const res = await w.fire({ method: "GET", url: "http://localhost:3000/app/udhaar", mode: "navigate" });
  assert.equal(await res.text(), "offline page");
});
