"use strict";
/* hints.test.js -- Thread N.1, option-(b) test for the progressive hint reveal.
 *
 * Drives the REAL drill.js renderHints / renderQuestion / clearHints against the
 * shared harness DOM (the hint-reveal node is in _harness.js's fixture 1:1 with
 * index.html). Covers the three cases SPIKE 1 called out: 0 hints (truthful
 * affordance -- NO control), many hints (reveal one-by-one until exhausted), and
 * the transition clear (a new question drops the prior question's hints).
 *
 * ASCII only.
 */
const { makeDom, installFetch, importModule, tick, makeChecker } = require("./_harness.js");

function fetchStub(calls) {
  return async (url, opts) => {
    calls.push({ url, body: opts && opts.body ? JSON.parse(opts.body) : null });
    const j = (o, ok = true, s = 200) => ({ ok, status: s, async json() { return o; }, async text() { return JSON.stringify(o); } });
    if (url === "/api/categories") return j({ categories: [{ id: 1, name: "arithmetic", description: "", config: {} }] });
    if (url === "/api/banks") return j({ banks: [] });
    if (url === "/api/difficulty-rungs") return j({ rungs: [] });
    if (url.indexOf("/api/session/start") === 0) return j({ session_id: 7 });
    if (url === "/api/session/end") return j({ ended: true });
    /* A bank question that carries two hints -- the transition-clear case. */
    if (url.indexOf("/api/question") === 0) {
      return j({
        qtype: "translate", question_text: "hola", expected: "hello",
        question_id: 42, alternatives: [], media_url: null,
        hints: ["starts with h", "a greeting"]
      });
    }
    return j({ error: "x" }, false, 404);
  };
}

(async () => {
  const c = makeChecker();
  const calls = [];
  const { document: doc } = makeDom();
  installFetch(window, fetchStub(calls));

  const drill = await importModule("drill.js");
  const area = doc.getElementById("hint-reveal");

  /* --- Case 1: 0 hints -> no control, area hidden (truthful affordance) --- */
  drill.renderQuestion({ qtype: "translate", question_text: "hola", hints: [] });
  c.ck("0 hints: area hidden", area.hidden === true);
  c.ck("0 hints: no reveal button", area.querySelector(".hint-reveal-button") === null);
  c.ck("0 hints: no hint items", area.querySelectorAll(".hint-item").length === 0);

  /* Also prove a MISSING hints key behaves like 0 (renderQuestion defaults []). */
  drill.renderQuestion({ qtype: "arithmetic", question_text: "6 + 7" });
  c.ck("missing hints key: area stays hidden", area.hidden === true);
  c.ck("missing hints key: no control", area.querySelector(".hint-reveal-button") === null);

  /* --- Case 2: many hints -> reveal one-by-one until exhausted ------------ */
  drill.renderQuestion({ qtype: "translate", question_text: "hola", hints: ["starts with h", "a greeting"] });
  const btn = () => area.querySelector(".hint-reveal-button");
  c.ck("2 hints: area shown", area.hidden === false);
  c.ck("2 hints: button present before any reveal", !!btn());
  c.ck("2 hints: no hints shown until clicked", area.querySelectorAll(".hint-item").length === 0);

  btn().click();
  c.ck("after 1 click: one hint shown", area.querySelectorAll(".hint-item").length === 1);
  c.ck("after 1 click: first hint text correct", area.querySelectorAll(".hint-item")[0].textContent === "starts with h");
  c.ck("after 1 click: button still present (more remain)", !!btn() && btn().hidden === false);

  btn().click();
  c.ck("after 2 clicks: both hints shown", area.querySelectorAll(".hint-item").length === 2);
  c.ck("after 2 clicks: second hint text correct", area.querySelectorAll(".hint-item")[1].textContent === "a greeting");
  c.ck("after 2 clicks: button retired (none remain)", !btn() || btn().hidden === true);

  /* --- Case 3: single hint -> one reveal, then retire -------------------- */
  drill.renderQuestion({ qtype: "translate", question_text: "uno", hints: ["only clue"] });
  c.ck("1 hint: area shown", area.hidden === false);
  area.querySelector(".hint-reveal-button").click();
  c.ck("1 hint: revealed", area.querySelectorAll(".hint-item").length === 1);
  c.ck("1 hint: button retired after the single reveal",
    !area.querySelector(".hint-reveal-button") || area.querySelector(".hint-reveal-button").hidden === true);

  /* --- Case 4: transition clear -- a new question drops prior hints ------ */
  /* Reveal a hint, then run the real loadQuestion (which calls clearHints);
     the served question also has hints, so after load the area is freshly
     built with NO revealed items and the stale ones are gone. */
  drill.renderQuestion({ qtype: "translate", question_text: "hola", hints: ["h1", "h2"] });
  area.querySelector(".hint-reveal-button").click();
  c.ck("pre-transition: a hint is revealed", area.querySelectorAll(".hint-item").length === 1);

  await drill.loadQuestion();
  await tick(60);
  /* loadQuestion cleared then re-rendered from the served payload (2 hints),
     so the area is shown with a fresh button and ZERO revealed items. */
  c.ck("post-transition: stale revealed hints cleared", area.querySelectorAll(".hint-item").length === 0);
  c.ck("post-transition: fresh reveal button for new question", !!area.querySelector(".hint-reveal-button"));

  /* And a transition to a question with NO hints hides the area entirely. */
  drill.clearHints();
  drill.renderQuestion({ qtype: "arithmetic", question_text: "2 + 2", hints: [] });
  c.ck("transition to hint-less question hides the area", area.hidden === true);

  c.done();
})().catch(e => { console.error(e); process.exit(2); });
