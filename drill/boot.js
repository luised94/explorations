/* boot.js -- application entry point: static wiring, the category/bank/
 * difficulty selectors, the import panel, and boot() (roadmap #1
 * modularization, E9 -- the last frontend module).
 *
 * Verbatim relocation from the index.html inline script -- no behavior change,
 * no logic added. No S9 renames land here (sel/cat locals live in
 * session/stats, already handled).
 *
 * boot.js is the TOP of the frontend DAG: it imports from state, el, api,
 * stage, stats, speech, session, and drill, and NOTHING imports boot (it is the
 * entry module, the frontend analog of drill.py-as-MAIN on the backend). At the
 * E10 cutover index.html loads it via <script type=module src=boot.js>.
 *
 * THE ONE MODULE-SCOPE STATEMENT (S7): the boot-guard at the bottom is the sole
 * executable statement at module scope -- it only CALLS the hoisted boot(), it
 * reads no other module's export at eval time, so it does not perturb the
 * drill<->session cycle. Everything else is a function declaration.
 *
 * DEPENDENCIES (as-built): imports state, el, api (apiGet/readJson), stage
 * (setNote), stats (onStatsToggle), speech (onSpeakerClick), session
 * (renderSessionUI/endSessionOnUnload), drill (onAction/onAnswerKey/
 * onAnswerInput/onDocumentKey/loadQuestion).
 *
 * ADR-049 import-time rule: no DOM at import time. Handlers attach and the
 * first getElementById fires only when boot() runs (from the boot-guard), never
 * during module import.
 *
 * onImportSubmit keeps its raw multipart fetch (E2 flag: outside the api seam),
 * and parses the reply via readJson imported from api.
 *
 * Per R1 (ADR-052) the inline script stays authoritative until the E10 cutover;
 * nothing imports this module until then.
 *
 * ASCII only.
 */

import { state } from "./state.js";
import { el } from "./el.js";
import { apiGet, readJson } from "./api.js";
import { setNote } from "./stage.js";
import { onStatsToggle } from "./stats.js";
import { onSpeakerClick } from "./speech.js";
import { renderSessionUI, endSessionOnUnload, endSession } from "./session.js";
import {
  onAction, onAnswerKey, onAnswerInput, onDocumentKey, loadQuestion
} from "./drill.js";

/* Module-load trace: if you see this in the console the whole ES module graph
   fetched and evaluated. If the page is inert and this line is ABSENT, the
   browser could not load a module (commonly a 404 on a .js file -- check the
   Network tab; the backend must serve each module, see http_layer serve_module)
   or a MIME/type=module error. This is a console.* call, not DOM access, so it
   is a module-scope statement the ADR-051 guard permits (only DOM-at-import is
   fenced). */
console.info("drill: modules loaded (boot.js evaluated)");

/* ---- Drillability gate ------------------------------------------------
   A category is drillable if it is arithmetic OR it has at least one bank.
   The predicate has been unchanged since C-013; C-016 finally feeds it real
   data by attaching `banks` to each category (fetchAndAttachBanks below),
   since /api/categories itself carries no banks. */
export function isDrillable(category) {
  return category.name === "arithmetic" ||
         (Array.isArray(category.banks) && category.banks.length > 0);
}

/* C-016: fetch all banks once and attach a `banks` array to each category in
   state.categories, grouped by category_id. This is what makes the gate work
   and what feeds the bank selector. /api/categories does not include banks,
   so this separate fetch is required. Safe to call repeatedly (after import,
   refreshCategories calls it again). On failure, categories keep whatever
   banks they had (or none) -- non-fatal. */
export async function fetchAndAttachBanks() {
  var data = await apiGet("/api/banks");
  var byCategory = {};
  (data.banks || []).forEach(function (bank) {
    var key = String(bank.category_id);
    if (!byCategory[key]) {
      byCategory[key] = [];
    }
    byCategory[key].push(bank);
  });
  state.categories.forEach(function (category) {
    category.banks = byCategory[String(category.id)] || [];
  });
}

