# Drill Tool -- Design Spec and Implementation Plan (v2, post-backend)

Authoritative reference for all implementation work. When in doubt, cite a
section number or ADR. This is the v2 revision: the original design is intact,
but resolved ambiguities, as-built decisions, gap-fills, and the hardening
pass are folded in. Changes from v1 are marked "[v2]". The companion
DECISIONS.md is the per-commit audit trail; this spec is the steady-state
description of the system.

Status: backend (drill.py) complete and hardened through C-012, plus the MAIN
server entry point (C-013a, pulled forward from C-019 -- the app is runnable).
Frontend done: C-013 (arithmetic drill loop), C-014 (session lifecycle + run
log), C-015 (keyboard + empty-answer hint), C-017 (import UI), C-016 (bank
selection + drilling non-arithmetic, incl. multiple-choice), C-016a (MC layout
+ advance-button patch). Remaining: C-018b (Option-A per-question-language
scaffold, comment-only), C-018c (per-answer timing collection), C-019 (stats
view + stats DB queries), and the unscheduled no-feedback speed-drill mode.
C-018 TTS was split: C-018a/b/c are DONE (TTS click-to-hear, Option-A scaffold,
timing collection). C-019 was split: C-019a (stats DB query + summary + GET
/api/stats) and C-019b (the stats view UI) are DONE. The INITIAL PLAN IS
COMPLETE -- every commit C-001..C-019b is built (with C-013a/C-016a inserted
along the way). The only remaining noted item is the unscheduled no-feedback
"speed drill" mode, which was always outside the initial plan. C-016/C-017
built in swapped order. [v11]

---

## 1. What we are building

A local, single-user drill/practice tool for self-study with persistent
cross-session tracking. Categories include arithmetic (generated on the
fly), vocabulary, trivia/history, geography, logic, typing, and code
snippets. Content comes from importable question banks (JSON Lines files),
manual entry, and (in the future) AI generation.

The tool is a Python backend serving one HTML page and a small JSON API.
The user runs it locally on WSL, opens a browser on Windows, and drills.

## 2. Stack and constraints

- Python 3.10+, managed with uv
- Bottle (single-file micro-framework, the ONE external Python dependency)
- SQLite via stdlib sqlite3 for persistence
- Vanilla JS, HTML, CSS for the frontend -- no frameworks, no build step
- Two files: drill.py (all backend) and index.html (all frontend)
- Coding style: data-oriented procedural programming with pure functions
- Separation: data IO / logic-computation / presentation clearly separated
- All data crosses boundaries as plain dicts, lists, strings, numbers
- No classes for behavior, no ORM, no mutation of shared state
  - [v2] Two small internal exception classes exist (ImportParseError,
    _BadParameter) -- these carry error data, not behavior, and do not
    violate the "no classes for behavior" rule.
- ASCII only in all code output and comments
- Modern type hints, docstrings on every function, full variable names

## 3. Architecture Decision Records

### ADR-001: Bottle as HTTP server
One file, zero deps of its own, routing and JSON responses with minimal
boilerplate. Rejected: raw stdlib http.server, Flask, FastAPI.

### ADR-002: SQLite for persistence
Built into Python. Structured queries for stats. Single .db file. Easy
backup (copy the file). Rejected: flat JSON, shelve, Postgres.

### ADR-003: Nested dicts for expression trees
Internal node: {"op": str, "left": node, "right": node}. Leaf: plain int.
Self-documenting keys. Direct JSON serialization. Extensible to unary ops.
Rejected: tuples, dataclasses, flat arrays.

### ADR-004: JSON Lines for bank import/export
One JSON object per line. Required fields: question, answer. Everything else
optional. Rejected: CSV (as the canonical format), JSON array, SQLite files.
[v2] CSV is supported as a convenience import adapter (see ADR-008); JSONL
remains canonical.

### ADR-005: Single-question focused UI with ambient stats
One question fills the main area. Persistent stats bar shows count,
accuracy, streak. Category/bank selection at top. Feedback inline. Next
question loads in place. Rejected: scrolling feed, dashboard, explorable space.

