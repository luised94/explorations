SYSTEM OVERVIEW

repository
 -> deterministic extraction
 -> graph construction
 -> repository dynamics
 -> semantic indexing
 -> targeted synthesis
 -> hypothesis refinement
 -> refactor planning

Primary rule:
LLMs synthesize.
Deterministic systems extract.

Never ask the LLM to exhaustively discover structure from raw files.

--------------------------------------------------
GLOBAL DATA STRUCTURES
--------------------------------------------------

REPO_STATE = {
    files,
    symbols,
    trees,
    imports,
    calls,
    mutations,
    dispatches,
    state_domains,
    vocab,
    git_history,
    churn,
    clusters,
    semantic_hypotheses,
    subsystem_maps,
    flow_slices,
    refactor_targets,
}

--------------------------------------------------
STAGE 1: FILE DISCOVERY
--------------------------------------------------

files = rg(
    include = [
        "*.py",
        "*.lua",
        "*.sh",
        "*.bash",
        "*.r",
        "*.js",
        "*.ts",
    ],

    exclude = [
        "node_modules",
        "dist",
        "build",
        ".git",
    ]
)

REPO_STATE.files = files

--------------------------------------------------
STAGE 2: TREE-SITTER PARSING
--------------------------------------------------

FOR each file IN files:

    tree = treesitter_parse(file)

    symbols = extract_symbols(tree)

    imports = extract_imports(tree)

    calls = extract_calls(tree)

    assignments = extract_assignments(tree)

    conditionals = extract_conditionals(tree)

    loops = extract_loops(tree)

    returns = extract_returns(tree)

    dispatch_patterns = extract_dispatch_patterns(tree)

    mutation_patterns = extract_mutations(tree)

    serialization_patterns = extract_serialization_patterns(tree)

    normalization_patterns = extract_normalization_patterns(tree)

    append REPO_STATE.trees

    append REPO_STATE.symbols

    append REPO_STATE.imports

    append REPO_STATE.calls

    append REPO_STATE.mutations

    append REPO_STATE.dispatches

--------------------------------------------------
STAGE 3: STRUCTURAL INDEXING
--------------------------------------------------

CALL_GRAPH = build_call_graph(
    REPO_STATE.calls
)

IMPORT_GRAPH = build_import_graph(
    REPO_STATE.imports
)

MUTATION_GRAPH = build_mutation_graph(
    REPO_STATE.mutations
)

DISPATCH_GRAPH = build_dispatch_graph(
    REPO_STATE.dispatches
)

STATE_DERIVATION_GRAPH = build_state_graph(
    assignments,
    mutations,
    normalization_patterns
)

REPO_STATE.graphs = {
    CALL_GRAPH,
    IMPORT_GRAPH,
    MUTATION_GRAPH,
    DISPATCH_GRAPH,
    STATE_DERIVATION_GRAPH,
}

--------------------------------------------------
STAGE 4: GIT DYNAMICS
--------------------------------------------------

git_log = git_log_extract()

git_blame = git_blame_extract()

git_churn = compute_churn()

git_cochange = compute_cochange_graph()

git_hotspots = compute_hotspots()

git_vocab = extract_commit_vocabulary()

REPO_STATE.git_history = git_log

REPO_STATE.churn = git_churn

REPO_STATE.cochange = git_cochange

REPO_STATE.hotspots = git_hotspots

--------------------------------------------------
STAGE 5: NLP + SEMANTIC ANALYSIS
--------------------------------------------------

identifiers = extract_identifiers(
    REPO_STATE.symbols
)

comments = extract_comments()

commit_messages = extract_commit_messages()

corpus = merge(
    identifiers,
    comments,
    commit_messages
)

tokenized = tokenize(corpus)

normalized = normalize_tokens(tokenized)

term_frequency = compute_tf_idf(normalized)

embedding_clusters = cluster_embeddings(normalized)

topic_clusters = compute_topic_clusters(normalized)

semantic_duplicates = detect_semantic_duplicates()

naming_inconsistencies = detect_naming_inconsistencies()

REPO_STATE.vocab = {
    term_frequency,
    embedding_clusters,
    topic_clusters,
    semantic_duplicates,
    naming_inconsistencies,
}

--------------------------------------------------
STAGE 6: DISPATCH + STATE ANALYSIS
--------------------------------------------------

dispatch_roots = locate_dispatch_roots(
    DISPATCH_GRAPH
)

state_roots = locate_state_roots(
    STATE_DERIVATION_GRAPH
)

normalization_layers = detect_normalization_layers()

repeated_derivations = detect_repeated_derivations()

repeated_validations = detect_repeated_validations()

mode_systems = detect_mode_systems()

implicit_state_machines = detect_state_machines()

REPO_STATE.state_domains = {
    dispatch_roots,
    state_roots,
    normalization_layers,
    repeated_derivations,
    repeated_validations,
    mode_systems,
    implicit_state_machines,
}

