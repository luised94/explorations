/* session.js -- session lifecycle: transitions, derived session UI, and the
 * on*Session handlers (roadmap #1 modularization, E7).
 *
 * Verbatim relocation from the index.html inline script -- no behavior change.
 * The ONE style change (S9): the terse local `sel` in startSession is renamed
 * to `selection` (it holds state.selection or the arithmetic default). Other
 * `sel` locals live in drill (questionQuery) and speech (activeBankLanguage)
 * and are handled in their own modules / left as-is per S9's scoping.
 *
 * Contents:
 *   activeSession / startSession / recordStats / endSession -- the transition
 *     layer (the only mutators of state.sessions).
 *   renderSessionUI / renderSessionControls -- derived render (never
 *     hand-patched); the control row wires on*Session handlers INSIDE
 *     renderSessionControls, so those handlers are session-owned (S6).
 *   onStartSession / onRestartSession / onEndSession -- the handlers.
 *   endSessionOnUnload -- dev cleanup on page close (see below).
 *
 * THE drill<->session CYCLE (S6, ADR-053 Option A): this module imports
 * loadQuestion + enterResting from drill.js, and drill.js imports startSession +
 * recordStats + renderSessionUI from here. The cycle is inherent to the domain
 * and RESOLVES GREEN under ESM because every cross-cycle call targets a HOISTED
 * function declaration and no module reads another's export at eval time (S7).
 * Because the cycle is a true bidirectional import, session.js and drill.js are
 * created together in one commit (neither is importable without the other);
 * both are proven by their option-(b) tests wired to the real other side.
 *
 * DEPENDENCIES (as-built): imports state, stage (setNote), api (apiPost),
 * stats (renderStats, renderRunLog), speech (cancelSpeech, setSpeakerSpeaking),
 * and drill (loadQuestion, enterResting -- the cycle edge). Section R said
 * "state, stage, api, stats"; speech and drill are added (drill = the cycle).
 *
 * ADR-049 import-time rule: no DOM at import time; el.<node> read only inside
 * functions.
 *
 * Per R1 (ADR-052) the inline script keeps its own copies until the E10
 * cutover; nothing imports this module until then.
 *
 * ASCII only.
 */

import { state, ZERO_STATS } from "./state.js";
import { el } from "./el.js";
import { apiPost } from "./api.js";
import { setNote } from "./stage.js";
import { renderStats, renderRunLog } from "./stats.js";
import { cancelSpeech, setSpeakerSpeaking } from "./speech.js";
import { loadQuestion, enterResting } from "./drill.js";

/* ---- Session state: transitions (the only mutators of state.sessions) -- */

/* Find the active record (status "active"), or null in the resting state. */
export function activeSession() {
  for (var i = 0; i < state.sessions.length; i++) {
    if (state.sessions[i].id === state.activeSessionId) {
      return state.sessions[i];
    }
  }
  return null;
}

/* Start a session on the server for the current selection and append a fresh
   active record carrying its category and (for bank categories) its bank.
   Sends bank_id to /api/session/start when a bank is selected. Resets the
   per-session recent-id window. Returns the new id.

   The selection defaults to arithmetic when nothing else is chosen (e.g. on
   boot), preserving C-013's arithmetic auto-start. */
export async function startSession() {
  var selection = state.selection || {
    categoryId: state.arithmeticCategoryId,
    categoryName: state.arithmeticCategoryName,
    bankId: null,
    bankName: null
  };
  var body = { category_id: selection.categoryId };
  if (selection.bankId !== null && selection.bankId !== undefined) {
    body.bank_id = selection.bankId;
  }
  var result = await apiPost("/api/session/start", body);
  state.sessions.push({
    id: result.session_id,
    categoryId: selection.categoryId,
    categoryName: selection.categoryName,
    bankId: selection.bankId !== undefined ? selection.bankId : null,
    bankName: selection.bankName !== undefined ? selection.bankName : null,
    status: "active",
    stats: ZERO_STATS
  });
  state.activeSessionId = result.session_id;
  state.recentIds = []; /* fresh repeat-avoidance window per session */
  return result.session_id;
}

/* Fold a session_stats snapshot (from /api/answer) into the active record.
   Pure assignment into the one record; no DOM here. */
export function recordStats(sessionId, stats) {
  for (var i = 0; i < state.sessions.length; i++) {
    if (state.sessions[i].id === sessionId) {
      state.sessions[i].stats = {
        total: stats.total,
        correct: stats.correct,
        accuracy: stats.accuracy,
        streak: stats.streak
      };
      return;
    }
  }
}