export function populateCategories(categories) {
  state.categories = categories;
  el.category.textContent = "";
  categories.forEach(function (category) {
    var drillable = isDrillable(category);
    var option = document.createElement("option");
    option.value = String(category.id);
    option.dataset.name = category.name;
    option.textContent = drillable
      ? category.name
      : category.name + " (no banks yet)";
    option.disabled = !drillable;
    el.category.appendChild(option);
    if (category.name === "arithmetic") {
      state.arithmeticCategoryId = category.id;
    }
  });
}

/* Find a category record by id (string or number). */
export function findCategory(id) {
  for (var i = 0; i < state.categories.length; i++) {
    if (String(state.categories[i].id) === String(id)) {
      return state.categories[i];
    }
  }
  return null;
}

/* Compose the human descriptor for a rung from its structural facts
   (C-2U-b). The server returns facts, not prose (GET /api/difficulty-rungs);
   the client owns the wording so presentation stays in the presentation
   layer while the server stays the source of truth for what rungs exist.
   Reads operator_depth, recurse_probability, and max_result_value to give a
   sense of what the rung drills. Example: "Rung 2 - nested, to any size". */
export function difficultyLabel(record) {
  var shape = (record.recurse_probability > 0) ? "nested" : "flat";
  var ceiling = (record.max_result_value === null
                 || record.max_result_value === undefined)
    ? "any size"
    : "to " + record.max_result_value;
  return "Rung " + record.rung + " - " + shape + ", " + ceiling;
}

/* Populate the difficulty selector from GET /api/difficulty-rungs (C-2U-b).
   The first option is "Default" (value "" = null), which keeps the
   unparameterized pre-#2 path. Each rung option carries its numeric rung as
   the value and a composed descriptor as the text. A fetch failure is
   non-fatal: the selector keeps just "Default", so difficulty silently
   stays at the default path rather than breaking the page. */
export async function populateDifficulty() {
  el.difficulty.textContent = "";
  var defaultOption = document.createElement("option");
  defaultOption.value = "";
  defaultOption.textContent = "Default";
  el.difficulty.appendChild(defaultOption);
  try {
    var data = await apiGet("/api/difficulty-rungs");
    (data.rungs || []).forEach(function (record) {
      var label = difficultyLabel(record);
      state.rungLabels[record.rung] = label; /* C-2U-c: for the active badge */
      var option = document.createElement("option");
      option.value = String(record.rung);
      option.textContent = label;
      el.difficulty.appendChild(option);
    });
  } catch (error) {
    /* Leave just "Default"; the default drill path is unaffected. */
  }
}

/* Gate the difficulty control to arithmetic (C-2U-b). Difficulty is
   meaningless for bank questions (they carry no rung), so for non-arithmetic
   categories the control is DISABLED and a note explains why -- it stays in
   the layout (no reflow) and visible (the affordance is comprehensible)
   rather than vanishing. Switching away from arithmetic also resets the
   selection back to Default and clears state.difficulty, so a stale rung
   never rides into a category that ignores it. */
export function applyDifficultyGating(categoryName) {
  var isArithmetic = (categoryName === "arithmetic");
  el.difficulty.disabled = !isArithmetic;
  el.difficultyNote.hidden = isArithmetic;
  if (!isArithmetic) {
    el.difficulty.value = "";
    state.difficulty = null;
  }
}

/* Changing the difficulty rung (C-2U-b): set state.difficulty (null for
   "Default") and re-fetch the next question immediately so the choice takes
   effect now. questionQuery() already serializes state.difficulty, so the
   only action needed is triggering a fresh question. The current on-screen
   question is discarded; this is stats-safe because loadQuestion() writes
   nothing -- a response row is only ever recorded on /api/answer when the
   user actually answers (submitAnswer/submitChoice), never on a re-fetch. */
export async function onDifficultyChange() {
  var raw = el.difficulty.value;
  state.difficulty = (raw === "") ? null : parseInt(raw, 10);
  await loadQuestion();
}

