"use strict";
/* C-018a contract test: drive the real index.html in jsdom with stubbed
   fetch + speechSynthesis. Verifies the speaker shows only for language
   questions on a language bank, speaks the prompt with the bank language,
   cancels speech across transitions / session end / unload, blurs after
   speak (Space-to-advance protection), and degrades when speech is absent. */
const fs = require("fs");
const { JSDOM } = require("jsdom");

const html = fs.readFileSync("index.html", "utf8");

let pass = 0, fail = 0;
function check(name, cond) {
  if (cond) { pass++; console.log("  ok  - " + name); }
  else { fail++; console.log("  FAIL- " + name); }
}

/* ---- Fake backend ----------------------------------------------------- */
/* Categories: arithmetic (id 1) + vocabulary (id 2). Banks: spanish (id 10,
   language "es") under vocabulary, and a no-language trivia bank (id 11)
   under a "trivia" category (id 3). Question feed is scripted per test. */
function makeFetch(questionQueue) {
  return async function (url, opts) {
    function json(obj, ok = true, status = 200) {
      return {
        ok, status,
        async json() { return obj; },
        async text() { return JSON.stringify(obj); }
      };
    }
    if (url === "/api/categories") {
      return json({ categories: [
        { id: 1, name: "arithmetic", description: "", config: {} },
        { id: 2, name: "vocabulary", description: "", config: {} },
        { id: 3, name: "trivia", description: "", config: {} }
      ]});
    }
    if (url === "/api/banks") {
      return json({ banks: [
        { id: 10, category_id: 2, name: "spanish", language: "es",
          source: "import", metadata: {}, created: "2024-01-01T00:00:00Z" },
        { id: 11, category_id: 3, name: "capitals", language: null,
          source: "import", metadata: {}, created: "2024-01-01T00:00:00Z" }
      ]});
    }
    if (url.indexOf("/api/session/start") === 0
        || (opts && opts.method === "POST" && url === "/api/session/start")) {
      return json({ session_id: 99 });
    }
    if (url === "/api/session/end") { return json({ ended: true }); }
    if (url.indexOf("/api/question") === 0) {
      const next = questionQueue.shift() || {
        qtype: "arithmetic", question_text: "1 + 1", expected: "2",
        question_id: null, alternatives: null, media_url: null
      };
      return json(next);
    }
    if (url === "/api/answer") {
      return json({ correct: true, expected: "x", user_input: "x",
        session_stats: { total: 1, correct: 1, accuracy: 1.0, streak: 1 } });
    }
    return json({ error: "unexpected " + url }, false, 404);
  };
}

/* ---- Fake speechSynthesis (records calls) ----------------------------- */
function installSpeech(win, present) {
  const log = { speak: [], cancel: 0 };
  if (!present) {
    delete win.speechSynthesis;
    delete win.SpeechSynthesisUtterance;
    return log;
  }
  win.SpeechSynthesisUtterance = function (text) {
    this.text = text; this.lang = ""; this.onend = null; this.onerror = null;
  };
  win.speechSynthesis = {
    speak(u) { log.speak.push({ text: u.text, lang: u.lang }); },
    cancel() { log.cancel++; }
  };
  return log;
}

async function tick(ms) { return new Promise(r => setTimeout(r, ms || 30)); }

async function bootDom(opts) {
  const questionQueue = (opts.questions || []).slice();
  const dom = new JSDOM(html, {
    runScripts: "dangerously",
    pretendToBeVisual: true,
    beforeParse(win) {
      win.fetch = makeFetch(questionQueue);
      win.navigator.sendBeacon = function () { return true; };
      win.__log = installSpeech(win, opts.speechPresent !== false);
    }
  });
  /* Let DOMContentLoaded + the async boot() chain settle. */
  await tick(120);
  dom.__log = dom.window.__log;
  return dom;
}

