
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
    names_url: str = 'https://raw.githubusercontent.com/karpathy/makemore/refs/heads/master/names.txt'
    urllib.request.urlretrieve(names_url, 'input.txt')

file_content: str = open('input.txt').read().strip()
document_lines: list[str] = file_content.split('\n')
docs: list[str] = []
for line in document_lines:
    stripped_line: str = line.strip()
    if stripped_line:
        docs.append(stripped_line)
random.shuffle(docs)
print(f"num docs: {len(docs)}")

# Let there be a Tokenizer to translate strings to discrete symbols and back
all_characters: str = ''.join(docs)
unique_characters: list[str] = sorted(set(all_characters))
character_to_token: dict[str, int] = {}
for token_id, character in enumerate(unique_characters):
    character_to_token[character] = token_id
token_to_character: list[str] = unique_characters  # list for inverse lookup
BOS: int = len(unique_characters) # token id for the special Beginning of Sequence (BOS) token
vocab_size: int = len(unique_characters) + 1 # total number of unique tokens, +1 is for BOS
print(f"vocab size: {vocab_size}")

# Let there be a Tape to record the computation graph as parallel flat lists
tape_data: list[float] = []
tape_grad: list[float] = []
tape_children: list[tuple[int, ...]] = []
tape_local_grads: list[tuple[float, ...]] = []

def tape_append_node(data: float, children: tuple[int, ...], local_grads: tuple[float, ...]) -> int:
    node_index: int = len(tape_data)
    tape_data.append(data)
    tape_grad.append(0.0)
    tape_children.append(children)
    tape_local_grads.append(local_grads)
    return node_index

def tape_add(a_index: int, b_index: int) -> int:
    data: float = tape_data[a_index] + tape_data[b_index]
    return tape_append_node(data, (a_index, b_index), (1.0, 1.0))

def tape_multiply(a_index: int, b_index: int) -> int:
    a_data: float = tape_data[a_index]
    b_data: float = tape_data[b_index]
    data: float = a_data * b_data
    return tape_append_node(data, (a_index, b_index), (b_data, a_data))

def tape_power(a_index: int, exponent: float) -> int:
    a_data: float = tape_data[a_index]
    data: float = a_data ** exponent
    local_grad: float = exponent * (a_data ** (exponent - 1))
    return tape_append_node(data, (a_index,), (local_grad,))

def tape_log(a_index: int) -> int:
    a_data: float = tape_data[a_index]
    data: float = math.log(a_data)
    local_grad: float = 1.0 / a_data
    return tape_append_node(data, (a_index,), (local_grad,))

def tape_exp(a_index: int) -> int:
    a_data: float = tape_data[a_index]
    data: float = math.exp(a_data)
    return tape_append_node(data, (a_index,), (data,))

def tape_relu(a_index: int) -> int:
    a_data: float = tape_data[a_index]
    data: float = max(0.0, a_data)
    local_grad: float = 1.0 if a_data > 0 else 0.0
    return tape_append_node(data, (a_index,), (local_grad,))

def tape_backward(loss_index: int) -> None:
    tape_grad[loss_index] = 1.0
    for node_index in range(loss_index, -1, -1):
        node_grad: float = tape_grad[node_index]
        for child_index, local_grad in zip(tape_children[node_index], tape_local_grads[node_index]):
            tape_grad[child_index] += local_grad * node_grad

# Initialize the parameters, to store the knowledge of the model.
embedding_dimension: int = 16     # embedding dimension
number_of_heads: int = 4          # number of attention heads
number_of_layers: int = 1         # number of layers
block_size: int = 8               # maximum sequence length
head_dimension: int = embedding_dimension // number_of_heads # dimension of each head

# Build flat parameter storage with offset table
parameter_offset_table: dict[str, tuple[int, int, int]] = {}
parameter_data: list[float] = []
current_offset: int = 0

# NOTE: allocate_matrix mutates global current_offset - style invariant violation to address
def allocate_matrix(name: str, number_of_rows: int, number_of_columns: int, std: float = 0.02) -> None:
    global current_offset
    start_index: int = current_offset
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
    start_index: int
    number_of_rows: int
    number_of_columns: int
    start_index, number_of_rows, number_of_columns = parameter_offset_table[name]
    matrix: list[list[int]] = []
    for row_index in range(number_of_rows):
        row: list[int] = []
        for column_index in range(number_of_columns):
            flat_index: int = start_index + row_index * number_of_columns + column_index
            row.append(flat_index)
        matrix.append(row)
    return matrix

def get_weight_matrix_float(name: str) -> list[list[float]]:
    start_index: int
    number_of_rows: int
    number_of_columns: int
    start_index, number_of_rows, number_of_columns = parameter_offset_table[name]
    matrix: list[list[float]] = []
    for row_index in range(number_of_rows):
        row: list[float] = []
        for column_index in range(number_of_columns):
            flat_index: int = start_index + row_index * number_of_columns + column_index
            row.append(parameter_data[flat_index])
        matrix.append(row)
    return matrix

