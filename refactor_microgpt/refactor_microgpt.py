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
file_content = open('input.txt').read().strip()
document_lines = file_content.split('\n')
docs: list[str] = []
for line in document_lines:
    stripped_line = line.strip()
    if stripped_line:
        docs.append(stripped_line)
random.shuffle(docs)
print(f"num docs: {len(docs)}")
# Let there be a Tokenizer to translate strings to discrete symbols and back
all_characters = ''.join(docs)
unique_characters = sorted(set(all_characters))
character_to_token: dict[str, int] = {}
for token_id, character in enumerate(unique_characters):
    character_to_token[character] = token_id
token_to_character = unique_characters  # list for inverse lookup
BOS = len(unique_characters) # token id for the special Beginning of Sequence (BOS) token
vocab_size = len(unique_characters) + 1 # total number of unique tokens, +1 is for BOS
print(f"vocab size: {vocab_size}")
# Let there be a Tape to record the computation graph as parallel flat lists
tape_data: list[float] = []
tape_grad: list[float] = []
tape_children: list[tuple[int, ...]] = []
tape_local_grads: list[tuple[float, ...]] = []

def tape_append_node(data: float, children: tuple[int, ...], local_grads: tuple[float, ...]) -> int:
    node_index = len(tape_data)
    tape_data.append(data)
    tape_grad.append(0.0)
    tape_children.append(children)
    tape_local_grads.append(local_grads)
    return node_index

def tape_add(a_index: int, b_index: int) -> int:
    data = tape_data[a_index] + tape_data[b_index]
    return tape_append_node(data, (a_index, b_index), (1.0, 1.0))

def tape_multiply(a_index: int, b_index: int) -> int:
    a_data = tape_data[a_index]
    b_data = tape_data[b_index]
    data = a_data * b_data
    return tape_append_node(data, (a_index, b_index), (b_data, a_data))

def tape_power(a_index: int, exponent: float) -> int:
    a_data = tape_data[a_index]
    data = a_data ** exponent
    local_grad = exponent * (a_data ** (exponent - 1))
    return tape_append_node(data, (a_index,), (local_grad,))

def tape_log(a_index: int) -> int:
    a_data = tape_data[a_index]
    data = math.log(a_data)
    local_grad = 1.0 / a_data
    return tape_append_node(data, (a_index,), (local_grad,))

def tape_exp(a_index: int) -> int:
    a_data = tape_data[a_index]
    data = math.exp(a_data)
    return tape_append_node(data, (a_index,), (data,))

def tape_relu(a_index: int) -> int:
    a_data = tape_data[a_index]
    data = max(0.0, a_data)
    local_grad = 1.0 if a_data > 0 else 0.0
    return tape_append_node(data, (a_index,), (local_grad,))

def tape_backward(loss_index: int):
    tape_grad[loss_index] = 1.0
    for node_index in range(loss_index, -1, -1):
        node_grad = tape_grad[node_index]
        for child_index, local_grad in zip(tape_children[node_index], tape_local_grads[node_index]):
            tape_grad[child_index] += local_grad * node_grad

# Initialize the parameters, to store the knowledge of the model.
embedding_dimension = 16     # embedding dimension
number_of_heads = 4          # number of attention heads
number_of_layers = 1         # number of layers
block_size = 8               # maximum sequence length
head_dimension = embedding_dimension // number_of_heads # dimension of each head
# Build flat parameter storage with offset table
parameter_offset_table: dict[str, tuple[int, int, int]] = {}
parameter_data: list[float] = []
current_offset = 0

def allocate_matrix(name: str, number_of_rows: int, number_of_columns: int, std: float = 0.02):
    global current_offset
    start_index = current_offset
    parameter_offset_table[name] = (start_index, number_of_rows, number_of_columns)
    for _ in range(number_of_rows * number_of_columns):
        parameter_data.append(random.gauss(0, std))
    current_offset += number_of_rows * number_of_columns

allocate_matrix('wte', vocab_size, embedding_dimension)
allocate_matrix('wpe', block_size, embedding_dimension)
allocate_matrix('lm_head', vocab_size, embedding_dimension)
for layer_index in range(number_of_layers):
    allocate_matrix(f'layer{layer_index}.attn_wq', embedding_dimension, embedding_dimension)
    allocate_matrix(f'layer{layer_index}.attn_wk', embedding_dimension, embedding_dimension)
    allocate_matrix(f'layer{layer_index}.attn_wv', embedding_dimension, embedding_dimension)
    allocate_matrix(f'layer{layer_index}.attn_wo', embedding_dimension, embedding_dimension, std=0)
    allocate_matrix(f'layer{layer_index}.mlp_fc1', 4 * embedding_dimension, embedding_dimension)
    allocate_matrix(f'layer{layer_index}.mlp_fc2', embedding_dimension, 4 * embedding_dimension, std=0)