(async function () {
  /* -- Test 1: language question (translate, es bank) shows speaker, speaks
        the prompt with lang "es", and blurs after click. ----------------- */
  console.log("Test 1: translate question on a language bank");
  {
    const dom = await bootDom({
      questions: [
        /* first question served is arithmetic (boot default selection) */
        { qtype: "arithmetic", question_text: "2 + 3", expected: "5",
          question_id: null, alternatives: null, media_url: null },
        /* after we switch to the spanish bank, this is served */
        { qtype: "translate", question_text: "gato", expected: "cat",
          question_id: 501, alternatives: [], media_url: null }
      ]
    });
    const win = dom.window, doc = win.document;
    const speaker = doc.getElementById("speaker");

    /* Initially arithmetic: speaker hidden. */
    check("speaker hidden on arithmetic", speaker.hidden === true);

    /* Switch selection to the spanish bank and load its question. We drive
       the app's own state + loadQuestion to mimic onBankChange's effect. */
    win.state.selection = { categoryId: 2, categoryName: "vocabulary",
                            bankId: 10, bankName: "spanish" };
    await win.loadQuestion();
    await tick(40);

    check("current qtype is translate", win.state.current.qtype === "translate");
    check("activeBankLanguage resolves to es", win.activeBankLanguage() === "es");
    check("canSpeakCurrent true for translate+es", win.canSpeakCurrent() === true);
    check("speaker visible on translate", speaker.hidden === false);

    /* Click the speaker: should speak "gato" with lang "es". */
    speaker.click();
    check("spoke once", winSpeechLog(dom).speak.length === 1);
    check("spoke the prompt text", winSpeechLog(dom).speak[0].text === "gato");
    check("spoke with lang es", winSpeechLog(dom).speak[0].lang === "es");
    check("speaker blurred after click",
          doc.activeElement !== speaker);

    dom.window.close();
  }

  /* -- Test 2: free_response / multiple_choice / identify gating --------- */
  console.log("Test 2: gating by qtype");
  {
    const dom = await bootDom({
      questions: [
        { qtype: "arithmetic", question_text: "1 + 1", expected: "2",
          question_id: null, alternatives: null, media_url: null }
      ]
    });
    const win = dom.window, doc = win.document;
    const speaker = doc.getElementById("speaker");
    win.state.selection = { categoryId: 2, categoryName: "vocabulary",
                            bankId: 10, bankName: "spanish" };

    /* free_response on a language bank: NOT spoken (English prompt). */
    win.state.current = { qtype: "free_response", question_text: "Capital?",
      expected: "x", question_id: 1, alternatives: [] };
    check("free_response not speakable", win.canSpeakCurrent() === false);

    /* multiple_choice: not spoken. */
    win.state.current = { qtype: "multiple_choice", question_text: "Q?",
      expected: "x", question_id: 2, alternatives: [], options: ["x","y"] };
    check("multiple_choice not speakable", win.canSpeakCurrent() === false);

    /* identify on a language bank: speakable. */
    win.state.current = { qtype: "identify", question_text: "esto",
      expected: "this", question_id: 3, alternatives: [] };
    check("identify speakable on language bank", win.canSpeakCurrent() === true);

    /* translate on a NO-language bank (trivia/capitals id 11): not speakable. */
    win.state.selection = { categoryId: 3, categoryName: "trivia",
                            bankId: 11, bankName: "capitals" };
    win.state.current = { qtype: "translate", question_text: "x",
      expected: "y", question_id: 4, alternatives: [] };
    check("null-language bank not speakable", win.canSpeakCurrent() === false);
    check("activeBankLanguage null for null bank",
          win.activeBankLanguage() === null);

    dom.window.close();
  }

  /* -- Test 3: speech cancelled across transition + session end + unload - */
  console.log("Test 3: stale-speech cancellation");
  {
    const dom = await bootDom({
      questions: [
        { qtype: "arithmetic", question_text: "4 + 4", expected: "8",
          question_id: null, alternatives: null, media_url: null },
        { qtype: "translate", question_text: "perro", expected: "dog",
          question_id: 502, alternatives: [], media_url: null },
        { qtype: "translate", question_text: "casa", expected: "house",
          question_id: 503, alternatives: [], media_url: null }
      ]
    });
    const win = dom.window, doc = win.document;
    win.state.selection = { categoryId: 2, categoryName: "vocabulary",
                            bankId: 10, bankName: "spanish" };
    await win.loadQuestion(); /* serves "perro" */
    await tick(30);
    const cancelsBefore = winSpeechLog(dom).cancel;
    doc.getElementById("speaker").click(); /* speak perro */
    await win.loadQuestion(); /* transition -> should cancel */
    await tick(30);
    check("loadQuestion cancelled speech",
          winSpeechLog(dom).cancel > cancelsBefore);

    /* session end cancels. */
    const c1 = winSpeechLog(dom).cancel;
    await win.endSession(win.state.activeSessionId);
    check("endSession cancelled speech", winSpeechLog(dom).cancel > c1);

    /* unload cancels. */
    const c2 = winSpeechLog(dom).cancel;
    win.endSessionOnUnload();
    check("unload cancelled speech", winSpeechLog(dom).cancel > c2);

    dom.window.close();
  }

  /* -- Test 4: speech UNAVAILABLE -> button never shows, speak no-ops ----- */
  console.log("Test 4: SpeechSynthesis absent");
  {
    const dom = await bootDom({
      speechPresent: false,
      questions: [
        { qtype: "arithmetic", question_text: "1 + 1", expected: "2",
          question_id: null, alternatives: null, media_url: null }
      ]
    });
    const win = dom.window, doc = win.document;
    const speaker = doc.getElementById("speaker");
    win.state.selection = { categoryId: 2, categoryName: "vocabulary",
                            bankId: 10, bankName: "spanish" };
    win.state.current = { qtype: "translate", question_text: "luz",
      expected: "light", question_id: 5, alternatives: [] };
    check("speechAvailable false", win.speechAvailable === false);
    check("canSpeakCurrent false when unavailable",
          win.canSpeakCurrent() === false);
    win.updateSpeakerVisibility();
    check("speaker stays hidden when unavailable", speaker.hidden === true);
    /* speak() must not throw with no API present. */
    let threw = false;
    try { win.speak("luz", "es", function(){}); } catch (e) { threw = true; }
    check("speak() no-op does not throw", threw === false);

    dom.window.close();
  }

  console.log("\n" + pass + " passed, " + fail + " failed");
  process.exit(fail === 0 ? 0 : 1);
})().catch(e => { console.error(e); process.exit(2); });

/* The speech log is created in beforeParse and stored on opts.speechLog, but
   that closure is not reachable here; expose it via the window for the test
   by reading the recorded calls off our fake. We re-find it through the fake
   object we installed. */
function winSpeechLog(dom) {
  return dom.window.__log;
}