### ADR-006: Browser TTS, no speech recognition in v1
window.speechSynthesis for "click to hear" pronunciation. Speech recognition
deferred.

### ADR-007: Constraints baked into expression generation
Each operator defines how its operands are generated. Division picks divisor
first, derives dividend (guarantees integers). Identity operations forbidden
at generation time. No post-hoc filtering.

### ADR-008 [v2]: Operator callables in LOGIC, scalar config in CONFIG
Resolves the layering tension in the original ADR-003/section 4.3, which put
function-valued dicts in CONFIG while declaring CONFIG "pure data". CONFIG now
holds only scalar operator data (symbol, name, arity, operand ranges,
forbid_identity values, and the enabled-by-default symbol list). The callables
(eval, operand generation) live in LOGIC. LOGIC assembles the full operator
table once at import as the module-level constant OPERATORS, validating at
build time that every enabled symbol has a config entry, an eval function, and
an operand generator (fails loudly at import on a typo). The join key between
the two layers is the operator symbol string.

### ADR-009 [v2]: Stateless per-question answer contract
The server holds no "current question" state. /api/question returns a payload
the client echoes back to /api/answer; the server re-runs validation (never
trusts a client verdict) and logs. This suits generated arithmetic (the
question never existed in the DB) and keeps one uniform contract for both
question paths. Trust note: the server does not verify that the echoed
"expected" matches a stored question -- acceptable for a single-user local
tool (you would only cheat yourself). A future multi-user version must grade
by question_id against the DB's stored answer, ignoring the client's
"expected". Rejected: in-memory current-question slot (lost on the frequent
dev restarts), DB-persisted current question (cleanup burden).

## 4. Data model

### 4.1 SQLite tables

schema_version: version (INTEGER), applied (TEXT ISO 8601)

categories: id, name (UNIQUE), description, config (JSON)
  Seeded: arithmetic, vocabulary, trivia, geography, logic, typing, code

banks: id, category_id (FK), name, language (ISO 639-1 nullable),
  source ("manual"/"import"/"ai_generated"), metadata (JSON), created (ISO 8601)

questions: id, bank_id (FK), qtype, question, answer, alternatives (JSON
  array), distractors (JSON array), hints (JSON array), media_url,
  tags (JSON array), difficulty (1-5 nullable), created (ISO 8601)

sessions: id, category_id (FK), bank_id (nullable), config (JSON),
  started (ISO 8601), ended (ISO 8601 nullable)

responses: id, session_id (FK), question_id (nullable for generated Qs),
  question_text, answer_text, user_input, correct (0/1), elapsed_ms (nullable),
  answered (ISO 8601)

[v2] Conventions confirmed/added:
- All timestamp columns are TEXT storing ISO 8601 (UTC). Only the HTTP layer
  and init_db read the clock; LOGIC takes timestamps as string parameters.
- JSON-array columns default to '[]', JSON-object columns to '{}', all NOT
  NULL, so reads never hit NULL during JSON parsing. media_url and difficulty
  stay nullable.
- qtype is enforced in CONFIG/LOGIC, not as a DB CHECK constraint.
- Foreign keys are declared and enforced per connection (PRAGMA foreign_keys
  = ON). delete_bank cascades manually (questions first).

### 4.2 qtype enum [v2 -- enumerated]
Stored-question types (CONFIG constant QTYPES): free_response (default for
trivia), multiple_choice (the only type using distractors), translate (show
term, type translation), identify ("what is this", may have media_url).
[v2] A separate validator-level qtype, "arithmetic" (QTYPE_ARITHMETIC), is
NOT in QTYPES because generated arithmetic is never stored; validate_answer
recognizes it for the numeric-comparison branch.

### 4.3 Expression tree (runtime only, not stored)
{"op": "+", "left": 3, "right": {"op": "*", "left": 5, "right": 2}}
Logged to responses as the rendered string in question_text. v1 generates
flat single-operator expressions; the tree/evaluator/renderer already support
nesting for a future enhancement.

