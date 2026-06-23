"use strict";
/* C-019b contract test: the stats view disclosure. Verifies open fetches
   /api/stats and renders overall + per-category breakdown; the empty/time-zero
   state; close tears the panel down; a single-category summary skips the
   breakdown; the window echo renders for a filtered view; a fetch error shows
   a note; and the panel is independent of the live stats bar. */
const fs = require("fs");
const { JSDOM } = require("jsdom");
const html = fs.readFileSync("index.html", "utf8");

let pass = 0, fail = 0;
function check(name, cond, extra) {
  if (cond) { pass++; console.log("  ok  - " + name); }
  else { fail++; console.log("  FAIL- " + name + (extra ? "  [" + extra + "]" : "")); }
}
async function tick(ms) { return new Promise(r => setTimeout(r, ms || 30)); }

/* Backend stub: categories + banks for boot, plus a programmable /api/stats
   response (statsState.next) and a flag to fail the stats call. */
function makeBackend(statsState) {
  return async function (url) {
    const j = (o, ok = true, s = 200) => ({
      ok, status: s, async json() { return o; }, async text() { return JSON.stringify(o); }
    });
    if (url === "/api/categories")
      return j({ categories: [{ id: 1, name: "arithmetic", description: "", config: {} },
                               { id: 2, name: "vocabulary", description: "", config: {} }] });
    if (url === "/api/banks") return j({ banks: [] });
    if (url === "/api/session/start") return j({ session_id: 1 });
    if (url === "/api/session/end") return j({ ended: true });
    if (url.indexOf("/api/question") === 0)
      return j({ qtype: "arithmetic", question_text: "1 + 1", expected: "2",
                 question_id: null, alternatives: null, media_url: null });
    if (url === "/api/answer")
      return j({ correct: true, expected: "2", user_input: "2",
                 session_stats: { total: 1, correct: 1, accuracy: 1.0, streak: 1 } });
    if (url === "/api/stats") {
      if (statsState.fail) return j({ error: "stats boom" }, false, 500);
      return j(statsState.next);
    }
    return j({ error: "unexpected " + url }, false, 404);
  };
}

async function boot(statsNext, opts) {
  const statsState = { next: statsNext, fail: !!(opts && opts.fail) };
  const dom = new JSDOM(html, {
    runScripts: "dangerously", pretendToBeVisual: true,
    beforeParse(win) {
      win.fetch = makeBackend(statsState);
      win.navigator.sendBeacon = () => true;
      win.SpeechSynthesisUtterance = function (t) { this.text = t; this.lang = ""; };
      win.speechSynthesis = { speak() {}, cancel() {} };
    }
  });
  await tick(120);
  return { dom, statsState };
}

