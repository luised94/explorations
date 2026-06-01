# Characteristic Numbers: Data-Oriented Programming
*A numerical landmarks reference - analogous to BioNumbers but for hardware-aware systems*
*Informed by: Acton, Carmack, Muratori, Blow, Sutherland, Ritchie, Pike*

---

## Ask These First (Before Looking at Any Numbers)
*- Synthesized from Acton, Pike, Sutherland*

These questions run before any hardware consideration. Wrong answers here make the numbers below irrelevant.

1. **What is the actual data?** Not the abstraction - the bytes. What fields exist, how large, how many instances?
2. **What is the access pattern?** Which fields are read together? How often? In what order?
3. **Is this the right representation?** Does the data structure match the mathematical structure of the problem? Could a different encoding (coordinates, compression, quantization) eliminate the expensive operation entirely?
4. **What transforms does it undergo?** Are they pure (input  output, no side effects)? Can they be batched?
5. **Where is the heat?** If you don't know, measure before restructuring. If you can reason about it from the access pattern, do that first - then verify.

> *"If you don't understand the data, you don't understand the problem."* - Acton  
> *"Data dominates. The right structure makes the algorithm self-evident."* - Pike  
> *"The right representation can make the algorithm trivial."* - Sutherland

---

## Axis 0: Problem Representation & Encoding
*New axis - Sutherland, Pike, Blow*

The choice of representation multiplies or divides every cost below. Make this decision before layout.

| Representation choice | Effect |
|---|---|
| Float32 where int16 suffices | 2x wasted bandwidth, 2x wasted cache |
| Float64 where float32 suffices | 2x wasted bandwidth; rarely justified in real-time |
| AoS where only 2 of 6 fields are hot | 3x wasted cache bandwidth on hot path |
| World-space coords where local-space is stable | Precision loss + no opportunity for SIMD coherence |
| Sparse index + dense values vs. dense array with holes | Scatter/gather cost vs. wasted memory - problem-dependent |
| Normalized/quantized (e.g., 10-bit normals) | 3-4x size reduction; GPU-native in many cases |
| Symbolic / enum where a float is used | Enables perfect switch prediction, smaller storage |
| Sorted order where unsorted is used | Enables binary search (O(log n) vs O(n)), SIMD-friendly scans |

**Landmark**: A suboptimal encoding can waste more bandwidth than a suboptimal layout. Fix encoding first, layout second.

**Code smell**: Using `float` for a field that is always 0.0, 0.5, or 1.0. Using `std::string` for a field that has ó 16 known values. Using a pointer where an index would be smaller and more cache-friendly.

---

## Axis 1: Memory Hierarchy - Latency

| Level | Latency (cycles) | Latency (ns) | Size (typical) |
|---|---|---|---|
| Register | ~1 | ~0.3 ns | 16-32 registers |
| L1 cache | ~4 | ~1 ns | 32-64 KB |
| L2 cache | ~12 | ~4 ns | 256 KB - 1 MB |
| L3 cache | ~40 | ~13 ns | 8-32 MB |
| DRAM | ~150-200 | ~60-80 ns | GBs |
| NVMe SSD | ~50,000 | ~10-100 æs | TBs |
| Network (LAN) | ~3,000,000 | ~1 ms | - |
| Network (WAN) | ~300,000,000 | ~100 ms | - |

**Landmark ratio**: L1DRAM ÷ 50x. DRAMNVMe ÷ 500x. One pointer chase missing L1 = ~50 float multiplications wasted.

**Code smell** *(Muratori)*: A loop that dereferences a pointer on every iteration. A virtual dispatch inside a hot loop. A `std::list` traversal. Any of these will show as DRAM latency on a profiler, not as algorithmic inefficiency.

---

## Axis 2: Memory Hierarchy - Bandwidth

| Level | Bandwidth |
|---|---|
| L1  CPU | ~1-2 TB/s |
| L2  CPU | ~500 GB/s |
| L3  CPU | ~200 GB/s |
| DRAM  CPU | ~50-100 GB/s (DDR5) |
| NVMe SSD | ~5-7 GB/s (PCIe 4.0) |
| SATA SSD | ~500 MB/s |
| GigE | ~125 MB/s |
| 100 GbE | ~12.5 GB/s |
| PCIe 4.0 x16 (GPUCPU) | ~32 GB/s |
| GPU HBM (internal) | ~1-3 TB/s |

