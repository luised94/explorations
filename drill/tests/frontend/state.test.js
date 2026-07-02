"use strict";
/* state.test.js -- E1, the FIRST option-(b) frontend test (roadmap #1).
 *
 * Proves state.js is a clean, import-safe ES-module leaf by importing the REAL
 * module through Node's loader and driving it directly -- the frontend mirror
 * of the backend load_drill() pattern (ADR-049, spike S1b/S1c). jsdom does NOT
 * execute <script type=module> (F1, re-confirmed against jsdom 29.1.1), so we
 * do NOT let jsdom run a page; we build a DOM with runScripts:"outside-only",
 * publish window+document as globals BEFORE the import, then dynamic import().
 *
 * state.js touches no DOM, so the globals are not strictly needed for THIS
 * module -- but publishing them first is the harness contract every later
 * option-(b) module test (E2-E9) inherits, and it proves the import is clean
 * (no import-time throw) under the exact conditions those modules will face.
 *
 * A plain .test.js (async IIFE + dynamic import()) is discovered by the run.sh
 * glob with zero run.sh changes (S1c). cwd is PROJECT_ROOT, so "./state.js"
 * resolves to the repo-root module next to index.html.
 *
 * ASCII only.
 */
const path = require("path");
const { JSDOM } = require("jsdom");

let pass = 0, fail = 0;
const ck = (n, c) => { c ? (pass++, console.log("  ok  - " + n)) : (fail++, console.log("  FAIL- " + n)); };

(async () => {
  /* Build a DOM WITHOUT running page scripts, then publish the globals a real
     ES module would see in the browser, BEFORE importing anything. */
  const dom = new JSDOM("<!DOCTYPE html><html><body></body></html>", {
    runScripts: "outside-only",
    pretendToBeVisual: true
  });
  global.window = dom.window;
  global.document = dom.window.document;

  /* Import the REAL module through Node's loader (absolute file URL so it works
     regardless of this file's directory). */
  const modUrl = "file://" + path.resolve("state.js");
  const mod = await import(modUrl);

  /* --- import is clean (no import-time DOM access / no throw) ------------- */
  ck("module imported without throwing", !!mod);

  /* --- constants relocated verbatim -------------------------------------- */
  ck("STREAK_PIPS_MAX === 10", mod.STREAK_PIPS_MAX === 10);
  ck("RECENT_MAX === 10", mod.RECENT_MAX === 10);

  /* --- ZERO_STATS shape -------------------------------------------------- */
  ck("ZERO_STATS.total === 0", mod.ZERO_STATS.total === 0);
  ck("ZERO_STATS.correct === 0", mod.ZERO_STATS.correct === 0);
  ck("ZERO_STATS.accuracy === 0.0", mod.ZERO_STATS.accuracy === 0.0);
  ck("ZERO_STATS.streak === 0", mod.ZERO_STATS.streak === 0);

  /* --- state initial shape (the resting/idle defaults) ------------------- */
  const s = mod.state;
  ck("state exported as an object", s && typeof s === "object");
  ck("state.phase starts idle", s.phase === "idle");
  ck("state.activeSessionId starts null", s.activeSessionId === null);
  ck("state.sessions starts empty array", Array.isArray(s.sessions) && s.sessions.length === 0);
  ck("state.categories starts empty array", Array.isArray(s.categories) && s.categories.length === 0);
  ck("state.recentIds starts empty array", Array.isArray(s.recentIds) && s.recentIds.length === 0);
  ck("state.selection starts null", s.selection === null);
  ck("state.difficulty starts null (default no-rung path)", s.difficulty === null);
  ck("state.rungLabels starts empty object",
    s.rungLabels && typeof s.rungLabels === "object" && Object.keys(s.rungLabels).length === 0);
  ck("state.current starts null", s.current === null);
  ck("state.answerStartMark starts null", s.answerStartMark === null);
  ck("state.arithmeticCategoryName === 'arithmetic'", s.arithmeticCategoryName === "arithmetic");
  ck("state.arithmeticCategoryId starts null", s.arithmeticCategoryId === null);

  /* --- state is a live mutable singleton (same reference across reads) ---- */
  ck("state is the same reference on re-read", mod.state === s);
  s.phase = "answering";
  ck("state mutation is observable on the module binding", mod.state.phase === "answering");

  console.log("\n" + pass + " passed, " + fail + " failed");
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error(e); process.exit(2); });
