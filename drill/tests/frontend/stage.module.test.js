"use strict";
/* stage.module.test.js -- E4, option-(b) test for the relocated stage helpers.
 *
 * Drives the REAL stage.js (which imports the real el.js) against a fixture DOM
 * and asserts the exact DOM effects of each relocated function, unchanged from
 * the inline script. Same option-(b) harness as the other module tests
 * (S1b/S1c): outside-only DOM, publish window+document, then dynamic import().
 *
 * stage.js imports el from ./el.js, so this test also exercises the real
 * two-module import chain (stage -> el) under Node's loader -- the first time
 * two extracted frontend modules are wired together (still isolated from the
 * inline script; nothing imports either until E10).
 *
 * ASCII only.
 */
const path = require("path");
const { JSDOM } = require("jsdom");

let pass = 0, fail = 0;
const ck = (n, c) => { c ? (pass++, console.log("  ok  - " + n)) : (fail++, console.log("  FAIL- " + n)); };

(async () => {
  const dom = new JSDOM(
    "<!DOCTYPE html><html><body>" +
    "<div id='note'></div>" +
    "<div id='answer-hint'></div>" +
    "<div id='choices'></div>" +
    "<div id='feedback'></div>" +
    "</body></html>",
    { runScripts: "outside-only", pretendToBeVisual: true }
  );
  global.window = dom.window;
  global.document = dom.window.document;
  const doc = dom.window.document;

  const mod = await import("file://" + path.resolve("stage.js"));
  ck("module imported without throwing", !!mod);
  ck("exports the six helpers",
    ["setNote", "setAnswerHint", "clearAnswerHint", "clearChoices", "clearAnd", "clearFeedback"]
      .every(n => typeof mod[n] === "function"));

  /* --- setNote: text + error class toggle -------------------------------- */
  mod.setNote("hello", false);
  ck("setNote sets note text", doc.getElementById("note").textContent === "hello");
  ck("setNote(false) removes error class", doc.getElementById("note").classList.contains("error") === false);
  mod.setNote("bad", true);
  ck("setNote(true) adds error class", doc.getElementById("note").classList.contains("error") === true);
  mod.setNote("", false);
  ck("setNote falls back to empty string on falsy text", doc.getElementById("note").textContent === "");
  ck("setNote(false) toggles error off again", doc.getElementById("note").classList.contains("error") === false);
  mod.setNote(undefined, false);
  ck("setNote(undefined) yields empty string", doc.getElementById("note").textContent === "");

  /* --- setAnswerHint / clearAnswerHint ----------------------------------- */
  mod.setAnswerHint("try again");
  ck("setAnswerHint sets hint text", doc.getElementById("answer-hint").textContent === "try again");
  mod.setAnswerHint("");
  ck("setAnswerHint falls back to empty on falsy", doc.getElementById("answer-hint").textContent === "");
  mod.setAnswerHint("more");
  mod.clearAnswerHint();
  ck("clearAnswerHint empties the hint", doc.getElementById("answer-hint").textContent === "");

  /* --- clearChoices: empty + hide ---------------------------------------- */
  const choices = doc.getElementById("choices");
  choices.innerHTML = "<button class='choice'>1</button>";
  choices.hidden = false;
  mod.clearChoices();
  ck("clearChoices empties the container", choices.textContent === "");
  ck("clearChoices hides the container", choices.hidden === true);

  /* --- clearAnd: empties feedback and returns its arg -------------------- */
  const fb = doc.getElementById("feedback");
  fb.textContent = "stale";
  const marker = doc.createElement("span");
  const returned = mod.clearAnd(marker);
  ck("clearAnd empties feedback", fb.textContent === "");
  ck("clearAnd returns the passed node", returned === marker);

  /* --- clearFeedback: empties + strips correct/miss classes -------------- */
  fb.textContent = "verdict";
  fb.classList.add("correct");
  fb.classList.add("miss");
  mod.clearFeedback();
  ck("clearFeedback empties feedback", fb.textContent === "");
  ck("clearFeedback removes 'correct'", fb.classList.contains("correct") === false);
  ck("clearFeedback removes 'miss'", fb.classList.contains("miss") === false);

  console.log("\n" + pass + " passed, " + fail + " failed");
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error(e); process.exit(2); });