**Landmark**: At ~50 GB/s DRAM bandwidth, a float32-per-element pass over 1 GB of data takes ~20 ms. If you need 60 fps (16.6 ms/frame), one full-memory pass is your entire frame budget. This number should be tattooed somewhere visible.

**Unix parallel** *(Ritchie)*: The pipe's power is that it forces sequential stream access - which is exactly what the prefetcher needs. Stream-oriented design is not just a Unix aesthetic; it's a bandwidth optimization.

---

## Axis 3: Data Layout - Sizes

| Unit | Size | Notes |
|---|---|---|
| bool (stored) | 1 byte | 1 bit logical, 1 byte typical |
| uint8 / char | 1 byte | |
| int16 / float16 | 2 bytes | ML inference, audio, quantized normals |
| int32 / float32 | 4 bytes | **Most common compute unit** |
| int64 / float64 / pointer | 8 bytes | 64-bit pointer = 8 bytes |
| SIMD register (SSE) | 16 bytes | 4x float32 |
| SIMD register (AVX2) | 32 bytes | 8x float32 |
| Cache line | **64 bytes** | **Universal unit of memory transfer** |
| SIMD register (AVX-512) | 64 bytes | = exactly 1 cache line |
| Page (small) | 4 KB | OS virtual memory unit |
| Page (huge) | 2 MB | TLB-friendly for large arrays |
| L1-resident dataset | < 32 KB | Hot loop target |
| L3-resident dataset | < 16-32 MB | |
| Memory-bound dataset | > 100 MB | Bandwidth-limited, not compute-limited |

**Landmark**: If your struct > 64 bytes, one object = multiple cache line fetches. If your hot fields ó 16 bytes, 4 objects share a cache line.

**Hot/cold split** *(Acton)*: Separate fields touched every frame (position, flags, health) from rarely-touched fields (name, backstory, spawn parameters) into different arrays. You double effective cache capacity for the hot path at zero algorithmic cost.

---

## Axis 4: Transform Purity
*New axis - Carmack, Ritchie*

How pure is this transform? Purity determines parallelism options, testability, cacheability, and architectural flexibility.

| Purity level | Description | Parallelism | Testable in isolation? |
|---|---|---|---|
| **Pure** | f(input)  output, no side effects, no shared state | û Embarrassingly parallel | û Yes |
| **Read-only side input** | f(input, const config)  output | û Parallel | û Yes |
| **Accumulate** | Writes to shared output (e.g., counters, histograms) | û With atomics or reduction | Partial |
| **Stateful** | Transform depends on internal state (e.g., filters, RNG) | ? Sequential or partitioned | Partial |
| **Side-effecting** | Writes to external state (DB, filesystem, globals) | ? No | ? Hard |

**Landmark**: Pure transforms compose freely - you can pipeline them, reorder them, cache their outputs, move them to a GPU or another thread. Each step toward impurity costs you one or more of those options.

**Design heuristic** *(Carmack)*: Write transforms pure by default. Introduce state only when the problem actually requires it, not for convenience. If a transform needs to be stateful, isolate the state explicitly rather than letting it leak.

**Code smell**: A "transform" function that also logs, allocates, or modifies a global. Purity violations compound - one impure stage prevents parallelism for all stages that depend on it.

---

## Axis 5: Transformation Types - Memory Access Profile

| Type | Access Pattern | Prefetcher? | Parallelizable? | Relative cost |
|---|---|---|---|---|
| Map | Seq R + Seq W | û Yes | û Embarrassingly | Low |
| Filter/Compaction | Seq R + irregular W | Partial | û via prefix scan | Low-Med |
| Reduce | Seq R + scalar W | û Yes | û tree reduction | Low |
| Scatter | Seq R + random W | ? No | ? write conflicts | **High** |
| Gather | Random R + Seq W | ? No | û reads safe | **High** |
| Sort | Complex mixed | Partial | û parallel sorts | Med-High |
| Prefix scan | Seq, data-dependent | û Yes | û work-efficient | Med |
| Stencil | Strided R + Seq W | Partial | û with halos | Med |