/* Selecting a category: arithmetic hides the bank selector and drills
   immediately (its run auto-starts, as before). A bank category reveals the
   bank selector populated with that category's banks and waits for a bank
   choice -- selecting the category alone does not start a run. */
export function onCategoryChange() {
  var category = findCategory(el.category.value);
  if (!category) {
    return;
  }
  applyDifficultyGating(category.name);
  if (category.name === "arithmetic") {
    el.bankSelector.hidden = true;
    switchSelection({
      categoryId: category.id,
      categoryName: category.name,
      bankId: null,
      bankName: null
    });
    return;
  }
  /* Bank category: show its banks and let the user pick one. */
  showBankSelector(category);
}

/* Populate and reveal the bank selector for a category. Auto-selects the
   first bank and starts drilling it (so choosing a category gets you into a
   run without a second click), matching how arithmetic starts on selection. */
export function showBankSelector(category) {
  var banks = category.banks || [];
  el.bank.textContent = "";
  banks.forEach(function (bank) {
    var option = document.createElement("option");
    option.value = String(bank.id);
    option.dataset.name = bank.name;
    option.textContent = bank.name;
    el.bank.appendChild(option);
  });
  el.bankSelector.hidden = banks.length === 0;
  if (banks.length === 0) {
    return;
  }
  /* Drill the first bank by default. */
  el.bank.selectedIndex = 0;
  switchSelection({
    categoryId: category.id,
    categoryName: category.name,
    bankId: banks[0].id,
    bankName: banks[0].name
  });
}

/* Selecting a bank from the bank selector: switch the run to that bank. */
export function onBankChange() {
  var category = findCategory(el.category.value);
  if (!category) {
    return;
  }
  var option = el.bank.options[el.bank.selectedIndex];
  if (!option) {
    return;
  }
  switchSelection({
    categoryId: category.id,
    categoryName: category.name,
    bankId: parseInt(option.value, 10),
    bankName: option.dataset.name
  });
}

/* Set the drill target and (re)start a run for it. If a run is active, end
   it first (preserved in the run log, per C-014) -- switching category or
   bank is a deliberate "new run" action, like Restart. Then drill. */
export async function switchSelection(selection) {
  setNote("");
  state.selection = selection;
  if (state.activeSessionId !== null) {
    await endSession(state.activeSessionId);
    renderSessionUI();
  }
  await loadQuestion(); /* auto-starts a fresh session for the new selection */
}

/* Toggle the disclosure. Builds the panel lazily on first open. */
export function onImportToggle() {
  var open = el.importToggle.getAttribute("aria-expanded") === "true";
  if (open) {
    el.importPanel.hidden = true;
    el.importToggle.setAttribute("aria-expanded", "false");
    el.importToggle.textContent = "+ Import a bank";
  } else {
    buildImportPanel();
    el.importPanel.hidden = false;
    el.importToggle.setAttribute("aria-expanded", "true");
    el.importToggle.textContent = "- Import a bank";
  }
}

/* (Re)build the import form. Pure DOM construction from state.categories;
   no network. A separate category picker from the top drill selector --
   different intent ("where does this bank go"), and every category is a
   valid import target, including ones with no banks yet. */
