# Drill Tool -- Verification Practices (runtime thinking, not just spec + tests)

This doc records a class of failure that green tests and a followed spec do not
catch, and the practice that prevents it. It exists because the E10 modularization
cutover shipped 555 green tests and still broke the running app.

ASCII only. Live status stays in STATUS.md; this file is a slow-changing practice.

================================================================================
THE FAILURE (E10, concrete)
================================================================================
The E10 cutover replaced index.html's inline <script> with
<script type="module" src="boot.js">. All ten modules were extracted, 336
frontend tests were green, the ownership guard passed, the patch applied cleanly
in a fresh clone, and the full suite ended ALL GREEN. The app was still broken:
the page rendered but nothing was interactive.

Root cause: the backend had NO route serving the .js module files. Before the
cutover all JS was inline in index.html (served for free by the "/" route);
after it, the browser fetches GET /boot.js, which returned 404, so no module
loaded and boot() never ran. See http_layer.serve_module and the fix commit.

Why nothing caught it:
- THE SPEC POINTED AWAY. The handoff said "no HTTP contract change" and scoped
  E10 as frontend-only. Serving static .js is not an API-contract change, so it
  fell in a gap between "frontend work" and "backend work" that no instruction
  owned. Reading "no HTTP change" literally removed the transport layer from
  consideration entirely.
- THE TESTS SHARED THE BLIND SPOT. jsdom cannot execute type=module scripts
  (finding F1), so every frontend test imported the modules DIRECTLY and drove
  them. Not one test exercised the real over-HTTP load path -- the exact thing
  the cutover changed. Green tests gave false confidence precisely because they
  tested modules in isolation, never the integration the cutover created.

================================================================================
THE PRACTICE
================================================================================
1. MODEL THE RUNTIME, NOT JUST THE ARTIFACT. Before declaring a change done, ask
   "what actually happens at run time, on whose timeline?" For E10 the missing
   question was: "the browser now FETCHES ten files over HTTP -- who serves them?"
   A change whose PURPOSE is how code loads must be reasoned about as a real
   client hitting a real server, not as a module graph or a test fixture.

2. SMOKE-TEST THE REAL PATH FOR ANY CHANGE TO HOW THINGS LOAD OR WIRE TOGETHER.
   When the change alters transport, packaging, startup, routing, or the
   client/server boundary, run the real thing once end to end before "done":
   start the server, request "/", and confirm every asset the page pulls returns
   2xx with the right content type. This is non-negotiable for cutovers; it is
   the single check that would have caught the 404.

3. GREEN TESTS THAT BYPASS THE CHANGED PATH ARE NOT EVIDENCE. If the test harness
   structurally cannot exercise the thing you changed (jsdom not running
   type=module here), say so out loud and add a test at a layer that CAN. The
   E10 fix added backend serving-tests (every module served as JavaScript; every
   import specifier resolves to a served module; non-modules 404), proven to go
   RED without the route. The rule from CODING_CONVENTIONS applies: a gap that
   bites gets converted into a check, not a sterner reminder.

4. TREAT SPEC SILENCE AS A QUESTION, NOT A PERMISSION. "No HTTP change" meant no
   API-contract change; it did not mean "the transport takes care of itself."
   When a scope boundary would leave some real runtime concern unowned, surface
   it rather than letting the literal wording decide.

================================================================================
CUTOVER / LOAD-PATH CHECKLIST (use before declaring such a change done)
================================================================================
- [ ] Start the actual server and open the actual URL (or drive the real WSGI
      callable for every asset path, which is equivalent here).
- [ ] Confirm "/" serves, and EVERY asset the page references returns 2xx with a
      correct content type (for ES modules: a JavaScript MIME, or the browser
      refuses type=module).
- [ ] Crawl the dependency graph: every import specifier any module pulls must
      itself be served (a mid-graph 404 breaks everything downstream).
- [ ] Confirm the entry actually runs (here: boot() fires and wires listeners) --
      not just that files return 200.
- [ ] Add/confirm a test at a layer that exercises the changed path, and prove it
      RED without the fix.
- [ ] Only then: run the suite and report the green count.

================================================================================
STARTUP OBSERVABILITY (so the passive-server model is not a trap)
================================================================================
The server is PASSIVE: `uv run drill.py` initializes the DB, registers routes,
and listens -- no application code runs at startup. The app runs on the CLIENT's
timeline: opening the URL serves index.html, the browser fetches the module graph
(boot.js + imports), then calls boot(). The startup log now says this explicitly
and tells the operator to watch for "serving module ..." lines on first connect;
their ABSENCE after opening the URL means the scripts did not load (the E10 bug's
signature). boot.js logs "modules loaded", "boot() wiring listeners",
"boot() complete", and "boot() failed: <err>" so the load+flow is visible in the
browser console. The lesson: when a system's real work happens on someone else's
timeline, make startup say so, and make the first real interaction observable.
