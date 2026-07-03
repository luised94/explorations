"use strict";
/* speech.test.js -- MIGRATED to option (b) at the E10 cutover (was the C-018a
 * contract test driving the real inline page via leaked globals).
 *
 * Verifies the speaker shows only for language questions on a language bank,
 * speaks the prompt with the bank language, cancels speech across transitions /
 * session end / unload, blurs after speak (Space-to-advance protection), and
 * degrades when speech is absent. Tests 1-3 drive the real module graph via
 * boot.js (resetting the state singleton between scenarios). Test 4 needs
 * speech.js RE-EVALUATED against a window with no SpeechSynthesis (speechAvailable
 * is import-time), so it uses a separate speech-absent DOM + a cache-busted
 * import of speech.js in isolation -- the pattern speech.module.test.js models. */
const { makeDom, installFetch, installDefaultFetch, importModule, resetState, tick, makeChecker } = require("./_harness.js");

function makeFetch(bs) {
  return async function (url, opts) {
    const j = (o, ok = true, s = 200) => ({ ok, status: s, async json() { return o; }, async text() { return JSON.stringify(o); } });
    if (url === "/api/categories") return j({ categories: [
      { id: 1, name: "arithmetic", description: "", config: {} },
      { id: 2, name: "vocabulary", description: "", config: {} },
      { id: 3, name: "trivia", description: "", config: {} }
    ] });
    if (url === "/api/banks") return j({ banks: [
      { id: 10, category_id: 2, name: "spanish", language: "es", source: "import", metadata: {}, created: "2024-01-01T00:00:00Z" },
      { id: 11, category_id: 3, name: "capitals", language: null, source: "import", metadata: {}, created: "2024-01-01T00:00:00Z" }
    ] });
    if (url === "/api/difficulty-rungs") return j({ rungs: [] });
    if (url.indexOf("/api/session/start") === 0 || (opts && opts.method === "POST" && url === "/api/session/start")) return j({ session_id: 99 });
    if (url === "/api/session/end") return j({ ended: true });
    if (url.indexOf("/api/question") === 0) {
      const next = bs.questions.shift() || { qtype: "arithmetic", question_text: "1 + 1", expected: "2", question_id: null, alternatives: null, media_url: null };
      return j(next);
    }
    if (url === "/api/answer") return j({ correct: true, expected: "x", user_input: "x", session_stats: { total: 1, correct: 1, accuracy: 1.0, streak: 1 } });
    return j({ error: "unexpected " + url }, false, 404);
  };
}

