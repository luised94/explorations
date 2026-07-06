/* drill.js -- the drill loop: question load, render, answer, grade, feedback,
 * and the phase machine (roadmap #1 modularization, E8).
 *
 * Verbatim relocation from the index.html inline script -- no behavior change.
 * The ONE style change (S9): the terse local `sel` in questionQuery is renamed
 * to `selection` (holds state.selection or the arithmetic default).
 *
 * THE drill<->session CYCLE (S6, ADR-053 Option A): this module imports
 * startSession + recordStats + renderSessionUI (and endSession/activeSession/
 * onEndSession) from session.js, and session.js imports loadQuestion +
 * enterResting from here. The cycle resolves green under ESM: every cross-cycle
 * call targets a HOISTED function declaration and no module reads another's
 * export at eval time (S7). drill.js and session.js are created in ONE commit
 * because the cycle is a true bidirectional import (neither is importable
 * without the other); both are proven by option-(b) tests wired to the real
 * other side.
 *
 * DEPENDENCIES (as-built): imports state, el, api (apiGet/apiPost), stage
 * (setNote/setAnswerHint/clearAnswerHint/clearChoices/clearAnd/clearFeedback),
 * speech (cancelSpeech/updateSpeakerVisibility/setSpeakerSpeaking),
 * timing (nowMs), and session (the cycle edge).
 *
 * ADR-049 import-time rule: no DOM at import time; el.<node> read only inside
 * functions. Per R1 (ADR-052) the inline script keeps its own copy until the
 * E10 cutover; nothing imports this module until then.
 *
 * ASCII only.
 */

import { state, RECENT_MAX } from "./state.js";
import { el } from "./el.js";
import { apiGet, apiPost } from "./api.js";
import {
  setNote, setAnswerHint, clearAnswerHint, clearChoices, clearAnd, clearFeedback
} from "./stage.js";
import {
  cancelSpeech, updateSpeakerVisibility, setSpeakerSpeaking
} from "./speech.js";
import { nowMs } from "./timing.js";
import { startSession, recordStats, renderSessionUI, onEndSession } from "./session.js";

export async function loadQuestion() {
  state.phase = "loading";
  state.current = null;
  state.answerStartMark = null; /* C-018c: no stale mark across a new load */
  el.action.disabled = true;
  el.answer.disabled = true;
  el.answer.value = "";
  clearChoices();
  clearFeedback();
  clearHints(); /* Thread N.1: drop prior question's revealed hints */
  /* C-018a: stop any prior word and hide the speaker until the next question
     renders, so speech never carries across a question transition. */
  cancelSpeech(setSpeakerSpeaking);
  if (el.speaker) {
    el.speaker.hidden = true;
  }
  el.expression.textContent = "...";

  try {
    /* Auto-start a session if none is active. For arithmetic this is the
       C-013 auto-start; for a bank category the session was already started
       by the bank selection (onBankChange), so this branch is the arithmetic
       fallback / resting-restart path. */
    if (state.activeSessionId === null) {
      await startSession();
      renderSessionUI();
    }
    var payload = await apiGet(questionQuery());
    state.current = payload;
    /* Track served bank question ids for soft repeat-avoidance (recent=).
       Arithmetic ids are null and are not tracked. */
    if (payload.question_id !== null && payload.question_id !== undefined) {
      pushRecent(payload.question_id);
    }
    renderQuestion(payload);
    enterAnswering();
  } catch (error) {
    el.expression.textContent = "--";
    setNote(error.message, true);
    state.phase = "idle";
  }
}

/* Build the GET /api/question URL for the active selection. Arithmetic uses
   just category; a bank category adds bank_id and the recent= window. */
