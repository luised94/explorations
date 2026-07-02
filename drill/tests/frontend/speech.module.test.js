"use strict";
/* speech.module.test.js -- E5, option-(b) test for the speechSynthesis
 * quarantine. Drives the REAL speech.js (imports real state.js + el.js) with a
 * stubbed window.speechSynthesis + SpeechSynthesisUtterance and a fixture DOM.
 *
 * speechAvailable is computed at MODULE LOAD from window, so the harness
 * publishes the speech stubs BEFORE importing. To also cover the unavailable
 * path (which is likewise import-time), a SECOND import with a cache-busting
 * ?query re-evaluates the module against a window without speech (Node caches
 * dynamic imports by resolved URL; a distinct query forces re-evaluation).
 *
 * Same option-(b) harness as the other module tests (S1b/S1c): outside-only
 * DOM, publish globals, then dynamic import(). Exercises the real three-module
 * chain speech -> {state, el} under Node's loader.
 *
 * ASCII only.
 */
const path = require("path");
const { JSDOM } = require("jsdom");

let pass = 0, fail = 0;
const ck = (n, c) => { c ? (pass++, console.log("  ok  - " + n)) : (fail++, console.log("  FAIL- " + n)); };

/* A recording speechSynthesis stub + an Utterance class that captures handlers
   so the test can fire onend/onerror. */
function installSpeechStubs(win) {
  const log = { cancels: 0, spoken: [] };
  win.speechSynthesis = {
    cancel() { log.cancels++; },
    speak(u) { log.spoken.push(u); }
  };
  win.SpeechSynthesisUtterance = function (text) {
    this.text = text; this.lang = ""; this.onend = null; this.onerror = null;
  };
  return log;
}

