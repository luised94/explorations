"use strict";
/* session.module.test.js -- E7, option-(b) test for the session module, wired
 * to the REAL drill.js (the drill<->session cycle, ADR-053/S6). Drives the real
 * session.js + its full import graph (state, el, api, stage, stats, speech,
 * drill) under Node's loader against a fixture DOM + stubbed fetch.
 *
 * This is one half of the cycle pair (E7); drill.module.test.js is the other.
 * Both prove the cycle resolves green under ESM (S7): importing session.js
 * pulls drill.js and vice versa, and every cross-cycle call is to a hoisted
 * function declaration.
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
    "<div id='hint-reveal'></div>" +
    "<span id='stat-total'></span><span id='stat-accuracy'></span><span id='stat-streak'></span>" +
    "<span id='streak-pips'></span><div id='session-controls'></div><div id='session-summary' hidden></div>" +
    "<div id='run-log' hidden><ul id='run-log-list'></ul></div>" +
    "<div id='note'></div>" +
    "</body></html>";
}

(async () => {
  const dom = new JSDOM(fixtureHtml(), { runScripts: "outside-only", pretendToBeVisual: true });
  global.window = dom.window;
  global.document = dom.window.document;
  /* Node 22 provides its own global.navigator (without sendBeacon); the module
     reads a bare `navigator`, so publish the jsdom one as the global to match
     the browser environment the module targets at cutover. */
  Object.defineProperty(global, "navigator", { value: dom.window.navigator, configurable: true });
  const doc = dom.window.document;
  dom.window.navigator.sendBeacon = () => true;
  /* speech feature-detect: give a minimal speechSynthesis so speechAvailable
     is true and cancelSpeech paths execute (they are called on session end). */
  dom.window.speechSynthesis = { cancel() {}, speak() {} };
  dom.window.SpeechSynthesisUtterance = function (t) { this.text = t; this.lang = ""; };

  /* fetch stub: session start/end + question + answer, recording bodies. */
  const calls = [];
  const j = (o, ok = true, s = 200) => ({ ok, status: s, async json() { return o; } });
  const fetchStub = async (url, opts) => {
    calls.push({ url, body: opts && opts.body ? JSON.parse(opts.body) : null });
    if (url === "/api/session/start") return j({ session_id: 42 });
    if (url === "/api/session/end") return j({ ended: true, summary: {
      total: 3, correct: 2, accuracy: 0.667, streak: 0,
      new_introduced_today: 1, due_remaining: 4
    } });
    if (url.indexOf("/api/question") === 0) return j({ qtype: "arithmetic", question_text: "2 + 2", expected: "4", question_id: null });
    if (url === "/api/answer") return j({ correct: true, expected: "4", session_stats: { total: 1, correct: 1, accuracy: 1.0, streak: 1 } });
    return j({ error: "x" }, false, 404);
  };
  global.fetch = fetchStub; dom.window.fetch = fetchStub;

  /* Import the cycle pair. session.js imports drill.js; the import resolves the
     whole graph. */
  const session = await import("file://" + path.resolve("session.js"));
  const { state, ZERO_STATS } = await import("file://" + path.resolve("state.js"));
  ck("session module imported (cycle resolved)", !!session && typeof session.startSession === "function");
  ck("exports the transition + UI + handler surface",
    ["activeSession", "startSession", "recordStats", "endSession", "renderSessionUI",
     "renderSessionControls", "onStartSession", "onRestartSession", "onEndSession", "endSessionOnUnload"]
      .every(n => typeof session[n] === "function"));

  /* --- startSession: posts + appends an active record ------------------- */
  state.sessions = []; state.activeSessionId = null; state.selection = null;
  state.arithmeticCategoryId = 1; state.arithmeticCategoryName = "arithmetic";
  const id = await session.startSession();
  ck("startSession returns the server id", id === 42);
  ck("startSession posted to /api/session/start", calls.some(c => c.url === "/api/session/start"));
  ck("startSession defaults to arithmetic category", calls.find(c => c.url === "/api/session/start").body.category_id === 1);
  ck("startSession appends an active record", state.sessions.length === 1 && state.sessions[0].status === "active");
  ck("startSession sets activeSessionId", state.activeSessionId === 42);
  ck("startSession resets recentIds", Array.isArray(state.recentIds) && state.recentIds.length === 0);

  /* --- activeSession: finds the active record --------------------------- */
  ck("activeSession returns the active record", session.activeSession() === state.sessions[0]);

  /* --- recordStats: folds a snapshot into the record -------------------- */
  session.recordStats(42, { total: 3, correct: 2, accuracy: 0.66, streak: 2 });
  ck("recordStats updates the record stats", state.sessions[0].stats.total === 3 && state.sessions[0].stats.streak === 2);
  session.recordStats(999, { total: 9, correct: 9, accuracy: 1, streak: 9 });
  ck("recordStats no-ops on unknown id", state.sessions[0].stats.total === 3);

  /* --- renderSessionUI: derived surfaces + pip visibility --------------- */
  session.renderSessionUI();
  ck("renderSessionUI shows pips when active", doc.getElementById("streak-pips").style.visibility === "visible");
  ck("renderSessionUI renders the active control row",
    doc.getElementById("session-controls").querySelector("#restart-session") !== null &&
    doc.getElementById("session-controls").querySelector("#end-session") !== null);

  /* --- endSession: posts end, marks ended, clears active ---------------- */
  await session.endSession(42);
  ck("endSession posted to /api/session/end", calls.some(c => c.url === "/api/session/end"));
  ck("endSession marks the record ended", state.sessions[0].status === "ended");
  ck("endSession clears activeSessionId", state.activeSessionId === null);
  await session.endSession(null);
  ck("endSession(null) is a no-op", state.activeSessionId === null);

  /* --- resting render: single Start control + pips hidden --------------- */
  session.renderSessionUI();
  ck("resting shows the Start control", doc.getElementById("session-controls").querySelector("#start-session") !== null);
  ck("resting hides the pips", doc.getElementById("streak-pips").style.visibility === "hidden");

  /* --- the CYCLE edge: onStartSession -> loadQuestion (real drill) ------- */
  state.sessions = []; state.activeSessionId = null; state.selection = null;
  const qBefore = calls.filter(c => c.url.indexOf("/api/question") === 0).length;
  await session.onStartSession();
  await tick();
  ck("onStartSession drove the real drill.loadQuestion (a session auto-started)", state.activeSessionId === 42);
  ck("onStartSession fetched a question through the cycle",
    calls.filter(c => c.url.indexOf("/api/question") === 0).length === qBefore + 1);
  ck("onStartSession left phase answering (drill entered the loop)", state.phase === "answering");

  /* --- onEndSession: ends + rests via real drill.enterResting ----------- */
  await session.onEndSession();
  ck("onEndSession cleared the active session", state.activeSessionId === null);
  ck("onEndSession rested the phase (drill.enterResting ran)", state.phase === "resting");

  /* --- Q4: the closing summary view -------------------------------------- */
  const summaryNode = doc.getElementById("session-summary");
  ck("onEndSession shows the summary view", summaryNode.hidden === false);
  ck("summary line carries the counts",
    summaryNode.textContent.indexOf("2/3 correct (67%)") !== -1 &&
    summaryNode.textContent.indexOf("1 new introduced today") !== -1 &&
    summaryNode.textContent.indexOf("4 due next in this bank") !== -1);
  ck("summary offers the feedback controls",
    summaryNode.querySelector("#session-rating") !== null &&
    summaryNode.querySelector("#session-note") !== null &&
    summaryNode.querySelector("#save-session-feedback") !== null);

  /* --- Q4b: saving feedback re-posts session/end with the fields --------- */
  summaryNode.querySelector("#session-rating").value = "4";
  summaryNode.querySelector("#session-note").value = "  felt smooth  ";
  const endPostsBefore = calls.filter(c => c.url === "/api/session/end").length;
  summaryNode.querySelector("#save-session-feedback").click();
  await tick();
  const feedbackCalls = calls.filter(c => c.url === "/api/session/end");
  ck("save posted a second session/end", feedbackCalls.length === endPostsBefore + 1);
  const feedbackBody = feedbackCalls[feedbackCalls.length - 1].body;
  ck("feedback body carries rating and trimmed note",
    feedbackBody.rating === 4 && feedbackBody.note === "felt smooth");
  ck("save disables after success",
    summaryNode.querySelector("#save-session-feedback").disabled === true);

  /* --- Q4: a new run dismisses the summary ------------------------------- */
  await session.onStartSession();
  await tick();
  ck("starting a new run hides the summary", summaryNode.hidden === true && summaryNode.textContent === "");
  await session.onEndSession(); /* back to resting for the unload check below */

  /* --- endSessionOnUnload: beacon path, no throw ------------------------ */
  state.activeSessionId = 7;
  let beaconUrl = null;
  dom.window.navigator.sendBeacon = (url) => { beaconUrl = url; return true; };
  session.endSessionOnUnload();
  ck("endSessionOnUnload beacons the end endpoint", beaconUrl === "/api/session/end");

  console.log("\n" + pass + " passed, " + fail + " failed");
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error(e); process.exit(2); });
