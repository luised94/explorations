"""C0.1 -- boundary-purity guard on the STILL-MONOLITHIC drill.py (ASCII only).

The layering invariant is the POINT of the modularization (CODING_CONVENTIONS
"Keep the layering invariant"): config <- db <- logic <- http; main wires;
LOGIC is pure (no clock/IO/DB); the clock is read only in HTTP, MAIN, and
init_db. This test turns that invariant into a CHECK rather than a reminder
(ADR-048 "conventions become checks", ADR-050 the guard contract), so a future
extraction that silently breaks the DAG reddens the suite instead of shipping.

It runs on the monolith NOW (before any cut). Layer is assigned BY SYMBOL --
the section a top-level name is DEFINED in, read from the `# --- SECTION ---`
banners -- not by the line a reference sits on, and the reference scan is
SCOPE-AWARE (params/locals are skipped). That combination is mandatory: the
naive line-range + substring version produced three false positives on the
clean file (S2/S8 -- a `leaf_count` PARAMETER shadowing the LOGIC function; a
builder co-located with its own validation constants). This guard reproduces
S2's measured DAG exactly (HTTP->DB 23, LOGIC->CONFIG 19, HTTP->LOGIC 12,
DB->CONFIG 7, MAIN->{DB,CONFIG,HTTP}) with ZERO forward edges.

TWO policies, each expressed as DATA (ADR-050 "DUAL guard"):
  1. LAYER-REFERENCE: no symbol may reference a strictly-higher layer.
  2. PURITY: a per-layer table of forbidden call targets. LOGIC may not read the
     clock or touch the DB; CONFIG may not either. This is a CALL-LEVEL check on
     purpose -- a function-LOCAL `import datetime` dodges any module-level import
     ban, and only the call-level AST check catches it (S4, proven by injection).

BOTH DIRECTIONS (S4): the guard is GREEN on the real drill.py and RED on an
injected clock read inside a LOGIC function -- the second half is asserted here
so a guard that silently passes everything cannot masquerade as green.
"""

import ast
import os

import pytest

DRILL = "drill.py"

# Layer order. A reference from layer X to layer Y is legal iff rank[X] > rank[Y]
# (you may call DOWN the stack, never UP). MAIN is the wiring root and sits on
# top; "nothing imports http" falls out of http being rank 3 and only main
# (rank 4) referencing it.
LAYER_RANK = {"CONFIG": 0, "DATABASE": 1, "LOGIC": 2, "HTTP": 3, "MAIN": 4}

# Banner that opens each section, verbatim in drill.py.
SECTION_BANNERS = {
    "# --- CONFIG ---": "CONFIG",
    "# --- DATABASE ---": "DATABASE",
    "# --- LOGIC ---": "LOGIC",
    "# --- HTTP ---": "HTTP",
    "# --- MAIN ---": "MAIN",
}

# Symbol -> layer OVERRIDES: the few names whose true layer differs from the
# section they physically sit in. This is the concrete form of ADR-050's rule
# ("assign layer by SYMBOL, not raw line number") and S2/S8's lesson (distrust
# physical position). Keep this table tiny and JUSTIFIED -- each entry is a
# membership fact the D-phase cuts must honor, not a way to silence a real
# violation.
#
#   The v2/v3 migration functions are DDL runners (connection.execute ALTER
#   TABLE). They live in the CONFIG *region* only because they are read next to
#   SCHEMA_VERSION and the MIGRATIONS registry that lists them; by role they are
#   DATABASE operations. The purity guard correctly refuses to call them CONFIG
#   (config touches no DB), and D2 will physically relocate them into db.py.
LAYER_OVERRIDES = {
    "_migrate_2_add_questions_metadata": "DATABASE",
    "_migrate_3_add_response_difficulty": "DATABASE",
}

# PURITY policy, as data: for each layer, the set of call TARGET names that a
# function in that layer may not invoke. Attribute calls are matched on the
# attribute name (datetime.now -> "now"); plain calls on the callee name. The
# clock primitives live here because LOGIC must stay clock-free (it is handed
# timestamps by HTTP/MAIN). DB access names catch a LOGIC function reaching for
# the connection layer directly.
CLOCK_CALLS = frozenset({"now", "utcnow", "utc_now_iso", "time", "monotonic"})
DB_CALLS = frozenset({"connect", "execute", "executemany", "commit", "cursor"})
FORBIDDEN_CALLS = {
    "CONFIG": CLOCK_CALLS | DB_CALLS,
    "LOGIC": CLOCK_CALLS | DB_CALLS,
}

