"""Audit retry attempt selection inside MBS benchmark outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .report import expand_paths


def audit_retry_attempts(paths: list[str | Path], *, max_examples: int = 20) -> dict[str, Any]:
    """Check that selected retry attempts do not regress versus attempt zero.

    This is intentionally different from comparing two independent benchmark
    directories. With sampled decoding, separate no-retry and retry jobs can
    drift even when they use the same nominal seed. This audit checks the
    invariant the runner can actually guarantee: the selected attempt in one
    retry run should not be worse than that run's first attempt.
    """

    files = expand_paths(paths)
    audited_rows = 0
    retried_rows = 0
    improved_rows = 0
    unchanged_rows = 0
    regressions: list[dict[str, Any]] = []

    for file_path in files:
        payload = json.loads(Path(file_path).read_text(encoding="utf-8"))
        for row in _case_rows(payload):
            attempts = [item for item in row.get("attempts", []) if isinstance(item, dict)]
            if len(attempts) < 2:
                continue
            audited_rows += 1
            retried_rows += 1 if int(row.get("retry_count") or 0) > 0 else 0
            first = attempts[0]
            selected = _selected_attempt(attempts)
            first_score = _attempt_score(first)
            selected_score = _attempt_score(selected)
            if selected_score < first_score:
                if len(regressions) < max_examples:
                    regressions.append(
                        {
                            "source": Path(file_path).name,
                            "case_id": row.get("case_id"),
                            "model": row.get("model") or payload.get("model"),
                            "schema": payload.get("schema") or row.get("schema"),
                            "prompt_style": row.get("prompt_style") or payload.get("prompt_style"),
                            "language": row.get("language") or payload.get("language"),
                            "first_attempt": _attempt_summary(first),
                            "selected_attempt": _attempt_summary(selected),
                        }
                    )
            elif selected_score > first_score:
                improved_rows += 1
            else:
                unchanged_rows += 1

    return {
        "status": "FAIL" if regressions else "PASS",
        "files": [str(path) for path in files],
        "audited_rows": audited_rows,
        "retried_rows": retried_rows,
        "improved_rows": improved_rows,
        "unchanged_rows": unchanged_rows,
        "selected_attempt_regressions": len(regressions),
        "regressions": regressions,
    }


def format_retry_audit(result: dict[str, Any]) -> str:
    lines = [
        f"Status: {result['status']}",
        f"Files: {len(result.get('files', []))}",
        f"Audited retry rows: {result.get('audited_rows', 0)}",
        f"Rows with retry count > 0: {result.get('retried_rows', 0)}",
        f"Selected attempt improvements: {result.get('improved_rows', 0)}",
        f"Selected attempt unchanged: {result.get('unchanged_rows', 0)}",
        f"Selected attempt regressions: {result.get('selected_attempt_regressions', 0)}",
    ]
    regressions = result.get("regressions") or []
    if regressions:
        lines.append("")
        lines.append("Regressions:")
        for item in regressions:
            label = " / ".join(
                str(value)
                for value in [
                    item.get("schema"),
                    item.get("model"),
                    item.get("prompt_style"),
                    item.get("language"),
                    item.get("case_id"),
                ]
                if value
            )
            lines.append(
                f"- {label}: first={item['first_attempt']} selected={item['selected_attempt']}"
            )
    return "\n".join(lines) + "\n"


def write_retry_audit_json(path: str | Path, result: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _case_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        rows = payload.get("rows")
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    return []


def _selected_attempt(attempts: list[dict[str, Any]]) -> dict[str, Any]:
    for attempt in attempts:
        if attempt.get("selected"):
            return attempt
    return attempts[-1]


def _attempt_score(attempt: dict[str, Any]) -> tuple[int, int, int, int]:
    semantic = attempt.get("semantic_correct")
    semantic_rank = {False: 0, None: 1, True: 2}.get(semantic, 1)
    schema_rank = 1 if attempt.get("schema_valid") else 0
    json_rank = 1 if attempt.get("json_valid") else 0
    failure_penalty = -_failure_severity(str(attempt.get("failure_type") or ""))
    return (schema_rank, semantic_rank, json_rank, failure_penalty)


def _failure_severity(failure_type: str) -> int:
    return {
        "invalid_json": 5,
        "invented_enum": 4,
        "invalid_enum": 3,
        "wrong_type": 3,
        "missing_required_key": 3,
        "semantic_mismatch": 2,
        "extra_key": 1,
    }.get(failure_type, 0)


def _attempt_summary(attempt: dict[str, Any]) -> dict[str, Any]:
    return {
        "attempt": attempt.get("attempt"),
        "json_valid": attempt.get("json_valid"),
        "schema_valid": attempt.get("schema_valid"),
        "semantic_correct": attempt.get("semantic_correct"),
        "failure_type": attempt.get("failure_type"),
    }
