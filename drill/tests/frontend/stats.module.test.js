"use strict";
/* stats.module.test.js -- E6, option-(b) test for stats rendering.
 *
 * Drives the REAL stats.js (imports real state.js, el.js, api.js) against a
 * fixture DOM. Same option-(b) harness (S1b/S1c): outside-only DOM, publish
 * window+document, stub fetch (for onStatsToggle's /api/stats), then dynamic
 * import(). Exercises the real chain stats -> {state, el, api}.
 *
 * ASCII only.
 */
const path = require("path");
const { JSDOM } = require("jsdom");

let pass = 0, fail = 0;
const ck = (n, c) => { c ? (pass++, console.log("  ok  - " + n)) : (fail++, console.log("  FAIL- " + n)); };
const tick = (ms) => new Promise(r => setTimeout(r, ms || 20));

(async () => {
  const dom = new JSDOM(
    "<!DOCTYPE html><html><body>" +
    "<span id='stat-total'></span><span id='stat-accuracy'></span>" +
    "<span id='stat-streak'></span><span id='streak-pips'></span>" +
    "<div id='run-log' hidden><ul id='run-log-list'></ul></div>" +
    "<button id='stats-toggle' aria-expanded='false'>+ Stats across sessions</button>" +
    "<div id='stats-panel' hidden></div>" +
    "</body></html>",
    { runScripts: "outside-only", pretendToBeVisual: true }
  );
  global.window = dom.window;
  global.document = dom.window.document;
  const doc = dom.window.document;

  /* fetch stub for onStatsToggle */
  let nextStats = null, statsCalls = 0;
  const fetchStub = async (url) => {
    if (url === "/api/stats") {
      statsCalls++;
      return { ok: true, status: 200, async json() { return nextStats; } };
    }
    return { ok: false, status: 404, async json() { return { error: "x" }; } };
  };
  global.fetch = fetchStub; dom.window.fetch = fetchStub;

  const mod = await import("file://" + path.resolve("stats.js"));
  const { state } = await import("file://" + path.resolve("state.js"));
  ck("module imported without throwing", !!mod);
  ck("exports the public surface",
    ["renderStats", "renderStreakPips", "renderRunLog", "figure", "onStatsToggle",
     "renderStatsPanel", "statsFigure", "statsWindowText", "categoryNameById",
     "formatElapsed"]
      .every(n => typeof mod[n] === "function"));

  /* --- renderStats: total/accuracy/streak + pips ------------------------- */
  mod.renderStats({ total: 8, correct: 6, accuracy: 0.75, streak: 3 });
  ck("renderStats sets total", doc.getElementById("stat-total").textContent === "8");
  ck("renderStats rounds accuracy to %", doc.getElementById("stat-accuracy").textContent === "75%");
  ck("renderStats sets streak", doc.getElementById("stat-streak").textContent === "3");
  ck("renderStats zero-total shows -- for accuracy",
    (mod.renderStats({ total: 0, correct: 0, accuracy: 0, streak: 0 }),
      doc.getElementById("stat-accuracy").textContent === "--"));

  /* --- renderStreakPips: capped pip row + overflow badge ----------------- */
  mod.renderStreakPips(3);
  let pips = doc.getElementById("streak-pips");
  ck("pips render exactly STREAK_PIPS_MAX (10) base pips", pips.querySelectorAll(".pip").length === 10);
  ck("3 pips are 'on'", pips.querySelectorAll(".pip.on").length === 3);
  ck("no overflow badge at streak 3", pips.querySelectorAll(".more").length === 0);
  mod.renderStreakPips(13);
  pips = doc.getElementById("streak-pips");
  ck("all 10 pips on at streak 13", pips.querySelectorAll(".pip.on").length === 10);
  ck("overflow badge shows +3", pips.querySelector(".more") && pips.querySelector(".more").textContent === "+3");

  /* --- renderRunLog: newest-first ended sessions with totals ------------- */
  state.sessions = [
    { id: 1, status: "ended", categoryName: "arithmetic", bankName: null, stats: { total: 5, correct: 5, accuracy: 1.0, streak: 5 } },
    { id: 2, status: "ended", categoryName: "vocabulary", bankName: "spanish", stats: { total: 3, correct: 2, accuracy: 0.66, streak: 1 } },
    { id: 3, status: "active", categoryName: "x", bankName: null, stats: { total: 9, correct: 9, accuracy: 1.0, streak: 9 } },
    { id: 4, status: "ended", categoryName: "y", bankName: null, stats: { total: 0, correct: 0, accuracy: 0, streak: 0 } }
  ];
  mod.renderRunLog();
  const runLog = doc.getElementById("run-log");
  const items = doc.getElementById("run-log-list").querySelectorAll("li.run-row");
  ck("run log shows only ended sessions with total>0 (2 of 4)", items.length === 2);
  ck("run log is visible when non-empty", runLog.hidden === false);
  ck("run log newest-first (session #2 first)",
    items[0].querySelector(".run-cat").textContent === "vocabulary / spanish #2");
  ck("run log names category only when no bank",
    items[1].querySelector(".run-cat").textContent === "arithmetic #1");
  /* empty run log hides */
  state.sessions = [];
  mod.renderRunLog();
  ck("empty run log is hidden", doc.getElementById("run-log").hidden === true);

  /* --- figure / statsFigure: value + label DOM -------------------------- */
  const f = mod.figure(12, "answered");
  ck("figure emphasizes the value", f.querySelector("b").textContent === "12");
  ck("figure appends the label text", f.textContent === "12 answered");
  const sf = mod.statsFigure("75%", "accuracy");
  ck("statsFigure has the stats-figure class", sf.className === "stats-figure");
  ck("statsFigure value in <b>", sf.querySelector("b").textContent === "75%");

  /* --- statsWindowText / categoryNameById ------------------------------- */
  ck("no window -> empty string", mod.statsWindowText(null) === "");
  ck("days window -> 'last N days'", mod.statsWindowText({ days: 7 }) === "Showing last 7 days");
  ck("singular day", mod.statsWindowText({ days: 1 }) === "Showing last 1 day");
  state.categories = [{ id: 5, name: "geography" }];
  ck("categoryNameById resolves", mod.categoryNameById(5) === "geography");
  ck("categoryNameById unknown -> empty", mod.categoryNameById(99) === "");
  ck("window with known category names it",
    mod.statsWindowText({ category_id: 5 }) === "Showing category: geography");

  /* --- onStatsToggle: open -> loading -> render; toggle closed ---------- */
  nextStats = { total: 10, correct: 8, accuracy: 0.8, categories: [], window: null, difficulty_breakdown: [] };
  await mod.onStatsToggle();
  await tick();
  const panel = doc.getElementById("stats-panel");
  const toggle = doc.getElementById("stats-toggle");
  ck("toggle fetched /api/stats once", statsCalls === 1);
  ck("panel is visible after open", panel.hidden === false);
  ck("toggle aria-expanded true after open", toggle.getAttribute("aria-expanded") === "true");
  ck("panel rendered the overall row", panel.querySelector(".stats-overall") !== null);
  await mod.onStatsToggle();
  ck("second toggle closes the panel", panel.hidden === true);
  ck("toggle aria-expanded false after close", toggle.getAttribute("aria-expanded") === "false");

  /* --- renderStatsPanel: empty summary -> friendly note ----------------- */
  mod.renderStatsPanel({ total: 0 });
  ck("empty summary shows the friendly note",
    panel.querySelector(".stats-note") !== null &&
    panel.querySelector(".stats-note").textContent.indexOf("No answers recorded") === 0);

  /* --- renderStatsPanel: category breakdown when >1 category ------------ */
  mod.renderStatsPanel({
    total: 20, correct: 15, accuracy: 0.75,
    categories: [{ category_name: "arithmetic", total: 12, accuracy: 0.8 },
                 { category_name: "vocabulary", total: 8, accuracy: 0.6 }],
    window: null, difficulty_breakdown: []
  });
  ck("category breakdown renders with >1 category", panel.querySelector(".stats-breakdown") !== null);
  ck("category rows present", panel.querySelectorAll(".stats-row").length === 2);

  /* --- formatElapsed: ms under a second, seconds with one decimal above --- */
  ck("formatElapsed sub-second -> ms", mod.formatElapsed(850) === "850 ms");
  ck("formatElapsed >= 1s -> seconds 1dp", mod.formatElapsed(2400) === "2.4 s");
  ck("formatElapsed exactly 1000 -> 1.0 s", mod.formatElapsed(1000) === "1.0 s");

  /* --- renderStatsPanel: median timing figure present when non-null ------ */
  mod.renderStatsPanel({
    total: 5, correct: 4, accuracy: 0.8,
    categories: [], window: null, difficulty_breakdown: [],
    median_elapsed_ms: 1500
  });
  const overallWithTime = panel.querySelector(".stats-overall");
  const timeFigPresent = Array.prototype.some.call(
    overallWithTime.querySelectorAll(".stats-figure span"),
    s => s.textContent === "median time"
  );
  ck("median time figure renders when present", timeFigPresent);
  const timeVal = Array.prototype.find.call(
    overallWithTime.querySelectorAll(".stats-figure"),
    f => f.querySelector("span") && f.querySelector("span").textContent === "median time"
  );
  ck("median time value formatted", timeVal && timeVal.querySelector("b").textContent === "1.5 s");

  /* --- renderStatsPanel: median timing figure ABSENT when null ---------- */
  mod.renderStatsPanel({
    total: 5, correct: 4, accuracy: 0.8,
    categories: [], window: null, difficulty_breakdown: [],
    median_elapsed_ms: null
  });
  const overallNoTime = panel.querySelector(".stats-overall");
  const timeFigAbsent = !Array.prototype.some.call(
    overallNoTime.querySelectorAll(".stats-figure span"),
    s => s.textContent === "median time"
  );
  ck("median time figure suppressed when null", timeFigAbsent);

  console.log("\n" + pass + " passed, " + fail + " failed");
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error(e); process.exit(2); });
