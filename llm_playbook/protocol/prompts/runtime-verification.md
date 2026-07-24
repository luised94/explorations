PROMPT: RUNTIME VERIFICATION
============================
date: 2026-07
type: prompt
scope: the class of failure that green tests and a followed spec do
NOT catch -- a change to how code LOADS, PACKAGES, STARTS, ROUTES, or
crosses a client/server boundary -- and the smoke test that catches
it. Generalized from a real incident.

USE THIS WHEN
  The change alters TRANSPORT, PACKAGING, STARTUP, ROUTING, or the
  client/server boundary. Symptoms that you are in this territory:
    - the change is described as "just moving code" or "no contract
      change"
    - the artifact is reorganized but its behavior is meant to be
      identical
    - the thing that changed is HOW something is fetched, served,
      bundled, imported, or started
    - the test suite drives the units DIRECTLY rather than through
      the path the change modified

SKIP IT WHEN the change is pure logic inside an already-loaded unit,
with no effect on how that unit reaches the runtime.

THE ORIGINATING FAILURE (kept concrete on purpose)
  A frontend modularization cutover replaced an inline script with a
  module-loading script tag. Ten modules extracted, 336 frontend
  tests green, ownership guard passed, the patch applied cleanly in a
  fresh clone, full suite ALL GREEN at 555. The app was broken: the
  page rendered and nothing was interactive.
  Root cause: the backend had no route serving the module files.
  Previously all code was inline and served for free by the page
  route; afterwards the browser fetched them and got 404, so nothing
  loaded and startup never ran.
  Why nothing caught it:
    - THE SPEC POINTED AWAY. The handoff said "no HTTP contract
      change" and scoped the work as frontend-only. Serving static
      assets is not an API-contract change, so it fell in a gap
      between "frontend work" and "backend work" that no instruction
      owned. Reading the scope literally removed the transport layer
      from consideration entirely.
    - THE TESTS SHARED THE BLIND SPOT. The harness could not execute
      the real loading mechanism, so every test imported the units
      directly and drove them. Not one test exercised the real load
      path -- the exact thing the change altered. Green tests gave
      false confidence PRECISELY because they tested units in
      isolation and never the integration the change created.

THE PRACTICE
  1. MODEL THE RUNTIME, NOT JUST THE ARTIFACT. Before declaring the
     change done, ask what actually happens at RUN TIME, on whose
     timeline. The missing question above was: the client now fetches
     ten files -- WHO SERVES THEM? A change whose purpose is how code
     loads must be reasoned about as a real client hitting a real
     server, not as a dependency graph or a test fixture.

  2. SMOKE-TEST THE REAL PATH, END TO END. Start the thing for real.
     Exercise the actual entry point. Confirm that EVERY asset the
     entry point pulls returns a success status with the right
     content type. "The suite is green" is not evidence about a path
     the suite does not traverse.

  3. TREAT A SCOPE BOUNDARY AS A SUSPECT, NOT A SHIELD. When a
     handoff says a layer is out of scope, ask whether the change
     creates NEW traffic across that layer. A scope statement
     describes intent; it does not constrain what the runtime
     actually does.

  4. NAME THE GAP BETWEEN WHAT THE HARNESS CAN DO AND WHAT THE
     RUNTIME DOES. Where the harness structurally cannot exercise a
     mechanism, that mechanism has NO test coverage regardless of the
     green count. Write that down as a known blind spot rather than
     letting the total imply coverage it does not have.

CHECKLIST FOR A CUTOVER OR LOAD-PATH CHANGE
  - What does the client fetch now that it did not fetch before?
  - Which route serves each of those, and does that route exist?
  - What is the content type, and does the runtime require a
    specific one?
  - Does startup actually run, or does it merely appear to?
  - Did anything render successfully while remaining non-functional?
  - Which of the above does the suite actually traverse, and which
    does it bypass?

REPORTING
  A green count is reported WITH the statement of what path it
  covers. "555 green" and "555 green, none of which traverse the
  module load path" are different claims, and only the second one is
  honest about a cutover.