export function questionQuery() {
  var selection = state.selection || { categoryName: state.arithmeticCategoryName,
                                       bankId: null };
  if (selection.bankId === null || selection.bankId === undefined) {
    var arithmetic = "/api/question?category=arithmetic";
    /* C-D2c: carry the selected difficulty rung when one is set. null means
       the default path -- omit the param entirely so the request is identical
       to pre-#2 (the server treats absent difficulty as the no-rung default). */
    if (state.difficulty !== null && state.difficulty !== undefined) {
      arithmetic += "&difficulty=" + encodeURIComponent(state.difficulty);
    }
    return arithmetic;
  }
  var params = "category=" + encodeURIComponent(selection.categoryName)
             + "&bank_id=" + encodeURIComponent(selection.bankId);
  if (state.recentIds.length > 0) {
    params += "&recent=" + state.recentIds.join(",");
  }
  return "/api/question?" + params;
}

/* Keep the last RECENT_MAX served bank ids. */
export function pushRecent(id) {
  state.recentIds.push(id);
  if (state.recentIds.length > RECENT_MAX) {
    state.recentIds = state.recentIds.slice(-RECENT_MAX);
  }
}

/* Show or hide the active-rung badge (C-2U-c). The served payload echoes the
   difficulty rung it was generated at (null on the default path). When a rung
   is present, name it using the cached descriptor (falling back to "Rung N"
   if the label cache is somehow empty); otherwise hide the badge so the
   default path stays uncluttered. Read-only; no fetch -- the rung is already
   in the payload. Bank questions carry no difficulty, so they hide it too. */
export function updateActiveRung(payload) {
  var rung = (payload && payload.difficulty !== undefined)
    ? payload.difficulty : null;
  if (rung === null || rung === undefined) {
    el.activeRung.hidden = true;
    el.activeRung.textContent = "";
    return;
  }
  el.activeRung.textContent = state.rungLabels[rung] || ("Rung " + rung);
  el.activeRung.hidden = false;
}

export function renderQuestion(payload) {
  el.expression.textContent = payload.question_text;
  var isArithmetic = payload.qtype === "arithmetic";
  el.expression.classList.toggle("prose", !isArithmetic);

  /* C-018a: show the speaker for language prompts on a language bank. */
  updateSpeakerVisibility();

  /* C-2U-c: name the active rung under the prompt (non-default rungs only). */
  updateActiveRung(payload);

  /* Thread N.1: surface any stored hints for this question (0 -> no control). */
  renderHints(payload.hints || []);

  if (payload.qtype === "multiple_choice") {
    el.answerRow.hidden = true;
    renderChoices(payload.options || []);
    el.choices.hidden = false;
  } else {
    el.choices.hidden = true;
    clearChoices();
    el.answerRow.hidden = false;
    /* Numeric keypad for arithmetic; normal text for word answers. */
    el.answer.setAttribute("inputmode", isArithmetic ? "numeric" : "text");
    el.answer.setAttribute("placeholder", isArithmetic ? "answer" : "your answer");
  }
}

/* Build the multiple-choice buttons. Each submits its own option text. */
export function renderChoices(options) {
  el.choices.textContent = "";
  options.forEach(function (optionText) {
    var button = document.createElement("button");
    button.type = "button";
    button.className = "choice";
    button.textContent = optionText;
    button.addEventListener("click", function () {
      submitChoice(optionText);
    });
    el.choices.appendChild(button);
  });
}

/* Thread N.1: progressive hint reveal. The served payload carries a `hints`
   LIST (0, 1, or many -- imported per question). Build a "Reveal hint" control
   that discloses hints one at a time; each click reveals the next until they
   are exhausted, then the button retires. TRUTHFUL AFFORDANCE (adversarial lens
   10): with 0 hints, nothing renders and the area stays hidden -- no button that
   would promise a hint that does not exist. Drill-owned node, so this lives here
   (not in stage) and needs no cross-owner allowlist row. */
