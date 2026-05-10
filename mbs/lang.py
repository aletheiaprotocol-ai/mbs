"""MBS-Lang helpers."""

from __future__ import annotations

from typing import Any

from .compiler import compile_schema, estimate_tokens


def compile_language_contract(
    schema: dict[str, Any],
    input_language: str,
    output_language: str,
    contract_language: str = "en",
) -> dict[str, Any]:
    """Compile an MBS-Lang hybrid contract."""
    result = compile_schema(
        schema,
        input_language=input_language,
        output_language=output_language,
        contract_language=contract_language,
    )
    english = compile_schema(
        schema,
        input_language="en",
        output_language="en",
        contract_language=contract_language,
    )
    result["token_fairness_ratio"] = token_fairness_ratio(result["prompt"], english["prompt"])
    result["english_baseline_tokens"] = english["token_estimate"]
    return result


def token_fairness_ratio(non_english_prompt: str, english_prompt: str) -> float | None:
    english_tokens = estimate_tokens(english_prompt)
    if english_tokens == 0:
        return None
    return round(estimate_tokens(non_english_prompt) / english_tokens, 3)