def linear_tape(x: list[int], w: list[list[int]]) -> list[int]:
    result: list[int] = []
    for weight_row in w:
        accumulator: int | None = None
        for weight_index, x_index in zip(weight_row, x):
            product: int = tape_multiply(weight_index, x_index)
            if accumulator is None:
                accumulator = product
            else:
                accumulator = tape_add(accumulator, product)
        result.append(accumulator)
    return result

def linear_float(x: list[float], w: list[list[float]]) -> list[float]:
    result: list[float] = []
    for weight_row in w:
        accumulator: float = 0.0
        for weight_value, x_value in zip(weight_row, x):
            accumulator += weight_value * x_value
        result.append(accumulator)
    return result

def softmax_tape(logits: list[int]) -> list[int]:
    max_val: float = max(tape_data[idx] for idx in logits)
    shifted: list[int] = []
    for logit_index in logits:
        max_node: int = tape_append_node(max_val, (), ())
        neg_one: int = tape_append_node(-1.0, (), ())
        neg_max: int = tape_multiply(max_node, neg_one)
        shifted_logit: int = tape_add(logit_index, neg_max)
        shifted.append(shifted_logit)
    exps: list[int] = []
    for shifted_index in shifted:
        exp_index: int = tape_exp(shifted_index)
        exps.append(exp_index)
    total: int = exps[0]
    for exp_index in exps[1:]:
        total = tape_add(total, exp_index)
    inv_total: int = tape_power(total, -1.0)
    result: list[int] = []
    for exp_index in exps:
        normalized: int = tape_multiply(exp_index, inv_total)
        result.append(normalized)
    return result

def softmax_float(logits: list[float]) -> list[float]:
    max_val: float = max(logits)
    shifted: list[float] = []
    for logit_value in logits:
        shifted.append(logit_value - max_val)
    exps: list[float] = []
    for shifted_value in shifted:
        exps.append(math.exp(shifted_value))
    total: float = 0.0
    for exp_value in exps:
        total += exp_value
    result: list[float] = []
    for exp_value in exps:
        result.append(exp_value / total)
    return result

def rmsnorm_tape(x: list[int]) -> list[int]:
    squares: list[int] = []
    for x_index in x:
        square: int = tape_power(x_index, 2.0)
        squares.append(square)
    sum_squares: int = squares[0]
    for square in squares[1:]:
        sum_squares = tape_add(sum_squares, square)
    n_const: int = tape_append_node(float(len(x)), (), ())
    inv_n: int = tape_power(n_const, -1.0)
    ms: int = tape_multiply(sum_squares, inv_n)
    epsilon: int = tape_append_node(1e-5, (), ())
    ms_eps: int = tape_add(ms, epsilon)
    scale: int = tape_power(ms_eps, -0.5)
    result: list[int] = []
    for x_index in x:
        scaled: int = tape_multiply(x_index, scale)
        result.append(scaled)
    return result

def rmsnorm_float(x: list[float]) -> list[float]:
    sum_squares: float = 0.0
    for x_value in x:
        sum_squares += x_value * x_value
    ms: float = sum_squares / float(len(x))
    scale: float = 1.0 / ((ms + 1e-5) ** 0.5)
    result: list[float] = []
    for x_value in x:
        result.append(x_value * scale)
    return result

