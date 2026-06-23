# Provider skeleton for llm.py -- NOT importable; a fill-in template.
# Modeled on the gemini entry because it exercises the most schema features:
# {model} URL templating, nested body extras, role mapping, system workaround.
# Replace every <<...>> using the stage-1 JSON. Delete branches that don't
# apply (marked OPTIONAL).

# ---- two functions: place in CONFIG, after gemini_extract_response ----

def <<provider_key>>_transform_messages(system: str | None,
                                        messages: list[dict]) -> dict:
    """Return <<Provider>>'s body fragment from (system, generic messages)."""
    # CASE system_handling == "top_level_field": do nothing here; put the
    #   field in the table's body via transform return:
    #     body = {"<<body_field>>": shaped_messages}
    #     if system is not None:
    #         body["<<system_field_name>>"] = system
    #     return body
    # CASE system_handling == "system_role_in_messages":
    #     if system is not None:
    #         messages = [{"role": "<<system_role>>", "content": system}, *messages]
    # CASE system_handling == "no_native_support": prepend a tagged user turn
    #   (see gemini_transform_messages for the working example).
    #
    # If message_shape is the plain {"role", "content"} dict, return
    # {"<<body_field>>": messages} directly. Otherwise reshape each message,
    # mapping roles via role_names (e.g. "assistant" -> "<<assistant_role>>").
    raise NotImplementedError("fill from stage-1 request_messages")

def <<provider_key>>_extract_response(data: dict) -> tuple[str, bool, dict]:
    """Return (text, truncated, usage) from a <<Provider>> response.

    Contract (must match the other providers exactly):
    - text: raise KeyError/IndexError/TypeError if absent or null -- call_llm's
      shape guard catches these and dumps the raw JSON. Never return None.
    - truncated: compare <<truncation.field_path>> (via .get, never indexing)
      against "<<truncation.truncated_value>>".
    - usage: read with .get chains only; missing usage yields None values,
      never an exception.
    """
    text = data<<text_path as chained ["..."][0]["..."] indexing>>
    usage = data.get("<<usage parent key>>", {})
    return (text,
            data.get("<<truncation parent>>", ...) == "<<truncated_value>>",
            {"input_tokens": usage.get("<<input_tokens key>>"),
             "output_tokens": usage.get("<<output_tokens key>>")})

# ---- table entry: place inside PROVIDERS, after the gemini entry ----

    "<<provider_key>>": {
        "url_template": "<<url_template>>",            # keep {model} only if model_in_url
        "env_key": "<<ENV_KEY>>",
        # auth.mechanism == "header": put it in auth_header, leave auth_params empty.
        # auth.mechanism == "query":  the reverse. Exactly one is non-empty.
        "auth_header": lambda api_key: {"<<auth.name>>": f"<<auth.value_format>>"},
        "auth_params": lambda api_key: {},
        "extra_headers": <<extra_headers dict, {} if none>>,
        # max_tokens.body_path "max_tokens"            -> {"model": model, "max_tokens": max_tokens}
        # max_tokens.body_path "a.b" (nested)          -> {"a": {"b": max_tokens}}
        # include "model": model here ONLY if model_in_url is false
        "body_extras": lambda model, max_tokens: <<body dict>>,
        "transform_messages": <<provider_key>>_transform_messages,
        "extract_response": <<provider_key>>_extract_response,
        "default_model": "<<default_model>>",
    },