parameter_grad: list[float] = [0.0] * len(parameter_data)
print(f"num params: {len(parameter_data)}")
# Define the model architecture: a stateless function mapping token sequence and parameters to logits over what comes next.
# Follow GPT-2, blessed among the GPTs, with minor differences: layernorm -> rmsnorm, no biases, GeLU -> ReLU^2
def linear(x: list[int], w: list[list[int]]) -> list[int]:
    result: list[int] = []
    for weight_row in w:
        accumulator = None
        for weight_index, x_index in zip(weight_row, x):
            product = tape_multiply(weight_index, x_index)
            if accumulator is None:
                accumulator = product
            else:
                accumulator = tape_add(accumulator, product)
        result.append(accumulator)
    return result

def softmax(logits: list[int]) -> list[int]:
    max_val = max(tape_data[idx] for idx in logits)
    shifted: list[int] = []
    for logit_index in logits:
        max_node = tape_append_node(max_val, (), ())
        neg_one = tape_append_node(-1.0, (), ())
        neg_max = tape_multiply(max_node, neg_one)
        shifted_logit = tape_add(logit_index, neg_max)
        shifted.append(shifted_logit)
    exps = [tape_exp(idx) for idx in shifted]
    total = exps[0]
    for exp_index in exps[1:]:
        total = tape_add(total, exp_index)
    result: list[int] = []
    for exp_index in exps:
        inv_total = tape_power(total, -1.0)
        result.append(tape_multiply(exp_index, inv_total))
    return result

def rmsnorm(x: list[int]) -> list[int]:
    squares = [tape_power(xi, 2.0) for xi in x]
    sum_squares = squares[0]
    for sq in squares[1:]:
        sum_squares = tape_add(sum_squares, sq)
    n_const = tape_append_node(float(len(x)), (), ())
    ms = tape_multiply(sum_squares, tape_power(n_const, -1.0))
    epsilon = tape_append_node(1e-5, (), ())
    ms_eps = tape_add(ms, epsilon)
    scale = tape_power(ms_eps, -0.5)
    return [tape_multiply(xi, scale) for xi in x]

def gpt(token_id: int, pos_id: int, keys: list[list[list[int]]], values: list[list[list[int]]]) -> list[int]:
    tok_emb = state_dict['wte'][token_id]
    pos_emb = state_dict['wpe'][pos_id]
    x: list[int] = []
    for t, p in zip(tok_emb, pos_emb):
        x.append(tape_add(t, p))
    x = rmsnorm(x)
    for layer_index in range(number_of_layers):
        x_residual = x
        x = rmsnorm(x)
        q = linear(x, state_dict[f'layer{layer_index}.attn_wq'])
        k = linear(x, state_dict[f'layer{layer_index}.attn_wk'])
        v = linear(x, state_dict[f'layer{layer_index}.attn_wv'])
        keys[layer_index].append(k)
        values[layer_index].append(v)
        x_attn: list[int] = []
        for head_index in range(number_of_heads):
            head_start = head_index * head_dimension
            q_h = q[head_start:head_start+head_dimension]
            k_h = [ki[head_start:head_start+head_dimension] for ki in keys[layer_index]]
            v_h = [vi[head_start:head_start+head_dimension] for vi in values[layer_index]]
            attn_logits: list[int] = []
            for t in range(len(k_h)):
                dot_product = None
                for j in range(head_dimension):
                    product = tape_multiply(q_h[j], k_h[t][j])
                    if dot_product is None:
                        dot_product = product
                    else:
                        dot_product = tape_add(dot_product, product)
                scale = tape_append_node(head_dimension ** 0.5, (), ())
                scaled_logit = tape_multiply(dot_product, tape_power(scale, -1.0))
                attn_logits.append(scaled_logit)
            attn_weights = softmax(attn_logits)
            for j in range(head_dimension):
                head_out_j = None
                for t in range(len(v_h)):
                    product = tape_multiply(attn_weights[t], v_h[t][j])
                    if head_out_j is None:
                        head_out_j = product
                    else:
                        head_out_j = tape_add(head_out_j, product)
                x_attn.append(head_out_j)
        x = linear(x_attn, state_dict[f'layer{layer_index}.attn_wo'])
        x = [tape_add(a, b) for a, b in zip(x, x_residual)]
        x_residual = x
        x = rmsnorm(x)
        x = linear(x, state_dict[f'layer{layer_index}.mlp_fc1'])
        x = [tape_power(tape_relu(xi), 2.0) for xi in x]
        x = linear(x, state_dict[f'layer{layer_index}.mlp_fc2'])
        x = [tape_add(a, b) for a, b in zip(x, x_residual)]
    logits = linear(x, state_dict['lm_head'])
    return logits

