"use strict";
/* api.test.js -- E2, option-(b) test for the frontend HTTP seam (roadmap #1).
 *
 * Imports the REAL api.js through Node's loader and drives readJson / apiGet /
 * apiPost against a stubbed fetch, mirroring state.test.js's harness (S1b/S1c):
 * build a DOM with runScripts:"outside-only", publish window+document, stub
 * fetch, THEN dynamic import(). api.js calls a bare global fetch(), so we
 * publish it on both window and global before importing.
 *
 * Covers the three real behaviors, unchanged from the inline script:
 *   - happy path: 2xx JSON is returned as-is;
 *   - the backend {error} envelope on !ok is surfaced as a thrown Error;
 *   - an unreadable body (json() rejects) throws the fixed reader message;
 *   - apiGet sends Accept; apiPost sends method/headers/JSON body.
 *
 * ASCII only.
 */
const path = require("path");
const { JSDOM } = require("jsdom");

let pass = 0, fail = 0;
const ck = (n, c) => { c ? (pass++, console.log("  ok  - " + n)) : (fail++, console.log("  FAIL- " + n)); };

/* A fetch stub that records calls and returns a Response-like object. Each
   queued reply is {status, ok, json} where json is a function (so it can
   resolve OR reject to model an unreadable body). */
function makeFetch() {
  const calls = [];
  let next = null;
  const stub = async (url, opts) => {
    calls.push({ url, opts: opts || null });
    const r = next; next = null;
    return r;
  };
  stub.calls = calls;
  stub.queue = (reply) => { next = reply; };
  return stub;
}
const ok = (obj) => ({ ok: true, status: 200, async json() { return obj; } });
const errEnvelope = (obj, status) => ({ ok: false, status: status, async json() { return obj; } });
const unreadable = (status) => ({ ok: (status || 200) < 400, status: status || 200, async json() { throw new Error("bad json"); } });

async function threw(fn) {
  try { await fn(); return null; } catch (e) { return e; }
}

(async () => {
  const dom = new JSDOM("<!DOCTYPE html><html><body></body></html>", {
    runScripts: "outside-only",
    pretendToBeVisual: true
  });
  global.window = dom.window;
  global.document = dom.window.document;
  const fetchStub = makeFetch();
  global.fetch = fetchStub;
  dom.window.fetch = fetchStub;

  const mod = await import("file://" + path.resolve("api.js"));
  ck("module imported without throwing", !!mod);
  ck("exports readJson / apiGet / apiPost",
    typeof mod.readJson === "function" && typeof mod.apiGet === "function" && typeof mod.apiPost === "function");

  /* --- apiGet happy path ------------------------------------------------- */
  fetchStub.queue(ok({ categories: [{ id: 1, name: "arithmetic" }] }));
  const got = await mod.apiGet("/api/categories");
  ck("apiGet returns parsed JSON", got && Array.isArray(got.categories) && got.categories[0].name === "arithmetic");
  const g = fetchStub.calls.pop();
  ck("apiGet requests the given path", g.url === "/api/categories");
  ck("apiGet sends Accept: application/json",
    g.opts && g.opts.headers && g.opts.headers["Accept"] === "application/json");
  ck("apiGet is a GET (no method field)", !(g.opts && g.opts.method));

  /* --- apiPost happy path ------------------------------------------------ */
  fetchStub.queue(ok({ session_id: 7 }));
  const posted = await mod.apiPost("/api/session/start", { category_id: 1 });
  ck("apiPost returns parsed JSON", posted && posted.session_id === 7);
  const p = fetchStub.calls.pop();
  ck("apiPost uses POST", p.opts && p.opts.method === "POST");
  ck("apiPost sends Content-Type application/json", p.opts.headers["Content-Type"] === "application/json");
  ck("apiPost sends Accept application/json", p.opts.headers["Accept"] === "application/json");
  ck("apiPost JSON-stringifies the body", p.opts.body === JSON.stringify({ category_id: 1 }));

  /* --- error envelope surfaced as a thrown Error ------------------------- */
  fetchStub.queue(errEnvelope({ error: "no such bank" }, 404));
  const e1 = await threw(() => mod.apiGet("/api/banks?x=1"));
  ck("!ok with {error} throws", e1 instanceof Error);
  ck("thrown message is the backend error text", e1 && e1.message === "no such bank");

  /* --- !ok without an {error} field falls back to status message --------- */
  fetchStub.queue(errEnvelope({}, 500));
  const e2 = await threw(() => mod.apiGet("/api/x"));
  ck("!ok without error uses status fallback", e2 instanceof Error && e2.message.indexOf("500") !== -1);

  /* --- unreadable body throws the fixed reader message ------------------- */
  fetchStub.queue(unreadable(200));
  const e3 = await threw(() => mod.apiGet("/api/y"));
  ck("unreadable body throws", e3 instanceof Error);
  ck("unreadable-body message is the fixed reader text",
    e3 && e3.message === "The server sent a response that could not be read.");

  /* --- readJson is usable directly (the multipart-import path depends on it) */
  const direct = await mod.readJson(ok({ ok: true }));
  ck("readJson returns data on a 2xx response", direct && direct.ok === true);
  const e4 = await threw(() => mod.readJson(errEnvelope({ error: "boom" }, 400)));
  ck("readJson throws the envelope error directly", e4 instanceof Error && e4.message === "boom");

  console.log("\n" + pass + " passed, " + fail + " failed");
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error(e); process.exit(2); });