(async function () {
  /* -- Test 1: open renders overall + breakdown -------------------------- */
  console.log("Test 1: open fetches and renders");
  {
    const summary = {
      total: 10, correct: 8, accuracy: 0.8,
      categories: [
        { category_id: 1, category_name: "arithmetic", total: 7, correct: 6, accuracy: 6 / 7 },
        { category_id: 2, category_name: "vocabulary", total: 3, correct: 2, accuracy: 2 / 3 }
      ],
      window: { category_id: null, days: null, since: null }
    };
    const { dom } = await boot(summary);
    const win = dom.window, doc = win.document;
    const toggle = doc.getElementById("stats-toggle");
    const panel = doc.getElementById("stats-panel");
    check("panel hidden initially", panel.hidden === true);
    toggle.click();
    await tick(50);
    check("panel shown after open", panel.hidden === false);
    check("aria-expanded true", toggle.getAttribute("aria-expanded") === "true");
    const text = panel.textContent;
    /* Assert against the structured figures (textContent concatenates without
       spaces, so check the .stats-figure elements directly). */
    const figs = panel.querySelectorAll(".stats-overall .stats-figure");
    const figMap = {};
    figs.forEach(function (f) {
      figMap[f.querySelector("span").textContent] = f.querySelector("b").textContent;
    });
    check("shows total 10 (answered)", figMap["answered"] === "10", JSON.stringify(figMap));
    check("shows accuracy 80%", figMap["accuracy"] === "80%", JSON.stringify(figMap));
    check("shows correct 8", figMap["correct"] === "8", JSON.stringify(figMap));
    check("breakdown lists arithmetic", text.indexOf("arithmetic") !== -1);
    check("breakdown lists vocabulary", text.indexOf("vocabulary") !== -1);
    check("breakdown has By category title", text.indexOf("By category") !== -1);
    /* No window note for an unfiltered view. */
    check("no window note when unfiltered",
          panel.querySelector(".stats-window") === null);
    /* Independent of the live bar: top bar still shows session stats (0/--). */
    check("live stats bar untouched (separate source)",
          doc.getElementById("stat-total").textContent === "0",
          doc.getElementById("stat-total").textContent);
    dom.window.close();
  }

  /* -- Test 2: empty/time-zero state ------------------------------------- */
  console.log("Test 2: empty state");
  {
    const summary = { total: 0, correct: 0, accuracy: 0.0, categories: [],
                      window: { category_id: null, days: null, since: null } };
    const { dom } = await boot(summary);
    const doc = dom.window.document;
    doc.getElementById("stats-toggle").click();
    await tick(50);
    const text = doc.getElementById("stats-panel").textContent;
    check("empty note shown", text.toLowerCase().indexOf("no answers recorded") !== -1, text);
    check("no breakdown rows when empty",
          doc.getElementById("stats-panel").querySelector(".stats-row") === null);
    dom.window.close();
  }

  /* -- Test 3: close tears down ------------------------------------------ */
  console.log("Test 3: close tears down");
  {
    const summary = { total: 3, correct: 3, accuracy: 1.0,
      categories: [{ category_id: 1, category_name: "arithmetic", total: 3, correct: 3, accuracy: 1.0 }],
      window: { category_id: null, days: null, since: null } };
    const { dom } = await boot(summary);
    const doc = dom.window.document;
    const toggle = doc.getElementById("stats-toggle");
    const panel = doc.getElementById("stats-panel");
    toggle.click(); await tick(50);
    check("open populated panel", panel.textContent.length > 0);
    toggle.click(); await tick(20);
    check("panel hidden after close", panel.hidden === true);
    check("panel emptied after close", panel.textContent === "");
    check("aria-expanded false after close", toggle.getAttribute("aria-expanded") === "false");
    dom.window.close();
  }

  /* -- Test 4: single category skips breakdown --------------------------- */
  console.log("Test 4: single category, no breakdown");
  {
    const summary = { total: 5, correct: 4, accuracy: 0.8,
      categories: [{ category_id: 1, category_name: "arithmetic", total: 5, correct: 4, accuracy: 0.8 }],
      window: { category_id: null, days: null, since: null } };
    const { dom } = await boot(summary);
    const doc = dom.window.document;
    doc.getElementById("stats-toggle").click();
    await tick(50);
    const panel = doc.getElementById("stats-panel");
    check("overall shown for single category", panel.textContent.indexOf("80%") !== -1);
    check("no 'By category' for single category",
          panel.textContent.indexOf("By category") === -1);
    dom.window.close();
  }

  /* -- Test 5: window echo for a filtered view --------------------------- */
  console.log("Test 5: window echo");
  {
    const summary = { total: 4, correct: 4, accuracy: 1.0,
      categories: [{ category_id: 2, category_name: "vocabulary", total: 4, correct: 4, accuracy: 1.0 }],
      window: { category_id: 2, days: 7, since: "2024-01-01T00:00:00+00:00" } };
    const { dom } = await boot(summary);
    const doc = dom.window.document;
    doc.getElementById("stats-toggle").click();
    await tick(50);
    const winNote = doc.getElementById("stats-panel").querySelector(".stats-window");
    check("window note present when filtered", winNote !== null);
    check("window note names last 7 days", winNote && winNote.textContent.indexOf("last 7 days") !== -1,
          winNote && winNote.textContent);
    check("window note names category", winNote && winNote.textContent.indexOf("vocabulary") !== -1,
          winNote && winNote.textContent);
    dom.window.close();
  }

  /* -- Test 6: fetch error shows a note ---------------------------------- */
  console.log("Test 6: fetch error");
  {
    const { dom } = await boot(null, { fail: true });
    const doc = dom.window.document;
    doc.getElementById("stats-toggle").click();
    await tick(50);
    const text = doc.getElementById("stats-panel").textContent;
    check("error note shown", text.toLowerCase().indexOf("could not load stats") !== -1, text);
    dom.window.close();
  }

  console.log("\n" + pass + " passed, " + fail + " failed");
  process.exit(fail === 0 ? 0 : 1);
})().catch(e => { console.error(e); process.exit(2); });
