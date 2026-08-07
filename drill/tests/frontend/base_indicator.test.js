"use strict";
/* base_indicator.test.js -- C-BIT-j.
 *
 * The bitwise display path adds two things to the stage: a monospace class on
 * the expression (fixed-width binary only reads as aligned columns in a mono
 * face -- finding H) and a base-indicator badge naming a non-decimal base.
 *
 * Like import.test.js, the CSS assertions read the REAL index.html stylesheet
 * TEXT statically, not via jsdom's cascade: jsdom does not model specificity or
 * resolve which rule wins, so a layout read would be meaningless. Asserting the
 * rule text is present is the correct, honest check (the handoff: assert
 * stylesheet RULE TEXT, not cascade-resolved layout). The DOM assertions use
 * the real parsed document.
 *
 * The BEHAVIORAL half -- updateBaseIndicator toggling the badge and the mono
 * class from a served payload -- lives in the module-graph harness tests
 * (drill.module/drill), which drive the real drill.js against a fixture DOM.
 *
 * ASCII only.
 */
const fs = require("fs");
const path = require("path");
const { JSDOM } = require("jsdom");

let pass = 0, fail = 0;
const ck = (n, c) => { c ? (pass++, console.log("  ok  - " + n)) : (fail++, console.log("  FAIL- " + n)); };

const html = fs.readFileSync(path.resolve("index.html"), "utf8");
const dom = new JSDOM(html);
const doc = dom.window.document;

/* --- DOM structure: the base-indicator node exists, is hidden by default, and
 *     sits on the stage next to the expression it annotates. ---------------- */
const node = doc.getElementById("base-indicator");
ck("base-indicator node present", node !== null);
ck("base-indicator hidden by default", node !== null && node.hasAttribute("hidden"));
ck("base-indicator is aria-live (announces on change)",
  node !== null && node.getAttribute("aria-live") === "polite");
ck("base-indicator sits inside the stage section",
  node !== null && node.closest("section.stage") !== null);

/* --- stylesheet RULE TEXT (static, not cascade): the mono expression class and
 *     the base-indicator hidden guard are both declared. --------------------- */
const monoRule = /\.expression\.mono\s*\{[^}]*font-family:\s*var\(--mono\)/.test(html);
ck("stylesheet has .expression.mono { font-family: var(--mono) }", monoRule);

const baseHiddenGuard = /\.base-indicator\[hidden\]\s*\{\s*display:\s*none/.test(html);
ck("stylesheet has .base-indicator[hidden]{display:none} guard", baseHiddenGuard);

const baseIndicatorRule = /\.base-indicator\s*\{[^}]*font-family:\s*var\(--mono\)/.test(html);
ck("stylesheet has .base-indicator { font-family: var(--mono) }", baseIndicatorRule);

console.log("\n" + pass + " passed, " + fail + " failed");
if (fail > 0) process.exit(1);