**Landmark**: Scatter/gather = random memory access = ~150 cycle misses per element. Restructuring data to convert scatter/gather into sequential access is often the single highest-leverage optimization available.

**Muratori's heuristic**: Write the direct version first. Run it. If scatter/gather shows up as the bottleneck in profiling, *then* consider restructuring. Don't anticipate it into your design blindly.

---

## Axis 6: Operation Costs

| Operation | Cost (cycles) | Notes |
|---|---|---|
| Integer add/mul | 1-3 | Pipelined |
| Float mul (scalar) | 3-5 | |
| Float div (scalar) | 10-20 | Avoid in hot loops |
| SIMD mul (AVX2) | 3-5 | 8x throughput |
| Branch (predicted) | ~0 | |
| Branch (mispredicted) | ~15-20 | Pipeline flush |
| L1 / L2 / L3 / DRAM | 4 / 12 / 40 / 150-200 | (see Axis 1) |
| Atomic CAS (uncontended) | ~10-20 | |
| Mutex (uncontended) | ~20-50 | |
| Mutex (contested) | ~500-5,000 | High variance |
| System call | ~1,000-5,000 | |
| Context switch | ~10,000-50,000 | |
| `malloc` (typical) | ~1,000-10,000 | Lock + bookkeeping |
| Arena alloc | ~1-5 | Pointer bump only |
| Virtual dispatch (cold) | ~150-200 | Effectively a cache miss |

**Landmark**: A single DRAM miss ÷ 50 float multiplications. A contested mutex ÷ 25 DRAM misses. Arena allocation is ~1000x cheaper than malloc in the hot path. These ratios are the grammar of performance reasoning.

**Ritchie's note**: Every abstraction layer has a cost. C's model was: you see what you get, no hidden allocations, no hidden dispatch. When your "clean abstraction" hides malloc or virtual dispatch in a hot path, you've paid a tax that doesn't appear in code review.

---

## Axis 7: Flow Topology

| Topology | Graph type | Parallelism | Latency | Use case |
|---|---|---|---|---|
| Linear chain | DAG (degenerate) | ? Sequential | Additive | Simple pipeline |
| Tree (fan-out) | DAG | û Subtrees | Log depth | Broadcast, LOD |
| DAG (general) | DAG | û Off critical path | Critical path | Render graphs, task graphs |
| Cyclic | General | ? Bounded | Iterative | Simulation, feedback control |

**Multiplicity patterns** (orthogonal to topology):

| Pattern | Streams | Use case |
|---|---|---|
| Transform | 1  1 | Map, normalize |
| Merge / Join | N  1 | Synchronization barrier |
| Split / Route | 1  N | Demux, conditional |
| Reduce | N elements  1 | Sum, max |
| Broadcast | 1  N copies | Fan-out |
| Feedback | Output  Input | Iterative refinement |

**Landmark**: DAG critical path = minimum latency regardless of parallelism. Optimize the critical path first; parallelize everything else. Unbounded queues + fast producer = memory explosion - always bound queue depth explicitly.

---

## Axis 8: Synchrony - Push vs Pull

| Model | Latency | Throughput | Back-pressure | Use case |
|---|---|---|---|---|
| Synchronous blocking | Lowest | Lower | Natural | Sequential pipelines |
| Async push | Low | High | Manual (bound queues) | Event streams, I/O |
| Async pull (lazy) | Higher | High | Natural | Iterators, generators |
| Tick/clock-driven | Fixed interval | Predictable | N/A | Game loops, simulation |
| Reactive / dataflow | Low | High | Operator-driven | Signal processing |

**Landmark**: Push without back-pressure buffers unboundedly when producer > consumer. Size your queues as N x element_size deliberately. This is a design decision, not an implementation detail.

---

## Axis 9: Ownership & Concurrency

