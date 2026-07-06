"use strict";
/* el.module.test.js -- E4, option-(b) test for the shared DOM-accessor leaf.
 *
 * Proves el.js is import-safe and that the lazy memoizing accessor resolves the
 * right nodes by id. Same option-(b) harness as the other leaf tests (S1b/S1c):
 * outside-only DOM, publish window+document, then dynamic import(). A fixture
 * document supplies a few registry ids so getElementById has something to find.
 *
 * The critical assertion is ADR-049: importing el.js does NOT touch the DOM.
 * We prove this by publishing a document whose getElementById COUNTS calls and
 * checking the count is still zero immediately after import -- resolution must
 * happen lazily, on first read of el.<name>, not at import time.
 *
 * ASCII only.
 */
const path = require("path");
const { JSDOM } = require("jsdom");

let pass = 0, fail = 0;
const ck = (n, c) => { c ? (pass++, console.log("  ok  - " + n)) : (fail++, console.log("  FAIL- " + n)); };

(async () => {
  const dom = new JSDOM(
    "<!DOCTYPE html><html><body>" +
    "<div id='note'></div>" +
    "<div id='answer-hint'></div>" +
    "<div id='choices'></div>" +
    "<div id='feedback'></div>" +
    "<input id='answer'>" +
    "<div id='speaker'></div>" +
    "</body></html>",
    { runScripts: "outside-only", pretendToBeVisual: true }
  );
  global.window = dom.window;
  global.document = dom.window.document;

  /* Wrap getElementById to count calls, so we can prove import is DOM-free. */
  let gebiCalls = 0;
  const realGebi = dom.window.document.getElementById.bind(dom.window.document);
  dom.window.document.getElementById = function (id) { gebiCalls++; return realGebi(id); };

  const mod = await import("file://" + path.resolve("el.js"));
  ck("module imported without throwing", !!mod);
  ck("exports el and EL_REGISTRY", !!mod.el && !!mod.EL_REGISTRY);

  /* --- ADR-049: import performed NO DOM lookups -------------------------- */
  ck("import touched the DOM zero times (lazy)", gebiCalls === 0);

  /* --- registry shape ---------------------------------------------------- */
  const reg = mod.EL_REGISTRY;
  ck("registry has 27 entries", Object.keys(reg).length === 27);
  ck("every entry has id + owner",
    Object.keys(reg).every(k => reg[k] && typeof reg[k].id === "string" && typeof reg[k].owner === "string"));
  ck("ids are unique",
    new Set(Object.keys(reg).map(k => reg[k].id)).size === Object.keys(reg).length);
  /* E4 reversal: choices/feedback stay drill-owned. */
  ck("choices owner is drill (E4 reversal)", reg.choices.owner === "drill");
  ck("feedback owner is drill (E4 reversal)", reg.feedback.owner === "drill");
  ck("note owner is stage", reg.note.owner === "stage");
  ck("answerHint owner is stage", reg.answerHint.owner === "stage");

  /* --- lazy resolution: first read resolves by id, then memoizes --------- */
  const before = gebiCalls;
  const noteNode = mod.el.note;
  ck("first read of el.note performs one lookup", gebiCalls === before + 1);
  ck("el.note resolves to the #note element", noteNode === dom.window.document.getElementById("note"));
  const midCount = gebiCalls; /* note the getElementById in the assert above bumps the count */
  const noteAgain = mod.el.note;
  ck("second read is memoized (no new lookup)", gebiCalls === midCount && noteAgain === noteNode);

  /* --- id mapping uses the registry id, not the logical name ------------- */
  const hintNode = mod.el.answerHint;
  ck("el.answerHint maps to id 'answer-hint'", hintNode === dom.window.document.getElementById("answer-hint"));

  console.log("\n" + pass + " passed, " + fail + " failed");
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error(e); process.exit(2); });