--------------------------------------------------
STAGE 7: FLOW SLICE EXTRACTION
--------------------------------------------------

TARGET_BEHAVIORS = [
    "keyboard navigation",
    "command dispatch",
    "selection movement",
    "config loading",
    "state serialization",
]

FOR each behavior IN TARGET_BEHAVIORS:

    entrypoints = locate_behavior_entrypoints(
        behavior
    )

    flows = trace_behavior_flows(
        entrypoints,
        CALL_GRAPH,
        MUTATION_GRAPH,
        DISPATCH_GRAPH
    )

    mutations = trace_state_mutations(
        flows
    )

    render_effects = trace_render_effects(
        flows
    )

    flow_slice = {
        behavior,
        entrypoints,
        flows,
        mutations,
        render_effects,
    }

    append REPO_STATE.flow_slices

--------------------------------------------------
STAGE 8: TARGETED LLM SYNTHESIS
--------------------------------------------------

FOR each flow_slice IN REPO_STATE.flow_slices:

    context = assemble_context(
        flow_slice,
        relevant_files,
        relevant_symbols,
        relevant_mutations,
        git_history,
        semantic_clusters
    )

    prompt = build_prompt(
        goals = [
            "identify invariants",
            "identify repeated interpretation",
            "identify hidden normalization",
            "identify unstable representations",
            "identify refactor opportunities",
        ],

        constraints = [
            "avoid premature architecture",
            "preserve procedural flow",
            "preserve locality",
            "favor data-oriented structure",
        ],

        context = context
    )

    llm_response = curl_llm_api(
        prompt
    )

    extracted_hypotheses = parse_llm_response(
        llm_response
    )

    append REPO_STATE.semantic_hypotheses

--------------------------------------------------
STAGE 9: HYPOTHESIS REFINEMENT
--------------------------------------------------

FOR each hypothesis IN semantic_hypotheses:

    supporting_evidence = locate_supporting_evidence(
        hypothesis,
        graphs,
        git_history,
        mutations,
        identifiers
    )

    contradictory_evidence = locate_contradictions(
        hypothesis
    )

    confidence = compute_confidence(
        supporting_evidence,
        contradictory_evidence
    )

    IF confidence >= threshold:

        promote hypothesis

    ELSE:

        mark hypothesis unresolved

--------------------------------------------------
STAGE 10: REPRESENTATION ANALYSIS
--------------------------------------------------

representation_families = identify_representations(
    state_domains,
    dispatches,
    mutations,
    flows
)

FOR each representation_family:

    analyze:
        ownership
        mutation_paths
        normalization_points
        serialization_quality
        duplication
        invariants
        instability
        lifecycle

    detect:
        hidden_state
        repeated_derivation
        scattered_normalization
        unstable_naming
        duplicated_interpretation

--------------------------------------------------
STAGE 11: REFACTOR TARGET IDENTIFICATION
--------------------------------------------------

refactor_targets = prioritize_targets(
    criteria = [
        high_churn,
        repeated_interpretation,
        unstable_state,
        duplicated_normalization,
        dispatch_entropy,
        mutation_complexity,
        semantic_duplication,
    ]
)

FOR each target:

    estimate:
        blast_radius
        reversibility
        conceptual_complexity
        architectural_pressure
        normalization_gain
        procedural_clarity_gain

REPO_STATE.refactor_targets = refactor_targets

--------------------------------------------------
STAGE 12: REFACTOR PLANNING
--------------------------------------------------

FOR each target:

    derive:
        minimal_structural_change

    preserve:
        working_behavior
        locality
        procedural_flow

    avoid:
        frameworkization
        abstraction inflation
        premature modularization

    generate:
        commit_sequence

        each commit:
            reversible
            mechanically isolated
            structurally coherent

--------------------------------------------------
STAGE 13: CONTINUOUS REFINEMENT LOOP
--------------------------------------------------

WHILE analysis_pressure_exists:

    select highest-uncertainty subsystem

    refine:
        flow traces
        mutation traces
        representation maps
        semantic hypotheses

    regenerate:
        targeted prompts

    update:
        graphs
        hypotheses
        refactor priorities

--------------------------------------------------
CORE PRINCIPLES
--------------------------------------------------

1.
Representations matter more than files.

2.
Mutations matter more than nominal structure.

3.
Normalization boundaries matter more than abstractions.

4.
LLMs synthesize.
Deterministic systems extract.

5.
Behavioral slices beat whole-codebase analysis.

6.
Repository dynamics reveal architectural pressure.

7.
Stable state representations simplify reasoning.

8.
Explicit invariants reduce semantic entropy.

9.
Procedural flow is not the enemy.
Unstable representations are.

10.
Do not architect globally before understanding locally.
