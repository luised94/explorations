# Drill test suite (C-020)

The permanent test suite, reorganized **by concern** from the per-commit
harnesses harvested during C-018a..C-019b. ASCII only, no framework on the JS
side, pytest on the Python side.

## Layout

    tests/
      _support.py                  shared backend helpers (load_drill, temp_db, wsgi_*)
      conftest.py                  chdir to project root so relative paths resolve
      test_logic.py                pure LOGIC: summaries, validate_answer, generate/
                                   evaluate/render, pick_next_question
      test_db.py                   DATABASE over a temp DB: round-trips, the
                                   get_responses_for_stats filter/order/elapsed contract
      test_http.py                 WSGI over a temp DB: endpoints + the 400 envelope
      test_generator_property.py   hypothesis property test for the generator
      frontend/
        drill.test.js              boot + arithmetic submit (was smoke.js)
        speech.test.js             TTS speaker gating (was test_c018a.js)
        timing.test.js             elapsed_ms collection (was test_c018c.js)
        stats.test.js              stats view disclosure (was test_c019b.js)
        stats.integration.test.js  real backend -> real view (was test_c019_integration.js)
    run.sh                         pytest (backend) + node (frontend)

## Where the harvested assertions went (the by-concern remap)

| Source harness        | Moved to                                            |
|-----------------------|-----------------------------------------------------|
| test_c019a.py (summary)| test_logic.py :: summarize_stats tests             |
| test_c019a.py (DB)    | test_db.py                                          |
| test_c019a.py (WSGI)  | test_http.py                                        |
| smoke.js              | frontend/drill.test.js                              |
| test_c018a.js         | frontend/speech.test.js                             |
| test_c018c.js         | frontend/timing.test.js                             |
| test_c019b.js         | frontend/stats.test.js                              |
| test_c019_integration.js | frontend/stats.integration.test.js              |

New coverage added in C-020 (did not exist in the harnesses):
summarize_correctness, validate_answer (all qtype branches + the unknown-qtype
guarantee), generate/evaluate/render example invariants, pick_next_question,
and the hypothesis generator property test.

## Running

From the project root (the directory with drill.py and index.html):

    python3 -m pytest tests              # backend only
    node tests/frontend/drill.test.js    # one frontend suite
    bash tests/run.sh                    # everything

Requirements (project root):
- Python: bottle, pytest, hypothesis  (add to pyproject [dependency-groups].test)
- Node:   jsdom resolvable  ->  npm install jsdom --no-save

`file://` blocks the app's ES modules, so the integration test (and the app)
must go through the server / a loaded module, never a double-clicked HTML file.

## The four reusable patterns (apply these in every future test)

### Pattern 1 -- Backend via WSGI over a temp DB (no server, no network)
`_support.py` provides `load_drill()`, `temp_db(m)`, `wsgi_get/wsgi_post_json`.
Load the real module, point `DATABASE_PATH` at a temp DB, drive `m.app`
through its WSGI callable.
Gotcha already paid for: `start_response` MUST accept the third `exc_info`
argument -- Bottle passes it.

### Pattern 2 -- Frontend in jsdom against the REAL index.html
Load the actual file, stub only the network and the weird browser globals,
let the app's own `boot()` run, then drive `window.*`.
Gotchas already paid for:
- `window.performance` is a read-only getter -- patch `performance.now` via
  `Object.defineProperty`, never reassign `window.performance` (timing.test.js).
- Assert against DOM structure (`querySelectorAll`), not `textContent` --
  `textContent` concatenates without spaces and breaks `\b` regexes
  (stats.test.js).
- Guard renders on the still-current state for in-flight fetches.

### Pattern 3 -- Full-stack integration (real backend feeds real frontend)
Run the real drill.py handler over a temp DB in a python child process,
capture its JSON, feed that exact payload to the real jsdom view. Catches
shape mismatches a stubbed test would miss (stats.integration.test.js).

### Pattern 4 -- The tiny assertion harness (JS side)
The JS suites keep the dependency-free 6-line scorer (`ck(name, cond)` ->
`process.exit(fail?1:0)`). The Python side moved to pytest; plain `assert`
plus parametrize replaces the hand-rolled `check()`.

## AST-equality trick (for no-behavior-change commits)
Kept in the toolkit for proving a change was comment/docstring-only: parse
before/after, strip module docstrings, compare `ast.dump`. Not wired into the
suite (it is a per-commit check, not a standing test).
