"""Report aggregation for MBS benchmark outputs."""

from __future__ import annotations

import glob
import json
from pathlib import Path
from typing import Any

from .bench import summarize as summarize_case_rows


REPORT_COLUMNS = [
    "schema",
    "model",
    "prompt_style",
    "decoding_mode",
    "language",
    "runs",
    "avg_retry_count",
    "valid_json_rate",
    "clean_json_rate",
    "schema_valid_rate",
    "semantic_correct_rate",
    "enum_accuracy",
    "required_key_accuracy",
    "cost_per_valid_output_tokens",
    "infra_failure",
    "failure_types",
    "source",
]

SCORECARD_COLUMNS = [
    "model",
    "status",
    "format_risk",
    "rows",
    "runs",
    "avg_retry_count",
    "schema_valid_rate",
    "semantic_correct_rate",
    "valid_json_rate",
    "clean_json_rate",
    "cost_per_valid_output_tokens",
    "top_failures",
]

FAILURE_COLUMNS = ["failure_type", "count"]

DIMENSION_COLUMNS = [
    "dimension",
    "value",
    "rows",
    "runs",
    "avg_retry_count",
    "schema_valid_rate",
    "semantic_correct_rate",
    "valid_json_rate",
    "clean_json_rate",
    "top_failures",
]


def aggregate_results(paths: list[str | Path], *, exclude_infra: bool = False) -> dict[str, Any]:
    """Load one or more MBS result files and return normalized report rows."""
    files = expand_paths(paths)
    all_rows: list[dict[str, Any]] = []
    for file_path in files:
        payload = json.loads(Path(file_path).read_text(encoding="utf-8"))
        all_rows.extend(_rows_from_payload(payload, str(file_path)))
    rows = [row for row in all_rows if not _is_infra_row(row)] if exclude_infra else all_rows
    return {
        "files": [str(path) for path in files],
        "rows": rows,
        "summary": summarize_report_rows(rows, all_rows=all_rows),
        "model_scorecards": model_scorecards(rows),
        "dimension_scorecards": {
            "language": dimension_scorecards(rows, "language"),
            "prompt_style": dimension_scorecards(rows, "prompt_style"),
            "schema": dimension_scorecards(rows, "schema"),
        },
        "failure_summary": failure_summary(rows),
        "filters": {"exclude_infra": exclude_infra},
    }


def expand_paths(paths: list[str | Path]) -> list[Path]:
    """Expand file paths and glob patterns in a shell-independent way."""
    found: list[Path] = []
    for raw in paths:
        value = str(raw)
        matches = [Path(p) for p in glob.glob(value)]
        if matches:
            for match in matches:
                if match.is_dir():
                    found.extend(match.glob("*.json"))
                else:
                    found.append(match)
        else:
            path = Path(value)
            if path.exists():
                if path.is_dir():
                    found.extend(path.glob("*.json"))
                else:
                    found.append(path)
    return sorted({p.resolve() for p in found})