export function renderHints(hints) {
  clearHints();
  if (!hints || hints.length === 0) {
    return; /* no control when there is nothing to reveal */
  }
  var revealed = 0;
  var list = document.createElement("ol");
  list.className = "hint-list";

  var button = document.createElement("button");
  button.type = "button";
  button.className = "hint-reveal-button";

  function updateButton() {
    if (revealed >= hints.length) {
      button.hidden = true;
      return;
    }
    button.hidden = false;
    button.textContent = revealed === 0
      ? (hints.length === 1 ? "Reveal hint" : "Reveal a hint")
      : "Reveal another hint";
  }

  button.addEventListener("click", function () {
    if (revealed >= hints.length) {
      return;
    }
    var item = document.createElement("li");
    item.className = "hint-item";
    item.textContent = hints[revealed];
    list.appendChild(item);
    revealed += 1;
    updateButton();
  });

  el.hintReveal.appendChild(button);
  el.hintReveal.appendChild(list);
  el.hintReveal.hidden = false;
  updateButton();
}

/* Tear down the hint-reveal area (transition clear -- mirrors clearChoices for
   the drill-owned hint node). Empties contents and hides the area so no stale
   hint from the prior question carries across. */
export function clearHints() {
  el.hintReveal.textContent = "";
  el.hintReveal.hidden = true;
}

export function enterAnswering() {
  state.phase = "answering";
  clearAnswerHint();
  /* C-018c: start (or restart, on a retry) the think+type timer the instant
     the question becomes answerable. Restarting here means a retry after a
     failed /api/answer re-times the question and elapsed_ms reflects the
     successful attempt, excluding the failed round-trip. */
  state.answerStartMark = nowMs();
  if (state.current && state.current.qtype === "multiple_choice") {
    /* Choice buttons are the input. Hide the action button entirely while
       answering (there is nothing to submit -- a click on a choice submits);
       it returns as "Next" in the feedback phase. Focus the first choice for
       keyboard users. */
    el.action.hidden = true;
    setChoicesDisabled(false);
    var first = el.choices.querySelector(".choice");
    if (first) {
      first.focus();
    }
  } else {
    el.action.hidden = false;
    el.answer.disabled = false;
    el.action.disabled = false;
    el.action.textContent = "Submit";
    el.answer.focus();
  }
}

export function setChoicesDisabled(disabled) {
  var buttons = el.choices.querySelectorAll(".choice");
  for (var i = 0; i < buttons.length; i++) {
    buttons[i].disabled = disabled;
  }
}

export async function submitAnswer() {
  if (state.phase !== "answering" || state.current === null) {
    return;
  }
  var userInput = el.answer.value.trim();
  if (userInput === "") {
    /* C-015: tell the user why nothing happened, instead of a silent refocus.
       The hint clears as soon as they type (see onAnswerInput). */
    setAnswerHint(emptyHintText());
    el.answer.focus();
    return;
  }
  clearAnswerHint();
  el.answer.disabled = true;
  await gradeAndShow(userInput);
}

/* Multiple-choice: the clicked option's text is the answer. Disables the
   choices, then grades through the same path as a typed answer. */
export async function submitChoice(optionText) {
  if (state.phase !== "answering" || state.current === null) {
    return;
  }
  setChoicesDisabled(true);
  await gradeAndShow(optionText);
}

/* Shared grading path for both typed answers and chosen options. Posts to
   /api/answer with the served context: the real question_id for bank
   questions (null for arithmetic), the qtype, and alternatives for text
   qtypes. Arithmetic sends no tolerance (exact compare) and no alternatives. */
