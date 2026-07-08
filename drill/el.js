/* el.js -- shared DOM-accessor leaf (roadmap #1 modularization, E4).
 *
 * The DOM node registry (EL_REGISTRY: logicalName -> {id, owner}) and the lazy
 * memoizing accessor `el`. Verbatim relocation from the index.html inline
 * script (C0.3a/C0.3b) -- no behavior change.
 *
 * WHY THIS IS ITS OWN MODULE (folded into E4): stage.js is the first extracted
 * module that references el; every later DOM module (speech/stats/session/
 * drill/boot) does too (handoff (d): "every frontend module depends on this").
 * el had no home module in the plan text, so it is carved out here as the
 * shared DOM leaf -- the DOM counterpart of the state/api/timing data+logic
 * leaves. It imports nothing.
 *
 * ADR-049 import-time rule: no DOM access at import time. Building the accessor
 * only defines getters; getElementById fires lazily on first read of el.<name>,
 * inside the getter -- never during import. Import-safe under the option-(b)
 * harness (which publishes document before importing).
 *
 * OWNER TAGS are inert metadata today: nothing reads .owner and the E10
 * ownership guard does not exist until the cutover. They are the data that
 * guard will consume (ADR-051). choices/feedback stay owner:"drill" (the E4
 * reversal -- drill remains their dominant manipulator; stage's teardown verbs
 * are allowlisted at E10, not owners).
 *
 * Per R1 (ADR-052) the inline script keeps its own registry+accessor copy until
 * the E10 cutover; nothing imports this module until then.
 *
 * ASCII only.
 */

export var EL_REGISTRY = {
  category: { id: "category", owner: "boot" },
  expression: { id: "expression", owner: "drill" },
  answer: { id: "answer", owner: "drill" },
  action: { id: "action", owner: "drill" },
  feedback: { id: "feedback", owner: "drill" },
  note: { id: "note", owner: "stage" },
  statTotal: { id: "stat-total", owner: "stats" },
  statAccuracy: { id: "stat-accuracy", owner: "stats" },
  statStreak: { id: "stat-streak", owner: "stats" },
  streakPips: { id: "streak-pips", owner: "stats" },
  sessionControls: { id: "session-controls", owner: "session" },
  sessionSummary: { id: "session-summary", owner: "session" },
  runLog: { id: "run-log", owner: "stats" },
  runLogList: { id: "run-log-list", owner: "stats" },
  answerHint: { id: "answer-hint", owner: "stage" },
  importToggle: { id: "import-toggle", owner: "boot" },
  importPanel: { id: "import-panel", owner: "boot" },
  statsToggle: { id: "stats-toggle", owner: "stats" },
  statsPanel: { id: "stats-panel", owner: "stats" },
  bankSelector: { id: "bank-selector", owner: "boot" },
  bank: { id: "bank", owner: "boot" },
  difficulty: { id: "difficulty", owner: "boot" },
  difficultyNote: { id: "difficulty-note", owner: "boot" },
  activeRung: { id: "active-rung", owner: "drill" },
  answerRow: { id: "answer-row", owner: "drill" },
  choices: { id: "choices", owner: "drill" },
  hintReveal: { id: "hint-reveal", owner: "drill" },
  speaker: { id: "speaker", owner: "speech" }
};

/* Build the accessor: one memoizing getter per logical name. First read of
   el.<name> resolves getElementById(id) and caches it; later reads return the
   cache. Same read syntax (el.answer), same node, later timing. */
export var el = (function buildEl(registry) {
  var target = {};
  var cache = {};
  Object.keys(registry).forEach(function (name) {
    Object.defineProperty(target, name, {
      enumerable: true,
      get: function () {
        if (!(name in cache)) {
          cache[name] = document.getElementById(registry[name].id);
        }
        return cache[name];
      }
    });
  });
  return target;
})(EL_REGISTRY);
