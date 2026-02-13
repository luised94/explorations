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

print(f"num params: {len(parameter_data)}")

# Define the model architecture: a stateless function mapping token sequence and parameters to logits over what comes next.
# Follow GPT-2, blessed among the GPTs, with minor differences: layernorm -> rmsnorm, no biases, GeLU -> ReLU^2

def get_weight_matrix_tape(name: str) -> list[list[int]]:
    start_index, number_of_rows, number_of_columns = parameter_offset_table[name]
    matrix: list[list[int]] = []
    for row_index in range(number_of_rows):
        row: list[int] = []
        for column_index in range(number_of_columns):
            flat_index = start_index + row_index * number_of_columns + column_index
            row.append(flat_index)
        matrix.append(row)
    return matrix

def get_weight_matrix_float(name: str) -> list[list[float]]:
    start_index, number_of_rows, number_of_columns = parameter_offset_table[name]
    matrix: list[list[float]] = []
    for row_index in range(number_of_rows):
        row: list[float] = []
        for column_index in range(number_of_columns):
            flat_index = start_index + row_index * number_of_columns + column_index
            row.append(parameter_data[flat_index])
        matrix.append(row)
    return matrix

def linear_tape(x: list[int], w: list[list[int]]) -> list[int]:
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

def linear_float(x: list[float], w: list[list[float]]) -> list[float]:
    result: list[float] = []
    for weight_row in w:
        accumulator = 0.0
        for weight_value, x_value in zip(weight_row, x):
            accumulator += weight_value * x_value
        result.append(accumulator)
    return result

def softmax_tape(logits: list[int]) -> list[int]:
    max_val = max(tape_data[idx] for idx in logits)
    shifted: list[int] = []
    for logit_index in logits:
        max_node = tape_append_node(max_val, (), ())
        neg_one = tape_append_node(-1.0, (), ())
        neg_max = tape_multiply(max_node, neg_one)
        shifted_logit = tape_add(logit_index, neg_max)
        shifted.append(shifted_logit)
    exps: list[int] = []
    for shifted_index in shifted:
        exp_index = tape_exp(shifted_index)
        exps.append(exp_index)
    total = exps[0]
    for exp_index in exps[1:]:
        total = tape_add(total, exp_index)
    inv_total = tape_power(total, -1.0)
    result: list[int] = []
    for exp_index in exps:
        normalized = tape_multiply(exp_index, inv_total)
        result.append(normalized)
    return result

def softmax_float(logits: list[float]) -> list[float]:
    max_val = max(logits)
    shifted: list[float] = []
    for logit_value in logits:
        shifted.append(logit_value - max_val)
    exps: list[float] = []
    for shifted_value in shifted:
        exps.append(math.exp(shifted_value))
    total = 0.0
    for exp_value in exps:
        total += exp_value
    result: list[float] = []
    for exp_value in exps:
        result.append(exp_value / total)
    return result

def rmsnorm_tape(x: list[int]) -> list[int]:
    squares: list[int] = []
    for x_index in x:
        square = tape_power(x_index, 2.0)
        squares.append(square)
    sum_squares = squares[0]
    for square in squares[1:]:
        sum_squares = tape_add(sum_squares, square)
    n_const = tape_append_node(float(len(x)), (), ())
    inv_n = tape_power(n_const, -1.0)
    ms = tape_multiply(sum_squares, inv_n)
    epsilon = tape_append_node(1e-5, (), ())
    ms_eps = tape_add(ms, epsilon)
    scale = tape_power(ms_eps, -0.5)
    result: list[int] = []
    for x_index in x:
        scaled = tape_multiply(x_index, scale)
        result.append(scaled)
    return result

def rmsnorm_float(x: list[float]) -> list[float]:
    sum_squares = 0.0
    for x_value in x:
        sum_squares += x_value * x_value
    ms = sum_squares / float(len(x))
    scale = 1.0 / ((ms + 1e-5) ** 0.5)
    result: list[float] = []
    for x_value in x:
        result.append(x_value * scale)
    return result

