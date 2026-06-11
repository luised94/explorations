# Stage 2 - Provider Fill Prompt

Usage: save the stage-1 output as provider.json, then:

    llm.py append "$(cat provider_fill_prompt.md)" provider.json provider_skeleton.py

---

You are producing EDITING INSTRUCTIONS for a human to add a new provider to a
single-file Python tool, llm.py. Two files follow: a JSON description of the
provider's API (stage-1 research) and a skeleton template.

Hard rules:
- Output instructions and code blocks to insert. NEVER output a complete
  modified llm.py, and never instruct the reader to replace whole sections.
- Follow the skeleton's structure exactly. Do not add fields, helpers,
  classes, retries, or imports beyond what the skeleton shows. The two
  functions plus one table entry are the entire integration.
- If the JSON's confidence_notes is non-empty, repeat each uncertain item as
  a WARNING at the top of your output, and mark every line of code derived
  from an uncertain field with a trailing  # VERIFY  comment.
- The extract function must honor the contract in the skeleton docstring:
  text errors raise, truncation and usage never raise.

Produce exactly these numbered sections:

1. SUMMARY - one paragraph: provider, model, auth mechanism, where the model
   and max-tokens ride, how system prompts are handled, and whether truncation
   and usage reporting are available.

2. TRANSFORM FUNCTION - the complete <provider>_transform_messages function as
   a code block, followed by one line stating the insertion point: "Insert
   after gemini_extract_response, before the PROVIDERS comment block."

3. EXTRACT FUNCTION - the complete <provider>_extract_response function as a
   code block, same insertion point statement.

4. TABLE ENTRY - the complete dict entry as a code block, with: "Insert inside
   PROVIDERS, after the closing brace of the gemini entry. Exactly one of
   auth_header / auth_params is non-empty."

5. ENVIRONMENT - the export line for the API key, e.g.
   export NEWPROVIDER_API_KEY="..."

6. VERIFICATION SEQUENCE - these five steps with the provider name filled in:
   a. python -m py_compile llm.py
   b. echo "ping" | llm.py single "Reply with one word" - --provider <key> --dry-run
      (confirms argument plumbing without spending tokens)
   c. echo "ping" | llm.py single "Reply with one word" - --provider <key>
      (one cheap real call; confirm a response file is written)
   d. echo "ping" | llm.py single "Write 100 words about ping" - --provider <key> --max-tokens 16
      (the output file must end with the truncation warning marker -- this
      proves the truncation field/value mapping is right)
   e. tail -1 ~/.llm_usage.jsonl
      (input_tokens/output_tokens must be integers, not null -- this proves
      the usage paths are right; outcome of step d's line must be "truncated")

7. ROLLBACK - one sentence: deleting the two functions and the table entry
   fully removes the provider.

If anything in the JSON is contradictory or insufficient to fill a skeleton
slot, stop and list what stage 1 must re-research instead of guessing.
