"use strict";
/* stats.integration.test.js -- MIGRATED to option (b) at the E10 cutover.
 *
 * The fuller-page-flow integration (ADR-051 named this the "genuinely different
 * path" kept as-is at the cutover): drive the REAL stats view against the REAL
 * drill.py /api/stats handler (run in a child python process serving the WSGI
 * app over a temp DB with seeded responses). Confirms the view renders actual
 * backend output, not just a stubbed shape.
 *
 * The Python driver (seed DB, call the real handler, print JSON) is UNCHANGED
 * from the classic test. Only the frontend half migrates: instead of loading
 * the inline index.html under runScripts:"dangerously" and clicking the leaked
 * page, it imports the real module graph via boot.js and clicks the boot-wired
 * stats-toggle -- the same disclosure path, now module-backed. */
const fs = require("fs");
const { execFileSync } = require("child_process");
const path = require("path");
const os = require("os");
const { makeDom, installFetch, installDefaultFetch, importModule, resetState, tick, makeChecker } = require("./_harness.js");

/* ---- Seed a temp DB + compute the two real /api/stats payloads ---------- */
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "c019int-"));
const dbpath = path.join(tmp, "drill.db");

const pyDriver = `
import importlib.util, json, io, sys
from datetime import datetime, timedelta, timezone
def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod
db = _load("db", "db.py")
h = _load("http_layer", "http_layer.py")
h.DATABASE_PATH = ${JSON.stringify(dbpath)}
conn = db.connect(h.DATABASE_PATH); db.init_db(conn)
db.run_migrations(conn, datetime.now(timezone.utc).isoformat())
cats = {c["name"]: c["id"] for c in db.list_categories(conn)}
now = datetime.now(timezone.utc)
recent = now - timedelta(days=1); old = now - timedelta(days=20)
s = db.start_session(conn, cats["arithmetic"], now.isoformat())
for i in range(6):  # 6 recent: 5 correct
    db.insert_response(conn, session_id=s, question_text="q", answer_text="a",
        user_input=("a" if i < 5 else "x"), correct=(i < 5),
        answered=recent.isoformat(), question_id=None, elapsed_ms=1000+i)
db.insert_response(conn, session_id=s, question_text="old", answer_text="a",
    user_input="a", correct=True, answered=old.isoformat(),
    question_id=None, elapsed_ms=999)
conn.commit(); conn.close()

def call(qs):
    cap = {}
    env = {"REQUEST_METHOD":"GET","PATH_INFO":"/api/stats","QUERY_STRING":qs,
           "SERVER_NAME":"t","SERVER_PORT":"80","wsgi.input":io.BytesIO(),
           "wsgi.errors":sys.stderr,"wsgi.url_scheme":"http"}
    def sr(status, headers, exc_info=None): cap["s"]=status
    body=b"".join(h.app(env, sr)); return cap["s"], body.decode()

s1,b1 = call("")
s7,b7 = call("days=7")
print(json.dumps({"all":{"status":s1,"body":b1},"d7":{"status":s7,"body":b7}}))
`;

const PROJECT_ROOT = process.env.PROJECT_ROOT || path.resolve(__dirname, "..", "..");
const PYTHON_CMD = (process.env.PYTHON_CMD || "python3").split(" ");
const pyExe = PYTHON_CMD[0];
const pyPrefix = PYTHON_CMD.slice(1);
const out = execFileSync(pyExe, [...pyPrefix, "-c", pyDriver], { cwd: PROJECT_ROOT, encoding: "utf8" });
const payloads = JSON.parse(out.trim().split("\n").pop());
const allSummary = JSON.parse(payloads.all.body);
const d7Summary = JSON.parse(payloads.d7.body);
console.log("real backend all-time:", JSON.stringify(allSummary));
console.log("real backend days=7 :", JSON.stringify(d7Summary));

/* ---- Frontend backend stub: categories/banks for boot + programmable stats -- */
function makeBackend(statsRef) {
  return async function (url) {
    const j = (o, ok = true, s = 200) => ({ ok, status: s, async json() { return o; }, async text() { return JSON.stringify(o); } });
    if (url === "/api/categories") return j({ categories: [{ id: 1, name: "arithmetic", description: "", config: {} }] });
    if (url === "/api/banks") return j({ banks: [] });
    if (url === "/api/difficulty-rungs") return j({ rungs: [] });
    if (url === "/api/session/start") return j({ session_id: 1 });
    if (url.indexOf("/api/question") === 0) return j({ qtype: "arithmetic", question_text: "1 + 1", expected: "2", question_id: null, alternatives: null, media_url: null });
    if (url === "/api/stats") return j(statsRef.summary);
    return j({ error: "x" }, false, 404);
  };
}

(async () => {
  const c = makeChecker();
  const { window: win, document: doc } = makeDom({});
  installDefaultFetch(win);
  const boot = await importModule("boot.js");
  const { state } = await importModule("state.js");
  const statsRef = { summary: null };
  installFetch(win, makeBackend(statsRef));

  /* Open the panel against a given (real) summary and read the overall figures. */
  async function render(summary) {
    statsRef.summary = summary;
    const toggle = doc.getElementById("stats-toggle");
    const panel = doc.getElementById("stats-panel");
    toggle.setAttribute("aria-expanded", "false");
    panel.hidden = true;
    panel.textContent = "";
    resetState(state);
    await boot.boot();
    await tick(100);
    toggle.click();
    await tick(60);
    const figs = {};
    panel.querySelectorAll(".stats-overall .stats-figure").forEach(f => { figs[f.querySelector("span").textContent] = f.querySelector("b").textContent; });
    return figs;
  }

  console.log("Render real all-time payload:");
  const figsAll = await render(allSummary);
  c.ck("all-time total 7 (6 recent + 1 old)", figsAll["answered"] === "7", JSON.stringify(figsAll));
  c.ck("all-time correct 6", figsAll["correct"] === "6", JSON.stringify(figsAll));
  c.ck("all-time accuracy 86%", figsAll["accuracy"] === "86%", JSON.stringify(figsAll));

  console.log("Render real days=7 payload (old row excluded):");
  const figs7 = await render(d7Summary);
  c.ck("days=7 total 6", figs7["answered"] === "6", JSON.stringify(figs7));
  c.ck("days=7 correct 5", figs7["correct"] === "5", JSON.stringify(figs7));
  c.ck("days=7 accuracy 83%", figs7["accuracy"] === "83%", JSON.stringify(figs7));

  c.done();
})().catch(e => { console.error(e); process.exit(2); });