### 4.4 Operator scalar config (CONFIG)
OPERATOR_CONFIG: list of dicts with keys symbol, name, arity, operand_min,
operand_max, forbid_identity. OPERATOR_SYMBOLS: enabled-by-default symbols.
[v2] Default ranges (a difficulty choice, freely adjustable -- pure data):
+ and - use [1..20]; * and / use [2..12]. For division the range bounds the
divisor and quotient; the dividend is derived. forbid_identity: + and -
forbid 0; * forbids 0 and 1; / forbids 1. Subtraction additionally forces
left >= right (non-negative results) and rejects x - x.

### 4.5 Answer validation model [v2]
normalize_text pipeline: lowercase; strip interior punctuation (, . ! ? : ;);
collapse internal whitespace; trim; strip surrounding quotes and parentheses.
Does NOT strip hyphens, apostrophes, or Unicode accents (meaningful in
language drills; accent-sensitive in v1). validate_answer dispatches by qtype:
free_response/translate/identify share the normalized path checking against
[expected] + alternatives; multiple_choice does exact compare of
server-generated strings; arithmetic parses numbers and compares within an
optional tolerance (None/0 = exact). Unrecognized qtype and non-numeric input
return False (never silently correct, never raises).

### 4.6 Session stats model [v2]
get_session_correctness (DATABASE) returns the ordered correct/incorrect
sequence; summarize_correctness (LOGIC, pure) computes {total, correct,
accuracy, streak}. streak = current run of consecutive corrects ending at the
most recent answer (0 if the most recent was wrong; not longest-ever). Empty
session yields zeros / 0.0 accuracy. This narrow per-session summary was built
with C-011; broader category/time-windowed stats queries are C-019.

## 5. Module boundaries (drill.py sections)

### # --- CONFIG ---
Constants and scalar configuration. No callables. [v2: see ADR-008]

### # --- DATABASE ---
Functions taking sqlite3.Connection, returning dicts/lists. No logic, no HTTP.
init_db, category readers [v2 gap-fill], bank/question CRUD, session/response
logging, get_session_correctness [v2]. Broader stats queries arrive in C-019.
init_db and connect are the only clock/PRAGMA touch points.

### # --- LOGIC ---
Pure functions. No IO, no DB, no HTTP. Operator table + expression
generate/evaluate/render, answer validation, JSONL/CSV parsing, session-stats
summary, question selection + payload assembly. Randomness is the one
tolerated impurity. [v2] Pure functions assert preconditions and raise
ValueError on violations (programming errors), rather than emitting silently
wrong output.

### # --- HTTP ---
Thin Bottle route handlers. Parse request, call DATABASE + LOGIC, return JSON.
No business logic. HTTP is the only clock-reader and the only glue between
DATABASE output and LOGIC input. [v2] Integer fields parsed via
_require_int/_optional_int -> 400 on bad input; sqlite3.IntegrityError caught
-> 400 with a clear message; non-dict JSON bodies tolerated.

### # --- MAIN ---
Server startup. init_db call. app.run. __main__ guard. [v3] Present as of
C-013a (pulled forward from C-019 so the app is runnable for live UI testing).
init_db is idempotent and seeds drill.db on first run; main() may override
DATABASE_PATH from the environment (DRILL_HOST/DRILL_PORT/DRILL_DB) before
serving. The module remains importable and route-complete without invoking
main(). [superseded v2: was "Scheduled with C-019; not yet present"]

Boundary invariant: DATABASE never calls LOGIC or HTTP; LOGIC never calls
DATABASE or HTTP; HTTP calls both. Verified by static audit after each commit.

## 6. API endpoints

GET  /                               serve index.html
GET  /api/categories                 list categories -> {"categories":[...]}
GET  /api/banks?category_id=N        list banks -> {"banks":[...]}
GET  /api/question?category=X&...    get next question (see below)
POST /api/answer                     submit answer -> feedback + session_stats
POST /api/session/start              begin session -> {"session_id":N}
POST /api/session/end                end session -> {"ended":bool}
GET  /api/stats[?category_id=N][&days=D] durable cross-session stats (C-019a)
       both params optional; days must be a positive int (omit for all time);
       -> {total, correct, accuracy, categories:[{category_id, category_name,
          total, correct, accuracy}], window:{category_id, days, since}}