(async () => {
  const c = makeChecker();

  /* Shared graph for Tests 1-3 (speech present). */
  const { window: win, document: doc, } = makeDom({});
  installDefaultFetch(win);
  const speechLog = win.__harnessSpeechLog = { speak: [], cancel: 0 };
  /* Re-point the harness speech stubs at a log this test can read. */
  win.SpeechSynthesisUtterance = function (t) { this.text = t; this.lang = ""; this.onend = null; this.onerror = null; };
  win.speechSynthesis = { speak(u) { speechLog.speak.push({ text: u.text, lang: u.lang }); }, cancel() { speechLog.cancel++; } };

  const boot = await importModule("boot.js");
  const { state } = await importModule("state.js");
  const drill = await importModule("drill.js");
  const speech = await importModule("speech.js");
  const session = await importModule("session.js");

  async function scenario(questions) {
    const bs = { questions: questions.slice() };
    resetState(state);
    speechLog.speak.length = 0; speechLog.cancel = 0;
    installFetch(win, makeFetch(bs));
    await boot.boot();
    await tick(100);
    return bs;
  }

  /* -- Test 1: translate question on a language bank --------------------- */
  console.log("Test 1: translate question on a language bank");
  {
    await scenario([
      { qtype: "arithmetic", question_text: "2 + 3", expected: "5", question_id: null, alternatives: null, media_url: null },
      { qtype: "translate", question_text: "gato", expected: "cat", question_id: 501, alternatives: [], media_url: null }
    ]);
    const speaker = doc.getElementById("speaker");
    c.ck("speaker hidden on arithmetic", speaker.hidden === true);

    state.selection = { categoryId: 2, categoryName: "vocabulary", bankId: 10, bankName: "spanish" };
    await drill.loadQuestion();
    await tick(40);
    c.ck("current qtype is translate", state.current.qtype === "translate");
    c.ck("activeBankLanguage resolves to es", speech.activeBankLanguage() === "es");
    c.ck("canSpeakCurrent true for translate+es", speech.canSpeakCurrent() === true);
    c.ck("speaker visible on translate", speaker.hidden === false);

    speaker.click();
    c.ck("spoke once", speechLog.speak.length === 1);
    c.ck("spoke the prompt text", speechLog.speak[0].text === "gato");
    c.ck("spoke with lang es", speechLog.speak[0].lang === "es");
    c.ck("speaker blurred after click", doc.activeElement !== speaker);
  }

  /* -- Test 2: gating by qtype ------------------------------------------- */
  console.log("Test 2: gating by qtype");
  {
    await scenario([{ qtype: "arithmetic", question_text: "1 + 1", expected: "2", question_id: null, alternatives: null, media_url: null }]);
    state.selection = { categoryId: 2, categoryName: "vocabulary", bankId: 10, bankName: "spanish" };

    state.current = { qtype: "free_response", question_text: "Capital?", expected: "x", question_id: 1, alternatives: [] };
    c.ck("free_response not speakable", speech.canSpeakCurrent() === false);
    state.current = { qtype: "multiple_choice", question_text: "Q?", expected: "x", question_id: 2, alternatives: [], options: ["x", "y"] };
    c.ck("multiple_choice not speakable", speech.canSpeakCurrent() === false);
    state.current = { qtype: "identify", question_text: "esto", expected: "this", question_id: 3, alternatives: [] };
    c.ck("identify speakable on language bank", speech.canSpeakCurrent() === true);

    state.selection = { categoryId: 3, categoryName: "trivia", bankId: 11, bankName: "capitals" };
    state.current = { qtype: "translate", question_text: "x", expected: "y", question_id: 4, alternatives: [] };
    c.ck("null-language bank not speakable", speech.canSpeakCurrent() === false);
    c.ck("activeBankLanguage null for null bank", speech.activeBankLanguage() === null);
  }

  /* -- Test 3: stale-speech cancellation --------------------------------- */
  console.log("Test 3: stale-speech cancellation");
  {
    await scenario([
      { qtype: "arithmetic", question_text: "4 + 4", expected: "8", question_id: null, alternatives: null, media_url: null },
      { qtype: "translate", question_text: "perro", expected: "dog", question_id: 502, alternatives: [], media_url: null },
      { qtype: "translate", question_text: "casa", expected: "house", question_id: 503, alternatives: [], media_url: null }
    ]);
    state.selection = { categoryId: 2, categoryName: "vocabulary", bankId: 10, bankName: "spanish" };
    await drill.loadQuestion(); /* serves perro */
    await tick(30);
    const cancelsBefore = speechLog.cancel;
    doc.getElementById("speaker").click(); /* speak perro */
    await drill.loadQuestion(); /* transition -> should cancel */
    await tick(30);
    c.ck("loadQuestion cancelled speech", speechLog.cancel > cancelsBefore);

    const c1 = speechLog.cancel;
    await session.endSession(state.activeSessionId);
    c.ck("endSession cancelled speech", speechLog.cancel > c1);

    const c2 = speechLog.cancel;
    session.endSessionOnUnload();
    c.ck("unload cancelled speech", speechLog.cancel > c2);
  }

  /* -- Test 4: SpeechSynthesis absent (isolated re-import) ---------------- */
  console.log("Test 4: SpeechSynthesis absent");
  {
    /* speechAvailable is computed at speech.js load from window. Build a DOM
       WITHOUT speech and re-evaluate speech.js under a cache-bust token so
       speechAvailable is false. speech.js's internal `import "./el.js"` is
       UNBUSTED, so speech4 shares the same `el` instance imported below; we read
       the speaker through THAT el (not a divergent busted copy) to observe
       updateSpeakerVisibility's effect. global.document now points at win4, and
       el caches lazily per id, so el.speaker resolves win4's speaker on first
       read here (the Tests 1-3 graph never accessed el.speaker via this path in
       a way that poisons the cache for win4 -- but to be safe we assert on the
       exact node el returns). */
    const { window: win4 } = makeDom({ speechPresent: false });
    const speech4 = await importModule("speech.js", "absent");
    const { state: state4 } = await importModule("state.js", "absent");
    const { el } = await importModule("el.js"); /* unbusted: the instance speech4 uses */
    state4.selection = { categoryId: 2, categoryName: "vocabulary", bankId: 10, bankName: "spanish" };
    state4.categories = [{ id: 2, name: "vocabulary", banks: [{ id: 10, language: "es" }] }];
    state4.current = { qtype: "translate", question_text: "luz", expected: "light", question_id: 5, alternatives: [] };
    c.ck("speechAvailable false", speech4.speechAvailable === false);
    c.ck("canSpeakCurrent false when unavailable", speech4.canSpeakCurrent() === false);
    speech4.updateSpeakerVisibility();
    c.ck("speaker stays hidden when unavailable", el.speaker.hidden === true);
    let threw = false;
    try { speech4.speak("luz", "es", function () {}); } catch (e) { threw = true; }
    c.ck("speak() no-op does not throw", threw === false);
  }

  c.done();
})().catch(e => { console.error(e); process.exit(2); });
