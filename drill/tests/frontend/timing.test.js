"use strict";
/* timing.test.js -- MIGRATED to option (b) at the E10 cutover (was the C-018c
 * contract test driving the real inline page via leaked globals).
 *
 * elapsed_ms is collected on the frontend and sent in the /api/answer body.
 * Verifies: a typed submit sends a sane elapsed_ms; an MC choice submit sends
 * one; retry-after-error re-times (mark resets so the second attempt is measured,
 * not the first); an empty submit does NOT consume/clear the mark. nowMs() reads
 * the global performance.now, so the harness injects a controllable clock via
 * global.performance.
 *
 * ISOLATION: modules are per-process singletons and boot.js's internal
 * `import "./state.js"` always resolves to the unbusted url, so a per-scenario
 * cache-bust cannot give boot a fresh state. We therefore import ONCE (unbusted),
 * and between scenarios reset the state singleton + re-run boot.boot() against a
 * fresh fetch queue and a re-baselined clock. */
const { makeDom, installFetch, installDefaultFetch, importModule, resetState, tick, makeChecker } = require("./_harness.js");

function makeClock() { let t = 1000; return { now() { return t; }, advance(ms) { t += ms; }, set(v) { t = v; } }; }

function makeBackend(bs) {
  return async function (url, opts) {
    const j = (o, ok = true, s = 200) => ({ ok, status: s, async json() { return o; }, async text() { return JSON.stringify(o); } });
    if (url === "/api/categories") return j({ categories: [{ id: 1, name: "arithmetic", description: "", config: {} }, { id: 2, name: "vocabulary", description: "", config: {} }] });
    if (url === "/api/banks") return j({ banks: [{ id: 10, category_id: 2, name: "es", language: "es", source: "import", metadata: {}, created: "2024-01-01T00:00:00Z" }] });
    if (url === "/api/difficulty-rungs") return j({ rungs: [] });
    if (url === "/api/session/start") return j({ session_id: 42 });
    if (url === "/api/session/end") return j({ ended: true });
    if (url.indexOf("/api/question") === 0) {
      const next = bs.questions.shift() || { qtype: "arithmetic", question_text: "1 + 1", expected: "2", question_id: null, alternatives: null, media_url: null };
      return j(next);
    }
    if (url === "/api/answer") {
      const body = JSON.parse(opts.body);
      bs.answerBodies.push(body);
      if (bs.failNext > 0) { bs.failNext--; return j({ error: "boom" }, false, 500); }
      return j({ correct: true, expected: body.expected, user_input: body.user_input, session_stats: { total: bs.answerBodies.length, correct: 1, accuracy: 1.0, streak: 1 } });
    }
    return j({ error: "unexpected " + url }, false, 404);
  };
}

