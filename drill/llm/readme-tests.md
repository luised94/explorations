# Harvested test harnesses (source material for C-020)

These are the actual test harnesses written during commits C-018a..C-019b this
session, recovered before the container reset so the THREAD-TEST (C-020) work
has real, working code to formalize from -- not a reconstruction from memory.

All six run green as of harvest: 108 assertions total
(C-018a 21, C-018c 19, C-019b 23, C-019a 33, smoke 6, integration 6).

## What is here

```
tests/
  test_c019a.py              backend: stats DB reader + summarize_stats +
                             GET /api/stats, driven via WSGI over a temp DB
  frontend/
    smoke.js                 frontend: arithmetic loop boot + submit (regression)
    test_c018a.js            frontend: TTS speaker (jsdom + stubbed speechSynthesis)
    test_c018c.js            frontend: elapsed_ms timing collection
    test_c019b.js            frontend: stats view disclosure
    test_c019_integration.js full stack: real drill.py /api/stats -> real view
run.sh                       provisional runner (formalize into tests/run.sh)
```

Run from this directory after `npm install jsdom --no-save` and ensuring
drill.py/index.html are in the parent dir:  `bash run.sh`

## These are SOURCE MATERIAL, not the final structure

They are organized by COMMIT (test_c018a, etc.) because that is how they were
written. C-020's job is to reorganize them by CONCERN into the permanent suite
described in PHASE0_PLAN.md Section B:

- `test_logic.py`  -- pure LOGIC. Harvest the summarize_stats assertions from
  test_c019a.py; add generator validity, validate_answer, summarize_correctness,
  pick_next_question. (Pure functions -- no DB, no jsdom, fastest tests.)
- `test_db.py`     -- DATABASE over a temp DB. Harvest the get_responses_for_stats
  filter/ordering/elapsed assertions from test_c019a.py.
- `test_http.py`   -- WSGI over a temp DB. Harvest the endpoint + 400-case
  assertions from test_c019a.py; extend to the other endpoints.
- `tests/frontend/`-- the jsdom suites mostly carry over as-is; keep them
  commit-named or rename by feature (speech.test.js, timing.test.js,
  stats.test.js, drill.test.js).
- Add the hypothesis property test for the generator (new in C-020).

## The reusable patterns (the actual value)

These four techniques are what every future test reuses. They are extracted
here so C-020 (and every later thread) applies them consistently.

### Pattern 1 -- Backend via WSGI over a temp DB (no server, no network)
From test_c019a.py. Load the real module, point it at a temp DB, drive the
Bottle app directly through the WSGI callable:

```python
import importlib.util, tempfile, os, json, io, sys
spec = importlib.util.spec_from_file_location("drill", "drill.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
m.DATABASE_PATH = os.path.join(tempfile.mkdtemp(), "drill.db")
conn = m.connect(m.DATABASE_PATH); m.init_db(conn)
# ... seed via m.start_session / m.insert_response ...

def wsgi_get(path, qs=""):
    cap = {}
    env = {"REQUEST_METHOD":"GET","PATH_INFO":path,"QUERY_STRING":qs,
           "SERVER_NAME":"t","SERVER_PORT":"80","wsgi.input":io.BytesIO(),
           "wsgi.errors":sys.stderr,"wsgi.url_scheme":"http"}
    def start_response(status, headers, exc_info=None):  # 3rd arg matters
        cap["status"] = status
    body = b"".join(m.app(env, start_response))
    return cap["status"], body.decode()
```
Gotcha already paid for: start_response MUST accept exc_info (Bottle passes it).

### Pattern 2 -- Frontend in jsdom against the REAL index.html
From the *.js harnesses. Load the actual file, stub only the network and the
weird browser globals, let the app's own boot() run:

```js
const { JSDOM } = require("jsdom");
const html = require("fs").readFileSync("index.html", "utf8");
const dom = new JSDOM(html, { runScripts: "dangerously", pretendToBeVisual: true,
  beforeParse(win) {
    win.fetch = makeBackendStub();      // route /api/* to canned responses
    win.navigator.sendBeacon = () => true;
    win.SpeechSynthesisUtterance = function (t) { this.text = t; this.lang = ""; };
    win.speechSynthesis = { speak() {}, cancel() {} };
  }});
await tick(120);  // let DOMContentLoaded + async boot() settle
// top-level `var`/`function` in the script become window.* -> drive them:
//   dom.window.state, dom.window.loadQuestion(), dom.window.submitAnswer()
```
Gotchas already paid for:
- jsdom's window.performance is a read-only getter -- patch performance.now via
  Object.defineProperty, do not reassign window.performance (test_c018c.js).
- Assert against DOM structure (querySelectorAll on the rendered elements), not
  textContent -- textContent concatenates without spaces and breaks \b regexes
  (test_c019b.js).
- A fetch in flight when state changes: guard renders on the still-current state
  (the stats panel checks aria-expanded before rendering).

### Pattern 3 -- Full-stack integration (real backend feeds real frontend)
From test_c019_integration.js. Run the real drill.py handler over a temp DB in a
python child process, capture its JSON, then feed that exact payload to the real
jsdom view. Proves the contract end to end, catching shape mismatches a stubbed
test would miss.

### Pattern 4 -- The assertion harness (tiny, dependency-free)
Every harness uses the same 6-line scorer; standardize on it:

```js
let pass=0, fail=0;
function check(name, cond, extra){ cond ? (pass++, console.log("  ok  - "+name))
  : (fail++, console.log("  FAIL- "+name+(extra?"  ["+extra+"]":""))); }
// ... at end:
console.log("\n"+pass+" passed, "+fail+" failed");
process.exit(fail===0?0:1);
```
```python
passed=failed=0
def check(name, cond, extra=""):
    global passed, failed
    if cond: passed+=1; print("  ok  - "+name)
    else: failed+=1; print("  FAIL- "+name+("  ["+str(extra)+"]" if extra else ""))
```
(C-020 may swap the Python side to pytest; the JS side stays this lightweight
runner unless you choose a node test framework. Either is fine -- the patterns
above are what matter, not the harness library.)

## AST-equality trick (for the no-behavior-change commits)
Not a test per se, but used in C-018b/C-019a to PROVE a change was comment-only
or did not alter executable code. Worth keeping in the toolkit:

```python
import ast
def strip_module_doc(t):
    b=list(t.body)
    if b and isinstance(b[0],ast.Expr) and isinstance(getattr(b[0],"value",None),ast.Constant) \
       and isinstance(b[0].value.value,str): b=b[1:]
    t.body=b; return t
a=ast.dump(strip_module_doc(ast.parse(open("before.py").read())))
b=ast.dump(strip_module_doc(ast.parse(open("after.py").read())))
assert a==b  # only docstrings/comments changed
```
