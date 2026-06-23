"""Provider configuration and the generic call_llm function.

Shared module for the toolkit (llm.py, workbench.py). Provider differences
are data: each entry in PROVIDERS describes how to authenticate, how to
shape the request body, and how to pull text out of the response. call_llm
has one code path for all providers.

IMPORT-SAFETY INVARIANT (do not break): importing this module must have no
side effects. Module top level holds only constants, pure functions, and the
PROVIDERS dict -- no argparse, no I/O, no network, no prints, no env reads at
import time. Environment is read inside call_llm, not here. This is what lets
llm.py and workbench.py import the module with `import llm_config` and call
through it as `llm_config.call_llm(...)` / `llm_config.PROVIDERS`.
"""

import os
import sys

import httpx

MAX_TOKENS = 4096
TIMEOUT_SECONDS = 120.0


# --- TRANSFORM ---
# Pure functions referenced by name in the provider table below.
# They take data, return data. No IO.


def anthropic_transform_messages(system: str | None, messages: list[dict]) -> dict:
    """Place system in Anthropic's top-level system field; messages carries the chat.

    Per ADR-11 system arrives as an explicit parameter, not a role inside the
    messages list. "system" is not a valid role in the generic messages list.
    """
    body: dict = {"messages": messages}
    if system:
        body["system"] = system
    return body


def anthropic_extract_response(data: dict) -> str:
    """Concatenate the text blocks from an Anthropic messages-API response."""
    return "".join(
        block["text"] for block in data["content"] if block["type"] == "text"
    )


def openai_transform_messages(system: str | None, messages: list[dict]) -> dict:
    """Prepend system as OpenAI's leading system-role message; chat follows.

    Per ADR-11 system arrives as a parameter; OpenAI's wire format wants it as
    a {"role": "system"} entry at the front of the array, so we add it here
    rather than expecting it pre-baked into messages.
    """
    if system:
        return {"messages": [{"role": "system", "content": system}, *messages]}
    return {"messages": messages}


def openai_extract_response(data: dict) -> str:
    """Pull the response text from an OpenAI chat-completions response."""
    return data["choices"][0]["message"]["content"]


def gemini_transform_messages(system: str | None, messages: list[dict]) -> dict:
    """Reshape generic messages into Gemini's contents/parts format with role mapping.

    Per ADR-11 system arrives as a parameter. Gemini has no system role in this
    endpoint shape, so a non-empty system is folded in as a leading user turn.
    """
    contents = []
    if system:
        contents.append({"role": "user", "parts": [{"text": f"[System] {system}"}]})
    for m in messages:
        role = "model" if m["role"] == "assistant" else m["role"]
        contents.append({"role": role, "parts": [{"text": m["content"]}]})
    return {"contents": contents}


def gemini_extract_response(data: dict) -> str:
    """Pull the response text from a Gemini generateContent response."""
    return data["candidates"][0]["content"]["parts"][0]["text"]


# To add a new provider: add an entry here following the pattern below.
# Then add its env var name. Each entry needs ALL of these fields (use
# lambda-returning-{} for auth mechanisms the provider doesn't use):
#   url_template       POST endpoint; may contain a {model} placeholder
#   env_key            environment variable holding the API key
#   auth_header        function: api_key -> header dict ({} if auth is not header-based)
#   auth_params        function: api_key -> query-param dict ({} if auth is not query-based)
#                      (exactly one of auth_header / auth_params is non-empty)
#   extra_headers      static provider-required headers ({} if none)
#   body_extras        function: (model, max_tokens) -> dict merged top-level into
#                      the body (model name, token limit -- wherever the provider
#                      wants them)
#   transform_messages function: (system: str|None, messages) -> provider body
#                      fragment; system is explicit (ADR-11), not a list role
#   extract_response   function: response JSON -> (text, truncated, usage); text
#                      extraction may raise, truncated/usage must never raise
#   default_model      model string used when --model is not given (snapshots age)
PROVIDERS: dict = {
    "anthropic": {
        "url_template": "https://api.anthropic.com/v1/messages",
        "env_key": "ANTHROPIC_API_KEY",
        "auth_header": lambda api_key: {"x-api-key": api_key},
        "auth_params": lambda api_key: {},
        "extra_headers": {"anthropic-version": "2023-06-01"},
        "body_extras": lambda model, max_tokens: {
            "model": model,
            "max_tokens": max_tokens,
        },
        "transform_messages": anthropic_transform_messages,
        "extract_response": anthropic_extract_response,
        "default_model": "claude-sonnet-4-20250514",
    },
    "openai": {
        "url_template": "https://api.openai.com/v1/chat/completions",
        "env_key": "OPENAI_API_KEY",
        "auth_header": lambda api_key: {"Authorization": f"Bearer {api_key}"},
        "auth_params": lambda api_key: {},
        "extra_headers": {},
        "body_extras": lambda model, max_tokens: {
            "model": model,
            "max_tokens": max_tokens,
        },
        "transform_messages": openai_transform_messages,
        "extract_response": openai_extract_response,
        "default_model": "gpt-4o",
    },
    "gemini": {
        "url_template": (
            "https://generativelanguage.googleapis.com/v1beta/"
            "models/{model}:generateContent"
        ),
        "env_key": "GEMINI_API_KEY",
        "auth_header": lambda api_key: {"x-goog-api-key": api_key},
        "auth_params": lambda api_key: {},
        "extra_headers": {},
        "body_extras": lambda model, max_tokens: {
            "generationConfig": {"maxOutputTokens": max_tokens}
        },
        "transform_messages": gemini_transform_messages,
        "extract_response": gemini_extract_response,
        "default_model": "gemini-2.0-flash",
    },
}


# --- IO ---


def call_llm(
    provider_name: str,
    model: str | None,
    system: str | None,
    messages: list[dict],
    max_tokens: int = MAX_TOKENS,
) -> str:
    """POST messages to the named provider and return the response text.

    system is an explicit parameter (ADR-11): each provider transform places it
    natively. "system" is not a valid role inside messages.
    """
    provider = PROVIDERS[provider_name]

    api_key = os.environ.get(provider["env_key"])
    if api_key is None:
        print(
            f"Missing API key: set the {provider['env_key']} environment variable.",
            file=sys.stderr,
        )
        sys.exit(1)

    model = model or provider["default_model"]
    url = provider["url_template"].format(model=model)
    body = {
        **provider["transform_messages"](system, messages),
        **provider["body_extras"](model, max_tokens),
    }
    headers = {
        "content-type": "application/json",
        **provider["auth_header"](api_key),
        **provider["extra_headers"],
    }

    response = httpx.post(
        url,
        params=provider["auth_params"](api_key),
        json=body,
        headers=headers,
        timeout=TIMEOUT_SECONDS,
    )
    if response.status_code >= 400:
        # Print here so error formatting lives in one place; raise so the
        # caller decides whether to exit (single-call scripts) or skip and
        # continue (batch scripts).
        print(f"HTTP {response.status_code}: {response.text}", file=sys.stderr)
        response.raise_for_status()

    return provider["extract_response"](response.json())
