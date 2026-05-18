"""Assert that MBS CI produced reviewable evidence artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_CI_FILES = [
    "ci_bench.json",
    "ci_report.md",
    "ci_gate.json",
    "ci_environment.json",
    "evidence_pack_ci/manifest.json",
    "evidence_pack_ci/report.md",
    "evidence_pack_ci/report.json",
    "evidence_pack_ci/gate.json",
    "evidence_pack_ci/triage.json",
    "evidence_pack_ci/README.md",
    "nested_tool_fixture_pack/manifest.json",
    "nested_tool_fixture_pack/combined_report.md",
    "nested_tool_fixture_pack/combined_triage.json",
    "nested_tool_fixture_pack/nested_tool_good.mbs.json",
    "nested_tool_fixture_pack/nested_tool_bad.mbs.json",
    "nested_tool_fixture_pack/evidence_pack_good/manifest.json",
    "nested_tool_fixture_pack/evidence_pack_bad/manifest.json",
    "multi_schema_fixture_bundle/manifest.json",
    "multi_schema_fixture_bundle/README.md",
    "multi_schema_fixture_bundle/evidence_pack/manifest.json",
    "multi_schema_fixture_bundle/evidence_pack/report.md",
    "multi_schema_fixture_bundle/evidence_pack/gate.json",
    "multi_schema_fixture_bundle/results/incident_response_runbook.mbs.json",
    "multi_schema_fixture_bundle/results/fintech_transaction_risk.mbs.json",
    "multi_schema_fixture_bundle/results/support_ticket_triage.mbs.json",
    "multi_schema_fixture_bundle/results/nested_tool_arguments.mbs.json",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Assert MBS CI artifact completeness")
    parser.add_argument("--results-dir", default="benchmarks/results")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    missing = [name for name in REQUIRED_CI_FILES if not (results_dir / name).exists()]
    checks: dict[str, Any] = {"required_files": len(REQUIRED_CI_FILES), "missing_files": missing}

    ci_manifest = _read_json(results_dir / "evidence_pack_ci" / "manifest.json")
    nested_manifest = _read_json(results_dir / "nested_tool_fixture_pack" / "manifest.json")
    multi_schema_manifest = _read_json(results_dir / "multi_schema_fixture_bundle" / "manifest.json")
    environment_manifest = _read_json(results_dir / "ci_environment.json")
    good_manifest = _read_json(results_dir / "nested_tool_fixture_pack" / "evidence_pack_good" / "manifest.json")
    bad_manifest = _read_json(results_dir / "nested_tool_fixture_pack" / "evidence_pack_bad" / "manifest.json")

    checks.update(
        {
            "ci_classification": ci_manifest.get("classification"),
            "ci_gate_status": ci_manifest.get("checks", {}).get("gate_status"),
            "ci_trace_errors": ci_manifest.get("checks", {}).get("trace_errors"),
            "ci_environment_status": environment_manifest.get("status"),
            "ci_environment_type": environment_manifest.get("evidence_type"),
            "nested_status": nested_manifest.get("status"),
            "nested_classification": nested_manifest.get("classification"),
            "nested_schema_error_present": nested_manifest.get("checks", {}).get("nested_schema_error_present"),
            "nested_prose_wrapped_json_warning_present": nested_manifest.get("checks", {}).get(
                "prose_wrapped_json_warning_present"
            ),
            "nested_semantic_mismatch_present": nested_manifest.get("checks", {}).get("semantic_mismatch_present"),
            "multi_schema_status": multi_schema_manifest.get("status"),
            "multi_schema_classification": multi_schema_manifest.get("classification"),
            "multi_schema_report_rows": multi_schema_manifest.get("checks", {}).get("report_rows"),
            "multi_schema_total_runs": multi_schema_manifest.get("checks", {}).get("total_runs"),
            "multi_schema_traceable_case_rows": multi_schema_manifest.get("checks", {}).get("traceable_case_rows"),
            "multi_schema_gate_status": multi_schema_manifest.get("checks", {}).get("gate_status"),
            "multi_schema_cost_per_valid_output_present": multi_schema_manifest.get("checks", {}).get(
                "cost_per_valid_output_present"
            ),
            "good_pack_classification": good_manifest.get("classification"),
            "bad_pack_classification": bad_manifest.get("classification"),
        }
    )

    passed = (
        not missing
        and checks["ci_classification"] == "ci_regression_check_not_broad_model_benchmark"
        and checks["ci_gate_status"] == "PASS"
        and checks["ci_trace_errors"] == []
        and checks["ci_environment_status"] == "PASS"
        and checks["ci_environment_type"] == "ci_environment_manifest"
        and checks["nested_status"] == "PASS"
        and checks["nested_classification"] == "fixture_smoke_not_provider_benchmark"
        and checks["nested_schema_error_present"] is True
        and checks["nested_prose_wrapped_json_warning_present"] is True
        and checks["nested_semantic_mismatch_present"] is True
        and checks["multi_schema_status"] == "PASS"
        and checks["multi_schema_classification"] == "fixture_smoke_not_provider_benchmark"
        and checks["multi_schema_report_rows"] == 4
        and checks["multi_schema_total_runs"] == 49
        and checks["multi_schema_traceable_case_rows"] == 49
        and checks["multi_schema_gate_status"] == "PASS"
        and checks["multi_schema_cost_per_valid_output_present"] is True
        and checks["good_pack_classification"] == "fixture_smoke_not_provider_benchmark"
        and checks["bad_pack_classification"] == "fixture_smoke_not_provider_benchmark"
    )
    checks["status"] = "PASS" if passed else "FAIL"

    if args.json:
        print(json.dumps(checks, indent=2))
    else:
        print(f"MBS CI artifact check: {checks['status']}")
        if missing:
            print("Missing files:")
            for item in missing:
                print(f"- {item}")
    return 0 if passed else 2


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    raise SystemExit(main())