def forward_training(token_id: int, position_index: int, keys: list[list[list[int]]], values: list[list[list[int]]]) -> list[int]:
    wte_start, wte_rows, wte_cols = parameter_offset_table['wte']
    tok_emb_start = wte_start + token_id * wte_cols
    tok_emb: list[int] = list(range(tok_emb_start, tok_emb_start + wte_cols))
    
    wpe_start, wpe_rows, wpe_cols = parameter_offset_table['wpe']
    pos_emb_start = wpe_start + position_index * wpe_cols
    pos_emb: list[int] = list(range(pos_emb_start, pos_emb_start + wpe_cols))
    
    x: list[int] = []
    for tok_index, pos_index in zip(tok_emb, pos_emb):
        x.append(tape_add(tok_index, pos_index))
    
    x = rmsnorm_tape(x)
    
    for layer_index in range(number_of_layers):
        x_residual = x
        x = rmsnorm_tape(x)
        
        q = linear_tape(x, get_weight_matrix_tape(f'layer{layer_index}.attn_wq'))
        k = linear_tape(x, get_weight_matrix_tape(f'layer{layer_index}.attn_wk'))
        v = linear_tape(x, get_weight_matrix_tape(f'layer{layer_index}.attn_wv'))
        
        keys[layer_index].append(k)
        values[layer_index].append(v)
        
        x_attn: list[int] = []
        for head_index in range(number_of_heads):
            head_start = head_index * head_dimension
            q_h = q[head_start:head_start+head_dimension]
            k_h = [ki[head_start:head_start+head_dimension] for ki in keys[layer_index]]
            v_h = [vi[head_start:head_start+head_dimension] for vi in values[layer_index]]
            
            attn_logits: list[int] = []
            for time_step in range(len(k_h)):
                dot_product = None
                for dimension_index in range(head_dimension):
                    product = tape_multiply(q_h[dimension_index], k_h[time_step][dimension_index])
                    if dot_product is None:
                        dot_product = product
                    else:
                        dot_product = tape_add(dot_product, product)
                scale = tape_append_node(head_dimension ** 0.5, (), ())
                inv_scale = tape_power(scale, -1.0)
                scaled_logit = tape_multiply(dot_product, inv_scale)
                attn_logits.append(scaled_logit)
            
            attn_weights = softmax_tape(attn_logits)
            
            for dimension_index in range(head_dimension):
                head_out_j = None
                for time_step in range(len(v_h)):
                    product = tape_multiply(attn_weights[time_step], v_h[time_step][dimension_index])
                    if head_out_j is None:
                        head_out_j = product
                    else:
                        head_out_j = tape_add(head_out_j, product)
                x_attn.append(head_out_j)
        
        x = linear_tape(x_attn, get_weight_matrix_tape(f'layer{layer_index}.attn_wo'))
        x = [tape_add(a, b) for a, b in zip(x, x_residual)]
        
        x_residual = x
        x = rmsnorm_tape(x)
        x = linear_tape(x, get_weight_matrix_tape(f'layer{layer_index}.mlp_fc1'))
        x = [tape_power(tape_relu(xi), 2.0) for xi in x]
        x = linear_tape(x, get_weight_matrix_tape(f'layer{layer_index}.mlp_fc2'))
        x = [tape_add(a, b) for a, b in zip(x, x_residual)]
    
    logits = linear_tape(x, get_weight_matrix_tape('lm_head'))
    return logits

def forward_inference(token_id: int, position_index: int, keys: list[list[list[float]]], values: list[list[list[float]]]) -> list[float]:
    wte_start, wte_rows, wte_cols = parameter_offset_table['wte']
    tok_emb_start = wte_start + token_id * wte_cols
    tok_emb: list[float] = []
    for column_index in range(wte_cols):
        tok_emb.append(parameter_data[tok_emb_start + column_index])
    
    wpe_start, wpe_rows, wpe_cols = parameter_offset_table['wpe']
    pos_emb_start = wpe_start + position_index * wpe_cols
    pos_emb: list[float] = []
    for column_index in range(wpe_cols):
        pos_emb.append(parameter_data[pos_emb_start + column_index])
    
    x: list[float] = []
    for tok_value, pos_value in zip(tok_emb, pos_emb):
        x.append(tok_value + pos_value)
    
    x = rmsnorm_float(x)
    
    for layer_index in range(number_of_layers):
        x_residual = x
        x = rmsnorm_float(x)
        
        q = linear_float(x, get_weight_matrix_float(f'layer{layer_index}.attn_wq'))
        k = linear_float(x, get_weight_matrix_float(f'layer{layer_index}.attn_wk'))
        v = linear_float(x, get_weight_matrix_float(f'layer{layer_index}.attn_wv'))
        
        keys[layer_index].append(k)
        values[layer_index].append(v)
        
        x_attn: list[float] = []
        for head_index in range(number_of_heads):
            head_start = head_index * head_dimension
            q_h = q[head_start:head_start+head_dimension]
            k_h = [ki[head_start:head_start+head_dimension] for ki in keys[layer_index]]
            v_h = [vi[head_start:head_start+head_dimension] for vi in values[layer_index]]
            
            attn_logits: list[float] = []
            for time_step in range(len(k_h)):
                dot_product = 0.0
                for dimension_index in range(head_dimension):
                    dot_product += q_h[dimension_index] * k_h[time_step][dimension_index]
                scaled_logit = dot_product / (head_dimension ** 0.5)
                attn_logits.append(scaled_logit)
            
            attn_weights = softmax_float(attn_logits)
            
            for dimension_index in range(head_dimension):
                head_out_j = 0.0
                for time_step in range(len(v_h)):
                    head_out_j += attn_weights[time_step] * v_h[time_step][dimension_index]
                x_attn.append(head_out_j)
        
        x = linear_float(x_attn, get_weight_matrix_float(f'layer{layer_index}.attn_wo'))
        x = [a + b for a, b in zip(x, x_residual)]
        
        x_residual = x
        x = rmsnorm_float(x)
        x = linear_float(x, get_weight_matrix_float(f'layer{layer_index}.mlp_fc1'))
        x = [max(0.0, xi) ** 2.0 for xi in x]
        x = linear_float(x, get_weight_matrix_float(f'layer{layer_index}.mlp_fc2'))
        x = [a + b for a, b in zip(x, x_residual)]
    
    logits = linear_float(x, get_weight_matrix_float('lm_head'))
    return logits

