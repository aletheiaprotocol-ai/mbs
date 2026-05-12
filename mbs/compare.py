"""Regression comparison helpers for MBS benchmark/test outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .report import aggregate_results


DEFAULT_METRICS = ["schema_valid_rate", "enum_accuracy", "semantic_correct_rate"]
DEFAULT_KEY_FIELDS = ["schema", "model", "prompt_style", "decoding_mode", "language"]


def compare_results(
    baseline_paths: list[str | Path],
    current_paths: list[str | Path],
    metrics: list[str] | None = None,
    max_drop: float = 0.0,
    key_fields: list[str] | None = None,
) -> dict[str, Any]:
    """Compare current MBS rows against baseline rows with matching keys."""
    metrics = metrics or DEFAULT_METRICS
    key_fields = key_fields or DEFAULT_KEY_FIELDS
    baseline = aggregate_results(baseline_paths)
    current = aggregate_results(current_paths)
    baseline_by_key = {_row_key(row, key_fields): row for row in baseline["rows"]}
    comparisons: list[dict[str, Any]] = []
    regressions: list[dict[str, Any]] = []
    missing_baseline: list[dict[str, Any]] = []

    for row in current["rows"]:
        key = _row_key(row, key_fields)
        base = baseline_by_key.get(key)
        if not base:
            missing_baseline.append({"key": key, "current": _row_identity(row)})
            continue
        for metric in metrics:
            before = base.get(metric)
            after = row.get(metric)
            if not isinstance(before, (int, float)) or not isinstance(after, (int, float)):
                continue
            delta = round(after - before, 4)
            item = {
                "key": key,
                "schema": row.get("schema"),
                "model": row.get("model"),
                "prompt_style": row.get("prompt_style"),
                "decoding_mode": row.get("decoding_mode"),
                "language": row.get("language"),
                "metric": metric,
                "baseline": before,
                "current": after,
                "delta": delta,
            }
            comparisons.append(item)
            if delta < -max_drop:
                regressions.append(item)

    status = "FAIL" if regressions else "PASS"
    if not comparisons:
        status = "NO_MATCH"

    return {
        "status": status,
        "metrics": metrics,
        "key_fields": key_fields,
        "max_drop": max_drop,
        "comparisons": comparisons,
        "regressions": regressions,
        "missing_baseline": missing_baseline,
        "baseline_files": baseline["files"],
        "current_files": current["files"],
    }


def format_compare(result: dict[str, Any]) -> str:
    lines = [f"Status: {result['status']}", f"Metrics: {', '.join(result['metrics'])}"]
    if result.get("key_fields"):
        lines.append(f"Match keys: {', '.join(result['key_fields'])}")
    if result["status"] == "NO_MATCH":
        lines.append("No comparable rows matched between baseline and current results.")
        lines.append("Check schema, model, prompt_style, decoding_mode, and language keys.")
    elif result["regressions"]:
        lines.append("")
        lines.append("Regression detected:")
        for item in result["regressions"]:
            label = _label(item)
            lines.append(
                f"- {label}: {item['metric']} dropped from {item['baseline']} to {item['current']} "
                f"(delta {item['delta']})"
            )
    else:
        lines.append("No regression detected.")
    if result["missing_baseline"]:
        lines.append("")
        lines.append(f"Rows without baseline: {len(result['missing_baseline'])}")
    return "\n".join(lines) + "\n"


def write_compare_json(path: str | Path, result: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _row_key(row: dict[str, Any], fields: list[str] | None = None) -> str:
    fields = fields or DEFAULT_KEY_FIELDS
    parts = [row.get(field) or "" for field in fields]
    return "|".join(str(part) for part in parts)


def _row_identity(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": row.get("schema"),
        "model": row.get("model"),
        "prompt_style": row.get("prompt_style"),
        "decoding_mode": row.get("decoding_mode"),
        "language": row.get("language"),
    }


def _label(item: dict[str, Any]) -> str:
    bits = [
        item.get("schema"),
        item.get("model"),
        item.get("prompt_style"),
        item.get("decoding_mode"),
        item.get("language"),
    ]
    return " / ".join(str(bit) for bit in bits if bit)
