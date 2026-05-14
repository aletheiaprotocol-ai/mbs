"""Validate the sanitized MBS-Lang provider summary package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


EXPECTED_LANGUAGES = ["ar", "de", "en", "es", "fr", "hu", "tr"]
EXPECTED_LABEL = "real_provider_mbs_lang_behavior_evidence"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate sanitized MBS-Lang provider summary")
    parser.add_argument(
        "--summary",
        default="docs/mbs_lang_provider_summary_20260514/mbs_lang_provider_matrix.json",
        help="Path to summary JSON",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    summary_path = Path(args.summary)
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    failures = validate_summary(payload)
    result = {
        "status": "PASS" if not failures else "FAIL",
        "summary": str(summary_path),
        "failures": failures,
        "rows": len(payload.get("rows", [])),
    }
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"{result['status']}: {summary_path} ({result['rows']} rows)")
        for failure in failures:
            print(f"- {failure}")
    return 0 if not failures else 2


def validate_summary(payload: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if payload.get("classification") != "provider":
        failures.append("classification must be provider")
    if payload.get("classification_label") != EXPECTED_LABEL:
        failures.append(f"classification_label must be {EXPECTED_LABEL}")
    if payload.get("raw_provider_outputs_public") is not False:
        failures.append("raw_provider_outputs_public must be false")
    if not payload.get("evidence_boundary"):
        failures.append("evidence_boundary is required")
    if not payload.get("non_claims"):
        failures.append("non_claims are required")

    rows = payload.get("rows", [])
    if len(rows) != 3:
        failures.append("expected exactly three provider matrix rows")
        return failures

    by_model = {row.get("model"): row for row in rows}
    expected_models = {"gpt-5-3-chat", "gpt-4-1-nano", "gpt-5-nano"}
    if set(by_model) != expected_models:
        failures.append(f"models must be {sorted(expected_models)}")

    for row in rows:
        if row.get("case_runs") != 7 or row.get("traceable_case_rows") != 7:
            failures.append(f"{row.get('model')} case_runs and traceable_case_rows must both equal 7")
        if row.get("missing_trace_rows") != 0:
            failures.append(f"{row.get('model')} missing_trace_rows must be 0")
        if row.get("infra_failed_rows") != 0:
            failures.append(f"{row.get('model')} infra_failed_rows must be 0")
        if sorted(row.get("languages", [])) != EXPECTED_LANGUAGES:
            failures.append(f"{row.get('model')} languages must be {EXPECTED_LANGUAGES}")
        if row.get("input_language_rows_present") is not True:
            failures.append(f"{row.get('model')} input_language_rows_present must be true")
        if row.get("contract_language_en") is not True:
            failures.append(f"{row.get('model')} contract_language_en must be true")
        if row.get("trace_errors") != 0:
            failures.append(f"{row.get('model')} trace_errors must be 0")

    for model in ("gpt-5-3-chat", "gpt-4-1-nano"):
        row = by_model.get(model, {})
        if row.get("gate_status") != "PASS":
            failures.append(f"{model} gate_status must be PASS")
        for metric in ("schema_valid_rate", "semantic_correct_rate", "clean_json_rate", "valid_json_rate"):
            if row.get(metric) != 1.0:
                failures.append(f"{model} {metric} must be 1.0")

    fail_row = by_model.get("gpt-5-nano", {})
    if fail_row.get("gate_status") != "FAIL":
        failures.append("gpt-5-nano gate_status must be FAIL")
    if fail_row.get("primary_failure_mode") != "format_schema_failure":
        failures.append("gpt-5-nano primary_failure_mode must be format_schema_failure")
    if fail_row.get("top_failures") != "invalid_json:7":
        failures.append("gpt-5-nano top_failures must be invalid_json:7")
    for metric in ("schema_valid_rate", "semantic_correct_rate", "clean_json_rate", "valid_json_rate"):
        if fail_row.get(metric) != 0.0:
            failures.append(f"gpt-5-nano {metric} must be 0.0")
    return failures


if __name__ == "__main__":
    raise SystemExit(main())