# Clock-read allowlist: symbols permitted to read the clock despite the general
# rule, because the convention names them explicitly ("the clock is read only in
# HTTP (and init_db)"). utc_now_iso is the clock PRIMITIVE itself; init_db
# stamps a created-at at baseline. HTTP and MAIN are allowed wholesale (not in
# FORBIDDEN_CALLS at all), matching "HTTP is the only layer that reads the
# clock" plus the MAIN startup injection.
CLOCK_ALLOWED_SYMBOLS = frozenset({"utc_now_iso", "init_db"})

# Extracted layer modules -> their layer. As the D-phase cuts progress, each
# layer moves from the drill.py monolith into its own top-level module (thin
# drill.py stays the MAIN composition root -- D-MOD-3). The guard checks the
# monolith regions for symbols not yet extracted AND the cross-file import
# direction for modules that exist. This is the handoff-named evolution: "post-
# split the guard's layer-of-symbol switches from line-range to the file it
# lives in". Only files that exist are analyzed, so the guard stays green
# through each incremental cut.
LAYER_MODULES = {
    "config.py": "CONFIG",
    "db.py": "DATABASE",
    "logic.py": "LOGIC",
    "http.py": "HTTP",
    # drill.py is the MAIN composition root + not-yet-extracted remainder; it is
    # allowed to import every lower layer, so it is handled specially (no ban).
}


def _existing_layer_modules():
    return {
        path: layer for path, layer in LAYER_MODULES.items() if os.path.exists(path)
    }


def _read(path=DRILL):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _section_bounds(source):
    """Return [(layer, start_line), ...] sorted by start line, from banners."""
    bounds = []
    for lineno, raw in enumerate(source.splitlines(), start=1):
        layer = SECTION_BANNERS.get(raw.strip())
        if layer is not None:
            bounds.append((layer, lineno))
    bounds.sort(key=lambda pair: pair[1])
    return bounds


def _layer_of_line(bounds, lineno):
    layer = bounds[0][0]
    for name, start in bounds:
        if lineno >= start:
            layer = name
    return layer


def _defined_names(node):
    """Top-level names a statement binds (def/class name, assignment targets)."""
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return [node.name]
    if isinstance(node, ast.Assign):
        return [t.id for t in node.targets if isinstance(t, ast.Name)]
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return [node.target.id]
    return []


def _top_level_symbols(tree, bounds):
    """Map top-level symbol name -> (layer, defining_node). Layer is the section
    the symbol is DEFINED in (by symbol, not by reference site)."""
    symbols = {}
    for node in tree.body:
        for name in _defined_names(node):
            layer = LAYER_OVERRIDES.get(name, _layer_of_line(bounds, node.lineno))
            symbols[name] = (layer, node)
    return symbols


def _local_bindings(func):
    """Names bound locally in func (params + assignment / for / with /
    comprehension targets). Scope-awareness: a reference to one of these is NOT
    a cross-layer reference even if a top-level symbol shares the name (the
    `leaf_count` parameter that shadows the LOGIC function -- S2)."""
    local = set()
    args = func.args
    for group in (args.posonlyargs, args.args, args.kwonlyargs):
        for arg in group:
            local.add(arg.arg)
    if args.vararg:
        local.add(args.vararg.arg)
    if args.kwarg:
        local.add(args.kwarg.arg)

    def add_targets(target):
        for sub in ast.walk(target):
            if isinstance(sub, ast.Name):
                local.add(sub.id)

    for node in ast.walk(func):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                add_targets(target)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            local.add(node.target.id)
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            add_targets(node.target)
        elif isinstance(node, ast.comprehension):
            add_targets(node.target)
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                if item.optional_vars is not None:
                    add_targets(item.optional_vars)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node is not func:
                local.add(node.name)  # nested def name is a local binding
    return local


def _iter_layer_functions(tree, symbols):
    """Yield (owner_name, owner_layer, func_node) for every top-level function,
    including methods defined inside a top-level class (the class's layer)."""
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node.name, symbols[node.name][0], node
        elif isinstance(node, ast.ClassDef):
            class_layer = symbols[node.name][0]
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    yield node.name + "." + child.name, class_layer, child


def _call_target_name(call):
    """The name a Call resolves to for purity matching: attribute name for
    obj.attr(...), plain name for f(...). None for anything else."""
    func = call.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def _reference_violations(tree, symbols):
    """Every cross-layer, scope-aware reference that points UP the stack."""
    violations = []
    known = set(symbols)
    for owner, owner_layer, func in _iter_layer_functions(tree, symbols):
        local = _local_bindings(func)
        for node in ast.walk(func):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                target = node.id
                if target == owner.split(".")[-1] or target in local:
                    continue
                if target not in known:
                    continue
                target_layer = symbols[target][0]
                if LAYER_RANK[target_layer] > LAYER_RANK[owner_layer]:
                    violations.append(
                        "%s (%s) references %s (%s) up-stack at line %d"
                        % (owner, owner_layer, target, target_layer, node.lineno)
                    )
    return violations