def forward_training(token_id: int, position_index: int, keys: list[list[list[int]]], values: list[list[list[int]]]) -> list[int]:
    wte_start: int
    wte_rows: int
    wte_cols: int
    wte_start, wte_rows, wte_cols = parameter_offset_table['wte']
    tok_emb_start: int = wte_start + token_id * wte_cols
    token_embedding: list[int] = list(range(tok_emb_start, tok_emb_start + wte_cols))
    
    wpe_start: int
    wpe_rows: int
    wpe_cols: int
    wpe_start, wpe_rows, wpe_cols = parameter_offset_table['wpe']
    pos_emb_start: int = wpe_start + position_index * wpe_cols
    position_embedding: list[int] = list(range(pos_emb_start, pos_emb_start + wpe_cols))
    
    hidden: list[int] = []
    for tok_index, pos_index in zip(token_embedding, position_embedding):
        hidden.append(tape_add(tok_index, pos_index))
    
    hidden = rmsnorm_tape(hidden)
    
    for layer_index in range(number_of_layers):
        residual: list[int] = hidden
        hidden = rmsnorm_tape(hidden)
        
        query: list[int] = linear_tape(hidden, get_weight_matrix_tape(f'layer{layer_index}.attn_wq'))
        key: list[int] = linear_tape(hidden, get_weight_matrix_tape(f'layer{layer_index}.attn_wk'))
        value: list[int] = linear_tape(hidden, get_weight_matrix_tape(f'layer{layer_index}.attn_wv'))
        
        keys[layer_index].append(key)
        values[layer_index].append(value)
        
        attention_output: list[int] = []
        for head_index in range(number_of_heads):
            head_start: int = head_index * head_dimension
            query_head: list[int] = query[head_start:head_start+head_dimension]
            key_head: list[list[int]] = [ki[head_start:head_start+head_dimension] for ki in keys[layer_index]]
            value_head: list[list[int]] = [vi[head_start:head_start+head_dimension] for vi in values[layer_index]]
            
            attn_logits: list[int] = []
            for time_step in range(len(key_head)):
                dot_product: int | None = None
                for dimension_index in range(head_dimension):
                    product: int = tape_multiply(query_head[dimension_index], key_head[time_step][dimension_index])
                    if dot_product is None:
                        dot_product = product
                    else:
                        dot_product = tape_add(dot_product, product)
                scale: int = tape_append_node(head_dimension ** 0.5, (), ())
                inv_scale: int = tape_power(scale, -1.0)
                scaled_logit: int = tape_multiply(dot_product, inv_scale)
                attn_logits.append(scaled_logit)
            
            attn_weights: list[int] = softmax_tape(attn_logits)
            
            for dimension_index in range(head_dimension):
                head_out_j: int | None = None
                for time_step in range(len(value_head)):
                    product: int = tape_multiply(attn_weights[time_step], value_head[time_step][dimension_index])
                    if head_out_j is None:
                        head_out_j = product
                    else:
                        head_out_j = tape_add(head_out_j, product)
                attention_output.append(head_out_j)
        
        hidden = linear_tape(attention_output, get_weight_matrix_tape(f'layer{layer_index}.attn_wo'))
        hidden = [tape_add(a, b) for a, b in zip(hidden, residual)]
        
        residual = hidden
        hidden = rmsnorm_tape(hidden)
        hidden = linear_tape(hidden, get_weight_matrix_tape(f'layer{layer_index}.mlp_fc1'))
        hidden = [tape_power(tape_relu(xi), 2.0) for xi in hidden]
        hidden = linear_tape(hidden, get_weight_matrix_tape(f'layer{layer_index}.mlp_fc2'))
        hidden = [tape_add(a, b) for a, b in zip(hidden, residual)]
    
    logits: list[int] = linear_tape(hidden, get_weight_matrix_tape('lm_head'))
    return logits

def forward_inference(token_id: int, position_index: int, keys: list[list[list[float]]], values: list[list[list[float]]]) -> list[float]:
    wte_start: int
    wte_rows: int
    wte_cols: int
    wte_start, wte_rows, wte_cols = parameter_offset_table['wte']
    tok_emb_start: int = wte_start + token_id * wte_cols
    token_embedding: list[float] = []
    for column_index in range(wte_cols):
        token_embedding.append(parameter_data[tok_emb_start + column_index])
    
    wpe_start: int
    wpe_rows: int
    wpe_cols: int
    wpe_start, wpe_rows, wpe_cols = parameter_offset_table['wpe']
    pos_emb_start: int = wpe_start + position_index * wpe_cols
    position_embedding: list[float] = []
    for column_index in range(wpe_cols):
        position_embedding.append(parameter_data[pos_emb_start + column_index])
    
    hidden: list[float] = []
    for tok_value, pos_value in zip(token_embedding, position_embedding):
        hidden.append(tok_value + pos_value)
    
    hidden = rmsnorm_float(hidden)
    
    for layer_index in range(number_of_layers):
        residual: list[float] = hidden
        hidden = rmsnorm_float(hidden)
        
        query: list[float] = linear_float(hidden, get_weight_matrix_float(f'layer{layer_index}.attn_wq'))
        key: list[float] = linear_float(hidden, get_weight_matrix_float(f'layer{layer_index}.attn_wk'))
        value: list[float] = linear_float(hidden, get_weight_matrix_float(f'layer{layer_index}.attn_wv'))
        
        keys[layer_index].append(key)
        values[layer_index].append(value)
        
        attention_output: list[float] = []
        for head_index in range(number_of_heads):
            head_start: int = head_index * head_dimension
            query_head: list[float] = query[head_start:head_start+head_dimension]
            key_head: list[list[float]] = [ki[head_start:head_start+head_dimension] for ki in keys[layer_index]]
            value_head: list[list[float]] = [vi[head_start:head_start+head_dimension] for vi in values[layer_index]]
            
            attn_logits: list[float] = []
            for time_step in range(len(key_head)):
                dot_product: float = 0.0
                for dimension_index in range(head_dimension):
                    dot_product += query_head[dimension_index] * key_head[time_step][dimension_index]
                scaled_logit: float = dot_product / (head_dimension ** 0.5)
                attn_logits.append(scaled_logit)
            
            attn_weights: list[float] = softmax_float(attn_logits)
            
            for dimension_index in range(head_dimension):
                head_out_j: float = 0.0
                for time_step in range(len(value_head)):
                    head_out_j += attn_weights[time_step] * value_head[time_step][dimension_index]
                attention_output.append(head_out_j)
        
        hidden = linear_float(attention_output, get_weight_matrix_float(f'layer{layer_index}.attn_wo'))
        hidden = [a + b for a, b in zip(hidden, residual)]
        
        residual = hidden
        hidden = rmsnorm_float(hidden)
        hidden = linear_float(hidden, get_weight_matrix_float(f'layer{layer_index}.mlp_fc1'))
        hidden = [max(0.0, xi) ** 2.0 for xi in hidden]
        hidden = linear_float(hidden, get_weight_matrix_float(f'layer{layer_index}.mlp_fc2'))
        hidden = [a + b for a, b in zip(hidden, residual)]
    
    logits: list[float] = linear_float(hidden, get_weight_matrix_float('lm_head'))
    return logits

