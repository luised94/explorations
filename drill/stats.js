/* stats.js -- stats rendering: the live stats bar, streak pips, run log, and
 * the cross-session stats panel (roadmap #1 modularization, E6).
 *
 * Verbatim relocation from the index.html inline script -- no behavior change.
 * The ONE style change (S9, sanctioned in the E-series "cut / style" pairing):
 * the terse local `cat` in renderRunLog is renamed to `catSpan` (it is the
 * category-label <span>). The CSS class strings "run-cat"/"stats-cat" are
 * UNCHANGED -- only the JS local identifier changed.
 *
 * Contents:
 *   renderStats / renderStreakPips  -- the live stats bar + signature pip row.
 *   renderRunLog / figure           -- the ended-sessions run log + its figure.
 *   onStatsToggle / renderStatsPanel / statsFigure / statsWindowText /
 *   categoryNameById                -- the "+ Stats across sessions" panel.
 *
 * DEPENDENCIES (as-built): imports state (STREAK_PIPS_MAX, state.sessions,
 * state.categories), el (the stats-owned nodes), and api (apiGet, in
 * onStatsToggle's /api/stats fetch).
 *
 * ADR-049 import-time rule: no DOM at import time; el.<node> is read only
 * inside functions. Import-safe under the option-(b) harness.
 *
 * Per R1 (ADR-052) the inline script keeps its own copy until the E10 cutover;
 * nothing imports this module until then.
 *
 * ASCII only.
 */

import { STREAK_PIPS_MAX, state } from "./state.js";
import { el } from "./el.js";
import { apiGet } from "./api.js";

/* ---- Live stats bar --------------------------------------------------- */

/* Render the stats bar from a session_stats object as returned by
   /api/answer: {total, correct, accuracy (0.0-1.0 float), streak}. */
export function renderStats(stats) {
  el.statTotal.textContent = String(stats.total);
  el.statAccuracy.textContent = stats.total > 0
    ? Math.round(stats.accuracy * 100) + "%"
    : "--";
  el.statStreak.textContent = String(stats.streak);
  renderStreakPips(stats.streak);
}

export function renderStreakPips(streak) {
  el.streakPips.textContent = "";
  var shown = Math.min(streak, STREAK_PIPS_MAX);
  for (var i = 0; i < STREAK_PIPS_MAX; i++) {
    var pip = document.createElement("span");
    pip.className = "pip" + (i < shown ? " on" : "");
    el.streakPips.appendChild(pip);
  }
  if (streak > STREAK_PIPS_MAX) {
    var more = document.createElement("span");
    more.className = "more";
    more.textContent = "+" + (streak - STREAK_PIPS_MAX);
    el.streakPips.appendChild(more);
  }
}

/* ---- Run log (ended sessions) ----------------------------------------- */

export function renderRunLog() {
  var runs = state.sessions.filter(function (s) {
    return s.status === "ended" && s.stats.total > 0;
  });
  runs.reverse(); /* array is append order (oldest-first); show newest-first */

  el.runLogList.textContent = "";
  if (runs.length === 0) {
    el.runLog.hidden = true;
    return;
  }
  el.runLog.hidden = false;

  runs.forEach(function (run) {
    var li = document.createElement("li");
    li.className = "run-row";

    var catSpan = document.createElement("span");
    catSpan.className = "run-cat";
    /* Runs are category (+ bank, for bank categories). Name both so the log
       distinguishes a vocabulary/spanish run from vocabulary/french. */
    var runLabel = run.categoryName;
    if (run.bankName) {
      runLabel += " / " + run.bankName;
    }
    catSpan.textContent = runLabel + " #" + run.id;
    li.appendChild(catSpan);

    var figs = document.createElement("span");
    figs.className = "run-figs";
    figs.appendChild(figure(run.stats.total, "answered"));
    figs.appendChild(figure(Math.round(run.stats.accuracy * 100) + "%", "accuracy"));
    figs.appendChild(figure(run.stats.streak, "final streak"));
    li.appendChild(figs);

    el.runLogList.appendChild(li);
  });
}

