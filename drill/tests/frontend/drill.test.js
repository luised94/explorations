"use strict";
/* drill.test.js -- MIGRATED to option (b) at the E10 cutover.
 *
 * Was: load real index.html under jsdom (runScripts:"dangerously") and read
 * win.state / win.submitAnswer / win.questionQuery off the leaked globals.
 * Now: import the real module graph via boot.js (its boot-guard runs boot() ->
 * the drill<->session cycle loads the first arithmetic question), then drive
 * the real drill.js submitAnswer / questionQuery + read real state.js. Same
 * C-D2c contract: arithmetic renders; submit updates the stats bar + phase;
 * the /api/answer body echoes served difficulty + leaf_count; questionQuery
 * carries &difficulty= only when state.difficulty is set. */
const path = require("path");
const { makeDom, installFetch, importModule, tick, makeChecker } = require("./_harness.js");

const calls = [];
function fetchStub() {
  return async (url, opts) => {
    calls.push({ url, body: opts && opts.body ? JSON.parse(opts.body) : null });
    const j = (o, ok = true, s = 200) => ({ ok, status: s, async json() { return o; }, async text() { return JSON.stringify(o); } });
    if (url === "/api/categories") return j({ categories: [{ id: 1, name: "arithmetic", description: "", config: {} }] });
    if (url === "/api/banks") return j({ banks: [] });
    if (url === "/api/difficulty-rungs") return j({ rungs: [] });
    if (url === "/api/session/start" || url.indexOf("/api/session/start") === 0) return j({ session_id: 7 });
    if (url === "/api/session/end") return j({ ended: true });
    /* C-D2c: arithmetic question payload carries difficulty + leaf_count. */
    if (url.indexOf("/api/question") === 0) return j({ qtype: "arithmetic", question_text: "6 + 7", expected: "13", question_id: null, alternatives: null, media_url: null, difficulty: 3, leaf_count: 2 });
    if (url === "/api/answer") return j({ correct: true, expected: "13", user_input: "13", session_stats: { total: 1, correct: 1, accuracy: 1.0, streak: 1 } });
    return j({ error: "x" }, false, 404);
  };
}

(async () => {
  const c = makeChecker();
  const { document: doc } = makeDom();
  installFetch(window, fetchStub());

  /* Importing boot fires boot() -> populateCategories -> default arithmetic
     selection -> startSession -> loadQuestion (the cycle). Await its async
     body to settle. */
  await importModule("boot.js");
  await tick(120);

  const { state } = await importModule("state.js");
  const drill = await importModule("drill.js");

  c.ck("arithmetic question rendered", doc.getElementById("expression").textContent === "6 + 7");
  c.ck("speaker hidden on arithmetic", doc.getElementById("speaker").hidden === true);
  c.ck("answer input visible", doc.getElementById("answer-row").hidden === false);
  c.ck("phase answering", state.phase === "answering");

  /* submit an answer through the real drill.submitAnswer */
  doc.getElementById("answer").value = "13";
  await drill.submitAnswer();
  await tick(40);
  c.ck("stats total updated to 1", doc.getElementById("stat-total").textContent === "1");
  c.ck("feedback phase after submit", state.phase === "feedback");

  /* C-D2c: served difficulty + leaf_count are echoed on the /api/answer body. */
  const ans = calls.filter(x => x.url === "/api/answer").pop();
  c.ck("answer body echoes served difficulty", ans && ans.body && ans.body.difficulty === 3);
  c.ck("answer body echoes served leaf_count", ans && ans.body && ans.body.leaf_count === 2);

  /* C-D2c: question URL carries difficulty only when state.difficulty set. */
  const qNull = calls.filter(x => x.url.indexOf("/api/question") === 0).pop();
  c.ck("default question URL omits difficulty", qNull && qNull.url.indexOf("difficulty=") === -1);
  state.difficulty = 4;
  const built = drill.questionQuery();
  c.ck("questionQuery adds difficulty when set", built.indexOf("difficulty=4") !== -1);

  /* C-BIT-j: a base-2 payload shows the base badge and switches the expression
     to mono; a base-10 payload clears both (the default decimal path stays
     serif and unbadged). Drives the real drill.renderQuestion. */
  drill.renderQuestion({
    qtype: "arithmetic", question_text: "0b0101 & 0b0011", expected: "0b0001",
    base: 2, difficulty: null, leaf_count: 2
  });
  const badge = doc.getElementById("base-indicator");
  const expr = doc.getElementById("expression");
  c.ck("base badge shown for base 2", badge.hidden === false);
  c.ck("base badge names Binary", badge.textContent === "Binary");
  c.ck("expression is mono for base 2", expr.classList.contains("mono") === true);

  drill.renderQuestion({
    qtype: "arithmetic", question_text: "6 + 7", expected: "13",
    base: 10, difficulty: null, leaf_count: 2
  });
  c.ck("base badge hidden for base 10", badge.hidden === true);
  c.ck("expression not mono for base 10", expr.classList.contains("mono") === false);

  c.done();
})().catch(e => { console.error(e); process.exit(2); });
