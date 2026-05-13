"""Adapters for converting external provider responses into MBS rows."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .bench import first_failure_type, language_label, load_jsonl, summarize
from .compiler import canonical_json, compile_schema, estimate_tokens, load_schema
from .trace import create_trace
from .validate import validate_output


OUTPUT_KEYS = ("output", "response", "content", "arguments", "tool_arguments")


def adapt_response_jsonl(
    schema_path: str | Path,
    responses_path: str | Path,
    *,
    cases_path: str | Path | None = None,
    model: str | None = None,
    prompt_style: str = "full",
    decoding_mode: str = "provider_response_file",
    input_language: str | None = None,
    output_language: str | None = None,
    contract_language: str | None = None,
) -> dict[str, Any]:
    """Convert provider-response JSONL into an MBS benchmark payload.

    Each JSONL row may contain:

    - `case_id` or `id`
    - `input`
    - `output`, `response`, `content`, `arguments`, or `tool_arguments`
    - `expected_valid_outputs` for semantic checks
    - `model`, `prompt_style`, `decoding_mode`, `language`
    - `tokens` and `latency_s`

    If `cases_path` is supplied, cases are merged by `case_id`/`id` and then by
    row order. Response rows override case metadata.
    """
    schema = load_schema(schema_path)
    contract = compile_schema(
        schema,
        format=prompt_style,
        input_language=input_language,
        output_language=output_language,
        contract_language=contract_language,
    )
    responses = load_jsonl(responses_path)
    cases = load_jsonl(cases_path) if cases_path else []
    case_by_id = _index_cases(cases)
    rows: list[dict[str, Any]] = []
    for idx, response in enumerate(responses):
        case = _matching_case(response, cases, case_by_id, idx)
        merged = {**case, **response}
        started = time.time()
        row_model = str(merged.get("model") or model or "provider-response")
        row_prompt_style = str(merged.get("prompt_style") or prompt_style)
        row_decoding_mode = str(merged.get("decoding_mode") or decoding_mode)
        row_language = str(
            merged.get("language")
            or language_label(input_language=input_language, output_language=output_language, contract_language=contract_language)
        )
        raw_output = _extract_output(merged)
        validation = validate_output(schema, raw_output)
        semantic_ok = _semantic_result(validation.get("output"), merged.get("expected_valid_outputs"))
        if semantic_ok is False and validation["schema_valid"]:
            validation["status"] = "REVIEW"
            validation["errors"].append(
                {"field": "$", "type": "semantic_mismatch", "expected": merged.get("expected_valid_outputs")}
            )
        output_tokens = _output_tokens(merged, validation.get("output"))
        trace = create_trace(
            schema,
            contract,
            validation,
            input_text=str(merged.get("input") or ""),
            model=row_model,
            output_tokens=output_tokens,
        )
        trace["tokens"].update(_token_overrides(merged.get("tokens")))
        rows.append(
            {
                "schema": str(schema_path),
                "case_id": merged.get("case_id", merged.get("id", idx)),
                "model": row_model,
                "prompt_style": row_prompt_style,
                "decoding_mode": row_decoding_mode,
                "language": row_language,
                "status": validation["status"],
                "json_valid": validation["json_valid"],
                "schema_valid": validation["schema_valid"],
                "semantic_correct": semantic_ok,
                "failure_type": first_failure_type(validation),
                "latency_s": round(float(merged.get("latency_s", time.time() - started)), 4),
                "errors": validation["errors"],
                "warnings": validation["warnings"],
                "tokens": trace["tokens"],
                "trace": trace,
            }
        )
    return {
        "schema": str(schema_path),
        "responses": str(responses_path),
        "cases": str(cases_path) if cases_path else None,
        "model": model or "provider-response",
        "prompt_style": prompt_style,
        "decoding_mode": decoding_mode,
        "language": language_label(input_language, output_language, contract_language),
        "summary": summarize(rows),
        "rows": rows,
    }


def _extract_output(row: dict[str, Any]) -> Any:
    for key in OUTPUT_KEYS:
        if key in row:
            return row[key]
    tool_call = row.get("tool_call")
    if isinstance(tool_call, dict):
        if "arguments" in tool_call:
            return tool_call["arguments"]
        function = tool_call.get("function")
        if isinstance(function, dict) and "arguments" in function:
            return function["arguments"]
    tool_calls = row.get("tool_calls")
    if isinstance(tool_calls, list) and tool_calls:
        first = tool_calls[0]
        if isinstance(first, dict):
            return _extract_output({"tool_call": first})
    return ""


def _index_cases(cases: list[dict[str, Any]]) -> dict[Any, dict[str, Any]]:
    indexed: dict[Any, dict[str, Any]] = {}
    for case in cases:
        if "case_id" in case:
            indexed[case["case_id"]] = case
        if "id" in case:
            indexed[case["id"]] = case
    return indexed


def _matching_case(
    response: dict[str, Any], cases: list[dict[str, Any]], case_by_id: dict[Any, dict[str, Any]], idx: int
) -> dict[str, Any]:
    for key in ("case_id", "id"):
        if key in response and response[key] in case_by_id:
            return case_by_id[response[key]]
    if idx < len(cases):
        return cases[idx]
    return {}


def _semantic_result(output: Any, expected: Any) -> bool | None:
    if expected is None:
        return None
    if not isinstance(output, dict):
        return False
    if isinstance(expected, dict):
        return _dict_matches_subset(output, expected)
    if not isinstance(expected, list):
        expected = [expected]
    flat_values = set(_flatten_values(output))
    for item in expected:
        if isinstance(item, dict) and _dict_matches_subset(output, item):
            return True
        if item in flat_values:
            return True
    return False


def _dict_matches_subset(output: dict[str, Any], expected: dict[str, Any]) -> bool:
    return all(key in output and output[key] == value for key, value in expected.items())


def _flatten_values(value: Any) -> list[Any]:
    if isinstance(value, dict):
        values: list[Any] = []
        for child in value.values():
            values.extend(_flatten_values(child))
        return values
    if isinstance(value, list):
        values = []
        for child in value:
            values.extend(_flatten_values(child))
        return values
    return [value]


def _output_tokens(row: dict[str, Any], output: Any) -> int:
    tokens = row.get("tokens")
    if isinstance(tokens, dict) and tokens.get("output") is not None:
        return int(tokens["output"])
    if isinstance(tokens, int):
        return tokens
    return estimate_tokens(canonical_json(output))


def _token_overrides(tokens: Any) -> dict[str, int]:
    if not isinstance(tokens, dict):
        return {}
    return {str(key): int(value) for key, value in tokens.items() if isinstance(value, int | float)}