"""
Pure data transformation functions extracted from DocumentBuilder.

These functions contain NO I/O, NO database access, NO logging.
They are deterministic, testable transformations of in-memory data.

Extracted as part of WS-CRAP-005: Testability Refactoring.

NOTE: DocumentBuilder.build() (CC 9) and build_stream() (CC 15) are
almost entirely I/O orchestration (LLM calls, DB persistence, SSE
streaming). The extractable pure logic is limited to:
- Model parameter resolution
- User message assembly
- Progress percentage clamping
"""

import json
from typing import Dict, Any


# ---------------------------------------------------------------------------
# resolve_model_params  (extracted from _prepare_build and build_stream)
# ---------------------------------------------------------------------------

def resolve_model_params(
    options: Dict[str, Any],
    default_model: str,
) -> tuple:
    """
    Resolve model, max_tokens, and temperature from options dict.

    Applies defaults and guards against sentinel values.

    Args:
        options: User-supplied options dict
        default_model: Fallback model name

    Returns:
        Tuple of (model: str, max_tokens: int, temperature: float)
    """
    model = options.get("model") or default_model
    if model in (None, "", "string"):
        model = default_model

    max_tokens = options.get("max_tokens") or 4096

    temperature = options.get("temperature")
    if temperature is None:
        temperature = 0.7

    return model, max_tokens, temperature


# ---------------------------------------------------------------------------
# build_user_message  (extracted from _build_user_message)
# ---------------------------------------------------------------------------

def build_user_message(
    config: Dict[str, Any],
    user_inputs: Dict[str, Any],
    input_docs: Dict[str, Any],
) -> str:
    """
    Build the user message for an LLM call from config, user inputs,
    and input documents.

    Args:
        config: Document type config with 'name' and 'description'
        user_inputs: Dict with optional 'user_query', 'project_description'
        input_docs: Dict of {doc_type: content} for input documents

    Returns:
        Assembled user message string
    """
    parts = []
    parts.append(f"Create a {config['name']}.")

    if config.get("description"):
        parts.append(f"\nDocument purpose: {config['description']}")

    if user_inputs.get("user_query"):
        parts.append(f"\nUser request:\n{user_inputs['user_query']}")

    if user_inputs.get("project_description"):
        parts.append(f"\nProject description:\n{user_inputs['project_description']}")

    if input_docs:
        parts.append("\n\n--- Input Documents ---")
        for doc_type, content in input_docs.items():
            parts.append(
                f"\n### {doc_type}:\n"
                + "`json\n"
                + json.dumps(content, indent=2)
                + "\n"
                + "`"
            )

    parts.append(
        "\n\nRemember: Output ONLY valid JSON matching the schema. No markdown, no prose."
    )

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# compute_stream_progress  (extracted from build_stream progress logic)
# ---------------------------------------------------------------------------

def compute_stream_progress(accumulated_length: int) -> int:
    """
    Compute the streaming progress percentage based on accumulated text length.

    Clamps between 30 and 70 (the streaming range in build_stream).

    Args:
        accumulated_length: Current length of accumulated LLM response text

    Returns:
        Progress percentage (int), between 30 and 70 inclusive
    """
    return min(30 + accumulated_length // 50, 70)


# ---------------------------------------------------------------------------
# should_emit_stream_update  (extracted from build_stream modulo logic)
# ---------------------------------------------------------------------------

def should_emit_stream_update(
    accumulated_length: int,
    chunk_length: int,
) -> bool:
    """
    Determine whether a streaming progress update should be emitted.

    The original logic emits when (accumulated_length % 100 < chunk_length),
    which throttles updates to roughly every 100 characters.

    Args:
        accumulated_length: Current total accumulated text length
        chunk_length: Length of the latest text chunk

    Returns:
        True if a progress update should be emitted
    """
    return (accumulated_length % 100) < chunk_length
