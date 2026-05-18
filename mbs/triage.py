"""Triage helpers for remote MBS benchmark result directories."""

from __future__ import annotations

import glob
import json
from pathlib import Path
from typing import Any


def triage_results(
    results: list[str | Path],
    expected_models: str | Path | None = None,
    min_schema_valid_rate: float = 0.8,
    min_valid_json_rate: float = 0.9,
    require_traces: bool = True,
    max_failure_examples: int = 20,
) -> dict[str, Any]:
    files = _expand(results)
    expected = _load_expected_models(expected_models)
    observed: set[str] = set()
    issues: list[dict[str, Any]] = []
    failure_examples: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []

    for file_path in files:
        payload = _load_json_file(file_path, issues)
        if payload is None:
            continue
        for record in _records_from_payload(payload):
            rows = record.get("rows", [])
            summary = record.get("summary", {})
            model = record.get("model") or _model_from_rows(rows)
            if model:
                observed.add(model)
            item = {"file": str(file_path), "model": model, **summary}
            summaries.append(item)
            _check_summary(file_path, summary, min_schema_valid_rate, min_valid_json_rate, issues)
            if require_traces:
                _check_traces(file_path, rows, issues)
            if len(failure_examples) < max_failure_examples:
                remaining = max_failure_examples - len(failure_examples)
                failure_examples.extend(_failure_examples(file_path, record, limit=remaining))

    for model in sorted(expected - observed):
        issues.append({"type": "missing_model_result", "model": model})

    status = "FAIL" if issues else "PASS"
    return {
        "status": status,
        "files": [str(path) for path in files],
        "expected_models": sorted(expected),
        "observed_models": sorted(observed),
        "missing_models": sorted(expected - observed),
        "summaries": summaries,
        "issue_summary": _issue_summary(issues),
        "issues": issues,
        "failure_examples": failure_examples,
    }


def format_triage(result: dict[str, Any], *, max_issues: int | None = 50) -> str:
    lines = [
        f"Status: {result['status']}",
        f"Files: {len(result['files'])}",
        f"Observed models: {len(result['observed_models'])}",
        f"Missing models: {len(result['missing_models'])}",
    ]
    if result.get("issue_summary"):
        lines.append("")
        lines.append("Issue summary:")
        for key, count in result["issue_summary"].items():
            lines.append(f"- {key}: {count}")
    if result["issues"]:
        lines.append("")
        shown = result["issues"] if max_issues is None else result["issues"][:max_issues]
        lines.append(f"Issues shown: {len(shown)}/{len(result['issues'])}")
        for issue in shown:
            detail = ", ".join(f"{k}={v}" for k, v in issue.items())
            lines.append(f"- {detail}")
        if max_issues is not None and len(result["issues"]) > max_issues:
            lines.append(f"- truncated=true, remaining={len(result['issues']) - max_issues}")
    examples = result.get("failure_examples") or []
    if examples:
        lines.append("")
        lines.append(f"Failure examples: {len(examples)}")
        for example in examples:
            detail = ", ".join(f"{k}={v}" for k, v in example.items() if v not in (None, "", []))
            lines.append(f"- {detail}")
    return "\n".join(lines) + "\n"


