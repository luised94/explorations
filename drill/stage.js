/* stage.js -- shared "stage" DOM helpers (roadmap #1 modularization, E4).
 *
 * THE RELOCATION (ADR-053): the shared teardown + note/hint helpers that both
 * drill and session lean on, pulled out so session->drill thins to the single
 * loadQuestion edge. One module (not a stage/notify split). Pure relocation
 * from the index.html inline script -- no behavior change, no logic added.
 *
 * Contents:
 *   setNote / setAnswerHint / clearAnswerHint -- the bottom note + inline hint.
 *   clearChoices                              -- clear + hide the MC choices.
 *   clearAnd / clearFeedback                  -- feedback teardown.
 *
 * Imports el (the shared DOM leaf). No other imports; touches the DOM only
 * inside functions (ADR-049 import-time rule holds). The four nodes it touches
 * are note + answerHint (owner:"stage") and choices + feedback (owner:"drill" --
 * stage's clear verbs here are allowlisted cross-owner reads at E10, per the E4
 * ownership reversal; drill remains their dominant manipulator).
 *
 * Per R1 (ADR-052) the inline script keeps its own copies until the E10
 * cutover; nothing imports this module until then.
 *
 * ASCII only.
 */

import { el } from "./el.js";

/* ---- Notes / errors --------------------------------------------------- */

export function setNote(text, isError) {
  el.note.textContent = text || "";
  el.note.classList.toggle("error", !!isError);
}

/* The inline hint under the input (C-015), distinct from the bottom note. */
export function setAnswerHint(text) {
  el.answerHint.textContent = text || "";
}
export function clearAnswerHint() {
  el.answerHint.textContent = "";
}

/* ---- Choices teardown ------------------------------------------------- */

export function clearChoices() {
  el.choices.textContent = "";
  el.choices.hidden = true;
}

/* ---- Feedback teardown ------------------------------------------------ */

/* Replace feedback contents with the first node in one step (keeps the
   aria-live region from announcing stale text). */
export function clearAnd(firstNode) {
  el.feedback.textContent = "";
  return firstNode;
}

export function clearFeedback() {
  el.feedback.textContent = "";
  el.feedback.classList.remove("correct", "miss");
}
