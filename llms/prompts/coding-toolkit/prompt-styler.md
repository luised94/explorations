อออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออ
FILE: prompt_styler.md
อออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออ

# Prompt Styler
VERSION: 1
UPDATED: 2026-05-27

Meta-prompt. Converts external or draft prompts into the structure
and conventions used by this prompt library.

---

## When to use

- Adapting a prompt found online or from another source
- Formalizing a prompt you've been using informally
- Ensuring a new prompt fits the library's conventions before
  saving it to prompts/

## Prompt

```
Here is a prompt (or prompt idea) I want to add to my prompt
library. Convert it to match my library's conventions.

SOURCE PROMPT:
[paste or describe the prompt]

My library conventions:
- File starts with: # Title, VERSION: N, UPDATED: YYYY-MM-DD
- Brief description of what it is and its category (thinking
  pattern, task module, thread lifecycle, meta-prompt)
- "When to invoke" section: bullet list of situations
- "Prompt" section: the actual prompt text in a code block,
  written as instructions to the LLM
- "Compact form" section: 2-3 sentence version for inline use
- "Conventions" section: rules for how the output should behave
- Optional: "Variants" for domain-specific or situational
  variations
- Tone: direct, imperative, no fluff. Tell the LLM what to do,
  not what it "might consider"
- Length: prompts are concise. The full file should be under 60
  lines unless the prompt genuinely requires more.

Classify it as one of:
  - thinking_pattern: reusable mid-conversation reasoning module
  - task: specific deliverable to produce
  - thread_lifecycle: manages thread transitions
  - meta: operates on other prompts or the library itself

Produce the formatted file. Flag anything in the source prompt
that conflicts with my coding style or interaction preferences
(if those documents are attached).
```

## Compact form

```
Convert this prompt to my library format. Classify as thinking
pattern, task, thread lifecycle, or meta. Match the structure
of my existing prompt files.
```

## Conventions

- The styler should not change the intent of the source prompt,
  only its structure and tone
- If the source prompt contains instructions that conflict with
  developer_profile.md or interaction_modes.md (e.g., suggests
  OOP, uses motivational framing), flag the conflict and suggest
  a revision
- The output should be saveable directly as a .md file in prompts/


อออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออ
FILE: thread_meta_reflector.md
อออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออ

