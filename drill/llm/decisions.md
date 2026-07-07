# Decision Log

Running record of implementation decisions that go beyond a literal reading
of the spec, plus flagged choices awaiting confirmation. Organized by commit.
Each entry: what was decided, why, and whether it needs your sign-off.

Legend:
  [DECIDED]  a defensible call made to proceed; reversible, noted for audit
  [FLAG]     a choice you may want to change; awaiting confirmation
  [DEFERRED] intentionally not built; belongs to a later commit or v2

---

## Pre-coding spec resolutions (from the Q&A thread)

- Operator callables live in LOGIC, not CONFIG. CONFIG is scalars only.
  Operator table built once at LOGIC import as a module-level constant.
  Build-time validation: every CONFIG-enabled symbol must exist in the
  table. (Affects C-005 scope down, C-006 scope up.)
- pick_next_question(candidates, history) is pure; HTTP is the only glue
  between DATABASE output and LOGIC input.
- qtype enum: free_response, multiple_choice, translate, identify.
- identify validation style (typed vs pick-from-options) still TBD before
  C-007. [OPEN]
- Arithmetic questions are ephemeral: written once to responses with
  question_id NULL, never persisted to questions.
- schema_version stamped once at init; no migration logic in v1.
- Import route wired in C-010 (calls C-008 parse + C-003 bulk insert).
- CSV import is an in-scope convenience adapter producing the same dicts
  as JSONL; JSONL stays canonical.
- All timestamp columns are TEXT ISO 8601. Only HTTP and init_db read the
  clock; LOGIC takes timestamps as string params.

---

## C-001  Project scaffolding

- [DECIDED] Build backend = hatchling, to support the `drill` script entry
  point under uv. Adds no runtime dependency. Can revert to backend-less
  (`uv run python drill.py`) by dropping [build-system] and [project.scripts].
- [DECIDED] `drill = "drill:main"` entry point assumes a main() in drill.py
  (exists by MAIN section). Won't resolve until then; fine for scaffolding.
- [DECIDED] bottle>=0.13, unpinned tighter (sole dependency).
- [FLAG] .gitignore ignores uv.lock. Common convention is to COMMIT the
  lockfile for reproducibility. Say the word to un-ignore.
- [DECIDED] Ignore *.db, *.local.jsonl, *.local.csv so local state and
  staged content banks are not committed by accident.

## C-002  Schema init + seed categories

- [DECIDED] utc_now_iso() placed in DATABASE (it is a callable; CONFIG is
  callable-free). Reads UTC. Switch to local time is one line if preferred.
- [DECIDED] connect() sets PRAGMA foreign_keys = ON per connection (SQLite
  defaults OFF, so FK declarations would otherwise be inert) and
  row_factory = sqlite3.Row.
- [DECIDED] Seeding uses INSERT OR IGNORE on the UNIQUE name constraint:
  idempotent, won't clobber later edits to description/config.
- [FLAG] qtype column is TEXT with no DB-level CHECK. Enum enforced in
  CONFIG/LOGIC instead. Ask if you want a hard CHECK (qtype IN (...)).