POST /api/banks/import               upload JSONL/CSV bank

All responses JSON. Errors: {"error": "message"} with a 4xx status. [v2]
4xx (not 500) for missing/non-integer fields, malformed uploads, unknown or
empty operator sets, and DB integrity conflicts (referencing an id deleted in
another tab). 404 for an empty/nonexistent bank.

[v2] /api/question detail:
- category=arithmetic: optional ?operators=+,- restricts generation (unknown
  or empty-after-parse -> 400). Returns {qtype:"arithmetic", question_text,
  expected, question_id:null, alternatives:null, media_url:null}.
- otherwise: required ?bank_id=N, optional ?recent=1,2,3 (recently served ids
  to softly avoid repeats). Returns the bank-question payload; multiple_choice
  additionally includes "options" = shuffle([answer] + distractors).

[v2] /api/answer request: client echoes the served context -- session_id (req),
qtype (req), question_text (req), expected (req), user_input (req), and
optional alternatives, question_id (null for arithmetic), elapsed_ms,
tolerance. Response: {correct, expected, user_input, session_stats:{total,
correct, accuracy, streak}}.

[v2] /api/banks/import request: multipart "file" part + form fields
category_id (req), name (optional, defaults to filename stem), format
(optional "jsonl"/"csv", else inferred from extension), language (optional).
source recorded as "import". Parse happens before any DB write (a bad file
creates no empty bank). Returns {bank_id, imported}.

## 7. Frontend (index.html) -- NOT YET BUILT (C-013 onward)

Single-column centered layout, top to bottom: category selector, bank
selector (conditional), stats bar (always visible), question display, answer
input (autofocus), feedback area, import section (toggleable), stats view
(toggleable).

Keyboard: Enter submits. After feedback, Enter/Space = next. Escape ends
session. Input auto-focuses.

TTS: speaker button on vocabulary questions; speechSynthesis.speak() with the
bank language code.

Vanilla JS, fetch() for API calls. Minimal CSS.

[v2] The UI must match the as-built contracts in section 6: echo question
context to /api/answer; render multiple_choice from the "options" list and
submit the chosen option's text; pass ?recent= for bank drills if it wants to
avoid repeats; read session_stats from the answer response to update the stats
bar without a separate call. CSV import array cells are pipe-separated.

## 8. Implementation plan -- commit sequence

DONE (backend, hardened + integration-tested):
  C-001 Project scaffolding (pyproject.toml, .gitignore, README)
  C-002 SQLite schema init, seed categories
  C-003 Bank and question CRUD (+ category readers, gap-fill)
  C-004 Session and response tracking
  C-005 Operator scalar config (CONFIG)
  C-006 Operator table + expression generate/evaluate/render (LOGIC)
  C-007 Answer validation
  C-008 JSON Lines and CSV import/parse
  C-009 Bottle server skeleton with route stubs
  C-010 Wire handlers to DATABASE + LOGIC (incl. import route)
  C-011 Arithmetic question endpoint (+ session_stats on answer)
  C-012 Bank-based question endpoint
  HARDENING PASS (post-C-012): see DECISIONS.md

