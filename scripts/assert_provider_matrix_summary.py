"""Validate the public sanitized provider matrix summary package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_FAILURE_MODES = {"schema_clean_semantic_mismatch", "format_schema_failure"}


def validate_summary(path: Path) -> dict[str, Any]:
    summary = json.loads(path.read_text(encoding="utf-8"))
    failures: list[str] = []

    if summary.get("classification") != "provider":
        failures.append("classification must be provider")
    if summary.get("raw_artifacts_public") is not False:
        failures.append("raw_artifacts_public must be false")

    rows = summary.get("rows", [])
    if len(rows) < 3:
        failures.append("summary must include at least three provider rows")

    modes = {row.get("primary_failure_mode") for row in rows}
    if not REQUIRED_FAILURE_MODES <= modes:
        failures.append("summary must preserve semantic and format/schema failure modes")

    for idx, row in enumerate(rows):
        prefix = f"rows[{idx}] {row.get('deployment', '<unknown>')}: "
        if row.get("gate_status") != "FAIL":
            failures.append(prefix + "gate_status must remain FAIL")
        if row.get("traceable_case_rows") != summary.get("case_count"):
            failures.append(prefix + "traceable_case_rows must equal case_count")
        if row.get("infra_failed_rows") != 0:
            failures.append(prefix + "infra_failed_rows must be 0")
        if row.get("primary_failure_mode") == "schema_clean_semantic_mismatch":
            if row.get("schema_valid_rate") != 1.0 or row.get("semantic_correct_rate", 1.0) >= 0.8:
                failures.append(prefix + "semantic mismatch rows must be schema-clean and below semantic gate")
        if row.get("primary_failure_mode") == "format_schema_failure" and row.get("schema_valid_rate") != 0.0:
            failures.append(prefix + "format/schema failure row must preserve schema_valid_rate 0.0")

    checks = summary.get("checks", {})
    expected_checks = {
        "all_rows_are_failures": True,
        "all_rows_traceable": True,
        "no_infra_failures": True,
        "semantic_failures_preserved": True,
        "format_schema_failure_preserved": True,
    }
    for key, expected in expected_checks.items():
        if checks.get(key) is not expected:
            failures.append(f"checks.{key} must be {expected}")

    return {"status": "FAIL" if failures else "PASS", "failures": failures, "rows": len(rows)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--summary",
        default="docs/provider_matrix_summary_20260514/provider_matrix_summary.json",
        help="Path to the sanitized provider matrix summary JSON.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    args = parser.parse_args(argv)

    result = validate_summary(Path(args.summary))
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Provider matrix summary: {result['status']} ({result['rows']} rows)")
        for failure in result["failures"]:
            print(f"- {failure}")
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
