"use strict";
/* ownership.guard.test.js -- E10 frontend guard (roadmap #1 modularization).
 *
 * Lands the ownership guard the ADR-051 addendum specifies. It is scope-aware /
 * symbol-based (acorn), never a substring grep (S8): a member expression counts
 * only when its receiver is the literal `el` identifier, so sel.bankId,
 * label.className, and the tail of el.importPanel.textContent are NOT counted.
 * acorn is on disk as a test-only dependency (installed alongside jsdom: a
 * SINGLE `npm install jsdom acorn --no-save` -- two separate --no-save installs
 * prune each other; see setup notes). The backend already owns the Python-side
 * purity guard (C0.1); this is its frontend analog, colocated with the option-(b)
 * harness.
 *
 * FOUR data-driven checks (per the addendum), plus RED-proofs that mirror the
 * backend C0.1 inject/parse/assert/restore discipline:
 *   (A) REGISTRY INTEGRITY  -- unique ids, non-empty owner in the module set,
 *       no two logical names share an id, no dead keys.
 *   (B) OWNER-DECLARES      -- each node's owner module references the node.
 *   (C) CROSS-OWNER ALLOWLIST (the check with teeth) -- any el.<node> read by a
 *       non-owner module must be an explicit CROSS_OWNER_READS row. Re-derived
 *       against the SHIPPED modules: 9 edges (NOT the ADR's pre-E1 count of 13
 *       -- functions moved to their real homes during E1-E9, so the attribution
 *       shifted; recomputed, not trusted blindly).
 *   (D) NO DOM AT IMPORT TIME (ADR-049) -- no module-scope getElementById /
 *       el.<key> / document.* outside a function body, with ONE named exemption:
 *       boot.js's readyState boot-guard (the sole module-scope statement, S7).
 *
 * RED-proofs (a guard that cannot fail is not a guard): prove GREEN on the clean
 * modules AND RED on each injection -- (1) an undeclared cross-owner read
 * (el.statsPanel into a speech function) reddens C; (2) a module-scope
 * document.getElementById in a NON-boot module reddens D (non-boot so the
 * boot-guard exemption cannot mask it).
 *
 * ASCII only.
 */
const fs = require("fs");
const path = require("path");
const acorn = require("acorn");

let pass = 0, fail = 0;
const ck = (n, c, extra) => { c ? (pass++, console.log("  ok  - " + n)) : (fail++, console.log("  FAIL- " + n + (extra ? "  [" + extra + "]" : ""))); };

const MODULES = ["state", "el", "api", "timing", "stage", "speech", "stats", "session", "drill", "boot"];
const KNOWN_OWNERS = new Set(["state", "el", "api", "timing", "stage", "speech", "stats", "session", "drill", "boot"]);

/* The 9 genuine cross-owner el.<node> reads, re-derived against the shipped
   modules (ADR-051 addendum: the 13-edge pre-E1 census shifted to 9 as
   functions landed in their real homes). Each row authorizes exactly one
   (node, reader) pair; node's owner is implied by EL_REGISTRY. */
const CROSS_OWNER_READS = [
  { node: "action", reader: "boot" },
  { node: "answer", reader: "boot" },
  { node: "answerHint", reader: "drill" },
  { node: "choices", reader: "stage" },
  { node: "feedback", reader: "stage" },
  { node: "speaker", reader: "boot" },
  { node: "speaker", reader: "drill" },
  { node: "statsToggle", reader: "boot" },
  { node: "streakPips", reader: "session" }
];
const allowKey = (node, reader) => node + "->" + reader;
const ALLOW = new Set(CROSS_OWNER_READS.map(r => allowKey(r.node, r.reader)));

function parse(src) { return acorn.parse(src, { ecmaVersion: 2022, sourceType: "module" }); }
function read(mod) { return fs.readFileSync(path.resolve(mod + ".js"), "utf8"); }

/* Walk with a parent-aware visitor. cb(node, ancestors[]) where ancestors is
   the stack of enclosing nodes (nearest last). */
function walk(node, cb, anc) {
  anc = anc || [];
  cb(node, anc);
  const next = anc.concat([node]);
  for (const k in node) {
    if (k === "type" || k === "start" || k === "end") continue;
    const v = node[k];
    if (Array.isArray(v)) v.forEach(c => c && typeof c.type === "string" && walk(c, cb, next));
    else if (v && typeof v.type === "string") walk(v, cb, next);
  }
}

const FN_TYPES = new Set(["FunctionDeclaration", "FunctionExpression", "ArrowFunctionExpression"]);
/* Is any ancestor a function body? (i.e. is this node inside a function) */
function insideFunction(anc) { return anc.some(a => FN_TYPES.has(a.type)); }

/* Extract the EL_REGISTRY {logicalName -> {id, owner}} from el.js by parsing
   the object literal (scope-aware, not regex). */