export function buildImportPanel() {
  el.importPanel.textContent = "";

  /* Import-target category picker. */
  var catField = importField("Import into category");
  var catSelect = document.createElement("select");
  catSelect.id = "import-category";
  state.categories.forEach(function (category) {
    var option = document.createElement("option");
    option.value = String(category.id);
    option.textContent = category.name;
    catSelect.appendChild(option);
  });
  catField.appendChild(catSelect);
  el.importPanel.appendChild(catField);

  /* File chooser (JSONL or CSV). */
  var fileField = importField("File (.jsonl or .csv)");
  var fileInput = document.createElement("input");
  fileInput.type = "file";
  fileInput.id = "import-file";
  fileInput.accept = ".jsonl,.csv,.json,.txt";
  fileField.appendChild(fileInput);
  el.importPanel.appendChild(fileField);

  /* Optional bank name. */
  var nameField = importField("Bank name (optional)");
  var nameInput = document.createElement("input");
  nameInput.type = "text";
  nameInput.id = "import-name";
  nameInput.placeholder = "defaults to the file name";
  nameInput.autocomplete = "off";
  nameField.appendChild(nameInput);
  el.importPanel.appendChild(nameField);

  /* Optional language code. */
  var langField = importField("Language code (optional)");
  var langInput = document.createElement("input");
  langInput.type = "text";
  langInput.id = "import-language";
  langInput.placeholder = "e.g. en, es, fr";
  langInput.autocomplete = "off";
  langField.appendChild(langInput);
  el.importPanel.appendChild(langField);

  /* Format help. */
  var help = document.createElement("p");
  help.className = "import-help";
  help.appendChild(document.createTextNode(
    "Each record needs question and answer. Optional: qtype "
    + "(free_response, multiple_choice, translate, identify; default "
    + "free_response), alternatives, distractors, hints, tags, media_url, "
    + "difficulty (1-4). JSONL: one JSON object per line. CSV: a header row; "
    + "array cells are pipe-separated."));
  el.importPanel.appendChild(help);

  /* Action row + status. */
  var actions = document.createElement("div");
  actions.className = "import-actions";
  var submit = document.createElement("button");
  submit.type = "button";
  submit.id = "import-submit";
  submit.textContent = "Import";
  submit.addEventListener("click", onImportSubmit);
  actions.appendChild(submit);
  var status = document.createElement("span");
  status.className = "import-status";
  status.id = "import-status";
  actions.appendChild(status);
  el.importPanel.appendChild(actions);
}

export function importField(labelText) {
  var field = document.createElement("div");
  field.className = "import-field";
  var label = document.createElement("label");
  label.textContent = labelText;
  field.appendChild(label);
  return field;
}

export function setImportStatus(text, kind) {
  var status = document.getElementById("import-status");
  if (!status) {
    return;
  }
  status.textContent = text || "";
  status.className = "import-status" + (kind ? " " + kind : "");
}

/* Submit the import as multipart/form-data. Validates a file is chosen,
   builds FormData, posts, and reports the {bank_id, imported} count or the
   server's row-naming parse error. */
export async function onImportSubmit() {
  var fileInput = document.getElementById("import-file");
  var catSelect = document.getElementById("import-category");
  var nameInput = document.getElementById("import-name");
  var langInput = document.getElementById("import-language");
  var submit = document.getElementById("import-submit");

  if (!fileInput || fileInput.files.length === 0) {
    setImportStatus("Choose a file to import.", "error");
    return;
  }

  var form = new FormData();
  form.append("file", fileInput.files[0]);
  form.append("category_id", catSelect.value);
  if (nameInput.value.trim() !== "") {
    form.append("name", nameInput.value.trim());
  }
  if (langInput.value.trim() !== "") {
    form.append("language", langInput.value.trim());
  }
  /* format is omitted: the server infers it from the file extension. */

  submit.disabled = true;
  setImportStatus("Importing...", null);
  try {
    var response = await fetch("/api/banks/import", {
      method: "POST",
      body: form /* no Content-Type header: the browser sets the multipart
                    boundary automatically */
    });
    var data = await readJson(response); /* throws on !ok with {error} */
    var bankLabel = (nameInput.value.trim() !== "")
      ? nameInput.value.trim()
      : (fileInput.files[0].name || "bank");
    setImportStatus(
      "Imported " + data.imported + " question"
      + (data.imported === 1 ? "" : "s") + " into '" + bankLabel + "'.",
      "ok");
    /* Refresh categories AND banks so the drillability gate updates now that
       a bank exists: the category un-gates and its new bank is selectable.
       This is the C-016 fix for the C-017 symptom (category stayed gated). */
    await refreshCategories();
    /* C-016 fold-in: collapse the panel on success so the user is returned to
       the drill. Kept open on error (the catch below) so they can fix and
       retry. A brief delay lets the success message be seen first. */
    setTimeout(collapseImportPanel, 1200);
  } catch (error) {
    setImportStatus(error.message, "error");
  } finally {
    submit.disabled = false;
  }
}