# Let there be Adam, the blessed optimizer and its buffers
learning_rate, beta1, beta2, eps_adam = 1e-2, 0.9, 0.95, 1e-8
m = [0.0] * len(parameter_data) # first moment buffer
v = [0.0] * len(parameter_data) # second moment buffer
# Repeat in sequence
num_steps = 500 # number of training steps
for step in range(num_steps):
    # Seed tape with parameters at start of forward pass
    tape_data = parameter_data.copy()
    tape_grad = [0.0] * len(parameter_data)
    tape_children = [() for _ in range(len(parameter_data))]
    tape_local_grads = [() for _ in range(len(parameter_data))]
    # Build state_dict as views into tape indices
    state_dict: dict[str, list[list[int]]] = {}
    for name, (start_index, number_of_rows, number_of_columns) in parameter_offset_table.items():
        matrix: list[list[int]] = []
        for row_index in range(number_of_rows):
            row: list[int] = []
            for column_index in range(number_of_columns):
                flat_index = start_index + row_index * number_of_columns + column_index
                row.append(flat_index)
            matrix.append(row)
        state_dict[name] = matrix
    # Take single document, tokenize it, surround it with BOS special token on both sides
    doc = docs[step % len(docs)]
    tokens = [BOS] + [character_to_token[character] for character in doc] + [BOS]
    n = min(block_size, len(tokens) - 1)
    # Forward the token sequence through the model, building up the computation graph all the way to the loss.
    keys: list[list[list[int]]] = [[] for _ in range(number_of_layers)]
    values: list[list[list[int]]] = [[] for _ in range(number_of_layers)]
    losses: list[int] = []
    for pos_id in range(n):
        token_id, target_id = tokens[pos_id], tokens[pos_id + 1]
        logits = gpt(token_id, pos_id, keys, values)
        probs = softmax(logits)
        neg_one = tape_append_node(-1.0, (), ())
        loss_t = tape_multiply(neg_one, tape_log(probs[target_id]))
        losses.append(loss_t)
    loss_sum = losses[0]
    for loss_t in losses[1:]:
        loss_sum = tape_add(loss_sum, loss_t)
    scale = tape_append_node(1.0 / n, (), ())
    loss = tape_multiply(scale, loss_sum)
    # Backward the loss, calculating the gradients with respect to all model parameters.
    tape_backward(loss)
    # Extract gradients from tape into parameter_grad
    for i in range(len(parameter_data)):
        parameter_grad[i] = tape_grad[i]
    # Adam optimizer update: update the model parameters based on the corresponding gradients.
    lr_t = learning_rate * 0.5 * (1 + math.cos(math.pi * step / num_steps)) # cosine learning rate decay
    for i in range(len(parameter_data)):
        m[i] = beta1 * m[i] + (1 - beta1) * parameter_grad[i]
        v[i] = beta2 * v[i] + (1 - beta2) * parameter_grad[i] ** 2
        m_hat = m[i] / (1 - beta1 ** (step + 1))
        v_hat = v[i] / (1 - beta2 ** (step + 1))
        parameter_data[i] -= lr_t * m_hat / (v_hat ** 0.5 + eps_adam)
    print(f"step {step+1:4d} / {num_steps:4d} | loss {tape_data[loss]:.4f}")
# Inference: may the model babble back to us
temperature = 0.5 # in (0, 1], control the "creativity" of generated text, low to high
print("\n--- inference ---")
for sample_idx in range(20):
    # Seed tape with parameters
    tape_data = parameter_data.copy()
    tape_grad = [0.0] * len(parameter_data)
    tape_children = [() for _ in range(len(parameter_data))]
    tape_local_grads = [() for _ in range(len(parameter_data))]
    # Build state_dict
    state_dict = {}
    for name, (start_index, number_of_rows, number_of_columns) in parameter_offset_table.items():
        matrix: list[list[int]] = []
        for row_index in range(number_of_rows):
            row: list[int] = []
            for column_index in range(number_of_columns):
                flat_index = start_index + row_index * number_of_columns + column_index
                row.append(flat_index)
            matrix.append(row)
        state_dict[name] = matrix
    keys: list[list[list[int]]] = [[] for _ in range(number_of_layers)]
    values: list[list[list[int]]] = [[] for _ in range(number_of_layers)]
    token_id = BOS
    sample = []
    for pos_id in range(block_size):
        logits = gpt(token_id, pos_id, keys, values)
        temp_node = tape_append_node(temperature, (), ())
        scaled_logits = [tape_multiply(l, tape_power(temp_node, -1.0)) for l in logits]
        probs = softmax(scaled_logits)
        token_id = random.choices(range(vocab_size), weights=[tape_data[p] for p in probs])[0]
        if token_id == BOS:
            break
        sample.append(token_to_character[token_id])
    print(f"sample {sample_idx+1:2d}: {''.join(sample)}")
