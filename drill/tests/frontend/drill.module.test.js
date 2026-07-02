"use strict";
/* drill.module.test.js -- E8, option-(b) test for the drill module, wired to
 * the REAL session.js (the drill<->session cycle, ADR-053/S6). Drives the real
 * drill.js + its full import graph (state, el, api, stage, speech, timing,
 * session) under Node's loader against a fixture DOM + stubbed fetch.
 *
 * The other half of the cycle pair (session.module.test.js is the first).
 * Focuses on drill-owned behavior: questionQuery URL building (the sel->
 * selection rename target), pushRecent windowing, the phase machine
 * (loading/answering/feedback/resting), and the loadQuestion -> render ->
 * answer -> gradeAndShow flow that drives the real session across the cycle.
 *
 * ASCII only.
 */
const path = require("path");
const { JSDOM } = require("jsdom");

let pass = 0, fail = 0;
const ck = (n, c) => { c ? (pass++, console.log("  ok  - " + n)) : (fail++, console.log("  FAIL- " + n)); };
const tick = (ms) => new Promise(r => setTimeout(r, ms || 20));

function fixtureHtml() {
  return "<!DOCTYPE html><html><body>" +
    "<span id='expression'></span><input id='answer'><div id='answer-row'></div>" +
    "<button id='action'></button><div id='feedback'></div><div id='answer-hint'></div>" +
    "<div id='choices'></div><button id='speaker'></button><div id='active-rung'></div>" +
    "<span id='stat-total'></span><span id='stat-accuracy'></span><span id='stat-streak'></span>" +
    "<span id='streak-pips'></span><div id='session-controls'></div>" +
    "<div id='run-log' hidden><ul id='run-log-list'></ul></div><div id='note'></div>" +
    "</body></html>";
}

(async () => {
  const dom = new JSDOM(fixtureHtml(), { runScripts: "outside-only", pretendToBeVisual: true });
  global.window = dom.window;
  global.document = dom.window.document;
  Object.defineProperty(global, "navigator", { value: dom.window.navigator, configurable: true });
  const doc = dom.window.document;
  dom.window.speechSynthesis = { cancel() {}, speak() {} };
  dom.window.SpeechSynthesisUtterance = function (t) { this.text = t; this.lang = ""; };

  const calls = [];
  const j = (o, ok = true, s = 200) => ({ ok, status: s, async json() { return o; } });
  let questionPayload = { qtype: "arithmetic", question_text: "6 + 7", expected: "13", question_id: null };
  let answerReply = { correct: true, expected: "13", user_input: "13", session_stats: { total: 1, correct: 1, accuracy: 1.0, streak: 1 } };
  const fetchStub = async (url, opts) => {
    calls.push({ url, body: opts && opts.body ? JSON.parse(opts.body) : null });
    if (url === "/api/session/start") return j({ session_id: 5 });
    if (url === "/api/session/end") return j({ ended: true });
    if (url.indexOf("/api/question") === 0) return j(questionPayload);
    if (url === "/api/answer") return j(answerReply);
    return j({ error: "x" }, false, 404);
  };
  global.fetch = fetchStub; dom.window.fetch = fetchStub;

  const drill = await import("file://" + path.resolve("drill.js"));
  const { state } = await import("file://" + path.resolve("state.js"));
  ck("drill module imported (cycle resolved)", !!drill && typeof drill.loadQuestion === "function");
  ck("exports the drill-loop surface",
    ["loadQuestion", "questionQuery", "pushRecent", "renderQuestion", "enterAnswering",
     "submitAnswer", "gradeAndShow", "enterFeedback", "enterResting", "onDocumentKey"]
      .every(n => typeof drill[n] === "function"));

  /* --- questionQuery: arithmetic default omits difficulty --------------- */
  state.selection = null; state.difficulty = null; state.recentIds = [];
  state.arithmeticCategoryName = "arithmetic";
  ck("arithmetic query has no difficulty when null",
    drill.questionQuery() === "/api/question?category=arithmetic");
  state.difficulty = 3;
  ck("arithmetic query carries difficulty when set",
    drill.questionQuery().indexOf("difficulty=3") !== -1);
  state.difficulty = null;

  /* --- questionQuery: bank category adds bank_id + recent --------------- */
  state.selection = { categoryName: "vocabulary", bankId: 8 };
  state.recentIds = [11, 12];
  const q = drill.questionQuery();
  ck("bank query adds bank_id", q.indexOf("bank_id=8") !== -1);
  ck("bank query adds recent window", q.indexOf("recent=11,12") !== -1);

  /* --- pushRecent: bounded window -------------------------------------- */
  state.recentIds = [];
  for (var i = 1; i <= 12; i++) drill.pushRecent(i);
  ck("pushRecent bounds the window to RECENT_MAX (10)", state.recentIds.length === 10);
  ck("pushRecent keeps the most-recent ids", state.recentIds[state.recentIds.length - 1] === 12 && state.recentIds[0] === 3);

  /* --- enterResting: phase + control DOM -------------------------------- */
  drill.enterResting();
  ck("enterResting sets phase resting", state.phase === "resting");
  ck("enterResting clears current", state.current === null);
  ck("enterResting shows -- placeholder", doc.getElementById("expression").textContent === "--");
  ck("enterResting disables the answer input", doc.getElementById("answer").disabled === true);

  /* --- loadQuestion: full arithmetic flow through the real session ------ */
  state.sessions = []; state.activeSessionId = null; state.selection = null;
  state.arithmeticCategoryId = 1;
  questionPayload = { qtype: "arithmetic", question_text: "6 + 7", expected: "13", question_id: null };
  await drill.loadQuestion();
  await tick();
  ck("loadQuestion auto-started a session via the cycle", state.activeSessionId === 5);
  ck("loadQuestion stored the served question", state.current && state.current.question_text === "6 + 7");
  ck("loadQuestion rendered the expression", doc.getElementById("expression").textContent === "6 + 7");
  ck("loadQuestion entered answering phase", state.phase === "answering");
  ck("answering enabled the input", doc.getElementById("answer").disabled === false);

  /* --- submitAnswer -> gradeAndShow: records to the real session -------- */
  doc.getElementById("answer").value = "13";
  await drill.submitAnswer();
  await tick();
  ck("answer posted to /api/answer", calls.some(c => c.url === "/api/answer"));
  ck("gradeAndShow entered feedback phase", state.phase === "feedback");
  ck("stats bar updated via the cycle (stats.renderStats ran)",
    doc.getElementById("stat-total").textContent === "1");
  ck("the active session recorded the stats (session.recordStats ran)",
    state.sessions[0].stats.total === 1 && state.sessions[0].stats.streak === 1);

  /* --- question_id tracking: bank ids are pushed to recent -------------- */
  state.recentIds = [];
  state.selection = { categoryName: "vocabulary", bankId: 8, categoryId: 2 };
  questionPayload = { qtype: "translate", question_text: "hola", expected: "hello", question_id: 77 };
  await drill.loadQuestion();
  await tick();
  ck("bank question id is tracked in recentIds", state.recentIds.indexOf(77) !== -1);

  console.log("\n" + pass + " passed, " + fail + " failed");
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error(e); process.exit(2); });
