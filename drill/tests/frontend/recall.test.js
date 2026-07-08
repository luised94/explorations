"use strict";
/* recall.test.js -- rec-4: the recall attempt flow. Drives the real drill.js
 * graph against a fixture DOM + stubbed fetch: a recall question submits its
 * attempt ungraded, reveals nothing, queues the attempt for the batched
 * grading pass, and advances straight to the next question. Empty submits
 * show the recall-specific hint and post nothing.
 *
 * ASCII only.
 */
const path = require("path");
const {
  fixtureHtml, makeDom, installFetch, importModule, tick, makeChecker
} = require("./_harness.js");

(async () => {
  const c = makeChecker();
  const { window: win, document: doc } = makeDom();

  const calls = [];
  let served = 0;
  const j = (o, ok = true, s = 200) => ({ ok, status: s, async json() { return o; } });
  installFetch(win, async (url, opts) => {
    calls.push({ url, body: opts && opts.body ? JSON.parse(opts.body) : null });
    if (url === "/api/categories") return j({ categories: [
      { id: 1, name: "arithmetic", description: "", config: {} },
      { id: 2, name: "vocabulary", description: "", config: {} }
    ] });
    if (url === "/api/banks") return j({ banks: [{ id: 11, name: "facts", category_id: 2, language: null }] });
    if (url === "/api/difficulty-rungs") return j({ rungs: [] });
    if (url === "/api/session/start") return j({ session_id: 5 });
    if (url === "/api/session/end") return j({ ended: true, summary: {
      total: 0, correct: 0, accuracy: 0, streak: 0,
      new_introduced_today: 0, due_remaining: 0
    } });
    if (url.indexOf("/api/question") === 0) {
      served += 1;
      return j({ qtype: "recall", question_text: "state theorem " + served,
                 expected: "criterion " + served, question_id: 100 + served,
                 alternatives: null, media_url: null });
    }
    if (url === "/api/answer") return j({
      recorded: true, graded: false, response_id: 900 + served,
      session_stats: { total: 0, correct: 0, accuracy: 0, streak: 0 }
    });
    return j({ error: "x" }, false, 404);
  });

  const drill = await importModule("drill.js");
  const { state } = await importModule("state.js");
  const { startSession } = await importModule("session.js");

  state.selection = { categoryId: 2, categoryName: "vocabulary", bankId: 11, bankName: "facts" };
  await startSession();
  await drill.loadQuestion();
  await tick();
  c.ck("recall question rendered into the answering phase", state.phase === "answering");
  c.ck("recall attempts start empty for the session", state.recallAttempts.length === 0);

  /* Empty submit: recall-specific hint, no POST. */
  const answerPosts = () => calls.filter(x => x.url === "/api/answer").length;
  doc.getElementById("answer").value = "   ";
  await drill.submitAnswer();
  c.ck("empty recall submit posts nothing", answerPosts() === 0);
  c.ck("empty recall submit shows the attempt hint",
    doc.getElementById("answer-hint").textContent.indexOf("attempt") !== -1);

  /* Real attempt: posts, queues, advances -- no reveal, no feedback phase. */
  doc.getElementById("answer").value = "my best recollection";
  await drill.submitAnswer();
  await tick();
  c.ck("attempt posted once", answerPosts() === 1);
  const posted = calls.filter(x => x.url === "/api/answer")[0].body;
  c.ck("attempt body carries qtype recall and the input",
    posted.qtype === "recall" && posted.user_input === "my best recollection");
  c.ck("attempt queued for the grading pass",
    state.recallAttempts.length === 1 &&
    state.recallAttempts[0].responseId === 901 &&
    state.recallAttempts[0].expected === "criterion 1");
  c.ck("no verdict rendered (nothing revealed inline)",
    doc.getElementById("feedback").textContent.indexOf("criterion") === -1 &&
    doc.getElementById("feedback").textContent.indexOf("Not quite") === -1);
  c.ck("submit advanced straight to the next question",
    state.phase === "answering" && state.current.question_text === "state theorem 2");

  /* A new session resets the grading queue. */
  await startSession();
  c.ck("startSession resets recallAttempts", state.recallAttempts.length === 0);

  c.done();
})().catch(e => { console.error(e); process.exit(2); });
