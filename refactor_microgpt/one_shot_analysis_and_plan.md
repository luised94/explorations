# Data-Oriented Transformation of a Minimal GPT

## Context

You are given a pure-Python GPT implementation (the ORIGINAL SCRIPT below). It trains a character-level GPT on a dataset of names and generates new ones. The code is intentionally minimal and pedagogical - written by Andrej Karpathy to demonstrate that the entire GPT algorithm fits in a single dependency-free Python file.

Your job is to produce a transformation plan that restructures this script from its current mixed OOP/functional style into a data-oriented style, then refine that plan through expert review. The plan will later be implemented one commit at a time in a follow-up conversation.

---

## Programming Paradigm

This refactor targets **procedural, data-oriented Python**. The organizing principle is: functions transform data that is passed to them explicitly.

- **No classes.** No `class` keyword anywhere in the final codebase. Data is organized in plain containers - flat lists, tuples, dicts used as named record stores - not objects with methods.
- **No hidden state.** Every function receives its inputs as arguments and returns its outputs. No reading from or writing to module-level mutable state inside functions. Module-level constants (hyperparameters, configuration) are acceptable.
- **No method dispatch.** No operator overloading, no dunder methods, no polymorphism. Operations are explicit function calls.
- **Data and functions are separate.** Data is declared and laid out in one place. Functions that transform that data are defined separately. They do not own, encapsulate, or "belong to" the data.

## Code Style Invariants

Every step of the plan - and every future commit implementing it - must respect these constraints:

- **Full descriptive names.** No abbreviations. `activation_data` not `act_data`, `layer_index` not `li`, `head_dimension` not `head_dim`. Names should read as plain English.
- **Type hints on all function signatures and major bindings.** Use `list[float]`, `tuple[int, int, int]`, etc. Introduce `TypeAlias` for recurring compound types if it aids clarity.
- **Prefer explicit `for` loops over list comprehensions** unless the comprehension is a trivial one-line mapping with no readability cost. If a reader has to scan horizontally or parse nested logic, use a loop.
- **One operation per line in hot paths.** No stacked or chained method calls. Each line should do one legible thing.
- **No clever tricks.** If a reader has to pause to understand an expression, it should be rewritten. Favor obviousness over concision.
- **Explicit control flow.** Avoid relying on short-circuit evaluation, ternary nesting, or implicit truthiness for logic that matters.
- **Use Python's standard vocabulary where it is paradigm-neutral.** `enumerate`, `zip`, `range`, `f-strings`, `math` and `random` standard library - these are fine. They are syntax and utilities, not paradigm commitments.
- **Avoid Python idioms that smuggle in abstraction.** No generators as lazy pipelines, no context managers for control flow, no decorators, no `__dunder__` anything. If a Python feature exists to hide mechanism, don't use it here.

These invariants apply from the first commit forward. They are non-negotiable and should not be deferred to a cleanup pass.

---

## Phase 1: Establish the DOD Lens

Reflect on data-oriented design as a strategy for restructuring this specific codebase. Ground your thinking in Mike Acton's core principles:

- **"The purpose of all programs, and all parts of those programs, is to transform data from one form to another."** Identify what the actual data transformations are in this script. What bytes go in, what bytes come out, and what are the intermediate representations?
- **"If you don't understand the data, you don't understand the problem."** Characterize the data: its shape, its lifetime, its access patterns, its hot paths vs. cold paths. Where does the script hide data layout decisions behind abstractions (like the `Value` class)?
- **"Where there is one, there are many."** Find where the script processes many homogeneous items but structures them as individual objects with per-item overhead. Where are the arrays-of-structs that should be structs-of-arrays?
- **Solve for the common case.** What does this program spend almost all of its time doing? What data does the hot loop actually touch?

Do not prescribe solutions yet. Build a clear picture of the data reality underneath the current code.

## Phase 2: Analyze the Script Through That Lens

Walk through the script's major regions and identify, for each, the tension between its current structure and DOD principles:

1. **Tokenizer / data loading** - What is the data, how is it stored, how is it accessed?
2. **`Value` class / autograd** - What problem does it solve, what data layout does it impose, and what is the cost of that layout?
3. **Parameter initialization (`state_dict`)** - How is model state organized vs. how it is accessed during forward/backward?
4. **Forward pass (`gpt()` function and helpers)** - What are the actual compute kernels? What data do they read and write?
5. **Loss computation and backward pass** - What is the access pattern over the computation graph?
6. **Optimizer (Adam update)** - What parallel arrays exist, and how are they traversed?
7. **Inference loop** - How does it differ from training in data access?