/* A small run-row figure: an emphasized value followed by a muted label
   (e.g. "<b>12</b> answered"). The value is the data; the label names it. */
export function figure(value, label) {
  var span = document.createElement("span");
  var head = document.createElement("b");
  head.textContent = String(value);
  span.appendChild(head);
  span.appendChild(document.createTextNode(" " + label));
  return span;
}

/* ---- Cross-session stats panel ---------------------------------------- */

export async function onStatsToggle() {
  var open = el.statsToggle.getAttribute("aria-expanded") === "true";
  if (open) {
    el.statsPanel.hidden = true;
    el.statsPanel.textContent = "";
    el.statsToggle.setAttribute("aria-expanded", "false");
    el.statsToggle.textContent = "+ Stats across sessions";
    return;
  }
  el.statsToggle.setAttribute("aria-expanded", "true");
  el.statsToggle.textContent = "- Stats across sessions";
  el.statsPanel.hidden = false;
  el.statsPanel.textContent = "";
  var loading = document.createElement("p");
  loading.className = "stats-note";
  loading.textContent = "Loading...";
  el.statsPanel.appendChild(loading);
  try {
    var summary = await apiGet("/api/stats");
    /* The panel may have been closed again while the fetch was in flight;
       only render if it is still open. */
    if (el.statsToggle.getAttribute("aria-expanded") === "true") {
      renderStatsPanel(summary);
    }
  } catch (error) {
    el.statsPanel.textContent = "";
    var failed = document.createElement("p");
    failed.className = "stats-note";
    failed.textContent = "Could not load stats: " + error.message;
    el.statsPanel.appendChild(failed);
  }
}

/* Render the /api/stats summary into the panel. Pure DOM construction from the
   response {total, correct, accuracy, categories:[...], window} -- no network.
   Empty/time-zero (total 0) gets a friendly note rather than a wall of zeros.
   The categories list arrives pre-sorted by the endpoint (most-practiced
   first), so it renders in order as-is. The median think+type time is shown in
   the overall row when present (Thread N.2); it is suppressed when null (no
   timed responses). */
