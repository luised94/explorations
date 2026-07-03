"use strict";
/* stats.test.js -- MIGRATED to option (b) at the E10 cutover (was the C-019b
 * contract test driving the real inline page via a stats-toggle click).
 *
 * The stats view disclosure: open fetches /api/stats and renders overall +
 * per-category breakdown; empty/time-zero state; close tears down; single-
 * category summary skips the breakdown; per-difficulty breakdown + suppression;
 * window echo for a filtered view; a fetch error shows a note; independence from
 * the live stats bar. Drives the real module graph via boot.js and the boot-
 * wired stats-toggle, resetting the state singleton + re-booting per scenario
 * so each gets a clean panel and its own programmable /api/stats payload. */
const { makeDom, installFetch, installDefaultFetch, importModule, resetState, tick, makeChecker } = require("./_harness.js");

function makeBackend(ss) {
  return async function (url) {
    const j = (o, ok = true, s = 200) => ({ ok, status: s, async json() { return o; }, async text() { return JSON.stringify(o); } });
    if (url === "/api/categories") return j({ categories: [{ id: 1, name: "arithmetic", description: "", config: {} }, { id: 2, name: "vocabulary", description: "", config: {} }] });
    if (url === "/api/banks") return j({ banks: [] });
    if (url === "/api/difficulty-rungs") return j({ rungs: [] });
    if (url === "/api/session/start") return j({ session_id: 1 });
    if (url === "/api/session/end") return j({ ended: true });
    if (url.indexOf("/api/question") === 0) return j({ qtype: "arithmetic", question_text: "1 + 1", expected: "2", question_id: null, alternatives: null, media_url: null });
    if (url === "/api/answer") return j({ correct: true, expected: "2", user_input: "2", session_stats: { total: 1, correct: 1, accuracy: 1.0, streak: 1 } });
    if (url === "/api/stats") {
      if (ss.fail) return j({ error: "stats boom" }, false, 500);
      return j(ss.next);
    }
    return j({ error: "unexpected " + url }, false, 404);
  };
}