For each region, note: what data is being transformed, what the access pattern is, what indirection or per-element overhead exists, and what a DOD restructuring would prioritize.

## Phase 3: Generate the Transformation Plan

Produce a numbered sequence of atomic transformation steps. Each step simulates a single git commit - a minimal, self-contained edit that moves the codebase toward data-oriented style.

**Constraints on each step:**
- One to two sentences only. Use precise, domain-specific language (e.g., "flatten," "separate," "hoist," "inline," "replace indirection with offset," "convert AoS to SoA").
- Describe the *what* and *why* of the edit, not the code.
- Each step must leave the program functionally equivalent - output remains identical.
- Steps are ordered by dependency: later steps may depend on earlier ones, never the reverse.
- Group steps under labeled phases if natural groupings emerge.
- Each step must conform to the Code Style Invariants above. If a step introduces new functions or variables, the commit description should use the full descriptive names that will appear in the code.

**Do not write any code.** The output of this phase is the plan, not the implementation.

## Phase 4: Expert Review and Refinement

After generating the plan, simulate a single round of review from three experts. Each expert reads the full plan from Phase 3 and provides brief, pointed feedback - not a rewrite, but specific critiques, reorderings, or missing steps. The experts are:

**Mike Acton** (Data-Oriented Design, Insomniac/Unity)
Focus: Are the data layout decisions correct? Does the plan actually solve for the real access patterns, or does it just reorganize abstractions? Does any step introduce indirection or allocation that shouldn't be there? Is the hot path truly flat and linear by the end?

**John Carmack** (id Software, Oculus, practical engineering clarity)
Focus: Is the plan pragmatic? Are there steps that add complexity without measurable benefit in this context (pure Python, pedagogical, tiny model)? Is the code going to be *simpler* and more readable at the end, or just differently complex? Would he cut or merge any steps?

**Casey Muratori** (Handmade Hero, compression-oriented programming)
Focus: Does the plan follow a natural compression sequence - start with the straightforward version, then compress repeated patterns? Are there steps that prematurely abstract or over-structure? Should any steps be deferred because the pattern hasn't been proven yet?

After the three reviews, produce a **revised plan** that incorporates the feedback. Annotate any changes with a brief note indicating which reviewer's feedback motivated the change.

---

## Implementation Protocol

*This section is not executed as part of the prompt above. It defines how the plan will be carried out in a follow-up conversation.*

When implementing the revised plan, respond as a single developer working through the commits. Each response corresponds to one commit and contains:

1. **Commit message** - imperative mood, one line, matching the plan step (e.g., `Flatten parameter storage into contiguous float arrays with offset table`).
2. **The full updated script** - complete file, not a diff. Every commit is a runnable program.
3. **Sanity check** - one line confirming the program still produces equivalent output, or noting any expected change (e.g., "Output identical. No functional change.").

No commentary outside this frame. The commit message *is* the explanation.

---

## ORIGINAL SCRIPT

