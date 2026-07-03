"use strict";
/* difficulty.test.js -- MIGRATED to option (b) at the E10 cutover (was C-2U-b,
 * driving the real index.html via leaked globals).
 *
 * Imports the real module graph via boot.js (boot() populates the selector from
 * GET /api/difficulty-rungs and wires onDifficultyChange/onCategoryChange), then
 * drives the difficulty <select> via real DOM change events and reads the real
 * state.js. Asserts, unchanged: the selector populates (Default + 4 rungs); a
 * rung sets state.difficulty AND the next /api/question URL carries &difficulty=;
 * "Default" clears it; a difficulty change re-fetches but records NO /api/answer
 * (stats-safe discard); the active-rung badge shows/hides; switching to a
 * non-arithmetic category disables the control and clears the rung. */
const { makeDom, installFetch, importModule, tick, makeChecker } = require("./_harness.js");

const calls = [];
function fetchStub() {
  return async (url, opts) => {
    calls.push({ url, body: opts && opts.body ? JSON.parse(opts.body) : null });
    const j = (o, ok = true, s = 200) => ({ ok, status: s, async json() { return o; }, async text() { return JSON.stringify(o); } });
    if (url === "/api/categories") return j({ categories: [
      { id: 1, name: "arithmetic", description: "", config: {} },
      { id: 2, name: "vocabulary", description: "", config: {} }
    ] });
    if (url === "/api/banks") return j({ banks: [{ id: 11, name: "spanish", category_id: 2, language: "es" }] });
    if (url === "/api/session/start" || url.indexOf("/api/session/start") === 0) return j({ session_id: 7 });
    if (url === "/api/session/end") return j({ ended: true });
    if (url === "/api/difficulty-rungs") return j({ rungs: [
      { rung: 1, operator_depth: 1, recurse_probability: 0.0, max_result_value: null },
      { rung: 2, operator_depth: 2, recurse_probability: 0.5, max_result_value: null },
      { rung: 3, operator_depth: 2, recurse_probability: 0.7, max_result_value: null },
      { rung: 4, operator_depth: 3, recurse_probability: 0.7, max_result_value: 100000 }
    ] });
    if (url.indexOf("/api/question") === 0) {
      const m = url.match(/[?&]difficulty=(\d+)/);
      const served = m ? parseInt(m[1], 10) : null;
      return j({ qtype: "arithmetic", question_text: "6 + 7", expected: "13", question_id: null, alternatives: null, media_url: null, difficulty: served, leaf_count: 2 });
    }
    if (url === "/api/answer") return j({ correct: true, expected: "13", user_input: "13", session_stats: { total: 1, correct: 1, accuracy: 1.0, streak: 1 } });
    return j({ error: "x" }, false, 404);
  };
}

(async () => {
  const c = makeChecker();
  const { window: win, document: doc } = makeDom();
  installFetch(win, fetchStub());
  await importModule("boot.js");
  await tick(150);
  const { state } = await importModule("state.js");

  const diff = doc.getElementById("difficulty");

  /* --- population from the endpoint --- */
  c.ck("difficulty endpoint was fetched", calls.some(x => x.url === "/api/difficulty-rungs"));
  c.ck("first option is Default (empty value)", diff.options[0].value === "" && diff.options[0].textContent === "Default");
  c.ck("four rung options follow Default", diff.options.length === 5);
  c.ck("rung option value is the numeric rung", diff.options[1].value === "1");
  c.ck("rung label composed from facts (nested/ceiling)", diff.options[4].textContent.indexOf("Rung 4") === 0
    && diff.options[4].textContent.indexOf("nested") !== -1
    && diff.options[4].textContent.indexOf("100000") !== -1);
  c.ck("rung 1 reads as flat / any size", diff.options[1].textContent.indexOf("flat") !== -1
    && diff.options[1].textContent.indexOf("any size") !== -1);

  /* --- default state: null, no difficulty in URL --- */
  c.ck("state.difficulty starts null", state.difficulty === null);
  const qBefore = calls.filter(x => x.url.indexOf("/api/question") === 0).pop();
  c.ck("default question URL omits difficulty", qBefore && qBefore.url.indexOf("difficulty=") === -1);
  const badge = doc.getElementById("active-rung");
  c.ck("active-rung badge hidden on default path", badge.hidden === true);

  /* --- picking a rung sets state + next question URL carries it --- */
  const answersBefore = calls.filter(x => x.url === "/api/answer").length;
  diff.value = "3";
  diff.dispatchEvent(new win.Event("change"));
  await tick(60);
  c.ck("picking rung 3 sets state.difficulty", state.difficulty === 3);
  const qAfter = calls.filter(x => x.url.indexOf("/api/question") === 0).pop();
  c.ck("next question URL carries difficulty=3", qAfter && qAfter.url.indexOf("difficulty=3") !== -1);
  c.ck("difficulty change recorded NO answer (stats-safe discard)",
    calls.filter(x => x.url === "/api/answer").length === answersBefore);
  c.ck("active-rung badge visible for a non-default rung", badge.hidden === false);
  c.ck("active-rung badge names rung 3", badge.textContent.indexOf("Rung 3") === 0);

  /* --- "Default" clears it --- */
  diff.value = "";
  diff.dispatchEvent(new win.Event("change"));
  await tick(60);
  c.ck("Default clears state.difficulty to null", state.difficulty === null);
  const qDefault = calls.filter(x => x.url.indexOf("/api/question") === 0).pop();
  c.ck("Default question URL omits difficulty again", qDefault && qDefault.url.indexOf("difficulty=") === -1);
  c.ck("active-rung badge hidden again on Default", badge.hidden === true);

  /* --- non-arithmetic gating: control disabled, rung cleared --- */
  diff.value = "2";
  diff.dispatchEvent(new win.Event("change"));
  await tick(60);
  const cat = doc.getElementById("category");
  cat.value = "2";
  cat.dispatchEvent(new win.Event("change"));
  await tick(60);
  c.ck("difficulty disabled for non-arithmetic", diff.disabled === true);
  c.ck("difficulty note shown for non-arithmetic", doc.getElementById("difficulty-note").hidden === false);
  c.ck("switching away from arithmetic clears state.difficulty", state.difficulty === null);

  c.done();
})().catch(e => { console.error(e); process.exit(2); });
