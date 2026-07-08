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
 *   renderSessionSummary / clearSessionSummary -- the Q4 closing view after
 *     an explicit End (summary + optional Q4b feedback capture).
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
  state.recallAttempts = []; /* rec-4: fresh grading queue per session */
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
/* End a session on the server and mark its record "ended". If it is the
   active one, the resting state begins (activeSessionId -> null). Ending an
   unknown/already-ended id is a harmless server no-op, so this is safe to
   call without first checking server state.

   Q4/Q4b: feedback is an optional {rating, note} object merged into the
   request; the server updates only the fields provided, so a later bare
   end (the unload beacon) cannot erase saved feedback. Returns the server
   response ({ended, summary}) or null when the request failed or was
   skipped, so callers can render the closing summary. */
export async function endSession(sessionId, feedback) {
  if (sessionId === null) {
    return null;
  }
  /* C-018a: a run ending should not leave a word still being spoken. */
  cancelSpeech(setSpeakerSpeaking);
  var body = { session_id: sessionId };
  if (feedback && feedback.rating !== undefined && feedback.rating !== null) {
    body.rating = feedback.rating;
  }
  if (feedback && feedback.note) {
    body.note = feedback.note;
  }
  var result = null;
  try {
    result = await apiPost("/api/session/end", body);
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
  return result;
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
  /* Q4: the closing summary belongs to the resting state only; a new run
     dismisses it (renderSessionUI runs on every transition). */
  if (active) {
    clearSessionSummary();
  }
  renderSessionControls(active);
  renderRunLog();
}

/* ---- End-of-session summary (Q4/Q4b) ----------------------------------- */

/* Hide and empty the closing view. */
export function clearSessionSummary() {
  el.sessionSummary.textContent = "";
  el.sessionSummary.hidden = true;
}

/* The closing view after an explicit End: what happened this run, plus the
   optional feedback capture. summary is the server's session/end payload
   ({total, correct, accuracy, streak, new_introduced_today, due_remaining})
   or null/undefined when the end failed -- then nothing is shown. Saving
   feedback re-posts session/end with {rating, note}; the server merges
   fields without erasing the first end (Q4b). */
export function renderSessionSummary(summary, sessionId) {
  clearSessionSummary();
  if (!summary) {
    return;
  }

  var line = document.createElement("div");
  var text = "Session ended: " + summary.correct + "/" + summary.total
    + " correct (" + Math.round(summary.accuracy * 100) + "%).";
  if (summary.new_introduced_today !== null
      && summary.new_introduced_today !== undefined) {
    text += " " + summary.new_introduced_today + " new introduced today.";
  }
  if (summary.due_remaining !== null && summary.due_remaining !== undefined) {
    text += " " + summary.due_remaining + " due next in this bank.";
  }
  line.textContent = text;
  el.sessionSummary.appendChild(line);

  var feedbackRow = document.createElement("div");
  feedbackRow.className = "summary-feedback-row";

  var feedbackLabel = document.createElement("span");
  feedbackLabel.textContent = "How was it? (optional)";
  feedbackRow.appendChild(feedbackLabel);

  var ratingSelect = document.createElement("select");
  ratingSelect.id = "session-rating";
  var blank = document.createElement("option");
  blank.value = "";
  blank.textContent = "rating";
  ratingSelect.appendChild(blank);
  for (var value = 1; value <= 5; value++) {
    var option = document.createElement("option");
    option.value = String(value);
    option.textContent = String(value);
    ratingSelect.appendChild(option);
  }
  feedbackRow.appendChild(ratingSelect);

  var noteInput = document.createElement("input");
  noteInput.type = "text";
  noteInput.id = "session-note";
  noteInput.placeholder = "note (how it felt, energy, difficulty)";
  feedbackRow.appendChild(noteInput);

  var save = document.createElement("button");
  save.type = "button";
  save.className = "secondary";
  save.id = "save-session-feedback";
  save.textContent = "Save feedback";
  save.addEventListener("click", async function onSaveFeedback() {
    var feedback = {};
    if (ratingSelect.value !== "") {
      feedback.rating = parseInt(ratingSelect.value, 10);
    }
    if (noteInput.value.trim() !== "") {
      feedback.note = noteInput.value.trim();
    }
    if (feedback.rating === undefined && feedback.note === undefined) {
      setNote("nothing to save -- pick a rating or write a note");
      return;
    }
    try {
      await apiPost("/api/session/end", {
        session_id: sessionId,
        rating: feedback.rating,
        note: feedback.note
      });
      /* Replace the capture controls with an explicit confirmation -- the
         visible state change IS the receipt (the human's report: leaving
         the filled controls in place read as "nothing happened"). */
      feedbackRow.textContent = "Feedback saved.";
    } catch (error) {
      setNote(error.message, true);
    }
  });
  feedbackRow.appendChild(save);

  el.sessionSummary.appendChild(feedbackRow);
  el.sessionSummary.hidden = false;
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


/* ---- The batched self-assessment pass (rec-5) --------------------------

   Shown at the explicit End when recall attempts are queued: each item
   presents the question, the user's typed attempt, and the now-revealed
   criterion, with Pass/Fail per item. Each grade POSTs /api/response/grade
   (the rec-3 one-way transition; a double-tap gets a harmless 400) and the
   returned session_stats snapshot is kept so the closing summary reflects
   the graded outcomes. "Finish" skips whatever remains -- ungraded rows
   stay NULL and inert (rec-1), the designed abandonment behavior. */
export function renderRecallGrading(attempts, sessionId, baseSummary) {
  clearSessionSummary();

  var heading = document.createElement("div");
  heading.textContent = "Self-assessment: grade your " + attempts.length
    + " recall attempt(s). The criterion is revealed below each attempt.";
  el.sessionSummary.appendChild(heading);

  var remaining = attempts.length;
  var latestStats = null;

  function finishGrading() {
    var summary = baseSummary;
    if (latestStats !== null) {
      summary = {
        total: latestStats.total,
        correct: latestStats.correct,
        accuracy: latestStats.accuracy,
        streak: latestStats.streak,
        new_introduced_today:
          baseSummary ? baseSummary.new_introduced_today : null,
        due_remaining: baseSummary ? baseSummary.due_remaining : null
      };
    }
    renderSessionSummary(summary, sessionId);
  }

  var finish = document.createElement("button");
  finish.type = "button";
  finish.className = "secondary";
  finish.id = "finish-grading";
  finish.textContent = "Skip remaining and finish";
  finish.addEventListener("click", finishGrading);

  attempts.forEach(function (attempt) {
    var item = document.createElement("div");
    item.className = "recall-grade-item";

    var question = document.createElement("div");
    question.textContent = attempt.questionText;
    item.appendChild(question);

    var yours = document.createElement("div");
    yours.textContent = "Your attempt: " + attempt.userInput;
    item.appendChild(yours);

    var criterion = document.createElement("div");
    criterion.textContent = "Answer: " + attempt.expected;
    item.appendChild(criterion);

    var verdictRow = document.createElement("div");
    verdictRow.className = "summary-feedback-row";
    function grade(correct, chosenLabel) {
      return async function onGrade() {
        try {
          var result = await apiPost("/api/response/grade", {
            response_id: attempt.responseId,
            correct: correct
          });
          latestStats = result.session_stats;
          verdictRow.textContent = chosenLabel;
          remaining -= 1;
          if (remaining === 0) {
            finishGrading();
          } else {
            finish.textContent = "Skip remaining and finish ("
              + remaining + " left)";
          }
        } catch (error) {
          setNote(error.message, true);
        }
      };
    }
    var pass = document.createElement("button");
    pass.type = "button";
    pass.className = "secondary recall-pass";
    pass.textContent = "Pass";
    pass.addEventListener("click", grade(true, "Passed"));
    verdictRow.appendChild(pass);
    var fail = document.createElement("button");
    fail.type = "button";
    fail.className = "secondary recall-fail";
    fail.textContent = "Fail";
    fail.addEventListener("click", grade(false, "Failed"));
    verdictRow.appendChild(fail);
    item.appendChild(verdictRow);

    el.sessionSummary.appendChild(item);
  });

  el.sessionSummary.appendChild(finish);
  el.sessionSummary.hidden = false;
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
  var endedSessionId = state.activeSessionId;
  /* rec-5: hand the queued recall attempts to the grading pass and clear
     the state copy -- once the session is ending they belong to the pass,
     and a subsequent startSession must not resurrect them. */
  var pendingAttempts = state.recallAttempts;
  state.recallAttempts = [];
  var result = await endSession(endedSessionId);
  enterResting();
  renderSessionUI();
  /* Q4: the explicit End shows the closing view (summary + optional
     feedback). Restart and selection switches flow straight into a new run,
     so they do not -- the next renderSessionUI dismisses any leftover.
     rec-5: when recall attempts await self-assessment, the grading pass
     comes FIRST (attempt shown, criterion revealed, pass/fail per item);
     the summary follows with the graded outcomes folded in. */
  if (pendingAttempts.length > 0) {
    renderRecallGrading(
      pendingAttempts, endedSessionId, result ? result.summary : null
    );
  } else {
    renderSessionSummary(result ? result.summary : null, endedSessionId);
  }
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
