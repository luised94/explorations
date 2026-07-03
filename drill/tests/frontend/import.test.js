"use strict";
/* import.test.js -- MIGRATED to option (b) at the E10 cutover (was C-2U-d,
 * driving the real inline page).
 *
 * Two concerns, split by what each actually tests after the cutover:
 *  (1) BEHAVIOR: the import panel toggle opens on first click and closes on the
 *      second (aria-expanded + hidden symmetric), and the panel's help text
 *      carries the corrected difficulty range. This is built by boot's
 *      onImportToggle/buildImportPanel, so it drives the real module graph.
 *  (2) THE STYLESHEET FIX: the .import-panel[hidden]{display:none} guard whose
 *      specificity beats .import-panel{display:flex} lives in index.html's CSS.
 *      jsdom does not model that cascade (it reports display:none regardless),
 *      so -- as the classic test already documented -- this is asserted by
 *      reading the real index.html stylesheet text statically, not via layout.
 *      That file still exists post-cutover; only its inline <script> was removed. */
const fs = require("fs");
const path = require("path");
const { makeDom, installFetch, importModule, tick, makeChecker } = require("./_harness.js");

function fetchStub() {
  return async (url) => {
    const j = (o, ok = true, s = 200) => ({ ok, status: s, async json() { return o; }, async text() { return JSON.stringify(o); } });
    if (url === "/api/categories") return j({ categories: [{ id: 1, name: "arithmetic", description: "", config: {} }] });
    if (url === "/api/banks") return j({ banks: [] });
    if (url === "/api/difficulty-rungs") return j({ rungs: [] });
    if (url === "/api/session/start" || url.indexOf("/api/session/start") === 0) return j({ session_id: 7 });
    if (url === "/api/session/end") return j({ ended: true });
    if (url.indexOf("/api/question") === 0) return j({ qtype: "arithmetic", question_text: "6 + 7", expected: "13", question_id: null, alternatives: null, media_url: null, difficulty: null, leaf_count: 2 });
    if (url === "/api/answer") return j({ correct: true, expected: "13", user_input: "13", session_stats: { total: 1, correct: 1, accuracy: 1.0, streak: 1 } });
    return j({ error: "x" }, false, 404);
  };
}

(async () => {
  const c = makeChecker();
  const { window: win, document: doc } = makeDom({});
  installFetch(win, fetchStub());
  const boot = await importModule("boot.js");
  await tick(120);

  const toggle = doc.getElementById("import-toggle");
  const panel = doc.getElementById("import-panel");

  /* --- (1) behavioral: the attribute toggle is symmetric --- */
  c.ck("import panel starts hidden", panel.hidden === true);
  toggle.dispatchEvent(new win.Event("click"));
  await tick(30);
  c.ck("first click opens (aria-expanded true)", toggle.getAttribute("aria-expanded") === "true");
  c.ck("first click clears hidden", panel.hidden === false);
  toggle.dispatchEvent(new win.Event("click"));
  await tick(30);
  c.ck("second click closes (aria-expanded false)", toggle.getAttribute("aria-expanded") === "false");
  c.ck("second click sets hidden again", panel.hidden === true);

  /* --- (2) the fix: the real index.html stylesheet carries the [hidden] guard --- */
  const html = fs.readFileSync(path.resolve("index.html"), "utf8");
  const guard = /\.import-panel\[hidden\]\s*\{\s*display:\s*none/.test(html);
  c.ck("stylesheet has .import-panel[hidden]{display:none} guard", guard);

  /* --- the corrected import-help difficulty range (built by buildImportPanel) --- */
  toggle.dispatchEvent(new win.Event("click"));
  await tick(30);
  const help = doc.querySelector(".import-help");
  c.ck("import help mentions difficulty (1-4)", help && help.textContent.indexOf("difficulty (1-4)") !== -1);
  c.ck("import help no longer says (1-5)", help && help.textContent.indexOf("(1-5)") === -1);

  c.done();
})().catch(e => { console.error(e); process.exit(2); });
