"use strict";
/* _harness.js -- shared option-(b) integration harness for the migrated
 * classic frontend tests (E10 cutover).
 *
 * BACKGROUND. Before E10 the seven classic tests loaded the real index.html
 * under jsdom with runScripts:"dangerously" and read functions/state off the
 * leaked window (win.state, win.submitAnswer, win.loadQuestion, ...). After the
 * cutover index.html carries only <script type=module src=boot.js>, which jsdom
 * does NOT execute (F1). So those globals vanish. This harness rebuilds the
 * option-(b) shape the ten *.module.test.js already model: build a DOM with
 * runScripts:"outside-only", publish window/document/navigator + speech stubs
 * as globals, install a fetch stub, then dynamic-import the REAL modules and
 * drive them directly. boot.js's module-scope boot-guard fires boot() at import
 * (Decision A / ADR-051 check-D exemption), so importing boot IS the boot act.
 *
 * The DOM fixture below mirrors index.html's element ids 1:1 (every id the
 * modules look up via el.<key>, plus the container/badge/help nodes a couple of
 * tests read: active-rung, answer-row, difficulty-note, difficulty-selector,
 * import-help). It is deliberately structural, not styled -- CSS-dependent
 * assertions (import.test.js's [hidden] guard) read the real index.html file
 * statically instead, since jsdom does not model that cascade anyway.
 *
 * Node caches dynamic imports by resolved URL, per PROCESS. run.sh spawns one
 * `node` per test file, so there is no cross-test cache leakage and most tests
 * need NO cache-busting at all. IMPORTANT: within a single test, import every
 * module with the SAME url (no per-import bust token) -- boot.js's own internal
 * `import "./state.js"` resolves to the UNBUSTED url, so a test that wants the
 * same `state` instance boot mutated must also import the unbusted url. A bust
 * token only helps when re-evaluating a module against fresh globals (as
 * speech.module.test.js does for its speech-absent second import), and then the
 * WHOLE subgraph must be busted together or the instances diverge.
 *
 * ASCII only.
 */
const path = require("path");
const { JSDOM } = require("jsdom");

/* Every element id index.html carries, as a flat structural fixture. Grouped
   by owner for readability; ids match el.js EL_REGISTRY + the extra nodes. */
function fixtureHtml() {
  return "<!DOCTYPE html><html><body>" +
    /* drill / stage nodes */
    "<span id='expression'></span>" +
    "<div id='answer-row'><input id='answer'></div>" +
    "<button id='action'></button>" +
    "<div id='feedback'></div>" +
    "<div id='answer-hint'></div>" +
    "<div id='choices'></div>" +
    "<button id='speaker'></button>" +
    "<div id='active-rung' hidden></div>" +
    "<div id='note'></div>" +
    /* stats / session nodes */
    "<span id='stat-total'></span><span id='stat-accuracy'></span><span id='stat-streak'></span>" +
    "<span id='streak-pips'></span>" +
    "<div id='session-controls'></div>" +
    "<div id='run-log' hidden><ul id='run-log-list'></ul></div>" +
    "<div id='stats-view'>" +
    "<button id='stats-toggle' aria-expanded='false'></button>" +
    "<div id='stats-panel' hidden></div></div>" +
    /* boot's selectors + import panel */
    "<select id='category'></select>" +
    "<div id='bank-selector'><select id='bank'></select></div>" +
    "<div id='difficulty-selector'>" +
    "<select id='difficulty'></select>" +
    "<div id='difficulty-note' hidden></div></div>" +
    "<div id='import-section'>" +
    "<button id='import-toggle' aria-expanded='false'></button>" +
    "<div id='import-panel' hidden></div></div>" +
    "</body></html>";
}

/* Publish the DOM + the ambient globals the modules read (window, document,
   navigator, performance-adjacent stubs). Returns { dom, window, document }. */
