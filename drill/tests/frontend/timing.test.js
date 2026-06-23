"use strict";
/* C-018c contract test: elapsed_ms is collected from the frontend and sent in
   the /api/answer body. Verifies: a typed submit sends a sane elapsed_ms; an
   MC choice submit sends one; retry-after-error re-times (mark resets so the
   second attempt's elapsed is measured, not the first); an empty submit does
   NOT consume/clear the mark; and the backend stays untouched (we only assert
   the wire body here). performance.now() is controlled so timings are exact. */
const fs = require("fs");
const { JSDOM } = require("jsdom");
const html = fs.readFileSync("index.html", "utf8");

let pass = 0, fail = 0;
function check(name, cond, extra) {
  if (cond) { pass++; console.log("  ok  - " + name); }
  else { fail++; console.log("  FAIL- " + name + (extra ? "  [" + extra + "]" : "")); }
}
async function tick(ms) { return new Promise(r => setTimeout(r, ms || 30)); }

/* Controllable monotonic clock injected as performance.now(). */
function makeClock() {
  let t = 1000;
  return {
    now() { return t; },
    advance(ms) { t += ms; },
    set(ms) { t = ms; }
  };
}

/* Backend stub that records every /api/answer body it receives, and can be
   told to fail the next N answer calls (to exercise the retry path). */
function makeBackend(state) {
  return async function (url, opts) {
    const j = (o, ok = true, s = 200) => ({
      ok, status: s, async json() { return o; }, async text() { return JSON.stringify(o); }
    });
    if (url === "/api/categories")
      return j({ categories: [{ id: 1, name: "arithmetic", description: "", config: {} },
                               { id: 2, name: "vocabulary", description: "", config: {} }] });
    if (url === "/api/banks")
      return j({ banks: [{ id: 10, category_id: 2, name: "es", language: "es",
                           source: "import", metadata: {}, created: "2024-01-01T00:00:00Z" }] });
    if (url === "/api/session/start") return j({ session_id: 42 });
    if (url === "/api/session/end") return j({ ended: true });
    if (url.indexOf("/api/question") === 0) {
      const next = state.questions.shift() || {
        qtype: "arithmetic", question_text: "1 + 1", expected: "2",
        question_id: null, alternatives: null, media_url: null
      };
      return j(next);
    }
    if (url === "/api/answer") {
      const body = JSON.parse(opts.body);
      state.answerBodies.push(body);
      if (state.failNext > 0) { state.failNext--; return j({ error: "boom" }, false, 500); }
      return j({ correct: true, expected: body.expected, user_input: body.user_input,
                 session_stats: { total: state.answerBodies.length,
                                  correct: 1, accuracy: 1.0, streak: 1 } });
    }
    return j({ error: "unexpected " + url }, false, 404);
  };
}

async function boot(questions) {
  const backendState = { questions: questions.slice(), answerBodies: [], failNext: 0 };
  const clock = makeClock();
  const dom = new JSDOM(html, {
    runScripts: "dangerously", pretendToBeVisual: true,
    beforeParse(win) {
      win.fetch = makeBackend(backendState);
      win.navigator.sendBeacon = () => true;
      /* Inject controllable clock: override only performance.now (jsdom's
         window.performance is a read-only getter, so we patch the method). */
      try {
        win.performance.now = () => clock.now();
      } catch (e) {
        Object.defineProperty(win.performance, "now", {
          configurable: true, writable: true, value: () => clock.now()
        });
      }
      /* Speech absent is fine for these tests. */
      win.SpeechSynthesisUtterance = function (t) { this.text = t; this.lang = ""; };
      win.speechSynthesis = { speak() {}, cancel() {} };
    }
  });
  await tick(120);
  return { dom, backendState, clock };
}

