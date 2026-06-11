# Stage 1 - Provider Research Prompt

Usage (paste the provider's API docs rather than relying on model memory):

    llm.py append "$(cat provider_research_prompt.md)" api_docs_page1.html api_docs_page2.html

Or with a search-capable model/session, send the prompt alone and name the
provider and model where indicated. Fill the two placeholders before sending.

---

You are mapping a chat-completions HTTP API onto a fixed integration schema.

PROVIDER: {{PROVIDER_NAME}}
MODEL:    {{MODEL_STRING}}

Using the documentation provided (or current documentation if you can search),
produce a single JSON object - no prose before or after, no markdown fences -
with exactly these fields:

{
  "provider_key": "lowercase short name used as the table key, e.g. 'mistral'",
  "env_key": "conventional API-key environment variable, e.g. 'MISTRAL_API_KEY'",
  "url_template": "full POST endpoint; write {model} where the model name goes IF it rides in the URL, otherwise a fixed URL",
  "model_in_url": true_or_false,
  "auth": {
    "mechanism": "header" or "query",
    "name": "header or query-parameter name, e.g. 'Authorization' or 'key'",
    "value_format": "exact value with {api_key} placeholder, e.g. 'Bearer {api_key}' or '{api_key}'"
  },
  "extra_headers": { "any static required headers": "their exact values", "...": "empty object if none" },
  "max_tokens": {
    "body_path": "dotted path in the request body, e.g. 'max_tokens' or 'generationConfig.maxOutputTokens'"
  },
  "request_messages": {
    "body_field": "top-level body field holding the conversation, e.g. 'messages' or 'contents'",
    "role_names": { "user": "provider's user role", "assistant": "provider's assistant role" },
    "message_shape": "exact JSON shape of one message, e.g. {\"role\": ..., \"content\": \"text\"} or {\"role\": ..., \"parts\": [{\"text\": ...}]}",
    "system_handling": "one of: 'top_level_field' (name it), 'system_role_in_messages' (name the role), 'no_native_support' (describe the accepted workaround)"
  },
  "response": {
    "text_path": "dotted path with [0] indices to the response text, e.g. 'choices[0].message.content'",
    "text_can_be_null_or_absent": "describe when (tool calls, safety blocks, refusals), or 'no'",
    "truncation": {
      "field_path": "dotted path to the stop/finish reason",
      "truncated_value": "exact value meaning the max-token limit was hit, e.g. 'length' or 'MAX_TOKENS'"
    },
    "usage": {
      "input_tokens_path": "dotted path to prompt/input token count, or null if not reported",
      "output_tokens_path": "dotted path to completion/output token count, or null if not reported"
    }
  },
  "default_model": "{{MODEL_STRING}}",
  "minimal_curl_example": "a one-line curl that would send 'hi' and get a reply, with $API_KEY for the key",
  "confidence_notes": "list anything you are unsure of or could not verify in the documentation given; empty string if fully verified"
}

Rules:
- Every field is required. Use null only where the schema explicitly allows it.
- Do not invent values. Anything not verifiable from the documentation goes in
  confidence_notes, and the corresponding field gets your best guess marked
  there by name.
- The truncation and usage fields matter as much as the happy path: the target
  tool detects truncated responses and logs token usage, so 'unknown' there
  degrades the integration. Look specifically for the stop/finish-reason enum
  and the usage/metadata block in the response examples.
- Output the JSON object and nothing else.