def markdown_report(report: dict[str, Any], *, summary_only: bool = False) -> str:
    rows = report.get("rows", [])
    lines = ["# MBS Benchmark Report", ""]
    summary = report.get("summary", {})
    lines.extend(
        [
            f"- Files: {len(report.get('files', []))}",
            f"- Rows: {summary.get('rows', 0)}",
            f"- Input rows: {summary.get('input_rows', summary.get('rows', 0))}",
            f"- Infra-failed rows: {summary.get('infra_failed_rows', 0)}",
            f"- Behavior rows: {summary.get('behavior_rows', summary.get('rows', 0))}",
            f"- Total runs: {summary.get('total_runs', 0)}",
            f"- Traceable case rows: {summary.get('traceable_case_rows', 0)}",
            f"- Missing trace rows: {summary.get('missing_trace_rows', 0)}",
            f"- Uncheckable result rows: {summary.get('uncheckable_result_rows', 0)}",
            f"- Mean schema-valid rate: {_fmt(summary.get('mean_schema_valid_rate'))}",
            f"- Mean behavior schema-valid rate: {_fmt(summary.get('mean_behavior_schema_valid_rate'))}",
            f"- Mean semantic-correct rate: {_fmt(summary.get('mean_semantic_correct_rate'))}",
            f"- Mean clean-JSON rate: {_fmt(summary.get('mean_clean_json_rate'))}",
            "",
        ]
    )
    if not rows:
        lines.append("No benchmark rows found.")
        return "\n".join(lines) + "\n"

    scorecards = report.get("model_scorecards", [])
    if scorecards:
        lines.extend(["## Model Scorecard", ""])
        lines.append("| " + " | ".join(SCORECARD_COLUMNS) + " |")
        lines.append("| " + " | ".join("---" for _ in SCORECARD_COLUMNS) + " |")
        for row in scorecards:
            cells = [_cell(row.get(col)) for col in SCORECARD_COLUMNS]
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")

    dimensions = report.get("dimension_scorecards", {})
    for key, title in (
        ("language", "Language Scorecard"),
        ("prompt_style", "Prompt Style Scorecard"),
        ("schema", "Schema Scorecard"),
    ):
        items = dimensions.get(key) if isinstance(dimensions, dict) else None
        if not items:
            continue
        lines.extend([f"## {title}", ""])
        lines.append("| " + " | ".join(DIMENSION_COLUMNS) + " |")
        lines.append("| " + " | ".join("---" for _ in DIMENSION_COLUMNS) + " |")
        for row in items:
            cells = [_cell(row.get(col)) for col in DIMENSION_COLUMNS]
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")

    failures = report.get("failure_summary", [])
    if failures:
        lines.extend(["## Failure Summary", ""])
        lines.append("| " + " | ".join(FAILURE_COLUMNS) + " |")
        lines.append("| " + " | ".join("---" for _ in FAILURE_COLUMNS) + " |")
        for row in failures:
            cells = [_cell(row.get(col)) for col in FAILURE_COLUMNS]
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")

    if summary_only:
        return "\n".join(lines) + "\n"

    lines.extend(["## Rows", ""])
    lines.append("| " + " | ".join(REPORT_COLUMNS) + " |")
    lines.append("| " + " | ".join("---" for _ in REPORT_COLUMNS) + " |")
    for row in rows:
        cells = [_cell(row.get(col)) for col in REPORT_COLUMNS]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def model_scorecards(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate result rows into ranked model scorecards."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        model = row.get("model")
        if not model:
            continue
        grouped.setdefault(str(model), []).append(row)

    cards: list[dict[str, Any]] = []
    for model, model_rows in grouped.items():
        schema_rate = _weighted_mean(model_rows, "schema_valid_rate")
        semantic_rate = _weighted_mean(model_rows, "semantic_correct_rate")
        valid_json_rate = _weighted_mean(model_rows, "valid_json_rate")
        clean_json_rate = _weighted_mean(model_rows, "clean_json_rate")
        cost = _weighted_mean(model_rows, "cost_per_valid_output_tokens")
        failures = _aggregate_failure_types(model_rows)
        format_risk = _format_risk(clean_json_rate, failures)
        cards.append(
            {
                "model": model,
                "status": _model_status(schema_rate, semantic_rate, clean_json_rate, failures),
                "format_risk": format_risk,
                "rows": len(model_rows),
                "runs": sum(int(row.get("runs") or 0) for row in model_rows),
                "avg_retry_count": _weighted_mean(model_rows, "avg_retry_count"),
                "schema_valid_rate": schema_rate,
                "semantic_correct_rate": semantic_rate,
                "valid_json_rate": valid_json_rate,
                "clean_json_rate": clean_json_rate,
                "cost_per_valid_output_tokens": cost,
                "top_failures": _top_failures(failures),
            }
        )
    return sorted(
        cards,
        key=lambda row: (
            _status_rank(row.get("status")),
            -(row.get("schema_valid_rate") or 0),
            -(row.get("semantic_correct_rate") or 0),
            str(row.get("model") or ""),
        ),
    )


def failure_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return aggregate failure-type counts across report rows."""
    counts = _aggregate_failure_types(rows)
    return [{"failure_type": key, "count": value} for key, value in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]


def dimension_scorecards(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    """Aggregate rows by a benchmark dimension such as language or prompt style."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        value = row.get(key)
        if value is None or value == "":
            value = "default"
        grouped.setdefault(str(value), []).append(row)

    cards: list[dict[str, Any]] = []
    for value, value_rows in grouped.items():
        failures = _aggregate_failure_types(value_rows)
        cards.append(
            {
                "dimension": key,
                "value": value,
                "rows": len(value_rows),
                "runs": sum(int(row.get("runs") or 0) for row in value_rows),
                "avg_retry_count": _weighted_mean(value_rows, "avg_retry_count"),
                "schema_valid_rate": _weighted_mean(value_rows, "schema_valid_rate"),
                "semantic_correct_rate": _weighted_mean(value_rows, "semantic_correct_rate"),
                "valid_json_rate": _weighted_mean(value_rows, "valid_json_rate"),
                "clean_json_rate": _weighted_mean(value_rows, "clean_json_rate"),
                "top_failures": _top_failures(failures),
            }
        )
    return sorted(
        cards,
        key=lambda row: (
            -(row.get("schema_valid_rate") or 0),
            -(row.get("semantic_correct_rate") or 0),
            str(row.get("value") or ""),
        ),
    )


def summarize_report_rows(rows: list[dict[str, Any]], *, all_rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    input_rows = all_rows if all_rows is not None else rows
    infra_rows = [row for row in input_rows if _is_infra_row(row)]
    behavior_rows = [row for row in input_rows if not _is_infra_row(row)]
    return {
        "rows": len(rows),
        "input_rows": len(input_rows),
        "infra_failed_rows": len(infra_rows),
        "behavior_rows": len(behavior_rows),
        "total_runs": sum(int(row.get("runs") or 0) for row in rows),
        "traceable_case_rows": sum(int(row.get("traceable_case_rows") or 0) for row in rows),
        "missing_trace_rows": sum(int(row.get("missing_trace_rows") or 0) for row in rows),
        "uncheckable_result_rows": sum(int(row.get("uncheckable_result_rows") or 0) for row in rows),
        "mean_schema_valid_rate": _mean(row.get("schema_valid_rate") for row in rows),
        "mean_behavior_schema_valid_rate": _mean(row.get("schema_valid_rate") for row in behavior_rows),
        "mean_semantic_correct_rate": _mean(row.get("semantic_correct_rate") for row in rows),
        "mean_clean_json_rate": _mean(row.get("clean_json_rate") for row in rows),
        "models": sorted({row.get("model") for row in rows if row.get("model")}),
        "schemas": sorted({row.get("schema") for row in rows if row.get("schema")}),
        "infra_failures": _count_values(row.get("infra_failure") for row in infra_rows),
    }


def _rows_from_payload(payload: Any, source: str) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [_normalize_row(row, source) for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return []
    if isinstance(payload.get("runs"), list):
        return [_normalize_row(row, source) for row in payload["runs"] if isinstance(row, dict)]
    if isinstance(payload.get("summary"), dict):
        row = dict(payload["summary"])
        case_rows = [item for item in payload.get("rows", []) if isinstance(item, dict)]
        if case_rows and any("schema_valid" in item for item in case_rows):
            row.update(summarize_case_rows(case_rows))
        sample_row = _first_payload_row(payload)
        row.setdefault("schema", payload.get("schema", source))
        row.setdefault("model", payload.get("model"))
        row.setdefault("prompt_style", payload.get("prompt_style") or sample_row.get("prompt_style"))
        row.setdefault(
            "decoding_mode",
            payload.get("decoding_mode") or sample_row.get("decoding_mode") or ("transformers" if payload.get("load_target") else None),
        )
        row.setdefault("language", payload.get("language") or sample_row.get("language"))
        row.setdefault("infra_failure", payload.get("infra_failure") or _infra_failure_from_rows(payload))
        trace_counts = _trace_counts(payload)
        row.setdefault("traceable_case_rows", trace_counts["traceable_case_rows"])
        row.setdefault("missing_trace_rows", trace_counts["missing_trace_rows"])
        row.setdefault("uncheckable_result_rows", trace_counts["uncheckable_result_rows"])
        return [_normalize_row(row, source)]
    return []


def _first_payload_row(payload: dict[str, Any]) -> dict[str, Any]:
    rows = payload.get("rows")
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict):
                return row
    return {}


def _normalize_row(row: dict[str, Any], source: str) -> dict[str, Any]:
    normalized = {col: row.get(col) for col in REPORT_COLUMNS}
    normalized["infra_failure"] = row.get("infra_failure") or _infra_failure_from_row(row)
    normalized["traceable_case_rows"] = row.get("traceable_case_rows")
    normalized["missing_trace_rows"] = row.get("missing_trace_rows")
    normalized["uncheckable_result_rows"] = row.get("uncheckable_result_rows")
    normalized["source"] = Path(source).name
    return normalized


def trace_errors(report: dict[str, Any]) -> list[str]:
    """Return report-level trace problems that should block headline claims."""
    summary = report.get("summary", {})
    errors: list[str] = []
    missing = int(summary.get("missing_trace_rows") or 0)
    uncheckable = int(summary.get("uncheckable_result_rows") or 0)
    if missing:
        errors.append(f"{missing} case rows are missing trace ids or token records")
    if uncheckable:
        errors.append(f"{uncheckable} result rows do not expose case rows for trace checking")
    return errors


def _trace_counts(payload: dict[str, Any]) -> dict[str, int]:
    rows = payload.get("rows")
    if not isinstance(rows, list):
        return {"traceable_case_rows": 0, "missing_trace_rows": 0, "uncheckable_result_rows": 1}
    missing = 0
    traceable = 0
    for row in rows:
        if not isinstance(row, dict):
            missing += 1
            continue
        trace = row.get("trace")
        if isinstance(trace, dict) and trace.get("trace_id") and trace.get("tokens"):
            traceable += 1
        else:
            missing += 1
    return {"traceable_case_rows": traceable, "missing_trace_rows": missing, "uncheckable_result_rows": 0}


def _infra_failure_from_rows(payload: dict[str, Any]) -> str | None:
    rows = payload.get("rows")
    if not isinstance(rows, list):
        return None
    for row in rows:
        failure = _infra_failure_from_row(row) if isinstance(row, dict) else None
        if failure:
            return failure
    return None


def _infra_failure_from_row(row: dict[str, Any]) -> str | None:
    if row.get("infra_failure"):
        return str(row["infra_failure"])
    if row.get("status") == "INFRA_FAIL":
        return str(row.get("failure_type") or "infra_failure")
    return None


def _is_infra_row(row: dict[str, Any]) -> bool:
    return bool(row.get("infra_failure"))


def _mean(values: Any) -> float | None:
    nums = [float(v) for v in values if isinstance(v, (int, float))]
    if not nums:
        return None
    return round(sum(nums) / len(nums), 4)


def _weighted_mean(rows: list[dict[str, Any]], key: str) -> float | None:
    weighted_sum = 0.0
    weight_total = 0
    for row in rows:
        value = row.get(key)
        if not isinstance(value, (int, float)):
            continue
        weight = int(row.get("runs") or 1)
        if weight <= 0:
            weight = 1
        weighted_sum += float(value) * weight
        weight_total += weight
    if not weight_total:
        return None
    return round(weighted_sum / weight_total, 4)


def _model_status(
    schema_rate: float | None,
    semantic_rate: float | None,
    clean_json_rate: float | None = None,
    failures: dict[str, int] | None = None,
) -> str:
    schema = schema_rate or 0.0
    semantic = semantic_rate if semantic_rate is not None else schema
    clean_json = 1.0 if clean_json_rate is None else clean_json_rate
    failures = failures or {}

    if failures.get("reasoning_prose") and clean_json < 0.75:
        return "FAIL"

    if schema >= 0.9 and semantic >= 0.8:
        if clean_json < 0.8:
            return "REVIEW"
        return "PASS"
    if schema >= 0.65 and semantic >= 0.6:
        return "REVIEW"
    return "FAIL"


def _format_risk(clean_json_rate: float | None, failures: dict[str, int]) -> str:
    clean_json = 1.0 if clean_json_rate is None else clean_json_rate
    if failures.get("reasoning_prose"):
        return "reasoning_prose"
    if failures.get("prose_wrapped_json"):
        return "prose_wrapped_json"
    if clean_json < 0.8:
        return "clean_json_low"
    return ""


def _status_rank(value: Any) -> int:
    return {"PASS": 0, "REVIEW": 1, "FAIL": 2}.get(str(value), 3)


def _aggregate_failure_types(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        failures = _failure_counts_from_value(row.get("failure_types"))
        infra_failure = row.get("infra_failure")
        if infra_failure:
            failures[str(infra_failure)] = failures.get(str(infra_failure), 0) + int(row.get("runs") or 1)
        for key, value in failures.items():
            counts[key] = counts.get(key, 0) + value
    return counts


def _failure_counts_from_value(value: Any) -> dict[str, int]:
    if isinstance(value, dict):
        return {str(k): int(v) for k, v in value.items() if isinstance(v, (int, float)) and v}
    if isinstance(value, str):
        text = value.strip()
        if not text or text == "{}":
            return {}
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {text: 1}
        if isinstance(parsed, dict):
            return {str(k): int(v) for k, v in parsed.items() if isinstance(v, (int, float)) and v}
    return {}


def _top_failures(counts: dict[str, int], *, limit: int = 3) -> str:
    if not counts:
        return ""
    items = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
    return ", ".join(f"{key}:{value}" for key, value in items)


def _count_values(values: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        if value:
            key = str(value)
            counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def _cell(value: Any) -> str:
    if isinstance(value, dict):
        if not value:
            return "{}"
        value = json.dumps(value, sort_keys=True, ensure_ascii=False)
    elif isinstance(value, float):
        value = f"{value:.4g}"
    elif value is None:
        value = ""
    else:
        value = str(value)
    return value.replace("|", "\\|").replace("\n", " ")