(async function () {
  /* -- Test 1: typed arithmetic submit sends elapsed_ms ------------------- */
  console.log("Test 1: typed submit sends elapsed_ms");
  {
    const { dom, backendState, clock } = await boot([
      { qtype: "arithmetic", question_text: "2 + 2", expected: "4",
        question_id: null, alternatives: null, media_url: null }
    ]);
    const win = dom.window, doc = win.document;
    check("phase answering after boot", win.state.phase === "answering");
    check("mark set on enterAnswering", typeof win.state.answerStartMark === "number");
    clock.advance(2500); /* user thinks/types for 2.5s */
    doc.getElementById("answer").value = "4";
    await win.submitAnswer();
    await tick(40);
    const body = backendState.answerBodies[0];
    check("answer body recorded", !!body);
    check("elapsed_ms present", body && typeof body.elapsed_ms === "number", JSON.stringify(body));
    check("elapsed_ms == 2500", body && body.elapsed_ms === 2500, body && String(body.elapsed_ms));
    check("mark cleared after submit", win.state.answerStartMark === null);
    dom.window.close();
  }

  /* -- Test 2: MC choice submit sends elapsed_ms -------------------------- */
  console.log("Test 2: multiple_choice submit sends elapsed_ms");
  {
    const { dom, backendState, clock } = await boot([
      { qtype: "arithmetic", question_text: "1 + 1", expected: "2",
        question_id: null, alternatives: null, media_url: null },
      { qtype: "multiple_choice", question_text: "Capital of France?",
        expected: "Paris", question_id: 7, alternatives: [],
        media_url: null, options: ["Paris", "Lyon", "Nice"] }
    ]);
    const win = dom.window, doc = win.document;
    /* Move onto the MC question via the app's loader. */
    win.state.selection = { categoryId: 2, categoryName: "vocabulary",
                            bankId: 10, bankName: "es" };
    await win.loadQuestion();
    await tick(40);
    check("MC rendered", win.state.current.qtype === "multiple_choice");
    check("mark set for MC", typeof win.state.answerStartMark === "number");
    clock.advance(1800);
    /* Click the first choice. */
    const firstChoice = doc.querySelector(".choice");
    check("choice button exists", !!firstChoice);
    firstChoice.click();
    await tick(40);
    const body = backendState.answerBodies[backendState.answerBodies.length - 1];
    check("MC elapsed_ms == 1800", body && body.elapsed_ms === 1800, body && String(body.elapsed_ms));
    dom.window.close();
  }

  /* -- Test 3: retry after error re-times (mark resets) ------------------- */
  console.log("Test 3: retry-after-error re-times");
  {
    const { dom, backendState, clock } = await boot([
      { qtype: "arithmetic", question_text: "3 + 3", expected: "6",
        question_id: null, alternatives: null, media_url: null }
    ]);
    const win = dom.window, doc = win.document;
    backendState.failNext = 1; /* first /api/answer fails */
    clock.advance(5000);       /* 5s on the failed attempt */
    doc.getElementById("answer").value = "6";
    await win.submitAnswer();  /* fails -> catch -> enterAnswering re-times */
    await tick(40);
    check("first (failed) attempt recorded a body", backendState.answerBodies.length === 1);
    check("failed attempt elapsed ~5000",
          backendState.answerBodies[0].elapsed_ms === 5000);
    check("back in answering after failure", win.state.phase === "answering");
    check("mark restarted (not null)", typeof win.state.answerStartMark === "number");
    clock.advance(900);        /* 0.9s on the successful retry */
    doc.getElementById("answer").value = "6";
    await win.submitAnswer();  /* succeeds */
    await tick(40);
    const ok = backendState.answerBodies[backendState.answerBodies.length - 1];
    check("retry succeeded recorded", backendState.answerBodies.length === 2);
    check("successful attempt elapsed == 900 (NOT 5900)",
          ok.elapsed_ms === 900, String(ok.elapsed_ms));
    dom.window.close();
  }

  /* -- Test 4: empty submit does not consume/clear the mark --------------- */
  console.log("Test 4: empty submit keeps the timer running");
  {
    const { dom, backendState, clock } = await boot([
      { qtype: "arithmetic", question_text: "9 + 1", expected: "10",
        question_id: null, alternatives: null, media_url: null }
    ]);
    const win = dom.window, doc = win.document;
    const markBefore = win.state.answerStartMark;
    clock.advance(1200);
    doc.getElementById("answer").value = "";   /* empty */
    await win.submitAnswer();                   /* early-returns, no POST */
    await tick(20);
    check("no answer POST on empty submit", backendState.answerBodies.length === 0);
    check("mark unchanged after empty submit",
          win.state.answerStartMark === markBefore, String(win.state.answerStartMark));
    clock.advance(800); /* total 2000 since the question became answerable */
    doc.getElementById("answer").value = "10";
    await win.submitAnswer();
    await tick(40);
    const body = backendState.answerBodies[0];
    check("elapsed counts from question start (==2000)",
          body && body.elapsed_ms === 2000, body && String(body.elapsed_ms));
    dom.window.close();
  }

  console.log("\n" + pass + " passed, " + fail + " failed");
  process.exit(fail === 0 ? 0 : 1);
})().catch(e => { console.error(e); process.exit(2); });