function parseRegistry() {
  const ast = parse(read("el"));
  let reg = null;
  walk(ast, (n) => {
    if (n.type === "VariableDeclarator" && n.id.name === "EL_REGISTRY" && n.init && n.init.type === "ObjectExpression") {
      reg = {};
      for (const prop of n.init.properties) {
        const name = prop.key.name || (prop.key.value);
        const obj = prop.value;
        let id = null, owner = null;
        for (const p of obj.properties) {
          const k = p.key.name || p.key.value;
          if (k === "id") id = p.value.value;
          if (k === "owner") owner = p.value.value;
        }
        reg[name] = { id, owner };
      }
    }
  });
  return reg;
}

/* Collect every el.<key> READ site in a module: member expressions whose object
   is the literal `el` identifier and property is a non-computed identifier.
   Scope-aware: the receiver must BE `el` (so sel.bankId, label.className are
   skipped; el.importPanel.textContent counts once, as el.importPanel). */
function elReads(mod) {
  const ast = parse(read(mod));
  const sites = [];
  walk(ast, (n, anc) => {
    if (n.type === "MemberExpression" && !n.computed
        && n.object.type === "Identifier" && n.object.name === "el"
        && n.property.type === "Identifier") {
      sites.push({ key: n.property.name, moduleScope: !insideFunction(anc) });
    }
  });
  return sites;
}

/* Collect module-scope DOM-at-import violations for check D: getElementById /
   document.* / el.<key> that sit OUTSIDE any function body. boot.js's readyState
   boot-guard is exempt (document.readyState + document.addEventListener in the
   trailing `if (document.readyState === "loading") {...}` that calls boot()). */
function domAtImport(mod) {
  const ast = parse(read(mod));
  const viol = [];
  walk(ast, (n, anc) => {
    if (insideFunction(anc)) return;                 /* only module scope */
    if (n.type === "MemberExpression" && !n.computed && n.object.type === "Identifier") {
      const obj = n.object.name, prop = n.property.name;
      if (obj === "el") viol.push(mod + ": el." + prop);
      if (obj === "document") viol.push(mod + ": document." + prop);
    }
    if (n.type === "CallExpression" && n.callee.type === "MemberExpression"
        && n.callee.property && n.callee.property.name === "getElementById") {
      viol.push(mod + ": getElementById()");
    }
  });
  /* Exempt boot.js's boot-guard: the module-scope `if (document.readyState...)`.
     Its document.readyState + document.addEventListener are the one sanctioned
     module-scope DOM touch (S7). Drop exactly document.readyState and
     document.addEventListener occurrences in boot. Any OTHER module-scope
     document.* (or in any non-boot module) still counts. */
  if (mod === "boot") {
    const exemptOnce = ["boot: document.readyState", "boot: document.addEventListener"];
    for (const e of exemptOnce) {
      const i = viol.indexOf(e);
      if (i !== -1) viol.splice(i, 1);
    }
  }
  return viol;
}

/* ---- Run the four checks on the clean, shipped modules ------------------ */
const registry = parseRegistry();

/* (A) REGISTRY INTEGRITY */
(function checkA() {
  const names = Object.keys(registry);
  const ids = names.map(n => registry[n].id);
  const uniqueIds = new Set(ids);
  ck("A: every registry id is unique", uniqueIds.size === ids.length, ids.length + " ids, " + uniqueIds.size + " unique");
  ck("A: every id is a non-empty string", ids.every(i => typeof i === "string" && i.length > 0));
  ck("A: every owner is in the known-module set",
    names.every(n => KNOWN_OWNERS.has(registry[n].owner)),
    names.filter(n => !KNOWN_OWNERS.has(registry[n].owner)).join(","));
  /* no dead keys: every registered node is read by at least one module */
  const readEverywhere = new Set();
  MODULES.forEach(m => elReads(m).forEach(s => readEverywhere.add(s.key)));
  const dead = names.filter(n => !readEverywhere.has(n));
  ck("A: no dead registry keys (every node is read somewhere)", dead.length === 0, "dead: " + dead.join(","));
})();

/* (B) OWNER-DECLARES: each node's owner module references the node. */
(function checkB() {
  const readsByModule = {};
  MODULES.forEach(m => { readsByModule[m] = new Set(elReads(m).map(s => s.key)); });
  const misassigned = [];
  for (const name of Object.keys(registry)) {
    const owner = registry[name].owner;
    if (!readsByModule[owner] || !readsByModule[owner].has(name)) misassigned.push(name + " (owner " + owner + " never references it)");
  }
  ck("B: every node's owner module references the node", misassigned.length === 0, misassigned.join("; "));
})();

/* (C) CROSS-OWNER ALLOWLIST: any el.<node> read by a non-owner module must be
   an explicit CROSS_OWNER_READS row. */
