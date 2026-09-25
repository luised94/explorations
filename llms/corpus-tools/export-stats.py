# export-stats.py -- counts from a Claude conversations.json, no content.
# usage: python3 export-stats.py conversations.json
#
# Prints: conversation records per month (by created_at), message
# totals by sender, and BRANCHING. Each message names its parent in
# parent_message_uuid, so one conversation is a TREE of messages, and an
# edited or retried message is a parent with two or more children. A
# "branch point" below is such a parent. Titles, text and ids are never
# printed, so the output is safe to paste.
# ASCII only.
import collections
import json
import sys

with open(sys.argv[1], encoding="utf-8") as input_file:
    conversation_records = json.load(input_file)

conversations_per_month = collections.Counter()
messages_per_sender = collections.Counter()
message_total = 0
branch_point_total = 0
conversations_with_a_branch = 0
largest_branch_fanout = 0
for conversation_record in conversation_records:
    conversations_per_month[(conversation_record.get("created_at") or "unknown")[:7]] += 1
    children_per_parent = collections.Counter()
    for message_record in conversation_record.get("chat_messages") or []:
        message_total += 1
        messages_per_sender[message_record.get("sender") or "unknown"] += 1
        parent_identifier = message_record.get("parent_message_uuid")
        if parent_identifier:
            children_per_parent[parent_identifier] += 1
    branch_points_here = [child_count for child_count in children_per_parent.values() if child_count >= 2]
    branch_point_total += len(branch_points_here)
    if branch_points_here:
        conversations_with_a_branch += 1
        largest_branch_fanout = max(largest_branch_fanout, max(branch_points_here))

print("conversation records: %d" % len(conversation_records))
print("messages: %d  (%s)" % (message_total, ", ".join("%s %d" % pair for pair in sorted(messages_per_sender.items()))))
print("conversations containing at least one branch point: %d" % conversations_with_a_branch)
print("branch points in total: %d  (largest: one message with %d children)" % (branch_point_total, largest_branch_fanout))
print("conversation records per month (by created_at):")
for month_label in sorted(conversations_per_month):
    print("  %s  %d" % (month_label, conversations_per_month[month_label]))