REMAINING (frontend + stats):
  C-013 Minimal HTML page with drill UI                          [sonnet] DONE
  C-013a MAIN server entry point (pulled forward from C-019)     [sonnet] DONE
  C-014 Session management in UI                                 [haiku]  DONE
  C-015 Keyboard interaction                                     [haiku]  DONE
  C-017 Import UI                                                [haiku]  DONE
  C-016 Bank selection UI                                        [haiku]  DONE
  C-016a MC layout + advance-button patch (bug fixes)            [sonnet] DONE
  C-018a TTS pronunciation (click-to-hear), frontend only        [sonnet] DONE
  C-018b Option-A per-question-language scaffold (comment only)  [sonnet] DONE
  C-018c Per-answer timing collection (elapsed_ms, collect-only) [sonnet] DONE
  C-019a Stats DB query + summary + GET /api/stats               [sonnet] DONE
  C-019b Stats view UI                                           [sonnet] DONE
        (MAIN moved to C-013a) [v3]
  [v7] C-018 (TTS) split into C-018a (click-to-hear, done) + C-018b (the
  deferred per-question-language path, scaffolded as a pure comment block in
  drill.py per the backend-freeze discipline). C-018c collects elapsed_ms from
  the frontend (the backend column + insert path already exist and are
  hardened, so no DB change). C-019 split into C-019a (backend stats query +
  pure summary + endpoint, the one sanctioned unfreeze) and C-019b (the view).
  elapsed_ms is collected from C-018c onward but no timing CALCULATION ships in
  v1 (deferred feature; the stats query may SELECT it but summarize_stats
  ignores it).
  [v4] Order swap: C-017 (import) built before C-016 (bank selection). A
  freshly seeded DB has no banks, so bank selection has nothing to show or
  drill until a bank exists; import is what creates one. Dependency is
  asymmetric (C-016 needs banks; C-017 does not need the selector), so
  C-017 -> C-016 keeps every commit live-testable. See DECISIONS C-017.
  [v6] C-016a patched three multiple-choice UI bugs found in live use: the
  Next button was trapped inside the hidden answer-row (moved out; shown as
  Next in feedback for all qtypes); the stage compressed below its content so
  choices/feedback overflowed and the run-log overlapped them (stage given
  flex-shrink:0, no fixed min-height); feedback was blocked by the same
  overflow. UI-only, no backend change. See DECISIONS C-016a.

[v3] Critical-path note: the MAIN block (app.run + __main__ + startup init_db)
landed early in C-013a, so `uv run drill.py` / `python drill.py` works now and
the C-013 UI was tested live end to end. C-019's remaining scope is the stats
view and its time-windowed DB queries (GET /api/stats is still a 501 stub).
[superseded by v10: /api/stats was implemented in C-019a; only the C-019b view
remains.]
[superseded v2: the external-WSGI-driver workaround is no longer needed.]

## 9. Excluded from v1 (schema accommodates all of these)

AI-generated content; speech recognition; handwriting canvas + CJK
recognition; timed rounds / speed mode (elapsed_ms exists for future use);
difficulty adjustment / adaptive selection; music/art/literature categories;
multi-user / network access; export / backup UI (the .db file IS the backup);
chart rendering in stats (text-only in v1); user-created categories (reads
only in v1); bank/question editing (no update endpoints in v1); accent-
insensitive matching (a possible per-bank flag later).

## 10. Available content sources (from research)

Trivia: Open Trivia Database (opentdb.com), OpenTriviaQA (CC BY-SA 4.0),
el-cms/Open-trivia-database, FreebaseQA (CC BY-4.0). Vocabulary:
CodingFriends/basic-vocabulary-word-lists (CSV), wordfreq, Tatoeba, Sketch
Engine. Handwriting (future): HanziLookupJS, KanjiCanvas.

## 11. Working agreements

- Produce code only when explicitly asked
- Each code request cites a commit ID (C-013 through C-019)
- Generate only what that commit describes; do not anticipate future commits
- When modifying existing code, produce the complete updated file
- Mark changes with commit ID comments
- If something in the spec seems wrong or incomplete, raise it before coding
- The exclusion list (section 9) is the contract for what is NOT built
- [v2] The backend (drill.py) is FROZEN. The UI is built against the section-6
  contracts. If a UI need exposes a real backend gap, raise it and amend the
  spec before changing drill.py -- do not silently edit the frozen backend.
- [v2] Maintain DECISIONS.md: append non-spec decisions and flags per commit.

## 12. [v2] Open items carried into the UI thread

- identify currently validates as typed answer (same path as free_response);
  qtype is in the signature so a future pick-from-options path can diverge.
  The UI should render identify as a text box (plus media_url image if present).
- Wire field is "expected" (not "answer_text"); answer_text is the DB column.
- uv.lock is gitignored (single-user tool); flip to committed if you want
  reproducible installs. README documents the pipe-separated CSV array
  convention -- keep it accurate if the UI's import section restates it.