(async () => {
  const c = makeChecker();
  const clock = makeClock();
  const { window: win, document: doc } = makeDom({ clock });
  installDefaultFetch(win);
  const boot = await importModule("boot.js");
  const { state } = await importModule("state.js");
  const drill = await importModule("drill.js");

  /* Fresh scenario: reset state, re-baseline clock, install a fetch queue, run boot(). */
  async function scenario(questions) {
    const bs = { questions: questions.slice(), answerBodies: [], failNext: 0 };
    resetState(state);
    clock.set(1000);
    installFetch(win, makeBackend(bs));
    await boot.boot();
    await tick(100);
    return bs;
  }

  /* -- Test 1: typed arithmetic submit sends elapsed_ms ------------------- */
  console.log("Test 1: typed submit sends elapsed_ms");
  {
    const bs = await scenario([{ qtype: "arithmetic", question_text: "2 + 2", expected: "4", question_id: null, alternatives: null, media_url: null }]);
    c.ck("phase answering after boot", state.phase === "answering");
    c.ck("mark set on enterAnswering", typeof state.answerStartMark === "number");
    clock.advance(2500);
    doc.getElementById("answer").value = "4";
    await drill.submitAnswer();
    await tick(40);
    const body = bs.answerBodies[0];
    c.ck("answer body recorded", !!body);
    c.ck("elapsed_ms present", body && typeof body.elapsed_ms === "number", JSON.stringify(body));
    c.ck("elapsed_ms == 2500", body && body.elapsed_ms === 2500, body && String(body.elapsed_ms));
    c.ck("mark cleared after submit", state.answerStartMark === null);
  }

  /* -- Test 2: MC choice submit sends elapsed_ms -------------------------- */
  console.log("Test 2: multiple_choice submit sends elapsed_ms");
  {
    const bs = await scenario([
      { qtype: "arithmetic", question_text: "1 + 1", expected: "2", question_id: null, alternatives: null, media_url: null },
      { qtype: "multiple_choice", question_text: "Capital of France?", expected: "Paris", question_id: 7, alternatives: [], media_url: null, options: ["Paris", "Lyon", "Nice"] }
    ]);
    state.selection = { categoryId: 2, categoryName: "vocabulary", bankId: 10, bankName: "es" };
    await drill.loadQuestion();
    await tick(40);
    c.ck("MC rendered", state.current.qtype === "multiple_choice");
    c.ck("mark set for MC", typeof state.answerStartMark === "number");
    clock.advance(1800);
    const firstChoice = doc.querySelector(".choice");
    c.ck("choice button exists", !!firstChoice);
    firstChoice.click();
    await tick(40);
    const body = bs.answerBodies[bs.answerBodies.length - 1];
    c.ck("MC elapsed_ms == 1800", body && body.elapsed_ms === 1800, body && String(body.elapsed_ms));
  }

  /* -- Test 3: retry after error re-times (mark resets) ------------------- */
  console.log("Test 3: retry-after-error re-times");
  {
    const bs = await scenario([{ qtype: "arithmetic", question_text: "3 + 3", expected: "6", question_id: null, alternatives: null, media_url: null }]);
    bs.failNext = 1;
    clock.advance(5000);
    doc.getElementById("answer").value = "6";
    await drill.submitAnswer();
    await tick(40);
    c.ck("first (failed) attempt recorded a body", bs.answerBodies.length === 1);
    c.ck("failed attempt elapsed ~5000", bs.answerBodies[0].elapsed_ms === 5000);
    c.ck("back in answering after failure", state.phase === "answering");
    c.ck("mark restarted (not null)", typeof state.answerStartMark === "number");
    clock.advance(900);
    doc.getElementById("answer").value = "6";
    await drill.submitAnswer();
    await tick(40);
    const ok = bs.answerBodies[bs.answerBodies.length - 1];
    c.ck("retry succeeded recorded", bs.answerBodies.length === 2);
    c.ck("successful attempt elapsed == 900 (NOT 5900)", ok.elapsed_ms === 900, String(ok.elapsed_ms));
  }

  /* -- Test 4: empty submit does not consume/clear the mark --------------- */
  console.log("Test 4: empty submit keeps the timer running");
  {
    const bs = await scenario([{ qtype: "arithmetic", question_text: "9 + 1", expected: "10", question_id: null, alternatives: null, media_url: null }]);
    const markBefore = state.answerStartMark;
    clock.advance(1200);
    doc.getElementById("answer").value = "";
    await drill.submitAnswer();
    await tick(20);
    c.ck("no answer POST on empty submit", bs.answerBodies.length === 0);
    c.ck("mark unchanged after empty submit", state.answerStartMark === markBefore, String(state.answerStartMark));
    clock.advance(800);
    doc.getElementById("answer").value = "10";
    await drill.submitAnswer();
    await tick(40);
    const body = bs.answerBodies[0];
    c.ck("elapsed counts from question start (==2000)", body && body.elapsed_ms === 2000, body && String(body.elapsed_ms));
  }

  c.done();
})().catch(e => { console.error(e); process.exit(2); });
