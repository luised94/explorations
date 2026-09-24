INTERFACE SKETCH SEED PLAYBOOK-DESIGN-007_interface-sketch-seed
===============================================================
date:  2026-09
type:  design
scope: a recyclable starting point for a future DESIGN thread on the
       interface. States the premise and the open choices; resolves
       none of them. Self-contained: it does not need the design
       record present, though it came from the same thread (companion:
       PLAYBOOK-DESIGN-007_harness-interface-and-build.md).

  ONE CORRECTION ON FILING. The branch that wrote this seed stated the
  navigated object as a TREE. The companion design record leaves the
  shape open (its open question A: tree, DAG or cyclic), and that
  record is right to. "Tree" below is replaced by "graph" and the
  choice is left to question A.


PREMISE (settled, carried in)

  The pain points with current chat interfaces -- cannot branch or
  navigate, cannot cheaply transform text before sending, cannot
  splice in repository and local files -- are all context-assembly
  operations, not model-quality problems. The model is stateless; the
  payload is the only lever. An interface's real job is assembling and
  steering that payload.

  The thesis that follows: the object being navigated is a graph of
  conversation states, each state holding an assembled context
  payload. The right interface is a modal editor over that graph,
  keyboard-driven, in the vimium and nvim register of interaction.
  This is the beam the whole design hangs from.

  Envisioned stack: frontend (html/css/js), python backend, served to
  the browser, modal keyboard control. One exploratory precedent is
  already in use: an nvim buffer as the interface.


NAIVE VERSUS VETERAN REACH (the one framing to keep)

  Naive reach: build a better chat UI -- add a branch button, a file
  picker, a text-transform menu. Bolts features onto a linear
  transcript.

  Veteran reach: the transcript is a navigable data structure, and the
  editor is the thing that assembles payloads over it.
    - Branching is fork-a-node on the graph.
    - "Transform text" is edit-the-payload-before-send.
    - "Bring in a file" is splice-a-typed-span into the stream. The
      grammar-boundary work reappears here: a spliced file is a typed
      span carrying its own grammar (design record finding 4; MCP
      typed content blocks are the shipped precedent).

  The gap between the two is the design thesis: linear transcript plus
  features, versus conversation graph plus modal editor. Pick the
  second.


OPEN QUESTIONS FOR THE FUTURE BRANCH (posed, not answered)

  1. NODE MODEL. What exactly is a node -- one turn, one message, one
     payload snapshot? What does a fork copy and what does it share
     with its parent? Is history immutable (a fork creates a new path)
     or editable in place (editing a node rewrites downstream)? And
     the design record's question A: tree, DAG, or cyclic.

  2. PAYLOAD AS A FIRST-CLASS EDITABLE OBJECT. If the payload is what
     gets edited before send, what is its representation -- a flat
     buffer, a sequence of typed spans, a document with regions? How
     does a spliced file, a repository excerpt, or a transformed
     selection enter it and get marked with its grammar?

  3. MODAL GRAMMAR. What are the modes and verbs of the editor itself?
     These are DISTINCT from the design and implement modes in the
     working defaults; do not confuse the two. What is the navigate,
     edit, send, fork verb set? Does vimium-style hinting map onto
     graph navigation, span selection, or both?

  4. BRANCH NAVIGATION AND DISPLAY. How is a graph of conversation
     states shown and moved through on a 2D screen -- how are branches
     surfaced, collapsed, compared, merged or abandoned? This is the
     pain that started it; it needs a concrete interaction, not only a
     data model.

  5. LOCAL I/O BOUNDARY. What does the python backend expose for
     pulling repository and local files, and where is the trust line on
     reading and writing the local filesystem from a browser-served
     frontend, across both the WSL and Windows sides?

  6. RELATIONSHIP TO THE HARNESS. This editor is project 1, buildable
     without model orchestration. The harness is project 2 and depends
     on this existing first. Keep the seam: the editor must deliver
     value with zero orchestration before any agent layer attaches.


WHAT NOT TO DO WHEN PICKING THIS UP

  Do not start from the harness or tool-calling. Build the navigation
  and payload-assembly editor first; it unblocks everything else and
  carries none of the orchestration risk. Starting from agents means
  debugging agent loops inside an interface that does not yet exist.
