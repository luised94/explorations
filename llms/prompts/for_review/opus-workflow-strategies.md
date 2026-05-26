# Workflow Placement Guide
#
# Phase 0   : Profiling & Benchmarking     BEFORE any optimization work
# Phase 1   : Design                      (existing)
# Phase 2   : Implementation              (existing)
# Phase 2b  : Testing & Verification       DURING implementation, after each stable function
# Phase 3   : Hardening                   (existing)
# Phase 3b  : Strategic Debugging          ON DEMAND when something is wrong
# Phase 4   : Refactoring Triggers         PERIODIC review after implementation stabilizes
#
# Rationale for placement:
# - Profiling comes first because you need a baseline before designing optimizations.
# - Testing slots next to implementation, not after hardening - you want numerical
#   correctness confirmed before adding invariant assertions, otherwise you're
#   asserting wrong behavior.
# - Debugging is not a phase, it's a mode you enter when needed. But having the
#   methodology pre-loaded means you don't flail when something breaks.
# - Refactoring triggers are a periodic checkpoint, not a one-time pass.


# อออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออ
# PHASE 0: PROFILING & BENCHMARKING
# อออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออ
# Slot: BEFORE optimization work. After initial implementation runs correctly.
# Purpose: establish baselines, identify actual bottlenecks, measure changes.
# Rule: no optimization without a number before and after.

## Principle

Never optimize based on intuition. Measure, identify the actual bottleneck, change one thing, measure again. The data-oriented mindset applies to performance work too - look at what's actually happening, not what you think is happening.

## Workflow

1. **Establish a reproducible benchmark.**
   - Fixed input (deterministic seed, specific dataset/document).
   - Fixed iteration count (enough to be stable, few enough to be fast).
   - Wall-clock time via `time.perf_counter` (or language equivalent) around the hot loop.
   - Record: total time, per-phase time (forward, backward, optimizer), throughput (tokens/sec, steps/sec).

2. **Profile to find the bottleneck.**
   - **Time:** Where is wall-clock time spent? Instrument by phase first (coarse), then by function (fine).
   - **Memory:** Where do allocations happen? How much GC pressure?
   - **Allocation count:** How many objects are created per step? (This is often the real bottleneck in Python.)

3. **Record the baseline.** Before any change, write down:
   ```
   Benchmark: [description]
   Input: [seed, dataset, config]
   Steps: [N]
   Total time: [X]s
   Per-step: [Y]ms
   Phase breakdown: fwd [A]ms / bwd [B]ms / opt [C]ms
   Peak memory: [Z]MB
   ```

4. **Change one thing. Measure again.** Compare against baseline. If improvement < noise margin, revert.

5. **Keep a log.** Every optimization attempt, whether it worked or not, with numbers.

## Language-Specific Profiling Tools

### Python
```
"Python time.perf_counter for micro-benchmarking - avoiding measurement overhead"
"Python tracemalloc - tracking allocation count and peak memory per code section"
"Python cProfile - function-level call count and cumulative time"
"Python sys.getsizeof vs pympler.asizeof - measuring actual memory of nested structures"
"Python gc.get_stats - understanding garbage collection pressure"
```

### C99
```
"C99 clock_gettime CLOCK_MONOTONIC for benchmarking"
"Valgrind massif - heap profiling for C programs"
"perf stat - hardware counters, cache misses, branch mispredictions"
"Cachegrind - cache simulation for C programs"
```

### Zig
```
"Zig std.time.Timer for benchmarking"
"Zig GeneralPurposeAllocator - allocation tracking and leak detection"
"Zig tracy integration - frame-level profiling"
```

### R
```
"R system.time vs microbenchmark for reliable timing"
"R Rprof - function-level profiling"
"R profmem - memory allocation profiling"
"R lobstr::obj_size - actual memory footprint of R objects"
```

### Bash
```
"Bash time builtin vs /usr/bin/time -v for memory and timing"
"Bash set -x with PS4='+ $(date +%s%N) ' for per-line timing"
```