- [DECIDED] JSON-array columns default '[]', JSON-object columns default
  '{}', all NOT NULL (spec didn't specify). Prevents NULL reaching JSON
  parsing. media_url and difficulty remain nullable.

## C-003  Bank + question CRUD

- [DECIDED] CRUD marshals JSON columns at the DB edge: callers pass/receive
  Python lists and dicts, never raw JSON strings. Marshalling treated as IO,
  not logic, so it stays in DATABASE.
- [FLAG] No update_bank / update_question. Spec has no edit endpoint or UI
  in v1. Add if you want editing.
- [FLAG] No singular insert_question and no delete_question. Only
  insert_questions_bulk and delete_bank. Manual single-entry has no v1
  endpoint. Add if wanted.
- [DECIDED] delete_bank cascades manually (delete questions first), returns
  count of banks removed (0 if absent). Schema left unchanged.
- [DECIDED] insert_bank stores `source` verbatim; validation of its value
  is a logic concern, not DATABASE's.
- [DECIDED] insert_questions_bulk assumes already-valid dicts: requires
  question/answer keys (KeyError if missing), defaults optional fields.
  Shape validation belongs to the parse layer (C-008).
- [DECIDED] _dump_json uses ensure_ascii=True so stored JSON is ASCII-only
  (non-Latin content stored as \uXXXX, round-trips correctly).

## C-004  Session + response tracking

- [DECIDED] responses.correct stored as INTEGER 0/1 but exposed to callers
  as Python bool (insert_response takes bool; _response_row_to_dict returns
  bool). Same edge-marshalling pattern as JSON columns. The correct/incorrect
  judgment is a LOGIC output (C-007); DATABASE only stores it.
- [DECIDED] start_session takes optional bank_id (NULL for category-wide
  sessions like generated arithmetic) and leaves ended NULL until
  end_session.
- [DECIDED] end_session overwrites ended even if already set; guarding
  against re-ending a session is a logic concern, not enforced in DATABASE.
  Returns rowcount (0 if session absent).
- [DECIDED] insert_response: question_id nullable (NULL for ephemeral
  arithmetic), question_text always carries the rendered text so a response
  is self-describing. elapsed_ms optional (reserved for future timed rounds).
- [DECIDED] Added get_session and list_responses as reads needed by
  session-end and stats paths. No update_response / delete_response (no v1
  need). [FLAG if you want them]

## C-005  Operator scalar config

- [DECIDED] Scope narrowed per item-1 resolution: CONFIG holds only scalar
  operator data (OPERATOR_CONFIG list of dicts + OPERATOR_SYMBOLS enabled
  list). Callables and table assembly deferred to C-006/LOGIC.
- [DECIDED] Encoded operand ranges as scalar config (operand_min/max per
  operator) and forbidden-identity values as forbid_identity lists. The
  PARAMETERS the ADR-007 constraints read are data and live here; the
  ENFORCEMENT logic is C-006.
- [FLAG] Chosen operand ranges: +/- use [1..20], * and / use [2..12]
  (division per spec). These are a reasonable default difficulty, not
  specified by the spec. Adjust freely -- pure data, no logic depends on
  the specific numbers.
- [DECIDED] forbid_identity values: + and - forbid 0; * forbids 0 and 1;
  / forbids 1. Derived from ADR-007's examples (x+0, x*1, x/1, 0*x). Note
  subtraction forbidding 0 covers x-0; commutative-pair cases (e.g. 0*x as
  well as x*0) are the generator's responsibility in C-006.
- [DECIDED] For division, operand_min/max bound divisor and quotient; the
  dividend is derived (ADR-007). Documented inline so C-006 interprets the
  range correctly rather than treating it as a dividend range.

## C-006  Operator table + generator + evaluator + renderer (first LOGIC)

- [DECIDED] OPERATORS table built once at module import via
  _build_operator_table(); module-level constant, not rebuilt per request
  (agreed pre-coding).
- [DECIDED] Build-time validation raises ValueError at import if any enabled
  symbol lacks a config entry, eval fn, or operand generator (agreed early-
  failure check).
- [DECIDED] Callables (_add/_subtract/_multiply/_divide, the two operand
  generators) live in LOGIC and are attached to scalar config by symbol key.
- [DECIDED] Subtraction generation forces left >= right so results are never
  negative, and rejects left == right (x - x = 0 is trivial). This is a
  generation choice beyond ADR-007's explicit list -- non-negative results
  suit a drill tool. [FLAG if you want negatives allowed]
- [DECIDED] Division uses floor division (//) in eval; safe because
  generation guarantees exact multiples. Eval never sees a zero divisor
  because operand ranges are positive.
- [DECIDED] randomness is the one tolerated impurity in LOGIC (the generator
  inherently needs it). Everything else in LOGIC is pure/deterministic.
- [DECIDED] v1 generates flat single-operator expressions. Tree shape and
  recursive evaluate/render already support nesting (future enhancement)
  with no change to evaluator or renderer. Renderer parenthesizes nested
  internal operands; flat v1 expressions produce no parentheses.
- [NOTE] generate_expression accepts optional enabled_symbols so a session
  config can restrict operators (e.g. addition-only drill); defaults to
  OPERATOR_SYMBOLS. Wiring to session config happens at the HTTP layer.

## C-007  Answer validation

- [DECIDED] normalize_text pipeline: lowercase, strip interior punctuation
  (, . ! ? : ;), collapse internal whitespace, trim, strip surrounding
  quotes and parens. Does NOT strip hyphens, apostrophes, or Unicode
  accents (per C-007 feedback -- these carry meaning in language drills).
- [DECIDED] Accent-sensitive in v1: accented answers must be typed with
  accents. Per-bank accent_insensitive flag is a noted future option, not
  built.
- [DECIDED] validate_answer is the single dispatcher. free_response /
  translate / identify share one normalized path (identify == free_response
  in v1; qtype kept in signature so paths can diverge later without a
  signature change). multiple_choice does exact string compare (both
  strings server-generated). arithmetic parses number, compares within
  tolerance.
- [DECIDED] Arithmetic uses a validator-level qtype constant
  QTYPE_ARITHMETIC = "arithmetic", deliberately NOT added to QTYPES (that
  enum is for stored bank questions; arithmetic is ephemeral). Resolves the
  minor conflict in the feedback doc between "called externally" and "a
  dispatcher branch" -- it is one dispatcher entry point.
- [DECIDED] Non-numeric input to an arithmetic question returns False (wrong
  answer), never raises.
- [DECIDED] Unrecognized qtype returns False (never silently scored
  correct), rather than raising.
- [DECIDED] tolerance: None or 0 means exact equality; positive means
  absolute-difference tolerance. All v1 arithmetic is integer so exact
  works; parameter exists for future float operators. HTTP arithmetic
  handler passes a tolerance; vocabulary/bank handlers pass None.
- [NOTE] multiple_choice options contract (from feedback, realized at
  HTTP/UI later): server builds options as [answer] + distractors, shuffles,
  sends the list; user submits the chosen option's TEXT; validator exact-
  matches it against expected. No seed/index bookkeeping needed.

## C-008  Import parsing (JSONL + CSV)

- [DECIDED] Both parsers converge through _normalize_question_dict, the
  single place that validates required fields (question, answer non-empty)
  and fills optional defaults. This is the dict-shape validation that C-003
  bulk insert assumes happened upstream.
- [DECIDED] Output dict shape matches insert_questions_bulk's consumed keys
  exactly (qtype, question, answer, alternatives, distractors, hints,
  media_url, tags, difficulty).
- [FLAG] CSV array-valued cells use PIPE separation (tag1|tag2|tag3), not
  commas (comma is the CSV delimiter). This is a convention I chose; it must
  be documented for users authoring CSV banks. JSONL uses native arrays.
- [DECIDED] New exception type ImportParseError(ValueError) carries a
  message naming the offending line (JSONL, 1-based) or row (CSV, 1-based
  excluding header) so HTTP can report which row failed.
- [DECIDED] qtype in imports validated against QTYPES (the stored-question
  enum); defaults to free_response. Note QTYPE_ARITHMETIC is NOT accepted in
  imports -- arithmetic is generated, never imported.
- [DECIDED] difficulty coerced to int 1..5 or None; present-but-invalid
  raises. media_url empty/absent -> None.
- [DECIDED] Blank lines skipped in JSONL (trailing newlines harmless). Empty
  array cells in CSV -> empty list.
- [DECIDED] parse_import(text, file_format) dispatches by "jsonl"/"csv";
  unknown format raises. HTTP decides format from extension or param.

## C-009  Bottle server skeleton + route stubs (first HTTP)

- [DECIDED] Routes attached to an explicit bottle.Bottle() app object (not
  the module-global default app) for clarity and testability.
- [DECIDED] DATABASE_PATH module global, defaulting to DEFAULT_DATABASE_PATH;
  MAIN (C-019 area) may override at startup, and tests can point it at a
  temp DB. Handlers open a connection per request (pattern set here, used
  from C-010).
- [DECIDED] Stubs return HTTP 501 with the standard {"error": ...} envelope
  and name the commit that will implement them, so an early server run is
  predictable rather than 404. Exception: GET / already serves index.html
  via static_file (real, not a stub) since the skeleton can serve the page
  once C-013 creates it; until then it 404s on the missing file, which is
  expected.
- [DECIDED] Two shared helpers: _json_error(message, status) sets response
  status and returns the envelope; _request_json() normalizes a missing/
  non-JSON body to {} so handlers use .get without None checks.
- [NOTE] All endpoints from spec section 6 are present as stubs:
  GET / , GET /api/categories , GET /api/banks , GET /api/question ,
  POST /api/answer , POST /api/session/start , POST /api/session/end ,
  GET /api/stats , POST /api/banks/import. The single GET /api/question
  endpoint will branch arithmetic vs bank internally (C-011/C-012).
- [NOTE] No bottle.run / __main__ guard yet -- that is the MAIN section,
  scheduled with C-019. The app is importable and route-complete without it.

## C-010  Wire handlers to DATABASE + LOGIC (incl. import route)

- [GAP-FILLED] The commit plan has no category-CRUD commit, but
  GET /api/categories needs to read categories. Added list_categories,
  get_category, _category_row_to_dict to DATABASE here. Minimal reads only;
  categories remain fixed/seeded in v1. [AUDIT: scope addition beyond plan]
- [DECIDED] /api/answer request contract: client echoes back the question
  context it was served (session_id, qtype, question_text, expected,
  user_input, + optional alternatives, question_id, elapsed_ms, tolerance).
  Server is stateless per-question -- no server-side "current question"
  memory. Returns {"correct": bool, "expected": str}. [FLAG: this is the
  client/server contract the C-013 UI must match; review if you expected
  server-held question state instead.]
- [DECIDED] All handlers open a connection per request and close it in a
  finally block. HTTP reads the clock (utc_now_iso) for answered/started/
  ended/created -- the only layer that does so besides init_db.
- [DECIDED] Import route (item 6) wired here: multipart "file" part + form
  fields category_id (required), name (optional, defaults to filename stem),
  format (optional, inferred from extension), language (optional). source
  recorded as "import". Parse happens before any DB write, so a bad file
  creates no empty bank. Parse errors -> 400 with the row-naming message.
- [DECIDED] Upload must be UTF-8; non-UTF-8 -> 400. Returns
  {"bank_id", "imported"} on success.
- [DECIDED] Query/body integer params (category_id, session_id) validated
  with explicit int() and 400 on failure, rather than trusting input.
- [NOTE] /api/question left as the 501 stub on purpose -- arithmetic branch
  is C-011, bank branch is C-012.
- [NOTE] Name-resolution: _category_row_to_dict (defined ~L297) calls
  _load_json (defined ~L365). Fine: resolved at call time (request handling),
  not import time. Verified by static grep + py_compile, not by running.

## C-011  Arithmetic question endpoint (+ session_stats on answer)

- [DECIDED] Adopted the session_stats-in-answer-response suggestion. POST
  /api/answer now returns {correct, expected, user_input, session_stats}
  where session_stats = {total, correct, accuracy, streak}. Saves a
  GET /api/stats round-trip per question; drill hot path = 2 calls.
- [PULLED-FORWARD] Added get_session_correctness (DATABASE) and
  summarize_correctness (LOGIC, pure) now rather than at C-019. Only the
  narrow per-session summary the answer handler needs. Broader category/
  time-windowed stats queries remain C-019. Mirrors the list_categories
  early-add pattern.
- [DECIDED] Stats split across layers to honor the boundary: DATABASE
  returns the raw correct/incorrect sequence (SQL), LOGIC computes
  total/accuracy/streak. Streak (consecutive corrects back from most recent)
  is trivial in Python, awkward in SQL -- the reason for the split.
- [DECIDED] streak = current run ending at most recent answer; 0 if most
  recent was wrong. (Not "best streak ever" -- that would be a different
  stat. Flag if you wanted longest-ever.)
- [DECIDED] Kept inbound wire field name "expected" (set in C-010), not the
  "answer_text" shown in the feedback doc's sketch. answer_text is the DB
  COLUMN it lands in; expected is the wire field. Avoided churning C-010.
  [AUDIT: minor naming divergence from feedback doc, intentional.]
- [DECIDED] Added the client-trust-assumption comment to /api/answer (per
  feedback): server re-validates, does not trust a client verdict, but does
  not verify expected against a stored question; multi-user future should
  grade by question_id against the DB.
- [DECIDED] Arithmetic branch keys on category=="arithmetic". Optional
  ?operators=+,- restricts generation; unknown symbols -> 400. Payload
  qtype=QTYPE_ARITHMETIC, question_id=null, alternatives=null.
- [NOTE] /api/question bank branch still 501 -> C-012.

## C-012  Bank question endpoint (backend complete)

- [DECIDED] pick_next_question(candidates, history) policy (v1, non-adaptive
  per ADR-005): uniformly random pick from candidates whose id is NOT in the
  recent-history window; fall back to random over all candidates if that set
  is empty (small bank, or all recently seen). Never fails to return when
  candidates is non-empty; returns None only for an empty bank.
  [FLAG: simple random + avoid-recent. Adaptive/spaced-repetition is v2.]
- [DECIDED] Client passes recent-history via optional ?recent=1,2,3 query
  param (recently served question ids). Server is stateless about which
  questions were seen -- consistent with the stateless per-question contract
  from C-010. Bad values -> 400.
- [DECIDED] build_question_payload mirrors the arithmetic payload shape so
  the client handles both uniformly. For multiple_choice it adds "options" =
  shuffle([answer] + distractors) per the C-007 contract; user submits the
  chosen option TEXT, validated by exact match. Non-MC types carry
  alternatives and no options list.
- [DECIDED] Empty bank -> 404 ("bank N has no questions"); non-integer
  bank_id -> 400; missing bank_id -> 400.
- [NOTE] Both question paths (arithmetic C-011, bank C-012) converge on the
  same payload contract, so /api/answer and the future UI treat them
  identically apart from the optional options/media_url fields.

---

## MILESTONE: backend (drill.py) complete through C-012

- All of CONFIG, DATABASE, LOGIC, HTTP implemented. Only /api/stats remains
  a 501 stub (C-019) and MAIN (bottle.run / __main__) is not yet added
  (rides with C-019 per the plan).
- Verified statically (py_compile + grep audits, NOT by running the server,
  per standing no-execution preference):
  * Every section-6 endpoint is wired except /api/stats (correctly 501).
  * Boundary invariant holds: no connection/connect/bottle/.execute calls
    anywhere in the LOGIC section -- LOGIC is pure; DATABASE is called only
    from HTTP.
- Remaining commits are the UI batch (C-013-C-018) + stats (C-019, which
  also adds the stats DB queries and the MAIN server entry point).
- RECOMMENDATION: start a fresh thread for the UI batch, carrying drill.py +
  DECISIONS.md forward. index.html is a new file against this now-frozen
  backend contract.

---

## HARDENING PASS (post-C-012, before UI)

Full read-through for assumptions / presuppositions / entailments / decay /
time-gradient. Verified by installing bottle and running the pure functions
(3000 arithmetic samples) plus a full WSGI integration test against a temp DB.

Bugs found and fixed:
- [BUG-FIXED] generate_expression treated an empty symbol list as falsy and
  silently fell back to ALL operators. An explicit [] (client sent
  ?operators= that parsed to empty) should be an error, not a silent widen.
  Fixed to distinguish None (omitted -> default) from [] (given empty ->
  ValueError). Caught by the edge-case simulation, not the read-through.

Hardening added (turning latent 500s into clean 4xx, silent-wrong to loud-fail):
- [HARDENED] HTTP int fields (session_id, category_id, bank_id, question_id,
  elapsed_ms) parsed via _require_int/_optional_int -> 400 on bad input.
  Previously bare int(body[...]) could raise ValueError -> 500. GET handlers
  already validated; POST handlers did not. Now consistent.
- [HARDENED] _request_json returns {} for a non-dict JSON body (array/scalar),
  preventing AttributeError -> 500 on later .get().
- [HARDENED] sqlite3.IntegrityError (FK violations) caught in post_answer,
  post_session_start, post_banks_import -> 400 with a clear message. The real
  multi-tab time-gradient case: a row referenced after deletion in another
  tab. _integrity_message translates it.
- [HARDENED] _validate_numeric tolerates a non-numeric tolerance (treats as
  exact) rather than crashing on abs() <= str.
- [HARDENED] _load_json raises a clear, located ValueError on corrupt stored
  JSON (hand-edited .db) instead of an opaque JSONDecodeError in row conversion.
- [HARDENED] Pure LOGIC functions assert preconditions and fail loudly
  (ValueError) not silently wrong: generate_expression (empty/unknown symbols),
  evaluate_expression (malformed tree / unknown op), build_question_payload
  (question missing required keys).
- [HARDENED] Arithmetic endpoint: ?operators= parsing to empty after filtering
  -> 400 (not 500).
- [HARDENED] bottle import wrapped -> friendly SystemExit telling the user to
  run uv sync, instead of an opaque ImportError (time-zero setup case).

Documentation decay fixed:
- Module docstring updated from stale "C-002 implements..." to backend-complete
  status + explicit error-handling contract.
- HTTP section banner updated from "C-009 skeleton... stubs" to implemented
  state. Removed stale "Stub bodies for C-009" block.
- post_answer docstring corrected to real return shape (adds user_input,
  session_stats).

Behavior confirmed unchanged where intended:
- summarize_correctness([]) returns zeros / 0.0 accuracy (time-zero: fresh
  session) -- verified, not a crash.
- Boundary invariant still holds (no DB/HTTP calls in LOGIC) -- re-verified.
- 3000-sample arithmetic invariants hold: non-negative subtraction, exact
  integer division, no forbidden identities.
- MC options shuffle (correct answer not always first) -- verified over 200 draws.

Note: bottle 0.13.4 installed in the sandbox to run these tests; does not
change pyproject (already declares bottle>=0.13).

---

## C-013  Minimal HTML page with the drill UI (arithmetic loop)

First frontend commit. index.html is a new, self-contained file (vanilla JS,
HTML, CSS; no framework, no build step) built against the frozen section-6
contracts. Scope held to the full arithmetic drill loop: category list
(gated), auto-started session, question render, answer grading, live stats,
load-next. Verified with a headless DOM harness driving the real index.html
JS against a faithful stub of the four endpoints it calls (27 contract
assertions, all passing), plus a live-rendered screenshot pass.

- [DECIDED] Implicit session auto-start (confirmed): one session is started
  on the first question via POST /api/session/start {category_id} and reused
  for the life of the page. C-013 owns only "a session exists so answers can
  be logged"; the visible lifecycle (see/end/switch/restart) is C-014. No
  control surface is exposed here.
- [DECIDED] beforeunload cleanup (confirmed in-scope as cleanup, not UI): the
  auto-started session is ended on page close/refresh so dev does not litter
  the DB with dangling never-ended sessions. Uses navigator.sendBeacon (with
  a keepalive fetch fallback) so the POST /api/session/end survives unload.
  Server treats an unknown/already-ended id as a harmless no-op, so firing
  this unconditionally is safe.
- [DECIDED] Drillability is data-derived, not a hardcoded arithmetic check:
  isDrillable(cat) = cat.name === "arithmetic" || (cat.banks && length > 0).
  Bank selection is C-016, so `banks` is never populated yet and only
  arithmetic is live. C-016 turns the rest on by wiring /api/banks into the
  category data, NOT by editing this predicate.
- [DECIDED] Gate note wording is neutral and true about data ("(no banks
  yet)" appended to disabled options), not a promise ("coming soon").
- [DECIDED] question_id passes through to POST /api/answer as JSON null (the
  arithmetic payload's value), never stringified, so it lands as a proper
  NULL in responses.question_id. _optional_int handles null/absent cleanly.
- [DECIDED] Arithmetic answer POST omits tolerance (exact integer compare is
  the server default for absent tolerance) and sends no recent= (generated
  questions have no ids to avoid). Only the five required fields plus
  question_id are sent.
- [DECIDED] Stats bar is fed ONLY by session_stats on the /api/answer
  response (total, correct, accuracy as a 0.0-1.0 float -> rendered as a
  rounded percent, streak). No separate GET /api/stats call (it is still the
  C-019 stub anyway). Empty/pre-first-answer state shows total 0 and "--"
  accuracy rather than 0%.
- [DECIDED] One action button drives the loop by phase: "Submit" while
  answering, "Next" in feedback. Enter in the answer field submits. This is
  the minimum interaction to make the loop usable; richer keyboard control
  (Enter/Space to advance, Escape to end) is deliberately left to C-015.
- [DECIDED] On an /api/answer network/error, the user keeps the same
  question and can retry (re-enters answering) rather than losing it; the
  error envelope's message is surfaced in the note area in the UI's voice.
- [DECIDED] boot() is bound to DOMContentLoaded (falling through to immediate
  call if the document is already parsed) rather than running bare at parse
  time. More robust lifecycle binding and what let the headless harness
  install fetch before boot.
- [DECIDED] Empty/whitespace-only submissions are ignored client-side (no
  POST), keeping junk blank rows out of responses. Server still re-validates
  everything it does receive.
- [NOTE] Design: single-question stage with the expression as the hero
  (math serif), mono instrumentation, slate-dark ground, one cyan correct
  signal + one clay miss signal. Signature element: a streak pip row that
  fills on a run of correct answers and clears on a miss, derived straight
  from session_stats.streak (capped at 10 pips with a "+N" overflow). A
  redundant "Next" text hint under the feedback was cut after a render pass
  (the button already labels the action; keyboard advance that would justify
  a hint is C-015).
- [PLACEHOLDER] Hidden #bank-selector, #import-section, #stats-view divs are
  in the markup so C-016/C-017/C-019 slot in without restructuring the page.
- [NOTE] No backend gap surfaced; drill.py untouched (it is frozen). All
  four endpoints used (categories, session/start, question, answer) matched
  their as-built shapes exactly; session/end used only for unload cleanup.
---

## C-013a  Server entry point (MAIN block; pulled forward from C-019)

Pulled the `# --- MAIN ---` server entry point forward from C-019 so the app
is runnable now and each UI commit can be tested live in the browser. C-019 is
re-scoped to the stats view + stats DB queries only. drill.py is otherwise
unchanged (still frozen); this adds only the MAIN block at the end.

- [DECIDED] MAIN moved to its own commit (C-013a) rather than landing inside
  a split C-019, for a cleaner history. The spec/commit-list note that
  scheduled MAIN with C-019 is superseded: MAIN = C-013a, stats view = C-019.
- [DECIDED] Entry point is exactly the spec's three things - init_db call,
  app.run, __main__ guard - wrapped in a main() so the `drill = "drill:main"`
  console-script entry point now resolves (was flagged dangling until main()
  existed). No other C-019 work included.
- [DECIDED] Runs the explicit `app` object via app.run(...), not bottle's
  module-global bottle.run(), matching how routes are attached.
- [DECIDED] main() rebinds the module global DATABASE_PATH before serving
  (the per-request handlers read that global; the spec says MAIN may override
  it at startup). A local would not reach the handlers.
- [DECIDED] init_db is called once at startup on a single connection, then
  committed and closed. Idempotent (schema IF NOT EXISTS, version stamped
  once, categories via INSERT OR IGNORE), so first run creates+seeds drill.db
  and later runs are safe no-ops. No separate init step or command.
- [DECIDED] No argparse/CLI flags (spec specifies none). host/port/db are
  overridable via env vars DRILL_HOST (127.0.0.1), DRILL_PORT (8080),
  DRILL_DB (drill.db) - convenience for WSL, adds no dependency (os already
  imported). Non-integer DRILL_PORT exits with a clear message.
- [DECIDED] Default bind host 127.0.0.1 (works with WSL2 localhost
  forwarding to the Windows browser). 0.0.0.0 available via DRILL_HOST if
  forwarding ever fails.
- [NOTE] Verified live end to end: server serves index.html, seeds 7
  categories on first run, and the full session/start -> answer (correct and
  wrong) -> session/end path persists to responses with question_id stored
  as SQL NULL and session_stats accuracy as a 0.0-1.0 float.
- [NOTE] Confirmed running on target machine (WSL2): `uv run drill.py` ->
  http://localhost:8080/ loads and the arithmetic loop is interactive.

---

## C-014  Session lifecycle UI + in-memory run log

Makes the session visible and controllable, building on C-013's implicit
auto-start. End the active session (-> resting state) and Restart (end +
start a fresh run). Sessions created during the page visit are retained in an
in-memory run log, newest-first. Verified: the full C-013 suite still passes
unchanged (27 assertions -- the refactor preserved the loop), plus a new
C-014 suite (24 assertions: lifecycle transitions, run log, ordering, zero-
answer omission, unload), plus a live render pass.

- [DECIDED] Data-oriented core (per design directive): one `sessions` array
  of plain records is the single source of truth. Record shape:
  {id, categoryId, categoryName, status:"active"|"ended", stats:{total,
  correct, accuracy, streak}}. Exactly three transitions mutate it --
  startSession (append active record), recordStats (fold a session_stats
  snapshot into a record), endSession (mark "ended", clear activeSessionId if
  it was active). Every visible surface is a pure render derived from the
  array (renderSessionUI -> renderStats + renderSessionControls +
  renderRunLog); renders are rebuilt wholesale, never hand-patched.
- [DECIDED] One meaning per surface (captured as a standing UI principle): the
  stats bar ALWAYS shows the active session (zeros/-- in the resting state);
  the run log shows ONLY finished runs. The stats bar is no longer separately
  tracked -- it is a view of the active record's stats, so there is a single
  source for "current numbers".
- [DECIDED] Restart preserves the ended run (confirmed). Restart = endSession
  (the just-ended run stays in the log with its final stats) + loadQuestion
  (auto-starts a fresh session). It does not replace the prior run.
- [DECIDED] A session enters the run log only once it has >= 1 recorded
  answer (confirmed). Started-but-unanswered sessions (total 0) -- including
  the auto-started-then-immediately-ended case -- are omitted from the
  displayed log. "We don't count how many times the page was opened." The
  records still exist in the array (and were ended server-side); the filter
  is at the render boundary (status==="ended" && stats.total>0).
- [DECIDED] Newest-first ordering (confirmed): the array is append order
  (oldest-first); renderRunLog reverses the filtered runs so the most recent
  run is on top.
- [DECIDED] categoryName carried on every record now (confirmed) even though
  it is uniformly "arithmetic" until C-016. Data-oriented: the record carries
  its own category so C-016 needs no reshape -- it just starts producing
  records with other category names. Run rows render "<categoryName> #<id>".
- [DECIDED] Resting state (explicit End): stage cleared to "--", answer input
  disabled, primary action disabled, stats bar reset to zeros/--. Controls
  collapse to a single "Start new session". The next question (via Start new,
  or Restart) auto-starts a fresh session exactly as page load does -- the
  auto-start path from C-013 is unchanged, just expressed as the startSession
  transition.
- [DECIDED] Session controls are secondary-styled (transparent, hairline
  border) so the loop's primary action (Submit/Next) stays visually dominant.
  Active state shows "Session <id>" + Restart + End; resting shows "No active
  session" + Start new session. Both states share one render path.
- [DECIDED] Streak pips hidden in the resting state (refinement from the
  render pass): the pip row is meaningful only for an in-progress run, so it
  is set visibility:hidden when there is no active session, leaving the bar
  reading cleanly as "nothing in progress".
- [DECIDED] Run-row streak labeled "final streak", not "best streak"
  (refinement): the backend's session_stats.streak is the current run length
  at the moment of ending, NOT the maximum achieved during the run. Calling
  it "best" would overstate the data. (No backend gives a max-streak; if a
  true best-streak is ever wanted it is a new DB query, deferred.)
- [DECIDED] beforeunload cleanup now targets state.activeSessionId (was the
  single sessionId). Resting state sends no beacon (nothing active); an
  active session is ended via sendBeacon on unload, unchanged in spirit from
  C-013.
- [DECIDED] endSession is resilient: a failed POST /api/session/end still
  marks the record ended locally and surfaces the message, rather than
  stranding the UI in a half-ended state. The server treats unknown ids as
  no-ops, so local-ended / server-failed cannot leak a usable dangling id.
- [NOTE] C-013 invariants intact: question_id passes through as JSON null;
  arithmetic sends no tolerance and no recent; one action button drives the
  loop by phase; Enter submits. Phase enum gained "resting".
- [NOTE] Boundary with C-019 unchanged and reaffirmed: C-014 reads nothing
  new from the server. The run log is purely the session_stats snapshots the
  client was already handed, held in memory for this visit only, and dies
  with the page (beforeunload). Durable, cross-visit, time-windowed history
  remains C-019 (GET /api/stats, still a 501 stub). No backend changes.
- [NOTE] Deferred to C-015 (unchanged): Escape-to-end and Enter/Space-to-
  advance. The end/restart/start actions now exist as functions
  (onEndSession/onRestartSession/onStartSession), so C-015 binds keys to
  them rather than building behavior.

---

## C-015  Keyboard control + empty-answer hint

Gives the drill a hands-on-keys rhythm and fixes a C-013-era silent failure.
Verified: C-013 (27) and C-014 (24) suites still pass unchanged, plus a new
C-015 keyboard suite (18 assertions), plus a live render of the hint state.
69 assertions total across the frontend.

- [DECIDED] One document-level keydown handler (onDocumentKey), gated strictly
  on state.phase, owns the global keys. Escape ends the active session from
  ANY active phase; Enter/Space advance ONLY in the feedback phase. The phase
  gate is what guarantees the global handler can never collide with the
  input's Enter-to-submit.
- [DECIDED] Escape means "I'm done with this run" (confirmed): it ends from
  answering OR feedback, discarding any unsubmitted input. No-op when there
  is no active session (resting).
- [DECIDED] Modal keys by phase (confirmed, "modal editing of sorts"): while
  answering, Enter belongs to the input (submit) and Space is a literal
  keystroke; while showing feedback, Enter/Space advance. The same physical
  key means different things by phase -- this is deliberate, documented in
  the file header so it is not mistaken for a bug.
- [DECIDED] Advance is one deliberate key, NOT a merge of submit+advance. The
  "two Enters" the user noticed (type, Enter to grade, then reach for the
  mouse / hunt for focus to continue) is resolved by making advance a single
  document-level Enter/Space that works regardless of focus -- so the rhythm
  is type -> Enter (grade) -> Enter (next). Submit and advance remain two
  distinct beats because the feedback moment (did I get it right?) is the
  point of the loop.
- [DECIDED] No double-advance / double-action guard: when a button is focused
  (the action button, or a session control like End/Restart), the global
  advance handler returns early and lets the button's NATIVE Enter/Space
  activation fire. It does not preventDefault in that case -- on a button,
  preventDefault on Space suppresses the native click and would swallow the
  action. The guard keys on event.target.tagName === "BUTTON". This prevents
  e.g. a focused "End session" from both ending AND advancing on one Space.
- [DECIDED] Category <select> keeps its native keyboard nav: onDocumentKey
  ignores events whose target is the selector.
- [DECIDED] Empty-answer feedback (the user's call-1 fix): submitting an empty
  / whitespace-only field was previously a SILENT refocus (no POST, looked
  like a broken button). Now it shows an inline hint "Enter a number to
  submit." directly under the input, cleared the instant the user types (an
  input listener) and on entering answering/resting. Still posts nothing, so
  the no-junk-rows invariant from C-013 is intact.
- [DECIDED] Hint placement (confirmed call-3): under the input, where the eye
  already is. The bottom note area stays reserved for errors. New
  .answer-hint element + helpers (setAnswerHint/clearAnswerHint), muted clay,
  reserves its line height so the stage does not jump when it appears.
- [NOTE] FUTURE COMMIT (noted, not built): a no-feedback "speed drill" mode
  where submit advances immediately and per-answer feedback is withheld until
  the run ends, concentrating feedback at session end rather than during the
  run. The user confirmed this is desirable eventually but out of scope for
  C-015: it changes the loop's meaning and needs extra state (a buffer of
  pending results to reveal at the end), so it is its own future commit. Not
  scheduled with a C-number yet; flag when ready to slot it (likely after the
  UI series, possibly alongside or after C-019 stats since it is feedback-
  presentation work).
- [NOTE] No backend changes; C-019 boundary untouched. C-013/C-014 invariants
  intact (null question_id, no tolerance/recent, one action button by phase,
  data-oriented session array). Phase enum unchanged from C-014 (idle,
  resting, loading, answering, feedback); C-015 only reads it.

---

## C-017  Import UI (upload a JSONL/CSV bank)

Built BEFORE C-016 (commit order swapped -- see note). A collapsed "Import a
bank" disclosure reveals a form that uploads a question bank to POST
/api/banks/import. Verified: C-013/014/015 suites still pass, a new C-017
suite (27 assertions), AND a live end-to-end import against the real drill.py
(imported 3 questions; the bank then appears via GET /api/banks with a real
question_id fetchable from it).

- [DECIDED] Order swap C-016 <-> C-017 (rationale recorded). A freshly seeded
  DB has categories but NO banks (verified: init_db seeds categories only).
  So C-016 (bank selection) built first would light up nothing and have
  nothing to drill -- unobservable and not live-testable, breaking the
  "every commit verifiable end to end" pattern (the reason MAIN was pulled
  forward in C-013a). C-017 (import) is what creates banks, and the
  dependency is asymmetric: C-016 needs banks (needs C-017), C-017 does not
  need the selector. So C-017 -> C-016 is the clean topological order. The
  spec commit list should be updated to reflect this (see spec note below).
- [DECIDED] Multipart, not JSON: POST /api/banks/import takes a file part +
  form fields, so onImportSubmit builds a FormData and posts it with fetch
  directly -- NOT the JSON apiPost helper. No Content-Type header is set, so
  the browser supplies the multipart boundary.
- [DECIDED] format field omitted from the upload: the server infers jsonl/csv
  from the file extension. Sent fields: file, category_id (required), and
  name/language only when non-empty.
- [DECIDED] Separate import-target category picker (lean confirmed), distinct
  from the top drill selector. Different intent: "where does this bank go" vs
  "what am I drilling". The import picker lists ALL categories including ones
  with no banks yet (every category is a valid import target); the top
  selector still gates non-drillable ones. Conflating them would violate one-
  meaning-per-surface.
- [DECIDED] Collapsed disclosure (lean confirmed): the panel is hidden behind
  a "+ Import a bank" toggle, built lazily on first open and rebuilt on each
  open so its category picker always reflects current categories. Import is
  an occasional action; the drill stage stays the focus.
- [DECIDED] On success (lean confirmed): show "Imported N question(s) into
  '<name>'" and silently refresh categories via refreshCategories(), which
  re-fetches /api/categories and re-renders the top selector (restoring the
  prior selection if still enabled). This un-gates a newly-drillable category
  without a reload -- the bridge to C-016, which reads the attached banks.
  Does NOT auto-switch the drill: switching would yank the user out of their
  run, and drilling the new bank is a C-016 action.
- [DECIDED] Errors: a missing file is guarded client-side ("Choose a file to
  import."). A server parse failure surfaces the backend's row-naming message
  verbatim (e.g. "line 3: record is missing a non-empty 'answer'") in the
  panel's own import-status area, NOT the global bottom note. Status is color-
  coded (ok = cyan, error = clay).
- [DECIDED] Format help is shown inline (required question+answer; optional
  qtype/alternatives/distractors/hints/tags/media_url/difficulty; JSONL = one
  object per line, CSV = header row with pipe-separated array cells) so a
  user can build a valid file without leaving the page. Mirrors the parser's
  actual contract (_normalize_question_dict), not a guess.
- [DECIDED] Global keyboard handler hardened (C-015 follow-through): added
  isFormControl() so onDocumentKey ignores keys from INPUT/SELECT/TEXTAREA/
  BUTTON (except the answer input, which keeps its own Enter-submit). Without
  this, Escape typed in the import name/language field would END the session,
  and Space would be hijacked. Verified by a test.
- [DECIDED] First-party user action, no confirmation gate: the user picks a
  local file through a file chooser and clicks a labeled "Import" button in a
  UI they drive. The click is the confirmation; this is not an agent acting
  on observed content, so no extra confirm step is added. The action is
  explicit (labeled button, clear about what it does), not auto-submit-on-
  pick.
- [NOTE] Found while testing (not a product bug): the real drill.py routes
  only GET / for index.html; there is NO /index.html route (returns 404).
  The live page must be opened at the root (matches the run instructions).
  My earlier local screenshots used a static file server that served by
  path, which masked this; harnesses must hit / against drill.py.
- [NOTE] No backend changes; /api/banks/import was already complete. C-019
  boundary untouched. C-016 is next and now has real banks to select and
  drill (free_response/translate/identify text input + multiple_choice option
  rendering, real question_id passthrough, recent= last-10 window).
- [SPEC] The spec commit list still shows C-016 (bank selection) before C-017
  (import). Recommend swapping those two lines to match the built order, with
  a one-line note that the swap was for live-testability (banks must exist
  before selection is meaningful). Left for the next spec-edit pass.

---

## C-016  Bank selection + drilling non-arithmetic categories

The meatiest UI commit: makes the non-arithmetic categories drillable, adds
the bank selector, multiple-choice rendering, the recent= window, and fixes
the C-017 gray-dropdown bug. Verified: all four prior suites still pass, a new
C-016 suite (33 assertions), and a live import-then-drill against the real
drill.py (import a bank -> category un-gates -> select it -> drill text and
multiple_choice questions -> answers logged with real question_ids). Two
layout bugs were found via the live screenshot and fixed (below).

- [DECIDED/FIX] The banks data layer is the fix for the user-reported gray
  dropdown. /api/categories does NOT carry banks (verified:
  _category_row_to_dict returns only id/name/description/config). The C-013
  gate predicate reads category.banks, which nothing populated -- so an
  imported category stayed gated. fetchAndAttachBanks() now fetches
  /api/banks once, groups by category_id, and attaches a `banks` array to
  each category. The predicate is UNCHANGED since C-013 (as designed: "C-016
  turns the rest on by populating banks, not by editing the gate").
  refreshCategories() (after import) re-fetches banks too, so the category
  un-gates immediately -- this is the precise fix for the symptom.
- [DECIDED] Bank selector appears under the category selector only for a
  non-arithmetic drillable category (hidden for arithmetic, which has no
  banks). Selecting a category auto-selects and drills its first bank;
  selecting a bank switches to it.
- [DECIDED] Selection model: state.selection = {categoryId, categoryName,
  bankId|null, bankName|null} is the drill target. startSession reads it,
  sends bank_id to /api/session/start for bank categories, and stamps the
  session record with bankId/bankName. Arithmetic keeps bankId null and its
  C-013 auto-start.
- [DECIDED] Switching category or bank mid-run ends the current run (preserved
  in the log, per C-014) and starts a fresh one -- a deliberate "new run",
  like Restart (lean confirmed). switchSelection() centralizes this.
- [DECIDED] Bank questions send the REAL question_id to /api/answer (not the
  arithmetic null), plus qtype and alternatives (text qtypes). Verified the
  id round-trips so responses.question_id is a proper FK, not NULL.
- [DECIDED] recent= window: last RECENT_MAX=10 served bank question ids per
  session (lean confirmed), reset on each startSession so ids never leak
  across sessions. Sent as recent=a,b,c on the bank question fetch; arithmetic
  sends none. pushRecent caps the list.
- [DECIDED] Multiple-choice rendering (requested now): for qtype
  multiple_choice the server's shuffled `options` render as clickable choice
  buttons IN PLACE OF the text input; clicking submits that option's text via
  the same gradeAndShow path. After grading, the correct option is marked
  cyan and a wrong pick clay. submitAnswer (text) and submitChoice (MC) share
  gradeAndShow so the answer contract is identical.
- [DECIDED] Question render branches on qtype: text input for arithmetic and
  free_response/translate/identify (numeric inputmode for arithmetic, text
  otherwise; placeholder "answer" vs "your answer"), choices for
  multiple_choice. Long bank prose uses a smaller .expression.prose size so a
  full sentence does not blow out the stage.
- [DECIDED] Empty-hint text adapts: "Enter a number" for arithmetic, "Enter an
  answer" for word qtypes.
- [FIX] Stage overflow overlap (found in live screenshot): .stage used
  justify-content: center with a min-height; a 4-option MC question exceeds
  that height, and centering OVERFLOWING content pushed the top items UP out
  of the stage, overlapping the stats bar. Changed to justify-content:
  flex-start so content always flows downward from the stage top. Short
  arithmetic still looks balanced via padding.
- [FIX] hidden-attribute vs display:flex (found in live screenshot): the MC
  question still showed the text input because .answer-row { display: flex }
  overrides the `hidden` attribute (UA display:none loses to a class rule).
  Added [hidden] { display: none } guards for .answer-row and .choices (the
  bank-selector already had one). This is a general gotcha: any element styled
  with an explicit display that also toggles via the hidden attribute needs
  the [hidden] guard.
- [DECIDED] Folded-in tweaks (from the user's C-017 observation): the import
  panel auto-collapses ~1.2s after a successful import (kept open on error so
  the user can fix and retry), returning focus to the drill. Run-log rows now
  name the bank ("vocabulary / spanish #N") since runs are category+bank.
- [DECIDED] fetchAndAttachBanks is non-fatal in boot: if /api/banks fails,
  categories stay bank-less and only arithmetic is drillable, rather than
  aborting boot. Arithmetic must always work.
- [NOTE] Found while testing (not a product bug, reaffirms C-017 note): the
  live page is served only at GET / (no /api/index.html route). Harnesses
  must navigate to /.
- [NOTE] No backend changes. C-019 boundary intact: C-016 reads
  /api/categories, /api/banks, /api/question, /api/answer, /api/session/*;
  GET /api/stats remains the 501 stub. The full UI series is now done except
  C-018 (TTS) and C-019 (stats view).

---

## C-016a  Multiple-choice layout + advance patch (bug fixes)

Three issues reported from live use (screenshots) on the C-016 multiple-choice
path, all now fixed and regression-guarded (new test_mc_patch: 12 assertions;
all prior suites still green; verified live with positional measurements
proving no overlap).

- [FIX] No Next button on multiple_choice. Root cause: the action button lived
  INSIDE #answer-row, which C-016 hides (display:none) for MC -- so the button
  was hidden with it, and after answering an MC question there was no visible
  advance control (keyboard Enter/Space still worked, but nothing on screen).
  Fix: moved the action button OUT of #answer-row to be a direct stage child.
  enterAnswering now hides the button for MC (a choice click submits; there is
  nothing to "submit") and enterFeedback shows it as "Next" for all qtypes --
  so the advance affordance returns in the feedback phase. For text qtypes the
  button behaves exactly as before (Submit -> Next).
- [FIX] Choices overlapped the run-log / feedback. Root cause: .stage was a
  flex column item with the default flex-shrink:1 and a fixed min-height:14rem;
  on a short page the flex layout compressed the stage BELOW its content
  height, so the choices + feedback overflowed the stage box downward and the
  next sibling (#run-log) was positioned against the stage's compressed box,
  landing on top of the overflowing content. Fix: .stage now has
  flex-shrink:0 and no fixed min-height, so it always grows to contain its
  content; later siblings sit below it. Verified live: with run-log history
  present, feedback bottom 710 < stage bottom 742 < run-log top 766 (no
  overlap). (The earlier C-016 justify-content:flex-start change was necessary
  but not sufficient; flex-shrink:0 is the actual fix.)
- [FIX] Feedback (right/wrong message) was blocked. Same root cause as the
  overlap; resolved by the same flex-shrink:0 fix -- the feedback div now sits
  in the stage flow below the Next button, fully visible.
- [NOTE] General gotcha reaffirmed: any element styled with an explicit
  `display` that also toggles via the `hidden` attribute needs a
  `[hidden]{display:none}` guard (added for button, alongside the existing
  ones for .answer-row, .choices, .bank-selector). And in a flex column,
  content-sized panels that must not be compressed need flex-shrink:0.
- [NOTE] No backend changes. This is a UI-only patch to C-016 (filed as
  C-016a). The remaining commits are unchanged: C-018 (TTS) and C-019 (stats
  view + stats DB queries), plus the still-unscheduled no-feedback speed-drill
  mode.

---

## C-018a  TTS pronunciation (click-to-hear), frontend only

First TTS commit. Adds a speaker button to the question stage that reads the
prompt aloud for language questions, using the browser SpeechSynthesis API.
Frontend-only: NO backend change (the question payload is unchanged; language
is sourced from the already-fetched bank selection). Verified with a jsdom
harness driving the real index.html against stubbed fetch + speechSynthesis
(21 assertions across four scenarios: language-question show+speak+lang,
qtype/null-language gating, stale-speech cancellation, and speech-absent
degradation), plus a 6-assertion arithmetic-loop regression smoke test (no
regression) and an ASCII-only check.

- [DECIDED] Language source is the BANK (the drill target), resolved on the
  client from state.selection.bankId against the banks attached to
  state.categories by fetchAndAttachBanks() (C-016) -- activeBankLanguage().
  The /api/question payload carries no language field, and we did NOT add one:
  this keeps C-018a genuinely frontend-only and respects the backend freeze.
  Language is arguably a property of the chosen bank, not of each question, so
  sourcing it from the selection is also the more correct model. The
  alternative (thread language through the payload) is deferred and scaffolded
  as a pure comment block in C-018b. (Option B in the analysis; accepted.)
- [DECIDED] speechSynthesis is QUARANTINED behind speak()/cancelSpeech() --
  the only two functions in the file that touch window.speechSynthesis. This
  follows the codebase's edge-IO-quarantine pattern: the global is stateful,
  async, and mutable (the opposite of the single-source-of-truth model), so it
  is fenced off rather than sprinkled through render code.
- [DECIDED] We do NOT enumerate voices via getVoices(). That call returns []
  until an async 'voiceschanged' event fires (the well-known Chrome
  voices-load bug), which would race the first click. We set utterance.lang
  and let the engine pick a matching voice -- it honours lang without
  getVoices(), sidestepping the race. Simpler and more robust.
- [DECIDED] Feature-detected ONCE at load (speechAvailable). If absent, the
  speaker is never shown and speak() is a no-op -- a visible-but-dead control
  is worse than none. The user-gesture requirement some engines impose is
  satisfied naturally (speech is click-triggered, never autoplay).
- [DECIDED] Show predicate canSpeakCurrent(): speech available AND qtype is
  translate or identify AND activeBankLanguage() is non-null. Explicitly NOT
  multiple_choice (its prompt is usually an L1 question), NOT arithmetic, NOT
  plain free_response (English trivia prompts). Speaks question_text only --
  never the answer or feedback (would undercut the drill). Data-derived and
  explicit, in the spirit of isDrillable().
- [DECIDED] Banks may have a null language (trivia/geography/logic/code, or
  vocab imported without a language= field). activeBankLanguage() returns null
  gracefully and the button stays hidden in that case.
- [DECIDED] Stale-speech: cancelSpeech() is called at the top of loadQuestion
  (every question transition), in endSession (a run ending), and in
  endSessionOnUnload (page close), so a prior word never talks over a new
  question or lingers past the run.
- [DECIDED] Keyboard safety: onSpeakerClick() calls el.speaker.blur() right
  after speaking, returning focus off the control. This preserves the C-015
  Space-to-advance contract -- a focused button would activate on Space
  (re-speak) instead of advancing, the same double-fire trap C-016a fought.
  The button is also a <button>, so isFormControl() already keeps the global
  keydown handler from hijacking its keys; blur is the belt-and-suspenders.
- [DECIDED/FIX, folded in] The hidden-vs-explicit-display gotcha (documented in
  C-016/C-016a): the speaker uses display:inline-flex and toggles via the
  hidden attribute, so it needs a [hidden]{display:none} guard. The existing
  button[hidden]{display:none} rule (added in C-016a) already covers it, and a
  dedicated .speaker[hidden]{display:none} was added alongside for clarity.
  Per the agreed plan, the guard is folded into this commit rather than a
  separate patch commit.
- [NOTE] No backend changes; drill.py untouched and still frozen. C-019
  boundary intact (GET /api/stats remains the 501 stub). Endpoints used are
  unchanged from C-016. Remaining: C-018b (Option-A comment-block scaffold),
  C-018c (timing collection), C-019a/b (stats query + view).
- [NOTE] ASCII-only preserved: the play glyph on the button is the HTML
  entity &#9658; (ASCII source), not a literal Unicode triangle.

---

## C-018b  Option-A per-question-language scaffold (comment-only)

Documents, but does not build, the deferred "Option A" path for TTS: threading
a bank/question language code through the GET /api/question payload. C-018a
ships TTS by resolving language on the CLIENT from the selected bank, so the
backend payload carries no language field and the backend stays frozen. This
commit records the gap and the future implementation steps in-place so a later
reader is not surprised.

- [DECIDED] Comment-block ONLY -- zero executable backend code. Verified by AST
  comparison against the pre-C-018b drill.py: the sole AST-level difference is
  the module docstring (a header status note); every executable statement and
  every function/class docstring is byte-identical, and the two inline scaffold
  blocks are pure comments invisible to the AST. A behavioral check confirms
  build_question_payload still emits the same payload shape with NO "language"
  key. (User instruction: "leave as pure comment block.")
- [DECIDED] Two scaffold sites, placed where the future code would live:
  (1) inside build_question_payload, after the payload dict, spelling out the
  three steps Option A would take (carry a language in -- via a new
  per-question column/metadata key or a bank_language= parameter; have the
  handler pass it; update the section-6 contract + frontend to prefer
  payload.language over the client lookup); and (2) at the bank-question
  handler's build_question_payload(chosen) call, where bank_id is in scope and
  the bank row (with banks.language) would be fetched and passed down.
- [DECIDED] Why Option A is deferred, not chosen: C-018a's client-side
  bank-language lookup covers every bank we actually have (language is a
  bank-level property today). Option A only matters when language is a property
  of the QUESTION rather than the bank -- a mixed-language bank or per-row
  override -- which we do not have. Building it now would change the frozen
  backend AND the API payload contract, so per working agreement 11 it needs
  its own spec amendment + commit. The scaffold makes that future work cheap to
  pick up without paying for it now.
- [NOTE] No schema change, no endpoint change, no contract change. drill.py
  remains frozen in every executable respect; GET /api/stats is still the 501
  stub. Remaining: C-018c (timing collection, frontend), C-019a/b (stats).
- [NOTE] The header status paragraph in drill.py still says MAIN/stats arrive
  "with C-019"; that line predates the C-013a MAIN move and was left as-is
  (correcting it is outside C-018b's comment-only scope). The new C-018b note
  in the same header is accurate.

---

## C-018c  Per-answer timing collection (elapsed_ms), collect-only

Begins collecting per-answer timing. Frontend-only: the backend already has
the full plumbing (responses.elapsed_ms column, insert_response's elapsed_ms
param, /api/answer parsing it via the hardened _optional_int and storing it),
verified by an end-to-end round-trip (2500 ms persisted through the DATABASE
layer). Until now nothing sent the field, so every prior row has elapsed_ms
NULL; this commit closes that from the client.

- [DECIDED] elapsed_ms means THINK+TYPE time: from when the question becomes
  answerable (enterAnswering) to submit. Measured with performance.now() (via
  a nowMs() helper that falls back to Date.now()) -- monotonic, so it is
  immune to wall-clock changes, the correct tool for durations. Captured at
  SUBMIT time, before the network round-trip, so it excludes grading latency.
  (Definition 1 in the analysis; accepted.)
- [DECIDED] Retry-after-error RE-TIMES. On a failed /api/answer, gradeAndShow's
  catch calls enterAnswering, which restarts the mark; so a retry measures the
  successful attempt only and excludes the failed round-trip. Test confirms:
  5000 ms failed attempt then 900 ms retry sends elapsed_ms=900, not 5900.
- [DECIDED] An EMPTY submit does not consume or reset the mark (submitAnswer
  early-returns before gradeAndShow), so the timer keeps running while the user
  is still thinking. Test confirms a 1200 ms empty submit then 800 ms more
  sends elapsed_ms=2000 (counted from question start).
- [DECIDED] COLLECT-ONLY. No code computes or displays timing in v1. The data
  simply accumulates so a future timing feature has real history. Per the plan
  this is its own micro-commit precisely so "collection began at C-018c" is a
  clean line in the history (the future analysis cares when collection started).
- [DECIDED] Defensive guards: elapsed_ms is sent only when a valid measurement
  exists (mark non-null); a negative diff (clock anomaly) is dropped rather
  than recorded; the mark is cleared after each submit and on loadQuestion so a
  stale value cannot leak into a later answer. The field stays optional on the
  wire, matching the server's _optional_int handling.
- [DECIDED] Both answer paths are covered: typed (submitAnswer) and
  multiple_choice (submitChoice) both flow through gradeAndShow, and both set
  the mark in the shared enterAnswering, so timing is uniform across qtypes.
- [NOTE] No backend change; drill.py byte-identical to its C-018b state. GET
  /api/stats still the 501 stub. Verified: jsdom timing suite (19 assertions),
  C-018a suite (21) and arithmetic regression smoke (6) still green, ASCII-only
  preserved. Remaining: C-019a (stats query + summary + endpoint), C-019b
  (stats view). The C-019a stats query may SELECT elapsed_ms but summarize_stats
  ignores it in v1 (timing calculation stays deferred).

---

## C-019a  Stats DB query + pure summary + GET /api/stats (the sanctioned unfreeze)

Implements the durable cross-session stats endpoint -- the one backend change
sanctioned after the section-11 freeze. Three pieces across the three layers,
following the established C-011 split (DB returns rows, LOGIC computes the
summary, HTTP reads the clock and glues). Verified by a 33-assertion test
against the real drill.py over a temp DB: DB reader filters/ordering/elapsed
carriage, pure summary (totals/accuracy/breakdown/empty/determinism/elapsed
ignored), and the handler end to end via WSGI (all-time, category filter, day
window, window echo, four 400 cases, empty-category 200). The three frontend
suites still pass and index.html is untouched (this commit is backend-only).

- [DECIDED] DATABASE.get_responses_for_stats(conn, category_id=None,
  since=None) joins responses -> sessions -> categories and returns plain
  dicts {correct, elapsed_ms, answered, category_id, category_name}, ordered
  answered DESC, id DESC (newest-first, matching the view's render order). Both
  filters are optional and AND-combined: category_id restricts to one
  category; since is an inclusive ISO lower bound on responses.answered. It is
  a pure reader -- only filtering, no aggregation -- so all computation stays
  in LOGIC (the C-011 correctness split, generalized).
- [DECIDED] elapsed_ms is SELECTed and carried in every row so the deferred
  timing feature can use it WITHOUT a new query, but it is the only stats input
  LOGIC ignores in v1. This is the agreed "collect/plumb now, calculate later"
  posture: C-018c began collecting it; C-019a makes it queryable; no metric
  reads it yet.
- [DECIDED] LOGIC.summarize_stats(rows) is pure and deterministic: total,
  correct, accuracy (0.0 when total 0), and a per-category breakdown
  [{category_id, category_name, total, correct, accuracy}] sorted by
  descending total then name (a stable tiebreak, so the same rows always
  summarize identically regardless of input order). The empty case yields
  zeros and [] -- the time-zero case handled like summarize_correctness, not
  asserted away. No charts, no timing (section 9 text-only v1).
- [DECIDED] GET /api/stats query params (both optional): category_id and days,
  parsed via the existing _optional_int (-> _BadParameter -> 400), matching the
  hardening pass. days <= 0 is a 400 with a clear message (a zero/negative
  window is malformed, NOT "all time"; omit the param for all time). Omitting
  both means all categories, all time.
- [DECIDED] The day-window cutoff is computed in the HANDLER from the clock
  (utc_now_iso() - timedelta(days=N)) and passed to DATABASE as an ISO string,
  so neither DATABASE nor LOGIC reads the clock -- the boundary invariant
  (only HTTP + init_db touch the clock) is preserved. Comparison is
  string-vs-string in one ISO 8601 UTC format (responses.answered is written
  by the same utc_now_iso()), which is correct for same-offset timestamps.
  Added `timedelta` to the existing datetime import (no new dependency).
- [DECIDED] Response shape: {total, correct, accuracy, categories:[...],
  window:{category_id, days, since}} where window echoes the effective filter
  (since is the ISO cutoff or null) so the C-019b view can show what it is
  displaying without re-deriving it.
- [DECIDED] The live stats BAR and this endpoint stay separate sources: the
  bar is fed only by session_stats on /api/answer (C-013, in-memory, current
  session); /api/stats is durable DB history. C-019a does not touch the bar or
  the answer handler. The streams are not crossed (preserving the C-013/C-014
  single-source-of-truth for the bar).
- [FIX, in scope] Corrected now-stale status comments that C-019a's existence
  invalidates: the file header ("complete through C-012 ... except /api/stats"
  -> "through C-019a, including /api/stats"), the get_session_correctness
  docstring (pointed "remains in C-019" at the now-built get_responses_for_stats
  /summarize_stats), the HTTP-section header ("except GET /api/stats" -> "incl.
  GET /api/stats"), and the MAIN-section comment ("Partial C-019 ... /api/stats
  is still a 501 stub" -> notes the endpoint landed in C-019a, only the view
  remains). The earlier-flagged "MAIN arrives with C-019" header line is now
  fixed as part of this. drill.py MAIN block itself is unchanged in behavior.
- [NOTE] Remaining work: C-019b (the stats view UI that calls this endpoint).
  That is the last commit in the initial plan.

---

## C-019b  Stats view UI -- the final commit of the initial plan

Adds the durable stats view that consumes C-019a's GET /api/stats. Frontend
only: drill.py is byte-identical to its C-019a state. Verified by a 23-assertion
jsdom suite (open/render, empty state, close teardown, single-category skip,
window echo, fetch-error note, independence from the live bar) AND a
6-assertion integration test that drives the real index.html view against the
REAL drill.py /api/stats handler over a seeded temp DB (7/6/86% all-time; the
day window correctly excludes a 20-day-old row -> 6/5/83%). All prior suites
(C-018a 21, C-018c 19, C-019a 33, smoke 6) still green; ASCII preserved.

- [DECIDED] Mirrors the import disclosure exactly: a quiet full-width toggle
  (aria-expanded/aria-controls) over a soft panel built on open and torn down
  on close. Same CSS family (.stats-toggle/.stats-panel echo
  .import-toggle/.import-panel) so the two disclosures read as siblings.
- [DECIDED] Re-fetched on EVERY open (no client cache): the panel must reflect
  answers logged since it was last viewed, including the current session's.
  Closing clears the panel DOM. A fetch in flight when the panel is re-closed
  is dropped (render guarded on aria-expanded still being "true").
- [DECIDED] Strictly SEPARATE from the live stats bar. The bar is fed only by
  session_stats on /api/answer (renderStats, in-memory, current session); this
  panel is DB history from /api/stats. They share no state and no render path;
  the test asserts the bar is untouched (still 0) while the panel shows history.
  This preserves the C-013/C-014 single-source-of-truth for the bar.
- [DECIDED] Renders the C-019a shape directly: an overall row (answered /
  accuracy / correct) plus a per-category breakdown. The breakdown arrives
  pre-sorted by the endpoint (most-practiced first), so it renders in order
  as-is -- no client re-sort. The breakdown is skipped when there is only one
  category (the overall line already says it). Text-only, no charts (section 9).
- [DECIDED] Empty/time-zero (total 0) shows a friendly "no answers recorded
  yet" note rather than a wall of zeros -- matching summarize_stats's zero
  handling on the backend.
- [DECIDED] Window echo: when a filter is active (days and/or category), a
  muted note ("Showing last 7 days, category: vocabulary") reads the window the
  endpoint echoes back, resolving category_id to a name via state.categories.
  v1 always fetches unfiltered (all categories, all time), so the note is
  normally absent; the rendering supports filters so a future control (a
  category/day picker) needs no view changes, only the fetch query.
- [DECIDED/FIX, folded in] The hidden-vs-explicit-display gotcha: the panel
  toggles via the hidden attribute, so .stats-panel[hidden]{display:none} is
  included. The old "#stats-view{display:none}" placeholder rule (which would
  have kept the whole disclosure hidden) was removed -- the disclosure
  container is always visible; only its panel toggles.
- [NOTE] Timing (elapsed_ms) is intentionally NOT shown. It is collected
  (C-018c) and queryable (C-019a SELECTs it) but the timing feature stays
  deferred; the view surfaces none of it.
- [MILESTONE] This completes the initial plan. Every commit C-001..C-019b is
  done (with C-013a/C-016a inserted and C-018/C-019 split into a/b[/c]). The
  only remaining noted-but-unscheduled item is the no-feedback "speed drill"
  mode, which was always outside the initial plan.
C-020 - Permanent test suite (THREAD-TEST, T1).

Formalized the harvested C-018a..C-019b harnesses into tests/, organized by concern (logic / db / http / generator-property + frontend), 159 assertions green. Harness-only: zero changes to drill.py / index.html.

Decisions: JS suites keep the dependency-free hand-rolled scorer rather than node:test (Pattern 4); Python side is pytest. Test deps live in [dependency-groups] test, not runtime dependencies; the wheel still ships only drill.py + index.html.

Two behavioral asymmetries the suite surfaced and now pins (note for downstream threads):

GET /api/question?operators= (empty value) returns 200 - the handler treats an empty string as "omitted, use all operators." Only operators=,, (present but parsing to no symbols) is a 400. Relevant to A1/A2 if operator handling changes.
normalize_text strips an apostrophe at an answer's ends (surrounding-quote stripping) but preserves it interior (don't  don't). Accents and interior hyphens are likewise preserved by the C-007 accent-sensitivity decision. Relevant to any thread touching normalization or adding accent_insensitive.

validate_answer's qtype dispatch is the seam for the future grading-kind enum (D1); it is now test-covered, so D1 can refactor against a green net.


C-021 - Encoding fix: test_logic.py accent literals (THREAD-FIX).

The accent-sensitivity tests (test_normalize_preserves_accents,
test_validate_translate_is_accent_sensitive) carried the intended lowercase
e-acute as a raw 0x82 byte -- a CP1252 encoding of the character that is
invalid as UTF-8. Python could not decode the source file, so pytest aborted
at COLLECTION: all 84 backend assertions failed to run and a clean clone at
21b5b57 reported only 75 green (frontend) instead of 159. The frontend suite
was unaffected.

Fix is encoding-only, no behavior change. The three "caf" + 0x82 literals are
now written "caf\u00e9" (an ASCII \u escape for U+00E9). normalize_text
lowercases and preserves accents (C-007), so the lowercase escape matches the
existing contract exactly; the assertions and their meaning are unchanged.
Harness-only: zero changes to drill.py / index.html, and no other test
changed. After the fix the suite is back to 159 green ("ALL GREEN").

Guidance for downstream threads: keep non-ASCII test data as \u escapes, not
literal high bytes, so the source stays valid UTF-8 (and ASCII-only). An
accent_insensitive bank flag, if ever added, would relax the C-007 contract
these two tests pin -- update them together if so.


C-T2 - Schema migration runner (THREAD-MIGRATE, T2, wave 0).

Builds the forward-only migration mechanism so every later thread can evolve
drill.db's schema without losing a user's data (the .db file IS their backup).
Adds _apply_one, run_migrations, the MIGRATIONS registry, the SCHEMA_VERSION
drift guard, and the MAIN startup wiring. MIGRATIONS ships EMPTY: this thread
delivers the mechanism, not any migration (the grading-kind/metadata columns
are D1's job). Backend 84 -> 100 (+16 in tests/test_migrate.py); frontend 75
unchanged; total 159 -> 175, "ALL GREEN". No endpoint contract, no existing
schema column, and no LOGIC/HTTP behavior changed.

ADR-021: version mechanism -- KEEP the schema_version table; do NOT switch to
PRAGMA user_version.
- [DECIDED] The schema_version table (version, applied) already shipped in
  C-002 and is read by get_schema_version. We extend that mechanism rather
  than re-pick. Justification beyond "it already exists": the table keeps one
  ROW PER applied version with an `applied` ISO-8601 timestamp -- a provenance
  / audit trail of every schema transition. PRAGMA user_version is a single
  integer that discards that history. For a single-user tool whose only data
  copy is the file, the audit trail is worth more than the scalar's simplicity.
- [REJECTED] PRAGMA user_version. It would mean abandoning a shipped table and
  re-stamping every existing drill.db, which fights the "do not lose data"
  requirement for zero gain over the table we already have.

ADR-022: init_db reconciliation -- init_db STAYS the version-1 baseline; the
runner LAYERS on top (option B).
- [DECIDED] init_db keeps creating today's schema (CREATE TABLE IF NOT EXISTS)
  and stamping version 1; the runner applies versions 2..N. Both fresh and
  existing databases reach the current version by ONE startup path: MAIN calls
  init_db then run_migrations on the same connection. Fresh -> init_db builds
  v1, runner advances; existing-at-vN -> init_db is a stamp-once/IF-NOT-EXISTS
  no-op, runner advances from vN. Migration version numbering is SCHEMA-DRIVEN:
  the registry must be the gap-free sequence range(2, SCHEMA_VERSION+1), checked
  at import by _check_migration_version_consistency so the constant and the
  registry cannot silently drift.
- [REJECTED] Option A (runner owns everything; migration 1 IS the baseline that
  creates today's schema, init_db becomes a thin wrapper). Conceptually cleaner
  -- one expression of schema change -- but it relocates the v1 DDL out of
  init_db/SCHEMA_STATEMENTS into a migration, a larger diff with more risk to
  the green baseline for no T2 benefit. Left as a possible future consolidation.

ADR-023: transaction discipline -- the runner drives BEGIN/COMMIT/ROLLBACK
explicitly. NON-OBVIOUS, do not "simplify" away.
- [DECIDED] _apply_one issues an explicit BEGIN before the migrate callable and
  COMMIT/ROLLBACK around it. Reason, verified empirically before coding: under
  Python's legacy sqlite3 isolation (the default that connect() returns), a DDL
  statement such as ALTER TABLE is NOT preceded by an implicit transaction, so
  it autocommits and SURVIVES a later rollback(). Relying on implicit handling
  would make a half-finished migration permanent -- the opposite of the
  forward-only, last-good-version guarantee. The explicit BEGIN puts the DDL in
  a transaction we control. A future thread that "tidies up" by removing the
  explicit BEGIN/COMMIT, or that switches connect() to isolation_level=None
  globally (which would change HTTP/LOGIC behavior), reintroduces the bug; the
  test_run_migrations_stops_at_last_good_version_on_failure case guards it.
- [DECIDED] Clock stays at the MAIN boundary: run_migrations takes `now` as a
  parameter and MAIN supplies utc_now_iso(); the DATABASE layer does not read
  the clock (consistent with the C-002 / item-8 convention; init_db remains the
  one sanctioned exception for its own stamp).

Out of scope, noted for later: a `description` column on schema_version (so the
table reads as a full audit log of what each version did) would be ADR-021's
provenance idea taken further -- but adding it is itself a schema change, i.e. a
migration, i.e. D1+ territory, not T2's mechanism-only remit.

--- HANDOFF: how D1 (and any later thread) adds a migration ---------------------

To add a schema change, you do exactly three things in drill.py and never touch
the runner (_apply_one / run_migrations). The runner discovers your migration
through the MIGRATIONS list; the import-time guard enforces that you did all
three consistently.

1. Write a migrate function in the DATABASE section. It takes the connection and
   performs ONLY the schema change -- additive DDL and/or a data backfill. It
   MUST NOT commit, rollback, or touch schema_version; the runner owns the
   transaction and stamps the version row for you.

     def _migrate_2_add_grading_kind(connection):
         """v2: add questions.grading_kind and banks.metadata_extra."""
         connection.execute(
             "ALTER TABLE questions ADD COLUMN grading_kind TEXT NOT NULL "
             "DEFAULT 'exact'"
         )
         connection.execute(
             "ALTER TABLE banks ADD COLUMN metadata_extra TEXT NOT NULL "
             "DEFAULT '{}'"
         )

   Use additive changes with NOT NULL DEFAULT so existing rows get a value
   (SQLite backfills the default). Existing user data must survive -- the .db
   file is the user's only copy.

2. Append one entry to the MIGRATIONS list, in version order:

     MIGRATIONS: list[tuple[int, str, object]] = [
         (2, "add questions.grading_kind and banks.metadata_extra",
          _migrate_2_add_grading_kind),
     ]

   The version must be the next integer (gap-free from 1: first is 2, then 3,
   ...). The description is the operator-facing string printed at startup.

3. Bump SCHEMA_VERSION to match the highest migration version:

     SCHEMA_VERSION: int = 2

   If you forget this (or add the migration without it, or vice versa), the
   import-time _check_migration_version_consistency raises and every test fails
   at collection -- the drift is caught immediately, not in production.

Then add a DATABASE-tier test in tests/test_migrate.py that runs your migration
over a temp DB (use the real MIGRATIONS, not an injected list) and asserts the
new column exists with its default AND that a pre-existing row survived. Run
bash tests/run.sh; the runner picks up the new test by glob (no run.sh edit).
Startup will print "drill: applied migration 2 (...)" then "schema migrated
1 -> 2" the first time each existing drill.db is opened after your change.

That is the whole procedure: write migrate fn, append tuple, bump constant, add
test. The runner, the transaction safety, the version stamping, and the
operator message are already handled.

================================================================================
D1 (thread-model wave 1): the first real migration -- questions.metadata
================================================================================

ADR-024: WHICH table gets metadata -- questions.metadata (NOT banks).
- [DECIDED] D1 adds ONE additive column: questions.metadata TEXT NOT NULL
  DEFAULT '{}'. banks.metadata ALREADY EXISTS in the v1 baseline
  (SCHEMA_STATEMENTS); questions had no metadata column, so this fills the real
  gap. The column is a deliberately UNCOMMITTED structured-extras hatch: later
  threads (difficulty tuning, SM2 scheduling state, new drill types) can stash
  per-question state here experimentally before any of them earns a dedicated,
  typed column. Additive + NOT NULL DEFAULT means every pre-existing row
  backfills to {} with no data loss (the .db file is the user's only copy).
- [DECIDED] SURFACING CEILING: metadata is surfaced at the READER level only --
  _question_row_to_dict parses it to a dict, so get_question / list_questions
  return it. It is NOT forwarded into build_question_payload's client payload:
  that allowlist guards the frozen section-6 payload contract (see the C-018b
  scaffold note in build_question_payload). When a real consumer needs metadata
  client-side or at grading time, that thread threads it through the payload +
  validation seam as its own change. "Surface now" therefore means
  readable-through-the-readers, not load-bearing in the answer hot path.
- [FINDING] The handoff procedure's worked EXAMPLE (below, "how D1 adds a
  migration") used banks.metadata_extra -- a column on the wrong table that
  also duplicates the existing banks.metadata. The PROCEDURE (write fn, append
  tuple, bump constant, add test) was mechanically correct and followed
  verbatim; only its illustrative column was wrong. Correct the example for D2+.

ADR-025: grading_kind -- DEFERRED to adaptive selection / SM2 (roadmap #7,
Phase 4). Not added in D1.
- [DECIDED] The original D1 brief paired a grading_kind column with metadata.
  It is intentionally NOT added. Reasoning: grading_kind would be a persisted
  GRADING-POLICY axis, but its only real consumer is adaptive selection / SM2,
  which consumes grading RESULTS (a quality grade), not the judging policy --
  so folding in SM2 does not create a consumer for grading_kind. SM2's actual
  per-question state is scheduling state (ease, interval, repetition,
  next-review), a DIFFERENT column set, slated for its own later migration after
  #7 (roadmap: "SM2 fields" + "reconciling two schemas and two notions of a
  review"). Adding grading_kind now is speculative: its semantics (new axis vs
  denormalization of the qtype dispatch) and even its home (questions vs bank vs
  category) are unsettled, and forward-only migrations make a wrong guess
  unrollable. The cheapest version of a speculative column is the one not yet
  added; questions.metadata already provides an uncommitted hatch to prototype
  in meanwhile.
- [RECONSIDER WHEN] roadmap #7 (adaptive selection) lands and SM2 (Phase 4)
  begins. At that point, against a real selection seam and a real caller,
  decide whether a persisted grading axis is needed at all and what shape it
  takes; if so, fold it in WITH the SM2 scheduling fields as a single migration.
  Must NOT fork validate_answer's qtype dispatch -- any such column FEEDS that
  single dispatch, it does not duplicate it. Flags left in code: see the
  DEFERRED note in _migrate_2_add_questions_metadata (drill.py) and the roadmap
  note for #6/#7.

ADR-026: init_db stamps a FIXED baseline (BASELINE_SCHEMA_VERSION = 1), not the
moving SCHEMA_VERSION. Upholds ADR-022; fixes a latent defect the bump exposed.
- [DECIDED] init_db stamps BASELINE_SCHEMA_VERSION (1) -- the version of the
  schema it actually builds (SCHEMA_STATEMENTS) -- as its own named constant,
  distinct from SCHEMA_VERSION (the current ceiling, reached by baseline +
  migrations). ADR-022 already required "init_db stamps version 1"; the code had
  stamped SCHEMA_VERSION, which was equal to 1 only while there were no
  migrations. The D1 bump to SCHEMA_VERSION = 2 made init_db stamp 2 on a fresh
  DB, so run_migrations (which applies only versions GREATER than the stamped
  one) skipped the v2 migration and left fresh installs at version 2 WITHOUT the
  metadata column -- schema-incoherent, latent until first read. Naming the
  baseline as a constant makes "init_db builds version 1" explicit and prevents
  it silently tracking a future bump.
- [DECIDED] TEST DB HELPER SPLIT. The same coupling meant the shared temp_db
  helper (init_db only, no migrations) no longer represents "a DB at the current
  version." Split into two explicitly-named helpers in tests/_support.py:
  temp_db = the BASELINE DB (for migration tests that drive run_migrations);
  current_db = init_db + run_migrations to SCHEMA_VERSION (the DB a running app
  actually has, for reader/endpoint tests that touch migration-added columns).
  Migration loop tests now key injected versions off the DB's ACTUAL current
  version (get_schema_version), not SCHEMA_VERSION, so they stay correct and
  genuinely-pending as the ceiling rises.
- [SCOPE] This fix + the helper split were outside D1's literal scope list
  (migration fn / MIGRATIONS / SCHEMA_VERSION / read-path wiring) but necessary
  for D1 to be correct: without it a fresh install ships broken. Surfaced at
  runtime by the Step 3 read-path test, not by static review. The general
  "extract every magic-number version literal into a named constant" pass is a
  separate later cleanup; D1 extracted only BASELINE_SCHEMA_VERSION, the one the
  defect forced.

D1 HANDOFF VERDICT (requested by the brief): was the decisions.md "how D1 adds a
migration" procedure correct as written?
- The PROCEDURE was mechanically correct and was followed verbatim: write the
  migrate fn, append one MIGRATIONS tuple in version order, bump SCHEMA_VERSION,
  add a real-MIGRATIONS test. The import-time guard behaved exactly as promised.
- Two corrections for D2+: (1) the worked example used banks.metadata_extra --
  wrong table and a duplicate of the existing banks.metadata; the real D1 gap
  was questions.metadata (ADR-024). (2) The procedure omitted the init_db
  baseline-stamp interaction (ADR-026): the FIRST migration to ever bump
  SCHEMA_VERSION above 1 exposed that init_db stamped the moving constant. D2+
  is now safe because BASELINE_SCHEMA_VERSION is fixed, but the procedure's
  closing claim ("the version stamping is already handled") was only true once
  ADR-026 landed. Update the handoff prose to point at BASELINE_SCHEMA_VERSION.

C-D2 - Arithmetic operators: modulo + exponent (#4, implementation thread).

Adds the modulo (%) and exponent (^) operators. Structurally this was a
refactor + 2 operators, not "add two dict entries": one operator's definition
had been scattered across OPERATOR_CONFIG + _OPERATOR_EVAL_FUNCTIONS +
_OPERATOR_OPERAND_GENERATORS plus hidden `if symbol == "-"` branches, joined by
the symbol string as an implicit foreign key. The refactor (C-D2a..C-D2d2)
collapsed that into one self-contained record per operator before the two new
operators were added (C-D2e). No schema change -- #4 is pure LOGIC; the
migration apparatus stayed dormant. Frontend untouched (question_text renders
server-side via textContent; operator symbols never reach client logic).
Backend 102 -> 104 (+2 example tests in test_logic.py; the property test gained
% / ^ assertions in place); frontend 75 unchanged; total 177 -> 179,
"ALL GREEN". Commits landed a -> c -> d1 -> d2 -> e -> f (this entry).

ADR-027: operator definition is ONE record per operator (OPERATOR_DEFINITIONS).
UPHOLDS ADR-007; does not contradict it.
- [DECIDED] Replaced the four-structure split (OPERATOR_CONFIG +
  _OPERATOR_EVAL_FUNCTIONS + _OPERATOR_OPERAND_GENERATORS + the `if symbol ==
  "-"` branches) with a single list of record dicts, each carrying symbol,
  name, arity, operand range(s), forbid_identity, the eval callable, and the
  operand strategy. _build_operator_table no longer JOINS four sources keyed by
  the symbol string; it indexes the records by symbol and validates RECORD
  COMPLETENESS (required keys present, eval_fn / operand_strategy callable,
  referent known, no duplicate symbol, every enabled symbol has a record),
  keeping the loud import-time ValueError guard.
- [DECIDED] This UPHOLDS ADR-007, which made operand ranges and forbidden
  identities DATA the enforcement logic reads. ADR-007's parameters were always
  meant to be data; the four-structure scatter had diluted that by spreading one
  operator's data across separate dicts joined implicitly. One record per
  operator is the honest expression of "ranges and identities are data" -- the
  refactor concentrates ADR-007's data, it does not weaken it. Eval callables
  are the stdlib `operator` module's binary functions (operator.add / sub / mul
  / floordiv / mod / pow), full namespace, no alias. _divide's exact-floor
  rationale (ADR-007 guarantees the dividend is a multiple of the divisor, so //
  never discards a remainder) is preserved as a comment on the "/" record.
- [DECIDED] forbid_identity now declares its REFERENT explicitly per record
  (forbid_identity_referent): "operands" (raw operands -- +, -, *), "quotient"
  (the derived quotient -- /), "divisor" (modulo), "exponent" (the power). The
  referent was previously implicit in which strategy read the list (standard
  checked raw operands; division checked the derived quotient), and the property
  test hard-coded that split. Adding two operators added two more referents, so
  the real axis is "forbidden WHAT," not "forbidden values"; each strategy owns
  and declares its referent so a new operator cannot silently inherit the wrong
  meaning.
- [DECIDED] Subtraction's two branches (force left >= right; reject left ==
  right) became ONE declared intent, result_constraint: "non_negative". They
  jointly serve a single goal -- non-negative, non-trivial results -- and
  splitting them into two independent booleans would let a future editor set
  them inconsistently (order without equal-rejection leaks 0; reject-equal
  without ordering leaks negatives). The strategy reads the constraint and
  implements both mechanics together. This supersedes the C-006 [FLAG] phrasing
  that described two separate generation steps; the invariant is now declared,
  not the steps.

ADR-028: modulo and exponent operand strategies -- each operator that needs two
ranges gets its OWN strategy with NAMED ranges; no generic per-operand-range
override.
- [DECIDED] Modulo (%): operator.mod. Left operand from the default range
  (1..20); divisor from a second range (2..12, >= 2) declared as divisor_min /
  divisor_max on the record. left < divisor IS allowed -- a % b == a is a
  legitimate, non-trivial case. Forbidden-identity referent is the DIVISOR (a
  divisor of 1 makes x % 1 == 0 for every x). Strategy
  _generate_operands_modulo.
- [DECIDED] Exponent (^): operator.pow. Base from 2..12; the power from its OWN
  narrow range (_EXPONENT_POWER_RANGE = 2..3) declared as exponent_min /
  exponent_max on the record. Forbids power 0 and 1 (x^0 == 1, x^1 == x). The
  narrow power range keeps results integer and UI-tractable (ceiling 12^3 =
  1728). Strategy _generate_operands_exponent, mirroring the division strategy's
  two-range shape. Both ranges are plain record fields, hand- or
  difficulty-adjustable later.
- [DECIDED] NO generic per-operand-range override field. An earlier draft
  proposed one on every record as a future hook; it was dropped because (1) it
  would have had no caller in the commit introducing it (untested by
  construction); (2) division already solves "two ranges" with its own named
  strategy, so the honest interface is "exponent gets its own strategy with two
  named ranges," not a generic indexed override; (3) a generic indexed override
  repeats the magic-list smell one level up. Each multi-range operator declares
  its second range as named fields its own strategy reads.
- [RECONSIDER WHEN] -> #2 (difficulty). See ADR-030.

ADR-029: deferred operators + the "easy operator" gate.
- [DECIDED] Deferred, with the gate below: true (float) division, GCD / LCM,
  factorial.
- [RECONSIDER WHEN] true division: the first feature that genuinely needs
  non-integer results. Cost then: change evaluate_expression's -> int contract
  or add a per-operator result_type, plus a real decimal/tolerance policy. The
  numeric validator already parses floats and supports tolerance, so the
  validator is NOT the blocker -- the -> int contract and floor-division
  derivation are.
- [RECONSIDER WHEN] GCD / LCM: alongside #5 (nested trees). They are FUNCTIONS,
  not infix operators, so they break render_expression's "left op right"
  assumption; #5 generalizes the renderer anyway.
- [RECONSIDER WHEN] factorial: when unary support is otherwise needed. It is
  UNARY; the table assumes arity 2 (a record field).
- [NOTE] THE GATE (one sentence): an operator is "easy" -- addable as a record
  with a strategy -- iff it is binary, integer-in / integer-out with bounded
  magnitude, and renders infix. Anything failing that test is a structural
  change, not a record. Modulo and exponent both pass; the three above each fail
  exactly one clause (float result; not infix; unary).

ADR-030: deferred to #2 (difficulty) -- full per-operand-range generalization
and the dataclass promotion.
- [DECIDED] NOT done in #4: (a) Approach B, generalizing per-position operand
  ranges to ALL operators behind one uniform interface; (b) Option 3, promoting
  the record dicts to a dataclass / typed structure. #4 kept records as plain
  dicts and let each multi-range operator name its own second range (ADR-028).
- [RECONSIDER WHEN] Approach B: when #2 has a REAL consumer that needs
  per-position ranges across operators (e.g. a difficulty knob that widens every
  operator's operand range uniformly). Write the caller first; do not generalize
  ahead of it. Until then the per-strategy named-range pattern is the honest
  interface.
- [RECONSIDER WHEN] Option 3 (dataclass): when the record field set stabilizes
  under #2's additions and the validation in _build_operator_table starts
  wanting types it currently checks by hand (callable, known referent). A
  dataclass buys typed fields + construction-time validation; #4's hand-rolled
  completeness check is the cheaper version while the shape is still moving.

ADR-031: provisional defaults #4 ships that #2 supersedes; exponent
associativity open for #5.
- [NOTE] "All six operators enabled, sampled uniformly" (OPERATOR_SYMBOLS =
  [+, -, *, /, %, ^]; generate_expression picks uniformly at random) is a
  PROVISIONAL default, not a considered pedagogical choice. #2 (difficulty) owns
  the real policy -- which operators are enabled and with what weighting -- and
  supersedes this. A future reader should not mistake the uniform six-way sample
  for a deliberate curriculum decision.
- [NOTE] Exponent is RIGHT-associative (2^2^3 = 2^(2^3)), unlike + - * /. The
  flat #4 generator never associates, so it is a non-issue now. #5 (nested
  trees) must handle it: a naive renderer/generator will get exponent
  associativity wrong. render_expression currently parenthesizes any nested dict
  operand unconditionally (safe but over-parenthesizing); precedence-aware
  parenthesization is the #5 subtlety. Flagged, not fixed here.
- [CLOSED in #5] Exponent right-associativity is now represented and handled:
  the "^" record carries associativity "right" and precedence 3, and
  render_expression's precedence/associativity rule wraps a same-tier child on
  the associativity-wrong side (the LEFT child of a right-associative parent),
  so (2 ^ 3) ^ 2 keeps parens while 2 ^ 3 ^ 2 (the right-associative reading)
  drops them. The "over-parenthesizing" renderer this note describes was
  replaced. See ADR-033. The generator never BUILDS a ^ with subtree children
  (^ is leaf-only, ADR-032), so the right-associative case is renderer-reachable
  only via hand-built trees; the renderer is correct on them regardless.

================================================================================
## #5  Nested expression trees (the #5 design thread)
================================================================================

ADR-032: bottom-up construction + the composable / leaf-only split. UPHOLDS
ADR-027 (records) and ADR-007 (ranges/identities as data); does not contradict
either.
- [DECIDED] generate_expression builds trees BOTTOM-UP via an internal helper
  build_subtree(symbols, remaining_depth): each child is built first, so its
  integer VALUE is known before the parent operator is chosen or its sibling
  derived. The parent is chosen/derived to fit the children; a built subtree is
  NEVER mutated to fit a parent. On a constraint failure the node redraws. This
  keeps generation a pure transformation -- the only impurity is random.*,
  identical to the flat #4 generator.
- [DECIDED] Operators split by ONE declared boolean field on the record,
  nestable: bool. COMPOSABLE (nestable True: + - *) MAY have subtree children.
  LEAF-ONLY (nestable False: / % ^) keep integer leaves as their operands.
- [PRECISE READING -- the most misread point] nestable governs whether an
  operator may have subtree CHILDREN. It does NOT govern whether an operator's
  node may itself BE a child. A / % ^ node IS a valid subtree child of a
  composable parent: (a / b) * c is reachable (the / node is a child of *);
  a * (b / c) is reachable (renderer parenthesizes the right child); a / (b * c)
  and 2 ^ (a + b) are NOT reachable (the / and ^ operands stay leaves). These
  trees are unreachable because the GENERATOR never builds them, not because the
  renderer cannot print them -- the renderer is total over all well-formed trees
  (ADR-033), which is what lets #2 widen generation with zero renderer change.
- [RATIONALE for the split] / % ^ DERIVE one operand from another (division:
  dividend = divisor * quotient; exponent: narrow power range; modulo: divisor
  >= 2). A subtree in a derived position would force "derive a compatible
  sibling from a fixed subtree value" -- sparse-factor failure for division, a
  magnitude blowup for exponent. + - * have no cross-operand value dependency,
  so a subtree value slots in cleanly.
- [DECIDED -- constraint lifting, composable operators only] a constraint stated
  over leaves generalizes to the same check against evaluate_expression(child):
  + forbids operand VALUE 0; * forbids VALUES 0 and 1 (a * subtree-evaluating-
  to-1 is the trivial identity and is rejected); subtraction orders operands by
  EVALUATED value (left_value >= right_value) and rejects equal values (result 0
  is trivial). Bottom-up means the child value is already in hand, so the check
  is cheap and pure. Swapping operand POSITIONS for subtraction is arrangement,
  not mutation of a built node.
- [DECIDED -- leaf-only operators keep leaf-based generation UNCHANGED] their
  invariants remain statements about LEAVES (divisor >= 2, derived quotient,
  exponent power range). They are NOT lifted to values. A blanket evaluate-and-
  recheck would corrupt them; the property test dispatches per operator (value
  for + - *, leaf for / % ^) rather than rechecking uniformly. The composable
  leaf ranges start above their forbidden values (+ - from 1, * from 2), so a
  leaf never self-violates; the value check only ever rejects a SUBTREE operand.

ADR-033: precedence + associativity REPRESENTED on the record; the renderer is
the sole owner of correct printing. Closes ADR-031's exponent item.
- [DECIDED] Precedence is an explicit integer tier per record, compared with <:
  + - => 1, * / % => 2, ^ => 3. NOT computed, NOT inferred from list position,
  NOT a categorical string. Associativity is a declared field: + - * / % "left",
  ^ "right". This follows the ADR-027 "declared, cannot silently inherit the
  wrong meaning" pattern.
- [DECIDED -- the render rule (~8 lines)] when rendering an internal node, wrap
  a child IFF the child is an internal node AND (child.precedence <
  parent.precedence) OR (child.precedence == parent.precedence AND the child is
  on the associativity-WRONG side: the right child of a left-associative parent,
  or the left child of a right-associative parent). The #4 renderer was the
  degenerate "wrap every internal child" (keyed on isinstance(child, dict));
  it was replaced.
- [WHY CORRECT-CRITICAL] the rendered string IS the question; the answer is
  computed from the TREE structure (evaluate_expression never consults
  precedence -- the tree shape is the grouping). The renderer must emit a string
  that, read under standard precedence/associativity, parses back to THAT tree.
  A mismatch silently makes the displayed question and the stored answer
  disagree. Tested exhaustively with HAND-BUILT trees (decoupled from generator
  output), table-driven over operator-pair x nested-side with exact-string
  assertions, covering the same-tier traps (a - (b - c) keeps, a - b + c drops,
  a / b * c drops, a * (b / c) keeps, (a + b) * c keeps, 2 ^ 3 ^ 2 drops vs
  (2 ^ 3) ^ 2 keeps).
- [CLOSED] ADR-031's open exponent right-associativity item: ^ is right-
  associative, represented on the record, handled by the render rule above.

ADR-034: depth is the knob, as a MODULE CONSTANT, and is STRUCTURAL not
difficulty. Consensus of adversarial Lenses 3 + 4 (write the concrete caller
first; ADR-028 spirit).
- [DECIDED] Size is controlled by OPERATOR DEPTH: operator_depth(leaf) = 0,
  operator_depth(internal) = 1 + max(left, right). A flat single-operator node
  has depth 1; (a+b)*c has 2. The knob is the module constant _MAX_OPERATOR_DEPTH
  (>= 1). _MAX_OPERATOR_DEPTH == 1 reproduces the flat #4 generator EXACTLY (an
  assertable property, tested). Provisional default 2.
- [DECIDED] Shape control: at each operand position of a composable node with
  budget remaining, an INDEPENDENT per-operand Bernoulli "subtree or leaf?" with
  probability _RECURSE_PROBABILITY (a single scalar in [0,1], provisional default
  0.5; the two operands flip independently and do NOT form a distribution).
  p == 0 reproduces flat generation; p == 1 recurses until the depth floor forces
  leaves.
- [DECIDED -- NOT a function parameter] _MAX_OPERATOR_DEPTH is a module constant,
  not a parameter on generate_expression. The single caller (the arithmetic
  endpoint) is generate_expression(enabled_symbols); nothing varies depth. A
  parameter with only a default and no caller is the speculative interface
  ADR-028 warns against. #2 (difficulty) adds the parameter TOGETHER WITH its
  real caller. generate_expression's public signature is UNCHANGED from #4.
- [DOMAIN NOTE] depth is a STRUCTURAL parameter, ONE input among several #2 will
  weigh (operator mix, operand magnitude, depth), explicitly NOT a difficulty
  score: 2 + 3 + 4 (depth 2) is easier than 7 * 8 (depth 1). depth != difficulty.

ADR-035: optional global result ceiling, shipped DARK (default OFF) as a
difficulty knob, with a LOCAL feasibility check. Resolves Q4's residual.
- [DECIDED] _MAX_RESULT_VALUE is a module constant, default None == OFF, making
  the feasibility check a no-op (behavior identical to the no-ceiling generator).
  The MECHANISM ships even though the default is off so #2 can flip a value with
  zero plumbing.
- [DECIDED -- local check, not whole-tree reject] because construction is
  bottom-up, when assembling a node both child VALUES are in hand, so check
  value(left) <op> value(right) <= ceiling BEFORE committing the node; on failure
  redraw the OPERAND (or pick a different operator), not the whole tree. This
  co-locates the cost away from the worst case (a root-level whole-tree reject
  discards the most work exactly when trees are largest). NO backtracking /
  subtree-memoization -- it adds state and fights purity; the local check already
  gets the win. Each redraw counts against _MAX_GENERATION_ATTEMPTS.
- [PRECISE READING] the ceiling bounds node RESULTS (value(left) op value(right)),
  NOT input-leaf magnitudes. Division derives a dividend (divisor * quotient)
  that can exceed the ceiling while the quotient RESULT stays under it; that is
  correct and intended. A leaf is an input, not a result.
- [NOTE] Q4 (exponent magnitude) mostly dissolves under the leaf-only rule: ^ is
  leaf-only, so no subtree feeds its base or power; the #4 ceiling (base 2..12,
  power 2..3, max 12**3 = 1728) stands unchanged. The residual -- a composable
  operator ABOVE leaf-only nodes growing large, e.g. (2^3) * (5^2) -- is what the
  global ceiling handles when #2 turns it on, NOT a new exponent rule.
- [FRAMING for #2] the ceiling is a DIFFICULTY-relevant knob #2 may turn, not a
  fixed sanity guard #2 should leave alone.

ADR-036: bounded retry / fail-loud, and nondeterministic generation with no seed
parameter.
- [DECIDED] Bottom-up reject-and-redraw presupposes a draw eventually succeeds;
  "redraw forever" has no termination proof and nesting compounds it. A generous
  bounded retry, module constant _MAX_GENERATION_ATTEMPTS (default 1000), counts
  down per redraw loop and RAISES a clear RuntimeError on exhaustion rather than
  hanging. Hitting the ceiling is the SIGNAL of a generation bug, not a thing to
  absorb (matches the generator's existing "fail loudly on unknown symbol"
  stance). The property test asserts normal generation NEVER raises it (pins
  "constraints are satisfiable in practice" as a tested property).
- [DECIDED] Generation is intentionally NONDETERMINISTIC (determinism is a
  property of evaluate over a fixed tree, not of generate). Production stays
  nondeterministic; NO seed parameter is threaded (no caller needs it; single-
  user). Tests achieve reproducibility by seeding the GLOBAL RNG (random.seed(N))
  per the existing pattern; global-seed tests are order-sensitive if they share
  process state.
- [NOTE] The internal helper is build_subtree(symbols, remaining_depth) calling
  random.* directly -- NO rng parameter (threading an rng is speculative
  seedability, killed by the same Lens 3 reasoning as the depth parameter).
- [INCIDENTAL] there is no CONFIG class; the generate_expression docstring's
  reference to "CONFIG.OPERATOR_SYMBOLS" was STALE and was fixed. The new
  constants follow the actual module-global pattern, placed beside
  OPERATOR_SYMBOLS.

ADR-037: DEFERRED doors for #2 -- convenience-not-principle. Each is a value or
shape #5 fixed for simplicity, to be widened only when #2 has a concrete caller.
- [RECONSIDER WHEN] per-POSITION subtree control: #5 uses one scalar
  _RECURSE_PROBABILITY with independent per-operand flips. If #2 wants asymmetric
  shaping (e.g. recurse left more than right, or per-operator recurse rates), it
  widens this then -- not before.
- [RECONSIDER WHEN] making / % ^ NESTABLE: leaf-only is a #5 simplification, not
  a law. #2 may allow a subtree in a derived position by solving "derive a
  compatible sibling from a fixed subtree value" (factor-aware division, range-
  aware exponent). Flip the nestable bool then, with the derivation that makes it
  feasible.
- [RECONSIDER WHEN] the result ceiling DEFAULT: _MAX_RESULT_VALUE is None in #5
  (off). #2 owns turning it on and choosing the value as a difficulty knob
  (ADR-035).
- [RECONSIDER WHEN] _RECURSE_PROBABILITY / _MAX_OPERATOR_DEPTH DEFAULTS (0.5 / 2):
  provisional, like ADR-031's uniform operator sample. #2 owns the real values
  as part of difficulty policy; a future reader should not mistake them for a
  deliberate pedagogical choice.
- [STILL BINDING from the #5 brief] node shape {op, left, right} with int leaves,
  no dataclass (ADR-030, deferred to #2); operator-record design (ADR-027) --
  new fields are ADDED to the record, not a new structure; no new operators, no
  unary/n-ary (ADR-029); no generic per-operand-range override and a single
  ceiling value, not per-operator (ADR-028/030); pure LOGIC only -- no clock, IO,
  HTTP, schema, or frontend change.
================================================================================
ROADMAP #2 -- DIFFICULTY CONTROL (design settled; see handoff-2-to-implementation.md)
================================================================================
ADR-038: difficulty model shape -- scalar rung expanding to a PER-OPERATOR
config (shape C, with the per-operator correction the code forced).
- [DECIDED] Difficulty is a scalar rung exposed as ?difficulty=, expanded via an
  overridable DIFFICULTY_RUNGS mapping into PER-OPERATOR structural config
  (operator depth, recurse probability, each operator's own operand ranges, the
  result ceiling). Caller sees a scalar; the internal representation is a
  per-operator vector. generate_expression(difficulty=None) is byte-identical to
  today (Q6); a rung is an explicit opt-in override.
- [DECIDED] "Reliably harder" is operationalized PER OPERATOR-MIX. For mixes
  containing a composable operator (+ - *), difficulty is COORDINATION-driven and
  the proxy is leaf_count (element-interactivity analog), pinned monotone
  non-decreasing across rungs by a property test. For all-leaf-only mixes
  (/ % ^), leaf_count is CONSTANT by construction (they cannot nest), so
  difficulty is MAGNITUDE-driven (wider per-operator ranges), pinned separately.
- [REJECTED -- with reason] the first design proposed leaf_count as a SINGLE
  scalar feature with a UNIFORM operand-range multiplier. Overturned by three
  converging lenses against the code: (a) generate_expression(['/']) yields
  leaf_count==2 for 5000/5000 samples -- a point mass, so a uniform monotonicity
  test is a lie for leaf-only mixes; (b) ranges are per-operator with bespoke
  fields (divisor_min/max, exponent_min/max, derived dividend), so a uniform
  multiplier is the generic override ADR-028/030 refused and is incoherent
  against the data; (c) the atom was ambiguous for #7. Recorded so the
  implementation thread does not re-derive the dead end.
- [NOTE -- domain honesty] a higher rung produces reliably harder questions ON
  AVERAGE WITHIN a mix; it is a heuristic over structural features, NOT a
  validated measure of cognitive load, and NOT a cardinal scale comparable across
  mixes. State this in user-facing framing and in #7's consumer.
- [DECIDED -- S11, resolved before C-D2i] the per-difficulty breakdown GROUPS BY
  leaf_count, NOT by rung. ?operators= and ?difficulty= are ORTHOGONAL query
  params: the user can request any (mix, rung) pair, including division-only at
  the top rung (where leaf_count is pinned at 2 and only magnitude moves). The
  rung number is therefore NOT comparable across operator mixes, yet C-D2i
  aggregates arithmetic responses regardless of the mix served. Grouping by rung
  would silently compare incomparable buckets (easy all-ops rung 3 vs hard
  division-only rung 3). leaf_count is the comparable structural fact across
  mixes -- which is precisely why it is stored (ADR-040) -- so grouping by it
  makes the stored-fact decision pay off immediately, not only for #7. This is
  the L6/domain objection resurfacing at the storage+display layer, where
  ADR-038's generation-layer fix (per-mix property tests) did not reach.
- [ALTERNATIVES CONSIDERED -- recorded, not chosen]
    (A) FIXED-MIX SCOPING: show the breakdown only for a single chosen operator
        mix, so rung is comparable within it. Cleanest comparability and lets the
        breakdown legitimately key on rung. Rejected as the default because it
        forces the user to pick a mix to see any difficulty stats and hides
        cross-mix practice entirely; it is strictly NARROWER than leaf_count
        grouping, which already shows everything and stays comparable. Kept as a
        future drill-down (a mix filter layered on top), not the v1 surface.
    (B) RUNG-WITH-DISCLAIMER: group by rung and label the section "rung as
        dialed, not comparable across operator sets." Most legible as a learning
        curve when the user drills ONE mix at a time (rung 1: 95% ... rung 4:
        60% reads directly), and rung is the human-facing label. Rejected as the
        default because the disclaimer invites exactly the misreading it warns
        against, and the legibility win only holds for single-mix usage we cannot
        assume. Note: if real usage turns out to be single-mix-dominant, (B) is
        the better display -- see the switchability note in ADR-041, which is why
        the grouping key is built as a swappable pure parameter, not hardcoded.
- [KNOWN LIMITATION of the chosen key] leaf_count is comparable across mixes but
  is NOT itself a complete difficulty cardinal: every leaf-only mix collapses to
  a single leaf_count==2 bucket, so all division/modulo/exponent practice (which
  differ in real difficulty and in magnitude) shares one row. leaf_count grouping
  is LESS WRONG than rung, not fully right. The magnitude axis that distinguishes
  leaf-only operators is captured in the per-operator ranges (ADR-039) and in #7's
  richer analysis, not in this v1 text breakdown. Documented so a reader does not
  over-read the single "2 leaves" row.

ADR-039: Q2 x Q3 feasible-region resolution -- per-operator range scaling plus a
difficulty-scaled result ceiling, jointly proven satisfiable.
- [DECIDED] Difficulty widens operand ranges PER OPERATOR, reading each record's
  own range fields (Q2): + - from _DEFAULT_OPERAND_RANGE; * / from
  _MULTIPLICATIVE_OPERAND_RANGE; % also scales its divisor range; ^ scales its
  base but its power range (_EXPONENT_POWER_RANGE, 2..3) has almost no headroom
  (12**3 already at the UI ceiling) so a rung likely holds it fixed. NOT a
  uniform multiplier; NOT a generic indexed override.
- [DECIDED] the result ceiling is PART of the difficulty model (lower ceiling =
  easier), turned on per rung from its dark default (ADR-035), NOT a fixed sanity
  guard. It bounds node RESULTS, not input leaves (ADR-035 precise reading): cap
  operand magnitude via the RANGES, never via the ceiling.
- [DECIDED] Q2 and Q3 are ONE feasible-region decision. Each rung's (per-operator
  ranges, ceiling) pair must be PROVEN jointly satisfiable by a property test,
  because widening ranges while lowering the ceiling can make generation
  infeasible -> _MAX_GENERATION_ATTEMPTS exhaustion -> RuntimeError (ADR-036).
  The division (dividend = divisor*quotient) and exponent mixes are where this
  bites. The C-D2e commit deliberately observes this RED first (the red is the
  feasibility proof), then reconciles to green.

ADR-040: storage -- responses.difficulty AND responses.leaf_count (mutable label
plus non-drifting fact). Opened Q5 because a real consumer (ADR-041) is built in
the same thread.
- [DECIDED] ONE additive forward-only migration (v3) adds two nullable INTEGER
  columns to responses: difficulty (the served rung, a human-facing label) and
  leaf_count (the served expression's structural ground truth). arithmetic rows
  get both; non-arithmetic and pre-#2 rows get NULL (unknown, not a default rung
  -- a backfill value would poison analysis; matches the v2 no-data-loss rule).
- [DECIDED -- why two columns] a bare rung integer denormalizes a MUTABLE label:
  re-tuning a rung's config (which monitor-and-adjust invites) silently re-means
  every historical row. leaf_count is recomputable from question_text and does
  not drift, so it is the trustworthy axis for analysis; the rung stays for
  readability. (Nelson/anti-drift lens.)
- [NOTE -- client-asserted] the round-trip is stateless: difficulty+leaf_count
  ride the question-payload -> client-echo -> answer-body -> insert_response path
  (as expected/elapsed_ms already do). The recorded value is therefore
  CLIENT-ASSERTED, as trustworthy as expected/elapsed_ms already are -- no worse,
  no better. #7 must know this when it consumes the field.
- [DECIDED] column on responses, NOT questions: arithmetic is generated with
  question_id NULL, so it has no questions row and the questions.metadata hatch is
  unreachable for it; responses has no extras column. Honest recording REQUIRES
  this migration -- there is no free hatch.

ADR-041: the per-difficulty stats breakdown as the real Q5 consumer.
- [DECIDED] summarize_stats gains a difficulty breakdown alongside the existing
  category breakdown, rendered in the existing .stats-breakdown panel,
  arithmetic-category only (other categories have no difficulty -- do not render
  empty rows; intended, not a bug).
- [DECIDED -- extract the implicit] get_responses_for_stats + summarize_stats are
  about to serve TWO grouping meanings (category AND difficulty/leaf_count) that
  currently coincide as one. EXTRACT breakdown_by(rows, key_function) and call it
  twice; do NOT copy-paste the group loop. (commit-planning "name the two
  meanings into two explicit helpers".) The category breakdown output must be
  reproduced byte-for-byte by the extracted helper (regression guard).
- [DECIDED -- live vs durable] this is a DURABLE-history view (summarize_stats /
  the stats panel), NOT the live in-session stats bar; the two never share a
  render path (existing convention).
- [CROSS-REF] the grouping KEY (rung vs leaf_count) WAS gated by ADR-038's
  [OPEN -- CRITICAL] item; now RESOLVED there: group by leaf_count. This
  breakdown is comparable across operator mixes as a result.
- [DECIDED -- swappable key seam, so the S11 choice is cheap to revisit] the
  grouping policy is passed to breakdown_by as PURE PARAMETERS, never hardcoded
  inside it. Signature:
      breakdown_by(rows, key_of, label_of, *, include_row=None) -> list[dict]
  where key_of(row) returns the bucket key (hashable), label_of(row) returns the
  human label for that key, and the optional include_row(row) predicate filters
  which rows participate (used to scope the difficulty breakdown to arithmetic
  rows only). breakdown_by owns ONLY the group/count/accuracy/sort mechanics; the
  three callables ARE the policy. The category breakdown is then
      breakdown_by(rows, key_of=lambda r: r["category_id"],
                          label_of=lambda r: r["category_name"])
  and the difficulty breakdown is
      breakdown_by(rows, key_of=lambda r: r["leaf_count"],
                          label_of=lambda r: str(r["leaf_count"]) + " leaves",
                          include_row=lambda r: r["category_name"] == "arithmetic"
                                                and r["leaf_count"] is not None)
  Because the key is a callable argument, switching S11's decision later is a
  ONE-LINE change at the call site (swap key_of/label_of), with ZERO change to
  breakdown_by, to summarize_stats's structure, or to the category-path tests.
  This mirrors the operator-table pattern (policy as data/callables consumed by a
  pure mechanism). breakdown_by stays PURE (no IO, no clock, deterministic sort),
  so it is independently unit-testable and a future caller (#7 adaptive
  selection, a CLI report, an export) can reuse it with its own key without
  touching the stats path.
- [SWITCHABILITY MEASUREMENT -- what each alternative would cost AFTER C-D2i ships
  with the seam above]
    -> switch to RUNG-WITH-DISCLAIMER (alt B): change key_of to r["difficulty"]
       and label_of to "rung " + str(...); add a static disclaimer line in the
       renderer. Backend: ~2 lines at the call site + 1 render string. Tests: the
       difficulty-breakdown test expectations change; category tests untouched.
       No migration (both columns already stored, ADR-040). Est. one small commit.
    -> switch to FIXED-MIX SCOPING (alt A): key_of stays leaf_count or becomes
       rung; add a mix selector to the stats request (a new optional query param
       threaded HTTP -> get_responses_for_stats as an extra filter, or filter in
       include_row if the served mix is recorded). This one is HEAVIER because the
       served operator-mix is NOT currently stored on responses -- only difficulty
       and leaf_count are (ADR-040). Fixed-mix scoping by the EXACT served mix
       would need either a third migration (responses.operator_set) or to infer
       the mix from question_text (fragile). So alt A is the only alternative that
       is NOT a pure-seam swap; it is a schema-touching feature. Recorded here so
       the cost asymmetry is explicit: leaf_count vs rung is a 1-line swap;
       fixed-mix is a migration. This asymmetry is itself a reason to default to
       leaf_count now (keeps the cheap swaps cheap; defers the expensive one until
       a real need).
- [NOTE] storing the served operator-mix is deliberately NOT done in #2 (no
  consumer yet; alt A is not chosen). If a future thread wants per-mix difficulty
  analysis, that is the migration to add THEN, with its consumer -- same
  build-the-consumer-with-the-column discipline that opened ADR-040.

ADR-037 DOOR DISPOSITION (as #2 opens them):
- [CLOSED] D1 (depth as a parameter) -- opened in C-D2b (threaded into
  build_subtree with its real caller).
- [CLOSED] D4 (result-ceiling default) -- opened in C-D2e (ADR-039).
- [CLOSED] D5 (provisional defaults 0.5 / 2) -- re-owned by the rung mapping
  (Q6); module constants remain the no-parameter fallback.
- [PARTIAL] D2 (per-position / shape control) -- #2 uses recurse probability only
  as a per-rung scalar; asymmetric / per-operator SHAPE is NOT added (not needed).
  D2 stays OPEN for a future thread; #2 did not require it.
- [STILL DEFERRED] making / % ^ nestable (a generator-capability change, not a
  difficulty knob; difficulty does not need nested division); the dataclass
  promotion (ADR-030 -- and #2 ADDS per-operator range fields, so the field set is
  LESS stable now, keep dicts).
- [SUPERSEDED/RETAINED] ADR-030's reserved per-operand-range generalization is
  OPENED in the per-operator shape (Q2), NOT the generic override it refused;
  ADR-031's provisional-sample note is superseded for the rung-driven path,
  retained for the default path (Q6).

================================================================================
## #2  Difficulty control -- AS-BUILT (the #2 implementation thread)
================================================================================
The #2 design (ADR-038..041 above, the S11 resolution, and the ADR-037 door
disposition) was implemented across C-D2a..C-D2i. This section records what
ACTUALLY shipped, the deviations from the plan, and the one piece deliberately
left for a follow-on thread. The design ADRs are not re-litigated here; this is
the build record.

ADR-042: the generator difficulty seam is FOUR plain-data parameters threaded
  through one path, not a config object or a strategy hierarchy. generate_expression
  gained a single scalar `difficulty` rung; internally it resolves the rung
  (_resolve_difficulty_rung) and threads FOUR plain values into build_subtree:
  operator_depth and recurse_probability (C-D2b, the weld), an operator_table
  scaled per-rung (C-D2d), and max_result_value (C-D2e). Each was added WITH its
  consumer, never speculatively (ADR-034's door discipline). difficulty=None is
  byte-identical to the pre-#2 path: it passes the module constants
  (_MAX_OPERATOR_DEPTH, _RECURSE_PROBABILITY, OPERATORS, _MAX_RESULT_VALUE), so
  #4/#5's behavior and #5's dark-ceiling tests are preserved unchanged. The
  module constants remain as the documented no-rung fallback; the rung table is
  the difficulty-driven path. This UPHOLDS ADR-038 (scalar in, per-operator
  expansion inside) and is the concrete shape of "shape C".

ADR-043: per-rung range overlay is PURE and COPY-ON-WRITE (_apply_rung_ranges).
  A rung's operator_ranges are overlaid onto a COPY of OPERATORS, field-level,
  never mutating the module-global table (proven by test: OPERATORS is byte-
  identical after generating thousands of trees across every rung). An operator
  a rung omits keeps its base range; a field a rung omits keeps its base value.
  This is why difficulty is request-scoped and safe under concurrency, and why
  the leaf-only operators (/ % ^) -- whose leaf_count is pinned at 2 -- still get
  harder: their MAGNITUDE moves via the overlay even though their SHAPE cannot
  (the S7 two-regime split, now enforced by tests: leaf_count monotone for
  composable-containing mixes, magnitude monotone for leaf-only mixes).

ADR-044: the result ceiling is enforced LOCALLY and proven JOINTLY SATISFIABLE.
  _result_within_ceiling checks only THIS node's result against the rung ceiling
  (max_result_value threaded as a parameter, replacing the module-global read).
  Because a parent accepts only ceiling-passing children, the local check
  transitively bounds every node result and the final result (no whole-subtree
  re-evaluation). The rung-4 ceiling (100000) was PROBED jointly satisfiable with
  rung-4's ranges before shipping (worst observed result ~99.8k over 30k trees,
  zero RuntimeErrors). The deliberate-red guard from the plan ships GREEN as a
  test (test_impossible_ceiling_raises_runtime_error): an impossible ceiling
  makes an operator infeasible and the bounded-retry guard raises rather than
  loops -- the test passes BECAUSE the ceiling is wired, and would flip red if it
  were ever unwired. No rung shipped red.

ADR-045: HTTP validates difficulty INBOUND, records it TRUSTED-BUT-TYPED.
  The question endpoint validates ?difficulty= against the known rung labels and
  400s on a bad value (mirroring the ?operators= unknown-symbol 400), so
  generate_expression's ValueError rung guard only ever fires on an internal
  programming error. post_answer, by contrast, records the echoed difficulty +
  leaf_count after a TYPE check only (_optional_int -> 400 on non-int), NOT a
  rung-range check: this is a recording field for a single-user local tool, the
  outbound path already validated the rung, and the C-D2i breakdown groups by
  leaf_count (not the rung label), so re-policing inbound would add a second
  rung-range source of truth for no benefit. Honest recording of what the client
  claimed is the chosen contract.

ADR-046: the breakdown grouping mechanism is the PURE breakdown_by seam, with the
  S11 key as a CALLABLE argument (delivers on ADR-041's switchability promise).
  breakdown_by(rows, key_of, label_of, *, include_row) owns only the group/count/
  accuracy/sort mechanics; the grouping POLICY is the three callables. The
  per-difficulty breakdown passes key_of=leaf_count, label_of="N leaves",
  include_row=arithmetic-with-leaf_count (the S11 resolution: leaf_count is
  comparable across operator mixes, the rung is not). Switching the S11 key to
  the rung is a one-line change at the summarize_stats call site, zero change to
  breakdown_by or the category path -- the switchability ADR-041 designed, now
  real. The category breakdown was LEFT on its existing inline loop (not
  refactored onto breakdown_by): the refactor was optional, carried regression
  risk on a shipped path, and bought nothing #2 needed. Recorded as a deliberate
  non-change, available to a future cleanup.

ADR-047 [OPEN -- handed off]: NO UI CONTROL sets the difficulty rung yet.
  state.difficulty exists in the client (default null) and round-trips end to
  end -- questionQuery() appends &difficulty= when set, the payload echoes it,
  post_answer records it -- but nothing in the UI SETS it, so in shipped form the
  rung is always null (the default path) unless a caller pokes state.difficulty.
  This was the deliberate C-D2c scope boundary: the carrier wiring is #2's
  concern, a selector is a UI commit. The full backend + data path is proven and
  green; only the control surface is absent. This is the single remaining piece
  of #2 and is handed off (see handoff-2-implementation-to-ui).

ADR-047 [CLOSED -- C-2U-a..d, the UI selector thread]: the rung selector
  shipped; roadmap #2 (difficulty control) is now COMPLETE end to end. As-built:
  - C-2U-a: GET /api/difficulty-rungs, a pure read of DIFFICULTY_RUNGS. The
    D-UI-1 decision (handoff section 5) was resolved to the read-endpoint
    option so the client does not re-encode the rung set. DEVIATION FROM THE
    HANDOFF SHAPE, recorded: the endpoint returns the rung's STRUCTURAL FACTS
    ({rung, operator_depth, recurse_probability, max_result_value}), NOT a
    server-invented {rung, label}. The rung records carry no label field, so a
    label would have to be fabricated server-side; instead the server stays the
    source of truth for what rungs exist and their shape, and the CLIENT composes
    the human descriptor. This keeps user-facing copy in the presentation layer
    and neither side re-encodes the other's domain -- a cleaner split than the
    handoff's suggested shape, made deliberately and noted here.
  - C-2U-b: the <select> (D-UI-2 = select, per recommendation), first option
    "Default" (value "" = null = the byte-identical pre-#2 path), rung options
    valued by rung number, descriptor composed client-side from the endpoint
    facts ("Rung N - flat|nested, any size|to CEILING"). Change -> set
    state.difficulty -> re-fetch immediately (apply-now, the user's call).
    Arithmetic-only gating: for non-arithmetic categories the control is
    DISABLED with an explanatory note rather than hidden, so the affordance
    stays visible and comprehensible (the user's "make the invisible visible"
    steer); switching away from arithmetic also resets to Default and clears
    state.difficulty so a stale rung never rides into a category that ignores it.
    D-UI-3 = NO persistence across reloads (per recommendation): the app has no
    client storage and a lone persisted setting would break the "reload is a
    clean slate" model shared by category/bank/session; a deliberate choice, not
    an oversight. If persistence is ever wanted it should be an app-wide feature
    (selection + difficulty together), not smuggled in via this control.
  - C-2U-c: a read-only active-rung badge under the prompt, shown only for a
    non-default rung (the default path stays uncluttered), text from the served
    payload's echoed difficulty via a state.rungLabels cache (no extra fetch).
  - C-2U-d: a folded-in fix for the import panel not closing -- .import-panel set
    display:flex, which overrides the UA [hidden]{display:none}, and it was the
    LONE toggleable element missing the [hidden] guard the knowledge-capture
    CONVENTIONS already mandate. Added the guard; corrected the stale import-help
    "(1-5)" difficulty range to "(1-4)". This is the documented gotcha being
    enforced after the fact, not a new lesson.
  - STATS-SAFETY of apply-now, verified and pinned by test: a difficulty change
    re-fetches via loadQuestion(), which writes NOTHING; a response row is only
    ever recorded on /api/answer (submitAnswer/submitChoice) when the user
    actually answers. Discarding an on-screen question costs no stats. The
    fetch path and the record path were never braided.
  - GUARDRAILS held: difficulty=None/absent stays byte-identical to pre-#2 (the
    default URL omits &difficulty=, pinned by test); bank questions carry no
    rung; the generator, schema, stats reader, and breakdown were untouched.
  - Suite 282 -> 311 green (backend 196 -> 197; frontend 86 -> 114: + difficulty
    20, + import 8). Clean-room verified at the pinned SHA per commit.

ADR-048 [DECIDED -- C-2U-docs/Phase A]: single-source status in STATUS.md and
  adopt CODING_CONVENTIONS.md.
  - PROBLEM: project status (what is done, the baseline, the green count) was
    duplicated across roadmap.md, knowledge-capture.md, and thread-launch-kit.md,
    and drifted -- stale line counts, "Wave 0 start now" after those threads
    landed, "only the generator is flat" after #5 made it recurse. Discipline
    against drift had failed repeatedly; per the project's own Nelson principle,
    make it structural.
  - DECISION: llm/STATUS.md is the SINGLE source of truth for live status. All
    other docs LINK to it and carry at most convenience snapshots that defer to
    it. When status changes, STATUS.md is edited; the plans/conventions/rationale
    docs are not touched for status.
  - DECISION: llm/CODING_CONVENTIONS.md is the enforceable coding standard,
    adapted from TigerStyle (TigerBeetle) and NASA's Power of Ten. Structured as
    shared -> Python -> JS. Deliberate DEVIATIONS from the source guides, recorded
    there: recursion IS allowed where the problem is naturally recursive (the
    expression trees), and there is NO hard function-length ceiling -- both source
    rules are static-bound/screen-real-estate heuristics that do not fit this
    Python+JS tool. The spirit (safety > performance > DX, explicit limits,
    validate-at-boundary, great names, programmer-error-only assertions) is kept.
  - ENFORCEMENT today is review + the suite; the modularization thread will add
    AST/lint guards (boundary purity, naming/idiom) so conventions become checks,
    not reminders. Recorded as the standing answer to "any convention that keeps
    getting missed becomes a check."
  - This is the bulk of roadmap #20 (docstring/status-drift cleanup); the ADR
    index remains outstanding. Docs-only; suite unchanged at 311 green.

ADR-049 [DECIDED -- C-MOD-design, spike S1/S1b/S1c]: frontend tests import
  modules directly (option b), not via jsdom page execution.
  - PROBLEM: after modularization the page uses <script type=module>. Spiked
    against the real jsdom (26.1.1): jsdom does NOT execute module scripts at
    all (inline or external src) -- classic scripts do run. So a test cannot
    let jsdom run the modular page and read leaked globals.
  - DECISION: tests build the DOM with jsdom runScripts:"outside-only", publish
    window+document as globals BEFORE import, then import the real ES module via
    Node's loader and drive it -- the frontend mirror of the backend
    load_drill() pattern. Fits a plain .test.js (async IIFE + dynamic import());
    the run.sh glob discovers it with no run.sh change.
  - CONSEQUENCE (minted rule): modules touch the DOM only INSIDE functions,
    never at import time (import-time getElementById throws under option b and
    is fragile in-browser). Enforceable by AST guard.
  - This FACT is settled (measured), not a preference.

ADR-050 [DECIDED -- C-MOD-design, spike S2/S4]: layering guards are data-driven
  and DUAL (ruff imports + AST calls).
  - PROBLEM: the layering invariant (config<-db<-logic<-http; nothing imports
    http; LOGIC touches no db/clock/bottle) is the POINT of the split and must
    become a check, not a reminder (ADR-048's "conventions become checks").
  - DECISION: enforce with BOTH, each policy expressed as DATA:
      * ruff flake8-tidy-imports banned-api + per-file-ignores -- import
        direction, declarative in pyproject.toml, pairs with `uv format`.
      * a scope-aware AST purity test (policy as a table) -- call-level purity,
        because a FUNCTION-LOCAL import dodges a module-level import ban (proven
        by injection: only the AST call-check caught an injected datetime.now in
        LOGIC). The AST test is GREEN on clean code and RED on the injection.
  - CONSEQUENCE: the AST checker must be scope-aware (ignore params/locals) and
    assign layer by SYMBOL/file, not by line range -- the naive version produced
    3 false positives on the clean file. Guards land in the suite (portable to
    the clean-room clone), not only in a local hook.
  - Backend split is a PURE TRANSCRIPTION: spike found ZERO forward cross-section
    references (clean one-way DAG). This FACT is settled.

ADR-051 [DECIDED -- C-MOD-design + C-MOD-review; judgment J1 CONFIRMED with a
  relabel]: DOM node OWNERSHIP REGISTRY with owner tags, not module-prefixed IDs.
  - PROBLEM: a top-level `el` object caches the DOM nodes (28 registry entries;
    ~149 real el.<key> read sites) and every feature reads it. Modularization
    needs a single, checkable owner for each node, and el must become lazy
    (ADR-049 import-time rule) regardless.
  - DECISION: keep el AS the single registry, add owner tags (logicalName ->
    {id, owner}); a test asserts each getElementById id is owned by the
    referencing module. No codebase-wide ID rename; a stale registry reddens the
    suite (auto-enforced). Alternative (prefix-in-ID) rejected: it forces a
    rename and merely relocates drift into the ID string.
  - RELABEL (adversarial-review, dependency-quarantine lens): this is a node-
    OWNERSHIP registry, NOT a DOM quarantine. It fences node LOOKUP (which module
    may reference node X), not DOM MUTATION. Mutation stays smeared across ~48
    createElement sites plus every .textContent/.hidden/.disabled write. The
    later thin DOM seam (setText/show/hide/makeButton -- DEFERRED) is what closes
    that gap, and the owner tags are exactly the data that seam will consume. So
    the registry is an honest stepping-stone, not the quarantine itself; do not
    claim the DOM is fenced when only lookup is.
  - GUARD REQUIREMENT (plan-review + a reproduced false positive): the ownership
    test MUST be scope-aware / symbol-based, never a substring grep. A naive
    `el\.\w+` scan matched sel.bankId, label.className, and el.importPanel.
    textContent -- the same false-positive class ADR-050 forced the backend AST
    guard to avoid. The guard is intended-not-enforced from the first frontend
    extraction until the E10 cutover (the inline script is authoritative in that
    window); this window is named in the commit plan so no green-claim overstates
    enforcement.
  - ADDENDUM [thread two, pre-E1 -- E10 guard assertion semantics]: attributing
    all 158 real el.<key> lookups in the shipped inline script to their enclosing
    module found 13 GENUINE cross-owner reads that are correct by design (stage
    reads drill's choices/feedback; drill reads speech's speaker + stage's
    answerHint; session reads stats' streakPips; boot reaches action/answer/
    speaker/statsToggle for static wiring). So the literal reading "only the
    owner module may reference node X" is WRONG -- it would redden all 13. The
    E10 guard therefore asserts FOUR data-driven, scope-aware checks, not one:
      (A) REGISTRY INTEGRITY: each EL_REGISTRY entry has a unique id + non-empty
          owner in the known-module set; no two logical names share an id; no
          dead keys. This is the "stale registry reddens the suite" property.
      (B) OWNER-DECLARES: each node's owner module itself references the node
          (an owner that never touches its node is mis-assigned).
      (C) CROSS-OWNER ALLOWLIST (the check with teeth): any lookup of node X by
          a non-owner module must appear in an explicit CROSS_OWNER_READS policy
          table (the 13 edges are its initial rows; the stage<->drill rows are
          removed by the E4 decision below). A NEW undeclared cross-owner read
          reddens -- forcing a conscious review decision, the frontend analog of
          the backend legal-backward-edge census.
      (D) NO DOM AT IMPORT TIME (ADR-049 rule): no module-scope getElementById /
          el.<key> / document.* outside a function body -- with ONE named
          exemption: boot.js's boot-guard. boot.js is the entry module and its
          sole module-scope statement is the boot-guard (S7: "the only
          module-level eval-time statement"), an `if (document.readyState...)`
          that CALLS the hoisted boot() (deferred via DOMContentLoaded, or
          immediately if the DOM is ready). This is how the app starts once
          loaded via <script type=module src=boot.js>, and it is a faithful
          relocation of the inline script's guard (E4-decision reversal
          precedent: verbatim relocation beats purity-driven restructuring; and
          the backend LAYER_OVERRIDES precedent shows one named exemption is how
          this codebase handles a single legitimate exception). So check D's
          allowlist carries exactly one entry: boot.js's readyState guard. Every
          OTHER module (and any other module-scope document.* in boot.js) still
          reddens. CONSEQUENCE for option-(b) TESTS: importing boot.js runs the
          guard -> boot() at import, so boot.module.test.js must publish a full
          DOM fixture + fetch/navigator stubs BEFORE importing; the import IS the
          boot() integration act (boot is the entry point, so an integration
          test is the honest shape).
    RED-proofs (mirror C0.1's inject/parse/assert/restore): (1) inject an
    undeclared cross-owner read (el.statsPanel into a speech fn) -> C reddens;
    (2) inject a module-scope document.getElementById -> D reddens (into a
    NON-boot module, so the boot-guard exemption does not mask it).
    IMPLEMENTATION SURFACE [decided]: JS + acorn in a .test.js (glob-discovered),
    NOT Python AST in pytest. Rationale: colocates with the option-(b) frontend
    harness, uses the acorn already present via jsdom's dependency tree (zero new
    deps), and the backend already owns the Python-side guard. Scope-aware parse
    is mandatory (S8): strip comments, resolve the receiver so member chains on
    non-el objects -- sel.bankId, label.className, el.importPanel.textContent --
    are not counted; never a substring grep.
  - ADDENDUM [thread two, pre-E1 -- E4 owner-tag decision]: clearChoices /
    clearFeedback relocate INTO stage.js at E4 (ADR-053). When they do, the
    owner tags for `choices` and `feedback` FLIP drill->stage (the module that
    manipulates a node owns it), rather than leaving them drill-owned with stage
    allowlisted. This shrinks the CROSS_OWNER_READS table and keeps ownership
    honest. E4's cut carries the two owner-tag edits; the E10 guard's initial
    allowlist is written WITHOUT the stage<->drill rows accordingly.
  - SUPERSEDED [thread two, at E4 -- reversal after write-site enumeration]:
    the flip above is REVERSED; `choices` and `feedback` STAY drill-owned. The
    flip's premise ("the module that manipulates the node owns it" => stage) is
    contradicted by the code: enumerating every write site, drill remains the
    DOMINANT manipulator of both nodes after E4 -- el.choices is written by
    drill's renderChoices/markChoices/setChoicesDisabled (7 sites) vs stage's
    clearChoices (2); el.feedback by drill's showFeedback (4) vs stage's
    clearAnd/clearFeedback (3). Both modules touch both nodes regardless, so the
    flip does not remove a cross-owner edge -- it only reverses its direction,
    and flipping to stage makes the MAJORITY writer (drill) the cross-owner,
    inverting "owner = primary manipulator" and LENGTHENING the allowlist. So:
    keep owner=drill for both; stage's three teardown verbs (clearChoices,
    clearFeedback, clearAnd) become CROSS_OWNER_READS rows at E10 instead.
    Consequence: E4 is a pure code relocation touching NO index.html (consistent
    with E1-E3 and R1); the tags are inert today (nothing reads .owner, no guard
    exists pre-E10), so timing of the tag choice has zero behavior/test effect.
  - ADDENDUM [thread three, C-MOD-E10 -- AS-BUILT, guard now ENFORCED]: the
    "intended-not-enforced" window (line ~2105) is CLOSED. The guard is live as
    tests/frontend/ownership.guard.test.js: four scope-aware acorn checks (A
    registry integrity, B owner-declares, C cross-owner allowlist, D no-DOM-at-
    import with boot's readyState guard the sole exemption) + RED-proofs (inject
    an undeclared cross-owner read -> C reddens; inject a module-scope
    getElementById into a NON-boot module -> D reddens; and an extra module-scope
    getElementById in boot still reddens, proving the exemption is tight). AS-BUILT
    corrections to this ADR's pre-E1 numbers:
      * CROSS_OWNER_READS is 9 edges, NOT 13. Re-deriving attribution against the
        SHIPPED modules (the addendum warned "recompute, do not trust the old
        count blindly") yields: action->boot, answer->boot, answerHint->drill,
        choices->stage, feedback->stage, speaker->boot, speaker->drill,
        statsToggle->boot, streakPips->session. The drop from 13 is functions
        landing in their real homes during E1-E9. The stage->drill teardown reads
        (choices, feedback) are present per the E4 REVERSAL (stay drill-owned;
        stage's clearChoices/clearFeedback are the allowlisted cross-owner reads).
      * IMPLEMENTATION SURFACE dep correction: acorn is NOT on jsdom 29.1.1's
        dependency tree here, so the "zero new deps" claim does not hold. acorn is
        a test-only dep; install with `npm install jsdom acorn --no-save` (one
        command -- separate --no-save installs prune each other).
      * The guard also asserts NO STALE allowlist rows (every CROSS_OWNER_READS
        row is actually exercised), so the policy cannot rot as functions move.
    Separately, the cutover surfaced + fixed two latent missing-import bugs masked
    by the inline shared scope (boot.js->endSession, drill.js->onEndSession, from
    session.js); see knowledge-capture v-MOD-E10 and STATUS.md.

ADR-052 [DECIDED -- C-MOD-design + C-MOD-review, judgment J2]: frontend
  strategy is R1 duplicate-then-delete with a single atomic cutover.
  - PROBLEM: all 7 frontend tests share the classic-script global-leak harness
    (spike S5); flipping the tag to type=module breaks them ALL at once, so the
    harness migration is not naively incremental.
  - DECISION: build each ES module ALONGSIDE the untouched inline script, prove
    each with a new option-(b) test; the old 7 tests keep passing against the
    inline script until ONE cutover commit flips the tag, deletes the inline
    script, migrates the 7 tests, and lands the frontend guards. R2 (dual-load
    modules also as classic window-assigning scripts) rejected: dual-mode is a
    complection and risks divergence. The cutover is the one unavoidably-atomic,
    non-small commit; a candidate for the "let it go red" tool, kept mechanical
    (delete+rewire+migrate) because every module is already green via new tests
    before it lands.
  - DEFERRED (recorded, not done here): the thin DOM seam (Eskil quarantine --
    setText/show/hide wrappers making [hidden] impossible-to-violate) is a
    SEPARATE post-modularization item (it rewrites 156 sites, not relocation);
    bulk-import bounding gets an inert scaffold-comment when the split touches
    the import code.
  - This is a JUDGMENT: open to plan-review. Docs-only; suite unchanged at 311.
  - PLAN-REVIEW OUTCOME [C-MOD-review]: J2 CONFIRMED. R1 stands (R2's dual-load
    is a complection). Two refinements landed, neither reaching the design:
    * THE drill<->session CYCLE (measured, not in the original design): the
      frontend has a real bidirectional edge -- drill.loadQuestion/gradeAndShow
      call session.startSession/recordStats/renderSessionUI, while session's
      onStartSession/onRestartSession (wired inside renderSessionControls, so
      session-owned) call drill.loadQuestion. Decision ADR-053 (Option A: accept
      the cycle) + the stage relocation below.
    * R1 WIRING RULE (clarified): extracted modules are proven in ISOLATION by
      their own option-(b) tests and cross-import ONLY at the E10 cutover. This
      is what "duplicate-then-delete" means and it dissolves the extraction-order
      question -- no module imports another until every module exists.

ADR-053 [DECIDED -- C-MOD-review, spike-verified]: accept the drill<->session
  circular import (Option A), with a pure-relocation stage.js to thin it.
  - PROBLEM: drill and session are mutually dependent (above). Dependencies-first
    extraction is impossible for this pair.
  - OPTIONS: (A) accept the cycle, rely on ES-module cycle semantics; (B) extract
    a designed `phase` seam to break it -- rejected as a rewrite needing its own
    design pass; (C) merge drill+session -- rejected as oversized (session 28
    state/19 el + drill 38 state/51 el reads exceed one comfortable co-load).
  - DECISION: Option A. SPIKE-VERIFIED against real Node v22 + jsdom via the
    option-(b) harness: the drill<->session cycle resolves GREEN for BOTH import
    orders (7/7 and 3/3). MECHANISM (the durable fact): cross-cycle calls to
    HOISTED function declarations work even at module-eval time; a cycle breaks
    only if a module reads another's const/arrow export at eval time (proven RED
    via TDZ -- the spike's both-directions check). The real script has ZERO
    module-level eval-time cross-references (the sole module-scope statement is
    the boot-guard calling boot), so F2 holds across the whole surface, not just
    the DOM. Option A is therefore safe; the cutover needs no cycle-breaking.
  - RELOCATION (pure, folded into the frontend extraction): move drill-stage
    teardown + shared notification helpers (clearChoices, clearFeedback,
    clearAnd, setNote, setAnswerHint, clearAnswerHint) into stage.js, which both
    drill and session depend on ONE-WAY. This shrinks session->drill to the
    single honest loadQuestion edge (the cycle stays, but thin). It is
    relocation, not rewrite -- no logic added -- so it honors "a cut is a cut".
    One stage.js (not a stage/notify split): six small related DOM-write helpers
    are one coherent concern.

ADR-054 [DECIDED -- 2026-07 roadmap reassessment, post-modularization]: after
  roadmap #1 (modularization) shipped, re-rank the REMAINING roadmap items
  against the actual code, and sequence the next threads by score TEMPERED with
  explicit user constraints rather than by raw score alone.
  - CONTEXT: the original priority model (roadmap.py ITEMS + roadmap.md tiers,
    C-MOD-design era) scored every candidate before modularization existed.
    Six items have since shipped (#1 modularize, #2/#4/#5 arithmetic, #8 tests,
    #11 migration runner). A fresh read of the code changed several feasibility
    numbers, so the ranking was recomputed for what remains.
  - MODEL: roadmap.py now carries a REASSESS_2026_07 block beside the original
    ITEMS (kept as history). Same six axes, SAME weights (the user's priorities
    are stable); only code-reality axes (EFFORT/RISK/FOUND) moved. `uv run
    python3 roadmap.py` prints both the original ranking and the reassessment
    with deltas, plus the recommended sequence.
  - SURVEY FACTS that moved scores (verified against shipped code):
    * pick_next_question(candidates, history) is a single PURE swappable
      function, history already threaded through http_layer -> SM2 (+0.22) and
      adaptive selection get +EFFORT/+RISK.
    * migration runner DONE + battle-tested; elapsed_ms/difficulty columns
      exist -> new-migration / timing work de-risked.
    * JSONL/CSV import pipeline + translate/identify/free_response qtypes +
      bank-language plumbing ALL exist -> "vocab/language features" is mostly
      content + small extension of built seams, not net-new (NEW item, 4.00).
    * typing has NO infra beyond an empty "typing" config category stub ->
      genuinely net-new; LEARN rises, EFFORT stays moderate.
    * stats pipeline modular, elapsed_ms collected-but-unsummarized -> timing
      stats (+0.14) and stats depth (+0.14) become render-additions (quick wins).
    * FOUND drops for items whose leverage was "unblocks the refactor"
      (curriculum -0.18, adaptive -0.04) now that the refactor is done.
  - REASSESSED TOP (remaining): study curriculum 4.26, SM2 4.26, vocab/language
    4.00 (new), adaptive 3.94, logic drill 3.80, code drill 3.72, typing 3.58,
    timed-round 3.50, ... timing-stats 3.26, stats-depth 3.22, ADR-index 3.04.
  - DECISION -- SEQUENCE (score TEMPERED by constraints, NOT raw score):
    the raw top is a tie between the study curriculum and SM2, but three user
    constraints reshape the order: (a) the study curriculum runs in PARALLEL
    (user decision), so it is not a "next thread" and its FOUND was dropped
    accordingly; (b) the user wants product movement WITH comprehension, not a
    reflective-only phase (pure study is explicitly off the table); (c)
    modularization was heavy, so avoid a second architecturally-invasive thread
    immediately (SM2 is schema-invasive). Therefore lead with the highest-value
    item that is BOTH product-facing AND low-risk on proven seams:
      Thread N   : Vocab/language features (4.00) + timing-stats (3.26) + the
                   ADR index (3.04). One meaty-but-safe feature on built seams,
                   two quick wins folded in (both touch files the feature
                   touches anyway). Cashes in the modularization; safe re-warm-up.
      Thread N+1 : SM2 consolidation (4.26) + adaptive selection (3.94). Its own
                   focused, schema-invasive thread; the two share the
                   pick_next_question seam. Reserves the SM2 fields migration
                   (ADR-025) for here.
      Thread N+2 : Typing drill (3.58). A deliberate net-new qtype -- the test
                   of whether the modular seams absorb a genuinely new question
                   kind cleanly.
      Parallel   : Study curriculum (4.26) throughout, feeding on each thread's
                   fresh code (auditing new code teaches more per hour than
                   re-reading code already understood from the cutover).
  - ALTERNATIVES WEIGHED:
    * "SM2 next" (follow raw score): rejected as the immediate next thread --
      highest value but schema-invasive right after a brutal refactor; violates
      constraint (c). Kept as Thread N+1.
    * "Study curriculum next" (roadmap Phase 3 as written): rejected as a
      standalone next thread -- it is parallel now, and a reflective-only phase
      risks becoming avoidance of product work (constraint b). Runs in parallel
      instead.
    * "Deferred-cleanup thread next" (DOM-mutation seam, leaf-test merge, HTML/
      CSS conventions): rejected as next -- more refactoring right after a
      refactor (fatigue). Cleanup is INTERLEAVED into feature threads instead
      (timing-stats + ADR index ride the vocab thread).
    * "Typing next" (the user's meaty suggestion): deferred to Thread N+2 --
      it is net-new (least de-risked by modularization) and a better structural
      stress test once re-warmed up on the codebase.
  - USER-STATED GOAL served: "understand the codebase while moving it forward."
    Leading with vocab (largely reading + extending existing code) plus the
    parallel study is the comprehension throttle; the LLM loop ships features at
    speed while the audit forces human-speed reading of what shipped.
  - [RECONSIDER WHEN] a thread completes (re-run roadmap.py; the survey facts
    may shift again), or the user re-weights the axes.

ADR-055 [DECIDED -- C1, resolving the scheduling half of ADR-025]: SM2
scheduling state lives in a SEPARATE 1:1 side table, question_schedule.
- [DECIDED] Migration 4 creates question_schedule keyed on question_id
  (PK, REFERENCES questions) with six NOT NULL columns: easiness_factor,
  interval_days, repetition_count, due_date, last_review, lapse_count.
  SCHEMA_VERSION is 4. NOT columns on questions: scheduling state is
  mutable review state, not content, and a side table keeps the import
  pipeline (parse_import -> _normalize_question_dict ->
  insert_questions_bulk) entirely ignorant of scheduling. This reproduces
  sm2's proven "absence of row means never scheduled" semantics: a row is
  created whole on the first graded review, so no schedule field is ever
  NULL and the scheduler needs no NULL handling.
- Dates are ordinal-day integers (datetime.date.toordinal); day granularity
  IS the SM2 contract. The timezone/midnight policy lives at the HTTP edge
  where the ordinal is stamped (ADR-057), never in the schema.
- No backfill in the migration: rows appear lazily on the write path or via
  rebuild_schedule_from_response_log (C3). The migration is one idempotent
  CREATE TABLE IF NOT EXISTS.
- ADR-025's other half (grading_kind) stays unresolved and unadded; C2
  confirmed its reasoning -- the scheduler consumes a derived quality grade,
  not a persisted judging policy.

ADR-056 [DECIDED -- C2]: derive_recall_quality is BINARY in v1 (wrong -> 0,
correct -> 2); no quality is persisted.
- [DECIDED] Quality is derived at grading time from (correct, elapsed_ms),
  never stored (per ADR-025: no grading column). The v1 policy ignores
  elapsed_ms entirely; the parameter is accepted so a timing-derived policy
  can swap in behind the same signature. The middle grade (1, "correct with
  effort") is therefore UNREACHABLE in v1.
- Accepted cost: easiness never decays on effortful passes. Bounded by the
  lapse path (any miss resets interval to one day and floors toward 1.3).
- [RECONSIDER WHEN] per-qtype elapsed_ms baselines exist. C5's
  summarize_elapsed_percentiles (median/p90 per qtype) is deliberately that
  measurement: the stats landed BEFORE the policy so the v2 thresholds are
  evidence, not guesses. Do not add timing thresholds before then.
- The grade table (0->1, 1->3, 2->5 SM2 grades), EF floor 1.3, ceiling 3.0,
  and the 1 -> 6 -> interval*EF opening are pinned field-identical to
  sm2.sm2_update by the ported invariant suite in tests/test_logic.py; that
  suite carries the sm2 contract forward when sm2/ retires at A3.

ADR-057 [DECIDED -- C4]: the once-per-day rule, rebuild-equals-stored, and
the local-day stamp.
- [DECIDED] Only the FIRST graded attempt of a question's day advances its
  schedule (schedule_update_allowed_today: last_review != today). Every
  response is still logged -- the log is complete; same-day retries are
  history the scheduler ignores, both on the live write path and inside
  rebuild_schedule_from_response_log's fold. Rationale: a same-day retry
  re-tests minutes of memory, not the interval.
- [DECIDED] Schedule state is a CACHE of the response log. The invariant --
  folding responses through the rebuild reproduces the stored
  question_schedule on every field to 1e-9 -- is enforced by the 90-day
  simulation test in tests/test_http.py (two banks, throttling, deliberate
  same-day repeats). It holds only while derive_recall_quality is
  deterministic from stored fields; a policy change makes rebuild a
  REINTERPRETATION of history, not a reconstruction (acceptable, but the
  test must then pin the policy version).
- [DECIDED] The day ordinal is stamped ONCE per request at the top of the
  handler, from date.today() -- the LOCAL calendar day, the honest boundary
  for a single-user local tool (a 23:59 review and a 00:01 retry are
  different days). KNOWN LIMIT: responses.answered is stored in UTC, so the
  rebuild's ordinal derivation (substr of the ISO timestamp) matches the
  live stamp only while the local and UTC date agree at review time.
  Documented in both handler docstrings; revisit only if reviews near
  midnight prove common.
- Interval fuzz (apply_interval_fuzz) is deterministic per question_id (no
  RNG) precisely so this invariant can hold; intervals <= 2 days are exempt
  to protect the fixed 1 -> 6 opening.

ADR-058 [DECIDED -- A2]: authoring shells are append-first, two faces over
one parse, with explicit-create bank targeting.
- [DECIDED] `drill add` (the $EDITOR loop, git-commit contract: error
  banner reinserted as #! comments, untouched-or-empty buffer aborts) and
  `drill push` (stdin/file filter) are the two impure faces over the one
  pure author_parse; both append through insert_questions_bulk, the same
  funnel as HTTP import. Neither validates anything itself.
- [DECIDED, human, option ii] --bank names an EXISTING bank; creating one
  requires an explicit --category naming a seeded category. Rationale: in
  a long-lived personal collection, a typo in --bank must refuse loudly
  (exit 2, nothing created) rather than silently mint a stray bank. The
  HTTP import endpoint keeps its always-new-bank behavior; the CLI is the
  first append path.
- [DECIDED] The filter face emits parse failures to stderr as exactly
  `file:line: message` (stdin reads report as "stdin") and exits 1 writing
  nothing. That format IS the nvim integration (errorformat=%f:%l:\ %m; :w
  !drill push --bank X from a buffer; no plugin). To serve it, every
  ImportParseError raised on the authoring path carries an integer
  error_line attribute -- structured position data at the raise site, so
  the edge never re-parses its own error strings.
- Dispatch: add/push live in a second small data table (AUTHORING_COMMANDS)
  consulted before REPORT_COMMANDS, because their shape (args + side
  effects) is not the report shape (database_path -> str). This deviates
  from the kickoff amendment's "extend that table" wording while keeping
  its substance (data-driven, no argparse); recorded per R1/R2.
- [RESERVED] An in-buffer bank:/category: header (option c) is a
  backward-compatible later ergonomic; a `type: recall` self-graded qtype
  and any category-taxonomy re-grain are named follow-up decisions raised
  at the A2 STOP, not folded in here.

ADR-059 [DECIDED -- A3]: sm2/ retired; the contract is carried by ported
tests and code, recoverable from git.
- [DECIDED] The sm2/ directory is removed (git rm -r sm2). SM2
  consolidation is complete: the scheduler (sm2.sm2_update ->
  logic.advance_schedule_state, field-identical, RECALL_QUALITY_TO_SM2_GRADE
  mapping), the new-question throttle (apply_throttle_and_cap ->
  apply_new_question_throttle), and all five terminal views (render_table,
  failures_view, leeches_view, preview_view, dry_run_view) were ported into
  drill in threads B/C. The scheduling invariants (EF floor 1.3 / ceiling,
  point-value rows, 1->6 interval opening, non-decreasing intervals,
  stuck-item and recovery behavior, deterministic interval fuzz,
  once-per-day gate) are pinned by the SM2 section of tests/test_logic.py
  (C2). The exercise CONTENT is migratable by tools/migrate_sm2_exercises.py
  (A3, previous commit).
- Verify-before-delete evidence: what sm2/ held falls in two piles.
  CARRIED FORWARD (has a drill home + tests): scheduler, throttle, the five
  views, the exercise content, the invariant contract. NOT carried, by
  design (sm2-internal, superseded): sm2's own grade_item/domain_of (drill
  keys throttle on bank_id, not sm2 domains), its @@@ parser (drill authors
  via the A1/A2 buffer format; the one-off migration inlines a copy), its
  two-table DB layer (reconcile/fetch_*/commit_review -- drill has its own
  schedule table + review path, C4), its argparse CLI
  (build_review_card/build_reveal/run_review_session -- drill is web +
  REPORT_COMMANDS), and its frozen-schema/e2e tests (drill has its own).
  No load-bearing behavior is lost.
- RECOVERY: the full sm2/ tree exists at commit
  bf8f43d926e21c0934a61c0012e6dd31a3c95994 (the A3 script commit, the last
  before this deletion). Restore any part with:
      git checkout bf8f43d -- sm2/
  This is the whole archival mechanism -- git history is the archive; no
  snapshot copy is kept in the tree (a dead copy is drift bait). The
  migration script's directory argument would then point at the restored
  sm2/exercises.
- The real-fixtures migration test (test_migrate_sm2.py) skips once
  sm2/exercises is gone, so the suite stays green post-retirement; the
  synthetic-fixture tests keep pinning the script.

ADR-060 [DECIDED -- backlog, not this thread]: two named follow-ups from
the authoring thread, recorded so they are not lost.
- [DECIDED to build later] A self-graded recall qtype ("recall"): the
  prompt shows a criterion/expected answer after the attempt and the user
  presses pass/fail, rather than string-matching. This is the honest home
  for self-assessment content (the sm2 exercises, textbook concept
  questions) whose criteria are paragraphs no one types verbatim; without
  it, such content imports as free_response and the scheduler buries it as
  a false leech. Precedent: the recitation/catechism tradition and
  Wozniak's minimum-information principle (make the criterion specific
  enough that honest self-grading is easy). Scope: one qtype constant plus
  one review-mode branch (HTTP/C4 territory); the scheduler downstream is
  indifferent to where the boolean came from. LLM-in-the-loop grading was
  considered and rejected for the hot path (cost/sustainability/complexity);
  LLMs belong at AUTHORING time (extraction pipelines), not grading time.
- [DECIDED to build later] Category-taxonomy re-grain: today categories are
  a coarse seeded set (arithmetic/vocabulary/trivia/geography/logic/typing/
  code) and subject collides (physics, chemistry, calculus, art, history all
  land in "trivia"). The direction is category = grading/session domain,
  SUBJECT = tags (list-valued, already free), so coverage and per-session
  balancing key on the fine axis (tags) rather than encoding hierarchy into
  category name strings (which every consumer would then have to split).
  This is schema/consumer-touching and deserves its own thread; not folded
  in here.