```python
"""
The most atomic way to train and inference a GPT in pure, dependency-free Python.
This file is the complete algorithm.
Everything else is just efficiency.

@karpathy
"""

import os       # os.path.exists
import math     # math.log, math.exp
import random   # random.seed, random.choices, random.gauss, random.shuffle
random.seed(42) # Let there be order among chaos

# Let there be an input dataset `docs`: list[str] of documents (e.g. a dataset of names)
if not os.path.exists('input.txt'):
    import urllib.request
    names_url = 'https://raw.githubusercontent.com/karpathy/makemore/refs/heads/master/names.txt'
    urllib.request.urlretrieve(names_url, 'input.txt')
docs = [l.strip() for l in open('input.txt').read().strip().split('\n') if l.strip()] # list[str] of documents
random.shuffle(docs)
print(f"num docs: {len(docs)}")

# Let there be a Tokenizer to translate strings to discrete symbols and back
uchars = sorted(set(''.join(docs))) # unique characters in the dataset become token ids 0..n-1
BOS = len(uchars) # token id for the special Beginning of Sequence (BOS) token
vocab_size = len(uchars) + 1 # total number of unique tokens, +1 is for BOS
print(f"vocab size: {vocab_size}")

# Let there be an Autograd to apply the chain rule recursively across a computation graph
class Value:
    """Stores a single scalar value and its gradient, as a node in a computation graph."""

    def __init__(self, data, children=(), local_grads=()):
        self.data = data                # scalar value of this node calculated during forward pass
        self.grad = 0                   # derivative of the loss w.r.t. this node, calculated in backward pass
        self._children = children       # children of this node in the computation graph
        self._local_grads = local_grads # local derivative of this node w.r.t. its children

    def __add__(self, other):
        other = other if isinstance(other, Value) else Value(other)
        return Value(self.data + other.data, (self, other), (1, 1))

    def __mul__(self, other):
        other = other if isinstance(other, Value) else Value(other)
        return Value(self.data * other.data, (self, other), (other.data, self.data))

    def __pow__(self, other): return Value(self.data**other, (self,), (other * self.data**(other-1),))
    def log(self): return Value(math.log(self.data), (self,), (1/self.data,))
    def exp(self): return Value(math.exp(self.data), (self,), (math.exp(self.data),))
    def relu(self): return Value(max(0, self.data), (self,), (float(self.data > 0),))
    def __neg__(self): return self * -1
    def __radd__(self, other): return self + other
    def __sub__(self, other): return self + (-other)
    def __rsub__(self, other): return other + (-self)
    def __rmul__(self, other): return self * other
    def __truediv__(self, other): return self * other**-1
    def __rtruediv__(self, other): return other * self**-1

    def backward(self):
        topo = []
        visited = set()
        def build_topo(v):
            if v not in visited:
                visited.add(v)
                for child in v._children:
                    build_topo(child)
                topo.append(v)
        build_topo(self)
        self.grad = 1
        for v in reversed(topo):
            for child, local_grad in zip(v._children, v._local_grads):
                child.grad += local_grad * v.grad

# Initialize the parameters, to store the knowledge of the model.
n_embd = 16     # embedding dimension
n_head = 4      # number of attention heads
n_layer = 1     # number of layers
block_size = 8  # maximum sequence length
head_dim = n_embd // n_head # dimension of each head
matrix = lambda nout, nin, std=0.02: [[Value(random.gauss(0, std)) for _ in range(nin)] for _ in range(nout)]
state_dict = {'wte': matrix(vocab_size, n_embd), 'wpe': matrix(block_size, n_embd), 'lm_head': matrix(vocab_size, n_embd)}
for i in range(n_layer):
    state_dict[f'layer{i}.attn_wq'] = matrix(n_embd, n_embd)
    state_dict[f'layer{i}.attn_wk'] = matrix(n_embd, n_embd)
    state_dict[f'layer{i}.attn_wv'] = matrix(n_embd, n_embd)
    state_dict[f'layer{i}.attn_wo'] = matrix(n_embd, n_embd, std=0)
    state_dict[f'layer{i}.mlp_fc1'] = matrix(4 * n_embd, n_embd)
    state_dict[f'layer{i}.mlp_fc2'] = matrix(n_embd, 4 * n_embd, std=0)
params = [p for mat in state_dict.values() for row in mat for p in row] # flatten params into a single list[Value]
print(f"num params: {len(params)}")

# Define the model architecture: a stateless function mapping token sequence and parameters to logits over what comes next.
# Follow GPT-2, blessed among the GPTs, with minor differences: layernorm -> rmsnorm, no biases, GeLU -> ReLU^2
def linear(x, w):
    return [sum(wi * xi for wi, xi in zip(wo, x)) for wo in w]

def softmax(logits):
    max_val = max(val.data for val in logits)
    exps = [(val - max_val).exp() for val in logits]
    total = sum(exps)
    return [e / total for e in exps]

def rmsnorm(x):
    ms = sum(xi * xi for xi in x) / len(x)
    scale = (ms + 1e-5) ** -0.5
    return [xi * scale for xi in x]

def gpt(token_id, pos_id, keys, values):
    tok_emb = state_dict['wte'][token_id] # token embedding
    pos_emb = state_dict['wpe'][pos_id] # position embedding
    x = [t + p for t, p in zip(tok_emb, pos_emb)] # joint token and position embedding
    x = rmsnorm(x)

    for li in range(n_layer):
        # 1) Multi-head attention block
        x_residual = x
        x = rmsnorm(x)
        q = linear(x, state_dict[f'layer{li}.attn_wq'])
        k = linear(x, state_dict[f'layer{li}.attn_wk'])
        v = linear(x, state_dict[f'layer{li}.attn_wv'])
        keys[li].append(k)
        values[li].append(v)
        x_attn = []
        for h in range(n_head):
            hs = h * head_dim
            q_h = q[hs:hs+head_dim]
            k_h = [ki[hs:hs+head_dim] for ki in keys[li]]
            v_h = [vi[hs:hs+head_dim] for vi in values[li]]
            attn_logits = [sum(q_h[j] * k_h[t][j] for j in range(head_dim)) / head_dim**0.5 for t in range(len(k_h))]
            attn_weights = softmax(attn_logits)
            head_out = [sum(attn_weights[t] * v_h[t][j] for t in range(len(v_h))) for j in range(head_dim)]
            x_attn.extend(head_out)
        x = linear(x_attn, state_dict[f'layer{li}.attn_wo'])
        x = [a + b for a, b in zip(x, x_residual)]
        # 2) MLP block
        x_residual = x
        x = rmsnorm(x)
        x = linear(x, state_dict[f'layer{li}.mlp_fc1'])
        x = [xi.relu() ** 2 for xi in x]
        x = linear(x, state_dict[f'layer{li}.mlp_fc2'])
        x = [a + b for a, b in zip(x, x_residual)]

    logits = linear(x, state_dict['lm_head'])
    return logits

# Let there be Adam, the blessed optimizer and its buffers
learning_rate, beta1, beta2, eps_adam = 1e-2, 0.9, 0.95, 1e-8
m = [0.0] * len(params) # first moment buffer
v = [0.0] * len(params) # second moment buffer

# Repeat in sequence
num_steps = 500 # number of training steps
for step in range(num_steps):

    # Take single document, tokenize it, surround it with BOS special token on both sides
    doc = docs[step % len(docs)]
    tokens = [BOS] + [uchars.index(ch) for ch in doc] + [BOS]
    n = min(block_size, len(tokens) - 1)

    # Forward the token sequence through the model, building up the computation graph all the way to the loss.
    keys, values = [[] for _ in range(n_layer)], [[] for _ in range(n_layer)]
    losses = []
    for pos_id in range(n):
        token_id, target_id = tokens[pos_id], tokens[pos_id + 1]
        logits = gpt(token_id, pos_id, keys, values)
        probs = softmax(logits)
        loss_t = -probs[target_id].log()
        losses.append(loss_t)
    loss = (1 / n) * sum(losses) # final average loss over the document sequence. May yours be low.

    # Backward the loss, calculating the gradients with respect to all model parameters.
    loss.backward()

    # Adam optimizer update: update the model parameters based on the corresponding gradients.
    lr_t = learning_rate * 0.5 * (1 + math.cos(math.pi * step / num_steps)) # cosine learning rate decay
    for i, p in enumerate(params):
        m[i] = beta1 * m[i] + (1 - beta1) * p.grad
        v[i] = beta2 * v[i] + (1 - beta2) * p.grad ** 2
        m_hat = m[i] / (1 - beta1 ** (step + 1))
        v_hat = v[i] / (1 - beta2 ** (step + 1))
        p.data -= lr_t * m_hat / (v_hat ** 0.5 + eps_adam)
        p.grad = 0

    print(f"step {step+1:4d} / {num_steps:4d} | loss {loss.data:.4f}")

# Inference: may the model babble back to us
temperature = 0.5 # in (0, 1], control the "creativity" of generated text, low to high
print("\n--- inference ---")
for sample_idx in range(20):
    keys, values = [[] for _ in range(n_layer)], [[] for _ in range(n_layer)]
    token_id = BOS
    sample = []
    for pos_id in range(block_size):
        logits = gpt(token_id, pos_id, keys, values)
        probs = softmax([l / temperature for l in logits])
        token_id = random.choices(range(vocab_size), weights=[p.data for p in probs])[0]
        if token_id == BOS:
            break
        sample.append(uchars[token_id])
    print(f"sample {sample_idx+1:2d}: {''.join(sample)}")
```

---

## Output Format

Structure your response under the four phase headings. Phases 1-3 build the initial plan. Phase 4 provides the expert reviews followed by the revised plan with change annotations. The revised plan is the deliverable - it is what will be implemented commit-by-commit in the follow-up.