/* Collapse the import disclosure (used after a successful import). */
export function collapseImportPanel() {
  if (el.importToggle.getAttribute("aria-expanded") === "true") {
    el.importPanel.hidden = true;
    el.importToggle.setAttribute("aria-expanded", "false");
    el.importToggle.textContent = "+ Import a bank";
  }
}

/* Re-fetch categories and re-render the top selector (keeping the current
   selection if still present). Used after an import so a newly-drillable
   category un-gates without a page reload. */
export async function refreshCategories() {
  try {
    var data = await apiGet("/api/categories");
    var previous = el.category.value;
    populateCategories(data.categories);
    /* CRITICAL (C-016 fix): re-attach banks after re-populating, since
       /api/categories carries none. Without this the just-imported category
       would re-render still gated -- this was the C-017 gray-dropdown bug. */
    await fetchAndAttachBanks();
    populateCategories(state.categories); /* re-render now that banks exist */
    /* Restore prior selection when it still exists and is enabled. */
    var optionToRestore = null;
    for (var i = 0; i < el.category.options.length; i++) {
      if (el.category.options[i].value === previous
          && !el.category.options[i].disabled) {
        optionToRestore = el.category.options[i];
        break;
      }
    }
    if (optionToRestore) {
      el.category.value = previous;
    }
  } catch (error) {
    /* A failed refresh is non-fatal: the import already succeeded. Leave the
       selector as-is; the user can reload to see the new category state. */
  }
}

export async function boot() {
  console.info("drill: boot() wiring listeners");
  el.action.addEventListener("click", onAction);
  el.answer.addEventListener("keydown", onAnswerKey);
  el.answer.addEventListener("input", onAnswerInput);
  el.category.addEventListener("change", onCategoryChange);
  el.bank.addEventListener("change", onBankChange);
  el.difficulty.addEventListener("change", onDifficultyChange);
  el.importToggle.addEventListener("click", onImportToggle);
  el.statsToggle.addEventListener("click", onStatsToggle);
  el.speaker.addEventListener("click", onSpeakerClick);
  document.addEventListener("keydown", onDocumentKey);
  window.addEventListener("beforeunload", endSessionOnUnload);

  try {
    var data = await apiGet("/api/categories");
    populateCategories(data.categories);
    /* Attach banks (separate fetch -- /api/categories has none), then
       re-render so any category with banks is already un-gated on load. A
       banks-fetch failure is non-fatal: arithmetic still drills. */
    try {
      await fetchAndAttachBanks();
      populateCategories(state.categories);
    } catch (banksError) {
      /* Leave categories bank-less; only arithmetic will be drillable. */
    }

    if (state.arithmeticCategoryId === null) {
      setNote("No arithmetic category found. Check the seeded categories.", true);
      return;
    }
    /* Default selection is arithmetic (first seeded category); start drilling.
       Set the selection explicitly so startSession targets arithmetic. */
    el.category.value = String(state.arithmeticCategoryId);
    el.bankSelector.hidden = true;
    /* Populate the difficulty selector (arithmetic-only) and gate it for the
       default arithmetic selection: enabled, note hidden. A populate failure
       is non-fatal (the control keeps just "Default"). */
    await populateDifficulty();
    applyDifficultyGating(state.arithmeticCategoryName);
    state.selection = {
      categoryId: state.arithmeticCategoryId,
      categoryName: state.arithmeticCategoryName,
      bankId: null,
      bankName: null
    };
    renderSessionUI(); /* show controls/zeroed bar before the first answer */
    await loadQuestion();
    console.info("drill: boot() complete -- app is live");
  } catch (error) {
    console.error("drill: boot() failed:", error);
    setNote(error.message, true);
  }
}

/* ---- Boot-guard: the sole module-scope statement (S7) ----------------- */
/* Run boot once the DOM is ready. Calls the hoisted boot(); reads no other
   module's export at eval time, so the drill<->session cycle is undisturbed. */
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", boot);
} else {
  boot();
}
