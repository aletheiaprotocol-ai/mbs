"""Build a fixture-classified retry/repair matrix for hard nested tool arguments.

This script is intentionally deterministic and fixture-only. It proves the MBS
retry accounting surface before running the same retry policies against real
provider/OSS/HPC outputs. It must not be presented as model-behavior evidence.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mbs.adapter import adapt_response_jsonl
from mbs.bench import summarize
from mbs.report import aggregate_results, markdown_report
from mbs.retry_audit import audit_retry_attempts, format_retry_audit, write_retry_audit_json
from mbs.triage import triage_results, write_triage_json

CLASSIFICATION = "fixture_retry_matrix_not_provider_benchmark"
STRATEGIES = ("no_retry", "mbs_retry", "format_retry", "semantic_retry", "best_of_retry")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build hard nested retry/repair fixture matrix")
    parser.add_argument("--root", default=".", help="MBS repo root")
    parser.add_argument("--out-dir", default="results/nested_retry_matrix_fixture", help="Artifact output directory")
    parser.add_argument("--json", action="store_true", help="Print manifest JSON only")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    example_dir = root / "examples" / "nested_tool_arguments"
    schema = example_dir / "schema.json"
    cases = example_dir / "cases.jsonl"
    bad_responses = example_dir / "provider_tool_call_bad.jsonl"
    good_responses = example_dir / "provider_tool_call_good.jsonl"

    bad_payload = adapt_response_jsonl(
        schema,
        bad_responses,
        cases_path=cases,
        model="nested-tool-retry-fixture",
        decoding_mode="tool_call",
    )
    good_payload = adapt_response_jsonl(
        schema,
        good_responses,
        cases_path=cases,
        model="nested-tool-retry-fixture",
        decoding_mode="tool_call",
    )
    good_by_case = {row["case_id"]: row for row in good_payload["rows"]}

    strategy_files: dict[str, Path] = {}
    strategy_summaries: dict[str, dict[str, Any]] = {}
    policy_metrics: dict[str, dict[str, Any]] = {}
    for strategy in STRATEGIES:
        rows = [_row_for_strategy(row, good_by_case[row["case_id"]], strategy) for row in bad_payload["rows"]]
        summary = summarize(rows)
        payload = {
            "classification": CLASSIFICATION,
            "schema": str(schema),
            "cases": str(cases),
            "model": "nested-tool-retry-fixture",
            "prompt_style": "full",
            "decoding_mode": f"tool_call_{strategy}",
            "retry_policy": strategy,
            "summary": summary,
            "rows": rows,
        }
        path = out_dir / f"{strategy}.mbs.json"
        _write_json(path, payload)
        strategy_files[strategy] = path
        strategy_summaries[strategy] = payload["summary"]
        policy_metrics[strategy] = _policy_metrics(rows, summary)

    report = aggregate_results(list(strategy_files.values()))
    report_path = out_dir / "report.md"
    report_path.write_text(markdown_report(report, summary_only=True), encoding="utf-8")

    audit = audit_retry_attempts(list(strategy_files.values()))
    audit_path = out_dir / "retry_audit.json"
    write_retry_audit_json(audit_path, audit)
    audit_md = out_dir / "retry_audit.md"
    audit_md.write_text(format_retry_audit(audit), encoding="utf-8")

    triage = triage_results(list(strategy_files.values()), max_failure_examples=20)
    triage_path = out_dir / "triage.json"
    write_triage_json(triage_path, triage)

    matrix = {
        "classification": CLASSIFICATION,
        "evidence_boundary": "Deterministic fixture retry matrix; proves retry accounting and regression detection, not provider/model behavior.",
        "strategies": {
            name: {
                "summary": strategy_summaries[name],
                "policy_metrics": policy_metrics[name],
                "artifact": str(strategy_files[name]),
            }
            for name in STRATEGIES
        },
        "audit": {
            "status": audit.get("status"),
            "audited_rows": audit.get("audited_rows"),
            "retried_rows": audit.get("retried_rows"),
            "improved_rows": audit.get("improved_rows"),
            "unchanged_rows": audit.get("unchanged_rows"),
            "selected_attempt_regressions": audit.get("selected_attempt_regressions"),
        },
        "triage_status": triage.get("status"),
    }
    matrix_path = out_dir / "retry_matrix_summary.json"
    _write_json(matrix_path, matrix)

    checks = {
        "case_count": len(bad_payload["rows"]),
        "strategies": list(STRATEGIES),
        "no_retry_schema_valid_rate": strategy_summaries["no_retry"].get("schema_valid_rate"),
        "no_retry_semantic_correct_rate": strategy_summaries["no_retry"].get("semantic_correct_rate"),
        "format_retry_schema_valid_rate": strategy_summaries["format_retry"].get("schema_valid_rate"),
        "mbs_retry_schema_valid_rate": strategy_summaries["mbs_retry"].get("schema_valid_rate"),
        "mbs_retry_semantic_correct_rate": strategy_summaries["mbs_retry"].get("semantic_correct_rate"),
        "semantic_retry_semantic_correct_rate": strategy_summaries["semantic_retry"].get("semantic_correct_rate"),
        "best_of_schema_valid_rate": strategy_summaries["best_of_retry"].get("schema_valid_rate"),
        "best_of_semantic_correct_rate": strategy_summaries["best_of_retry"].get("semantic_correct_rate"),
        "selected_attempt_regressions": audit.get("selected_attempt_regressions"),
        "improved_rows": audit.get("improved_rows"),
        "triage_status": triage.get("status"),
    }
    passed = (
        checks["case_count"] == 25
        and checks["no_retry_schema_valid_rate"] == 0.72
        and checks["no_retry_semantic_correct_rate"] == 0.2
        and checks["mbs_retry_schema_valid_rate"] == 1.0
        and checks["mbs_retry_semantic_correct_rate"] == 1.0
        and checks["format_retry_schema_valid_rate"] == 1.0
        and checks["semantic_retry_semantic_correct_rate"] > checks["no_retry_semantic_correct_rate"]
        and checks["best_of_schema_valid_rate"] == 1.0
        and checks["best_of_semantic_correct_rate"] == 1.0
        and checks["selected_attempt_regressions"] == 0
        and checks["improved_rows"] > 0
    )

    manifest = {
        "classification": CLASSIFICATION,
        "status": "PASS" if passed else "FAIL",
        "artifacts": {
            "matrix": str(matrix_path),
            "report": str(report_path),
            "retry_audit": str(audit_path),
            "retry_audit_markdown": str(audit_md),
            "triage": str(triage_path),
            **{name: str(path) for name, path in strategy_files.items()},
        },
        "checks": checks,
        "next_evidence_gate": "Run equivalent retry policies against real provider/OSS/HPC response rows and classify them separately.",
    }
    _write_json(out_dir / "manifest.json", manifest)

    if args.json:
        print(json.dumps(manifest, indent=2))
    else:
        print(f"Nested retry matrix: {manifest['status']}")
        print(f"Classification: {manifest['classification']}")
        print(f"Matrix: {matrix_path}")
        print(f"Report: {report_path}")
        print(f"Retry audit: {audit_path}")
        print(f"Triage: {triage_path}")
    return 0 if passed else 2


def _row_for_strategy(bad_row: dict[str, Any], good_row: dict[str, Any], strategy: str) -> dict[str, Any]:
    first_attempt = _attempt_from_row(bad_row, 0, selected=False)
    should_repair = _should_repair(bad_row, strategy)
    selected = dict(good_row if should_repair else bad_row)
    selected["decoding_mode"] = f"tool_call_{strategy}"
    selected["retry_policy"] = strategy
    selected["retry_count"] = 1 if should_repair else 0
    selected["attempts"] = [first_attempt]
    if should_repair:
        selected["attempts"].append(_attempt_from_row(good_row, 1, selected=True))
        selected["repair_applied"] = True
    else:
        selected["attempts"][0]["selected"] = True
        selected["repair_applied"] = False
    return selected


def _should_repair(row: dict[str, Any], strategy: str) -> bool:
    if strategy == "no_retry":
        return False
    if strategy == "mbs_retry":
        return not _row_passes(row)
    if strategy == "best_of_retry":
        return not _row_passes(row)
    if strategy == "format_retry":
        return not row.get("json_valid") or not row.get("schema_valid")
    if strategy == "semantic_retry":
        return bool(row.get("schema_valid")) and row.get("semantic_correct") is False
    raise ValueError(f"unknown strategy: {strategy}")


def _row_passes(row: dict[str, Any]) -> bool:
    semantic = row.get("semantic_correct")
    semantic_ok = True if semantic is None else bool(semantic)
    return bool(row.get("json_valid")) and bool(row.get("schema_valid")) and semantic_ok and row.get("status") == "PASS"


def _attempt_from_row(row: dict[str, Any], attempt: int, *, selected: bool) -> dict[str, Any]:
    return {
        "attempt": attempt,
        "selected": selected,
        "json_valid": row.get("json_valid"),
        "schema_valid": row.get("schema_valid"),
        "semantic_correct": row.get("semantic_correct"),
        "failure_type": row.get("failure_type"),
        "status": row.get("status"),
    }


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


def _policy_metrics(rows: list[dict[str, Any]], summary: dict[str, Any]) -> dict[str, Any]:
    runs = len(rows)
    retried = [row for row in rows if int(row.get("retry_count") or 0) > 0]
    review = [row for row in rows if row.get("status") == "REVIEW"]
    failed = [row for row in rows if row.get("status") == "FAIL"]
    improved = 0
    unchanged = 0
    regressions = 0
    for row in rows:
        attempts = [item for item in row.get("attempts", []) if isinstance(item, dict)]
        if len(attempts) < 2:
            continue
        first_score = _attempt_score(attempts[0])
        selected = next((attempt for attempt in attempts if attempt.get("selected")), attempts[-1])
        selected_score = _attempt_score(selected)
        if selected_score > first_score:
            improved += 1
        elif selected_score == first_score:
            unchanged += 1
        else:
            regressions += 1
    return {
        "runs": runs,
        "retried_rows": len(retried),
        "improved_rows": improved,
        "unchanged_rows": unchanged,
        "selected_attempt_regressions": regressions,
        "human_review_rate": round(len(review) / runs, 4) if runs else None,
        "fail_rate": round(len(failed) / runs, 4) if runs else None,
        "repair_applied_rate": round(len(retried) / runs, 4) if runs else None,
        "clean_json_rate": summary.get("clean_json_rate"),
        "cost_per_valid_output_tokens": summary.get("cost_per_valid_output_tokens"),
    }


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