function crossOwnerViolations(registryArg) {
  const reg = registryArg || registry;
  const viol = [];
  for (const mod of MODULES) {
    for (const site of elReads(mod)) {
      const entry = reg[site.key];
      if (!entry) { viol.push(mod + " reads unregistered el." + site.key); continue; }
      if (entry.owner !== mod && !ALLOW.has(allowKey(site.key, mod))) {
        viol.push(mod + " reads el." + site.key + " (owned by " + entry.owner + ") -- not in CROSS_OWNER_READS");
      }
    }
  }
  return viol;
}
(function checkC() {
  const viol = crossOwnerViolations();
  ck("C: no undeclared cross-owner el reads (clean modules)", viol.length === 0, viol.join("; "));
  /* Also assert the allowlist has no STALE rows (every row is actually used) --
     keeps the policy honest as functions move. */
  const actual = new Set();
  for (const mod of MODULES) for (const site of elReads(mod)) {
    const entry = registry[site.key];
    if (entry && entry.owner !== mod) actual.add(allowKey(site.key, mod));
  }
  const stale = [...ALLOW].filter(k => !actual.has(k));
  ck("C: no stale CROSS_OWNER_READS rows", stale.length === 0, "stale: " + stale.join(","));
})();

/* (D) NO DOM AT IMPORT TIME (with boot-guard exemption). */
function domAtImportAll(sources) {
  /* sources: optional {mod: src} override for RED-proof injection. */
  const viol = [];
  for (const mod of MODULES) {
    const src = sources && sources[mod] !== undefined ? sources[mod] : read(mod);
    const ast = parse(src);
    const local = [];
    walk(ast, (n, anc) => {
      if (insideFunction(anc)) return;
      if (n.type === "MemberExpression" && !n.computed && n.object.type === "Identifier") {
        if (n.object.name === "el") local.push(mod + ": el." + n.property.name);
        if (n.object.name === "document") local.push(mod + ": document." + n.property.name);
      }
      if (n.type === "CallExpression" && n.callee.type === "MemberExpression"
          && n.callee.property && n.callee.property.name === "getElementById") {
        local.push(mod + ": getElementById()");
      }
    });
    if (mod === "boot") {
      ["boot: document.readyState", "boot: document.addEventListener"].forEach(e => {
        const i = local.indexOf(e); if (i !== -1) local.splice(i, 1);
      });
    }
    viol.push(...local);
  }
  return viol;
}
(function checkD() {
  const viol = domAtImportAll();
  ck("D: no module-scope DOM access at import time (boot-guard exempt)", viol.length === 0, viol.join("; "));
})();

/* ---- RED-PROOFS: the guard must FAIL on injected violations ------------- */
/* (1) Inject an undeclared cross-owner read: el.statsPanel (owned by stats)
   into a speech function. Check C must redden. Parse the modified speech source
   via the same scope-aware machinery (inject/parse/assert/restore). */
(function redProofC() {
  const speechSrc = read("speech");
  /* Add a benign statement referencing el.statsPanel inside canSpeakCurrent. */
  const marker = "export function canSpeakCurrent() {";
  const injected = speechSrc.replace(marker, marker + "\n  var _x = el.statsPanel;");
  const ok = injected !== speechSrc;
  /* Re-run check C with the injected speech source swapped in. */
  const savedElReads = elReads;
  const viol = (function () {
    const out = [];
    for (const mod of MODULES) {
      const src = mod === "speech" ? injected : read(mod);
      const ast = parse(src);
      walk(ast, (n, anc) => {
        if (n.type === "MemberExpression" && !n.computed && n.object.type === "Identifier"
            && n.object.name === "el" && n.property.type === "Identifier") {
          const entry = registry[n.property.name];
          if (entry && entry.owner !== mod && !ALLOW.has(allowKey(n.property.name, mod))) {
            out.push(mod + " reads el." + n.property.name);
          }
        }
      });
    }
    return out;
  })();
  ck("RED-proof C: injected cross-owner read (el.statsPanel in speech) reddens C",
    ok && viol.some(v => v.indexOf("speech reads el.statsPanel") !== -1), viol.join("; "));
})();

/* (2) Inject a module-scope document.getElementById into a NON-boot module
   (stats), so the boot-guard exemption cannot mask it. Check D must redden. */
(function redProofD() {
  const statsSrc = read("stats");
  /* Prepend a module-scope statement after the last import (before any fn). */
  const injected = statsSrc + "\nvar _leak = document.getElementById(\"stat-total\");\n";
  const viol = domAtImportAll({ stats: injected });
  ck("RED-proof D: module-scope getElementById in a non-boot module reddens D",
    viol.some(v => v.indexOf("stats: getElementById()") !== -1 || v.indexOf("stats: document.getElementById") !== -1),
    viol.join("; "));
  /* And prove the exemption is TIGHT: the same injection in boot is NOT masked
     unless it is exactly the readyState guard. A module-scope getElementById in
     boot still reddens. */
  const bootSrc = read("boot");
  const bootInjected = bootSrc + "\nvar _leak2 = document.getElementById(\"answer\");\n";
  const bootViol = domAtImportAll({ boot: bootInjected });
  ck("RED-proof D: an EXTRA module-scope getElementById in boot still reddens (exemption is tight)",
    bootViol.some(v => v.indexOf("boot: getElementById()") !== -1));
})();

console.log("\n" + pass + " passed, " + fail + " failed");
process.exit(fail ? 1 : 0);