export async function gradeAndShow(userInput) {
  state.phase = "loading";
  el.action.disabled = true;

  /* C-018c: capture think+type elapsed at SUBMIT time (before the network
     round-trip), so elapsed_ms excludes grading latency. Guard the mark:
     if it is somehow unset, omit elapsed_ms rather than send a bogus value
     (the field is optional server-side). Clear the mark after reading so it
     cannot leak into a later submit. */
  var elapsedMs = null;
  if (state.answerStartMark !== null) {
    elapsedMs = Math.round(nowMs() - state.answerStartMark);
    if (elapsedMs < 0) {
      elapsedMs = null; /* clock anomaly: do not record a negative duration */
    }
  }
  state.answerStartMark = null;

  var q = state.current;
  var sessionId = state.activeSessionId;
  var body = {
    session_id: sessionId,
    qtype: q.qtype,
    question_text: q.question_text,
    expected: q.expected,
    user_input: userInput,
    /* Arithmetic: question_id is null -> NULL response row. Bank questions:
       the real stored id passes through as an int -> proper FK. */
    question_id: q.question_id
  };
  /* C-018c: per-answer timing. Optional server-side (reserved column); sent
     only when a valid measurement exists. Collect-only -- no UI uses it yet. */
  if (elapsedMs !== null) {
    body.elapsed_ms = elapsedMs;
  }
  /* C-D2c: echo the served difficulty rung and the expression's leaf_count
     back so the server can record them (capture lands in C-D2g, gated on the
     v3 migration). Only arithmetic payloads carry these; difficulty may be
     null on the no-rung path, leaf_count is always present for arithmetic.
     Echo difficulty even when null so the server sees an explicit value;
     leaf_count only when the payload actually carried it (bank payloads do
     not). The server ignores these until C-D2g, so sending them now is
     forward-compatible. */
  if (q.leaf_count !== undefined && q.leaf_count !== null) {
    body.difficulty = (q.difficulty === undefined) ? null : q.difficulty;
    body.leaf_count = q.leaf_count;
  }
  /* Text qtypes accept also-correct answers; forward them so the server can
     match. multiple_choice ignores alternatives (exact match); arithmetic
     has none. */
  if (q.alternatives && q.alternatives.length > 0) {
    body.alternatives = q.alternatives;
  }
  try {
    var result = await apiPost("/api/answer", body);
    /* Single source of truth: fold the snapshot into the session record and
       let the derived render redraw the stats bar (and any run log). */
    recordStats(sessionId, result.session_stats);
    renderSessionUI();
    showFeedback(result);
    if (q.qtype === "multiple_choice") {
      markChoices(result);
    }
    enterFeedback();
  } catch (error) {
    setNote(error.message, true);
    /* Let the user retry the same question rather than losing it. */
    enterAnswering();
  }
}

/* The empty-submit hint text depends on the question type: arithmetic wants
   a number, word answers want text. */
export function emptyHintText() {
  if (state.current && state.current.qtype === "arithmetic") {
    return "Enter a number to submit.";
  }
  return "Enter an answer to submit.";
}

/* After grading a multiple_choice question, mark the correct option and, on a
   miss, the wrong pick, so the feedback is visible on the choices too. */
export function markChoices(result) {
  var buttons = el.choices.querySelectorAll(".choice");
  for (var i = 0; i < buttons.length; i++) {
    var text = buttons[i].textContent;
    if (text === result.expected) {
      buttons[i].classList.add("correct");
    } else if (!result.correct && text === result.user_input) {
      buttons[i].classList.add("wrong");
    }
  }
}

export function showFeedback(result) {
  setNote("");
  el.feedback.classList.remove("correct", "miss");
  el.feedback.classList.add(result.correct ? "correct" : "miss");

  var verdict = document.createElement("div");
  verdict.className = "verdict";
  verdict.textContent = result.correct ? "Correct" : "Not quite";
  el.feedback.appendChild(clearAnd(verdict));

  if (!result.correct) {
    var detail = document.createElement("div");
    detail.className = "detail";
    var label = document.createTextNode("Answer: ");
    var value = document.createElement("b");
    value.textContent = result.expected;
    detail.appendChild(label);
    detail.appendChild(value);
    el.feedback.appendChild(detail);
  }
}

