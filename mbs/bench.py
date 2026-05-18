"""Starter benchmark and CI helpers for MBS."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .compiler import canonical_json, compile_schema, estimate_tokens, load_schema
from .cost import report_cost
from .trace import create_trace
from .validate import validate_output


FAILURE_TYPES = [
    "invalid_json",
    "missing_required_key",
    "invalid_enum",
    "invented_enum",
    "wrong_type",
    "extra_key",
    "semantic_mismatch",
    "language_mismatch",
    "refusal",
    "timeout",
    "overlong_output",
    "prompt_injection_followed",
    "reasoning_prose",
    "prose_wrapped_json",
]


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def run_cases(
    schema: dict[str, Any],
    cases: list[dict[str, Any]],
    model: str = "mock",
    prompt_style: str = "full",
    decoding_mode: str = "local_mock",
    input_language: str | None = None,
    output_language: str | None = None,
    contract_language: str | None = None,
) -> list[dict[str, Any]]:
    """Run local mock benchmark cases. Real model adapters are intentionally separate."""
    contract = compile_schema(
        schema,
        format=prompt_style,
        input_language=input_language,
        output_language=output_language,
        contract_language=contract_language,
    )
    rows: list[dict[str, Any]] = []
    for idx, case in enumerate(cases):
        started = time.time()
        output = case.get("output")
        if output is None:
            output = mock_output(schema, case.get("input", ""))
        validation = validate_output(schema, output)
        expected = case.get("expected_valid_outputs")
        semantic_ok = None
        if expected:
            semantic_ok = _output_matches_expected(validation.get("output"), expected)
            if validation["schema_valid"] and not semantic_ok:
                validation["status"] = "REVIEW"
                validation["errors"].append({"field": "$", "type": "semantic_mismatch", "expected": expected})
        output_tokens = estimate_tokens(canonical_json(validation.get("output")))
        trace = create_trace(
            schema,
            contract,
            validation,
            input_text=case.get("input", ""),
            model=model,
            output_tokens=output_tokens,
        )
        rows.append(
            {
                "case_id": case.get("id", idx),
                "model": model,
                "prompt_style": prompt_style,
                "decoding_mode": decoding_mode,
                "language": language_label(input_language, output_language, contract_language),
                "status": validation["status"],
                "json_valid": validation["json_valid"],
                "schema_valid": validation["schema_valid"],
                "semantic_correct": semantic_ok,
                "failure_type": first_failure_type(validation),
                "latency_s": round(time.time() - started, 4),
                "errors": validation["errors"],
                "warnings": validation["warnings"],
                "tokens": trace["tokens"],
                "trace": trace,
            }
        )
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    if n == 0:
        return {"runs": 0}
    cost = report_cost(rows)
    return {
        "runs": n,
        "avg_retry_count": _avg(rows, "retry_count"),
        "valid_json_rate": _rate(rows, "json_valid"),
        "clean_json_rate": _clean_json_rate(rows),
        "schema_valid_rate": _rate(rows, "schema_valid"),
        "semantic_correct_rate": _rate([r for r in rows if r.get("semantic_correct") is not None], "semantic_correct"),
        "enum_accuracy": _no_error_rate(rows, {"invalid_enum", "invented_enum"}),
        "required_key_accuracy": _no_error_rate(rows, {"missing_required_key"}),
        "extra_key_rate": _warning_rate(rows, {"extra_key"}),
        "avg_latency_s": _avg(rows, "latency_s"),
        "avg_mbs_contract_tokens": _avg_token(rows, "mbs_contract"),
        "avg_verbose_baseline_tokens": _avg_token(rows, "verbose_baseline"),
        "cost_per_valid_output_tokens": cost["cost_per_valid_output_tokens"],
        "failure_types": _failure_counts(rows),
    }


def first_failure_type(validation: dict[str, Any]) -> str | None:
    if validation.get("errors"):
        return validation["errors"][0].get("type")
    if validation.get("warnings"):
        return validation["warnings"][0].get("type")
    return None


def mock_output(schema: dict[str, Any], input_text: str = "") -> dict[str, Any]:
    output: dict[str, Any] = {}
    properties = schema.get("properties", {})
    for name, spec in properties.items():
        output[name] = _mock_value(name, spec, input_text)
    return output


def _mock_value(name: str, spec: dict[str, Any], input_text: str) -> Any:
    enum = spec.get("enum")
    if enum:
        upper = input_text.upper()
        for value in enum:
            if str(value).upper() in upper:
                return value
        if name == "tool":
            if any(term in upper for term in ("TAKEOVER", "SECURITY", "URGENT", "ESCALATE")) and "escalate_case" in enum:
                return "escalate_case"
            if any(term in upper for term in ("INVOICE", "STATUS", "LOOKUP", "SEARCH")) and "search_customer" in enum:
                return "search_customer"
        if name == "category":
            if any(term in upper for term in ("TAKEOVER", "PASSWORD", "SECURITY", "COMPROMISED")) and "SECURITY" in enum:
                return "SECURITY"
            if any(term in upper for term in ("INVOICE", "BILL", "BILLING", "CHARGE")) and "BILLING" in enum:
                return "BILLING"
            if any(term in upper for term in ("BUG", "ERROR", "CRASH")) and "BUG" in enum:
                return "BUG"
            if any(term in upper for term in ("ACCOUNT", "SIGN IN", "LOGIN")) and "ACCOUNT" in enum:
                return "ACCOUNT"
        if name in {"next_action", "action"}:
            if any(term in upper for term in ("TAKEOVER", "SECURITY", "URGENT", "ESCALATE")) and "ESCALATE" in enum:
                return "ESCALATE"
            if any(term in upper for term in ("INVOICE", "BILL", "BILLING", "CHARGE")) and "CREATE_TICKET" in enum:
                return "CREATE_TICKET"
            if any(term in upper for term in ("MISSING", "UNCLEAR", "UNKNOWN")) and "REQUEST_INFO" in enum:
                return "REQUEST_INFO"
        if name in {"decision", "action", "recommendation"}:
            for preferred in ("REVIEW", "ESCALATE", "BLOCK", "TOOL_CALL", "ANSWER"):
                if preferred in enum:
                    return preferred
        if name in {"risk_level", "priority", "severity"}:
            for preferred in ("HIGH", "MEDIUM", "LOW"):
                if preferred in enum:
                    return preferred
        return enum[0]
    t = spec.get("type", "string")
    if t == "boolean":
        return False
    if t == "integer":
        return 0
    if t == "number":
        return 0.0
    if t == "array":
        return []
    if t == "object":
        return {
            child_name: _mock_value(child_name, child_spec if isinstance(child_spec, dict) else {}, input_text)
            for child_name, child_spec in spec.get("properties", {}).items()
        }
    if "reason" in name or "notes" in name:
        return "Generated by local MBS mock adapter."
    return f"{name}_value"


def _output_matches_expected(output: Any, expected: Any) -> bool:
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
    for key, value in expected.items():
        if key not in output or output[key] != value:
            return False
    return True


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


def _rate(rows: list[dict[str, Any]], key: str) -> float | None:
    if not rows:
        return None
    return round(sum(1 for r in rows if r.get(key)) / len(rows), 4)


def _no_error_rate(rows: list[dict[str, Any]], error_types: set[str]) -> float | None:
    if not rows:
        return None
    clean = 0
    for row in rows:
        errors = row.get("errors") or row.get("trace", {}).get("errors", [])
        if not any(err.get("type") in error_types for err in errors):
            clean += 1
    return round(clean / len(rows), 4)


def _warning_rate(rows: list[dict[str, Any]], warning_types: set[str]) -> float | None:
    if not rows:
        return None
    flagged = 0
    for row in rows:
        warnings = row.get("warnings", [])
        if any(warn.get("type") in warning_types for warn in warnings):
            flagged += 1
    return round(flagged / len(rows), 4)


def _clean_json_rate(rows: list[dict[str, Any]]) -> float | None:
    """Rate of rows that were valid raw JSON, not extracted from prose/reasoning."""
    if not rows:
        return None
    clean = 0
    noisy_types = {"prose_wrapped_json", "reasoning_prose"}
    for row in rows:
        if not row.get("json_valid"):
            continue
        errors = row.get("errors") or []
        warnings = row.get("warnings") or []
        has_noisy_error = any(isinstance(err, dict) and err.get("type") in noisy_types for err in errors)
        has_noisy_warning = any(isinstance(warn, dict) and warn.get("type") in noisy_types for warn in warnings)
        if not has_noisy_error and not has_noisy_warning:
            clean += 1
    return round(clean / len(rows), 4)


def _avg(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [float(row[key]) for row in rows if row.get(key) is not None]
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def _avg_token(rows: list[dict[str, Any]], key: str) -> float | None:
    values = []
    for row in rows:
        tokens = row.get("tokens", {})
        if key in tokens:
            values.append(float(tokens[key]))
    if not values:
        return None
    return round(sum(values) / len(values), 3)


def _failure_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        ft = row.get("failure_type")
        if ft:
            counts[ft] = counts.get(ft, 0) + 1
    return counts


def language_label(
    input_language: str | None = None,
    output_language: str | None = None,
    contract_language: str | None = None,
) -> str:
    if not input_language and not output_language and not contract_language:
        return "default"
    return f"in={input_language or 'default'};out={output_language or 'default'};contract={contract_language or 'default'}"


def run_benchmark(
    schema_path: str | Path,
    cases_path: str | Path,
    model: str = "mock",
    prompt_style: str = "full",
    decoding_mode: str = "local_mock",
    input_language: str | None = None,
    output_language: str | None = None,
    contract_language: str | None = None,
) -> dict[str, Any]:
    schema = load_schema(schema_path)
    cases = load_jsonl(cases_path)
    rows = run_cases(
        schema,
        cases,
        model=model,
        prompt_style=prompt_style,
        decoding_mode=decoding_mode,
        input_language=input_language,
        output_language=output_language,
        contract_language=contract_language,
    )
    return {
        "schema": str(schema_path),
        "cases": str(cases_path),
        "model": model,
        "prompt_style": prompt_style,
        "decoding_mode": decoding_mode,
        "language": language_label(input_language, output_language, contract_language),
        "summary": summarize(rows),
        "rows": rows,
    }


def run_benchmark_matrix(
    schema_paths: str | Path | list[str | Path],
    cases_path: str | Path,
    models: list[str],
    prompt_styles: list[str] | None = None,
    decoding_modes: list[str] | None = None,
    languages: list[str | dict[str, str] | None] | None = None,
) -> dict[str, Any]:
    """Run a small reproducible matrix for local/dev benchmark validation."""
    schemas = schema_paths if isinstance(schema_paths, list) else [schema_paths]
    prompt_styles = prompt_styles or ["full"]
    decoding_modes = decoding_modes or ["local_mock"]
    languages = languages or [None]
    runs: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []

    for schema_path in schemas:
        for model in models:
            for prompt_style in prompt_styles:
                for decoding_mode in decoding_modes:
                    for language in languages:
                        lang_kwargs = _language_kwargs(language)
                        result = run_benchmark(
                            schema_path,
                            cases_path,
                            model=model,
                            prompt_style=prompt_style,
                            decoding_mode=decoding_mode,
                            **lang_kwargs,
                        )
                        summary = {
                            "schema": str(schema_path),
                            "model": model,
                            "prompt_style": prompt_style,
                            "decoding_mode": decoding_mode,
                            "language": language_label(**lang_kwargs),
                            **result["summary"],
                        }
                        runs.append(summary)
                        for row in result["rows"]:
                            rows.append({"schema": str(schema_path), **row})

    summary = summarize(rows)
    summary["matrix_runs"] = len(runs)
    summary["schemas"] = len(schemas)
    summary["models"] = len(models)
    return {"summary": summary, "runs": runs, "rows": rows}


def _language_kwargs(language: str | dict[str, str] | None) -> dict[str, str | None]:
    if language is None:
        return {"input_language": None, "output_language": None, "contract_language": None}
    if isinstance(language, str):
        return {"input_language": language, "output_language": language, "contract_language": "en"}
    return {
        "input_language": language.get("input_language"),
        "output_language": language.get("output_language"),
        "contract_language": language.get("contract_language"),
    }
