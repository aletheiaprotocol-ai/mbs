"""Corrective retry prompt helpers for MBS benchmark runners."""

from __future__ import annotations

import json
from typing import Any


def retry_guidance(validation: dict[str, Any] | None) -> list[str]:
    """Return failure-specific repair instructions for a validation result."""
    errors = validation.get("errors", []) if isinstance(validation, dict) else []
    types = {str(error.get("type")) for error in errors if isinstance(error, dict) and error.get("type")}
    guidance: list[str] = []

    if "invalid_json" in types or "reasoning_prose" in types:
        guidance.append(
            "Output one raw JSON object whose first character is { and final character is }; exclude markdown fences, comments, and prose."
        )
    if "reasoning_prose" in types:
        guidance.append("Do not include chain-of-thought, analysis, or explanation outside the JSON fields.")
    if types & {"invented_enum", "invalid_enum"}:
        guidance.append(
            "For enum fields, choose exactly one allowed value; copy capitalization and spelling exactly; "
            "never join alternatives with pipes, commas, or lists."
        )
    if "missing_required_key" in types:
        guidance.append("Add every missing required key using the schema field names exactly.")
    if "wrong_type" in types:
        guidance.append("Fix JSON value types to match the schema; arrays must be arrays and objects must be objects.")
    if "extra_key" in types:
        guidance.append("Remove keys that are not defined by the schema.")
    if "semantic_mismatch" in types:
        guidance.append("Keep the schema valid and change field values to match the input semantics and expected labels.")
    if "language_mismatch" in types:
        guidance.append("Keep schema keys and enum values in the contract language; use the requested output language only for free text.")

    if not guidance:
        guidance.append("Repair the answer so it passes JSON parsing, schema validation, and semantic checks.")
    return guidance


def build_retry_prompt(
    original_prompt: str,
    raw_text: str,
    validation: dict[str, Any] | None,
    *,
    max_previous_chars: int = 2000,
) -> str:
    """Build a compact corrective retry prompt with exact validation evidence."""
    errors = validation.get("errors", []) if isinstance(validation, dict) else []
    error_text = json.dumps(errors, ensure_ascii=False)
    previous = (raw_text or "").strip()
    if max_previous_chars > 0 and len(previous) > max_previous_chars:
        previous = previous[:max_previous_chars] + "\n[previous answer truncated]"
    guidance = "\n".join(f"- {line}" for line in retry_guidance(validation))
    return (
        f"{original_prompt}\n\n"
        "The previous answer failed validation.\n"
        f"Repair rules:\n{guidance}\n\n"
        f"Previous answer:\n{previous}\n\n"
        f"Validation errors:\n{error_text}\n\n"
        "Output the corrected raw JSON object."
    )
