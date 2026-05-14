"""Threshold gates for MBS benchmark reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .report import aggregate_results, trace_errors


DEFAULT_THRESHOLDS = {
    "min_rows": 1,
    "min_traceable_case_rows": None,
    "min_total_runs": 1,
    "min_models": 1,
    "min_schemas": 1,
    "min_schema_valid_rate": 0.95,
    "min_semantic_correct_rate": 0.90,
    "min_clean_json_rate": 0.90,
    "max_missing_trace_rows": 0,
    "max_uncheckable_result_rows": 0,
    "max_infra_failed_rows": 0,
}


def load_gate_config(path: str | Path | None) -> dict[str, Any]:
    """Load a JSON/YAML gate config or return default thresholds."""
    if not path:
        return {"thresholds": dict(DEFAULT_THRESHOLDS)}
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() in {".yaml", ".yml"}:
        config = _load_yaml_text(text)
    else:
        config = json.loads(text)
    if not isinstance(config, dict):
        raise ValueError("MBS gate config must be an object")
    thresholds = dict(DEFAULT_THRESHOLDS)
    thresholds.update(config.get("thresholds") or {})
    return {**config, "thresholds": thresholds}


def evaluate_gate(
    paths: list[str | Path],
    *,
    config: dict[str, Any] | None = None,
    exclude_infra: bool = False,
) -> dict[str, Any]:
    """Evaluate aggregate MBS results against defensive thresholds."""
    config = config or {"thresholds": dict(DEFAULT_THRESHOLDS)}
    thresholds = dict(DEFAULT_THRESHOLDS)
    thresholds.update(config.get("thresholds") or {})
    report = aggregate_results(paths, exclude_infra=exclude_infra)
    summary = report.get("summary", {})
    failures: list[dict[str, Any]] = []

    _check_min(failures, summary, "mean_schema_valid_rate", thresholds.get("min_schema_valid_rate"))
    _check_min(failures, summary, "mean_semantic_correct_rate", thresholds.get("min_semantic_correct_rate"))
    _check_min(failures, summary, "mean_clean_json_rate", thresholds.get("min_clean_json_rate"))
    _check_min(failures, summary, "rows", thresholds.get("min_rows"))
    _check_min(failures, summary, "traceable_case_rows", thresholds.get("min_traceable_case_rows"))
    _check_min(failures, summary, "total_runs", thresholds.get("min_total_runs"))
    _check_min_count(failures, summary, "models", thresholds.get("min_models"))
    _check_min_count(failures, summary, "schemas", thresholds.get("min_schemas"))
    _check_max(failures, summary, "missing_trace_rows", thresholds.get("max_missing_trace_rows"))
    _check_max(failures, summary, "uncheckable_result_rows", thresholds.get("max_uncheckable_result_rows"))
    _check_max(failures, summary, "infra_failed_rows", thresholds.get("max_infra_failed_rows"))

    if thresholds.get("require_rows", True) and not report.get("rows"):
        failures.append({"metric": "rows", "actual": 0, "required": ">0", "reason": "no result rows found"})
    if thresholds.get("require_traces", True):
        for error in trace_errors(report):
            failures.append({"metric": "trace_coverage", "actual": error, "required": "all case rows traceable"})

    status = "PASS" if not failures else "FAIL"
    return {
        "status": status,
        "thresholds": thresholds,
        "summary": summary,
        "failures": failures,
        "files": report.get("files", []),
        "model_scorecards": report.get("model_scorecards", []),
    }


def format_gate(result: dict[str, Any]) -> str:
    """Format a gate result as a concise human-readable report."""
    lines = ["# MBS Gate", "", f"Status: {result.get('status')}", ""]
    summary = result.get("summary") or {}
    lines.extend(
        [
            f"- Rows: {summary.get('rows', 0)}",
            f"- Infra-failed rows: {summary.get('infra_failed_rows', 0)}",
            f"- Traceable case rows: {summary.get('traceable_case_rows', 0)}",
            f"- Missing trace rows: {summary.get('missing_trace_rows', 0)}",
            f"- Mean schema-valid rate: {_fmt(summary.get('mean_schema_valid_rate'))}",
            f"- Mean semantic-correct rate: {_fmt(summary.get('mean_semantic_correct_rate'))}",
            f"- Mean clean-JSON rate: {_fmt(summary.get('mean_clean_json_rate'))}",
            "",
        ]
    )
    failures = result.get("failures") or []
    if failures:
        lines.extend(["## Failed thresholds", ""])
        for failure in failures:
            lines.append(
                f"- {failure.get('metric')}: actual={failure.get('actual')} required={failure.get('required')}"
            )
        lines.append("")
    else:
        lines.append("All configured thresholds passed.")
    return "\n".join(lines) + "\n"


def write_gate_json(path: str | Path, result: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")


def _check_min(failures: list[dict[str, Any]], summary: dict[str, Any], key: str, required: Any) -> None:
    if required is None:
        return
    actual = summary.get(key)
    if actual is None or float(actual) < float(required):
        failures.append({"metric": key, "actual": actual, "required": f">= {required}"})


def _check_max(failures: list[dict[str, Any]], summary: dict[str, Any], key: str, required: Any) -> None:
    if required is None:
        return
    actual = int(summary.get(key) or 0)
    if actual > int(required):
        failures.append({"metric": key, "actual": actual, "required": f"<= {required}"})


def _check_min_count(failures: list[dict[str, Any]], summary: dict[str, Any], key: str, required: Any) -> None:
    if required is None:
        return
    values = summary.get(key) or []
    actual = len(values) if isinstance(values, list) else 0
    if actual < int(required):
        failures.append({"metric": key, "actual": actual, "required": f">= {required}"})


def _load_yaml_text(text: str) -> dict[str, Any]:
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text) or {}
        if not isinstance(data, dict):
            raise ValueError("MBS YAML gate config must be an object")
        return data
    except ModuleNotFoundError:
        return _parse_simple_yaml(text)


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, data)]
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if ":" not in stripped:
            raise ValueError(f"Unsupported YAML config line: {raw_line}")
        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if raw_value == "":
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _parse_scalar(raw_value)
    return data


def _parse_scalar(value: str) -> Any:
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "None", "~"}:
        return None
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value.strip('"\'')


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)