export function renderStatsPanel(summary) {
  el.statsPanel.textContent = "";

  if (!summary || !summary.total) {
    var empty = document.createElement("p");
    empty.className = "stats-note";
    empty.textContent =
      "No answers recorded yet. Stats appear here once you have drilled.";
    el.statsPanel.appendChild(empty);
    return;
  }

  /* Overall total + accuracy. */
  var overall = document.createElement("div");
  overall.className = "stats-overall";
  overall.appendChild(statsFigure(String(summary.total), "answered"));
  overall.appendChild(
    statsFigure(Math.round((summary.accuracy || 0) * 100) + "%", "accuracy")
  );
  overall.appendChild(statsFigure(String(summary.correct), "correct"));
  /* Median think+type time (Thread N.2). Shown only when the backend returned a
     figure (non-null): a null means no timed responses, so suppress it the way
     single-category/single-bucket breakdowns are suppressed (C-D2i-3), rather
     than printing a misleading "0 ms". Rendered in seconds with one decimal for
     readability (elapsed_ms is stored in milliseconds). */
  if (summary.median_elapsed_ms !== null && summary.median_elapsed_ms !== undefined) {
    overall.appendChild(
      statsFigure(formatElapsed(summary.median_elapsed_ms), "median time")
    );
  }
  el.statsPanel.appendChild(overall);

  /* Window echo (only when a filter is active), so the user knows the scope. */
  var windowText = statsWindowText(summary.window);
  if (windowText) {
    var win = document.createElement("div");
    win.className = "stats-window";
    win.textContent = windowText;
    el.statsPanel.appendChild(win);
  }

  /* Per-category breakdown (skip when there is only one category -- the
     overall line already covers it). */
  var categories = summary.categories || [];
  if (categories.length > 1) {
    var breakdown = document.createElement("div");
    breakdown.className = "stats-breakdown";
    var title = document.createElement("div");
    title.className = "stats-breakdown-title";
    title.textContent = "By category";
    breakdown.appendChild(title);

    categories.forEach(function (entry) {
      var row = document.createElement("div");
      row.className = "stats-row";
      var name = document.createElement("span");
      name.className = "stats-cat";
      name.textContent = entry.category_name || "(unknown)";
      var figs = document.createElement("span");
      figs.className = "stats-figs";
      figs.textContent = entry.total + " answered, "
        + Math.round((entry.accuracy || 0) * 100) + "%";
      row.appendChild(name);
      row.appendChild(figs);
      breakdown.appendChild(row);
    });
    el.statsPanel.appendChild(breakdown);
  }

  /* Per-difficulty breakdown (C-D2i-3): grouped by leaf_count on the server
     (S11 -- leaf_count is comparable across operator mixes, the rung is not).
     Mirrors the category rule: skip when there is 0 or 1 bucket (a single
     bucket adds no comparison over the overall line). Only arithmetic responses
     carrying a leaf_count appear here, so this section is naturally absent for
     bank-only practice or pre-#2 data. The server supplies the label ("N
     leaves"); the client just renders it. */
  var difficulty = summary.difficulty_breakdown || [];
  if (difficulty.length > 1) {
    var diffBreakdown = document.createElement("div");
    diffBreakdown.className = "stats-breakdown";
    var diffTitle = document.createElement("div");
    diffTitle.className = "stats-breakdown-title";
    diffTitle.textContent = "By difficulty";
    diffBreakdown.appendChild(diffTitle);

    difficulty.forEach(function (entry) {
      var row = document.createElement("div");
      row.className = "stats-row";
      var name = document.createElement("span");
      name.className = "stats-cat";
      name.textContent = entry.label || "(unknown)";
      var figs = document.createElement("span");
      figs.className = "stats-figs";
      figs.textContent = entry.total + " answered, "
        + Math.round((entry.accuracy || 0) * 100) + "%";
      row.appendChild(name);
      row.appendChild(figs);
      diffBreakdown.appendChild(row);
    });
    el.statsPanel.appendChild(diffBreakdown);
  }
}

/* A stacked figure (big value over a muted label) for the overall row. */
export function statsFigure(value, label) {
  var fig = document.createElement("div");
  fig.className = "stats-figure";
  var head = document.createElement("b");
  head.textContent = value;
  var cap = document.createElement("span");
  cap.textContent = label;
  fig.appendChild(head);
  fig.appendChild(cap);
  return fig;
}

/* Format a millisecond duration for display (Thread N.2). Sub-second times read
   as "NNN ms"; one second and up read as seconds with one decimal ("2.4 s"),
   which is the scale a think+type answer actually lands at. Pure. */
export function formatElapsed(ms) {
  if (ms < 1000) {
    return String(Math.round(ms)) + " ms";
  }
  return (Math.round(ms / 100) / 10).toFixed(1) + " s";
}

/* Build a short human description of the active window/filter, or "" when the
   view is unfiltered (all categories, all time -- the common case, no note
   needed). Reads the window echo the endpoint returns. */
export function statsWindowText(window) {
  if (!window) {
    return "";
  }
  var parts = [];
  if (window.days) {
    parts.push("last " + window.days + (window.days === 1 ? " day" : " days"));
  }
  if (window.category_id !== null && window.category_id !== undefined) {
    var name = categoryNameById(window.category_id);
    parts.push(name ? ("category: " + name) : ("category " + window.category_id));
  }
  return parts.length ? ("Showing " + parts.join(", ")) : "";
}

/* Resolve a category id to its name from state.categories, or "" if unknown. */
export function categoryNameById(categoryId) {
  for (var i = 0; i < state.categories.length; i++) {
    if (state.categories[i].id === categoryId) {
      return state.categories[i].name;
    }
  }
  return "";
}
