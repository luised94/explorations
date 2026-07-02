/* timing.js -- frontend monotonic-clock leaf (roadmap #1 modularization, E3).
 *
 * nowMs: a monotonic millisecond clock (C-018c) for measuring elapsed
 * think+type time. Prefers performance.now() (monotonic -- immune to wall-clock
 * changes, the right tool for durations); falls back to Date.now() where
 * performance is unavailable. Returns a float (ms). Verbatim relocation from
 * the index.html inline script -- no behavior change.
 *
 * Leaf beside state.js / api.js: no imports, no DOM. It reads the global
 * `performance` behind a typeof guard, so import is side-effect-free and safe
 * under the option-(b) harness (ADR-049); the clock is only read when nowMs()
 * is called.
 *
 * Per R1 (ADR-052) the inline script keeps its own copy until the E10 cutover;
 * nothing imports this module until then.
 *
 * ASCII only.
 */

export function nowMs() {
  if (typeof performance !== "undefined"
      && typeof performance.now === "function") {
    return performance.now();
  }
  return Date.now();
}