/* End a session on the server and mark its record "ended". If it is the
   active one, the resting state begins (activeSessionId -> null). Ending an
   unknown/already-ended id is a harmless server no-op, so this is safe to
   call without first checking server state. */
export async function endSession(sessionId) {
  if (sessionId === null) {
    return;
  }
  /* C-018a: a run ending should not leave a word still being spoken. */
  cancelSpeech(setSpeakerSpeaking);
  try {
    await apiPost("/api/session/end", { session_id: sessionId });
  } catch (error) {
    /* A failed end should not strand the UI: still mark it ended locally and
       surface the message. The server treats unknown ids as no-ops anyway. */
    setNote(error.message, true);
  }
  for (var i = 0; i < state.sessions.length; i++) {
    if (state.sessions[i].id === sessionId) {
      state.sessions[i].status = "ended";
      break;
    }
  }
  if (state.activeSessionId === sessionId) {
    state.activeSessionId = null;
  }
}

/* ---- Session UI: derived renders (never hand-patched) ----------------- */

/* Draw every session-derived surface from the array in one place: the stats
   bar (active session, or zeros when resting) and the run log (ended,
   non-empty runs, newest-first). */
export function renderSessionUI() {
  var active = activeSession();
  renderStats(active ? active.stats : ZERO_STATS);
  /* The streak pips are meaningful only for an in-progress run; hide the row
     in the resting state so the bar reads as "nothing in progress". */
  el.streakPips.style.visibility = active ? "visible" : "hidden";
  renderSessionControls(active);
  renderRunLog();
}

/* The control row. Active: a "Restart" and an "End" control. Resting: a
   single "Start new session" control. Rendered from state, so the two states
   share one code path. */
export function renderSessionControls(active) {
  el.sessionControls.textContent = "";

  var label = document.createElement("span");
  label.className = "session-label";
  if (active) {
    label.textContent = "Session " + active.id;
    el.sessionControls.appendChild(label);

    var restart = document.createElement("button");
    restart.type = "button";
    restart.className = "secondary";
    restart.id = "restart-session";
    restart.textContent = "Restart";
    restart.addEventListener("click", onRestartSession);
    el.sessionControls.appendChild(restart);

    var end = document.createElement("button");
    end.type = "button";
    end.className = "secondary";
    end.id = "end-session";
    end.textContent = "End session";
    end.addEventListener("click", onEndSession);
    el.sessionControls.appendChild(end);
  } else {
    label.textContent = "No active session";
    el.sessionControls.appendChild(label);

    var start = document.createElement("button");
    start.type = "button";
    start.className = "secondary";
    start.id = "start-session";
    start.textContent = "Start new session";
    start.addEventListener("click", onStartSession);
    el.sessionControls.appendChild(start);
  }
}

/* ---- Handlers (wired inside renderSessionControls; session-owned, S6) -- */

/* Restart = end the current run (preserved in the log) + start a fresh one,
   then drill. Confirmed behavior: the just-ended run stays visible; the new
   run begins with zeroed stats. */
export async function onRestartSession() {
  setNote("");
  await endSession(state.activeSessionId);
  renderSessionUI(); /* show the ended run in the log + resting bar briefly */
  await loadQuestion(); /* auto-starts a fresh session and serves a question */
}

/* Start a new session from the resting state and drill. */
export async function onStartSession() {
  setNote("");
  await loadQuestion(); /* loadQuestion auto-starts when none is active */
}

export async function onEndSession() {
  if (state.activeSessionId === null) {
    return;
  }
  setNote("");
  await endSession(state.activeSessionId);
  enterResting();
  renderSessionUI();
}

/* Dev cleanup, not session UI: end the active session on page close/refresh
   so the DB does not fill with dangling never-ended sessions during
   development. Unknown-id end is a harmless no-op server-side. Uses
   sendBeacon so the request survives unload. */
export function endSessionOnUnload() {
  /* C-018a: stop speech on the way out so nothing speaks during unload. */
  cancelSpeech();
  if (state.activeSessionId === null) {
    return;
  }
  var payload = JSON.stringify({ session_id: state.activeSessionId });
  if (navigator.sendBeacon) {
    navigator.sendBeacon(
      "/api/session/end",
      new Blob([payload], { type: "application/json" })
    );
  } else {
    /* Best-effort fallback for browsers without sendBeacon. */
    fetch("/api/session/end", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: payload,
      keepalive: true
    });
  }
}
