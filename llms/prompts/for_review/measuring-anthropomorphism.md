# Metrics for Comparing Anthropomorphic vs. Data-Oriented Technical Abstracts

## 1. Classical Readability (surface complexity)

These will favor the original, which is the point - they measure the wrong thing for this comparison.

| Metric | What it measures | Expected result |
|---|---|---|
| Flesch-Kincaid Grade Level | Sentence length + syllable count | Original scores "easier" |
| Gunning Fog Index | Sentence length + complex word % | Original scores "easier" |
| Coleman-Liau Index | Character count per word/sentence | Likely similar |
| Dale-Chall | Proportion of "unfamiliar" words | Dereified scores harder (more technical terms) |
| Type-Token Ratio | Lexical diversity | Dereified likely higher (less term reuse) |

**Limitation**: These metrics treat all words as equally interpretable. "Agent" and "array" get the same score, but "agent" carries massive hidden ambiguity. These metrics measure reading difficulty, not understanding difficulty.

## 2. Structural / Syntactic Complexity (parse-level)

| Metric | What it measures | How to compute |
|---|---|---|
| Dependency distance | Mean distance between syntactically related words in parse tree | spaCy/Stanza dependency parse, compute mean arc length |
| Proposition density | Number of distinct predicate-argument structures per sentence | Semantic role labeling (AllenNLP SRL) |
| Clausal embedding depth | Max depth of subordinate clauses | Constituency parse, measure tree depth |
| Sentence length variance | Consistency of sentence complexity | Standard deviation of token counts per sentence |
| Noun phrase complexity | Mean modifier count per NP | Parse tree NP extraction, count dependents |

**What these capture**: Processing difficulty at the syntactic level. The dereified version likely has higher proposition density (more claims per sentence) but possibly lower embedding depth (more direct predication, less nominalization).

## 3. Semantic / Referential Analysis (meaning-level)

These are the most diagnostic for the question you're actually asking.

| Metric | What it measures | How to compute |
|---|---|---|
| Referential ambiguity | Number of terms with multiple possible computational referents | Manual annotation or LLM-based: for each technical term, ask "how many distinct implementations could this refer to?" |
| Concreteness rating | Mean concreteness of content words | MRC Psycholinguistic Database concreteness norms, or Brysbaert et al. (2014) concreteness ratings |
| Semantic specificity | How narrowly each term constrains interpretation | Embedding neighborhood size: embed each technical term, count how many other terms fall within radius r |
| Cohesive harmony | Whether adjacent sentences share referents that are the same kind of object | Coh-Metrix referential cohesion indices |
| Nominalization density | Proportion of verbs converted to nouns ("orchestration" vs "route calls") | POS tag ratio: count nouns derived from verbs (suffix heuristics: -tion, -ment, -ance, -ity) |
| Metaphor density | Proportion of terms used non-literally | Manual annotation or LLM-based detection: "is this term used literally or metaphorically in context?" |

**Key metric - Referential ambiguity**: This is the one that most directly measures what we've been discussing. "Agent" can refer to many different computational structures. "Generation-call loop" refers to one thing. You could operationalize this by asking an LLM: "Given only this sentence, describe the concrete data structures and operations involved" - and measuring response variance across multiple samples. High variance = high ambiguity.

## 4. LLM-Based Assessment (pragmatic-level)

These use language models as measurement instruments.

| Metric | What it measures | Method |
|---|---|---|
| Implementation convergence | Whether the text constrains implementation to a narrow set of designs | Give each abstract to N LLM instances, ask each to produce pseudocode. Measure pairwise similarity of outputs. Higher similarity = more constrained/concrete description. |
| Paraphrase stability | Whether meaning is preserved under rephrasing | Generate K paraphrases per abstract, embed all, measure cluster tightness. Tight cluster = stable meaning. Diffuse cluster = ambiguous source. |
| Information extraction precision | Whether concrete system details can be recovered | Ask: "List every data structure, function, and data transformation described." Score completeness and specificity of answers. |
| Comprehension probe accuracy | Whether readers actually understood the mechanism | Ask targeted questions: "What is the input to the routing component? What data type? What determines the output?" Measure answer correctness. |
| Clarification question type | What kind of confusion each generates | Generate questions a reader might ask. Classify as: clarification ("what does X mean?"), specification ("what specifically happens at step Y?"), or extension ("could this also handle Z?"). Anthropomorphic version should generate more clarification/specification. Dereified should generate more extension. |
| Jargon dependency | How much domain-specific knowledge is presupposed | Ask an LLM with no ML background context to explain each abstract. Measure how much it confabulates vs. admits confusion. Confabulation = the jargon gave false confidence. |

## 5. Information-Theoretic (signal-level)

| Metric | What it measures | Method |
|---|---|---|
| Token-level surprisal | How predictable each token is given context | Run through a language model, extract per-token log-probabilities. High mean surprisal = more informative (or more unusual). |
| Entropy rate | Information density | Mean entropy over sliding context windows |
| Compression ratio | Redundancy | gzip or LLM-based compression. Lower ratio = more redundant |
| Mutual information between sentences | How much each sentence constrains interpretation of the next | Compute pointwise MI between adjacent sentence embeddings |

## Recommended Priority

For the specific question "which version communicates the actual system more faithfully":

1. **Implementation convergence** (LLM-based) - most direct measure of descriptive precision
2. **Referential ambiguity** (semantic) - directly measures the gap we're hypothesizing
3. **Paraphrase stability** (LLM-based) - proxy for meaning determinacy
4. **Metaphor density** (semantic) - quantifies how much figurative language is doing load-bearing work
5. **Comprehension probe accuracy** (LLM-based) - measures actual understanding vs. felt understanding