def _purity_violations(tree, symbols):
    """Every forbidden call (by target name) made from a function whose layer
    bans it, honoring the clock allowlist."""
    violations = []
    for owner, owner_layer, func in _iter_layer_functions(tree, symbols):
        banned = FORBIDDEN_CALLS.get(owner_layer)
        if not banned:
            continue
        short = owner.split(".")[-1]
        for node in ast.walk(func):
            if not isinstance(node, ast.Call):
                continue
            target = _call_target_name(node)
            if target is None or target not in banned:
                continue
            if target in CLOCK_CALLS and short in CLOCK_ALLOWED_SYMBOLS:
                continue
            violations.append(
                "%s (%s) makes forbidden call to %s() at line %d"
                % (owner, owner_layer, target, node.lineno)
            )
    return violations


def _import_direction_violations():
    """Every cross-layer MODULE import that points UP the stack. This is the
    file-level analog of _reference_violations: once a layer lives in its own
    module, an illegal edge shows up as `import <higher-layer-module>` rather
    than a bare-name reference. drill.py (MAIN composition root) is exempt -- it
    legally imports every lower layer. Only modules that exist are checked, so
    the guard stays green through each incremental D-phase cut.

    This is the AST twin of the C0.2 ruff banned-api rule (declarative import
    ban): the ruff config catches it at lint time, this catches it in the suite
    (portable to the clean-room clone), and neither depends on the other."""
    existing = _existing_layer_modules()
    violations = []
    for path, layer in existing.items():
        with open(path, "r", encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                module_file = name.split(".")[0] + ".py"
                target_layer = LAYER_MODULES.get(module_file)
                if target_layer is None:
                    continue  # stdlib / third-party / drill itself
                if LAYER_RANK[target_layer] > LAYER_RANK[layer]:
                    violations.append(
                        "%s (%s) imports %s (%s) up-stack at line %d"
                        % (path, layer, module_file, target_layer, node.lineno)
                    )
    return violations


# --------------------------------------------------------------------------
# Fixtures: parse the real file once.
# --------------------------------------------------------------------------
@pytest.fixture(scope="module")
def drill_source():
    assert os.path.exists(DRILL), "run from PROJECT_ROOT (conftest chdirs there)"
    return _read()


@pytest.fixture(scope="module")
def drill_tree(drill_source):
    return ast.parse(drill_source)


@pytest.fixture(scope="module")
def bounds(drill_source):
    b = _section_bounds(drill_source)
    present = [name for name, _ in b]
    # As layers are extracted into their own modules, their banner leaves
    # drill.py. What remains must (a) be a subsequence of the canonical order and
    # (b) exactly account for the layers NOT yet extracted: every canonical layer
    # is either still a drill.py banner or an existing layer module (config.py,
    # db.py, ...). CONFIG is special-cased: its banner lingers over the config
    # IMPORT block in drill.py even though config.py exists, so it may appear in
    # both. This lets the guard stay green across each incremental D-phase cut
    # without a hardcoded five-banner list.
    canonical = ["CONFIG", "DATABASE", "LOGIC", "HTTP", "MAIN"]
    assert present == [x for x in canonical if x in present], (
        "banners out of canonical order: %r" % (present,)
    )
    extracted = set(_existing_layer_modules().values())
    for layer in canonical:
        if layer == "MAIN":
            continue  # MAIN is drill.py itself; no separate module, banner optional
        in_banner = layer in present
        in_module = layer in extracted
        assert in_banner or in_module, (
            "layer %s is neither a drill.py banner nor an extracted module" % layer
        )
    return b


@pytest.fixture(scope="module")
def symbols(drill_tree, bounds):
    return _top_level_symbols(drill_tree, bounds)


# --------------------------------------------------------------------------
# GREEN on the clean monolith.
# --------------------------------------------------------------------------
def test_no_upstack_references(drill_tree, symbols):
    """The backend is a one-way DAG: nothing references a higher layer (S2)."""
    violations = _reference_violations(drill_tree, symbols)
    assert violations == [], "up-stack references found:\n  " + "\n  ".join(violations)


def test_logic_and_config_are_pure(drill_tree, symbols):
    """LOGIC and CONFIG read no clock and touch no DB (call-level, S4). Covers
    the drill.py residual AND every extracted layer module that exists, so a cut
    that drags a clock/DB call into config.py or logic.py reddens immediately."""
    violations = _purity_violations(drill_tree, symbols)
    for path, layer in _existing_layer_modules().items():
        with open(path, "r", encoding="utf-8") as handle:
            mod_tree = ast.parse(handle.read())
        # In an extracted module every top-level symbol IS that module's layer.
        mod_symbols = {}
        for node in mod_tree.body:
            for nm in _defined_names(node):
                mod_symbols[nm] = (layer, node)
        violations.extend(_purity_violations(mod_tree, mod_symbols))
    assert violations == [], "purity violations found:\n  " + "\n  ".join(violations)


def test_no_upstack_module_imports():
    """No extracted layer module imports a higher layer (the file-level DAG).
    drill.py (MAIN root) is exempt. Complements the C0.2 ruff banned-api rule."""
    violations = _import_direction_violations()
    assert violations == [], "up-stack module imports:\n  " + "\n  ".join(violations)


def test_backend_dag_has_no_upstack_edges(drill_tree, symbols):
    """The backend is a one-way DAG (S2). Within the drill.py residual, no
    bare-name reference points up-stack; the count of any surviving cross-layer
    edge is not pinned (extraction legitimately drains the monolith's internal
    edges into cross-file imports, checked by test_no_upstack_module_imports).
    This replaces the monolith-era headline-count pin, which no longer holds
    once layers split into their own files."""
    from collections import Counter

    edges = Counter()
    known = set(symbols)
    for owner, owner_layer, func in _iter_layer_functions(drill_tree, symbols):
        local = _local_bindings(func)
        short = owner.split(".")[-1]
        for node in ast.walk(func):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                t = node.id
                if t == short or t in local or t not in known:
                    continue
                tl = symbols[t][0]
                if tl != owner_layer:
                    edges[(owner_layer, tl)] += 1
    upstack = {
        pair: c
        for pair, c in edges.items()
        if LAYER_RANK[pair[0]] < LAYER_RANK[pair[1]]
    }
    assert upstack == {}, "up-stack references within drill.py: %r" % (upstack,)


# --------------------------------------------------------------------------
# RED on injection -- the other direction (S4). A guard that cannot fail is
# not a guard; prove it reddens on a clock read planted in a LOGIC function.
# --------------------------------------------------------------------------
def _inject_clock_into_a_logic_function(source):
    """Return source with `datetime.now(timezone.utc)` planted as the first
    statement of the LOGIC function validate_answer, via a FUNCTION-LOCAL
    import so a module-level import ban would miss it (S4)."""
    lines = source.splitlines()
    target = None
    for i, line in enumerate(lines):
        if line.startswith("def validate_answer("):
            target = i
            break
    assert target is not None, "validate_answer not found -- update the injection"
    # find the line after the def (and its possible multi-line signature) where
    # the body begins; insert an indented local import + clock call there.
    insert_at = target
    while not lines[insert_at].rstrip().endswith(":"):
        insert_at += 1
    insert_at += 1
    inject = [
        "    import datetime as _injected_dt",
        "    _ = _injected_dt.datetime.now()",
    ]
    return "\n".join(lines[:insert_at] + inject + lines[insert_at:])


def test_guard_reddens_on_injected_clock_in_logic(drill_source, bounds):
    injected = _inject_clock_into_a_logic_function(drill_source)
    tree = ast.parse(injected)
    symbols = _top_level_symbols(tree, bounds)
    violations = _purity_violations(tree, symbols)
    assert any("validate_answer" in v and "now()" in v for v in violations), (
        "the guard failed to catch a clock read injected into a LOGIC "
        "function -- it would pass anything (found: %r)" % (violations,)
    )


def test_guard_reddens_on_injected_upstack_reference(drill_source, bounds):
    """A LOGIC function reaching UP to an HTTP symbol must redden the reference
    check. (Originally injected a DB->LOGIC edge; DB moved to db.py in D2, so
    this now uses a LOGIC->HTTP pair that still lives in the drill.py residual.)"""
    lines = drill_source.splitlines()
    target = None
    for i, line in enumerate(lines):
        if line.startswith("def normalize_text("):  # a LOGIC function
            target = i
            break
    assert target is not None, "normalize_text not found -- update the injection"
    insert_at = target
    while not lines[insert_at].rstrip().endswith(":"):
        insert_at += 1
    insert_at += 1
    # serve_index is an HTTP route handler; referencing it from LOGIC is up-stack.
    inject = ["    _ = serve_index"]
    injected = "\n".join(lines[:insert_at] + inject + lines[insert_at:])
    tree = ast.parse(injected)
    symbols = _top_level_symbols(tree, bounds)
    violations = _reference_violations(tree, symbols)
    assert any("normalize_text" in v and "serve_index" in v for v in violations), (
        "the guard failed to catch an up-stack reference injected into a LOGIC "
        "function (found: %r)" % (violations,)
    )