| Model | Alloc cost | Sync cost | Aliasing | Parallelism |
|---|---|---|---|---|
| Single owner, exclusive | ~1 (stack) | ~0 | None | Sequential |
| Immutable shared | Varies | ~0 reads | Read-only | û Full |
| Scoped borrow / view | ~0 | ~0 | Controlled | û |
| Atomic RMW | Varies | ~10-40 cycles | None | û Lock-free |
| Mutex | Varies | ~20-5,000 cycles | None (locked) | ? Serialized |
| Arena-owned | ~1-5 cycles | ~0 (if single-threaded) | None | û read-only after fill |
| GC-managed | Unpredictable | Unpredictable | Graph | Partial |

**Landmark**: Shared mutable state is the bottleneck in concurrent systems. A contended mutex (~1,000 cycles) ÷ 7 DRAM accesses ÷ 200 float multiplications. The cost is not the lock itself - it's the contention, serialization, and cache invalidation.

---

## Axis 10: Cardinality

| Type | N | Technique |
|---|---|---|
| 1:1 (map) | 1 | Linear, trivially parallel |
| 1:few | 2-4 | Inline, unroll |
| 1:many (expand) | 8-1M | Output buffer must be pre-sized |
| 1:broadcast | 1,000+ | Explicit fan-out layer needed |
| N:1 (reduce), small | < 16 | Scalar tree reduction |
| N:1 (reduce), SIMD | 8-16 | Horizontal SIMD ops |
| N:1 (reduce), large | 1M+ | Parallel prefix scan |
| N:M compression | M ® N | Index structure needed (sparse) |
| N:M expansion | M ¯ N | Budget output memory explicitly |

---

## Axis 11: Developer Loop Costs
*New axis - Blow*

Ignored in most performance literature, but these costs bound the rate at which all other knowledge can be applied.

| Operation | Typical cost | Fast | Slow |
|---|---|---|---|
| Compile (incremental) | 1-30 s | < 2 s | > 15 s |
| Compile (full rebuild) | 10 s - 20 min | < 30 s | > 5 min |
| Test run (unit) | ms - seconds | < 1 s | > 10 s |
| Profiler attach + capture | 5-30 s | < 10 s | > 1 min |
| Hot reload / live edit | 0-5 s | < 1 s | N/A |
| Debugger step through hot path | 1-30 min | < 5 min | hours |

**Blow's principle**: A 30-second build loop means you run ~120 experiments per hour. A 2-second loop means ~1,800. That 15x multiplier compounds over days and weeks. Build time is not a comfort issue - it's a productivity order-of-magnitude issue.

**Practical targets**: Keep incremental builds under 2 seconds. Keep hot-path profiling under 10 seconds from "I wonder if..." to data on screen. If either is violated, fix it before optimizing anything else.

---

## The "Is This Fast?" Heuristic
*Muratori's compression: five questions before profiling*

1. **Right representation?** Does the encoding match the problem's actual precision/range needs?
2. **Sequential access?** Random > strided > sequential. Sequential is always fastest.
3. **Hot data fits in cache?** < 32 KB for L1-hot, < 32 MB for L3-warm.
4. **Pure transform?** Impure = lost parallelism, lost caching, lost composability.
5. **Sync cost proportional to work?** Never take a 1,000-cycle mutex for a 3-cycle add.

If all five are yes: you are doing well. If any is no: you have found your work.

---

## Sequencing: When to Use This Reference

| Stage | What to do | This artifact's role |
|---|---|---|
| **Design** | Choose representation, define transforms | Axis 0, 4, 7 |
| **First implementation** | Write the obvious direct thing | Don't optimize yet |
| **Measure** | Profile to find actual heat | Validate assumptions |
| **Optimize** | Apply layout/access/purity fixes | Axes 1-6, 8-10 |
| **Tooling** | Keep build loop fast throughout | Axis 11 |

> *"Compression-oriented: don't abstract until you've seen the pattern. Don't optimize until you've seen the heat."* - Muratori  
> *"The numbers are priors, not certainties. Profile to confirm."* - Carmack

---

*Reference values: modern x86 (Intel/AMD, ~2020-2025). ARM differs modestly; GPU differs significantly on bandwidth and parallelism.*