def write_triage_json(path: str | Path, result: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _expand(paths: list[str | Path]) -> list[Path]:
    found: list[Path] = []
    for raw in paths:
        matches = [Path(p) for p in glob.glob(str(raw))]
        if matches:
            found.extend(matches)
        elif Path(raw).exists():
            found.append(Path(raw))
    return sorted({p.resolve() for p in found})


def _load_expected_models(path: str | Path | None) -> set[str]:
    if not path:
        return set()
    p = Path(path)
    if not p.exists():
        return set()
    models: set[str] = set()
    for raw_line in p.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        models.add(line.split("\t", 1)[0].strip())
    return models


def _load_json_file(path: Path, issues: list[dict[str, Any]]) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        issues.append({"type": "unreadable_result", "file": str(path), "error": str(exc)})
        return None


def _records_from_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [{"model": row.get("model"), "summary": row, "rows": []} for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return []
    return [
        {
            "model": payload.get("model"),
            "schema": payload.get("schema"),
            "prompt_style": payload.get("prompt_style"),
            "decoding_mode": payload.get("decoding_mode"),
            "language": payload.get("language"),
            "summary": payload.get("summary", {}),
            "rows": payload.get("rows", []),
        }
    ]


def _model_from_rows(rows: list[dict[str, Any]]) -> str | None:
    for row in rows:
        if isinstance(row, dict) and row.get("model"):
            return str(row["model"])
    return None


def _check_summary(
    file_path: Path,
    summary: dict[str, Any],
    min_schema_valid_rate: float,
    min_valid_json_rate: float,
    issues: list[dict[str, Any]],
) -> None:
    if not summary:
        issues.append({"type": "missing_summary", "file": str(file_path)})
        return
    if (summary.get("schema_valid_rate") or 0) < min_schema_valid_rate:
        issues.append(
            {
                "type": "low_schema_valid_rate",
                "file": str(file_path),
                "rate": summary.get("schema_valid_rate"),
                "threshold": min_schema_valid_rate,
            }
        )
    if (summary.get("valid_json_rate") or 0) < min_valid_json_rate:
        issues.append(
            {
                "type": "low_valid_json_rate",
                "file": str(file_path),
                "rate": summary.get("valid_json_rate"),
                "threshold": min_valid_json_rate,
            }
        )
    failure_types = summary.get("failure_types") or {}
    if failure_types:
        issues.append({"type": "failure_types_present", "file": str(file_path), "failure_types": failure_types})


def _check_traces(file_path: Path, rows: list[dict[str, Any]], issues: list[dict[str, Any]]) -> None:
    if not rows:
        issues.append({"type": "missing_rows", "file": str(file_path)})
        return
    missing = 0
    for row in rows:
        trace = row.get("trace") if isinstance(row, dict) else None
        if not isinstance(trace, dict) or not trace.get("trace_id") or not trace.get("tokens"):
            missing += 1
    if missing:
        issues.append({"type": "incomplete_traces", "file": str(file_path), "rows": missing})


def _failure_examples(file_path: Path, record: dict[str, Any], *, limit: int) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    rows = record.get("rows")
    if not isinstance(rows, list) or limit <= 0:
        return examples
    for row in rows:
        if not isinstance(row, dict) or not _is_failure_row(row):
            continue
        trace = row.get("trace") if isinstance(row.get("trace"), dict) else {}
        examples.append(
            {
                "failure_type": _row_failure_type(row),
                "case_id": row.get("case_id"),
                "model": row.get("model") or record.get("model"),
                "schema": row.get("schema") or record.get("schema"),
                "prompt_style": row.get("prompt_style") or record.get("prompt_style"),
                "language": row.get("language") or record.get("language"),
                "status": row.get("status"),
                "trace_id": trace.get("trace_id") if isinstance(trace, dict) else None,
                "detail": _failure_detail(row),
                "source": file_path.name,
            }
        )
        if len(examples) >= limit:
            break
    return examples


def _is_failure_row(row: dict[str, Any]) -> bool:
    if row.get("failure_type"):
        return True
    if row.get("status") and row.get("status") not in {"PASS", "OK"}:
        return True
    if row.get("schema_valid") is False:
        return True
    if row.get("semantic_correct") is False:
        return True
    return False


def _row_failure_type(row: dict[str, Any]) -> str:
    if row.get("failure_type"):
        return str(row["failure_type"])
    if row.get("json_valid") is False:
        return "invalid_json"
    if row.get("schema_valid") is False:
        return "schema_invalid"
    if row.get("semantic_correct") is False:
        return "semantic_mismatch"
    return str(row.get("status") or "unknown_failure")


def _failure_detail(row: dict[str, Any]) -> str:
    errors = row.get("errors")
    if isinstance(errors, list) and errors:
        first = errors[0]
        if isinstance(first, dict):
            parts = [str(first.get("field") or "$"), str(first.get("type") or _row_failure_type(row))]
            if "received" in first:
                parts.append(f"received={first['received']}")
            if "expected" in first:
                parts.append(f"expected={first['expected']}")
            if "allowed" in first:
                parts.append(f"allowed={first['allowed']}")
            return "; ".join(parts)
        return str(first)
    if row.get("semantic_correct") is False:
        return "semantic correctness check failed"
    if row.get("raw_text"):
        return str(row["raw_text"]).replace("\n", " ")[:180]
    return ""


def _issue_summary(issues: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for issue in issues:
        key = str(issue.get("type") or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))
