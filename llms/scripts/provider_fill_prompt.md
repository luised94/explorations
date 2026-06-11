You are adding a new LLM provider to llm.py. A JSON description of the provider's API follows at the end. Your job: write two functions and one table entry, following the reference material below exactly.

If the JSON's confidence_notes array is non-empty:
- Repeat every uncertain item as a WARNING line at the very top of your output.
- Mark every line of code derived from an uncertain field with a trailing # VERIFY comment.
- If anything is contradictory or insufficient to fill a required slot, STOP and list what must be re-researched instead of guessing.

------------------------------------------------------------------------
REFERENCE: OpenAI provider (follow this pattern exactly)
------------------------------------------------------------------------

Transform function -- reshapes (system, messages) into the provider's body fragment:

    def openai_transform_messages(system: str | None, messages: list[dict]) -> dict:
        """Return OpenAI's body fragment: system rides in the messages array."""
        if system is not None:
            messages = [{"role": "system", "content": system}, *messages]
        return {"messages": messages}

Extract function -- pulls (text, truncated, usage) from the provider's response JSON:

    def openai_extract_response(data: dict) -> tuple[str, bool, dict]:
        """Return (text, truncated, usage) from an OpenAI chat-completions response."""
        choice = data["choices"][0]
        text = choice["message"]["content"]
        if text is None:
            raise KeyError("message.content is null")
        usage = data.get("usage", {})
        return (text, choice.get("finish_reason") == "length",
                {"input_tokens": usage.get("prompt_tokens"),
                 "output_tokens": usage.get("completion_tokens")})

Table entry in the PROVIDERS dict:

    "openai": {
        "url_template": "https://api.openai.com/v1/chat/completions",
        "env_key": "OPENAI_API_KEY",
        "auth_header": lambda api_key: {"Authorization": f"Bearer {api_key}"},
        "auth_params": lambda api_key: {},
        "extra_headers": {},
        "body_extras": lambda model, max_tokens: {"model": model, "max_tokens": max_tokens},
        "transform_messages": openai_transform_messages,
        "extract_response": openai_extract_response,
        "default_model": "gpt-4o",
    },

------------------------------------------------------------------------
PROVIDER TABLE FIELD CONTRACT
------------------------------------------------------------------------

Each PROVIDERS entry must have ALL of these fields:

  url_template       POST endpoint; may contain a {model} placeholder
  env_key            environment variable holding the API key
  auth_header        function: api_key -> header dict ({} if auth is not header-based)
  auth_params        function: api_key -> query-param dict ({} if auth is not query-based)
  extra_headers      static provider-required headers ({} if none)
  body_extras        function: (model, max_tokens) -> dict merged into the request body
  transform_messages function: (system or None, messages list) -> provider body fragment
  extract_response   function: response JSON -> (text, truncated, usage)
  default_model      model string used when --model is not given

Exactly one of auth_header / auth_params must return a non-empty dict.

------------------------------------------------------------------------
EXTRACT FUNCTION CONTRACT
------------------------------------------------------------------------

Signature: (data: dict) -> tuple[str, bool, dict]

Returns (text, truncated, usage) where:

  text       The response string. RAISE on null or missing -- KeyError,
             IndexError, TypeError are caught upstream by call_llm, which
             prints the raw JSON and logs a "shape" outcome.
  truncated  bool. NEVER RAISE. Return False if the field is absent.
  usage      {"input_tokens": int|None, "output_tokens": int|None}.
             NEVER RAISE. Use .get() so missing keys become None.

------------------------------------------------------------------------
OUTPUT FORMAT
------------------------------------------------------------------------

Do not output a complete modified llm.py. Do not add fields, helpers,
classes, retries, or imports beyond what the reference shows. The two
functions plus one table entry are the entire integration.

Produce exactly these sections:

1. SUMMARY
   One paragraph: provider name, default model, auth mechanism, where
   model and max-tokens ride in the body, how system prompts are handled,
   and whether truncation detection and usage reporting are available.

2. TRANSFORM FUNCTION
   The complete <provider>_transform_messages function as a code block.
   State the insertion point: "Insert after the last extract function,
   before the PROVIDERS dict."

3. EXTRACT FUNCTION
   The complete <provider>_extract_response function as a code block.
   Same insertion point (directly after the transform function).

4. TABLE ENTRY
   The complete PROVIDERS dict entry as a code block.
   State: "Insert inside PROVIDERS, after the last existing entry."
   Note which of auth_header / auth_params is non-empty.

5. ENVIRONMENT
   The shell export line, e.g.:  export NEWPROVIDER_API_KEY="..."

6. VERIFICATION SEQUENCE
   Fill in the provider key for each step:
   a. python -m py_compile llm.py
   b. echo "ping" | python llm.py single "Reply with one word" - \
        --provider <key> --dry-run
   c. echo "ping" | python llm.py single "Reply with one word" - \
        --provider <key>
   d. echo "ping" | python llm.py single "Write 100 words about ping" - \
        --provider <key> --max-tokens 16
      (output file must end with the truncation warning marker)
   e. tail -1 ~/.llm_usage.jsonl
      (input_tokens and output_tokens must be integers, not null;
       outcome of step d's record must be "truncated")

------------------------------------------------------------------------
STAGE-1 RESEARCH JSON (the provider to integrate)
------------------------------------------------------------------------

<paste JSON here>
