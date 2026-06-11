You are mapping a chat-completions HTTP API onto a fixed integration schema.

PROVIDER: {{PROVIDER}}

Using the documentation provided (or current documentation if you can search),
produce a single JSON object with exactly the fields shown below.

If no documentation was provided, use your knowledge but flag every field you
cannot verify in confidence_notes.

Output the JSON object and nothing else. If you must use markdown fences,
use ```json. Do not include any prose before or after the JSON.

{
  "provider_key": "lowercase short name used as the table key, e.g. 'mistral'",

  "env_key": "conventional API-key environment variable, e.g. 'MISTRAL_API_KEY'",

  "url_template": "full POST endpoint; write {model} where the model name goes if it rides in the URL, otherwise a fixed URL",

  "auth": {
    "mechanism": "header or query",
    "name": "header or query-parameter name, e.g. 'Authorization' or 'key'",
    "value_format": "exact value with {api_key} placeholder, e.g. 'Bearer {api_key}' or '{api_key}'"
  },

  "extra_headers": {
    "_note": "static required headers as key-value pairs; omit this _note field and leave the object empty {} if none are needed"
  },

  "max_tokens": {
    "body_path": "dotted path in the request body, e.g. 'max_tokens' or 'generationConfig.maxOutputTokens'"
  },

  "request_messages": {
    "body_field": "top-level body field holding the conversation, e.g. 'messages' or 'contents'",
    "role_names": {
      "user": "provider's user role string",
      "assistant": "provider's assistant role string"
    },
    "message_shape": "exact JSON shape of one message, e.g. {\"role\": \"...\", \"content\": \"...\"} or {\"role\": \"...\", \"parts\": [{\"text\": \"...\"}]}",
    "system_handling": {
      "method": "one of: top_level_field | system_role_in_messages | no_native_support",
      "field_or_role": "the field name or role string used, e.g. 'system' for both common cases; null if no_native_support",
      "workaround": "if no_native_support, describe the accepted workaround; null otherwise"
    }
  },

  "response": {
    "text_path": "human-readable dotted path to the response text, e.g. 'choices[0].message.content' -- this is a breadcrumb for a developer, not a parsed expression",
    "text_can_be_null_or_absent": "describe when this happens (tool calls, safety blocks, refusals), or 'no'",
    "truncation": {
      "field_path": "dotted path to the stop/finish reason field",
      "truncated_value": "exact string value meaning the max-token limit was hit, e.g. 'length' or 'MAX_TOKENS'"
    },
    "usage": {
      "input_tokens_path": "dotted path to prompt/input token count, or null if not reported",
      "output_tokens_path": "dotted path to completion/output token count, or null if not reported"
    }
  },

  "default_model": "the provider's flagship or recommended model string; infer from docs if not specified by the user",

  "confidence_notes": [
    "a list of strings, one per uncertain item",
    "name the specific field and what is uncertain",
    "empty array [] if everything is verified from documentation"
  ]
}

Rules:

- Every field is required. Use null only where the schema explicitly allows it
  (auth value_format, system_handling.field_or_role, system_handling.workaround,
  usage paths).

- Do not invent values. Anything not verifiable from the provided documentation
  goes in confidence_notes with the corresponding field named, and the field
  gets your best guess.

- Truncation and usage fields matter as much as the happy path. The target tool
  detects truncated responses and logs token counts, so gaps here degrade the
  integration. Look specifically for the stop/finish-reason enum and the
  usage/metadata block in the API's response examples.