export function enterFeedback() {
  state.phase = "feedback";
  /* Show the action button as "Next" regardless of qtype -- for MC it was
     hidden during answering, so this is where the advance affordance returns
     (the missing-Next-button bug from the screenshots). */
  el.action.hidden = false;
  el.action.disabled = false;
  el.action.textContent = "Next";
  el.action.focus();
}

/* The single action button drives the loop: submit while answering, advance
   while showing feedback. (Richer keyboard control is C-015.) */
export function onAction() {
  if (state.phase === "answering") {
    submitAnswer();
  } else if (state.phase === "feedback") {
    loadQuestion();
  }
}

/* Enter submits an answer from the input while answering. The answer input
   owns Enter in this phase; the document-level handler deliberately ignores
   Enter while answering so the two never both fire. */
export function onAnswerKey(event) {
  if (event.key === "Enter" && state.phase === "answering") {
    event.preventDefault();
    submitAnswer();
  }
}

/* Typing anything clears a pending empty-answer hint. */
export function onAnswerInput() {
  if (el.answerHint.textContent) {
    clearAnswerHint();
  }
}

/* ---- Keyboard control (C-015) ----------------------------------------

   A single document-level keydown handler, gated strictly on state.phase so
   it can never collide with the input's Enter-to-submit or double-fire with a
   focused button:

     - Escape: end the active session from ANY active phase ("I'm done").
     - Enter / Space: advance to the next question, but ONLY in the feedback
       phase. In the answering phase Enter belongs to the input and Space is
       a literal keystroke (modal: keys mean different things by phase).

   Guards: ignore key events originating from the category <select> (so its
   own keyboard navigation works), and when the advance key's target is the
   action button itself, let the button's native activation drive onAction
   rather than advancing twice. */
export function onDocumentKey(event) {
  var key = event.key;
  var target = event.target;

  /* Do not hijack keys typed into form controls (the category selector, and
     the import panel's text inputs / file picker / select). Escape there
     should not end the session; Space/Enter there are normal keystrokes.
     The answer input is excluded from this guard: it has its own Enter-to-
     submit handler and the phase gate below covers the rest. */
  if (target !== el.answer && isFormControl(target)) {
    return;
  }

  if (key === "Escape") {
    /* End from any phase where a session is active. Discards an unsubmitted
       answer by design -- Escape means done. */
    if (state.activeSessionId !== null) {
      event.preventDefault();
      onEndSession();
    }
    return;
  }

  if (state.phase === "feedback" && (key === "Enter" || key === " ")) {
    /* If a button is focused (the action button or a session control), its
       native Enter/Space activation already does the right thing; let it.
       Do NOT preventDefault on a focused button -- on a button, preventDefault
       on Space would suppress the native click and swallow the action. (No
       page scroll happens while a button is focused.) This prevents a
       focused "End"/"Restart" from both activating AND advancing. */
    if (target.tagName === "BUTTON") {
      return;
    }
    event.preventDefault();
    loadQuestion();
  }
}

/* True for interactive form controls where keystrokes must not be hijacked
   by the global keyboard handler. */
export function isFormControl(node) {
  if (!node || !node.tagName) {
    return false;
  }
  var tag = node.tagName;
  return tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA"
      || tag === "BUTTON";
}

/* Put the stage in the resting state: no question, controls offer "Start
   new session". The just-ended run (if any) is already in the log via the
   endSession transition. One meaning per surface -- the stats bar resets to
   zeros here because it always reflects the ACTIVE session, and there is
   none. */
export function enterResting() {
  state.phase = "resting";
  state.current = null;
  el.expression.textContent = "--";
  el.expression.classList.remove("prose");
  el.answer.value = "";
  el.answer.disabled = true;
  el.answerRow.hidden = false;
  el.action.hidden = false;
  el.action.disabled = true;
  el.action.textContent = "Submit";
  clearChoices();
  clearAnswerHint();
  clearFeedback();
}