## Anti-Patterns
- Optimizing without a benchmark (you don't know if it helped).
- Optimizing the wrong thing (profile first).
- Optimizing past the point of diminishing returns (know your target).
- Changing two things at once (can't attribute the effect).


# อออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออ
# PHASE 2b: TESTING & VERIFICATION
# อออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออ
# Slot: DURING implementation. After each function stabilizes, before hardening.
# Purpose: confirm correctness of computation before asserting invariants.
# Rule: verify the math is right first. Then harden.

## Principle

Tests are input-output pairs. Pure functions (which the design phase maximizes) are trivially testable: known input  expected output. The purer the codebase, the less test infrastructure you need.

## Three Testing Layers

### 1. Numerical Verification (highest value for math-heavy code)

For any function that computes gradients, verify analytically-computed gradients against numerical finite-difference gradients.

**Method:**
```
For each parameter p:
  f(p + epsilon) - f(p - epsilon)
  ฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤ ๗ analytical gradient
            2 * epsilon
```

**Search prompts:**
```
"Numerical gradient checking - optimal epsilon value (typically 1e-5 to 1e-7)"
"Relative error vs absolute error for gradient checking - when to use which"
"Gradient checking for softmax cross-entropy - closed-form analytical gradient"
"Numerical stability of finite difference gradient check - double precision limits"
"Karpathy gradient check implementation - micrograd / makemore approach"
```

**What to check:**
- Every tape operation (`tape_add`, `tape_multiply`, `tape_power`, `tape_log`, `tape_exp`, `tape_relu`) individually.
- Full forward-backward pass on a tiny model (2-dim embedding, 1 head, 1 layer, 2-token sequence).
- Relative error should be < 1e-5 for each parameter.

### 2. Structural Verification

Confirm data structure contracts hold after operations. This overlaps with Phase 3 hardening but the goal here is catching bugs during development, not permanently guarding invariants.

**Lightweight checks run during development:**
- After `tape_append_node`: all four tape arrays same length.
- After full forward pass: KV cache sizes match expected positions.
- After backward: gradient of loss node is 1.0, all other grads have been accumulated.
- After Adam step: parameter count unchanged, no NaN/Inf values.

### 3. Regression Snapshots

After a known-good run:
- Save the loss at steps 1, 10, 50, 100, 500 (or whatever your schedule is).
- Save 3-5 inference samples with the same seed.
- Any future change must reproduce these exactly (deterministic seeding).

**Implementation:** A simple text file with expected values. Compare after each run. No framework needed.

**Search prompts:**
```
"Deterministic training reproducibility - sources of non-determinism in Python"
"Floating point reproducibility across Python versions - IEEE 754 guarantees"
```

## Testing Without Frameworks

No pytest, no unittest. Tests are plain functions that print PASS/FAIL:

```
def verify_[thing]():
    # setup known input
    # run function
    # compare against expected
    # print result
```

Run them at the bottom of the file during development, remove or gate behind a flag when done. Testing is a development activity, not a permanent artifact (assertions from Phase 3 are the permanent version).

## When to Write Tests

- After each pure function stabilizes (not before - the interface may change).
- Immediately when a bug is found (reproduce it as a test first, then fix).
- Before any optimization (the test confirms the optimization didn't break correctness).


# อออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออ
# PHASE 3b: STRATEGIC DEBUGGING
# อออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออ
# Slot: ON DEMAND. Enter this mode when something is wrong.
# Purpose: systematic methodology for finding bugs in data-oriented code.
# Rule: narrow by DATA first, then trace through code.

## Principle

In data-oriented code, bugs manifest as wrong values in arrays, not as wrong control flow. Debug by inspecting data, not by stepping through code. The flat, inspectable data layout you designed for performance is also your debugging advantage.

## Method: Bisect by Phase, Narrow by Data

### Step 1: Which phase is wrong?

The program has clear phase boundaries (setup  forward  backward  optimizer  output). Check the output of each phase boundary:

- **After forward:** Are logits reasonable? Are probabilities in (0,1) and sum to ~1?
- **After backward:** Is the loss gradient 1.0? Are parameter gradients non-zero and finite?
- **After optimizer:** Did parameters change? Are changes small and finite?

The first phase with wrong output contains the bug. Don't look further until you've localized.

### Step 2: Which data element is wrong?

Within the broken phase, don't read code - dump the arrays and find the first wrong element.

- For the tape: print `tape_data[start:end]` for the relevant section.
- For parameters: print the gradient norms per weight matrix (the `INSTRUMENT` block already does this).
- For attention: print attention weights. Are they uniform (undertrained) or spiked on one position (possible bug)?

### Step 3: Trace backward through the graph.

Once you've found a wrong value at index `i`:
- What are its children? `tape_children[i]`
- What are their values? `tape_data[child]` for each child.
- What are the local gradients? `tape_local_grads[i]`
- Are the children's values correct? If yes, the bug is in this node's operation. If no, recurse.

This is mechanical. The computation graph IS the debugger.

### Step 4: Golden-value test.

For the failing case, construct the smallest possible reproduction:
- 2-dim embedding, 1 head, 1 layer, 2-token sequence.
- Hand-compute expected values through each operation.
- Compare against actual.

**Search prompts for common failure modes:**
```
"NaN in neural network training - common causes and diagnosis"
"Exploding gradients - detection and typical sources"
"Softmax numerical instability - overflow and underflow patterns"
"Loss not decreasing - learning rate, gradient flow, initialization diagnosis"
"Attention weights all uniform - causes in transformer training"
```

## Debugging Utilities (build as needed, don't pre-build)

- `dump_tape_node(index)` - print data, grad, children, local_grads for one node.
- `trace_backward(index)` - recursively print the subgraph rooting at a node.
- `check_finite(array, name)` - scan for NaN/Inf, print first occurrence with index.
- `compare_gradients(analytical, numerical, name)` - print relative error per parameter.

Build these when you need them. They're debugging tools, not permanent infrastructure.

## When to Enter This Mode

- Loss is NaN or Inf.
- Loss doesn't decrease after 50+ steps.
- Inference produces garbage after training.
- Assertions from Phase 3 start failing.
- Numerical gradient check (Phase 2b) shows disagreement.


# อออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออ
# PHASE 4: REFACTORING TRIGGERS
# อออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออ
# Slot: PERIODIC review. Check after implementation stabilizes and
#       after any significant feature addition.
# Purpose: explicit criteria for structural changes. Decisions, not drift.

## Principle

The single-file, flat, explicit structure is the default. Deviation from it requires a concrete trigger - not "it feels messy" but a specific, articulable problem that refactoring solves. Every structural change has a cost (indirection, navigation overhead, import complexity). The trigger must outweigh the cost.

## Trigger: Split the File

**When:**
- File exceeds ~1000 lines AND has clearly separable sections with no interleaved dependencies.
- Two people need to work on different sections simultaneously.
- Compile time becomes a bottleneck (C99/Zig - not relevant for Python/R/Bash).

**How:**
- Split along phase boundaries (data model, forward pass, backward pass, optimizer, inference, tests).
- Each file should be independently understandable. No circular imports.
- Shared data structures and constants go in one file that others import.

**Do NOT split** just because the file is long. Length without confusion is fine.

## Trigger: Extract a Function

**When:**
- The same sequence of operations appears 3+ times AND has identical structure (not just superficial similarity).
- A gatekeeper invariant needs enforcement and the enforcement logic is non-trivial.

**Do NOT extract** for two occurrences. Two is coincidence. Three is a pattern.

## Trigger: Merge Separated Code Paths

**When:**
- A bug fix must be applied to both paths and you forgot one (the duplication caused a real bug, not a hypothetical one).
- The paths have converged to be structurally identical except for types.

**Do NOT merge** preemptively. The performance and clarity benefits of separation are real.

## Trigger: Introduce Abstraction (struct, named tuple, type alias)

**When:**
- A group of parallel arrays is passed together to 4+ functions and every caller must remember the same bundling order.
- An offset table entry's interpretation requires documentation that could be replaced by named fields.

**Do NOT abstract** to "make it cleaner." Abstract to prevent a specific class of bug.

## Trigger: Move from Development to Production Structure

**When:**
- The algorithm is stable (no structural changes in N sessions).
- Other code needs to import and use it.
- It needs packaging, distribution, or deployment.

**How:**
- Add `if __name__ == '__main__'` guard.
- Extract public API functions.
- Add proper error handling (not just assertions) for external inputs.
- Keep internal structure unchanged - the flat, explicit style is the production code. Don't "clean it up" into classes unless a trigger above fires.

## Review Checklist (periodic)

Run through these questions after any significant change:

1. Is any section of the file confusing WITHOUT being complex? (Confusion from inherent algorithmic complexity is fine. Confusion from structural messiness is a trigger.)
2. Has any duplication caused a real bug? (Not "could cause" - HAS caused.)
3. Is any function doing two unrelated things? (Split it.)
4. Is any data being passed through functions that don't use it? (Reorganize the data, not the functions.)
5. Are there more than 3 global mutable variables? (Consider whether gatekeeper functions cover all of them.)