(async () => {
  const dom = new JSDOM(
    "<!DOCTYPE html><html><body><button id='speaker'></button></body></html>",
    { runScripts: "outside-only", pretendToBeVisual: true }
  );
  global.window = dom.window;
  global.document = dom.window.document;
  const log = installSpeechStubs(dom.window);
  /* speak()/cancelSpeech() reach through the bare global `window`; jsdom's
     window is the same object we published, so the stubs are visible. */

  const mod = await import("file://" + path.resolve("speech.js"));
  ck("module imported without throwing", !!mod);
  ck("speechAvailable is true when stubs present", mod.speechAvailable === true);
  ck("exports the public surface",
    ["speak", "cancelSpeech", "activeBankLanguage", "canSpeakCurrent",
     "setSpeakerSpeaking", "onSpeakerClick", "updateSpeakerVisibility"]
      .every(n => typeof mod[n] === "function"));

  /* --- speak: cancels first, then speaks; fires onStateChange lifecycle -- */
  let states = [];
  mod.speak("hola", "es", (s) => states.push(s));
  ck("speak cancels any in-flight utterance first", log.cancels === 1);
  ck("speak enqueues one utterance", log.spoken.length === 1);
  ck("speak set the utterance text", log.spoken[0].text === "hola");
  ck("speak set the utterance lang", log.spoken[0].lang === "es");
  ck("speak fired onStateChange(true) at start", states[0] === true);
  /* fire the engine's end event -> onStateChange(false) */
  log.spoken[0].onend();
  ck("utterance onend fires onStateChange(false)", states[states.length - 1] === false);

  /* --- speak no-ops on empty text ---------------------------------------- */
  const before = log.spoken.length;
  mod.speak("", "es", () => {});
  ck("speak no-ops on empty text", log.spoken.length === before);

  /* --- cancelSpeech: cancels + clears speaking state --------------------- */
  const cBefore = log.cancels;
  let cleared = null;
  mod.cancelSpeech((s) => { cleared = s; });
  ck("cancelSpeech cancels the engine", log.cancels === cBefore + 1);
  ck("cancelSpeech fires onStateChange(false)", cleared === false);

  /* --- activeBankLanguage: resolves from state.selection + categories ---- */
  const st = mod === null ? null : (await import("file://" + path.resolve("state.js"))).state;
  st.selection = null;
  ck("no selection -> null language", mod.activeBankLanguage() === null);
  st.categories = [{ id: 9, banks: [{ id: 3, language: "es" }, { id: 4, language: null }] }];
  st.selection = { bankId: 3 };
  ck("bank with language resolves it", mod.activeBankLanguage() === "es");
  st.selection = { bankId: 4 };
  ck("bank with null language -> null", mod.activeBankLanguage() === null);
  st.selection = { bankId: 999 };
  ck("unknown bank -> null", mod.activeBankLanguage() === null);

  /* --- canSpeakCurrent: qtype gate + language gate ----------------------- */
  st.selection = { bankId: 3 };
  st.current = { qtype: "translate", question_text: "hola" };
  ck("translate with language -> speakable", mod.canSpeakCurrent() === true);
  st.current = { qtype: "identify", question_text: "hola" };
  ck("identify with language -> speakable", mod.canSpeakCurrent() === true);
  st.current = { qtype: "multiple_choice", question_text: "x" };
  ck("multiple_choice -> not speakable", mod.canSpeakCurrent() === false);
  st.current = null;
  ck("no current question -> not speakable", mod.canSpeakCurrent() === false);

  /* --- setSpeakerSpeaking: toggles the 'speaking' class ------------------ */
  const speaker = dom.window.document.getElementById("speaker");
  mod.setSpeakerSpeaking(true);
  ck("setSpeakerSpeaking(true) adds class", speaker.classList.contains("speaking") === true);
  mod.setSpeakerSpeaking(false);
  ck("setSpeakerSpeaking(false) removes class", speaker.classList.contains("speaking") === false);

  /* --- updateSpeakerVisibility: shows when speakable, hides + cancels else */
  st.selection = { bankId: 3 };
  st.current = { qtype: "translate", question_text: "hola" };
  speaker.hidden = true;
  mod.updateSpeakerVisibility();
  ck("visibility: shows speaker when speakable", speaker.hidden === false);
  const cancelsBefore = log.cancels;
  st.current = { qtype: "multiple_choice", question_text: "x" };
  mod.updateSpeakerVisibility();
  ck("visibility: hides speaker when not speakable", speaker.hidden === true);
  ck("visibility: cancels in-flight speech when hiding", log.cancels === cancelsBefore + 1);

  /* --- onSpeakerClick: speaks current prompt, then blurs ----------------- */
  st.selection = { bankId: 3 };
  st.current = { qtype: "translate", question_text: "buenos dias" };
  let blurred = false;
  speaker.blur = () => { blurred = true; };
  const spokenBefore = log.spoken.length;
  mod.onSpeakerClick();
  ck("click speaks the current prompt", log.spoken.length === spokenBefore + 1 &&
    log.spoken[log.spoken.length - 1].text === "buenos dias");
  ck("click blurs the speaker button", blurred === true);
  st.current = null;
  const spokenAfter = log.spoken.length;
  mod.onSpeakerClick();
  ck("click no-ops with no current question", log.spoken.length === spokenAfter);

  /* --- UNAVAILABLE path: re-evaluate the module against a speech-less window */
  delete dom.window.speechSynthesis;
  delete dom.window.SpeechSynthesisUtterance;
  const modU = await import("file://" + path.resolve("speech.js") + "?nospeech=1");
  ck("speechAvailable is false when stubs absent", modU.speechAvailable === false);
  /* speak/cancelSpeech become no-ops; canSpeakCurrent false regardless */
  let touched = false;
  modU.speak("x", "es", () => { touched = true; });
  ck("speak is a no-op when unavailable", touched === false);
  modU.setSpeakerSpeaking(true); /* still safe: el.speaker exists */
  ck("canSpeakCurrent false when unavailable", modU.canSpeakCurrent() === false);

  console.log("\n" + pass + " passed, " + fail + " failed");
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error(e); process.exit(2); });