# Let there be Adam, the blessed optimizer and its buffers
learning_rate: float
beta1: float
beta2: float
epsilon_adam: float
learning_rate, beta1, beta2, epsilon_adam = 1e-2, 0.9, 0.95, 1e-8
first_moment: list[float] = [0.0] * len(parameter_data) # first moment buffer
second_moment: list[float] = [0.0] * len(parameter_data) # second moment buffer

# Repeat in sequence
num_steps: int = 500 # number of training steps
for step in range(num_steps):
    tape_data = parameter_data.copy()
    tape_grad = [0.0] * len(parameter_data)
    tape_children = [() for _ in range(len(parameter_data))]
    tape_local_grads = [() for _ in range(len(parameter_data))]
    
    doc: str = docs[step % len(docs)]
    tokens: list[int] = [BOS] + [character_to_token[character] for character in doc] + [BOS]
    sequence_length: int = min(block_size, len(tokens) - 1)
    
    keys: list[list[list[int]]] = [[] for _ in range(number_of_layers)]
    values: list[list[list[int]]] = [[] for _ in range(number_of_layers)]
    
    losses: list[int] = []
    for position_index in range(sequence_length):
        token_id: int
        target_id: int
        token_id, target_id = tokens[position_index], tokens[position_index + 1]
        logits: list[int] = forward_training(token_id, position_index, keys, values)
        probs: list[int] = softmax_tape(logits)
        neg_one: int = tape_append_node(-1.0, (), ())
        position_loss: int = tape_multiply(neg_one, tape_log(probs[target_id]))
        losses.append(position_loss)
    
    total_loss_sum: int = losses[0]
    for position_loss in losses[1:]:
        total_loss_sum = tape_add(total_loss_sum, position_loss)
    
    loss_scale: int = tape_append_node(1.0 / sequence_length, (), ())
    loss: int = tape_multiply(loss_scale, total_loss_sum)
    
    tape_backward(loss)
    
    adjusted_learning_rate: float = learning_rate * 0.5 * (1 + math.cos(math.pi * step / num_steps))
    for parameter_index in range(len(parameter_data)):
        first_moment[parameter_index] = beta1 * first_moment[parameter_index] + (1 - beta1) * tape_grad[parameter_index]
        second_moment[parameter_index] = beta2 * second_moment[parameter_index] + (1 - beta2) * tape_grad[parameter_index] ** 2
        first_moment_corrected: float = first_moment[parameter_index] / (1 - beta1 ** (step + 1))
        second_moment_corrected: float = second_moment[parameter_index] / (1 - beta2 ** (step + 1))
        parameter_data[parameter_index] -= adjusted_learning_rate * first_moment_corrected / (second_moment_corrected ** 0.5 + epsilon_adam)
    
    print(f"step {step+1:4d} / {num_steps:4d} | loss {tape_data[loss]:.4f}")

# Inference: may the model babble back to us
temperature: float = 0.5
print("\n--- inference ---")
for sample_idx in range(20):
    keys: list[list[list[float]]] = [[] for _ in range(number_of_layers)]
    values: list[list[list[float]]] = [[] for _ in range(number_of_layers)]
    token_id: int = BOS
    sample: list[str] = []
    for position_index in range(block_size):
        logits: list[float] = forward_inference(token_id, position_index, keys, values)
        scaled_logits: list[float] = []
        for logit_value in logits:
            scaled_logits.append(logit_value / temperature)
        probs: list[float] = softmax_float(scaled_logits)
        token_id = random.choices(range(vocab_size), weights=probs)[0]
        if token_id == BOS:
            break
        sample.append(token_to_character[token_id])
    print(f"sample {sample_idx+1:2d}: {''.join(sample)}")
