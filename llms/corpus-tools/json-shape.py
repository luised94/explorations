# json-shape.py -- the STRUCTURE of a JSON file, never its values.
# usage: python3 json-shape.py FILE.json
# Prints every key path with the value types seen there and how many
# times it occurs, e.g.  [].chat_messages[].text  str  48213
# List elements collapse into "[]", so a file of ten thousand
# conversations prints one line per distinct field, not per record.
# No value, and no key that is itself data (see below), is printed, so
# the output is safe to paste when asking for an extraction script.
# ASCII only.
import json
import sys

with open(sys.argv[1], encoding="utf-8") as input_file:
    parsed_document = json.load(input_file)

# key path -> {type name: occurrence count}
type_counts_by_path = {}
# Walk iteratively: exports nest deeply enough that recursion depth is
# a real risk, and an explicit stack is just as legible here.
pending_nodes = [("", parsed_document)]
while pending_nodes:
    node_path, node_value = pending_nodes.pop()
    type_name = type(node_value).__name__
    counts_for_path = type_counts_by_path.setdefault(node_path or "(root)", {})
    counts_for_path[type_name] = counts_for_path.get(type_name, 0) + 1
    if isinstance(node_value, dict):
        # Many exports use data as keys (ids, dates). Past 50 distinct
        # keys in one object, the keys are treated as data and collapsed
        # to "{key}" so no value leaks through a key name.
        keys_are_data = len(node_value) > 50
        for child_key, child_value in node_value.items():
            child_name = "{key}" if keys_are_data else child_key
            pending_nodes.append((node_path + "." + child_name, child_value))
    elif isinstance(node_value, list):
        for child_value in node_value:
            pending_nodes.append((node_path + "[]", child_value))

for key_path in sorted(type_counts_by_path):
    type_summary = " ".join("%s:%d" % (type_name, count) for type_name, count in sorted(type_counts_by_path[key_path].items()))
    print("%-70s %s" % (key_path, type_summary))
