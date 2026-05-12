Here are the irreducible components of the data-oriented programmer persona-the indivisible, atomic truths, habits, and heuristics that collectively define it. Each is a self-contained statement; none can be split without losing essential meaning.

---

### Core Axioms (truths about data and systems)

1. **Plain text is the only archival format.**  
   Binary formats and proprietary databases are non-negotiable liabilities for long-term access.

2. **Metadata lives inside the file it describes.**  
   The authoritative source of title, tags, and dates is embedded in the same document, not in an external database.

3. **The file on disk is the source of truth.**  
   All indexes, caches, and views are derived from it and can be discarded without data loss.

4. **Derived artifacts are always disposable and rebuildable.**  
   If you cannot `rm -rf` the cache and regenerate it from sources in under a minute, the design is wrong.

5. **Data flows as text streams between small programs.**  
   The unit of communication is a stream of lines or records, never a complex object graph.

---

### Foundational Design Principles

6. **Build only when friction is felt.**  
   Functional need, not speculation, drives every feature. The system asks for its own expansions.

7. **Measure before you optimize, visualize before you fix.**  
   Heatmaps, failure logs, and edit-cadence graphs are the only admissible evidence for a change.

8. **Compose, don't aggregate.**  
   Complex behavior is achieved by piping simple filters, not by adding code to a monolithic tool.

9. **Graceful degradation is mandatory.**  
   When metadata is missing, the index is down, or discipline slips, the system must remain partially useful-soft failure, never silent death.

10. **Errors must be loud and cheap to fix.**  
    A dead-metadata log visited once a week costs nothing; a silent fallback that hides problems ultimately destroys trust.

11. **Human discipline always decays; automate the hook, make the failure visible.**  
    Use `new` commands, templates, and capture prompts. When they're skipped, log it and review regularly.

---

### Invariant Practices

12. **Every content file starts with a timestamp and a structured header.**  
    Title, tags, date, and optional links are the minimum machine-readable front matter.

13. **A single extraction script converts all files into a uniform TSV stream.**  
    The stream is the bridge: it abstracts file format differences into a canonical record shape.

14. **SQLite FTS5 is the only cache you need for full-text search.**  
    It is stable, rebuildable, and its schema mirrors the header fields exactly.

15. **Retrieval is a shell function: query  candidate paths  `fzf`  `nvim`.**  
    The human makes the final selection; the machine narrows the field.

16. **The query "language" is never formalized; it remains a set of pipeline conventions.**  
    `tag:foo bar` is pattern-matched in the shell function, everything else is chained `grep`, `rg`, `awk`, and one-off Python.

17. **Spaced repetition schedules insight review, not rote memorization.**  
    Cards link back to the source note; a failed recall triggers re-derivation, not passive re-reading.

18. **The card deck is a TSV file; the scheduler is SM-2 in < 50 lines of Python.**  
    No external app, no opaque database, no sync.

19. **Zettelkasten is implemented as a flat directory of timestamp-slug files with manual `links:` in front matter.**  
    Dead-link checking and a `redirects.txt` file are the only maintenance tools.

20. **Non-text artifacts (PDFs, images) are converted to text via one-line adapters.**  
    The indexer never knows the difference; the corpus stays pure text.

---

### Posture Toward Time and Entropy

21. **Longevity is the overriding non-functional requirement.**  
    Every decision is tested against: "Will this still work after a year of neglect, an OS upgrade, and my own forgetfulness?"

22. **Neglect is the default state; the system must survive it.**  
    Deliberately stop maintaining it for a month-if retrieval breaks, the design fails.

23. **Tools are pruned when unused.**  
    A script in `~/bin` that hasn't run in a year gets deleted. The survivors earn their place.

24. **Rituals, not willpower, sustain the system.**  
    Monday coffee + dead-metadata log, random note every morning, quarterly script review-these are the only guarantees of consistency.

---

### Rules of Collaboration (with Self and Others)

25. **When designing a format for a domain expert, observe their existing shorthand and embed it directly.**  
    The format must be their language, not a translation.

26. **Enforce exactly one structural rule on custom formats: every record is mechanically separable.**  
    One line, one blank-line gap, or a timestamp-anything that lets a splitter work reliably.

27. **The parser tolerates ambiguity, logs misfits, and asks the human "what did you mean?"**  
    Perfection is not the goal; low-friction iteration is.

28. **Format migrations happen silently in the extraction pipeline, not in the user's face.**  
    Old entries are gracefully converted during a rebuild; the expert never sees a version number.

---

### The Deepest Heuristics

29. **The tool must be an exoskeleton for memory, not a passive store.**  
    It extends associative recall; retrieval is a conversation with your past self.

30. **Serendipity is a muscle that must be exercised.**  
    Random note encounters, cross-domain prompts, and daily one-liners keep it alive.

31. **The ultimate test: hand a one-page README to a friend and ask them to find a specific note.**  
    If they cannot, the system is too personal-acceptable, but an acknowledged risk.

32. **If you're polishing the indexer more than you're using it, stop.**  
    The system exists to free you for real work, not to become the work.

---

These components are the periodic table of the data-oriented programmer. Combine them to generate every habit, design choice, and story you heard in the lecture. Use them as a checklist when evaluating a new tool, or as a scaffold when building your own.