function makeDom(opts) {
  opts = opts || {};
  const dom = new JSDOM(fixtureHtml(), { runScripts: "outside-only", pretendToBeVisual: true });
  const win = dom.window;
  global.window = win;
  global.document = win.document;
  /* navigator is a read-only getter on global in modern Node; define it so the
     unload keepalive path (navigator.sendBeacon) is reachable. */
  Object.defineProperty(global, "navigator", { value: win.navigator, configurable: true });
  win.navigator.sendBeacon = opts.sendBeacon || (() => true);

  /* Speech stubs, unless a test asks for speech to be absent. */
  if (opts.speechPresent === false) {
    delete win.speechSynthesis;
    delete win.SpeechSynthesisUtterance;
  } else {
    const speechLog = { speak: [], cancel: 0 };
    win.SpeechSynthesisUtterance = function (t) { this.text = t; this.lang = ""; this.onend = null; this.onerror = null; };
    win.speechSynthesis = {
      speak(u) { speechLog.speak.push({ text: u.text, lang: u.lang }); if (opts.onSpeak) opts.onSpeak(u); },
      cancel() { speechLog.cancel++; }
    };
    dom.__speechLog = speechLog;
  }

  /* Optional controllable clock. timing.js's nowMs() reads the BARE global
     `performance`, which under the option-(b) harness resolves to Node's global
     performance (NOT window.performance). So patch global.performance.now, the
     way timing.module.test.js drives it. */
  if (opts.clock) {
    dom.__savedPerf = global.performance;
    global.performance = { now: () => opts.clock.now() };
  }
  return { dom, window: win, document: win.document };
}

/* A benign default fetch so the boot-guard's auto-fired boot() at import time
   (before a test installs its real stub) does not throw on relative URLs under
   undici -- which would spuriously trip boot.js's console.error trace. Tests
   that drive real flows call installFetch() with their own stub afterward. */
function installDefaultFetch(win) {
  const noop = async () => ({ ok: true, status: 200, async json() { return { categories: [], banks: [], rungs: [] }; }, async text() { return "{}"; } });
  global.fetch = noop; win.fetch = noop;
}

/* Install a fetch stub on both the jsdom window and the bare global (modules
   reach fetch through the global). */
function installFetch(win, fetchImpl) {
  global.fetch = fetchImpl;
  win.fetch = fetchImpl;
}

/* Import a module by repo-root-relative name, optionally cache-busting so the
   whole reachable graph re-evaluates against the current DOM/stubs. */
async function importModule(name, cacheBust) {
  const url = "file://" + path.resolve(name) + (cacheBust ? "?b=" + cacheBust : "");
  return import(url);
}

const tick = (ms) => new Promise(r => setTimeout(r, ms || 30));

/* Reset the shared `state` singleton to its initial shape between scenarios.
 * Modules are singletons per process and boot.js's internal `import "./state.js"`
 * always resolves to the UNBUSTED url, so a per-scenario cache-bust cannot give
 * boot a fresh state (it would mutate the unbusted instance while the test reads
 * the busted one -- instance divergence). The faithful isolation is therefore to
 * import ONCE unbusted and reset the singleton's fields here, then re-run
 * boot.boot(). Mirrors the initial values in state.js. */
function resetState(state) {
  state.sessions = [];
  state.activeSessionId = null;
  state.arithmeticCategoryId = null;
  state.arithmeticCategoryName = "arithmetic";
  state.categories = [];
  state.selection = null;
  state.recentIds = [];
  state.difficulty = null;
  state.rungLabels = {};
  state.current = null;
  state.answerStartMark = null;
  state.phase = "idle";
}

/* Tiny check harness identical in spirit to the module tests'. */
function makeChecker() {
  const c = { pass: 0, fail: 0 };
  c.ck = (name, cond, extra) => {
    if (cond) { c.pass++; console.log("  ok  - " + name); }
    else { c.fail++; console.log("  FAIL- " + name + (extra ? "  [" + extra + "]" : "")); }
  };
  c.done = () => { console.log("\n" + c.pass + " passed, " + c.fail + " failed"); process.exit(c.fail ? 1 : 0); };
  return c;
}

module.exports = { fixtureHtml, makeDom, installFetch, installDefaultFetch, importModule, resetState, tick, makeChecker };
