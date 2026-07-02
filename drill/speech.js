/* speech.js -- text-to-speech quarantine (roadmap #1 modularization, E5).
 *
 * QUARANTINE (C-018a). window.speechSynthesis is the one weird external
 * dependency in the frontend: a process-wide singleton with an internal mutable
 * utterance queue and async voice loading -- the opposite of this codebase's
 * "single source of truth, derived render, no shared mutable state" model. We
 * cannot make it pure, so we fence it off here: speak() / cancelSpeech() are the
 * ONLY code that touches window.speechSynthesis; everything else calls them and
 * never reaches through to the global. Verbatim relocation from the index.html
 * inline script -- no behavior change, no logic added.
 *
 * Design choices (see DECISIONS C-018a):
 *   - Feature-detected ONCE at module load (speechAvailable). If absent, the
 *     speaker button is never shown and speak() is a no-op.
 *   - We DO NOT enumerate voices via getVoices() (the Chrome voices-load race);
 *     we set utterance.lang and let the engine choose a matching voice.
 *   - cancelSpeech() is called on every question transition, session end, and
 *     unload, so a prior word never talks over a new question.
 *   - The "speaking" visual state is cleared on the utterance end/error events;
 *     cancelSpeech() also clears it for the immediate-cancel path.
 *
 * DEPENDENCIES (as-built): imports state (activeBankLanguage/canSpeakCurrent
 * read state.selection/categories/current) and el (the speaker button). It does
 * NOT import stage -- Section R's "imports state, stage" is superseded here; the
 * speech block calls zero stage functions (see E5 commit note).
 *
 * ADR-049 import-time rule: speechAvailable feature-detects window at import,
 * which is a global-capability read, NOT a DOM-node lookup (no getElementById /
 * el.<node> at import time). el.speaker is only read inside functions. Under the
 * option-(b) harness window is published before import, so this is safe.
 *
 * Per R1 (ADR-052) the inline script keeps its own copy until the E10 cutover;
 * nothing imports this module until then.
 *
 * ASCII only.
 */

import { state } from "./state.js";
import { el } from "./el.js";

/* ---- Feature detection (once, at module load) ------------------------- */

export var speechAvailable = (typeof window !== "undefined")
  && ("speechSynthesis" in window)
  && (typeof window.SpeechSynthesisUtterance !== "undefined");

/* ---- The speechSynthesis fence (the only touchers of the global) ------ */

/* Speak `text` in `lang` (an ISO 639-1 code or null). No-op if speech is
   unavailable or the text is empty. Cancels any in-flight utterance first so
   clicks never stack. onStateChange(isSpeaking) is an optional callback for
   the caller to reflect the speaking state in the UI; it is invoked with true
   at start and false at end/error. */
export function speak(text, lang, onStateChange) {
  if (!speechAvailable || !text) {
    return;
  }
  /* Clear any queued/active utterance so a second click does not stack. */
  window.speechSynthesis.cancel();

  var utterance = new window.SpeechSynthesisUtterance(text);
  if (lang) {
    utterance.lang = lang; /* engine picks a matching voice; no getVoices() */
  }
  if (typeof onStateChange === "function") {
    utterance.onend = function () { onStateChange(false); };
    utterance.onerror = function () { onStateChange(false); };
    onStateChange(true);
  }
  window.speechSynthesis.speak(utterance);
}

/* Stop any in-flight or queued speech immediately. Safe to call when nothing
   is speaking (a no-op) and when speech is unavailable. onStateChange(false),
   if provided, lets the caller clear any speaking UI on the cancel path
   (cancel() does not always fire onend). */
export function cancelSpeech(onStateChange) {
  if (!speechAvailable) {
    return;
  }
  window.speechSynthesis.cancel();
  if (typeof onStateChange === "function") {
    onStateChange(false);
  }
}

/* ---- TTS targeting (pure-ish helpers, read state) --------------------- */

/* The language is a property of the chosen BANK (the drill target), not of
   the individual question -- the question payload carries no language field.
   So we resolve it from state.selection.bankId against the banks already
   fetched and attached to state.categories by fetchAndAttachBanks() (C-016).
   No backend call, no payload change. Returns the ISO 639-1 string or null
   (banks may have a null language: trivia/geography/logic/code, or any vocab
   imported without a language= field). */
export function activeBankLanguage() {
  var sel = state.selection;
  if (!sel || sel.bankId === null || sel.bankId === undefined) {
    return null; /* arithmetic or no selection: no bank, no language */
  }
  for (var c = 0; c < state.categories.length; c++) {
    var banks = state.categories[c].banks || [];
    for (var b = 0; b < banks.length; b++) {
      if (banks[b].id === sel.bankId) {
        return banks[b].language || null;
      }
    }
  }
  return null;
}

/* Decide whether the current question should expose the speaker button. True
   only when: speech is available in this browser; a bank language resolves;
   and the prompt is itself the foreign-language content -- qtype translate or
   identify. Explicitly NOT multiple_choice (its prompt is usually an L1
   question), NOT arithmetic, NOT plain free_response (English trivia prompts).
   Data-derived and explicit, in the spirit of isDrillable(). */
export function canSpeakCurrent() {
  if (!speechAvailable) {
    return false;
  }
  var q = state.current;
  if (!q) {
    return false;
  }
  if (q.qtype !== "translate" && q.qtype !== "identify") {
    return false;
  }
  return activeBankLanguage() !== null;
}

/* ---- Speaker button UI (reads el.speaker) ----------------------------- */

/* Reflect the speaking state on the speaker button (class toggle only). */
export function setSpeakerSpeaking(isSpeaking) {
  if (el.speaker) {
    el.speaker.classList.toggle("speaking", !!isSpeaking);
  }
}

/* Speak the current prompt. Wired to the speaker button's click. Blurs the
   button afterward so focus returns off the control: this preserves the
   C-015 Space-to-advance contract (a focused button would activate on Space
   instead of advancing -- the documented double-fire trap). */
export function onSpeakerClick() {
  if (!state.current) {
    return;
  }
  speak(state.current.question_text, activeBankLanguage(), setSpeakerSpeaking);
  el.speaker.blur();
}

/* Show or hide the speaker for the current question, driven by canSpeakCurrent
   (called from renderQuestion). Hiding also stops any in-flight speech. */
export function updateSpeakerVisibility() {
  if (!el.speaker) {
    return;
  }
  if (canSpeakCurrent()) {
    el.speaker.hidden = false;
  } else {
    el.speaker.hidden = true;
    cancelSpeech(setSpeakerSpeaking);
  }
}