(async () => {
  const c = makeChecker();
  const { window: win, document: doc } = makeDom({});
  installDefaultFetch(win);
  const boot = await importModule("boot.js");
  const { state } = await importModule("state.js");

  const ss = { next: null, fail: false };
  installFetch(win, makeBackend(ss));

  /* Reset + re-boot; set the stats payload for the upcoming open. The DOM
     persists across scenarios (one fixture), so reset the panel/toggle DOM the
     way a fresh JSDOM did classically -- onStatsToggle reads open-state off the
     toggle's aria-expanded, so a stale "true" from a prior scenario would make
     the next click CLOSE instead of open. */
  async function scenario(statsNext, opts) {
    ss.next = statsNext;
    ss.fail = !!(opts && opts.fail);
    const toggle = doc.getElementById("stats-toggle");
    const panel = doc.getElementById("stats-panel");
    toggle.setAttribute("aria-expanded", "false");
    panel.hidden = true;
    panel.textContent = "";
    resetState(state);
    await boot.boot();
    await tick(100);
  }

  /* -- Test 1: open renders overall + breakdown -------------------------- */
  console.log("Test 1: open fetches and renders");
  {
    await scenario({
      total: 10, correct: 8, accuracy: 0.8,
      categories: [
        { category_id: 1, category_name: "arithmetic", total: 7, correct: 6, accuracy: 6 / 7 },
        { category_id: 2, category_name: "vocabulary", total: 3, correct: 2, accuracy: 2 / 3 }
      ],
      window: { category_id: null, days: null, since: null }
    });
    const toggle = doc.getElementById("stats-toggle");
    const panel = doc.getElementById("stats-panel");
    c.ck("panel hidden initially", panel.hidden === true);
    toggle.click();
    await tick(50);
    c.ck("panel shown after open", panel.hidden === false);
    c.ck("aria-expanded true", toggle.getAttribute("aria-expanded") === "true");
    const text = panel.textContent;
    const figMap = {};
    panel.querySelectorAll(".stats-overall .stats-figure").forEach(f => { figMap[f.querySelector("span").textContent] = f.querySelector("b").textContent; });
    c.ck("shows total 10 (answered)", figMap["answered"] === "10", JSON.stringify(figMap));
    c.ck("shows accuracy 80%", figMap["accuracy"] === "80%", JSON.stringify(figMap));
    c.ck("shows correct 8", figMap["correct"] === "8", JSON.stringify(figMap));
    c.ck("breakdown lists arithmetic", text.indexOf("arithmetic") !== -1);
    c.ck("breakdown lists vocabulary", text.indexOf("vocabulary") !== -1);
    c.ck("breakdown has By category title", text.indexOf("By category") !== -1);
    c.ck("no window note when unfiltered", panel.querySelector(".stats-window") === null);
    c.ck("live stats bar untouched (separate source)", doc.getElementById("stat-total").textContent === "0", doc.getElementById("stat-total").textContent);
  }

  /* -- Test 2: empty/time-zero state ------------------------------------- */
  console.log("Test 2: empty state");
  {
    await scenario({ total: 0, correct: 0, accuracy: 0.0, categories: [], window: { category_id: null, days: null, since: null } });
    doc.getElementById("stats-toggle").click();
    await tick(50);
    const text = doc.getElementById("stats-panel").textContent;
    c.ck("empty note shown", text.toLowerCase().indexOf("no answers recorded") !== -1, text);
    c.ck("no breakdown rows when empty", doc.getElementById("stats-panel").querySelector(".stats-row") === null);
  }

  /* -- Test 3: close tears down ------------------------------------------ */
  console.log("Test 3: close tears down");
  {
    await scenario({ total: 3, correct: 3, accuracy: 1.0, categories: [{ category_id: 1, category_name: "arithmetic", total: 3, correct: 3, accuracy: 1.0 }], window: { category_id: null, days: null, since: null } });
    const toggle = doc.getElementById("stats-toggle");
    const panel = doc.getElementById("stats-panel");
    toggle.click(); await tick(50);
    c.ck("open populated panel", panel.textContent.length > 0);
    toggle.click(); await tick(20);
    c.ck("panel hidden after close", panel.hidden === true);
    c.ck("panel emptied after close", panel.textContent === "");
    c.ck("aria-expanded false after close", toggle.getAttribute("aria-expanded") === "false");
  }

  /* -- Test 4: single category skips breakdown --------------------------- */
  console.log("Test 4: single category, no breakdown");
  {
    await scenario({ total: 5, correct: 4, accuracy: 0.8, categories: [{ category_id: 1, category_name: "arithmetic", total: 5, correct: 4, accuracy: 0.8 }], window: { category_id: null, days: null, since: null } });
    doc.getElementById("stats-toggle").click();
    await tick(50);
    const panel = doc.getElementById("stats-panel");
    c.ck("overall shown for single category", panel.textContent.indexOf("80%") !== -1);
    c.ck("no 'By category' for single category", panel.textContent.indexOf("By category") === -1);
  }

  /* -- Test 5: window echo for a filtered view --------------------------- */
  console.log("Test 5: window echo");
  {
    await scenario({ total: 4, correct: 4, accuracy: 1.0, categories: [{ category_id: 2, category_name: "vocabulary", total: 4, correct: 4, accuracy: 1.0 }], window: { category_id: 2, days: 7, since: "2024-01-01T00:00:00+00:00" } });
    doc.getElementById("stats-toggle").click();
    await tick(50);
    const winNote = doc.getElementById("stats-panel").querySelector(".stats-window");
    c.ck("window note present when filtered", winNote !== null);
    c.ck("window note names last 7 days", winNote && winNote.textContent.indexOf("last 7 days") !== -1, winNote && winNote.textContent);
    c.ck("window note names category", winNote && winNote.textContent.indexOf("vocabulary") !== -1, winNote && winNote.textContent);
  }

  /* -- Test 6: fetch error shows a note ---------------------------------- */
  console.log("Test 6: fetch error");
  {
    await scenario(null, { fail: true });
    doc.getElementById("stats-toggle").click();
    await tick(50);
    const text = doc.getElementById("stats-panel").textContent;
    c.ck("error note shown", text.toLowerCase().indexOf("could not load stats") !== -1, text);
  }

  /* -- Test 7: per-difficulty breakdown renders (C-D2i-3) ---------------- */
  console.log("Test 7: By difficulty breakdown");
  {
    await scenario({
      total: 5, correct: 3, accuracy: 0.6,
      categories: [{ category_id: 1, category_name: "arithmetic", total: 5, correct: 3, accuracy: 0.6 }],
      difficulty_breakdown: [
        { key: 2, label: "2 leaves", total: 3, correct: 2, accuracy: 2 / 3 },
        { key: 4, label: "4 leaves", total: 2, correct: 1, accuracy: 0.5 }
      ],
      window: { category_id: null, days: null, since: null }
    });
    doc.getElementById("stats-toggle").click();
    await tick(50);
    const text = doc.getElementById("stats-panel").textContent;
    c.ck("has 'By difficulty' title", text.indexOf("By difficulty") !== -1, text);
    c.ck("lists 2 leaves bucket", text.indexOf("2 leaves") !== -1);
    c.ck("lists 4 leaves bucket", text.indexOf("4 leaves") !== -1);
    c.ck("By category suppressed for single category", text.indexOf("By category") === -1);
  }

  /* -- Test 8: single difficulty bucket is suppressed -------------------- */
  console.log("Test 8: single difficulty bucket suppressed");
  {
    await scenario({
      total: 3, correct: 3, accuracy: 1.0,
      categories: [{ category_id: 1, category_name: "arithmetic", total: 3, correct: 3, accuracy: 1.0 }],
      difficulty_breakdown: [{ key: 2, label: "2 leaves", total: 3, correct: 3, accuracy: 1.0 }],
      window: { category_id: null, days: null, since: null }
    });
    doc.getElementById("stats-toggle").click();
    await tick(50);
    const text = doc.getElementById("stats-panel").textContent;
    c.ck("By difficulty suppressed for single bucket", text.indexOf("By difficulty") === -1, text);
  }

  /* -- Test 9: absent difficulty_breakdown is harmless ------------------- */
  console.log("Test 9: missing difficulty_breakdown");
  {
    await scenario({
      total: 4, correct: 4, accuracy: 1.0,
      categories: [
        { category_id: 1, category_name: "arithmetic", total: 2, correct: 2, accuracy: 1.0 },
        { category_id: 2, category_name: "vocabulary", total: 2, correct: 2, accuracy: 1.0 }
      ],
      window: { category_id: null, days: null, since: null }
    });
    doc.getElementById("stats-toggle").click();
    await tick(50);
    const text = doc.getElementById("stats-panel").textContent;
    c.ck("renders without difficulty_breakdown key", text.indexOf("By category") !== -1, text);
    c.ck("no By difficulty when key absent", text.indexOf("By difficulty") === -1);
  }

  c.done();
})().catch(e => { console.error(e); process.exit(2); });
