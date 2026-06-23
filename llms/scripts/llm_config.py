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

import json
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


def anthropic_extract_response(data: dict) -> tuple[str, bool, dict]:
    """Return (text, truncated, usage) from an Anthropic messages-API response.

    Per ADR-12 the text extraction may raise (KeyError/IndexError/TypeError)
    on an unexpected shape -- call_llm's shape guard catches it. The truncated
    bool and usage dict must NEVER raise: read with .get chains so a missing
    field yields None, not an exception.
    """
    text = "".join(
        block["text"] for block in data["content"] if block["type"] == "text"
    )
    usage = data.get("usage", {})
    return (
        text,
        data.get("stop_reason") == "max_tokens",
        {
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
        },
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


def openai_extract_response(data: dict) -> tuple[str, bool, dict]:
    """Return (text, truncated, usage) from an OpenAI chat-completions response.

    A null message.content (content-filter / refusal) is raised as KeyError so
    call_llm's shape guard surfaces the raw payload. truncated/usage never raise.
    """
    choice = data["choices"][0]
    text = choice["message"]["content"]
    if text is None:
        raise KeyError("message.content is null")  # caught by call_llm's shape guard
    usage = data.get("usage", {})
    return (
        text,
        choice.get("finish_reason") == "length",
        {
            "input_tokens": usage.get("prompt_tokens"),
            "output_tokens": usage.get("completion_tokens"),
        },
    )


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


def gemini_extract_response(data: dict) -> tuple[str, bool, dict]:
    """Return (text, truncated, usage) from a Gemini generateContent response.

    Safety-blocked responses arrive with no parts; the resulting KeyError is
    caught by call_llm's shape guard, which prints the raw JSON (including the
    block reason) instead of tracebacking. truncated/usage never raise.
    """
    candidate = data["candidates"][0]
    text = candidate["content"]["parts"][0]["text"]
    usage = data.get("usageMetadata", {})
    return (
        text,
        candidate.get("finishReason") == "MAX_TOKENS",
        {
            "input_tokens": usage.get("promptTokenCount"),
            "output_tokens": usage.get("candidatesTokenCount"),
        },
    )


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


class ResponseError(Exception):
    """Marker for a 2xx response call_llm could not turn into text.

    Raised for non-JSON bodies and for 2xx payloads with an unexpected shape
    (safety block, null content, API drift). Empty by design (spec: only empty
    marker exceptions, no behavior-bearing classes); the human-readable detail
    is already printed to stderr at the raise site. Callers catch this to decide
    exit-vs-skip without re-formatting the error.
    """


def call_llm(
    provider_name: str,
    model: str | None,
    system: str | None,
    messages: list[dict],
    max_tokens: int = MAX_TOKENS,
) -> tuple[str, bool, dict]:
    """POST system + messages to the named provider; return (text, truncated, usage).

    system is an explicit parameter (ADR-11): each provider transform places it
    natively; "system" is not a valid role inside messages. The return is the
    (text, truncated, usage) triple (ADR-12): text may have been extracted from
    a truncated response (truncated=True), and usage carries provider-reported
    {"input_tokens", "output_tokens"} (either may be None).

    This shared call_llm owns transport and turning the response into the triple,
    including the shape guard. It deliberately does NOT own caller policy: it does
    not append the truncation marker to the text, does not write any usage log,
    and does not decide exit-vs-skip on error. Each tool (llm.py, workbench.py)
    wraps this and adds its own telemetry and truncation handling.
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

    try:
        data = response.json()
    except ValueError as exc:
        print(
            f"Non-JSON response from {provider_name}: {response.text[:2000]}",
            file=sys.stderr,
        )
        raise ResponseError(provider_name) from exc

    try:
        return provider["extract_response"](data)
    except (KeyError, IndexError, TypeError) as exc:
        # A 2xx with an unexpected shape (safety block, null content, API
        # drift). Surface the raw payload instead of a traceback so the block
        # reason / drift is visible.
        print(
            f"Unexpected response shape from {provider_name} "
            f"({type(exc).__name__}: {exc}); raw JSON follows:",
            file=sys.stderr,
        )
        print(json.dumps(data, indent=2)[:5000], file=sys.stderr)
        raise ResponseError(provider_name) from exc
