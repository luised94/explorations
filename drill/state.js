/* state.js -- frontend shared-data leaf (roadmap #1 modularization, E1).
 *
 * The clean data leaf (spike S3): STREAK_PIPS_MAX, RECENT_MAX, the mutable
 * `state` singleton, and the ZERO_STATS constant. No DOM, no fetch, no imports.
 * Every other frontend module reads/writes `state`; nothing here reads anything
 * else, so this extracts first (dependencies-first, J3).
 *
 * Verbatim relocation of the inline-script block (index.html) -- no behavior
 * change. Per the R1 duplicate-then-delete strategy (ADR-052), the inline
 * script keeps its own copy until the E10 cutover; this module is proven in
 * isolation by state.test.js (option (b): Node imports the real module and
 * drives it -- ADR-049). No module imports this one until E10.
 *
 * ADR-049 import-time rule: this module touches no DOM at import time (it
 * touches no DOM at all), so it is import-safe under the option-(b) harness.
 *
 * ASCII only. Single-user assumption holds.
 */

export var STREAK_PIPS_MAX = 10; /* visual cap for the signature pip row */
export var RECENT_MAX = 10;      /* C-016: per-session recent-id window for recent= */

export var state = {
  sessions: [],            /* run log: all sessions created this page visit */
  activeSessionId: null,   /* id of the active record, or null when resting */
  arithmeticCategoryId: null,
  arithmeticCategoryName: "arithmetic",
  categories: [],          /* category records from /api/categories, with a
                              `banks` array attached by fetchAndAttachBanks
                              (C-016) -- /api/categories itself carries none */
  selection: null,         /* C-016: {categoryId, categoryName, bankId,
                              bankName} -- the current drill target */
  recentIds: [],           /* C-016: last-RECENT_MAX served bank question ids
                              for the active session (recent= param) */
  difficulty: null,        /* C-D2c: selected arithmetic difficulty rung, or
                              null for the default (no-rung) path. The C-2U-b
                              selector sets this; null is the default path. */
  rungLabels: {},          /* C-2U-c: rung number -> composed descriptor,
                              filled by populateDifficulty so the active-rung
                              badge can name the served rung without a refetch. */
  current: null,           /* the question payload now on screen */
  answerStartMark: null,   /* C-018c: performance.now() ms when the current
                              question became answerable; null when not in an
                              answerable phase. Diffed at submit -> elapsed_ms.
                              Resets each enterAnswering (so a retry re-times). */
  phase: "idle"            /* idle | resting | loading | answering | feedback */
};

export var ZERO_STATS = { total: 0, correct: 0, accuracy: 0.0, streak: 0 };
