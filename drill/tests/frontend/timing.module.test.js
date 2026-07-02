"use strict";
/* timing.module.test.js -- E3, option-(b) test for the monotonic clock.
 *
 * Imports the REAL timing.js and proves both branches of nowMs, unchanged from
 * the inline script:
 *   - prefers performance.now() when available (monotonic);
 *   - falls back to Date.now() when performance is absent or has no now().
 * nowMs reads the GLOBAL performance behind a typeof guard, so the test drives
 * each branch by controlling global.performance before calling. Same option-(b)
 * harness as state/api (S1b/S1c): outside-only DOM, publish globals, then
 * dynamic import(). Kept structurally uniform with the other leaf tests so the
 * deferred leaves.module.test.js merge stays copy-paste (C-MOD-E-naming).
 *
 * Distinct from the pre-existing classic timing.test.js, which drives the whole
 * inline page to assert elapsed_ms on the /api/answer wire (C-018c contract).
 * This file checks the extracted module in isolation instead.
 *
 * ASCII only.
 */
const path = require("path");
const { JSDOM } = require("jsdom");

let pass = 0, fail = 0;
const ck = (n, c) => { c ? (pass++, console.log("  ok  - " + n)) : (fail++, console.log("  FAIL- " + n)); };

(async () => {
  const dom = new JSDOM("<!DOCTYPE html><html><body></body></html>", {
    runScripts: "outside-only",
    pretendToBeVisual: true
  });
  global.window = dom.window;
  global.document = dom.window.document;

  const savedPerf = global.performance;
  const mod = await import("file://" + path.resolve("timing.js"));
  ck("module imported without throwing", !!mod);
  ck("exports nowMs", typeof mod.nowMs === "function");

  /* --- performance.now() branch: preferred when available ---------------- */
  let perfCalls = 0;
  global.performance = { now: () => { perfCalls++; return 1234.5; } };
  const a = mod.nowMs();
  ck("uses performance.now() when present", perfCalls === 1 && a === 1234.5);
  ck("returns a number (ms)", typeof a === "number");

  /* monotonic: successive reads with an advancing stub are non-decreasing -- */
  let t = 100;
  global.performance = { now: () => { t += 5; return t; } };
  const m1 = mod.nowMs(), m2 = mod.nowMs();
  ck("successive reads are non-decreasing (monotonic)", m2 >= m1 && (m2 - m1) === 5);

  /* --- Date.now() fallback: performance undefined ------------------------ */
  global.performance = undefined;
  const before = Date.now();
  const f = mod.nowMs();
  const after = Date.now();
  ck("falls back to Date.now() when performance absent", f >= before && f <= after);

  /* --- guard also tolerates a performance without a now() function -------- */
  global.performance = {};
  const before2 = Date.now();
  const f2 = mod.nowMs();
  const after2 = Date.now();
  ck("falls back when performance has no now()", f2 >= before2 && f2 <= after2);

  global.performance = savedPerf;

  console.log("\n" + pass + " passed, " + fail + " failed");
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error(e); process.exit(2); });
