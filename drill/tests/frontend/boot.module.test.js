"use strict";
/* boot.module.test.js -- E9, option-(b) test for the entry module boot.js.
 *
 * boot.js is the entry module: its module-scope boot-guard fires boot() at
 * import (Decision A / check-D exemption). So this test publishes a FULL DOM
 * fixture + fetch/navigator stubs BEFORE importing, and the import itself IS
 * the boot() integration act -- the honest shape for an entry point. It then
 * asserts the boot sequence ran end to end through the real module DAG (boot ->
 * {state, el, api, stage, stats, speech, session, drill}, with the drill<->
 * session cycle live).
 *
 * boot.js pulls the ENTIRE frontend graph, so a green import here is also the
 * strongest single check that all ten modules wire together under real ESM.
 *
 * ASCII only.
 */
const path = require("path");
const { JSDOM } = require("jsdom");

let pass = 0, fail = 0;
const ck = (n, c) => { c ? (pass++, console.log("  ok  - " + n)) : (fail++, console.log("  FAIL- " + n)); };
const tick = (ms) => new Promise(r => setTimeout(r, ms || 30));

function fixtureHtml() {
  return "<!DOCTYPE html><html><body>" +
    /* drill/stage nodes */
    "<span id='expression'></span><input id='answer'><div id='answer-row'></div>" +
    "<button id='action'></button><div id='feedback'></div><div id='answer-hint'></div>" +
    "<div id='choices'></div><button id='speaker'></button><div id='active-rung'></div>" +
    "<div id='hint-reveal'></div>" +
    "<div id='note'></div>" +
    /* stats/session nodes */
    "<span id='stat-total'></span><span id='stat-accuracy'></span><span id='stat-streak'></span>" +
    "<span id='streak-pips'></span><div id='session-controls'></div><div id='session-summary' hidden></div>" +
    "<div id='run-log' hidden><ul id='run-log-list'></ul></div>" +
    "<button id='stats-toggle' aria-expanded='false'></button><div id='stats-panel' hidden></div>" +
    /* boot's own selector + import nodes */
    "<select id='category'></select>" +
    "<div id='bank-selector'><select id='bank'></select></div>" +
    "<select id='difficulty'></select><div id='difficulty-note'></div>" +
    "<button id='import-toggle' aria-expanded='false'></button><div id='import-panel' hidden></div>" +
    "</body></html>";
}

(async () => {
  const dom = new JSDOM(fixtureHtml(), { runScripts: "outside-only", pretendToBeVisual: true });
  global.window = dom.window;
  global.document = dom.window.document;
  Object.defineProperty(global, "navigator", { value: dom.window.navigator, configurable: true });
  const doc = dom.window.document;
  dom.window.navigator.sendBeacon = () => true;
  dom.window.speechSynthesis = { cancel() {}, speak() {} };
  dom.window.SpeechSynthesisUtterance = function (t) { this.text = t; this.lang = ""; };

  const calls = [];
  const j = (o, ok = true, s = 200) => ({ ok, status: s, async json() { return o; } });
  const fetchStub = async (url, opts) => {
    calls.push({ url, body: opts && opts.body ? JSON.parse(opts.body) : null });
    if (url === "/api/categories") return j({ categories: [
      { id: 1, name: "arithmetic", description: "", config: {} },
      { id: 2, name: "vocabulary", description: "", config: {} }
    ] });
    if (url === "/api/banks") return j({ banks: [{ id: 9, category_id: 2, name: "spanish", language: "es" }] });
    if (url === "/api/difficulty-rungs") return j({ rungs: [] });
    if (url === "/api/session/start") return j({ session_id: 3 });
    if (url === "/api/session/end") return j({ ended: true });
    if (url.indexOf("/api/question") === 0) return j({ qtype: "arithmetic", question_text: "4 + 5", expected: "9", question_id: null });
    if (url === "/api/answer") return j({ correct: true, expected: "9", session_stats: { total: 1, correct: 1, accuracy: 1.0, streak: 1 } });
    return j({ error: "x" }, false, 404);
  };
  global.fetch = fetchStub; dom.window.fetch = fetchStub;

  /* Importing boot.js fires the boot-guard -> boot(). readyState is not
     "loading" under pretendToBeVisual, so boot() runs synchronously at import;
     await a tick for its async body (fetches) to settle. */
  const boot = await import("file://" + path.resolve("boot.js"));
  await tick();

  ck("boot module imported (full DAG resolved)", !!boot && typeof boot.boot === "function");
  ck("exports the boot surface",
    ["isDrillable", "fetchAndAttachBanks", "populateCategories", "populateDifficulty",
     "onCategoryChange", "onBankChange", "onImportToggle", "buildImportPanel",
     "refreshCategories", "boot"].every(n => typeof boot[n] === "function"));

  /* --- boot() ran: categories fetched + populated ----------------------- */
  const { state } = await import("file://" + path.resolve("state.js"));
  ck("boot fetched /api/categories", calls.some(c => c.url === "/api/categories"));
  ck("boot populated the category selector",
    doc.getElementById("category").querySelectorAll("option").length === 2);
  ck("boot set arithmeticCategoryId from the arithmetic category", state.arithmeticCategoryId === 1);
  ck("boot attached banks (fetchAndAttachBanks ran)",
    calls.some(c => c.url === "/api/banks") &&
    state.categories.find(c => c.id === 2).banks.length === 1);

  /* --- boot() set the default arithmetic selection ---------------------- */
  ck("boot defaulted the selection to arithmetic",
    state.selection && state.selection.categoryId === 1 && state.selection.bankId === null);
  ck("boot set the category control value", doc.getElementById("category").value === "1");
  ck("boot hid the bank selector for arithmetic", doc.getElementById("bank-selector").hidden === true);

  /* --- boot() drove the first question through the cycle ---------------- */
  ck("boot auto-started a session (cycle: loadQuestion -> startSession)", state.activeSessionId === 3);
  ck("boot loaded the first question", state.current && state.current.question_text === "4 + 5");
  ck("boot rendered the expression", doc.getElementById("expression").textContent === "4 + 5");
  ck("boot left the phase answering", state.phase === "answering");

  /* --- isDrillable: pure predicate -------------------------------------- */
  ck("isDrillable true for arithmetic", boot.isDrillable({ name: "arithmetic" }) === true);
  ck("isDrillable true for a category with banks",
    boot.isDrillable({ name: "vocabulary", banks: [{ id: 1 }] }) === true);
  ck("isDrillable false for a bankless non-arithmetic category",
    boot.isDrillable({ name: "vocabulary", banks: [] }) === false);

  /* --- onImportToggle: opens/builds the import panel -------------------- */
  const panel = doc.getElementById("import-panel");
  boot.onImportToggle();
  ck("onImportToggle opens the import panel", panel.hidden === false);
  ck("onImportToggle built the panel form (import-file present)",
    doc.getElementById("import-file") !== null);
  boot.onImportToggle();
  ck("onImportToggle closes the panel again", panel.hidden === true);

  console.log("\n" + pass + " passed, " + fail + " failed");
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error(e); process.exit(2); });
