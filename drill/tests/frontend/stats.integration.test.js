"use strict";
/* C-019a <-> C-019b integration: drive the real index.html stats view against
   the REAL drill.py /api/stats handler (run as a child process serving the
   WSGI app over a temp DB with seeded responses). Confirms the view renders
   actual backend output, not just a stubbed shape. */
const fs = require("fs");
const { execFileSync, spawn } = require("child_process");
const { JSDOM } = require("jsdom");
const path = require("path");
const os = require("os");

let pass = 0, fail = 0;
function check(name, cond, extra) {
  if (cond) { pass++; console.log("  ok  - " + name); }
  else { fail++; console.log("  FAIL- " + name + (extra ? "  [" + extra + "]" : "")); }
}
async function tick(ms) { return new Promise(r => setTimeout(r, ms || 30)); }

/* Seed a temp DB via a short python script using the real module, then return
   the computed /api/stats payloads by calling the real handler over WSGI in
   python and printing JSON. We capture two payloads: all-time and days=7. */
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "c019int-"));
const dbpath = path.join(tmp, "drill.db");

const pyDriver = `
import importlib.util, json, io, sys
from datetime import datetime, timedelta, timezone
def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod
# Post-modularization the backend is split: DB setup lives in db.py, the app +
# DATABASE_PATH live in http_layer.py. Load each from its own module (D-4: use
# the submodule you exercise). http_layer's route handlers read its own
# DATABASE_PATH global, so we rebind it on the http module.
db = _load("db", "db.py")
h = _load("http_layer", "http_layer.py")
h.DATABASE_PATH = ${JSON.stringify(dbpath)}
conn = db.connect(h.DATABASE_PATH); db.init_db(conn)
# Advance to the current schema before inserting: as of C-D2g insert_response
# writes the v3 difficulty/leaf_count columns, absent from the v1 init_db
# baseline. Mirrors the real startup sequence (init_db -> run_migrations).
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

// Project root holding drill.py + index.html. Defaults to two levels up
// (tests/frontend/ -> project root); override with PROJECT_ROOT for other
// layouts. The pyDriver loads drill.py relative to this cwd.
const PROJECT_ROOT = process.env.PROJECT_ROOT || path.resolve(__dirname, "..", "..");
// The Python interpreter to spawn. Default to bare "python3" so the test runs
// standalone, but allow run.sh to inject "uv run python3" so the child resolves
// bottle from the project venv (the system python3 has no bottle). Split on
// spaces: PYTHON_CMD="uv run python3" -> argv ["uv","run","python3"].
const PYTHON_CMD = (process.env.PYTHON_CMD || "python3").split(" ");
const pyExe = PYTHON_CMD[0];
const pyPrefix = PYTHON_CMD.slice(1);   // e.g. ["run","python3"]
const out = execFileSync(pyExe, [...pyPrefix, "-c", pyDriver],
  { cwd: PROJECT_ROOT, encoding: "utf8" });
const payloads = JSON.parse(out.trim().split("\n").pop());
const allSummary = JSON.parse(payloads.all.body);
const d7Summary = JSON.parse(payloads.d7.body);
console.log("real backend all-time:", JSON.stringify(allSummary));
console.log("real backend days=7 :", JSON.stringify(d7Summary));

const html = fs.readFileSync(path.join(PROJECT_ROOT, "index.html"), "utf8");

function makeBackend(statsBody) {
  return async function (url) {
    const j = (o, ok = true, s = 200) => ({ ok, status: s,
      async json() { return o; }, async text() { return JSON.stringify(o); } });
    if (url === "/api/categories")
      return j({ categories: [{ id: 1, name: "arithmetic", description: "", config: {} }] });
    if (url === "/api/banks") return j({ banks: [] });
    if (url === "/api/session/start") return j({ session_id: 1 });
    if (url.indexOf("/api/question") === 0)
      return j({ qtype: "arithmetic", question_text: "1 + 1", expected: "2",
                 question_id: null, alternatives: null, media_url: null });
    if (url === "/api/stats") return j(statsBody);
    return j({ error: "x" }, false, 404);
  };
}

async function run(summary) {
  const dom = new JSDOM(html, { runScripts: "dangerously", pretendToBeVisual: true,
    beforeParse(win) {
      win.fetch = makeBackend(summary);
      win.navigator.sendBeacon = () => true;
      win.SpeechSynthesisUtterance = function (t) { this.text = t; };
      win.speechSynthesis = { speak() {}, cancel() {} };
    } });
  await tick(120);
  const doc = dom.window.document;
  doc.getElementById("stats-toggle").click();
  await tick(50);
  const panel = doc.getElementById("stats-panel");
  const figs = {};
  panel.querySelectorAll(".stats-overall .stats-figure").forEach(function (f) {
    figs[f.querySelector("span").textContent] = f.querySelector("b").textContent;
  });
  dom.window.close();
  return figs;
}

(async function () {
  console.log("Render real all-time payload:");
  const figsAll = await run(allSummary);
  check("all-time total 7 (6 recent + 1 old)", figsAll["answered"] === "7", JSON.stringify(figsAll));
  check("all-time correct 6", figsAll["correct"] === "6", JSON.stringify(figsAll));
  /* 6/7 = 85.7% -> rounds to 86%. */
  check("all-time accuracy 86%", figsAll["accuracy"] === "86%", JSON.stringify(figsAll));

  console.log("Render real days=7 payload (old row excluded):");
  const figs7 = await run(d7Summary);
  check("days=7 total 6", figs7["answered"] === "6", JSON.stringify(figs7));
  check("days=7 correct 5", figs7["correct"] === "5", JSON.stringify(figs7));
  /* 5/6 = 83.3% -> 83%. */
  check("days=7 accuracy 83%", figs7["accuracy"] === "83%", JSON.stringify(figs7));

  console.log("\n" + pass + " passed, " + fail + " failed");
  process.exit(fail === 0 ? 0 : 1);
})().catch(e => { console.error(e); process.exit(2); });