# Let there be Adam, the blessed optimizer and its buffers
learning_rate, beta1, beta2, eps_adam = 1e-2, 0.9, 0.95, 1e-8
m = [0.0] * len(parameter_data) # first moment buffer
v = [0.0] * len(parameter_data) # second moment buffer

# Repeat in sequence
num_steps = 500 # number of training steps
for step in range(num_steps):
    tape_data = parameter_data.copy()
    tape_grad = [0.0] * len(parameter_data)
    tape_children = [() for _ in range(len(parameter_data))]
    tape_local_grads = [() for _ in range(len(parameter_data))]
    
    doc = docs[step % len(docs)]
    tokens = [BOS] + [character_to_token[character] for character in doc] + [BOS]
    sequence_length = min(block_size, len(tokens) - 1)
    
    keys: list[list[list[int]]] = [[] for _ in range(number_of_layers)]
    values: list[list[list[int]]] = [[] for _ in range(number_of_layers)]
    
    losses: list[int] = []
    for position_index in range(sequence_length):
        token_id, target_id = tokens[position_index], tokens[position_index + 1]
        logits = forward_training(token_id, position_index, keys, values)
        probs = softmax_tape(logits)
        neg_one = tape_append_node(-1.0, (), ())
        loss_t = tape_multiply(neg_one, tape_log(probs[target_id]))
        losses.append(loss_t)
    
    loss_sum = losses[0]
    for loss_t in losses[1:]:
        loss_sum = tape_add(loss_sum, loss_t)
    scale = tape_append_node(1.0 / sequence_length, (), ())
    loss = tape_multiply(scale, loss_sum)
    
    tape_backward(loss)
    
    lr_t = learning_rate * 0.5 * (1 + math.cos(math.pi * step / num_steps))
    for parameter_index in range(len(parameter_data)):
        m[parameter_index] = beta1 * m[parameter_index] + (1 - beta1) * tape_grad[parameter_index]
        v[parameter_index] = beta2 * v[parameter_index] + (1 - beta2) * tape_grad[parameter_index] ** 2
        m_hat = m[parameter_index] / (1 - beta1 ** (step + 1))
        v_hat = v[parameter_index] / (1 - beta2 ** (step + 1))
        parameter_data[parameter_index] -= lr_t * m_hat / (v_hat ** 0.5 + eps_adam)
    
    print(f"step {step+1:4d} / {num_steps:4d} | loss {tape_data[loss]:.4f}")

# Inference: may the model babble back to us
temperature = 0.5
print("\n--- inference ---")
for sample_idx in range(20):
    keys: list[list[list[float]]] = [[] for _ in range(number_of_layers)]
    values: list[list[list[float]]] = [[] for _ in range(number_of_layers)]
    
    token_id = BOS
    sample = []
    for position_index in range(block_size):
        logits = forward_inference(token_id, position_index, keys, values)
        scaled_logits: list[float] = []
        for logit_value in logits:
            scaled_logits.append(logit_value / temperature)
        probs = softmax_float(scaled_logits)
        token_id = random.choices(range(vocab_size), weights=probs)[0]
        if token_id == BOS:
            break
        sample.append(token_to_character[token_id])
    print(f"sample {sample_idx+1:2d}: {''.join(sample)}")
